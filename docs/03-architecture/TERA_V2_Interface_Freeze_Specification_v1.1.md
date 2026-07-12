# TERA V2 Interface Freeze Specification (Version 1.1)
## Authoritative Implementation Contract & Codebase Constitution

---

## 1. Purpose

This document establishes the **Interface Freeze Specification (v1.1)** for TERA V2. It is the final, binding contract that governs the integration and implementation of the codebase. 

To enable six software engineers to develop and integrate components in parallel without merge conflicts or architectural divergence, all data structures, method signatures, exceptions, configurations, logging patterns, and telemetry structures are hereby frozen. No modifications, extensions, optional paths, or placeholder values are permitted during the implementation phase.

---

## 2. Repository Freeze

The following directory tree maps the complete codebase structure. Every directory and source file is frozen. No additional files may be introduced:

```
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── router_inspector.py
│   ├── cache/
│   │   ├── __init__.py
│   │   └── semantic_cache.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── orchestrator.py
│   │   └── state.py
│   ├── parser/
│   │   ├── __init__.py
│   │   └── intent_parser.py
│   ├── solvers/
│   │   ├── __init__.py
│   │   ├── base_solver.py
│   │   ├── solver_registry.py
│   │   └── plugins/
│   │       ├── __init__.py
│   │       ├── arithmetic_solver.py
│   │       ├── logic_solver.py
│   │       └── text_counter_solver.py
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── model_interface.py
│   │   ├── local_client.py
│   │   └── remote_client.py
│   ├── verification/
│   │   ├── __init__.py
│   │   ├── rovl.py
│   │   ├── validators.py
│   │   └── entropy.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── data_contracts.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── telemetry.py
│   ├── run_batch.py
│   └── main.py
```

---

## 3. Import Rules & Dependency Boundaries

To prevent circular dependencies and maintain architectural isolation, imports must strictly adhere to a **unidirectional layered boundary** model:

```
                       ┌─────────────────────────┐
                       │  schemas/data_contracts │
                       └────────────┬────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   cache/         │       │   solvers/       │       │   verification/  │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         │                          ▼                          │
         │                 ┌──────────────────┐                │
         │                 │   parser/        │                │
         │                 └────────┬─────────┘                │
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │   inference/     │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │   core/          │
                           └──────────────────┘
```

### Import Rules
1.  **Leaf Layer (`app/schemas/`):** May only import from standard libraries or external packages (like Pydantic). Imports from any other application package are strictly forbidden.
2.  **Service Layers (`app/cache/`, `app/solvers/`, `app/verification/`):** May import from `app/schemas/`, `app/core/exceptions.py` (for custom exceptions), and standard/third-party modules. They must remain isolated from each other. For example, `app/cache/` must not import from `app/verification/`.
3.  **Parser Layer (`app/parser/`):** May import from `app/schemas/`, `app/core/exceptions.py`, and `app/solvers/` (for accessing `SolverRegistry` configurations).
4.  **Inference Layer (`app/inference/`):** May import from `app/schemas/`, `app/core/exceptions.py`, and external HTTP libraries (such as `httpx`). Imports from core/state, cache, or verification are forbidden.
5.  **Orchestration Layer (`app/core/`):** May import from all sub-packages, including state, config, and exceptions.
6.  **Batch Layer (`run_batch.py` & `main.py`):** May only import from `app/core/`, `app/schemas/`, and `app/utils/`. Direct imports of model clients or validators are disallowed.
7.  **Circular Imports:** Any use of inline imports (e.g., nesting `import` statements inside functions) to bypass circular dependency errors is blocked.

---

## 4. Data Contract Freeze

All schemas passed across package boundaries must be declared using the following Pydantic models:

```python
# file: backend/app/schemas/data_contracts.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TokenLogprob(BaseModel):
    token: str = Field(
        ..., 
        description="The generated string token representation."
    )
    logprob: float = Field(
        ..., 
        description="The natural log probability of the token choice."
    )

class RawModelOutput(BaseModel):
    text: str = Field(
        ..., 
        description="The raw text output generated by the language model completion."
    )
    tokens: List[TokenLogprob] = Field(
        default_factory=list, 
        description="List of tokens and their associated log probabilities."
    )
    latency_ms: float = Field(
        ..., 
        gt=0.0, 
        description="Total inference execution time in milliseconds."
    )
    usage_tokens: int = Field(
        ..., 
        ge=0, 
        description="Total number of tokens consumed during completion generation."
    )

class VerificationConstraints(BaseModel):
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pydantic or OpenAPI schema to validate JSON responses against."
    )
    regex_pattern: Optional[str] = Field(
        default=None,
        description="Optional regular expression pattern that the response must match."
    )
    stop_sequences: List[str] = Field(
        default_factory=list,
        description="List of stop sequences that should have terminated the output."
    )
    min_length_chars: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional minimum length constraint in characters for the response."
    )
    max_length_chars: Optional[int] = Field(
        default=None,
        gt=0,
        description="Optional maximum length constraint in characters for the response."
    )

class VerificationResult(BaseModel):
    passed: bool = Field(
        ..., 
        description="True if completion passes all syntax, logic, and entropy checks."
    )
    average_surprisal: float = Field(
        ..., 
        description="The calculated average token-level surprisal."
    )
    sequence_entropy: float = Field(
        ..., 
        description="The sequence-level mean Shannon entropy."
    )
    failed_validators: List[str] = Field(
        default_factory=list, 
        description="Array of validator labels that rejected the output."
    )

class InferenceRequest(BaseModel):
    prompt: str = Field(
        ..., 
        min_length=1, 
        description="The raw prompt text submitted to the orchestrator."
    )
    task_id: str = Field(
        ..., 
        pattern=r"^task_\d+_[a-zA-Z0-9]+$", 
        description="Structured identifier matching task pattern: task_<index>_<hash>."
    )
    c2: float = Field(
        ..., 
        ge=0.0, 
        description="Token cost factor of the local cheap model tier."
    )
    c3: float = Field(
        ..., 
        ge=0.0, 
        description="Token cost factor of the remote dense model tier."
    )
    lambda_coeff: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Tradeoff parameter between cost minimization and accuracy maximization."
    )
    alpha_dense: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Profiled baseline accuracy of the dense model for this task domain."
    )
    schema_type: str = Field(
        default="none", 
        description="Target structure schema constraint type (none, json, regex)."
    )
    regex_pattern: Optional[str] = Field(
        default=None, 
        description="Compiled regular expression pattern required if schema_type is regex."
    )

class InferenceResponse(BaseModel):
    final_response: str = Field(
        ..., 
        description="The final text completion output."
    )
    route_taken: str = Field(
        ..., 
        description="The chosen execution route (cache, solver, local_llm, remote_fallback)."
    )
    verification: Optional[VerificationResult] = Field(
        default=None, 
        description="Audit metrics from the ROVL pipeline."
    )
    tokens_consumed: int = Field(
        ..., 
        ge=0, 
        description="Total competition token cost billed."
    )
    latency_ms: float = Field(
        ..., 
        gt=0.0, 
        description="End-to-end processing time in milliseconds."
    )

class TelemetryLog(BaseModel):
    task_id: str = Field(..., description="The unique task identifier.")
    route_taken: str = Field(..., description="The finalized execution route taken.")
    verification_passed: bool = Field(..., description="True if output passed verification.")
    m2_tokens: int = Field(default=0, description="Tokens consumed locally (cheap tier).")
    m3_tokens: int = Field(default=0, description="Tokens consumed remotely (dense tier).")
    del_bypass: bool = Field(default=False, description="True if bypassed to programmatic solver.")
    cache_hit: bool = Field(default=False, description="True if resolved by Semantic Cache.")
    latency_ms: float = Field(..., description="Total elapsed time in milliseconds.")
```

---

## 5. RequestState Specifications

To ensure trace observability and state propagation, the orchestrator tracks the transaction lifecycle within a mutable state object:

*   **File Location:** `backend/app/core/state.py`
*   **Ownership:** Instantiated and mutated exclusively by `TERAOrchestrator`. Read-only access is provided to telemetry helpers and logging middleware.
*   **Lifecycle:**
    1.  **Instantiation:** Created at the immediate ingress of `process_request_async` using parameters derived from `InferenceRequest`.
    2.  **Mutation:** Updated step-by-step as execution moves through semantic caching, intent matching, inference, and ROVL verification.
    3.  **Serialization:** Converted to `TelemetryLog` schema at request completion and appended to the telemetry log file.
    4.  **Destruction:** Dereferenced upon return of the `InferenceResponse`.

```python
# file: backend/app/core/state.py

import time
from typing import Optional, List, Dict, Any
from app.schemas.data_contracts import TokenLogprob

class RequestState:
    def __init__(self, task_id: str, prompt: str) -> None:
        self.task_id: str = task_id
        self.prompt: str = prompt
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        
        # Routing State
        self.route_taken: str = "unknown"
        self.cache_hit: bool = False
        self.del_bypass: bool = False
        
        # Inference Telemetry
        self.local_tokens_consumed: int = 0
        self.remote_tokens_consumed: int = 0
        self.raw_output_text: Optional[str] = None
        self.output_tokens: List[TokenLogprob] = []
        self.inference_latency_ms: float = 0.0
        
        # Verification Telemetry
        self.verification_passed: bool = False
        self.average_surprisal: float = 0.0
        self.sequence_entropy: float = 0.0
        self.failed_validators: List[str] = []
        
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

    def update_inference(self, text: str, tokens: List[TokenLogprob], tokens_count: int, latency_ms: float, is_local: bool) -> None:
        self.raw_output_text = text
        self.output_tokens = tokens
        self.inference_latency_ms = latency_ms
        if is_local:
            self.local_tokens_consumed = tokens_count
        else:
            self.remote_tokens_consumed = tokens_count

    def update_verification(self, passed: bool, surprisal: float, entropy: float, failures: List[str]) -> None:
        self.verification_passed = passed
        self.average_surprisal = surprisal
        self.sequence_entropy = entropy
        self.failed_validators = failures

    def finalize(self, final_route: str) -> None:
        self.route_taken = final_route
        self.end_time = time.time()

    @property
    def total_latency_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000.0
        return (self.end_time - self.start_time) * 1000.0
```

---

## 6. Exception Hierarchy

TERA V2 utilizes a structured custom exception tree. All system exceptions inherit from `TERABaseException`:

*   **File Location:** `backend/app/core/exceptions.py`
*   **Exception Definitions:**

```python
# file: backend/app/core/exceptions.py

from typing import Optional

class TERABaseException(Exception):
    """Base class for all exceptions raised within the TERA platform."""
    def __init__(self, message: str, task_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.task_id: Optional[str] = task_id

class VerificationError(TERABaseException):
    """Raised when an LLM completion fails structure, type, or constraint checks."""
    pass

class CacheError(TERABaseException):
    """Raised when the semantic or exact database fails to read, write, or initialize."""
    pass

class InferenceTimeoutError(TERABaseException):
    """Raised when a local or remote model fails to return output within the SLA limit."""
    pass

class RoutingError(TERABaseException):
    """Raised when query metadata fails parser validation or registry mapping."""
    pass

class ConfigurationError(TERABaseException):
    """Raised when required environment configurations are missing or invalid at startup."""
    pass
```

---

## 7. Interface Freeze

All classes and helper modules across packages must implement these signatures exactly:

```python
# file: backend/app/cache/semantic_cache.py
class SemanticCache:
    def __init__(self, cache_dir: str, embedding_model_path: str) -> None:
        """Initialize LMDB client and load ONNX embedding model.
        
        Raises:
            ConfigurationError: If paths are malformed or missing.
        """
        pass
        
    def lookup(self, prompt: str, threshold: float = 0.95) -> Optional[str]:
        """Perform exact match check, followed by cosine similarity embedding search.
        
        Raises:
            CacheError: If database read fails.
        """
        pass
        
    def insert(self, prompt: str, response: str) -> None:
        """Insert prompt text, embedding array, and output response into LMDB.
        
        Raises:
            CacheError: If database write fails.
        """
        pass

# file: backend/app/parser/intent_parser.py
class IntentParser:
    def __init__(self, registry: Any) -> None:
        """Bind to the SolverRegistry instance."""
        pass
        
    def parse_intent(self, prompt: str) -> Optional[str]:
        """Verify prompt against compiled regex definitions of registered solvers.
        
        Raises:
            RoutingError: If registry lookup fails.
        """
        pass

# file: backend/app/solvers/base_solver.py
from abc import ABC, abstractmethod

class BaseSolver(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique code name string of the solver."""
        pass

    @property
    @abstractmethod
    def pattern(self) -> str:
        """Return the pre-compiled regex trigger string."""
        pass

    @abstractmethod
    def solve(self, prompt: str) -> str:
        """Execute the deterministic calculation algorithm.
        
        Raises:
            VerificationError: If parsing mathematical/logical AST fails.
        """
        pass

# file: backend/app/solvers/solver_registry.py
class SolverRegistry:
    def __init__(self) -> None:
        """Initialize empty solver maps."""
        pass
        
    def register_solver(self, solver: BaseSolver) -> None:
        """Register a solver class instance under its name."""
        pass
        
    def get_solver(self, name: str) -> BaseSolver:
        """Retrieve solver instance.
        
        Raises:
            RoutingError: If name is not registered.
        """
        pass
        
    def execute(self, solver_name: str, prompt: str) -> str:
        """Directly call solve() on target solver."""
        pass

# file: backend/app/inference/model_interface.py
from abc import ABC, abstractmethod

class ModelInterface(ABC):
    @abstractmethod
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Asynchronously dispatch prompt payload and parse response token list.
        
        Raises:
            InferenceTimeoutError: If request latency exceeds SLA timeout.
        """
        pass

# file: backend/app/inference/local_client.py
class LocalModelClient(ModelInterface):
    def __init__(self, endpoint_url: str, model_name: str, timeout_sec: float = 5.0) -> None:
        """Configure local HTTP connection pool pointing to ROCm client server."""
        pass
        
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Dispatch post request to vLLM/llama.cpp backend requesting logprobs."""
        pass

# file: backend/app/inference/remote_client.py
class RemoteModelClient(ModelInterface):
    def __init__(self, api_key: str, endpoint_url: str, model_name: str, max_retries: int = 3) -> None:
        """Initialize Fireworks client wrapper with retry configuration."""
        pass
        
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Dispatch remote request with exponential backoff handlers."""
        pass

# file: backend/app/verification/rovl.py
from app.schemas.data_contracts import VerificationResult, VerificationConstraints, RawModelOutput

class ROVL:
    def __init__(self, entropy_threshold: float = 1.5, min_prob_floor: float = 0.05) -> None:
        """Initialize audit limits."""
        pass
        
    def verify(self, output: RawModelOutput, constraints: VerificationConstraints) -> VerificationResult:
        """Orchestrate verification pipeline check across syntax and statistical entropy.
        
        Raises:
            VerificationError: If critical validation engines fail structurally.
        """
        pass

# file: backend/app/core/orchestrator.py
from app.schemas.data_contracts import InferenceRequest, InferenceResponse

class TERAOrchestrator:
    def __init__(
        self, 
        cache: SemanticCache, 
        parser: IntentParser, 
        registry: SolverRegistry, 
        local_client: ModelInterface, 
        remote_client: ModelInterface, 
        rovl: ROVL
    ) -> None:
        """Inject core pipeline dependencies."""
        pass
        
    async def process_request_async(self, request: InferenceRequest) -> InferenceResponse:
        """Drive the execution lifecycle: Cache -> Parser -> Solver -> Local Model -> ROVL -> Fallback."""
        pass

# file: backend/app/utils/telemetry.py
from app.schemas.data_contracts import TelemetryLog

class TelemetryLogger:
    def __init__(self, file_path: str) -> None:
        """Bind to output JSON file path."""
        pass
        
    def log_metrics(self, entry: TelemetryLog) -> None:
        """Append log record atomically utilizing file locks."""
        pass
```

---

### 7.1 Helper Module Signatures

The interfaces for verification helper modules are frozen below:

```python
# file: backend/app/verification/validators.py

from typing import List, Dict, Any

def validate_json_schema(text: str, schema: Dict[str, Any]) -> bool:
    """Validate JSON text against a target JSON Schema dictionary.
    
    Args:
        text: The string output to check.
        schema: OpenAPI or JSON Schema dictionary structure.
        
    Returns:
        True if the text is valid JSON and matches the schema, False otherwise.
        
    Raises:
        VerificationError: If the schema itself is invalid.
    """
    pass

def validate_regex(text: str, pattern: str) -> bool:
    """Check if the text matches a compiled regex pattern.
    
    Args:
        text: The string output to check.
        pattern: The regex pattern string.
        
    Returns:
        True if pattern is found, False otherwise.
        
    Raises:
        VerificationError: If pattern string is invalid and fails to compile.
    """
    pass

def validate_stop_sequences(text: str, stop_sequences: List[str]) -> bool:
    """Verify that the generation naturally terminated on a valid stop sequence.
    
    Args:
        text: The string output to check.
        stop_sequences: List of target stop tokens.
        
    Returns:
        True if output ends with a registered stop sequence or contains it.
    """
    pass


# file: backend/app/verification/entropy.py

from typing import List
from app.schemas.data_contracts import TokenLogprob

def compute_sequence_entropy(tokens: List[TokenLogprob]) -> float:
    """Calculate the average Shannon entropy across a sequence of token logprobs.
    
    Args:
        tokens: List of TokenLogprob instances from model metadata.
        
    Returns:
        The calculated mean sequence entropy score.
    """
    pass

def compute_average_surprisal(tokens: List[TokenLogprob]) -> float:
    """Calculate the mean surprisal score (-logprob) across generated tokens.
    
    Args:
        tokens: List of TokenLogprob instances.
        
    Returns:
        The calculated average surprisal score.
    """
    pass
```

---

## 8. Configuration Freeze

All runtime configurations are derived strictly from environment variables. No configuration files or inline code overrides are allowed:

| Environment Variable | Target Data Type | Default Value | Required? | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `TERA_CACHE_DIR` | `str` | `"/tmp/tera/cache"` | Yes | Valid path; folder created on start. |
| `TERA_ONNX_MODEL_PATH`| `str` | `"/app/models/minilm.onnx"`| Yes | File must exist on local disk. |
| `TERA_LOCAL_INFERENCE_URL` | `str` | `"http://localhost:8000/v1"` | Yes | Valid HTTP/HTTPS socket URL format. |
| `TERA_LOCAL_MODEL_NAME` | `str` | `"Qwen/Qwen2.5-Coder-7B-Instruct"` | Yes | String length must be $\ge 3$ characters. |
| `TERA_FIREWORKS_API_KEY` | `str` | `None` | Yes | String length must be $\ge 32$ characters. |
| `TERA_FIREWORKS_API_URL` | `str` | `"https://api.fireworks.ai/v1"`| No | Valid HTTP/HTTPS socket URL format. |
| `TERA_REMOTE_MODEL_NAME`| `str` | `"accounts/fireworks/models/deepseek-v3"`| Yes | String length must be $\ge 3$ characters. |
| `TERA_LOG_LEVEL` | `str` | `"INFO"` | No | Must equal one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `TERA_TELEMETRY_PATH` | `str` | `"/app/output/telemetry.json"`| Yes | Must represent write-accessible path. |
| `TERA_RESULTS_PATH` | `str` | `"/app/output/results.json"`| Yes | Must represent write-accessible path. |

---

## 9. System Constants

All critical operational parameters and verification thresholds are frozen as constant values:

```python
# file: backend/app/core/config.py

# Caching Thresholds
SEMANTIC_SIMILARITY_THRESHOLD = 0.95  # Cosine similarity boundary for semantic hit
LMDB_MAP_SIZE = 104857600  # 100MB database page mapping size allocation

# Dynamic Queue Parameters
DYNAMIC_BATCH_WINDOW_MS = 10  # Queue bundling wait window
MAX_CONCURRENT_WORKERS = 16  # Thread pool count for async tasks execution

# Logprob and Entropy Thresholds
ENTROPY_THRESHOLD = 1.5  # Mean Shannon sequence entropy limit
SURPRISAL_THRESHOLD = 1.5  # Per-token maximum surprisal bound
MIN_PROBABILITY_FLOOR = 0.05  # Critical surprisal limit per token

# Network Parameters
MODEL_TIMEOUT_SEC = 5.0  # Max runtime boundary before timeout exception
FALLBACK_RETRY_COUNT = 3  # Exponential retry ceiling
FALLBACK_BACKOFF_FACTOR = 2.0  # Backoff delay multiplier rate
```

---

## 10. Logging Contract

TERA V2 enforces structured JSON logging for all log events. 

### Logger Configuration
- **Logger Name:** `"tera_core"`
- **Log Format:** Single-line JSON strings output directly to stdout.

### Required Fields
Every log entry must contain the following keys:
*   `timestamp`: ISO-8601 string representation.
*   `log_level`: String indicating importance (INFO, WARNING, ERROR).
*   `module`: Python module path (e.g., `app.core.orchestrator`).
*   `message`: Description string.
*   `task_id`: String (if context represents a task transaction, else `null`).

### Example Log Entry
```json
{"timestamp": "2026-07-12T06:15:32.482Z", "log_level": "WARNING", "module": "app.verification.rovl", "message": "Average surprisal exceeded threshold. Value: 1.84, Limit: 1.50", "task_id": "task_104_8f2e9a1"}
```

---

## 11. Telemetry Contract

Execution logs are exported to `telemetry.json` as a single, structural JSON array containing flat schemas matching the `TelemetryLog` contract. No nested properties are permitted.

### Output Field Requirements
*   `task_id` (`str`): Unique task key.
*   `route_taken` (`str`): Final route classification (`cache`, `solver`, `local_llm`, `remote_fallback`).
*   `verification_passed` (`bool`): `true` if ROVL accepted output, `false` if rejected and escalated.
*   `m2_tokens` (`int`): Billed cheap tokens (unit: count).
*   `m3_tokens` (`int`): Billed dense tokens (unit: count).
*   `del_bypass` (`bool`): `true` if solved programmatically by solver.
*   `cache_hit` (`bool`): `true` if resolved by semantic cache.
*   `latency_ms` (`float`): Millisecond execution duration (unit: ms).

---

## 12. State Machine & Execution Transitions

The system transitions across states deterministically:

| Source State | Event / Input Condition | Target State | Action / Transition Outputs |
| :--- | :--- | :--- | :--- |
| **Ingress** | Task record read from queue | **Cache_Lookup** | Query semantic cache. |
| **Cache_Lookup** | Cosine similarity $\ge 0.95$ | **Egress** | Retrieve cached response (Route: `cache`). |
| **Cache_Lookup** | Cosine similarity $< 0.95$ | **Intent_Parsing** | Pass prompt to IntentParser. |
| **Intent_Parsing**| Solver regex matches | **DEL_Execution** | Execute Solver (Route: `solver`). |
| **Intent_Parsing**| No regex matches | **Local_Inference**| Dispatch post request to local model. |
| **DEL_Execution** | Solver runs successfully | **Egress** | Return solver output (Route: `solver`). |
| **DEL_Execution** | Solver throws exception | **Local_Inference**| Log error; fall back to local inference. |
| **Local_Inference**| Server returns output | **ROVL_Verification**| Run validators. |
| **Local_Inference**| Server socket timeout | **Remote_Fallback** | Raise InferenceTimeoutError; route to fallback. |
| **ROVL_Verification**| Passed all checks | **Egress** | Return local completion (Route: `local_llm`). |
| **ROVL_Verification**| Verification failed | **Remote_Fallback** | Discard text; call Remote client. |
| **Remote_Fallback**| Fireworks API returns output| **Egress** | Return remote completion (Route: `remote_fallback`). |
| **Remote_Fallback**| Fireworks API fails | **Error_State** | Raise terminal SystemError. |
| **Error_State** | Exception caught | **Egress** | Output fallback error string to results.json. |
| **Egress** | Output written | **Ingress** | Free thread slot; process next task. |

---

## 13. Integration Rules

1.  **No Global State:** Modules must not store request-specific variables in global configurations. All transaction states must reside inside the `RequestState` object passed down the execution chain.
2.  **Explicit Dependency Injection:** Services (e.g., `SemanticCache`, `ROVL`) must be injected into the constructor of `TERAOrchestrator` on application launch inside `main.py`. Classes must not instantiate their dependencies internally.
3.  **Namespace Isolation:** To prevent git merging conflicts, developers must work strictly within their designated directories. Modifications outside their assigned paths are disallowed.

---

## 14. Coding Rules

-   **Python Version:** Python 3.11+ is the mandatory runtime version.
-   **Type Hinting:** Code must pass static validation with `mypy --strict`. Use of implicit `Any` is disallowed.
-   **Asynchronous Runtimes:** All network client calls (local and remote) must use `async`/`await` signatures. Core orchestrator pipelines must execute asynchronously using standard loop structures.
-   **Formatting & Linting:** Code formatting is strictly governed by `black` and `ruff`. Enforce a maximum line length of 88 characters.
-   **Docstring Specification:** Every class, method, and function must be declared with a Google-style docstring detailing arguments, return types, and exceptions raised.

---

## 15. Definition of Done (DoD)

A module is declared complete only when it satisfies the following criteria:
*   **Signatures Conformance:** All public interfaces match this Interface Freeze Specification exactly.
*   **Typing Passes:** Static analysis verification returns zero errors using `mypy --strict`.
*   **Linting Compliance:** Ruff/Black verification returns zero syntax or format violations.
*   **Testing Coverage:** Unit testing coverage achieves $\ge 90\%$. Integration testing mock validations verify successfully.
*   **Resource Bounds Met:** Memory profiles (RAM) do not exceed 256MB during simulated execution tests.

---

## 16. Evaluation of Ingress Length Constraints

During the v1.1 update review, adding `min_chars` and `max_chars` parameters directly to `InferenceRequest` was evaluated.

*   **Decision:** Excluded from `InferenceRequest`.
*   **Technical Rationale:** The ingress request model maps 1:1 with the input schemas of the benchmark evaluation harness. Injecting required character limits onto the ingress contract violates compatibility with standard task inputs in `tasks.json`.
*   **Approved Design Resolution:** Character limit validations represent output properties rather than input configurations. Therefore, `min_length_chars` and `max_length_chars` have been added strictly to the **`VerificationConstraints`** schema inside the ROVL verification path. If the output generation exceeds these thresholds, ROVL raises a validation check failure and escalates the request downstream. This enforces exact output limits without breaking ingress compatibility.

---

## 17. Revision Summary (v1.0 to v1.1)

The changes incorporated in this revision are mapped below:

| Change Location | Scope of Adjustment | Reason for Modification |
| :--- | :--- | :--- |
| `schemas/data_contracts.py` | Replaced `regex=` validation parameter with `pattern=`. | Deprecated in Pydantic v2; updated to prevent runtime parser warnings. |
| `schemas/data_contracts.py` | Added Pydantic model class `VerificationConstraints`. | Replaced the raw dictionary configuration inside the ROVL interface. |
| `core/state.py` | Created module; fully specified the `RequestState` class. | Implemented telemetry trace variables and lifecycle methods. |
| `core/exceptions.py` | Created module; specified custom exception class tree. | Consolidated custom exceptions to define system-wide error triggers. |
| `verification/validators.py` | Frozen public signatures and types for helper functions. | Provides explicit contracts for JSON schema and regex validation. |
| `verification/entropy.py` | Frozen public signatures for entropy calculations. | Standardizes logs and calculation arguments. |
| `core/config.py` | Added `TERA_LOCAL_MODEL_NAME` and `TERA_REMOTE_MODEL_NAME`. | Enables configuration of active local/remote models via environment. |
| `schemas/data_contracts.py` | Excluded `min_chars`/`max_chars` from `InferenceRequest`. | Avoids breaking raw ingress schema compatibility with task loops. |
