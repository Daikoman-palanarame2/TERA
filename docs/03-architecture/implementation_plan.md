# Implementation Plan: TERA Deterministic Solver Engine

This plan details the implementation of the **Deterministic Solver Engine** inside the frozen TERA architecture. The solver's goal is to maximize zero-token execution by intercepting deterministic queries pre-LLM and resolving them with 100% accuracy using custom Python and SymPy solvers.

## User Review Required

> [!IMPORTANT]
> **SymPy Dependency:** Introducing symbolic execution and equation solving requires adding `sympy` to the dependencies. This package is lightweight but must be installed in the backend environment.
> **Scope Boundaries:** Tasks that contain a mix of subjective text generation and deterministic computation (e.g., *"Calculate the root of 3x^2 - 12x + 9 = 0 and write a poem about it"*) will be routed around this engine with a confidence score of `0.0` to preserve the user's intent.

## Open Questions

> [!NOTE]
> **NER Level of Support:** Named Entity Extraction (NER) in a purely deterministic environment (without LLMs or heavy SpaCy models) is limited to pattern-based rules, lookup tables, and part-of-speech heuristics. We plan to implement a high-speed, rule-based matcher for common entities (names, email addresses, phone numbers, organizations). Please verify if this matches Track 1 expectations.

---

## Proposed Changes

We will implement the Deterministic Solver Engine inside a modular folder structure in the backend inference namespace:

### Deterministic Solver Subsystem

#### [NEW] [deterministic_solver.py](file:///c:/Users/MonMon/Desktop/TERA/backend/app/inference/deterministic_solver.py)
* Defines the core `DeterministicSolverEngine` class that acts as the entrypoint dispatcher.
* Performs pattern detection, extracts task parameters, registers sub-solvers, and handles escalation rules.

#### [NEW] [base_solver.py](file:///c:/Users/MonMon/Desktop/TERA/backend/app/inference/solvers/base_solver.py)
* Abstract base class `BaseDeterministicSolver` defining standard interfaces for detection, execution, and metadata reporting.

#### [NEW] [math_solver.py](file:///c:/Users/MonMon/Desktop/TERA/backend/app/inference/solvers/math_solver.py)
* Implements mathematical, algebraic, and symbolic solvers.
* Integrates `sympy` for symbolic math parsing, equation solving (quadratic/system), calculus derivatives, and `statistics` for average/variance calculations.

#### [NEW] [text_solver.py](file:///c:/Users/MonMon/Desktop/TERA/backend/app/inference/solvers/text_solver.py)
* Implements string and formatting subroutines.
* Features regex extraction, lists and sorting parsing, JSON structural repairs, and basic rule-based NER.

#### [NEW] [util_solver.py](file:///c:/Users/MonMon/Desktop/TERA/backend/app/inference/solvers/util_solver.py)
* Implements date parsing/date math (using `datetime` and `dateutil`) and physical unit conversions.

---

## Technical Details

### 1. Pattern Detection & Dispatcher
* Prompts are run through a compiled regex state dictionary matching target intents.
* Matching intents are routed to the registered sub-solver class.
* If multiple intents match, the UDC executes them in a priority order (Echo > Math > List > Format).

### 2. Confidence Scoring
* If a regex pattern matches *and* parameter parsing succeeds without parsing errors, the solver returns confidence `1.0`.
* If a prompt matches partially but contains non-deterministic components, the solver returns `0.0`, forcing routing to the Local/Remote LLM lane.

### 3. Failure Conditions & Escalation Rules
* If a solver runs into a runtime exception during evaluation (e.g. division by zero, unparseable variable, or CPU timeout), it catches the error, logs it, and returns `None` (representing an escalation/bypass miss), which seamlessly drops the request to the Local LLM.

---

## Verification Plan

### Automated Tests
We will add a new test file:
* **[NEW] [test_deterministic_solver.py](file:///c:/Users/MonMon/Desktop/TERA/tests/test_deterministic_solver.py)**: Running unit tests for:
  * Arithmetic (AST parsing)
  * Symbolic Algebra & Derivatives (SymPy equations)
  * JSON and List Sorting validation
  * Date difference logic
  * Error recovery (exceptions routing)

### Benchmark Plan
* Run the batch suite in `evaluation/run_batch.py` and verify that the escalation rate drops from 100% (where simple math/format tasks failed ROVL) to a target $<20\%$.
* Measure UDC dispatch overhead to ensure it runs in under $0.1\text{ ms}$ on local CPU.
