import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.accuracy_gate import (  # noqa: E402
    assert_zero_external_telemetry,
    evaluate_results,
    grade_answer,
    load_dataset,
    validate_dataset,
)


DATASET_PATH = ROOT / "evaluation" / "public_validation_tasks.json"
ZERO = {"fireworks_tokens": 0, "external_tokens": 0, "m3_tokens": 0, "external_api_calls": 0}


PASSING = {
    "T01": "Red, green, and blue; displays emit light using additive mixing, unlike subtractive pigment mixing.",
    "T01b": "Deep learning is a subset of machine learning using a multi-layer neural network. Traditional ML often needs manual feature engineering, while deep learning automatically extracts features.",
    "T01c": "RAM (random access memory) is fast, volatile temporary storage for active programs; ROM (read-only memory) is non-volatile storage for firmware or BIOS.",
    "T02": "1,672 units remain.",
    "T02b": "The recipe needs 1.875 cups and costs $4.50.",
    "T03": "Mixed: Although delivery was late and packaging damaged, it worked perfectly and support resolved the issue.",
    "T03b": "Positive: Despite the dented box and missing manual, the flawless device had a fast setup.",
    "T04": "Machine learning helps healthcare diagnosis and other clinical work. Privacy, bias, liability, and regulatory lag remain challenges.",
    "T04b": "- Flexibility and shorter commutes improve work-life balance.\n- Collaboration, culture, and blurred boundaries remain difficult.\n- Organisations adopt digital tools and rethink office workspace.",
    "T05": "Sundar Pichai — PERSON; March 15 2023 — DATE; Google — ORGANIZATION; Zurich — LOCATION; ETH Zurich — ORGANIZATION.",
    "A02_01": "1,275",
    "A02_02": "2,350 units",
    "A02b_01": "1.5 cups costing $4.50.",
    "A03_01": "Mixed: Shipping was slow and the box torn, but the laptop works beautifully and support refunded delivery.",
    "A04b_01": "- Solar power provides clean, low emissions energy.\n- Intermittency makes supply variable.\n- Storage investment and batteries improve reliability.",
    "A05_01": "Satya Nadella: PERSON; July 4 2025: DATE; Microsoft: ORGANIZATION; Singapore: LOCATION; NUS: ORGANIZATION.",
}


def _results(dataset, answers=PASSING):
    return [{"task_id": task["task_id"], "answer": answers[task["task_id"]], "telemetry": dict(ZERO)} for task in dataset["tasks"]]


def test_dataset_is_valid_and_covers_every_retired_track_one_task():
    dataset = load_dataset(DATASET_PATH)
    source_ids = {task["source_id"] for task in dataset["tasks"]}
    assert {"T01", "T01b", "T01c", "T02", "T02b", "T03", "T03b", "T04", "T04b", "T05"} <= source_ids
    assert len(dataset["tasks"]) > len(source_ids)


@pytest.mark.parametrize("task_id", sorted(PASSING))
def test_defensible_reference_answers_pass(task_id):
    dataset = load_dataset(DATASET_PATH)
    task = next(task for task in dataset["tasks"] if task["task_id"] == task_id)
    assert grade_answer(task, PASSING[task_id])


def test_accuracy_aggregation_and_gate_threshold():
    dataset = load_dataset(DATASET_PATH)
    report = evaluate_results(dataset, _results(dataset))
    assert report == {
        "passed": True,
        "accuracy": 1.0,
        "passed_tasks": [task["task_id"] for task in dataset["tasks"]],
        "failed_tasks": [],
        "total_tasks": len(dataset["tasks"]),
        "zero_external_usage": True,
    }
    results = _results(dataset)
    results[0]["answer"] = "Incorrect"
    assert evaluate_results(dataset, results, minimum_accuracy=0.99)["passed"] is False


def test_format_constraints_reject_wrong_sentence_and_bullet_counts():
    dataset = load_dataset(DATASET_PATH)
    tasks = {task["task_id"]: task for task in dataset["tasks"]}
    assert not grade_answer(tasks["T04"], "Healthcare diagnosis improves, but privacy, bias, and regulation are challenging.")
    assert not grade_answer(tasks["T04b"], "- Flexibility helps.\n- Collaboration and culture suffer; digital tools reshape offices.")
    assert not grade_answer(tasks["T03"], "Negative: Delivery was late and damaged. Support resolved it.")
    assert not grade_answer(tasks["T05"], "Sundar Pichai — LOCATION; March 15 2023 — DATE; Google — ORGANIZATION; Zurich — PERSON; ETH Zurich — ORGANIZATION.")


def test_task_coverage_is_exact():
    dataset = load_dataset(DATASET_PATH)
    with pytest.raises(AssertionError, match="task coverage mismatch"):
        evaluate_results(dataset, _results(dataset)[:-1])
    duplicated = _results(dataset) + [_results(dataset)[0]]
    with pytest.raises(ValueError, match="unique string task_id"):
        evaluate_results(dataset, duplicated)


@pytest.mark.parametrize("field", ["fireworks_tokens", "external_tokens", "m3_tokens", "external_api_calls"])
def test_external_usage_is_explicitly_zero(field):
    telemetry = dict(ZERO)
    telemetry[field] = 1
    with pytest.raises(AssertionError, match="external usage must be zero"):
        assert_zero_external_telemetry(telemetry)
    missing = dict(ZERO)
    del missing[field]
    with pytest.raises(AssertionError, match="missing external telemetry fields"):
        assert_zero_external_telemetry(missing)


def test_dataset_rejects_duplicate_ids(tmp_path):
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    data["tasks"].append(dict(data["tasks"][0]))
    with pytest.raises(ValueError, match="duplicate task_id"):
        validate_dataset(data)
