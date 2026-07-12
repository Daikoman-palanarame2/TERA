"""
Module: tests/test_rovl
Purpose:
    Exhaustive unit tests for TERA V2 ROVL verification subsystem (entropy, validators, rovl).
    Achieves 100% branch coverage across the subsystem modules.
"""

import unittest
import sys
import os
import math
import time
from unittest.mock import patch, MagicMock

# Add backend directory to path to allow imports from app
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
)

from app.schemas.data_contracts import (
    RawModelOutput,
    TokenLogprob,
    VerificationConstraints,
)
from app.core.exceptions import VerificationError, ConfigurationError
from app.verification.entropy import compute_sequence_entropy, compute_average_surprisal
from app.verification.validators import (
    validate_json_schema,
    validate_regex,
    validate_stop_sequences,
)
from app.verification.rovl import ROVL, log_structured


class TestEntropy(unittest.TestCase):
    """Unit tests for entropy.py calculations."""

    def test_empty_sequence(self):
        """Empty token list returns 0.0."""
        self.assertEqual(compute_sequence_entropy([]), 0.0)
        self.assertEqual(compute_average_surprisal([]), 0.0)

    def test_one_token_valid(self):
        """Single token calculates correctly."""
        # logprob = ln(0.5) ~ -0.693147
        tokens = [TokenLogprob(token="test", logprob=math.log(0.5))]
        # Entropy: -0.5 * ln(0.5) = 0.346573
        self.assertAlmostEqual(compute_sequence_entropy(tokens), 0.34657359, places=6)
        # Surprisal: -ln(0.5) = 0.693147
        self.assertAlmostEqual(compute_average_surprisal(tokens), 0.69314718, places=6)

    def test_many_tokens_valid(self):
        """Multiple tokens average correctly."""
        tokens = [
            TokenLogprob(token="a", logprob=math.log(0.8)),
            TokenLogprob(token="b", logprob=math.log(0.5)),
            TokenLogprob(token="c", logprob=math.log(0.2)),
        ]
        # Entropy individual:
        # a: -0.8 * ln(0.8) = 0.178514
        # b: -0.5 * ln(0.5) = 0.346573
        # c: -0.2 * ln(0.2) = 0.321887
        # Total: 0.846974 / 3 = 0.282324
        self.assertAlmostEqual(compute_sequence_entropy(tokens), 0.282324, places=5)
        # Surprisal individual:
        # a: -ln(0.8) = 0.223143
        # b: -ln(0.5) = 0.693147
        # c: -ln(0.2) = 1.609437
        # Total: 2.525727 / 3 = 0.841909
        self.assertAlmostEqual(compute_average_surprisal(tokens), 0.841909, places=5)

    def test_invalid_values_and_clamping(self):
        """Invalid, NaN, infinite, and out of bounds logprobs are handled gracefully."""
        tokens = [
            TokenLogprob(token="nan", logprob=float("nan")),
            TokenLogprob(token="inf", logprob=float("inf")),
            TokenLogprob(token="ninf", logprob=float("-inf")),
            TokenLogprob(token="positive", logprob=0.5),  # probability > 1.0, clamped
            TokenLogprob(
                token="zero_prob", logprob=-1000.0
            ),  # underflows math.exp to exactly 0.0
        ]
        # Valid count for entropy: 3 (ninf, positive, zero_prob)
        # "positive" -> clamped to 0.0 -> prob = 1.0 -> entropy contribution = 0.0
        # "zero_prob" -> math.exp(-1000.0) = 0.0 <= 0.0 -> contribution = 0.0
        # ninf -> lp = -inf, p = 0.0 <= 0.0 -> contrib = 0.0
        # total entropy = 0.0 / 3 = 0.0
        self.assertEqual(compute_sequence_entropy(tokens), 0.0)

        # For surprisal:
        # "nan" -> invalid, skipped
        # "inf" -> valid float, positive -> clamped to 0.0 surprisal
        # "ninf" -> -inf -> contribution clamped to 100.0
        # "positive" -> logprob 0.5 > 0.0 -> clamped to 0.0 surprisal
        # "zero_prob" -> logprob -1000.0 -> surprisal is 1000.0
        # Total surprisal: 0.0 (inf) + 100.0 (ninf) + 0.0 (positive) + 1000.0 (zero_prob) = 1100.0 / 4 = 275.0
        self.assertEqual(compute_average_surprisal(tokens), 275.0)

        # If all tokens are invalid:
        invalid_tokens = [TokenLogprob(token="nan", logprob=float("nan"))]
        self.assertEqual(compute_sequence_entropy(invalid_tokens), 0.0)
        self.assertEqual(compute_average_surprisal(invalid_tokens), 0.0)


class TestValidators(unittest.TestCase):
    """Unit tests for validators.py matching schema, regex and stop tokens."""

    def test_valid_json_schema(self):
        """JSON matches schema returns True."""
        text = '{"name": "Alice", "age": 30}'
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        self.assertTrue(validate_json_schema(text, schema))

    def test_malformed_json(self):
        """Malformed JSON input returns False."""
        self.assertFalse(validate_json_schema("Alice is 30", {}))
        self.assertFalse(validate_json_schema(None, {}))  # type: ignore

    def test_json_schema_mismatch(self):
        """Valid JSON not matching schema returns False."""
        text = '{"name": "Alice", "age": "thirty"}'
        schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        self.assertFalse(validate_json_schema(text, schema))

    def test_json_schema_error(self):
        """Invalid schema raises VerificationError."""
        text = '{"name": "Alice"}'
        schema = {"type": "invalid_type"}  # schema error
        with self.assertRaises(VerificationError):
            validate_json_schema(text, schema)

    def test_regex_pass_and_fail(self):
        """Regex matches return True, mismatches return False."""
        self.assertTrue(validate_regex("Order #12345", r"#\d+"))
        self.assertFalse(validate_regex("Order #abc", r"#\d+"))

    def test_regex_invalid_pattern(self):
        """Uncompilable regex raises VerificationError."""
        with self.assertRaises(VerificationError):
            validate_regex("text", "[invalid")

    def test_regex_timeout(self):
        """Catastrophic regex or hanging execution times out safely returning False."""
        # Mock re.compile to return a pattern that hangs during search
        mock_pattern = MagicMock()
        mock_pattern.search.side_effect = lambda t: time.sleep(3.0)

        with patch("re.compile", return_value=mock_pattern):
            self.assertFalse(validate_regex("test", "pattern"))

    def test_stop_sequences(self):
        """Stop sequence matches correctly."""
        # Empty sequences returns True
        self.assertTrue(validate_stop_sequences("Hello", []))

        # End matches
        self.assertTrue(validate_stop_sequences("Hello world.", ["."]))

        # Contain matches
        self.assertTrue(
            validate_stop_sequences("Hello <|im_end|> world", ["<|im_end|>"])
        )

        # Mismatch
        self.assertFalse(validate_stop_sequences("Hello world", ["."]))


class TestROVL(unittest.TestCase):
    """Unit tests for the ROVL orchestrator class."""

    def test_init_validation(self):
        """Constructor checks limits configurations."""
        with self.assertRaises(ConfigurationError):
            ROVL(entropy_threshold=-1.0)
        with self.assertRaises(ConfigurationError):
            ROVL(min_prob_floor=-0.1)
        with self.assertRaises(ConfigurationError):
            ROVL(min_prob_floor=1.5)

    def test_verify_input_validation(self):
        """verify checks that inputs are not None."""
        rovl = ROVL()
        with self.assertRaises(VerificationError):
            rovl.verify(None, VerificationConstraints())  # type: ignore
        with self.assertRaises(VerificationError):
            rovl.verify(
                RawModelOutput(text="ok", latency_ms=10.0, usage_tokens=5), None
            )  # type: ignore

    def test_complete_pass(self):
        """Completions passing all validations return passed=True."""
        rovl = ROVL(entropy_threshold=2.0, min_prob_floor=0.01)
        output = RawModelOutput(
            text='{"status": "ok"}',
            tokens=[
                TokenLogprob(token="{", logprob=-0.05),
                TokenLogprob(token="status", logprob=-0.1),
                TokenLogprob(token="}", logprob=-0.05),
            ],
            latency_ms=100.0,
            usage_tokens=3,
        )
        constraints = VerificationConstraints(
            json_schema={"type": "object"},
            regex_pattern=r"status",
            stop_sequences=["}"],
            min_length_chars=5,
            max_length_chars=50,
        )
        result = rovl.verify(output, constraints, task_id="task_1_abc")
        self.assertTrue(result.passed)
        self.assertEqual(result.failed_validators, [])
        self.assertLess(result.sequence_entropy, 2.0)

    def test_schema_failure(self):
        """Fails when JSON schema is violated."""
        rovl = ROVL()
        output = RawModelOutput(
            text='{"status": "ok"}', latency_ms=50.0, usage_tokens=2
        )
        constraints = VerificationConstraints(
            json_schema={"type": "array"}  # Schema expects array, got object
        )
        result = rovl.verify(output, constraints)
        self.assertFalse(result.passed)
        self.assertIn("json_schema", result.failed_validators)

    def test_regex_failure(self):
        """Fails when regex pattern is not found."""
        rovl = ROVL()
        output = RawModelOutput(text="Hello world", latency_ms=50.0, usage_tokens=2)
        constraints = VerificationConstraints(
            regex_pattern=r"\d+"  # Pattern requires numbers
        )
        result = rovl.verify(output, constraints)
        self.assertFalse(result.passed)
        self.assertIn("regex_pattern", result.failed_validators)

    def test_length_failures(self):
        """Fails when output is too short or too long."""
        rovl = ROVL()
        output = RawModelOutput(text="abc", latency_ms=50.0, usage_tokens=1)

        # Too short
        res_short = rovl.verify(output, VerificationConstraints(min_length_chars=10))
        self.assertFalse(res_short.passed)
        self.assertIn("min_length_chars", res_short.failed_validators)

        # Too long
        res_long = rovl.verify(output, VerificationConstraints(max_length_chars=2))
        self.assertFalse(res_long.passed)
        self.assertIn("max_length_chars", res_long.failed_validators)

    def test_entropy_and_surprisal_failures(self):
        """Fails when entropy, surprisal, or probability floors are breached."""
        # Low entropy threshold to force failure
        rovl = ROVL(entropy_threshold=0.01)
        output = RawModelOutput(
            text="uncertain completion",
            tokens=[
                TokenLogprob(token="a", logprob=-1.2),  # probability = 0.3
                TokenLogprob(token="b", logprob=-1.2),
            ],
            latency_ms=10.0,
            usage_tokens=2,
        )
        result = rovl.verify(output, VerificationConstraints())
        self.assertFalse(result.passed)
        self.assertIn("entropy", result.failed_validators)

        # Surprisal threshold breach (SURPRISAL_THRESHOLD is frozen to 1.5)
        rovl_surp = ROVL(entropy_threshold=10.0)
        output_surp = RawModelOutput(
            text="high surprisal",
            tokens=[
                TokenLogprob(token="x", logprob=-2.5),  # surprisal = 2.5 > 1.5
                TokenLogprob(token="y", logprob=-2.5),
            ],
            latency_ms=10.0,
            usage_tokens=2,
        )
        result_surp = rovl_surp.verify(output_surp, VerificationConstraints())
        self.assertFalse(result_surp.passed)
        self.assertIn("average_surprisal", result_surp.failed_validators)

        # Probability floor check breach (min_prob_floor defaults to 0.05, ln(0.05) ~ -3.0)
        rovl_floor = ROVL(entropy_threshold=10.0, min_prob_floor=0.1)
        output_floor = RawModelOutput(
            text="floor breach",
            tokens=[
                TokenLogprob(
                    token="z", logprob=1000.0
                ),  # triggers math.exp OverflowError -> p = 0.0 < 0.1 (put first for coverage)
                TokenLogprob(token="x", logprob=-0.01),  # prob ~ 0.99
                TokenLogprob(token="y", logprob=-3.0),  # prob ~ 0.05 < 0.1
            ],
            latency_ms=10.0,
            usage_tokens=3,
        )
        result_floor = rovl_floor.verify(output_floor, VerificationConstraints())
        self.assertFalse(result_floor.passed)
        self.assertIn("probability_floor", result_floor.failed_validators)

    def test_stop_sequence_failure(self):
        """Fails when stop sequence matches are missing."""
        rovl = ROVL()
        output = RawModelOutput(
            text="incomplete response", latency_ms=10.0, usage_tokens=2
        )
        constraints = VerificationConstraints(stop_sequences=["\n", "<|im_end|>"])
        result = rovl.verify(output, constraints)
        self.assertFalse(result.passed)
        self.assertIn("stop_sequences", result.failed_validators)

    def test_local_judge_pass_and_fail(self):
        """Triggers and maps Local Judge results when other checks pass."""
        # Judge passes
        rovl_pass = ROVL(local_judge=lambda text: True)
        output = RawModelOutput(text="good text", latency_ms=10.0, usage_tokens=2)
        res_pass = rovl_pass.verify(output, VerificationConstraints())
        self.assertTrue(res_pass.passed)

        # Judge fails
        rovl_fail = ROVL(local_judge=lambda text: False)
        res_fail = rovl_fail.verify(output, VerificationConstraints())
        self.assertFalse(res_fail.passed)
        self.assertIn("local_judge", res_fail.failed_validators)

    def test_multiple_simultaneous_failures(self):
        """Aggregates multiple failed validation layers correctly."""
        rovl = ROVL(entropy_threshold=0.01)
        output = RawModelOutput(
            text="failed completion",
            tokens=[TokenLogprob(token="x", logprob=-2.5)],
            latency_ms=10.0,
            usage_tokens=1,
        )
        constraints = VerificationConstraints(
            json_schema={"type": "object"}, stop_sequences=["\n"]
        )
        result = rovl.verify(output, constraints)
        self.assertFalse(result.passed)
        self.assertIn("json_schema", result.failed_validators)
        self.assertIn("entropy", result.failed_validators)
        self.assertIn("average_surprisal", result.failed_validators)
        self.assertIn("stop_sequences", result.failed_validators)

    def test_exceptions_wrapping_in_verify(self):
        """Verify catches unexpected exceptions and wraps them in VerificationError."""
        rovl = ROVL()
        output = RawModelOutput(text="data", latency_ms=10.0, usage_tokens=2)

        # 1. Schema exception (VerificationError directly)
        with patch(
            "app.verification.rovl.validate_json_schema",
            side_effect=VerificationError("Frozen schema error"),
        ):
            constraints = VerificationConstraints(json_schema={"type": "object"})
            with self.assertRaises(VerificationError):
                rovl.verify(output, constraints)

        # 2. Schema exception (Generic Exception wrapped)
        with patch(
            "app.verification.rovl.validate_json_schema",
            side_effect=RuntimeError("JSON crash"),
        ):
            constraints = VerificationConstraints(json_schema={"type": "object"})
            with self.assertRaises(VerificationError):
                rovl.verify(output, constraints)

        # 3. Regex exception (VerificationError directly)
        with patch(
            "app.verification.rovl.validate_regex",
            side_effect=VerificationError("Frozen regex error"),
        ):
            constraints = VerificationConstraints(regex_pattern=".*")
            with self.assertRaises(VerificationError):
                rovl.verify(output, constraints)

        # 4. Regex exception (Generic Exception wrapped)
        with patch(
            "app.verification.rovl.validate_regex",
            side_effect=RuntimeError("Regex crash"),
        ):
            constraints = VerificationConstraints(regex_pattern=".*")
            with self.assertRaises(VerificationError):
                rovl.verify(output, constraints)

        # 5. Stop sequence exception (Generic Exception wrapped)
        with patch(
            "app.verification.rovl.validate_stop_sequences",
            side_effect=RuntimeError("Stop crash"),
        ):
            constraints = VerificationConstraints(stop_sequences=["\n"])
            with self.assertRaises(VerificationError):
                rovl.verify(output, constraints)

        # 6. Local judge exception (Generic Exception wrapped)
        rovl_bad_judge = ROVL(
            local_judge=MagicMock(side_effect=RuntimeError("Judge crash"))
        )
        with self.assertRaises(VerificationError):
            rovl_bad_judge.verify(output, VerificationConstraints())

    def test_log_structured_helper(self):
        """log_structured formats output without throwing."""
        # Simple test to verify execution of log helper under debug, warning, error, info
        log_structured("INFO", "info log", "task_1")
        log_structured("WARNING", "warning log", "task_2")
        log_structured("ERROR", "error log", "task_3")
        log_structured("DEBUG", "debug log", "task_4")


if __name__ == "__main__":
    unittest.main()
