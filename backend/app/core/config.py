"""
Module: backend/app/core/config
Purpose:
    Manages TERA V3 environment-driven configurations and validation gates.
    Exposes immutable configuration objects and a configuration provider.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.core.exceptions import ConfigurationError

# Frozen operational constants retained for the runtime modules that implement
# the V2 pipeline beneath the V3 interfaces.
SEMANTIC_SIMILARITY_THRESHOLD = 0.95
LMDB_MAP_SIZE = 104_857_600
DYNAMIC_BATCH_WINDOW_MS = 10
MAX_CONCURRENT_WORKERS = 16
ENTROPY_THRESHOLD = 1.5
SURPRISAL_THRESHOLD = 1.5
MIN_PROBABILITY_FLOOR = 0.05
MODEL_TIMEOUT_SEC = 5.0
FALLBACK_RETRY_COUNT = 3
FALLBACK_BACKOFF_FACTOR = 2.0


class RuntimeSettings:
    """Environment-backed compatibility settings for the frozen runtime path."""

    def __init__(self) -> None:
        self.tera_cache_dir = os.getenv("TERA_CACHE_DIR", "/tmp/tera/cache")
        self.tera_onnx_model_path = os.getenv(
            "TERA_ONNX_MODEL_PATH", "/app/models/minilm.onnx"
        )
        self.tera_local_inference_url = os.getenv(
            "TERA_LOCAL_INFERENCE_URL", "http://localhost:8000/v1"
        )
        self.tera_local_model_name = os.getenv(
            "TERA_LOCAL_MODEL_NAME", "Qwen/Qwen2.5-Coder-7B-Instruct"
        )
        self.tera_power_inference_url = os.getenv(
            "TERA_POWER_INFERENCE_URL", "http://localhost:8001/v1"
        )
        self.tera_power_model_name = os.getenv(
            "TERA_POWER_MODEL_NAME", "Qwen/Qwen2.5-14B-Instruct"
        )
        self.tera_fireworks_api_key = os.getenv("TERA_FIREWORKS_API_KEY")
        self.tera_fireworks_api_url = os.getenv(
            "TERA_FIREWORKS_API_URL", "https://api.fireworks.ai/v1"
        )
        self.tera_remote_model_name = os.getenv(
            "TERA_REMOTE_MODEL_NAME", "accounts/fireworks/models/deepseek-v3"
        )
        self.tera_external_fallback_enabled = os.getenv(
            "TERA_EXTERNAL_FALLBACK_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.tera_model_timeout_sec = float(
            os.getenv("TERA_MODEL_TIMEOUT_SEC", str(MODEL_TIMEOUT_SEC))
        )
        if self.tera_model_timeout_sec <= 0:
            raise ConfigurationError("TERA_MODEL_TIMEOUT_SEC must be positive.")
        self.tera_log_level = os.getenv("TERA_LOG_LEVEL", "INFO")
        self.tera_telemetry_path = os.getenv(
            "TERA_TELEMETRY_PATH", "/app/output/telemetry.json"
        )
        self.tera_results_path = os.getenv(
            "TERA_RESULTS_PATH", "/app/output/results.json"
        )
        self.entropy_threshold = float(
            os.getenv("ENTROPY_THRESHOLD", str(ENTROPY_THRESHOLD))
        )
        self.tera_cascade_enabled = os.getenv(
            "TERA_CASCADE_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.tera_cisc_enabled = os.getenv(
            "TERA_CISC_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.tera_refinement_enabled = os.getenv(
            "TERA_REFINEMENT_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.tera_enriched_handoff_enabled = os.getenv(
            "TERA_ENRICHED_HANDOFF_ENABLED", "false"
        ).strip().lower() in {"1", "true", "yes", "on"}



settings = RuntimeSettings()

@dataclass(frozen=True)
class Configuration:
    """Immutable data contract containing active configuration settings.

    Attributes:
        FAST_MODEL_ENDPOINT (str): Serving base endpoint for the fast model tier.
        FAST_MODEL_IDENTIFIER (str): Model name/version for the fast model tier.
        POWER_MODEL_ENDPOINT (str): Serving base endpoint for the power model tier.
        POWER_MODEL_IDENTIFIER (str): Model name/version for the power model tier.
    """
    FAST_MODEL_ENDPOINT: str
    FAST_MODEL_IDENTIFIER: str
    POWER_MODEL_ENDPOINT: str
    POWER_MODEL_IDENTIFIER: str


class ConfigurationProviderInterface(ABC):
    """Abstract base class defining the configuration retrieval contract."""

    @abstractmethod
    def get_config(self) -> Configuration:
        """Retrieve active configuration metadata.

        Returns:
            Configuration: The frozen, validated configuration settings.

        Raises:
            ConfigurationError: If loading or validation fails.
        """
        pass


class EnvConfigurationProvider(ConfigurationProviderInterface):
    """Loads and validates configuration from environment variables."""

    def get_config(self) -> Configuration:
        """Retrieves and validates configuration from the system environment.

        Returns:
            Configuration: The frozen, validated configuration settings.

        Raises:
            ConfigurationError: If required variables are missing, empty, or invalid.
        """
        fast_endpoint = os.environ.get("FAST_MODEL_ENDPOINT")
        fast_id = os.environ.get("FAST_MODEL_IDENTIFIER")
        power_endpoint = os.environ.get("POWER_MODEL_ENDPOINT")
        power_id = os.environ.get("POWER_MODEL_IDENTIFIER")

        missing = []
        if not fast_endpoint:
            missing.append("FAST_MODEL_ENDPOINT")
        if not fast_id:
            missing.append("FAST_MODEL_IDENTIFIER")
        if not power_endpoint:
            missing.append("POWER_MODEL_ENDPOINT")
        if not power_id:
            missing.append("POWER_MODEL_IDENTIFIER")

        if missing:
            raise ConfigurationError(
                f"Missing required configuration environment variables: {', '.join(missing)}"
            )

        # Validate URL schema
        for key, val in [("FAST_MODEL_ENDPOINT", fast_endpoint), ("POWER_MODEL_ENDPOINT", power_endpoint)]:
            if not val.startswith(("http://", "https://")):
                raise ConfigurationError(
                    f"Invalid URL schema for {key}: '{val}'. Must start with 'http://' or 'https://'"
                )

        return Configuration(
            FAST_MODEL_ENDPOINT=fast_endpoint,
            FAST_MODEL_IDENTIFIER=fast_id,
            POWER_MODEL_ENDPOINT=power_endpoint,
            POWER_MODEL_IDENTIFIER=power_id
        )
