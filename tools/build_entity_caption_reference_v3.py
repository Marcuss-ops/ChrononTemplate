#!/usr/bin/env python3
"""Author and render ten Trump profile caption studies from the supplied references.

All type is native Chronon text; the generated portrait and paper/archival art
are image layers. Clips are rendered through Chronon3D's Vulkan path and NVENC.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
CLI = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
OUT = ROOT / "out/entity_caption_reference_v3"
ASSET_ROOT = OUT
PORTRAIT_SOURCE = Path("/home/pierone/.codex/generated_images/01a102bb-8739-71f1-9b4f-4a189d1661cb/exec-7ff09748-8944-4fcd-a13d-94b8657e535f.png")
W, H, FPS, FRAMES = 1920, 1080, 30, 150
PAPER = (235, 233, 223)
INK = (18, 19, 20)
WHITE = "#F5F3EC"
BLUE = "#5CA9F5"
RED = "#B23236"
MOTIONS = [
    ("archive_paper_wipe", "Archive Paper Wipe", "PlayfairDisplay-Italic.ttf", "#17181A", "#DFDCD3", "paper"),
    ("newsroom_profile_rise", "Newsroom Profile Rise", "DMSans-Bold.ttf", WHITE, "#C9C9C4", "newsroom"),
    ("halftone_card_settle", "Halftone Card Settle", "Montserrat-Bold.ttf", WHITE, BLUE, "card"),
    ("new_york_locator", "New York Locator", "Space-Grotesk.ttf", WHITE, "#C6D6C0", "map"),
    ("archival_split_reveal", "Archival Split Reveal", "Sora.ttf", WHITE, "#E0E2DB", "split"),
    ("typewriter_tracking_lock", "Typewriter Tracking Lock", "Instrument-Sans.ttf", WHITE, "#B6B4AD", "chalk"),
    ("front_page_tear_drop", "Front Page Tear Drop", "Bodoni72-BookItalic.ttf", "#151515", "#64615C", "frontpage"),
    ("ink_punch_focus", "Ink Punch Focus", "Outfit.ttf", WHITE, "#F1D4CF", "ink"),
    ("dossier_stack_glide", "Dossier Stack Glide", "Manrope.ttf", WHITE, "#B7B5AC", "dossier"),
    ("map_portrait_lock", "Map Portrait Lock", "Bricolage-Grotesque.ttf", WHITE, "#BDD3C3", "map_portrait"),
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ASSET_ROOT / "assets/fonts" / path), size)


def grayscale_photo() -> Image.Image:
    im = Image.open(PORTRAIT_SOURCE).convert("RGBA")
    # Keep the alpha cutout and make the editorial black-and-white tonality consistent.
    gray = ImageOps.grayscale(im.convert("RGB"))
    gray = ImageEnhance.Contrast(gray).enhance(1.23)
    return Image.merge("RGBA", (gray, gray.copy(), gray.copy(), im.getchannel("A")))


def grain(im: Image.Image, amount: int = 16, seed: int = 9) -> Image.Image:
    noise_bytes = np.random.default_rng(seed).integers(0, 256, (H, W), dtype=np.uint8).tobytes()
    noise = Image.frombytes("L", (W, H), noise_bytes)
    layer = Image.new("RGBA", (W, H), (205, 198, 180, 0))
    layer.putalpha(noise.point(lambda v: int(abs(v - 128) * amount / 128)))
    return Image.alpha_composite(im.convert("RGBA"), layer)


def dark_board(seed: int = 13, green: bool = False) -> Image.Image:
    base = Image.new("RGB", (W, H), (8, 10, 11) if not green else (6, 30, 19))
    d = ImageDraw.Draw(base, "RGBA")
    import random
    rng = random.Random(seed)
    for _ in range(130):
        x, y = rng.randrange(W), rng.randrange(H)
        c = (170, 175, 170, rng.randrange(5, 25)) if green else (190, 185, 174, rng.randrange(4, 18))
        d.line((x, y, x + rng.randrange(-100, 100), y + rng.randrange(-45, 45)), fill=c, width=rng.choice([1, 2, 3]))
    for x in range(0, W, 8):
        d.line((x, 0, x, H), fill=(220, 220, 220, 20), width=1)
    for y in range(0, H, 8):
        d.line((0, y, W, y), fill=(220, 220, 220, 18), width=1)
    base = base.filter(ImageFilter.GaussianBlur(0.35))
    return grain(base, 2, seed)


def cover_portrait(im: Image.Image, size: tuple[int, int], crop_x: float = 0.5) -> Image.Image:
    alpha = im.getchannel("A")
    bbox = alpha.getbbox()
    assert bbox
    cut = im.crop(bbox)
    cut = ImageOps.fit(cut, size, method=Image.Resampling.LANCZOS, centering=(crop_x, 0.32))
    return cut


def torn_strip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], seed: int) -> None:
    import random
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    top = [(x, y0 + rng.randrange(-7, 8)) for x in range(x0, x1 + 1, 24)]
    bot = [(x, y1 + rng.randrange(-8, 9)) for x in range(x1, x0 - 1, -24)]
    draw.polygon(top + bot, fill=fill)


def title_for(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font_obj, fill, anchor=None) -> None:
    draw.text(xy, text, font=font_obj, fill=fill, anchor=anchor, stroke_width=0)


def make_plate(kind: str, index: int, portrait: Image.Image) -> Path:
    pdir = ASSET_ROOT / "assets/plates"
    pdir.mkdir(parents=True, exist_ok=True)
    plate = pdir / f"plate-{index:02d}.jpg"
    # Keep the reference's editorial photo + name idea, with all decorative
    # plate copy removed so the person's name is the only text in the frame.
    palettes = [
        ((235, 233, 223), (32, 33, 34)), ((9, 12, 16), (218, 224, 230)),
        ((8, 8, 9), (92, 169, 245)), ((11, 20, 17), (192, 213, 193)),
        ((17, 18, 20), (224, 226, 219)), ((15, 15, 16), (182, 180, 173)),
        ((224, 222, 214), (32, 33, 34)), ((10, 10, 11), (241, 212, 207)),
        ((14, 15, 16), (183, 181, 172)), ((9, 24, 17), (189, 211, 195)),
    ]
    idx = index - 1
    bg, accent = palettes[idx]
    im = Image.new("RGBA", (W, H), (*bg, 255))
    d = ImageDraw.Draw(im, "RGBA")
    photo_left = idx % 2 == 0
    # Two centered portrait studies place the name directly beneath the photo.
    if idx in (2, 6):
        size = (660, 760)
        shot = cover_portrait(portrait, size, .5)
        im.alpha_composite(shot, ((W-size[0])//2, 74))
        d.rectangle((590, 865, 1330, 872), fill=(*accent, 225))
    else:
        photo_x = 108 if photo_left else 1152
        size = (660, 900)
        shot = cover_portrait(portrait, size, .5)
        im.alpha_composite(shot, (photo_x, 90))
        if idx in (0, 1):
            d.rectangle((photo_x + size[0] + (20 if photo_left else -30), 90,
                         photo_x + size[0] + (30 if photo_left else -20), 990), fill=(*accent, 255))
        elif idx in (4, 5):
            d.rounded_rectangle((photo_x-12, 78, photo_x+size[0]+12, 1002), radius=12,
                                outline=(*accent, 175), width=3)
        elif idx == 7:
            d.rectangle((photo_x + size[0] + (18 if photo_left else -28), 90,
                         photo_x + size[0] + (28 if photo_left else -18), 990), fill=(*accent, 240))
        elif idx == 8:
            d.rectangle((photo_x-18, 90, photo_x+size[0]+18, 990), outline=(*accent, 130), width=2)
        # restrained background texture and a small color cue, with no labels
        # or biographical copy baked into the image.
        if idx == 3:
            for y in range(90, 990, 42):
                d.line((photo_x + size[0] + 110 if photo_left else 120,
                        y, 960 if photo_left else photo_x-110, y), fill=(*accent, 24), width=1)
        elif idx == 9:
            d.ellipse((photo_x + size[0]//2-5, 528, photo_x + size[0]//2+5, 538), fill=(*accent, 220))
    if idx == 2:
        for x in range(0, W, 12):
            for y in range(0, H, 12):
                d.ellipse((x, y, x+1, y+1), fill=(170, 170, 170, 22))
    # Film grain and vignette bind the styles into one archival package.
    im = grain(im, 4, 90 + index)
    im.convert("RGB").save(plate, quality=93, subsampling=0, optimize=True)
    return plate


def kf(prop: str, keys: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing, "keyframes": [{"frame": f, "value": v} for f, v in keys]}


MOTION_TRACKS = [
    [kf("position_x", [(0, -170), (28, 0)]), kf("opacity", [(0, 0), (14, 1)])],
    [kf("position_y", [(0, 72), (34, 0)]), kf("scale", [(0, 1.07), (34, 1)]), kf("opacity", [(0, 0), (12, 1)])],
    [kf("scale", [(0, 0.84), (27, 1.035), (40, 1)], "out_back"), kf("opacity", [(0, 0), (14, 1)])],
    [kf("position_x", [(0, 54), (30, 0)]), kf("scale", [(0, 0.88), (30, 1)]), kf("opacity", [(0, 0), (12, 1)])],
    [kf("opacity", [(0, 0), (10, 1)])],
    [kf("position_y", [(0, 30), (22, -4), (34, 0)]), kf("opacity", [(0, 0), (9, 1)])],
    [kf("position_x", [(0, -290), (32, 0)]), kf("rotation_z", [(0, -2.4), (32, 0)]), kf("opacity", [(0, 0), (10, 1)])],
    [kf("scale", [(0, 1.14), (24, 0.99), (38, 1)], "in_out_cubic"), kf("opacity", [(0, 0.1), (10, 1)])],
    [kf("position_y", [(0, -55), (27, 4), (38, 0)]), kf("scale_x", [(0, 0.93), (38, 1)]), kf("opacity", [(0, 0), (10, 1)])],
    [kf("position_x", [(0, 90), (20, -5), (34, 0)]), kf("scale", [(0, 0.96), (34, 1)]), kf("opacity", [(0, 0), (9, 1)])],
]


def text_layer(layer_id: str, text: str, pos: tuple[int, int], size: tuple[int, int], fontname: str,
               pixels: int, fill: str, tracks: list[dict], start: int = 0, glow: str | None = None,
               text_animators: list[dict] | None = None) -> dict:
    style = {"font": f"assets/fonts/{fontname}", "font_size": pixels, "min_font_size": pixels,
             "max_font_size": pixels, "fit_mode": "shrink_only", "fill": fill}
    if glow:
        style["glow"] = {"radius": 5, "intensity": 0.16, "color": glow}
    layer = {"id": layer_id, "type": "text", "text": text, "size": list(size), "position": list(pos),
            "start_frame": 0, "duration_frames": FRAMES,
            "style": style, "animation": {"tracks": tracks}, "enable_3d": True}
    if text_animators:
        layer["text_animators"] = text_animators
    return layer


def build_plan(index: int) -> dict:
    motion_id, label, fontname, fill, secondary, kind = MOTIONS[index]
    plate = make_plate(kind, index + 1, grayscale_photo())
    screen_titles = [
        (1300, 500, 1000, 180), (620, 500, 1000, 145), (960, 930, 1000, 150),
        (620, 500, 1000, 160), (1300, 500, 1000, 150), (620, 500, 1000, 160),
        (960, 930, 1000, 170), (620, 500, 1000, 160), (1300, 500, 1000, 160),
        (620, 500, 1000, 160),
    ]
    title_sizes = [90, 90, 96, 94, 90, 88, 98, 92, 92, 90]
    x, screen_y, tw, th = screen_titles[index]
    y = H - screen_y
    # Headline fill is ink on torn newsprint, warm white on charcoal elsewhere.
    subfill = secondary
    title_animators = []
    tracking_ranges = [(32, 28), (27, 32), (22, 30), (14, 28), (27, 32), (20, 34), (12, 30), (16, 28), (19, 34), (14, 34)]
    initial_tracking, tracking_frames = tracking_ranges[index]
    if initial_tracking:
        title_animators.append({
            "id": f"caption_tracking_{index+1:02d}",
            "selectors": [{"id": f"caption_glyphs_{index+1:02d}", "unit": "glyph", "shape": "square",
                           "order": "forward", "combine": "replace", "exclude_spaces": True,
                           "start": {"keyframes": [{"frame": 0, "value": 0}], "easing": "linear"},
                           "end": {"keyframes": [{"frame": 0, "value": 100}], "easing": "linear"}}],
            "properties": [{"property": "tracking", "easing": "linear", "keyframes": [
                {"frame": 0, "value": initial_tracking}, {"frame": tracking_frames, "value": 0}]}],
        })
    plan = {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": f"entity_caption_{motion_id}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": [
            {"id": "documentary-plate", "type": "image", "asset": f"assets/plates/plate-{index+1:02d}.jpg",
             "size": [W, H], "fit": "cover", "position": [0, 0], "start_frame": 0,
             "duration_frames": FRAMES, "animation": {"tracks": [kf("scale", [(0, 1.035), (149, 1.0)], "in_out_sine")] }},
            text_layer("profile-name", "DONALD TRUMP", (x, y), (tw, th), fontname,
                       title_sizes[index], fill,
                       MOTION_TRACKS[index], glow=BLUE if index == 2 else None,
                       text_animators=title_animators),
        ],
        "output": {"path": f"entity_caption_{motion_id}.mp4", "format": "mp4", "codec": "h264"},
    }
    return plan


def build_gallery_plan() -> dict:
    layers: list[dict] = []
    for index in range(len(MOTIONS)):
        plan = build_plan(index)
        start = index * FRAMES
        for layer in plan["layers"]:
            layer["id"] = f"scene-{index+1:02d}-{layer['id']}"
            layer["start_frame"] = start
            layers.append(layer)
    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "entity_caption_reference_v3_gallery",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES * len(MOTIONS)},
        "layers": layers,
        "output": {"path": "entity_caption_reference_v3_gallery.mp4", "format": "mp4", "codec": "h264"},
    }


def prepare() -> list[tuple[str, Path]]:
    (ASSET_ROOT / "assets/fonts").mkdir(parents=True, exist_ok=True)
    (ASSET_ROOT / "assets/portraits").mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORTRAIT_SOURCE, ASSET_ROOT / "assets/portraits/donald-trump-editorial.png")
    used = {motion[2] for motion in MOTIONS} | {"Space-Grotesk.ttf"}
    for name in used:
        shutil.copy2(CHRONON / "assets/fonts" / name, ASSET_ROOT / "assets/fonts" / name)
    return []


def render(plan_path: Path, output: Path, cli: Path) -> None:
    raw = output.with_suffix(".nv12")
    cmd = [str(cli), "render", "--plan", str(plan_path), "--assets-root", str(ASSET_ROOT),
           "--backend", "vulkan", "--profile", "preview", "--fps", str(FPS),
           "--video-sink", "raw", "--pipe-pixfmt", "nv12", "--chunks", "1",
           "--fb-pool-budget-mb", "512", "--fb-pool-clear-policy", "trim-after-job",
           "--start-frame", "0", "--end-frame", str(FRAMES - 1), "-o", str(raw)]
    print("RENDER_VULKAN_NV12", output.name, flush=True)
    subprocess.run(cmd, cwd=WORKSPACE, check=True)
    expected_bytes = FRAMES * W * H * 3 // 2
    if raw.stat().st_size != expected_bytes:
        raise RuntimeError(f"unexpected Vulkan NV12 byte count in {raw}: {raw.stat().st_size}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "nv12",
                    "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", str(raw),
                    "-frames:v", str(FRAMES), "-vsync", "cfr", "-c:v", "h264_nvenc", "-preset", "p4",
                    "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-video_track_timescale", str(FPS * 1000), str(output)], cwd=WORKSPACE, check=True)
    raw.unlink()
    probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate,nb_frames,nb_read_frames:format=duration", "-of", "json", str(output)],
                           check=True, capture_output=True, text=True)
    data = json.loads(probe.stdout)
    stream = data["streams"][0]
    if (stream["width"], stream["height"], stream["r_frame_rate"]) != (W, H, "30/1"):
        raise RuntimeError(f"unexpected video stream properties in {output}: {stream}")
    if int(stream.get("nb_read_frames", 0)) != FRAMES or abs(float(data["format"]["duration"]) - 5) > 0.02:
        raise RuntimeError(f"unexpected duration/frame count in {output}: {data}")
    print("VERIFIED", output.name, stream["width"], stream["height"], stream["r_frame_rate"], data["format"]["duration"], flush=True)


def contact_sheet() -> Path:
    sheet = Image.new("RGB", (1940, 5 * 572 + 75), (8, 9, 10))
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(str(ASSET_ROOT / "assets/fonts/Space-Grotesk.ttf"), 22)
    draw.text((28, 18), "DONALD TRUMP · 10 VARIANTI MODERNE", font=title_font, fill=(238, 235, 224))
    for i, (motion_id, label, *_rest) in enumerate(MOTIONS):
        clip = OUT / f"entity_caption_{motion_id}.mp4"
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "2.0", "-i", str(clip), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], check=True, stdout=subprocess.PIPE).stdout
        frame = Image.open(io.BytesIO(raw)).convert("RGB").resize((940, 528), Image.Resampling.LANCZOS)
        col, row = i % 2, i // 2
        x, y = 20 + col * 960, 58 + row * 572
        sheet.paste(frame, (x, y))
        draw.text((x + 8, y + 534), label.upper(), font=title_font, fill=(225, 223, 216))
    path = OUT / "entity_caption_reference_v3_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--contact-only", action="store_true")
    parser.add_argument("--motion", action="append", choices=[item[0] for item in MOTIONS],
                        help="render only selected motion id(s), may be repeated")
    parser.add_argument("--cli", type=Path, default=CLI)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.contact_only:
        print("CONTACT_SHEET", contact_sheet())
        return 0
    prepare()
    plans: list[tuple[str, Path]] = []
    for i, motion in enumerate(MOTIONS):
        plan = build_plan(i)
        path = OUT / f"entity_caption_{motion[0]}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        plans.append((motion[0], path))
        print("PLAN_WRITTEN", path.name)
    if not args.render:
        return 0
    selected = set(args.motion or [])
    for motion_id, path in plans:
        if selected and motion_id not in selected:
            continue
        render(path, OUT / f"entity_caption_{motion_id}.mp4", args.cli)
    if not selected:
        print("CONTACT_SHEET", contact_sheet())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
