"""Submission-path invariants for the zero-external-token build."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PRODUCTION_FILES = (
    ROOT / "backend/app/main.py",
    ROOT / "backend/app/run_batch.py",
    ROOT / "backend/app/api/router_inspector.py",
    ROOT / "backend/app/core/config.py",
    ROOT / "entrypoint.sh",
    ROOT / ".env.example",
)


def test_active_production_path_has_no_external_inference_configuration() -> None:
    forbidden = (
        "RemoteModelClient",
        "FireworksModel",
        "api.fireworks.ai",
        "FIREWORKS_API_KEY",
        "TERA_FIREWORKS_API_KEY",
    )
    violations: list[str] = []
    for path in ACTIVE_PRODUCTION_FILES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)} contains {token}")
    assert not violations, "\n".join(violations)


def test_runtime_settings_hard_disable_external_fallback() -> None:
    from app.core.config import settings

    assert settings.tera_external_fallback_enabled is False

