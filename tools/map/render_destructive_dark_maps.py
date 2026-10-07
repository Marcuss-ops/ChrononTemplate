#!/usr/bin/env python3
"""Destructive Dark Geopolitical Map Animations (5 Distinct Country Motion Styles).

Features 5 distinct, high-impact dark map motion styles with red glow:
1. ITALY: Tactical Radar Scan & Target Lock HUD with GPS Coordinates
2. JAPAN: Archipelago Chain-Reaction Wave & Pacific Pulse
3. RUSSIA: Continental Laser Trace & Dynamic Area Metric (17.1 Mln km²)
4. GERMANY: Central Europe Logistic Network with Inter-City Beams
5. SAUDI ARABIA: Desert Grid, Strategic Chokepoints & Red Sea / Gulf Corridors

All rendered with NVIDIA GPU NVENC hardware acceleration at 1080p 30 FPS.
"""
from __future__ import annotations

import argparse
import concurrent.futures
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
OUT_DIR = CHRONON_TEMPLATE / "out/destructive_dark_maps"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Aesthetic color palettes (BGR for OpenCV)
COLOR_OCEAN_DARK = (14, 12, 10)         # Deep black/charcoal ocean
COLOR_OCEAN_BLUE = (120, 68, 42)        # Steel blue ocean (Latin America style)
COLOR_LAND_DARK = (24, 21, 18)          # Landmass slate
COLOR_LAND_DEEP = (16, 14, 12)          # Darker landmass
COLOR_BORDER_MUTED = (44, 40, 36)       # Country boundaries
COLOR_GRID_BLUE = (145, 95, 65)         # Cartographic grid lines
COLOR_GRID_CYAN = (180, 140, 80)        # Bright grid accents

COLOR_RED_VIVID = (20, 25, 245)         # Saturated geopolitical red #F51914
COLOR_RED_GLOW = (40, 45, 255)          # Bright neon red core
COLOR_WHITE = (255, 255, 255)
COLOR_GOLD = (30, 210, 255)


def smooth_swoop(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3

def ease_in_cubic(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * t

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class GeoEngine:
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
                    arr = np.asarray(r, dtype=np.float32)
                    stride = max(1, math.ceil(len(arr) / 600))
                    arr_country = arr[::stride]
                    if len(arr_country) >= 3:
                        country_list.append(arr_country)

                    arr_land = arr[::4]
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
    def __init__(self, start_pose: tuple[float, float, float],
                 end_pose: tuple[float, float, float],
                 total_frames: int):
        self.start_pose = start_pose
        self.end_pose = end_pose
        self.total_frames = max(1, total_frames)

    def get_pose(self, frame_idx: int) -> tuple[float, float, float]:
        t = smooth_swoop(frame_idx / float(self.total_frames))
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
                    border_color=COLOR_BORDER_MUTED, with_grid: bool = True) -> np.ndarray:
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = ocean_color

        if with_grid:
            # Cartographic coordinate grid like Latin America scene
            for x in range(0, WIDTH, 75):
                cv2.line(frame, (x, 0), (x, HEIGHT), COLOR_GRID_BLUE, 1, cv2.LINE_AA)
            for y in range(0, HEIGHT, 75):
                cv2.line(frame, (0, y), (WIDTH, y), COLOR_GRID_BLUE, 1, cv2.LINE_AA)

        lon_margin = (WIDTH / 2.0 + 200) / max(0.1, scale)
        vis_min_lon = c_lon - lon_margin
        vis_max_lon = c_lon + lon_margin

        c_lat_clamped = max(-85.0, min(85.0, c_lat))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        scale_deg = scale * (180.0 / math.pi)

        ym_top = cy_m - (-200 - HEIGHT / 2.0) / scale_deg
        ym_bot = cy_m - (HEIGHT + 200 - HEIGHT / 2.0) / scale_deg
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
                          thickness: int = 3, halo_strength: float = 1.2):
        if progress <= 0.001 or not polys:
            return
        edge = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)

        if progress >= 0.999:
            cv2.polylines(edge, polys, True, 255, thickness, cv2.LINE_AA)
        else:
            for poly in polys:
                if len(poly) < 2:
                    continue
                seg_lens = np.sqrt(np.sum(np.diff(poly.astype(np.float64), axis=0) ** 2, axis=1))
                total_len = float(seg_lens.sum())
                budget = total_len * progress
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

        base_f = frame.astype(np.float32)
        c_f = np.asarray(color_bgr, dtype=np.float32)[None, None, :]
        for sigma, weight in [(24, 0.40 * halo_strength), (10, 0.65 * halo_strength), (3, 0.90 * halo_strength)]:
            halo = cv2.GaussianBlur(edge, (0, 0), sigma).astype(np.float32) / 255.0
            a = (halo * weight)[:, :, None]
            base_f = base_f * (1.0 - a) + c_f * a

        rim = (edge.astype(np.float32) / 255.0)[:, :, None]
        bright = np.clip(c_f * 0.6 + 255.0 * 0.4, 0, 255)
        base_f = base_f * (1.0 - rim) + bright * rim
        frame[:] = np.clip(base_f, 0, 255).astype(np.uint8)

    @staticmethod
    def draw_speech_pin(frame: np.ndarray, text: str, anchor_pt: tuple[int, int], progress: float,
                        subtitle: str = ""):
        """Authentic speech-bubble pin matching the Latin America style."""
        if progress <= 0.001:
            return
        p = ease_out_cubic(progress)
        font_title = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), size=23)
        font_sub = ImageFont.truetype(str(FONTS_DIR / "Inter-Regular.ttf"), size=15) if subtitle else None

        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font_title)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        if subtitle:
            s_box = d.textbbox((0, 0), subtitle, font=font_sub)
            tw = max(tw, s_box[2] - s_box[0])
            th += s_box[3] - s_box[1] + 6

        pad_x, pad_y = 18, 10
        w = int((tw + pad_x * 2) * p)
        h = int((th + pad_y * 2) * p)
        tail_h = int(10 * p)
        if w < 10 or h < 10:
            return

        tot_w = w + 40
        tot_h = h + tail_h + 20

        img = Image.new("RGBA", (tot_w, tot_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cx = tot_w // 2
        top = 10
        rect_box = [cx - w // 2, top, cx + w // 2, top + h]
        draw.rounded_rectangle(rect_box, radius=5, fill=(255, 255, 255, 255))
        tri = [(cx - 7, top + h - 1), (cx + 7, top + h - 1), (cx, top + h + tail_h)]
        draw.polygon(tri, fill=(255, 255, 255, 255))

        if p > 0.6:
            if subtitle:
                draw.text((cx, top + 14), text, font=font_title, fill=(15, 18, 24, int(255 * p)), anchor="mm")
                draw.text((cx, top + 34), subtitle, font=font_sub, fill=(110, 115, 125, int(255 * p)), anchor="mm")
            else:
                draw.text((cx, top + h // 2), text, font=font_title, fill=(15, 18, 24, int(255 * p)), anchor="mm")

        np_img = np.asarray(img)
        shadow = cv2.GaussianBlur(np_img[:, :, 3], (0, 0), 4)
        shadow_rgba = np.zeros_like(np_img)
        shadow_rgba[:, :, :3] = 0
        shadow_rgba[:, :, 3] = (shadow.astype(np.float32) * 0.45).astype(np.uint8)
        M = np.float32([[1, 0, 0], [0, 1, 3]])
        shadow_shifted = cv2.warpAffine(shadow_rgba, M, (tot_w, tot_h))
        comp = Image.alpha_composite(Image.fromarray(shadow_shifted), img)

        px = anchor_pt[0] - tot_w // 2
        py = anchor_pt[1] - (top + h + tail_h)

        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        pil_frame.paste(comp, (px, py), comp)
        frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)


def write_video_h264(frames: list[np.ndarray], out_path: Path):
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
        str(out_path)
    ]
    try:
        proc = subprocess.Popen(cmd_nvenc, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for f in frames:
            proc.stdin.write(f.tobytes())
        proc.stdin.close()
        proc.wait()
        if proc.returncode == 0:
            return
    except Exception:
        pass

    # CPU fallback
    cmd_cpu = [
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
    proc = subprocess.Popen(cmd_cpu, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in frames:
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    proc.wait()


# -----------------------------------------------------------------------------
# 5 DISTINCT DESTRUCTIVE DARK ANIMATIONS (1 NATION PER VIDEO)
# -----------------------------------------------------------------------------

def render_italy_radar_lock(out_mp4: Path, num_frames=120):
    """1. ITALY: Tactical Radar Scan & Target Lock HUD with GPS Coordinates."""
    print("Rendering 1/5: Italy Tactical Radar Lock...")
    # Camera starts over high Europe and dives tightly into Italy
    cam = DynamicCamera(start_pose=(10.0, 48.0, 9.0),
                        end_pose=(12.8, 42.0, 36.0),
                        total_frames=num_frames)

    it_rings = GEO.get_country_rings("Italy")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 40, 36), with_grid=True)

        it_polys = cam.project_rings(it_rings, c_lon, c_lat, scale)
        it_center = cam.project_point(12.5, 41.9, c_lon, c_lat, scale)

        p_lock = smooth_swoop((f - 18) / 35.0)

        # Radar sweep angle
        angle_deg = (f * 9.0) % 360.0
        angle_rad = math.radians(angle_deg)
        radar_len = 500
        rx = int(it_center[0] + radar_len * math.cos(angle_rad))
        ry = int(it_center[1] + radar_len * math.sin(angle_rad))
        cv2.line(frame, it_center, (rx, ry), (80, 240, 180), 2, cv2.LINE_AA)

        # Country glow on lock
        if p_lock > 0:
            DynamicEffects.draw_country_fill(frame, it_polys, COLOR_RED_VIVID, opacity=0.96 * p_lock)
            DynamicEffects.draw_outline_glow(frame, it_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.4)

            # Target Lock Brackets around Italy
            bw = int(180 * (2.0 - p_lock))
            bh = int(240 * (2.0 - p_lock))
            cx, cy = it_center
            corner_len = 24
            # 4 corners
            corners = [
                ((cx - bw, cy - bh), (cx - bw + corner_len, cy - bh), (cx - bw, cy - bh + corner_len)),
                ((cx + bw, cy - bh), (cx + bw - corner_len, cy - bh), (cx + bw, cy - bh + corner_len)),
                ((cx - bw, cy + bh), (cx - bw + corner_len, cy + bh), (cx - bw, cy + bh - corner_len)),
                ((cx + bw, cy + bh), (cx + bw - corner_len, cy + bh), (cx + bw, cy + bh - corner_len)),
            ]
            for c_pt, p_h, p_v in corners:
                cv2.line(frame, c_pt, p_h, COLOR_WHITE, 3, cv2.LINE_AA)
                cv2.line(frame, c_pt, p_v, COLOR_WHITE, 3, cv2.LINE_AA)

        # Pin with GPS coordinates
        DynamicEffects.draw_speech_pin(frame, "ITALIA", it_center, (f - 28) / 22.0, subtitle="41.9° N, 12.5° E")

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Italy")


def render_japan_archipelago_chain(out_mp4: Path, num_frames=120):
    """2. JAPAN: Archipelago Chain-Reaction Wave & Pacific Pulse."""
    print("Rendering 2/5: Japan Archipelago Chain...")
    cam = DynamicCamera(start_pose=(147.0, 33.0, 9.5),
                        end_pose=(138.5, 37.0, 27.0),
                        total_frames=num_frames)

    jp_rings = GEO.get_country_rings("Japan")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(42, 38, 35), with_grid=True)

        jp_polys = cam.project_rings(jp_rings, c_lon, c_lat, scale)

        # Sequential wave ignition along latitude (North to South)
        tokyo_pt = cam.project_point(139.69, 35.68, c_lon, c_lat, scale)

        p_wave = smooth_swoop((f - 10) / 45.0)
        DynamicEffects.draw_country_fill(frame, jp_polys, COLOR_RED_VIVID, opacity=0.96 * p_wave)
        DynamicEffects.draw_outline_glow(frame, jp_polys, COLOR_RED_VIVID, progress=p_wave, halo_strength=1.5)

        # Expanding circular seismic ripples in Pacific from Tokyo
        p_ripple = (f - 30) / 70.0
        if p_ripple > 0:
            for r_idx in range(3):
                r_phase = ((f - 30 + r_idx * 18) % 60) / 60.0
                rad = int(r_phase * 340)
                alpha = (1.0 - r_phase) * 0.7
                if rad > 5:
                    overlay = frame.copy()
                    cv2.circle(overlay, tokyo_pt, rad, COLOR_RED_VIVID, 3, cv2.LINE_AA)
                    cv2.circle(overlay, tokyo_pt, rad + 4, (255, 255, 255), 1, cv2.LINE_AA)
                    frame[:] = cv2.addWeighted(frame, 1.0 - alpha, overlay, alpha, 0)

        # Tokyo pin & country card
        DynamicEffects.draw_speech_pin(frame, "JAPAN", tokyo_pt, (f - 35) / 22.0, subtitle="PACIFIC FRONT")

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Japan")


def render_russia_continental_laser(out_mp4: Path, num_frames=120):
    """3. RUSSIA: Continental Laser Trace & Dynamic Area Metric (17.1 Mln km²)."""
    print("Rendering 3/5: Russia Continental Laser...")
    # Epic transcontinental glide across Eurasia
    cam = DynamicCamera(start_pose=(45.0, 62.0, 4.4),
                        end_pose=(95.0, 58.0, 5.8),
                        total_frames=num_frames)

    ru_rings = GEO.get_country_rings("Russia")
    font_metric = ImageFont.truetype(str(FONTS_DIR / "Urbanist.ttf"), 68)

    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 13, 11),
                                land_color=COLOR_LAND_DEEP, border_color=(38, 35, 32), with_grid=True)

        ru_polys = cam.project_rings(ru_rings, c_lon, c_lat, scale)

        p_laser = smooth_swoop(f / 65.0)
        DynamicEffects.draw_country_fill(frame, ru_polys, COLOR_RED_VIVID, opacity=0.94 * p_laser)
        DynamicEffects.draw_outline_glow(frame, ru_polys, COLOR_RED_VIVID, progress=p_laser, halo_strength=1.6)

        # Moscow anchor
        moscow_pt = cam.project_point(37.61, 55.75, c_lon, c_lat, scale)
        DynamicEffects.draw_speech_pin(frame, "RUSSIA", moscow_pt, (f - 15) / 20.0, subtitle="FEDERATION")

        # Huge kinetic counter badge '17.1 Mln km²'
        p_metric = ease_out_cubic((f - 25) / 45.0)
        if p_metric > 0:
            val = p_metric * 17.1
            text_str = f"{val:.1f} Mln km²" if p_metric < 0.99 else "17.1 Mln km²"

            temp_img = Image.new("RGBA", (650, 160), (0, 0, 0, 0))
            d = ImageDraw.Draw(temp_img)
            d.text((325, 80), text_str, font=font_metric, fill=(255, 255, 255, 255), anchor="mm")

            np_m = np.asarray(temp_img)
            shadow = cv2.GaussianBlur(np_m[:, :, 3], (0, 0), 12)
            shadow_rgba = np.zeros_like(np_m)
            shadow_rgba[:, :, :3] = 0
            shadow_rgba[:, :, 3] = (shadow.astype(np.float32) * 0.8).astype(np.uint8)
            M_s = np.float32([[1, 0, 2], [0, 1, 4]])
            shadow_shifted = cv2.warpAffine(shadow_rgba, M_s, (650, 160))
            comp_metric = Image.alpha_composite(Image.fromarray(shadow_shifted), temp_img)

            # Paste in upper right
            mx, my = WIDTH - 680, 80
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_frame.paste(comp_metric, (mx, my), comp_metric)
            frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Russia")


def render_germany_industrial_nodes(out_mp4: Path, num_frames=120):
    """4. GERMANY: Central Europe Hub & Logistic Network Beams."""
    print("Rendering 4/5: Germany Industrial Network...")
    cam = DynamicCamera(start_pose=(10.0, 52.0, 10.0),
                        end_pose=(10.4, 51.2, 38.0),
                        total_frames=num_frames)

    de_rings = GEO.get_country_rings("Germany")
    cities = [
        ("Berlin", 13.40, 52.52),
        ("Hamburg", 9.99, 53.55),
        ("Frankfurt", 8.68, 50.11),
        ("Munich", 11.58, 48.13),
    ]

    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 42, 38), with_grid=True)

        de_polys = cam.project_rings(de_rings, c_lon, c_lat, scale)

        p_fill = smooth_swoop(f / 45.0)
        DynamicEffects.draw_country_fill(frame, de_polys, COLOR_RED_VIVID, opacity=0.96 * p_fill)
        DynamicEffects.draw_outline_glow(frame, de_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.3)

        # Project city nodes
        city_pts = [cam.project_point(lon, lat, c_lon, c_lat, scale) for _, lon, lat in cities]

        # Inter-city laser network lines
        p_net = ease_out_cubic((f - 18) / 35.0)
        if p_net > 0:
            lines = [(0, 1), (0, 2), (1, 2), (2, 3), (0, 3)]
            for i1, i2 in lines:
                pt1, pt2 = city_pts[i1], city_pts[i2]
                cur_pt = (int(pt1[0] + (pt2[0] - pt1[0]) * p_net),
                          int(pt1[1] + (pt2[1] - pt1[1]) * p_net))
                cv2.line(frame, pt1, cur_pt, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.line(frame, pt1, cur_pt, COLOR_RED_VIVID, 6, cv2.LINE_AA)

        # Pulse city nodes
        for idx, (name, _, _) in enumerate(cities):
            pt = city_pts[idx]
            cv2.circle(frame, pt, 7, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 12, COLOR_RED_VIVID, 2, cv2.LINE_AA)

        # Country speech pin
        center_de = cam.project_point(10.4, 51.2, c_lon, c_lat, scale)
        DynamicEffects.draw_speech_pin(frame, "GERMANY", (center_de[0], center_de[1] - 40),
                                       (f - 25) / 20.0, subtitle="INDUSTRIAL CORE")

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Germany")


def render_saudi_arabia_desert_pipeline(out_mp4: Path, num_frames=120):
    """5. SAUDI ARABIA: Desert Grid, Strategic Chokepoints & Red Sea / Gulf Corridors."""
    print("Rendering 5/5: Saudi Arabia Strategic Chokepoints...")
    # Flight from Red Sea diagonally across Saudi desert towards Persian Gulf
    cam = DynamicCamera(start_pose=(39.0, 20.0, 11.5),
                        end_pose=(48.0, 24.5, 23.0),
                        total_frames=num_frames)

    sa_rings = GEO.get_country_rings("Saudi Arabia")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=COLOR_LAND_DEEP, border_color=(45, 40, 36), with_grid=True)

        sa_polys = cam.project_rings(sa_rings, c_lon, c_lat, scale)

        p_fill = smooth_swoop(f / 45.0)
        DynamicEffects.draw_country_fill(frame, sa_polys, COLOR_RED_VIVID, opacity=0.96 * p_fill)
        DynamicEffects.draw_outline_glow(frame, sa_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.4)

        # Strategic Chokepoints: Strait of Hormuz & Bab el-Mandeb
        hormuz_pt = cam.project_point(56.45, 26.56, c_lon, c_lat, scale)
        mandeb_pt = cam.project_point(43.33, 12.58, c_lon, c_lat, scale)
        riyadh_pt = cam.project_point(46.67, 24.71, c_lon, c_lat, scale)

        # Curved dashed maritime trade corridors
        p_route = ease_out_cubic((f - 15) / 45.0)
        if p_route > 0:
            ctrl = (int((mandeb_pt[0] + hormuz_pt[0]) / 2.0 + 80),
                    int((mandeb_pt[1] + hormuz_pt[1]) / 2.0 + 100))
            steps = 80
            cur_steps = int(steps * p_route)
            for i in range(0, cur_steps, 2):
                t0 = i / float(steps)
                t1 = min(1.0, (i + 1.2) / float(steps))
                p0 = (int((1 - t0)**2 * mandeb_pt[0] + 2*(1 - t0)*t0 * ctrl[0] + t0**2 * hormuz_pt[0]),
                      int((1 - t0)**2 * mandeb_pt[1] + 2*(1 - t0)*t0 * ctrl[1] + t0**2 * hormuz_pt[1]))
                p1 = (int((1 - t1)**2 * mandeb_pt[0] + 2*(1 - t1)*t1 * ctrl[0] + t1**2 * hormuz_pt[0]),
                      int((1 - t1)**2 * mandeb_pt[1] + 2*(1 - t1)*t1 * ctrl[1] + t1**2 * hormuz_pt[1]))
                cv2.line(frame, p0, p1, (255, 255, 255), 3, cv2.LINE_AA)

        # Chokepoint target pulses
        for pt, label in [(hormuz_pt, "HORMUZ"), (mandeb_pt, "BAB EL-MANDEB")]:
            cv2.circle(frame, pt, 6, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 11, (20, 220, 255), 2, cv2.LINE_AA)

        DynamicEffects.draw_speech_pin(frame, "SAUDI ARABIA", riyadh_pt, (f - 25) / 20.0, subtitle="2.15 Mln km²")

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Saudi Arabia")


def run_single(scene_id: int):
    scenes = {
        1: (render_italy_radar_lock, OUT_DIR / "01_italy_radar_lock.mp4"),
        2: (render_japan_archipelago_chain, OUT_DIR / "02_japan_archipelago_chain.mp4"),
        3: (render_russia_continental_laser, OUT_DIR / "03_russia_continental_laser.mp4"),
        4: (render_germany_industrial_nodes, OUT_DIR / "04_germany_industrial_nodes.mp4"),
        5: (render_saudi_arabia_desert_pipeline, OUT_DIR / "05_saudi_arabia_desert_pipeline.mp4"),
    }
    fn, path = scenes[scene_id]
    fn(path)


def main():
    parser = argparse.ArgumentParser(description="Render destructive dark map animations (GPU accelerated)")
    parser.add_argument("--scene", type=int, choices=range(1, 6), help="Render specific scene 1-5")
    args = parser.parse_args()

    if args.scene:
        run_single(args.scene)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
            list(executor.map(run_single, range(1, 6)))

    print(f"\nAll 5 destructive dark scenes rendered to: {OUT_DIR}")


if __name__ == "__main__":
    main()
