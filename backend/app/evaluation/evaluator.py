import os
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from app.router.runtime_router import RuntimeRouter
from app.verification.verification_types import SchemaType
from app.verification.rovl import ROVL
from app.inference.inference_types import InferenceRequest, ModelOutput
from app.inference.model_interface import ModelInterface
from app.inference.dense_model import DenseModel
from app.inference.orchestrator import InferenceOrchestrator
from app.training.dataset import load_csv_dataset
from app.evaluation.baselines import run_always_cheap, run_always_dense, run_random_routing
from app.evaluation.metrics import compute_evaluation_metrics
from app.evaluation.report import generate_json_report, generate_markdown_report

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


class EvaluationRunner:
    """
    Purpose:
        Orchestrates labeled dataset evaluations. Runs TERA, runs baselines,
        calculates metrics, and writes JSON/Markdown performance reports.
        
    Time Complexity:
        O(N * (L + Q * log(M))) dominated by TERA routing overhead per prompt.
        
    Memory Complexity:
        O(N) to hold dataset lists and evaluation logs.
    """

    def run_benchmark(
        self,
        dataset_path: str,
        models_dir: str,
        c2: float,
        c3: float,
        lambda_coeff: float,
        alpha_dense: float,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Purpose:
            Executes the end-to-end benchmark comparison.
            
        Inputs:
            dataset_path: Filepath to the CSV benchmark dataset.
            models_dir: Folder containing trained model artifacts.
            c2: Cheap model cost.
            c3: Dense model cost (C_max).
            lambda_coeff: Lagrangian trade-off multiplier.
            alpha_dense: Baseline dense accuracy.
            output_dir: Optional custom folder to save report outputs.
            
        Outputs:
            A dictionary containing TERA and baseline performance statistics.
        """
        # 1. Load benchmark dataset
        dataset = load_csv_dataset(dataset_path)
        if not dataset:
            raise ValueError(f"Benchmark dataset at {dataset_path} is empty.")
            
        # 2. Build outcomes map for mock cheap model
        outcomes_map = {item[0]: item[1] for item in dataset}
        labels = np.array([item[1] for item in dataset])
        
        # 3. Instantiate pipeline components
        router = RuntimeRouter(models_dir)
        cheap_model = LabeledMockCheapModel(outcomes_map)
        dense_model = DenseModel(default_text="Dense clean response\n")
        rovl = ROVL(entropy_threshold=3.0)
        orchestrator = InferenceOrchestrator(router, cheap_model, dense_model, rovl)
        
        # 4. Execute orchestrator over dataset prompts
        query_logs = []
        for prompt, label, domain in dataset:
            # We configure schema checking to JSON so malformed outputs trigger ROVL schema failure
            request = InferenceRequest(
                prompt=prompt,
                c2=c2,
                c3=c3,
                lambda_coeff=lambda_coeff,
                alpha_dense=alpha_dense,
                schema_type=SchemaType.JSON
            )
            
            response = orchestrator.run(request)
            
            query_logs.append({
                "prompt": prompt,
                "selected_route": response.selected_route.value,
                "escalated": response.escalated,
                "calibrated_probability": response.routing_decision.calibrated_probability,
                "cheap_utility": response.routing_decision.cheap_utility,
                "dense_utility": response.routing_decision.dense_utility,
                "cascade_utility": response.routing_decision.cascade_utility,
                "latency_ms": response.metadata["inference_time_ms"],
                "verification_status": response.verification_result.status.value if response.verification_result else "skipped"
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
