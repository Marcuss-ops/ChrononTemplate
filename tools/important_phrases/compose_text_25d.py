#!/usr/bin/env python3
"""Turn Chronon's GPU text pass into a focused, beveled 2.5D title PNG."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


def shifted(mask: Image.Image, dx: int, dy: int) -> Image.Image:
    return mask.transform(
        mask.size, Image.Transform.AFFINE,
        (1, 0, -dx, 0, 1, -dy), Image.Resampling.BICUBIC, fillcolor=0,
    )


def tint(dst: Image.Image, mask: Image.Image, color: tuple[int, int, int], opacity: float) -> None:
    alpha = mask.point(lambda value: round(value * opacity))
    layer = Image.new("RGBA", dst.size, (*color, 0))
    layer.putalpha(alpha)
    dst.alpha_composite(layer)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-render", type=Path, required=True)
    parser.add_argument("--gpu-background", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rendered = Image.open(args.gpu_render).convert("RGB")
    background = Image.open(args.gpu_background).convert("RGB")
    if rendered.size != background.size:
        raise ValueError("GPU text render and GPU background must have the same dimensions")

    # Chronon renders the glyph geometry and blurred image plate on Vulkan.
    # Recover the glyph alpha from the difference between its text and clean BG passes.
    delta = ImageOps.grayscale(ImageChops.difference(rendered, background))
    mask = delta.point(lambda value: 0 if value <= 1 else min(255, (value - 1) * 22))
    mask = mask.filter(ImageFilter.MaxFilter(3))
    if mask.getbbox() is None:
        raise RuntimeError("No text silhouette found in the GPU render")

    canvas = background.convert("RGBA")

    # Defocused contact shadow anchors the letters to the background plane.
    shadow = shifted(mask, 2, 8).filter(ImageFilter.GaussianBlur(9))
    tint(canvas, shadow, (0, 10, 20), 0.78)

    # Six-pixel rigid extrusion; darkens toward the rear edge.
    side_colors = [(5, 67, 97), (6, 82, 115), (7, 101, 136),
                   (8, 119, 151), (10, 137, 166), (13, 151, 177)]
    for depth in range(6, 0, -1):
        tint(canvas, shifted(mask, 0, depth), side_colors[depth - 1], 0.98)

    # Cool face gradient, with a soft roll-off at the bevel.
    top = (188, 246, 252)
    mid = (54, 183, 216)
    bottom = (8, 112, 160)
    face = Image.new("RGB", rendered.size)
    bounds = mask.getbbox()
    y0, y1 = bounds[1], bounds[3]
    for y in range(rendered.height):
        t = max(0.0, min(1.0, (y - y0) / max(1, y1 - y0)))
        if t < 0.42:
            u = t / 0.42
            color = tuple(round(top[i] * (1-u) + mid[i] * u) for i in range(3))
        else:
            u = (t - 0.42) / 0.58
            color = tuple(round(mid[i] * (1-u) + bottom[i] * u) for i in range(3))
        face.paste(color, (0, y, rendered.width, y + 1))
    canvas.paste(face, (0, 0), mask)

    # Thin chiseled bevel: dark lower edge and ice highlight along upper-facing rims.
    inner = mask.filter(ImageFilter.MinFilter(7))
    edge = ImageChops.subtract(mask, inner)
    tint(canvas, edge, (2, 62, 95), 0.48)
    top_rim = ImageChops.subtract(mask, shifted(mask, 0, 2))
    top_rim = top_rim.filter(ImageFilter.MinFilter(3))
    tint(canvas, top_rim, (226, 255, 255), 0.9)
    lower_rim = ImageChops.subtract(mask, shifted(mask, 0, -2))
    tint(canvas, lower_rim, (0, 57, 90), 0.68)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(args.out, quality=96)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
