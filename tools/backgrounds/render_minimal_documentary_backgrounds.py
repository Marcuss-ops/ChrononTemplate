#!/usr/bin/env python3
"""Chronon 15 Minimalist Documentary Backgrounds Suite.

Generates 15 elegant, cinema-grade, restrained background presets tailored for
documentaries, video essays, and archival storytelling:

  01 — Dark Film Grain
  02 — Dark Paper
  03 — Archival Film
  04 — Deep Navy Gradient
  05 — Warm Documentary
  06 — Editorial Ivory
  07 — Soft Vignette
  08 — Matte Charcoal
  09 — Subtle Film Scratches
  10 — Blurred Backdrop
  11 — Newspaper Paper
  12 — Faint Horizontal Lines
  13 — Floating Dust
  14 — Muted Olive
  15 — Soft Light Sweep

Design Principles:
- Almost static to the naked eye; subtle organic motion and breathing emerge over several seconds.
- Restrained color palettes (charcoal, graphite, sepia, editorial ivory, deep navy, muted olive).
- Tactile, physical surface textures (paper fibers, 35mm grain, microscopic dust, soft vignette).
- 1920x1080 @ 30 FPS, 8.0 seconds (240 frames), H.264 CRF 18.
- Google Drive upload integration via RenderingGen/bin/drive-upload.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
CATALOG_DIR = BASE_DIR / "ChrononTemplate/catalog/minimal_documentary_backgrounds"
ASSETS_DIR = CATALOG_DIR / "assets"
PLANS_DIR = CATALOG_DIR / "plans"
OUT_DIR = CATALOG_DIR / "out"
MANIFEST_PATH = CATALOG_DIR / "manifest.json"

DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = Path(os.path.expanduser("~/.config/velox/credentials.json"))
TOKEN_FILE = Path(os.path.expanduser("~/.config/velox/token.json"))
DEFAULT_DRIVE_FOLDER = "1ZShFShvCn5Lyf57XD0HfVBKhgYJxbMP_"
DRIVE_SUBFOLDER = "Minimal_Documentary_Backgrounds"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SECONDS = 8.0
FRAMES = int(FPS * DURATION_SECONDS)  # 240 frames


# ==============================================================================
# Procedural Noise & Texture Utilities (NumPy / PIL)
# ==============================================================================

def make_grain_texture(w: int, h: int, seed: int, fine: float = 0.5,
                       rough: float = 0.5, contrast: float = 1.0) -> Image.Image:
    """Multi-scale Gaussian film grain texture array."""
    rng = np.random.default_rng(seed)
    # Fine grain
    g_fine = rng.normal(128, 14 * contrast, (h, w)).astype(np.float32)
    # Medium grain
    g_med = rng.normal(0, 10 * contrast, (h // 2, w // 2)).astype(np.float32)
    im_med = Image.fromarray(g_med).resize((w, h), Image.BILINEAR)
    # Combine
    combined = g_fine * fine + np.asarray(im_med) * rough
    combined = np.clip(combined, 0, 255).astype(np.uint8)
    return Image.fromarray(combined, mode="L")


def make_paper_fibers_texture(w: int, h: int, seed: int, num_fibers: int = 400) -> Image.Image:
    """Tactile paper cellulose fiber map."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    
    # Tiny organic hair/cellulose fibers
    for _ in range(num_fibers):
        x0 = rng.uniform(0, w)
        y0 = rng.uniform(0, h)
        length = rng.uniform(12, 65)
        angle = rng.uniform(-0.4, 0.4) if rng.random() > 0.3 else rng.uniform(0, math.pi)
        x1 = x0 + length * math.cos(angle)
        y1 = y0 + length * math.sin(angle)
        curvature = rng.uniform(-8, 8)
        cx = (x0 + x1) / 2 + curvature * math.sin(angle)
        cy = (y0 + y1) / 2 - curvature * math.cos(angle)
        alpha = int(rng.uniform(15, 45))
        # Warm fiber tone
        shade = int(rng.uniform(180, 240))
        d.line([(x0, y0), (cx, cy), (x1, y1)], fill=(shade, shade, shade, alpha), width=1)
        
    # Micro specks (pulp flecks)
    for _ in range(num_fibers // 2):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        r = rng.uniform(0.5, 1.8)
        alpha = int(rng.uniform(20, 60))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 195, 185, alpha))
        
    return im.filter(ImageFilter.GaussianBlur(0.6))


# ==============================================================================
# 15 Optical Master Plate Builders
# ==============================================================================

def build_plate_01_dark_film_grain() -> Image.Image:
    """01 — Dark Film Grain: Deep charcoal with fine multi-scale film grain."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (14, 16, 19, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft vertical gradient (slightly lighter at top)
    for y in range(HEIGHT):
        t = y / HEIGHT
        shade = int(14 + (1.0 - t) * 6)
        d.line([(0, y), (WIDTH, y)], fill=(shade, shade + 2, shade + 5, 255))
    
    grain = make_grain_texture(WIDTH, HEIGHT, seed=101, fine=0.7, rough=0.3, contrast=0.7)
    grain_rgba = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    # Map grain to subtle luminance overlay
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.45, 0, 25).astype(np.uint8)
    tone = np.where(arr > 0, 255, 0).astype(np.uint8)
    grain_arr = np.dstack([tone, tone, tone, alpha])
    grain_im = Image.fromarray(grain_arr, mode="RGBA")
    im.alpha_composite(grain_im)
    return im


def build_plate_02_dark_paper() -> Image.Image:
    """02 — Dark Paper: Dark grey graphite with delicate cellulose fibers."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (22, 24, 27, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft diagonal raking light
    for y in range(0, HEIGHT, 2):
        t = y / HEIGHT
        shade = int(22 + (1.0 - t) * 5)
        d.line([(0, y), (WIDTH, y)], fill=(shade, shade + 1, shade + 3, 255), width=2)
    
    # Paper fibers
    fibers = make_paper_fibers_texture(WIDTH, HEIGHT, seed=202, num_fibers=550)
    im.alpha_composite(fibers)
    
    # Fine paper tooth
    tooth = make_grain_texture(WIDTH, HEIGHT, seed=203, fine=0.8, rough=0.2, contrast=0.5)
    arr = np.asarray(tooth, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.35, 0, 20).astype(np.uint8)
    grain_im = Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 230, dtype=np.uint8), alpha]), mode="RGBA")
    im.alpha_composite(grain_im)
    return im


def build_plate_03_archival_film() -> Image.Image:
    """03 — Archival Film: Vintage film base with warm sepia grain and dust."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (16, 14, 12, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Warm dark vignette
    for r in range(1200, 300, -80):
        alpha = int(45 * (1.0 - r / 1200))
        d.ellipse([WIDTH // 2 - r, HEIGHT // 2 - int(r * 0.65),
                   WIDTH // 2 + r, HEIGHT // 2 + int(r * 0.65)],
                  fill=(28, 22, 17, alpha))
    im = im.filter(ImageFilter.GaussianBlur(40.0))
    d = ImageDraw.Draw(im, "RGBA")
    
    # 2 hairline vertical film scratches
    d.line([(480, 0), (481, HEIGHT)], fill=(210, 195, 170, 22), width=1)
    d.line([(1410, 0), (1409, HEIGHT)], fill=(210, 195, 170, 18), width=1)
    
    # Archival grain
    grain = make_grain_texture(WIDTH, HEIGHT, seed=303, fine=0.6, rough=0.4, contrast=0.8)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.45, 0, 28).astype(np.uint8)
    grain_im = Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 200, dtype=np.uint8), alpha]), mode="RGBA")
    im.alpha_composite(grain_im)
    return im


def build_plate_04_deep_navy_gradient() -> Image.Image:
    """04 — Deep Navy Gradient: Inky midnight blue smooth gradient."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (3, 7, 16, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Rich navy gradient from top-right to bottom-left
    for y in range(0, HEIGHT, 2):
        t = y / HEIGHT
        r = int(9 - t * 6)
        g = int(19 - t * 12)
        b = int(34 - t * 18)
        d.line([(0, y), (WIDTH, y)], fill=(max(2, r), max(4, g), max(10, b), 255), width=2)
    
    # Soft upper-right ambient radial glow
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    for radius in range(900, 100, -80):
        a = int(22 * (1.0 - radius / 900))
        gd.ellipse([1600 - radius, 200 - radius, 1600 + radius, 200 + radius],
                   fill=(18, 42, 75, a))
    glow = glow.filter(ImageFilter.GaussianBlur(65.0))
    im.alpha_composite(glow)
    
    # Fine dither grain to prevent any 8-bit banding
    dither = make_grain_texture(WIDTH, HEIGHT, seed=404, fine=0.8, rough=0.2, contrast=0.4)
    arr = np.asarray(dither, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.3, 0, 16).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 210, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_05_warm_documentary() -> Image.Image:
    """05 — Warm Documentary: Earthy antique sepia and raw umber tones."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (20, 15, 10, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft warm center pool
    for r in range(1100, 200, -75):
        alpha = int(38 * (1.0 - r / 1100))
        d.ellipse([WIDTH // 2 - r, HEIGHT // 2 - int(r * 0.7),
                   WIDTH // 2 + r, HEIGHT // 2 + int(r * 0.7)],
                  fill=(48, 32, 20, alpha))
    im = im.filter(ImageFilter.GaussianBlur(55.0))
    
    # Warm tactile texture
    grain = make_grain_texture(WIDTH, HEIGHT, seed=505, fine=0.65, rough=0.35, contrast=0.6)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.4, 0, 22).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 190, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_06_editorial_ivory() -> Image.Image:
    """06 — Editorial Ivory: Clean off-white paper for quotes and graphics."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (243, 239, 230, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft edge darkening / vignette
    for r in range(1250, 450, -80):
        t = (1.0 - r / 1250)
        shade_r = int(243 - t * 20)
        shade_g = int(239 - t * 24)
        shade_b = int(230 - t * 28)
        d.ellipse([WIDTH // 2 - r, HEIGHT // 2 - int(r * 0.62),
                   WIDTH // 2 + r, HEIGHT // 2 + int(r * 0.62)],
                  outline=(shade_r, shade_g, shade_b, int(t * 18)), width=40)
    im = im.filter(ImageFilter.GaussianBlur(45.0))
    
    # Delicate laid paper fibers
    fibers = make_paper_fibers_texture(WIDTH, HEIGHT, seed=606, num_fibers=380)
    # Tint fibers dark warm grey
    f_arr = np.asarray(fibers)
    f_arr[:, :, 0] = 70
    f_arr[:, :, 1] = 65
    f_arr[:, :, 2] = 58
    f_arr[:, :, 3] = (f_arr[:, :, 3] * 0.35).astype(np.uint8)
    im.alpha_composite(Image.fromarray(f_arr, mode="RGBA"))
    return im


def build_plate_07_soft_vignette() -> Image.Image:
    """07 — Soft Vignette: Neutral charcoal with wide luminous center pool."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (9, 10, 13, 255))
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    # Optical center aperture
    cx, cy = WIDTH // 2, HEIGHT // 2
    for r in range(950, 150, -60):
        alpha = int(48 * (1.0 - r / 950))
        gd.ellipse([cx - r, cy - int(r * 0.65), cx + r, cy + int(r * 0.65)],
                   fill=(30, 34, 42, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(60.0))
    im.alpha_composite(glow)
    
    grain = make_grain_texture(WIDTH, HEIGHT, seed=707, fine=0.7, rough=0.3, contrast=0.5)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.35, 0, 18).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 220, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_08_matte_charcoal() -> Image.Image:
    """08 — Matte Charcoal: Uniform architectural graphite/plaster surface."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (24, 25, 27, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Micro tonal variation
    for y in range(0, HEIGHT, 4):
        t = y / HEIGHT
        shade = int(24 + math.sin(t * math.pi) * 3)
        d.line([(0, y), (WIDTH, y)], fill=(shade, shade + 1, shade + 2, 255), width=4)
    
    # Fine stone/chalk tooth
    tooth = make_grain_texture(WIDTH, HEIGHT, seed=808, fine=0.9, rough=0.1, contrast=0.6)
    arr = np.asarray(tooth, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.38, 0, 22).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 200, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_09_subtle_film_scratches() -> Image.Image:
    """09 — Subtle Film Scratches: Dark film plate with 3 faint vertical emulsion lines."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (12, 12, 14, 255))
    d = ImageDraw.Draw(im, "RGBA")
    
    # 3 discrete hairline scratches (broken/faint segments)
    rng = np.random.default_rng(909)
    scratch_xs = [560, 1080, 1540]
    for sx in scratch_xs:
        y = 0
        while y < HEIGHT:
            seg_len = rng.uniform(40, 240)
            gap = rng.uniform(20, 150)
            alpha = int(rng.uniform(16, 38))
            d.line([(sx, y), (sx, min(HEIGHT, y + seg_len))], fill=(210, 210, 215, alpha), width=1)
            y += int(seg_len + gap)
            
    # Small flecks / specks
    for _ in range(35):
        px = rng.uniform(0, WIDTH)
        py = rng.uniform(0, HEIGHT)
        r = rng.uniform(0.5, 1.2)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(210, 210, 215, int(rng.uniform(20, 50))))
        
    grain = make_grain_texture(WIDTH, HEIGHT, seed=910, fine=0.7, rough=0.3, contrast=0.75)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.45, 0, 24).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 220, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_10_blurred_backdrop() -> Image.Image:
    """10 — Blurred Backdrop: Muted large-aperture photographic bokeh masses."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (12, 14, 18, 255))
    temp = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    
    # Warm amber interior glow (top-left)
    for r in range(750, 150, -60):
        td.ellipse([420 - r, 340 - r, 420 + r, 340 + r], fill=(36, 26, 18, int(35 * (1.0 - r / 750))))
    # Soft sage shadow mass (bottom-right)
    for r in range(680, 120, -55):
        td.ellipse([1480 - r, 740 - r, 1480 + r, 740 + r], fill=(19, 28, 24, int(32 * (1.0 - r / 680))))
    # Center ambient depth pool
    for r in range(550, 100, -50):
        td.ellipse([980 - r, 520 - r, 980 + r, 520 + r], fill=(22, 22, 28, int(28 * (1.0 - r / 550))))
        
    temp = temp.filter(ImageFilter.GaussianBlur(80.0))
    im.alpha_composite(temp)
    
    # Fine film noise to bind the blurred masses
    grain = make_grain_texture(WIDTH, HEIGHT, seed=1010, fine=0.75, rough=0.25, contrast=0.55)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.35, 0, 18).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 210, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_11_newspaper_paper() -> Image.Image:
    """11 — Newspaper Paper: Aged beige newsprint with fibers and edge wear."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (221, 212, 193, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Edge age toning
    for y in range(0, HEIGHT, 2):
        t = y / HEIGHT
        edge_t = max(0.0, 1.0 - abs(t - 0.5) * 2.0)
        tone = int(195 + edge_t * 18)
        d.line([(0, y), (WIDTH, y)], fill=(tone + 6, tone + 2, tone - 10, 255), width=2)
    
    # Newsprint horizontal laid fibers
    rng = np.random.default_rng(1111)
    fibers_im = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fibers_im, "RGBA")
    for _ in range(650):
        fx = rng.uniform(0, WIDTH)
        fy = rng.uniform(0, HEIGHT)
        flen = rng.uniform(20, 90)
        fd.line([(fx, fy), (fx + flen, fy + rng.uniform(-1.5, 1.5))],
                fill=(85, 75, 62, int(rng.uniform(14, 34))), width=1)
    fibers_im = fibers_im.filter(ImageFilter.GaussianBlur(0.5))
    im.alpha_composite(fibers_im)
    return im


def build_plate_12_faint_horizontal_lines() -> Image.Image:
    """12 — Faint Horizontal Lines: Deep slate with ultra-thin documentary rules."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (10, 12, 15, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # 1px ledger rules spaced 36px apart
    line_y = 18
    while line_y < HEIGHT:
        d.line([(0, line_y), (WIDTH, line_y)], fill=(120, 140, 165, 14), width=1)
        line_y += 36
    
    # Subtle film grain
    grain = make_grain_texture(WIDTH, HEIGHT, seed=1212, fine=0.7, rough=0.3, contrast=0.5)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.35, 0, 18).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 200, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_13_floating_dust() -> Image.Image:
    """13 — Floating Dust: Dark empty space with 14 soft illuminated dust motes."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (7, 8, 10, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft ambient side gradient
    for x in range(0, WIDTH, 4):
        t = x / WIDTH
        alpha = int(18 * (1.0 - t))
        d.line([(x, 0), (x, HEIGHT)], fill=(22, 25, 30, alpha), width=4)
        
    rng = np.random.default_rng(1313)
    dust_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dust_layer, "RGBA")
    for _ in range(16):
        px = rng.uniform(100, WIDTH - 100)
        py = rng.uniform(80, HEIGHT - 80)
        radius = rng.uniform(2.5, 6.0)
        alpha = int(rng.uniform(35, 95))
        dd.ellipse([px - radius, py - radius, px + radius, py + radius],
                   fill=(230, 225, 215, alpha))
    dust_layer = dust_layer.filter(ImageFilter.GaussianBlur(1.8))
    im.alpha_composite(dust_layer)
    return im


def build_plate_14_muted_olive() -> Image.Image:
    """14 — Muted Olive: Desaturated geopolitical/investigative olive plate."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (21, 28, 22, 255))
    d = ImageDraw.Draw(im, "RGBA")
    # Soft diagonal gradient towards bottom-right
    for y in range(0, HEIGHT, 2):
        t = y / HEIGHT
        r = int(21 - t * 8)
        g = int(28 - t * 10)
        b = int(22 - t * 8)
        d.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255), width=2)
        
    # Soft edge vignette
    for r in range(1150, 300, -75):
        alpha = int(35 * (1.0 - r / 1150))
        d.ellipse([WIDTH // 2 - r, HEIGHT // 2 - int(r * 0.65),
                   WIDTH // 2 + r, HEIGHT // 2 + int(r * 0.65)],
                  fill=(13, 18, 14, alpha))
    im = im.filter(ImageFilter.GaussianBlur(50.0))
    
    # Matte surface grain
    grain = make_grain_texture(WIDTH, HEIGHT, seed=1414, fine=0.7, rough=0.3, contrast=0.6)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.38, 0, 20).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 200, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


def build_plate_15_soft_light_sweep() -> Image.Image:
    """15 — Soft Light Sweep: Void black with wide angled soft light beam."""
    im = Image.new("RGBA", (WIDTH, HEIGHT), (8, 9, 11, 255))
    temp = Image.new("RGBA", (WIDTH * 2, HEIGHT * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(temp, "RGBA")
    cx, cy = WIDTH, HEIGHT
    # Wide, soft daylight beam
    for w in range(700, 100, -80):
        alpha = int(32 * (1.0 - w / 700))
        td.rounded_rectangle([cx - w // 2, cy - 1400, cx + w // 2, cy + 1400],
                             radius=w // 2, fill=(245, 240, 230, alpha))
    temp = temp.filter(ImageFilter.GaussianBlur(75.0))
    rotated = temp.rotate(-32, resample=Image.BICUBIC, center=(cx, cy))
    im.alpha_composite(rotated, dest=(-WIDTH // 2, -HEIGHT // 2))
    
    grain = make_grain_texture(WIDTH, HEIGHT, seed=1515, fine=0.75, rough=0.25, contrast=0.5)
    arr = np.asarray(grain, dtype=np.float32) - 128.0
    alpha = np.clip(np.abs(arr) * 0.35, 0, 18).astype(np.uint8)
    im.alpha_composite(Image.fromarray(np.dstack([np.full((HEIGHT, WIDTH, 3), 220, dtype=np.uint8), alpha]), mode="RGBA"))
    return im


PRESET_BUILDERS = {
    "01_dark_film_grain": (build_plate_01_dark_film_grain, "Dark Film Grain",
                           "Nero antracite con grana finissima e leggere variazioni di luminosità"),
    "02_dark_paper": (build_plate_02_dark_paper, "Dark Paper",
                      "Carta grigio scuro con fibre quasi invisibili e piccole imperfezioni"),
    "03_archival_film": (build_plate_03_archival_film, "Archival Film",
                         "Pellicola vintage con grain, polvere e rarissimi graffi sottili"),
    "04_deep_navy_gradient": (build_plate_04_deep_navy_gradient, "Deep Navy Gradient",
                              "Blu notte quasi nero, con gradiente morbido e leggero noise"),
    "05_warm_documentary": (build_plate_05_warm_documentary, "Warm Documentary",
                            "Toni marroni scuri e seppia, ideali per racconti storici"),
    "06_editorial_ivory": (build_plate_06_editorial_ivory, "Editorial Ivory",
                           "Bianco sporco con grana delicata, perfetto per citazioni e statistiche"),
    "07_soft_vignette": (build_plate_07_soft_vignette, "Soft Vignette",
                         "Centro leggermente luminoso e angoli scuri, con transizione naturale"),
    "08_matte_charcoal": (build_plate_08_matte_charcoal, "Matte Charcoal",
                          "Superficie antracite opaca, quasi uniforme, con texture delicata"),
    "09_subtle_film_scratches": (build_plate_09_subtle_film_scratches, "Subtle Film Scratches",
                                 "Sfondo scuro con graffi occasionali e imperfezioni analogiche"),
    "10_blurred_backdrop": (build_plate_10_blurred_backdrop, "Blurred Backdrop",
                            "Sfondo fotografico molto sfocato, con colori smorzati e senza distrazioni"),
    "11_newspaper_paper": (build_plate_11_newspaper_paper, "Newspaper Paper",
                           "Carta giornale beige, leggermente consumata e desaturata"),
    "12_faint_horizontal_lines": (build_plate_12_faint_horizontal_lines, "Faint Horizontal Lines",
                                  "Linee orizzontali molto sottili e quasi invisibili su fondo scuro"),
    "13_floating_dust": (build_plate_13_floating_dust, "Floating Dust",
                         "Pochissime particelle di polvere che si muovono lentamente"),
    "14_muted_olive": (build_plate_14_muted_olive, "Muted Olive",
                       "Verde oliva desaturato, con texture appena percepibile"),
    "15_soft_light_sweep": (build_plate_15_soft_light_sweep, "Soft Light Sweep",
                            "Una fascia di luce molto morbida attraversa lentamente un fondo nero"),
}


# ==============================================================================
# Chronon RenderPlan V3 Assembly (Restrained Documentary Camera Drifts)
# ==============================================================================

def make_documentary_plan(preset_id: str, plate_filename: str) -> Dict[str, Any]:
    """Generate a Chronon RenderPlan V3 with ultra-slow, almost static organic drift."""
    i = int(preset_id.split("_")[0])
    
    # 5 restrained organic drift archetypes tailored to documentaries
    # Scale ranges stay strictly between 1.000 and 1.015; positions between -15px and +15px.
    drift_archetypes = [
        # Archetype 0: Micro-breathe (scale 1.000 -> 1.012 -> 1.000, tiny x float)
        [
            {"property": "position_x", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": -12.0}, {"frame": FRAMES // 2, "value": 12.0}, {"frame": FRAMES - 1, "value": -12.0}]},
            {"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.000}, {"frame": FRAMES // 2, "value": 1.014}, {"frame": FRAMES - 1, "value": 1.000}]}
        ],
        # Archetype 1: Slow subtle push-in (scale 1.000 -> 1.015, gentle y crawl)
        [
            {"property": "position_y", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 8.0}, {"frame": FRAMES - 1, "value": -8.0}]},
            {"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.000}, {"frame": FRAMES - 1, "value": 1.015}]}
        ],
        # Archetype 2: Lateral documentary tracking (x: -16px -> +16px)
        [
            {"property": "position_x", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": -16.0}, {"frame": FRAMES - 1, "value": 16.0}]},
            {"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.005}, {"frame": FRAMES // 2, "value": 1.012}, {"frame": FRAMES - 1, "value": 1.005}]}
        ],
        # Archetype 3: Diagonal organic float (x +10, y -10)
        [
            {"property": "position_x", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": -10.0}, {"frame": FRAMES - 1, "value": 10.0}]},
            {"property": "position_y", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 8.0}, {"frame": FRAMES - 1, "value": -8.0}]},
            {"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.000}, {"frame": FRAMES - 1, "value": 1.012}]}
        ],
        # Archetype 4: Subtle light sweep float (specialized for 15)
        [
            {"property": "position_x", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": -45.0}, {"frame": FRAMES - 1, "value": 45.0}]},
            {"property": "scale", "easing": "in_out_sine",
             "keyframes": [{"frame": 0, "value": 1.000}, {"frame": FRAMES - 1, "value": 1.010}]}
        ],
    ]
    
    # Preset-specific archetype assignment
    if preset_id == "15_soft_light_sweep":
        tracks = drift_archetypes[4]
    elif preset_id in ("02_dark_paper", "06_editorial_ivory", "11_newspaper_paper"):
        tracks = drift_archetypes[1]  # Steady tactile push-in
    elif preset_id in ("05_warm_documentary", "08_matte_charcoal"):
        tracks = drift_archetypes[2]  # Lateral tracking
    elif preset_id in ("12_faint_horizontal_lines", "14_muted_olive"):
        tracks = drift_archetypes[3]  # Diagonal float
    else:
        tracks = drift_archetypes[0]  # Micro-breathe
        
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": preset_id,
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES
        },
        "output": {
            "path": str(OUT_DIR / f"{preset_id}.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": [
            {
                "id": f"{preset_id}_plate",
                "type": "image",
                "asset": str(Path(plate_filename).resolve().relative_to(BASE_DIR.resolve())),
                "size": [WIDTH + 80.0, HEIGHT + 45.0],
                "position": [0.0, 0.0],
                "start_frame": 0,
                "duration_frames": FRAMES,
                "enable_3d": True,
                "animation": {"tracks": tracks}
            }
        ]
    }


# ==============================================================================
# Pipeline Automation: Build, Render, Upload
# ==============================================================================

def generate_assets_and_plans() -> List[str]:
    """Generate master texture plates and RenderPlan V3 JSONs."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated = []
    print(f"=== Generating 15 Minimalist Documentary Plates & Plans ===")
    for preset_id, (builder, title, desc) in PRESET_BUILDERS.items():
        plate_path = ASSETS_DIR / f"{preset_id}_plate.png"
        plan_path = PLANS_DIR / f"{preset_id}.plan.json"
        
        if not plate_path.exists():
            print(f"  [PLATE] Generating {preset_id}_plate.png ...", flush=True)
            im = builder()
            im.save(plate_path, "PNG", optimize=True)
        else:
            print(f"  [PLATE] Reusing existing {preset_id}_plate.png", flush=True)
            
        plan = make_documentary_plan(preset_id, str(plate_path))
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"  [PLAN]  Wrote {plan_path.name}", flush=True)
        generated.append(preset_id)
        
    return generated


def render_preset(preset_id: str) -> bool:
    """Render one 8.0s MP4 using chronon3d_cli."""
    plan_path = PLANS_DIR / f"{preset_id}.plan.json"
    mp4_path = OUT_DIR / f"{preset_id}.mp4"
    preview_path = OUT_DIR / f"{preset_id}_preview.png"
    
    if not plan_path.exists():
        print(f"[ERROR] Plan not found: {plan_path}")
        return False

    if mp4_path.exists() and mp4_path.stat().st_size > 1000:
        print(f"  [SKIP] {mp4_path.name} already exists ({mp4_path.stat().st_size / 1024.0:.1f} KB)", flush=True)
        if not preview_path.exists():
            subprocess.run([
                "ffmpeg", "-y", "-ss", "00:00:04.000", "-i", str(mp4_path),
                "-vframes", "1", "-q:v", "2", str(preview_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
        
    print(f"\n[RENDER] Rendering {preset_id} (1920x1080 @ 30fps, 240 frames, 8s) ...", flush=True)
    t0 = time.time()
    cmd = [
        str(CHRONON_CLI), "render",
        "--plan", str(plan_path),
        "--assets-root", str(BASE_DIR),
        "--backend", "vulkan",
        "--hardware", "none",
        "--profile", "preview",
        "--fps", str(FPS),
        "--rate-control", "crf",
        "--crf", "18",
        "-o", str(mp4_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    
    if res.returncode != 0 or not mp4_path.exists() or mp4_path.stat().st_size == 0:
        print(f"  [FAIL] Render failed ({elapsed:.1f}s):\n{res.stderr}\n{res.stdout}")
        return False
        
    size_kb = mp4_path.stat().st_size / 1024.0
    print(f"  [PASS] Rendered {mp4_path.name} ({size_kb:.1f} KB in {elapsed:.1f}s)", flush=True)
    
    # Generate high-res preview frame at frame 120 (4.0s midpoint)
    subprocess.run([
        "ffmpeg", "-y", "-ss", "00:00:04.000", "-i", str(mp4_path),
        "-vframes", "1", "-q:v", "2", str(preview_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return True


def upload_to_drive(preset_id: str) -> Dict[str, Any]:
    """Upload rendered MP4 to Google Drive via RenderingGen/bin/drive-upload."""
    mp4_path = OUT_DIR / f"{preset_id}.mp4"
    if not mp4_path.exists():
        return {"status": "error", "error": "file not found"}
        
    cmd = [
        str(DRIVE_UPLOAD_BIN),
        "-credentials", str(CREDS_FILE),
        "-token", str(TOKEN_FILE),
        "-folder", DEFAULT_DRIVE_FOLDER,
        "-subfolder", DRIVE_SUBFOLDER,
        "-file", str(mp4_path),
        "-name", f"{preset_id}.mp4"
    ]
    print(f"[DRIVE] Uploading {mp4_path.name} to {DEFAULT_DRIVE_FOLDER}/{DRIVE_SUBFOLDER} ...", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    out = res.stdout.strip()
    
    link = file_id = ""
    for token in out.split():
        if token.startswith("link="):
            link = token.split("link=", 1)[1]
        elif token.startswith("id="):
            file_id = token.split("id=", 1)[1]
            
    if res.returncode == 0 and "DRIVE_UPLOAD_PASS" in out:
        print(f"  -> SUCCESS ({elapsed:.1f}s): {link}", flush=True)
        return {
            "status": "success",
            "file_id": file_id,
            "link": link,
            "elapsed_seconds": elapsed,
            "file_size_bytes": mp4_path.stat().st_size
        }
    print(f"  -> ERROR ({elapsed:.1f}s): {out} / {res.stderr}", flush=True)
    return {"status": "error", "error": out + "\n" + res.stderr, "elapsed_seconds": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Chronon 15 Minimalist Documentary Backgrounds")
    parser.add_argument("--list", action="store_true", help="List all 15 presets")
    parser.add_argument("--generate-plans", action="store_true", help="Generate plates and plan JSONs")
    parser.add_argument("--render", action="store_true", help="Render presets to MP4")
    parser.add_argument("--preset", type=str, help="Render only a specific preset ID")
    parser.add_argument("--top5", action="store_true", help="Render the 5 flagship presets (01, 04, 06, 07, 10)")
    parser.add_argument("--upload-drive", action="store_true", help="Upload rendered MP4s to Google Drive")
    args = parser.parse_args()
    
    if args.list:
        print("=== 15 Minimalist Documentary Background Presets ===")
        for pid, (_, title, desc) in PRESET_BUILDERS.items():
            print(f"  {pid:25} — {title:22} : {desc}")
        return
        
    generate_assets_and_plans()
    
    targets = []
    if args.preset:
        if args.preset not in PRESET_BUILDERS:
            print(f"Unknown preset: {args.preset}")
            sys.exit(1)
        targets = [args.preset]
    elif args.top5:
        targets = ["01_dark_film_grain", "04_deep_navy_gradient",
                   "06_editorial_ivory", "07_soft_vignette", "10_blurred_backdrop"]
    elif args.render or args.upload_drive:
        targets = list(PRESET_BUILDERS.keys())
        
    manifest = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = []
            
    manifest_map = {m["preset_id"]: m for m in manifest}

    for pid in targets:
        _, title, desc = PRESET_BUILDERS[pid]
        mp4_path = OUT_DIR / f"{pid}.mp4"
        
        if args.render:
            render_preset(pid)
            
        if args.upload_drive:
            existing = manifest_map.get(pid, {})
            if existing.get("upload_status") == "success" and existing.get("drive_link") and mp4_path.exists():
                print(f"  [DRIVE SKIP] {pid} already uploaded: {existing['drive_link']}")
                continue
                
            res = upload_to_drive(pid)
            manifest_map[pid] = {
                "preset_id": pid,
                "title": title,
                "description": desc,
                "duration_seconds": DURATION_SECONDS,
                "resolution": f"{WIDTH}x{HEIGHT}",
                "fps": FPS,
                "local_mp4": str(mp4_path.relative_to(BASE_DIR)) if mp4_path.exists() else "",
                "file_size_bytes": mp4_path.stat().st_size if mp4_path.exists() else 0,
                "drive_link": res.get("link", ""),
                "drive_file_id": res.get("file_id", ""),
                "upload_status": res.get("status", "none")
            }
            with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                json.dump(list(manifest_map.values()), f, indent=2)
                
    print(f"\n[DONE] Manifest updated at {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
