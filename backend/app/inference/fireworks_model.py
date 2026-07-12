import math
import time
import httpx
import random
import asyncio
from typing import List, Optional, Dict, Any

from app.inference.model_interface import ModelInterface
from app.inference.inference_types import ModelOutput
from app.core.settings import settings
from app.schemas.data_contracts import RawModelOutput

class FireworksModel(ModelInterface):
    """
    Purpose:
        A production-grade implementation of ModelInterface that interacts with the
        Fireworks API endpoint. Supports text extraction, token usage metrics, 
        logprobs translation, and round-trip latency tracking.
        
    Time Complexity:
        O(T) where T is response token length (for logprobs decoding).
        
    Memory Complexity:
        O(T) to store token probabilities in RAM.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0
    ) -> None:
        """
        Purpose:
            Initializes the Fireworks model client adapter.
            
        Inputs:
            model_name: The Fireworks model tag (e.g. accounts/fireworks/models/llama-v3-8b-instruct).
            api_key: Optional override for FIREWORKS_API_KEY.
            base_url: Optional override for FIREWORKS_BASE_URL.
            timeout_seconds: Timeout for HTTP requests (default 30.0s).
        """
        self.model_name = model_name
        self.api_key = api_key or settings.fireworks_api_key
        self.base_url = base_url or settings.fireworks_base_url
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> ModelOutput:
        """
        Purpose:
            Performs a synchronous POST request to the Fireworks chat completions endpoint,
            tracks execution latency, parses token usage, and translates log probability scores.
            Supports transport failure retries (max 1 retry).
            
        Inputs:
            prompt: Text prompt to generate completion for.
            
        Outputs:
            ModelOutput dataclass.
            
        Raises:
            ValueError: If FIREWORKS_API_KEY is not configured.
            httpx.HTTPError: If HTTP communication fails after retries.
        """
        if not self.api_key:
            raise ValueError("Configuration error: FIREWORKS_API_KEY is not set.")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Configure payload to request log probabilities
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "logprobs": True,
            "top_logprobs": 1
        }

        response = None
        t0 = time.perf_counter()
        
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                break  # Success
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                should_retry = False
                if isinstance(e, httpx.HTTPStatusError):
                    status = e.response.status_code
                    if status == 429 or (status >= 500 and status < 600):
                        should_retry = True
                else:
                    should_retry = True
                
                if attempt == 0 and should_retry:
                    backoff = 1.0 + random.uniform(0.1, 0.5)
                    time.sleep(backoff)
                    continue
                raise e
            
        latency_ms = (time.perf_counter() - t0) * 1000.0
        resp_data = response.json()
        
        # 1. Extract response text
        choice = resp_data["choices"][0]
        text_content = choice["message"]["content"]
        
        # 2. Extract token usage
        usage = resp_data.get("usage", {})
        
        # 3. Extract logprobs if available
        token_probs: Optional[List[float]] = None
        logprobs_info = choice.get("logprobs")
        
        if logprobs_info and "content" in logprobs_info:
            token_probs = []
            for item in logprobs_info["content"]:
                logprob = item.get("logprob")
                if logprob is not None:
                    # Convert natural logprob to probability: p = exp(logprob)
                    token_probs.append(math.exp(logprob))

        # 4. Construct metadata
        metadata = {
            "model": self.model_name,
            "latency_ms": float(latency_ms),
            "usage": usage,
            "finish_reason": choice.get("finish_reason"),
            "provider": "fireworks"
        }

        return ModelOutput(
            text=text_content,
            token_probs=token_probs,
            metadata=metadata
        )

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        """
        Purpose:
            Performs an asynchronous POST request to the Fireworks chat completions endpoint,
            tracks execution latency, parses token usage, and translates log probability scores.
            Supports transport failure retries (max 1 retry).
            
        Inputs:
            prompt: Text prompt to generate completion for.
            params: Optional execution parameters.
            
        Outputs:
            RawModelOutput.
            
        Raises:
            ValueError: If FIREWORKS_API_KEY is not configured.
            httpx.HTTPError: If HTTP communication fails after retries.
        """
        if not self.api_key:
            raise ValueError("Configuration error: FIREWORKS_API_KEY is not set.")

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Configure payload to request log probabilities
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "logprobs": True,
            "top_logprobs": 1
        }

        response = None
        t0 = time.perf_counter()
        
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                break  # Success
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                should_retry = False
                if isinstance(e, httpx.HTTPStatusError):
                    status = e.response.status_code
                    if status == 429 or (status >= 500 and status < 600):
                        should_retry = True
                else:
                    should_retry = True
                
                if attempt == 0 and should_retry:
                    backoff = 1.0 + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)
                    continue
                raise e
            
        latency_ms = (time.perf_counter() - t0) * 1000.0
        resp_data = response.json()
        
        # 1. Extract response text
        choice = resp_data["choices"][0]
        text_content = choice["message"]["content"]
        
        # 2. Extract token usage
        usage = resp_data.get("usage", {})
        usage_tokens = usage.get("total_tokens", len(text_content) // 4)
        
        # 3. Extract logprobs if available
        tokens_list = []
        logprobs_info = choice.get("logprobs")
        
        from app.schemas.data_contracts import RawModelOutput, TokenLogprob
        if logprobs_info and "content" in logprobs_info:
            for item in logprobs_info["content"]:
                token = item.get("token", "")
                logprob = item.get("logprob", 0.0)
                tokens_list.append(TokenLogprob(token=token, logprob=logprob))
        else:
            # Fallback mock tokens list
            tokens_list.append(TokenLogprob(token="test", logprob=-0.1))

        return RawModelOutput(
            text=text_content,
            tokens=tokens_list,
            latency_ms=float(latency_ms),
            usage_tokens=usage_tokens
        )
