#!/usr/bin/env python3
"""
Space-to-Street Continuous Zoom Engine (Colosseum 8192x LOD Motion Suite)

Bridges the Macro Geopolitical Vector Engine (Natural Earth WGS84 GeoJSON + laser glow)
with the Micro Slippy Tile Pyramid Engine (Web Mercator EPSG:3857 Quadtree) to render a
flawless, jitter-free continuous zoom from orbit (1,450 km) down to architectural street-level (150 m).

Key Features:
- Subpixel floating-point cv2.warpAffine resampling (eliminates all integer rounding jitter).
- Smoothstep alpha cross-fading across continuous fractional zoom levels.
- Topographic World Hillshade blending for mountain depth (Alps & Apennines).
- Dynamic geopolitical laser outline that dissolves seamlessly as high-res satellite imagery emerges.
- Tactical HUD telemetry with live geodetic optical altitude, target reticle, and speech callout pin.
- Fast multi-threaded tile prefetching & NVIDIA GPU NVENC hardware encoding.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas & Timing parameters
WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_FRAMES = 180  # 6.0 seconds

# Geodetic Coordinates (Rome Colosseum)
TARGET_LAT = 41.890210
TARGET_LON = 12.492231
TARGET_NAME = "COLOSSEO (ROMA)"

# Zoom flight envelope
ZOOM_START = 4.3    # Orbit / European continental view (~1,500 km altitude)
ZOOM_END = 17.3      # Architectural street-level view (~160 m altitude)

# Path configuration
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
CHRONON_TEMPLATE = HERE.parents[1]
CATALOG_DIR = CHRONON_TEMPLATE / "catalog"
GEOJSON_PATH = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
CACHE_DIR = PROJECT_ROOT / "Chronon3d/assets/maps/cache/pyramid"
FONTS_DIR = PROJECT_ROOT / "Chronon3d/assets/fonts"
OUT_DIR = CHRONON_TEMPLATE / "out/space_to_street_zoom"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Google Drive credentials & target
DRIVE_FOLDER_ID = "1WALc4JbFz6uK5nEM_tYnAeQqiPVRacp_"
CRED_PATH = PROJECT_ROOT / "RenderingGen/UploadDrive/credentials.json"
TOKEN_PATH = PROJECT_ROOT / "RenderingGen/UploadDrive/token.json"
DRIVE_BIN = PROJECT_ROOT / "RenderingGen/bin/drive-upload"

# Tile provider URLs (Web Mercator EPSG:3857)
_ARCGIS = "https://server.arcgisonline.com/ArcGIS/rest/services"
TILE_URLS = {
    "esri_sat": f"{_ARCGIS}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
    "esri_hillshade": f"{_ARCGIS}/Elevation/World_Hillshade/MapServer/tile/{{z}}/{{y}}/{{x}}",
    "esri_dark": f"{_ARCGIS}/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}",
}

# Geodetic constants
MERCATOR_EQUATOR_METRES_PER_PIXEL = 156543.03392

# Palette (BGR for OpenCV)
COLOR_RED_LASER = (20, 25, 245)       # Geopolitical neon red #F51914
COLOR_RED_GLOW = (45, 55, 255)        # Hot core glow
COLOR_CYAN_HUD = (255, 240, 0)        # Tactical HUD cyan (BGR)
COLOR_EMERALD_LOCK = (129, 185, 16)   # Locked target emerald green #10B981
COLOR_WHITE = (255, 255, 255)
COLOR_GRID = (70, 55, 45)


def latlon_to_global_px(lat: float, lon: float, zoom: float) -> tuple[float, float]:
    """Convert WGS84 coordinates to continuous float Web Mercator pixel coordinates."""
    lat = max(-85.05112878, min(85.05112878, float(lat)))
    lon = max(-180.0, min(180.0, float(lon)))
    scale = 256.0 * (2.0 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) * 0.5 * scale
    return float(x), float(y)


def compute_altitude_km(zoom: float, lat: float) -> float:
    """Calculates approximate camera eye altitude in km from Web Mercator zoom level."""
    lat_rad = math.radians(lat)
    m_per_px = (MERCATOR_EQUATOR_METRES_PER_PIXEL * math.cos(lat_rad)) / (2.0 ** zoom)
    alt_m = m_per_px * 1080.0 * 0.95
    return alt_m / 1000.0


def smoothstep_c2(t: float) -> float:
    """C2 smootherstep ease-in-out: 6t^5 - 15t^4 + 10t^3."""
    t = max(0.0, min(1.0, float(t)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


class GeoJsonBoundaries:
    """Loads and projects Natural Earth country boundaries to subpixel screen coords."""

    def __init__(self, geojson_path: Path = GEOJSON_PATH):
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.target_rings: list[np.ndarray] = []
        self.neighbor_rings: list[np.ndarray] = []

        for f in data["features"]:
            name = f.get("properties", {}).get("ADMIN", "")
            geom = f["geometry"]
            coords = []
            if geom["type"] == "Polygon":
                coords = geom["coordinates"]
            elif geom["type"] == "MultiPolygon":
                for p in geom["coordinates"]:
                    coords.extend(p)

            for r in coords:
                if len(r) >= 3:
                    arr = np.asarray(r, dtype=np.float32)
                    if name == "Italy":
                        self.target_rings.append(arr)
                    elif name in ("France", "Spain", "Switzerland", "Austria", "Germany", "Greece", "Croatia", "Slovenia", "Tunisia"):
                        self.neighbor_rings.append(arr[::2])

    def project_rings(self, rings: list[np.ndarray], cam_lat: float, cam_lon: float,
                      cam_zoom: float) -> list[np.ndarray]:
        """Project WGS84 rings directly to screen pixels matching the camera state."""
        scale = 256.0 * (2.0 ** cam_zoom)
        cam_x, cam_y = latlon_to_global_px(cam_lat, cam_lon, cam_zoom)

        projected = []
        for r in rings:
            lons = r[:, 0]
            lats = np.clip(r[:, 1], -85.05112878, 85.05112878)
            xs = (lons + 180.0) / 360.0 * scale - cam_x + WIDTH * 0.5

            lats_rad = np.radians(lats)
            ys_raw = (1.0 - np.log(np.tan(lats_rad) + 1.0 / np.cos(lats_rad)) / math.pi) * 0.5 * scale
            ys = ys_raw - cam_y + HEIGHT * 0.5

            pts = np.stack([xs, ys], axis=-1)
            projected.append(pts)
        return projected


class SubpixelTilePyramid:
    """High-performance multi-resolution tile pyramid with subpixel float affine resampling."""

    def __init__(self, provider: str = "esri_sat"):
        self.provider = provider
        self.url_template = TILE_URLS[provider]
        self.tile_cache: dict[tuple[int, int, int], np.ndarray] = {}
        self.plates: dict[int, tuple[float, float, np.ndarray]] = {}
        self._lock = Lock()

    def fetch_tile(self, z: int, x: int, y: int) -> tuple[tuple[int, int, int], np.ndarray]:
        max_idx = 2 ** z
        x = x % max_idx
        if y < 0 or y >= max_idx:
            return (z, x, y), np.zeros((256, 256, 3), dtype=np.uint8)

        prov_cache = CACHE_DIR / self.provider / str(z) / str(x)
        prov_cache.mkdir(parents=True, exist_ok=True)
        tile_path = prov_cache / f"{y}.jpg"

        if tile_path.exists():
            try:
                img = cv2.imread(str(tile_path), cv2.IMREAD_COLOR)
                if img is not None and img.shape == (256, 256, 3):
                    return (z, x, y), img
            except Exception:
                pass

        url = self.url_template.format(z=z, x=x, y=y)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ChrononSpaceToStreet/2.0)"})
        for _ in range(3):
            try:
                with urllib.request.urlopen(req, timeout=6) as resp:
                    raw = resp.read()
                    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None and img.shape == (256, 256, 3):
                        tile_path.write_bytes(raw)
                        return (z, x, y), img
            except Exception:
                time.sleep(0.1)

        fallback = np.full((256, 256, 3), (20, 24, 30), dtype=np.uint8)
        return (z, x, y), fallback

    def prefetch_and_build_plates(self, center_lat: float, center_lon: float,
                                 min_zoom: int = 4, max_zoom: int = 18,
                                 half_tiles_extent: int = 3):
        """Prefetches tiles around center and builds one unified plate per integer level."""
        print(f"[{self.provider}] Prefetching multi-resolution tiles z={min_zoom}..{max_zoom}...")
        tasks = []
        for z in range(min_zoom, max_zoom + 1):
            gx, gy = latlon_to_global_px(center_lat, center_lon, z)
            ctx = int(gx // 256)
            cty = int(gy // 256)
            # Extent depends on zoom: wider at high zoom for safe coverage
            rad = half_tiles_extent if z <= 12 else half_tiles_extent + 1
            for dx in range(-rad, rad + 1):
                for dy in range(-rad, rad + 1):
                    tasks.append((z, ctx + dx, cty + dy))

        unique_tasks = list(set(tasks))
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(self.fetch_tile, *t) for t in unique_tasks]
            for fut in concurrent.futures.as_completed(futures):
                k, img = fut.result()
                self.tile_cache[k] = img

        print(f"[{self.provider}] Composing continuous plates...")
        for z in range(min_zoom, max_zoom + 1):
            gx, gy = latlon_to_global_px(center_lat, center_lon, z)
            ctx = int(gx // 256)
            cty = int(gy // 256)
            rad = half_tiles_extent if z <= 12 else half_tiles_extent + 1

            min_tx = ctx - rad
            max_tx = ctx + rad + 1
            min_ty = max(0, cty - rad)
            max_ty = min(2 ** z, cty + rad + 1)

            plate_w = (max_tx - min_tx) * 256
            plate_h = (max_ty - min_ty) * 256
            plate = np.zeros((plate_h, plate_w, 3), dtype=np.uint8)

            for ty in range(min_ty, max_ty):
                y_dst = (ty - min_ty) * 256
                for tx in range(min_tx, max_tx):
                    x_dst = (tx - min_tx) * 256
                    key = (z, tx % (2 ** z), ty)
                    tile = self.tile_cache.get(key)
                    if tile is not None:
                        plate[y_dst:y_dst + 256, x_dst:x_dst + 256] = tile

            origin_x = min_tx * 256.0
            origin_y = min_ty * 256.0
            self.plates[z] = (origin_x, origin_y, plate)

        print(f"[{self.provider}] Plate construction complete.")

    def sample_plate_subpixel(self, z: int, cam_lat: float, cam_lon: float,
                              scale: float, width: int = WIDTH, height: int = HEIGHT) -> np.ndarray:
        """Sample integer level z with exact floating-point subpixel affine matrix."""
        if z not in self.plates:
            return np.zeros((height, width, 3), dtype=np.uint8)

        origin_x, origin_y, plate = self.plates[z]
        cam_gx, cam_gy = latlon_to_global_px(cam_lat, cam_lon, z)

        pcx = cam_gx - origin_x
        pcy = cam_gy - origin_y

        # Exact 2x3 affine matrix mapping plate coordinates directly to screen
        M = np.array([
            [scale, 0.0, width * 0.5 - scale * pcx],
            [0.0, scale, height * 0.5 - scale * pcy]
        ], dtype=np.float32)

        return cv2.warpAffine(plate, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class CinematicHudRenderer:
    """Renders high-end documentary typography and tactical targeting reticle."""

    def __init__(self):
        try:
            self.font_title = ImageFont.truetype(str(FONTS_DIR / "Urbanist.ttf"), 30)
            self.font_sub = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), 17)
            self.font_mono = ImageFont.truetype(str(FONTS_DIR / "UbuntuMono-R.ttf"), 18)
            self.font_mono_lg = ImageFont.truetype(str(FONTS_DIR / "UbuntuMono-R.ttf"), 28)
            self.font_pin_title = ImageFont.truetype(str(FONTS_DIR / "Urbanist.ttf"), 26)
            self.font_pin_sub = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), 14)
        except Exception:
            self.font_title = self.font_sub = self.font_mono = self.font_mono_lg = ImageFont.load_default()
            self.font_pin_title = self.font_pin_sub = ImageFont.load_default()

    def draw_hud(self, frame: np.ndarray, cam_lat: float, cam_lon: float,
                 zoom: float, progress: float, is_locked: bool):
        h, w = frame.shape[:2]
        alt_km = compute_altitude_km(zoom, cam_lat)

        # 1. Targeting Reticle in screen center
        cx, cy = w // 2, h // 2
        reticle_r = int(140 - 85 * (progress ** 0.6))
        reticle_col = COLOR_EMERALD_LOCK if is_locked else COLOR_CYAN_HUD

        b_len = 18
        # Top-left bracket
        cv2.line(frame, (cx - reticle_r, cy - reticle_r), (cx - reticle_r + b_len, cy - reticle_r), reticle_col, 2, cv2.LINE_AA)
        cv2.line(frame, (cx - reticle_r, cy - reticle_r), (cx - reticle_r, cy - reticle_r + b_len), reticle_col, 2, cv2.LINE_AA)
        # Top-right bracket
        cv2.line(frame, (cx + reticle_r, cy - reticle_r), (cx + reticle_r - b_len, cy - reticle_r), reticle_col, 2, cv2.LINE_AA)
        cv2.line(frame, (cx + reticle_r, cy - reticle_r), (cx + reticle_r, cy - reticle_r + b_len), reticle_col, 2, cv2.LINE_AA)
        # Bottom-left bracket
        cv2.line(frame, (cx - reticle_r, cy + reticle_r), (cx - reticle_r + b_len, cy + reticle_r), reticle_col, 2, cv2.LINE_AA)
        cv2.line(frame, (cx - reticle_r, cy + reticle_r), (cx - reticle_r, cy + reticle_r - b_len), reticle_col, 2, cv2.LINE_AA)
        # Bottom-right bracket
        cv2.line(frame, (cx + reticle_r, cy + reticle_r), (cx + reticle_r - b_len, cy + reticle_r), reticle_col, 2, cv2.LINE_AA)
        cv2.line(frame, (cx + reticle_r, cy + reticle_r), (cx + reticle_r, cy + reticle_r - b_len), reticle_col, 2, cv2.LINE_AA)

        # Center crosshair
        cv2.drawMarker(frame, (cx, cy), reticle_col, cv2.MARKER_CROSS, 16, 1, cv2.LINE_AA)

        # Radar pulse ring when locked at high zoom
        if progress > 0.7:
            pulse_phase = ((progress - 0.7) / 0.3 * 4.0) % 1.0
            pulse_r = int(20 + 70 * pulse_phase)
            pulse_alpha = max(0.0, 1.0 - pulse_phase)
            p_col = tuple(int(c * pulse_alpha) for c in reticle_col)
            cv2.circle(frame, (cx, cy), pulse_r, p_col, 2, cv2.LINE_AA)

        # 2. Vector overlays / HUD Panels using PIL for typography
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_frame, "RGBA")

        # Top-Left HUD Badge: Mission & Coordinates
        badge_w, badge_h = 490, 125
        draw.rounded_rectangle([40, 40, 40 + badge_w, 40 + badge_h], radius=8,
                               fill=(12, 16, 22, 220), outline=(45, 65, 90, 255), width=1)

        draw.text((60, 56), "SPACE-TO-STREET RECON // 8192x LOD", font=self.font_mono, fill=(0, 240, 255, 255))
        draw.text((60, 82), TARGET_NAME, font=self.font_title, fill=(255, 255, 255, 255))
        draw.text((60, 122), f"WGS84: {abs(cam_lat):.6f}° N, {abs(cam_lon):.6f}° E",
                  font=self.font_mono, fill=(160, 185, 215, 255))

        # Top-Right HUD Badge: Optical Altitude & Zoom
        r_w, r_h = 440, 125
        r_x = w - 40 - r_w
        draw.rounded_rectangle([r_x, 40, r_x + r_w, 40 + r_h], radius=8,
                               fill=(12, 16, 22, 220), outline=(45, 65, 90, 255), width=1)

        alt_label = "OPTICAL EYE ALTITUDE"
        if alt_km >= 1.0:
            alt_val = f"{alt_km:9.1f} km"
        else:
            alt_val = f"{alt_km * 1000.0:9.0f} m"

        draw.text((r_x + 25, 56), alt_label, font=self.font_mono, fill=(0, 240, 255, 255))
        draw.text((r_x + 25, 78), alt_val, font=self.font_mono_lg, fill=(255, 255, 255, 255))
        draw.text((r_x + 25, 122), f"PYRAMID CONTINUOUS: z={zoom:5.2f} (EPSG:3857)",
                  font=self.font_mono, fill=(160, 185, 215, 255))

        # Bottom Timeline Bar
        bar_x = 80
        bar_w = w - 160
        bar_y = h - 50
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 6], fill=(25, 35, 45, 220))
        fill_w = int(bar_w * progress)
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 6], fill=(0, 240, 255, 255))

        status_text = "STATUS: SUPERSONIC DESCENT SEQUENCE" if not is_locked else "STATUS: TARGET ACQUIRED & LOCKED"
        status_col = (16, 185, 129, 255) if is_locked else (0, 240, 255, 255)
        draw.text((bar_x, bar_y - 24), status_text, font=self.font_mono, fill=status_col)

        # 3. Speech-Bubble Callout Pin on Target (when close to street level)
        if progress > 0.78:
            pin_p = min(1.0, (progress - 0.78) / 0.15)
            # Spring bounce
            pin_scale = 1.0 + 0.15 * math.sin(pin_p * math.pi) * (1.0 - pin_p)
            self._draw_speech_pin(draw, cx, cy - 35, "COLOSSEO (ROMA)",
                                  "FLAVIAN AMPHITHEATRE // ROMAN EMPIRE",
                                  "LAT 41.8902° N  |  LON 12.4922° E  |  ELEV 54m",
                                  p=pin_p, scale=pin_scale)

        frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)

    def _draw_speech_pin(self, draw: ImageDraw.ImageDraw, anchor_x: int, anchor_y: int,
                         title: str, subtitle: str, meta: str, p: float, scale: float = 1.0):
        if p <= 0.05:
            return

        box_w = int(460 * scale)
        box_h = int(96 * scale)
        tail_h = int(14 * scale)

        cx = anchor_x
        top = anchor_y - box_h - tail_h
        rect = [cx - box_w // 2, top, cx + box_w // 2, top + box_h]

        # White clean modern speech card
        draw.rounded_rectangle(rect, radius=8, fill=(255, 255, 255, int(250 * p)),
                               outline=(20, 245, 150, int(255 * p)), width=2)
        # Tail triangle
        tri = [(cx - int(10 * scale), top + box_h - 1),
               (cx + int(10 * scale), top + box_h - 1),
               (cx, top + box_h + tail_h)]
        draw.polygon(tri, fill=(255, 255, 255, int(250 * p)))

        if p > 0.4:
            draw.text((cx, top + int(18 * scale)), title, font=self.font_pin_title,
                      fill=(15, 20, 28, int(255 * p)), anchor="mm")
            draw.text((cx, top + int(46 * scale)), subtitle, font=self.font_pin_sub,
                      fill=(80, 90, 105, int(255 * p)), anchor="mm")
            draw.text((cx, top + int(72 * scale)), meta, font=self.font_pin_sub,
                      fill=(180, 25, 25, int(255 * p)), anchor="mm")


def render_space_to_street_zoom():
    print("=================================================================")
    print("CHRONON DYNAMIC CARTOGRAPHY: SPACE-TO-STREET CONTINUOUS ZOOM")
    print(f"Target: {TARGET_NAME} ({TARGET_LAT} N, {TARGET_LON} E)")
    print(f"LOD Envelope: z={ZOOM_START:.2f} -> z={ZOOM_END:.2f} ({TOTAL_FRAMES} frames)")
    print("=================================================================")

    # 1. Initialize Vector Boundaries
    geo = GeoJsonBoundaries()

    # 2. Initialize Subpixel Tile Pyramids
    sat_pyr = SubpixelTilePyramid(provider="esri_sat")
    sat_pyr.prefetch_and_build_plates(TARGET_LAT, TARGET_LON, min_zoom=4, max_zoom=18, half_tiles_extent=3)

    hill_pyr = SubpixelTilePyramid(provider="esri_hillshade")
    hill_pyr.prefetch_and_build_plates(TARGET_LAT, TARGET_LON, min_zoom=4, max_zoom=10, half_tiles_extent=3)

    hud = CinematicHudRenderer()

    out_mp4 = OUT_DIR / "space_to_street_colosseum_1080p.mp4"

    # 3. Setup NVENC GPU Video Writer
    cmd_nvenc = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "h264_nvenc",
        "-preset", "p5",
        "-cq", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_mp4)
    ]

    try:
        proc = subprocess.Popen(cmd_nvenc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        using_gpu = True
    except Exception:
        cmd_cpu = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-pix_fmt", "bgr24",
            "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_mp4)
        ]
        proc = subprocess.Popen(cmd_cpu, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        using_gpu = False

    print(f"Video pipeline started. Encoder: {'NVIDIA NVENC (GPU)' if using_gpu else 'libx264 (CPU)'}")

    t_start = time.perf_counter()
    stills_saved = {}

    for f_idx in range(TOTAL_FRAMES):
        prog = f_idx / float(TOTAL_FRAMES - 1)
        eased_prog = smoothstep_c2(prog)

        # Continuous zoom
        cur_zoom = ZOOM_START + (ZOOM_END - ZOOM_START) * eased_prog

        # Camera center with subtle drift from continental offset into exact pin
        drift_factor = max(0.0, 1.0 - eased_prog * 1.5)
        cam_lat = TARGET_LAT + 0.6 * drift_factor
        cam_lon = TARGET_LON - 0.4 * drift_factor

        # 1. Sample continuous satellite imagery across fractional zoom
        z_lo = int(math.floor(cur_zoom))
        z_hi = z_lo + 1
        sub_t = cur_zoom - z_lo
        alpha_blend = sub_t * sub_t * (3.0 - 2.0 * sub_t)

        scale_lo = 2.0 ** sub_t
        scale_hi = 2.0 ** (sub_t - 1.0)

        frame_lo = sat_pyr.sample_plate_subpixel(z_lo, cam_lat, cam_lon, scale_lo)

        if alpha_blend > 0.001 and z_hi in sat_pyr.plates:
            frame_hi = sat_pyr.sample_plate_subpixel(z_hi, cam_lat, cam_lon, scale_hi)
            frame = cv2.addWeighted(frame_lo, 1.0 - alpha_blend, frame_hi, alpha_blend, 0.0)
        else:
            frame = frame_lo

        # 2. Hillshade elevation relief blending (at macro zoom z <= 9.5)
        if cur_zoom < 9.5 and z_lo in hill_pyr.plates:
            hill_lo = hill_pyr.sample_plate_subpixel(z_lo, cam_lat, cam_lon, scale_lo)
            # Contrast curve for mountain relief
            hill_gray = cv2.cvtColor(hill_lo, cv2.COLOR_BGR2GRAY)
            hill_norm = cv2.equalizeHist(hill_gray)
            hill_bgr = cv2.cvtColor(hill_norm, cv2.COLOR_GRAY2BGR)
            # Blend weight fades out as camera descends
            hill_w = max(0.0, min(0.35, (9.5 - cur_zoom) / 5.5 * 0.35))
            frame = cv2.addWeighted(frame, 1.0 - hill_w, hill_bgr, hill_w, 0.0)

        # 3. Geopolitical dark aesthetic grade at macro zooms
        if cur_zoom < 8.5:
            # Subtle dark charcoal vignette / toning
            grade_alpha = max(0.0, min(1.0, (8.5 - cur_zoom) / 3.5))
            dark_tone = np.full_like(frame, (16, 20, 26))
            frame = cv2.addWeighted(frame, 1.0 - 0.4 * grade_alpha, dark_tone, 0.4 * grade_alpha, 0.0)

            # Cartographic coordinate grid lines
            for gx in range(0, WIDTH, 80):
                cv2.line(frame, (gx, 0), (gx, HEIGHT), COLOR_GRID, 1, cv2.LINE_AA)
            for gy in range(0, HEIGHT, 80):
                cv2.line(frame, (0, gy), (WIDTH, gy), COLOR_GRID, 1, cv2.LINE_AA)

            # Neighboring boundaries
            neighbor_polys = geo.project_rings(geo.neighbor_rings, cam_lat, cam_lon, cur_zoom)
            for poly in neighbor_polys:
                if len(poly) >= 2:
                    cv2.polylines(frame, [poly.astype(np.int32)], True, (55, 50, 45), 1, cv2.LINE_AA)

            # Target Country (Italy) neon red laser outline + glow
            target_polys = geo.project_rings(geo.target_rings, cam_lat, cam_lon, cur_zoom)
            glow_fade = max(0.0, min(1.0, (8.5 - cur_zoom) / 2.0))

            if glow_fade > 0.01:
                # Translucent red country fill
                fill_mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
                int_polys = [p.astype(np.int32) for p in target_polys if len(p) >= 3]
                if int_polys:
                    cv2.fillPoly(fill_mask, int_polys, 255)
                    red_fill = np.zeros_like(frame)
                    red_fill[:] = COLOR_RED_LASER
                    fill_alpha = 0.28 * glow_fade
                    frame[fill_mask > 0] = cv2.addWeighted(frame, 1.0 - fill_alpha, red_fill, fill_alpha, 0)[fill_mask > 0]

                    # Multi-pass neon glow outline
                    edge_img = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
                    cv2.polylines(edge_img, int_polys, True, 255, 3, cv2.LINE_AA)

                    glow1 = cv2.GaussianBlur(edge_img, (0, 0), 4)
                    glow2 = cv2.GaussianBlur(edge_img, (0, 0), 12)
                    glow_comb = cv2.addWeighted(glow1, 0.65, glow2, 0.35, 0)

                    colored_glow = np.zeros_like(frame)
                    colored_glow[:] = COLOR_RED_GLOW
                    glow_mask = (glow_comb.astype(np.float32) / 255.0 * glow_fade)[:, :, None]
                    frame = (frame * (1.0 - glow_mask * 0.9) + colored_glow * (glow_mask * 0.9)).astype(np.uint8)

                    # Crisp white/pink inner core
                    cv2.polylines(frame, int_polys, True, (240, 240, 255), 2, cv2.LINE_AA)

        # 4. Telemetry HUD & Targeting Reticle
        is_locked = (prog >= 0.85)
        hud.draw_hud(frame, cam_lat, cam_lon, cur_zoom, prog, is_locked)

        # Write frame to NVENC encoder
        proc.stdin.write(frame.tobytes())

        # Save representative still captures
        if f_idx == 0:
            still_path = OUT_DIR / "space_to_street_01_orbit_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["orbit"] = still_path
        elif f_idx == int(TOTAL_FRAMES * 0.5):
            still_path = OUT_DIR / "space_to_street_02_descent_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["descent"] = still_path
        elif f_idx == TOTAL_FRAMES - 1:
            still_path = OUT_DIR / "space_to_street_03_colosseum_lock_still.png"
            cv2.imwrite(str(still_path), frame)
            stills_saved["lock"] = still_path

        if f_idx % 30 == 0 or f_idx == TOTAL_FRAMES - 1:
            fps_cur = (f_idx + 1) / max(0.001, time.perf_counter() - t_start)
            alt_km = compute_altitude_km(cur_zoom, cam_lat)
            print(f"  Frame {f_idx + 1:3d}/{TOTAL_FRAMES} (prog={prog * 100:5.1f}%, zoom={cur_zoom:5.2f}, alt={alt_km:6.1f}km, speed={fps_cur:4.1f} fps)")

    proc.stdin.close()
    proc.wait()

    elapsed = time.perf_counter() - t_start
    file_size_mb = out_mp4.stat().st_size / (1024 * 1024) if out_mp4.exists() else 0.0
    print(f"\nRender completed in {elapsed:.1f}s ({TOTAL_FRAMES / elapsed:.1f} FPS)!")
    print(f"Saved video ({file_size_mb:.2f} MB): {out_mp4}")

    return out_mp4, stills_saved


def upload_to_drive(video_path: Path, still_paths: dict[str, Path]):
    print(f"\nUploading render outputs to Google Drive folder: {DRIVE_FOLDER_ID}...")
    files_to_upload = [
        (video_path, "00_space_to_street_colosseum_continuous_zoom.mp4"),
    ]
    for key, sp in still_paths.items():
        files_to_upload.append((sp, f"00_space_to_street_colosseum_{key}_still.png"))

    for local_file, drive_name in files_to_upload:
        if not local_file.exists():
            continue
        print(f"  Uploading {drive_name} ({local_file})...")
        cmd = [
            str(DRIVE_BIN),
            "-credentials", str(CRED_PATH),
            "-token", str(TOKEN_PATH),
            "-folder", str(DRIVE_FOLDER_ID),
            "-file", str(local_file),
            "-name", drive_name
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  ✓ Uploaded {drive_name}: {res.stdout.strip()}")
        else:
            print(f"  ✗ Failed {drive_name}: {res.stderr.strip()}")


if __name__ == "__main__":
    mp4_file, stills = render_space_to_street_zoom()
    upload_to_drive(mp4_file, stills)
