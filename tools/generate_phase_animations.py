#!/usr/bin/env python3
"""Generate the first reusable ChrononTemplate editorial phase animations.

The plans deliberately stay inside the canonical render-plan contract.  The
visual language comes from catalog/emitted.json: black canvas, white face and
one Gaussian glow.  Chronon3D remains the authority for font loading,
shaping, compositing and encoding.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import emit_native_phrase_pack as native  # noqa: E402


FPS = 30
DURATION_SECONDS = 5
DURATION_FRAMES = FPS * DURATION_SECONDS
TITLE = "XANDER ZAYAS VS JARON ENNIS"


def keyframes(values: list[tuple[int, float]]) -> list[dict[str, Any]]:
    return [{"frame": frame, "value": value} for frame, value in values]


def track(property_name: str, values: list[tuple[int, float]], easing: str = "out_cubic") -> dict[str, Any]:
    return {
        "property": property_name,
        "keyframes": keyframes(values),
        "easing": easing,
    }


def base_plan(job_id: str, text: str, style: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": job_id,
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "layers": [
            {
                "id": "background",
                "type": "color",
                "color": style["background"],
                "size": [1920, 1080],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
            },
            {
                "id": "phrase",
                "type": "text",
                "text": text,
                "size": [1700, 360],
                "position": [960, 540],
                "style": {
                    "font": style["font"],
                    "font_size": 108,
                    "fill": style["fill"],
                    "stroke": style["stroke"],
                    "glow": native.plan_glow(style),
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
            },
        ],
        "output": {
            "path": f"{job_id}.mp4",
            "format": "mp4",
            "codec": "h264",
        },
    }


def three_d_plan(style: dict[str, Any]) -> dict[str, Any]:
    plan = base_plan("zayas_ennis_3d_orbit", TITLE, style)
    plan["layers"][1]["animation"] = {
        "tracks": [
            track("position_x", [(0, -280), (36, 0), (112, 0), (149, 240)]),
            track("rotation_x", [(0, 9), (52, 0), (112, 0), (149, -5)]),
            track("scale", [(0, 0.72), (38, 1.05), (58, 1), (112, 1), (149, 0.86)]),
            track("opacity", [(0, 0), (18, 1), (128, 1), (149, 0)], "linear"),
        ]
    }
    return plan


def typewriter_plan(style: dict[str, Any]) -> dict[str, Any]:
    plan = base_plan("zayas_ennis_typewriter", TITLE, style)
    plan["layers"][1]["animation"] = {
        "tracks": [
            track("scale", [(0, 0.96), (34, 1.015), (58, 1), (128, 1), (149, 0.98)]),
            track("opacity", [(0, 0), (15, 1), (132, 1), (149, 0)], "linear"),
        ]
    }
    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style-catalog", type=Path, default=Path("ChrononTemplate/catalog/emitted.json"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("ChrononTemplate/out/phase_animations_zayas_ennis_v1"),
    )
    args = parser.parse_args()

    emitted = json.loads(args.style_catalog.read_text())
    style = emitted.get("native_phrase_style")
    if not isinstance(style, dict):
        raise SystemExit(f"missing native_phrase_style in {args.style_catalog}")
    required = {"font", "background", "fill", "stroke", "glow"}
    missing = sorted(required - style.keys())
    if missing:
        raise SystemExit(f"native_phrase_style is missing: {', '.join(missing)}")

    args.out.mkdir(parents=True, exist_ok=True)
    plans = {
        "zayas_ennis_3d_orbit.plan.json": three_d_plan(style),
        "zayas_ennis_typewriter.plan.json": typewriter_plan(style),
    }
    for name, plan in plans.items():
        (args.out / name).write_text(json.dumps(plan, indent=2) + "\n")
    manifest = {
        "source": str(args.style_catalog),
        "title": TITLE,
        "canvas": {"width": 1920, "height": 1080, "fps": FPS, "duration_seconds": DURATION_SECONDS},
        "plans": sorted(plans),
        "styles": ["3d_orbit", "typewriter"],
        "typewriter_postprocess": "render_phase_animations.sh (left-to-right reveal mask)",
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"generated {len(plans)} ChrononTemplate phase plans in {args.out}")


if __name__ == "__main__":
    main()
