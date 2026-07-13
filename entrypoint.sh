#!/bin/bash
set -e

echo "===================================="
echo "TERA Track 1 Production Startup"
echo "===================================="

# Check for web launcher mode (no arguments, or first argument is "web")
if [ $# -eq 0 ] || [ "$1" = "web" ]; then
  TARGET_PORT=${PORT:-7860}
  echo "Launching TERA Web Server on port $TARGET_PORT..."
  exec uvicorn app.main:app --host 0.0.0.0 --port "$TARGET_PORT"
fi

# Check if self-test mode is requested
SELF_TEST=false
for arg in "$@"; do
  if [ "$arg" = "--self-test" ]; then
    SELF_TEST=true
  fi
done

# Initialize validation indicators
ROUTER_MODEL_OK="FAIL"
CALIBRATION_MODEL_OK="FAIL"
LOCAL_MODELS_OK="FAIL"
INPUT_FILE_OK="FAIL"
OUTPUT_DIR_OK="FAIL"
VALIDATION_FAILED=false

# 1. Verify trained routing and calibration models exist
if [ -f "/app/backend/app/models/logistic_model.pkl" ]; then
  ROUTER_MODEL_OK="OK"
else
  echo "Error: Router model (/app/backend/app/models/logistic_model.pkl) not found!"
  VALIDATION_FAILED=true
fi

if [ -f "/app/backend/app/models/isotonic_model.pkl" ]; then
  CALIBRATION_MODEL_OK="OK"
else
  echo "Error: Calibration model (/app/backend/app/models/isotonic_model.pkl) not found!"
  VALIDATION_FAILED=true
fi

# 2. Verify local model configuration (if not in self-test mode)
if [ "$SELF_TEST" = "true" ]; then
  LOCAL_MODELS_OK="SKIP"
else
  if [ -n "${TERA_LOCAL_MODEL_NAME:-}" ] && [ -n "${TERA_POWER_MODEL_NAME:-}" ] && \
     [ -n "${TERA_LOCAL_INFERENCE_URL:-}" ] && [ -n "${TERA_POWER_INFERENCE_URL:-}" ]; then
    LOCAL_MODELS_OK="OK"
  else
    echo "Error: local fast/power model names and inference URLs must be configured."
    VALIDATION_FAILED=true
  fi
fi

# 3. Verify input file existence (if not in self-test mode)
if [ "$SELF_TEST" = "true" ]; then
  INPUT_FILE_OK="SKIP"
else
  if [ -f "/input/tasks.json" ]; then
    INPUT_FILE_OK="OK"
  else
    echo "Error: Input file (/input/tasks.json) not found!"
    VALIDATION_FAILED=true
  fi
fi

# 4. Verify output directory exists and is writable
# Create if missing
mkdir -p /output || { echo "Error: Failed to create /output directory!"; VALIDATION_FAILED=true; }

if [ "$VALIDATION_FAILED" = "false" ]; then
  if [ -w "/output" ]; then
    OUTPUT_DIR_OK="OK"
  else
    echo "Error: Output directory (/output) is not writable!"
    VALIDATION_FAILED=true
  fi
fi

# Print Diagnostics summary
echo ""
echo "===================================="
echo "TERA Track 1 Production"
echo ""
echo "Router Model ............ $ROUTER_MODEL_OK"
echo "Calibration Model ....... $CALIBRATION_MODEL_OK"
echo "Local Model Config ...... $LOCAL_MODELS_OK"
echo "Input File .............. $INPUT_FILE_OK"
echo "Output Directory ........ $OUTPUT_DIR_OK"
echo ""

if [ "$VALIDATION_FAILED" = "true" ]; then
  echo "Batch Harness ........... FAILED"
  echo "===================================="
  echo "Pre-flight validation failed. Exiting."
  exit 1
else
  echo "Batch Harness ........... READY"
  echo "===================================="
  echo "Launching TERA Batch Harness..."
  echo ""
fi

# Execute run_batch.py and pass all command-line arguments (propagating exit code)
exec python /app/backend/app/run_batch.py "$@"
