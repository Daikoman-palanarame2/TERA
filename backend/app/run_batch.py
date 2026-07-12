import os
import sys
import json
import argparse
import asyncio
from typing import List, Dict, Any

# Ensure backend directory is in the path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings, ENTROPY_THRESHOLD, MIN_PROBABILITY_FLOOR, MODEL_TIMEOUT_SEC, FALLBACK_RETRY_COUNT
from app.cache.semantic_cache import SemanticCache
from app.parser.intent_parser import IntentParser
from app.solvers.solver_registry import SolverRegistry
from app.solvers.plugins.arithmetic_solver import ArithmeticSolver
from app.solvers.plugins.logic_solver import LogicSolver
from app.solvers.plugins.text_counter_solver import TextCounterSolver
from app.solvers.plugins.word_problem_solver import WordProblemSolver
from app.inference.local_client import LocalModelClient
from app.inference.local_power_client import LocalPowerModelClient
from app.inference.remote_client import RemoteModelClient
from app.verification.rovl import ROVL
from app.core.orchestrator import TERAOrchestrator
from app.schemas.data_contracts import InferenceRequest

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TERA V2 Batch Processing Harness")
    parser.add_argument(
        "--input", 
        type=str, 
        default="/input/tasks.json", 
        help="Path to tasks input JSON file (default: /input/tasks.json)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="/output/results.json", 
        help="Path to results output JSON file (default: /output/results.json)"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run startup self-test verifying models, settings, and orchestrator loading without network calls"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run batch processing in mock mode using fast dummy model outputs instead of real inference"
    )
    return parser.parse_args()

def save_atomic(output_path: str, data: List[Dict[str, Any]]) -> None:
    """
    Saves a JSON list atomically to output_path using a temporary file
    and forcing write to disk via fsync before replacing.
    """
    dir_name = os.path.dirname(output_path)
    tmp_path = os.path.join(dir_name, f"{os.path.basename(output_path)}.tmp") if dir_name else f"{output_path}.tmp"
    
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            # Ignore if fsync is not supported by target filesystem/volume mount
            pass
            
    os.replace(tmp_path, output_path)

async def process_task(
    index: int,
    task: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    orchestrator: TERAOrchestrator,
    c2: float,
    c3: float,
    lambda_coeff: float,
    alpha_dense: float,
    results_dict: Dict[int, Dict[str, Any]],
    results_lock: asyncio.Lock,
    output_path: str,
    metadata: Dict[str, Any]
) -> None:
    task_id_raw = task.get("task_id") or task.get("id") or f"task_{index}_default"
    prompt = task.get("prompt")
    
    # Clean task ID to satisfy strict Pydantic pattern constraint: ^task_\d+_[a-zA-Z0-9]+$
    cleaned_id = "".join(c for c in str(task_id_raw) if c.isalnum())
    if not cleaned_id:
        cleaned_id = "default"
    conforming_task_id = f"task_{index}_{cleaned_id}"
    
    if not prompt:
        print(f"Warning: Skipping task {task_id_raw} due to empty prompt.")
        async with results_lock:
            results_dict[index] = {
                "task_id": task_id_raw,
                "answer": ""
            }
            sorted_res = [results_dict[k] for k in sorted(results_dict.keys())]
            save_atomic(output_path, sorted_res)
        return
        
    # Parse schema type
    schema_str = str(task.get("schema_type", "none")).lower()
    
    # Retrieve category from metadata if available
    t_meta = metadata.get(str(task_id_raw)) or metadata.get(task_id_raw) or {}
    category = t_meta.get("category", "unknown")
    
    # Build request payload conforming to V2 InferenceRequest
    request = InferenceRequest(
        prompt=prompt,
        task_id=conforming_task_id,
        c2=c2,
        c3=c3,
        lambda_coeff=lambda_coeff,
        alpha_dense=alpha_dense,
        schema_type=schema_str,
        regex_pattern=task.get("regex_pattern"),
        category=category
    )

    async with semaphore:
        try:
            response = await orchestrator.process_request_async(request)
            answer_val = response.final_response
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error processing task {task_id_raw}: {e}", file=sys.stderr)
            answer_val = ""

    async with results_lock:
        results_dict[index] = {
            "task_id": task_id_raw,
            "answer": answer_val
        }
        
        # Write files atomically and sorted after each task completes
        sorted_res = [results_dict[k] for k in sorted(results_dict.keys())]
        save_atomic(output_path, sorted_res)

def main() -> None:
    args = parse_args()
    
    if args.self_test:
        print("Running TERA Self-Test Mode...")
        try:
            # 1. Verify settings load
            local_name = settings.tera_local_model_name
            remote_name = settings.tera_remote_model_name
            print(f"  Settings Loaded. Local: {local_name}, Remote: {remote_name}")
            
            # 2. Verify cache and registry loads
            cache = SemanticCache(
                cache_dir=settings.tera_cache_dir,
                embedding_model_path=settings.tera_onnx_model_path
            )
            print("  Semantic Cache OK.")
            
            # 3. Solver registry setup
            registry = SolverRegistry()
            registry.register_solver(ArithmeticSolver())
            registry.register_solver(LogicSolver())
            registry.register_solver(TextCounterSolver())
            registry.register_solver(WordProblemSolver())
            registry.lock()
            print("  Solvers Registered & Locked OK.")
            
            # 4. Model clients setup
            local_client = LocalModelClient(
                endpoint_url=settings.tera_local_inference_url,
                model_name=settings.tera_local_model_name,
                timeout_sec=settings.tera_model_timeout_sec
            )
            if settings.tera_external_fallback_enabled:
                if not settings.tera_fireworks_api_key:
                    raise RuntimeError(
                        "TERA_FIREWORKS_API_KEY is required when external fallback is enabled."
                    )
                remote_client = RemoteModelClient(
                    api_key=settings.tera_fireworks_api_key,
                    endpoint_url=settings.tera_fireworks_api_url,
                    model_name=settings.tera_remote_model_name,
                    max_retries=FALLBACK_RETRY_COUNT
                )
            else:
                remote_client = LocalPowerModelClient(
                    endpoint_url=settings.tera_power_inference_url,
                    model_name=settings.tera_power_model_name,
                    timeout_sec=settings.tera_model_timeout_sec
                )
            print("  Local & Remote model clients OK.")
            
            # 5. Verify orchestrator initializes
            rovl = ROVL(
                entropy_threshold=ENTROPY_THRESHOLD,
                min_prob_floor=MIN_PROBABILITY_FLOOR
            )
            _ = TERAOrchestrator(
                cache=cache,
                parser=IntentParser(registry),
                registry=registry,
                local_client=local_client,
                remote_client=remote_client,
                rovl=rovl,
                settings=settings
            )
            print("  Orchestrator V2 Initialized OK.")
            
            # Clean up cache database handle
            cache.env.close()
            
            # Configuration validation warning if API key absent
            if not settings.tera_fireworks_api_key:
                print("  Note: TERA_FIREWORKS_API_KEY is not set (expected for dry runs).")
            else:
                print("  TERA_FIREWORKS_API_KEY is set.")
                
            print("Self-test passed successfully.")
            sys.exit(0)
        except Exception as e:
            print(f"Self-test failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 1. Resolve paths (fallback to local cwd paths if root-level paths don't exist and we're not in Docker)
    input_path = args.input
    if not os.path.exists(input_path) and input_path == "/input/tasks.json":
        local_input = "input/tasks.json"
        if os.path.exists(local_input):
            input_path = local_input
            
    output_path = args.output
    if output_path == "/output/results.json" and not os.path.exists("/output"):
        # If output directory doesn't exist, try local directory
        os.makedirs("output", exist_ok=True)
        output_path = "output/results.json"
    else:
        # Ensure parent output directory exists
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

    telemetry_path = os.path.join(os.path.dirname(output_path), "telemetry.json")
    settings.tera_telemetry_path = telemetry_path

    metadata_path = "evaluation/benchmark_metadata.json"
    metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            print(f"Loaded benchmark metadata for {len(metadata)} tasks.")
        except Exception as e:
            print(f"Warning: Failed to load benchmark metadata: {e}")

    print(f"Reading tasks from: {input_path}")
    print(f"Writing results to: {output_path}")
    print(f"Writing telemetry to: {telemetry_path}")

    # 2. Check input file
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except Exception as e:
        print(f"Error parsing input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(tasks, list):
        print("Error: Input JSON must be a list of tasks.", file=sys.stderr)
        sys.exit(1)

    # 3. Initialize TERA V2 Components
    print("Initializing TERA V2 pipeline components...")
    if args.mock:
        class MockSemanticCache:
            def __init__(self):
                class FakeEnv:
                    def close(self):
                        pass
                self.env = FakeEnv()
            def lookup(self, prompt: str):
                return None
            def update(self, prompt: str, response: Any):
                pass
            def insert(self, prompt: str, response: str):
                pass
            def close(self):
                pass
        cache = MockSemanticCache()  # type: ignore
    else:
        cache = SemanticCache(
            cache_dir=settings.tera_cache_dir,
            embedding_model_path=settings.tera_onnx_model_path
        )
    registry = SolverRegistry()
    registry.register_solver(ArithmeticSolver())
    registry.register_solver(LogicSolver())
    registry.register_solver(TextCounterSolver())
    registry.register_solver(WordProblemSolver())
    registry.lock()
    
    parser = IntentParser(registry)
    
    if args.mock:
        from app.schemas.data_contracts import RawModelOutput, TokenLogprob
        class MockModelClient:
            def __init__(self, answer_text: str):
                self.answer_text = answer_text
            async def generate_async(self, prompt: str, params: Any = None) -> RawModelOutput:
                # Return conforming JSON structure if prompt indicates json/regex schema requested
                if "json" in prompt.lower() or "schema" in prompt.lower() or "payload" in prompt.lower():
                    text = '{"status": "success", "data": "mocked"}\n'
                else:
                    text = self.answer_text
                return RawModelOutput(
                    text=text,
                    tokens=[TokenLogprob(token="tok", logprob=-0.05)],
                    latency_ms=10.0,
                    usage_tokens=len(text) // 4
                )
            async def generate_n_async(self, prompt: str, n: int, params: Any = None) -> list:
                results = []
                for i in range(n):
                    out = await self.generate_async(prompt, params)
                    results.append({
                        "success": True,
                        "output": out,
                        "error": None,
                        "latency_ms": out.latency_ms,
                        "usage_tokens": out.usage_tokens,
                        "prompt_tokens": max(0, out.usage_tokens - len(out.tokens)),
                        "completion_tokens": len(out.tokens)
                    })
                return results
            async def close(self):
                pass
        local_client = MockModelClient("Mocked local answer")  # type: ignore
        remote_client = MockModelClient("Mocked remote fallback answer")  # type: ignore
    else:
        local_client = LocalModelClient(
            endpoint_url=settings.tera_local_inference_url,
            model_name=settings.tera_local_model_name,
            timeout_sec=settings.tera_model_timeout_sec
        )
        if settings.tera_external_fallback_enabled:
            if not settings.tera_fireworks_api_key:
                raise RuntimeError(
                    "TERA_FIREWORKS_API_KEY is required when external fallback is enabled."
                )
            remote_client = RemoteModelClient(
                api_key=settings.tera_fireworks_api_key,
                endpoint_url=settings.tera_fireworks_api_url,
                model_name=settings.tera_remote_model_name,
                max_retries=FALLBACK_RETRY_COUNT
            )
        else:
            remote_client = LocalPowerModelClient(
                endpoint_url=settings.tera_power_inference_url,
                model_name=settings.tera_power_model_name,
                timeout_sec=settings.tera_model_timeout_sec
            )
    rovl = ROVL(
        entropy_threshold=ENTROPY_THRESHOLD,
        min_prob_floor=MIN_PROBABILITY_FLOOR
    )
    orchestrator = TERAOrchestrator(
        cache=cache,
        parser=parser,
        registry=registry,
        local_client=local_client,
        remote_client=remote_client,
        rovl=rovl,
        settings=settings
    )

    # Load routing cost coefficients from environment
    c2 = float(os.environ.get("C2", 10.0))
    c3 = float(os.environ.get("C3", 100.0))
    lambda_coeff = float(os.environ.get("LAMBDA", 0.5))
    alpha_dense = float(os.environ.get("ALPHA_DENSE", 0.9))

    # Bounded concurrency settings
    max_concurrency = int(os.environ.get("MAX_CONCURRENCY", "4"))
    print(f"Max concurrency: {max_concurrency}")

    # 5. Process Batch
    results_dict: Dict[int, Dict[str, Any]] = {}
    results_lock = asyncio.Lock()
    
    print(f"Processing {len(tasks)} tasks...")

    async def run_all() -> None:
        sem = asyncio.Semaphore(max_concurrency)
        tasks_list = [
            process_task(
                i, t, sem, orchestrator, c2, c3, lambda_coeff, alpha_dense,
                results_dict, results_lock, output_path, metadata
            )
            for i, t in enumerate(tasks)
        ]
        await asyncio.gather(*tasks_list)

    try:
        asyncio.run(run_all())
        print(f"Batch execution completed. Outputs saved to {output_path}")
        
        # Format the telemetry file as a JSON array for offline compliance if in evaluation
        if "evaluation" in telemetry_path.lower() and os.path.exists(telemetry_path):
            try:
                tele_data = []
                with open(telemetry_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            line_content = line.strip()
                            if line_content.startswith("[") and line_content.endswith("]"):
                                tele_data.extend(json.loads(line_content))
                                break
                            elif line_content.startswith("{"):
                                tele_data.append(json.loads(line_content))
                with open(telemetry_path, "w", encoding="utf-8") as f:
                    json.dump(tele_data, f, indent=4)
                print(f"Formatted telemetry file as a JSON array: {telemetry_path}")
            except Exception as e:
                print(f"Warning: Failed to format telemetry file as JSON array: {e}")
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nBatch processing interrupted or cancelled. Exiting gracefully.", file=sys.stderr)
        sys.exit(130)
    finally:
        # Shutdown connection pools and handles cleanly
        asyncio.run(local_client.close())
        asyncio.run(remote_client.close())
        cache.env.close()

    sys.exit(0)

if __name__ == "__main__":
    main()
