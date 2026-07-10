import unittest
import sys
import os

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.verification.verification_types import (
    VerificationStatus, 
    FailureReason, 
    SchemaType, 
    VerificationResult
)
from app.verification.rovl import ROVL

class TestROVL(unittest.TestCase):
    def setUp(self):
        # Initialize default ROVL with empty stop sequences to test other checkers independently
        self.rovl = ROVL(entropy_threshold=3.0, stop_sequences=[])

    def test_schema_valid_json(self):
        """
        Tests that valid JSON passes the SchemaType.JSON validation.
        """
        text = '{"status": "ok", "elements": [1, 2, 3]}'
        result = self.rovl.verify(text, schema_type=SchemaType.JSON)
        
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertTrue(result.schema_passed)
        self.assertEqual(result.failure_reasons, [])

    def test_schema_malformed_json(self):
        """
        Tests that malformed JSON fails the SchemaType.JSON validation.
        """
        text = '{"status": "ok", "elements": [1, 2, 3'
        result = self.rovl.verify(text, schema_type=SchemaType.JSON)
        
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertFalse(result.schema_passed)
        self.assertEqual(result.failure_reasons, [FailureReason.SCHEMA])

    def test_schema_regex_success_and_failure(self):
        """
        Tests SchemaType.REGEX validation with matching and non-matching patterns.
        """
        text = "Order total is $45.67."
        pattern = r"\$\d+\.\d{2}"
        
        # Matching pattern
        res_pass = self.rovl.verify(text, schema_type=SchemaType.REGEX, regex_pattern=pattern)
        self.assertEqual(res_pass.status, VerificationStatus.PASS)
        self.assertTrue(res_pass.schema_passed)
        
        # Non-matching pattern
        res_fail = self.rovl.verify(text, schema_type=SchemaType.REGEX, regex_pattern=r"€\d+")
        self.assertEqual(res_fail.status, VerificationStatus.FAIL)
        self.assertFalse(res_fail.schema_passed)
        self.assertEqual(res_fail.failure_reasons, [FailureReason.SCHEMA])

    def test_length_min_max_bounds(self):
        """
        Tests character length boundary checks.
        """
        text = "Hello world"  # length = 11
        
        # min_chars check fail
        res_min = self.rovl.verify(text, min_chars=15)
        self.assertEqual(res_min.status, VerificationStatus.FAIL)
        self.assertFalse(res_min.length_passed)
        self.assertEqual(res_min.failure_reasons, [FailureReason.LENGTH])
        
        # max_chars check fail
        res_max = self.rovl.verify(text, max_chars=5)
        self.assertEqual(res_max.status, VerificationStatus.FAIL)
        self.assertFalse(res_max.length_passed)
        self.assertEqual(res_max.failure_reasons, [FailureReason.LENGTH])
        
        # valid range check pass
        res_ok = self.rovl.verify(text, min_chars=5, max_chars=15)
        self.assertEqual(res_ok.status, VerificationStatus.PASS)
        self.assertTrue(res_ok.length_passed)

    def test_max_token_ceiling_hit(self):
        """
        Tests that ceiling hit indicators automatically flag length failure.
        """
        text = "Truncated text..."
        result = self.rovl.verify(text, max_token_ceiling_hit=True)
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertFalse(result.length_passed)
        self.assertEqual(result.failure_reasons, [FailureReason.LENGTH])

    def test_stop_tokens_conformity(self):
        """
        Tests check on valid trailing stop tokens.
        """
        # Instantiate test-specific rovl carrying stop token sequences
        rovl_with_stop = ROVL(entropy_threshold=3.0, stop_sequences=["\n", "}", "]", "<|im_end|>"])
        
        # Conforming output
        res_pass = rovl_with_stop.verify("Result: Success\n")
        self.assertEqual(res_pass.status, VerificationStatus.PASS)
        self.assertTrue(res_pass.stop_token_passed)
        
        # Abruptly cut-off output
        res_fail = rovl_with_stop.verify("Result: Abru")
        self.assertEqual(res_fail.status, VerificationStatus.FAIL)
        self.assertFalse(res_fail.stop_token_passed)
        self.assertEqual(res_fail.failure_reasons, [FailureReason.STOP_TOKEN])

    def test_entropy_computation_and_thresholds(self):
        """
        Tests token sequence entropy limits.
        """
        # Low entropy list: p = [0.95, 0.98, 0.99]
        low_probs = [0.95, 0.98, 0.99]
        res_low = self.rovl.verify("Hello", token_probs=low_probs)
        self.assertEqual(res_low.status, VerificationStatus.PASS)
        self.assertTrue(res_low.entropy_passed)
        self.assertLess(res_low.output_entropy, 3.0)
        
        # High entropy list: p = [0.1] * 50
        high_probs = [0.1] * 50
        res_high = self.rovl.verify("Hello", token_probs=high_probs)
        self.assertEqual(res_high.status, VerificationStatus.FAIL)
        self.assertFalse(res_high.entropy_passed)
        self.assertGreater(res_high.output_entropy, 3.0)
        self.assertEqual(res_high.failure_reasons, [FailureReason.ENTROPY])

    def test_degraded_observability_mode(self):
        """
        Tests that when probabilities are missing or empty, entropy checks are suspended.
        """
        # Missing probabilities
        result = self.rovl.verify("Hello")
        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertIsNone(result.output_entropy)
        self.assertIsNone(result.entropy_passed)
        
        # Empty probabilities list
        result_empty = self.rovl.verify("Hello", token_probs=[])
        self.assertEqual(result_empty.status, VerificationStatus.PASS)
        self.assertIsNone(result_empty.output_entropy)
        self.assertIsNone(result_empty.entropy_passed)

    def test_multiple_failures_aggregation(self):
        """
        Tests that if multiple checks fail, it reports FailureReason.MULTIPLE.
        """
        # Instantiate test-specific rovl carrying stop sequences
        rovl_with_stop = ROVL(entropy_threshold=3.0, stop_sequences=["\n"])
        
        # Failing both JSON schema and stop token check (text doesn't end in \n)
        text = '{"status": "ok", "elements": [1, 2, 3'
        result = rovl_with_stop.verify(text, schema_type=SchemaType.JSON)
        
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertFalse(result.schema_passed)
        self.assertFalse(result.stop_token_passed)
        self.assertEqual(result.failure_reasons, [FailureReason.MULTIPLE])

    def test_result_fields_observation(self):
        """
        Tests that VerificationResult holds all individual checker values.
        """
        # Instantiate test-specific rovl carrying stop sequences
        rovl_with_stop = ROVL(entropy_threshold=3.0, stop_sequences=["\n"])
        
        text = "Hello world"
        result = rovl_with_stop.verify(text, min_chars=20)
        
        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertEqual(result.schema_passed, True)
        self.assertEqual(result.length_passed, False)
        self.assertEqual(result.stop_token_passed, False)
        self.assertEqual(result.entropy_passed, None)
        self.assertEqual(result.failure_reasons, [FailureReason.MULTIPLE])

if __name__ == "__main__":
    unittest.main()
