# ROCmRoute Zero Demo Script

Target length: 2-3 minutes.

## Recording sequence

1. Show the AMD notebook environment and say: "ROCmRoute Zero runs on AMD ROCm 7.2 with PyTorch 2.9 and vLLM 0.16.1."
2. Show `torch.cuda.is_available()` and the AMD GPU/VRAM output.
3. Show the local vLLM process serving `Qwen/Qwen2.5-Coder-7B-Instruct` on `127.0.0.1:8000`.
4. Show the ROCmRoute Zero architecture slide and explain the three layers: deterministic solvers, local Qwen generation, and deterministic verification/repair.
5. Run the public batch command and show that all 16 task IDs receive answers.
6. Run the public accuracy gate and show `accuracy: 1.0` and `zero_external_usage: true`.
7. Show telemetry totals: zero external tokens and zero external API calls.
8. Close with: "ROCmRoute Zero moves work to deterministic execution whenever possible and keeps all remaining inference local on AMD hardware."

## Commands to display

```bash
/opt/venv/bin/python -c "import torch,vllm; print(torch.__version__, torch.version.hip, vllm.__version__, torch.cuda.is_available())"

PYTHONPATH=backend python backend/app/run_batch.py \
  --input evaluation/public_validation_tasks_flat.json \
  --output output/amd_qwen7b_results.json

PYTHONPATH=backend python scripts/run_public_accuracy_gate.py \
  --results output/amd_qwen7b_results.json \
  --telemetry output/telemetry.json \
  --report output/amd_qwen7b_accuracy_report.json
```

Do not claim that public validation guarantees hidden leaderboard accuracy.
