#!/usr/bin/env python3
"""Chronon Multi-Image Trio V2: additional portrait-card animations.

The three NASA portrait cards remain on screen together in every clip. The
Heartbeat recipe was withdrawn after its zero-opacity opening caused black
frames; the suite retains the other nine recipes. It uses the canonical kit
pipeline and leaves the original multi_image_trio_v1 deliveries untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kit import Canvas, Plan, Suite, SuiteItem, fade, track

CANVAS = Canvas(width=1920, height=1080, fps=30, duration_frames=150)
OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "multi_image_trio_v2"
DRIVE_FOLDER_ID = "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX"
CARD_SIZE = (500, 680)
POSITIONS = ((-540, 0), (0, 0), (540, 0))
ASSETS = (
    "assets/famous_people_trio_v1/neil_armstrong.png",
    "assets/famous_people_trio_v1/sally_ride.png",
    "assets/famous_people_trio_v1/john_glenn.png",
)
END = CANVAS.duration_frames - 1

# Each recipe creates an intentionally different timing/transform language.
# Keep transformations within the original trio's safe canvas and focus bounds.
def _tracks(recipe: str, index: int) -> list[dict]:
    phase = index * 5
    sign = -1.0 if index % 2 == 0 else 1.0

    if recipe == "iris_reveal":
        delay = index * 4
        return [
            track("scale", "out_cubic", (0, 0.82), (24 + delay, 1.03), (42 + delay, 1.0), (END, 1.0)),
            fade("out_cubic", (0, 0.0), (14 + delay, 1.0), (END, 1.0)),
            track("rotation_z", "out_cubic", (0, sign * 9.0), (24 + delay, 0.0), (END, 0.0)),
        ]
    if recipe == "triple_ripple":
        return [
            track("scale", "in_out_sine", (0, 0.94), (20 + phase, 1.04), (39 + phase, 0.98), (66 + phase, 1.02), (88 + phase, 1.0), (END, 1.0)),
            fade("out_cubic", (0, 0.0), (16 + phase, 1.0), (END, 1.0)),
            track("rotation_z", "in_out_sine", (0, sign * 4.0), (34 + phase, 0.0), (72 + phase, sign * -2.0), (104 + phase, 0.0), (END, 0.0)),
        ]
    if recipe == "rack_focus":
        start = 12 + index * 42
        peak = min(1.05, 1.03 + 0.01 * (index % 2))
        return [
            track("scale", "in_out_cubic", (0, 0.94), (start, 0.94), (start + 10, peak), (start + 28, peak), (start + 40, 0.94), (END, 0.94)),
            fade("in_out_cubic", (0, 0.72), (start, 0.72), (start + 10, 1.0), (start + 28, 1.0), (start + 40, 0.72), (END, 0.72)),
        ]
    if recipe == "float_orbit":
        lift = (index - 1) * 18.0
        return [
            track("position_y", "in_out_sine", (0, lift + 36.0), (38, lift), (76, lift - 28.0), (114, lift), (END, lift + 36.0)),
            track("scale", "in_out_sine", (0, 0.96), (38, 1.02), (76, 1.04), (114, 1.0), (END, 0.96)),
            fade("in_out_cubic", (0, 0.0), (18 + phase, 1.0), (END, 1.0)),
        ]
    if recipe == "pendulum_sway":
        return [
            track("rotation_z", "in_out_sine", (0, sign * 8.0), (30, 0.0), (60, sign * -5.0), (90, 0.0), (120, sign * 3.0), (END, 0.0)),
            track("scale", "in_out_sine", (0, 0.96), (30, 1.02), (60, 0.98), (90, 1.02), (120, 0.99), (END, 1.0)),
            fade("out_cubic", (0, 0.0), (16 + phase, 1.0), (END, 1.0)),
        ]
    if recipe == "depth_breath":
        return [
            track("position_z", "in_out_sine", (0, 140.0 + index * 24.0), (38, 0.0), (76, -32.0), (114, 0.0), (END, 80.0 + index * 18.0)),
            track("scale", "in_out_sine", (0, 0.92), (38, 1.02), (76, 1.04), (114, 1.0), (END, 0.96)),
            fade("in_out_cubic", (0, 0.0), (18 + phase, 1.0), (END, 1.0)),
        ]
    if recipe == "vertical_cascade":
        delay = index * 9
        return [
            track("position_y", "out_cubic", (0, sign * (70.0 + index * 8.0)), (28 + delay, 0.0), (END, 0.0)),
            track("scale", "out_cubic", (0, 0.88), (28 + delay, 1.04), (48 + delay, 1.0), (END, 1.0)),
            fade("out_cubic", (0, 0.0), (18 + delay, 1.0), (END, 1.0)),
        ]
    if recipe == "side_drift":
        drift = sign * 34.0
        return [
            track("position_x", "in_out_sine", (0, drift), (38, 0.0), (76, -drift), (114, 0.0), (END, drift * 0.35)),
            track("scale", "in_out_sine", (0, 0.98), (38, 1.02), (76, 1.0), (114, 1.03), (END, 1.0)),
            fade("out_cubic", (0, 0.0), (18 + phase, 1.0), (END, 1.0)),
        ]
    if recipe == "spring_pop":
        delay = index * 8
        return [
            track("scale", "out_cubic", (0, 0.72), (22 + delay, 1.05), (36 + delay, 0.98), (52 + delay, 1.0), (END, 1.0)),
            track("rotation_z", "out_cubic", (0, sign * 6.0), (24 + delay, 0.0), (END, 0.0)),
            fade("out_cubic", (0, 0.0), (14 + delay, 1.0), (END, 1.0)),
        ]
    raise ValueError(f"unknown trio animation recipe: {recipe}")


def _build(job_id: str, recipe: str) -> Plan:
    plan = Plan(job_id=job_id, canvas=CANVAS, output_path=OUT_DIR / f"{job_id}.mp4")
    plan.color_layer("studio_dark_bg", (0.03, 0.04, 0.07, 1.0))
    for index, (asset, position, layer_id) in enumerate(zip(
        ASSETS, POSITIONS, ("card_left", "card_mid", "card_right"), strict=True
    )):
        plan.image_card(
            layer_id, asset, CARD_SIZE, position, _tracks(recipe, index),
            radius=0.0, fit="cover", enable_3d=True,
            start_frame=0, duration_frames=CANVAS.duration_frames,
        )
    return plan


ANIMATIONS = (
    ("trio_v2_01_iris_reveal", "iris_reveal"),
    ("trio_v2_02_triple_ripple", "triple_ripple"),
    ("trio_v2_03_rack_focus", "rack_focus"),
    ("trio_v2_04_float_orbit", "float_orbit"),
    ("trio_v2_05_pendulum_sway", "pendulum_sway"),
    ("trio_v2_06_depth_breath", "depth_breath"),
    ("trio_v2_07_vertical_cascade", "vertical_cascade"),
    ("trio_v2_08_side_drift", "side_drift"),
    ("trio_v2_09_spring_pop", "spring_pop"),
)

SUITE = Suite(
    name="multi_image_trio_v2",
    out_dir=OUT_DIR,
    drive_folder=DRIVE_FOLDER_ID,
    assets_root=Path(__file__).resolve().parents[2],
    items=[
        SuiteItem(name, lambda name=name, recipe=recipe: _build(name, recipe))
        for name, recipe in ANIMATIONS
    ],
)

if __name__ == "__main__":
    from kit import run_suite
    raise SystemExit(run_suite(SUITE))
