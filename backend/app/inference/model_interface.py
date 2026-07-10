from abc import ABC, abstractmethod
from app.inference.inference_types import ModelOutput

"""
This module defines the abstract interface for language model providers.
Any downstream LLM adapter (Gemini, OpenAI, Llama, etc.) must implement this class.
"""

class ModelInterface(ABC):
    """
    Purpose:
        Abstract base class representing a provider-agnostic language model gateway.
    """

    @abstractmethod
    def generate(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Triggers completion generation for the given prompt.
            
        Inputs:
            prompt: Text prompt to generate completion for.
            
        Outputs:
            A ModelOutput dataclass carrying completion text, token probabilities, and metadata.
        """
        pass

    async def generate_async(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Triggers asynchronous completion generation for the given prompt.
            Default implementation is a wrapper around synchronous generate().
            Can be overridden by subclasses for native async implementation.
            
        Inputs:
            prompt: Text prompt to generate completion for.
            
        Outputs:
            A ModelOutput dataclass carrying completion text, token probabilities, and metadata.
        """
        return self.generate(prompt)
