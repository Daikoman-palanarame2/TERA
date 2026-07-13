"""Strict local vLLM readiness checks for the submission batch path."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse
from typing import Any

import httpx

from app.core.exceptions import ConfigurationError, InferenceTimeoutError


def require_loopback_endpoint(endpoint: str) -> None:
    """Reject endpoints that could send prompts outside the local machine."""
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigurationError(f"Invalid local inference endpoint: {endpoint}")
    hostname = parsed.hostname.casefold()
    if hostname == "localhost":
        return
    try:
        if ipaddress.ip_address(hostname).is_loopback:
            return
    except ValueError:
        pass
    raise ConfigurationError(f"Inference endpoint must be loopback-only: {endpoint}")


def parse_version(value: str) -> tuple[int, ...]:
    """Parse the numeric prefix of a semantic-style version string."""
    numbers: list[int] = []
    for component in value.strip().lstrip("v").split("."):
        digits = "".join(character for character in component if character.isdigit())
        if not digits:
            break
        numbers.append(int(digits))
    if not numbers:
        raise ConfigurationError(f"Unrecognized vLLM version: {value!r}")
    return tuple(numbers)


def version_at_least(actual: str, required: str) -> bool:
    width = max(len(parse_version(actual)), len(parse_version(required)))
    left = parse_version(actual) + (0,) * (width - len(parse_version(actual)))
    right = parse_version(required) + (0,) * (width - len(parse_version(required)))
    return left >= right


async def check_vllm_endpoint(
    endpoint: str,
    expected_model: str,
    minimum_version: str,
    timeout_sec: float = 10.0,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Verify version, served model ID, generation, usage, and chat logprobs."""
    require_loopback_endpoint(endpoint)
    base = endpoint.rstrip("/")
    if base.endswith("/v1"):
        root = base[:-3]
    else:
        root = base
        base = f"{base}/v1"
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout_sec)
    try:
        version_response = await http.get(f"{root}/version")
        version_response.raise_for_status()
        version_payload = version_response.json()
        actual_version = str(
            version_payload.get("version") if isinstance(version_payload, dict) else version_payload
        )
        if not version_at_least(actual_version, minimum_version):
            raise ConfigurationError(
                f"vLLM {actual_version} is below required {minimum_version} for {expected_model}."
            )

        models_response = await http.get(f"{base}/models")
        models_response.raise_for_status()
        model_ids = {
            str(item.get("id"))
            for item in models_response.json().get("data", [])
            if isinstance(item, dict) and item.get("id")
        }
        if expected_model not in model_ids:
            raise ConfigurationError(
                f"Expected model {expected_model!r} is not served; available={sorted(model_ids)}"
            )

        completion_response = await http.post(
            f"{base}/chat/completions",
            json={
                "model": expected_model,
                "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
                "max_tokens": 8,
                "temperature": 0,
                "logprobs": True,
                "top_logprobs": 1,
            },
        )
        completion_response.raise_for_status()
        payload = completion_response.json()
        choices = payload.get("choices", [])
        if not choices or not str(choices[0].get("message", {}).get("content", "")).strip():
            raise InferenceTimeoutError("vLLM readiness completion returned no text.")
        logprobs = choices[0].get("logprobs", {}).get("content", [])
        if not logprobs:
            raise InferenceTimeoutError("vLLM readiness completion returned no token logprobs.")
        return {
            "endpoint": endpoint,
            "model": expected_model,
            "vllm_version": actual_version,
            "logprob_tokens": len(logprobs),
        }
    except httpx.HTTPError as error:
        raise InferenceTimeoutError(f"Local vLLM readiness failed: {error}") from error
    finally:
        if owns_client:
            await http.aclose()
