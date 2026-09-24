#!/usr/bin/env python3
"""Emit the first native typewriter variants from the approved font base."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import emit_native_phrase_pack as native  # noqa: E402


MOTIONS = [
    "premium_soft_reveal",
    "precision_word_stagger",
    "masked_vertical_lift",
    "hero_scale_focus",
    "kinetic_keyword_lock",
]

# The approved GlowBasics look uses a flat, readable face with a small amount
# of real card-space motion. These are layer transforms (not a 2D shadow or
# duplicated blur), so Chronon3D evaluates the text plane in 3D and its single
# Gaussian halo remains attached to the transformed text.
THREE_D_PROFILES = {
    "premium_soft_reveal": {
        "rotation_x": [(0, 7), (30, 1.5), (72, 0), (141, 0), (149, -4)],
        "rotation_y": [(0, -14), (30, -3), (72, 0), (141, 0), (149, 9)],
        "position_z": [(0, 120), (30, 28), (72, 0), (141, 0), (149, -70)],
    },
    "precision_word_stagger": {
        "rotation_x": [(0, -6), (28, -1), (72, 0), (141, 0), (149, 4)],
        "rotation_y": [(0, 16), (28, 4), (72, 0), (141, 0), (149, -10)],
        "position_z": [(0, -100), (28, -18), (72, 0), (141, 0), (149, 65)],
    },
    "masked_vertical_lift": {
        "rotation_x": [(0, 10), (34, 2), (72, 0), (141, 0), (149, -6)],
        "rotation_y": [(0, -9), (34, -2), (72, 0), (141, 0), (149, 8)],
        "position_z": [(0, 145), (34, 24), (72, 0), (141, 0), (149, -82)],
    },
    "hero_scale_focus": {
        "rotation_x": [(0, 5), (36, 0.8), (72, 0), (141, 0), (149, -3)],
        "rotation_y": [(0, -11), (36, -2), (72, 0), (141, 0), (149, 7)],
        "position_z": [(0, 90), (36, 16), (72, 0), (141, 0), (149, -55)],
    },
    "kinetic_keyword_lock": {
        "rotation_x": [(0, -8), (32, -1), (72, 0), (141, 0), (149, 5)],
        "rotation_y": [(0, 13), (32, 2), (72, 0), (141, 0), (149, -8)],
        "position_z": [(0, -125), (32, -22), (72, 0), (141, 0), (149, 75)],
    },
}


def make_plan(motion: dict, style: dict, text: str, font: str, font_size: float, duration: int) -> dict:
    lowered = native.lower_motion(motion, duration)
    three_d = THREE_D_PROFILES[motion["id"]]
    tracks = list(lowered["tracks"])
    for property_name, values in three_d.items():
        if property_name == "rotation_x":
            continue
        if property_name == "rotation_y":
            x_values = dict(three_d["rotation_x"])
            tracks.append({
                "property": "rotation",
                "keyframes": [
                    {"frame": frame, "value": [x_values[frame], value, 0.0]}
                    for frame, value in values
                ],
                "easing": "out_cubic",
            })
            continue
        tracks.append({
            "property": property_name,
            "keyframes": [{"frame": frame, "value": value} for frame, value in values],
            "easing": "out_cubic",
        })

    # Chronon3D accepts one animated vector per transform family.  Catalog
    # motions may already animate position_y (or scale_y), while the 3D layer
    # adds position_z.  Fold component tracks into one vector so the runtime
    # sees one coherent transform instead of overlapping claims.
    for family, defaults in (("position", (0.0, 0.0, 0.0)), ("scale", (1.0, 1.0, 1.0))):
        component_tracks = [
            track for track in tracks
            if track["property"] == family or track["property"].startswith(f"{family}_")
        ]
        if len(component_tracks) <= 1:
            continue
        frames = sorted({
            key["frame"]
            for track in component_tracks
            for key in track["keyframes"]
        })

        def sample(track: dict, frame: int) -> float | list[float]:
            keys = track["keyframes"]
            if frame <= keys[0]["frame"]:
                return keys[0]["value"]
            if frame >= keys[-1]["frame"]:
                return keys[-1]["value"]
            for left, right in zip(keys, keys[1:]):
                if left["frame"] <= frame <= right["frame"]:
                    span = right["frame"] - left["frame"]
                    amount = (frame - left["frame"]) / span
                    left_value = left["value"]
                    right_value = right["value"]
                    return left_value + (right_value - left_value) * amount
            return keys[-1]["value"]

        merged = []
        for frame in frames:
            value = list(defaults)
            for component_track in component_tracks:
                sampled = sample(component_track, frame)
                if isinstance(sampled, list):
                    value = sampled + [1.0] * (3 - len(sampled))
                    continue
                property_name = component_track["property"]
                if property_name == family:
                    value = [sampled, sampled, sampled]
                else:
                    axis = {"x": 0, "y": 1, "z": 2}[property_name[-1]]
                    value[axis] = sampled
            merged.append({"frame": frame, "value": value})
        tracks = [track for track in tracks if track not in component_tracks]
        tracks.append({"property": family, "keyframes": merged, "easing": "out_cubic"})
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"chronontemplate_typewriter_{motion['id']}_{Path(font).stem.lower()}",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": 30,
            "fps_den": 1,
            "duration_frames": duration,
        },
        "layers": [
            {
                "id": "background",
                "type": "color",
                "color": style["background"],
                "size": [1920, 1080],
                "start_frame": 0,
                "duration_frames": duration,
            },
            {
                "id": "phrase",
                "type": "text",
                "text": text,
                "size": style["box"],
                "position": style["position"],
                "enable_3d": True,
                "style": {
                    "font": font,
                    "font_size": font_size,
                    "fill": style["fill"],
                    "stroke": style["stroke"],
                    "glow": native.plan_glow(style),
                },
                "start_frame": 0,
                "duration_frames": duration,
                "animation": {"tracks": tracks},
                "text_animators": lowered["text_animators"],
            },
        ],
        "output": {
            "path": f"{motion['id']}_{Path(font).stem.lower()}.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("ChrononTemplate/catalog/motion_catalog.v1.json"))
    parser.add_argument("--style-catalog", type=Path, default=Path("ChrononTemplate/catalog/emitted.json"))
    parser.add_argument("--out", type=Path, default=Path("ChrononTemplate/out/typewriter_modern_base_v1_gpu"))
    parser.add_argument("--text", default="CHRONON")
    parser.add_argument("--font", default="assets/fonts/Poppins-Bold.ttf")
    parser.add_argument("--font-size", type=float, default=None)
    parser.add_argument("--duration", type=int, default=150)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text())
    emitted = json.loads(args.style_catalog.read_text())
    style = emitted["native_phrase_style"]
    by_id = {motion["id"]: motion for motion in catalog["motions"]}
    missing = [motion_id for motion_id in MOTIONS if motion_id not in by_id]
    if missing:
        raise SystemExit(f"missing motions: {', '.join(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)
    font_size = args.font_size if args.font_size is not None else style["font_size"]
    plans = []
    for motion_id in MOTIONS:
        plan = make_plan(by_id[motion_id], style, args.text, args.font, font_size, args.duration)
        filename = f"{motion_id}_{Path(args.font).stem.lower()}.plan.json"
        (args.out / filename).write_text(json.dumps(plan, indent=2) + "\n")
        plans.append({"id": motion_id, "plan": filename})

    manifest = {
        "source": str(args.catalog),
        "style_source": str(args.style_catalog),
        "base": "font_fleet_v1",
        "text": args.text,
        "font": args.font,
        "font_size": font_size,
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "duration_frames": args.duration},
        "glow": style["glow"],
        "three_d": {
            "enabled": True,
            "transforms": ["rotation_x", "rotation_y", "position_z"],
            "space": "layer_3d",
        },
        "motions": plans,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"emitted {len(plans)} native typewriter plans in {args.out}")


if __name__ == "__main__":
    main()
