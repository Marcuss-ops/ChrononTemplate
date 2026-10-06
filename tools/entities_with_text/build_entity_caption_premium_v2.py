#!/usr/bin/env python3
"""Build and optionally render fifteen 5-second Trump entity-caption studies.

The motion recipes are owned by ``author_editorial_motions.py`` and its
ChrononTemplate catalog. This tool resolves those recipes into native V3
RenderPlans and renders them through Chronon3D for visual review.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
CHRONON = ROOT / "Chronon3d"
CATALOG = TEMPLATE / "catalog/motion_catalog.v1.json"
OUTPUT = TEMPLATE / "out/entity_caption_premium_v2"
ASSET_ROOT = OUTPUT
PORTRAIT = ROOT / "RenderingGen/renderinggen/out/editorial_v1/assets/canary/people-demo-portrait.png"
CLI = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
MOTION_IDS = [f"trump_entity_text_{index:02d}" for index in range(1, 16)]
PALETTES = [
    ("#F5F8FF", "#77E8FF", "assets/fonts/Montserrat-Bold.ttf"),
    ("#F6F1FF", "#B38AFF", "assets/fonts/Space-Grotesk.ttf"),
    ("#FFF6EA", "#FFB65C", "assets/fonts/Manrope.ttf"),
    ("#F2FAFF", "#55D6BE", "assets/fonts/Outfit.ttf"),
    ("#FFF3F6", "#FF5E8A", "assets/fonts/Sora.ttf"),
    ("#FFF8E9", "#F4C76A", "assets/fonts/PlayfairDisplay-Italic.ttf"),
    ("#F6F5FF", "#8D9BFF", "assets/fonts/Bricolage-Grotesque.ttf"),
    ("#EAF7FF", "#58C8FF", "assets/fonts/Instrument-Sans.ttf"),
    ("#F1FFF9", "#6FE1B5", "assets/fonts/DMSans-Bold.ttf"),
    ("#FFF7F0", "#FF9671", "assets/fonts/Bodoni72-BookItalic.ttf"),
]


def track(raw: dict) -> dict:
    keys = []
    for key in raw["keyframes"]:
        frame = min(47, round(key["frame"] * 0.8))
        converted = {"frame": frame, "value": key["value"]}
        if keys and keys[-1]["frame"] == frame:
            keys[-1] = converted
        else:
            keys.append(converted)
    if keys[-1]["frame"] < 47:
        keys.append({"frame": 47, "value": keys[-1]["value"]})
    return {"property": raw["property"], "easing": raw.get("easing", "out_cubic"),
            "keyframes": keys}


def build_plan(motion: dict, index: int) -> dict:
    white, accent, font = PALETTES[index % len(PALETTES)]
    duration = 48
    caption_tracks = [track(item) for item in motion["tracks"]]
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": motion["id"],
        "canvas": {"width": 1920, "height": 1080, "fps_num": 24,
                   "fps_den": 1, "duration_frames": duration},
        "layers": [
            {"id": "editorial-plate", "type": "image", "asset": f"assets/canary/plate-{index + 1:02d}.png",
             "size": [1920, 1080], "fit": "cover", "position": [0, 0],
             "start_frame": 0, "duration_frames": duration},
            {"id": "profile-name", "type": "image", "asset": f"assets/canary/title-{index + 1:02d}.png",
             "size": [1000, 180], "fit": "contain", "position": [320, -30], "start_frame": 0,
             "duration_frames": duration,
             "animation": {"tracks": caption_tracks}},
        ],
        "output": {"path": f"{motion['id']}.mp4", "format": "mp4", "codec": "h264"},
    }


def prepare_assets() -> None:
    (ASSET_ROOT / "assets/canary").mkdir(parents=True, exist_ok=True)
    (ASSET_ROOT / "assets/fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORTRAIT, ASSET_ROOT / "assets/canary/people-demo-portrait.png")
    fonts = {font for _, _, font in PALETTES} | {"assets/fonts/Space-Grotesk.ttf", "assets/fonts/Inter-SemiBold.ttf"}
    for logical in fonts:
        source = CHRONON / "assets" / logical.removeprefix("assets/")
        shutil.copy2(source, ASSET_ROOT / logical)
    portrait = Image.open(PORTRAIT).convert("RGB")
    kicker_font = ImageFont.truetype(str(ASSET_ROOT / "assets/fonts/Space-Grotesk.ttf"), 28)
    label_font = ImageFont.truetype(str(ASSET_ROOT / "assets/fonts/Inter-SemiBold.ttf"), 22)
    for index in range(1, len(MOTION_IDS) + 1):
        white, accent, font_name = PALETTES[(index - 1) % len(PALETTES)]
        font_path = ASSET_ROOT / font_name
        title_font = ImageFont.truetype(str(font_path), 94)
        title = Image.new("RGBA", (1200, 240), (0, 0, 0, 0))
        mask = Image.new("L", title.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((20, 34), "PROFILE NAME", font=title_font, fill=255,
                       stroke_width=1, stroke_fill=255)
        rgb = tuple(int(white[pos:pos + 2], 16) for pos in (1, 3, 5))
        glow_rgb = tuple(int(accent[pos:pos + 2], 16) for pos in (1, 3, 5))
        title = Image.new("RGBA", title.size, (0, 0, 0, 0))
        for radius, alpha in ((32, 70), (16, 110), (6, 90)):
            halo = mask.filter(ImageFilter.GaussianBlur(radius))
            halo = halo.point(lambda value, amount=alpha: value * amount // 255)
            title.alpha_composite(Image.new("RGBA", title.size, (*glow_rgb, 0)))
            tint = Image.new("RGBA", title.size, (*glow_rgb, 0))
            tint.putalpha(halo)
            title.alpha_composite(tint)
        crisp = Image.new("RGBA", title.size, (*rgb, 0))
        crisp.putalpha(mask)
        title.alpha_composite(crisp)
        title.save(ASSET_ROOT / f"assets/canary/title-{index:02d}.png", optimize=True)
        plate = Image.new("RGB", (1920, 1080), "#080D16")
        glow = Image.new("RGBA", plate.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        color = tuple(int(accent[pos:pos + 2], 16) for pos in (1, 3, 5))
        glow_draw.ellipse((940, 150, 1880, 1030), fill=(*color, 34))
        glow = glow.filter(ImageFilter.GaussianBlur(150))
        plate = Image.alpha_composite(plate.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(plate)
        draw.rectangle((0, 0, 22, 1080), fill=accent)
        draw.rounded_rectangle((148, 150, 762, 930), radius=38, fill="#EAF1FA")
        crop = ImageOps.fit(portrait, (590, 760), method=Image.Resampling.LANCZOS, centering=(0.5, 0.47))
        mask = Image.new("L", crop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 589, 759), radius=30, fill=255)
        plate.paste(crop, (160, 160), mask)
        draw = ImageDraw.Draw(plate)
        draw.text((870, 325), "SYNTHETIC PORTRAIT  /  MOTION STUDY", font=kicker_font, fill="#91A3B8")
        draw.rounded_rectangle((870, 718, 1330, 724), radius=3, fill=accent)
        draw.text((870, 784), "CHRONONTEMPLATE  ·  EDITORIAL ENTITY SERIES", font=label_font, fill="#718299")
        draw.text((870, 855), f"MOTION {index:02d}  /  15", font=label_font, fill=accent)
        plate.save(ASSET_ROOT / f"assets/canary/plate-{index:02d}.png", optimize=True)


def make_contact_sheet() -> Path:
    sheet = Image.new("RGB", (1940, ((len(MOTION_IDS) + 1) // 2) * 572 + 60), "#080D16")
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype(str(ASSET_ROOT / "assets/fonts/Inter-SemiBold.ttf"), 22)
    draw.text((28, 18), "CHRONONTEMPLATE  /  TRUMP ENTITY TEXT V1", font=label_font, fill="#F3F6FB")
    for index, motion_id in enumerate(MOTION_IDS):
        clip = OUTPUT / f"{motion_id}.mp4"
        frame = subprocess.run(["ffmpeg", "-v", "error", "-ss", "1.2", "-i", str(clip),
                                "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                               check=True, stdout=subprocess.PIPE).stdout
        image = Image.open(io.BytesIO(frame)).convert("RGB").resize((940, 528), Image.Resampling.LANCZOS)
        col, row = index % 2, index // 2
        x, y = 20 + col * 960, 54 + row * 572
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + 534), motion_id.replace("trump_entity_text_", "TRUMP TEXT ").replace("_", " ").upper(),
                  font=label_font, fill="#E7EDF6")
    path = OUTPUT / "entity_caption_premium_v2_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="render all fifteen MP4 previews with Chronon3D")
    parser.add_argument("--contact-only", action="store_true", help="build the contact sheet from existing MP4 renders")
    parser.add_argument("--cli", type=Path, default=CLI)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.contact_only:
        path = make_contact_sheet()
        print(f"CONTACT_SHEET {path} ({path.stat().st_size} bytes)")
        return 0
    prepare_assets()
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_id = {motion["id"]: motion for motion in catalog["motions"]}
    missing = [motion_id for motion_id in MOTION_IDS if motion_id not in by_id]
    if missing:
        raise SystemExit(f"ChrononTemplate catalog is missing entity caption motions: {missing}")
    plans = []
    for index, motion_id in enumerate(MOTION_IDS):
        plan = build_plan(by_id[motion_id], index)
        path = OUTPUT / f"{motion_id}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        plans.append((motion_id, path))
        print(f"PLAN_WRITTEN {path}")
    if not args.render:
        return 0
    for motion_id, path in plans:
        output = OUTPUT / f"{motion_id}.mp4"
        subprocess.run([str(args.cli), "render", "--plan", str(path),
                        "--assets-root", str(ASSET_ROOT), "--backend", "software",
                        "--profile", "preview", "--hardware", "none",
                        "--encoder-backend", "pipe",
                        "--output", str(OUTPUT / f"{motion_id}.base.mp4")], cwd=ROOT, check=True)
        base = OUTPUT / f"{motion_id}.base.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(base),
                        "-vf", "tpad=stop_mode=clone:stop_duration=3,trim=duration=5,fps=30,format=yuv420p",
                        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        str(output)], cwd=ROOT, check=True)
        if not output.is_file() or output.stat().st_size < 10_000:
            raise RuntimeError(f"missing or implausibly small render: {output}")
        base.unlink()
        print(f"RENDERED {output} ({output.stat().st_size} bytes)")
    print(f"CONTACT_SHEET {make_contact_sheet()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
