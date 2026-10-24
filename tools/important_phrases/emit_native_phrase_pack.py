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


def easing_value(name: str, t: float) -> float:
    """GLM-compatible easing polynomials, used to bake text-animator tracks."""

    import math

    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if name == "linear":
        return t
    if name == "smoothstep":
        return t * t * (3.0 - 2.0 * t)
    if name == "in_quad":
        return t * t
    if name == "out_quad":
        return -(t * (t - 2.0))
    if name == "in_cubic":
        return t * t * t
    if name == "out_cubic":
        f = t - 1.0
        return f * f * f + 1.0
    if name == "in_out_cubic":
        if t < 0.5:
            return 4.0 * t * t * t
        f = 2.0 * t - 2.0
        return 0.5 * f * f * f + 1.0
    if name == "in_sine":
        return math.sin((t - 1.0) * math.pi / 2.0) + 1.0
    if name == "out_sine":
        return math.sin(t * math.pi / 2.0)
    if name == "in_out_sine":
        return 0.5 * (1.0 - math.cos(t * math.pi))
    if name == "out_back":
        o = 1.70158
        n = t - 1.0
        return n * n * ((o + 1.0) * n + o) + 1.0
    raise SystemExit(f"unsupported text-animator easing: {name}")


def baked_keyframes(track: dict[str, Any], duration: int, enter: int) -> list[dict[str, Any]]:
    """Sample a track per frame: Chronon3D text animators are linear-only."""

    keys = extended_keyframes(track, duration, enter)
    points = [(int(k["frame"]), float(k["value"])) for k in keys]
    baked = []
    segment = 0
    for frame in range(duration):
        while segment + 1 < len(points) and frame > points[segment + 1][0]:
            segment += 1
        value = points[-1][1]
        if segment + 1 < len(points):
            start, start_value = points[segment]
            end, end_value = points[segment + 1]
            if frame <= start:
                value = start_value
            elif end <= start:
                value = end_value
            else:
                t = (frame - start) / (end - start)
                eased = easing_value(track.get("easing", "linear"), t)
                value = start_value + (end_value - start_value) * eased
        baked.append({"frame": frame, "value": value})
    return baked


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
        # A reveal window keeps the tail pinned open and sweeps its leading
        # edge forward: units ahead of the edge still carry the animator's
        # hidden value, units behind it fall back to the layer's rest style.
        # The inverted ramp (start 0 -> 100) is what makes the effect a
        # reveal instead of a wipe that leaves the last unit hidden.
        lowered["start"] = {
            "keyframes": [
                {"frame": 0, "value": 0},
                {"frame": enter, "value": 100},
            ],
            "easing": "linear",
        }
        lowered["end"] = {
            "keyframes": [{"frame": 0, "value": 100}],
            "easing": "linear",
        }
    else:
        # Make a non-staggered animator affect every glyph. This avoids the
        # zero-width default selector used by older render-plan producers.
        lowered["shape"] = "square"
        lowered["start"] = {
            "keyframes": [{"frame": 0, "value": 0}],
            "easing": "linear",
        }
        lowered["end"] = {
            "keyframes": [{"frame": 0, "value": 100}],
            "easing": "linear",
        }
    return lowered


def lower_motion(motion: dict[str, Any], duration: int) -> dict[str, Any]:
    # 60 frames = two seconds at 30 fps; matches kPhraseEnterFrames in
    # include/chronontemplate/important_phrases/ImportantPhrasePack.hpp.
    enter = min(int(motion.get("enter", 60)), duration - 1)
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
    for index, animator in enumerate(motion.get("text_animators", [])):
        if "id" not in animator:
            animator = {**animator, "id": f"{motion['id']}_animator_{index}"}
        animators.append(
            {
                "id": animator["id"],
                "selectors": [lowered_selector(animator, enter)],
                "properties": [
                    {
                        "property": prop["property"],
                        "keyframes": baked_keyframes(prop, duration, enter),
                        "easing": "linear",
                    }
                    for prop in animator.get("properties", [])
                ],
            }
        )

    return {"tracks": tracks, "text_animators": animators}


# The Classic Apple long-phrase set: five short-phrase recipes re-authored
# for wrapped phrases (line selectors, so each line joins the reveal in turn).
CLASSIC_MOTIONS = [
    "classic_playfair_baseline_rise",
    "classic_playfair_tracking_close",
    "classic_playfair_focus_resolve",
    "classic_playfair_quiet_zoom",
    "classic_playfair_glyph_curtain",
]

# One long, wrapped Italian phrase for every recipe: comparing the five
# animations on the same three-line copy is what makes the review meaningful.
CLASSIC_PHRASE = "Le parole giuste\narrivano al momento\ngiusto"


def text_style(style: dict[str, Any]) -> dict[str, Any]:
    """Lower the appearance, adding the paper card when the style owns one."""

    lowered = {
        "font": style["font"],
        "font_size": style["font_size"],
        "fill": style["fill"],
        "stroke": style["stroke"],
        "glow": plan_glow(style),
    }
    card = style.get("card")
    if card:
        padding = card.get("padding", [0, 0])
        background = {
            "color": card["color"],
            "radius": float(card.get("radius", 0)),
            "padding": [float(padding[0]), float(padding[1])],
        }
        if "opacity" in card:
            background["opacity"] = float(card["opacity"])
        lowered["background"] = background
    return lowered


def make_plan(
    motion: dict[str, Any],
    duration: int,
    style: dict[str, Any],
    phrases: dict[str, str],
    fps: int = 24,
) -> dict[str, Any]:
    motion_id = motion["id"]
    lowered = lower_motion(motion, duration)
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": f"chronontemplate_native_{motion_id}",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": fps,
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
                "text": phrases[motion_id],
                "size": style["box"],
                "position": style["position"],
                "style": text_style(style),
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
        default=Path("ChrononTemplate/catalog/chronontemplate_catalog.v1.json"),
        help="C++-emitted catalog containing native_phrase_style",
    )
    parser.add_argument("--duration", type=int, default=None)
    parser.add_argument(
        "--classic-style",
        type=Path,
        default=Path("ChrononTemplate/catalog/classic_phrase_style.v1.json"),
        help="Classic Apple long-phrase appearance (Playfair, black ink, paper card)",
    )
    parser.add_argument(
        "--pack",
        choices=("native", "classic-long"),
        default="native",
        help="native: 15 Unicode phrases; classic-long: the Classic Apple long set",
    )
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text())
    required_style = {"font", "font_size", "box", "position", "background", "fill", "stroke", "glow"}
    if args.pack == "classic-long":
        motion_ids = CLASSIC_MOTIONS
        phrases = {motion_id: CLASSIC_PHRASE for motion_id in motion_ids}
        style = json.loads(args.classic_style.read_text())
        style_source = str(args.classic_style)
        duration = args.duration or 150
        fps = 30
    else:
        motion_ids = MOTIONS
        phrases = PHRASES
        emitted = json.loads(args.style_catalog.read_text())
        style = emitted.get("native_phrase_style")
        style_source = str(args.style_catalog)
        duration = args.duration or 120
        fps = 24
    missing = sorted(required_style - style.keys()) if isinstance(style, dict) else []
    if not isinstance(style, dict) or missing:
        raise SystemExit(
            f"invalid phrase style in {style_source}: "
            f"missing {', '.join(missing) if missing else 'object'}"
        )
    by_id = {motion["id"]: motion for motion in catalog["motions"]}
    missing = [motion_id for motion_id in motion_ids if motion_id not in by_id]
    if missing:
        raise SystemExit(f"missing ChrononTemplate motions: {', '.join(missing)}")
    if duration < 30:
        raise SystemExit("duration must leave room for entrance and exit")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": str(args.catalog),
        "style_source": style_source,
        "pipeline": "ChrononTemplate -> Chronon3D native render-plan",
        "canvas": {"width": 1920, "height": 1080, "fps": fps, "duration_frames": duration},
        "style": style,
        "motions": [],
    }
    for motion_id in motion_ids:
        plan = make_plan(by_id[motion_id], duration, style, phrases, fps)
        destination = args.out / f"{motion_id}.plan.json"
        destination.write_text(json.dumps(plan, indent=2) + "\n")
        manifest["motions"].append({"id": motion_id, "plan": destination.name, "phrase": phrases[motion_id]})
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"emitted {len(motion_ids)} native ChrononTemplate plans in {args.out}")


if __name__ == "__main__":
    main()
