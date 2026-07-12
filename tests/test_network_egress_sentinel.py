import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from urllib.parse import urlparse
import httpx

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.exceptions import ConfigurationError, InferenceTimeoutError
from app.inference.local_power_client import LocalPowerModelClient
from app.inference.local_client import LocalModelClient
from app.schemas.data_contracts import InferenceRequest, RawModelOutput
from app.core.orchestrator import TERAOrchestrator

# Global hook for httpx.AsyncClient.send to enforce zero-egress loopback checks
orig_send = httpx.AsyncClient.send

async def strict_loopback_send(self, request, *args, **kwargs):
    url = str(request.url)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    host_clean = host.strip("[]")
    
    allowed_hosts = {"127.0.0.1", "localhost", "::1", "[::1]"}
    if host_clean not in allowed_hosts:
        raise AssertionError(f"NETWORK EGRESS BLOCKED: Attempted to contact non-loopback host '{host}' via URL '{url}'")
        
    return await orig_send(self, request, *args, **kwargs)


class TestNetworkEgressSentinel(unittest.TestCase):
    def setUp(self):
        # Apply the egress interceptor patch
        self.patcher = patch.object(httpx.AsyncClient, "send", strict_loopback_send)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_egress_sentinel_blocks_external_host(self):
        client = httpx.AsyncClient()
        
        async def run_req(url):
            try:
                await client.get(url)
            except AssertionError as e:
                return str(e)
            return "passed"

        res_external = asyncio.run(run_req("https://api.fireworks.ai/inference/v1"))
        self.assertIn("NETWORK EGRESS BLOCKED", res_external)
        
        # Verify spoofing attempts are caught
        res_spoof = asyncio.run(run_req("http://localhost.evil.example/v1"))
        self.assertIn("NETWORK EGRESS BLOCKED", res_spoof)

    def test_power_client_rejects_fireworks_domains(self):
        with self.assertRaises(ConfigurationError):
            LocalPowerModelClient("https://api.fireworks.ai/inference/v1", "Qwen/Qwen2.5-14B-Instruct")
            
        with self.assertRaises(ConfigurationError):
            LocalPowerModelClient("https://some-subdomain.fireworks.ai/v1", "Qwen/Qwen2.5-14B-Instruct")

    @patch("app.utils.telemetry.TelemetryLogger.log_metrics")
    @patch("app.cache.semantic_cache.SemanticCache")
    @patch("app.inference.local_client.LocalModelClient.generate_async")
    @patch("app.inference.local_power_client.LocalPowerModelClient.generate_async")
    def test_orchestrator_fallback_to_power_is_loopback_only(self, mock_power_gen, mock_local_gen, mock_cache, mock_log_metrics):
        # 1. Setup mock cheap client to fail/timeout
        mock_local_gen.side_effect = InferenceTimeoutError("Cheap local model timed out.")
        
        # 2. Setup mock power client to succeed
        mock_power_gen.return_value = RawModelOutput(
            text="Factual reasoning result",
            tokens=[],
            latency_ms=150.0,
            usage_tokens=25,
            external_api_calls=0
        )
        
        # Setup mocks for constructor dependencies
        mock_cache = MagicMock()
        mock_cache.lookup.return_value = None
        mock_parser = MagicMock()
        mock_parser.parse_intent.return_value = None
        mock_registry = MagicMock()
        mock_registry.execute.side_effect = Exception("No solver matched")
        
        from app.schemas.data_contracts import VerificationResult
        mock_rovl = MagicMock()
        mock_rovl.verify.return_value = VerificationResult(
            passed=True,
            average_surprisal=0.0,
            sequence_entropy=0.0,
            failed_validators=[]
        )
        
        mock_settings = MagicMock()
        mock_settings.tera_telemetry_path = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "test_telemetry.json")
        mock_settings.tera_local_model_name = "cheap-model"
        mock_settings.tera_external_fallback_enabled = False
        
        # Initialize orchestrator
        orchestrator = TERAOrchestrator(
            cache=mock_cache,
            parser=mock_parser,
            registry=mock_registry,
            local_client=LocalModelClient("http://127.0.0.1:8000/v1", "cheap-model"),
            remote_client=LocalPowerModelClient("http://127.0.0.1:8001/v1", "power-model"),
            rovl=mock_rovl,
            settings=mock_settings
        )
        
        # Build request that fails localcheap and escalates to localpower
        req = InferenceRequest(
            prompt="Evaluate formula.",
            task_id="task_1_abc123",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.1,  # Low lambda favors power tier escalation
            alpha_dense=0.99
        )
        
        res = asyncio.run(orchestrator.process_request_async(req))
        
        # Assert route taken is local_power, not remote_fallback
        self.assertEqual(res.route_taken, "local_power")
        self.assertEqual(res.final_response, "Factual reasoning result")

if __name__ == "__main__":
    unittest.main()
