import unittest
import os
import sys
from unittest.mock import patch

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.settings import Settings, get_model_capability_key
Settings.model_config["env_file"] = None

class TestModelDiscovery(unittest.TestCase):

    def test_get_model_capability_key_heuristics(self):
        """
        Validates tiering classifications for cheap, medium, and dense models.
        """
        # Cheap tier (<= 10B or cheap keywords)
        self.assertEqual(get_model_capability_key("llama3-8b")[0], 0)
        self.assertEqual(get_model_capability_key("phi3-mini")[0], 0)
        
        # Medium tier (<= 45B or mixtral-8x7b or medium keywords)
        self.assertEqual(get_model_capability_key("llama3-13b")[0], 1)
        self.assertEqual(get_model_capability_key("mixtral-8x7b")[0], 1)
        self.assertEqual(get_model_capability_key("qwen-pro")[0], 1)
        
        # Dense tier (> 45B or mixtral-8x22b or dense keywords)
        self.assertEqual(get_model_capability_key("llama3-70b")[0], 2)
        self.assertEqual(get_model_capability_key("mixtral-8x22b")[0], 2)
        self.assertEqual(get_model_capability_key("dbrx-instruct")[0], 2)

    @patch.dict(os.environ, {})
    def test_fallback_defaults(self):
        """
        Verifies that in the absence of ALLOWED_MODELS and overrides, it falls back to defaults.
        """
        # Clear any settings cache by instantiating a clean class
        settings = Settings()
        cheap, dense, method = settings.get_resolved_models()
        
        self.assertEqual(cheap, "accounts/fireworks/models/deepseek-v4-pro")
        self.assertEqual(dense, "accounts/fireworks/models/gpt-oss-120b")
        self.assertEqual(method, "Fallback Defaults")

    @patch.dict(os.environ, {
        "ALLOWED_MODELS": "accounts/fireworks/models/llama-v3-8b-instruct, accounts/fireworks/models/llama-v3-70b-instruct"
    })
    def test_automatic_discovery(self):
        """
        Verifies that the router automatically chooses the lowest tier model as cheap,
        and the highest tier model as dense from ALLOWED_MODELS.
        """
        settings = Settings(
            allowed_models_str="accounts/fireworks/models/llama-v3-8b-instruct, accounts/fireworks/models/llama-v3-70b-instruct"
        )
        cheap, dense, method = settings.get_resolved_models()
        
        self.assertEqual(cheap, "accounts/fireworks/models/llama-v3-8b-instruct")
        self.assertEqual(dense, "accounts/fireworks/models/llama-v3-70b-instruct")
        self.assertEqual(method, "Automatic Discovery")

    @patch.dict(os.environ, {
        "ALLOWED_MODELS": "accounts/fireworks/models/llama-v3-8b-instruct, accounts/fireworks/models/llama-v3-70b-instruct",
        "SMALL_MODEL": "custom-cheap-override"
    })
    def test_manual_override_precedence(self):
        """
        Verifies that explicit SMALL_MODEL or LARGE_MODEL overrides take absolute priority
        over automatic discovery.
        """
        settings = Settings(
            cheap_model_default="custom-cheap-override",
            allowed_models_str="accounts/fireworks/models/llama-v3-8b-instruct, accounts/fireworks/models/llama-v3-70b-instruct"
        )
        cheap, dense, method = settings.get_resolved_models()
        
        self.assertEqual(cheap, "custom-cheap-override")
        # Uses the default dense since only SMALL_MODEL was overridden in this test config
        self.assertEqual(dense, "accounts/fireworks/models/gpt-oss-120b")
        self.assertEqual(method, "Manual Override")

    @patch.dict(os.environ, {"ALLOWED_MODELS": ""})
    def test_empty_allowed_models_raises_exception(self):
        """
        Verifies that an empty ALLOWED_MODELS env value throws a configuration exception.
        """
        settings = Settings(allowed_models_str="")
        with self.assertRaises(ValueError) as context:
            _ = settings.allowed_models
        self.assertIn("ALLOWED_MODELS is defined but empty or invalid", str(context.exception))

    @patch.dict(os.environ, {"ALLOWED_MODELS": "  ,  ,  "})
    def test_malformed_allowed_models_raises_exception(self):
        """
        Verifies that a malformed ALLOWED_MODELS env value containing only commas/spaces
        throws a configuration exception.
        """
        settings = Settings(allowed_models_str="  ,  ,  ")
        with self.assertRaises(ValueError) as context:
            _ = settings.allowed_models
        self.assertIn("ALLOWED_MODELS is defined but empty or invalid", str(context.exception))

    def test_unknown_model_names_warning_and_tiering(self):
        """
        Verifies that unknown model names don't crash, warning is printed to stderr,
        and they are classified as 'medium' tier (tier priority = 1).
        """
        stderr_capture = []
        
        # Intercept print to sys.stderr
        original_stderr = sys.stderr
        class StderrMock:
            def write(self, s):
                stderr_capture.append(s)
            def flush(self):
                pass
                
        sys.stderr = StderrMock()
        try:
            tier, size = get_model_capability_key("mysterious-unknown-model")
        finally:
            sys.stderr = original_stderr
            
        self.assertEqual(tier, 1)  # Classifies as medium
        self.assertEqual(size, 13.0)  # Default size
        # Check warning log was written
        warning_msg = "".join(stderr_capture)
        self.assertIn("Warning: Unknown model name 'mysterious-unknown-model'", warning_msg)

    @patch.dict(os.environ, {
        "ALLOWED_MODELS": "accounts/fireworks/models/llama-v3-8b-instruct"
    })
    def test_single_allowed_model(self):
        """
        If only one model exists, cheap_model should be equal to dense_model.
        """
        settings = Settings(allowed_models_str="accounts/fireworks/models/llama-v3-8b-instruct")
        cheap, dense, method = settings.get_resolved_models()
        
        self.assertEqual(cheap, "accounts/fireworks/models/llama-v3-8b-instruct")
        self.assertEqual(dense, "accounts/fireworks/models/llama-v3-8b-instruct")
        self.assertEqual(method, "Automatic Discovery")

    @patch.dict(os.environ, {
        "ALLOWED_MODELS": "llama3-8b, phi3-mini, tiny-llama-1b"
    })
    def test_only_cheap_models(self):
        """
        If only cheap models exist, cheap_model is the lowest capability model
        and dense_model is the highest capability model within the cheap tier.
        """
        settings = Settings(allowed_models_str="llama3-8b, phi3-mini, tiny-llama-1b")
        cheap, dense, _ = settings.get_resolved_models()
        
        # Sort order by size: tiny-llama-1b (0.001B) -> phi3-mini (3.0B keyword) -> llama3-8b (8.0B)
        self.assertEqual(cheap, "tiny-llama-1b")
        self.assertEqual(dense, "llama3-8b")

    @patch.dict(os.environ, {
        "ALLOWED_MODELS": "mixtral-8x22b, llama3-70b, deepseek-67b"
    })
    def test_only_dense_models(self):
        """
        If only dense models exist, cheap_model is the lowest capability dense model
        and dense_model is the highest capability dense model.
        """
        settings = Settings(allowed_models_str="mixtral-8x22b, llama3-70b, deepseek-67b")
        cheap, dense, _ = settings.get_resolved_models()
        
        # Sort order: deepseek-67b (67B) -> llama3-70b (70B) -> mixtral-8x22b (176.0B MoE)
        self.assertEqual(cheap, "deepseek-67b")
        self.assertEqual(dense, "mixtral-8x22b")

if __name__ == "__main__":
    unittest.main()
