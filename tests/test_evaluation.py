import unittest
import sys
import os
import tempfile
import json
import numpy as np

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.evaluation.baselines import run_always_cheap, run_always_dense, run_random_routing
from app.evaluation.metrics import compute_evaluation_metrics
from app.evaluation.report import generate_json_report, generate_markdown_report
from app.evaluation.evaluator import LabeledMockCheapModel, EvaluationRunner
from app.training.dataset import load_csv_dataset

class TestEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/models"))
        self.benchmark_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/evaluation/sample_benchmark.csv"))
        
        # Labeled mock dataset
        self.samples = [
            ("calculate sum 1 + 2", 1, "math"),
            ("debug memory leak error", 0, "code"),
            ("translate Hello to French", 1, "translate"),
            ("json schema payload", 0, "json")
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sample_benchmark_loading(self):
        """
        Tests that sample_benchmark.csv loads correctly and contains 10 rows.
        """
        dataset = load_csv_dataset(self.benchmark_csv)
        self.assertEqual(len(dataset), 150)
        for prompt, label, domain in dataset:
            self.assertIsInstance(prompt, str)
            self.assertIn(label, [0, 1])
            self.assertIsInstance(domain, str)

    def test_metrics_confusion_matrix_and_ratios(self):
        """
        Verifies compute_evaluation_metrics correctly computes accuracies,
        ECE, Brier, cheap/dense selection rates, and false decisions.
        """
        # 4 queries: 
        # Query 1: route = cheap, escalated = False, prob = 0.9, label = 1, latency = 10ms -> Success cheap
        # Query 2: route = cascade, escalated = True, prob = 0.4, label = 0, latency = 120ms -> Escalated to dense (succeeds via dense (alpha=0.8))
        # Query 3: route = dense, escalated = False, prob = 0.2, label = 1, latency = 100ms -> Success dense (alpha=0.8)
        # Query 4: route = cheap, escalated = False, prob = 0.95, label = 0, latency = 8ms -> Failed cheap (label=0)
        
        results = [
            {"selected_route": "cheap", "escalated": False, "calibrated_probability": 0.9, "latency_ms": 10.0},
            {"selected_route": "cascade", "escalated": True, "calibrated_probability": 0.4, "latency_ms": 120.0},
            {"selected_route": "dense", "escalated": False, "calibrated_probability": 0.2, "latency_ms": 100.0},
            {"selected_route": "cheap", "escalated": False, "calibrated_probability": 0.95, "latency_ms": 8.0}
        ]
        
        labels = np.array([1, 0, 1, 0])
        c2 = 10.0
        c3 = 100.0
        alpha_dense = 0.8
        
        metrics = compute_evaluation_metrics(results, labels, c2, c3, alpha_dense)
        
        self.assertEqual(metrics["dataset_size"], 4)
        
        # Distribution: 2 cheap (50%), 1 cascade (25%), 1 dense (25%)
        self.assertEqual(metrics["routing_distribution_pct"]["cheap"], 50.0)
        self.assertEqual(metrics["routing_distribution_pct"]["cascade"], 25.0)
        self.assertEqual(metrics["routing_distribution_pct"]["dense"], 25.0)
        
        # Escalation rate: out of 3 non-direct-dense, 1 escalated -> 33.33%
        self.assertAlmostEqual(metrics["escalation_rate_pct"], 33.33333333)
        
        # Latencies: (10 + 120 + 100 + 8) / 4 = 238 / 4 = 59.5 ms
        self.assertEqual(metrics["average_latency_ms"], 59.5)
        
        # Cost check:
        # Q1: cheap -> c2 (10)
        # Q2: cascade + escalated -> c2 + c3 (110)
        # Q3: dense -> c3 (100)
        # Q4: cheap -> c2 (10)
        # Total cost: 230. Avg cost: 230 / 4 = 57.5. Avg norm cost: 57.5 / 100 = 0.575
        self.assertEqual(metrics["average_cost"], 57.5)
        self.assertEqual(metrics["average_normalized_cost"], 0.575)
        
        # Accuracy check:
        # Q1: cheap -> label = 1.0
        # Q2: cascade escalated -> alpha_dense = 0.8
        # Q3: dense -> alpha_dense = 0.8
        # Q4: cheap not escalated -> label = 0.0
        # Total acc: 1.0 + 0.8 + 0.8 + 0.0 = 2.6. Avg: 2.6 / 4 = 0.65
        self.assertEqual(metrics["accuracy"], 0.65)
        
        # Confusion stats check:
        # False Cheap: Router chose cheap/cascade, but cheap failed (label == 0)
        # Q2 (cascade, label=0) -> False cheap!
        # Q4 (cheap, label=0) -> False cheap!
        # Total False Cheap = 2.
        # False Dense: Router chose dense, but cheap would have succeeded (label == 1)
        # Q3 (dense, label=1) -> False dense!
        # Total False Dense = 1.
        self.assertEqual(metrics["false_decisions"]["false_cheap"], 2)
        self.assertEqual(metrics["false_decisions"]["false_dense"], 1)

    def test_baselines(self):
        """
        Verifies baseline performance computation functions.
        """
        c2 = 10.0
        c3 = 100.0
        alpha_dense = 0.9
        
        # Always Cheap: cost = c2 (10), accuracy = mean(labels) = 0.5
        cheap_res = run_always_cheap(self.samples, c2, c3)
        self.assertEqual(cheap_res["average_cost"], c2)
        self.assertEqual(cheap_res["accuracy"], 0.5)
        self.assertEqual(cheap_res["normalized_cost"], 0.1)
        
        # Always Dense: cost = c3 (100), accuracy = alpha_dense = 0.9
        dense_res = run_always_dense(self.samples, c3, alpha_dense)
        self.assertEqual(dense_res["average_cost"], c3)
        self.assertEqual(dense_res["accuracy"], 0.9)
        self.assertEqual(dense_res["normalized_cost"], 1.0)
        
        # Random routing test (deterministic with seed)
        random_res = run_random_routing(self.samples, c2, c3, alpha_dense, seed=42)
        self.assertTrue(c2 <= random_res["average_cost"] <= c3)
        self.assertTrue(0.0 <= random_res["accuracy"] <= 1.0)

    def test_evaluator_end_to_end_benchmarking(self):
        """
        Executes EvaluationRunner on the sample benchmark CSV and trained models,
        verifying that the MD and JSON reports are generated successfully.
        """
        runner = EvaluationRunner()
        results = runner.run_benchmark(
            dataset_path=self.benchmark_csv,
            models_dir=self.models_dir,
            c2=15.0,
            c3=150.0,
            lambda_coeff=0.55,
            alpha_dense=0.85,
            output_dir=self.temp_dir.name
        )
        
        # Verify result dict
        self.assertIn("tera", results)
        self.assertIn("baselines", results)
        
        # Verify files created
        json_report_path = os.path.join(self.temp_dir.name, "evaluation_report.json")
        md_report_path = os.path.join(self.temp_dir.name, "evaluation_report.md")
        
        self.assertTrue(os.path.exists(json_report_path))
        self.assertTrue(os.path.exists(md_report_path))
        
        # Verify JSON report content
        with open(json_report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["tera"]["dataset_size"], 150)
            self.assertIn("always_cheap", data["baselines"])
            self.assertIn("always_dense", data["baselines"])
            self.assertIn("random_routing", data["baselines"])
            self.assertIn("false_decisions", data["tera"])
            self.assertIn("routing_distribution_pct", data["tera"])

if __name__ == "__main__":
    unittest.main()
