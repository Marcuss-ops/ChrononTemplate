#!/usr/bin/env python3
"""Chronon Cinematic Backgrounds Back3 Suite V1: 20 GPU-Native Presets.

Implements all 20 cinematic background looks identified from the reference study (back3.mp4),
organized into 5 visual families using native Chronon RenderPlan V3 primitives,
fully optimized for GPU Vulkan rendering:

  Family 1: Film Burn / Blob (01, 02, 03, 10, 13, 19, 20)
  Family 2: Light Streak / Ribbon (04, 06, 07, 08, 15, 16)
  Family 3: Radial Burst (05, 09, 11)
  Family 4: Aperture / Dark Shape (12, 14, 17, 18)
  Family 5: Multi Streak Fan (16, etc.)

Architecture:
  1. Optical Master Plates: Generated with high-precision PIL optical gradients and Gaussian halos.
  2. Native GPU Compositing: Chronon RenderPlan V3 image layers with enable_3d and continuous drift.
  3. Vulkan Hardware Rendering: chronon3d_cli --backend vulkan with fast hardware encoding.
  4. Google Drive Delivery: Uploads ONLY .mp4 video files to target Drive folder.

Target Google Drive Folder: 1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP
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

from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_backgrounds_back3_suite_v1"
PLATES_DIR = OUT_DIR / "assets"
DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = BASE_DIR / "refactored/credentials.json"
TOKEN_FILE = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
FRAMES = 120  # 4.0 seconds per background loop/drift
DEMO_FRAMES = 150  # Five-second, 30fps previews; the optical master plates stay fixed.
DEMO_TRANSITIONS = {
    "transition_diagonal_sweep": ("cinematic_back_04", 0),
    "transition_double_beam": ("cinematic_back_07", 1),
    "transition_anamorphic_flare": ("cinematic_back_15", 2),
    "transition_light_fan": ("cinematic_back_16", 3),
    "transition_radial_sunburst": ("cinematic_back_05", 0),
    "transition_offcenter_sunburst": ("cinematic_back_09", 1),
    "transition_multi_ray_burst": ("cinematic_back_11", 2),
    "transition_warm_edge_bloom": ("cinematic_back_20", 3),
    "transition_diagonal_sweep_drift": ("cinematic_back_04", 1),
    "transition_double_beam_drift": ("cinematic_back_07", 2),
    "transition_anamorphic_flare_drift": ("cinematic_back_15", 3),
    "transition_light_fan_drift": ("cinematic_back_16", 0),
    "transition_radial_sunburst_drift": ("cinematic_back_05", 1),
    "transition_warm_edge_bloom_drift": ("cinematic_back_20", 2),
}
DEMO_TARGET_FOLDER = "19hP526NAFlu7rLbKjHqcGHi1MT7q_wtA"
DEMO_OUT_DIR = BASE_DIR / "ChrononTemplate/out/light_beam_transition_demos_v2"
DEMO_CREDS = BASE_DIR / "RenderingGen/UploadDrive/credentials.json"
DEMO_TOKEN = BASE_DIR / "RenderingGen/UploadDrive/token.json"
DEMO_DRIVE_UPLOAD = BASE_DIR / "RenderingGen/bin/drive-upload"

# Previous upload receipts: IDs and names from the exact demo batch being replaced.
# Cleanup refuses to delete anything outside the requested folder or with a different name.
REPLACED_DRIVE_FILES = {
    "1R7B027BZHlkTM4Lg6kuujm4D7pqAuaPf": "film_burn_rgb.mp4",
    "1Qz6yBtT5tXQLi4eFJw_450RnHPAOKE31": "lightleak_amber_iris.mp4",
    "1QSKUdonkUHROlOfYrwNhggfT9C4CSKNx": "lightleak_crossflare.mp4",
    "1tB60iTc3Jo1y62IO_eNJ3zP5YJBq1vqZ": "lightleak_diagonal_double_sweep.mp4",
    "1hOTzP5zbFZIlJlU40w4cTHuuMJKFIo7a": "lightleak_prism_burst.mp4",
    "1xCZBLXzNOVz3RNaA__BDYDI67G_nNCgc": "lightleak_rgb_combo.mp4",
    "1QsYqcgCmSkvHP4nmo2LRYttk0Al2f6j9": "prismatic_flash.mp4",
    "1b9dZjIyjsCbhI15kQnCqpqG4PhqPtnHn": "rgb_glitch_cut.mp4",
    "1ZJxmj9env6BistAwBkHohyma1GQJVsj0": "rgb_horizontal_tear.mp4",
    "1v_cE4kjs2Vu2v91U_KaiMHtQSOzQ7Zfz": "rgb_lens_snap.mp4",
    "1TdWLO88p4TUkC4u3g8p0My-H8zg1Emuq": "rgb_snap.mp4",
    "1WplC9tB1shLDmnB89C3fXQMrI43J2NVM": "rgb_spin_blur.mp4",
    "1nr78QmalRzjDMKIQvp-bYQDZuxZdV4xf": "rgb_split_whip.mp4",
    "1K6oN7U55bFutTGEA5c5rCDjMH9RYLbys": "rgb_zoom_punch.mp4",
}

# Palette constants
PAL_BLACK = (3, 2, 2, 255)
PAL_DEEP_BROWN = (26, 6, 4, 255)
PAL_DEEP_RED = (77, 12, 5, 255)
PAL_ORANGE = (230, 68, 10, 255)
PAL_AMBER = (255, 132, 16, 255)
PAL_YELLOW = (255, 204, 36, 255)
PAL_HOT_YELLOW = (255, 240, 102, 255)


# ==============================================================================
# Optical Plate Generators (Family 1 - 5)
# ==============================================================================

def make_plate_01() -> Image.Image:
    """01: Film Burn / Blob - Warm upper-left corner bloom."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 480, 360
    radii = [
        (180, (255, 240, 102, 245)),
        (360, (255, 132, 16, 195)),
        (600, (230, 68, 10, 135)),
        (880, (77, 12, 5, 75)),
        (1150, (26, 6, 4, 35))
    ]
    for r, col in reversed(radii):
        d.ellipse((cx - r, cy - r * 0.82, cx + r, cy + r * 0.82), fill=col)
    return im.filter(ImageFilter.GaussianBlur(52.0))


def make_plate_02() -> Image.Image:
    """02: Film Burn / Blob - Dual asymmetric warm blobs."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Blob A (top-right)
    ax, ay = 1450, 340
    for r, col in reversed([
        (160, (255, 240, 102, 235)),
        (340, (255, 132, 16, 180)),
        (560, (230, 68, 10, 115)),
        (800, (77, 12, 5, 55))
    ]):
        d.ellipse((ax - r, ay - r * 0.78, ax + r, ay + r * 0.78), fill=col)
    # Blob B (bottom-left)
    bx, by = 440, 780
    for r, col in reversed([
        (140, (255, 204, 36, 210)),
        (280, (230, 68, 10, 160)),
        (480, (77, 12, 5, 95)),
        (700, (26, 6, 4, 40))
    ]):
        d.ellipse((bx - r * 0.9, by - r * 0.75, bx + r * 0.9, by + r * 0.75), fill=col)
    return im.filter(ImageFilter.GaussianBlur(48.0))


def make_plate_03() -> Image.Image:
    """03: Film Burn / Blob - Two large orange ellipses + 1 dark occluding blob."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Left glowing ellipse
    for r, col in reversed([
        (180, (255, 240, 102, 230)),
        (380, (255, 132, 16, 180)),
        (650, (230, 68, 10, 110)),
        (900, (77, 12, 5, 50))
    ]):
        d.ellipse((700 - r, 500 - r * 0.75, 700 + r, 500 + r * 0.75), fill=col)
    # Right glowing ellipse
    for r, col in reversed([
        (160, (255, 204, 36, 220)),
        (340, (230, 68, 10, 160)),
        (600, (77, 12, 5, 90))
    ]):
        d.ellipse((1280 - r, 580 - r * 0.72, 1280 + r, 580 + r * 0.72), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(50.0))
    # Dark occluding blob in center
    d_occlude = ImageDraw.Draw(im, "RGBA")
    d_occlude.ellipse((960 - 320, 540 - 280, 960 + 320, 540 + 280), fill=(2, 1, 1, 230))
    return im.filter(ImageFilter.GaussianBlur(38.0))


def make_plate_04() -> Image.Image:
    """04: Light Streak / Ribbon - Diagonal wide rounded beam crossing at -25 degrees."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = WIDTH, HEIGHT
    # Draw horizontal glowing beam
    for h, col in reversed([
        (50, (255, 240, 102, 250)),
        (140, (255, 132, 16, 200)),
        (280, (230, 68, 10, 130)),
        (480, (77, 12, 5, 70)),
        (720, (26, 6, 4, 30))
    ]):
        td.rounded_rectangle((cx - 1600, cy - h // 2, cx + 1600, cy + h // 2), radius=h // 2, fill=col)
    temp = temp.filter(ImageFilter.GaussianBlur(42.0))
    rotated = temp.rotate(-25, resample=Image.BICUBIC, center=(cx, cy))
    im.alpha_composite(rotated, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_05() -> Image.Image:
    """05: Radial Burst - 12-ray warm volumetric burst."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = WIDTH, HEIGHT
    # 12 radial rays
    for i in range(12):
        angle = i * (180.0 / 12)
        ray = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ray, "RGBA")
        rd.rounded_rectangle((cx - 1500, cy - 40, cx + 1500, cy + 40), radius=20, fill=(255, 132, 16, 85))
        rd.rounded_rectangle((cx - 1500, cy - 15, cx + 1500, cy + 15), radius=8, fill=(255, 240, 102, 130))
        ray = ray.filter(ImageFilter.GaussianBlur(24.0))
        rotated = ray.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))
        temp.alpha_composite(rotated)
    # Central warm core
    for r, col in reversed([
        (140, (255, 240, 102, 255)),
        (280, (255, 132, 16, 210)),
        (460, (230, 68, 10, 140)),
        (700, (77, 12, 5, 60))
    ]):
        td.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    temp = temp.filter(ImageFilter.GaussianBlur(36.0))
    im.alpha_composite(temp, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_06() -> Image.Image:
    """06: Light Streak / Ribbon - Glowing curved Bezier ribbon."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Approximate smooth Bezier curve points
    pts = []
    for step in range(101):
        t = step / 100.0
        # cubic Bezier: P0=(-100, 850), P1=(600, 950), P2=(1350, 150), P3=(2020, 250)
        x = (1 - t)**3 * (-100) + 3 * (1 - t)**2 * t * 600 + 3 * (1 - t) * t**2 * 1350 + t**3 * 2020
        y = (1 - t)**3 * 850 + 3 * (1 - t)**2 * t * 950 + 3 * (1 - t) * t**2 * 150 + t**3 * 250
        pts.append((x, y))
    # Stacked glowing ribbon strokes
    for w, col in reversed([
        (260, (77, 12, 5, 80)),
        (130, (230, 68, 10, 160)),
        (65, (255, 132, 16, 220)),
        (26, (255, 240, 102, 255))
    ]):
        d.line(pts, fill=col, width=w, joint="curve")
    return im.filter(ImageFilter.GaussianBlur(34.0))


def make_plate_07() -> Image.Image:
    """07: Light Streak / Ribbon - Twin angled parallel light beams."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = WIDTH, HEIGHT
    # Beam 1
    y1 = cy - 120
    for h, col in reversed([(36, (255, 240, 102, 250)), (100, (255, 132, 16, 185)), (220, (77, 12, 5, 80))]):
        td.rounded_rectangle((cx - 1500, y1 - h // 2, cx + 1500, y1 + h // 2), radius=h // 2, fill=col)
    # Beam 2
    y2 = cy + 120
    for h, col in reversed([(30, (255, 204, 36, 240)), (80, (230, 68, 10, 175)), (180, (77, 12, 5, 75))]):
        td.rounded_rectangle((cx - 1500, y2 - h // 2, cx + 1500, y2 + h // 2), radius=h // 2, fill=col)
    temp = temp.filter(ImageFilter.GaussianBlur(38.0))
    rotated = temp.rotate(-20, resample=Image.BICUBIC, center=(cx, cy))
    im.alpha_composite(rotated, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_08() -> Image.Image:
    """08: Light Streak / Ribbon - S-curve undulating light ribbon."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    pts = []
    for step in range(101):
        t = step / 100.0
        # cubic Bezier: P0=(-150, 200), P1=(700, 100), P2=(1200, 1000), P3=(2070, 900)
        x = (1 - t)**3 * (-150) + 3 * (1 - t)**2 * t * 700 + 3 * (1 - t) * t**2 * 1200 + t**3 * 2070
        y = (1 - t)**3 * 200 + 3 * (1 - t)**2 * t * 100 + 3 * (1 - t) * t**2 * 1000 + t**3 * 900
        pts.append((x, y))
    for w, col in reversed([
        (280, (77, 12, 5, 75)),
        (140, (230, 68, 10, 150)),
        (68, (255, 132, 16, 215)),
        (28, (255, 240, 102, 255))
    ]):
        d.line(pts, fill=col, width=w, joint="curve")
    return im.filter(ImageFilter.GaussianBlur(36.0))


def make_plate_09() -> Image.Image:
    """09: Radial Burst - Off-center celestial sun rays sweeping from top-left."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    ox, oy = 280 + WIDTH // 2, 200 + HEIGHT // 2
    # Celestial rays radiating from (ox, oy)
    for angle in [12, 20, 28, 36, 44, 52, 60, 68, 76, 84]:
        ray = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ray, "RGBA")
        rd.rounded_rectangle((ox, oy - 35, ox + 2200, oy + 35), radius=18, fill=(255, 132, 16, 85))
        rd.rounded_rectangle((ox, oy - 14, ox + 2200, oy + 14), radius=7, fill=(255, 240, 102, 135))
        ray = ray.filter(ImageFilter.GaussianBlur(26.0))
        rotated = ray.rotate(angle, resample=Image.BICUBIC, center=(ox, oy))
        temp.alpha_composite(rotated)
    # Origin sun core
    for r, col in reversed([
        (160, (255, 240, 102, 255)),
        (320, (255, 132, 16, 210)),
        (520, (230, 68, 10, 140)),
        (760, (77, 12, 5, 65))
    ]):
        td.ellipse((ox - r, oy - r, ox + r, oy + r), fill=col)
    temp = temp.filter(ImageFilter.GaussianBlur(38.0))
    im.alpha_composite(temp, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_10() -> Image.Image:
    """10: Film Burn / Blob - Center stage golden film burn core."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 960, 540
    for r, col in reversed([
        (220, (255, 240, 102, 255)),
        (420, (255, 132, 16, 215)),
        (680, (230, 68, 10, 150)),
        (960, (77, 12, 5, 80)),
        (1250, (26, 6, 4, 35))
    ]):
        d.ellipse((cx - r, cy - r * 0.72, cx + r, cy + r * 0.72), fill=col)
    return im.filter(ImageFilter.GaussianBlur(54.0))


def make_plate_11() -> Image.Image:
    """11: Radial Burst - Radiant sunburst with 16 radial sectors."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = WIDTH, HEIGHT
    for i in range(16):
        angle = i * (180.0 / 16)
        ray = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ray, "RGBA")
        rd.rounded_rectangle((cx - 1500, cy - 35, cx + 1500, cy + 35), radius=16, fill=(255, 204, 36, 85))
        rd.rounded_rectangle((cx - 1500, cy - 12, cx + 1500, cy + 12), radius=6, fill=(255, 240, 102, 140))
        ray = ray.filter(ImageFilter.GaussianBlur(22.0))
        rotated = ray.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))
        temp.alpha_composite(rotated)
    for r, col in reversed([
        (160, (255, 240, 102, 255)),
        (320, (255, 132, 16, 210)),
        (500, (230, 68, 10, 140)),
        (720, (77, 12, 5, 65))
    ]):
        td.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    temp = temp.filter(ImageFilter.GaussianBlur(36.0))
    im.alpha_composite(temp, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_12() -> Image.Image:
    """12: Aperture / Dark Shape - Horizontal letterbox optical slit aperture."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Center warm horizontal slit
    for h, col in reversed([
        (60, (255, 240, 102, 255)),
        (160, (255, 132, 16, 220)),
        (340, (230, 68, 10, 150)),
        (560, (77, 12, 5, 80))
    ]):
        d.rectangle((0, 540 - h // 2, WIDTH, 540 + h // 2), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(40.0))
    # Top and bottom heavy letterbox masks
    md = ImageDraw.Draw(im, "RGBA")
    md.rectangle((0, 0, WIDTH, 280), fill=(2, 1, 1, 250))
    md.rectangle((0, HEIGHT - 280, WIDTH, HEIGHT), fill=(2, 1, 1, 250))
    return im.filter(ImageFilter.GaussianBlur(28.0))


def make_plate_13() -> Image.Image:
    """13: Film Burn / Blob - Vertical edge burn along right perimeter."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 1820, 540
    for r, col in reversed([
        (220, (255, 240, 102, 255)),
        (420, (255, 132, 16, 215)),
        (680, (230, 68, 10, 155)),
        (980, (77, 12, 5, 85)),
        (1300, (26, 6, 4, 35))
    ]):
        d.ellipse((cx - r * 0.75, cy - r, cx + r * 0.75, cy + r), fill=col)
    return im.filter(ImageFilter.GaussianBlur(54.0))


def make_plate_14() -> Image.Image:
    """14: Aperture / Dark Shape - Diagonal dark wedge divide."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Golden underglow across center
    for r, col in reversed([
        (260, (255, 240, 102, 245)),
        (500, (255, 132, 16, 195)),
        (800, (230, 68, 10, 130)),
        (1150, (77, 12, 5, 65))
    ]):
        d.ellipse((960 - r, 540 - r * 0.7, 960 + r, 540 + r * 0.7), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(52.0))
    # Diagonal dark wedge mask
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    td.rounded_rectangle((WIDTH - 1200, HEIGHT - 380, WIDTH + 1200, HEIGHT + 380), radius=120, fill=(2, 1, 1, 245))
    temp = temp.filter(ImageFilter.GaussianBlur(42.0))
    rotated = temp.rotate(-30, resample=Image.BICUBIC, center=(WIDTH, HEIGHT))
    im.alpha_composite(rotated, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_15() -> Image.Image:
    """15: Light Streak / Ribbon - Horizontal anamorphic flare streak."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Horizontal razor streak
    for h, col in reversed([
        (14, (255, 240, 102, 255)),
        (48, (255, 132, 16, 230)),
        (110, (230, 68, 10, 160)),
        (220, (77, 12, 5, 80))
    ]):
        d.rounded_rectangle((0, 540 - h // 2, WIDTH, 540 + h // 2), radius=h // 2, fill=col)
    # Intense central iris flare
    for r, col in reversed([
        (90, (255, 240, 102, 255)),
        (180, (255, 132, 16, 210)),
        (300, (230, 68, 10, 135)),
        (460, (77, 12, 5, 55))
    ]):
        d.ellipse((960 - r, 540 - r, 960 + r, 540 + r), fill=col)
    return im.filter(ImageFilter.GaussianBlur(32.0))


def make_plate_16() -> Image.Image:
    """16: Multi Streak Fan - Four diagonal streaks fanning with varied angles."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    cx, cy = WIDTH, HEIGHT
    streaks = [
        (-18.0, -180, 240, (255, 240, 102, 220)),
        (-24.0, -60, 180, (255, 132, 16, 190)),
        (-30.0, 60, 190, (230, 68, 10, 160)),
        (-36.0, 180, 150, (255, 204, 36, 175))
    ]
    for ang, dy, h, col in streaks:
        s_im = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
        sd = ImageDraw.Draw(s_im, "RGBA")
        y = cy + dy
        sd.rounded_rectangle((cx - 1500, y - h // 2, cx + 1500, y + h // 2), radius=h // 2, fill=col)
        sd.rounded_rectangle((cx - 1500, y - h // 6, cx + 1500, y + h // 6), radius=h // 6, fill=(255, 240, 102, 240))
        s_im = s_im.filter(ImageFilter.GaussianBlur(36.0))
        rot = s_im.rotate(ang, resample=Image.BICUBIC, center=(cx, cy))
        temp.alpha_composite(rot)
    im.alpha_composite(temp, dest=(-WIDTH // 2, -HEIGHT // 2))
    return im


def make_plate_17() -> Image.Image:
    """17: Aperture / Dark Shape - Vignetted keyhole aperture."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    # Central warm core
    for r, col in reversed([
        (180, (255, 240, 102, 250)),
        (360, (255, 132, 16, 200)),
        (580, (230, 68, 10, 140)),
        (820, (77, 12, 5, 70))
    ]):
        d.ellipse((960 - r, 540 - r * 0.8, 960 + r, 540 + r * 0.8), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(46.0))
    # Keyhole dark mask border
    mask = Image.new("RGBA", (WIDTH, HEIGHT), (2, 1, 1, 245))
    md = ImageDraw.Draw(mask, "RGBA")
    md.ellipse((960 - 450, 540 - 350, 960 + 450, 540 + 350), fill=(0, 0, 0, 0))
    mask = mask.filter(ImageFilter.GaussianBlur(50.0))
    im.alpha_composite(mask)
    return im


def make_plate_18() -> Image.Image:
    """18: Aperture / Dark Shape - 4-wedge hourglass diamond aperture."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    for r, col in reversed([
        (220, (255, 240, 102, 250)),
        (440, (255, 132, 16, 205)),
        (720, (230, 68, 10, 145)),
        (1050, (77, 12, 5, 75))
    ]):
        d.ellipse((960 - r, 540 - r, 960 + r, 540 + r), fill=col)
    im = im.filter(ImageFilter.GaussianBlur(48.0))
    # 4 corner dark wedges creating diamond hourglass
    cd = ImageDraw.Draw(im, "RGBA")
    cd.rounded_rectangle((-200, -200, 650, 480), radius=100, fill=(2, 1, 1, 240))
    cd.rounded_rectangle((WIDTH - 650, -200, WIDTH + 200, 480), radius=100, fill=(2, 1, 1, 240))
    cd.rounded_rectangle((-200, HEIGHT - 480, 650, HEIGHT + 200), radius=100, fill=(2, 1, 1, 240))
    cd.rounded_rectangle((WIDTH - 650, HEIGHT - 480, WIDTH + 200, HEIGHT + 200), radius=100, fill=(2, 1, 1, 240))
    return im.filter(ImageFilter.GaussianBlur(44.0))


def make_plate_19() -> Image.Image:
    """19: Film Burn / Blob - Low horizon warm caldera rising from bottom."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 960, 1060
    for r, col in reversed([
        (280, (255, 240, 102, 255)),
        (540, (255, 132, 16, 220)),
        (850, (230, 68, 10, 160)),
        (1200, (77, 12, 5, 95)),
        (1600, (26, 6, 4, 40))
    ]):
        d.ellipse((cx - r * 1.3, cy - r * 0.55, cx + r * 1.3, cy + r * 0.55), fill=col)
    return im.filter(ImageFilter.GaussianBlur(54.0))


def make_plate_20() -> Image.Image:
    """20: Film Burn / Blob - Organic floating bokeh cloud with 3 drifting blobs."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), PAL_BLACK)
    d = ImageDraw.Draw(im, "RGBA")
    blobs = [
        (650, 420, (255, 240, 102, 225), (255, 132, 16, 160)),
        (1340, 500, (255, 204, 36, 215), (230, 68, 10, 155)),
        (960, 740, (255, 132, 16, 220), (77, 12, 5, 140))
    ]
    for bx, by, core, halo in blobs:
        for r, col in reversed([(140, core), (300, halo), (520, (77, 12, 5, 70))]):
            d.ellipse((bx - r, by - r * 0.82, bx + r, by + r * 0.82), fill=col)
    return im.filter(ImageFilter.GaussianBlur(50.0))


ALL_PLATE_BUILDERS = {
    "cinematic_back_01": make_plate_01,
    "cinematic_back_02": make_plate_02,
    "cinematic_back_03": make_plate_03,
    "cinematic_back_04": make_plate_04,
    "cinematic_back_05": make_plate_05,
    "cinematic_back_06": make_plate_06,
    "cinematic_back_07": make_plate_07,
    "cinematic_back_08": make_plate_08,
    "cinematic_back_09": make_plate_09,
    "cinematic_back_10": make_plate_10,
    "cinematic_back_11": make_plate_11,
    "cinematic_back_12": make_plate_12,
    "cinematic_back_13": make_plate_13,
    "cinematic_back_14": make_plate_14,
    "cinematic_back_15": make_plate_15,
    "cinematic_back_16": make_plate_16,
    "cinematic_back_17": make_plate_17,
    "cinematic_back_18": make_plate_18,
    "cinematic_back_19": make_plate_19,
    "cinematic_back_20": make_plate_20,
}


# ==============================================================================
# Chronon RenderPlan V3 Builder with Native GPU Motion
# ==============================================================================

def make_chronon_plan(name: str, plate_filename: str) -> Dict[str, Any]:
    """Build a Chronon RenderPlan V3 referencing the plate with GPU 3D drift."""
    i = int(name.split("_")[-1])
    # Varied subtle organic drifts for each preset
    drift_patterns = [
        [{"property": "position_x", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": -35.0}, {"frame": 60, "value": 35.0}, {"frame": FRAMES - 1, "value": -35.0}]},
         {"property": "scale", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": 1.0}, {"frame": 60, "value": 1.04}, {"frame": FRAMES - 1, "value": 1.0}]}],
        [{"property": "position_y", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": 25.0}, {"frame": 60, "value": -25.0}, {"frame": FRAMES - 1, "value": 25.0}]},
         {"property": "scale", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": 1.03}, {"frame": 60, "value": 1.0}, {"frame": FRAMES - 1, "value": 1.03}]}],
        [{"property": "rotation_z", "easing": "linear", "keyframes": [{"frame": 0, "value": -1.5}, {"frame": FRAMES - 1, "value": 1.5}]},
         {"property": "scale", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": 1.01}, {"frame": 60, "value": 1.05}, {"frame": FRAMES - 1, "value": 1.01}]}],
        [{"property": "position_x", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": 30.0}, {"frame": 60, "value": -30.0}, {"frame": FRAMES - 1, "value": 30.0}]},
         {"property": "position_y", "easing": "in_out_sine", "keyframes": [{"frame": 0, "value": -15.0}, {"frame": 60, "value": 15.0}, {"frame": FRAMES - 1, "value": -15.0}]}]
    ]
    tracks = drift_patterns[i % len(drift_patterns)]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": name,
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES
        },
        "output": {
            "path": str(OUT_DIR / f"{name}.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": [
            {
                "id": f"{name}_plate",
                "type": "image",
                "asset": plate_filename,
                "size": [WIDTH + 160.0, HEIGHT + 90.0],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {"tracks": tracks}
            }
        ]
    }


def make_light_beam_transition_plan(name: str, plate_id: str,
                                    motion_variant: int) -> Dict[str, Any]:
    """Render one original light-beam plate with the suite's restrained camera drift."""
    if not 0 <= motion_variant < 4:
        raise ValueError("light-beam motion variant must be between 0 and 3")
    drift_patterns = [
        [{"property": "position_x", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": -35.0},
                        {"frame": DEMO_FRAMES // 2, "value": 35.0},
                        {"frame": DEMO_FRAMES - 1, "value": -35.0}]},
         {"property": "scale", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": 1.0},
                        {"frame": DEMO_FRAMES // 2, "value": 1.04},
                        {"frame": DEMO_FRAMES - 1, "value": 1.0}]}],
        [{"property": "position_y", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": 25.0},
                        {"frame": DEMO_FRAMES // 2, "value": -25.0},
                        {"frame": DEMO_FRAMES - 1, "value": 25.0}]},
         {"property": "scale", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": 1.03},
                        {"frame": DEMO_FRAMES // 2, "value": 1.0},
                        {"frame": DEMO_FRAMES - 1, "value": 1.03}]}],
        [{"property": "rotation_z", "easing": "linear",
          "keyframes": [{"frame": 0, "value": -1.5},
                        {"frame": DEMO_FRAMES - 1, "value": 1.5}]},
         {"property": "scale", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": 1.01},
                        {"frame": DEMO_FRAMES // 2, "value": 1.05},
                        {"frame": DEMO_FRAMES - 1, "value": 1.01}]}],
        [{"property": "position_x", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": 30.0},
                        {"frame": DEMO_FRAMES // 2, "value": -30.0},
                        {"frame": DEMO_FRAMES - 1, "value": 30.0}]},
         {"property": "position_y", "easing": "in_out_sine",
          "keyframes": [{"frame": 0, "value": -15.0},
                        {"frame": DEMO_FRAMES // 2, "value": 15.0},
                        {"frame": DEMO_FRAMES - 1, "value": -15.0}]}],
    ]
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": name,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": DEMO_FRAMES},
        "output": {"path": str(DEMO_OUT_DIR / f"{name}.mp4"),
                   "format": "mp4", "codec": "h264"},
        "layers": [{
            "id": f"{name}-optical-master", "type": "image",
            "asset": f"{plate_id}_plate.png", "size": [WIDTH + 160, HEIGHT + 90],
            "position": [0, 0], "start_frame": 0,
            "duration_frames": DEMO_FRAMES, "enable_3d": True,
            "animation": {"tracks": drift_patterns[motion_variant]},
        }],
    }


def render_light_beam_demos() -> None:
    """Render 14 five-second transitions from the suite's original optical master plates."""
    DEMO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLATES_DIR.mkdir(parents=True, exist_ok=True)
    if not CHRONON_CLI.is_file():
        raise FileNotFoundError(f"Chronon CLI is missing: {CHRONON_CLI}")
    for name, (plate_id, motion_variant) in DEMO_TRANSITIONS.items():
        plate_path = PLATES_DIR / f"{plate_id}_plate.png"
        if not plate_path.is_file():
            plate = ALL_PLATE_BUILDERS[plate_id]()
            plate.save(plate_path, optimize=True)
        plan = make_light_beam_transition_plan(name, plate_id, motion_variant)
        plan_path = DEMO_OUT_DIR / f"{name}.plan.json"
        video_path = DEMO_OUT_DIR / f"{name}.mp4"
        previous_plan = None
        if plan_path.is_file():
            try:
                previous_plan = json.loads(plan_path.read_text())
            except json.JSONDecodeError:
                pass
        plan_path.write_text(json.dumps(plan, indent=2) + "\n")
        validate = [str(CHRONON_CLI), "validate", "--plan", str(plan_path),
                    "--assets-root", str(PLATES_DIR)]
        subprocess.run(validate, check=True)
        if video_path.is_file() and video_path.stat().st_size > 0:
            probe = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
                "-show_entries", "format=duration", "-of", "json", str(video_path),
            ], capture_output=True, text=True)
            if probe.returncode == 0:
                media = json.loads(probe.stdout)
                streams = media.get("streams", [])
                if previous_plan == plan and streams and (
                        streams[0].get("codec_name"), streams[0].get("width"),
                        streams[0].get("height"), streams[0].get("r_frame_rate"),
                        int(streams[0].get("nb_frames", 0))) == (
                        "h264", WIDTH, HEIGHT, "30/1", DEMO_FRAMES) and \
                        float(media.get("format", {}).get("duration", 0)) >= 5.0:
                    print(f"SKIPPED valid existing {video_path}")
                    continue
        render = [str(CHRONON_CLI), "render", "--plan", str(plan_path),
                  "--assets-root", str(PLATES_DIR), "--backend", "software",
                  "--output", str(video_path)]
        subprocess.run(render, check=True)
        print(f"RENDERED {video_path}")


def upload_verified_light_beam_demos(folder_id: str = DEMO_TARGET_FOLDER) -> list[dict]:
    """Upload only fully rendered H.264 1080p/5s demo files to the explicit folder."""
    import re

    if not folder_id or not DEMO_CREDS.is_file() or not DEMO_TOKEN.is_file():
        raise RuntimeError("Drive demo upload needs the explicit destination and secure local OAuth files")
    for secret_path in (DEMO_CREDS, DEMO_TOKEN):
        mode = secret_path.stat().st_mode & 0o777
        if mode & 0o077:
            raise PermissionError(f"refusing Drive upload; {secret_path.name} must have mode 0600")
    manifest = []
    for name in DEMO_TRANSITIONS:
        path = DEMO_OUT_DIR / f"{name}.mp4"
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
            "-show_entries", "format=duration", "-of", "json", str(path),
        ], capture_output=True, text=True, check=True)
        media = json.loads(probe.stdout)
        stream = media["streams"][0]
        if (stream["codec_name"], stream["width"], stream["height"],
                stream["r_frame_rate"], int(stream["nb_frames"])) != (
                "h264", WIDTH, HEIGHT, "30/1", DEMO_FRAMES) or \
                float(media["format"]["duration"]) < 5.0:
            raise RuntimeError(f"refusing to upload nonconforming demo: {path.name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = subprocess.run([
            str(DEMO_DRIVE_UPLOAD), "-credentials", str(DEMO_CREDS),
            "-token", str(DEMO_TOKEN), "-folder", folder_id,
            "-file", str(path), "-name", path.name, "-sha256", digest,
        ], capture_output=True, text=True, check=True)
        match = re.search(r"^DRIVE_UPLOAD_PASS id=(\S+) link=(\S+) parent=(\S+) sha256=(\S+) bytes=(\d+)$",
                          result.stdout.strip())
        if not match or match.group(3) != folder_id or match.group(4) != digest:
            raise RuntimeError(f"Drive upload receipt failed verification for {path.name}")
        manifest.append({"name": path.name, "id": match.group(1), "url": match.group(2),
                         "parent": match.group(3), "sha256": digest, "bytes": int(match.group(5))})
        print(f"UPLOADED {path.name} id={match.group(1)}")
    manifest_path = DEMO_OUT_DIR / "drive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def delete_replaced_transition_uploads(folder_id: str = DEMO_TARGET_FOLDER) -> int:
    """Delete only prior demo files after verifying their exact name and parent."""
    helper = BASE_DIR / "RenderingGen/renderinggen/cmd/drive-delete-verified/main.go"
    if not helper.is_file():
        raise FileNotFoundError(f"verified Drive cleanup helper is missing: {helper}")
    for file_id, expected_name in REPLACED_DRIVE_FILES.items():
        subprocess.run([
            "go", "run", str(helper),
            "-credentials", str(DEMO_CREDS), "-token", str(DEMO_TOKEN),
            "-folder", folder_id, "-id", file_id, "-name", expected_name,
        ], cwd=BASE_DIR / "RenderingGen/renderinggen", check=True)
    return len(REPLACED_DRIVE_FILES)


def validate_plan(plan_file: Path) -> bool:
    """Validate plan using chronon3d_cli validate."""
    cmd = [
        str(CHRONON_CLI), "validate",
        "--plan", str(plan_file),
        "--assets-root", str(PLATES_DIR)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [ERROR] {plan_file.name} validation failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}")
        return False
    print(f"  [OK] {plan_file.name} validated successfully")
    return True


def render_plan_gpu(plan_file: Path, mp4_file: Path) -> bool:
    """Render plan using chronon3d_cli with GPU Vulkan backend."""
    cmd = [
        str(CHRONON_CLI), "render",
        "--plan", str(plan_file),
        "--assets-root", str(PLATES_DIR),
        "--backend", "vulkan",
        "--profile", "preview",
        "--fps", str(FPS),
        "--video-sink", "ffmpeg",
        "--codec", "h264",
        "--preset", "fast",
        "--start-frame", "0",
        "--end-frame", str(FRAMES - 1),
        "--output", str(mp4_file)
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if res.returncode != 0 or not mp4_file.exists() or mp4_file.stat().st_size == 0:
        print(f"  [ERROR] {plan_file.name} GPU render failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}")
        return False
    size = mp4_file.stat().st_size
    print(f"  [OK] {mp4_file.name} rendered via GPU in {elapsed:.2f}s ({size:,} bytes)")
    return True


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
    parser = argparse.ArgumentParser(description="Render 20 Chronon Cinematic Backgrounds on GPU and upload MP4s to Google Drive.")
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER, help="Google Drive destination folder ID")
    parser.add_argument("--plates-only", action="store_true", help="Only generate optical master plates")
    parser.add_argument("--plans-only", action="store_true", help="Only generate plan files")
    parser.add_argument("--validate-only", action="store_true", help="Generate and validate plans only")
    parser.add_argument("--render-only", action="store_true", help="Generate, validate, and render without uploading")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing MP4s without rendering")
    parser.add_argument("--force-render", action="store_true", help="Force re-rendering existing MP4s")
    parser.add_argument("--jobs", type=int, default=2, help="Number of concurrent GPU render jobs")
    parser.add_argument("--filter", default=None, help="Filter specific background name")
    parser.add_argument("--light-beam-demos", action="store_true",
                        help="render 14 five-second light-beam transitions from the cinematic optical plates")
    parser.add_argument("--demo-upload", action="store_true",
                        help="upload only the 14 verified five-second light transitions")
    parser.add_argument("--demo-delete-replaced", action="store_true",
                        help="remove the exact prior demo uploads after the replacement renders are ready")
    parser.add_argument("--demo-drive-folder", default=DEMO_TARGET_FOLDER)
    args = parser.parse_args()

    if args.light_beam_demos:
        render_light_beam_demos()
        if args.demo_upload:
            upload_verified_light_beam_demos(args.demo_drive_folder)
        if args.demo_delete_replaced:
            count = delete_replaced_transition_uploads(args.demo_drive_folder)
            print(f"REMOVED {count} replaced Drive demos from {args.demo_drive_folder}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLATES_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Chronon Cinematic Backgrounds Suite (20 Backgrounds - GPU Vulkan) ===")
    print(f"Output directory: {OUT_DIR}")
    print(f"Plates directory: {PLATES_DIR}")
    print(f"Drive Folder ID:  {args.drive_folder}")
    print(f"GPU Render Jobs:  {args.jobs}")

    # Step 1: Generate Optical Master Plates
    print("\n--- Generating Optical Master Plates ---")
    for name, plate_fn in ALL_PLATE_BUILDERS.items():
        if args.filter and args.filter not in name:
            continue
        plate_path = PLATES_DIR / f"{name}_plate.png"
        if not plate_path.exists() or args.force_render:
            t0 = time.time()
            img = plate_fn()
            img.save(plate_path, optimize=True)
            print(f"  [plate] {plate_path.name} generated in {time.time() - t0:.2f}s ({plate_path.stat().st_size:,} bytes)")
        else:
            print(f"  [SKIP] {plate_path.name} already exists")

    if args.plates_only:
        print("Plates generated. Exiting.")
        return

    # Step 2: Author Chronon RenderPlans
    print("\n--- Authoring Chronon RenderPlans ---")
    plans: List[tuple[str, Path, Path]] = []
    for name in ALL_PLATE_BUILDERS:
        if args.filter and args.filter not in name:
            continue
        plate_filename = f"{name}_plate.png"
        plan_dict = make_chronon_plan(name, plate_filename)
        plan_path = OUT_DIR / f"{name}.plan.json"
        mp4_path = OUT_DIR / f"{name}.mp4"
        plan_path.write_text(json.dumps(plan_dict, indent=2))
        plans.append((name, plan_path, mp4_path))
        print(f"  [plan] {plan_path.name} written")

    if args.plans_only:
        print("Plans generated. Exiting.")
        return

    # Step 3: Validate Plans
    print("\n--- Validating Plans with Chronon3d CLI ---")
    all_valid = True
    for name, plan_path, _ in plans:
        if not validate_plan(plan_path):
            all_valid = False
    if not all_valid:
        print("One or more plans failed validation. Aborting render.")
        sys.exit(1)

    if args.validate_only:
        print("All plans validated successfully.")
        return

    # Step 4: Render Plans on GPU
    if not args.upload_only:
        print(f"\n--- Rendering MP4s on GPU (Jobs: {args.jobs}, Backend: vulkan) ---")
        from concurrent.futures import ThreadPoolExecutor, as_completed

        render_tasks = []
        for name, plan_path, mp4_path in plans:
            if mp4_path.exists() and not args.force_render:
                print(f"  [SKIP] {mp4_path.name} already exists ({mp4_path.stat().st_size:,} bytes)")
                continue
            render_tasks.append((name, plan_path, mp4_path))

        if render_tasks:
            failed = False
            with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                futures = {executor.submit(render_plan_gpu, plan, mp4): (name, mp4) for name, plan, mp4 in render_tasks}
                for fut in as_completed(futures):
                    name, mp4 = futures[fut]
                    ok = fut.result()
                    if not ok:
                        print(f"  [FAIL] GPU Render failed for {name}")
                        failed = True
            if failed:
                print("One or more renders failed. Aborting.")
                sys.exit(1)

    if args.render_only:
        print("\nRendering complete (render-only mode).")
        return

    # Step 5: Upload ONLY MP4 Videos to Google Drive
    print(f"\n--- Uploading MP4 Videos ONLY to Google Drive ({args.drive_folder}) ---")
    manifest = {}
    for name, _, mp4_path in plans:
        if not mp4_path.exists():
            print(f"  [ERROR] {mp4_path.name} does not exist for upload.")
            sys.exit(1)
        print(f"  Uploading {mp4_path.name} ({mp4_path.stat().st_size:,} bytes)...")
        up_info = upload_mp4_to_drive(mp4_path, args.drive_folder)
        manifest[mp4_path.name] = up_info
        print(f"    -> ID: {up_info['id']} | Link: {up_info['link']}")

    manifest_path = OUT_DIR / "upload_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nUpload manifest written to {manifest_path}")
    print("\n=== All 20 Cinematic Backgrounds Uploaded Successfully ===")


if __name__ == "__main__":
    main()
