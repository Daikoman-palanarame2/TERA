"""
Module: backend/app/solvers/plugins/logic_solver
Purpose:
    Processes and evaluates boolean propositional logic expressions and 
    generates deterministic Markdown truth tables.
"""

import ast
import itertools
import re
from typing import Dict
from app.solvers.base_solver import BaseSolver
from app.core.exceptions import VerificationError

class LogicSolver(BaseSolver):
    """Solver for evaluating propositional logic formulas and generating truth tables."""

    @property
    def name(self) -> str:
        """Return the unique code name string of the solver."""
        return "logic_solver"

    @property
    def pattern(self) -> str:
        """Return the pre-compiled regex trigger string."""
        # Anchor the command and require either a single proposition or an
        # expression containing an actual supported logical operator.  This
        # avoids routing prose which merely mentions "truth table".
        return (
            r"^\s*(?:(?:generate|create|show|make)\s+)?(?:a\s+)?"
            r"truth\s+table(?:\s+for)?\s+"
            r"(?:[a-zA-Z_]\w*|"
            r"(?=[^\r\n]*(?:\b(?:and|or|not|xor|implies|iff)\b|<->|->|[&|~!]))"
            r"[a-zA-Z0-9_\s<>=&|~!()^]+)\s*$"
        )

    def solve(self, prompt: str) -> str:
        """Execute the deterministic logical evaluation algorithm.

        Args:
            prompt: The raw user prompt containing the logic expression.

        Returns:
            A deterministic Markdown representation of the truth table.

        Raises:
            VerificationError: If parsing the logic expression or AST fails.
        """
        # Parse the logic expression from prompt
        # We look for everything after "truth table for" or "truth table"
        expr_match = re.search(r"(?i)\btruth\s+table\s+(?:for\s+)?(.+)", prompt)
        if expr_match:
            expression = expr_match.group(1).strip()
        else:
            expression = re.sub(r"(?i)\btruth\s+table\s+(?:for\s+)?", "", prompt).strip()

        if not expression:
            raise VerificationError("Empty logic expression in prompt.", task_id=None)

        # Extract variables from expression
        # Variables are words that are not operators/keywords
        all_words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", expression)
        keywords = {
            "and", "or", "not", "xor", "implies", "iff", "true", "false", 
            "impl", "equivalence", "t", "f"
        }
        variables = sorted(list({word for word in all_words if word.lower() not in keywords}))

        # Generate combinations in descending binary order (True, then False)
        combinations = list(itertools.product([True, False], repeat=len(variables)))

        # Format header
        headers = variables + [expression]
        header_row = "| " + " | ".join(headers) + " |"
        sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows = [header_row, sep_row]

        for combo in combinations:
            env = dict(zip(variables, combo))
            try:
                res = self._eval_expression(expression, env)
            except Exception as e:
                raise VerificationError(f"Logic evaluation failed: {e}", task_id=None)

            res_str = "T" if res else "F"
            vals_str = ["T" if env[v] else "F" for v in variables]
            row_str = "| " + " | ".join(vals_str + [res_str]) + " |"
            rows.append(row_str)

        return "\n".join(rows)

    def _eval_expression(self, expression: str, env: Dict[str, bool]) -> bool:
        """Helper to transform and safely evaluate logical expressions using AST.

        Args:
            expression: The raw logic expression string.
            env: Variable assignment mapping.

        Returns:
            The boolean evaluation result.

        Raises:
            VerificationError: If parsing fails or unsafe nodes are found.
        """
        # Transform logic operators to Python equivalents
        expr = expression

        # Replace case-insensitive operator words
        expr = re.sub(r"\bimplies\b", "<=", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\biff\b", "==", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bxor\b", "^", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\band\b", " and ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bor\b", " or ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bnot\b", " not ", expr, flags=re.IGNORECASE)

        # Replace standard symbol operators
        expr = expr.replace("<->", "==")
        expr = expr.replace("->", "<=")
        expr = expr.replace("&", " and ")
        expr = expr.replace("|", " or ")
        expr = expr.replace("~", " not ")
        expr = expr.replace("!", " not ")

        # Replace variables with True/False literal strings
        for var, val in env.items():
            expr = re.sub(rf"\b{var}\b", str(val), expr)

        # Normalize spaces
        expr = expr.strip()

        try:
            node = ast.parse(expr, mode="eval")
        except SyntaxError as e:
            raise VerificationError(f"Logic syntax error: {e}", task_id=None)

        return self._eval_boolean_node(node.body)

    def _eval_boolean_node(self, node: ast.AST) -> bool:
        """Safely evaluates a boolean logic AST node.

        Args:
            node: The AST node to evaluate.

        Returns:
            The boolean result.

        Raises:
            VerificationError: If an unsafe AST node or operator is found.
        """
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, bool):
                raise VerificationError(
                    "Logic constants must be boolean.", task_id=None
                )
            return node.value
        elif isinstance(node, ast.Name):
            if node.id == "True":
                return True
            elif node.id == "False":
                return False
            raise VerificationError(f"Unbound logic identifier: {node.id}", task_id=None)

        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval_boolean_node(node.operand)
            raise VerificationError(f"Unsupported logic unary operator: {type(node.op)}", task_id=None)

        elif isinstance(node, ast.BoolOp):
            values = [self._eval_boolean_node(val) for val in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
            raise VerificationError(f"Unsupported logic boolean operator: {type(node.op)}", task_id=None)

        elif isinstance(node, ast.BinOp):
            left = self._eval_boolean_node(node.left)
            right = self._eval_boolean_node(node.right)
            if isinstance(node.op, ast.BitXor):
                return left ^ right
            raise VerificationError(f"Unsupported logic binary operator: {type(node.op)}", task_id=None)

        elif isinstance(node, ast.Compare):
            left = self._eval_boolean_node(node.left)
            # Implication is mapped to <= and Equivalence is mapped to ==
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.LtE)):
                right = self._eval_boolean_node(node.comparators[0])
                if isinstance(node.ops[0], ast.Eq):
                    return left == right
                elif isinstance(node.ops[0], ast.LtE):
                    return left <= right
            raise VerificationError("Unsupported logic comparison structure.", task_id=None)

        else:
            raise VerificationError(f"Unsafe node type detected in logic expression: {type(node)}", task_id=None)
