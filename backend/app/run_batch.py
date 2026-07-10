import os
import sys
import json
import argparse
import asyncio
from typing import List, Dict, Any

# Ensure backend directory is in the path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.settings import settings
from app.router.runtime_router import RuntimeRouter
from app.verification.verification_types import SchemaType
from app.verification.rovl import ROVL
from app.inference.inference_types import InferenceRequest
from app.inference.orchestrator import InferenceOrchestrator
from app.inference.fireworks_model import FireworksModel
from app.inference.cheap_model import CheapModel
from app.inference.dense_model import DenseModel

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TERA Batch Processing Harness")
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
        "--mock",
        action="store_true",
        help="Use mock model adapters for offline testing"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run startup self-test verifying models, settings, and orchestrator loading without network calls"
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
    orchestrator: InferenceOrchestrator,
    c2: float,
    c3: float,
    lambda_coeff: float,
    alpha_dense: float,
    results_dict: Dict[int, Dict[str, Any]],
    telemetry_dict: Dict[int, Dict[str, Any]],
    results_lock: asyncio.Lock,
    output_path: str,
    telemetry_path: str
) -> None:
    task_id = task.get("task_id") or task.get("id") or f"task-{index}"
    prompt = task.get("prompt")
    
    if not prompt:
        print(f"Warning: Skipping task {task_id} due to empty prompt.")
        async with results_lock:
            results_dict[index] = {
                "task_id": task_id,
                "answer": ""
            }
            telemetry_dict[index] = {
                "task_id": task_id,
                "selected_route": "skipped",
                "escalated": False,
                "error": "Empty prompt",
                "metadata": {}
            }
            sorted_res = [results_dict[k] for k in sorted(results_dict.keys())]
            sorted_tele = [telemetry_dict[k] for k in sorted(telemetry_dict.keys())]
            save_atomic(output_path, sorted_res)
            save_atomic(telemetry_path, sorted_tele)
        return
        
    # Parse schema type
    schema_str = str(task.get("schema_type", "none")).lower()
    if schema_str == "json":
        schema_type = SchemaType.JSON
    elif schema_str == "regex":
        schema_type = SchemaType.REGEX
    else:
        schema_type = SchemaType.NONE

    # Build request payload
    request = InferenceRequest(
        prompt=prompt,
        c2=c2,
        c3=c3,
        lambda_coeff=lambda_coeff,
        alpha_dense=alpha_dense,
        schema_type=schema_type,
        regex_pattern=task.get("regex_pattern"),
        min_chars=task.get("min_chars"),
        max_chars=task.get("max_chars")
    )

    async with semaphore:
        try:
            response = await orchestrator.run_async(request)
            answer_val = response.final_response
            route_val = response.selected_route.value
            escalated_val = response.escalated
            meta_val = response.metadata
            err_val = None
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error processing task {task_id}: {e}", file=sys.stderr)
            answer_val = ""
            route_val = "error"
            escalated_val = False
            meta_val = {}
            err_val = str(e)

    async with results_lock:
        results_dict[index] = {
            "task_id": task_id,
            "answer": answer_val
        }
        
        tele_item = {
            "task_id": task_id,
            "selected_route": route_val,
            "escalated": escalated_val,
            "metadata": meta_val
        }
        if err_val:
            tele_item["error"] = err_val
        telemetry_dict[index] = tele_item
        
        # Write files atomically and sorted after each task completes
        sorted_res = [results_dict[k] for k in sorted(results_dict.keys())]
        sorted_tele = [telemetry_dict[k] for k in sorted(telemetry_dict.keys())]
        save_atomic(output_path, sorted_res)
        save_atomic(telemetry_path, sorted_tele)

def main() -> None:
    args = parse_args()
    
    if args.self_test:
        print("Running TERA Self-Test Mode...")
        try:
            # 1. Verify settings load
            cheap = settings.cheap_model
            dense = settings.dense_model
            print(f"  Settings Loaded. Cheap: {cheap}, Dense: {dense}")
            
            # 2. Verify models load and router initializes
            models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
            router = RuntimeRouter(models_dir)
            print("  Router & Calibration Models Loaded OK.")
            
            # 3. Verify orchestrator initializes
            cheap_model = CheapModel()
            dense_model = DenseModel()
            rovl = ROVL(entropy_threshold=settings.entropy_threshold)
            _ = InferenceOrchestrator(router, cheap_model, dense_model, rovl)
            print("  Orchestrator Initialized OK.")
            
            # 4. Configuration validation warning if API key absent
            if not settings.fireworks_api_key:
                print("  Note: FIREWORKS_API_KEY is not set (expected for dry runs).")
            else:
                print("  FIREWORKS_API_KEY is set.")
                
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

    # 3. Environment pre-flight validations (unless in mock mode)
    if not args.mock:
        try:
            settings.validate_production()
        except ValueError as val_err:
            print(f"Pre-flight configuration failed: {val_err}", file=sys.stderr)
            sys.exit(1)

    # 4. Initialize TERA Components
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
    router = RuntimeRouter(models_dir)
    
    if args.mock:
        print("Initializing with offline mock model adapters...")
        cheap_model = CheapModel()
        dense_model = DenseModel()
    else:
        print(f"Initializing Fireworks Model Adapters: {settings.cheap_model} & {settings.dense_model}")
        cheap_model = FireworksModel(model_name=settings.cheap_model)
        dense_model = FireworksModel(model_name=settings.dense_model)

    rovl = ROVL(entropy_threshold=settings.entropy_threshold)
    orchestrator = InferenceOrchestrator(router, cheap_model, dense_model, rovl)

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
    telemetry_dict: Dict[int, Dict[str, Any]] = {}
    results_lock = asyncio.Lock()
    
    print(f"Processing {len(tasks)} tasks...")

    async def run_all() -> None:
        sem = asyncio.Semaphore(max_concurrency)
        tasks_list = [
            process_task(
                i, t, sem, orchestrator, c2, c3, lambda_coeff, alpha_dense,
                results_dict, telemetry_dict, results_lock, output_path, telemetry_path
            )
            for i, t in enumerate(tasks)
        ]
        await asyncio.gather(*tasks_list)

    try:
        asyncio.run(run_all())
        print(f"Batch execution completed. Outputs saved to {output_path}")
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nBatch processing interrupted or cancelled. Exiting gracefully.", file=sys.stderr)
        sys.exit(130)

    sys.exit(0)

if __name__ == "__main__":
    main()
