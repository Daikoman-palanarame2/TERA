import unittest
import sys
import os
import asyncio
import httpx
import time
from unittest.mock import patch, MagicMock

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.settings import settings
from app.router.runtime_router import RuntimeRouter
from app.verification.verification_types import SchemaType, VerificationStatus, FailureReason
from app.verification.rovl import ROVL
from app.inference.inference_types import InferenceRequest, InferenceResponse, ModelOutput
from app.inference.orchestrator import InferenceOrchestrator
from app.inference.cheap_model import CheapModel
from app.inference.dense_model import DenseModel
from app.inference.fireworks_model import FireworksModel
from app.inference.model_interface import ModelInterface

class TestAsyncTransition(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/app/models"))
        self.router = RuntimeRouter(self.models_dir)
        self.rovl = ROVL(entropy_threshold=settings.entropy_threshold, stop_sequences=["\n"])

    async def test_sync_async_equivalence(self):
        """
        Verifies that run() and run_async() produce identical routing decisions,
        utility calculations, escalation decisions, and final output payloads.
        """
        cheap_model = CheapModel()
        dense_model = DenseModel()
        orchestrator = InferenceOrchestrator(self.router, cheap_model, dense_model, self.rovl)

        request = InferenceRequest(
            prompt="solve: x + 2 = 5",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
            schema_type=SchemaType.NONE
        )

        # 1. Run Synchronously
        sync_res = orchestrator.run(request)

        # 2. Run Asynchronously
        async_res = await orchestrator.run_async(request)

        # 3. Assert Equivalence
        self.assertEqual(sync_res.final_response, async_res.final_response)
        self.assertEqual(sync_res.selected_route, async_res.selected_route)
        self.assertEqual(sync_res.escalated, async_res.escalated)
        self.assertEqual(sync_res.metadata["router_probability"], async_res.metadata["router_probability"])
        self.assertEqual(sync_res.metadata["cheap_utility"], async_res.metadata["cheap_utility"])
        self.assertEqual(sync_res.metadata["dense_utility"], async_res.metadata["dense_utility"])
        self.assertEqual(sync_res.metadata["cascade_utility"], async_res.metadata["cascade_utility"])

    @patch("httpx.AsyncClient.post")
    async def test_fireworks_model_retry_success_on_retry(self, mock_post):
        """
        Verifies that if the first request fails with HTTP 429, the client retries
        exactly once and succeeds if the second request returns status 200.
        """
        # Mock initial rate limit failure (429) then successful response
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

        # First call fails, second succeeds
        mock_post.side_effect = [mock_response_fail, mock_response_success]

        client = FireworksModel(model_name="test-model", api_key="dummy-key", base_url="https://api.example.com")
        
        # Patch sleep to avoid delay during testing
        with patch("asyncio.sleep", return_value=None) as mock_sleep:
            output = await client.generate_async("hello")
            
            self.assertEqual(output.text, "Success response after retry")
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_called_once()

    @patch("httpx.AsyncClient.post")
    async def test_fireworks_model_retry_exhaustion_raises(self, mock_post):
        """
        Verifies that if both attempts fail with HTTP 503, the client raises
        the exception and does not attempt a third request (max ONE retry).
        """
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

    async def test_cheap_model_failure_isolation_and_escalation(self):
        """
        Verifies that if the cheap model throws a connection/network exception,
        the orchestrator run_async catches it, logs a warning, and escalates
        to the dense model successfully instead of crashing.
        """
        # Set up a cheap model that always crashes
        bad_cheap = MagicMock(spec=ModelInterface)
        bad_cheap.generate_async.side_effect = httpx.ConnectError("Connection refused")
        
        # Dense model works fine
        good_dense = DenseModel(default_text="Dense recovery response")
        
        orchestrator = InferenceOrchestrator(self.router, bad_cheap, good_dense, self.rovl)
        
        request = InferenceRequest(
            prompt="solve: x + 2 = 5",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
            schema_type=SchemaType.NONE
        )
        
        # Run orchestrator
        response = await orchestrator.run_async(request)
        
        # Verify it escalated and returned dense model output
        self.assertEqual(response.final_response, "Dense recovery response")
        self.assertTrue(response.escalated)
        self.assertIn("cheap_model_failure", response.metadata["escalation_reason"])

    async def test_bounded_concurrency_semaphore(self):
        """
        Stress test verifying that concurrency is successfully bounded by a semaphore
        when processing multiple concurrent requests.
        """
        sem = asyncio.Semaphore(2)
        active_requests = 0
        max_seen_concurrency = 0

        async def worker():
            nonlocal active_requests, max_seen_concurrency
            async with sem:
                active_requests += 1
                max_seen_concurrency = max(max_seen_concurrency, active_requests)
                # Sleep to simulate network delay
                await asyncio.sleep(0.01)
                active_requests -= 1

        # Run 10 workers concurrently
        await asyncio.gather(*(worker() for _ in range(10)))
        
        # Max concurrency seen should be exactly 2
        self.assertEqual(max_seen_concurrency, 2)

if __name__ == "__main__":
    unittest.main()
