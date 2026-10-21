#!/usr/bin/env python3
"""Generate a certified static Web Mercator map plate for PipelineGen.

This is the adapter used by PipelineGen's chronontemplateMapPlateResolver.
The dynamic map runtime and this plate path share the same tile source,
projection and disk cache, so camera LOD images stay geographically aligned.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
sys.path.insert(0, str(WORKSPACE / "Chronon3d" / "tools" / "cartography"))

from dynamic_tile_pyramid import DynamicTilePyramid, latlon_to_global_px  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--zoom", type=int, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not (-85.05112878 < args.latitude < 85.05112878):
        parser.error("latitude must be inside the Web Mercator extent")
    if not (-180.0 <= args.longitude <= 180.0):
        parser.error("longitude must be between -180 and 180")
    if not (0 <= args.zoom <= 19) or args.width <= 0 or args.height <= 0:
        parser.error("zoom and raster dimensions are outside supported bounds")

    pyramid = DynamicTilePyramid(provider="esri_sat")
    center_x, center_y = latlon_to_global_px(args.latitude, args.longitude, args.zoom)
    left, top = center_x - args.width / 2, center_y - args.height / 2
    x0 = math.floor(left / 256)
    x1 = math.ceil((left + args.width) / 256)
    y0 = math.floor(top / 256)
    y1 = math.ceil((top + args.height) / 256)
    pyramid.prefetch_tiles(
        [(args.zoom, x, y) for y in range(y0, y1) for x in range(x0, x1)],
        max_workers=8,
    )
    plate = pyramid.render_plate_at_zoom(
        args.latitude, args.longitude, args.zoom, args.width, args.height,
    )
    if plate.shape != (args.height, args.width, 3) or not np.any(plate):
        raise RuntimeError(f"map plate is empty or has the wrong dimensions: {plate.shape}")
    if pyramid.telemetry["tile_fallbacks"] != 0:
        raise RuntimeError(f"map plate used {pyramid.telemetry['tile_fallbacks']} fallback tiles")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), plate):
        raise RuntimeError(f"could not write map plate: {args.output}")
    print(
        f"MAP_PLATE_PASS zoom={args.zoom} size={args.width}x{args.height} "
        f"tiles={pyramid.telemetry['prefetch_tiles_requested']} "
        f"network={pyramid.telemetry['tile_network_fetches']} output={args.output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
