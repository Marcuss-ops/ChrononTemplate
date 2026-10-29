#!/usr/bin/env python3
"""Author the GPU parallax example RenderPlans from the CM3D camera sample seed."""

from __future__ import annotations

import copy
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = ROOT / "examples" / "gpu_food_parallax_v1" / "plans"
ASSET_DIR = ROOT / "assets" / "gpu_food_parallax_v1"
W, H, FPS, FRAMES = 1920, 1080, 30, 180
PORTRAIT_SOURCE = ROOT / "assets" / "images" / "truett_cathy_portrait_v5_photo_cutout.png"
PORTRAIT = ASSET_DIR / "truett_cathy_portrait_tight_v1.png"
PARTICLES = ASSET_DIR / "amber_dust_particles_v1.png"


def make_particle_plate() -> None:
    rng = random.Random(7319)
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    halo = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    draw_halo = ImageDraw.Draw(halo)
    draw_core = ImageDraw.Draw(plate)
    for _ in range(155):
        x = rng.randrange(18, W - 18)
        y = rng.randrange(18, H - 18)
        radius = rng.choices([1, 2, 3, 4], weights=[42, 38, 16, 4])[0]
        alpha = rng.randrange(35, 115)
        color = (255, rng.randrange(153, 207), rng.randrange(72, 130))
        draw_halo.ellipse((x - radius * 4, y - radius * 4,
                           x + radius * 4, y + radius * 4),
                          fill=(*color, max(5, alpha // 5)))
        draw_core.ellipse((x - radius, y - radius, x + radius, y + radius),
                          fill=(*color, alpha))
    halo = halo.filter(ImageFilter.GaussianBlur(8))
    plate.alpha_composite(halo)
    plate.save(PARTICLES)


def make_near_focus_assets(sandwich_path: Path, fries_path: Path) -> None:
    """Bake restrained optical softness onto near-foreground cutouts."""
    for source, target, radius in (
        (sandwich_path, ASSET_DIR / "near_sandwich_soft_v1.png", 7),
        (fries_path, ASSET_DIR / "near_fries_soft_v1.png", 6),
    ):
        image = Image.open(source).convert("RGBA")
        rgb = image.convert("RGB").filter(ImageFilter.GaussianBlur(radius))
        rgb.putalpha(image.getchannel("A").filter(ImageFilter.GaussianBlur(radius * 0.45)))
        rgb.save(target)


def image_layer(layer_id: str, asset: str, pos: tuple[float, float, float],
                size: tuple[float, float], tracks: list[dict] | None = None) -> dict:
    result = {
        "id": layer_id, "type": "image", "asset": asset,
        "position": list(pos), "size": list(size), "fit": "contain",
        "enable_3d": True, "start_frame": 0, "duration_frames": FRAMES,
    }
    if tracks:
        result["animation"] = {"tracks": tracks}
    return result


def float_tracks(y: float, phase: float = 0.0, swing: float = 34.0,
                 turn: float = 5.0) -> list[dict]:
    keys = []
    for frame in (0, 45, 90, 135, 179):
        a = math.tau * frame / (FRAMES - 1) + phase
        keys.append({"frame": frame, "value": round(y + swing * math.sin(a), 3)})
    rotation = []
    for frame in (0, 45, 90, 135, 179):
        a = math.tau * frame / (FRAMES - 1) + phase
        rotation.append({"frame": frame, "value": round(turn * math.sin(a), 3)})
    return [
        {"property": "position_y", "easing": "linear", "keyframes": keys},
        {"property": "rotation_z", "easing": "linear", "keyframes": rotation},
    ]


def push_tracks(start: float = 1.0, end: float = 1.06) -> list[dict]:
    keys = [{"frame": 0, "value": start}, {"frame": 179, "value": end}]
    return [
        {"property": "scale_x", "easing": "in_out_cubic", "keyframes": keys},
        {"property": "scale_y", "easing": "in_out_cubic", "keyframes": keys},
    ]


def text_layer(layer_id: str, text: str, y: float, z: float, *,
               font_size: int, color: str = "#FFF9F0", width: int = 1840,
               height: int = 260, font: str = "Poppins-Bold.ttf",
               align: str = "center", x: float = 0.0) -> dict:
    return {
        "id": layer_id, "type": "text", "text": text,
        "position": [x, y, z], "size": [width, height],
        "enable_3d": True, "start_frame": 0, "duration_frames": FRAMES,
        "style": {
            "font": f"Chronon3d/assets/fonts/{font}",
            "font_size": font_size, "min_font_size": max(16, font_size - 35),
            "max_font_size": font_size, "fit_mode": "shrink_only",
            "text_align": align, "fill": color,
        },
    }


def particle_layer(z: float, drift_x: float, drift_y: float) -> dict:
    tracks = [
        {"property": "position_x", "easing": "linear", "keyframes": [
            {"frame": 0, "value": -960}, {"frame": 179, "value": -960 + drift_x}]},
        {"property": "position_y", "easing": "linear", "keyframes": [
            {"frame": 0, "value": -540}, {"frame": 179, "value": -540 + drift_y}]},
    ]
    return image_layer("amber_dust", "ChrononTemplate/assets/gpu_food_parallax_v1/amber_dust_particles_v1.png",
                       (-960, -540, z), (2500, 1406), tracks)


def camera_path(seed_plan: dict, start: tuple[float, float, float],
                end: tuple[float, float, float], focus_z: float,
                dof: bool) -> tuple[list[dict], dict]:
    samples = copy.deepcopy(seed_plan["camera_samples"])
    last = FRAMES - 1
    for i, sample in enumerate(samples):
        frame = float(sample.get("frame", i))
        t = frame / last
        eased = t * t * (3.0 - 2.0 * t)
        camera = sample["camera"]
        # The CM3D seed carries its own animated rotations and position offsets.
        # Reusing those while authoring a new dolly made the hero leave frame.
        # Keep the camera target fixed, and use only a restrained forward move.
        camera["position"] = [
            round(start[0] + (end[0] - start[0]) * eased, 4),
            round(start[1] + (end[1] - start[1]) * eased, 4),
            round(start[2] + (end[2] - start[2]) * eased, 4),
        ]
        camera["rotation_deg"] = [0.0, 0.0, 0.0]
        camera["zoom"] = round(1.0 + 0.025 * eased, 5)
        camera["dof"] = {
            "enabled": dof,
            "focus_distance": round(abs(camera["position"][2] - focus_z), 4),
            "aperture": 0.016 if dof else 0.018,
            "max_blur": 26.0 if dof else 24.0,
            "iris_blades": 0,
            "highlight_gain": 0.0,
        }
    camera = copy.deepcopy(samples[0]["camera"])
    return samples, camera


def plan(seed: dict, *, job_id: str, background: str,
         camera_start: tuple[float, float, float], camera_end: tuple[float, float, float],
         layers: list[dict], focus_z: float = 0.0, dof: bool = False) -> dict:
    samples, camera = camera_path(seed, camera_start, camera_end, focus_z, dof)
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "camera": camera, "camera_samples": samples, "layers": layers,
        "output": {"path": job_id + ".mp4", "format": "mp4", "codec": "h264"},
    }


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    alpha = Image.open(PORTRAIT_SOURCE).convert("RGBA")
    alpha.crop(alpha.getchannel("A").getbbox()).save(PORTRAIT)
    make_particle_plate()

    seed_path = PLAN_DIR / "food_story_01_humble_beginnings.plan.json"
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    bg_night = "ChrononTemplate/assets/images/true_legacy_night_restaurant_v1.png"
    bg_legacy = "ChrononTemplate/assets/images/true_legacy_restaurant_background_v3_graded.png"
    portrait = "ChrononTemplate/assets/gpu_food_parallax_v1/truett_cathy_portrait_tight_v1.png"
    sandwich = "ChrononTemplate/assets/gpu_food_parallax_v1/crispy_chicken_sandwich_cutout_v1.png"
    fries = "ChrononTemplate/assets/gpu_food_parallax_v1/crinkle_fries_cutout_v1.png"
    near_sandwich = "ChrononTemplate/assets/gpu_food_parallax_v1/near_sandwich_soft_v1.png"
    near_fries = "ChrononTemplate/assets/gpu_food_parallax_v1/near_fries_soft_v1.png"
    make_near_focus_assets(ASSET_DIR / "crispy_chicken_sandwich_cutout_v1.png",
                           ASSET_DIR / "crinkle_fries_cutout_v1.png")
    def bg(asset: str) -> list[dict]:
        # Scale is applied after the image plane's native geometry; this
        # overscan keeps the projected backplate edge outside the frame.
        plate = image_layer("restaurant_backplate", asset, (-960, -540, 360), (3600, 2025))
        plate["scale"] = [2.0, 2.0, 1.0]
        return [plate]

    # 01 — centered founder portrait; the oversized name sits behind his silhouette.
    one = [
        *bg(bg_night),
        text_layer("chapter", "A STORY BUILT ON A SIMPLE IDEA", 425, 220,
                   font_size=38, color="#F5B45F", height=80, font="Inter-Bold.ttf"),
        text_layer("title_true", "TRUETT CATHY", 300, 175, font_size=310, width=1900, height=360),
        text_layer("title_origin", "HUMBLE BEGINNINGS", 70, 165, font_size=185,
                   color="#F7EEE3", width=1840, height=230),
        image_layer("founder_cutout", portrait, (-960, -540, 15), (1200, 1093), push_tracks()),
        image_layer("side_sandwich", sandwich, (-1510, -660, -150), (430, 286),
                    float_tracks(-660, 0.7, 24, 4.0)),
        image_layer("side_fries", fries, (-330, -390, -220), (365, 334),
                    float_tracks(-390, 2.2, 28, 4.5)),
        particle_layer(-500, 60, 30),
    ]

    # 02 — product tableau, with a centered two-line chapter title and food at
    # three camera depths; the near burger is deliberately allowed to clip frame.
    two = [
        *bg(bg_night),
        image_layer("far_sandwich_left", sandwich, (-1530, 110, 310), (560, 373),
                    float_tracks(110, 0.4, 42, 5.0)),
        image_layer("far_fries_right", fries, (-330, 120, 290), (500, 457),
                    float_tracks(120, 2.1, 48, 6.0)),
        text_layer("chapter", "CHAPTER 01", 200, 220, font_size=76,
                   color="#FF8E86", width=1700, height=100),
        text_layer("title_humble", "HUMBLE BEGINNINGS", -35, 180, font_size=250,
                   width=1900, height=330),
        image_layer("hero_sandwich", sandwich, (-960, -540, -40), (690, 460),
                    float_tracks(-540, 1.3, 46, 5.0) + push_tracks(1.0, 1.1)),
        image_layer("near_burger", near_sandwich, (-1630, -970, -420), (900, 600),
                    float_tracks(-970, 2.8, 34, 3.0)),
        image_layer("near_fries", near_fries, (-300, -710, -300), (620, 566),
                    float_tracks(-710, 4.5, 40, 4.0)),
        particle_layer(-650, 90, 58),
    ]

    # 03 — a different founder/product beat, with an oblique camera track and
    # the food passing in front of the centered headline.
    three = [
        *bg(bg_legacy),
        text_layer("chapter", "FROM ONE STORE", 415, 220, font_size=48,
                   color="#F5B45F", width=1600, height=90, font="Inter-Bold.ttf"),
        text_layer("title_national", "NATIONAL ICON", 280, 175, font_size=280,
                   width=1900, height=330),
        image_layer("founder_cutout", portrait, (-960, -540, 15), (1180, 1076), push_tracks(1.0, 1.055)),
        image_layer("hero_sandwich", sandwich, (-430, -570, -150), (640, 426),
                    float_tracks(-570, 2.4, 48, 5.0)),
        image_layer("fries_cutout", fries, (-1520, -300, -260), (475, 434),
                    float_tracks(-300, 5.0, 48, 5.0)),
        particle_layer(-560, -80, 45),
    ]

    specs = [
        ("food_story_01_humble_beginnings", one, (-960, -540, -1380), (-960, -540, -1360), 15, False),
        ("food_story_02_the_sandwich", two, (-960, -540, -1380), (-960, -540, -1360), -40, False),
        ("food_story_03_long_game", three, (-960, -540, -1380), (-960, -540, -1360), 15, False),
    ]
    manifest = {"schema": "chronontemplate.gpu-food-parallax.v2", "renderer": "Chronon3D Vulkan",
                "camera_authority": "Chronon3D perspective camera with authored dolly samples",
                "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
                "plans": []}
    for job_id, layers, start, end, focus_z, dof in specs:
        value = plan(seed, job_id=job_id, background=bg_night,
                     camera_start=start, camera_end=end, layers=layers,
                     focus_z=focus_z, dof=dof)
        path = PLAN_DIR / f"{job_id}.plan.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["plans"].append(path.name)
    (PLAN_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Authored 3 distinct scenes with {FRAMES} baked camera samples each")


if __name__ == "__main__":
    main()
