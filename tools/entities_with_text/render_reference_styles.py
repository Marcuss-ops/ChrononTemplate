#!/usr/bin/env python3
"""Style stills: recreate the two reference screenshots as PNG renders.

Two single-still plans, both 1920x1080:

1. ``reference_dark_cards.png`` — dark textured board, faint cross grid,
   two cream photo cards side by side with a small blue caption
   (the dark-collage style of reference screenshot 1).
2. ``reference_archive_paper.png`` — peach archive paper with the
   top-left ``Archive image`` label and two named photo cards
   (the archive-paper style of reference screenshot 2; reuses the
   verified gallery plan builder).

Example::

    python render_reference_styles.py --render
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__)
ROOT = SCRIPT.parents[2]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(SCRIPT.parent))

from render_archive_gallery_pan import _camera, _default_cli  # noqa: E402

WIDTH, HEIGHT = 1920, 1080
FONT_BLUE = "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_CAPTION = "ChrononTemplate/assets/fonts/didone_font_playfair_display_italic.ttf"

IMAGES = [
    ("ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png", "Al Capone"),
    ("ChrononTemplate/assets/archival_refs_v2/von_puckler_source.png", "Von Puckler"),
]

BOARD_COLOR = [0.055, 0.055, 0.062, 1.0]            # near-black board
PAPER_COLOR = [0.937, 0.780, 0.639, 1.0]            # peach archive paper
CARD_COLOR = [0.954, 0.922, 0.874, 1.0]             # cream photo card
CAPTION_COLOR = "#2b1b12"                           # deep sepia caption
GRID_COLOR = [1.0, 1.0, 1.0, 0.05]                  # faint grid lines
SPECK_COLOR = [1.0, 1.0, 1.0, 0.55]                 # light scratches
BLUE_CAPTION = "#4da3ff"


def _hex_rgba(hex_color: str) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def build_dark_cards_plan() -> dict:
    """Dark board, faint grid, two tilted photo cards, blue caption."""
    layers = [
        {"id": "board", "type": "color", "color": BOARD_COLOR,
         "size": [WIDTH, HEIGHT], "screen_space": True,
         "start_frame": 0, "duration_frames": 1},
    ]
    for step in range(80, WIDTH, 160):              # vertical grid lines
        layers.append({
            "id": f"grid-v-{step}", "type": "shape",
            "size": [2, HEIGHT], "position": [step, 0],
            "screen_space": True, "start_frame": 0, "duration_frames": 1,
            "shape": {"type": "rect", "fill": GRID_COLOR},
        })
    for step in range(80, HEIGHT, 160):             # horizontal grid lines
        layers.append({
            "id": f"grid-h-{step}", "type": "shape",
            "size": [WIDTH, 2], "position": [0, step],
            "screen_space": True, "start_frame": 0, "duration_frames": 1,
            "shape": {"type": "rect", "fill": GRID_COLOR},
        })
    # Deterministic speck scratches (x, y, size).
    for index, (sx, sy, s) in enumerate([
        (260, 180, 3), (640, 520, 2), (920, 240, 3), (1180, 700, 2),
        (1420, 380, 3), (330, 880, 2), (760, 960, 3), (1060, 120, 2),
        (1560, 200, 3), (480, 360, 2), (1680, 820, 3), (880, 800, 2),
    ]):
        layers.append({
            "id": f"speck-{index:02d}", "type": "shape",
            "size": [s, s], "position": [sx, sy],
            "start_frame": 0, "duration_frames": 1,
            "shape": {"type": "rect", "fill": SPECK_COLOR},
        })

    # Two photo cards: cream border plate behind the inset photo. Sizes fit
    # the visible world width (~1228 units at camera z=-1180, fov 55) so
    # neither card is clipped, matching the reference margins.
    cards = [
        (-320, -2.4, "ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png"),
        (320, 2.0, "ChrononTemplate/assets/archival_refs_v2/von_puckler_source.png"),
    ]
    for index, (x_world, tilt, asset) in enumerate(cards):
        layers.append({
            "id": f"plate-{index}", "type": "shape",
            "size": [580, 780],
            "position": [x_world, 0.0, 2.0],
            "rotation": [0.0, 0.0, tilt],
            "enable_3d": True, "start_frame": 0, "duration_frames": 1,
            "shape": {"type": "rect", "fill": CARD_COLOR},
        })
        layers.append({
            "id": f"photo-{index}", "type": "image", "asset": asset,
            "size": [520, 700],
            "position": [x_world, 10.0, 0.0],
            "rotation": [0.0, 0.0, tilt],
            "fit": "cover", "enable_3d": True,
            "start_frame": 0, "duration_frames": 1,
        })
    # Small blue caption along the bottom, like the reference stamp.
    layers.append({
        "id": "blue-caption", "type": "text",
        "text": "ARCHIVE  CLIP 24",
        "size": [520, 60], "position": [960, 1010],
        "start_frame": 0, "duration_frames": 1,
        "style": {"font": FONT_BLUE, "font_size": 40,
                  "fill": BLUE_CAPTION},
    })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "reference_dark_cards",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": 30,
                   "fps_den": 1, "duration_frames": 1},
        "camera": _camera(-1180.0),
        "layers": layers,
        # codec enum only accepts video codecs; the -o .png decides the writer.
        "output": {"path": "reference_dark_cards.png",
                   "format": "mp4", "codec": "h264"},
    }


def build_archive_paper_plan() -> dict:
    """Peach paper, 'Archive image' label, two named photo cards that fit."""
    total_frames = 1
    layers = [
        {"id": "paper", "type": "color", "color": PAPER_COLOR,
         "size": [WIDTH, HEIGHT], "screen_space": True,
         "start_frame": 0, "duration_frames": total_frames},
        {"id": "label", "type": "text", "text": "Archive image",
         "size": [640, 60], "position": [170, 115], "screen_space": True,
         "start_frame": 0, "duration_frames": total_frames,
         "style": {"font": FONT_BLUE, "font_size": 38, "fill": "#1f1710"}},
        {"id": "rule", "type": "shape",
         "size": [210, 3], "position": [170, 152], "screen_space": True,
         "start_frame": 0, "duration_frames": total_frames,
         "shape": {"type": "rect", "fill": [0.12, 0.09, 0.06, 1.0]}},
    ]
    # Cards must stay inside the visible world width (~1228 units at
    # camera z=-1180): 2 plates plus the middle gap.
    for index, (asset, caption) in enumerate(IMAGES):
        x_world = -320.0 if index == 0 else 315.0
        tilt = -1.8 if index == 0 else 1.8
        layers.append({
            "id": f"plate-{index}", "type": "shape",
            "size": [600, 560],
            "position": [x_world, 40.0, 2.0],
            "rotation": [0.0, 0.0, tilt],
            "enable_3d": True, "start_frame": 0, "duration_frames": total_frames,
            "shape": {"type": "rect", "fill": CARD_COLOR},
        })
        layers.append({
            "id": f"photo-{index}", "type": "image", "asset": asset,
            "size": [540, 400],
            "position": [x_world, 170.0, 0.0],
            "rotation": [0.0, 0.0, tilt],
            "fit": "cover", "enable_3d": True,
            "start_frame": 0, "duration_frames": total_frames,
        })
        layers.append({
            "id": f"caption-{index}", "type": "text", "text": caption,
            "size": [560, 70], "position": [x_world, -190.0],
            "rotation": [0.0, 0.0, tilt],
            "enable_3d": True, "start_frame": 0, "duration_frames": total_frames,
            "style": {"font": FONT_CAPTION, "font_size": 46,
                      "fill": CAPTION_COLOR},
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "reference_archive_paper",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": 30,
                   "fps_den": 1, "duration_frames": total_frames},
        "camera": _camera(-1180.0),
        "layers": layers,
        "output": {"path": "reference_archive_paper.png",
                   "format": "mp4", "codec": "h264"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true",
                        help="render the stills with the Chronon3D CLI")
    parser.add_argument("--backend", choices=("software", "vulkan"),
                        default="software")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "out/reference_styles")
    parser.add_argument("--cli", type=Path, default=None)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)

    style_a = build_dark_cards_plan()
    style_b = build_archive_paper_plan()
    for name, plan in (("reference_dark_cards", style_a),
                       ("reference_archive_paper", style_b)):
        plan_path = args.out / f"{name}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {plan_path}")

    if not args.render:
        return 0
    cli = (args.cli or _default_cli()).resolve()
    if not cli.is_file():
        raise SystemExit(f"Chronon3D CLI not found: {cli}")

    renders = [
        (args.out / "reference_dark_cards.plan.json",
         args.out / "reference_dark_cards.png"),
        (args.out / "reference_archive_paper.plan.json",
         args.out / "reference_archive_paper.png"),
    ]
    for plan_path, png in renders:
        # The direct -o .png writer frames the scene differently than the
        # video pipeline; render through the verified raw-YUV route and
        # convert with ffmpeg so the still matches the video framing.
        yuv = png.with_suffix(".yuv.tmp")
        cmd = [str(cli), "render", "--backend", args.backend,
               "--plan", str(plan_path), "--assets-root", str(WORKSPACE),
               "-o", str(yuv), "--video-sink", "raw",
               "--pipe-pixfmt", "yuv420p"]
        subprocess.run(cmd, check=True, cwd=WORKSPACE)
        subprocess.run(["ffmpeg", "-y", "-v", "error",
                        "-f", "rawvideo", "-pix_fmt", "yuv420p",
                        "-s", "1920x1080", "-r", "30", "-i", str(yuv),
                        "-frames:v", "1", str(png)], check=True, cwd=WORKSPACE)
        yuv.unlink()
        print(f"Rendered {png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
