#!/usr/bin/env python3
"""Render eight clean Apple-style portrait and name studies on Vulkan/NVENC."""
from __future__ import annotations

import io
import json
import sys
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import build_entity_caption_reference_v3 as base  # noqa: E402

OUT = ROOT / "out/entity_caption_apple_v1"
ASSET_ROOT = base.ASSET_ROOT
W, H, FPS, FRAMES = 1920, 1080, 30, 150
FONT = "Bricolage-Grotesque.ttf"
NAME = "DONALD TRUMP"
BG = "assets/plates"
PORTRAIT = "assets/portraits/donald-trump-apple.png"

STUDIES = [
    ("soft_spring", "Soft Spring", [
        base.kf("position_y", [(0, 64), (28, 0)], "out_cubic"),
        base.kf("scale", [(0, 0.92), (34, 1.0)], "out_cubic"),
        base.kf("opacity", [(0, 0), (14, 1)], "out_cubic")]),
    ("focus_reveal", "Focus Reveal", [
        base.kf("blur", [(0, 14), (24, 0)], "out_cubic"),
        base.kf("scale", [(0, 1.025), (32, 1.0)], "out_cubic"),
        base.kf("opacity", [(0, 0.15), (12, 1)], "out_cubic")]),
    ("parallax_drift", "Parallax Drift", [
        base.kf("position_x", [(0, -78), (36, 0)], "out_cubic"),
        base.kf("position_y", [(0, 18), (36, 0)], "out_cubic"),
        base.kf("scale", [(0, 1.035), (36, 1.0)], "in_out_sine")]),
    ("perspective_turn", "Perspective Turn", [
        base.kf("rotation_y", [(0, -22), (34, 0)], "out_cubic"),
        base.kf("position_x", [(0, -36), (34, 0)], "out_cubic"),
        base.kf("opacity", [(0, 0.1), (14, 1)], "out_cubic")]),
    ("lift_settle", "Lift and Settle", [
        base.kf("position_y", [(0, 80), (28, -3), (40, 0)], "out_cubic"),
        base.kf("scale", [(0, 0.96), (32, 1.0)], "out_cubic"),
        base.kf("opacity", [(0, 0), (10, 1)], "out_cubic")]),
    ("vertical_pan", "Vertical Pan", [
        base.kf("position_y", [(0, -95), (38, 0)], "out_cubic"),
        base.kf("scale_x", [(0, 0.95), (38, 1.0)], "out_cubic"),
        base.kf("opacity", [(0, 0.1), (12, 1)], "out_cubic")]),
    ("quiet_orbit", "Quiet Orbit", [
        base.kf("rotation_z", [(0, -3.0), (28, 0)], "out_cubic"),
        base.kf("scale", [(0, 0.97), (34, 1.0)], "out_cubic"),
        base.kf("position_x", [(0, -24), (30, 0)], "out_cubic")]),
    ("soft_zoom", "Soft Zoom", [
        base.kf("scale", [(0, 0.82), (24, 1.025), (42, 1.0)], "out_back"),
        base.kf("opacity", [(0, 0), (13, 1)], "out_cubic")]),
]


def make_plate(index: int) -> Path:
    path = ASSET_ROOT / BG / f"apple-entity-{index+1:02d}.png"
    im = Image.new("RGBA", (W, H), (250, 250, 248, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Whisper-soft Apple-like portrait card, shadow and abstract accents only;
    # all copy remains editable in the separate native text layer.
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    if index in (0, 4):
        sd.rounded_rectangle((146, 86, 800, 1000), radius=34, fill=(24, 28, 32, 28))
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(24)))
        d.rounded_rectangle((140, 78, 790, 990), radius=30, fill=(255, 255, 255, 255), outline=(229, 230, 232, 255), width=2)
    elif index in (1, 5):
        d.ellipse((55, 205, 875, 1025), fill=(244, 245, 246, 255))
        d.ellipse((89, 239, 841, 991), outline=(231, 233, 235, 255), width=2)
    elif index in (2, 6):
        d.rounded_rectangle((112, 118, 824, 954), radius=38, fill=(246, 247, 248, 255))
        d.line((866, 172, 866, 898), fill=(224, 226, 229, 255), width=2)
    else:
        d.rounded_rectangle((154, 84, 786, 996), radius=20, outline=(225, 227, 230, 255), width=2)
        d.ellipse((65, 90, 280, 305), fill=(245, 246, 247, 255))
    im.convert("RGB").save(path, optimize=True)
    return path


def plan_for(index: int) -> dict:
    motion_id, label, tracks = STUDIES[index]
    plate = make_plate(index)
    name_tracks = [base.kf("position_y", [(0, -14), (26, 0)], "out_cubic"),
                   base.kf("opacity", [(0, 0), (16, 1)], "out_cubic")]
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"entity_apple_{motion_id}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": [
            {"id": "apple-white-stage", "type": "image", "asset": f"{BG}/{plate.name}",
             "size": [W, H], "fit": "cover", "position": [0, 0], "start_frame": 0,
             "duration_frames": FRAMES},
            {"id": "entity-portrait", "type": "image", "asset": PORTRAIT,
             "size": [620, 840], "fit": "contain", "position": [-500, 0],
             "start_frame": 0, "duration_frames": FRAMES, "enable_3d": True,
             "animation": {"tracks": tracks}},
            base.text_layer("profile-name", NAME, (1310, 540), (1020, 190), FONT, 92,
                            "#161718", name_tracks),
        ],
        "output": {"path": f"entity_apple_{motion_id}.mp4", "format": "mp4", "codec": "h264"},
    }


def contact_sheet() -> Path:
    sheet = Image.new("RGB", (1940, 2 * 570 + 80), (248, 248, 246))
    d = ImageDraw.Draw(sheet)
    label_font = base.font(FONT, 22)
    d.text((28, 18), "DONALD TRUMP · APPLE MOTION STUDIES", font=label_font, fill=(30, 31, 33))
    for i, (motion_id, label, _) in enumerate(STUDIES):
        clip = OUT / f"entity_apple_{motion_id}.mp4"
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "2.0", "-i", str(clip),
                              "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                             check=True, stdout=subprocess.PIPE).stdout
        frame = Image.open(io.BytesIO(raw)).convert("RGB").resize((940, 528), Image.Resampling.LANCZOS)
        col, row = i % 2, i // 2
        x, y = 20 + col * 960, 58 + row * 570
        sheet.paste(frame, (x, y))
        d.text((x + 8, y + 534), label.upper(), font=label_font, fill=(42, 43, 45))
    path = OUT / "entity_apple_v1_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    portrait = base.grayscale_photo()
    portrait.save(ASSET_ROOT / PORTRAIT)
    # Chronon fonts are shared with the prior reference pack.
    (ASSET_ROOT / "assets/fonts").mkdir(parents=True, exist_ok=True)
    for i, (motion_id, _label, _tracks) in enumerate(STUDIES):
        plan = plan_for(i)
        plan_path = OUT / f"entity_apple_{motion_id}.plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        base.render(plan_path, OUT / f"entity_apple_{motion_id}.mp4", base.CLI)
    print("CONTACT_SHEET", contact_sheet())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
