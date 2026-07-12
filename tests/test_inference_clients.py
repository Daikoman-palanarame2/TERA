"""
Module: tests/test_inference_clients
Purpose:
    Unit tests for LocalModelClient and RemoteModelClient covering success,
    timeouts, failures, retries, legacy payload formats, and lifecycle events.
"""

import unittest
import sys
import os
import httpx
from typing import Any
from unittest.mock import patch, MagicMock

# Add backend directory to path to allow imports from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.inference.local_client import LocalModelClient
from app.inference.remote_client import RemoteModelClient
from app.core.exceptions import InferenceTimeoutError, ConfigurationError
from app.schemas.data_contracts import RawModelOutput


class TestLocalModelClient(unittest.IsolatedAsyncioTestCase):

    @patch("httpx.AsyncClient.post")
    async def test_successful_response(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Local completion output"},
                    "logprobs": {
                        "content": [
                            {"token": "Local", "logprob": -0.15},
                            {"token": " completion", "logprob": -0.05}
                        ]
                    }
                }
            ],
            "usage": {"total_tokens": 10}
        }
        mock_post.return_value = mock_response

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt text", params={"task_id": "task_1_abc"})

        self.assertIsInstance(output, RawModelOutput)
        self.assertEqual(output.text, "Local completion output")
        self.assertEqual(len(output.tokens), 2)
        self.assertEqual(output.tokens[0].token, "Local")
        self.assertEqual(output.tokens[0].logprob, -0.15)
        self.assertEqual(output.usage_tokens, 10)
        self.assertGreater(output.latency_ms, 0.0)

    @patch("httpx.AsyncClient.post")
    async def test_timeout(self, mock_post: Any) -> None:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt text", params={})
        self.assertIn("Request timed out", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_malformed_json(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        # When json() raises exception
        mock_response.json.side_effect = ValueError("Decoding failed")

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt text", params={})
        self.assertIn("Malformed local model response", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_connection_refused(self, mock_post: Any) -> None:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt text", params={})
        self.assertIn("Connection refused", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_missing_logprobs(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "No logprobs here"}
                }
            ],
            "usage": {}
        }
        mock_post.return_value = mock_response

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt text", params={})

        self.assertEqual(output.text, "No logprobs here")
        self.assertEqual(output.tokens, [])
        self.assertEqual(output.usage_tokens, 4)

    @patch("httpx.AsyncClient.post")
    @patch("asyncio.sleep", return_value=None)
    async def test_retry_behavior(self, mock_sleep: Any, mock_post: Any) -> None:
        mock_response_fail = MagicMock(spec=httpx.Response)
        mock_response_fail.status_code = 503
        mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=mock_response_fail
        )

        mock_response_success = MagicMock(spec=httpx.Response)
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Success after failure"}}],
            "usage": {"total_tokens": 5}
        }

        mock_post.side_effect = [mock_response_fail, mock_response_success]

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt text", params={})

        self.assertEqual(output.text, "Success after failure")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once()

    async def test_local_client_context_manager(self) -> None:
        async with LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen") as client:
            self.assertEqual(client.model_name, "local-qwen")

    def test_local_client_init_validation(self) -> None:
        with self.assertRaises(ConfigurationError):
            LocalModelClient(endpoint_url="", model_name="model")
        with self.assertRaises(ConfigurationError):
            LocalModelClient(endpoint_url="http://url", model_name="")
        with self.assertRaises(ConfigurationError):
            LocalModelClient(endpoint_url="http://url", model_name="model", timeout_sec=-1.0)

    @patch("httpx.AsyncClient.post")
    async def test_local_client_legacy_logprobs_format(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "text": "Legacy output text",
                    "logprobs": {
                        "tokens": ["Legacy", " output"],
                        "token_logprobs": [-0.5, -0.1]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4
            }
        }
        mock_post.return_value = mock_response

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt", params={})
        self.assertEqual(output.text, "Legacy output text")
        self.assertEqual(len(output.tokens), 2)
        self.assertEqual(output.tokens[0].token, "Legacy")
        self.assertEqual(output.tokens[0].logprob, -0.5)
        self.assertEqual(output.usage_tokens, 7)

    @patch("httpx.AsyncClient.post")
    async def test_local_client_forbidden_raises_configuration_error(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(ConfigurationError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("Access forbidden", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_local_client_generic_exception_retry(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Retry success"}}]
        }
        mock_post.side_effect = [Exception("Unexpected system failure"), mock_response]

        client = LocalModelClient(endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt", params={})
        self.assertEqual(output.text, "Retry success")
        self.assertEqual(mock_post.call_count, 2)


class TestRemoteModelClient(unittest.IsolatedAsyncioTestCase):

    @patch("httpx.AsyncClient.post")
    async def test_success(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {"content": "Remote output text"},
                    "logprobs": {
                        "content": [
                            {"token": "Remote", "logprob": -0.22}
                        ]
                    }
                }
            ],
            "usage": {"total_tokens": 15}
        }
        mock_post.return_value = mock_response

        client = RemoteModelClient(
            api_key="fw_test_key_12345678901234567890",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=2
        )
        # Use parameters to cover formatting logic
        output = await client.generate_async("prompt text", params={"task_id": "remote_task_1", "temperature": 0.5})

        self.assertIsInstance(output, RawModelOutput)
        self.assertEqual(output.text, "Remote output text")
        self.assertEqual(len(output.tokens), 1)
        self.assertEqual(output.tokens[0].token, "Remote")
        self.assertEqual(output.usage_tokens, 15)

    @patch("httpx.AsyncClient.post")
    async def test_authentication_failure(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        client = RemoteModelClient(
            api_key="invalid_key",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=3
        )

        with self.assertRaises(ConfigurationError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("Remote authentication failed", str(context.exception))
        self.assertEqual(mock_post.call_count, 1)

    @patch("httpx.AsyncClient.post")
    @patch("asyncio.sleep", return_value=None)
    async def test_rate_limiting_retries(self, mock_sleep: Any, mock_post: Any) -> None:
        mock_response_429 = MagicMock(spec=httpx.Response)
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limit Exceeded", request=MagicMock(), response=mock_response_429
        )

        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "Success after rate limiting"}}],
            "usage": {"total_tokens": 4}
        }

        mock_post.side_effect = [mock_response_429, mock_response_200]

        client = RemoteModelClient(
            api_key="fw_test_key_12345678901234567890",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=3
        )
        output = await client.generate_async("prompt", params={})

        self.assertEqual(output.text, "Success after rate limiting")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("httpx.AsyncClient.post")
    @patch("asyncio.sleep", return_value=None)
    async def test_timeout_retries(self, mock_sleep: Any, mock_post: Any) -> None:
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        client = RemoteModelClient(
            api_key="fw_test_key_12345678901234567890",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=2
        )

        with self.assertRaises(InferenceTimeoutError):
            await client.generate_async("prompt", params={})
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("httpx.AsyncClient.post")
    @patch("asyncio.sleep", return_value=None)
    async def test_retry_exhaustion(self, mock_sleep: Any, mock_post: Any) -> None:
        mock_response_500 = MagicMock(spec=httpx.Response)
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=mock_response_500
        )

        mock_post.side_effect = [mock_response_500] * 4

        client = RemoteModelClient(
            api_key="fw_test_key_12345678901234567890",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=3
        )

        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("Remote client failed after 4 attempts", str(context.exception))
        self.assertEqual(mock_post.call_count, 4)

    @patch("httpx.AsyncClient.post")
    async def test_malformed_payload_raises_immediately(self, mock_post: Any) -> None:
        mock_response_400 = MagicMock(spec=httpx.Response)
        mock_response_400.status_code = 400
        mock_post.return_value = mock_response_400

        client = RemoteModelClient(
            api_key="fw_test_key_12345678901234567890",
            endpoint_url="https://api.example.com/v1",
            model_name="remote-deepseek",
            max_retries=3
        )

        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("terminal status 400", str(context.exception))
        self.assertEqual(mock_post.call_count, 1)

    async def test_remote_client_context_manager(self) -> None:
        async with RemoteModelClient(api_key="key", endpoint_url="http://url", model_name="model") as client:
            self.assertEqual(client.model_name, "model")

    def test_remote_client_init_validation(self) -> None:
        with self.assertRaises(ConfigurationError):
            RemoteModelClient(api_key="", endpoint_url="http://url", model_name="model")
        with self.assertRaises(ConfigurationError):
            RemoteModelClient(api_key="key", endpoint_url="", model_name="model")
        with self.assertRaises(ConfigurationError):
            RemoteModelClient(api_key="key", endpoint_url="http://url", model_name="")
        with self.assertRaises(ConfigurationError):
            RemoteModelClient(api_key="key", endpoint_url="http://url", model_name="model", max_retries=-1)

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_legacy_logprobs_format(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "text": "Legacy output text",
                    "logprobs": {
                        "tokens": ["Legacy", " output"],
                        "token_logprobs": [-0.5, -0.1]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4
            }
        }
        mock_post.return_value = mock_response

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt", params={})
        self.assertEqual(output.text, "Legacy output text")
        self.assertEqual(len(output.tokens), 2)
        self.assertEqual(output.tokens[0].token, "Legacy")
        self.assertEqual(output.tokens[0].logprob, -0.5)
        self.assertEqual(output.usage_tokens, 7)

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_forbidden_raises_timeout_error(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("terminal status 403", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_generic_exception_retry(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Retry success"}}]
        }
        mock_post.side_effect = [Exception("Unexpected system failure"), mock_response]

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt", params={})
        self.assertEqual(output.text, "Retry success")
        self.assertEqual(mock_post.call_count, 2)

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_malformed_json(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        mock_response.json.side_effect = ValueError("Parsing failed")

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("Malformed remote model response", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_http_status_error_terminal(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 409
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Conflict", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        with self.assertRaises(InferenceTimeoutError) as context:
            await client.generate_async("prompt", params={})
        self.assertIn("terminal status 409", str(context.exception))

    @patch("httpx.AsyncClient.post")
    async def test_remote_client_legacy_logprobs_zip_mismatch(self, mock_post: Any) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "text": "Legacy mismatch",
                    "logprobs": {
                        "tokens": ["Mismatch"],
                        "token_logprobs": []  # unequal length
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = RemoteModelClient(api_key="key", endpoint_url="http://localhost:8000/v1", model_name="local-qwen")
        output = await client.generate_async("prompt", params={})
        self.assertEqual(output.tokens, [])


if __name__ == "__main__":
    unittest.main()
