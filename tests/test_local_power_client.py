"""Focused tests for the local power-model inference adapter."""

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
)

from app.core.exceptions import ConfigurationError
from app.inference.local_power_client import LocalPowerModelClient


def test_rejects_fireworks_endpoints() -> None:
    with pytest.raises(ConfigurationError, match="must not use a Fireworks host"):
        LocalPowerModelClient(
            "https://api.fireworks.ai/inference/v1", "power-model"
        )

    with pytest.raises(ConfigurationError, match="must not use a Fireworks host"):
        LocalPowerModelClient("https://fireworks.ai/v1", "power-model")


@pytest.mark.asyncio
async def test_uses_local_openai_contract_without_credentials() -> None:
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "choices": [
            {
                "message": {"content": "power answer"},
                "logprobs": {
                    "content": [{"token": "power", "logprob": -0.1}]
                },
            }
        ],
        "usage": {"total_tokens": 8},
    }

    client = LocalPowerModelClient(
        "http://127.0.0.1:8001/v1", "local-power-model"
    )
    client.client.post = AsyncMock(return_value=response)
    try:
        output = await client.generate_async(
            "hard prompt",
            {
                "task_id": "power-1",
                "temperature": 0,
                "api_key": "must-not-leak",
                "Authorization": "must-not-leak",
            },
        )
    finally:
        await client.close()

    assert output.text == "power answer"
    assert output.usage_tokens == 8
    assert output.tokens[0].token == "power"

    call = client.client.post.await_args
    assert call.args[0] == "http://127.0.0.1:8001/v1/chat/completions"
    assert "Authorization" not in call.kwargs["headers"]
    assert call.kwargs["json"]["model"] == "local-power-model"
    assert call.kwargs["json"]["logprobs"] is True
    assert call.kwargs["json"]["top_logprobs"] == 1
    assert "api_key" not in call.kwargs["json"]
    assert "Authorization" not in call.kwargs["json"]


@pytest.mark.asyncio
async def test_defaults_to_longer_power_timeout() -> None:
    client = LocalPowerModelClient("http://localhost:8001/v1", "power-model")
    try:
        assert client.timeout_sec == 30.0
        assert client.tier == "local_power"
    finally:
        await client.close()
