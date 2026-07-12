"""
Unit and integration tests for the TERAOrchestrator implementation.
Provides mock boundary configurations to verify cache hits, solver match, local success,
ROVL verification failures, remote fallbacks, timeouts, and exceptions.
"""

import os
import sys
import json
import pytest
import tempfile
import asyncio
from typing import Dict, Any, List

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.schemas.data_contracts import (
    InferenceRequest,
    InferenceResponse,
    RawModelOutput,
    VerificationConstraints,
    VerificationResult,
    TokenLogprob,
    TelemetryLog
)
from app.core.orchestrator import TERAOrchestrator
from app.core.state import RequestState
from app.core.exceptions import (
    TERABaseException,
    VerificationError,
    CacheError,
    InferenceTimeoutError,
    RoutingError,
    ConfigurationError
)
from app.inference.model_interface import ModelInterface


# =====================================================================
# Mock Subsystems Implementation
# =====================================================================

class MockSemanticCache:
    def __init__(self) -> None:
        self.data: Dict[str, str] = {}
        self.should_fail: bool = False
        self.inserted: Dict[str, str] = {}

    def lookup(self, prompt: str, threshold: float = 0.95) -> Any:
        if self.should_fail:
            raise CacheError("LMDB read failure")
        return self.data.get(prompt)

    def insert(self, prompt: str, response: str) -> None:
        if self.should_fail:
            raise CacheError("LMDB write failure")
        self.inserted[prompt] = response


class MockIntentParser:
    def __init__(self) -> None:
        self.should_fail: bool = False

    def parse_intent(self, prompt: str) -> Any:
        if self.should_fail:
            raise RoutingError("Regex compilation failed")
        if "solver:" in prompt:
            return "mock_arithmetic"
        return None


class MockSolverRegistry:
    def __init__(self) -> None:
        self.should_fail: bool = False

    def execute(self, solver_name: str, prompt: str) -> str:
        if self.should_fail:
            raise Exception("Ast solver crashed")
        return f"solver_solved:{prompt}"


class MockModelClient(ModelInterface):
    def __init__(self, text: str = "Local completion", latency: float = 10.0, tokens: int = 5) -> None:
        self.text = text
        self.latency = latency
        self.tokens = tokens
        self.should_timeout = False
        self.call_count = 0

    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        self.call_count += 1
        if self.should_timeout:
            raise InferenceTimeoutError("Connection timed out")
        return RawModelOutput(
            text=self.text,
            tokens=[TokenLogprob(token="test", logprob=-0.1)],
            latency_ms=self.latency,
            usage_tokens=self.tokens
        )


class MockROVL:
    def __init__(self) -> None:
        self.should_pass: bool = True
        self.should_fail_verification: bool = False

    def verify(self, output: RawModelOutput, constraints: VerificationConstraints, task_id: Any = None) -> VerificationResult:
        if self.should_fail_verification:
            raise VerificationError("ROVL schema failure")
        return VerificationResult(
            passed=self.should_pass,
            average_surprisal=0.1,
            sequence_entropy=0.1,
            failed_validators=[] if self.should_pass else ["json_schema"]
        )


class MockSettings:
    def __init__(self, telemetry_path: str) -> None:
        self.tera_telemetry_path = telemetry_path


class LocalOnlyMockSettings(MockSettings):
    def __init__(self, telemetry_path: str) -> None:
        super().__init__(telemetry_path)
        self.tera_external_fallback_enabled = False


# =====================================================================
# Test Suite
# =====================================================================

@pytest.fixture
def temp_telemetry_file() -> Any:
    """Fixture providing a temporary file path for telemetry logging."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.asyncio
async def test_cache_hit_route(temp_telemetry_file: str) -> None:
    """Verify that a semantic cache hit bypasses both parser and model generation."""
    cache = MockSemanticCache()
    cache.data["test prompt"] = "Cached response text"
    
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    remote = MockModelClient()
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="test prompt",
        task_id="task_123_abc",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    
    assert response.route_taken == "cache"
    assert response.final_response == "Cached response text"
    assert response.tokens_consumed == 0
    assert response.verification is None
    
    # Check telemetry file
    with open(temp_telemetry_file, "r") as f:
        line = f.readline()
        import json
        telemetry = json.loads(line)
        assert telemetry["route_taken"] == "cache"
        assert telemetry["cache_hit"] is True
        assert telemetry["del_bypass"] is False


@pytest.mark.asyncio
async def test_solver_match_route(temp_telemetry_file: str) -> None:
    """Verify that deterministic solver match resolves programmatically without calling LLM."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    remote = MockModelClient()
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="solver: arithmetic text",
        task_id="task_124_def",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    
    assert response.route_taken == "solver"
    assert response.final_response == "solver_solved:solver: arithmetic text"
    assert response.tokens_consumed == 0
    
    # Check telemetry
    with open(temp_telemetry_file, "r") as f:
        line = f.readline()
        import json
        telemetry = json.loads(line)
        assert telemetry["route_taken"] == "solver"
        assert telemetry["del_bypass"] is True


@pytest.mark.asyncio
async def test_local_model_success_path(temp_telemetry_file: str) -> None:
    """Verify that a successful local model generation passing ROVL is saved to cache and returned."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient(text="Local clean output", tokens=10)
    remote = MockModelClient()
    rovl = MockROVL()
    rovl.should_pass = True
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="standard text prompt",
        task_id="task_125_ghi",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    
    assert response.route_taken == "local_llm"
    assert response.final_response == "Local clean output"
    assert response.tokens_consumed == 10
    assert response.verification.passed is True
    
    # Verify cached output
    assert cache.inserted["standard text prompt"] == "Local clean output"


@pytest.mark.asyncio
async def test_local_verification_fail_remote_fallback(temp_telemetry_file: str) -> None:
    """Verify that if local model fails verification, the remote fallback is executed and returned."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient(text="Local failed output", tokens=10)
    remote = MockModelClient(text="Remote fallback success", tokens=15)
    rovl = MockROVL()
    # Mock ROVL: fail first call (local output), pass second call (remote fallback)
    verify_calls = []
    def verify_mock(output: RawModelOutput, constraints: VerificationConstraints, task_id: Any = None) -> VerificationResult:
        verify_calls.append(output.text)
        if output.text == "Local failed output":
            return VerificationResult(passed=False, average_surprisal=2.0, sequence_entropy=2.0, failed_validators=["json_schema"])
        return VerificationResult(passed=True, average_surprisal=0.1, sequence_entropy=0.1, failed_validators=[])
    rovl.verify = verify_mock
    
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="complex task prompt",
        task_id="task_126_jkl",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    
    assert response.route_taken == "remote_fallback"
    assert response.final_response == "Remote fallback success"
    assert response.tokens_consumed == 25  # Local (10) + Remote (15)
    assert len(verify_calls) == 2
    assert cache.inserted["complex task prompt"] == "Remote fallback success"


@pytest.mark.asyncio
async def test_local_only_mode_never_calls_remote(temp_telemetry_file: str) -> None:
    """A rejected local answer must not cause network fallback in local-only mode."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient(text="Rejected local output")
    remote = MockModelClient(text="Must never be requested")
    remote.is_external = True
    rovl = MockROVL()
    rovl.should_pass = False
    settings = LocalOnlyMockSettings(temp_telemetry_file)
    orchestrator = TERAOrchestrator(
        cache, parser, registry, local, remote, rovl, settings
    )
    request = InferenceRequest(
        prompt="local-only prompt",
        task_id="task_126_localonly",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8,
    )

    with pytest.raises(InferenceTimeoutError, match="External fallback is disabled"):
        await orchestrator.process_request_async(request)

    assert local.call_count == 1
    assert remote.call_count == 0


@pytest.mark.asyncio
async def test_local_power_escalation_has_zero_fireworks_telemetry(
    temp_telemetry_file: str,
) -> None:
    """A second local model is an allowed power tier, not an external fallback."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient(text="Rejected fast output", tokens=5)
    power = MockModelClient(text="Accepted power output", tokens=9)
    power.tier = "local_power"
    verify_calls = 0
    rovl = MockROVL()

    def verify(output: RawModelOutput, constraints: VerificationConstraints, task_id: Any = None) -> VerificationResult:
        nonlocal verify_calls
        verify_calls += 1
        return VerificationResult(
            passed=verify_calls == 2,
            average_surprisal=0.1,
            sequence_entropy=0.1,
            failed_validators=[] if verify_calls == 2 else ["probability_floor"],
        )

    rovl.verify = verify
    settings = LocalOnlyMockSettings(temp_telemetry_file)
    orchestrator = TERAOrchestrator(
        cache, parser, registry, local, power, rovl, settings
    )
    request = InferenceRequest(
        prompt="power-tier prompt",
        task_id="task_126_localpower",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8,
    )

    response = await orchestrator.process_request_async(request)

    assert response.route_taken == "local_power"
    assert response.final_response == "Accepted power output"
    with open(temp_telemetry_file, "r", encoding="utf-8") as handle:
        telemetry = json.loads(handle.readline())
    assert telemetry["fireworks_tokens"] == 0
    assert telemetry["remote_fallback_triggered"] is False


@pytest.mark.asyncio
async def test_local_inference_timeout(temp_telemetry_file: str) -> None:
    """Verify that local inference timeout throws custom exceptions if remote fallback also fails."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    local.should_timeout = True
    remote = MockModelClient()
    remote.should_timeout = True
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="standard prompt",
        task_id="task_127_mno",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    with pytest.raises(InferenceTimeoutError):
        await orchestrator.process_request_async(request)
        
    # Check telemetry file captures error route
    with open(temp_telemetry_file, "r") as f:
        line = f.readline()
        import json
        telemetry = json.loads(line)
        assert telemetry["route_taken"] == "error"
        assert telemetry["verification_passed"] is False


@pytest.mark.asyncio
async def test_local_inference_timeout_fallback(temp_telemetry_file: str) -> None:
    """Verify that local inference timeout triggers successful fallback to remote client."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    local.should_timeout = True
    remote = MockModelClient(text="Remote success after local timeout", tokens=8)
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="fallback prompt",
        task_id="task_127_mn2",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    assert response.route_taken == "remote_fallback"
    assert response.final_response == "Remote success after local timeout"
    assert response.tokens_consumed == 8


@pytest.mark.asyncio
async def test_cache_error_graceful_fallback(temp_telemetry_file: str) -> None:
    """Verify that if CacheError is raised, orchestrator logs warning and falls back to model pipeline."""
    cache = MockSemanticCache()
    cache.should_fail = True
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient(text="Local fallback clean", tokens=5)
    remote = MockModelClient()
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="prompt with cache error",
        task_id="task_128_pqr",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    assert response.route_taken == "local_llm"
    assert response.final_response == "Local fallback clean"


@pytest.mark.asyncio
async def test_parser_error_graceful_fallback(temp_telemetry_file: str) -> None:
    """Verify that if RoutingError is raised during intent parsing, pipeline falls back to model inference."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    parser.should_fail = True
    registry = MockSolverRegistry()
    local = MockModelClient(text="Local model response", tokens=5)
    remote = MockModelClient()
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="prompt with parser error",
        task_id="task_129_stu",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    assert response.route_taken == "local_llm"
    assert response.final_response == "Local model response"


@pytest.mark.asyncio
async def test_solver_error_graceful_fallback(temp_telemetry_file: str) -> None:
    """Verify that if solver execution crashes, the pipeline logs error and falls back to local model."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    registry.should_fail = True
    local = MockModelClient(text="Local model fallback response", tokens=5)
    remote = MockModelClient()
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="solver: crashing math",
        task_id="task_130_vwx",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    assert response.route_taken == "local_llm"
    assert response.final_response == "Local model fallback response"


@pytest.mark.asyncio
async def test_unhandled_system_exception(temp_telemetry_file: str) -> None:
    """Verify that unhandled raw python exceptions on both local and remote are wrapped and escalated."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    async def generate_crash(prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        raise ValueError("General Python error")
    local.generate_async = generate_crash
    
    remote = MockModelClient()
    remote.generate_async = generate_crash
    
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="crashing prompt",
        task_id="task_131_yz1",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    with pytest.raises(TERABaseException) as excinfo:
        await orchestrator.process_request_async(request)
        
    assert "Unhandled pipeline error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_local_unhandled_system_exception_fallback(temp_telemetry_file: str) -> None:
    """Verify that unhandled raw python exceptions on local are isolated and remote fallback resolves it."""
    cache = MockSemanticCache()
    parser = MockIntentParser()
    registry = MockSolverRegistry()
    local = MockModelClient()
    async def generate_crash(prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        raise ValueError("General Python error")
    local.generate_async = generate_crash
    
    remote = MockModelClient(text="Remote success after local crash", tokens=6)
    rovl = MockROVL()
    settings = MockSettings(temp_telemetry_file)

    orchestrator = TERAOrchestrator(cache, parser, registry, local, remote, rovl, settings)
    
    request = InferenceRequest(
        prompt="crashing prompt",
        task_id="task_131_yz2",
        c2=1.0,
        c3=10.0,
        lambda_coeff=0.5,
        alpha_dense=0.8
    )

    response = await orchestrator.process_request_async(request)
    assert response.route_taken == "remote_fallback"
    assert response.final_response == "Remote success after local crash"
    assert response.tokens_consumed == 6
