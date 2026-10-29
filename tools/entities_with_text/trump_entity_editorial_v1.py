#!/usr/bin/env python3
"""Render a Trump portrait + animated editorial title as PNG frames, software-only."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
WORKSPACE = TEMPLATE.parent
OUT_DEFAULT = TEMPLATE / "out/trump_style_entity_v1"
IMAGE = "ChrononTemplate/assets/trump_style_v1/donald_trump_oval_office_2025.jpg"
FONT = "ChrononTemplate/assets/fonts/"
FRAME_COUNT = 150

_spec = importlib.util.spec_from_file_location(
    "entity_presentation_v1",
    TEMPLATE / "tools/entities_with_text/build_entity_presentation_v1.py")
assert _spec and _spec.loader
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)


def build_plan() -> dict:
    layers = [
        BASE.color_layer("background", [1920, 1080], [960, 540], 0, FRAME_COUNT,
                         [0.035, 0.052, 0.075, 1]),
        BASE.color_layer("left-rule", [4, 920], [112, 540], 0, FRAME_COUNT,
                         [0.78, 0.19, 0.22, 1]),
    ]
    portrait = {
        "id": "donald-trump-photo", "type": "image", "asset": IMAGE,
        "size": [760, 680], "fit": "cover",
        "position": BASE.renderer_center_position([1370, 490]),
        "start_frame": 0, "duration_frames": FRAME_COUNT,
        "animation": {"tracks": [
            BASE.track("opacity", [(0, 0), (22, 1), (149, 1)]),
            BASE.track("scale", [(0, .91), (62, 1.035), (88, 1), (149, 1)]),
            BASE.track("position_x", [(0, 82), (66, 0), (149, -12)]),
        ]}, "effects": [],
    }
    BASE.add_entity_image_frame(portrait, image_radius=6, stroke_width=4)
    layers.append(portrait)
    layers.extend([
        BASE.layer_text("eyebrow", "THE WHITE HOUSE  /  2025", [740, 32], [525, 268],
                        0, FRAME_COUNT, font=FONT + "Inter-Bold.ttf", font_size=20,
                        fill="#D8B977",
                        tracks=[BASE.track("opacity", [(0, 0), (18, 1), (149, 1)])]),
        BASE.layer_text("title", "DONALD J.\nTRUMP", [800, 300], [540, 450],
                        0, FRAME_COUNT, font=FONT + "Anton-Regular.ttf", font_size=116,
                        min_font_size=94, fill="#F3F0E8",
                        tracks=[BASE.track("opacity", [(0, 0), (32, 1), (149, 1)]),
                                BASE.track("position_x", [(0, 42), (48, 0), (149, 0)])]),
        BASE.layer_text("subtitle", "A return to the Oval Office", [760, 55], [500, 735],
                        26, FRAME_COUNT - 26, font=FONT + "Inter-Medium.ttf", font_size=27,
                        fill="#BAC6D0",
                        tracks=[BASE.track("opacity", [(0, 0), (39, 1), (123, 1)]),
                                BASE.track("position_y", [(0, 24), (42, 0), (123, 0)])]),
        BASE.layer_text("date", "OVAL OFFICE  /  FEBRUARY 2025", [760, 32], [500, 820],
                        42, FRAME_COUNT - 42, font=FONT + "Inter-SemiBold.ttf", font_size=18,
                        fill="#F0EDE4",
                        tracks=[BASE.track("opacity", [(0, 0), (36, 1), (107, 1)])]),
        BASE.layer_text("source", "OFFICIAL WHITE HOUSE PHOTO  ·  OVAL OFFICE", [760, 28],
                        [500, 964], 0, FRAME_COUNT, font=FONT + "Inter-Regular.ttf",
                        font_size=14, fill="#8293A1"),
    ])
    plan = BASE.scene_plan("trump_entity_editorial_v1", layers, FRAME_COUNT)
    plan["output"] = {"path": "trump_entity_editorial_v1.mp4", "format": "mp4", "codec": "h264"}
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=Path(os.environ.get(
        "CHRONON_CLI", WORKSPACE /
        "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")))
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--assets-root", type=Path, default=WORKSPACE)
    parser.add_argument("--frames", type=int, nargs="+", default=[18, 40, 64, 92, 120, 149])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / "trump_entity_editorial_v1.plan.json"
    plan_path.write_text(json.dumps(build_plan(), indent=2) + "\n", encoding="utf-8")
    cli = args.cli.resolve()
    subprocess.run([str(cli), "validate", "--plan", str(plan_path),
                    "--assets-root", str(args.assets_root.resolve()), "--profile", "preview"],
                   check=True, cwd=WORKSPACE)
    for frame in args.frames:
        if not 0 <= frame < FRAME_COUNT:
            raise SystemExit(f"frame outside range: {frame}")
        raw = args.out / f"frame_{frame:03d}.rgba"
        png = args.out / f"trump_entity_{frame:03d}.png"
        subprocess.run([str(cli), "render", "--backend", "software", "--plan", str(plan_path),
                        "--assets-root", str(args.assets_root.resolve()), "--video-sink", "raw",
                        "--pipe-pixfmt", "rgba", "--start-frame", str(frame),
                        "--end-frame", str(frame), "-o", str(raw)], check=True, cwd=WORKSPACE)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo",
                        "-pixel_format", "rgba", "-video_size", "1920x1080",
                        "-i", str(raw), "-frames:v", "1", str(png)],
                       check=True, cwd=WORKSPACE)
        raw.unlink()
        print(png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
