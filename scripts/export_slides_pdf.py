"""Export rendered 16:9 slide PNGs as a presentation PDF."""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    slides = sorted(args.slides.glob("slide-*.png"))
    if not slides:
        raise SystemExit("no rendered slides found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    pdf = Canvas(str(args.output), pagesize=(width, height))
    for slide in slides:
        pdf.drawImage(str(slide), 0, 0, width=width, height=height)
        pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    main()
