#!/usr/bin/env python3
"""Render five restrained, premium image-group transition previews."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import render_image_slide_group_v2 as shared

ROOT = shared.ROOT
CHRONON = shared.CHRONON
CLI = shared.CLI
OUT = ROOT / "out/image_group_premium_v1"
ASSET_DIR = shared.ASSET_DIR

MOVES = {
    "soft_fade": {
        "label": "SOFT FADE",
        "position_x": [0, 0, 0, 0], "position_y": [0, 0, 0, 0],
        "scale": [1.0, 1.0, 1.0, 0.995],
    },
    "gentle_zoom": {
        "label": "GENTLE ZOOM",
        "position_x": [0, 0, 0, 0], "position_y": [0, 0, 0, -8],
        "scale": [0.965, 1.012, 1.0, 0.995],
    },
    "soft_lift": {
        "label": "SOFT LIFT",
        "position_x": [0, 0, 0, 0], "position_y": [18, -1, 0, -8],
        "scale": [0.99, 1.005, 1.0, 0.995],
    },
    "diagonal_drift": {
        "label": "DIAGONAL DRIFT",
        "position_x": [18, 0, 0, -10], "position_y": [12, 0, 0, -6],
        "scale": [0.99, 1.005, 1.0, 0.995],
    },
    "depth_settle": {
        "label": "DEPTH SETTLE",
        "position_x": [0, 0, 0, 0], "position_y": [6, -2, 0, -8],
        "scale": [1.03, 1.006, 1.0, 0.995],
    },
}


def make_plan(move: str, images):
    plan = shared.make_plan("slide_in", images)
    transition_id = f"image_group_{move}"
    plan["job_id"] = f"{transition_id}_premium_v1"
    plan["output"]["path"] = f"{transition_id}_premium_v1.mp4"
    for layer in plan["layers"]:
        if layer["id"] == "transition_label":
            layer["text"] = MOVES[move]["label"]

    count = len(images)
    slot = shared.FRAMES / count
    enter_frames = max(18, min(24, round(slot * 0.28)))
    exit_frames = max(14, min(20, round(slot * 0.22)))
    overlap = min(12, max(8, round(slot * 0.14)))
    image_index = 0
    for layer in plan["layers"]:
        if layer["type"] != "image" or not layer["id"].startswith("image_"):
            continue
        index = image_index
        image_index += 1
        start = round(index * slot)
        next_start = round((index + 1) * slot)
        exit_start = max(start + enter_frames + 4, next_start - exit_frames + overlap)
        exit_end = min(shared.FRAMES - 1, next_start + overlap)
        if index == count - 1:
            exit_start = max(start + enter_frames + 8, shared.FRAMES - exit_frames)
            exit_end = shared.FRAMES - 1
        enter_end = min(start + enter_frames, exit_start - 2)
        points = [start, enter_end, exit_start, exit_end]
        tracks = [
            shared._track(prop, list(zip(points, values)))
            for prop, values in MOVES[move].items()
            if prop != "label"
        ]
        tracks.append(shared._track("opacity", [(start, 0.0), (enter_end, 1.0),
                                                   (exit_start, 1.0), (exit_end, 0.0)]))
        layer["animation"] = {"tracks": tracks}
    if image_index != count:
        raise RuntimeError(f"expected {count} image layers, rewrote {image_index}")
    return plan


def main():
    images = shared._parse_images([])
    OUT.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shared._make_background(ASSET_DIR / "background.png")
    if not CLI.is_file():
        raise SystemExit(f"Chronon3D renderer not found: {CLI}")

    results = []
    for move in MOVES:
        plan = make_plan(move, images)
        name = plan["job_id"]
        plan_path = OUT / f"{name}.plan.json"
        video_path = OUT / f"{name}.mp4"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        subprocess.run([str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ROOT)],
                       check=True, cwd=ROOT)
        subprocess.run([str(CLI), "render", "--plan", str(plan_path), "--output", str(video_path),
                        "--assets-root", str(ROOT), "--backend", "vulkan", "--profile", "preview",
                        "--hardware", "nvenc", "--fps", str(shared.FPS)], check=True, cwd=ROOT)
        results.append({"id": name, "move": move, "video": video_path.name,
                        "image_count": len(images), "renderer": "vulkan", "encoder": "nvenc"})
    (OUT / "manifest.json").write_text(json.dumps({
        "canvas": [shared.W, shared.H], "fps": shared.FPS,
        "duration_frames": shared.FRAMES, "image_count": len(images),
        "shared_transition_independent_of_image_count": True, "renders": results,
    }, indent=2) + "\n")
    print(f"Rendered {len(results)} premium transitions with {len(images)} images to {OUT}")


if __name__ == "__main__":
    main()
