# TERA Track 1 Production Guide & Deployment Instructions

This guide documents the procedures to build, configure, run, and self-test TERA in the production AMD Developer Hackathon Track 1 container environment.

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
  -e ALLOWED_MODELS="accounts/fireworks/models/llama-v3-8b-instruct, accounts/fireworks/models/llama-v3-70b-instruct" \
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
| `ALLOWED_MODELS` | Comma-separated list of approved Fireworks model tags. | Required in Production |
| `SMALL_MODEL` | Explicitly sets the cheap model lane (overrides automatic discovery). | Optional |
| `LARGE_MODEL` | Explicitly sets the dense model lane (overrides automatic discovery). | Optional |

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
    "id": "smoke-task-1",
    "final_response": "Cheap model response\n",
    "selected_route": "cheap",
    "escalated": false,
    "metadata": {
      "router_probability": 0.8235,
      "cheap_utility": 0.3617,
      "dense_utility": -0.05,
      "cascade_utility": 0.3529,
      "verification_time_ms": 0.01269,
      "inference_time_ms": 0.0038,
      "escalation_reason": null,
      "model_metadata": {
        "model": "cheap_mock_default"
      }
    }
  }
]
```
