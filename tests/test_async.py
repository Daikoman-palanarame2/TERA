import unittest
import sys
import os
import asyncio
import httpx
import tempfile
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.config import settings
from app.verification.rovl import ROVL
from app.schemas.data_contracts import InferenceRequest, RawModelOutput, TokenLogprob, TelemetryLog
from app.inference.fireworks_model import FireworksModel
from app.inference.model_interface import ModelInterface
from app.core.orchestrator import TERAOrchestrator
from app.cache.semantic_cache import SemanticCache
from app.solvers.solver_registry import SolverRegistry
from app.parser.intent_parser import IntentParser


class MockSemanticCache:
    def lookup(self, prompt: str, threshold: float = 0.95) -> Any:
        return None
    def insert(self, prompt: str, response: str) -> None:
        pass


class MockModelClient(ModelInterface):
    def __init__(self, text: str = "Mock output", tokens: int = 5) -> None:
        self.text = text
        self.tokens = tokens

    async def generate_async(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> RawModelOutput:
        return RawModelOutput(
            text=self.text,
            tokens=[TokenLogprob(token="test", logprob=-0.1)],
            latency_ms=10.0,
            usage_tokens=self.tokens
        )


class MockSettings:
    def __init__(self, telemetry_path: str) -> None:
        self.tera_telemetry_path = telemetry_path


class TestAsyncTransition(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.telemetry_path = os.path.join(self.temp_dir.name, "telemetry.json")
        self.settings = MockSettings(self.telemetry_path)
        self.rovl = ROVL(entropy_threshold=3.0)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("httpx.AsyncClient.post")
    async def test_fireworks_model_retry_success_on_retry(self, mock_post: MagicMock) -> None:
        """Verifies that if the first request fails with HTTP 429, the client retries exactly once."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 429
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Too Many Requests",
            request=MagicMock(),
            response=mock_response_fail
        )

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Success response after retry"},
                    "finish_reason": "stop",
                    "logprobs": {"content": [{"token": "ok", "logprob": -0.01}]}
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10}
        }

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        client = FireworksModel(model_name="test-model", api_key="dummy-key", base_url="https://api.example.com")
        
        with patch("asyncio.sleep", return_value=None) as mock_sleep:
            output = await client.generate_async("hello")
            self.assertEqual(output.text, "Success response after retry")
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_fireworks_model_retry_exhaustion_raises(self, mock_post: MagicMock) -> None:
        """Verifies that if both attempts fail with HTTP 503, the client raises the exception."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Service Unavailable",
            request=MagicMock(),
            response=mock_response
        )

        mock_post.side_effect = [mock_response, mock_response]

        client = FireworksModel(model_name="test-model", api_key="dummy-key", base_url="https://api.example.com")

        with patch("asyncio.sleep", return_value=None):
            with self.assertRaises(httpx.HTTPStatusError):
                await client.generate_async("hello")
                
            self.assertEqual(mock_post.call_count, 2)

    async def test_cheap_model_failure_isolation_and_escalation(self) -> None:
        """Verifies that if the cheap model throws an exception, TERAOrchestrator escalates to remote fallback."""
        cache = MockSemanticCache()  # type: ignore
        registry = SolverRegistry()
        registry.lock()
        parser = IntentParser(registry)
        
        bad_cheap = MagicMock(spec=ModelInterface)
        bad_cheap.generate_async.side_effect = httpx.ConnectError("Connection refused")
        
        good_remote = MockModelClient(text="Remote recovery response", tokens=5)
        
        orchestrator = TERAOrchestrator(
            cache=cache,  # type: ignore
            parser=parser,
            registry=registry,
            local_client=bad_cheap,
            remote_client=good_remote,
            rovl=self.rovl,
            settings=self.settings
        )
        
        request = InferenceRequest(
            prompt="solve: x + 2 = 5",
            task_id="task_0_recovery",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
            schema_type="none"
        )
        
        response = await orchestrator.process_request_async(request)
        
        self.assertEqual(response.final_response, "Remote recovery response")
        self.assertEqual(response.route_taken, "remote_fallback")
        self.assertEqual(response.tokens_consumed, 5)

    async def test_bounded_concurrency_semaphore(self) -> None:
        """Stress test verifying that concurrency is successfully bounded by a semaphore."""
        sem = asyncio.Semaphore(2)
        active_requests = 0
        max_seen_concurrency = 0

        async def worker() -> None:
            nonlocal active_requests, max_seen_concurrency
            async with sem:
                active_requests += 1
                max_seen_concurrency = max(max_seen_concurrency, active_requests)
                await asyncio.sleep(0.01)
                active_requests -= 1

        await asyncio.gather(*(worker() for _ in range(10)))
        self.assertEqual(max_seen_concurrency, 2)


if __name__ == "__main__":
    unittest.main()
