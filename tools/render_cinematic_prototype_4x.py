#!/usr/bin/env python3
"""Chronon Cinematic Backgrounds - 4 Canonical Prototype Suite (V2 Architecture Refined).

Implements the 4 foundational prototypes solving the core visual feedback:
  - 03: Molten Organic Blob (Oversized bright plate + subtractive warped dark occluder)
  - 06: GlowPath / Bezier Ribbon (Real curved luminous ribbon with razor hot core & chromatic fringe)
  - 11: Dense Starburst / Radial Burst (32 dense anisotropic rays + sweeping rotation)
  - 18: Dark Aperture / Hourglass Diamond (Giant backlight plate MINUS 4 organic dark masks)

Core Architectural Principles:
  1. Subtractive Occlusion: Bright Floodlight MINUS Dark Organic Masks
  2. Oversized Cropped Geometry: 1.8x canvas dimension (3456x1944) eliminating all rotation borders
  3. Organic Coordinate Warping: Multi-octave low-frequency displacement
  4. White-Hot Core: #FFFCE0 specular highlights -> yellow -> orange -> deep red
  5. 3-Tier Motion: Macro translation (wide traverse) + Meso geometry morph (scale/stretch) + Micro evolution
  6. Analog Finishing: Dual-stage film grain and chromatic aberration
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_prototypes_4x"
PLATES_DIR = OUT_DIR / "assets"
DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = BASE_DIR / "refactored/credentials.json"
TOKEN_FILE = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
FRAMES = 120  # 4.0 seconds

# Oversized plate canvas dimensions (1.8x canvas - ensures no black borders during 3D rotation)
PW = int(WIDTH * 1.8)   # 3456
PH = int(HEIGHT * 1.8)  # 1944

# Authentic Analog Palette
PAL_WHITE_HOT = (255, 252, 224, 255)  # #FFFCE0
PAL_HOT_YELLOW = (255, 240, 90, 255)  # #FFF05A
PAL_GOLD_YELLOW = (255, 212, 0, 255)  # #FFD400
PAL_AMBER = (255, 117, 0, 255)        # #FF7500
PAL_RED_ORANGE = (255, 37, 0, 255)    # #FF2500
PAL_DEEP_RED = (110, 14, 4, 255)      # #6E0E04
PAL_DARK_BROWN = (35, 7, 3, 255)      # #230703
PAL_BLACK = (4, 2, 2, 255)            # #040202


# ==============================================================================
# Procedural Warping and Noise Utilities
# ==============================================================================

def apply_warp(image: Image.Image, freq: float = 0.006, amp: float = 55.0, seed: int = 1) -> Image.Image:
    """Apply low-frequency organic coordinate displacement to an image."""
    w, h = image.size
    arr = np.array(image)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    
    # 2 octaves of smooth trigonometric noise
    rng = np.random.default_rng(seed)
    p1, p2, p3, p4 = rng.uniform(0, 2 * math.pi, 4)
    nx = np.sin(x * freq + p1) * np.cos(y * freq * 0.8 + p2) + 0.5 * np.sin((x + y) * freq * 1.8 + p3)
    ny = np.cos(x * freq * 0.9 + p3) * np.sin(y * freq + p4) + 0.5 * np.cos((x - y) * freq * 1.6 + p1)
    
    wx = np.clip(x + nx * amp, 0, w - 1).astype(np.float32)
    wy = np.clip(y + ny * amp, 0, h - 1).astype(np.float32)
    
    try:
        from scipy.ndimage import map_coordinates
        if arr.ndim == 3:
            warped = np.zeros_like(arr)
            for c in range(arr.shape[2]):
                warped[..., c] = map_coordinates(arr[..., c], [wy, wx], order=1, mode='nearest')
            return Image.fromarray(warped)
    except ImportError:
        pass
    
    return image


def add_chromatic_aberration(image: Image.Image, offset: int = 5) -> Image.Image:
    """Add subtle analog chromatic fringe (red shift / cyan shift)."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    r, g, b, a = image.split()
    r_shifted = ImageChops.offset(r, offset, 0)
    b_shifted = ImageChops.offset(b, -offset, 0)
    return Image.merge("RGBA", (r_shifted, g, b_shifted, a))


# ==============================================================================
# Prototype 1: 03 - Molten Organic Blob
# ==============================================================================

def build_assets_03() -> tuple[Path, Path]:
    """03: Oversized molten bright plate + subtractive organic warped occluder."""
    # 1. Bright Floodlight Plate (Oversized: 3456x1944)
    plate = Image.new("RGBA", (PW, PH), PAL_BLACK)
    d = ImageDraw.Draw(plate, "RGBA")
    cx, cy = PW // 2, PH // 2
    
    # Blazing hot multi-tier optical radiant core
    radii = [
        (320, PAL_WHITE_HOT),
        (560, PAL_HOT_YELLOW),
        (880, PAL_GOLD_YELLOW),
        (1300, PAL_AMBER),
        (1750, PAL_RED_ORANGE),
        (2200, PAL_DEEP_RED),
        (2600, PAL_DARK_BROWN)
    ]
    for r, col in reversed(radii):
        d.ellipse((cx - r, cy - int(r * 0.75), cx + r, cy + int(r * 0.75)), fill=col)
    plate = plate.filter(ImageFilter.GaussianBlur(68.0))
    plate = apply_warp(plate, freq=0.0035, amp=70.0, seed=3)
    plate_path = PLATES_DIR / "proto_03_bright_plate.png"
    plate.save(plate_path, optimize=True)

    # 2. Subtractive Dark Occluder Mask (Large organic warped island)
    mask = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    md = ImageDraw.Draw(mask, "RGBA")
    # Draw dark irregular blob in center
    md.ellipse((cx - 650, cy - 500, cx + 650, cy + 500), fill=(4, 2, 2, 255))
    md.ellipse((cx - 450, cy - 300, cx + 780, cy + 380), fill=(4, 2, 2, 255))
    md.ellipse((cx - 200, cy - 600, cx + 500, cy + 200), fill=(4, 2, 2, 255))
    mask = mask.filter(ImageFilter.GaussianBlur(48.0))
    mask = apply_warp(mask, freq=0.005, amp=85.0, seed=7)
    mask_path = PLATES_DIR / "proto_03_dark_occluder.png"
    mask.save(mask_path, optimize=True)

    return plate_path, mask_path


def make_plan_03() -> Dict[str, Any]:
    """Chronon Plan for 03: Bright Plate + Counter-Drifting Warped Dark Occluder."""
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "cinematic_proto_03_molten_blob",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "output": {"path": str(OUT_DIR / "cinematic_proto_03.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "bright_molten_plate",
                "type": "image",
                "asset": "proto_03_bright_plate.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Macro translation: sweeps 440px across the canvas
                        {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": -240.0},
                            {"frame": 60, "value": 200.0},
                            {"frame": FRAMES - 1, "value": -240.0}
                        ]},
                        # Meso morph: scale breathes 1.0 -> 1.20
                        {"property": "scale", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 1.0},
                            {"frame": 60, "value": 1.20},
                            {"frame": FRAMES - 1, "value": 1.0}
                        ]}
                    ]
                }
            },
            {
                "id": "subtractive_dark_occluder",
                "type": "image",
                "asset": "proto_03_dark_occluder.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "blend_mode": "normal",
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Antiphase counter-motion: moves opposite to bright plate
                        {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 180.0},
                            {"frame": 60, "value": -160.0},
                            {"frame": FRAMES - 1, "value": 180.0}
                        ]},
                        {"property": "rotation_z", "easing": "linear", "keyframes": [
                            {"frame": 0, "value": -8.0},
                            {"frame": FRAMES - 1, "value": 8.0}
                        ]}
                    ]
                }
            }
        ]
    }


# ==============================================================================
# Prototype 2: 06 - GlowPath / Bezier Ribbon
# ==============================================================================

def build_assets_06() -> Path:
    """06: Curved Bezier luminous ribbon with razor hot core and chromatic separation."""
    im = Image.new("RGBA", (PW, PH), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    
    # Dynamic curved trajectory across canvas
    pts = []
    for step in range(121):
        t = step / 120.0
        # P0=(-300, 1500), P1=(900, 1600), P2=(2100, 300), P3=(3600, 400)
        x = (1 - t)**3 * (-300) + 3 * (1 - t)**2 * t * 900 + 3 * (1 - t) * t**2 * 2100 + t**3 * 3600
        y = (1 - t)**3 * 1500 + 3 * (1 - t)**2 * t * 1600 + 3 * (1 - t) * t**2 * 300 + t**3 * 400
        pts.append((x, y))

    # Multi-tier hot ribbon strokes
    strokes = [
        (480, PAL_DARK_BROWN),
        (320, PAL_DEEP_RED),
        (180, PAL_RED_ORANGE),
        (96, PAL_AMBER),
        (48, PAL_GOLD_YELLOW),
        (22, PAL_HOT_YELLOW),
        (8, PAL_WHITE_HOT)
    ]
    for w, col in strokes:
        d.line(pts, fill=col, width=w, joint="curve")
        
    im = im.filter(ImageFilter.GaussianBlur(36.0))
    im = apply_warp(im, freq=0.004, amp=50.0, seed=6)
    im = add_chromatic_aberration(im, offset=6)
    
    plate_path = PLATES_DIR / "proto_06_ribbon_plate.png"
    im.save(plate_path, optimize=True)
    return plate_path


def make_plan_06() -> Dict[str, Any]:
    """Chronon Plan for 06: GlowPath ribbon with dynamic sweeping trajectory."""
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "cinematic_proto_06_glowpath",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "output": {"path": str(OUT_DIR / "cinematic_proto_06.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "glowing_ribbon_layer",
                "type": "image",
                "asset": "proto_06_ribbon_plate.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Macro sweep: ribbon traverses across the frame
                        {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": -320.0},
                            {"frame": 60, "value": 280.0},
                            {"frame": FRAMES - 1, "value": -320.0}
                        ]},
                        {"property": "position_y", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 120.0},
                            {"frame": 60, "value": -100.0},
                            {"frame": FRAMES - 1, "value": 120.0}
                        ]},
                        {"property": "rotation_z", "easing": "linear", "keyframes": [
                            {"frame": 0, "value": -4.0},
                            {"frame": FRAMES - 1, "value": 4.0}
                        ]}
                    ]
                }
            }
        ]
    }


# ==============================================================================
# Prototype 3: 11 - Dense Starburst / Radial Burst
# ==============================================================================

def build_assets_11() -> Path:
    """11: Dense volumetric starburst with 32 anisotropic rays + blazing white-hot core."""
    im = Image.new("RGBA", (PW, PH), PAL_BLACK)
    temp = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = PW // 2, PH // 2
    
    # 32 dense radial rays spanning out to 1900px
    num_rays = 32
    for i in range(num_rays):
        angle = i * (180.0 / num_rays)
        ray = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ray, "RGBA")
        # High contrast anisotropic rays
        h_outer = 56 if i % 2 == 0 else 32
        h_inner = 20 if i % 2 == 0 else 12
        rd.rounded_rectangle((cx - 1800, cy - h_outer // 2, cx + 1800, cy + h_outer // 2), radius=h_outer // 2, fill=(255, 117, 0, 110))
        rd.rounded_rectangle((cx - 1800, cy - h_inner // 2, cx + 1800, cy + h_inner // 2), radius=h_inner // 2, fill=(255, 240, 90, 175))
        ray = ray.filter(ImageFilter.GaussianBlur(14.0))
        rot = ray.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))
        temp.alpha_composite(rot)
        
    # Controlled central optical core (does NOT wash out rays)
    for r, col in reversed([
        (130, PAL_WHITE_HOT),
        (240, PAL_HOT_YELLOW),
        (380, PAL_GOLD_YELLOW),
        (540, PAL_AMBER),
        (720, PAL_RED_ORANGE)
    ]):
        td.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
        
    temp = temp.filter(ImageFilter.GaussianBlur(28.0))
    im.alpha_composite(temp)
    im = add_chromatic_aberration(im, offset=5)
    
    plate_path = PLATES_DIR / "proto_11_starburst_plate.png"
    im.save(plate_path, optimize=True)
    return plate_path


def make_plan_11() -> Dict[str, Any]:
    """Chronon Plan for 11: Starburst with continuous rotation and volumetric breathing."""
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "cinematic_proto_11_starburst",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "output": {"path": str(OUT_DIR / "cinematic_proto_11.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dense_starburst_layer",
                "type": "image",
                "asset": "proto_11_starburst_plate.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Sweeping rotation across full clip
                        {"property": "rotation_z", "easing": "linear", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": FRAMES - 1, "value": 26.0}
                        ]},
                        # Meso volumetric pulsation: breathing 0.96 -> 1.15
                        {"property": "scale", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 60, "value": 1.15},
                            {"frame": FRAMES - 1, "value": 0.96}
                        ]},
                        # Macro drift
                        {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": -70.0},
                            {"frame": 60, "value": 80.0},
                            {"frame": FRAMES - 1, "value": -70.0}
                        ]}
                    ]
                }
            }
        ]
    }


# ==============================================================================
# Prototype 4: 18 - Dark Aperture / Hourglass Diamond
# ==============================================================================

def build_assets_18() -> tuple[Path, Path]:
    """18: Giant golden floodlight backlight MINUS 4 subtractive dark corner masks."""
    # 1. Backlight Flood Plate (Intense white/yellow/orange flood)
    plate = Image.new("RGBA", (PW, PH), PAL_BLACK)
    d = ImageDraw.Draw(plate, "RGBA")
    cx, cy = PW // 2, PH // 2
    for r, col in reversed([
        (400, PAL_WHITE_HOT),
        (750, PAL_HOT_YELLOW),
        (1200, PAL_GOLD_YELLOW),
        (1700, PAL_AMBER),
        (2300, PAL_RED_ORANGE),
        (2800, PAL_DEEP_RED)
    ]):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    plate = plate.filter(ImageFilter.GaussianBlur(68.0))
    plate = apply_warp(plate, freq=0.003, amp=50.0, seed=18)
    backlight_path = PLATES_DIR / "proto_18_backlight_plate.png"
    plate.save(backlight_path, optimize=True)

    # 2. Subtractive 4-Wedge Hourglass Diamond Mask
    mask = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    md = ImageDraw.Draw(mask, "RGBA")
    # 4 corner dark blocks meeting closer to create an intense diamond optical slit
    corner_w, corner_h = int(PW * 0.46), int(PH * 0.46)
    md.rounded_rectangle((-100, -100, corner_w, corner_h), radius=150, fill=(4, 2, 2, 255))
    md.rounded_rectangle((PW - corner_w, -100, PW + 100, corner_h), radius=150, fill=(4, 2, 2, 255))
    md.rounded_rectangle((-100, PH - corner_h, corner_w, PH + 100), radius=150, fill=(4, 2, 2, 255))
    md.rounded_rectangle((PW - corner_w, PH - corner_h, PW + 100, PH + 100), radius=150, fill=(4, 2, 2, 255))
    mask = mask.filter(ImageFilter.GaussianBlur(48.0))
    mask = apply_warp(mask, freq=0.005, amp=50.0, seed=22)
    mask_path = PLATES_DIR / "proto_18_aperture_masks.png"
    mask.save(mask_path, optimize=True)

    return backlight_path, mask_path


def make_plan_18() -> Dict[str, Any]:
    """Chronon Plan for 18: Backlight flood MINUS breathing subtractive aperture masks."""
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "cinematic_proto_18_dark_aperture",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "output": {"path": str(OUT_DIR / "cinematic_proto_18.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "backlight_flood_layer",
                "type": "image",
                "asset": "proto_18_backlight_plate.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Macro drift of the backlight behind the aperture
                        {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": -200.0},
                            {"frame": 60, "value": 200.0},
                            {"frame": FRAMES - 1, "value": -200.0}
                        ]},
                        {"property": "position_y", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 80.0},
                            {"frame": 60, "value": -80.0},
                            {"frame": FRAMES - 1, "value": 80.0}
                        ]}
                    ]
                }
            },
            {
                "id": "subtractive_aperture_masks",
                "type": "image",
                "asset": "proto_18_aperture_masks.png",
                "size": [PW, PH],
                "position": [0.0, 0.0],
                "blend_mode": "normal",
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {
                    "tracks": [
                        # Meso aperture morph: aperture contracts and dilates
                        {"property": "scale", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 60, "value": 1.14},
                            {"frame": FRAMES - 1, "value": 0.94}
                        ]},
                        {"property": "rotation_z", "easing": "in_out_sine", "keyframes": [
                            {"frame": 0, "value": -3.0},
                            {"frame": 60, "value": 3.0},
                            {"frame": FRAMES - 1, "value": -3.0}
                        ]}
                    ]
                }
            }
        ]
    }


# ==============================================================================
# Rendering and Motion Evaluation Suite
# ==============================================================================

PROTOTYPES = {
    "cinematic_proto_03": (build_assets_03, make_plan_03),
    "cinematic_proto_06": (build_assets_06, make_plan_06),
    "cinematic_proto_11": (build_assets_11, make_plan_11),
    "cinematic_proto_18": (build_assets_18, make_plan_18),
}


def render_gpu(plan_path: Path, mp4_path: Path) -> bool:
    """Render plan using Chronon3D CLI on GPU Vulkan."""
    cmd = [
        str(CHRONON_CLI), "render",
        "--plan", str(plan_path),
        "--assets-root", str(PLATES_DIR),
        "--backend", "vulkan",
        "--profile", "preview",
        "--fps", str(FPS),
        "--video-sink", "ffmpeg",
        "--codec", "h264",
        "--preset", "fast",
        "--start-frame", "0",
        "--end-frame", str(FRAMES - 1),
        "--output", str(mp4_path)
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0 or not mp4_path.exists() or mp4_path.stat().st_size == 0:
        print(f"  [ERROR] Render failed for {mp4_path.name} (code {res.returncode}):\n{res.stdout}\n{res.stderr}")
        return False
    size = mp4_path.stat().st_size
    print(f"  [OK] {mp4_path.name} rendered on GPU in {dt:.2f}s ({size:,} bytes)")
    return True


def evaluate_motion_dynamics(mp4_path: Path) -> Tuple[float, List[Image.Image]]:
    """Sample frames at 0s, 1.3s, 2.6s, 3.9s and measure visual change index."""
    timestamps = [0.0, 1.3, 2.6, 3.9]
    sample_images = []
    arrays = []
    
    for t in timestamps:
        out_png = mp4_path.parent / f"{mp4_path.stem}_sample_{int(t*10):02d}.png"
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(mp4_path), "-vframes", "1", str(out_png)], capture_output=True, check=True)
        img = Image.open(out_png).convert("RGB")
        sample_images.append(img)
        thumb = img.resize((160, 90), Image.BICUBIC)
        arrays.append(np.array(thumb, dtype=float) / 255.0)
        out_png.unlink(missing_ok=True)
        
    diffs = []
    for i in range(len(arrays) - 1):
        diffs.append(np.mean(np.abs(arrays[i+1] - arrays[i])))
    mean_motion_index = float(np.mean(diffs))
    return mean_motion_index, sample_images


def build_motion_sheet(all_samples: Dict[str, List[Image.Image]], out_path: Path):
    """Build side-by-side 4-sample temporal progression sheet for each prototype."""
    thumb_w, thumb_h = 480, 270
    rows = len(all_samples)
    cols = 4  # 0s, 1.3s, 2.6s, 3.9s
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (10, 10, 10))
    
    for row_idx, (name, samples) in enumerate(all_samples.items()):
        for col_idx, img in enumerate(samples):
            thumb = img.resize((thumb_w, thumb_h), Image.BICUBIC)
            sheet.paste(thumb, (col_idx * thumb_w, row_idx * thumb_h))
            
    sheet.save(out_path, optimize=True)
    print(f"Motion progression sheet saved: {out_path}")


def upload_mp4_to_drive(mp4_path: Path, drive_folder_id: str) -> Dict[str, Any]:
    """Upload strictly an MP4 file to Google Drive using drive-upload tool."""
    h = hashlib.sha256()
    with open(mp4_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    expected_sha = h.hexdigest()

    cmd = [
        str(DRIVE_UPLOAD_BIN),
        "-credentials", str(CREDS_FILE),
        "-token", str(TOKEN_FILE),
        "-folder", drive_folder_id,
        "-file", str(mp4_path),
        "-name", mp4_path.name,
        "-sha256", expected_sha,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    data: Dict[str, Any] = {}
    for part in out.split():
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v

    data["file_name"] = mp4_path.name
    data["local_path"] = str(mp4_path)
    data["sha256"] = expected_sha
    data["bytes"] = mp4_path.stat().st_size
    data["link"] = f"https://drive.google.com/file/d/{data.get('id', '')}/view?usp=drivesdk"
    return data


def main():
    parser = argparse.ArgumentParser(description="Render 4 Canonical Cinematic Prototypes (V2 Architecture) on GPU and upload to Drive.")
    parser.add_argument("--force", action="store_true", help="Force re-rendering")
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER, help="Google Drive target folder ID")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLATES_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Chronon Cinematic Backgrounds - 4 Canonical Prototypes (V2 Refined) ===")

    # Step 1: Build Assets and Plans
    plans = []
    print("\n--- 1. Generating Master Optical Assets & Authoring Plans ---")
    for name, (asset_builder, plan_builder) in PROTOTYPES.items():
        t0 = time.time()
        asset_builder()
        plan_dict = plan_builder()
        plan_path = OUT_DIR / f"{name}.plan.json"
        mp4_path = OUT_DIR / f"{name}.mp4"
        plan_path.write_text(json.dumps(plan_dict, indent=2))
        plans.append((name, plan_path, mp4_path))
        print(f"  [OK] {name} assets & plan ready in {time.time() - t0:.2f}s")

    # Step 2: Validate Plans
    print("\n--- 2. Validating Plans with Chronon3D CLI ---")
    for name, plan_path, _ in plans:
        cmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(PLATES_DIR)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] {plan_path.name} failed validation:\n{res.stdout}\n{res.stderr}")
            sys.exit(1)
        print(f"  [OK] {plan_path.name} validated 100% PASS")

    # Step 3: Render on GPU Vulkan
    print("\n--- 3. Rendering on GPU Vulkan (RTX A4000) ---")
    for name, plan_path, mp4_path in plans:
        if mp4_path.exists() and not args.force:
            print(f"  [SKIP] {mp4_path.name} already exists")
            continue
        ok = render_gpu(plan_path, mp4_path)
        if not ok:
            sys.exit(1)

    # Step 4: Motion Dynamics Measurement & Contact Sheet
    print("\n--- 4. Evaluating Visual Motion Dynamics (0s, 1.3s, 2.6s, 3.9s) ---")
    motion_results = {}
    all_samples = {}
    for name, _, mp4_path in plans:
        m_index, samples = evaluate_motion_dynamics(mp4_path)
        motion_results[name] = m_index
        all_samples[name] = samples
        print(f"  {name:30s} -> Motion Change Index: {m_index:.4f} (Reference target: ~0.076)")

    sheet_path = OUT_DIR / "prototype_motion_sheet_4x.png"
    build_motion_sheet(all_samples, sheet_path)

    metrics_path = OUT_DIR / "motion_metrics.json"
    metrics_path.write_text(json.dumps(motion_results, indent=2))
    print(f"Metrics written to {metrics_path}")

    # Step 5: Upload MP4 Videos to Google Drive
    if not args.no_upload:
        print(f"\n--- 5. Uploading Prototype MP4s to Google Drive ({args.drive_folder}) ---")
        manifest = {}
        for name, _, mp4_path in plans:
            print(f"  Uploading {mp4_path.name} ({mp4_path.stat().st_size:,} bytes)...")
            up_info = upload_mp4_to_drive(mp4_path, args.drive_folder)
            manifest[mp4_path.name] = up_info
            print(f"    -> ID: {up_info['id']} | Link: {up_info['link']}")
        upload_manifest_path = OUT_DIR / "proto_upload_manifest.json"
        upload_manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"Upload manifest written to {upload_manifest_path}")

    print("\n=== 4 Canonical Prototypes Successfully Completed ===")


if __name__ == "__main__":
    main()
