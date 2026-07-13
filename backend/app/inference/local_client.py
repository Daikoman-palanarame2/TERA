"""
Module: backend/app/inference/local_client
Purpose:
    Implements the LocalModelClient class for asynchronous execution against
    local vLLM, llama.cpp, or SGLang completions endpoints.
"""

import time
import httpx
import random
import asyncio
import logging
import json
import datetime
from typing import Dict, Any, Optional, List

from app.inference.model_interface import ModelInterface
from app.schemas.data_contracts import RawModelOutput, TokenLogprob
from app.core.exceptions import InferenceTimeoutError, ConfigurationError

# Get loggers
logger = logging.getLogger("app.inference.local_client")
logger_core = logging.getLogger("tera_core")

def _log_structured(
    log_level: str,
    module: str,
    message: str,
    task_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """Helper to write structured log records matching the TERA V2 Logging Contract."""
    log_dict = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "log_level": log_level,
        "module": module,
        "message": message,
        "task_id": task_id if task_id else None
    }
    if extra:
        log_dict.update(extra)
    logger_core.log(getattr(logging, log_level.upper()), json.dumps(log_dict))


class LocalModelClient(ModelInterface):
    """
    Purpose:
        Production-grade asynchronous client for local model serving (vLLM/llama.cpp/SGLang).
    """

    def __init__(self, endpoint_url: str, model_name: str, timeout_sec: float = 5.0) -> None:
        """Initialize the local HTTP client.
        
        Args:
            endpoint_url: Base URL of local server (e.g. http://localhost:8000/v1).
            model_name: Identifier of the local model.
            timeout_sec: Maximum latency in seconds.
            
        Raises:
            ConfigurationError: If configurations are invalid.
        """
        if not endpoint_url or not endpoint_url.strip():
            raise ConfigurationError("Endpoint URL must not be empty.")
        if not model_name or not model_name.strip():
            raise ConfigurationError("Model name must not be empty.")
        if timeout_sec <= 0.0:
            raise ConfigurationError("Timeout must be a positive float.")
            
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_sec = timeout_sec
        # Reuse a single client instance
        self.client = httpx.AsyncClient(timeout=self.timeout_sec)

    async def close(self) -> None:
        """Performs proper cleanup of the underlying HTTP connection pool."""
        await self.client.aclose()

    async def __aenter__(self) -> "LocalModelClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _parse_completion(self, resp_json: Dict[str, Any]) -> str:
        """Private helper to safely extract generation text."""
        try:
            choices = resp_json.get("choices")
            if not choices:
                return ""
            choice = choices[0]
            if "message" in choice:
                return str(choice["message"].get("content", ""))
            return str(choice.get("text", ""))
        except Exception:
            return ""

    def _parse_logprobs(self, resp_json: Dict[str, Any]) -> List[TokenLogprob]:
        """Private helper to safely extract log probability lists."""
        tokens: List[TokenLogprob] = []
        try:
            choices = resp_json.get("choices")
            if not choices:
                return tokens
            choice = choices[0]
            logprobs_data = choice.get("logprobs")
            if not logprobs_data:
                return tokens

            # Standard Chat completions: choices[0].logprobs.content = list
            if "content" in logprobs_data and logprobs_data["content"] is not None:
                for item in logprobs_data["content"]:
                    tok = item.get("token")
                    prob = item.get("logprob")
                    if tok is not None and prob is not None:
                        tokens.append(TokenLogprob(token=str(tok), logprob=float(prob)))
            # Legacy completions: choices[0].logprobs = dict of tokens, token_logprobs
            elif "tokens" in logprobs_data and "token_logprobs" in logprobs_data:
                legacy_toks = logprobs_data["tokens"]
                legacy_probs = logprobs_data["token_logprobs"]
                if legacy_toks and legacy_probs and len(legacy_toks) == len(legacy_probs):
                    for tok, prob in zip(legacy_toks, legacy_probs):
                        if tok is not None and prob is not None:
                            tokens.append(TokenLogprob(token=str(tok), logprob=float(prob)))
        except Exception as e:
            logger.warning(f"Error parsing logprobs: {e}")
        return tokens

    def _parse_usage(self, resp_json: Dict[str, Any], text: str) -> int:
        """Private helper to safely extract usage token count."""
        try:
            usage = resp_json.get("usage", {})
            total = usage.get("total_tokens")
            if total is not None:
                return int(total)
            
            prompt = usage.get("prompt_tokens", 0)
            comp = usage.get("completion_tokens", 0)
            if prompt or comp:
                return int(prompt + comp)
        except Exception:
            pass
        # Fallback estimation
        return max(1, len(text) // 4)

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        """Asynchronously dispatch prompt payload to local server.
        
        Raises:
            InferenceTimeoutError: If the request fails or times out.
        """
        url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Build standard chat completions payload with task-aware system prompt
        system_content = "Answer the user's actual task directly and accurately. Do not add a preamble."
        
        # Detect explicit constraints in prompt
        import re
        constraints_added = []
        
        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        number = r"(?P<count>\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
        
        sentence_match = re.search(
            rf"\b(?:exactly\s+)?{number}\s+sentences?\b", prompt, re.IGNORECASE
        )
        bullet_match = re.search(
            rf"\b(?:exactly\s+)?{number}\s+bullet(?:\s+points?)?\b",
            prompt,
            re.IGNORECASE,
        )
        word_match = re.search(
            r"\b(?:no\s+(?:longer|more)\s+than|at\s+most|maximum(?:\s+of)?)\s+"
            r"(?P<count>\d+)\s+words?(?:\s+per\s+bullet|\s+each)?\b",
            prompt,
            re.IGNORECASE,
        )
        
        if sentence_match:
            raw = sentence_match.group("count").casefold()
            count = int(raw) if raw.isdigit() else number_words.get(raw, 1)
            constraints_added.append(f"Return exactly {count} sentences.")
            
        if bullet_match:
            raw = bullet_match.group("count").casefold()
            count = int(raw) if raw.isdigit() else number_words.get(raw, 1)
            constraints_added.append(f"Return exactly {count} bullet points.")
            
        if word_match:
            count = int(word_match.group("count"))
            constraints_added.append(f"Each bullet must contain at most {count} words.")
            
        if "json" in prompt.lower() or "schema" in prompt.lower():
            constraints_added.append("Return raw valid JSON only, without Markdown fences.")
            
        if "sentiment" in prompt.lower() or any(label in prompt.lower() for label in ["mixed", "neutral", "positive"]):
            constraints_added.append("Start with one allowed label (mixed, neutral, positive) and acknowledge both positive and negative evidence.")
            
        if constraints_added:
            system_content += "\n" + "\n".join(constraints_added)
            
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "logprobs": True,
            "top_logprobs": 1
        }

        category = str((params or {}).get("category", "")).casefold()
        prompt_lower = prompt.casefold()
        if category in {"sentiment_classification", "classification"} or "classify" in prompt_lower:
            payload.update({"max_tokens": 160, "temperature": 0.0})
        elif category in {"named_entity_recognition", "ner"} or "named entit" in prompt_lower:
            payload.update({"max_tokens": 300, "temperature": 0.0})
        elif category in {"mathematical_reasoning", "math"} or any(
            marker in prompt_lower for marker in ("calculate", "solve", "how many", "how much")
        ):
            payload.update({"max_tokens": 400, "temperature": 0.0})
        elif category == "text_summarization" or "summarize" in prompt_lower:
            payload.update({"max_tokens": 450, "temperature": 0.0})
        elif category in {"creative", "creative_writing"}:
            payload.update({"max_tokens": 900, "temperature": 0.4})
        else:
            payload.update({"max_tokens": 500, "temperature": 0.0})
        
        # Merge input parameters, filtering out system metadata like task_id
        task_id = None
        if params:
            task_id = params.get("task_id")
            for k, v in params.items():
                if k not in {"task_id", "category"}:
                    payload[k] = v

        max_retries = 3
        attempt = 0
        status_code = None
        latency_ms = 0.0
        token_count = 0
        last_error: Any = None
        response: Optional[httpx.Response] = None

        while attempt <= max_retries:
            if attempt > 0:
                # Exponential backoff delay: 2^attempt + jitter
                delay = (2.0 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                await asyncio.sleep(delay)

            t0 = time.perf_counter()
            try:
                response = await self.client.post(url, headers=headers, json=payload, timeout=self.timeout_sec)
                status_code = response.status_code
                latency_ms = (time.perf_counter() - t0) * 1000.0

                # Stop retrying on terminal client errors
                if response.status_code in {400, 401, 403, 404}:
                    if response.status_code == 401:
                        raise ConfigurationError("Authentication failure (401) on local client.")
                    elif response.status_code == 403:
                        raise ConfigurationError("Access forbidden (403) on local client.")
                    else:
                        raise InferenceTimeoutError(f"Local request failed with terminal status {response.status_code}")
                
                # Raise exception on transient errors to trigger retry block
                response.raise_for_status()
                break  # Successful response

            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.ConnectTimeout) as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                logger.warning(f"Transient network/timeout error on attempt {attempt + 1}: {e}")
                attempt += 1
            except httpx.HTTPStatusError as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                # Only retry on transient codes: 429, 500, 502, 503, 504
                if e.response.status_code in {429, 500, 502, 503, 504}:
                    logger.warning(f"Transient HTTP status {e.response.status_code} on attempt {attempt + 1}")
                    attempt += 1
                else:
                    raise InferenceTimeoutError(f"Local request failed with terminal status {e.response.status_code}")
            except (ConfigurationError, InferenceTimeoutError):
                raise
            except Exception as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                attempt += 1
        else:
            # Loop completed without break: retry exhaustion
            extra_fail = {
                "route": "local_llm",
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "retry_count": min(attempt, max_retries),
                "status_code": status_code,
                "token_count": 0
            }
            _log_structured("ERROR", "app.inference.local_client", f"Local request failed: {last_error}", task_id, extra_fail)
            raise InferenceTimeoutError(f"Local client failed after {attempt} attempts. Last error: {last_error}")

        # Parse response (outside retry loop to prevent wasteful retries on JSON value errors)
        try:
            response_json = response.json()
        except Exception as e:
            extra_fail_json = {
                "route": "local_llm",
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "retry_count": attempt,
                "status_code": status_code,
                "token_count": 0
            }
            _log_structured("ERROR", "app.inference.local_client", f"Malformed JSON: {e}", task_id, extra_fail_json)
            raise InferenceTimeoutError(f"Malformed local model response: {e}")

        text = self._parse_completion(response_json)
        tokens = self._parse_logprobs(response_json)
        token_count = self._parse_usage(response_json, text)

        # Emit successful structured log
        extra_success = {
            "route": "local_llm",
            "model_name": self.model_name,
            "latency_ms": latency_ms,
            "retry_count": attempt,
            "status_code": status_code,
            "token_count": token_count
        }
        _log_structured("INFO", "app.inference.local_client", "Local inference completed successfully", task_id, extra_success)

        return RawModelOutput(
            text=text,
            tokens=tokens,
            latency_ms=latency_ms,
            usage_tokens=token_count
        )

    async def generate_n_async(
        self,
        prompt: str,
        n: int,
        params: Optional[Dict[str, Any]] = None,
        concurrency_limit: int = 3,
        use_sequential_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Request n completions, with concurrency limit and optional sequential fallback.
        Treats each call as an independent inference request.
        """
        import asyncio
        import time

        results = []
        sem = asyncio.Semaphore(concurrency_limit)

        async def make_request(idx: int) -> Dict[str, Any]:
            t0 = time.perf_counter()
            success = False
            error_msg = None
            out = None
            prompt_toks = 0
            comp_toks = 0
            latency = 0.0
            usage_toks = 0

            try:
                async with sem:
                    out = await self.generate_async(prompt, params)
                    success = True
                    latency = out.latency_ms
                    usage_toks = out.usage_tokens
                    comp_toks = len(out.tokens) if out.tokens else max(1, len(out.text) // 4)
                    prompt_toks = max(0, usage_toks - comp_toks)
            except Exception as e:
                error_msg = str(e)
                latency = (time.perf_counter() - t0) * 1000.0
                logger.warning(f"Sample generation {idx} failed: {e}")

            return {
                "success": success,
                "output": out,
                "error": error_msg,
                "latency_ms": latency,
                "usage_tokens": usage_toks,
                "prompt_tokens": prompt_toks,
                "completion_tokens": comp_toks
            }

        try:
            tasks = [make_request(i) for i in range(n)]
            results = await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Parallel requests failed: {e}")
            if use_sequential_fallback:
                logger.info("Falling back to sequential request mode.")
                results = []
                for i in range(n):
                    res = await make_request(i)
                    results.append(res)
            else:
                raise e

        return results
