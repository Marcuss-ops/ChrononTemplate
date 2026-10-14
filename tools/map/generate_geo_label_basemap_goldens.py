#!/usr/bin/env python3
"""Render deterministic label/basemap golden frames from a seeded raster fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

SYSTEM_DIST_PACKAGES = Path("/usr/lib/python3/dist-packages")
if SYSTEM_DIST_PACKAGES.is_dir():
    sys.path.insert(0, str(SYSTEM_DIST_PACKAGES))
import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Chronon3d" / "tools" / "cartography"))
import render_geo_camera_small_places as labels
from dynamic_tile_pyramid import BASEMAP_STYLES

# Four style representatives are frozen as the published comparison matrix.
GOLDEN_BASEMAPS = ("esri_sat", "esri_street", "esri_topo", "esri_dark")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write PNGs and manifest")
    parser.add_argument("--out", type=Path, default=HERE / "assets" / "geo_label_basemap_goldens")
    args = parser.parse_args()
    manifest_path = HERE / "assets" / "geo_label_basemap_golden_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    height, width = map(int, manifest["size"][::-1])
    styles = tuple(manifest["labels"])
    if set(styles) != set(labels.MAP_LABEL_ANIMATIONS):
        raise RuntimeError("golden manifest label palette is stale; update it to exact runtime IDs")
    if any(name not in BASEMAP_STYLES and name != "esri_dark" for name in GOLDEN_BASEMAPS):
        raise RuntimeError("golden matrix contains an unrecognized basemap")
    outputs = []
    palette = {
        "esri_sat": ((35, 72, 44), (49, 112, 77)),
        "esri_street": ((218, 213, 200), (245, 241, 229)),
        "esri_topo": ((104, 126, 86), (174, 157, 117)),
        "esri_dark": ((22, 27, 35), (41, 49, 60)),
    }
    for basemap in GOLDEN_BASEMAPS:
        # Stable, provider-distinct vector-style plates avoid network access and
        # ensure the basemap dimension itself changes each golden frame.
        dark, light = palette[basemap]
        yy, xx = np.mgrid[:height, :width]
        frame_base = np.empty((height, width, 3), dtype=np.uint8)
        mix = ((xx // 48 + yy // 36) % 2)[..., None]
        frame_base[:] = np.where(mix == 0, np.asarray(dark, np.uint8),
                                 np.asarray(light, np.uint8))
        cv2.line(frame_base, (0, height//2), (width-1, height//2),
                 tuple(reversed(light)), 2, cv2.LINE_AA)
        cv2.line(frame_base, (width//2, 0), (width//2, height-1),
                 tuple(reversed(light)), 2, cv2.LINE_AA)
        for style in styles:
            labels.WIDTH, labels.HEIGHT = width, height
            frame = frame_base.copy()
            labels.draw_map_location_marker(frame, (480, 270), "Garlasco", .95, style)
            name = f"{basemap}__{style}.png"
            path = args.out / name
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(path), frame):
                    raise RuntimeError(f"failed to write golden frame {path}")
            outputs.append({"file": name, "sha256": hashlib.sha256(frame.tobytes()).hexdigest()})
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(
            json.dumps({"schema": manifest["schema"], "size": manifest["size"],
                        "seed": manifest["seed"], "cases": len(outputs),
                        "goldens": outputs}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    else:
        print(json.dumps({"cases": len(outputs), "goldens": outputs}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
