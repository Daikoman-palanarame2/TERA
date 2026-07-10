from typing import List, Optional
from app.inference.model_interface import ModelInterface
from app.inference.inference_types import ModelOutput

class DenseModel(ModelInterface):
    """
    Purpose:
        A mock implementation of ModelInterface representing the heavy, dense model.
        Returns conforming, successful completions deterministically.
    """

    def __init__(
        self,
        default_text: str = "Dense model successful response\n",
        default_probs: Optional[List[float]] = None
    ) -> None:
        """
        Purpose:
            Initializes the mock dense model.
            
        Inputs:
            default_text: Successful completion text (default ends in newline).
            default_probs: List of floating-point probabilities (defaults to high-probability list).
            
        Outputs:
            None
        """
        self.default_text = default_text
        self.default_probs = default_probs if default_probs is not None else [0.99, 0.99, 0.99]

    def generate(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Generates the mock dense model output.
            
        Inputs:
            prompt: Text prompt to complete.
            
        Outputs:
            ModelOutput dataclass.
            
        Time/Memory Complexity:
            O(1).
        """
        return ModelOutput(
            text=self.default_text,
            token_probs=self.default_probs,
            metadata={"model": "dense_mock_default"}
        )

    async def generate_async(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Asynchronous wrapper around synchronous mock completion generation.
        """
        return self.generate(prompt)
