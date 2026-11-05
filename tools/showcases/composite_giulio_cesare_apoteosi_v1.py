#!/usr/bin/env python3
"""Composite the blurred Caesar title behind the Chronon3D bust render.

The software mesh compositor always draws mesh layers in layer order and does
not use the per-layer depth map across mesh layers, so a 3D title behind the
bust is painted over the chest. This script keeps the bust render from
Chronon3D, builds a pre-blurred title plate, derives a filled silhouette matte
from each frame, and composites the plate *behind* the bust.

Usage:
    python3 tools/showcases/composite_giulio_cesare_apoteosi_v1.py \
        --bust out/giulio_cesare_apoteosi_v1/bust_only_v2.mp4 \
        --out out/giulio_cesare_apoteosi_v1/giulio_cesare_apoteosi_v2.mp4
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import binary_closing, binary_fill_holes, gaussian_filter

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = TEMPLATE_ROOT.parent
FONT = PROJECT_ROOT / "Chronon3d" / "assets" / "fonts" / "PlayfairDisplay-Bold.ttf"
WIDTH = 1920
HEIGHT = 1080
FPS = 30
TITLE = "GIULIO CESARE"
TITLE_SIZE = 180
TITLE_TRACKING = 8
TITLE_BASELINE = 560
TITLE_COLOR = (142, 114, 72)
TITLE_BLUR = 10


def build_title_plate(path: Path) -> None:
    # A subtle floor and contact shadow anchor the socle without turning the
    # whole background grey. The native shadow pass is not used here because
    # its mesh-caster output replaces the bust with a white silhouette in this
    # build; the title/floor plate is composited behind the bust matte.
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    floor_mask = np.clip(
        1.0 - ((xx - 960.0) / 620.0) ** 2 - ((yy - 1010.0) / 150.0) ** 2,
        0.0,
        1.0,
    ) ** 2
    canvas = floor_mask[..., None] * np.array([15.0, 13.0, 11.0], dtype=np.float32)
    shadow_mask = np.clip(
        1.0 - ((xx - 960.0) / 300.0) ** 2 - ((yy - 1000.0) / 55.0) ** 2,
        0.0,
        1.0,
    ) ** 2
    canvas *= 1.0 - 0.55 * shadow_mask[..., None]
    plate = Image.fromarray(np.clip(canvas, 0.0, 255.0).astype(np.uint8), mode="RGB")
    draw = ImageDraw.Draw(plate)
    font = ImageFont.truetype(str(FONT), TITLE_SIZE)
    advances = [draw.textlength(char, font=font) for char in TITLE]
    total = sum(advances) + TITLE_TRACKING * (len(TITLE) - 1)
    x = (WIDTH - total) * 0.5
    for char, advance in zip(TITLE, advances):
        draw.text((x, TITLE_BASELINE), char, font=font, fill=TITLE_COLOR, anchor="ls")
        x += advance + TITLE_TRACKING
    plate = plate.filter(ImageFilter.GaussianBlur(TITLE_BLUR))
    plate.save(path)


def silhouette_matte(frame: np.ndarray) -> np.ndarray:
    # The Chronon render is an opaque bust over a black clear. Recover a solid
    # bust silhouette, close JPEG/H.264 edge noise, and fill the interior so the
    # title can never show through dark chest/neck pixels.
    alpha = frame.max(axis=2) > 6
    alpha = binary_closing(alpha, iterations=2)
    alpha = binary_fill_holes(alpha)
    return gaussian_filter(alpha.astype(np.float32), 0.8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bust", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--plate", type=Path)
    args = parser.parse_args()

    plate_path = args.plate or args.out.with_name(args.out.stem + "_title_plate.png")
    plate_path.parent.mkdir(parents=True, exist_ok=True)
    build_title_plate(plate_path)
    plate = np.asarray(Image.open(plate_path).convert("RGB"), dtype=np.float32)

    with tempfile.TemporaryDirectory(prefix="caesar_composite_") as temporary:
        frames_dir = Path(temporary) / "frames"
        frames_dir.mkdir()
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(args.bust), str(frames_dir / "%04d.png")],
            check=True,
        )
        frames = sorted(frames_dir.glob("*.png"))
        if not frames:
            raise RuntimeError("the bust render produced no frames")
        for index, path in enumerate(frames):
            frame = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
            alpha = silhouette_matte(frame)
            composed = np.clip(frame + plate * (1.0 - alpha[..., None]), 0.0, 255.0)
            Image.fromarray(composed.astype(np.uint8)).save(path)
            if index == 0:
                print(f"frame size: {frame.shape[1]}x{frame.shape[0]}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-framerate", str(FPS),
                "-i", str(frames_dir / "%04d.png"),
                "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(args.out),
            ],
            check=True,
        )

    print(f"bust:  {args.bust}")
    print(f"plate: {plate_path}")
    print(f"out:   {args.out}")


if __name__ == "__main__":
    main()
