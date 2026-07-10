import unittest
import sys
import os
import tempfile
import json
import pickle
import numpy as np

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.training.dataset import load_csv_dataset, split_dataset
from app.training.metrics import compute_brier_score, compute_ece
from app.training.trainer import run_training_pipeline

class TestTrainingPipeline(unittest.TestCase):
    def setUp(self):
        # Create a temporary CSV dataset file for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.temp_dir.name, "test_dataset.csv")
        
        # 20 samples to fit 60/20/20 split constraints perfectly (12 train, 4 cal, 4 val)
        self.samples = [
            ("explain what a binary search tree is.", 0, "logic"),
            ("calculate: solve 1 + 2 = 3", 1, "math"),
            ("debug a memory leak error in Python.", 0, "code"),
            ("summarize this page in a short outline.", 1, "gen"),
            ("translate this sentence to German.", 1, "translate"),
            ("json output formatter script.", 0, "json"),
            ("compare React and Angular frameworks.", 0, "gen"),
            ("extract details from this text.", 1, "gen"),
            ("classify review text as positive.", 1, "logic"),
            ("calculate the average standard deviation.", 0, "math"),
            ("summarize the clean energy presentation.", 1, "gen"),
            ("debug uvicorn launch error.", 0, "code"),
            ("translate French language text.", 1, "translate"),
            ("json schema parser validation.", 1, "json"),
            ("explain Isotonic Regression curves.", 0, "logic"),
            ("compare AMD and Intel CPU cores.", 0, "logic"),
            ("extract all hyperlinks from site.", 1, "gen"),
            ("classify article as sport.", 1, "logic"),
            ("code a binary search algorithm.", 0, "code"),
            ("solve arithmetic division equation.", 1, "math")
        ]
        
        # Write to temporary CSV file
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("prompt,label,domain\n")
            for item in self.samples:
                if isinstance(item, tuple):
                    f.write(f'"{item[0]}",{item[1]},{item[2]}\n')
                else:
                    # Handle string formatting fallback in samples declaration
                    f.write(f'"{item}",1,gen\n')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_csv_dataset(self):
        """
        Tests loading prompts, labels, and domains from a CSV file.
        """
        dataset = load_csv_dataset(self.csv_path)
        self.assertEqual(len(dataset), len(self.samples))
        for prompt, label, domain in dataset:
            self.assertIsInstance(prompt, str)
            self.assertIn(label, [0, 1])
            self.assertIsInstance(domain, str)

    def test_split_dataset(self):
        """
        Tests that splitting is deterministic and yields 60/20/20 proportion splits.
        """
        dataset = load_csv_dataset(self.csv_path)
        train, cal, val = split_dataset(dataset, seed=42)
        
        # Split size for N=20: 12 train, 4 calibration, 4 validation
        self.assertEqual(len(train), 12)
        self.assertEqual(len(cal), 4)
        self.assertEqual(len(val), 4)
        
        # Check determinism: running again with same seed yields identical splits
        train2, cal2, val2 = split_dataset(dataset, seed=42)
        self.assertEqual(train, train2)
        self.assertEqual(cal, cal2)
        self.assertEqual(val, val2)
        
        # Running with different seed yields different splits
        train_diff, _, _ = split_dataset(dataset, seed=99)
        self.assertNotEqual(train, train_diff)

    def test_metrics(self):
        """
        Tests Expected Calibration Error and Brier Score calculators.
        """
        # Perfect predictions matching labels
        y_true = np.array([1, 0, 1, 0])
        y_prob_perfect = np.array([1.0, 0.0, 1.0, 0.0])
        
        brier_perfect = compute_brier_score(y_true, y_prob_perfect)
        ece_perfect = compute_ece(y_true, y_prob_perfect, n_bins=2)
        
        self.assertEqual(brier_perfect, 0.0)
        self.assertEqual(ece_perfect, 0.0)
        
        # Totally incorrect / miscalibrated predictions
        y_prob_bad = np.array([0.0, 1.0, 0.0, 1.0])
        brier_bad = compute_brier_score(y_true, y_prob_bad)
        self.assertEqual(brier_bad, 1.0)
        
        # Expected error on dummy array
        y_true_dummy = np.array([1, 1, 0, 0])
        y_prob_dummy = np.array([0.9, 0.9, 0.1, 0.1])
        # Brier score: ((1-0.9)^2 * 2 + (0-0.1)^2 * 2)/4 = (0.01 * 2 + 0.01 * 2)/4 = 0.01
        brier_dummy = compute_brier_score(y_true_dummy, y_prob_dummy)
        self.assertAlmostEqual(brier_dummy, 0.01)

    def test_training_pipeline_and_serialization(self):
        """
        Tests that run_training_pipeline fits models, saves the four artifacts,
        and that the reloaded artifacts compute calibrated probabilities correctly.
        """
        output_path = os.path.join(self.temp_dir.name, "models")
        metrics = run_training_pipeline(self.csv_path, output_path, seed=42)
        
        # Check metrics payload
        self.assertIn("accuracy", metrics)
        self.assertIn("ece", metrics)
        self.assertIn("brier_score", metrics)
        
        # Check files exist
        logistic_file = os.path.join(output_path, "logistic_model.pkl")
        isotonic_file = os.path.join(output_path, "isotonic_model.pkl")
        corpus_file = os.path.join(output_path, "bm25_corpus.txt")
        metadata_file = os.path.join(output_path, "training_metadata.json")
        
        self.assertTrue(os.path.exists(logistic_file))
        self.assertTrue(os.path.exists(isotonic_file))
        self.assertTrue(os.path.exists(corpus_file))
        self.assertTrue(os.path.exists(metadata_file))
        
        # Check metadata payload
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            self.assertEqual(metadata["schema_version"], "1.0.0")
            self.assertEqual(metadata["feature_version"], "1.0.0")
            self.assertEqual(metadata["dataset_size"], 20)
            self.assertEqual(metadata["random_seed"], 42)
            self.assertIn("scikit_learn_version", metadata)
            
        # Verify that models can be reloaded and yield predictions
        with open(logistic_file, "rb") as f:
            lr_reloaded = pickle.load(f)
        with open(isotonic_file, "rb") as f:
            iso_reloaded = pickle.load(f)
            
        # Test predictions from reloaded models using dummy FeatureVector array
        # Dummy feature vector with shape (1, 4)
        dummy_x = np.array([[20.0, 0.1, 1.0, 0.5]])
        
        raw_prob = lr_reloaded.predict_proba(dummy_x)[:, 1]
        cal_prob = iso_reloaded.predict(raw_prob)
        
        self.assertTrue(0.0 <= raw_prob[0] <= 1.0)
        self.assertTrue(0.0 <= cal_prob[0] <= 1.0)

if __name__ == "__main__":
    unittest.main()
