#!/usr/bin/env python3
"""Chronon Cinematic Light Leaks - Sand Grain & Tactile Particulate Suite (RTX A4000 GPU).

Implements the modern trending aesthetic of tactile "sand grain / animated stipple / organic particulate":
  - Sand stipple gradient shading (risograph / sand dissolve)
  - Drifting dust motes & golden illuminated sand specks
  - Coarse tactile film emulsion grit boiling with the light leak
  - Solar wind particulate flow across anamorphic light beams

4 Distinct Studies:
  01: Sand Dissolve Film Burn (Tactile sand stipple falloff on molten leak)
  02: Golden Dust Motes in Beam (Floating particles illuminated by sweeping band)
  03: Coarse 35mm Sand Emulsion (Heavy organic dancing grit in solar flare)
  04: Solar Wind Sandstorm (Directional streaming sand particles in light wash)
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
from typing import Any, Callable, Dict, List, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate/out/cinematic_sand_grain_lightleaks"
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
# GPU Vectorized Sand & Particulate Shader Engine
# ==============================================================================

class GPUSandEngine:
    def __init__(self, width: int = 1920, height: int = 1080, device: str = "cuda"):
        self.w = width
        self.h = height
        self.device = torch.device(device)
        
        aspect = width / height
        y = torch.linspace(-1.0, 1.0, height, device=self.device)
        x = torch.linspace(-aspect, aspect, width, device=self.device)
        self.Y, self.X = torch.meshgrid(y, x, indexing="ij")
        
        # Harmonic turbulence wave banks
        torch.manual_seed(101)
        self.kx = torch.tensor([0.7, 1.4, 2.8, 5.2], device=self.device).view(4, 1, 1)
        self.ky = torch.tensor([0.6, 1.2, 2.5, 4.8], device=self.device).view(4, 1, 1)
        self.phases = (torch.rand(4, device=self.device) * 6.283).view(4, 1, 1)
        self.speeds = torch.tensor([0.8, 1.2, 1.6, 2.1], device=self.device).view(4, 1, 1)
        self.amps = torch.tensor([0.55, 0.28, 0.12, 0.05], device=self.device).view(4, 1, 1)

        # Pre-seed particle field for floating sand motes (500 distinct particles)
        num_motes = 600
        rng = torch.Generator(device=self.device)
        rng.manual_seed(2026)
        self.mote_x0 = (torch.rand(num_motes, device=self.device, generator=rng) * 2.0 - 1.0) * aspect * 1.2
        self.mote_y0 = (torch.rand(num_motes, device=self.device, generator=rng) * 2.0 - 1.0) * 1.2
        self.mote_vx = (torch.rand(num_motes, device=self.device, generator=rng) * 0.15 + 0.05)
        self.mote_vy = (torch.rand(num_motes, device=self.device, generator=rng) * 0.10 - 0.05)
        self.mote_radii = torch.rand(num_motes, device=self.device, generator=rng) * 0.008 + 0.003
        self.mote_brightness = torch.rand(num_motes, device=self.device, generator=rng) * 0.7 + 0.3

    def turb(self, x: torch.Tensor, y: torch.Tensor, t: float, speed_mult: float = 1.0) -> torch.Tensor:
        t_vec = t * self.speeds * speed_mult
        w = torch.sin(x.unsqueeze(0) * self.kx + y.unsqueeze(0) * self.ky + t_vec + self.phases)
        return (w * self.amps).sum(dim=0)

    def generate_sand_texture(self, f: int, scale: float = 1.0) -> torch.Tensor:
        """High-density animated sand grain with multi-frequency tactile grit."""
        # Temporal boil: changes each frame to simulate 24-30fps boiling grain
        rand_field = torch.rand_like(self.X)
        # Clumping sand filter: contrast enhancement on grain
        sand = (rand_field - 0.5) * 2.0
        # Multi-scale grit: add a second octave of micro-dots
        micro = (torch.rand_like(self.X) > 0.88).float() * (torch.rand_like(self.X) * 0.6 + 0.4)
        return sand * 0.12 * scale + micro * 0.18 * scale

    def render_sand_motes(self, t: float) -> torch.Tensor:
        """Render drifting floating sand / dust particles caught in light."""
        aspect = self.w / self.h
        # Update mote positions with cyclical wrap
        mx = torch.remainder(self.mote_x0 + self.mote_vx * t + aspect * 1.5, aspect * 3.0) - aspect * 1.5
        my = torch.remainder(self.mote_y0 + self.mote_vy * t + 1.5, 3.0) - 1.5
        
        # Grid-downsampled particle splat for fast GPU execution
        # Downsample coordinates to evaluate proximity
        field = torch.zeros_like(self.X)
        # We sample a subset of nearest motes or vectorized splatting
        # Fast vectorized distance check for active motes
        for i in range(0, len(mx), 12):  # Batch 50 motes at a time
            dx = self.X.unsqueeze(0) - mx[i:i+12].view(-1, 1, 1)
            dy = self.Y.unsqueeze(0) - my[i:i+12].view(-1, 1, 1)
            r2 = dx**2 + dy**2
            sig2 = (self.mote_radii[i:i+12].view(-1, 1, 1))**2
            bright = self.mote_brightness[i:i+12].view(-1, 1, 1)
            mote_contrib = torch.exp(-r2 / (2.0 * sig2)) * bright
            field += mote_contrib.sum(dim=0)
            
        return torch.clamp(field, 0.0, 1.5)

    def color_ramp(self, intensity: torch.Tensor, palette: list[tuple[float, tuple[float, float, float]]]) -> torch.Tensor:
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
# The 4 Sand Grain Light Leak Studies
# ==============================================================================

def sand_study_01(e: GPUSandEngine, f: int) -> torch.Tensor:
    """Study 01: Sand Dissolve Film Burn.
    
    Tactile sand stipple falloff on a molten corner film burn.
    Light dissolves into dancing sand granules (risograph / stipple shading).
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    cx = -1.35 + 1.10 * progress
    cy = -0.85 + 0.65 * progress + 0.10 * math.sin(t * 2.0)
    
    warp_x = e.turb(e.X * 0.9, e.Y * 0.9, t * 1.5) * 0.30
    warp_y = e.turb((e.X + 2.0) * 0.9, (e.Y - 1.5) * 0.9, t * 1.3) * 0.30
    Xw, Yw = e.X + warp_x, e.Y + warp_y
    
    dx_l, dy_l = Xw - cx, Yw - cy
    r_light = torch.sqrt(dx_l**2 * 0.75 + dy_l**2 * 1.20)
    raw_light = torch.exp(-r_light * 1.10) * 1.50 * (1.0 + 0.15 * math.sin(t * 3.8))
    ambient = torch.exp(-r_light * 0.40) * 0.28
    
    # Sand Stipple Modulation:
    # Modulate the light field with high-density sand texture
    sand = e.generate_sand_texture(f, scale=1.35)
    
    # Tactile stipple dissolve: creates that sandy, particulate edge falloff
    stippled_light = raw_light + sand * (0.35 + raw_light * 0.45)
    total_raw = torch.clamp(stippled_light + ambient, 0.0, 2.5)
    
    intensity = 1.0 - torch.exp(-total_raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    
    # Surface sand grit overlay
    sand_overlay = (torch.rand_like(r_light) - 0.5) * 0.045
    return (torch.clamp(rgb + sand_overlay.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def sand_study_02(e: GPUSandEngine, f: int) -> torch.Tensor:
    """Study 02: Golden Dust Motes in Anamorphic Beam.
    
    Broad exposure sweep illuminating a swarm of floating, drifting sand/dust motes.
    Particles in the beam glow intensely like golden dust in sunlight.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    y_center = 0.80 - 1.60 * progress
    tilt = 0.36 + 0.06 * math.sin(t * 1.8)
    wave = 0.20 * torch.sin(e.X * 1.4 + t * 2.8) + 0.10 * torch.cos(e.X * 2.8 - t * 2.2)
    dist = torch.abs(e.Y - (y_center - e.X * tilt + wave))
    
    core = torch.exp(-(dist / 0.35)**2) * 0.95
    halo = torch.exp(-dist / 0.70) * 0.65
    wash = torch.exp(-dist / 1.60) * 0.30
    beam = core + halo + wash
    
    # Render drifting sand particles
    motes = e.render_sand_motes(t)
    
    # Particles caught in the beam light up brilliantly
    illuminated_motes = motes * (core * 2.2 + halo * 1.2 + 0.15)
    
    # Fine sand grain texture
    sand = e.generate_sand_texture(f, scale=0.85)
    
    total_raw = beam + illuminated_motes * 0.85 + sand * 0.12
    intensity = 1.0 - torch.exp(-total_raw * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    
    sand_grit = (torch.rand_like(dist) - 0.5) * 0.035
    return (torch.clamp(rgb + sand_grit.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def sand_study_03(e: GPUSandEngine, f: int) -> torch.Tensor:
    """Study 03: Coarse 35mm Sand Emulsion in Optical Starburst.
    
    Dirty asymmetrical starburst with heavy, boiling, tactile 35mm sand-grain emulsion.
    Gives a rich, retro, tactile documentary grit.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    ox = -0.75 + 0.65 * progress + 0.12 * math.sin(t * 1.5)
    oy = -0.50 + 0.30 * progress + 0.10 * math.cos(t * 1.4)
    dx, dy = e.X - ox, e.Y - oy
    r = torch.sqrt(dx**2 + dy**2)
    theta = torch.atan2(dy, dx)
    
    ang_turb = e.turb(e.X * 1.0, e.Y * 1.0, t * 1.2) * 0.18
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
        rays_field += torch.exp(-(d_th / w_ang)**2) * a_ang
        
    rays_decay = rays_field / (1.0 + (r * 1.8)**1.4) * 0.70
    core = torch.exp(-(r / 0.18)**2) * 1.25 * (1.0 + 0.15 * math.sin(t * 4.0))
    halo = torch.exp(-r / 0.65) * 0.60
    ambient = torch.exp(-r / 1.8) * 0.25
    burst = core + halo + rays_decay + ambient
    
    # Coarse 35mm sand emulsion: heavy, boiling granules
    sand_coarse = e.generate_sand_texture(f, scale=1.65)
    # The sand grain responds to exposure: denser and darker in shadows, incandescent in highlights
    burst_with_sand = burst * (1.0 + sand_coarse * 0.35) + sand_coarse * 0.08
    
    intensity = 1.0 - torch.exp(-burst_with_sand * 1.35)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    
    sand_grit = (torch.rand_like(r) - 0.5) * 0.055
    return (torch.clamp(rgb + sand_grit.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


def sand_study_04(e: GPUSandEngine, f: int) -> torch.Tensor:
    """Study 04: Solar Wind Sandstorm & Anamorphic Light Wash.
    
    Directional streaming sand particles blown across an intense golden exposure field.
    Cinematic dune/desert sunbeam look.
    """
    t = f / FPS
    progress = f / (TOTAL_FRAMES - 1)
    
    # Diagonal streaming wind coordinates
    wind_x = e.X + t * 0.85 + e.turb(e.X * 1.5, e.Y * 1.5, t * 1.5) * 0.15
    wind_y = e.Y - t * 0.25
    
    # Directional sand streaks
    sand_streaks = torch.sin(wind_x * 85.0 + wind_y * 35.0) * 0.5 + 0.5
    sand_streaks = sand_streaks**6.0 * (torch.rand_like(e.X) * 0.4 + 0.6)
    
    # Ambient light leak flood
    cx = -1.20 + 0.80 * progress
    cy = 0.70 - 0.40 * progress
    r = torch.sqrt((e.X - cx)**2 * 0.70 + (e.Y - cy)**2 * 1.10)
    flood = torch.exp(-r * 0.85) * 1.45 * (1.0 + 0.15 * math.sin(t * 3.2))
    ambient = torch.exp(-r * 0.30) * 0.32
    
    # Wind sand grains illuminated by the sun flood
    illuminated_sand = sand_streaks * (flood * 0.75 + 0.10)
    base_sand = e.generate_sand_texture(f, scale=1.1)
    
    total_raw = flood + ambient + illuminated_sand * 0.65 + base_sand * 0.10
    intensity = 1.0 - torch.exp(-total_raw * 1.30)
    rgb = e.color_ramp(intensity, PAL_ANALOG_LEAK)
    
    grain = (torch.rand_like(r) - 0.5) * 0.040
    return (torch.clamp(rgb + grain.unsqueeze(2), 0.0, 1.0) * 255.0).byte()


STUDIES: Dict[str, Tuple[str, Callable[[GPUSandEngine, int], torch.Tensor], str]] = {
    "01": ("sand_leak_01_dissolve.mp4", sand_study_01, "01: Sand Dissolve Film Burn (Tactile Stipple)"),
    "02": ("sand_leak_02_dust_motes.mp4", sand_study_02, "02: Golden Dust Motes in Beam (Floating Particles)"),
    "03": ("sand_leak_03_coarse_emulsion.mp4", sand_study_03, "03: Coarse 35mm Sand Emulsion (Heavy Grit)"),
    "04": ("sand_leak_04_solar_wind.mp4", sand_study_04, "04: Solar Wind Sandstorm (Streaming Grains)"),
}


# ==============================================================================
# Rendering & Packaging Harness
# ==============================================================================

def render_study(key: str, engine: GPUSandEngine, out_dir: Path) -> Path:
    filename, func, title = STUDIES[key]
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
    proc.wait()
    
    elapsed = time.time() - t0
    print(f"  ✓ [{key}] {title} rendered in {elapsed:.2f}s ({TOTAL_FRAMES / elapsed:.1f} FPS)")
    return out_path


def generate_contact_sheet(out_dir: Path):
    cell_w, cell_h = 960, 540
    sheet = np.zeros((cell_h * 2, cell_w * 2, 3), dtype=np.uint8)
    
    keys = ["01", "02", "03", "04"]
    positions = [(0, 0), (cell_w, 0), (0, cell_h), (cell_w, cell_h)]
    
    for key, (x, y) in zip(keys, positions):
        vid_path = out_dir / STUDIES[key][0]
        if vid_path.exists():
            cap = cv2.VideoCapture(str(vid_path))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 60)
            ret, frame = cap.read()
            if ret:
                thumb = cv2.resize(frame, (cell_w, cell_h))
                title = STUDIES[key][2]
                cv2.putText(thumb, title, (25, 45), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
                sheet[y:y+cell_h, x:x+cell_w] = thumb
                
    contact_path = out_dir / "contact_sheet_sand_grain_4x.jpg"
    cv2.imwrite(str(contact_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    
    art_dir = Path("/home/pierone/.gemini/antigravity-cli/brain/3f72aa22-108a-4300-83ad-d1d03f38464c")
    art_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(art_dir / "contact_sheet_sand_grain_4x.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"Contact sheet saved: {contact_path}")


def upload_to_drive(videos: List[Path], folder_id: str) -> Dict[str, Any]:
    print(f"\n[Drive Upload] Uploading {len(videos)} sand grain light leaks to folder: {folder_id}...")
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
            link = data.get("link", f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk")
            manifest[v.name] = {
                "id": file_id,
                "link": link,
                "bytes": int(data.get("bytes", v.stat().st_size)),
                "name": v.name
            }
            print(f"  ✓ {v.name} -> {link}")
            
    manifest_path = OUT_DIR / "sand_upload_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Render Sand Grain & Particulate Light Leaks on GPU")
    parser.add_argument("--keys", nargs="+", default=["01", "02", "03", "04"])
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Initializing GPUSandEngine on {device} ({torch.cuda.get_device_name(0)})...")
    engine = GPUSandEngine(WIDTH, HEIGHT, device=device)
    
    rendered = []
    for k in args.keys:
        if k in STUDIES:
            out_file = render_study(k, engine, OUT_DIR)
            rendered.append(out_file)
            
    generate_contact_sheet(OUT_DIR)
    
    if not args.no_upload:
        upload_to_drive(rendered, args.drive_folder)


if __name__ == "__main__":
    main()
