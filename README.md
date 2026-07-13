# ROCmRoute Zero — AMD Track 1

ROCmRoute Zero is a local-first routing agent for the AMD Developer Hackathon. It combines deterministic zero-token solvers, response verification, and a locally hosted Qwen model running through vLLM on AMD ROCm hardware.

The leaderboard runtime makes no Fireworks or other external inference calls. The validated AMD notebook run used `Qwen/Qwen2.5-Coder-7B-Instruct`, achieved 100% accuracy on the 16 retired public validation tasks, and recorded zero external tokens and zero external API calls. These public results do not guarantee hidden-set accuracy.

The internal Python package and environment-variable prefix remain `TERA` for backward compatibility with the frozen interface contracts.

---

## ROCmRoute Zero System Architecture & Overview

### Project Overview
**ROCmRoute Zero** routes requests through deterministic solvers, a fast local inference lane, and a local power lane. Both neural lanes use the bundled Qwen model through loopback-only vLLM; external fallback is hard-disabled in the leaderboard profile.

### System Architecture
The TERA pipeline is modular and executes in microsecond scales on CPU before initiating external API requests:

```
                  ┌──────────────────────┐
                  │     Input Prompt     │
                  └──────────┬───────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ Lexical Feature Extractor │
               │ (Length, Symbols, Regex,  │
               │        BM25 Score)        │
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │    Logistic Regressor     │
               │ (Predict Raw Probability) │
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │    Isotonic Calibrator    │
               │ (Calibrated Probability)  │
               └─────────────┬─────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │       Utility Engine      │
               │   (Compute Expected EUs)  │
               └─────────────┬─────────────┘
                             │
            ┌────────────────┼────────────────┐
            │ (Route: Cheap) │ (Route: Cascade)│ (Route: Dense)
            ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ Cheap Model │  │ Cheap Model │  │ Dense Model │
     └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
            │                │                │
            ▼                ▼                │
     ┌─────────────┐  ┌─────────────┐         │
     │  ROVL Check │  │  ROVL Check │         │
     └──────┬──────┘  └──────┬──────┘         │
            │                │                │
    PASS ───┼─── FAIL PASS ──┼── FAIL         │
    ┌───────┴───┐     ┌──────┴──┐             │
    ▼           ▼     ▼         ▼             ▼
┌───────┐ ┌─────────┐┌──────┐┌─────────┐ ┌─────────┐
│Return │ │Escalate ││Return││Escalate │ │Return   │
│Cheap  │ │to Dense ││Cheap ││to Dense │ │Dense    │
└───────┘ └─────────┘└──────┘└─────────┘ └─────────┘
```

*   **Router**: Extracts a 4-dimensional lexical representation from the input prompt: prompt length, symbol density (ratio of non-alphanumeric/non-space characters), regex category match density, and BM25 lexical similarity score against a reference task corpus.
*   **Calibration**: Maps the logistic regressor's raw output to a calibrated probability using Isotonic Regression, ensuring that the estimated success rate matches empirical model performance.
*   **Runtime Output Verification Layer (ROVL)**: Validates cheap model completions against:
    *   *Schema constraints* (JSON structure or specific regular expressions).
    *   *Character length* boundaries (minimum and maximum bounds).
    *   *Stop-token verification* (ensuring completion terminates cleanly on valid stop tokens).
    *   *Token entropy* (ensuring average sequence entropy is below a threshold to prevent hallucinations/gibberish).
*   **Cascade Flow**: Computes the Expected Utility (EU) for each path (`cheap`, `cascade`, `dense`) using the calibrated success probability, token costs (\(C_{cheap}, C_{dense}\)), and task hyperparameters. If `cheap` or `cascade` is selected and the cheap model generation fails ROVL validation, it automatically escalates to execute the `dense` model lane.

---

## Directory Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints
│   │   ├── core/            # Environment configurations & settings
│   │   ├── evaluation/      # Offline batch benchmarking & sensitivity sweep
│   │   ├── inference/       # Model adapters for Fireworks & Offline Mock adapter
│   │   ├── models/          # Deserialized router coefficients & BM25 corpus
│   │   ├── router/          # Feature extraction, BM25 similarity & utility engine
│   │   ├── schemas/         # Request and Response schemas
│   │   ├── training/        # ML model training and calibration scripts
│   │   └── verification/    # ROVL and validators (JSON, Regex, Entropy)
│   └── requirements.txt     # Python environment package requirements
├── docs/                    # Architecture, UI/UX, and Deployment Specifications
├── input/                   # Default tasks input directory
├── output/                  # Default results output directory
├── tests/                   # Extensive pytest suite (64 unit tests)
├── Dockerfile               # Production container definition
├── .dockerignore            # Build ignore specifications
├── .gitignore               # Git version control ignore configuration
└── entrypoint.sh            # Pre-flight validator and runner entrypoint script
```

---

## Local Python Setup

To run tests and scripts locally without Docker:

1. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv backend/.venv
   # On Windows:
   backend\.venv\Scripts\activate
   # On Linux/macOS:
   source backend/.venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Run Unit Tests:**
   ```bash
   $env:PYTHONPATH="backend" # Windows PowerShell
   # export PYTHONPATH="backend" # Linux/macOS
   pytest tests/
   ```

---

## Evaluation & Benchmarking

TERA includes benchmarking and evaluation modules to test router performance:

*   **Offline Batch Benchmarking**: Runs the router against a static labeled csv dataset to compute accuracy, cost, and latency comparisons:
    ```bash
    python backend/app/evaluation/run_eval.py
    ```
*   **Calibration Parameter Sweep**: Sweeps across the \(\lambda\) frugality coefficient to output cost-accuracy trade-off curves:
    ```bash
    python backend/app/evaluation/run_sensitivity.py
    ```

---

## 1. Directory Structures & Volume Mounts
The container expects two directory volumes to be mounted at runtime:
- `/input`: A volume containing the task definition payload `/input/tasks.json`.
- `/output`: A volume where the results file `/output/results.json` will be written.

---

## 2. Docker Commands

### Build the Image
To build the Track 1 submission container targetting the AMD platform (`linux/amd64`):
```bash
docker build -t tera-router .
```

### Run in Production Mode
To execute the batch processing on mounted input/output directories with a live Fireworks connection:
```bash
docker run --rm \
  -e FIREWORKS_API_KEY="your_api_key_here" \
  -e FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1" \
  -e ALLOWED_MODELS="accounts/fireworks/models/deepseek-v4-pro, accounts/fireworks/models/gpt-oss-120b" \
  -v "$(pwd)/input:/input" \
  -v "$(pwd)/output:/output" \
  tera-router
```

### Run in Local Self-Test Mode
To verify container dependencies, configurations, router initialization, and weights loading without contacting external APIs:
```bash
docker run --rm tera-router --self-test
```

### Run in Offline Mock Mode
To verify the container pipeline logic end-to-end on local input files without Fireworks credentials:
```bash
docker run --rm \
  -v "$(pwd)/input:/input" \
  -v "$(pwd)/output:/output" \
  tera-router --mock
```

---

## 3. Environment Variables

| Variable | Description | Requirement |
| :--- | :--- | :--- |
| `FIREWORKS_API_KEY` | Fireworks API Authorization Bearer token. | Required in Production |
| `FIREWORKS_BASE_URL` | Base URL endpoint (defaults to `https://api.fireworks.ai/inference/v1`). | Optional |
| `ALLOWED_MODELS` | Comma-separated list of approved Fireworks model tags. | Optional |
| `SMALL_MODEL` | Explicitly sets the cheap model lane (overrides automatic discovery). | Optional |
| `LARGE_MODEL` | Explicitly sets the dense model lane (overrides automatic discovery). | Optional |

**Model Resolution Precedence:**
1. `SMALL_MODEL` / `LARGE_MODEL` / `cheap_model` / `dense_model` (Explicit Overrides - Highest Priority).
2. `ALLOWED_MODELS` (Automatic Discovery - Picks lowest parameter/tier model as cheap, highest as dense).
3. Fallback Defaults (Cheap: `accounts/fireworks/models/deepseek-v4-pro`, Dense: `accounts/fireworks/models/gpt-oss-120b` - Lowest Priority).

---

## 4. Input & Output Formats

### `/input/tasks.json`
The input file must contain a JSON array of task dictionary items:
```json
[
  {
    "id": "smoke-task-1",
    "prompt": "Summarize the history of space travel in one sentence.",
    "schema_type": "none",
    "min_chars": 5,
    "max_chars": 200
  },
  {
    "id": "smoke-task-2",
    "prompt": "Convert the following mapping to JSON: name is Alice, age is 30.",
    "schema_type": "json",
    "min_chars": 10
  }
]
```

### `/output/results.json`
The generated output compiled by the batch harness follows this format:
```json
[
  {
    "task_id": "smoke-task-1",
    "answer": "Cheap model response\n"
  }
]
```
