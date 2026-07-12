import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_accuracy_runner", ROOT / "scripts" / "run_public_accuracy_gate.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)

DATASET = runner.load_dataset(ROOT / "evaluation" / "public_validation_tasks.json")
ZERO = {field: 0 for field in runner.EXTERNAL_TELEMETRY_FIELDS}


def _passing_answers():
    from test_accuracy_gate import PASSING
    return PASSING


def _records():
    answers = _passing_answers()
    return [{"task_id": task["task_id"], "answer": answers[task["task_id"]], "telemetry": dict(ZERO)} for task in DATASET["tasks"]]


def test_offline_results_write_passing_report(tmp_path):
    results, report = tmp_path / "results.json", tmp_path / "report.json"
    results.write_text(json.dumps({"results": _records()}), encoding="utf-8")
    assert runner.main(["--results", str(results), "--report", str(report)]) == 0
    written = json.loads(report.read_text(encoding="utf-8"))
    assert written["status"] == "passed"
    assert written["accuracy"] == 1.0
    assert written["zero_external_usage"] is True


@pytest.mark.parametrize("failure", ["coverage", "telemetry", "accuracy"])
def test_offline_failures_exit_nonzero_and_write_report(tmp_path, failure):
    records = _records()
    if failure == "coverage":
        records.pop()
    elif failure == "telemetry":
        records[0]["telemetry"]["fireworks_tokens"] = 1
    else:
        records[0]["answer"] = "wrong"
    results, report = tmp_path / "results.json", tmp_path / "report.json"
    results.write_text(json.dumps(records), encoding="utf-8")
    assert runner.main(["--results", str(results), "--report", str(report)]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "failed"


def test_normalization_accepts_runtime_response_and_top_level_telemetry():
    record = {"id": "T02", "final_response": "1,672", **ZERO}
    assert runner.normalize_result(record) == {"task_id": "T02", "answer": "1,672", "telemetry": ZERO}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def test_endpoint_mode_posts_every_task_and_normalizes_results(tmp_path):
    answers = _passing_answers()
    calls = []

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data)
        task_id = payload["context"]["task_id"]
        calls.append((request.full_url, task_id, timeout))
        return _Response({"response": answers[task_id], "telemetry": ZERO})

    report = tmp_path / "report.json"
    with patch.object(runner, "urlopen", side_effect=fake_urlopen):
        code = runner.main(["--endpoint", "http://127.0.0.1:8000/route", "--report", str(report), "--timeout", "3"])
    assert code == 0
    assert len(calls) == len(DATASET["tasks"])
    assert all(timeout == 3 for _, _, timeout in calls)


def test_endpoint_must_be_local():
    with pytest.raises(ValueError, match="must be local"):
        runner.query_endpoint("https://example.com/route", DATASET["tasks"], 1)


def test_missing_explicit_external_telemetry_fails(tmp_path):
    records = _records()
    del records[0]["telemetry"]["external_api_calls"]
    results, report = tmp_path / "results.json", tmp_path / "report.json"
    results.write_text(json.dumps(records), encoding="utf-8")
    assert runner.main(["--results", str(results), "--report", str(report)]) == 1
    written = json.loads(report.read_text(encoding="utf-8"))
    assert "missing external telemetry fields" in written["error"]
