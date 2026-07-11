#!/bin/bash
set -e

echo "===================================="
echo "TERA Track 1 Production Startup"
echo "===================================="

# Check for web launcher mode (no arguments, or first argument is "web")
if [ $# -eq 0 ] || [ "$1" = "web" ]; then
  echo "Launching TERA Web Server on port 7860..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 7860
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
FIREWORKS_CONFIG_OK="FAIL"
ALLOWED_MODELS_OK="FAIL"
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

# 2. Verify Fireworks API configuration (if not in self-test mode)
if [ "$SELF_TEST" = "true" ]; then
  FIREWORKS_CONFIG_OK="SKIP"
else
  if [ -n "$FIREWORKS_API_KEY" ] && [ -n "$FIREWORKS_BASE_URL" ]; then
    FIREWORKS_CONFIG_OK="OK"
  else
    echo "Error: FIREWORKS_API_KEY or FIREWORKS_BASE_URL environment variables are not set!"
    VALIDATION_FAILED=true
  fi
fi

# 3. Verify ALLOWED_MODELS configuration (if not in self-test mode)
if [ "$SELF_TEST" = "true" ]; then
  ALLOWED_MODELS_OK="SKIP"
else
  if [ -n "$ALLOWED_MODELS" ]; then
    ALLOWED_MODELS_OK="OK"
  else
    echo "Error: ALLOWED_MODELS environment variable is not set!"
    VALIDATION_FAILED=true
  fi
fi

# 4. Verify input file existence (if not in self-test mode)
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

# 5. Verify output directory exists and is writable
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
echo "Fireworks Config ........ $FIREWORKS_CONFIG_OK"
echo "Allowed Models .......... $ALLOWED_MODELS_OK"
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
