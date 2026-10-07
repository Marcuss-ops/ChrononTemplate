#!/usr/bin/env python3
"""Cinematic Dynamic Map Motion Kit using OpenCV, NumPy and Authoritative GeoJSON.

Features:
- True dynamic camera animations: smooth pans, zooms, dolly-ins and 2.5D perspective tracking
- Vectorized geographic projection with fast spatial frustum culling (real-time rendering)
- High-end multi-layer neon bloom & edge contour draw-on
- Smooth spring-eased graphic badges, flags, 90-degree callout elbows, and metric animations
- Encodes directly to universal streaming H.264 (yuv420p) for immediate playback on Google Drive and web
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
FPS = 30

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
CHRONON_TEMPLATE = HERE.parents[1]
CATALOG_DIR = CHRONON_TEMPLATE / "catalog"
GEOJSON_PATH = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
FONTS_DIR = PROJECT_ROOT / "Chronon3d/assets/fonts"
OUT_DIR = CHRONON_TEMPLATE / "out/geopolitical_maps_h264"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Aesthetic color palettes (BGR for OpenCV)
COLOR_OCEAN_DARK = (14, 12, 10)         # Deep black/charcoal ocean
COLOR_OCEAN_BLUE = (120, 68, 42)        # Steel blue ocean for LatAm scene
COLOR_LAND_DARK = (26, 23, 20)          # Landmass slate
COLOR_LAND_DEEP = (16, 14, 12)          # Darker landmass
COLOR_BORDER_MUTED = (48, 44, 40)       # Country boundaries
COLOR_GRID_BLUE = (150, 95, 65)         # Grid lines
COLOR_GRID_DARK = (32, 28, 25)

COLOR_RED_VIVID = (18, 20, 245)         # Saturated geopolitical red #F51412
COLOR_BLUE_VIVID = (245, 45, 15)        # Saturated diplomatic blue #0F2DF5
COLOR_MAGENTA_NEON = (210, 40, 240)     # Vibrant magenta/pink #F028D2
COLOR_WHITE = (255, 255, 255)


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3

def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * t

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class GeoEngine:
    """Precomputed GeoJSON spatial database for ultra-fast vector rendering."""

    def __init__(self, geojson_path: Path = GEOJSON_PATH):
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.country_rings: dict[str, list[np.ndarray]] = {}
        self.all_land_rings: list[tuple[np.ndarray, float, float, float, float]] = []

        for f in data["features"]:
            name = f.get("properties", {}).get("ADMIN")
            geom = f["geometry"]
            coords = []
            if geom["type"] == "Polygon":
                coords = geom["coordinates"]
            elif geom["type"] == "MultiPolygon":
                for p in geom["coordinates"]:
                    coords.extend(p)

            country_list = []
            for r in coords:
                if len(r) >= 3:
                    # Precise country boundaries
                    arr = np.asarray(r, dtype=np.float32)
                    stride = max(1, math.ceil(len(arr) / 1000))
                    arr_country = arr[::stride]
                    if len(arr_country) >= 3:
                        country_list.append(arr_country)

                    # Simplified background landmass
                    arr_land = arr[::3]
                    if len(arr_land) >= 3:
                        min_lon, min_lat = float(arr_land[:, 0].min()), float(arr_land[:, 1].min())
                        max_lon, max_lat = float(arr_land[:, 0].max()), float(arr_land[:, 1].max())
                        self.all_land_rings.append((arr_land, min_lon, max_lon, min_lat, max_lat))

            if name:
                self.country_rings[name] = country_list

    def get_country_rings(self, name: str) -> list[np.ndarray]:
        return self.country_rings.get(name, [])


GEO = GeoEngine()


class DynamicCamera:
    """Dynamic geographic camera that tracks, zooms and pans over lat/lon coordinates."""

    def __init__(self, start_pose: tuple[float, float, float],
                 end_pose: tuple[float, float, float],
                 total_frames: int):
        """Pose: (center_lon, center_lat, scale)."""
        self.start_pose = start_pose
        self.end_pose = end_pose
        self.total_frames = max(1, total_frames)

    def get_pose(self, frame_idx: int) -> tuple[float, float, float]:
        t = ease_in_out(frame_idx / float(self.total_frames))
        lon = lerp(self.start_pose[0], self.end_pose[0], t)
        lat = lerp(self.start_pose[1], self.end_pose[1], t)
        scale = lerp(self.start_pose[2], self.end_pose[2], t)
        return lon, lat, scale

    def project_point(self, lon: float, lat: float, c_lon: float, c_lat: float, scale: float) -> tuple[int, int]:
        x = WIDTH / 2.0 + (lon - c_lon) * scale
        lat_clamped = max(-85.0, min(85.0, lat))
        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        y_m = math.log(math.tan(math.pi / 4.0 + math.radians(lat_clamped) / 2.0))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        y = HEIGHT / 2.0 - (y_m - cy_m) * scale * (180.0 / math.pi)
        return int(round(x)), int(round(y))

    def project_rings(self, rings: list[np.ndarray], c_lon: float, c_lat: float, scale: float) -> list[np.ndarray]:
        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        scale_deg = scale * (180.0 / math.pi)

        polys = []
        for r in rings:
            lons = r[:, 0]
            lats = np.clip(r[:, 1], -85.0, 85.0)
            xs = WIDTH / 2.0 + (lons - c_lon) * scale
            yms = np.log(np.tan(np.pi / 4.0 + np.radians(lats) / 2.0))
            ys = HEIGHT / 2.0 - (yms - cy_m) * scale_deg
            pts = np.stack([xs, ys], axis=-1).astype(np.int32)
            polys.append(pts)
        return polys

    def render_base(self, c_lon: float, c_lat: float, scale: float,
                    ocean_color=COLOR_OCEAN_DARK, land_color=COLOR_LAND_DARK,
                    border_color=COLOR_BORDER_MUTED) -> np.ndarray:
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = ocean_color

        # View frustum in degrees
        lon_margin = (WIDTH / 2.0 + 150) / scale
        vis_min_lon = c_lon - lon_margin
        vis_max_lon = c_lon + lon_margin

        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        scale_deg = scale * (180.0 / math.pi)

        ym_top = cy_m - (-150 - HEIGHT / 2.0) / scale_deg
        ym_bot = cy_m - (HEIGHT + 150 - HEIGHT / 2.0) / scale_deg
        vis_max_lat = math.degrees(2.0 * math.atan(math.exp(ym_top)) - math.pi / 2.0)
        vis_min_lat = math.degrees(2.0 * math.atan(math.exp(ym_bot)) - math.pi / 2.0)

        visible_polys = []
        for arr, min_lon, max_lon, min_lat, max_lat in GEO.all_land_rings:
            if max_lon < vis_min_lon or min_lon > vis_max_lon or max_lat < vis_min_lat or min_lat > vis_max_lat:
                continue
            lons = arr[:, 0]
            lats = np.clip(arr[:, 1], -85.0, 85.0)
            xs = WIDTH / 2.0 + (lons - c_lon) * scale
            yms = np.log(np.tan(np.pi / 4.0 + np.radians(lats) / 2.0))
            ys = HEIGHT / 2.0 - (yms - cy_m) * scale_deg
            pts = np.stack([xs, ys], axis=-1).astype(np.int32)
            visible_polys.append(pts)

        if visible_polys:
            cv2.fillPoly(frame, visible_polys, land_color)
            cv2.polylines(frame, visible_polys, True, border_color, 1, cv2.LINE_AA)

        return frame


class DynamicEffects:
    """Specialized animated overlay components."""

    @staticmethod
    def draw_country_fill(frame: np.ndarray, polys: list[np.ndarray],
                          color_bgr: tuple[int, int, int], opacity: float):
        if opacity <= 0.001 or not polys:
            return
        mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
        cv2.fillPoly(mask, polys, 255)
        overlay = np.zeros_like(frame)
        overlay[:] = color_bgr
        alpha = max(0.0, min(1.0, opacity))
        fg = cv2.addWeighted(frame, 1.0 - alpha, overlay, alpha, 0)
        frame[mask > 0] = fg[mask > 0]

    @staticmethod
    def draw_outline_glow(frame: np.ndarray, polys: list[np.ndarray],
                          color_bgr: tuple[int, int, int], progress: float = 1.0,
                          thickness: int = 3, halo_strength: float = 1.0):
        if progress <= 0.001 or not polys:
            return
        edge = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

        # Animate along polygon boundary
        for poly in polys:
            if len(poly) < 2:
                continue
            seg_lens = np.sqrt(np.sum(np.diff(poly.astype(np.float64), axis=0) ** 2, axis=1))
            total_len = float(seg_lens.sum())
            budget = total_len * max(0.0, min(1.0, progress))
            if budget <= 0:
                continue
            for i, d in enumerate(seg_lens):
                if budget <= 0:
                    break
                p1 = poly[i]
                p2 = poly[(i + 1) % len(poly)]
                ratio = min(1.0, budget / max(1e-6, d))
                p_end = (p1 + (p2 - p1) * ratio).astype(int)
                cv2.line(edge, tuple(p1), tuple(p_end), 255, thickness, cv2.LINE_AA)
                budget -= d

        # Layered Gaussian halo
        base_f = frame.astype(np.float32)
        c_f = np.asarray(color_bgr, dtype=np.float32)[None, None, :]
        for sigma, weight in [(24, 0.45 * halo_strength), (10, 0.65 * halo_strength), (3, 0.90 * halo_strength)]:
            halo = cv2.GaussianBlur(edge, (0, 0), sigma).astype(np.float32) / 255.0
            a = (halo * weight)[:, :, None]
            base_f = base_f * (1.0 - a) + c_f * a

        rim = (edge.astype(np.float32) / 255.0)[:, :, None]
        bright = np.clip(c_f * 0.6 + 255.0 * 0.4, 0, 255)
        base_f = base_f * (1.0 - rim) + bright * rim
        frame[:] = np.clip(base_f, 0, 255).astype(np.uint8)

    @staticmethod
    def draw_flag_card(frame: np.ndarray, center: tuple[int, int], country_code: str,
                       progress: float, size=(160, 105)):
        if progress <= 0.001:
            return
        p = ease_out(progress)
        w, h = int(size[0] * p), int(size[1] * p)
        if w < 12 or h < 8:
            return

        x1 = center[0] - w // 2
        y1 = center[1] - h // 2
        card = np.zeros((h, w, 3), dtype=np.uint8)

        if country_code == "VN":
            card[:] = (18, 20, 240)
            cx, cy = w // 2, h // 2
            r_out = int(h * 0.35)
            r_in = int(r_out * 0.38)
            star = []
            for i in range(10):
                angle = -math.pi / 2.0 + i * math.pi / 5.0
                r = r_out if i % 2 == 0 else r_in
                star.append((int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))
            cv2.fillPoly(card, [np.array(star, dtype=np.int32)], (20, 230, 255))
        elif country_code == "USA":
            card[:] = (255, 255, 255)
            sh = h / 13.0
            for i in range(13):
                if i % 2 == 0:
                    cv2.rectangle(card, (0, int(i * sh)), (w, int((i + 1) * sh)), (20, 24, 200), -1)
            cw = int(w * 0.46)
            ch = int(sh * 7)
            cv2.rectangle(card, (0, 0), (cw, ch), (150, 40, 20), -1)
            for r_i in range(3):
                for c_i in range(4):
                    cv2.circle(card, (int((c_i + 1) * (cw / 5.0)), int((r_i + 1) * (ch / 4.0))),
                               1, (255, 255, 255), -1)

        cv2.rectangle(card, (0, 0), (w - 1, h - 1), (255, 255, 255), 1)

        # Drop shadow
        sx1, sy1 = x1 + 6, y1 + 6
        if 0 <= sx1 and sx1 + w <= WIDTH and 0 <= sy1 and sy1 + h <= HEIGHT:
            frame[sy1:sy1 + h, sx1:sx1 + w] = (frame[sy1:sy1 + h, sx1:sx1 + w] * 0.3).astype(np.uint8)

        if 0 <= x1 and x1 + w <= WIDTH and 0 <= y1 and y1 + h <= HEIGHT:
            frame[y1:y1 + h, x1:x1 + w] = card

    @staticmethod
    def draw_white_pin_card(frame: np.ndarray, text: str, anchor_pt: tuple[int, int],
                           progress: float):
        if progress <= 0.001:
            return
        p = ease_out(progress)
        card_w = 110
        card_h = 42
        cx, cy = anchor_pt[0], anchor_pt[1] - 40

        x1 = cx - card_w // 2
        y1 = cy - card_h // 2
        x2 = x1 + card_w
        y2 = y1 + card_h

        triangle = np.array([[cx - 8, y2], [cx + 8, y2], [cx, anchor_pt[1] - 6]], dtype=np.int32)
        cv2.fillPoly(frame, [triangle], COLOR_WHITE)
        cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_WHITE, -1)

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=20)
        draw.text((cx, cy), text, font=font, fill=(15, 18, 24), anchor="mm")
        frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)


def write_video_h264(frames: list[np.ndarray], out_path: Path):
    """Write frame sequence directly to H.264 mp4 via ffmpeg pipeline."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
        "-movflags", "+faststart",
        "-crf", "18",
        str(out_path)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in frames:
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    proc.wait()


# -----------------------------------------------------------------------------
# DYNAMIC SCENE IMPLEMENTATIONS
# -----------------------------------------------------------------------------

def render_scene_1(out_mp4: Path, num_frames=120):
    """SCENE 1: Dynamic camera push-in on Southeast Asia + Vietnam red glow + flags + magenta bars."""
    print("Rendering Scene 1 with dynamic camera...")
    # Camera drifts from broad Asia (scale=18) to focused Vietnam (scale=34) with subtle pan
    cam = DynamicCamera(start_pose=(102.0, 18.0, 18.0),
                        end_pose=(108.5, 15.5, 33.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_DARK, land_color=(28, 25, 22))

        # Vietnam country polygons at current camera pose
        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        p_fill = ease_out(f / 35.0)
        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.95 * p_fill)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.1)

        # Dynamic screen anchors tracking with the camera
        vn_top = cam.project_point(105.8, 21.0, c_lon, c_lat, scale)
        vn_mid = cam.project_point(108.2, 16.0, c_lon, c_lat, scale)

        vn_flag_pt = (vn_top[0] - 120, vn_top[1] - 160)
        us_flag_pt = (vn_mid[0] + 360, vn_mid[1] - 40)

        # Magenta connection bars tracking in world space
        p_bars = ease_out((f - 20) / 30.0)
        if p_bars > 0:
            target_1 = (int(vn_top[0] + (us_flag_pt[0] - 70 - vn_top[0]) * p_bars),
                        int(vn_top[1] + (us_flag_pt[1] - 60 - vn_top[1]) * p_bars))
            cv2.line(frame, vn_top, target_1, COLOR_MAGENTA_NEON, 14, cv2.LINE_AA)

            target_2 = (int(vn_mid[0] + (us_flag_pt[0] - 70 - vn_mid[0]) * p_bars),
                        int(vn_mid[1] + (us_flag_pt[1] + 30 - vn_mid[1]) * p_bars))
            cv2.line(frame, vn_mid, target_2, COLOR_MAGENTA_NEON, 14, cv2.LINE_AA)

        # Flag badges pop in and track
        DynamicEffects.draw_flag_card(frame, vn_flag_pt, "VN", (f - 12) / 25.0)
        DynamicEffects.draw_flag_card(frame, us_flag_pt, "USA", (f - 26) / 25.0)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 1")


def render_scene_2(out_mp4: Path, num_frames=120):
    """SCENE 2: Dynamic diagonal camera pan over Latin America + grid + sequential red reveals + pins."""
    print("Rendering Scene 2 with dynamic camera...")
    # Camera pans smoothly from Mexico down towards Brazil
    cam = DynamicCamera(start_pose=(-85.0, 12.0, 8.2),
                        end_pose=(-62.0, -4.0, 9.6),
                        total_frames=num_frames)

    mex_rings = GEO.get_country_rings("Mexico")
    col_rings = GEO.get_country_rings("Colombia")
    bra_rings = GEO.get_country_rings("Brazil")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=(16, 14, 12), border_color=(45, 42, 40))

        # Dynamic coordinate grid
        for x in range(0, WIDTH, 80):
            cv2.line(frame, (x, 0), (x, HEIGHT), (145, 95, 65), 1, cv2.LINE_AA)
        for y in range(0, HEIGHT, 80):
            cv2.line(frame, (0, y), (WIDTH, y), (145, 95, 65), 1, cv2.LINE_AA)

        # Project country rings
        mex_polys = cam.project_rings(mex_rings, c_lon, c_lat, scale)
        col_polys = cam.project_rings(col_rings, c_lon, c_lat, scale)
        bra_polys = cam.project_rings(bra_rings, c_lon, c_lat, scale)

        # Sequential reveals
        p_mex = ease_out(f / 25.0)
        DynamicEffects.draw_country_fill(frame, mex_polys, COLOR_RED_VIVID, opacity=0.95 * p_mex)
        mex_anchor = cam.project_point(-101.0, 22.0, c_lon, c_lat, scale)
        DynamicEffects.draw_white_pin_card(frame, "Mexico", mex_anchor, (f - 8) / 20.0)

        p_col = ease_out((f - 20) / 25.0)
        DynamicEffects.draw_country_fill(frame, col_polys, COLOR_RED_VIVID, opacity=0.95 * p_col)
        col_anchor = cam.project_point(-73.5, 4.0, c_lon, c_lat, scale)
        DynamicEffects.draw_white_pin_card(frame, "Colombia", col_anchor, (f - 25) / 20.0)

        p_bra = ease_out((f - 40) / 25.0)
        DynamicEffects.draw_country_fill(frame, bra_polys, COLOR_RED_VIVID, opacity=0.95 * p_bra)
        bra_anchor = cam.project_point(-51.0, -12.0, c_lon, c_lat, scale)
        DynamicEffects.draw_white_pin_card(frame, "Brazil", bra_anchor, (f - 45) / 20.0)

        # Striped metallic diagonal arrow indicator into Colombia
        p_arr = ease_out((f - 35) / 30.0)
        if p_arr > 0:
            target_pt = (col_anchor[0], col_anchor[1] - 45)
            start_pt = (target_pt[0] + 160, target_pt[1] - 160)
            steps = 20
            for i in range(steps):
                t1 = i / float(steps)
                t2 = (i + 1) / float(steps)
                if t1 > p_arr:
                    break
                p1 = (int(start_pt[0] + (target_pt[0] - start_pt[0]) * t1),
                      int(start_pt[1] + (target_pt[1] - start_pt[1]) * t1))
                p2 = (int(start_pt[0] + (target_pt[0] - start_pt[0]) * min(p_arr, t2)),
                      int(start_pt[1] + (target_pt[1] - start_pt[1]) * min(p_arr, t2)))
                col = (255, 255, 255) if (i % 2 == 0) else (180, 180, 180)
                cv2.line(frame, p1, p2, col, 8, cv2.LINE_AA)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 2")


def render_scene_3(out_mp4: Path, num_frames=120):
    """SCENE 3: Cinematic camera push into Ho Chi Minh City + 90-deg connector + massive glowing Intel logo."""
    print("Rendering Scene 3 with dynamic camera...")
    # Camera starts centered on Indochina and glides eastward to make room for the Intel callout
    cam = DynamicCamera(start_pose=(107.0, 14.5, 26.0),
                        end_pose=(111.0, 13.8, 32.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_DARK, land_color=(28, 25, 22))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)
        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.95)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.0)

        # Dynamic tracking of Ho Chi Minh City
        hcm_pt = cam.project_point(106.63, 10.82, c_lon, c_lat, scale)

        # City dot & pulse ring
        cv2.circle(frame, hcm_pt, 8, COLOR_WHITE, -1, cv2.LINE_AA)
        cv2.circle(frame, hcm_pt, 14, COLOR_WHITE, 2, cv2.LINE_AA)

        # Label card 'Ho Chi Minh City'
        card_w, card_h = 240, 52
        cx, cy = hcm_pt[0] - 8, hcm_pt[1] - 46
        x1, y1 = cx - card_w // 2, cy - card_h // 2
        cv2.rectangle(frame, (x1, y1), (x1 + card_w, y1 + card_h), COLOR_WHITE, -1)

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=24)
        draw.text((cx, cy), "Ho Chi Minh City", font=font, fill=(15, 18, 22), anchor="mm")
        frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

        # Target callout destination
        logo_center = (WIDTH // 2 + 380, HEIGHT // 2 - 120)
        p_line = ease_in_out((f - 15) / 35.0)

        if p_line > 0:
            corner_pt = (logo_center[0] - 120, hcm_pt[1])
            end_pt = (logo_center[0] - 120, logo_center[1] + 100)

            len1 = corner_pt[0] - hcm_pt[0]
            len2 = corner_pt[1] - end_pt[1]
            tot = len1 + len2
            budget = tot * p_line

            if budget <= len1:
                cur_x = int(hcm_pt[0] + budget)
                cv2.line(frame, hcm_pt, (cur_x, hcm_pt[1]), COLOR_WHITE, 4, cv2.LINE_AA)
            else:
                cv2.line(frame, hcm_pt, corner_pt, COLOR_WHITE, 4, cv2.LINE_AA)
                cur_y = int(corner_pt[1] - (budget - len1))
                cv2.line(frame, corner_pt, (corner_pt[0], cur_y), COLOR_WHITE, 4, cv2.LINE_AA)

        # Massive glowing Intel logo
        p_logo = ease_out((f - 35) / 30.0)
        if p_logo > 0:
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            f_intel = ImageFont.truetype(str(FONTS_DIR / "Montserrat-Bold.ttf"), size=150)
            tx, ty = logo_center
            draw.text((tx, ty), "intel", font=f_intel, fill=(255, 255, 255), anchor="mm")
            f_reg = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=24)
            draw.text((tx + 225, ty + 20), "®", font=f_reg, fill=(255, 255, 255), anchor="mm")

            rendered = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
            cv2.putText(mask, "intel", (tx - 210, ty + 50), cv2.FONT_HERSHEY_DUPLEX, 4.5, 255, 12, cv2.LINE_AA)
            halo = cv2.GaussianBlur(mask, (0, 0), 22).astype(np.float32) / 255.0
            bloom = (halo * 0.65)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)
            frame[:] = np.clip(rendered.astype(np.float32) + bloom, 0, 255).astype(np.uint8)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 3")


def render_scene_4(out_mp4: Path, num_frames=120):
    """SCENE 4: Smooth camera drift over East Asia with pure glowing white rim tracing China."""
    print("Rendering Scene 4 with dynamic camera...")
    # Camera drifts slowly in scale and position
    cam = DynamicCamera(start_pose=(102.0, 36.0, 10.0),
                        end_pose=(106.0, 34.5, 11.5),
                        total_frames=num_frames)

    china_rings = GEO.get_country_rings("China")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 14, 12),
                                land_color=(20, 18, 16), border_color=(35, 32, 28))

        china_polys = cam.project_rings(china_rings, c_lon, c_lat, scale)

        p_draw = ease_in_out(f / 75.0)
        DynamicEffects.draw_country_fill(frame, china_polys, (10, 8, 8), opacity=0.55 * p_draw)
        DynamicEffects.draw_outline_glow(frame, china_polys, COLOR_WHITE, progress=p_draw,
                                         thickness=3, halo_strength=1.5)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 4")


def render_scene_5(out_mp4: Path, num_frames=120):
    """SCENE 5: Slow cinematic push-in on Vietnam with intense red neon outline."""
    print("Rendering Scene 5 with dynamic camera...")
    cam = DynamicCamera(start_pose=(107.0, 17.0, 30.0),
                        end_pose=(108.2, 15.5, 37.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(14, 12, 10),
                                land_color=(22, 20, 18), border_color=(32, 30, 26))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        p_draw = ease_in_out(f / 70.0)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=p_draw,
                                         thickness=3, halo_strength=1.6)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 5")


def render_scene_6(out_mp4: Path, num_frames=120):
    """SCENE 6: Dynamic 2.5D perspective camera tracking + focus ring + massive glowing 'LA NUOVA CINA'."""
    print("Rendering Scene 6 with dynamic camera...")
    # Oversized base for tilt warping
    pad = 300
    BIG_W, BIG_H = WIDTH + pad * 2, HEIGHT + pad * 2

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        t_cam = ease_in_out(f / float(num_frames))
        # Camera zoom & pan drift
        c_lon = lerp(106.5, 108.5, t_cam)
        c_lat = lerp(17.5, 16.0, t_cam)
        scale = lerp(20.0, 24.5, t_cam)

        # Render oversized flat plate
        cam = DynamicCamera((c_lon, c_lat, scale), (c_lon, c_lat, scale), 1)
        base_big = cam.render_base(c_lon, c_lat, scale, ocean_color=(16, 14, 12),
                                   land_color=(24, 22, 20), border_color=(40, 38, 34))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)
        DynamicEffects.draw_country_fill(base_big, vn_polys, COLOR_RED_VIVID, opacity=0.98)
        DynamicEffects.draw_outline_glow(base_big, vn_polys, COLOR_RED_VIVID, progress=1.0, thickness=2)

        # Dynamic perspective warp (2.5D camera tilt)
        tilt_amount = lerp(0.14, 0.11, t_cam)
        src_pts = np.float32([[pad, pad], [pad + WIDTH, pad], [pad + WIDTH, pad + HEIGHT], [pad, pad + HEIGHT]])
        tilt_margin = int(WIDTH * tilt_amount)
        dst_pts = np.float32([[tilt_margin, -40],
                              [WIDTH - tilt_margin, -40],
                              [WIDTH + 100, HEIGHT + 80],
                              [-100, HEIGHT + 80]])
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)

        frame = cv2.warpPerspective(base_big, M, (WIDTH, HEIGHT), borderMode=cv2.BORDER_REPLICATE)

        # Track Vietnam center into 2.5D screen coordinates
        vn_pt_2d = cam.project_point(107.8, 16.0, c_lon, c_lat, scale)
        v_homo = np.array([vn_pt_2d[0], vn_pt_2d[1], 1.0], dtype=np.float32)
        v_warped = M.dot(v_homo)
        ring_center = (int(v_warped[0] / v_warped[2]), int(v_warped[1] / v_warped[2]))

        # Focus ring scaling and pulsing
        p_ring = ease_out(f / 40.0)
        rx = int(140 * p_ring)
        if rx > 5:
            cv2.ellipse(frame, ring_center, (rx, rx), -15, 0, 360, COLOR_WHITE, 4, cv2.LINE_AA)
            cv2.ellipse(frame, ring_center, (rx + 6, rx + 6), -15, 0, 360, (180, 180, 180), 1, cv2.LINE_AA)

        # Accent dashes
        if p_ring > 0.4:
            cv2.line(frame, (ring_center[0] - 120, ring_center[1] - 120),
                     (ring_center[0] - 190, ring_center[1] - 190), COLOR_WHITE, 3, cv2.LINE_AA)
            cv2.line(frame, (ring_center[0] - 210, ring_center[1] - 210),
                     (ring_center[0] - 270, ring_center[1] - 270), COLOR_WHITE, 3, cv2.LINE_AA)

        # Glowing kinetic typography 'LA NUOVA CINA' (moves with camera tracking)
        p_title = ease_out((f - 20) / 35.0)
        if p_title > 0:
            font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=108)
            temp_txt = Image.new("RGBA", (1300, 240), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(temp_txt)
            t_draw.text((650, 120), "LA NUOVA CINA", font=font,
                        fill=(255, 255, 255, int(255 * p_title)), anchor="mm")
            rotated = temp_txt.rotate(22, resample=Image.BICUBIC, expand=True)

            txt_x = int(WIDTH * 0.08 + t_cam * 30.0)
            txt_y = int(HEIGHT * 0.54 - t_cam * 20.0)
            txt_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            txt_layer.paste(rotated, (txt_x, txt_y), rotated)

            np_txt = np.asarray(txt_layer)
            alpha_mask = np_txt[:, :, 3].astype(np.float32) / 255.0

            glow = cv2.GaussianBlur((alpha_mask * 255).astype(np.uint8), (0, 0), 18).astype(np.float32) / 255.0
            bloom = (glow * 0.55)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)

            f_float = frame.astype(np.float32) * (1.0 - alpha_mask[:, :, None]) + \
                      np_txt[:, :, :3][:, :, ::-1].astype(np.float32) * alpha_mask[:, :, None] + bloom
            frame[:] = np.clip(f_float, 0, 255).astype(np.uint8)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 6")


def render_scene_7(out_mp4: Path, num_frames=120):
    """SCENE 7: Dynamic global pan & zoom along transcontinental flight route + '194 mld $' metric."""
    print("Rendering Scene 7 with dynamic camera...")
    # Camera glides westward across the globe following the route
    cam = DynamicCamera(start_pose=(-25.0, 28.0, 3.8),
                        end_pose=(5.0, 22.0, 4.4),
                        total_frames=num_frames)

    usa_rings = GEO.get_country_rings("United States of America")
    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 14, 12),
                                land_color=(25, 22, 20), border_color=(40, 38, 34))

        # Project countries dynamically
        usa_polys = cam.project_rings(usa_rings, c_lon, c_lat, scale)
        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        p_in = ease_out(f / 25.0)
        DynamicEffects.draw_country_fill(frame, usa_polys, COLOR_BLUE_VIVID, opacity=0.90 * p_in)
        DynamicEffects.draw_outline_glow(frame, usa_polys, COLOR_BLUE_VIVID, progress=1.0, thickness=2)

        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.95 * p_in)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, thickness=2)

        # Dynamic point anchors tracking with the globe
        p1 = cam.project_point(-98.0, 39.0, c_lon, c_lat, scale)  # USA
        p2 = cam.project_point(107.0, 16.0, c_lon, c_lat, scale)  # Vietnam

        # Animated curved dashed trajectory
        p_route = ease_in_out((f - 12) / 50.0)
        if p_route > 0:
            ctrl = (int((p1[0] + p2[0]) / 2.0 - 50), int((p1[1] + p2[1]) / 2.0 - 320))
            steps = 140
            t_vals = np.linspace(0.0, max(0.0, min(1.0, p_route)), int(steps * p_route) + 2)
            curve_pts = []
            for t in t_vals:
                bx = (1 - t) ** 2 * p1[0] + 2 * (1 - t) * t * ctrl[0] + t ** 2 * p2[0]
                by = (1 - t) ** 2 * p1[1] + 2 * (1 - t) * t * ctrl[1] + t ** 2 * p2[1]
                curve_pts.append((int(bx), int(by)))

            acc_dist = 0.0
            dash_len, gap_len = 18, 12
            for i in range(len(curve_pts) - 1):
                pt_a, pt_b = curve_pts[i], curve_pts[i + 1]
                d = math.hypot(pt_b[0] - pt_a[0], pt_b[1] - pt_a[1])
                if (acc_dist % (dash_len + gap_len)) < dash_len:
                    cv2.line(frame, pt_a, pt_b, COLOR_WHITE, 3, cv2.LINE_AA)
                acc_dist += d

        # Massive floating metric '194 mld $' tracking dynamically along curve
        p_metric = ease_out((f - 30) / 25.0)
        if p_metric > 0:
            temp_txt = Image.new("RGBA", (700, 180), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(temp_txt)
            f_val = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=76)
            t_draw.text((353, 93), "194 mld $", font=f_val,
                        fill=(0, 0, 0, int(180 * p_metric)), anchor="mm")
            t_draw.text((350, 90), "194 mld $", font=f_val,
                        fill=(255, 255, 255, int(255 * p_metric)), anchor="mm")

            rotated = temp_txt.rotate(-18, resample=Image.BICUBIC, expand=True)

            txt_x = int(WIDTH * 0.50 + (f / float(num_frames)) * 40.0)
            txt_y = int(HEIGHT * 0.12 - (f / float(num_frames)) * 20.0)
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_frame.paste(rotated, (txt_x, txt_y), rotated)
            frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 7")


def main():
    parser = argparse.ArgumentParser(description="Render cinematic dynamic map motions")
    parser.add_argument("--scene", type=int, choices=range(1, 8), help="Render specific scene")
    parser.add_argument("--frames", type=int, default=120, help="Frames per scene (default 120 = 4s)")
    args = parser.parse_args()

    scenes = {
        1: render_scene_1,
        2: render_scene_2,
        3: render_scene_3,
        4: render_scene_4,
        5: render_scene_5,
        6: render_scene_6,
        7: render_scene_7,
    }

    if args.scene:
        scenes[args.scene](OUT_DIR / f"scene_{args.scene}.mp4", args.frames)
    else:
        for idx in range(1, 8):
            scenes[idx](OUT_DIR / f"scene_{idx}.mp4", args.frames)

    print(f"\nAll dynamic scenes rendered to: {OUT_DIR}")


if __name__ == "__main__":
    main()
