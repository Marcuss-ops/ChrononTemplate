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
    im = dark_board(30 + index, green=kind in {"map", "map_portrait"}).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    # The portrait remains image content, while all captions stay as editable Chronon text.
    if kind == "paper":
        shot = cover_portrait(portrait, (830, H), .48)
        im.alpha_composite(shot, (0, 0))
        d.rectangle((830, 0, 842, H), fill=(226, 223, 213, 255))
        torn_strip(d, (838, 394, 1919, 672), PAPER, 104)
        title_for(d, "U.S. PRESIDENT / PROFILE", (920, 274), font("Space-Grotesk.ttf", 28), (225, 223, 214, 230))
        title_for(d, "THE AMERICAN PROFILE", (980, 713), font("Space-Grotesk.ttf", 24), (188, 186, 177, 235))
    elif kind == "newsroom":
        # Layered paper desks and soft monochrome newsroom silhouettes evoke a wire-service still.
        d.rectangle((0, 0, W, H), fill=(12, 12, 12, 215))
        for y in (90, 250, 410, 555):
            d.rectangle((90, y, 1820, y + 92), fill=(38, 38, 36, 255), outline=(78, 77, 72, 255), width=2)
            for x in range(130, 1750, 135):
                d.line((x, y + 28, x + 90, y + 28), fill=(95, 92, 85, 255), width=3)
        shot = cover_portrait(portrait, (430, 560), .52)
        im.alpha_composite(shot, (745, 75))
        d.rounded_rectangle((735, 65, 1185, 645), radius=9, outline=(245, 243, 230, 185), width=4)
        title_for(d, "THE PUBLIC RECORD", (960, 32), font("Space-Grotesk.ttf", 22), (220, 217, 207, 245), "mm")
        d.line((500, 812, 1420, 812), fill=(235, 232, 222, 145), width=2)
    elif kind == "card":
        d.rectangle((0, 0, W, H), fill=(6, 6, 7, 255))
        for x in range(12, W, 8):
            for y in range(12, H, 8):
                d.ellipse((x, y, x + 1, y + 1), fill=(170, 170, 170, 32))
        d.rounded_rectangle((104, 71, 780, 1010), radius=40, fill=(211, 210, 201, 255))
        shot = cover_portrait(portrait, (650, 920), .52)
        im.alpha_composite(shot, (117, 80))
        d.line((925, 518, 1665, 518), fill=(85, 163, 241, 250), width=10)
        title_for(d, "PROFILE / 01", (930, 290), font("Space-Grotesk.ttf", 25), (187, 187, 179, 240))
        title_for(d, "UNITED STATES", (930, 600), font("Space-Grotesk.ttf", 26), (196, 196, 188, 230))
    elif kind in {"map", "map_portrait"}:
        # A restrained locator map with New York called out (Trump's birthplace); no invented case marker.
        d.rectangle((0, 0, W, H), fill=(7, 31, 20, 255))
        for x in range(0, W, 80):
            d.line((x, 0, x, H), fill=(164, 191, 161, 22), width=1)
        for y in range(0, H, 80):
            d.line((0, y, W, y), fill=(164, 191, 161, 22), width=1)
        usa = [(174,330),(285,245),(418,265),(510,223),(676,263),(782,300),(900,265),(1000,330),(1112,330),(1226,280),(1370,325),(1484,356),(1585,380),(1675,438),(1610,532),(1534,562),(1462,640),(1380,670),(1270,732),(1150,722),(1075,644),(950,602),(857,555),(770,610),(690,580),(610,620),(518,543),(420,525),(340,466),(250,465)]
        d.polygon(usa, fill=(32, 62, 40, 255), outline=(151, 178, 144, 180))
        for i in range(3):
            d.line([(235+i*24, 377+i*13),(460+i*12, 326+i*20),(718,343+i*8),(1010,384+i*5),(1320,421+i*9),(1550-i*25,472+i*8)], fill=(180, 202, 161, 35), width=2)
        d.ellipse((1470, 366, 1500, 396), fill=(220, 75, 66, 230))
        d.ellipse((1458, 354, 1512, 408), outline=(230, 112, 92, 150), width=3)
        d.line((1490, 382, 1590, 290), fill=(221, 219, 207, 200), width=2)
        title_for(d, "QUEENS, NEW YORK", (1600, 266), font("Space-Grotesk.ttf", 22), (230, 228, 217, 240))
        if kind == "map_portrait":
            shot = cover_portrait(portrait, (350, 460), .52)
            im.alpha_composite(shot, (1220, 568))
            d.rectangle((1205, 553, 1580, 1040), outline=(232, 231, 219, 160), width=3)
    elif kind == "split":
        d.rectangle((0, 0, 959, H), fill=(7, 8, 9, 255))
        d.rectangle((960, 0, W, H), fill=(7, 39, 24, 255))
        shot_a = cover_portrait(portrait, (725, 550), .45)
        shot_b = cover_portrait(portrait, (725, 550), .66).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        im.alpha_composite(shot_a, (115, 115))
        im.alpha_composite(shot_b, (1080, 115))
        title_for(d, "ARCHIVE / A", (478, 62), font("Space-Grotesk.ttf", 24), (241, 238, 226, 250), "mm")
        title_for(d, "ARCHIVE / B", (1435, 62), font("Space-Grotesk.ttf", 24), (241, 238, 226, 250), "mm")
        d.line((960, 0, 960, H), fill=(232, 231, 223, 70), width=2)
    elif kind == "chalk":
        shot = cover_portrait(portrait, (900, H), .51)
        im.alpha_composite(shot, (0, 0))
        for i in range(6):
            y = 198 + i * 118
            d.line((980, y, 1770, y), fill=(201, 198, 185, 24 + i * 3), width=2)
        title_for(d, "CASE NOTES / PROFILE", (1010, 249), font("Space-Grotesk.ttf", 25), (202, 200, 189, 245))
    elif kind == "frontpage":
        im = Image.new("RGBA", (W, H), (202, 199, 188, 255))
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 0, W, 120), fill=(20, 21, 22, 255))
        for x in range(60, W - 40, 44):
            d.line((x, 180, x, 1025), fill=(33, 32, 29, 24), width=1)
        shot = cover_portrait(portrait, (670, 840), .5)
        im.alpha_composite(shot, (1140, 166))
        torn_strip(d, (0, 590, 1920, 865), PAPER, 241)
        title_for(d, "THE AMERICAN PROFILE", (85, 132), font("Space-Grotesk.ttf", 28), (229, 226, 216, 235))
        title_for(d, "PERSONALITY / PUBLIC RECORD", (105, 920), font("Space-Grotesk.ttf", 23), (55, 53, 50, 220))
    elif kind == "ink":
        d.rectangle((0, 0, W, H), fill=(9, 9, 10, 255))
        shot = cover_portrait(portrait, (980, H), .5)
        # A low-strength red/cyan offset keeps the reference's analog registration fringe restrained.
        warm = shot.copy(); warm.putalpha(warm.getchannel("A").point(lambda v: v * 35 // 255))
        im.alpha_composite(warm, (-12, 0)); im.alpha_composite(shot, (0, 0))
        d.rectangle((0, 0, 960, H), fill=(0, 0, 0, 42))
        d.rectangle((970, 0, 980, H), fill=(173, 55, 60, 255))
        for x in range(1040, W, 12):
            d.line((x, 0, x, H), fill=(230, 230, 220, 10), width=1)
    elif kind == "dossier":
        d.rectangle((0, 0, W, H), fill=(13, 14, 15, 255))
        d.rounded_rectangle((115, 126, 1145, 953), radius=8, fill=(190, 187, 176, 24), outline=(226, 223, 211, 90), width=2)
        d.rounded_rectangle((145, 156, 1175, 983), radius=8, fill=(226, 224, 215, 255))
        shot = cover_portrait(portrait, (1000, 810), .5)
        im.alpha_composite(shot, (160, 164))
        d.rectangle((1240, 140, 1248, 900), fill=(175, 54, 59, 235))
        title_for(d, "BIOGRAPHICAL FILE", (1285, 198), font("Space-Grotesk.ttf", 24), (190, 188, 179, 240))
        title_for(d, "45 / 47", (1285, 827), font("Space-Grotesk.ttf", 74), (233, 230, 218, 245))
    else:
        raise ValueError(kind)
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
        (1374, 526, 1080, 180), (960, 760, 1390, 145), (1375, 496, 1030, 150),
        (760, 720, 1060, 160), (960, 780, 1500, 120), (1390, 554, 1030, 180),
        (930, 715, 1760, 200), (1425, 532, 880, 180), (1510, 544, 830, 150),
        (730, 787, 950, 156),
    ]
    title_sizes = [104, 118, 110, 112, 104, 92, 122, 110, 108, 110]
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
            text_layer("profile-role", "45TH & 47TH U.S. PRESIDENT", (x, y - 160),
                       (tw, 60), "Space-Grotesk.ttf", 27, subfill,
                       [kf("opacity", [(0, 0), (16 + index % 5, 1)])]),
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
    draw.text((28, 18), "CHRONONTEMPLATE / DONALD TRUMP PROFILE — ARCHIVAL MOTION STUDIES", font=title_font, fill=(238, 235, 224))
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
