#!/usr/bin/env python3
"""Emit native Chronon RenderPlans for the SVG 2D rig animation gallery."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DEFAULT = ROOT / "artifacts" / "rig_2d_anims_v1"
W, H, FPS, FRAMES = 854, 480, 30, 120

# Pivots are in the centered, Y-up space produced by the SVG's root transform.
PIVOTS = {
    "arm_l": (-42.75, -39.0), "arm_r": (42.75, -39.0),
    "leg_l": (-22.5, 61.5), "leg_r": (22.5, 61.5),
}
JOINTS = PIVOTS.copy()


def linear_track(values: list[tuple[int, list[float]]]) -> dict:
    return {"keyframes": [{"frame": frame, "value": value,
                            "easing": "linear"} for frame, value in values]}


def smooth_samples(key_values: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """Sample angular curves densely so the joint-pivot compensation stays exact."""
    samples: list[tuple[int, float]] = []
    for (f0, v0), (f1, v1) in zip(key_values, key_values[1:]):
        step = max(1, (f1 - f0) // 5)
        for frame in range(f0, f1, step):
            t = (frame - f0) / (f1 - f0)
            # Smoothstep between poses; the renderer still gets linear short segments.
            eased = t * t * (3.0 - 2.0 * t)
            samples.append((frame, v0 + (v1 - v0) * eased))
    samples.append(key_values[-1])
    return samples


def rotate(point: tuple[float, float], degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return c * point[0] - s * point[1], s * point[0] + c * point[1]


def curve_at(samples: list[tuple[int, float]], frame: int) -> float:
    for (f0, v0), (f1, v1) in zip(samples, samples[1:]):
        if f0 <= frame <= f1:
            t = (frame - f0) / max(1, f1 - f0)
            return v0 + (v1 - v0) * t
    return samples[-1][1] if frame > samples[-1][0] else samples[0][1]


def transform_binding(target: str, samples: list[tuple[int, float]],
                      parent: str | None = None) -> list[dict]:
    pivot = PIVOTS[target]
    parent_pivot = JOINTS[parent] if parent else None
    bindings = []
    rotation_keys, translation_keys = [], []
    for frame, angle in samples:
        parent_angle = 0.0
        target_pivot = pivot
        if parent and parent_pivot:
            parent_angle = curve_at(samples_by_target[parent], frame)
            parent_endpoint = JOINTS[target]
            relative = (parent_endpoint[0] - parent_pivot[0],
                        parent_endpoint[1] - parent_pivot[1])
            swung = rotate(relative, parent_angle)
            target_pivot = (parent_pivot[0] + swung[0], parent_pivot[1] + swung[1])
        total_angle = angle + parent_angle
        rotated_pivot = rotate(pivot, total_angle)
        translation = [target_pivot[0] - rotated_pivot[0],
                       target_pivot[1] - rotated_pivot[1]]
        rotation_keys.append((frame, [total_angle]))
        translation_keys.append((frame, translation))
    bindings.append({"target": target, "property": "transform.rotation",
                     "animation": linear_track(rotation_keys)})
    bindings.append({"target": target, "property": "transform.translate",
                     "animation": linear_track(translation_keys)})
    return bindings


def make_motion(kind: str) -> tuple[str, list[dict], dict | None]:
    bindings: list[dict] = []
    layer_motion = None
    if kind == "idle_breath":
        breathe = [(0, [0.0, 0.0]), (28, [0.0, 4.0]),
                   (58, [0.0, 0.0]), (87, [0.0, 4.0]), (119, [0.0, 0.0])]
        bindings.append({"target": "puppet_art", "property": "transform.translate",
                         "animation": linear_track(breathe)})
        return "IDLE / BREATHING", bindings, layer_motion

    if kind == "wave":
        samples = smooth_samples([(0, 0), (20, -72), (38, -72), (54, -105),
                                  (70, -72), (88, -105), (104, -72), (119, 0)])
        bindings.extend(transform_binding("arm_r", samples))
        return "WAVE / SHOULDER PIVOT", bindings, layer_motion

    if kind == "walk_cycle":
        phase = [(0, 0), (15, 30), (30, 0), (45, -30),
                 (60, 0), (75, 30), (90, 0), (105, -30), (119, 0)]
        for target, factor in (("leg_l", 1.0), ("leg_r", -1.0),
                               ("arm_l", -0.55), ("arm_r", 0.55)):
            samples = smooth_samples([(frame, angle * factor) for frame, angle in phase])
            bindings.extend(transform_binding(target, samples))
        return "WALK / ALTERNATING LIMB CYCLE", bindings, layer_motion

    if kind == "jump_land":
        layer_motion = {"tracks": [{"property": "position", "keyframes": [
            {"frame": 0, "value": [0.0, 0.0], "easing": "linear"},
            {"frame": 34, "value": [0.0, 0.0], "easing": "out_cubic"},
            {"frame": 58, "value": [0.0, -20.0], "easing": "out_cubic"},
            {"frame": 77, "value": [0.0, -20.0], "easing": "linear"},
            {"frame": 98, "value": [0.0, 0.0], "easing": "in_cubic"},
            {"frame": 119, "value": [0.0, 0.0], "easing": "linear"},
        ]}]}
        for target, angle in (("arm_l", 42.0), ("arm_r", -42.0),
                              ("leg_l", -16.0), ("leg_r", 16.0)):
            samples = smooth_samples([(0, 0), (34, 0), (58, angle),
                                      (77, angle), (98, 0), (119, 0)])
            bindings.extend(transform_binding(target, samples))
        return "JUMP / ANTICIPATION + LANDING", bindings, layer_motion
    raise KeyError(kind)


samples_by_target: dict[str, list[tuple[int, float]]] = {}


def build_plan(kind: str) -> dict:
    global samples_by_target
    samples_by_target = {}
    title, bindings, layer_motion = make_motion(kind)
    rig = {
        "id": "svg_rig", "type": "shape", "position": [W / 2, H / 2],
        "size": [640, 360], "start_frame": 0, "duration_frames": FRAMES,
        "shape": {"type": "path",
                  "asset": "tools/vector_diagram/rig_2d_anims/assets/rigged_puppet.svg",
                  "element_animations": bindings},
    }
    if layer_motion:
        rig["animation"] = layer_motion
    heading = {
        "id": "rig_title", "type": "text", "position": [W / 2, 34],
        "size": [730, 38], "start_frame": 0, "duration_frames": FRAMES,
        "text": "RIGGING 2D  /  ANIMS",
        "style": {"font": "assets/fonts/Inter-ExtraBold.ttf", "font_size": 27,
                  "fill": "#f4efe6"},
    }
    subtitle = {
        "id": "motion_title", "type": "text", "position": [W / 2, 62],
        "size": [760, 26], "start_frame": 0, "duration_frames": FRAMES,
        "text": f"SVG JOINT STUDY   /   {title}",
        "style": {"font": "assets/fonts/Inter-Medium.ttf", "font_size": 14,
                  "fill": "#72d9cb"},
    }
    footer = {
        "id": "rig_footer", "type": "text", "position": [W / 2, 458],
        "size": [760, 22], "start_frame": 0, "duration_frames": FRAMES,
        "text": "PIVOT LOCK  /  SHOULDER · ELBOW · HIP · KNEE",
        "style": {"font": "assets/fonts/Inter-Medium.ttf", "font_size": 12,
                  "fill": "#99a9b4"},
    }
    background = {"id": "background", "type": "color",
        "color": [0.018, 0.03, 0.045, 1.0], "position": [0, 0],
        "size": [W, H], "start_frame": 0, "duration_frames": FRAMES}
    return {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"rig_2d_{kind}_v1",
        "canvas": {"width": W, "height": H, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": FRAMES},
        "layers": [background, rig, heading, subtitle, footer],
        "output": {"path": f"rig_2d_{kind}_v1.mp4", "format": "mp4"}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for kind in ("idle_breath", "wave", "walk_cycle", "jump_land"):
        path = args.output / f"rig_2d_{kind}_v1.plan.json"
        path.write_text(json.dumps(build_plan(kind), indent=2) + "\n", encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
