#!/usr/bin/env python3
"""Generate deterministic modern-documentary support assets.

The banknote is a 2:1 textured sprite for the macro UI rain. It is intentionally
abstract (no real currency, no political marks): a green security-paper field,
a circular seal, a border and a large "$" watermark. Regenerating the script
produces byte-identical output when Pillow's PNG encoder version is unchanged.

Usage:
    python3 tools/web_styles/generate_modern_documentary_assets.py [--out DIR]
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 384, 192
PAPER = (118, 156, 112, 255)
INK = (30, 58, 38, 255)
LIGHT = (196, 214, 174, 255)


def font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("assets/modern_documentary"),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(20261114)
    image = Image.new("RGBA", (W, H), PAPER)
    draw = ImageDraw.Draw(image)

    # Security-paper fiber wash.
    for _ in range(900):
        x, y = rng.randrange(W), rng.randrange(H)
        value = rng.randrange(96, 176)
        draw.point((x, y), fill=(value, value + 24, value - 12, 70))

    # Guilloche-style arcs.
    for radius in (54, 66, 78):
        draw.arc((W // 2 - radius * 2, H // 2 - radius, W // 2 + radius * 2, H // 2 + radius),
                 start=8, end=172, fill=LIGHT, width=2)
        draw.arc((W // 2 - radius * 2, H // 2 - radius, W // 2 + radius * 2, H // 2 + radius),
                 start=188, end=352, fill=INK, width=1)

    # Portrait oval / seal on the left.
    draw.ellipse((34, 42, 118, 150), outline=INK, width=5)
    draw.ellipse((46, 56, 106, 136), outline=LIGHT, width=2)
    draw.ellipse((58, 74, 94, 118), fill=(88, 126, 92, 255), outline=INK, width=2)
    draw.arc((54, 60, 100, 118), start=200, end=340, fill=INK, width=3)

    # Big denomination watermark.
    draw.text((158, 18), "$10,000", font=font(62), fill=(235, 242, 216, 235),
              stroke_width=2, stroke_fill=INK)
    draw.text((166, 96), "ATTENTION NOTE", font=font(21), fill=INK)
    draw.text((166, 126), "SERIES / 05", font=font(18), fill=(52, 84, 58, 255))
    draw.text((166, 150), "NON-NEGOTIABLE", font=font(15), fill=(52, 84, 58, 255))

    # Denomination corners.
    small = font(20)
    for x, y in ((20, 12), (W - 86, 12), (20, H - 38), (W - 86, H - 38)):
        draw.text((x, y), "10K", font=small, fill=INK)

    # Paper border and irregular inner line.
    draw.rectangle((2, 2, W - 3, H - 3), outline=(225, 236, 202, 230), width=3)
    draw.rectangle((10, 10, W - 11, H - 11), outline=INK, width=2)
    for i in range(0, W, 16):
        draw.line((i, 16, min(W, i + 6), 16), fill=LIGHT, width=1)
        draw.line((i, H - 17, min(W, i + 6), H - 17), fill=LIGHT, width=1)

    # Fine rotation-friendly vertical serial.
    serial = "AT 05 1114 0001"
    for index, char in enumerate(serial):
        draw.text((W - 34, 42 + index * 13), char, font=font(11), fill=INK)

    # Very subtle diagonal specular band: keeps tumbling readable in motion.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for x in range(-H, W, 28):
        odraw.line((x, H, x + H, 0), fill=(255, 255, 255, 16), width=10)
    image = Image.alpha_composite(image, overlay)

    # The renderer sizes sprite particles as squares. Keep the note 2:1 inside
    # a transparent square canvas so the texture is not stretched.
    square = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    square.alpha_composite(image, (0, (W - H) // 2))
    out = args.out / "banknote.png"
    square.save(out, optimize=True)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
