# TERA Utility Sensitivity Sweep Report

## Experiment Metadata
- **Execution Timestamp:** 2026-07-10T10:55:17.075477Z
- **Evaluated Dataset:** `C:\Users\MonMon\Desktop\TERA\backend\app\evaluation\sample_benchmark.csv`
- **Cheap Model Cost ($C_2$):** 10.0
- **Dense Model Cost ($C_max$ / $C_3$):** 100.0
- **Dense Baseline Accuracy ($\alpha_{dense}$):** 0.9
- **Trained Model Schema:** version 1.0.0
- **Trained Feature Schema:** version 1.0.0
- **Training Dataset Size:** 600 prompts
- **Scikit-learn Environment:** version 1.9.0


## Parameter Sensitivity Sweep Table
| $\lambda$ | Accuracy | Avg Cost | Avg Norm Cost | Cheap % | Cascade % | Dense % | Escalation % | False Cheap | False Dense | ECE | Brier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0.20 | 0.9407 | 49.33 | 0.4933 | 100.0% | 0.0% | 0.0% | 39.3% | 60 | 0 | 0.1264 | 0.2561 |
| 0.40 | 0.9407 | 49.33 | 0.4933 | 100.0% | 0.0% | 0.0% | 39.3% | 60 | 0 | 0.1264 | 0.2561 |
| 0.60 | 0.9407 | 49.33 | 0.4933 | 0.0% | 100.0% | 0.0% | 39.3% | 60 | 0 | 0.1264 | 0.2561 |
| 0.80 | 0.9407 | 49.33 | 0.4933 | 0.0% | 100.0% | 0.0% | 39.3% | 60 | 0 | 0.1264 | 0.2561 |
| 1.00 | 0.9407 | 49.33 | 0.4933 | 0.0% | 100.0% | 0.0% | 39.3% | 60 | 0 | 0.1264 | 0.2561 |


## Sensitivity Diagnostics & Observations
- **Frugality vs Accuracy Policy:** As $\lambda$ increases towards 1.0, the router places higher weight on task success probability, leading to higher rates of direct Dense/Cascade selections and higher average token costs.
- **Calibration Stability:** Check the ECE and Brier score across sweeps; stable calibration values indicate that the routing decisions remain sound across different policy trade-off parameters.