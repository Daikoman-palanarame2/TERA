import os
import json
import datetime
import tempfile
from typing import List, Dict, Any, Optional

from app.evaluation.evaluator import EvaluationRunner

"""
This module performs utility sensitivity evaluations by sweeping the Lagrangian
trade-off parameter (lambda) and analyzing its effects on system accuracy, 
routing distributions, cost bounds, and calibration scores.
It logs experiment metadata for complete scientific reproducibility.
"""

def run_lambda_sweep(
    dataset_path: str,
    models_dir: str,
    lambda_values: List[float],
    c2: float,
    c3: float,
    alpha_dense: float,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Purpose:
        Sweeps lambda values over the dataset to analyze trade-off behaviors.
        Reuses EvaluationRunner without duplicating any routing or evaluation logic.
        
    Inputs:
        dataset_path: Path to the labeled CSV benchmark dataset.
        models_dir: Folder containing trained model artifacts.
        lambda_values: List of floats representing lambda values to evaluate.
        c2: Cost threshold of the cheap model.
        c3: Cost threshold of the dense model (C_max).
        alpha_dense: Constant baseline accuracy parameter of the dense model.
        output_dir: Target folder to save output reports.
        
    Outputs:
        A dictionary containing the compiled sweep results and experiment metadata.
        
    Time/Memory Complexity:
        O(M * N * Routing_Overhead) where M is lambda sweep size and N is dataset size.
    """
    # 1. Load trained models metadata if available
    metadata_path = os.path.join(models_dir, "training_metadata.json")
    training_meta = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                training_meta = json.load(f)
        except Exception:
            pass
            
    # 2. Build experiment metadata block
    experiment_metadata = {
        "c2": c2,
        "c3": c3,
        "alpha_dense": alpha_dense,
        "dataset_path": os.path.abspath(dataset_path),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "training_metadata": training_meta
    }
    
    sweep_results = []
    
    # 3. Instantiate EvaluationRunner
    runner = EvaluationRunner()
    
    # 4. Iterate over lambda values
    for val in lambda_values:
        # Execute run_benchmark in a temporary directory to avoid overwriting base reports
        with tempfile.TemporaryDirectory() as tmp_dir:
            res = runner.run_benchmark(
                dataset_path=dataset_path,
                models_dir=models_dir,
                c2=c2,
                c3=c3,
                lambda_coeff=val,
                alpha_dense=alpha_dense,
                output_dir=tmp_dir
            )
            
        tera = res["tera"]
        dist = tera.get("routing_distribution_pct", {})
        confusion = tera.get("false_decisions", {})
        
        sweep_results.append({
            "lambda": val,
            "accuracy": tera.get("accuracy"),
            "average_token_cost": tera.get("average_cost"),
            "average_normalized_cost": tera.get("average_normalized_cost"),
            "cheap_route_pct": dist.get("cheap"),
            "cascade_route_pct": dist.get("cascade"),
            "dense_route_pct": dist.get("dense"),
            "escalation_rate_pct": tera.get("escalation_rate_pct"),
            "false_cheap_decisions": confusion.get("false_cheap"),
            "false_dense_decisions": confusion.get("false_dense"),
            "expected_calibration_error": tera.get("expected_calibration_error"),
            "brier_score": tera.get("brier_score")
        })
        
    compiled_data = {
        "experiment_metadata": experiment_metadata,
        "sweep_results": sweep_results
    }
    
    # 5. Generate Markdown report
    md_content = _generate_sweep_markdown(experiment_metadata, sweep_results)
    
    # 6. Save reports
    target_dir = output_dir if output_dir else os.path.dirname(dataset_path)
    os.makedirs(target_dir, exist_ok=True)
    
    json_path = os.path.join(target_dir, "lambda_sensitivity.json")
    md_path = os.path.join(target_dir, "lambda_sensitivity.md")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(compiled_data, f, indent=4)
        
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    return compiled_data


def _generate_sweep_markdown(metadata: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    """
    Purpose:
        Helper to format sweep results and experiment metadata into Markdown.
    """
    t_meta = metadata.get("training_metadata", {})
    
    md = []
    md.append("# TERA Utility Sensitivity Sweep Report\n")
    
    md.append("## Experiment Metadata")
    md.append(f"- **Execution Timestamp:** {metadata.get('timestamp')}")
    md.append(f"- **Evaluated Dataset:** `{metadata.get('dataset_path')}`")
    md.append(f"- **Cheap Model Cost ($C_2$):** {metadata.get('c2')}")
    md.append(f"- **Dense Model Cost ($C_max$ / $C_3$):** {metadata.get('c3')}")
    md.append(f"- **Dense Baseline Accuracy ($\\alpha_{{dense}}$):** {metadata.get('alpha_dense')}")
    
    if t_meta:
        md.append(f"- **Trained Model Schema:** version {t_meta.get('schema_version', 'N/A')}")
        md.append(f"- **Trained Feature Schema:** version {t_meta.get('feature_version', 'N/A')}")
        md.append(f"- **Training Dataset Size:** {t_meta.get('dataset_size', 'N/A')} prompts")
        md.append(f"- **Scikit-learn Environment:** version {t_meta.get('scikit_learn_version', 'N/A')}")
    md.append("\n")
    
    md.append("## Parameter Sensitivity Sweep Table")
    md.append("| $\\lambda$ | Accuracy | Avg Cost | Avg Norm Cost | Cheap % | Cascade % | Dense % | Escalation % | False Cheap | False Dense | ECE | Brier |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    for r in results:
        md.append(
            f"| {r['lambda']:.2f} | "
            f"{r['accuracy']:.4f} | "
            f"{r['average_token_cost']:.2f} | "
            f"{r['average_normalized_cost']:.4f} | "
            f"{r['cheap_route_pct']:.1f}% | "
            f"{r['cascade_route_pct']:.1f}% | "
            f"{r['dense_route_pct']:.1f}% | "
            f"{r['escalation_rate_pct']:.1f}% | "
            f"{r['false_cheap_decisions']} | "
            f"{r['false_dense_decisions']} | "
            f"{r['expected_calibration_error']:.4f} | "
            f"{r['brier_score']:.4f} |"
        )
    md.append("\n")
    
    md.append("## Sensitivity Diagnostics & Observations")
    md.append("- **Frugality vs Accuracy Policy:** As $\\lambda$ increases towards 1.0, the router places higher weight on task success probability, leading to higher rates of direct Dense/Cascade selections and higher average token costs.")
    md.append("- **Calibration Stability:** Check the ECE and Brier score across sweeps; stable calibration values indicate that the routing decisions remain sound across different policy trade-off parameters.")
    
    return "\n".join(md)
