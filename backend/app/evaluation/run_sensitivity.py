import os
import sys

# Ensure backend directory is in the path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.evaluation.sensitivity import run_lambda_sweep

"""
A helper script to trigger TERA utility sensitivity sweeping over lambda values
[0.2, 0.4, 0.6, 0.8, 1.0] and generate MD and JSON reports.
"""

def main() -> None:
    """
    Purpose:
        Executes the utility sensitivity sweep runner on the sample benchmark.
    """
    base_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(base_dir, "sample_benchmark.csv")
    models_dir = os.path.abspath(os.path.join(base_dir, "../models"))
    
    print("====================================================")
    print("Running TERA Utility Sensitivity Analysis Sweep...")
    print(f"Benchmark Dataset: {dataset_path}")
    print(f"Model Directory: {models_dir}")
    print("====================================================")
    
    lambda_values = [0.2, 0.4, 0.6, 0.8, 1.0]
    
    # Run the sweep
    run_lambda_sweep(
        dataset_path=dataset_path,
        models_dir=models_dir,
        lambda_values=lambda_values,
        c2=10.0,
        c3=100.0,
        alpha_dense=0.9
    )
    
    print("\n----------------------------------------------------")
    print("Sweep executed successfully.")
    print(f"Reports saved to: {base_dir}")
    print("====================================================")

if __name__ == "__main__":
    main()
