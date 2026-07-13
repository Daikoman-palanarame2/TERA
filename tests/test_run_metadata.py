from pathlib import Path

from app.utils.run_metadata import build_run_metadata, write_run_metadata


class Settings:
    tera_local_model_name = "google/gemma-4-E4B-it"
    tera_power_model_name = "google/gemma-4-26B-A4B-it"
    tera_local_inference_url = "http://127.0.0.1:8000/v1"
    tera_power_inference_url = "http://127.0.0.1:8001/v1"
    tera_cascade_enabled = True


def test_run_metadata_is_reproducible_and_local_only(tmp_path: Path) -> None:
    dataset = tmp_path / "tasks.json"
    dataset.write_text("[]", encoding="utf-8")
    metadata = build_run_metadata(str(dataset), Settings(), "cold")
    assert metadata["dataset_sha256"]
    assert metadata["cache_state"] == "cold"
    assert metadata["external_fallback_enabled"] is False
    assert metadata["feature_flags"]["cascade"] is True

    destination = tmp_path / "run_metadata.json"
    write_run_metadata(str(destination), metadata)
    assert destination.exists()
    assert not (tmp_path / "run_metadata.json.tmp").exists()

