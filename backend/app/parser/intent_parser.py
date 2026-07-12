"""
Module: backend/app/parser/intent_parser
Purpose:
    Exposes the IntentParser class to identify registered programmatic solver patterns.
"""

import re
from typing import Optional, Dict, Any
from app.core.exceptions import RoutingError
from app.solvers.base_solver import BaseSolver

class IntentParser:
    """Parses user prompts to detect deterministic solver match intents."""

    def __init__(self, registry: Any) -> None:
        """Bind to the SolverRegistry instance.

        Args:
            registry: The SolverRegistry instance to lookup solvers.
        """
        self._registry: Any = registry
        # Cache for compiled regex patterns
        self._compiled_patterns: Dict[str, re.Pattern[str]] = {}

    def parse_intent(self, prompt: str) -> Optional[str]:
        """Verify prompt against compiled regex definitions of registered solvers.

        Args:
            prompt: The raw user prompt text.

        Returns:
            The unique string name of the matched solver, or None if no match.

        Raises:
            RoutingError: If registry lookup fails.
        """
        try:
            # Check registry access. registry._solvers is a Dict[str, BaseSolver].
            solvers: dict[str, BaseSolver] = self._registry._solvers
        except AttributeError as e:
            raise RoutingError(f"Registry lookup failed: {e}", task_id=None)

        for name, solver in solvers.items():
            if name not in self._compiled_patterns:
                try:
                    # Compile regex pattern once and cache it
                    self._compiled_patterns[name] = re.compile(solver.pattern, re.IGNORECASE)
                except Exception as e:
                    raise RoutingError(
                        f"Failed to compile pattern '{solver.pattern}' for solver '{name}': {e}",
                        task_id=None
                    )

            pattern = self._compiled_patterns[name]
            if pattern.search(prompt):
                return name

        return None
