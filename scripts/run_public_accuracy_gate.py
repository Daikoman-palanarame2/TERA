#!/usr/bin/env python3
"""Run the retired Track 1 accuracy gate against a local endpoint or results file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.evaluation.accuracy_gate import (  # noqa: E402
    EXTERNAL_TELEMETRY_FIELDS,
    evaluate_results,
    load_dataset,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation" / "public_validation_tasks.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--results", type=Path, help="Existing JSON result list or {'results': [...]} file")
    source.add_argument("--endpoint", help="Local TERA route URL, for example http://127.0.0.1:8000/route")
    parser.add_argument("--telemetry", type=Path, help="Path to the matching telemetry file")
    parser.add_argument("--report", type=Path, default=ROOT / "evaluation" / "public_accuracy_report.json")
    parser.add_argument("--threshold", type=float, default=0.99)
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request HTTP timeout in seconds")
    return parser


def _telemetry(record: Mapping[str, Any]) -> dict[str, Any]:
    nested = record.get("telemetry")
    telemetry = dict(nested) if isinstance(nested, Mapping) else {}
    for field in EXTERNAL_TELEMETRY_FIELDS:
        if field in record and field not in telemetry:
            telemetry[field] = record[field]
    return telemetry


def normalize_result(record: Mapping[str, Any], expected_task_id: str | None = None) -> dict[str, Any]:
    task_id = record.get("task_id", record.get("id", expected_task_id))
    answer = record.get("answer", record.get("response", record.get("final_response")))
    if not isinstance(task_id, str) or not task_id or not isinstance(answer, str):
        raise ValueError("each result requires a string task_id and answer/response/final_response")
    return {"task_id": task_id, "answer": answer, "telemetry": _telemetry(record)}


def load_results_and_telemetry(results_path: Path, telemetry_path: Path | None) -> list[dict[str, Any]]:
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found at: {results_path}")

    raw_res = json.loads(results_path.read_text(encoding="utf-8"))
    res_records = raw_res.get("results") if isinstance(raw_res, dict) else raw_res
    if not isinstance(res_records, list) or not all(isinstance(item, dict) for item in res_records):
        raise ValueError("results file must be a JSON list or an object containing a results list")

    # If telemetry_path is NOT provided, fallback to inline telemetry validation (backward compatibility)
    if not telemetry_path:
        results = []
        res_task_ids = []
        for item in res_records:
            norm_item = normalize_result(item)
            task_id = norm_item["task_id"]
            res_task_ids.append(task_id)
            
            # Verify required inline fields exist and are exactly 0
            tel = norm_item["telemetry"]
            for fld in EXTERNAL_TELEMETRY_FIELDS:
                if fld not in tel:
                    raise ValueError(f"missing external telemetry fields: {fld}")
                val = tel[fld]
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise TypeError(f"Field '{fld}' must be a number")
                if int(val) != 0:
                    raise ValueError(f"Field '{fld}' must be exactly 0, got {val}")
            results.append(norm_item)
            
        if len(res_task_ids) != len(set(res_task_ids)):
            raise ValueError("Duplicate task IDs found in results file")
        return results

    # If telemetry_path is explicitly provided, enforce the strict join schema
    if not telemetry_path.exists():
        raise FileNotFoundError(f"Telemetry file not found at: {telemetry_path}")

    raw_tel_content = telemetry_path.read_text(encoding="utf-8").strip()
    if raw_tel_content.startswith("["):
        raw_tel = json.loads(raw_tel_content)
        tel_records = raw_tel.get("telemetry") if isinstance(raw_tel, dict) else raw_tel
    else:
        tel_records = [json.loads(line) for line in raw_tel_content.splitlines() if line.strip()]
        
    if not isinstance(tel_records, list) or not all(isinstance(item, dict) for item in tel_records):
        raise ValueError("telemetry file must be a JSON list or JSON Lines format")

    # Check for duplicate task IDs in results
    res_task_ids = []
    for item in res_records:
        task_id = item.get("task_id", item.get("id"))
        if not task_id:
            raise ValueError("each result requires a task_id")
        res_task_ids.append(task_id)
    if len(res_task_ids) != len(set(res_task_ids)):
        raise ValueError("Duplicate task IDs found in results file")

    # Check for duplicate task IDs in telemetry
    tel_task_ids = []
    for item in tel_records:
        task_id = item.get("task_id", item.get("id"))
        if not task_id:
            raise ValueError("each telemetry record requires a task_id")
        tel_task_ids.append(task_id)
    if len(tel_task_ids) != len(set(tel_task_ids)):
        raise ValueError("Duplicate task IDs found in telemetry file")

    # Match sets exactly
    if set(res_task_ids) != set(tel_task_ids):
        raise ValueError(
            f"Mismatched task IDs between results and telemetry. "
            f"Results: {sorted(list(res_task_ids))}. Telemetry: {sorted(list(tel_task_ids))}"
        )

    # Validate and Join
    telemetry_map = {item.get("task_id", item.get("id")): item for item in tel_records}
    results = []
    for item in res_records:
        task_id = item.get("task_id", item.get("id"))
        answer = item.get("answer", item.get("response", item.get("final_response")))
        if not isinstance(task_id, str) or not task_id or not isinstance(answer, str):
            raise ValueError("each result requires a string task_id and answer")
        
        tel_item = telemetry_map[task_id]
        
        # Verify required external fields exist, are correct type, and are exactly 0
        for fld in EXTERNAL_TELEMETRY_FIELDS:
            if fld not in tel_item:
                raise ValueError(f"Missing required telemetry field '{fld}' for task_id '{task_id}'")
            val = tel_item[fld]
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"Field '{fld}' for task_id '{task_id}' must be a number, got {type(val)}")
            if int(val) != 0:
                raise ValueError(f"Field '{fld}' for task_id '{task_id}' must be exactly 0, got {val}")

        results.append({
            "task_id": task_id,
            "answer": answer,
            "telemetry": _telemetry(tel_item)
        })
    return results


def join_endpoint_results_with_telemetry(endpoint_res: list[dict[str, Any]], telemetry_path: Path | None) -> list[dict[str, Any]]:
    if not telemetry_path:
        raise ValueError("The --telemetry path must be explicitly provided to verify telemetry when querying endpoint.")
    if not telemetry_path.exists():
        raise FileNotFoundError(f"Telemetry file not found at: {telemetry_path}")

    raw_tel_content = telemetry_path.read_text(encoding="utf-8").strip()
    if raw_tel_content.startswith("["):
        raw_tel = json.loads(raw_tel_content)
        tel_records = raw_tel.get("telemetry") if isinstance(raw_tel, dict) else raw_tel
    else:
        tel_records = [json.loads(line) for line in raw_tel_content.splitlines() if line.strip()]
        
    if not isinstance(tel_records, list) or not all(isinstance(item, dict) for item in tel_records):
        raise ValueError("telemetry file must be a JSON list or JSON Lines format")

    # Detect duplicates in telemetry
    tel_task_ids = []
    for item in tel_records:
        task_id = item.get("task_id", item.get("id"))
        if not task_id:
            raise ValueError("each telemetry record requires a task_id")
        tel_task_ids.append(task_id)
    if len(tel_task_ids) != len(set(tel_task_ids)):
        raise ValueError("Duplicate task IDs found in telemetry file")

    # Check matches
    res_task_ids = [item["task_id"] for item in endpoint_res]
    if set(res_task_ids) != set(tel_task_ids):
        raise ValueError(
            f"Mismatched task IDs between endpoint results and telemetry. "
            f"Results: {sorted(list(res_task_ids))}. Telemetry: {sorted(list(tel_task_ids))}"
        )

    telemetry_map = {item.get("task_id", item.get("id")): item for item in tel_records}
    results = []
    for item in endpoint_res:
        task_id = item["task_id"]
        answer = item["answer"]
        tel_item = telemetry_map[task_id]
        
        # Verify required external fields exist, are correct type, and are exactly 0
        for fld in EXTERNAL_TELEMETRY_FIELDS:
            if fld not in tel_item:
                raise ValueError(f"Missing required telemetry field '{fld}' for task_id '{task_id}'")
            val = tel_item[fld]
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"Field '{fld}' for task_id '{task_id}' must be a number, got {type(val)}")
            if int(val) != 0:
                raise ValueError(f"Field '{fld}' for task_id '{task_id}' must be exactly 0, got {val}")

        results.append({
            "task_id": task_id,
            "answer": answer,
            "telemetry": _telemetry(tel_item)
        })
    return results


def query_endpoint(endpoint: str, tasks: Sequence[Mapping[str, Any]], timeout: float) -> list[dict[str, Any]]:
    if not endpoint.startswith(("http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost")):
        raise ValueError("accuracy gate endpoint must be local (localhost or 127.0.0.1)")
    results = []
    for task in tasks:
        payload = json.dumps({"prompt": task["prompt"], "context": {"task_id": task["task_id"]}}).encode("utf-8")
        request = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                record = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"local endpoint failed for {task['task_id']}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"endpoint response for {task['task_id']} must be a JSON object")
        
        results.append(normalize_result(record, expected_task_id=task["task_id"]))
    return results


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        dataset = load_dataset(args.dataset)
        if args.results:
            results = load_results_and_telemetry(args.results, args.telemetry)
        else:
            endpoint_res = query_endpoint(args.endpoint, dataset["tasks"], args.timeout)
            if args.telemetry:
                results_only = [{"task_id": r["task_id"], "answer": r["answer"]} for r in endpoint_res]
                results = join_endpoint_results_with_telemetry(results_only, args.telemetry)
            else:
                for r in endpoint_res:
                    tel = r["telemetry"]
                    for fld in EXTERNAL_TELEMETRY_FIELDS:
                        if fld not in tel:
                            raise ValueError(f"missing external telemetry fields: {fld}")
                        val = tel[fld]
                        if not isinstance(val, (int, float)) or isinstance(val, bool):
                            raise TypeError(f"Field '{fld}' must be a number")
                        if int(val) != 0:
                            raise ValueError(f"Field '{fld}' must be exactly 0, got {val}")
                results = endpoint_res
        report = evaluate_results(dataset, results, minimum_accuracy=args.threshold)
        report = {"status": "passed" if report["passed"] else "failed", "threshold": args.threshold, **report}
    except Exception as exc:
        report = {"status": "failed", "threshold": args.threshold, "error": str(exc), "zero_external_usage": False}
        write_report(args.report, report)
        print(json.dumps(report, sort_keys=True), file=sys.stderr)
        return 1
    write_report(args.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
