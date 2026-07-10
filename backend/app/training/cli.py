import argparse
import sys
import os

# Ensure backend directory is in the path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.training.trainer import run_training_pipeline

"""
This module serves as the command-line entry point to invoke the offline training pipeline.
"""

def main() -> None:
    """
    Purpose:
        Entry point function for TERA training CLI. Parses arguments and starts pipeline.
        
    Inputs:
        None (uses command-line arguments in sys.argv).
        
    Outputs:
        None
    """
    parser = argparse.ArgumentParser(
        description="TERA (Token-Efficient Routing Agent) Labeled Training Pipeline CLI"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to the labeled CSV dataset containing prompt, label, and optional domain columns."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "../models"),
        help="Directory to save the trained model weights and calibration artifacts."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Integer seed for deterministic splits and training algorithms (default: 42)."
    )
    
    args = parser.parse_args()
    
    try:
        run_training_pipeline(
            dataset_path=args.dataset,
            output_dir=args.output,
            seed=args.seed
        )
    except Exception as e:
        print(f"Training pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
