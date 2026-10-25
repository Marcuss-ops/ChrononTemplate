#!/usr/bin/env python3
"""Emit the 150-frame cinematic DoF RenderPlan (1920x1080, 30 fps).

The ten focus-plane layers and their camera-space depths come from
build_focus_plane_stack_v1.py. Focus distance is linearly interpolated from
the first to the last plane over 150 frames and lowered to one resolved
camera_samples entry per frame, as the RenderPlan v2 decoder expects.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_focus_plane_stack_v1 as base  # noqa: E402

ROOT = base.ROOT
OUT = ROOT / "out/cinematic_dof_v1"
W, H = 1920, 1080
FPS = 30
FRAMES = 150
REF_HALF_H = 240.0  # half of the 854x480 authoring height used by the base layout


def focus_at(frame: int) -> float:
    lo, hi = base.DEPTHS[0], base.DEPTHS[-1]
    return lo + (hi - lo) * frame / (FRAMES - 1)


def camera(focus_distance: float, f_stop: float, max_blur: float) -> dict:
    return {
        "type": "perspective", "position": [0.0, 0.0, 0.0],
        "rotation_deg": [0.0, 180.0, 0.0], "fov_deg": base.FOV,
        "focal_length_mm": base.FOCAL_LENGTH_MM, "f_stop": f_stop,
        "near": 10.0, "far": 3000.0, "zoom": 1.0,
        "dof": {"enabled": True, "focus_distance": focus_distance,
                "f_stop": f_stop, "max_blur": max_blur},
    }


def layers() -> list[dict]:
    tan_half = math.tan(math.radians(base.FOV * 0.5))
    xs = [-260.0, -87.0, 87.0, 260.0]
    ys = [95.0, 0.0, -95.0]
    out = []
    for i, (asset, depth) in enumerate(zip(base.ASSETS, base.DEPTHS, strict=True)):
        col, row = i % 4, i // 4
        plane_w = 110.0 * depth / base.DEPTHS[0]
        plane_h = plane_w * 9.0 / 16.0
        out.append({
            "id": f"plane_{i + 1:02d}", "type": "image",
            "asset": f"ChrononTemplate/assets/focus_plane_stack_v1/layers_rgba/{asset}",
            "position": [xs[col] / REF_HALF_H * tan_half * depth,
                         ys[row] / REF_HALF_H * tan_half * depth, -depth],
            "size": [plane_w, plane_h], "fit": "contain", "enable_3d": True,
            "start_frame": 0, "duration_frames": FRAMES,
        })
    return out


def build_plan(f_stop: float = base.F_STOP, max_blur: float = base.MAX_BLUR_PX * 2.25) -> dict:
    samples = [
        {"frame": f, "camera": camera(focus_at(f), f_stop, max_blur)}
        for f in range(FRAMES)
    ]
    return {
        "schema": "chronon.render-plan.v2", "version": 2,
        "job_id": "cinematic_dof_v1",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "camera": camera(focus_at(0), f_stop, max_blur),
        "camera_samples": samples,
        "layers": layers(),
        "output": {"path": str(OUT / "cinematic_dof_v1.mp4"),
                   "format": "mp4", "codec": "h264"},
    }


OVERLAP_DEPTHS = [600.0, 1200.0, 1800.0]
OVERLAP_ASSETS = ["07_film_camera.png", "08_citrus_bowl.png", "09_globe_telescope.png"]


def overlap_layers() -> list[dict]:
    # Three partially overlapping RGBA planes at distinct camera-space depths.
    tan_half = math.tan(math.radians(base.FOV * 0.5))
    xs = [-60.0, 0.0, 60.0]
    out = []
    for i, (asset, depth) in enumerate(zip(OVERLAP_ASSETS, OVERLAP_DEPTHS, strict=True)):
        plane_w = 260.0 * depth / OVERLAP_DEPTHS[0]
        plane_h = plane_w * 9.0 / 16.0
        out.append({
            "id": f"overlap_{i + 1:02d}", "type": "image",
            "asset": f"ChrononTemplate/assets/focus_plane_stack_v1/layers_rgba/{asset}",
            "position": [xs[i] / REF_HALF_H * tan_half * depth, 0.0, -depth],
            "size": [plane_w, plane_h], "fit": "contain", "enable_3d": True,
            "start_frame": 0, "duration_frames": FRAMES,
        })
    return out


def build_overlap_plan() -> dict:
    lo, hi = OVERLAP_DEPTHS[0], OVERLAP_DEPTHS[-1]
    samples = []
    for f in range(FRAMES):
        focus = lo + (hi - lo) * f / (FRAMES - 1)
        samples.append({"frame": f, "camera": camera(focus, base.F_STOP, base.MAX_BLUR_PX * 2.25)})
    return {
        "schema": "chronon.render-plan.v2", "version": 2,
        "job_id": "cinematic_dof_overlap_v1",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "camera": camera(lo, base.F_STOP, base.MAX_BLUR_PX * 2.25),
        "camera_samples": samples,
        "layers": overlap_layers(),
        "output": {"path": str(OUT / "cinematic_dof_overlap_v1.mp4"),
                   "format": "mp4", "codec": "h264"},
    }


FSTOP_CASES = {"fstop_0_7": 0.7, "fstop_2_8": 2.8, "fstop_8_0": 8.0}


def build_fstop_plan(name: str, f_stop: float) -> dict:
    # Same scene, focus distance and blur cap as the 0.7 hero plan; only f-stop changes.
    plan = build_plan(f_stop=f_stop)
    plan["job_id"] = name
    plan["output"]["path"] = str(OUT / f"{name}.mp4")
    return plan


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    plans = {"cinematic_dof_v1.plan.json": build_plan(),
             "cinematic_dof_overlap_v1.plan.json": build_overlap_plan()}
    for name, f_stop in FSTOP_CASES.items():
        plans[f"{name}.plan.json"] = build_fstop_plan(name, f_stop)
    for filename, plan in plans.items():
        destination = OUT / filename
        destination.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(destination)
