"""
Module: backend/app/solvers/base_solver
Purpose:
    Defines the abstract base class and interface contract that all
    deterministic solver plugins must implement, along with solver metadata schema.
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class SolverMetadata(BaseModel):
    """Container for deterministic solver metadata properties.

    Attributes:
        name (str): Unique code name of the solver.
        category (str): Task classification category.
        description (str): Short explanation of what it solves.
    """

    name: str = Field(..., description="Unique code name of the solver.")
    category: str = Field(..., description="Task classification category.")
    description: str = Field(..., description="Short explanation of what it solves.")


class BaseSolver(ABC):
    """Abstract base class that all deterministic solver plugins must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique code name string of the solver."""
        pass

    @property
    @abstractmethod
    def pattern(self) -> str:
        """Return the pre-compiled regex trigger string."""
        pass

    @abstractmethod
    def solve(self, prompt: str) -> str:
        """Execute the deterministic calculation algorithm.

        Args:
            prompt: The raw user prompt query to process.

        Returns:
            The deterministic string output.

        Raises:
            VerificationError: If parsing mathematical/logical AST fails.
        """
        pass
