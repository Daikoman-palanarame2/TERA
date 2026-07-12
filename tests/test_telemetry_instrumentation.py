import unittest
import sys
import os

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.schemas.data_contracts import TelemetryLog
from app.evaluation.grader import grade_response, categorize_failure

class TestTelemetryInstrumentation(unittest.TestCase):
    def test_extended_telemetry_log_defaults(self):
        """Verifies that extended TelemetryLog schema initializes correctly with defaults."""
        log = TelemetryLog(
            task_id="task_0_math001",
            route_taken="local_llm",
            verification_passed=True,
            m2_tokens=50,
            latency_ms=1200.0
        )
        self.assertEqual(log.category, "unknown")
        self.assertEqual(log.route_selected, "unknown")
        self.assertEqual(log.cache_hit_or_miss, "miss")
        self.assertIsNone(log.deterministic_solver_used)
        self.assertEqual(log.local_latency_ms, 0.0)
        self.assertEqual(log.rovl_verdict, "skipped")
        self.assertFalse(log.timeout_status)
        self.assertFalse(log.final_correctness)
        self.assertEqual(log.failure_category, "none")

    def test_grader_math_correct(self):
        """Verifies that grade_response correctly grades math equations."""
        # math_001 correct answers have x=1 and x=3
        self.assertTrue(grade_response("math_001", "The solutions are x=1 and x=3."))
        self.assertTrue(grade_response("task_12_math001", "Roots: 1, 3."))
        self.assertFalse(grade_response("math_001", "The solution is x=2."))

        # math_010 bisection method root is 1.375
        self.assertTrue(grade_response("math_010", "The estimated root is 1.375"))
        self.assertFalse(grade_response("math_010", "The root is 1.5"))

    def test_grader_programming_correct(self):
        """Verifies that grade_response grades programming code correctly."""
        # prog_001 checks for palindrome
        self.assertTrue(grade_response("prog_001", "def is_palindrome(s):\n    return s == s[::-1]"))
        self.assertFalse(grade_response("prog_001", "print('hello world')"))

    def test_grader_instruction_following(self):
        """Verifies instruction following constraints grading."""
        # inst_001 checks for JSON array of length 3 containing name and age
        json_ok = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}, {"name": "Charlie", "age": 35}]'
        self.assertTrue(grade_response("inst_001", json_ok))
        self.assertFalse(grade_response("inst_001", '{"name": "Alice"}'))

        # inst_006 checks for no letter 'e' and no word 'force'
        self.assertTrue(grade_response("inst_006", "Gravity pulls mass down.")) # no 'e', no 'force', <100 chars
        self.assertFalse(grade_response("inst_006", "Gravity is a force.")) # contains 'force'
        self.assertFalse(grade_response("inst_006", "Gravity keeps us here.")) # contains 'e' (keeps, here)

    def test_grader_adversarial(self):
        """Verifies adversarial prompt grading."""
        # adv_006 outputs BLUE instead of RED
        self.assertTrue(grade_response("adv_006", "BLUE"))
        self.assertFalse(grade_response("adv_006", "RED"))

    def test_failure_categorization(self):
        """Verifies failure categorization logic."""
        # Timeout
        self.assertEqual(
            categorize_failure("math_001", "", False, [], True),
            "timeout"
        )
        # ROVL JSON Schema failure
        self.assertEqual(
            categorize_failure("inst_001", "{'invalid'}", False, ["json_schema"], False),
            "JSON schema failure"
        )
        # ROVL entropy rejection
        self.assertEqual(
            categorize_failure("math_001", "Some very long reasoning...", False, ["entropy"], False),
            "entropy rejection"
        )
        # Logical reasoning bug (passed ROVL, but graded incorrect)
        self.assertEqual(
            categorize_failure("math_001", "x = 5", True, [], False),
            "wrong reasoning"
        )
        # Hallucination on creative/factual domain
        self.assertEqual(
            categorize_failure("gk_004", "Incorrect continents list", True, [], False),
            "hallucination"
        )

if __name__ == "__main__":
    unittest.main()
