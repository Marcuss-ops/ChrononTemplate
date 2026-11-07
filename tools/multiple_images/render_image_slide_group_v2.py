#!/usr/bin/env python3
"""Count-independent, camera-soft image-group transitions for ChrononTemplate."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
CHRONON = ROOT.parent / "Chronon3d"
CLI = CHRONON / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
OUT = ROOT / "out/image_slide_group_v2"
ASSET_DIR = OUT / "assets"
W, H, FPS, FRAMES = 1920, 1080, 30, 210
DEFAULT_IMAGES = [
    ("assets/famous_people_trio_v1/john_glenn.png", "John Glenn"),
    ("assets/famous_people_trio_v1/neil_armstrong.png", "Neil Armstrong"),
    ("assets/famous_people_trio_v1/sally_ride.png", "Sally Ride"),
]

# The selected transition is identical for every group size. Only the time
# slot is derived from the number of supplied images.
MOVES = {
    "slide_right": ("position_x", -54.0, 36.0),
    "slide_left": ("position_x", 54.0, -36.0),
    "slide_in": ("scale", 0.985, 0.992),
    "slide_down": ("position_y", -48.0, 26.0),
    "slide_up": ("position_y", 48.0, -26.0),
}
MOVE_LABELS = {
    "slide_right": "SLIDE DA DESTRA",
    "slide_left": "SLIDE DA SINISTRA",
    "slide_in": "ZOOM IN MORBIDO",
    "slide_down": "SLIDE DALL’ALTO",
    "slide_up": "SLIDE DAL BASSO",
}


def _track(prop, keys, easing="in_out_sine"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": int(f), "value": v} for f, v in keys]}


def _make_background(path: Path) -> None:
    """A full-frame midnight gradient with restrained blue/violet light."""
    top = (8, 15, 29)
    bottom = (18, 31, 50)
    gradient = Image.new("RGB", (W, H))
    pixels = gradient.load()
    for y in range(H):
        t = y / max(1, H - 1)
        row = tuple(round(top[c] * (1 - t) + bottom[c] * t) for c in range(3))
        for x in range(W):
            pixels[x, y] = row

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse((-320, -440, 850, 600), fill=(37, 105, 145, 55))
    draw.ellipse((1260, -360, 2210, 470), fill=(78, 67, 152, 38))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    gradient = Image.alpha_composite(gradient.convert("RGBA"), glow)
    gradient.convert("RGB").save(path, quality=95)


def _make_card(source_path: Path, output_path: Path) -> None:
    """Bake the matte, rounded photo mask and shadow into one clean asset."""
    outer_w, outer_h = 720, 820
    photo_w, photo_h = 672, 772
    inset = 24
    card = Image.new("RGBA", (outer_w, outer_h), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (outer_w, outer_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((inset, inset + 12, inset + photo_w, inset + 12 + photo_h),
                                  radius=28, fill=(0, 0, 0, 138))
    card = Image.alpha_composite(card, shadow.filter(ImageFilter.GaussianBlur(18)))

    matte = Image.new("RGBA", (outer_w, outer_h), (0, 0, 0, 0))
    matte_draw = ImageDraw.Draw(matte)
    matte_draw.rounded_rectangle((inset, inset, inset + photo_w, inset + photo_h),
                                 radius=28, fill=(194, 211, 229, 255),
                                 outline=(232, 243, 255, 255), width=2)
    card = Image.alpha_composite(card, matte)

    source = Image.open(source_path).convert("RGB")
    lanczos = getattr(Image, "Resampling", Image).LANCZOS
    photo = ImageOps.fit(source, (photo_w - 20, photo_h - 20),
                         method=lanczos, centering=(0.5, 0.4))
    mask = Image.new("L", photo.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, photo.width - 1, photo.height - 1),
                                          radius=20, fill=255)
    photo_rgba = photo.convert("RGBA")
    photo_rgba.putalpha(mask)
    card.alpha_composite(photo_rgba, (inset + 10, inset + 10))
    card.save(output_path)


def _parse_images(values):
    if not values:
        return DEFAULT_IMAGES
    result = []
    for value in values:
        asset, separator, caption = value.partition("=")
        path = Path(asset)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise ValueError(f"image asset does not exist: {path}")
        result.append((str(path), caption.strip() if separator else path.stem.replace("_", " ").title()))
    if not 2 <= len(result) <= 5:
        raise ValueError("the current group renderer accepts 2 to 5 image layers")
    return result


def make_plan(move: str, images):
    property_name, enter_value, exit_value = MOVES[move]
    count = len(images)
    slot = FRAMES / count
    enter_frames = max(18, min(24, round(slot * 0.28)))
    exit_frames = max(14, min(20, round(slot * 0.22)))
    overlap = min(12, max(8, round(slot * 0.14)))
    plan = {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": f"image_group_{move}_v2",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "output": {"path": f"image_group_{move}_v2.mp4", "format": "mp4", "codec": "h264"},
        "layers": [{"id": "modern_gradient_background", "type": "image",
                    "asset": "out/image_slide_group_v2/assets/background.png",
                    "size": [W, H], "position": [0, 0], "fit": "cover",
                    "screen_space": True, "start_frame": 0, "duration_frames": FRAMES}],
    }

    plan["layers"].extend([
        {"id": "series_kicker", "type": "text", "text": "CAMERA  /  IMAGE GROUP",
         "size": [1000, 32], "position": [960, 64], "start_frame": 0,
         "duration_frames": FRAMES,
         "style": {"font": "assets/fonts/Inter-SemiBold.ttf", "font_size": 18,
                   "min_font_size": 18, "max_font_size": 18,
                   "fit_mode": "shrink_only", "fill": "#9CCBE2"}},
        {"id": "transition_label", "type": "text", "text": MOVE_LABELS[move],
         "size": [1200, 54], "position": [960, 116], "start_frame": 0,
         "duration_frames": FRAMES,
         "style": {"font": "assets/fonts/Inter-SemiBold.ttf", "font_size": 31,
                   "min_font_size": 31, "max_font_size": 31,
                   "fit_mode": "shrink_only", "fill": "#F3F7FC"}},
    ])

    for index, (source, caption) in enumerate(images):
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        if not source_path.is_file():
            raise ValueError(f"image asset does not exist: {source_path}")
        card_path = ASSET_DIR / f"image_{index + 1}.png"
        _make_card(source_path, card_path)

        start = round(index * slot)
        next_start = round((index + 1) * slot)
        exit_start = max(start + enter_frames + 4, next_start - exit_frames + overlap)
        exit_end = min(FRAMES - 1, next_start + overlap)
        if index == count - 1:
            exit_start = max(start + enter_frames + 8, FRAMES - exit_frames)
            exit_end = FRAMES - 1
        enter_end = min(start + enter_frames, exit_start - 2)

        if property_name == "scale":
            motion_tracks = [
                _track("position_y", [(start, 14), (enter_end, 0),
                                      (exit_start, 0), (exit_end, -10)]),
                _track("scale", [(start, enter_value), (enter_end, 1.0),
                                 (exit_start, 1.0), (exit_end, exit_value)]),
            ]
        else:
            motion_tracks = [
                _track(property_name, [(start, enter_value), (enter_end, 0),
                                       (exit_start, 0), (exit_end, exit_value)]),
                _track("scale", [(start, 0.99), (enter_end, 1.0),
                                 (exit_start, 1.0), (exit_end, 0.995)]),
            ]
        motion_tracks.append(_track("opacity", [(start, 0.0), (enter_end, 1.0),
                                                 (exit_start, 1.0), (exit_end, 0.0)]))
        plan["layers"].append({
            "id": f"image_{index + 1}", "type": "image",
            "asset": f"out/image_slide_group_v2/assets/{card_path.name}",
            "size": [720, 820], "position": [0, 0], "fit": "contain",
            "radius": 0, "enable_3d": True, "start_frame": 0,
            "duration_frames": FRAMES, "animation": {"tracks": motion_tracks},
        })
        plan["layers"].append({
            "id": f"caption_{index + 1}", "type": "text", "text": caption,
            "size": [1200, 54], "position": [960, 1000],
            "start_frame": 0, "duration_frames": FRAMES,
            "style": {"font": "assets/fonts/Inter-SemiBold.ttf", "font_size": 31,
                      "min_font_size": 31, "max_font_size": 31,
                      "fit_mode": "shrink_only", "fill": "#E5EDF6"},
            "animation": {"tracks": [_track("opacity", [(start, 0.0), (enter_end, 1.0),
                                                          (exit_start, 1.0), (exit_end, 0.0)])]},
        })
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", action="append", default=[], metavar="PATH[=CAPTION]",
                        help="image layer (repeat 2..5 times); each uses the same selected transition")
    args = parser.parse_args()
    images = _parse_images(args.image)
    OUT.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    _make_background(ASSET_DIR / "background.png")
    if not CLI.is_file():
        raise SystemExit(f"Chronon3D renderer not found: {CLI}")

    results = []
    for move in MOVES:
        plan = make_plan(move, images)
        name = plan["job_id"]
        plan_path = OUT / f"{name}.plan.json"
        video_path = OUT / f"{name}.mp4"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        subprocess.run([str(CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ROOT)],
                       check=True, cwd=ROOT)
        subprocess.run([str(CLI), "render", "--plan", str(plan_path), "--output", str(video_path),
                        "--assets-root", str(ROOT), "--backend", "vulkan", "--profile", "preview",
                        "--hardware", "nvenc", "--fps", str(FPS)], check=True, cwd=ROOT)
        results.append({"id": name, "move": move, "video": video_path.name,
                        "image_count": len(images), "renderer": "vulkan", "encoder": "nvenc"})
    (OUT / "manifest.json").write_text(json.dumps({"canvas": [W, H], "fps": FPS,
                            "duration_frames": FRAMES, "image_count": len(images),
                            "shared_transition_independent_of_image_count": True,
                            "renders": results}, indent=2) + "\n")
    print(f"Rendered {len(results)} reusable transitions with {len(images)} images to {OUT}")


if __name__ == "__main__":
    main()
