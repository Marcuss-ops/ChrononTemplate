#!/usr/bin/env python3
"""Emit ten Chronon still plans, one static focus distance per plane."""
from __future__ import annotations

import json
import math
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/focus_plane_stack_v1"
W, H = 854, 480
TRACK_CSV = Path(__file__).with_name("camera_rig_focus_samples.csv")
with TRACK_CSV.open(newline="", encoding="utf-8") as track_file:
    CAMERA_TRACK = list(csv.DictReader(track_file))
if len(CAMERA_TRACK) != 10:
    raise ValueError(f"expected ten sampled CameraRig keys in {TRACK_CSV}")
DEPTHS = [float(row["focus_distance"]) for row in CAMERA_TRACK]
FOV = float(CAMERA_TRACK[0]["fov_deg"])
FOCAL_LENGTH_MM = float(CAMERA_TRACK[0]["focal_length_mm"])
SENSOR_WIDTH_MM = float(CAMERA_TRACK[0]["sensor_width_mm"])
F_STOP = float(CAMERA_TRACK[0]["f_stop"])
MAX_BLUR_PX = float(CAMERA_TRACK[0]["max_blur_px"])
ASSETS = [
    "01_kettle_mug.png", "02_compass_watch.png", "03_vase_stem.png",
    "04_books_glasses.png", "05_toy_robot_gears.png", "06_plant_stones.png",
    "07_film_camera.png", "08_citrus_bowl.png", "09_globe_telescope.png",
    "10_hourglass_key.png",
]


def build_plan(focus_index: int) -> dict:
    # A regular 4x3 grid keeps all ten silhouettes readable while each remains
    # a physical image plane at its own camera-space depth.
    layers = []
    fov = FOV
    focal_px = (H * 0.5) / math.tan(math.radians(fov * 0.5))
    xs_px = [-260.0, -87.0, 87.0, 260.0]
    ys_px = [95.0, 0.0, -95.0]
    for i, (asset, depth) in enumerate(zip(ASSETS, DEPTHS, strict=True)):
        col, row = i % 4, i // 4
        plane_w = 110.0 * depth / DEPTHS[0]
        plane_h = plane_w * 9.0 / 16.0
        layers.append({
            "id": f"plane_{i + 1:02d}", "type": "image",
            "asset": f"ChrononTemplate/assets/focus_plane_stack_v1/layers_rgba/{asset}",
            "position": [xs_px[col] * depth / focal_px,
                         ys_px[row] * depth / focal_px, -depth],
            "size": [plane_w, plane_h], "fit": "contain", "enable_3d": True,
            "start_frame": 0, "duration_frames": 1,
        })

    camera = {
        "type": "perspective", "position": [0.0, 0.0, 0.0],
        # CameraRig forward is local -Z. RenderPlan's view transform follows
        # its camera backward axis, so Y=180 maps the optical axis to world -Z.
        "rotation_deg": [0.0, 180.0, 0.0], "fov_deg": fov,
        # The sensor/focal pair resolves to the same 48-degree vertical FOV.
        "focal_length_mm": FOCAL_LENGTH_MM,
        "f_stop": F_STOP,
        "near": 10.0, "far": 3000.0, "zoom": 1.0,
        # Distances and focal length use matching render units; 0.7 is the
        # CameraRig aperture value and max_blur is measured in output pixels.
        "dof": {"enabled": True, "focus_distance": DEPTHS[focus_index],
                "f_stop": F_STOP, "max_blur": MAX_BLUR_PX},
    }
    return {
        "schema": "chronon.render-plan.v2", "version": 2,
        "job_id": f"focus_plane_stack_v1_{focus_index + 1:02d}",
        "canvas": {"width": W, "height": H, "fps_num": 1, "fps_den": 1,
                   "duration_frames": 1},
        "camera": camera, "layers": layers,
        # MP4 format causes plan preparation to build the full composition
        # compatibility view. The production proof command overrides its
        # encoder with the raw RGBA pixel-truth sink and writes a PNG per pose.
        "output": {"path": str(OUT / f"focus_{focus_index + 1:02d}.mp4"),
                   "format": "mp4", "codec": "h264"},
    }


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for index in range(10):
        destination = OUT / f"focus_{index + 1:02d}.plan.json"
        destination.write_text(json.dumps(build_plan(index), indent=2) + "\n", encoding="utf-8")
        print(destination)
