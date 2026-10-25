#!/usr/bin/env python3
"""Build three static Chronon plans that focus background, title, and foreground."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets/three_plane_focus_v1"
DEPTHS = [900.0, 650.0, 450.0]
FOCUS_NAMES = ["background", "text", "foreground"]


def make_plan(width: int, height: int, focus_index: int, out_dir: Path) -> dict:
    scale = height / 480.0
    focal_px = height * 0.5 / math.tan(math.radians(48.0 * 0.5))
    background_depth, text_depth, foreground_depth = DEPTHS
    bg_height = 2 * background_depth * math.tan(math.radians(48.0 * 0.5))
    bg_width = bg_height * width / height
    foreground_width_px = 220.0 * scale
    foreground_width = foreground_width_px * foreground_depth / focal_px
    foreground_height = foreground_width * 1145.0 / 1374.0
    # Keep the center of the lens on the right and overlapping the title plane.
    foreground_x = -215.0 * foreground_depth / 450.0
    foreground_y = -50.0 * foreground_depth / 450.0
    dof_max_blur = 24.0 * scale
    font_path = "Chronon3d/assets/fonts/Inter-Bold.ttf"
    return {
        "schema": "chronon.render-plan.v2", "version": 2,
        "job_id": f"three_plane_focus_v1_{FOCUS_NAMES[focus_index]}_{width}x{height}",
        "canvas": {"width": width, "height": height, "fps_num": 1,
                   "fps_den": 1, "duration_frames": 1},
        "camera": {
            "type": "perspective", "position": [0.0, 0.0, 0.0],
            "rotation_deg": [0.0, 180.0, 0.0], "fov_deg": 48.0,
            "focal_length_mm": 22.72337, "f_stop": 0.7,
            "near": 10.0, "far": 1200.0, "zoom": 1.0,
            "dof": {"enabled": True, "focus_distance": DEPTHS[focus_index],
                    "f_stop": 0.7, "max_blur": dof_max_blur},
        },
        "layers": [
            {"id": "layer_0_background", "type": "image",
             "asset": "ChrononTemplate/assets/three_plane_focus_v1/background_camera_studio.png",
             "position": [0.0, 0.0, -background_depth],
             "size": [bg_width, bg_height], "scale": [2.0, 2.0, 1.0],
             "fit": "cover", "enable_3d": True,
             "start_frame": 0, "duration_frames": 1},
            {"id": "layer_1_text", "type": "text", "text": "FOCUS TEST",
             "position": [400.0 * scale, 180.0 * scale, -text_depth],
             "size": [560.0, 100.0], "enable_3d": True,
             "style": {"font": font_path, "font_size": 60.0,
                       "fill": "#FFF0CB", "text_align": "center",
                       "shadow": {"color": "#1C1208", "opacity": 0.72,
                                  "blur": 8.0, "offset": [0.0, 3.0]}},
             "start_frame": 0, "duration_frames": 1},
            {"id": "layer_2_foreground_lens", "type": "image",
             "asset": "ChrononTemplate/assets/three_plane_focus_v1/foreground_brass_lens.png",
             "position": [foreground_x, foreground_y, -foreground_depth],
             "size": [foreground_width, foreground_height], "fit": "contain",
             "enable_3d": True,
             "start_frame": 0, "duration_frames": 1},
        ],
        "output": {"path": str(out_dir / f"focus_{FOCUS_NAMES[focus_index]}.mp4"),
                   "format": "mp4", "codec": "h264"},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=854)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "out/three_plane_focus_v1/plans_854x480")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for index in range(3):
        plan_path = args.out / f"focus_{FOCUS_NAMES[index]}.plan.json"
        plan_path.write_text(json.dumps(make_plan(args.width, args.height, index, args.out),
                                        indent=2) + "\n", encoding="utf-8")
        print(plan_path)
