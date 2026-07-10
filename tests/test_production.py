import unittest
import sys
import os
import json
import tempfile
import subprocess
from unittest.mock import patch

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.settings import Settings
from app.inference.fireworks_model import FireworksModel
from app.inference.model_interface import ModelInterface

class TestProductionPhase1(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_settings_allowed_models_parsing(self):
        """
        Verifies that allowed models comma-separated string parses into list.
        """
        settings = Settings(
            cheap_model="llama-cheap",
            dense_model="llama-dense",
            allowed_models_str="llama-cheap, llama-dense, other-model"
        )
        
        self.assertEqual(settings.allowed_models, ["llama-cheap", "llama-dense", "other-model"])

    def test_settings_validate_production_keys(self):
        """
        Verifies settings.validate_production raises correct exceptions.
        """
        # Missing API Key
        settings_no_key = Settings(cheap_model_default="llama-cheap", dense_model_default="llama-dense")
        settings_no_key.fireworks_api_key = None
        
        with self.assertRaises(ValueError) as context:
            settings_no_key.validate_production()
        self.assertIn("FIREWORKS_API_KEY must be set", str(context.exception))
        
        # Model not in ALLOWED_MODELS
        with patch.dict(os.environ, {
            "SMALL_MODEL": "unallowed-cheap",
            "ALLOWED_MODELS": "llama-dense"
        }):
            settings_invalid_model = Settings(
                cheap_model_default="unallowed-cheap", 
                dense_model_default="llama-dense",
                allowed_models_str="llama-dense"
            )
            settings_invalid_model.fireworks_api_key = "dummy-key"
            
            with self.assertRaises(ValueError) as context:
                settings_invalid_model.validate_production()
            self.assertIn("is not in ALLOWED_MODELS", str(context.exception))

    @patch("app.inference.fireworks_model.settings.fireworks_api_key", None)
    def test_fireworks_model_interface_conformance(self):
        """
        Verifies FireworksModel implements ModelInterface and checks API key settings.
        """
        client = FireworksModel(model_name="test-model", api_key=None, base_url="https://api.example.com")
        self.assertIsInstance(client, ModelInterface)
        
        # Calling generate without API key should raise ValueError
        with self.assertRaises(ValueError):
            client.generate("hello")

    def test_batch_harness_mock_run(self):
        """
        Executes run_batch.py in mock mode using a temporary tasks JSON,
        verifying that results.json compiles outputs and exits 0.
        """
        tasks = [
            {
                "task_id": "test-1",
                "prompt": "explain what is photosynsthesis?",
                "schema_type": "none"
            },
            {
                "id": "test-2",
                "prompt": "generate order payload",
                "schema_type": "json",
                "min_chars": 5
            }
        ]
        
        input_file = os.path.join(self.temp_dir.name, "tasks.json")
        output_file = os.path.join(self.temp_dir.name, "results.json")
        
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f)
            
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/run_batch.py"))
        
        # Run run_batch.py via subprocess to test as an independent CLI entrypoint
        cmd = [
            sys.executable,
            script_path,
            "--input", input_file,
            "--output", output_file,
            "--mock"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Batch run failed with stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        
        # Verify output compiled correctly
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["task_id"], "test-1")
        self.assertEqual(data[1]["task_id"], "test-2")
        self.assertIn("answer", data[0])
        self.assertNotIn("selected_route", data[0])
        
        # Verify telemetry file compiled correctly
        telemetry_file = os.path.join(self.temp_dir.name, "telemetry.json")
        self.assertTrue(os.path.exists(telemetry_file))
        with open(telemetry_file, "r", encoding="utf-8") as f:
            tele_data = json.load(f)
        self.assertEqual(len(tele_data), 2)
        self.assertEqual(tele_data[0]["task_id"], "test-1")
        self.assertIn("selected_route", tele_data[0])

if __name__ == "__main__":
    unittest.main()
