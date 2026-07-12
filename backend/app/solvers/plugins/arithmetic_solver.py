"""
Module: backend/app/solvers/plugins/arithmetic_solver
Purpose:
    Implements a safe arithmetic solver using AST parsing and evaluation.
"""

import ast
import re
from typing import Any
from app.solvers.base_solver import BaseSolver
from app.core.exceptions import VerificationError

class ArithmeticSolver(BaseSolver):
    """Solver for evaluating simple infix arithmetic expressions safely via AST."""

    @property
    def name(self) -> str:
        """Return the unique code name string of the solver."""
        return "arithmetic_solver"

    @property
    def pattern(self) -> str:
        """Return the pre-compiled regex trigger string."""
        # Keep routing deliberately narrower than AST validation.  In particular,
        # arbitrary letters here caused this solver (registered first) to capture
        # almost every short English prompt before the intended solver saw it.
        # ``e``/``E`` remain available for numeric scientific notation.
        return (
            r"^\s*(?:calculate|evaluate|what\s+is|compute)?\s*"
            r"(?=[0-9eE\s\+\-\*\/\(\)\.%]+\d)"
            r"([0-9eE\s\+\-\*\/\(\)\.%]+)\s*\??\s*$"
        )

    def solve(self, prompt: str) -> str:
        """Execute the deterministic arithmetic calculation algorithm.

        Args:
            prompt: The raw user prompt query containing the arithmetic expression.

        Returns:
            The calculated value as a string.

        Raises:
            VerificationError: If parsing mathematical AST fails, division by zero
                               occurs, or unsafe nodes are detected.
        """
        match = re.match(self.pattern, prompt, re.IGNORECASE)
        if not match:
            raise VerificationError("Prompt does not match arithmetic pattern.", task_id=None)

        expression_str = match.group(1).strip()

        try:
            node = ast.parse(expression_str, mode="eval")
        except SyntaxError as e:
            raise VerificationError(f"Invalid arithmetic syntax: {e}", task_id=None)

        try:
            val = self._eval(node.body)
            # Standardize output string
            return str(val)
        except ZeroDivisionError:
            raise VerificationError("Division by zero in arithmetic solver.", task_id=None)
        except VerificationError as ve:
            raise ve
        except Exception as e:
            raise VerificationError(f"Arithmetic evaluation failed: {e}", task_id=None)

    def _eval(self, node: ast.AST) -> Any:
        """Recursively evaluate AST nodes safely.

        Args:
            node: The AST node to evaluate.

        Returns:
            The evaluated result value (int or float).

        Raises:
            VerificationError: If an unsafe AST node is encountered.
            ZeroDivisionError: If division by zero is attempted.
        """
        if isinstance(node, ast.Constant):
            # bool is an int subclass in Python, so reject it explicitly.
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise VerificationError(
                    "Arithmetic constants must be numeric.", task_id=None
                )
            return node.value

        elif isinstance(node, ast.BinOp):
            left = self._eval(node.left)
            right = self._eval(node.right)

            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError()
                return left / right
            elif isinstance(node.op, ast.Pow):
                # Bound exponent to prevent CPU denial of service exhaustion attacks
                if abs(right) > 1000:
                    raise VerificationError("Exponent too large to prevent CPU exhaustion.", task_id=None)
                return left ** right
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    raise ZeroDivisionError()
                return left // right
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    raise ZeroDivisionError()
                return left % right
            else:
                raise VerificationError(f"Unsupported binary operator: {type(node.op)}", task_id=None)

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
            else:
                raise VerificationError(f"Unsupported unary operator: {type(node.op)}", task_id=None)

        else:
            raise VerificationError(
                f"Unsafe node type detected in arithmetic expression: {type(node)}", 
                task_id=None
            )
