from typing import List, Optional, Dict, Any
from app.inference.model_interface import ModelInterface
from app.inference.inference_types import ModelOutput
from app.schemas.data_contracts import RawModelOutput

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

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        """
        Purpose:
            Asynchronous wrapper around synchronous mock completion generation.
        """
        import math
        from app.schemas.data_contracts import RawModelOutput, TokenLogprob
        res = self.generate(prompt)
        probs = res.token_probs if res.token_probs is not None else [0.99]
        tokens = [TokenLogprob(token="tok", logprob=math.log(max(p, 1e-9))) for p in probs]
        return RawModelOutput(
            text=res.text,
            tokens=tokens,
            latency_ms=20.0,
            usage_tokens=max(1, len(res.text) // 4)
        )
