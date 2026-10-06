#!/usr/bin/env python3
"""Generate one exact Web Mercator basemap plate for PipelineGen map overlays.

The renderer supplies the grounded center, zoom, and canvas. Tile sampling is
shared with geo_runtime.py; pins/camera movement remain owned by the overlay
plan renderer so the georeference is checked again at compile time.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Chronon3d/tools/cartography"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--zoom", type=int, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not math.isfinite(args.latitude) or not -85.05112878 <= args.latitude <= 85.05112878:
        parser.error("latitude must be finite and inside the Web Mercator range")
    if not math.isfinite(args.longitude) or not -180.0 <= args.longitude <= 180.0:
        parser.error("longitude must be finite and within [-180, 180]")
    if not 0 <= args.zoom <= 22 or args.width <= 0 or args.height <= 0:
        parser.error("zoom must be 0..22 and dimensions must be positive")

    import cv2
    import numpy as np
    from dynamic_tile_pyramid import DynamicTilePyramid

    cv2.setNumThreads(1)
    pyramid = DynamicTilePyramid(provider="esri_sat")
    image = pyramid.render_plate_at_zoom(args.latitude, args.longitude, args.zoom,
                                         args.width, args.height)
    if image.shape != (args.height, args.width, 3):
        raise RuntimeError(f"unexpected map plate shape: {image.shape}")
    # The shared tile loader has a dark fallback for offline showcase renders.
    # Production must fail closed instead of certifying a fallback as a map.
    luminance = image.mean(axis=2)
    if float(np.std(image)) < 5.0 or float(np.mean(luminance > 4.0)) < 0.95:
        raise RuntimeError("map plate contains missing/fallback tiles")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".partial.png")
    if not cv2.imwrite(str(temporary), image):
        raise RuntimeError(f"could not write map plate: {temporary}")
    os.replace(temporary, args.output)
    print(f"MAP_PLATE_PASS path={args.output} zoom={args.zoom} "
          f"width={args.width} height={args.height}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
