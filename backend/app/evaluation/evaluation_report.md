# TERA (Token-Efficient Routing Agent) Evaluation Report

## Overview
This report evaluates the performance of TERA against three baseline routing strategies on a benchmark dataset of size **150** prompts.

## Strategy Performance Comparison Table
| Routing Strategy | Blended Accuracy | Avg Token Cost | Avg Normalized Cost |
| :--- | :--- | :--- | :--- |
| **TERA (Calibrated Utility)** | **0.9407** | **49.33** | **0.4933** |
| Always Cheap model lane ($M_2$) | 0.6000 | 10.00 | 0.1000 |
| Always Dense model lane ($M_3$) | 0.9000 | 100.00 | 1.0000 |
| Random Routing (50/50) | 0.7413 | 50.80 | 0.5080 |

## Key Insights
- **Cost Savings:** TERA achieved **50.67%** token cost savings compared to the Always Dense model baseline while maintaining a calibrated utility trade-off.
- **Blended Accuracy Score:** TERA achieved an average accuracy of **0.9407**.

## TERA Routing Diagnostics & Confusion Statistics
### Router Decisions Distribution
- **Direct Cheap Routes ($M_2$):** 100.00%
- **Direct Dense Routes ($M_3$):** 0.00%
- **Cascade Routes ($M_2 \rightarrow M_3$):** 0.00%

### ROVL Verification Metrics
- **Automatic Escalation Rate:** 39.33%

### Routing Confusion Metrics
- **False Cheap Decisions:** 60
  *(Router selected CHEAP/CASCADE but the cheap model output failed ROVL verification)*
- **False Dense Decisions:** 0
  *(Router selected DENSE directly but the cheap model would have passed verification)*

### Efficiency & Calibration
- **Average Routing + Model Latency:** 0.00 ms
- **Expected Calibration Error (ECE):** 0.1264
- **Brier Score:** 0.2561
