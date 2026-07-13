import httpx
import pytest

from app.core.exceptions import ConfigurationError, InferenceTimeoutError
from app.inference.readiness import (
    check_vllm_endpoint,
    require_loopback_endpoint,
    version_at_least,
)


def test_loopback_and_version_validation() -> None:
    require_loopback_endpoint("http://localhost:8000/v1")
    require_loopback_endpoint("http://127.0.0.1:8001/v1")
    require_loopback_endpoint("http://[::1]:8000/v1")
    with pytest.raises(ConfigurationError):
        require_loopback_endpoint("https://api.example.com/v1")
    assert version_at_least("0.19.1", "0.19.0")
    assert not version_at_least("0.16.0", "0.19.0")


@pytest.mark.asyncio
async def test_readiness_checks_model_and_logprobs() -> None:
    model = "google/gemma-4-E4B-it"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/version":
            return httpx.Response(200, json={"version": "0.19.1"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": model}]})
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(
                200,
                json={
                    "choices": [{
                        "message": {"content": "READY"},
                        "logprobs": {"content": [{"token": "READY", "logprob": -0.01}]},
                    }]
                },
            )
        raise AssertionError(request.url)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_vllm_endpoint(
            "http://127.0.0.1:8000/v1", model, "0.19.0", client=client
        )
    assert result["model"] == model
    assert result["logprob_tokens"] == 1


@pytest.mark.asyncio
async def test_readiness_rejects_old_runtime_and_missing_logprobs() -> None:
    model = "google/gemma-4-E4B-it"

    def old_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"version": "0.16.0"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(old_handler)) as client:
        with pytest.raises(ConfigurationError, match="below required"):
            await check_vllm_endpoint(
                "http://127.0.0.1:8000/v1", model, "0.19.0", client=client
            )

    def no_logprob_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/version":
            return httpx.Response(200, json={"version": "0.19.1"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": model}]})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "READY"}, "logprobs": {}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(no_logprob_handler)) as client:
        with pytest.raises(InferenceTimeoutError, match="no token logprobs"):
            await check_vllm_endpoint(
                "http://127.0.0.1:8000/v1", model, "0.19.0", client=client
            )
