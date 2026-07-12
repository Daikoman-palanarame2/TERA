"""
Module: backend/app/core/state
Purpose:
    Manages global application runtime state, lifecycle tracking, initialization, 
    and shutdown states in a thread-safe manner.
"""

import time
import threading
from typing import Optional

from app.schemas.data_contracts import TokenLogprob


class RequestState:
    """Mutable, request-scoped execution and telemetry state."""

    def __init__(self, task_id: str, prompt: str) -> None:
        self.task_id = task_id
        self.prompt = prompt
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.route_taken = "unknown"
        self.cache_hit = False
        self.del_bypass = False
        self.local_tokens_consumed = 0
        self.remote_tokens_consumed = 0
        self.raw_output_text: Optional[str] = None
        self.output_tokens: list[TokenLogprob] = []
        self.inference_latency_ms = 0.0
        self.verification_passed = False
        self.average_surprisal = 0.0
        self.sequence_entropy = 0.0
        self.failed_validators: list[str] = []

        # Frozen benchmark telemetry extensions used by the orchestrator.
        self.category = "unknown"
        self.deterministic_solver: Optional[str] = None
        self.local_model: Optional[str] = None
        self.local_latency_ms = 0.0
        self.local_completion_length = 0
        self.timeout_status = False
        self.remote_fallback_triggered = False
        self.fireworks_tokens = 0
        self.external_api_calls = 0

        # Cascade routing metrics
        self.difficulty_tier = None
        self.routing_reasons = []
        self.cisc_enabled = False
        self.sample_count = 0
        self.agreement_type = None
        self.agreement_score = 0.0
        self.did_refine = False
        self.refinement_passed = None
        self.enriched_handoff_used = False
        self.cascade_fallback_used = False


    def mark_cache_hit(self, response: str) -> None:
        self.route_taken = "cache"
        self.cache_hit = True
        self.raw_output_text = response
        self.verification_passed = True
        self.end_time = time.time()

    def mark_solver_hit(self, response: str) -> None:
        self.route_taken = "solver"
        self.del_bypass = True
        self.raw_output_text = response
        self.verification_passed = True
        self.end_time = time.time()

    def update_inference(
        self,
        text: str,
        tokens: list[TokenLogprob],
        tokens_count: int,
        latency_ms: float,
        is_local: bool,
        external_api_calls: int = 0,
    ) -> None:
        self.raw_output_text = text
        self.output_tokens = tokens
        self.inference_latency_ms = latency_ms
        self.external_api_calls += external_api_calls
        if is_local:
            self.local_tokens_consumed = tokens_count
        else:
            self.remote_tokens_consumed = tokens_count

    def update_verification(
        self, passed: bool, surprisal: float, entropy: float, failures: list[str]
    ) -> None:
        self.verification_passed = passed
        self.average_surprisal = surprisal
        self.sequence_entropy = entropy
        self.failed_validators = failures

    def finalize(self, final_route: str) -> None:
        self.route_taken = final_route
        self.end_time = time.time()

    @property
    def total_latency_ms(self) -> float:
        end_time = self.end_time if self.end_time is not None else time.time()
        return (end_time - self.start_time) * 1000.0

class ApplicationState:
    """Manages global application runtime state, lifecycle tracking, and request concurrency.

    Attributes:
        _initialized (bool): Flag indicating if the system is fully initialized.
        _shutdown (bool): Flag indicating if the system has been shut down.
        _start_time (float): UTC timestamp when the state tracker was instantiated.
        _active_requests (int): Counter of active concurrent requests.
        _lock (threading.Lock): Mutex to ensure thread-safe modifications to state properties.
    """

    def __init__(self) -> None:
        """Initializes the global application state tracker."""
        self._initialized: bool = False
        self._shutdown: bool = False
        self._start_time: float = time.time()
        self._active_requests: int = 0
        self._lock: threading.Lock = threading.Lock()

    def initialize(self) -> None:
        """Marks the application runtime as initialized and ready to receive requests."""
        with self._lock:
            self._initialized = True
            self._shutdown = False

    def shutdown_system(self) -> None:
        """Marks the application runtime as shut down, preventing new requests."""
        with self._lock:
            self._shutdown = True

    def increment_active_requests(self) -> None:
        """Increments the concurrent active request counter thread-safely."""
        with self._lock:
            self._active_requests += 1

    def decrement_active_requests(self) -> None:
        """Decrements the concurrent active request counter thread-safely."""
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1

    @property
    def is_initialized(self) -> bool:
        """Indicates if the application initialization phase is complete.

        Returns:
            bool: True if initialized, False otherwise.
        """
        with self._lock:
            return self._initialized

    @property
    def is_shutdown(self) -> bool:
        """Indicates if the application has been shut down.

        Returns:
            bool: True if shut down, False otherwise.
        """
        with self._lock:
            return self._shutdown

    @property
    def active_requests(self) -> int:
        """Returns the current number of concurrent requests.

        Returns:
            int: The active request count.
        """
        with self._lock:
            return self._active_requests

    @property
    def uptime_seconds(self) -> float:
        """Calculates system uptime since instantiation in seconds.

        Returns:
            float: Uptime duration in seconds.
        """
        return time.time() - self._start_time

    def is_healthy(self) -> bool:
        """Verifies if the application state is operational and healthy.

        Returns:
            bool: True if initialized and not shut down, False otherwise.
        """
        with self._lock:
            return self._initialized and not self._shutdown
