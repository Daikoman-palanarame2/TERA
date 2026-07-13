"""Check both local vLLM tiers before starting a submission batch."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.inference.readiness import check_vllm_endpoint


async def main_async() -> list[dict[str, object]]:
    minimum = os.getenv("TERA_MIN_VLLM_VERSION", "0.19.0")
    timeout = float(os.getenv("TERA_READINESS_TIMEOUT_SEC", "15"))
    return await asyncio.gather(
        check_vllm_endpoint(
            os.getenv("TERA_LOCAL_INFERENCE_URL", "http://127.0.0.1:8000/v1"),
            os.environ["TERA_LOCAL_MODEL_NAME"],
            minimum,
            timeout,
        ),
        check_vllm_endpoint(
            os.getenv("TERA_POWER_INFERENCE_URL", "http://127.0.0.1:8001/v1"),
            os.environ["TERA_POWER_MODEL_NAME"],
            minimum,
            timeout,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args()
    try:
        results = asyncio.run(main_async())
    except Exception as error:
        print(f"Local model readiness failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2) if args.json else "Local model readiness passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
