"""Reproducibility metadata for benchmark and submission rehearsals."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any


def build_run_metadata(dataset_path: str, settings: Any, cache_state: str) -> dict[str, Any]:
    """Describe the exact local-only configuration used for one batch run."""
    dataset = Path(dataset_path)
    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "run_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset),
        "dataset_sha256": digest,
        "cache_state": cache_state,
        "fast_model": settings.tera_local_model_name,
        "power_model": settings.tera_power_model_name,
        "fast_endpoint": settings.tera_local_inference_url,
        "power_endpoint": settings.tera_power_inference_url,
        "external_fallback_enabled": False,
        "feature_flags": {
            "cascade": bool(getattr(settings, "tera_cascade_enabled", False)),
            "cisc": bool(getattr(settings, "tera_cisc_enabled", False)),
            "refinement": bool(getattr(settings, "tera_refinement_enabled", False)),
            "enriched_handoff": bool(
                getattr(settings, "tera_enriched_handoff_enabled", False)
            ),
        },
    }


def write_run_metadata(path: str, metadata: dict[str, Any]) -> None:
    """Write metadata atomically beside result and telemetry artifacts."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    temporary.replace(target)

