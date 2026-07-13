#!/usr/bin/env bash
set -Eeuo pipefail

MODEL_PATH="${TERA_MODEL_PATH:-/models/qwen2.5-coder-7b}"
MODEL_NAME="${TERA_LOCAL_MODEL_NAME:-Qwen/Qwen2.5-Coder-7B-Instruct}"
INPUT_PATH="${TERA_INPUT_PATH:-/input/tasks.json}"
RESULTS_PATH="${TERA_RESULTS_PATH:-/output/results.json}"
VLLM_LOG="${TERA_VLLM_LOG:-/output/vllm.log}"

mkdir -p /output

if [[ ! -s "$INPUT_PATH" ]]; then
  echo "Missing or empty benchmark input: $INPUT_PATH" >&2
  exit 2
fi
if [[ ! -d "$MODEL_PATH" ]]; then
  echo "Bundled model is missing: $MODEL_PATH" >&2
  exit 2
fi

unset FIREWORKS_API_KEY FIREWORKS_BASE_URL TERA_FIREWORKS_API_KEY TERA_FIREWORKS_API_URL
export TERA_SEMANTIC_CACHE_ENABLED=false
export TERA_CACHE_STATE=disabled
export TERA_EXTERNAL_FALLBACK_ENABLED=false

python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name "$MODEL_NAME" \
  --host 127.0.0.1 \
  --port 8000 \
  --dtype bfloat16 \
  --max-model-len "${TERA_MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${TERA_GPU_MEMORY_UTILIZATION:-0.90}" \
  >"$VLLM_LOG" 2>&1 &
VLLM_PID=$!

cleanup() {
  kill "$VLLM_PID" 2>/dev/null || true
  wait "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

deadline=$((SECONDS + ${TERA_VLLM_STARTUP_TIMEOUT_SEC:-300}))
until curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; do
  if ! kill -0 "$VLLM_PID" 2>/dev/null; then
    echo "vLLM exited during startup; log follows:" >&2
    tail -200 "$VLLM_LOG" >&2 || true
    exit 3
  fi
  if (( SECONDS >= deadline )); then
    echo "vLLM did not become ready before the startup deadline" >&2
    tail -200 "$VLLM_LOG" >&2 || true
    exit 3
  fi
  sleep 2
done

python /app/backend/app/run_batch.py --input "$INPUT_PATH" --output "$RESULTS_PATH"
python /app/scripts/check_submission_output.py --input "$INPUT_PATH" --results "$RESULTS_PATH"

