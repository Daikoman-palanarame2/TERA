"""
Unit and integration tests for TERA V2 Deterministic Solvers and Intent Parser.
"""

import sys
import os
import unittest
import re
import ast

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.exceptions import RoutingError, VerificationError
from app.solvers.base_solver import BaseSolver, SolverMetadata
from app.solvers.solver_registry import SolverRegistry
from app.parser.intent_parser import IntentParser
from app.solvers.plugins.arithmetic_solver import ArithmeticSolver
from app.solvers.plugins.logic_solver import LogicSolver
from app.solvers.plugins.text_counter_solver import TextCounterSolver

class DummySolver(BaseSolver):
    """Dummy solver for registry testing."""
    @property
    def name(self) -> str:
        return "dummy_solver"

    @property
    def pattern(self) -> str:
        return r"^dummy$"

    def solve(self, prompt: str) -> str:
        if prompt == "fail":
            raise VerificationError("Error", task_id=None)
        return "solved_dummy"

class TestBaseAndMetadata(unittest.TestCase):
    def test_metadata_instantiation(self):
        """Verify SolverMetadata validates attributes correctly."""
        meta = SolverMetadata(
            name="test_solver",
            category="math",
            description="Testing base solver metadata"
        )
        self.assertEqual(meta.name, "test_solver")
        self.assertEqual(meta.category, "math")
        self.assertEqual(meta.description, "Testing base solver metadata")

class TestSolverRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = SolverRegistry()
        self.solver = DummySolver()

    def test_register_and_get_solver(self):
        """Verify standard registration and retrieval."""
        self.registry.register_solver(self.solver)
        retrieved = self.registry.get_solver("dummy_solver")
        self.assertIs(retrieved, self.solver)

    def test_duplicate_registration_rejection(self):
        """Verify registry rejects duplicate solver names."""
        self.registry.register_solver(self.solver)
        with self.assertRaises(RoutingError) as context:
            self.registry.register_solver(self.solver)
        self.assertIn("Duplicate solver registration", str(context.exception))

    def test_lock_prevents_registration(self):
        """Verify register_solver raises RoutingError if registry is locked."""
        self.registry.lock()
        with self.assertRaises(RoutingError) as context:
            self.registry.register_solver(self.solver)
        self.assertIn("Registry is locked", str(context.exception))

    def test_lookup_locks_registry(self):
        """Verify get_solver locks the registry automatically."""
        self.registry.register_solver(self.solver)
        _ = self.registry.get_solver("dummy_solver")
        
        # Now try registering another solver; it should raise RoutingError
        another_solver = DummySolver()
        with self.assertRaises(RoutingError):
            self.registry.register_solver(another_solver)

    def test_get_solver_not_found(self):
        """Verify get_solver raises RoutingError if name is not found."""
        with self.assertRaises(RoutingError) as context:
            self.registry.get_solver("non_existent")
        self.assertIn("not found in registry", str(context.exception))

    def test_execute(self):
        """Verify execute calls solve() on target solver and raises errors appropriately."""
        self.registry.register_solver(self.solver)
        res = self.registry.execute("dummy_solver", "dummy")
        self.assertEqual(res, "solved_dummy")

        with self.assertRaises(VerificationError):
            self.registry.execute("dummy_solver", "fail")

class TestIntentParser(unittest.TestCase):
    def setUp(self):
        self.registry = SolverRegistry()
        self.solver = DummySolver()
        self.registry.register_solver(self.solver)
        self.parser = IntentParser(self.registry)

    def test_parse_intent_match(self):
        """Verify parser correctly matches registered solver patterns."""
        matched = self.parser.parse_intent("dummy")
        self.assertEqual(matched, "dummy_solver")

    def test_parse_intent_no_match(self):
        """Verify parser returns None for unmatched patterns."""
        matched = self.parser.parse_intent("not_matching")
        self.assertIsNone(matched)

    def test_registry_lookup_failure(self):
        """Verify parser raises RoutingError if registry attribute lookup fails."""
        bad_parser = IntentParser(None) # Passing invalid registry
        with self.assertRaises(RoutingError) as context:
            bad_parser.parse_intent("any")
        self.assertIn("Registry lookup failed", str(context.exception))

    def test_invalid_regex_compilation_raises_routing_error(self):
        """Verify parser handles invalid regex patterns inside solvers gracefully."""
        class BadPatternSolver(DummySolver):
            @property
            def name(self) -> str:
                return "bad_pattern"
            @property
            def pattern(self) -> str:
                return "[invalid regex pattern"
        
        self.registry.register_solver(BadPatternSolver())
        # Re-initialize to clear locks/parser cache
        fresh_parser = IntentParser(self.registry)
        with self.assertRaises(RoutingError) as context:
            # Triggering parsing will compile the bad pattern
            fresh_parser.parse_intent("any")
        self.assertIn("Failed to compile pattern", str(context.exception))

    def test_real_solver_patterns_are_conservative_and_do_not_collide(self):
        """Registration order must not let arithmetic steal other intents."""
        registry = SolverRegistry()
        registry.register_solver(ArithmeticSolver())
        registry.register_solver(LogicSolver())
        registry.register_solver(TextCounterSolver())
        parser = IntentParser(registry)

        self.assertEqual(parser.parse_intent("what is 2 + 2?"), "arithmetic_solver")
        self.assertEqual(
            parser.parse_intent("truth table for A and B"), "logic_solver"
        )
        self.assertEqual(
            parser.parse_intent("count words in: one two"), "text_counter_solver"
        )

    def test_real_solver_patterns_reject_adversarial_prose(self):
        """Mentions and factual prose must fall through to model routing."""
        registry = SolverRegistry()
        registry.register_solver(ArithmeticSolver())
        registry.register_solver(LogicSolver())
        registry.register_solver(TextCounterSolver())
        parser = IntentParser(registry)

        prompts = (
            "What is the capital of France?",
            "Please explain the truth table database design",
            "How do I count words efficiently?",
            "number of words in the English language",
            "truth table for A => B",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertIsNone(parser.parse_intent(prompt))

class TestArithmeticSolver(unittest.TestCase):
    def setUp(self):
        self.solver = ArithmeticSolver()

    def test_precedence_and_operations(self):
        """Verify precedence rules and standard binary/unary operators."""
        self.assertEqual(self.solver.solve("calculate 3 + 5 * 2"), "13")
        self.assertEqual(self.solver.solve("evaluate (3 + 5) * 2"), "16")
        self.assertEqual(self.solver.solve("what is -5 + +3"), "-2")
        self.assertEqual(self.solver.solve("compute 2**3"), "8")
        self.assertEqual(self.solver.solve("10 // 3"), "3")
        self.assertEqual(self.solver.solve("10 % 3"), "1")
        self.assertEqual(self.solver.solve(" 3.5 + 1.5 "), "5.0")

    def test_divide_by_zero(self):
        """Verify division by zero raises VerificationError."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("1 / 0")
        self.assertIn("Division by zero", str(context.exception))
        
        with self.assertRaises(VerificationError):
            self.solver.solve("5 // 0")
        with self.assertRaises(VerificationError):
            self.solver.solve("5 % 0")

    def test_invalid_syntax(self):
        """Verify syntactically invalid prompts raise VerificationError."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("calculate 3 + * 5")
        self.assertIn("Invalid arithmetic syntax", str(context.exception))

    def test_prompt_no_match(self):
        """Verify prompt solve fails if it doesn't match the pattern."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("Calculate letters in 'abc'")
        self.assertIn("does not match arithmetic pattern", str(context.exception))

    def test_malicious_ast_and_unsafe_nodes(self):
        """Verify exec, import, calls, attributes, subscripts, and lambda are blocked."""
        # Function call
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("abs(-5)")
        self.assertIn("does not match arithmetic pattern", str(context.exception))

        # Import/Attribute access
        with self.assertRaises(VerificationError):
            self.solver.solve("__import__('os').system('ls')")

        # Lambda/Variables
        with self.assertRaises(VerificationError):
            self.solver.solve("lambda x: x + 1")

        # Subscripts
        with self.assertRaises(VerificationError):
            self.solver.solve("[1, 2][0]")

    def test_large_exponent_denial_of_service(self):
        """Verify massive exponent powers are rejected to prevent CPU exhaustion."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("2 ** 99999")
        self.assertIn("Exponent too large", str(context.exception))

    def test_unsupported_operators_in_ast(self):
        """Verify unsupported binary/unary operators raise VerificationError."""
        # Unary bitwise invert (not supported by arithmetic)
        with self.assertRaises(VerificationError):
            self.solver.solve("~5")

        # Bitwise shift (not supported)
        with self.assertRaises(VerificationError):
            self.solver.solve("5 << 2")

    def test_non_numeric_constants_are_rejected(self):
        """Verify the AST evaluator accepts numbers only, never bools or strings."""
        for value in (True, "5", None):
            with self.subTest(value=value), self.assertRaises(VerificationError):
                self.solver._eval(ast.Constant(value=value))

class TestLogicSolver(unittest.TestCase):
    def setUp(self):
        self.solver = LogicSolver()

    def test_basic_operators_and_precedence(self):
        """Verify truth table generation for AND, OR, XOR, implies, iff, and negation."""
        # AND
        res_and = self.solver.solve("truth table A AND B")
        self.assertIn("| A | B | A AND B |", res_and)
        self.assertIn("| T | T | T |", res_and)
        self.assertIn("| T | F | F |", res_and)
        
        # OR
        res_or = self.solver.solve("generate truth table for p OR q")
        self.assertIn("| p | q | p OR q |", res_or)
        self.assertIn("| T | F | T |", res_or)

        # XOR
        res_xor = self.solver.solve("truth table A XOR B")
        self.assertIn("| T | T | F |", res_xor)
        self.assertIn("| T | F | T |", res_xor)

        # IMPLICATION
        res_impl = self.solver.solve("truth table A -> B")
        self.assertIn("| T | F | F |", res_impl)
        self.assertIn("| F | T | T |", res_impl)

        # IFF
        res_iff = self.solver.solve("truth table A <-> B")
        self.assertIn("| T | T | T |", res_iff)
        self.assertIn("| T | F | F |", res_iff)
        self.assertIn("| F | F | T |", res_iff)

    def test_complex_formulas_and_constants(self):
        """Verify complex propositional logic structures and constant values evaluate correctly."""
        res = self.solver.solve("truth table (A and B) or not C")
        self.assertIn("| A | B | C | (A and B) or not C |", res)
        
        # A=T, B=T, C=T -> T
        self.assertIn("| T | T | T | T |", res)
        # A=F, B=F, C=T -> F
        self.assertIn("| F | F | T | F |", res)
        # A=F, B=F, C=F -> T
        self.assertIn("| F | F | F | T |", res)

    def test_empty_logic_expression(self):
        """Verify empty logic expression raises VerificationError."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("truth table ")
        self.assertIn("Empty logic expression", str(context.exception))

    def test_logic_syntax_error(self):
        """Verify syntactically invalid logic expressions raise VerificationError."""
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("truth table A AND OR B")
        self.assertIn("Logic syntax error", str(context.exception))

    def test_unbound_identifier_in_ast_eval(self):
        """Verify Name nodes other than True/False/Env variables raise VerificationError."""
        # Unbound variables are resolved via env. If somehow ast.Name gets evaluated and is not in env or True/False,
        # it should raise VerificationError.
        with self.assertRaises(VerificationError) as context:
            self.solver._eval_boolean_node(ast.Name(id="NoneName", ctx=ast.Load()))
        self.assertIn("Unbound logic identifier", str(context.exception))

    def test_non_boolean_constants_are_rejected(self):
        """Verify truth-table evaluation cannot coerce arbitrary constants."""
        for value in (1, 0, "false", None):
            with self.subTest(value=value), self.assertRaises(VerificationError):
                self.solver._eval_boolean_node(ast.Constant(value=value))

    def test_unsupported_operators_in_logic_ast(self):
        """Verify unsupported operations in logic expressions raise VerificationError."""
        # Boolean operator and/or are supported, but addition in logic is not.
        with self.assertRaises(VerificationError):
            self.solver.solve("truth table A + B")

        # Unary negative of logic is unsupported (must use NOT)
        with self.assertRaises(VerificationError):
            self.solver.solve("truth table -A")

        # Multiple comparators (e.g. A == B == C) are unsupported
        with self.assertRaises(VerificationError):
            self.solver.solve("truth table A == B == C")

class TestTextCounterSolver(unittest.TestCase):
    def setUp(self):
        self.solver = TextCounterSolver()

    def test_words_count(self):
        """Verify words counting logic."""
        self.assertEqual(self.solver.solve("Count words in 'Hello World'"), "2")
        self.assertEqual(self.solver.solve("count words in: Hello   large   world  "), "3")
        self.assertEqual(self.solver.solve("number of words in '   '"), "0")

    def test_characters_count(self):
        """Verify characters counting logic."""
        self.assertEqual(self.solver.solve("Count characters in 'Hello World'"), "11")
        self.assertEqual(self.solver.solve("count chars in 'abc'"), "3")
        self.assertEqual(self.solver.solve("number of characters of: '你好'"), "2")

    def test_lines_count(self):
        """Verify lines counting logic."""
        self.assertEqual(self.solver.solve("Count lines in 'Hello\nWorld'"), "2")
        self.assertEqual(self.solver.solve("count lines in 'Line1\r\nLine2\rLine3'"), "3")
        self.assertEqual(self.solver.solve("number of lines in: "), "0")

    def test_occurrences_count(self):
        """Verify substring occurrence counting logic."""
        self.assertEqual(self.solver.solve("Count occurrences of 'l' in 'Hello World'"), "3")
        self.assertEqual(self.solver.solve("count occurrences of 'apple' in: 'an apple and another apple'"), "2")
        self.assertEqual(self.solver.solve("Count 'a' in 'banana'"), "3")

    def test_unsupported_category_or_parse_failure(self):
        """Verify unsupported counting fields or malformed prompts raise VerificationError."""
        # Unmatched prompt pattern
        with self.assertRaises(VerificationError) as context:
            self.solver.solve("Count average characters in 'abc'")
        self.assertIn("does not match text counter pattern", str(context.exception))

        # occurrences parsing failure (missing target or text)
        with self.assertRaises(VerificationError):
            self.solver.solve("Count occurrences of in 'abc'")

        # missing target text completely
        with self.assertRaises(VerificationError):
            self.solver.solve("Count words in")

if __name__ == "__main__":
    unittest.main()
