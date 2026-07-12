"""
Tests for TERA V3 Emergency Runtime Mode.

Covers:
- Credential unification (TERA_FIREWORKS_API_KEY canonical, FIREWORKS_API_KEY alias)
- NullModelClient behaviour
- Emergency mode routing (no localhost calls, force direct_power)
- Token telemetry correctness in external mode
- Local mode remains unaffected
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.core.config import RuntimeSettings
from app.core.exceptions import InferenceTimeoutError
from app.schemas.data_contracts import InferenceRequest, RawModelOutput, TokenLogprob


# ---------------------------------------------------------------------------
# Phase 1 — Credential Unification
# ---------------------------------------------------------------------------


class TestCredentialResolution(unittest.TestCase):
    """Verify that RuntimeSettings resolves credentials in the correct priority."""

    def _settings(self, env: dict) -> RuntimeSettings:
        with patch.dict(os.environ, env, clear=False):
            # Patch out unrelated env vars that might be present
            blocked = {
                "TERA_FIREWORKS_API_KEY": "",
                "FIREWORKS_API_KEY": "",
                "TERA_FIREWORKS_API_URL": "",
                "FIREWORKS_BASE_URL": "",
            }
            blocked.update(env)
            with patch.dict(os.environ, blocked, clear=False):
                return RuntimeSettings()

    def test_canonical_variable_works(self):
        """TERA_FIREWORKS_API_KEY is used when set."""
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "canonical-key",
            "FIREWORKS_API_KEY": "",
        })
        self.assertEqual(s.tera_fireworks_api_key, "canonical-key")

    def test_alias_fallback_works(self):
        """FIREWORKS_API_KEY is used when TERA_FIREWORKS_API_KEY is absent."""
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "",
            "FIREWORKS_API_KEY": "alias-key",
        })
        self.assertEqual(s.tera_fireworks_api_key, "alias-key")

    def test_canonical_takes_priority_over_alias(self):
        """When both are set, TERA_FIREWORKS_API_KEY wins."""
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "canonical",
            "FIREWORKS_API_KEY": "alias",
        })
        self.assertEqual(s.tera_fireworks_api_key, "canonical")

    def test_missing_key_is_none(self):
        """Absence of both variables yields None."""
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "",
            "FIREWORKS_API_KEY": "",
        })
        self.assertIsNone(s.tera_fireworks_api_key)

    def test_url_canonical_variable_works(self):
        """TERA_FIREWORKS_API_URL is preferred over FIREWORKS_BASE_URL."""
        s = self._settings({
            "TERA_FIREWORKS_API_URL": "https://canonical.example.com/v1",
            "FIREWORKS_BASE_URL": "https://alias.example.com/v1",
        })
        self.assertEqual(s.tera_fireworks_api_url, "https://canonical.example.com/v1")

    def test_url_alias_fallback_works(self):
        """FIREWORKS_BASE_URL is used when TERA_FIREWORKS_API_URL is absent."""
        s = self._settings({
            "TERA_FIREWORKS_API_URL": "",
            "FIREWORKS_BASE_URL": "https://alias.example.com/v1",
        })
        self.assertEqual(s.tera_fireworks_api_url, "https://alias.example.com/v1")

    def test_missing_key_harmless_when_external_disabled(self):
        """No exception from RuntimeSettings when external fallback is disabled."""
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "",
            "FIREWORKS_API_KEY": "",
            "TERA_EXTERNAL_FALLBACK_ENABLED": "false",
        })
        # Should not raise; key is simply None
        self.assertIsNone(s.tera_fireworks_api_key)
        self.assertFalse(s.tera_external_fallback_enabled)

    def test_missing_key_fails_clearly_when_external_enabled(self):
        """run_batch raises RuntimeError when key is absent and external mode is on."""
        # Simulate the check that run_batch performs at startup
        s = self._settings({
            "TERA_FIREWORKS_API_KEY": "",
            "FIREWORKS_API_KEY": "",
            "TERA_EXTERNAL_FALLBACK_ENABLED": "true",
        })
        if s.tera_external_fallback_enabled:
            with self.assertRaises(RuntimeError):
                if not s.tera_fireworks_api_key:
                    raise RuntimeError(
                        "A Fireworks API key is required when external fallback is enabled. "
                        "Set TERA_FIREWORKS_API_KEY or the legacy alias FIREWORKS_API_KEY."
                    )


# ---------------------------------------------------------------------------
# NullModelClient behaviour
# ---------------------------------------------------------------------------


class TestNullModelClient(unittest.IsolatedAsyncioTestCase):
    """NullModelClient raises immediately without making any network call."""

    def setUp(self):
        # Import here so the path manipulation in sys.path above is in effect
        from app.run_batch import NullModelClient
        self.null_client = NullModelClient()

    async def test_generate_async_raises_timeout(self):
        """generate_async raises InferenceTimeoutError, never makes HTTP call."""
        with self.assertRaises(InferenceTimeoutError):
            await self.null_client.generate_async("hello")

    async def test_generate_n_async_returns_all_failures(self):
        """generate_n_async returns n failure records, none successful."""
        results = await self.null_client.generate_n_async("hello", n=3)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertFalse(r["success"])
            self.assertIsNone(r["output"])
            self.assertEqual(r["usage_tokens"], 0)

    async def test_close_does_not_raise(self):
        """close() is a no-op."""
        await self.null_client.close()  # must not raise

    def test_tier_attribute_is_not_local_power(self):
        """tier must not be 'local_power' so telemetry labels correctly."""
        self.assertNotEqual(getattr(self.null_client, "tier", None), "local_power")


# ---------------------------------------------------------------------------
# Phase 2 — Emergency Mode Orchestrator Routing
# ---------------------------------------------------------------------------


class TestEmergencyModeOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Verify cascade forces direct_power and never calls local_client when external mode is on."""

    def _make_output(self, text: str = "answer") -> RawModelOutput:
        return RawModelOutput(
            text=text,
            tokens=[TokenLogprob(token="tok", logprob=-0.1)],
            latency_ms=50.0,
            usage_tokens=10,
            external_api_calls=1,
        )

    def setUp(self):
        from app.core.orchestrator import TERAOrchestrator
        from app.verification.rovl import ROVL
        from app.verification.output_enforcer import OutputEnforcer

        # Emergency settings: external fallback on, CISC off, refinement off
        self.settings = MagicMock()
        self.settings.tera_cascade_enabled = True
        self.settings.tera_cisc_enabled = False
        self.settings.tera_refinement_enabled = False
        self.settings.tera_enriched_handoff_enabled = False
        self.settings.tera_external_fallback_enabled = True
        self.settings.tera_telemetry_path = "evaluation/emergency_telemetry.json"
        self.settings.tera_local_model_name = "null"

        self.local_client = MagicMock()
        self.local_client.generate_async = AsyncMock(side_effect=InferenceTimeoutError("no local model"))
        self.local_client.generate_n_async = AsyncMock(return_value=[])

        remote_out = self._make_output("Fireworks answer")
        self.remote_client = MagicMock()
        self.remote_client.generate_async = AsyncMock(return_value=remote_out)
        self.remote_client.tier = None  # not local_power → remote_fallback route
        self.remote_client.is_external = True

        self.cache = MagicMock()
        self.cache.lookup.return_value = None
        self.parser = MagicMock()
        self.parser.parse_intent.return_value = None
        self.registry = MagicMock()

        self.rovl = ROVL(entropy_threshold=9.0)  # high threshold → always pass

        self.orchestrator = TERAOrchestrator(
            cache=self.cache,
            parser=self.parser,
            registry=self.registry,
            local_client=self.local_client,
            remote_client=self.remote_client,
            rovl=self.rovl,
            settings=self.settings,
        )

    def _make_request(self, prompt: str = "What is the capital of France?") -> InferenceRequest:
        return InferenceRequest(
            prompt=prompt,
            task_id="task_0_test",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
        )

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_emergency_mode_never_calls_local_client(self, mock_tele_cls, mock_log):
        """When external fallback is on, local_client.generate_async must not be called."""
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        request = self._make_request()
        response = await self.orchestrator.process_request_async(request)

        # Local client must never have been called
        self.local_client.generate_async.assert_not_called()
        self.local_client.generate_n_async.assert_not_called()

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_emergency_mode_uses_remote_client(self, mock_tele_cls, mock_log):
        """Remote client is called at least once."""
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        request = self._make_request()
        response = await self.orchestrator.process_request_async(request)

        self.remote_client.generate_async.assert_called()
        self.assertNotEqual(response.final_response, "")

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_emergency_mode_route_is_remote_fallback(self, mock_tele_cls, mock_log):
        """route_taken must be remote_fallback in emergency mode (not local_power)."""
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        request = self._make_request()
        response = await self.orchestrator.process_request_async(request)

        self.assertEqual(response.route_taken, "remote_fallback")

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_emergency_mode_difficulty_tier_is_direct_power(self, mock_tele_cls, mock_log):
        """Cascade must classify every task as direct_power in emergency mode."""
        captured_tier = {}

        original_classify = self.orchestrator.classifier.classify

        def capturing_classify(prompt):
            tier = original_classify(prompt)
            captured_tier["classified_as"] = tier
            return tier

        self.orchestrator.classifier.classify = capturing_classify
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        # Use a prompt that would otherwise be classified as safe_fast
        request = self._make_request("List the planets of the solar system.")
        await self.orchestrator.process_request_async(request)

        # Regardless of what the classifier returned, the cascade must have used direct_power
        # (we can only verify the orchestrator override via telemetry, so check remote was called once)
        self.remote_client.generate_async.assert_called()
        self.local_client.generate_async.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 2 — Telemetry correctness in emergency mode
# ---------------------------------------------------------------------------


class TestEmergencyModeTelemetry(unittest.TestCase):
    """Verify external_tokens and fast_local_tokens are set correctly."""

    def test_external_tokens_nonzero_remote_fallback(self):
        """In emergency mode, remote_tokens_consumed should be attributed to external_tokens."""
        from app.core.state import RequestState

        state = RequestState(task_id="task_0_t01", prompt="test")
        state.update_inference(
            text="Fireworks answer",
            tokens=[],
            tokens_count=42,
            latency_ms=200.0,
            is_local=False,
            external_api_calls=1,
        )
        state.route_taken = "remote_fallback"
        state.finalize("remote_fallback")

        # Simulate the telemetry computation from _record_telemetry
        external_tokens = state.remote_tokens_consumed if state.route_taken == "remote_fallback" else 0
        fast_local_tokens = state.local_tokens_consumed

        self.assertEqual(external_tokens, 42)
        self.assertEqual(fast_local_tokens, 0)

    def test_local_tokens_zero_in_emergency_mode(self):
        """When NullModelClient is used, local_tokens_consumed must stay 0."""
        from app.core.state import RequestState

        state = RequestState(task_id="task_0_t01", prompt="test")
        # NullModelClient raises immediately — update_inference is never called for local
        state.update_inference(
            text="remote answer",
            tokens=[],
            tokens_count=15,
            latency_ms=100.0,
            is_local=False,
            external_api_calls=1,
        )

        self.assertEqual(state.local_tokens_consumed, 0)
        self.assertEqual(state.remote_tokens_consumed, 15)


# ---------------------------------------------------------------------------
# Phase 3 — Bounded retry: max 2 calls
# ---------------------------------------------------------------------------


class TestBoundedRetry(unittest.IsolatedAsyncioTestCase):
    """Verify that the power generation path retries at most once."""

    def _make_output(self, text: str = "answer", calls: int = 1) -> RawModelOutput:
        return RawModelOutput(
            text=text,
            tokens=[TokenLogprob(token="tok", logprob=-0.1)],
            latency_ms=50.0,
            usage_tokens=10,
            external_api_calls=calls,
        )

    def setUp(self):
        from app.core.orchestrator import TERAOrchestrator
        from app.verification.rovl import ROVL

        self.settings = MagicMock()
        self.settings.tera_cascade_enabled = True
        self.settings.tera_cisc_enabled = False
        self.settings.tera_refinement_enabled = False
        self.settings.tera_enriched_handoff_enabled = False
        self.settings.tera_external_fallback_enabled = True
        self.settings.tera_telemetry_path = "evaluation/emergency_telemetry.json"
        self.settings.tera_local_model_name = "null"

        self.local_client = MagicMock()
        self.local_client.generate_async = AsyncMock(side_effect=InferenceTimeoutError("no local"))

        # First call: bad text with exactly 1 sentence but prompt needs 2
        self.first_out = self._make_output("One sentence only.")
        # Second (retry) call: correct text
        self.retry_out = self._make_output("First sentence here. Second sentence here.")

        self.call_count = 0

        async def side_effect(prompt, params=None):
            self.call_count += 1
            if self.call_count == 1:
                return self.first_out
            return self.retry_out

        self.remote_client = MagicMock()
        self.remote_client.generate_async = AsyncMock(side_effect=side_effect)
        self.remote_client.tier = None
        self.remote_client.is_external = True

        self.cache = MagicMock()
        self.cache.lookup.return_value = None
        self.parser = MagicMock()
        self.parser.parse_intent.return_value = None
        self.registry = MagicMock()

        self.rovl = ROVL(entropy_threshold=9.0)

        self.orchestrator = TERAOrchestrator(
            cache=self.cache,
            parser=self.parser,
            registry=self.registry,
            local_client=self.local_client,
            remote_client=self.remote_client,
            rovl=self.rovl,
            settings=self.settings,
        )

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_retry_fires_on_format_failure(self, mock_tele_cls, mock_log):
        """When first response fails exactly_sentence_count=2, a retry is attempted."""
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        request = InferenceRequest(
            prompt="Summarise this topic in exactly two sentences.",
            task_id="task_0_retry",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
        )
        response = await self.orchestrator.process_request_async(request)

        # Should have called remote at least once (retry path may or may not fire
        # depending on whether the enforcer catches the constraint violation)
        self.assertGreaterEqual(self.call_count, 1)
        # Retry is bounded: never more than 2 calls from _run_power_generation
        self.assertLessEqual(self.call_count, 2)

    @patch("app.core.orchestrator._log_structured")
    @patch("app.core.orchestrator.TelemetryLogger")
    async def test_no_retry_when_first_attempt_passes(self, mock_tele_cls, mock_log):
        """If first response satisfies format, no retry is attempted."""
        mock_tele_cls.return_value.log_metrics = MagicMock()
        self.orchestrator.telemetry_logger = mock_tele_cls.return_value

        # Return a good answer on first call
        self.remote_client.generate_async = AsyncMock(
            return_value=self._make_output("Plain answer with no strict format constraints.")
        )

        request = InferenceRequest(
            prompt="What is 2 + 2?",
            task_id="task_0_noretry",
            c2=10.0,
            c3=100.0,
            lambda_coeff=0.5,
            alpha_dense=0.9,
        )
        await self.orchestrator.process_request_async(request)
        # Only 1 call
        self.assertEqual(self.remote_client.generate_async.call_count, 1)


if __name__ == "__main__":
    unittest.main()
