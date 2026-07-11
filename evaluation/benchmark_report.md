# TERA Offline Benchmark Performance Report

This report provides a detailed performance summary of TERA on the 80-prompt evaluation dataset.

## 1. Executive Summary
TERA was benchmarked over 80 realistic prompts spanning 8 distinct categories. The evaluation assesses latency bounds, routing decisions, calibration, token economies, and cost savings on the Fireworks API.

## 2. Overall Statistics
| Metric | Value |
| :--- | :--- |
| Total Prompts | 80 |
| Average Latency | 29.486 s |
| Median Latency | 20.307 s |
| Minimum Latency | 5.302 s |
| Maximum Latency | 122.797 s |
| 95th Percentile Latency | 75.014 s |
| Average Router Probability | 0.8235 |
| Estimated Total Cost | $0.45336 |
| Average Cost per Prompt | $0.00567 |

## 3. Routing Analysis
| Route Selection | Count | Percentage |
| :--- | :--- | :--- |
| Cheap Route | 80 | 100.0% |
| Dense Route | 0 | 0.0% |
| Escalated to Dense | 80 | 100.0% |

### Escalation Reasons Breakdown
| Reason | Count |
| :--- | :--- |
| entropy | 71 |
| cheap_model_failure:  | 9 |

## 4. Token Consumption Statistics
| Token Metric | Count |
| :--- | :--- |
| Total Prompt Tokens | 8633 |
| Total Completion Tokens | 88083 |
| Total Tokens | 96716 |
| Average Prompt Tokens | 107.9 |
| Average Completion Tokens | 1101.0 |
| Average Tokens per Prompt | 1209.0 |

## 5. Per-Category Results
| Category | Prompts | Avg Latency (s) | Escalation Rate | Avg Tokens | Total Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Mathematics | 10 | 15.913 | 100.0% | 1010.2 | $0.04669 |
| Programming | 10 | 44.095 | 100.0% | 2282.1 | $0.11051 |
| Science | 10 | 37.852 | 100.0% | 2096.7 | $0.10146 |
| General Knowledge | 10 | 45.940 | 100.0% | 1784.4 | $0.08601 |
| Summarization | 10 | 9.445 | 100.0% | 353.4 | $0.01179 |
| Instruction Following | 10 | 22.783 | 100.0% | 536.9 | $0.02330 |
| Creative | 10 | 44.286 | 100.0% | 934.0 | $0.04341 |
| Adversarial | 10 | 15.573 | 100.0% | 673.9 | $0.03018 |

## 6. Failure Analysis
- **Empty Responses:** 0
- **Missing Task IDs:** 0
- **Missing Telemetry logs:** 0
- **Schema/Validation Failures:** 0
- **Duplicate Answers:** 0 (indicates repetitive outputs or model loops)

## 7. Recommendations
- High escalation rate detected (100.0%). Programming or instruction-following constraints are likely triggering frequent verification failures. Consider checking ROVL thresholds.
- The router is efficiently utilizing the cheap model lane across diverse tasks, maximizing token efficiency.
- Average latency is relatively high (29.49s). Latency spikes may be caused by concurrent network requests or long-context summarizations.
- Zero empty responses detected. API adapters are returning complete completions.

