#!/usr/bin/env python3
"""Recreate ten Drive phrase references as editable, animated Chronon layers."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_entity_caption_reference_v3 as base

SOURCE = WORKSPACE / "RenderingGen/out/drive_style_refs_20261004"
OUT = ROOT / "out/phrase_style_drive_20261004"
ASSETS = OUT / "assets"
W, H, FPS, FRAMES = 1920, 1080, 30, 150
TEXT = "anche 3.000€ al mese non bastavano"
FONT = "PlayfairDisplay-Italic.ttf"
WHITE = "#F4F0E8"
INK = "#171615"
RED = (218, 28, 28)


def kf(prop: str, keys: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def phrase_brush(index: int, width: int, y: int, color: tuple[int, int, int], thickness: int) -> Path:
    """Draw one tapered, lightly ragged underline; Chronon animates its reveal."""
    path = ASSETS / "accents" / f"brush_{index:02}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx = W // 2
    x0, x1 = cx - width // 2, cx + width // 2
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    # A subtly irregular edge gives the stroke a hand-painted profile while
    # keeping its baseline directly tied to the phrase above it.
    half = max(2, thickness // 2)
    d.polygon([(x0, y + half // 2), (x0 + 36, y - half // 3), (cx - 80, y - half // 2),
               (x1 - 44, y - half // 4), (x1, y - half), (x1 - 28, y + half // 2),
               (cx + 70, y + half), (x0 + 32, y + half * 1.15)], fill=230)
    d.line((x0 + 25, y + half, cx, y + half // 2, x1 - 20, y + half // 2), fill=110, width=max(1, thickness // 4))
    # Smaller dry-brush streaks taper at the ends.
    d.line((x0 + 90, y + 13, cx - 30, y + 8, x1 - 110, y + 9), fill=95, width=max(1, thickness // 7))
    glow = mask.filter(ImageFilter.GaussianBlur(12))
    glow_color = Image.new("RGBA", (W, H), (*color, 0)); glow_color.putalpha(glow.point(lambda a: int(a * .52)))
    paint = Image.new("RGBA", (W, H), (*color, 0)); paint.putalpha(mask)
    canvas = Image.alpha_composite(glow_color, paint)
    if index == 9:
        canvas = canvas.rotate(3, resample=Image.Resampling.BICUBIC, center=(cx, y))
    canvas.save(path, optimize=True)
    return path


def cursor_asset() -> Path:
    path = ASSETS / "accents" / "cursor.png"
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((1790, 420, 1794, 555), radius=2, fill=(246, 243, 235, 235))
    im.save(path, optimize=True)
    return path


def text_layer(index: int, text: str, screen_y: int, size: int, fill: str,
               tracks: list[dict], *, box_height: int = H, glow: str | None = None) -> dict:
    # Chronon text positions use a bottom-up canvas origin; the helper's
    # screen_y parameter remains top-down for reference matching.
    layer = base.text_layer(
        f"phrase-title-{index:02}-{len(LAYERS)}", text,
        (W // 2, H - screen_y), (W, box_height), FONT, size, fill, tracks,
        start=0, glow=glow)
    return layer


def build(index: int) -> dict:
    plate = ASSETS / "plates" / f"{index:02}.png"
    title_anim = [
        [kf("position_y", [(0, 30), (34, 0)]), kf("opacity", [(0, 0), (18, 1)])],
        [kf("position_y", [(0, -20), (30, 0)]), kf("scale", [(0, .98), (35, 1)]), kf("opacity", [(0, 0), (14, 1)])],
        [kf("scale", [(0, .92), (34, 1)]), kf("opacity", [(0, 0), (15, 1)])],
        [kf("position_x", [(0, -45), (30, 0)]), kf("opacity", [(0, 0), (15, 1)])],
        [kf("position_y", [(0, 18), (34, 0)]), kf("opacity", [(0, 0), (12, 1)])],
        [kf("scale", [(0, .96), (34, 1)]), kf("opacity", [(0, 0), (16, 1)])],
        [kf("position_y", [(0, 24), (32, 0)]), kf("opacity", [(0, 0), (15, 1)])],
        [kf("position_x", [(0, 36), (30, 0)]), kf("opacity", [(0, 0), (14, 1)])],
        [kf("position_y", [(0, -26), (32, 0)]), kf("opacity", [(0, 0), (13, 1)])],
        [kf("scale", [(0, .90), (35, 1)]), kf("opacity", [(0, 0), (12, 1)])],
    ][index - 1]
    settings = {
        1: dict(y=492, size=86, color=WHITE, line_y=585, line_w=1460, thickness=10, line="brush"),
        2: dict(y=500, size=90, color=INK, line_y=600, line_w=1430, thickness=11, line="brush"),
        3: dict(y=528, size=84, color=WHITE, line_y=612, line_w=1420, thickness=13, line="brush"),
        4: dict(y=496, size=104, color=WHITE, line_y=588, line_w=1600, thickness=28, line="brush"),
        5: dict(y=533, size=0, color=WHITE, line_y=745, line_w=1370, thickness=48, line="brush"),
        6: dict(y=512, size=90, color=WHITE, line_y=600, line_w=1260, thickness=10, line="neon"),
        7: dict(y=500, size=96, color=INK, line_y=594, line_w=1500, thickness=8, line="rule"),
        8: dict(y=502, size=94, color=WHITE, line_y=594, line_w=1450, thickness=9, line="neon"),
        9: dict(y=490, size=108, color=WHITE, line_y=600, line_w=1650, thickness=76, line="brush"),
        10: dict(y=500, size=90, color=WHITE, line_y=592, line_w=1460, thickness=42, line="brush"),
    }[index]
    LAYERS.clear()
    LAYERS.append({"id": f"reference-plate-{index:02}", "type": "image",
        "asset": str(plate.relative_to(OUT)), "size": [W, H], "fit": "cover",
        "position": [0, 0], "start_frame": 0, "duration_frames": FRAMES,
        "animation": {"tracks": [kf("scale", [(0, 1.035), (FRAMES - 1, 1.0)], "in_out_sine")]}})

    if index == 5:
        # The fifth reference uses a two-line editorial hierarchy.
        LAYERS.append(text_layer(index, "3.000€ al mese", 450, 160, WHITE,
            [kf("scale", [(0, .90), (32, 1)]), kf("opacity", [(0, 0), (14, 1)])], glow="#F09A72"))
        LAYERS.append(text_layer(index, "non bastavano", 635, 130, WHITE,
            [kf("position_y", [(0, 22), (34, 0)]), kf("opacity", [(0, 0), (16, 1)])], glow="#F09A72"))
    else:
        size = settings["size"]
        if index == 3:
            title = TEXT
        else:
            title = TEXT
        LAYERS.append(text_layer(index, title, settings["y"], size, settings["color"],
            title_anim, glow="#F7E8D8" if settings["color"] == WHITE else None))

    line = phrase_brush(index, settings["line_w"], settings["line_y"], RED, settings["thickness"])
    if settings["line"] == "rule":
        # Reference 07 uses a cleaner, thinner red rule than the brush styles.
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((W//2-settings["line_w"]//2, settings["line_y"],
                             W//2+settings["line_w"]//2, settings["line_y"]+4), radius=2,
                            fill=(214, 35, 31, 240))
        line = ASSETS / "accents" / f"brush_{index:02}.png"; im.save(line, optimize=True)
    if settings["line"] == "neon":
        # A crisp center stroke inside a soft red halo echoes the illuminated
        # references while the same drawing reveal drives both.
        im = Image.open(line).convert("RGBA")
        mask = im.getchannel("A")
        center = Image.new("RGBA", im.size, (255, 28, 34, 0)); center.putalpha(mask.point(lambda a: min(255, int(a * 1.18))))
        glow = Image.new("RGBA", im.size, (244, 32, 37, 0)); glow.putalpha(mask.filter(ImageFilter.GaussianBlur(18)).point(lambda a: int(a * .60)))
        Image.alpha_composite(glow, center).save(line, optimize=True)
    LAYERS.append({"id": f"underline-{index:02}", "type": "image",
        "asset": str(line.relative_to(OUT)), "size": [W, H], "fit": "contain",
        "position": [0, 0], "start_frame": 0, "duration_frames": FRAMES,
        "animation": {"tracks": [kf("scale_x", [(0, .04), (38, 1)]),
                                  kf("opacity", [(0, 0), (15, 1)])]}})
    if index == 4:
        cursor = cursor_asset()
        LAYERS.append({"id": "typing-cursor", "type": "image",
            "asset": str(cursor.relative_to(OUT)), "size": [W, H], "fit": "contain",
            "position": [0, 0], "start_frame": 0, "duration_frames": FRAMES,
            "animation": {"tracks": [kf("opacity", [(0, 0), (22, 1), (38, 0), (54, 1),
                                                         (70, 0), (86, 1), (102, 0), (118, 1), (149, 0)], "linear")]}})
    return {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"phrase_drive_reference_{index:02}_native",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": list(LAYERS),
        "output": {"path": f"phrase_style_{index:02}_chronon.mp4", "format": "mp4", "codec": "h264"}}


LAYERS: list[dict] = []


def prepare_reference_assets() -> None:
    """Keep original references beside clean plates; repair three residuals."""
    references = ASSETS / "references"
    references.mkdir(parents=True, exist_ok=True)
    for index in range(1, 11):
        shutil.copy2(SOURCE / f"{index:02}.png", references / f"{index:02}.png")

    # Reference 02 is a clean paper background. Rebuild that paper texture
    # procedurally so no inpainted letter shadows or brush tips remain.
    width, height = Image.open(SOURCE / "02.png").size
    yy, xx = np.mgrid[0:height, 0:width]
    t = .58 * (xx / max(1, width - 1)) + .42 * (yy / max(1, height - 1))
    base_rgb = np.stack([247 - 5*t, 245 - 6*t, 239 - 7*t], axis=2)
    noise = np.random.default_rng(20261004).normal(0, 1.25, (height, width, 1))
    paper = np.clip(base_rgb + noise, 0, 255).astype(np.uint8)
    Image.fromarray(paper).save(ASSETS / "plates" / "02.png", optimize=True)

    # Reference 05 is a black/red cinematic glow; rebuilding its smooth light
    # field removes the source's baked typography while retaining that palette.
    dark = Image.new("RGBA", (width, height), (5, 6, 8, 255))
    for box, color, blur in [
        ((-300, -250, 660, 600), (112, 15, 20, 104), 150),
        ((940, 365, 1900, 1280), (120, 12, 17, 90), 185),
        ((-140, 710, 620, 1320), (103, 45, 22, 58), 165),
        ((1100, -180, 1900, 430), (55, 34, 29, 28), 210),
    ]:
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse(box, fill=color)
        dark = Image.alpha_composite(dark, glow.filter(ImageFilter.GaussianBlur(blur)))
    noise = np.random.default_rng(50).normal(0, 1.1, (height, width, 1))
    arr = np.asarray(dark.convert("RGB"), dtype=np.float32)
    Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8)).save(ASSETS / "plates" / "05.png", optimize=True)

    # The source for 09 has a broad dark title platform. Restore it as a clean,
    # softly blended plane while preserving the metallic floor and side glow.
    plate = Image.open(ASSETS / "plates" / "09.png").convert("RGB")
    w, h = plate.size
    panel = Image.new("RGB", (w, h), (9, 10, 12))
    pd = ImageDraw.Draw(panel)
    for x in range(w):
        v = x / max(1, w - 1)
        c = (int(16 - 7*v), int(17 - 7*v), int(19 - 7*v))
        pd.line((x, 270, x, 565), fill=c)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((0, 270, w, 565), fill=250)
    mask = mask.filter(ImageFilter.GaussianBlur(22))
    plate.paste(panel, (0, 0), mask)
    plate.save(ASSETS / "plates" / "09.png", optimize=True)

    # Remove the cursor baked into reference 04; the blinking cursor in the
    # Chronon plan is the only cursor in the finished animation.
    plate = Image.open(ASSETS / "plates" / "04.png").convert("RGB")
    w, h = plate.size
    cursor_patch = Image.new("RGB", (w, h), (7, 7, 9))
    cursor_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(cursor_mask).rectangle((1554, 345, 1585, 490), fill=250)
    cursor_mask = cursor_mask.filter(ImageFilter.GaussianBlur(7))
    plate.paste(cursor_patch, (0, 0), cursor_mask)
    plate.save(ASSETS / "plates" / "04.png", optimize=True)

    # Clear the last baked glyph at the far edge of 10 without touching the
    # ambient red light that frames the rest of the plate.
    plate = Image.open(ASSETS / "plates" / "10.png").convert("RGB")
    w, h = plate.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((1515, 325, w, 590), fill=245)
    mask = mask.filter(ImageFilter.GaussianBlur(24))
    patch = Image.new("RGB", (w, h), (6, 6, 8))
    plate.paste(patch, (0, 0), mask)
    plate.save(ASSETS / "plates" / "10.png", optimize=True)


def render(plan: dict, index: int) -> Path:
    output = OUT / "individual_mp4" / plan["output"]["path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / "plans" / f"phrase_style_{index:02}.plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    raw = OUT / f"phrase_style_{index:02}.nv12"
    log = OUT / "logs" / f"phrase_style_{index:02}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(base.CLI), "render", "--plan", str(plan_path), "--assets-root", str(OUT),
        "--backend", "vulkan", "--profile", "preview", "--fps", str(FPS),
        "--video-sink", "raw", "--pipe-pixfmt", "nv12", "--chunks", "1",
        "--fb-pool-budget-mb", "512", "--fb-pool-clear-policy", "trim-after-job",
        "--start-frame", "0", "--end-frame", str(FRAMES - 1), "-o", str(raw)]
    with log.open("w") as stream:
        subprocess.run(cmd, cwd=WORKSPACE, stdout=stream, stderr=subprocess.STDOUT, check=True)
    expected = FRAMES * W * H * 3 // 2
    if raw.stat().st_size != expected:
        raise RuntimeError(f"{plan_path.name}: raw frame size mismatch ({raw.stat().st_size}, expected {expected})")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "nv12",
        "-video_size", f"{W}x{H}", "-framerate", str(FPS), "-i", str(raw), "-frames:v", str(FRAMES),
        "-an", "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "18", "-b:v", "0",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-video_track_timescale", "30000", str(output)],
        cwd=WORKSPACE, check=True)
    raw.unlink()
    print(f"RENDERED {output}", flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, nargs="+")
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (ASSETS / "fonts").mkdir(parents=True, exist_ok=True)
    prepare_reference_assets()
    shutil.copy2(base.ASSET_ROOT / "assets/fonts" / FONT, ASSETS / "fonts" / FONT)
    indices = args.only or list(range(1, 11))
    manifest = []
    for index in indices:
        if not (SOURCE / f"{index:02}.png").is_file() or not (ASSETS / "plates" / f"{index:02}.png").is_file():
            raise FileNotFoundError(f"reference or clean plate missing for {index:02}")
        plan = build(index)
        plan_path = OUT / "plans" / f"phrase_style_{index:02}.plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        if not args.no_render:
            render(plan, index)
        manifest.append({"index": index, "reference": f"{index:02}.png",
            "plan": str(plan_path.relative_to(OUT)), "video": plan["output"]["path"],
            "width": W, "height": H, "fps": FPS, "duration_seconds": 5,
            "animated_layers": len(plan["layers"]) - 1})
    (OUT / "manifest.json").write_text(json.dumps({
        "schema": "chronontemplate.drive-phrase-style-recreations.v1",
        "source_folder": "1IKyEP-Yg95zpwCRbzJzP0nDWiWCOm8qZ",
        "note": "Typography and brush accents are native Chronon layers; image files supply only the cleaned visual plates.",
        "clips": manifest}, indent=2) + "\n")


if __name__ == "__main__":
    main()
