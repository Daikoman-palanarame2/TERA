import os
import sys

# Ensure backend directory is in the path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.evaluation.evaluator import EvaluationRunner

"""
A helper script to trigger TERA benchmarking against always-cheap, always-dense,
and random routing baseline strategies.
"""

def main() -> None:
    """
    Purpose:
        Loads the sample benchmark dataset, executes the evaluator runner, 
        and writes MD and JSON reports comparing TERA against baselines.
    """
    base_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(base_dir, "sample_benchmark.csv")
    models_dir = os.path.abspath(os.path.join(base_dir, "../models"))
    
    print("====================================================")
    print("Running TERA Offline Evaluation & Benchmarking Framework...")
    print(f"Benchmark Dataset: {dataset_path}")
    print(f"Model Directory: {models_dir}")
    print("====================================================")
    
    runner = EvaluationRunner()
    # Configuration parameters derived from research specifications
    results = runner.run_benchmark(
        dataset_path=dataset_path,
        models_dir=models_dir,
        c2=10.0,
        c3=100.0,
        lambda_coeff=0.5,
        alpha_dense=0.9
    )
    
    print("\n----------------------------------------------------")
    print("Execution Summary")
    print("----------------------------------------------------")
    print(f"Dataset Size:          {results['tera']['dataset_size']}")
    print(f"TERA Blended Accuracy: {results['tera']['accuracy']:.4f}")
    print(f"TERA Average Cost:     {results['tera']['average_cost']:.2f} tokens")
    print(f"TERA Average Latency:  {results['tera']['average_latency_ms']:.2f} ms")
    print(f"ECE (Calibration Err): {results['tera']['expected_calibration_error']:.4f}")
    print(f"Brier Score:           {results['tera']['brier_score']:.4f}")
    print("----------------------------------------------------")
    print(f"Reports successfully saved to: {base_dir}")
    print("====================================================")

if __name__ == "__main__":
    main()
