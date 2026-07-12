"""
Module: backend/app/inference/model_interface
Purpose:
    Defines the frozen abstract interface for language model providers.
"""

from abc import ABC
from typing import Dict, Any, Optional
from app.schemas.data_contracts import RawModelOutput

class ModelInterface(ABC):
    """
    Purpose:
        Abstract base class representing a provider-agnostic language model gateway.
    """

    def generate(self, prompt: str) -> Any:
        """Synchronously dispatch prompt payload.
        
        Subclasses may implement this method for V1 compatibility.
        """
        raise NotImplementedError("Subclasses must implement generate")

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        """Asynchronously dispatch prompt payload and parse response token list.
        
        Raises:
            InferenceTimeoutError: If request latency exceeds SLA timeout.
        """
        raise NotImplementedError("Subclasses must implement generate_async")
