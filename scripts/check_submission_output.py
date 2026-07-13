"""Fail a leaderboard run if results.json is incomplete or schema-invalid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _rows(value: Any, *, name: str) -> list[dict[str, Any]]:
    if isinstance(value, dict) and isinstance(value.get("tasks"), list):
        value = value["tasks"]
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{name} must be a JSON list of objects")
    return value


def validate(input_path: Path, results_path: Path) -> None:
    tasks = _rows(json.loads(input_path.read_text(encoding="utf-8")), name="input")
    results = _rows(json.loads(results_path.read_text(encoding="utf-8")), name="results")

    expected_ids = [row.get("task_id") for row in tasks]
    result_ids = [row.get("task_id") for row in results]
    if any(not isinstance(task_id, str) or not task_id for task_id in expected_ids):
        raise ValueError("every input task must have a non-empty string task_id")
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError("input contains duplicate task_id values")
    if len(set(result_ids)) != len(result_ids):
        raise ValueError("results contain duplicate task_id values")
    if result_ids != expected_ids:
        raise ValueError("results must preserve every input task_id in input order")

    for index, row in enumerate(results):
        if set(row) != {"task_id", "answer"}:
            raise ValueError(f"result {index} must contain only task_id and answer")
        if not isinstance(row["answer"], str) or not row["answer"].strip():
            raise ValueError(f"result {row['task_id']} has an empty answer")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    validate(args.input, args.results)
    print("Submission output validation passed.")


if __name__ == "__main__":
    main()

