# TERA Presentation Copy & Slide Assets

Use the following verified statistics directly in your presentation slides.

## Slide 1: Core Performance Metrics
- **Total Benchmark Prompts:** 80
- **Total Execution Categories:** 8 distinct task types
- **Total Tokens Consumed:** 96,716 tokens
- **Average Token Density:** 1209.0 tokens per prompt
- **Total API Cost:** $0.45336
- **Average Cost per Prompt:** $0.00567

## Slide 2: Pipeline Execution Latency
- **TERA Router Decision Latency:** < 0.20 ms (CPU only)
- **ROVL Output Verification Latency:** < 1.0 ms
- **Average API Latency:** 29.49 seconds
- **Median API Latency:** 20.31 seconds
- **Max API Latency:** 122.80 seconds

## Slide 3: Routing & Calibration Ratios
- **Cheap Lane Selections:** 80 / 80 (100.0%)
- **Dense Lane Selections:** 0 / 80 (0.0%)
- **ROVL Cascade Escalations:** 80 / 80 (100.0%)
- **Reason 1: Sequence Entropy Exception:** 71 triggers (88.8%)
- **Reason 2: Endpoint Read Timeouts:** 9 triggers (11.2%)

## Slide 4: Testing & Reliability Verification
- **Unit and Integration Test Count:** 64 tests
- **Verification Pass Rate:** 100% Passed (64/64)
- **Production Self-Test Status:** Passed
- **Container Packaging Target:** linux/amd64 (Multi-stage build succeeded)
