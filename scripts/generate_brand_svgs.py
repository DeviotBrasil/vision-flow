#!/usr/bin/env python3
"""Gera SVGs de marca a partir dos PNGs-fonte em ``packaging/brand/``."""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = PROJECT_ROOT / "packaging" / "brand"
ICON_OUT = (
    PROJECT_ROOT
    / "src"
    / "visionflow"
    / "presentation"
    / "resources"
    / "icons"
    / "icon_app.svg"
)
LOGO_OUT = (
    PROJECT_ROOT
    / "src"
    / "visionflow"
    / "presentation"
    / "resources"
    / "images"
    / "logo.svg"
)


def _png_to_embedded_svg(
    png_path: Path,
    svg_path: Path,
    *,
    square: bool = False,
) -> None:
    image = Image.open(png_path)
    width, height = image.size
    encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")

    if square:
        size = max(width, height)
        x = (size - width) // 2
        y = (size - height) // 2
        view_box = f"0 0 {size} {size}"
        image_tag = (
            f'  <image x="{x}" y="{y}" width="{width}" height="{height}" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'href="data:image/png;base64,{encoded}"/>'
        )
    else:
        view_box = f"0 0 {width} {height}"
        image_tag = (
            f'  <image width="{width}" height="{height}" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'href="data:image/png;base64,{encoded}"/>'
        )

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg viewBox="{view_box}" fill="none" xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        f"{image_tag}\n"
        "</svg>\n"
    )
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")
    print(f"Gerado: {svg_path.relative_to(PROJECT_ROOT)}")


def main() -> int:
    favicon = BRAND_DIR / "favicon.png"
    logo = BRAND_DIR / "logo.png"
    missing = [path.name for path in (favicon, logo) if not path.is_file()]
    if missing:
        print(
            f"PNG ausente em {BRAND_DIR}: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    _png_to_embedded_svg(favicon, ICON_OUT, square=True)
    _png_to_embedded_svg(logo, LOGO_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
