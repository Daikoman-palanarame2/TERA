"""
Module: backend/app/solvers/solver_registry
Purpose:
    Manages registration, lookup, and execution of deterministic solvers,
    with duplicate registration prevention and post-initialization immutability.
"""

from app.solvers.base_solver import BaseSolver
from app.core.exceptions import RoutingError


class SolverRegistry:
    """Manages the registry of all available deterministic solvers."""

    def __init__(self) -> None:
        """Initialize empty solver maps and lock flag."""
        self._solvers: dict[str, BaseSolver] = {}
        self._locked: bool = False

    def lock(self) -> None:
        """Lock the registry to prevent further registrations."""
        self._locked = True

    def register_solver(self, solver: BaseSolver) -> None:
        """Register a solver class instance under its name.

        Args:
            solver: The BaseSolver instance to register.

        Raises:
            RoutingError: If registry is locked or name is already registered.
        """
        if self._locked:
            raise RoutingError(
                "Registry is locked and cannot accept new registrations."
            )

        name = solver.name
        if name in self._solvers:
            raise RoutingError(
                f"Duplicate solver registration attempt for name: {name}"
            )

        self._solvers[name] = solver

    def get_solver(self, name: str) -> BaseSolver:
        """Retrieve solver instance.

        Args:
            name: The name of the solver.

        Returns:
            The registered BaseSolver instance.

        Raises:
            RoutingError: If name is not registered.
        """
        # Automatically lock registry upon first query/lookup to ensure immutability
        self._locked = True

        if name not in self._solvers:
            raise RoutingError(f"Solver '{name}' not found in registry.")
        return self._solvers[name]

    def execute(self, solver_name: str, prompt: str) -> str:
        """Directly call solve() on target solver.

        Args:
            solver_name: The target solver name.
            prompt: The user query prompt.

        Returns:
            The solved result string.

        Raises:
            RoutingError: If the solver name is not registered.
            VerificationError: If parsing mathematical/logical AST fails.
        """
        solver = self.get_solver(solver_name)
        return solver.solve(prompt)
