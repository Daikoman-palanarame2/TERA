"""
Unit tests for TERA V3 Core Foundation components:
- config.py
- exceptions.py
- state.py
- helpers.py
"""

import os
import time
import pytest
import asyncio
from app.core.exceptions import (
    TERABaseException,
    ConfigurationError,
    InferenceTimeoutError,
    CacheError,
    VerificationError,
    RoutingError,
)
from app.core.config import Configuration, EnvConfigurationProvider
from app.core.state import ApplicationState
from app.utils.helpers import run_in_executor, clean_prompt


def test_exception_hierarchy() -> None:
    """Verifies that all custom exceptions derive from TERABaseException and retain attributes."""
    task_id = "test-task-123"
    message = "An error occurred"

    # Test Base Exception
    base_err = TERABaseException(message, task_id=task_id)
    assert base_err.message == message
    assert base_err.task_id == task_id
    assert str(base_err) == message

    # Test Specific Exceptions
    with pytest.raises(ConfigurationError) as exc:
        raise ConfigurationError("Config error", task_id=task_id)
    assert exc.value.task_id == task_id
    assert isinstance(exc.value, TERABaseException)

    with pytest.raises(InferenceTimeoutError) as exc:
        raise InferenceTimeoutError("Timeout error", task_id=task_id)
    assert exc.value.task_id == task_id
    assert isinstance(exc.value, TERABaseException)

    with pytest.raises(CacheError) as exc:
        raise CacheError("Cache error", task_id=task_id)
    assert exc.value.task_id == task_id
    assert isinstance(exc.value, TERABaseException)

    with pytest.raises(VerificationError) as exc:
        raise VerificationError("Verification error", task_id=task_id)
    assert exc.value.task_id == task_id
    assert isinstance(exc.value, TERABaseException)

    with pytest.raises(RoutingError) as exc:
        raise RoutingError("Routing error", task_id=task_id)
    assert exc.value.task_id == task_id
    assert isinstance(exc.value, TERABaseException)


def test_configuration_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests environment-driven configuration loading and validation rules."""
    provider = EnvConfigurationProvider()

    # Clear environment variables
    monkeypatch.delenv("FAST_MODEL_ENDPOINT", raising=False)
    monkeypatch.delenv("FAST_MODEL_IDENTIFIER", raising=False)
    monkeypatch.delenv("POWER_MODEL_ENDPOINT", raising=False)
    monkeypatch.delenv("POWER_MODEL_IDENTIFIER", raising=False)

    # Test missing parameters raising ConfigurationError
    with pytest.raises(ConfigurationError) as exc:
        provider.get_config()
    assert "Missing required configuration" in str(exc.value)

    # Set valid configuration
    monkeypatch.setenv("FAST_MODEL_ENDPOINT", "http://localhost:8000/v1")
    monkeypatch.setenv("FAST_MODEL_IDENTIFIER", "fast-model-1")
    monkeypatch.setenv("POWER_MODEL_ENDPOINT", "https://api.fireworks.ai/v1")
    monkeypatch.setenv("POWER_MODEL_IDENTIFIER", "power-model-2")

    config = provider.get_config()
    assert isinstance(config, Configuration)
    assert config.FAST_MODEL_ENDPOINT == "http://localhost:8000/v1"
    assert config.FAST_MODEL_IDENTIFIER == "fast-model-1"
    assert config.POWER_MODEL_ENDPOINT == "https://api.fireworks.ai/v1"
    assert config.POWER_MODEL_IDENTIFIER == "power-model-2"

    # Test invalid URL schema validation raising ConfigurationError
    monkeypatch.setenv("FAST_MODEL_ENDPOINT", "ftp://localhost:8000/v1")
    with pytest.raises(ConfigurationError) as exc:
        provider.get_config()
    assert "Invalid URL schema" in str(exc.value)


def test_application_state_lifecycle() -> None:
    """Verifies ApplicationState properties, transitions, and concurrent request tracking."""
    state = ApplicationState()

    # Initial state
    assert not state.is_initialized
    assert not state.is_shutdown
    assert not state.is_healthy()
    assert state.active_requests == 0
    assert state.uptime_seconds >= 0.0

    # Initialize
    state.initialize()
    assert state.is_initialized
    assert not state.is_shutdown
    assert state.is_healthy()

    # Request concurrency tracking
    state.increment_active_requests()
    state.increment_active_requests()
    assert state.active_requests == 2

    state.decrement_active_requests()
    assert state.active_requests == 1

    state.decrement_active_requests()
    state.decrement_active_requests()
    # Check lower boundary guard
    assert state.active_requests == 0

    # Shutdown
    state.shutdown_system()
    assert state.is_shutdown
    assert not state.is_healthy()


def test_string_clean_helper() -> None:
    """Tests clean_prompt utility behavior on various strings."""
    assert clean_prompt("   hello world   \n") == "hello world"
    assert clean_prompt("") == ""
    # Check type check/safety representation
    assert clean_prompt(None) == ""


@pytest.mark.anyio
async def test_async_executor_helper() -> None:
    """Tests run_in_executor runs blocking code asynchronously."""
    def blocking_calc(x: int, y: int, multiplier: int = 2) -> int:
        time.sleep(0.01)
        return (x + y) * multiplier

    # Run blocking code asynchronously
    res = await run_in_executor(blocking_calc, 5, 10, multiplier=3)
    assert res == 45
