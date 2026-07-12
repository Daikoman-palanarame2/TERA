# TERA V2 Interface Freeze Specification
## Authoritative Implementation Contract & Codebase Constitution

---

## 1. Purpose

This document establishes the **Interface Freeze Specification** for TERA V2. It is the final, binding contract that governs the integration and implementation of the codebase. 

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
1.  **Leaf Layer (`app/schemas/`):** May only import from standard library libraries or external packages (like Pydantic). Imports from any other application package are strictly forbidden.
2.  **Service Layers (`app/cache/`, `app/solvers/`, `app/verification/`):** May import from `app/schemas/` and standard/third-party modules. They must remain isolated from each other. For example, `app/cache/` must not import from `app/verification/`.
3.  **Parser Layer (`app/parser/`):** May import from `app/schemas/` and `app/solvers/` (for accessing `SolverRegistry` configurations).
4.  **Inference Layer (`app/inference/`):** May import from `app/schemas/` and external HTTP libraries (such as `httpx`). Imports from core, cache, or verification are forbidden.
5.  **Orchestration Layer (`app/core/`):** May import from all sub-packages.
6.  **Batch Layer (`run_batch.py` & `main.py`):** May only import from `app/core/`, `app/schemas/`, and `app/utils/`. Direct imports of model clients or validators are disallowed.
7.  **Circular Imports:** Any use of inline imports (e.g., nesting `import` statements inside functions) to bypass circular dependency errors is blocked.

---

## 4. Data Contract Freeze

All schemas passed across package boundaries must be declared using the following Pydantic models:

```python
# file: backend/app/schemas/data_contracts.py

from pydantic import BaseModel, Field, conlist, constr
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
        regex=r"^task_\d+_[a-zA-Z0-9]+$", 
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

## 5. Interface Freeze

All classes across packages must implement these signatures exactly:

```python
# file: backend/app/cache/semantic_cache.py
class SemanticCache:
    def __init__(self, cache_dir: str, embedding_model_path: str) -> None:
        """Initialize LMDB client and load ONNX embedding model."""
        pass
        
    def lookup(self, prompt: str, threshold: float = 0.95) -> Optional[str]:
        """Perform exact match check, followed by cosine similarity embedding search."""
        pass
        
    def insert(self, prompt: str, response: str) -> None:
        """Insert prompt text, embedding array, and output response into LMDB."""
        pass

# file: backend/app/parser/intent_parser.py
class IntentParser:
    def __init__(self, registry: Any) -> None:
        """Bind to the SolverRegistry instance."""
        pass
        
    def parse_intent(self, prompt: str) -> Optional[str]:
        """Verify prompt against compiled regex definitions of registered solvers."""
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
        """Execute the deterministic calculation algorithm."""
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
        """Retrieve solver instance, raise KeyException if missing."""
        pass
        
    def execute(self, solver_name: str, prompt: str) -> str:
        """Directly call solve() on target solver."""
        pass

# file: backend/app/inference/model_interface.py
from abc import ABC, abstractmethod

class ModelInterface(ABC):
    @abstractmethod
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Asynchronously dispatch prompt payload and parse response token list."""
        pass

# file: backend/app/inference/local_client.py
class LocalModelClient(ModelInterface):
    def __init__(self, endpoint_url: str, timeout_sec: float = 5.0) -> None:
        """Configure local HTTP connection pool pointing to ROCm client server."""
        pass
        
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Dispatch post request to vLLM/llama.cpp backend requesting logprobs."""
        pass

# file: backend/app/inference/remote_client.py
class RemoteModelClient(ModelInterface):
    def __init__(self, api_key: str, endpoint_url: str, max_retries: int = 3) -> None:
        """Initialize Fireworks client wrapper with retry configuration."""
        pass
        
    async def generate_async(self, prompt: str, params: Dict[str, Any]) -> RawModelOutput:
        """Dispatch remote request with exponential backoff handlers."""
        pass

# file: backend/app/verification/rovl.py
class ROVL:
    def __init__(self, entropy_threshold: float = 1.5, min_prob_floor: float = 0.05) -> None:
        """Initialize audit limits."""
        pass
        
    def verify(self, output: RawModelOutput, schema_type: str, constraints: Dict[str, Any]) -> VerificationResult:
        """Orchestrate verification pipeline check across syntax and statistical entropy."""
        pass

# file: backend/app/core/orchestrator.py
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
class TelemetryLogger:
    def __init__(self, file_path: str) -> None:
        """Bind to output JSON file path."""
        pass
        
    def log_metrics(self, entry: TelemetryLog) -> None:
        """Append log record atomically utilizing file locks."""
        pass
```

---

## 6. Exception Hierarchy

TERA V2 utilizes a structured custom exception tree. All system exceptions inherit from `TERABaseException`. Catching generic `Exception` is restricted to terminal boundaries:

```
                  ┌────────────────────────┐
                  │    TERABaseException   │
                  └───────────┬────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│VerificationError│  │   CacheError    │  │InferenceTimeout │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐  ┌─────────────────┐
│  RoutingError   │  │ConfigurationErr │
└─────────────────┘  └─────────────────┘
```

### Exception Rules
1.  **`TERABaseException` (Root):** Extends Python's native `Exception`. Requires structured metadata (timestamp, error code).
2.  **`VerificationError`:** Thrown if an output fails Tier 1, 2, or 4 validations and cannot be resolved, or if parsing AST fails inside a logical checker.
3.  **`CacheError`:** Thrown if the LMDB client fails to open, lock, or read records, or if ONNX runtime throws execution errors during embedding calculation.
4.  **`InferenceTimeoutError`:** Thrown strictly when the local inference server or remote API fails to return a response within `MODEL_TIMEOUT_SEC`.
5.  **`RoutingError`:** Thrown if the orchestrator is unable to parse task properties, or if the registry is unable to locate a matched solver name.
6.  **`ConfigurationError`:** Thrown on application startup if required environment variables are missing, malformed, or fail validation rules.

---

## 7. Configuration Freeze

All runtime configurations are derived strictly from environment variables. No configuration files or inline code overrides are allowed:

| Environment Variable | Target Data Type | Default Value | Required? | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `TERA_CACHE_DIR` | `str` | `"/tmp/tera/cache"` | Yes | Must represent a valid path; folder created on start. |
| `TERA_ONNX_MODEL_PATH`| `str` | `"/app/models/minilm.onnx"`| Yes | File must exist on local disk. |
| `TERA_LOCAL_INFERENCE_URL` | `str` | `"http://localhost:8000/v1"` | Yes | Valid HTTP/HTTPS socket URL format. |
| `TERA_FIREWORKS_API_KEY` | `str` | `None` | Yes | String length must be $\ge 32$ characters. |
| `TERA_FIREWORKS_API_URL` | `str` | `"https://api.fireworks.ai/v1"`| No | Valid HTTP/HTTPS socket URL format. |
| `TERA_LOG_LEVEL` | `str` | `"INFO"` | No | Must equal one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `TERA_TELEMETRY_PATH` | `str` | `"/app/output/telemetry.json"`| Yes | Must represent write-accessible path. |
| `TERA_RESULTS_PATH` | `str` | `"/app/output/results.json"`| Yes | Must represent write-accessible path. |

---

## 8. System Constants

All critical operational parameters and verification thresholds are frozen as constant values. Changes to these values are forbidden:

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

## 9. Logging Contract

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

## 10. Telemetry Contract

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

## 11. State Machine & Execution Transitions

The system transitions across states deterministically. The state machine contains no loops; transition paths terminate at the Egress state:

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

## 12. Integration Rules

1.  **No Global State:** Modules must not store request-specific variables in global configurations. All transaction states must reside inside the `RequestState` object passed down the execution chain.
2.  **Explicit Dependency Injection:** Services (e.g., `SemanticCache`, `ROVL`) must be injected into the constructor of `TERAOrchestrator` on application launch inside `main.py`. Classes must not instantiate their dependencies internally.
3.  **Namespace Isolation:** To prevent git merging conflicts, developers must work strictly within their designated directory directories. Modifications outside their assigned paths are disallowed.

---

## 13. Coding Rules

-   **Python Version:** Python 3.11+ is the mandatory runtime version.
-   **Type Hinting:** Code must pass static validation with `mypy --strict`. Use of implicit `Any` is disallowed.
-   **Asynchronous Runtimes:** All network client calls (local and remote) must use `async`/`await` signatures. Core orchestrator pipelines must execute asynchronously using standard loop structures.
-   **Formatting & Linting:** Code formatting is strictly governed by `black` and `ruff`. Enforce a maximum line length of 88 characters.
-   **Docstring Specification:** Every class, method, and function must be declared with a Google-style docstring detailing arguments, return types, and exceptions raised.

---

## 14. Definition of Done (DoD)

A module is declared complete only when it satisfies the following criteria:
*   **Signatures Conformance:** All public interfaces match this Interface Freeze Specification exactly.
*   **Typing Passes:** Static analysis verification returns zero errors using `mypy --strict`.
*   **Linting Compliance:** Ruff/Black verification returns zero syntax or format violations.
*   **Testing Coverage:** Unit testing coverage achieves $\ge 90\%$. Integration testing mock validations verify successfully.
*   **Resource Bounds Met:** Memory profiles (RAM) do not exceed 256MB during simulated execution tests.

---

## 15. Appendix

### Glossary & Abbreviations
*   **DEL:** Deterministic Execution Layer (programmatic execution).
*   **ROVL:** Runtime Output Verification Layer.
*   **LMDB:** Lightning Memory-Mapped Database.
*   **SPS:** Speculative Program Synthesis.
*   **ROCm:** Radeon Open Compute stack.
*   **HIP:** Heterogeneous-compute Interface for Portability.

### Inherited Architecture Decisions
*   *Calibration:* Standardized under Platt Sigmoid optimization followed by Isotonic Regression using PAVA algorithms.
*   *Entropy Calculation:* Standardized to mean Shannon sequence entropy bounds (excluding grammatical syntax carrier tokens).
