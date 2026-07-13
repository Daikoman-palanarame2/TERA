import json

import pytest

from scripts.check_submission_output import validate


def test_submission_output_accepts_complete_exact_schema(tmp_path):
    input_path = tmp_path / "tasks.json"
    results_path = tmp_path / "results.json"
    input_path.write_text(json.dumps([{"task_id": "a", "prompt": "p"}]), encoding="utf-8")
    results_path.write_text(json.dumps([{"task_id": "a", "answer": "answer"}]), encoding="utf-8")

    validate(input_path, results_path)


@pytest.mark.parametrize(
    "results",
    [
        [],
        [{"task_id": "a", "answer": ""}],
        [{"task_id": "a", "answer": "ok", "telemetry": {}}],
        [{"task_id": "wrong", "answer": "ok"}],
    ],
)
def test_submission_output_rejects_incomplete_or_invalid_results(tmp_path, results):
    input_path = tmp_path / "tasks.json"
    results_path = tmp_path / "results.json"
    input_path.write_text(json.dumps([{"task_id": "a", "prompt": "p"}]), encoding="utf-8")
    results_path.write_text(json.dumps(results), encoding="utf-8")

    with pytest.raises(ValueError):
        validate(input_path, results_path)
