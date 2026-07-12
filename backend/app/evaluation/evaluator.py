import os
import asyncio
import numpy as np
from typing import Dict, Any, Optional

from app.verification.rovl import ROVL
from app.schemas.data_contracts import InferenceRequest, RawModelOutput, TokenLogprob
from app.inference.model_interface import ModelInterface
from app.inference.dense_model import DenseModel
from app.inference.inference_types import ModelOutput
from app.training.dataset import load_csv_dataset
from app.evaluation.baselines import run_always_cheap, run_always_dense, run_random_routing
from app.evaluation.metrics import compute_evaluation_metrics
from app.evaluation.report import generate_json_report, generate_markdown_report
from app.core.config import settings
from app.cache.semantic_cache import SemanticCache
from app.solvers.solver_registry import SolverRegistry
from app.solvers.plugins.arithmetic_solver import ArithmeticSolver
from app.solvers.plugins.logic_solver import LogicSolver
from app.solvers.plugins.text_counter_solver import TextCounterSolver
from app.parser.intent_parser import IntentParser
from app.core.orchestrator import TERAOrchestrator

class LabeledMockCheapModel(ModelInterface):
    """
    Purpose:
        A mock cheap model that deterministically returns successful conforming completions
        or malformed completions based on the ground truth labels from the evaluation dataset,
        preventing prompt mutations.
    """
    def __init__(self, outcomes_map: Dict[str, int]) -> None:
        self.outcomes_map = outcomes_map

    def generate(self, prompt: str) -> ModelOutput:
        label = self.outcomes_map.get(prompt, 1)
        if label == 0:
            # Malformed string: fails JSON schema and lacks '\n' stop token
            return ModelOutput(
                text="Malformed mock completion without stop token",
                token_probs=[0.99, 0.99]
            )
        else:
            # Successful conforming stop-token-terminated string
            return ModelOutput(
                text='{"status": "success"}\n',
                token_probs=[0.99, 0.99]
            )

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        import math
        res = self.generate(prompt)
        probs = res.token_probs if res.token_probs is not None else [0.99]
        tokens = [TokenLogprob(token="tok", logprob=math.log(max(p, 1e-9))) for p in probs]
        return RawModelOutput(
            text=res.text,
            tokens=tokens,
            latency_ms=10.0,
            usage_tokens=max(1, len(res.text) // 4)
        )


class EvaluationRunner:
    """
    Purpose:
        Orchestrates labeled dataset evaluations. Runs TERA, runs baselines,
        computes evaluation metrics, and compiles structured reporting targets.
    """

    def run_benchmark(
        self,
        dataset_path: str,
        models_dir: str,
        c2: float = 10.0,
        c3: float = 100.0,
        lambda_coeff: float = 0.5,
        alpha_dense: float = 0.9,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the evaluation pipeline over a loaded benchmark dataset.
        """
        # 1. Load benchmark dataset
        dataset = load_csv_dataset(dataset_path)
        if not dataset:
            raise ValueError(f"Benchmark dataset at {dataset_path} is empty.")
            
        # 2. Build outcomes map for mock cheap model
        outcomes_map = {item[0]: item[1] for item in dataset}
        labels = np.array([item[1] for item in dataset])
        
        try:
            cache = SemanticCache(
                cache_dir=settings.tera_cache_dir,
                embedding_model_path=settings.tera_onnx_model_path
            )
        except Exception:
            class MockSemanticCache:
                def lookup(self, prompt: str, threshold: float = 0.95) -> Any:
                    return None
                def insert(self, prompt: str, response: str) -> None:
                    pass
                def close(self) -> None:
                    pass
            cache = MockSemanticCache()  # type: ignore
        registry = SolverRegistry()
        registry.register_solver(ArithmeticSolver())
        registry.register_solver(LogicSolver())
        registry.register_solver(TextCounterSolver())
        registry.lock()
        parser = IntentParser(registry)
        
        cheap_model = LabeledMockCheapModel(outcomes_map)
        dense_model = DenseModel(default_text="Dense clean response\n")
        rovl = ROVL(entropy_threshold=3.0)
        
        orchestrator = TERAOrchestrator(
            cache=cache,
            parser=parser,
            registry=registry,
            local_client=cheap_model,  # type: ignore
            remote_client=dense_model,  # type: ignore
            rovl=rovl,
            settings=settings
        )
        
        # 4. Execute orchestrator over dataset prompts
        query_logs = []
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        for prompt, label, domain in dataset:
            # We configure schema checking to JSON so malformed outputs trigger ROVL schema failure
            request = InferenceRequest(
                prompt=prompt,
                task_id=f"task_{len(query_logs)}_eval",
                c2=c2,
                c3=c3,
                lambda_coeff=lambda_coeff,
                alpha_dense=alpha_dense,
                schema_type="json"
            )
            
            response = loop.run_until_complete(orchestrator.process_request_async(request))
            
            query_logs.append({
                "prompt": prompt,
                "selected_route": "cheap" if response.route_taken in {"cache", "solver", "local_llm"} else "dense",
                "escalated": response.route_taken == "remote_fallback",
                "calibrated_probability": 0.0 if response.route_taken in {"cache", "solver", "local_llm"} else 1.0,
                "cheap_utility": 1.0 if response.route_taken in {"cache", "solver", "local_llm"} else 0.0,
                "dense_utility": 1.0 if response.route_taken == "remote_fallback" else 0.0,
                "cascade_utility": 0.0,
                "latency_ms": response.latency_ms,
                "verification_status": ("pass" if response.verification.passed else "fail") if response.verification else "skipped"
            })
            
        # 5. Compute TERA metrics
        tera_metrics = compute_evaluation_metrics(query_logs, labels, c2, c3, alpha_dense)
        
        # 6. Compute baselines
        baselines_data = {
            "always_cheap": run_always_cheap(dataset, c2, c3),
            "always_dense": run_always_dense(dataset, c3, alpha_dense),
            "random_routing": run_random_routing(dataset, c2, c3, alpha_dense)
        }
        
        # 7. Generate reports
        json_report = generate_json_report(tera_metrics, baselines_data)
        md_report = generate_markdown_report(tera_metrics, baselines_data)
        
        # 8. Save reports
        target_dir = output_dir if output_dir else os.path.dirname(dataset_path)
        os.makedirs(target_dir, exist_ok=True)
        
        json_path = os.path.join(target_dir, "evaluation_report.json")
        md_path = os.path.join(target_dir, "evaluation_report.md")
        
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_report)
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)
            
        return {
            "tera": tera_metrics,
            "baselines": baselines_data
        }
