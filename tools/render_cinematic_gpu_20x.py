#!/usr/bin/env python3
"""Chronon Cinematic Backgrounds - Complete 20-Preset GPU Suite (RTX A4000 + NVENC).

Renders all 20 distinct cinematic background looks from the reference study (back3.mp4)
using high-performance vectorized PyTorch GPU shaders and hardware NVENC encoding.
Zero black borders (100% full bleed continuous coordinate functions) and living organic motion.

Presets 01 to 20:
  01: Warm Corner Bloom / Film Leak
  02: Dual Asymmetric Blobs
  03: Molten Organic Film Burn
  04: Diagonal Light Streak (-25 deg)
  05: 12-Ray Volumetric Burst
  06: GlowPath Anamorphic Sweep
  07: Twin Angled Light Beams
  08: S-Curve Undulating Ribbon
  09: Celestial Sun Rays (Top-Left)
  10: Center-Stage Golden Film Burn
  11: Celestial Starburst (32 Rays)
  12: Horizontal Optical Letterbox Aperture
  13: Vertical Right Edge Burn
  14: Diagonal Dark Wedge Divide
  15: Horizontal Anamorphic Flare Streak
  16: Multi-Streak Fan (4 Angles)
  17: Keyhole Aperture
  18: 4-Wedge Hourglass Diamond Aperture
  19: Low Horizon Caldera
  20: Floating Bokeh Cloud (3 Orbs)

Uploads directly to Google Drive folder: 1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP
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
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_backgrounds_20x_gpu"
DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = BASE_DIR / "refactored/credentials.json"
TOKEN_FILE = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "1a5_U3jc82Jl2CpgPgY4c41koZz5tVhdP"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SEC = 4.0
TOTAL_FRAMES = int(FPS * DURATION_SEC)  # 120 frames


# ==============================================================================
# Vectorized GPU Shader Engine
# ==============================================================================

class GPUShaderEngine:
    def __init__(self, width: int = 1920, height: int = 1080, device: str = "cuda"):
        self.w = width
        self.h = height
        self.device = torch.device(device)
        
        # Coordinate grids: X in [-16/9, 16/9], Y in [-1.0, 1.0]
        aspect = width / height
        y = torch.linspace(-1.0, 1.0, height, device=self.device)
        x = torch.linspace(-aspect, aspect, width, device=self.device)
        self.Y, self.X = torch.meshgrid(y, x, indexing="ij")
        
        # Precomputed vectorized harmonic wave banks for instant FBM turbulence
        # 4 octaves computed in a single GPU broadcasted tensor operation
        torch.manual_seed(101)
        self.kx = torch.tensor([1.4, 2.8, 5.6, 11.2], device=self.device).view(4, 1, 1)
        self.ky = torch.tensor([1.2, 2.5, 5.1, 10.4], device=self.device).view(4, 1, 1)
        self.phases = (torch.rand(4, device=self.device) * 6.283).view(4, 1, 1)
        self.speeds = torch.tensor([0.9, 1.4, 1.9, 2.5], device=self.device).view(4, 1, 1)
        self.amps = torch.tensor([0.52, 0.28, 0.14, 0.06], device=self.device).view(4, 1, 1)

    def turb(self, x: torch.Tensor, y: torch.Tensor, t: float, speed_mult: float = 1.0) -> torch.Tensor:
        """Instant vectorized 4-octave turbulence in single tensor broadcast."""
        t_vec = t * self.speeds * speed_mult
        w = torch.sin(x.unsqueeze(0) * self.kx + y.unsqueeze(0) * self.ky + t_vec + self.phases)
        return (w * self.amps).sum(dim=0)

    def color_ramp(self, intensity: torch.Tensor, palette: list[tuple[float, tuple[float, float, float]]]) -> torch.Tensor:
        """Map intensity to RGB using smooth Hermite interpolation."""
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
# Authentic Kodak 5219 / Optical Palettes
# ==============================================================================

PAL_MOLTEN = [
    (0.00, (0.015, 0.008, 0.008)),  # Cinema black
    (0.12, (0.160, 0.025, 0.012)),  # Burnt dark brown
    (0.28, (0.450, 0.055, 0.015)),  # Carmine flame
    (0.48, (0.850, 0.160, 0.005)),  # Fiery red
    (0.68, (1.000, 0.480, 0.010)),  # Molten amber
    (0.85, (1.000, 0.880, 0.250)),  # Solar yellow
    (1.00, (1.000, 0.985, 0.920)),  # White-hot specular
]

PAL_ANAMORPHIC = [
    (0.00, (0.010, 0.006, 0.006)),
    (0.15, (0.220, 0.030, 0.010)),
    (0.35, (0.750, 0.120, 0.005)),
    (0.60, (1.000, 0.420, 0.010)),
    (0.82, (1.000, 0.850, 0.200)),
    (1.00, (1.000, 0.990, 0.940)),
]

PAL_SUNBURST = [
    (0.00, (0.012, 0.008, 0.008)),
    (0.18, (0.260, 0.040, 0.010)),
    (0.40, (0.700, 0.180, 0.008)),
    (0.65, (1.000, 0.520, 0.015)),
    (0.85, (1.000, 0.860, 0.280)),
    (1.00, (1.000, 0.990, 0.930)),
]


# ==============================================================================
# Presets 01 - 20 GPU Frame Evaluators
# ==============================================================================

def f_01(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """01: Warm Upper-Left Corner Bloom / Film Leak."""
    t = f / FPS
    # Origin drifts from top-left toward center
    cx = -0.95 + 0.25 * math.sin(t * 0.9)
    cy = -0.65 + 0.18 * math.cos(t * 0.8)
    disp = e.turb(e.X * 1.8, e.Y * 1.8, t * 0.9) * 0.3
    r = torch.sqrt((e.X + disp - cx)**2 * 0.9 + (e.Y + disp - cy)**2 * 1.2)
    heat = torch.exp(-r * 1.2) * (1.1 + 0.25 * e.turb(e.X * 3.5, e.Y * 3.5, t * 1.3))
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_02(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """02: Dual Asymmetric Blobs in Antiphase."""
    t = f / FPS
    # Blob 1 (top-right orbiting)
    c1x = 0.85 + 0.25 * math.cos(t * 1.1)
    c1y = -0.40 + 0.20 * math.sin(t * 0.9)
    # Blob 2 (bottom-left counter-orbiting)
    c2x = -0.80 - 0.20 * math.sin(t * 1.0)
    c2y = 0.50 - 0.22 * math.cos(t * 1.2)
    disp = e.turb(e.X * 2.0, e.Y * 2.0, t * 0.8) * 0.25
    r1 = torch.sqrt((e.X + disp - c1x)**2 + (e.Y + disp - c1y)**2 * 1.4)
    r2 = torch.sqrt((e.X + disp - c2x)**2 * 1.3 + (e.Y + disp - c2y)**2)
    heat = torch.exp(-r1 * 1.5) * 1.1 + torch.exp(-r2 * 1.6) * 0.95
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_03(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """03: Molten Organic Film Burn (Two Hot Centers + Subtractive Soot)."""
    t = f / FPS
    disp_x = e.turb(e.X * 2.0, e.Y * 2.0, t * 0.8) * 0.35
    disp_y = e.turb(e.X * 2.0 + 3.1, e.Y * 2.0 + 1.7, t * 0.9) * 0.35
    Xw, Yw = e.X + disp_x, e.Y + disp_y
    cx1 = 0.35 * math.sin(t * 1.1) - 0.1
    cy1 = 0.22 * math.cos(t * 0.85)
    r1 = torch.sqrt((Xw - cx1)**2 + (Yw - cy1)**2 * 1.6)
    cx2 = -0.45 * math.cos(t * 0.95 + 1.2)
    cy2 = 0.30 * math.sin(t * 1.3)
    r2 = torch.sqrt((Xw - cx2)**2 * 1.3 + (Yw - cy2)**2 * 1.1)
    heat = torch.exp(-r1 * 1.45) + torch.exp(-r2 * 1.65) * 0.75
    # Subtractive soot
    ox = 0.5 * math.cos(t * 0.7)
    oy = 0.3 * math.sin(t * 0.85)
    ro = torch.sqrt((Xw - ox)**2 * 2.0 + (Yw - oy)**2 * 2.0)
    soot = torch.clamp(1.0 - torch.exp(-ro * 3.0), 0.0, 1.0)
    heat = heat * (0.2 + 0.8 * soot)
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_04(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """04: Diagonal Light Streak (-25 deg) Sweeping Frame."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    y_center = 0.55 - 1.10 * progress
    tilt = 0.466  # tan(25 deg)
    wave = 0.12 * torch.sin(e.X * 3.0 + t * 3.5)
    dist = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    pulse = 1.0 + 0.35 * torch.sin(e.X * 4.0 - t * 5.0)
    core = torch.exp(-(dist / 0.055)**2) * pulse
    halo = torch.exp(-dist / 0.22) * 0.8
    wash = torch.exp(-dist / 0.75) * 0.35
    total = core + halo + wash
    rgb = e.color_ramp(total, PAL_ANAMORPHIC)
    grain = (torch.rand_like(dist) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_05(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """05: 12-Ray Volumetric Radial Burst."""
    t = f / FPS
    cx = 0.10 * math.sin(t * 0.8)
    cy = 0.08 * math.cos(t * 0.9)
    dx, dy = e.X - cx, e.Y - cy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.15
    rays = (torch.cos(theta * 12.0) * 0.5 + 0.5)**5.0
    turb_val = e.turb(e.X * 2.5, e.Y * 2.5, t * 1.1) * 0.25
    rays = rays * (0.8 + 0.4 * turb_val) / (1.0 + r * 1.5)
    core = torch.exp(-r / 0.22) * 1.25 * (1.0 + 0.08 * math.sin(t * 3.0))
    halo = torch.exp(-r / 0.65) * 0.55
    total = core + halo + rays * 0.8
    rgb = e.color_ramp(total, PAL_SUNBURST)
    grain = (torch.rand_like(r) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_06(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """06: GlowPath Anamorphic Sweep (Traversing Bezier/Sine Ribbon)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    y_center = 0.65 - 1.30 * progress
    tilt = 0.35 + 0.08 * math.sin(t * 1.5)
    wave = 0.16 * torch.sin(e.X * 3.2 + t * 4.0) + 0.08 * torch.cos(e.X * 6.5 - t * 2.8)
    dist_G = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    dist_R = torch.abs(e.Y - (y_center - e.X * tilt + wave + 0.025))
    dist_B = torch.abs(e.Y - (y_center - e.X * tilt + wave - 0.025))
    pulse = 1.0 + 0.45 * torch.sin(e.X * 4.0 - t * 6.0)
    core_R = torch.exp(-(dist_R / 0.045)**2) * pulse
    core_G = torch.exp(-(dist_G / 0.045)**2) * pulse
    core_B = torch.exp(-(dist_B / 0.045)**2) * pulse
    halo_R = torch.exp(-dist_R / 0.18) * 0.85
    halo_G = torch.exp(-dist_G / 0.18) * 0.70
    halo_B = torch.exp(-dist_B / 0.18) * 0.40
    wash = torch.exp(-dist_G / 0.60) * 0.35
    R = core_R + halo_R + wash * 0.6
    G = core_G * 0.96 + halo_G * 0.45 + wash * 0.12
    B = core_B * 0.85 + halo_B * 0.08 + wash * 0.02
    rgb = torch.clamp(torch.stack([R, G, B], dim=2), 0.0, 1.0)
    grain = (torch.rand_like(R) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_07(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """07: Twin Angled Light Beams Fanning in Parallax."""
    t = f / FPS
    tilt = 0.36
    sep = 0.32 + 0.08 * math.sin(t * 1.8)
    y_center = 0.15 * math.sin(t * 1.2)
    w1 = 0.09 * torch.sin(e.X * 3.5 + t * 4.2)
    w2 = 0.09 * torch.cos(e.X * 3.5 - t * 3.8)
    d1 = torch.abs(e.Y - (y_center - sep - e.X * tilt + w1))
    d2 = torch.abs(e.Y - (y_center + sep - e.X * tilt + w2))
    b1 = torch.exp(-(d1 / 0.05)**2) * 1.1 + torch.exp(-d1 / 0.22) * 0.75
    b2 = torch.exp(-(d2 / 0.05)**2) * 1.0 + torch.exp(-d2 / 0.22) * 0.70
    wash = torch.exp(-torch.min(d1, d2) / 0.65) * 0.3
    total = b1 + b2 + wash
    rgb = e.color_ramp(total, PAL_ANAMORPHIC)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_08(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """08: S-Curve Undulating Luminous Ribbon."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    # Double S-curve moving across
    y_center = 0.40 - 0.80 * progress
    s_curve = 0.35 * torch.sin(e.X * 2.2 + t * 2.5) + 0.15 * torch.sin(e.X * 4.8 - t * 3.2)
    dist = torch.abs(e.Y - (y_center + s_curve))
    pulse = 1.0 + 0.3 * torch.sin(e.X * 3.0 - t * 5.0)
    core = torch.exp(-(dist / 0.048)**2) * pulse
    halo = torch.exp(-dist / 0.20) * 0.85
    wash = torch.exp(-dist / 0.65) * 0.35
    total = core + halo + wash
    rgb = e.color_ramp(total, PAL_ANAMORPHIC)
    grain = (torch.rand_like(dist) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_09(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """09: Off-Center Celestial Sun Rays (Top-Left Origin)."""
    t = f / FPS
    ox = -1.25 + 0.15 * math.sin(t * 0.7)
    oy = -0.75 + 0.10 * math.cos(t * 0.8)
    dx, dy = e.X - ox, e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.12
    rays = (torch.cos(theta * 14.0) * 0.5 + 0.5)**6.0
    turb_val = e.turb(e.X * 2.5, e.Y * 2.5, t * 1.3) * 0.25
    rays = rays * (0.8 + 0.4 * turb_val) / (1.0 + r * 1.2)
    sun = torch.exp(-r / 0.35) * 1.3
    total = sun + rays * 0.95
    rgb = e.color_ramp(total, PAL_SUNBURST)
    grain = (torch.rand_like(r) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_10(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """10: Center-Stage Golden Film Burn Core."""
    t = f / FPS
    cx = 0.15 * math.sin(t * 0.9)
    cy = 0.10 * math.cos(t * 1.1)
    disp = e.turb(e.X * 2.2, e.Y * 2.2, t * 1.0) * 0.32
    r = torch.sqrt((e.X + disp - cx)**2 * 1.1 + (e.Y + disp - cy)**2 * 1.4)
    pulse = 1.0 + 0.12 * math.sin(t * 3.2)
    heat = torch.exp(-r * 1.15) * 1.25 * pulse
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_11(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """11: Celestial Starburst (32 Anisotropic Rays)."""
    t = f / FPS
    ox = -0.15 + 0.12 * math.sin(t * 0.75)
    oy = 0.05 + 0.08 * math.cos(t * 0.90)
    dx, dy = e.X - ox, e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.18
    rays = (torch.cos(theta * 16.0) * 0.5 + 0.5)**5.0 + (torch.sin(theta * 24.0 + t * 0.5) * 0.5 + 0.5)**7.0 * 0.7
    turb_val = e.turb(e.X * 3.0, e.Y * 3.0, t * 1.2) * 0.25
    rays = rays * (0.8 + 0.4 * turb_val) / (1.0 + r * 1.8)
    core = torch.exp(-r / 0.18) * 1.35 * (1.0 + 0.08 * math.sin(t * 3.5))
    halo = torch.exp(-r / 0.65) * 0.65
    ring = torch.exp(-((r - 0.45) / 0.06)**2) * 0.18
    total = core + halo + rays * 0.85 + ring
    rgb = e.color_ramp(total, PAL_SUNBURST)
    grain = (torch.rand_like(r) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_12(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """12: Horizontal Letterbox Optical Slit Aperture."""
    t = f / FPS
    # Core slit
    d_slit = torch.abs(e.Y)
    slit = torch.exp(-(d_slit / 0.15)**2) * 1.25 + torch.exp(-d_slit / 0.45) * 0.7
    # Breathing letterbox bars
    bar_y = 0.55 + 0.12 * math.sin(t * 1.5)
    turb_bar = e.turb(e.X * 3.0, e.Y * 3.0, t * 0.9) * 0.06
    mask = torch.sigmoid((bar_y - (d_slit + turb_bar)) * 12.0)
    rim = torch.exp(-torch.abs(d_slit - bar_y) * 10.0) * 1.2
    total = slit * mask + rim * 0.75
    rgb = e.color_ramp(total, PAL_MOLTEN)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_13(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """13: Vertical Right Edge Burn Billowing Inward."""
    t = f / FPS
    # Burn origin at right perimeter X ~ 1.7
    cx = 1.65 - 0.15 * math.sin(t * 1.2)
    disp = e.turb(e.X * 2.0, e.Y * 2.0, t * 1.1) * 0.35
    r = torch.sqrt((e.X + disp - cx)**2 * 1.5 + e.Y**2 * 0.8)
    heat = torch.exp(-r * 1.1) * (1.2 + 0.3 * e.turb(e.X * 3.5, e.Y * 3.5, t * 1.5))
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_14(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """14: Diagonal Dark Wedge Divide with Underglow."""
    t = f / FPS
    # Underglow
    r_under = torch.sqrt(e.X**2 * 0.9 + e.Y**2 * 1.3)
    under = torch.exp(-r_under * 0.85) * 1.3
    # Diagonal dark wedge dividing top-right and bottom-left
    tilt = 0.55
    wedge_dist = torch.abs(e.Y - e.X * tilt) + e.turb(e.X * 3.0, e.Y * 3.0, t * 1.0) * 0.15
    wedge_w = 0.35 + 0.10 * math.sin(t * 1.4)
    wedge_mask = torch.sigmoid((wedge_dist - wedge_w) * 8.0)
    rim = torch.exp(-torch.abs(wedge_dist - wedge_w) * 9.0) * 1.35
    total = under * wedge_mask + rim * 0.8
    rgb = e.color_ramp(total, PAL_MOLTEN)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_15(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """15: Horizontal Anamorphic Flare Streak + Central Iris Flare."""
    t = f / FPS
    # Horizontal streak
    wave = 0.025 * torch.sin(e.X * 5.0 + t * 4.0)
    dy = torch.abs(e.Y - wave)
    streak_core = torch.exp(-(dy / 0.025)**2) * 1.4
    streak_halo = torch.exp(-dy / 0.14) * 0.75
    # Central iris flare
    dx = e.X - 0.15 * math.sin(t * 1.1)
    r_iris = torch.sqrt(dx**2 + e.Y**2)
    iris = torch.exp(-r_iris / 0.28) * 1.1
    total = streak_core + streak_halo + iris
    rgb = e.color_ramp(total, PAL_ANAMORPHIC)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_16(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """16: Multi-Streak Fan (4 Angles Sweeping in Parallax)."""
    t = f / FPS
    angles = [-0.31, -0.42, -0.52, -0.63]
    offsets = [-0.35, -0.10, 0.15, 0.40]
    total = torch.zeros_like(e.X)
    for i, (ang, off) in enumerate(zip(angles, offsets)):
        spd = 1.0 + i * 0.3
        drift = 0.08 * math.sin(t * spd + i)
        d = torch.abs(e.Y - (off + drift - e.X * math.tan(ang)))
        beam = torch.exp(-(d / 0.045)**2) * 0.95 + torch.exp(-d / 0.18) * 0.65
        total += beam
    rgb = e.color_ramp(total * 0.75, PAL_ANAMORPHIC)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_17(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """17: Keyhole Aperture Framing Boiling Core."""
    t = f / FPS
    r_core = torch.sqrt(e.X**2 * 1.1 + e.Y**2 * 1.4)
    flood = torch.exp(-r_core * 0.9) * 1.45 * (0.85 + 0.25 * e.turb(e.X * 2.5, e.Y * 2.5, t * 1.2))
    # Keyhole super-ellipse boundary
    key_r = 0.65 + 0.12 * math.sin(t * 1.3)
    turb_edge = e.turb(e.X * 3.5, e.Y * 3.5, t * 0.9) * 0.08
    r_key = torch.sqrt(e.X**2 + e.Y**2 * 1.3) + turb_edge
    mask = torch.sigmoid((key_r - r_key) * 10.0)
    rim = torch.exp(-torch.abs(r_key - key_r) * 11.0) * 1.4
    total = flood * mask + rim * 0.75
    rgb = e.color_ramp(total, PAL_MOLTEN)
    grain = (torch.rand_like(total) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_18(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """18: 4-Wedge Hourglass Diamond Aperture."""
    t = f / FPS
    back_r = torch.sqrt(e.X**2 * 1.1 + e.Y**2 * 1.5)
    flood = torch.exp(-back_r * 0.95) * 1.4 * (0.85 + 0.30 * e.turb(e.X * 2.5, e.Y * 2.5, t * 1.3))
    aperture_w = 0.85 + 0.20 * math.sin(t * 1.4)
    aperture_h = 0.55 + 0.15 * math.cos(t * 1.2)
    warp = e.turb(e.X * 4.0, e.Y * 4.0, t * 0.9) * 0.12
    aperture_dist = ((torch.abs(e.X) + warp) / aperture_w)**2.4 + ((torch.abs(e.Y) + warp) / aperture_h)**2.4
    shutter_matte = torch.sigmoid((1.0 - aperture_dist) * 6.5)
    rim = torch.exp(-torch.abs(aperture_dist - 1.0) * 8.0) * 1.5
    light = flood * shutter_matte + rim * 0.65
    rgb = e.color_ramp(light, PAL_MOLTEN)
    grain = (torch.rand_like(light) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_19(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """19: Low Horizon Molten Caldera Rising."""
    t = f / FPS
    # Horizon at Y ~ 0.7 (bottom of screen)
    y_horiz = 0.75 - 0.15 * math.sin(t * 1.1)
    disp = e.turb(e.X * 2.0, e.Y * 2.0, t * 1.2) * 0.28
    dy = torch.clamp((e.Y + disp) - y_horiz, -2.0, 1.0)
    # Heat billows upward (negative dy is above horizon)
    heat = torch.exp(dy * 1.6) * 1.4
    # Convective heat plumes
    plume = e.turb(e.X * 3.5, (e.Y - t * 0.6) * 3.5, t * 1.0) * 0.35
    heat = heat * (0.8 + plume)
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_20(e: GPUShaderEngine, f: int) -> torch.Tensor:
    """20: Floating Bokeh Cloud (3 Orbiting Plasma Orbs)."""
    t = f / FPS
    # Orb 1 (top-left)
    o1x = -0.65 + 0.20 * math.sin(t * 1.1)
    o1y = -0.35 + 0.18 * math.cos(t * 0.9)
    # Orb 2 (top-right)
    o2x = 0.70 + 0.22 * math.cos(t * 1.2)
    o2y = -0.20 + 0.16 * math.sin(t * 1.0)
    # Orb 3 (bottom-center)
    o3x = 0.05 + 0.25 * math.sin(t * 0.95 + 1.5)
    o3y = 0.45 + 0.15 * math.cos(t * 1.3)
    disp = e.turb(e.X * 2.0, e.Y * 2.0, t * 0.8) * 0.2
    r1 = torch.sqrt((e.X + disp - o1x)**2 + (e.Y + disp - o1y)**2 * 1.3)
    r2 = torch.sqrt((e.X + disp - o2x)**2 * 1.2 + (e.Y + disp - o2y)**2)
    r3 = torch.sqrt((e.X + disp - o3x)**2 * 1.1 + (e.Y + disp - o3y)**2 * 1.2)
    heat = torch.exp(-r1 * 1.6) * 1.1 + torch.exp(-r2 * 1.7) * 0.95 + torch.exp(-r3 * 1.8) * 0.9
    rgb = e.color_ramp(heat, PAL_MOLTEN)
    grain = (torch.rand_like(heat) - 0.5) * 0.025
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


ALL_PRESETS: Dict[str, Tuple[str, Callable[[GPUShaderEngine, int], torch.Tensor], str]] = {
    "01": ("cinematic_back_01.mp4", f_01, "01 Warm Corner Bloom / Film Leak"),
    "02": ("cinematic_back_02.mp4", f_02, "02 Dual Asymmetric Blobs"),
    "03": ("cinematic_back_03.mp4", f_03, "03 Molten Organic Film Burn"),
    "04": ("cinematic_back_04.mp4", f_04, "04 Diagonal Light Streak (-25 deg)"),
    "05": ("cinematic_back_05.mp4", f_05, "05 12-Ray Volumetric Burst"),
    "06": ("cinematic_back_06.mp4", f_06, "06 GlowPath Anamorphic Sweep"),
    "07": ("cinematic_back_07.mp4", f_07, "07 Twin Angled Light Beams"),
    "08": ("cinematic_back_08.mp4", f_08, "08 S-Curve Undulating Ribbon"),
    "09": ("cinematic_back_09.mp4", f_09, "09 Celestial Sun Rays (Top-Left)"),
    "10": ("cinematic_back_10.mp4", f_10, "10 Center-Stage Golden Film Burn"),
    "11": ("cinematic_back_11.mp4", f_11, "11 Celestial Starburst (32 Rays)"),
    "12": ("cinematic_back_12.mp4", f_12, "12 Horizontal Letterbox Optical Slit"),
    "13": ("cinematic_back_13.mp4", f_13, "13 Vertical Right Edge Burn"),
    "14": ("cinematic_back_14.mp4", f_14, "14 Diagonal Dark Wedge Divide"),
    "15": ("cinematic_back_15.mp4", f_15, "15 Horizontal Anamorphic Flare Streak"),
    "16": ("cinematic_back_16.mp4", f_16, "16 Multi-Streak Fan (4 Angles)"),
    "17": ("cinematic_back_17.mp4", f_17, "17 Keyhole Aperture"),
    "18": ("cinematic_back_18.mp4", f_18, "18 4-Wedge Hourglass Diamond Aperture"),
    "19": ("cinematic_back_19.mp4", f_19, "19 Low Horizon Caldera"),
    "20": ("cinematic_back_20.mp4", f_20, "20 Floating Bokeh Cloud (3 Orbs)"),
}


# ==============================================================================
# Rendering & Drive Upload Pipeline
# ==============================================================================

def render_preset(key: str, engine: GPUShaderEngine, out_dir: Path) -> Path:
    filename, func, title = ALL_PRESETS[key]
    out_path = out_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    t0 = time.time()
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", "18",
        "-b:v", "16M",
        "-maxrate", "24M",
        "-bufsize", "32M",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path)
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    
    for f in range(TOTAL_FRAMES):
        frame_tensor = func(engine, f)
        proc.stdin.write(frame_tensor.cpu().numpy().tobytes())
        
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", errors="ignore")
    proc.wait()
    
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error on {filename}: {stderr}")
        
    elapsed = time.time() - t0
    print(f"  ✓ [{key}/20] {filename} rendered in {elapsed:.2f}s ({TOTAL_FRAMES / elapsed:.1f} FPS)")
    return out_path


def upload_videos(videos: List[Path], folder_id: str) -> Dict[str, Any]:
    print(f"\n[Drive Upload] Uploading {len(videos)} videos to folder: {folder_id}...")
    manifest = {}
    
    for v in videos:
        cmd = [
            str(DRIVE_UPLOAD_BIN),
            "-credentials", str(CREDS_FILE),
            "-token", str(TOKEN_FILE),
            "-folder", folder_id,
            "-file", str(v)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = {}
            for token_part in res.stdout.strip().split():
                if "=" in token_part:
                    k, val = token_part.split("=", 1)
                    data[k] = val
            file_id = data.get("id")
            manifest[v.name] = {
                "id": file_id,
                "link": data.get("link", f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"),
                "bytes": int(data.get("bytes", v.stat().st_size)),
                "sha256": data.get("sha256"),
                "name": v.name
            }
            print(f"  ✓ {v.name} -> {manifest[v.name]['link']}")
        else:
            print(f"  ✗ Failed {v.name}: {res.stderr}")
            
    manifest_path = OUT_DIR / "upload_manifest_20x.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Render 20 cinematic background videos on GPU.")
    parser.add_argument("--keys", nargs="+", default=[f"{i:02d}" for i in range(1, 21)])
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Initializing GPUShaderEngine on {device} ({torch.cuda.get_device_name(0)})...")
    engine = GPUShaderEngine(WIDTH, HEIGHT, device=device)
    
    t_start = time.time()
    rendered = []
    print(f"\n[GPU Render] Rendering {len(args.keys)} presets (1080p, 30fps, 4s = 120 frames each)...")
    for k in args.keys:
        out_file = render_preset(k, engine, OUT_DIR)
        rendered.append(out_file)
        
    t_render = time.time() - t_start
    print(f"\n[Done Rendering] All {len(rendered)} videos rendered in {t_render:.2f}s ({t_render / len(rendered):.2f}s/video)!")
    
    if not args.no_upload:
        upload_videos(rendered, args.drive_folder)
        
    print(f"\n[Success] Complete suite delivered.")


if __name__ == "__main__":
    main()
