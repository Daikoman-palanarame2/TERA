"""Deterministic offline accuracy gate for retired Track 1 validation tasks."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


EXTERNAL_TELEMETRY_FIELDS = ("fireworks_tokens", "external_tokens", "m3_tokens", "external_api_calls")


def load_dataset(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_dataset(data)
    return data


def validate_dataset(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != 1 or not isinstance(data.get("tasks"), list):
        raise ValueError("accuracy dataset must use schema_version 1 and contain a tasks list")
    ids: set[str] = set()
    for task in data["tasks"]:
        required = ("task_id", "source_id", "category", "prompt", "grader")
        if not isinstance(task, dict) or any(not task.get(key) for key in required):
            raise ValueError("every task must contain non-empty task_id, source_id, category, prompt, grader")
        if task["task_id"] in ids:
            raise ValueError(f"duplicate task_id: {task['task_id']}")
        ids.add(task["task_id"])


def _contains_any(text: str, alternatives: Sequence[str]) -> bool:
    return any(item.casefold() in text.casefold() for item in alternatives)


def _numbers(text: str) -> list[float]:
    return [float(value.replace(",", "")) for value in re.findall(r"(?<!\w)[+-]?(?:\d[\d,]*\.?\d*|\.\d+)", text)]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def grade_answer(task: Mapping[str, Any], answer: str) -> bool:
    if not isinstance(answer, str) or not answer.strip():
        return False
    grader = task["grader"]
    kind = grader["type"]
    if kind == "keyword_groups":
        return all(_contains_any(answer, group) for group in grader["groups"])
    if kind == "numbers":
        found, tolerance = _numbers(answer), float(grader.get("tolerance", 0.001))
        return all(any(math.isclose(value, expected, abs_tol=tolerance) for value in found) for expected in grader["required"])
    if kind == "balanced_sentiment":
        first = answer.strip().split(maxsplit=1)[0].strip("#:,-.").casefold()
        return first in grader["labels"] and _contains_any(answer, grader["negative"]) and _contains_any(answer, grader["positive"]) and len(_sentences(answer)) == 1
    if kind == "sentence_summary":
        return len(_sentences(answer)) == grader["count"] and all(_contains_any(answer, group) for group in grader["concept_groups"])
    if kind == "bullet_summary":
        bullets = [line.strip()[1:].strip() for line in answer.splitlines() if re.match(r"^\s*[-*]\s+", line)]
        return len(bullets) == grader["count"] and all(len(re.findall(r"\b[\w'-]+\b", bullet)) <= grader["max_words"] for bullet in bullets) and all(_contains_any(answer, group) for group in grader["concept_groups"])
    if kind == "entities":
        return all(
            re.search(
                rf"(?:{re.escape(name)}\s*.{{0,12}}\b{re.escape(label)}\b|\b{re.escape(label)}\b.{{0,12}}{re.escape(name)})",
                answer,
                flags=re.IGNORECASE,
            )
            is not None
            for name, label in grader["entities"].items()
        )
    raise ValueError(f"unknown grader type: {kind}")


def assert_zero_external_telemetry(telemetry: Mapping[str, Any]) -> None:
    missing = [field for field in EXTERNAL_TELEMETRY_FIELDS if field not in telemetry]
    if missing:
        raise AssertionError(f"missing external telemetry fields: {', '.join(missing)}")
    nonzero = {field: telemetry[field] for field in EXTERNAL_TELEMETRY_FIELDS if telemetry[field] != 0}
    if nonzero:
        raise AssertionError(f"external usage must be zero: {nonzero}")


def evaluate_results(dataset: Mapping[str, Any], results: Sequence[Mapping[str, Any]], minimum_accuracy: float = 0.99) -> dict[str, Any]:
    validate_dataset(dataset)
    if not 0.0 <= minimum_accuracy <= 1.0:
        raise ValueError("minimum_accuracy must be between 0 and 1")
    by_id: dict[str, Mapping[str, Any]] = {}
    for result in results:
        task_id = result.get("task_id")
        if not isinstance(task_id, str) or task_id in by_id:
            raise ValueError("results require unique string task_id values")
        by_id[task_id] = result
    expected = {task["task_id"] for task in dataset["tasks"]}
    missing, unexpected = sorted(expected - by_id.keys()), sorted(by_id.keys() - expected)
    if missing or unexpected:
        raise AssertionError(f"task coverage mismatch; missing={missing}, unexpected={unexpected}")
    passed: list[str] = []
    failed: list[str] = []
    for task in dataset["tasks"]:
        result = by_id[task["task_id"]]
        assert_zero_external_telemetry(result.get("telemetry", {}))
        (passed if grade_answer(task, result.get("answer", "")) else failed).append(task["task_id"])
    accuracy = len(passed) / len(dataset["tasks"]) if dataset["tasks"] else 0.0
    return {"passed": accuracy >= minimum_accuracy, "accuracy": accuracy, "passed_tasks": passed, "failed_tasks": failed, "total_tasks": len(dataset["tasks"]), "zero_external_usage": True}
