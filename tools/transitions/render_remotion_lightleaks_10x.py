#!/usr/bin/env python3
"""Chronon Remotion-Style High Quality Light Leak Transitions (0.5s GPU Suite).

Authentic analog optical light leak transitions for high-quality video editing,
inspired by Remotion @remotion/effects and 35mm / anamorphic cinematic lens flares.

Key specifications:
  - Duration: 0.5 seconds (30 frames at 60 FPS, ultra-smooth motion graphics).
  - Resolution: 1080p (1920x1080).
  - Architecture: PyTorch GPU (CUDA RTX A4000) + NVENC H.264 studio encoding.
  - Optical transition envelope: 0 intensity at frame 0, peaks at t=0.5 with
    intense bloom covering the cut point, then smoothly dissolves back to 0.
  - 10 distinct optical styles:
      01: Warm Golden Flare Sweep (Kodak 500T style)
      02: 35mm Film Burn Edge Flash (Molten perforation leak)
      03: Anamorphic Streak Cyan (Cinematic cylindrical flare)
      04: Solar Radial Sunburst (Celestial 14-ray burst)
      05: Corner Bloom Amber (Vintage lens flare)
      06: Prismatic Rainbow Wash (Spectral dispersion leak)
      07: Dual Antiphase Glow (Counter-rotating bi-color lobes)
      08: Vintage Super 8 Bleed (Organic gate halation)
      09: Horizontal Whip Flare (High-velocity pan streak)
      10: Sunset Aurora Drift (Multitonal evening wave)

Uploads directly to Google Drive folder: 1cg55lnTcCusPS2mxj2zekYQcS0OTTnjM
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
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/remotion_lightleaks_10x"
DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = Path.home() / ".config/velox/credentials.json"
TOKEN_FILE = Path.home() / ".config/velox/token.json"
DEFAULT_DRIVE_FOLDER = "1cg55lnTcCusPS2mxj2zekYQcS0OTTnjM"

WIDTH = 1920
HEIGHT = 1080
FPS = 60
DURATION_SEC = 0.5
TOTAL_FRAMES = int(FPS * DURATION_SEC)  # 30 frames for exactly 0.500s


# ==============================================================================
# GPU Optical Shader Engine
# ==============================================================================

class GPULightLeakEngine:
    def __init__(self, width: int = 1920, height: int = 1080, device: str = "cuda"):
        self.w = width
        self.h = height
        self.device = torch.device(device)

        aspect = width / height
        y = torch.linspace(-1.0, 1.0, height, device=self.device)
        x = torch.linspace(-aspect, aspect, width, device=self.device)
        self.Y, self.X = torch.meshgrid(y, x, indexing="ij")

        # Smooth low-frequency wave banks for fluid turbulence
        torch.manual_seed(2026)
        self.kx = torch.tensor([0.70, 1.40, 2.60, 4.50], device=self.device).view(4, 1, 1)
        self.ky = torch.tensor([0.60, 1.20, 2.30, 3.90], device=self.device).view(4, 1, 1)
        self.phases = (torch.rand(4, device=self.device) * 6.283).view(4, 1, 1)
        self.speeds = torch.tensor([1.20, 1.80, 2.40, 3.20], device=self.device).view(4, 1, 1)
        self.amps = torch.tensor([0.55, 0.28, 0.12, 0.05], device=self.device).view(4, 1, 1)

    def organic_turb(self, x: torch.Tensor, y: torch.Tensor, t: float, speed_mult: float = 1.0) -> torch.Tensor:
        """Smooth low-frequency organic fluid turbulence."""
        t_vec = t * self.speeds * speed_mult
        w = torch.sin(x.unsqueeze(0) * self.kx + y.unsqueeze(0) * self.ky + t_vec + self.phases)
        return (w * self.amps).sum(dim=0)

    def color_ramp(self, intensity: torch.Tensor, palette: list[tuple[float, tuple[float, float, float]]]) -> torch.Tensor:
        """Continuous analog film color ramp using smooth Hermite cubic interpolation."""
        intensity = torch.clamp(intensity, 0.0, 1.0)
        R = torch.zeros_like(intensity)
        G = torch.zeros_like(intensity)
        B = torch.zeros_like(intensity)

        for i in range(len(palette) - 1):
            p0, c0 = palette[i]
            p1, c1 = palette[i + 1]
            mask = (intensity >= p0) & (intensity <= p1 if i == len(palette) - 2 else intensity < p1)
            t = (intensity - p0) / (p1 - p0 + 1e-6)
            t_smooth = t * t * (3.0 - 2.0 * t)

            R = torch.where(mask, c0[0] + (c1[0] - c0[0]) * t_smooth, R)
            G = torch.where(mask, c0[1] + (c1[1] - c0[1]) * t_smooth, G)
            B = torch.where(mask, c0[2] + (c1[2] - c0[2]) * t_smooth, B)

        return torch.stack([R, G, B], dim=2)


# ==============================================================================
# Authentic Cinematic Palettes
# ==============================================================================

# Kodak Warm Gold (Vision3 500T)
PAL_WARM_GOLD = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.12, (0.180, 0.020, 0.005)),
    (0.30, (0.580, 0.090, 0.008)),
    (0.52, (0.920, 0.320, 0.015)),
    (0.70, (1.000, 0.650, 0.040)),
    (0.85, (1.000, 0.880, 0.160)),
    (0.95, (1.000, 0.970, 0.650)),
    (1.00, (1.000, 1.000, 0.950)),
]

# 35mm Film Burn (Fiery Scarlet & Molten Amber)
PAL_FILM_BURN = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.10, (0.220, 0.010, 0.005)),
    (0.28, (0.680, 0.050, 0.010)),
    (0.48, (0.980, 0.220, 0.015)),
    (0.68, (1.000, 0.520, 0.030)),
    (0.84, (1.000, 0.820, 0.120)),
    (0.94, (1.000, 0.950, 0.550)),
    (1.00, (1.000, 1.000, 0.920)),
]

# Panavision Anamorphic Cyan Flare
PAL_ANAMORPHIC_CYAN = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.12, (0.005, 0.040, 0.090)),
    (0.30, (0.015, 0.180, 0.380)),
    (0.50, (0.040, 0.480, 0.780)),
    (0.70, (0.180, 0.780, 0.950)),
    (0.86, (0.550, 0.920, 1.000)),
    (0.95, (0.880, 0.980, 1.000)),
    (1.00, (1.000, 1.000, 1.000)),
]

# Celestial Solar Sunburst
PAL_SOLAR_BURST = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.12, (0.160, 0.030, 0.005)),
    (0.32, (0.650, 0.180, 0.010)),
    (0.55, (0.980, 0.550, 0.030)),
    (0.74, (1.000, 0.820, 0.150)),
    (0.88, (1.000, 0.940, 0.450)),
    (0.96, (1.000, 0.990, 0.820)),
    (1.00, (1.000, 1.000, 1.000)),
]

# Amber Halation Bloom
PAL_AMBER_BLOOM = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.14, (0.180, 0.040, 0.008)),
    (0.35, (0.600, 0.160, 0.012)),
    (0.58, (0.920, 0.480, 0.035)),
    (0.76, (1.000, 0.740, 0.120)),
    (0.88, (1.000, 0.900, 0.380)),
    (0.96, (1.000, 0.980, 0.750)),
    (1.00, (1.000, 1.000, 0.950)),
]

# Prismatic Rainbow Dispersion
PAL_PRISMATIC = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.15, (0.080, 0.010, 0.220)),  # Deep violet
    (0.32, (0.010, 0.150, 0.650)),  # Royal blue
    (0.48, (0.020, 0.650, 0.550)),  # Turquoise / green
    (0.65, (0.850, 0.720, 0.020)),  # Golden yellow
    (0.80, (0.950, 0.280, 0.350)),  # Vivid rose
    (0.92, (0.980, 0.750, 0.880)),  # Pastel magenta
    (1.00, (1.000, 1.000, 1.000)),  # Hot white
]

# Dual Antiphase (Gold & Rose)
PAL_DUAL_ROSE = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.15, (0.150, 0.005, 0.060)),
    (0.35, (0.550, 0.030, 0.250)),
    (0.58, (0.900, 0.180, 0.450)),
    (0.78, (1.000, 0.550, 0.720)),
    (0.90, (1.000, 0.850, 0.920)),
    (1.00, (1.000, 1.000, 1.000)),
]

# Vintage Super 8 Kodachrome
PAL_SUPER8_KODAK = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.12, (0.220, 0.030, 0.008)),
    (0.32, (0.650, 0.120, 0.015)),
    (0.55, (0.950, 0.420, 0.025)),
    (0.72, (1.000, 0.700, 0.100)),
    (0.86, (1.000, 0.880, 0.320)),
    (0.95, (1.000, 0.980, 0.720)),
    (1.00, (1.000, 1.000, 0.940)),
]

# Horizontal Whip Flare (Copper to Hot White)
PAL_WHIP_COPPER = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.10, (0.180, 0.025, 0.005)),
    (0.28, (0.620, 0.140, 0.010)),
    (0.50, (0.950, 0.450, 0.025)),
    (0.70, (1.000, 0.750, 0.150)),
    (0.85, (1.000, 0.920, 0.450)),
    (0.95, (1.000, 0.980, 0.820)),
    (1.00, (1.000, 1.000, 1.000)),
]

# Sunset Aurora (Plum -> Magenta -> Sunset Peach -> Gold)
PAL_SUNSET_AURORA = [
    (0.00, (0.000, 0.000, 0.000)),
    (0.12, (0.120, 0.010, 0.120)),
    (0.30, (0.480, 0.040, 0.320)),
    (0.50, (0.880, 0.180, 0.350)),
    (0.70, (1.000, 0.520, 0.220)),
    (0.85, (1.000, 0.820, 0.380)),
    (0.95, (1.000, 0.960, 0.780)),
    (1.00, (1.000, 1.000, 0.980)),
]


# ==============================================================================
# Transition Progress & Optical Envelope Helpers
# ==============================================================================

def transition_envelope(p: float, power: float = 1.0) -> float:
    """Symmetric optical bell curve for seamless transition.
    p in [0, 1]: 0 at p=0, 1.0 at p=0.5 (peak cut frame), 0 at p=1.
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    val = math.sin(math.pi * p)
    return float(val ** power)


# ==============================================================================
# 10 Remotion-Style High Quality Light Leak Transitions
# ==============================================================================

def t_01_warm_golden_sweep(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """01: Warm Golden Flare Sweep (Diagonal across cut)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.1)
    t = f / FPS

    # Diagonal sweep trajectory: top-left to bottom-right
    cx = -2.2 + 4.4 * p
    cy = -1.3 + 2.6 * p

    turb = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 2.5) * 0.22
    # Diagonal tilted distance band (-30 deg)
    tilt = 0.577
    dist_band = torch.abs((e.Y + turb - cy) + (e.X + turb - cx) * tilt)

    # Core beam + wide soft wash
    core = torch.exp(-(dist_band / 0.35)**2) * 1.85
    halo = torch.exp(-dist_band / 0.85) * 0.95
    wash = torch.exp(-dist_band / 2.20) * 0.55

    raw = (core + halo + wash) * env * 1.70
    intensity = 1.0 - torch.exp(-raw * 1.40)
    rgb = e.color_ramp(intensity, PAL_WARM_GOLD)
    grain = (torch.rand_like(dist_band) - 0.5) * (0.018 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_02_film_burn_edge_flash(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """02: 35mm Film Burn Edge Flash (Perforation leak surging from left)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.0)
    t = f / FPS

    # Burn surges in from left to center, then burns away
    cx = -2.0 + 2.2 * math.sin(math.pi * p)
    cy = 0.0 + 0.35 * math.sin(t * 3.0)

    turb_x = e.organic_turb(e.X * 1.2, e.Y * 1.2, t * 2.8) * 0.38
    turb_y = e.organic_turb((e.X + 1.5) * 1.1, (e.Y - 1.2) * 1.1, t * 2.5) * 0.32
    Xw, Yw = e.X + turb_x, e.Y + turb_y

    dx, dy = Xw - cx, Yw - cy
    r = torch.sqrt(dx**2 * 0.70 + dy**2 * 1.35)

    flicker = 1.0 + 0.15 * math.sin(t * 12.0)
    core = torch.exp(-r * 0.95) * 2.10 * flicker
    halo = torch.exp(-r * 0.35) * 0.75

    # Soot occluder along outer perimeter
    soot_mask = torch.sigmoid((r - 1.4) * 3.5)
    raw = (core * (0.25 + 0.75 * (1.0 - soot_mask)) + halo) * env * 1.65
    intensity = 1.0 - torch.exp(-raw * 1.45)
    rgb = e.color_ramp(intensity, PAL_FILM_BURN)
    grain = (torch.rand_like(r) - 0.5) * (0.020 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_03_anamorphic_streak_cyan(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """03: Anamorphic Streak Cyan (Horizontal cinematic cylindrical flare)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.2)
    t = f / FPS

    # Slight vertical drift across center
    cy = 0.08 * math.sin(p * math.pi * 2.0)

    turb = e.organic_turb(e.X * 1.8, e.Y * 1.8, t * 3.0) * 0.06
    # Ultra-wide horizontal stretch
    y_dist = torch.abs(e.Y + turb - cy)
    x_dist = torch.abs(e.X)

    # Intense razor-sharp horizontal filament
    filament = torch.exp(-(y_dist / 0.035)**2) * 2.40 * torch.exp(-(x_dist / 1.70)**2)
    # Cylindrical horizontal halo
    streak_halo = torch.exp(-(y_dist / 0.16)**2) * 1.20 * torch.exp(-(x_dist / 1.50))
    # Broad optical bloom at center cut
    center_bloom = torch.exp(-(torch.sqrt(e.X**2 + (e.Y * 2.2)**2) / 0.65)) * 0.95

    raw = (filament + streak_halo + center_bloom) * env * 1.80
    intensity = 1.0 - torch.exp(-raw * 1.40)
    rgb = e.color_ramp(intensity, PAL_ANAMORPHIC_CYAN)
    grain = (torch.rand_like(y_dist) - 0.5) * (0.015 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_04_solar_radial_burst(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """04: Solar Radial Sunburst (Celestial 14-ray burst at center)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.05)
    t = f / FPS

    # Center origin slightly above focal line
    cx = 0.0
    cy = -0.15

    dx = e.X - cx
    dy = e.Y - cy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.80

    turb = e.organic_turb(e.X * 1.3, e.Y * 1.3, t * 2.0) * 0.15
    # 14 dynamic volumetric rays
    rays = (torch.cos(theta * 14.0 + turb * 4.0) * 0.5 + 0.5) ** 2.2
    ray_intensity = torch.exp(-r * 0.90) * rays * 1.80
    sun_core = torch.exp(-(r / 0.38)**2) * 2.60
    corona = torch.exp(-r * 0.45) * 0.85

    raw = (sun_core + ray_intensity + corona) * env * 1.65
    intensity = 1.0 - torch.exp(-raw * 1.40)
    rgb = e.color_ramp(intensity, PAL_SOLAR_BURST)
    grain = (torch.rand_like(r) - 0.5) * (0.018 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_05_corner_bloom_amber(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """05: Corner Bloom Amber (Massive top-right optical bloom)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.0)
    t = f / FPS

    # Expands inward from top-right corner
    cx = 1.65 - 0.70 * math.sin(math.pi * p)
    cy = -1.15 + 0.50 * math.sin(math.pi * p)

    turb = e.organic_turb(e.X * 0.95, e.Y * 0.95, t * 2.2) * 0.28
    dx = e.X + turb - cx
    dy = e.Y + turb - cy
    r = torch.sqrt(dx**2 * 0.85 + dy**2 * 1.15)

    flicker = 1.0 + 0.12 * math.sin(t * 10.0)
    core = torch.exp(-r * 0.85) * 2.20 * flicker
    halo = torch.exp(-r * 0.38) * 0.95
    wash = torch.exp(-r * 0.18) * 0.40

    raw = (core + halo + wash) * env * 1.70
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_AMBER_BLOOM)
    grain = (torch.rand_like(r) - 0.5) * (0.020 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_06_prismatic_rainbow_wash(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """06: Prismatic Rainbow Wash (Spectral chromatic dispersion)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.1)
    t = f / FPS

    # Angled sweep: bottom-left to top-right
    cx = -1.8 + 3.6 * p
    cy = 1.0 - 2.0 * p

    turb = e.organic_turb(e.X * 1.3, e.Y * 1.3, t * 2.6) * 0.20
    # Multi-band chromatic dispersion wave
    dist = (e.X + turb - cx) * 0.707 - (e.Y + turb - cy) * 0.707

    # Spatial chromatic mapping: maps wave coordinate to spectral palette
    band = torch.abs(dist)
    core = torch.exp(-(band / 0.40)**2) * 1.90
    halo = torch.exp(-band / 0.90) * 0.85

    raw = (core + halo) * env * 1.75
    intensity = 1.0 - torch.exp(-raw * 1.45)
    rgb = e.color_ramp(intensity, PAL_PRISMATIC)
    grain = (torch.rand_like(dist) - 0.5) * (0.016 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_07_dual_antiphase_glow(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """07: Dual Antiphase Glow (Counter-rotating gold & rose lobes meeting at center)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.0)
    t = f / FPS

    # Lobe 1 (Gold, top-left rushing toward center)
    l1_x = -1.6 + 1.6 * math.sin(math.pi * p)
    l1_y = -1.0 + 1.0 * math.sin(math.pi * p)
    # Lobe 2 (Rose, bottom-right rushing toward center)
    l2_x = 1.6 - 1.6 * math.sin(math.pi * p)
    l2_y = 1.0 - 1.0 * math.sin(math.pi * p)

    turb = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 2.4) * 0.24
    r1 = torch.sqrt((e.X + turb - l1_x)**2 * 0.85 + (e.Y + turb - l1_y)**2 * 1.15)
    r2 = torch.sqrt((e.X + turb - l2_x)**2 * 1.10 + (e.Y + turb - l2_y)**2 * 0.85)

    c1 = (torch.exp(-r1 * 0.95) * 1.50 + torch.exp(-r1 * 0.35) * 0.55) * env
    c2 = (torch.exp(-r2 * 0.95) * 1.50 + torch.exp(-r2 * 0.35) * 0.55) * env

    int1 = 1.0 - torch.exp(-c1 * 1.40)
    int2 = 1.0 - torch.exp(-c2 * 1.40)

    rgb1 = e.color_ramp(int1, PAL_WARM_GOLD)
    rgb2 = e.color_ramp(int2, PAL_DUAL_ROSE)

    # Additive screen blending of the two lobes
    combined = 1.0 - (1.0 - rgb1) * (1.0 - rgb2)
    grain = (torch.rand_like(r1) - 0.5) * (0.018 * env)
    return (torch.clamp(combined + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_08_vintage_super8_bleed(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """08: Vintage Super 8 Bleed (Organic shutter flicker & gate halation)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=0.95)
    t = f / FPS

    # Shutter shutter flicker
    flicker = 1.0 + 0.18 * math.sin(t * 18.0) + 0.08 * math.cos(t * 36.0)

    # Edge frame burn on right & top borders
    edge_x = torch.clamp((e.X - 0.40) / 1.10, 0.0, 2.0)
    edge_y = torch.clamp((-e.Y - 0.20) / 0.80, 0.0, 2.0)
    turb = e.organic_turb(e.X * 1.2, e.Y * 1.2, t * 3.2) * 0.25

    edge_dist = (edge_x + edge_y + turb)
    core = torch.exp(-(2.0 - edge_dist)**2 * 0.75) * 1.90 * flicker
    bloom = torch.exp(-torch.sqrt(e.X**2 + e.Y**2) * 0.55) * 0.65

    raw = (core + bloom) * env * 1.70
    intensity = 1.0 - torch.exp(-raw * 1.45)
    rgb = e.color_ramp(intensity, PAL_SUPER8_KODAK)
    grain = (torch.rand_like(e.X) - 0.5) * (0.024 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_09_horizontal_whip_flare(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """09: Horizontal Whip Flare (High-velocity camera pan streak)."""
    p = f / (TOTAL_FRAMES - 1)
    # Fast rise, rapid fall
    env = transition_envelope(p, power=1.35)
    t = f / FPS

    # High speed pan along X axis
    cx = -2.8 + 5.6 * p
    cy = 0.05 * math.sin(p * math.pi * 3.0)

    turb = e.organic_turb(e.X * 1.5, e.Y * 1.5, t * 4.0) * 0.08
    dx = (e.X + turb - cx)
    dy = (e.Y + turb - cy)

    # Extreme motion blur elongation along X
    streak = torch.exp(-(dy / 0.18)**2) * torch.exp(-(dx / 1.20)**2) * 2.60
    flare_halo = torch.exp(-(dy / 0.55)**2) * 0.85
    burst = torch.exp(-torch.sqrt(dx**2 + (dy * 2.5)**2) / 0.45) * 1.30

    raw = (streak + flare_halo + burst) * env * 1.85
    intensity = 1.0 - torch.exp(-raw * 1.50)
    rgb = e.color_ramp(intensity, PAL_WHIP_COPPER)
    grain = (torch.rand_like(dx) - 0.5) * (0.015 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def t_10_sunset_aurora_drift(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """10: Sunset Aurora Drift (Multitonal evening organic light wave)."""
    p = f / (TOTAL_FRAMES - 1)
    env = transition_envelope(p, power=1.0)
    t = f / FPS

    # Vertical wave moving from bottom to top
    cy = 1.4 - 2.8 * p

    turb = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 2.2) * 0.28
    wave = 0.22 * torch.sin(e.X * 1.6 + t * 3.0) + 0.10 * torch.cos(e.X * 3.2 - t * 2.5)
    dist = torch.abs(e.Y + turb - (cy + wave))

    core = torch.exp(-(dist / 0.38)**2) * 2.10
    halo = torch.exp(-dist / 0.85) * 0.85
    wash = torch.exp(-dist / 2.00) * 0.45

    raw = (core + halo + wash) * env * 1.70
    intensity = 1.0 - torch.exp(-raw * 1.40)
    rgb = e.color_ramp(intensity, PAL_SUNSET_AURORA)
    grain = (torch.rand_like(dist) - 0.5) * (0.018 * env)
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


# ==============================================================================
# Presets Registry
# ==============================================================================

PRESETS: Dict[str, Tuple[str, Callable[[GPULightLeakEngine, int], torch.Tensor], str]] = {
    "01": (
        "transition_01_warm_golden_sweep",
        t_01_warm_golden_sweep,
        "Warm Golden Flare Sweep (Diagonal Kodak Vision3 wash)"
    ),
    "02": (
        "transition_02_film_burn_edge_flash",
        t_02_film_burn_edge_flash,
        "35mm Film Burn Edge Flash (Molten perforation leak)"
    ),
    "03": (
        "transition_03_anamorphic_streak_cyan",
        t_03_anamorphic_streak_cyan,
        "Anamorphic Streak Cyan (Cinematic cylindrical flare)"
    ),
    "04": (
        "transition_04_solar_radial_burst",
        t_04_solar_radial_burst,
        "Solar Radial Sunburst (Celestial 14-ray burst)"
    ),
    "05": (
        "transition_05_corner_bloom_amber",
        t_05_corner_bloom_amber,
        "Corner Bloom Amber (Vintage lens flare & halation)"
    ),
    "06": (
        "transition_06_prismatic_rainbow_wash",
        t_06_prismatic_rainbow_wash,
        "Prismatic Rainbow Wash (Spectral chromatic dispersion)"
    ),
    "07": (
        "transition_07_dual_antiphase_glow",
        t_07_dual_antiphase_glow,
        "Dual Antiphase Glow (Counter-rotating gold & rose lobes)"
    ),
    "08": (
        "transition_08_vintage_super8_bleed",
        t_08_vintage_super8_bleed,
        "Vintage Super 8 Bleed (Organic shutter flicker & gate halation)"
    ),
    "09": (
        "transition_09_horizontal_whip_flare",
        t_09_horizontal_whip_flare,
        "Horizontal Whip Flare (High-velocity camera pan streak)"
    ),
    "10": (
        "transition_10_sunset_aurora_drift",
        t_10_sunset_aurora_drift,
        "Sunset Aurora Drift (Multitonal evening organic light wave)"
    ),
}


# ==============================================================================
# Rendering Engine & NVENC Encoder
# ==============================================================================

def render_transition(key: str, engine: GPULightLeakEngine, out_dir: Path) -> Tuple[Path, np.ndarray]:
    name, func, desc = PRESETS[key]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.mp4"

    t0 = time.time()

    # Hardware NVENC H.264 pipe with high quality settings
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", "16",
        "-b:v", "35M",
        "-maxrate", "45M",
        "-bufsize", "45M",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    peak_frame_np = None

    for f in range(TOTAL_FRAMES):
        with torch.no_grad():
            frame_tensor = func(engine, f)
            frame_np = frame_tensor.cpu().numpy()
        proc.stdin.write(frame_np.tobytes())
        # Save frame at midpoint (peak of transition, frame 15)
        if f == TOTAL_FRAMES // 2:
            peak_frame_np = frame_np.copy()

    proc.stdin.close()
    stderr = proc.stderr.read().decode(errors="replace")
    proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error on {name}: {stderr}")

    elapsed = time.time() - t0
    print(f"  ✓ [{key}/10] {name}.mp4 rendered in {elapsed:.2f}s ({TOTAL_FRAMES / elapsed:.1f} FPS)")
    return out_path, peak_frame_np


def generate_contact_sheet(frames: Dict[str, np.ndarray], out_path: Path):
    """Generate a high-res 2x5 contact sheet of all 10 transition peak frames."""
    thumbs = []
    tw, th = 640, 360
    for k in sorted(PRESETS.keys()):
        frame = frames[k]
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        thumb = cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_AREA)

        # Title overlay
        name, _, desc = PRESETS[k]
        cv2.rectangle(thumb, (0, 0), (tw, 44), (10, 10, 10), -1)
        cv2.putText(thumb, f"#{k}: {name}", (14, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(thumb, desc[:60], (14, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1, cv2.LINE_AA)
        thumbs.append(thumb)

    # 5 columns x 2 rows
    row1 = np.hstack(thumbs[:5])
    row2 = np.hstack(thumbs[5:10])
    sheet = np.vstack([row1, row2])

    cv2.imwrite(str(out_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94])
    print(f"  ✓ Contact sheet saved: {out_path} ({sheet.shape[1]}x{sheet.shape[0]})")


# ==============================================================================
# Google Drive Uploader
# ==============================================================================

def refresh_drive_token() -> str:
    with open(TOKEN_FILE) as f:
        tok_data = json.load(f)
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    client_info = creds.get("installed") or creds.get("web")
    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]
    refresh_token = tok_data.get("refresh_token")

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        new_token = res["access_token"]
        tok_data["access_token"] = new_token
        with open(TOKEN_FILE, "w") as f:
            json.dump(tok_data, f, indent=2)
        return new_token


def upload_to_drive(files: List[Path], folder_id: str) -> Dict[str, Any]:
    print(f"\n[Google Drive Upload] Refreshing OAuth2 token and uploading to folder: {folder_id}...")
    token = refresh_drive_token()
    boundary = "----ChrononRemotionLightLeaks"
    manifest: Dict[str, Any] = {}

    for idx, fpath in enumerate(files, 1):
        fname = fpath.name
        fsize = fpath.stat().st_size
        mime = "video/mp4" if fpath.suffix == ".mp4" else "image/jpeg"

        print(f"  [{idx}/{len(files)}] Uploading {fname} ({fsize / 1024:.1f} KB)...", flush=True)
        with open(fpath, "rb") as f:
            file_bytes = f.read()

        meta = json.dumps({"name": fname, "parents": [folder_id]})
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: {mime}\r\n\r\n"
        ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}"
            },
            method="POST"
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    res = json.load(resp)
                    file_id = res["id"]
                    link = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"

                    # Calculate sha256
                    sha = hashlib.sha256(file_bytes).hexdigest()
                    manifest[fname] = {
                        "name": fname,
                        "id": file_id,
                        "link": link,
                        "bytes": fsize,
                        "sha256": sha
                    }
                    print(f"    ✓ Uploaded! Link: {link}", flush=True)

                    # Set reader permissions
                    try:
                        perm_req = urllib.request.Request(
                            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
                            data=json.dumps({"role": "reader", "type": "anyone"}).encode(),
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                            method="POST"
                        )
                        with urllib.request.urlopen(perm_req):
                            pass
                    except Exception:
                        pass
                    break
            except Exception as e:
                if attempt == 2:
                    print(f"    ✗ Failed upload after 3 attempts: {e}")
                time.sleep(1.0)

    manifest_path = OUT_DIR / "drive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n[Manifest] Saved upload manifest to {manifest_path}")
    return manifest


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Render 10 Remotion-style high-quality light leak transitions.")
    parser.add_argument("--keys", nargs="+", default=[f"{i:02d}" for i in range(1, 11)])
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"=== Chronon Remotion-Style Light Leak Transitions (0.5s GPU Suite) ===")
    print(f"Device: {device} ({torch.cuda.get_device_name(0)})")
    print(f"Format: 1920x1080 @ {FPS} FPS | Duration: {DURATION_SEC}s ({TOTAL_FRAMES} frames)")
    print(f"Target Drive Folder: {args.drive_folder}")

    engine = GPULightLeakEngine(WIDTH, HEIGHT, device=device)

    t_start = time.time()
    rendered_videos: List[Path] = []
    peak_frames: Dict[str, np.ndarray] = {}

    print(f"\n[GPU Render] Rendering {len(args.keys)} transitions...")
    for k in args.keys:
        v_path, peak_frame = render_transition(k, engine, OUT_DIR)
        rendered_videos.append(v_path)
        peak_frames[k] = peak_frame

    # Generate contact sheet
    contact_sheet_path = OUT_DIR / "contact_sheet_remotion_lightleaks_10x.jpg"
    generate_contact_sheet(peak_frames, contact_sheet_path)

    t_total = time.time() - t_start
    print(f"\n[Done Rendering] All {len(rendered_videos)} transitions rendered in {t_total:.2f}s!")

    if not args.no_upload:
        files_to_upload = rendered_videos + [contact_sheet_path]
        upload_to_drive(files_to_upload, args.drive_folder)


if __name__ == "__main__":
    main()
