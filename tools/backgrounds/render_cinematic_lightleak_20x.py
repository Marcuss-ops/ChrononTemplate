#!/usr/bin/env python3
"""Chronon Cinematic Light Leaks - Complete 20-Preset GPU Analog Suite (RTX A4000 + NVENC).

Pivots from procedural/sci-fi graphics back to true analog optical light leaks:
  - Oversized light fields (1.5x - 4x viewport), 60-80% off-screen.
  - Authentic thermal decay: white-hot core smoothly blending into saturated yellow -> amber -> crimson haze.
  - Low-frequency organic turbulence (k ~ 0.5..1.5), eliminating high-frequency lightning/sparks.
  - Non-uniform, asymmetrical optical flares and wide exposure bands (not vector strokes).
  - Living kinetic motion via macro drift, mask warping, and exposure breathing.

Presets 01 to 20:
  01: Warm Upper-Left Corner Bloom / Film Burn
  02: Dual Asymmetric Blobs in Antiphase
  03: Molten Organic Film Burn & Soot Occluder
  04: Diagonal Anamorphic Exposure Band (-25 deg)
  05: 10-Ray Volumetric Optical Burst
  06: Anamorphic Exposure Band Sweep
  07: Twin Angled Exposure Bands in Parallax
  08: S-Curve Undulating Luminous Exposure Wave
  09: Top-Left Celestial Sun Rays & Dust
  10: Center-Stage Boiling Molten Core
  11: Dirty Asymmetrical Optical Starburst (14 Rays)
  12: Horizontal Letterbox Optical Slit Aperture
  13: Vertical Right Edge Burn (Sprocket Leak)
  14: Organic Lobe Divide & Underglow (Subtractive Boundary)
  15: Horizontal Anamorphic Flare Streak & Iris
  16: Multi-Streak Optical Fan (4 Angles)
  17: Keyhole Aperture Film Burn Framing
  18: 4-Wedge Hourglass Shutter Leak
  19: Low Horizon Molten Caldera
  20: Floating Soft Optical Bokeh Orbs (3 Discs)

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

import cv2
import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_lightleaks_20x_gpu"
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
# GPU Vectorized Optical Shader Engine
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
        
        # Smooth low-frequency wave banks for organic fluid lobes (k ~ 0.5..4.0)
        torch.manual_seed(42)
        self.kx = torch.tensor([0.65, 1.35, 2.40, 4.20], device=self.device).view(4, 1, 1)
        self.ky = torch.tensor([0.55, 1.15, 2.10, 3.80], device=self.device).view(4, 1, 1)
        self.phases = (torch.rand(4, device=self.device) * 6.283).view(4, 1, 1)
        self.speeds = torch.tensor([0.75, 1.10, 1.50, 1.90], device=self.device).view(4, 1, 1)
        self.amps = torch.tensor([0.55, 0.28, 0.12, 0.05], device=self.device).view(4, 1, 1)

    def organic_turb(self, x: torch.Tensor, y: torch.Tensor, t: float, speed_mult: float = 1.0) -> torch.Tensor:
        """Smooth low-frequency organic turbulence tensor broadcast."""
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
# Authentic Kodak Analog Optical Palettes
# ==============================================================================

PAL_ANALOG_LEAK = [
    (0.00, (0.008, 0.004, 0.004)),  # Cinema Black
    (0.15, (0.160, 0.020, 0.008)),  # Deep Burnt Crimson Haze
    (0.35, (0.550, 0.065, 0.005)),  # Velvety Carmine Flame
    (0.55, (0.880, 0.280, 0.008)),  # Rich Fiery Orange
    (0.72, (1.000, 0.620, 0.025)),  # Deep Molten Amber
    (0.85, (1.000, 0.840, 0.120)),  # Solar Golden Yellow
    (0.94, (1.000, 0.950, 0.550)),  # Warm Specular Yellow
    (1.00, (1.000, 0.985, 0.880)),  # Warm White-Hot Peak
]


# ==============================================================================
# Presets 01 - 20 GPU Frame Evaluators
# ==============================================================================

def f_01(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """01: Warm Upper-Left Corner Bloom / Film Burn."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    cx = -1.40 + 0.95 * progress + 0.10 * math.sin(t * 1.8)
    cy = -0.90 + 0.55 * progress + 0.08 * math.cos(t * 1.6)
    
    warp = e.organic_turb(e.X * 0.9, e.Y * 0.9, t * 1.4) * 0.28
    r = torch.sqrt((e.X + warp - cx)**2 * 0.75 + (e.Y + warp - cy)**2 * 1.15)
    
    flicker = 1.0 + 0.18 * math.sin(t * 3.6) + 0.08 * math.cos(t * 7.2)
    raw = torch.exp(-r * 1.05) * 1.45 * flicker
    ambient = torch.exp(-r * 0.38) * 0.28
    
    intensity = 1.0 - torch.exp(-(raw + ambient) * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_02(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """02: Dual Asymmetric Blobs in Antiphase."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Blob 1 (top-right orbiting)
    b1_x = 1.30 - 0.70 * progress + 0.12 * math.cos(t * 1.7)
    b1_y = -0.75 + 0.40 * progress + 0.10 * math.sin(t * 1.5)
    # Blob 2 (bottom-left orbiting)
    b2_x = -1.25 + 0.65 * progress + 0.10 * math.sin(t * 1.6)
    b2_y = 0.80 - 0.45 * progress + 0.08 * math.cos(t * 1.8)
    
    warp = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 1.3) * 0.25
    r1 = torch.sqrt((e.X + warp - b1_x)**2 * 0.85 + (e.Y + warp - b1_y)**2 * 1.15)
    r2 = torch.sqrt((e.X + warp - b2_x)**2 * 1.10 + (e.Y + warp - b2_y)**2 * 0.90)
    
    flicker1 = 1.0 + 0.15 * math.sin(t * 3.4)
    flicker2 = 1.0 + 0.15 * math.cos(t * 3.9)
    raw = torch.exp(-r1 * 1.10) * 1.15 * flicker1 + torch.exp(-r2 * 1.15) * 1.05 * flicker2
    ambient = (torch.exp(-r1 * 0.40) + torch.exp(-r2 * 0.40)) * 0.16
    
    intensity = 1.0 - torch.exp(-(raw + ambient) * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r1) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_03(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """03: Molten Organic Film Burn & Soot Occluder."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx_light = -1.35 + 1.10 * progress
    cy_light = -0.85 + 0.65 * progress + 0.10 * math.sin(t * 2.0)
    
    warp_x = e.organic_turb(e.X * 0.9, e.Y * 0.9, t * 1.5) * 0.30
    warp_y = e.organic_turb((e.X + 2.0) * 0.9, (e.Y - 1.5) * 0.9, t * 1.3) * 0.30
    Xw, Yw = e.X + warp_x, e.Y + warp_y
    
    dx_l, dy_l = Xw - cx_light, Yw - cy_light
    r_light = torch.sqrt(dx_l**2 * 0.75 + dy_l**2 * 1.20)
    flicker = 1.0 + 0.18 * math.sin(t * 3.8) + 0.08 * math.cos(t * 7.5)
    raw_light = torch.exp(-r_light * 1.10) * 1.45 * flicker
    ambient = torch.exp(-r_light * 0.40) * 0.28
    
    cx_soot = 0.90 - 0.85 * progress
    cy_soot = 0.60 - 0.55 * progress + 0.10 * math.cos(t * 1.8)
    dx_s, dy_s = Xw - cx_soot, Yw - cy_soot
    r_soot = torch.sqrt(dx_s**2 * 1.1 + dy_s**2 * 0.90)
    soot_edge = 0.85 + 0.15 * math.sin(t * 1.6)
    soot_matte = torch.sigmoid((r_soot - soot_edge) * 3.2)
    
    total_raw = raw_light * (0.15 + 0.85 * soot_matte) + ambient
    intensity = 1.0 - torch.exp(-total_raw * 1.25)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r_light) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_04(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """04: Diagonal Anamorphic Exposure Band (-25 deg)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_center = 0.75 - 1.50 * progress
    tilt = 0.466  # tan(25 deg)
    wave = 0.18 * torch.sin(e.X * 1.5 + t * 2.5) + 0.08 * torch.cos(e.X * 3.0 - t * 2.0)
    dist = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    
    pulse = 1.0 + 0.18 * torch.sin(t * 3.5 + e.X * 1.8)
    core = torch.exp(-(dist / 0.32)**2) * 0.95 * pulse
    halo = torch.exp(-dist / 0.65) * 0.60
    wash = torch.exp(-dist / 1.50) * 0.28
    
    disp = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 1.2) * 0.08
    raw = (core + halo + wash) * (0.94 + disp)
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(dist) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_05(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """05: 10-Ray Volumetric Optical Burst."""
    t = f / FPS
    cx = 0.15 * math.sin(t * 0.8)
    cy = 0.10 * math.cos(t * 0.9)
    dx, dy = e.X - cx, e.Y - cy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.12
    
    turb_val = e.organic_turb(e.X * 1.5, e.Y * 1.5, t * 1.0) * 0.18
    # 10 wide irregular rays
    rays = (torch.cos((theta + turb_val) * 10.0) * 0.5 + 0.5)**3.5
    rays_decay = rays / (1.0 + (r * 1.6)**1.2) * 0.65
    
    flicker = 1.0 + 0.12 * math.sin(t * 3.5)
    core = torch.exp(-(r / 0.22)**2) * 1.25 * flicker
    halo = torch.exp(-r / 0.70) * 0.60
    ambient = torch.exp(-r / 1.8) * 0.25
    
    raw = core + halo + rays_decay + ambient
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_06(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """06: Anamorphic Exposure Band Sweep."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_center = 0.80 - 1.60 * progress
    tilt = 0.36 + 0.06 * math.sin(t * 1.8)
    wave = 0.20 * torch.sin(e.X * 1.4 + t * 2.8) + 0.10 * torch.cos(e.X * 2.8 - t * 2.2)
    dist = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    
    pulse = 1.0 + 0.20 * torch.sin(t * 3.8 + e.X * 1.6)
    core = torch.exp(-(dist / 0.35)**2) * 0.95 * pulse
    halo = torch.exp(-dist / 0.70) * 0.65
    wash = torch.exp(-dist / 1.60) * 0.30
    
    disp = e.organic_turb(e.X * 1.2, e.Y * 1.2, t * 1.4) * 0.08
    raw = (core + halo + wash) * (0.94 + disp)
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(dist) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_07(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """07: Twin Angled Exposure Bands in Parallax."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    tilt = 0.36
    sep = 0.40 + 0.08 * math.sin(t * 1.6)
    y_center = 0.60 - 1.20 * progress
    
    w1 = 0.14 * torch.sin(e.X * 1.6 + t * 2.4)
    w2 = 0.14 * torch.cos(e.X * 1.6 - t * 2.1)
    d1 = torch.abs(e.Y - (y_center - sep - e.X * tilt + w1))
    d2 = torch.abs(e.Y - (y_center + sep - e.X * tilt + w2))
    
    b1 = torch.exp(-(d1 / 0.30)**2) * 0.85 + torch.exp(-d1 / 0.65) * 0.50
    b2 = torch.exp(-(d2 / 0.30)**2) * 0.80 + torch.exp(-d2 / 0.65) * 0.45
    wash = torch.exp(-torch.min(d1, d2) / 1.50) * 0.28
    
    raw = b1 + b2 + wash
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_08(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """08: S-Curve Undulating Luminous Exposure Wave."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_center = 0.65 - 1.30 * progress
    s_curve = 0.35 * torch.sin(e.X * 1.3 + t * 2.0) + 0.15 * torch.sin(e.X * 2.8 - t * 2.6)
    dist = torch.abs(e.Y - (y_center + s_curve))
    
    pulse = 1.0 + 0.20 * torch.sin(e.X * 1.5 - t * 3.2)
    core = torch.exp(-(dist / 0.36)**2) * 0.95 * pulse
    halo = torch.exp(-dist / 0.75) * 0.65
    wash = torch.exp(-dist / 1.65) * 0.30
    
    raw = core + halo + wash
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(dist) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_09(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """09: Top-Left Celestial Sun Rays & Dust."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    ox = -1.45 + 0.40 * progress + 0.10 * math.sin(t * 1.2)
    oy = -0.95 + 0.25 * progress + 0.08 * math.cos(t * 1.3)
    dx, dy = e.X - ox, e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx) - t * 0.08
    
    turb_val = e.organic_turb(e.X * 1.3, e.Y * 1.3, t * 1.1) * 0.18
    rays = (torch.cos((theta + turb_val) * 11.0) * 0.5 + 0.5)**3.8
    rays_decay = rays / (1.0 + (r * 1.4)**1.2) * 0.70
    
    sun = torch.exp(-r / 0.45) * 1.25 * (1.0 + 0.10 * math.sin(t * 3.0))
    halo = torch.exp(-r / 1.10) * 0.65
    ambient = torch.exp(-r / 2.2) * 0.30
    
    raw = sun + halo + rays_decay + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_10(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """10: Center-Stage Boiling Molten Core."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx = -0.30 + 0.60 * progress + 0.12 * math.sin(t * 1.4)
    cy = 0.10 * math.cos(t * 1.6)
    
    disp = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 1.2) * 0.28
    r = torch.sqrt((e.X + disp - cx)**2 * 1.0 + (e.Y + disp - cy)**2 * 1.2)
    
    flicker = 1.0 + 0.16 * math.sin(t * 3.6)
    heat = torch.exp(-r * 1.05) * 1.40 * flicker
    ambient = torch.exp(-r * 0.35) * 0.30
    
    raw = heat + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(heat) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_11(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """11: Dirty Asymmetrical Optical Starburst (14 Rays)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    ox = -0.75 + 0.65 * progress + 0.12 * math.sin(t * 1.5)
    oy = -0.50 + 0.30 * progress + 0.10 * math.cos(t * 1.4)
    dx, dy = e.X - ox, e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx)
    
    ang_turb = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 1.2) * 0.18
    theta_w = theta - t * 0.35 + ang_turb
    
    ray_angles = torch.tensor([
        -2.75, -2.10, -1.45, -0.90, -0.35, 0.15, 0.60, 
         1.05,  1.55,  1.95,  2.40,  2.85, 3.10, -0.65
    ], device=e.device)
    ray_widths = torch.tensor([
        0.06, 0.14, 0.04, 0.18, 0.08, 0.04, 0.12,
        0.09, 0.20, 0.05, 0.11, 0.07, 0.14, 0.08
    ], device=e.device)
    ray_amps = torch.tensor([
        0.90, 0.50, 1.10, 0.40, 1.00, 0.35, 0.80,
        0.95, 0.40, 0.85, 0.65, 0.80, 0.50, 0.70
    ], device=e.device)
    
    rays_field = torch.zeros_like(r)
    for ang, w_ang, a_ang in zip(ray_angles, ray_widths, ray_amps):
        d_th = torch.remainder(theta_w - ang + math.pi, 2 * math.pi) - math.pi
        ray_profile = torch.exp(-(d_th / w_ang)**2) * a_ang
        rays_field += ray_profile
        
    rays_decay = rays_field / (1.0 + (r * 1.8)**1.4) * 0.70
    flicker = 1.0 + 0.16 * math.sin(t * 4.0) + 0.08 * math.cos(t * 8.2)
    core = torch.exp(-(r / 0.18)**2) * 1.25 * flicker
    halo = torch.exp(-r / 0.65) * 0.60
    ambient = torch.exp(-r / 1.8) * 0.25
    
    raw = core + halo + rays_decay + ambient
    intensity = 1.0 - torch.exp(-raw * 1.40)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_12(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """12: Horizontal Letterbox Optical Slit Aperture."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    d_slit = torch.abs(e.Y)
    slit = torch.exp(-(d_slit / 0.32)**2) * 1.15 + torch.exp(-d_slit / 0.80) * 0.60
    
    bar_y = 0.65 + 0.10 * math.sin(t * 1.5)
    turb_bar = e.organic_turb(e.X * 1.3, e.Y * 1.3, t * 1.1) * 0.12
    mask = torch.sigmoid((bar_y - (d_slit + turb_bar)) * 4.5)
    rim = torch.exp(-torch.abs(d_slit - bar_y) * 4.0) * 0.75
    
    raw = slit * mask + rim + 0.15
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_13(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """13: Vertical Right Edge Burn (Sprocket Leak)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx = 1.65 - 0.40 * progress + 0.10 * math.sin(t * 1.5)
    disp = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 1.3) * 0.28
    r = torch.sqrt((e.X + disp - cx)**2 * 1.3 + e.Y**2 * 0.75)
    
    flicker = 1.0 + 0.18 * math.sin(t * 3.4)
    heat = torch.exp(-r * 0.95) * 1.45 * flicker
    ambient = torch.exp(-r * 0.35) * 0.28
    
    raw = heat + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(heat) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_14(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """14: Organic Lobe Divide & Underglow (Subtractive Boundary)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Smooth organic divide: zero lightning, zero electric sparks!
    r_under = torch.sqrt(e.X**2 * 0.75 + e.Y**2 * 1.1)
    under = torch.exp(-r_under * 0.75) * 1.35 * (1.0 + 0.12 * math.sin(t * 2.8))
    
    tilt = 0.50
    warp_edge = e.organic_turb(e.X * 0.9, e.Y * 0.9, t * 1.2) * 0.25
    wedge_dist = torch.abs(e.Y - e.X * tilt) + warp_edge
    wedge_w = 0.40 + 0.12 * math.sin(t * 1.5)
    
    wedge_matte = torch.sigmoid((wedge_dist - wedge_w) * 3.5)
    rim_bloom = torch.exp(-torch.abs(wedge_dist - wedge_w) * 4.0) * 0.75
    ambient = torch.exp(-r_under * 0.35) * 0.25
    
    raw = under * wedge_matte + rim_bloom + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_15(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """15: Horizontal Anamorphic Flare Streak & Iris."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_center = 0.15 * math.sin(t * 1.4)
    wave = 0.06 * torch.sin(e.X * 1.8 + t * 2.5)
    dy = torch.abs(e.Y - (y_center + wave))
    
    streak_core = torch.exp(-(dy / 0.15)**2) * 0.95
    streak_halo = torch.exp(-dy / 0.55) * 0.65
    
    cx = -0.50 + 1.00 * progress
    dx = e.X - cx
    r_iris = torch.sqrt(dx**2 + (e.Y - y_center)**2 * 1.5)
    iris = torch.exp(-r_iris / 0.45) * 0.90
    ambient = torch.exp(-dy / 1.50) * 0.25
    
    raw = streak_core + streak_halo + iris + ambient
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_16(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """16: Multi-Streak Optical Fan (4 Angles)."""
    t = f / FPS
    angles = [-0.30, -0.42, -0.54, -0.65]
    offsets = [-0.40, -0.12, 0.15, 0.42]
    
    total_raw = torch.zeros_like(e.X)
    for i, (ang, off) in enumerate(zip(angles, offsets)):
        spd = 1.0 + i * 0.25
        drift = 0.12 * math.sin(t * spd + i * 1.2)
        d = torch.abs(e.Y - (off + drift - e.X * math.tan(ang)))
        beam = torch.exp(-(d / 0.28)**2) * 0.65 + torch.exp(-d / 0.65) * 0.40
        total_raw += beam
        
    ambient = torch.exp(-torch.abs(e.Y) / 1.5) * 0.25
    raw = total_raw * 0.75 + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_17(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """17: Keyhole Aperture Film Burn Framing."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx = -0.20 + 0.40 * progress
    cy = 0.08 * math.cos(t * 1.4)
    r_core = torch.sqrt((e.X - cx)**2 * 0.95 + (e.Y - cy)**2 * 1.25)
    flicker = 1.0 + 0.16 * math.sin(t * 3.6)
    flood = torch.exp(-r_core * 0.80) * 1.45 * flicker
    
    key_r = 0.75 + 0.12 * math.sin(t * 1.4)
    turb_edge = e.organic_turb(e.X * 1.2, e.Y * 1.2, t * 1.1) * 0.15
    r_key = torch.sqrt(e.X**2 + e.Y**2 * 1.25) + turb_edge
    mask = torch.sigmoid((key_r - r_key) * 3.8)
    rim = torch.exp(-torch.abs(r_key - key_r) * 4.0) * 0.80
    ambient = torch.exp(-r_core * 0.35) * 0.25
    
    raw = flood * mask + rim + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_18(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """18: 4-Wedge Hourglass Shutter Leak."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx_back = -0.25 + 0.50 * progress + 0.12 * math.sin(t * 1.6)
    cy_back = 0.08 * math.cos(t * 1.4)
    r_back = torch.sqrt((e.X - cx_back)**2 * 0.80 + (e.Y - cy_back)**2 * 1.15)
    flicker = 1.0 + 0.16 * math.sin(t * 3.5) + 0.08 * math.cos(t * 7.0)
    flood = torch.exp(-r_back * 0.75) * 1.35 * flicker
    
    waist_x = 0.60 + 0.16 * math.sin(t * 1.8)
    waist_y = 0.48 + 0.12 * math.cos(t * 1.5)
    warp = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 1.4) * 0.15
    
    aperture_dist = ((e.X / (waist_x + 0.55 * e.Y**2))**2 + (e.Y / (waist_y + 0.45 * e.X**2))**2) * (1.0 + warp)
    shutter_matte = torch.sigmoid((1.15 - aperture_dist) * 3.5)
    rim_bloom = torch.exp(-torch.abs(aperture_dist - 1.0) * 3.5) * 0.85
    ambient = torch.exp(-r_back * 0.35) * 0.25
    
    raw = flood * shutter_matte + rim_bloom + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r_back) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_19(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """19: Low Horizon Molten Caldera."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_horiz = 0.85 - 0.25 * math.sin(t * 1.3)
    disp = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 1.3) * 0.25
    dy = torch.clamp((e.Y + disp) - y_horiz, -2.0, 1.0)
    heat = torch.exp(dy * 1.5) * 1.45 * (1.0 + 0.15 * math.sin(t * 3.2))
    ambient = torch.exp(dy * 0.5) * 0.30
    
    raw = heat + ambient
    intensity = 1.0 - torch.exp(-raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(heat) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def f_20(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """20: Floating Soft Optical Bokeh Orbs (3 Discs)."""
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Orb 1 (drifts top-left to center)
    o1x = -0.75 + 0.45 * progress + 0.15 * math.sin(t * 1.3)
    o1y = -0.35 + 0.20 * math.cos(t * 1.1)
    # Orb 2 (drifts top-right to bottom)
    o2x = 0.70 - 0.35 * progress + 0.18 * math.cos(t * 1.4)
    o2y = -0.25 + 0.40 * progress + 0.14 * math.sin(t * 1.2)
    # Orb 3 (drifts bottom to center)
    o3x = 0.10 + 0.20 * math.sin(t * 1.2 + 1.5)
    o3y = 0.50 - 0.35 * progress + 0.12 * math.cos(t * 1.5)
    
    disp = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 1.0) * 0.18
    r1 = torch.sqrt((e.X + disp - o1x)**2 + (e.Y + disp - o1y)**2 * 1.1)
    r2 = torch.sqrt((e.X + disp - o2x)**2 * 1.1 + (e.Y + disp - o2y)**2)
    r3 = torch.sqrt((e.X + disp - o3x)**2 * 0.95 + (e.Y + disp - o3y)**2 * 1.05)
    
    # Soft bokeh discs with gentle Gaussian edge falloff
    orb1 = torch.exp(-(r1 / 0.45)**2) * 0.95
    orb2 = torch.exp(-(r2 / 0.50)**2) * 0.85
    orb3 = torch.exp(-(r3 / 0.40)**2) * 0.80
    ambient = (torch.exp(-r1 / 1.5) + torch.exp(-r2 / 1.5) + torch.exp(-r3 / 1.5)) * 0.12
    
    raw = orb1 + orb2 + orb3 + ambient
    intensity = 1.0 - torch.exp(-raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(raw) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


ALL_PRESETS: Dict[str, Tuple[str, Callable[[GPULightLeakEngine, int], torch.Tensor], str]] = {
    "01": ("cinematic_lightleak_01.mp4", f_01, "01 Warm Corner Bloom / Film Burn"),
    "02": ("cinematic_lightleak_02.mp4", f_02, "02 Dual Asymmetric Blobs"),
    "03": ("cinematic_lightleak_03.mp4", f_03, "03 Molten Organic Film Burn"),
    "04": ("cinematic_lightleak_04.mp4", f_04, "04 Diagonal Anamorphic Band (-25 deg)"),
    "05": ("cinematic_lightleak_05.mp4", f_05, "05 10-Ray Volumetric Optical Burst"),
    "06": ("cinematic_lightleak_06.mp4", f_06, "06 Anamorphic Exposure Band Sweep"),
    "07": ("cinematic_lightleak_07.mp4", f_07, "07 Twin Angled Exposure Bands"),
    "08": ("cinematic_lightleak_08.mp4", f_08, "08 S-Curve Undulating Exposure Wave"),
    "09": ("cinematic_lightleak_09.mp4", f_09, "09 Top-Left Celestial Sun Rays"),
    "10": ("cinematic_lightleak_10.mp4", f_10, "10 Center-Stage Boiling Molten Core"),
    "11": ("cinematic_lightleak_11.mp4", f_11, "11 Dirty Asymmetrical Optical Starburst"),
    "12": ("cinematic_lightleak_12.mp4", f_12, "12 Horizontal Letterbox Slit Aperture"),
    "13": ("cinematic_lightleak_13.mp4", f_13, "13 Vertical Right Edge Burn"),
    "14": ("cinematic_lightleak_14.mp4", f_14, "14 Organic Lobe Divide & Underglow"),
    "15": ("cinematic_lightleak_15.mp4", f_15, "15 Horizontal Anamorphic Flare Streak"),
    "16": ("cinematic_lightleak_16.mp4", f_16, "16 Multi-Streak Optical Fan (4 Angles)"),
    "17": ("cinematic_lightleak_17.mp4", f_17, "17 Keyhole Aperture Film Burn"),
    "18": ("cinematic_lightleak_18.mp4", f_18, "18 4-Wedge Hourglass Shutter Leak"),
    "19": ("cinematic_lightleak_19.mp4", f_19, "19 Low Horizon Molten Caldera"),
    "20": ("cinematic_lightleak_20.mp4", f_20, "20 Floating Soft Optical Bokeh Orbs"),
}


# ==============================================================================
# Rendering & Drive Upload Pipeline
# ==============================================================================

def render_preset(key: str, engine: GPULightLeakEngine, out_dir: Path) -> Path:
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
        "-b:v", "18M",
        "-maxrate", "24M",
        "-bufsize", "36M",
        "-pix_fmt", "yuv420p",
        str(out_path)
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    
    for f in range(TOTAL_FRAMES):
        with torch.no_grad():
            frame_tensor = func(engine, f)
            frame_np = frame_tensor.cpu().numpy()
        proc.stdin.write(frame_np.tobytes())
        
    proc.stdin.close()
    stderr = proc.stderr.read().decode(errors="replace")
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
    parser = argparse.ArgumentParser(description="Render 20 Cinematic Analog Light Leaks on GPU.")
    parser.add_argument("--keys", nargs="+", default=[f"{i:02d}" for i in range(1, 21)])
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Initializing GPULightLeakEngine on {device} ({torch.cuda.get_device_name(0)})...")
    engine = GPULightLeakEngine(WIDTH, HEIGHT, device=device)
    
    t_start = time.time()
    rendered = []
    print(f"\n[GPU Render] Rendering {len(args.keys)} analog light leak presets (1080p, 30fps, 4s = 120 frames each)...")
    for k in args.keys:
        out_file = render_preset(k, engine, OUT_DIR)
        rendered.append(out_file)
        
    t_render = time.time() - t_start
    print(f"\n[Done Rendering] All {len(rendered)} videos rendered in {t_render:.2f}s ({t_render / len(rendered):.2f}s/video)!")
    
    if not args.no_upload:
        upload_videos(rendered, args.drive_folder)


if __name__ == "__main__":
    main()
