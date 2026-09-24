#!/usr/bin/env python3
"""Emit native Chronon3D render plans from the ChrononTemplate motion catalog.

This is deliberately kept in ChrononTemplate.  It lowers the catalog's
editorial motion definitions directly to the Chronon3D render-plan contract;
RenderingGen is not involved in this path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MOTIONS = [
	"premium_soft_reveal",
	"precision_word_stagger",
	"masked_vertical_lift",
	"hero_scale_focus",
	"kinetic_keyword_lock",
	"depth_parallax_reveal",
	"glass_morphism_fade",
	"editorial_line_build",
	"soft_kinetic_rise",
	"magnetic_word_focus",
	"cinematic_camera_push",
	"isometric_plane_fold",
	"light_sweep_reveal",
	"precision_tracking_lock",
	"quiet_hero_settle",
]

PHRASES = {
	"premium_soft_reveal": "A QUIETLY POWERFUL IDEA",
	"precision_word_stagger": "EVERY DETAIL HAS A PURPOSE",
	"masked_vertical_lift": "RISE WITH INTENTION",
	"hero_scale_focus": "THE MOMENT THAT MATTERS",
	"kinetic_keyword_lock": "MAKE THE SIGNAL STAND OUT",
	"depth_parallax_reveal": "DEPTH CREATES PRESENCE",
	"glass_morphism_fade": "LIGHT THROUGH GLASS",
	"editorial_line_build": "EDIT WITH INTENTION",
	"soft_kinetic_rise": "MOTION THAT FEELS NATURAL",
	"magnetic_word_focus": "FOLLOW THE SIGNAL",
	"cinematic_camera_push": "THE CAMERA MOVES WITH YOU",
	"isometric_plane_fold": "A NEW DIMENSION",
	"light_sweep_reveal": "BRING THE IDEA TO LIGHT",
	"precision_tracking_lock": "EVERY DETAIL COUNTS",
	"quiet_hero_settle": "QUIETLY ICONIC",
}


def frame_value(value: Any) -> Any:
    """Convert catalog values to the scalar/array form accepted by Chronon3D."""

    if isinstance(value, list):
        return [float(v) for v in value]
    return float(value)


def plan_glow(style: dict[str, Any]) -> dict[str, Any]:
    """Return the native canary halo in chronon.render-plan.v2 form."""

    return dict(style["glow"])


def extended_keyframes(track: dict[str, Any], duration: int, enter: int) -> list[dict[str, Any]]:
    """Keep the motion visible, then return it to its initial state at the exit."""

    source = track.get("keyframes", [])
    if not source:
        return []

    values = [
        {
            "frame": int(k["frame"]),
            "value": frame_value(k["value"]),
        }
        for k in source
    ]
    first = values[0]["value"]
    last = values[-1]["value"]
    hold = max(enter, duration - 9)
    end = duration - 1

    # Do not duplicate existing boundary frames. The catalog's final value is
    # held until the final nine frames, then the opening state is restored.
    result = [k for k in values if k["frame"] < hold]
    if not result or result[-1]["frame"] != hold:
        result.append({"frame": hold, "value": last})
    if end > hold:
        result.append({"frame": end, "value": first})
    return result


def lowered_selector(animator: dict[str, Any], enter: int) -> dict[str, Any]:
    selector = animator.get("selector", {})
    kind = selector.get("kind", "glyph")
    staggered = bool(selector.get("stagger"))
    native_unit = kind
    # A non-staggered glyph selector is equivalent to selecting the whole
    # word for these phrase-level effects, and the native word unit avoids a
    # backend glyph-map edge case around spaces in a shaped run.
    lowered: dict[str, Any] = {
        "id": f"{animator['id']}_selector",
        "unit": native_unit,
        "shape": selector.get("shape", "smooth"),
        "order": selector.get("order", "forward"),
        "combine": "replace",
        "exclude_spaces": True,
    }
    if staggered:
        lowered["start"] = {
            "property": "start",
            "keyframes": [{"frame": 0, "value": 0}],
            "easing": "linear",
        }
        # Chronon3D selectors are a window: start is the leading edge and
        # end is the reveal edge. Animating start to 100 would collapse the
        # window at the end and leave only partial glyphs visible.
        lowered["end"] = {
            "property": "end",
            "keyframes": [
                {"frame": 0, "value": 0},
                {"frame": enter, "value": 100},
            ],
            "easing": "out_cubic",
        }
    else:
        # Make a non-staggered animator affect every glyph. This avoids the
        # zero-width default selector used by older render-plan producers.
        lowered["shape"] = "square"
        lowered["start"] = {
            "property": "start",
            "keyframes": [{"frame": 0, "value": 0}],
            "easing": "linear",
        }
        lowered["end"] = {
            "property": "end",
            "keyframes": [{"frame": 0, "value": 100}],
            "easing": "linear",
        }
    return lowered


def lower_motion(motion: dict[str, Any], duration: int) -> dict[str, Any]:
    enter = min(int(motion.get("enter", 72)), duration - 1)
    tracks: list[dict[str, Any]] = []
    for track in motion.get("tracks", []):
        tracks.append(
            {
                "property": track["property"],
                "keyframes": extended_keyframes(track, duration, enter),
                "easing": track.get("easing", "linear"),
            }
        )

    # Every phrase has a real layer-level entrance/hold/exit. This is an
    # additional safety net for motions whose selector is line-based.
    if not any(track["property"] == "opacity" for track in tracks):
        tracks.append(
            {
                "property": "opacity",
                "keyframes": [
                    {"frame": 0, "value": 0},
                    {"frame": 8, "value": 1},
                    {"frame": duration - 9, "value": 1},
                    {"frame": duration - 1, "value": 0},
                ],
                "easing": "linear",
            }
        )

    animators = []
    for animator in motion.get("text_animators", []):
        animators.append(
            {
                "id": animator["id"],
                "selectors": [lowered_selector(animator, enter)],
                "properties": [
                    {
                        "property": prop["property"],
                        "keyframes": extended_keyframes(prop, duration, enter),
                        "easing": prop.get("easing", "linear"),
                    }
                    for prop in animator.get("properties", [])
                ],
            }
        )

    return {"tracks": tracks, "text_animators": animators}


def make_plan(motion: dict[str, Any], duration: int, style: dict[str, Any]) -> dict[str, Any]:
    motion_id = motion["id"]
    lowered = lower_motion(motion, duration)
    glow = plan_glow(style)
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"chronontemplate_native_{motion_id}",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": 24,
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
                "text": PHRASES[motion_id],
                "size": style["box"],
                "position": style["position"],
                "style": {
                    "font": style["font"],
                    "font_size": style["font_size"],
                    "fill": style["fill"],
                    "stroke": style["stroke"],
                    "glow": glow,
                },
                "start_frame": 0,
                "duration_frames": duration,
                "animation": lowered["tracks"] and {"tracks": lowered["tracks"]},
                "text_animators": lowered["text_animators"],
            },
        ],
        "output": {
            "path": f"{motion_id}.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("ChrononTemplate/catalog/motion_catalog.v1.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("ChrononTemplate/out/native_phrase_pack_v1"),
    )
    parser.add_argument(
        "--style-catalog",
        type=Path,
        default=Path("ChrononTemplate/catalog/emitted.json"),
        help="C++-emitted catalog containing native_phrase_style",
    )
    parser.add_argument("--duration", type=int, default=120)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text())
    emitted = json.loads(args.style_catalog.read_text())
    style = emitted.get("native_phrase_style")
    required_style = {"font", "font_size", "box", "position", "background", "fill", "stroke", "glow"}
    missing = sorted(required_style - style.keys()) if isinstance(style, dict) else []
    if not isinstance(style, dict) or missing:
        raise SystemExit(
            f"invalid native_phrase_style in {args.style_catalog}: "
            f"missing {', '.join(missing) if missing else 'object'}"
        )
    by_id = {motion["id"]: motion for motion in catalog["motions"]}
    missing = [motion_id for motion_id in MOTIONS if motion_id not in by_id]
    if missing:
        raise SystemExit(f"missing ChrononTemplate motions: {', '.join(missing)}")
    if args.duration < 30:
        raise SystemExit("duration must leave room for entrance and exit")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": str(args.catalog),
        "style_source": str(args.style_catalog),
        "pipeline": "ChrononTemplate -> Chronon3D native render-plan",
        "canvas": {"width": 1920, "height": 1080, "fps": 24, "duration_frames": args.duration},
        "style": style,
        "motions": [],
    }
    for motion_id in MOTIONS:
        plan = make_plan(by_id[motion_id], args.duration, style)
        destination = args.out / f"{motion_id}.plan.json"
        destination.write_text(json.dumps(plan, indent=2) + "\n")
        manifest["motions"].append({"id": motion_id, "plan": destination.name, "phrase": PHRASES[motion_id]})
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"emitted {len(MOTIONS)} native ChrononTemplate plans in {args.out}")


if __name__ == "__main__":
    main()
