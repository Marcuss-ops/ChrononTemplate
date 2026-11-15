#!/usr/bin/env python3
"""Deterministic assets for the motion-design stress suite.

Everything is a pure function of the seed in this file: re-running the script
must produce byte-identical PNGs. The suite renders at 1920x1080 and 3840x2160,
so the paper plates and the alpha cutout are authored at both sizes where the
tests need them.

Usage:
    python3 tools/motion_design_stress/generate_assets.py [output-dir]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SEED = 20261114
W, H = 1920, 1080
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "out/motion_design_stress/assets"
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    str(ROOT.parent / "Chronon3d/assets/fonts/Inter-Bold.ttf"),
    str(ROOT / "assets/fonts/Inter-Bold.ttf"),
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _save(image: Image.Image, path: Path, manifest: list[dict]) -> None:
    image.save(path, optimize=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.append({
        "file": path.name,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "sha256": digest,
    })
    print(f"{path}  {image.width}x{image.height}  {digest[:16]}")


def paper_grain(w: int, h: int) -> Image.Image:
    """Grey paper with fine, isotropic grain and a few darker fibres."""
    rng = np.random.default_rng(SEED)
    base = 0.62 + 0.012 * np.sin(np.linspace(0.0, 9.0, w))[None, :]
    grain = rng.normal(0.0, 0.035, (h, w))
    # Fine horizontal tooth: higher frequency than the Gaussian grain.
    tooth = 0.012 * np.sin(np.arange(w) * 0.73)[None, :]
    lum = np.clip(base + grain + tooth, 0.0, 1.0)
    rgb = np.stack([lum * 0.985, lum, lum * 1.005], axis=-1)
    fibres = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(fibres)
    for i in range(140):
        x = int(rng.integers(0, w))
        y = int(rng.integers(0, h))
        length = int(rng.integers(18, 150))
        draw.line((x, y, x + length, y + int(rng.integers(-3, 4))),
                  fill=int(rng.integers(20, 55)), width=1)
    fibres = fibres.filter(ImageFilter.GaussianBlur(0.45))
    rgb_layer = Image.fromarray((rgb * 255.0).astype(np.uint8), "RGB")
    # Darken only the fibre pixels: black where the fibre mask is high, the
    # paper everywhere else. The previous argument order made the whole plate
    # black, which the renderer faithfully reproduced.
    darkened = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), rgb_layer, fibres)
    rgb_layer = Image.blend(rgb_layer, darkened, 0.22)
    rgba = rgb_layer.convert("RGBA")
    rgba.putalpha(255)
    return rgba


def paper_texture(w: int, h: int) -> Image.Image:
    """Low-frequency mottling over the fine grain, for large background plates."""
    rng = np.random.default_rng(SEED + 1)
    coarse = rng.normal(0.0, 1.0, (h // 16, w // 16)).astype(np.float32)
    coarse = Image.fromarray(((coarse * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8), "L")
    coarse = coarse.resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(28))
    mottle = np.asarray(coarse, dtype=np.float32) / 255.0 - 0.5
    fine = rng.normal(0.0, 0.022, (h, w))
    lum = np.clip(0.58 + 0.10 * mottle + fine, 0.0, 1.0)
    rgb = np.stack([lum * 1.01, lum * 0.995, lum * 0.965], axis=-1)
    return Image.fromarray((rgb * 255.0).astype(np.uint8), "RGB").convert("RGBA")


def cutout_subject(w: int, h: int) -> Image.Image:
    """RGBA portrait with curled hair, soft flyaways and a semi-transparent rim.

    The silhouette is deliberately simple (head, neck, shoulders) but the hair
    edge is made of ~420 overlapping curls with fractional alpha so a wrong
    straight-vs-premultiplied path shows a white or black fringe immediately.
    """
    rng = np.random.default_rng(SEED + 2)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = w * 0.5, h * 0.46
    head_rx, head_ry = w * 0.115, h * 0.22
    skin = (196, 158, 130, 255)
    hair = (33, 27, 24, 255)
    cloth = (34, 45, 52, 255)

    # Shoulders and neck first: the head/hair overlaps them.
    draw.ellipse((cx - w * 0.28, cy + h * 0.18, cx + w * 0.28, cy + h * 0.62), fill=cloth)
    draw.rectangle((cx - w * 0.047, cy + h * 0.10, cx + w * 0.047, cy + h * 0.30), fill=skin)
    draw.ellipse((cx - head_rx, cy - head_ry, cx + head_rx, cy + head_ry), fill=skin)

    # Hair mass behind and around the face.
    draw.ellipse((cx - w * 0.145, cy - h * 0.255, cx + w * 0.145, cy + h * 0.215), fill=hair)
    draw.ellipse((cx - head_rx * 0.94, cy - head_ry * 0.88,
                  cx + head_rx * 0.94, cy + head_ry * 0.82), fill=skin)
    # Keep the face clear of the hair mass; add a fringe.
    draw.chord((cx - w * 0.14, cy - h * 0.26, cx + w * 0.13, cy + h * 0.03),
               185, 355, fill=hair)

    # Curls: deterministic ellipses along an arc, each with partial alpha.
    for i in range(420):
        angle = rng.uniform(-2.75, 0.55)
        radius = rng.uniform(1.0, 1.18)
        px = cx + np.cos(angle) * head_rx * radius
        py = cy + np.sin(angle) * head_ry * radius * 0.98
        r = rng.uniform(w * 0.006, w * 0.022)
        a = int(rng.integers(120, 245))
        draw.ellipse((px - r, py - r * 1.25, px + r, py + r * 1.25), fill=(28, 23, 21, a))
        if i % 3 == 0:
            draw.ellipse((px - r * 0.55, py - r * 0.8, px + r * 0.55, py + r * 0.7),
                         fill=(54, 43, 36, int(a * 0.7)))

    # Flyaway strands: one-pixel lines, deliberately semi-transparent.
    for _ in range(90):
        angle = rng.uniform(-3.0, 0.4)
        start = (cx + np.cos(angle) * head_rx * 1.02,
                 cy + np.sin(angle) * head_ry * 1.02)
        end = (start[0] + np.cos(angle) * rng.uniform(18, 90),
               start[1] + np.sin(angle) * rng.uniform(18, 90) + rng.uniform(-30, 30))
        draw.line((*start, *end), fill=(40, 32, 27, int(rng.integers(70, 150))), width=1)

    # Soften only the outer hair edge, preserving the interior alpha.
    alpha = canvas.getchannel("A")
    softened = alpha.filter(ImageFilter.GaussianBlur(0.7))
    canvas.putalpha(Image.composite(softened, alpha, alpha.point(lambda v: 255 if v < 250 else 0)))
    return canvas


def dust_sprite(size: int = 256) -> Image.Image:
    """Soft bokeh disc with a faint rim, straight RGBA alpha."""
    y, x = np.mgrid[0:size, 0:size]
    c = (size - 1) * 0.5
    r = np.sqrt((x - c) ** 2 + (y - c) ** 2) / c
    core = np.clip(1.0 - r, 0.0, 1.0) ** 2.4
    rim = np.exp(-((r - 0.82) ** 2) / 0.012) * 0.22
    a = np.clip(core + rim, 0.0, 1.0)
    rgb = np.stack([a * 255.0 * 1.0, a * 255.0 * 0.96, a * 255.0 * 0.88], axis=-1)
    rgba = np.dstack([rgb, a * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def logo_plate(size: int = 1024) -> Image.Image:
    """White monogram plate, transparent background, for the 3D logo tests."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = int(size * 0.09)
    draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=int(size * 0.12),
                           fill=(248, 246, 240, 255), outline=(28, 31, 34, 255), width=6)
    draw.rounded_rectangle((pad + 18, pad + 18, size - pad - 18, size - pad - 18),
                           radius=int(size * 0.10), outline=(0, 168, 255, 255), width=4)
    font = _font(int(size * 0.30))
    label = "FIELD\nNOTES"
    box = draw.multiline_textbbox((0, 0), label, font=font, spacing=int(size * 0.01), align="center")
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.multiline_text(((size - tw) / 2, (size - th) / 2 - box[1]), label, font=font,
                        fill=(20, 23, 26, 255), spacing=int(size * 0.01), align="center")
    draw.rectangle((size * 0.30, size * 0.735, size * 0.70, size * 0.755),
                   fill=(0, 168, 255, 255))
    return image


def main() -> int:
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    _save(paper_grain(W, H), out / "paper_grain_1920x1080.png", manifest)
    _save(paper_texture(W, H), out / "paper_texture_1920x1080.png", manifest)
    _save(paper_grain(3840, 2160), out / "paper_grain_3840x2160.png", manifest)
    _save(cutout_subject(W, H), out / "cutout_hair_1920x1080.png", manifest)
    _save(dust_sprite(256), out / "dust_bokeh_256.png", manifest)
    _save(logo_plate(1024), out / "logo_field_notes_1024.png", manifest)

    (out / "manifest.json").write_text(
        json.dumps({"seed": SEED, "assets": manifest}, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(manifest)} assets -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
