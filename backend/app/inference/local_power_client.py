"""Local power-model adapter for the second vLLM inference tier.

The power tier deliberately reuses the same OpenAI-compatible HTTP contract as
``LocalModelClient``.  It has no API-key argument and rejects Fireworks hosts so
that wiring it as the escalation client cannot silently become a paid route.
"""

from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.core.exceptions import ConfigurationError
from app.inference.local_client import LocalModelClient
from app.schemas.data_contracts import RawModelOutput


class LocalPowerModelClient(LocalModelClient):
    """Client for a stronger model served by a second local vLLM endpoint."""

    _SENSITIVE_PARAM_NAMES = frozenset(
        {
            "api_key",
            "authorization",
            "fireworks_api_key",
            "tera_fireworks_api_key",
        }
    )

    def __init__(
        self, endpoint_url: str, model_name: str, timeout_sec: float = 30.0
    ) -> None:
        parsed = urlparse(endpoint_url.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
        if hostname == "fireworks.ai" or hostname.endswith(".fireworks.ai"):
            raise ConfigurationError(
                "Local power endpoint must not use a Fireworks host."
            )
        super().__init__(endpoint_url, model_name, timeout_sec)
        self.tier = "local_power"

    async def generate_async(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> RawModelOutput:
        """Generate locally while preventing credentials from entering payloads."""
        safe_params = None
        if params is not None:
            safe_params = {
                key: value
                for key, value in params.items()
                if key.lower() not in self._SENSITIVE_PARAM_NAMES
            }
        return await super().generate_async(prompt, safe_params)

