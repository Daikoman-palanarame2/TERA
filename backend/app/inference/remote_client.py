"""
Module: backend/app/inference/remote_client
Purpose:
    Implements the RemoteModelClient class for asynchronous execution against
    the remote Fireworks completions API.
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
from app.core.config import MODEL_TIMEOUT_SEC

# Get loggers
logger = logging.getLogger("app.inference.remote_client")
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


class RemoteModelClient(ModelInterface):
    """
    Purpose:
        Production-grade asynchronous client for Fireworks API with exponential backoff retries.
    """

    is_external = True

    def __init__(self, api_key: str, endpoint_url: str, model_name: str, max_retries: int = 3) -> None:
        """Initialize the remote Fireworks client.
        
        Args:
            api_key: Fireworks authentication token.
            endpoint_url: Base endpoint URL.
            model_name: Remote model name.
            max_retries: Retry threshold for transient errors.
            
        Raises:
            ConfigurationError: If key or settings are invalid.
        """
        if not api_key or not api_key.strip():
            raise ConfigurationError("API key must not be empty.")
        if not endpoint_url or not endpoint_url.strip():
            raise ConfigurationError("Endpoint URL must not be empty.")
        if not model_name or not model_name.strip():
            raise ConfigurationError("Model name must not be empty.")
        if max_retries < 0:
            raise ConfigurationError("Max retries must be a non-negative integer.")

        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout_sec = MODEL_TIMEOUT_SEC  # Core network parameter: MODEL_TIMEOUT_SEC
        # Reuse a single AsyncClient instance
        self.client = httpx.AsyncClient(timeout=self.timeout_sec)

    async def close(self) -> None:
        """Performs proper cleanup of the underlying HTTP connection pool."""
        await self.client.aclose()

    async def __aenter__(self) -> "RemoteModelClient":
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

            if "content" in logprobs_data and logprobs_data["content"] is not None:
                for item in logprobs_data["content"]:
                    tok = item.get("token")
                    prob = item.get("logprob")
                    if tok is not None and prob is not None:
                        tokens.append(TokenLogprob(token=str(tok), logprob=float(prob)))
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
        return max(1, len(text) // 4)

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        """Asynchronously dispatch prompt payload to Fireworks completions API.
        
        Raises:
            InferenceTimeoutError: If the requests fail, time out, or retries exhaust.
            ConfigurationError: If auth fails.
        """
        url = f"{self.endpoint_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "logprobs": True,
            "top_logprobs": 1
        }
        
        task_id = None
        if params:
            task_id = params.get("task_id")
            for k, v in params.items():
                if k != "task_id":
                    payload[k] = v

        attempt = 0
        status_code = None
        latency_ms = 0.0
        token_count = 0
        last_error: Any = None
        response: Optional[httpx.Response] = None

        while attempt <= self.max_retries:
            if attempt > 0:
                # Exponential backoff: FALLBACK_BACKOFF_FACTOR = 2.0 with jitter
                delay = (2.0 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                await asyncio.sleep(delay)

            t0 = time.perf_counter()
            try:
                response = await self.client.post(url, headers=headers, json=payload, timeout=self.timeout_sec)
                status_code = response.status_code
                latency_ms = (time.perf_counter() - t0) * 1000.0

                # Check terminal HTTP codes
                if response.status_code == 401:
                    logger.error("Authentication failure (401) on remote client.")
                    raise ConfigurationError("Remote authentication failed: Invalid API key.")
                elif response.status_code in {400, 403, 404}:
                    logger.error(f"Terminal HTTP error {response.status_code} on remote client.")
                    raise InferenceTimeoutError(f"Remote request failed with terminal status {response.status_code}")
                
                response.raise_for_status()
                break  # Success

            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.ConnectTimeout) as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                logger.warning(f"Transient error on attempt {attempt + 1}: {e}")
                attempt += 1
            except httpx.HTTPStatusError as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                # Retry on 429 and 5xx codes
                if e.response.status_code in {429, 500, 502, 503, 504}:
                    logger.warning(f"Transient HTTP status {e.response.status_code} on attempt {attempt + 1}")
                    attempt += 1
                else:
                    raise InferenceTimeoutError(f"Remote request failed with terminal status {e.response.status_code}")
            except (ConfigurationError, InferenceTimeoutError):
                raise
            except Exception as e:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                last_error = e
                attempt += 1
        else:
            # Loop completed without break: retry exhaustion
            extra_fail = {
                "route": "remote_fallback",
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "retry_count": min(attempt, self.max_retries),
                "status_code": status_code,
                "token_count": 0
            }
            _log_structured("ERROR", "app.inference.remote_client", f"Remote request failed: {last_error}", task_id, extra_fail)
            raise InferenceTimeoutError(f"Remote client failed after {attempt} attempts. Last error: {last_error}")

        # Parse response (outside retry loop to prevent wasteful retries on JSON value errors)
        try:
            response_json = response.json()
        except Exception as e:
            extra_fail_json = {
                "route": "remote_fallback",
                "model_name": self.model_name,
                "latency_ms": latency_ms,
                "retry_count": attempt,
                "status_code": status_code,
                "token_count": 0
            }
            _log_structured("ERROR", "app.inference.remote_client", f"Malformed JSON: {e}", task_id, extra_fail_json)
            raise InferenceTimeoutError(f"Malformed remote model response: {e}")

        text = self._parse_completion(response_json)
        tokens = self._parse_logprobs(response_json)
        token_count = self._parse_usage(response_json, text)

        # Emit successful structured log
        extra_success = {
            "route": "remote_fallback",
            "model_name": self.model_name,
            "latency_ms": latency_ms,
            "retry_count": attempt,
            "status_code": status_code,
            "token_count": token_count
        }
        _log_structured("INFO", "app.inference.remote_client", "Remote inference completed successfully", task_id, extra_success)

        return RawModelOutput(
            text=text,
            tokens=tokens,
            latency_ms=latency_ms,
            usage_tokens=token_count,
            external_api_calls=attempt + 1
        )
