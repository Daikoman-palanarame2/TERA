import unittest
import sys
import os
import tempfile
import json

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.evaluation.sensitivity import run_lambda_sweep

class TestSensitivity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/models"))
        self.benchmark_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/evaluation/sample_benchmark.csv"))
        self.lambda_values = [0.2, 0.5, 0.8]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_lambda_sweep_execution(self):
        """
        Tests that run_lambda_sweep completes successfully, returns the expected
        dictionary structures, and writes JSON and MD report files.
        """
        c2 = 12.0
        c3 = 120.0
        alpha_dense = 0.88
        
        sweep_data = run_lambda_sweep(
            dataset_path=self.benchmark_csv,
            models_dir=self.models_dir,
            lambda_values=self.lambda_values,
            c2=c2,
            c3=c3,
            alpha_dense=alpha_dense,
            output_dir=self.temp_dir.name
        )
        
        # 1. Verify returned structure
        self.assertIn("experiment_metadata", sweep_data)
        self.assertIn("sweep_results", sweep_data)
        
        meta = sweep_data["experiment_metadata"]
        self.assertEqual(meta["c2"], c2)
        self.assertEqual(meta["c3"], c3)
        self.assertEqual(meta["alpha_dense"], alpha_dense)
        self.assertEqual(meta["dataset_path"], os.path.abspath(self.benchmark_csv))
        self.assertIn("timestamp", meta)
        self.assertIn("training_metadata", meta)
        
        # Check training metadata holds schema if loaded (might be empty if not run in repo, but it should exist)
        if meta["training_metadata"]:
            self.assertIn("schema_version", meta["training_metadata"])
            
        results = sweep_data["sweep_results"]
        self.assertEqual(len(results), len(self.lambda_values))
        
        for i, res in enumerate(results):
            self.assertEqual(res["lambda"], self.lambda_values[i])
            self.assertIn("accuracy", res)
            self.assertIn("average_token_cost", res)
            self.assertIn("average_normalized_cost", res)
            self.assertIn("cheap_route_pct", res)
            self.assertIn("cascade_route_pct", res)
            self.assertIn("dense_route_pct", res)
            self.assertIn("escalation_rate_pct", res)
            self.assertIn("false_cheap_decisions", res)
            self.assertIn("false_dense_decisions", res)
            self.assertIn("expected_calibration_error", res)
            self.assertIn("brier_score", res)
            
        # 2. Verify files are generated
        json_path = os.path.join(self.temp_dir.name, "lambda_sensitivity.json")
        md_path = os.path.join(self.temp_dir.name, "lambda_sensitivity.md")
        
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))
        
        # Verify JSON file parses and holds data
        with open(json_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
            self.assertEqual(len(file_data["sweep_results"]), len(self.lambda_values))
            self.assertEqual(file_data["experiment_metadata"]["c2"], c2)

if __name__ == "__main__":
    unittest.main()
