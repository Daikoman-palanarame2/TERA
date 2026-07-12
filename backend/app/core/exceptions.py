"""
Module: backend/app/core/exceptions
Purpose:
    Defines the standardized custom exception hierarchy for TERA V3.
    All application exceptions derive from the base class TERABaseException.
"""

from typing import Optional

class TERABaseException(Exception):
    """Base class for all exceptions raised within the TERA V3 platform.

    Attributes:
        message (str): A descriptive error message explaining the failure.
        task_id (Optional[str]): The unique UUIDv4 transaction correlation ID associated with the failure.
    """

    def __init__(self, message: str, task_id: Optional[str] = None) -> None:
        """Initializes the base exception with a message and optional task ID.

        Args:
            message: The descriptive error message.
            task_id: The unique transaction identifier.
        """
        super().__init__(message)
        self.message: str = message
        self.task_id: Optional[str] = task_id


class ConfigurationError(TERABaseException):
    """Raised during system initialization when configurations are missing, malformed, or invalid."""
    pass


class InferenceTimeoutError(TERABaseException):
    """Raised when an LLM generation call breaches the SLA timeout or network request limits."""
    pass


class CacheError(TERABaseException):
    """Raised when the semantic or exact cache database encounters an availability or file corruption failure."""
    pass


class VerificationError(TERABaseException):
    """Raised when output auditor validation checks fail or parser engines crash on malformed outputs."""
    pass


class RoutingError(TERABaseException):
    """Raised when classifiers or estimators fail to load weights, evaluate features, or route queries."""
    pass
