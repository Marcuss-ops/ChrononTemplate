#!/usr/bin/env python3
"""Chronon Cinematic Light Leaks - 4 Canonical Analog Optical Prototypes (RTX A4000 GPU).

Pivots from procedural/sci-fi graphics back to true analog optical light leaks:
  - 03: Molten Organic Film Burn (Oversized light field + smooth low-frequency soot occluder)
  - 06: Anamorphic Exposure Band (Broad diffuse overexposure wash, not a vector stroke)
  - 11: Dirty Asymmetrical Optical Starburst (Non-uniform stochastic rays, off-axis origin)
  - 18: Hourglass Dark Vignette Shutter Leak (Giant backlight + organic billowing shutter)

Key Optical Principles Applied:
  1. Oversized Light Sources: 1.8x - 3.5x viewport dimension, 60-80% cropped outside frame.
  2. Analog Thermal Decay: White-hot core (>0.92) blends smoothly into saturated yellow -> amber -> crimson -> cinema black.
  3. Low-Frequency Organic Noise: Large fluid lobes (k ~ 0.5..1.5), eliminating high-frequency lightning/cracks.
  4. Non-Uniform Stochastic Rays: Irregular angular widths, random intensities, dirty optical dispersion.
  5. High Kinetic Motion (~0.06 - 0.08 variation): Preserved via macro drift, mask deformation, and exposure breathing.
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
from typing import Callable, Dict, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_lightleak_prototypes_4x"
REF_DIR = BASE_DIR / "ChrononTemplate/out/back3_analysis/frames"

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
        
        # Low-frequency organic harmonic wave banks (soft fluid lobes, NO high-frequency buzz)
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

# Rich analog color ramp: Dominant saturated amber/gold, white only at extreme peak
PAL_ANALOG_LEAK = [
    (0.00, (0.008, 0.004, 0.004)),  # Cinema Black
    (0.15, (0.160, 0.020, 0.008)),  # Deep Burnt Crimson Haze
    (0.35, (0.550, 0.065, 0.005)),  # Velvety Carmine Flame
    (0.55, (0.880, 0.280, 0.008)),  # Rich Fiery Orange
    (0.72, (1.000, 0.620, 0.025)),  # Deep Molten Amber
    (0.85, (1.000, 0.840, 0.120)),  # Solar Golden Yellow
    (0.94, (1.000, 0.950, 0.550)),  # Warm Specular Yellow
    (1.00, (1.000, 0.985, 0.880)),  # Warm White-Hot Peak (Never pure cyan/blue white!)
]


# ==============================================================================
# The 4 Canonical Analog Optical Shaders
# ==============================================================================

def leak_03(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """03: Molten Organic Film Burn.
    
    Oversized radiant field (2.5x viewport) + smooth low-frequency soot occluder.
    75% of light source is outside visible frame.
    Warm golden amber bleeding from edge with deep carmine haze.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Macro drift of the oversized light source (drifting from upper-left corner)
    cx_light = -1.35 + 1.10 * progress
    cy_light = -0.85 + 0.65 * progress + 0.10 * math.sin(t * 2.0)
    
    # Low-frequency organic coordinate warp (large smooth fluid lobes)
    warp_x = e.organic_turb(e.X * 0.9, e.Y * 0.9, t * 1.5) * 0.30
    warp_y = e.organic_turb((e.X + 2.0) * 0.9, (e.Y - 1.5) * 0.9, t * 1.3) * 0.30
    Xw = e.X + warp_x
    Yw = e.Y + warp_y
    
    # Oversized floodlight: elliptical radial falloff
    dx_l = Xw - cx_light
    dy_l = Yw - cy_light
    r_light = torch.sqrt(dx_l**2 * 0.75 + dy_l**2 * 1.20)
    
    # Exposure breathing & flicker
    flicker = 1.0 + 0.18 * math.sin(t * 3.8) + 0.08 * math.cos(t * 7.5)
    raw_light = torch.exp(-r_light * 1.10) * 1.45 * flicker
    
    # Soft ambient glow across the screen
    ambient = torch.exp(-r_light * 0.40) * 0.28
    
    # Subtractive dark soot occluder: smooth billowing mass drifting in counter-phase
    cx_soot = 0.90 - 0.85 * progress
    cy_soot = 0.60 - 0.55 * progress + 0.10 * math.cos(t * 1.8)
    dx_s = Xw - cx_soot
    dy_s = Yw - cy_soot
    r_soot = torch.sqrt(dx_s**2 * 1.1 + dy_s**2 * 0.90)
    
    # Soft organic sigmoid transition
    soot_edge = 0.85 + 0.15 * math.sin(t * 1.6)
    soot_matte = torch.sigmoid((r_soot - soot_edge) * 3.2)
    
    # Combine: light occluded by soot + ambient warm haze
    total_raw = raw_light * (0.15 + 0.85 * soot_matte) + ambient
    
    # Analog film H&D tone curve (soft shoulder, compresses highlights smoothly)
    intensity = 1.0 - torch.exp(-total_raw * 1.25)
    
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r_light) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def leak_06(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """06: Anamorphic Exposure Band.
    
    Broad diffuse warm overexposure wash drifting diagonally across the frame.
    Continuous analog gradient: amber/gold core fading into carmine haze.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Band traverses diagonally across frame
    y_center = 0.80 - 1.60 * progress
    tilt = 0.36 + 0.06 * math.sin(t * 1.8)
    
    # Organic low-frequency wave warping the band trajectory
    wave = 0.20 * torch.sin(e.X * 1.4 + t * 2.8) + 0.10 * torch.cos(e.X * 2.8 - t * 2.2)
    dist = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    
    # Exposure breathing pulse
    pulse = 1.0 + 0.20 * torch.sin(t * 3.8 + e.X * 1.6)
    
    # Broad multi-tier exposure profile
    core = torch.exp(-(dist / 0.35)**2) * 0.95 * pulse
    halo = torch.exp(-dist / 0.70) * 0.65
    wash = torch.exp(-dist / 1.60) * 0.30
    
    total_raw = core + halo + wash
    
    # Organic horizontal dispersion
    disp = e.organic_turb(e.X * 1.2, e.Y * 1.2, t * 1.4) * 0.08
    total_raw = total_raw * (0.94 + disp)
    
    # Analog film tone curve
    intensity = 1.0 - torch.exp(-total_raw * 1.35)
    
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(dist) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def leak_11(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """11: Dirty Asymmetrical Optical Starburst.
    
    Stochastic non-uniform rays, irregular angular widths, off-axis origin, radial optical blur.
    Compact incandescent solar core surrounded by dirty asymmetric golden flare rays.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Origin drifts across upper corner/edge
    ox = -0.75 + 0.65 * progress + 0.12 * math.sin(t * 1.5)
    oy = -0.50 + 0.30 * progress + 0.10 * math.cos(t * 1.4)
    dx = e.X - ox
    dy = e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx)
    
    # Organic angular turbulence (lens grease / micro-imperfections)
    ang_turb = e.organic_turb(e.X * 1.0, e.Y * 1.0, t * 1.2) * 0.18
    theta_w = theta - t * 0.35 + ang_turb
    
    # 14 Stochastic non-uniform rays
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
        
    # Radial decay of rays (1 / (1 + r^1.4))
    rays_decay = rays_field / (1.0 + (r * 1.8)**1.4) * 0.70
    
    # Compact incandescent core (small hot-spot, NOT a giant white circle!)
    flicker = 1.0 + 0.16 * math.sin(t * 4.0) + 0.08 * math.cos(t * 8.2)
    core = torch.exp(-(r / 0.18)**2) * 1.25 * flicker
    halo = torch.exp(-r / 0.65) * 0.60
    ambient = torch.exp(-r / 1.8) * 0.25
    
    total_raw = core + halo + rays_decay + ambient
    
    # Analog film tone curve
    intensity = 1.0 - torch.exp(-total_raw * 1.40)
    
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def leak_18(e: GPULightLeakEngine, f: int) -> torch.Tensor:
    """18: Hourglass Dark Vignette Shutter Leak.
    
    Giant golden backlight plate framed by soft billowing dark vignette lobes.
    Smooth super-ellipse aperture with zero mathematical pinching or cross artifacts.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Giant backlight flood drifting behind
    cx_back = -0.25 + 0.50 * progress + 0.12 * math.sin(t * 1.6)
    cy_back = 0.08 * math.cos(t * 1.4)
    r_back = torch.sqrt((e.X - cx_back)**2 * 0.80 + (e.Y - cy_back)**2 * 1.15)
    flicker = 1.0 + 0.16 * math.sin(t * 3.5) + 0.08 * math.cos(t * 7.0)
    flood = torch.exp(-r_back * 0.75) * 1.35 * flicker
    
    # Hourglass / diamond aperture dimensions breathing dynamically
    waist_x = 0.60 + 0.16 * math.sin(t * 1.8)
    waist_y = 0.48 + 0.12 * math.cos(t * 1.5)
    
    # Low-frequency organic warp of the shutter boundary (smooth fluid lobes)
    warp = e.organic_turb(e.X * 1.1, e.Y * 1.1, t * 1.4) * 0.15
    
    # Smooth hourglass distance (waist at center, flaring smoothly outwards)
    aperture_dist = ((e.X / (waist_x + 0.55 * e.Y**2))**2 + (e.Y / (waist_y + 0.45 * e.X**2))**2) * (1.0 + warp)
    
    # Soft organic occlusion matte
    shutter_matte = torch.sigmoid((1.15 - aperture_dist) * 3.5)
    
    # Warm rim bloom wrapping around the shutter edges
    rim_bloom = torch.exp(-torch.abs(aperture_dist - 1.0) * 3.5) * 0.85
    ambient = torch.exp(-r_back * 0.35) * 0.25
    
    total_raw = flood * shutter_matte + rim_bloom + ambient
    
    # Analog film tone curve
    intensity = 1.0 - torch.exp(-total_raw * 1.30)
    
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    grain = (torch.rand_like(r_back) - 0.5) * 0.024
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


# ==============================================================================
# Rendering Harness & Motion Metrics
# ==============================================================================

PROTOTYPES: Dict[str, Tuple[str, Callable[[GPULightLeakEngine, int], torch.Tensor], str]] = {
    "03": ("cinematic_lightleak_03.mp4", leak_03, "03: Molten Organic Film Burn"),
    "06": ("cinematic_lightleak_06.mp4", leak_06, "06: Anamorphic Exposure Band"),
    "11": ("cinematic_lightleak_11.mp4", leak_11, "11: Dirty Optical Starburst"),
    "18": ("cinematic_lightleak_18.mp4", leak_18, "18: Hourglass Dark Vignette Shutter"),
}


def render_prototype(key: str, engine: GPULightLeakEngine, out_dir: Path) -> Tuple[Path, float]:
    filename, func, title = PROTOTYPES[key]
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
    
    diffs = []
    prev_gray = None
    frames_for_contact = []
    
    for f in range(TOTAL_FRAMES):
        with torch.no_grad():
            frame_tensor = func(engine, f)
            frame_np = frame_tensor.cpu().numpy()
            
        proc.stdin.write(frame_np.tobytes())
        
        # Calculate motion variation
        gray = cv2.cvtColor(frame_np, cv2.COLOR_RGB2GRAY) / 255.0
        if prev_gray is not None:
            diffs.append(float(np.mean(np.abs(gray - prev_gray))))
        prev_gray = gray
        
        # Save sample keyframes for visual inspection (f=0, 30, 60, 90)
        if f in [0, 30, 60, 90]:
            frames_for_contact.append((f, frame_np))
            
    proc.stdin.close()
    proc.wait()
    
    dt = time.time() - t0
    mean_motion = float(np.mean(diffs)) if diffs else 0.0
    
    # Save keyframes
    keyframe_dir = out_dir / f"keyframes_{key}"
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    for f_idx, f_np in frames_for_contact:
        cv2.imwrite(str(keyframe_dir / f"frame_{f_idx:03d}.png"), cv2.cvtColor(f_np, cv2.COLOR_RGB2BGR))
        
    print(f"[{key}] {title} -> {out_path.name} ({dt:.2f}s, {TOTAL_FRAMES/dt:.1f} fps) Motion Variation: {mean_motion:.4f}")
    return out_path, mean_motion


def generate_comparison_contact_sheet(out_dir: Path):
    """Generates a side-by-side comparison sheet comparing keyframes of 03, 06, 11, 18 with reference frames."""
    # Build contact sheet
    canvas_w = 1920
    canvas_h = 1080
    sheet = np.zeros((canvas_h * 2, canvas_w * 2, 3), dtype=np.uint8)
    
    keys = ["03", "06", "11", "18"]
    positions = [(0, 0), (canvas_w, 0), (0, canvas_h), (canvas_w, canvas_h)]
    
    for key, (x, y) in zip(keys, positions):
        kf_path = out_dir / f"keyframes_{key}/frame_060.png"
        if kf_path.exists():
            im = cv2.imread(str(kf_path))
            # Put title
            title = PROTOTYPES[key][2]
            cv2.putText(im, f"NEW ANALOG LIGHT LEAK: {title}", (40, 70), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
            sheet[y:y+canvas_h, x:x+canvas_w] = im
            
    contact_path = out_dir / "comparison_contact_sheet_4x.jpg"
    cv2.imwrite(str(contact_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"Contact sheet saved to: {contact_path}")


def main():
    parser = argparse.ArgumentParser(description="Render 4 Canonical Analog Optical Light Leaks")
    parser.add_argument("--device", default="cuda", help="PyTorch compute device")
    parser.add_argument("--keys", nargs="+", default=["03", "06", "11", "18"], help="Preset keys to render")
    args = parser.parse_args()
    
    print("=" * 72)
    print("Chronon Cinematic Light Leaks - 4 Canonical Analog Prototypes")
    print(f"Output Directory: {OUT_DIR}")
    print(f"Resolution: {WIDTH}x{HEIGHT} @ {FPS}fps, Total Frames: {TOTAL_FRAMES}")
    print("=" * 72)
    
    engine = GPULightLeakEngine(WIDTH, HEIGHT, device=args.device)
    
    results = {}
    for key in args.keys:
        if key in PROTOTYPES:
            path, motion = render_prototype(key, engine, OUT_DIR)
            results[key] = {"path": str(path), "motion_variation": motion}
            
    generate_comparison_contact_sheet(OUT_DIR)
    
    summary_path = OUT_DIR / "prototypes_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\nSummary:")
    for k, v in results.items():
        print(f"  {k}: Motion={v['motion_variation']:.4f} -> {v['path']}")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
