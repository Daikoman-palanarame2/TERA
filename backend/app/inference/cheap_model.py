from typing import List, Optional, Dict
from app.inference.model_interface import ModelInterface
from app.inference.inference_types import ModelOutput

class CheapModel(ModelInterface):
    """
    Purpose:
        A mock implementation of ModelInterface representing the lightweight, cheap model.
        Supports configurable overrides based on substrings inside the prompt text 
        to test various verification outcomes (success, schema failure, entropy failure, etc.).
    """

    def __init__(
        self,
        default_text: str = "Cheap model response\n",
        default_probs: Optional[List[float]] = None,
        behavior_override: Optional[Dict[str, dict]] = None
    ) -> None:
        """
        Purpose:
            Initializes the mock cheap model with default completion text and behaviors.
            
        Inputs:
            default_text: Default completion string (should end with standard stop token by default).
            default_probs: List of floating-point probabilities (defaults to high-probability list).
            behavior_override: Dict mapping prompt substring flags to model output properties.
            
        Outputs:
            None
        """
        self.default_text = default_text
        self.default_probs = default_probs if default_probs is not None else [0.98, 0.99, 0.99]
        self.behavior_override = behavior_override or {}

    def generate(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Generates the mock model completion, checking for custom prompt keyword overrides.
            
        Inputs:
            prompt: Text prompt to complete.
            
        Outputs:
            ModelOutput dataclass.
            
        Time/Memory Complexity:
            O(1) lookup.
        """
        # Look for custom behaviors based on keyword matching inside the prompt
        for trigger, override in self.behavior_override.items():
            if trigger in prompt:
                text = override.get("text", self.default_text)
                probs = override.get("token_probs", self.default_probs)
                meta = override.get("metadata", {"model": "cheap_mock_override"})
                return ModelOutput(text=text, token_probs=probs, metadata=meta)
                
        return ModelOutput(
            text=self.default_text,
            token_probs=self.default_probs,
            metadata={"model": "cheap_mock_default"}
        )

    async def generate_async(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Asynchronous wrapper around synchronous mock completion generation.
        """
        return self.generate(prompt)
