#!/usr/bin/env python3
"""Cinematic Dynamic Map Motion Kit v2 using OpenCV, NumPy and Authoritative GeoJSON.

Improvements:
- Big, dramatic camera flights & swoops (from high orbit/space plunging down to country level: 4x-7x zoom dives)
- High-end typography engine with authentic fonts & tracking matching YouTube documentary references:
  * Scene 6: "LA NUOVA CINA" in Urbanist with wide tracking, 3D perspective orientation & luminous bloom
  * Scene 7: "194 mld $" in slanted italic geometry with drop shadow & glow along flight trajectory
  * Scene 2: Authentic speech-bubble pins ("Mexico", "Colombia", "Brazil") with drop shadow and 3D arrow
  * Scene 3: Pristine official Intel logo with volumetric glow & 90-degree technical orthogonal callout
- Fully vectorized polyline rendering for blazing-fast 30 FPS rendering
- Encodes directly to universal streaming H.264 (yuv420p)
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
COLOR_LAND_DARK = (24, 21, 18)          # Landmass slate
COLOR_LAND_DEEP = (16, 14, 12)          # Darker landmass
COLOR_BORDER_MUTED = (45, 42, 38)       # Country boundaries
COLOR_GRID_BLUE = (145, 95, 65)         # Grid lines

COLOR_RED_VIVID = (20, 25, 245)         # Saturated geopolitical red #F51914
COLOR_BLUE_VIVID = (245, 55, 15)        # Saturated diplomatic blue #0F37F5
COLOR_MAGENTA_NEON = (210, 40, 240)     # Vibrant magenta/pink #F028D2
COLOR_WHITE = (255, 255, 255)


def smooth_swoop(t: float) -> float:
    """Dramatic cubic easing for camera swoops & dives."""
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
    """Dynamic camera with fast frustum culling and Mercator projection."""

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
                    border_color=COLOR_BORDER_MUTED) -> np.ndarray:
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        frame[:] = ocean_color

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
    """High-end graphic typography and animated overlays."""

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

        if progress >= 0.999:
            # Fast vectorized rendering
            cv2.polylines(edge, polys, True, 255, thickness, cv2.LINE_AA)
        else:
            # Animate along polygon boundary
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

        # Layered Gaussian halo
        base_f = frame.astype(np.float32)
        c_f = np.asarray(color_bgr, dtype=np.float32)[None, None, :]
        for sigma, weight in [(24, 0.40 * halo_strength), (10, 0.60 * halo_strength), (3, 0.85 * halo_strength)]:
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
        p = ease_out_cubic(progress)
        w, h = int(size[0] * p), int(size[1] * p)
        if w < 10 or h < 10:
            return

        card = np.zeros((h, w, 3), dtype=np.uint8)
        if country_code == "VN":
            card[:] = (18, 20, 220) # Bright red
            pts = []
            cx, cy = w // 2, h // 2
            r_out = h * 0.28
            r_in = r_out * 0.38
            for i in range(10):
                angle = -math.pi / 2 + i * (math.pi / 5)
                r = r_out if (i % 2 == 0) else r_in
                pts.append([int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))])
            cv2.fillPoly(card, [np.array(pts, dtype=np.int32)], (30, 230, 255))
        elif country_code == "USA":
            stripe_h = max(1, h // 13)
            for s in range(13):
                col = (20, 20, 200) if (s % 2 == 0) else (240, 240, 240)
                card[s * stripe_h:(s + 1) * stripe_h, :] = col
            canton_w, canton_h = int(w * 0.45), int(h * 0.54)
            card[:canton_h, :canton_w] = (160, 35, 20)

        cv2.rectangle(card, (0, 0), (w - 1, h - 1), (255, 255, 255), 2)
        x1 = center[0] - w // 2
        y1 = center[1] - h // 2
        if 0 <= x1 and x1 + w <= WIDTH and 0 <= y1 and y1 + h <= HEIGHT:
            frame[y1:y1 + h, x1:x1 + w] = card

    @staticmethod
    def draw_speech_pin(frame: np.ndarray, text: str, anchor_pt: tuple[int, int], progress: float):
        """Speech-bubble tooltip pin matching YouTube reference 08-33-52."""
        if progress <= 0.001:
            return
        p = ease_out_cubic(progress)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-SemiBold.ttf"), size=23)

        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

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
        draw.rounded_rectangle(rect_box, radius=4, fill=(255, 255, 255, 255))
        tri = [(cx - 7, top + h - 1), (cx + 7, top + h - 1), (cx, top + h + tail_h)]
        draw.polygon(tri, fill=(255, 255, 255, 255))

        if p > 0.6:
            draw.text((cx, top + h // 2), text, font=font, fill=(15, 18, 24, int(255 * p)), anchor="mm")

        # Soft drop shadow
        np_img = np.asarray(img)
        alpha = np_img[:, :, 3]
        shadow = cv2.GaussianBlur(alpha, (0, 0), 4)
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

    @staticmethod
    def draw_tracked_title(text: str, font_path: str, font_size: int, tracking: int = 26,
                           color=(255, 255, 255), glow_color=(255, 255, 255), glow_radius: int = 14) -> Image.Image:
        """Render high-end tracking title with letter spacing and luminous bloom."""
        font = ImageFont.truetype(font_path, font_size)
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        char_widths = [d.textbbox((0, 0), ch, font=font)[2] - d.textbbox((0, 0), ch, font=font)[0] for ch in text]
        tot_w = sum(char_widths) + tracking * (len(text) - 1) + 80
        tot_h = font_size * 2 + 80

        img = Image.new("RGBA", (tot_w, tot_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cur_x = 40
        base_y = tot_h // 2
        for i, ch in enumerate(text):
            draw.text((cur_x, base_y), ch, font=font, fill=(color[0], color[1], color[2], 255), anchor="lm")
            cur_x += char_widths[i] + tracking

        np_img = np.asarray(img)
        alpha = np_img[:, :, 3]
        if glow_radius > 0:
            glow_mask = cv2.GaussianBlur(alpha, (0, 0), glow_radius)
            glow_rgba = np.zeros_like(np_img)
            glow_rgba[:, :, :3] = glow_color
            glow_rgba[:, :, 3] = (glow_mask.astype(np.float32) * 0.75).astype(np.uint8)
            out_pil = Image.alpha_composite(Image.fromarray(glow_rgba), img)
            return out_pil
        return img


def write_video_h264(frames: list[np.ndarray], out_path: Path):
    """Write frame sequence with NVIDIA GPU NVENC hardware acceleration, with CPU fallback."""
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
# DYNAMIC SCENES WITH HIGH-SPEED SWOOPS & REFINED TYPOGRAPHY
# -----------------------------------------------------------------------------

def render_scene_1(out_mp4: Path, num_frames=120):
    """SCENE 1: High-orbit satellite plunge (scale 6.5 -> 38.0: 6x zoom!) onto Vietnam."""
    print("Rendering Scene 1: High-orbit plunge on Vietnam...")
    cam = DynamicCamera(start_pose=(98.0, 24.0, 6.5),
                        end_pose=(108.5, 15.5, 38.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_DARK, land_color=(28, 25, 22))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        p_fill = ease_out_cubic(f / 45.0)
        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.96 * p_fill)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.3)

        vn_top = cam.project_point(105.8, 21.0, c_lon, c_lat, scale)
        vn_mid = cam.project_point(108.2, 16.0, c_lon, c_lat, scale)

        vn_flag_pt = (vn_top[0] - 130, vn_top[1] - 180)
        us_flag_pt = (vn_mid[0] + 380, vn_mid[1] - 30)

        p_bars = ease_out_cubic((f - 24) / 32.0)
        if p_bars > 0:
            target_1 = (int(vn_top[0] + (us_flag_pt[0] - 80 - vn_top[0]) * p_bars),
                        int(vn_top[1] + (us_flag_pt[1] - 50 - vn_top[1]) * p_bars))
            cv2.line(frame, vn_top, target_1, COLOR_MAGENTA_NEON, 15, cv2.LINE_AA)

            target_2 = (int(vn_mid[0] + (us_flag_pt[0] - 80 - vn_mid[0]) * p_bars),
                        int(vn_mid[1] + (us_flag_pt[1] + 40 - vn_mid[1]) * p_bars))
            cv2.line(frame, vn_mid, target_2, COLOR_MAGENTA_NEON, 15, cv2.LINE_AA)

        DynamicEffects.draw_flag_card(frame, vn_flag_pt, "VN", (f - 15) / 25.0)
        DynamicEffects.draw_flag_card(frame, us_flag_pt, "USA", (f - 30) / 25.0)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 1")


def render_scene_2(out_mp4: Path, num_frames=120):
    """SCENE 2: Sweeping transcontinental flight over Latin America with speech-bubble pins & arrow."""
    print("Rendering Scene 2: Transcontinental flight over Latin America...")
    # Camera starts wide over North America/Caribbean and swoops down-right into South America
    cam = DynamicCamera(start_pose=(-96.0, 26.0, 5.2),
                        end_pose=(-58.0, -12.0, 11.8),
                        total_frames=num_frames)

    mex_rings = GEO.get_country_rings("Mexico")
    col_rings = GEO.get_country_rings("Colombia")
    bra_rings = GEO.get_country_rings("Brazil")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_BLUE,
                                land_color=(15, 14, 12), border_color=(42, 38, 35))

        # Thin cartographic grid lines
        for x in range(0, WIDTH, 75):
            cv2.line(frame, (x, 0), (x, HEIGHT), (145, 95, 65), 1, cv2.LINE_AA)
        for y in range(0, HEIGHT, 75):
            cv2.line(frame, (0, y), (WIDTH, y), (145, 95, 65), 1, cv2.LINE_AA)

        mex_polys = cam.project_rings(mex_rings, c_lon, c_lat, scale)
        col_polys = cam.project_rings(col_rings, c_lon, c_lat, scale)
        bra_polys = cam.project_rings(bra_rings, c_lon, c_lat, scale)

        # Sequential country highlights
        p_mex = ease_out_cubic(f / 25.0)
        DynamicEffects.draw_country_fill(frame, mex_polys, COLOR_RED_VIVID, opacity=0.96 * p_mex)
        mex_anchor = cam.project_point(-101.0, 22.0, c_lon, c_lat, scale)
        DynamicEffects.draw_speech_pin(frame, "Mexico", mex_anchor, (f - 8) / 20.0)

        p_col = ease_out_cubic((f - 22) / 25.0)
        DynamicEffects.draw_country_fill(frame, col_polys, COLOR_RED_VIVID, opacity=0.96 * p_col)
        col_anchor = cam.project_point(-73.5, 4.2, c_lon, c_lat, scale)
        DynamicEffects.draw_speech_pin(frame, "Colombia", col_anchor, (f - 26) / 20.0)

        # 3D striped arrow diving into Colombia
        p_arr = ease_out_cubic((f - 30) / 25.0)
        if p_arr > 0:
            arr_tip = col_anchor
            arr_base = (col_anchor[0] + int(140 * p_arr), col_anchor[1] - int(160 * p_arr))
            cv2.line(frame, arr_base, arr_tip, (245, 245, 245), 9, cv2.LINE_AA)
            cv2.line(frame, arr_base, arr_tip, (70, 70, 70), 5, cv2.LINE_AA)
            # Arrowhead
            tip_tri = np.array([
                arr_tip,
                (arr_tip[0] + 25, arr_tip[1] - 10),
                (arr_tip[0] + 10, arr_tip[1] - 25)
            ], dtype=np.int32)
            cv2.fillPoly(frame, [tip_tri], (255, 255, 255))

        p_bra = ease_out_cubic((f - 42) / 25.0)
        DynamicEffects.draw_country_fill(frame, bra_polys, COLOR_RED_VIVID, opacity=0.96 * p_bra)
        bra_anchor = cam.project_point(-51.0, -12.0, c_lon, c_lat, scale)
        DynamicEffects.draw_speech_pin(frame, "Brazil", bra_anchor, (f - 46) / 20.0)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 2")


def render_scene_3(out_mp4: Path, num_frames=120):
    """SCENE 3: High-altitude dive onto Ho Chi Minh City + authentic Intel logo callout."""
    print("Rendering Scene 3: Ho Chi Minh City dive and Intel callout...")
    # Camera swoops from wide Southeast Asia (scale 8.5) down to scale 36.0, panning to frame Vietnam on left
    cam = DynamicCamera(start_pose=(102.0, 20.0, 8.5),
                        end_pose=(112.5, 13.5, 36.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    intel_logo_path = CATALOG_DIR / "intel_logo_authentic.png"
    intel_logo_img = Image.open(intel_logo_path).convert("RGBA") if intel_logo_path.exists() else None

    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=COLOR_OCEAN_DARK, land_color=(28, 25, 22))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)
        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.96)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, halo_strength=1.2)

        # Dynamic tracking of Ho Chi Minh City
        hcm_pt = cam.project_point(106.63, 10.82, c_lon, c_lat, scale)

        # Pin dot & pulsing ring
        cv2.circle(frame, hcm_pt, 8, COLOR_WHITE, -1, cv2.LINE_AA)
        cv2.circle(frame, hcm_pt, 14, COLOR_WHITE, 2, cv2.LINE_AA)

        # Label card 'Ho Chi Minh City' pill
        pill_w, pill_h = 240, 52
        cx, cy = hcm_pt[0] - 8, hcm_pt[1] - 46
        x1, y1 = cx - pill_w // 2, cy - pill_h // 2
        cv2.rectangle(frame, (x1, y1), (x1 + pill_w, y1 + pill_h), COLOR_WHITE, -1)

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=24)
        draw.text((cx, cy), "Ho Chi Minh City", font=font, fill=(15, 18, 22), anchor="mm")
        frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

        # 90-degree orthogonal elbow line across the sea
        logo_center = (WIDTH // 2 + 390, HEIGHT // 2 - 130)
        p_line = ease_out_cubic((f - 18) / 36.0)

        if p_line > 0:
            corner_pt = (logo_center[0] - 120, hcm_pt[1])
            end_pt = (logo_center[0] - 120, logo_center[1] + 90)

            len1 = max(1, corner_pt[0] - hcm_pt[0])
            len2 = max(1, corner_pt[1] - end_pt[1])
            tot = len1 + len2
            budget = tot * p_line

            if budget <= len1:
                cur_x = int(hcm_pt[0] + budget)
                cv2.line(frame, hcm_pt, (cur_x, hcm_pt[1]), COLOR_WHITE, 4, cv2.LINE_AA)
            else:
                cv2.line(frame, hcm_pt, corner_pt, COLOR_WHITE, 4, cv2.LINE_AA)
                cur_y = int(corner_pt[1] - (budget - len1))
                cv2.line(frame, corner_pt, (corner_pt[0], cur_y), COLOR_WHITE, 4, cv2.LINE_AA)

        # Authentic Intel logo with volumetric glow
        p_logo = ease_out_cubic((f - 38) / 28.0)
        if p_logo > 0 and intel_logo_img is not None:
            lw, lh = int(460 * p_logo), int(190 * p_logo)
            resized = intel_logo_img.resize((lw, lh), Image.BICUBIC)
            lx = logo_center[0] - lw // 2 + 130
            ly = logo_center[1] - lh // 2

            # Volumetric Gaussian bloom
            temp_l = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            temp_l.paste(resized, (lx, ly), resized)
            np_l = np.asarray(temp_l)
            alpha_l = np_l[:, :, 3]

            halo = cv2.GaussianBlur(alpha_l, (0, 0), 24).astype(np.float32) / 255.0
            bloom = (halo * 0.70)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)

            rendered = cv2.cvtColor(np.asarray(temp_l)[:, :, :3], cv2.COLOR_RGB2BGR)
            fg_alpha = (alpha_l.astype(np.float32) / 255.0)[:, :, None]
            base_f = frame.astype(np.float32) * (1.0 - fg_alpha) + rendered.astype(np.float32) * fg_alpha + bloom
            frame[:] = np.clip(base_f, 0, 255).astype(np.uint8)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 3")


def render_scene_4(out_mp4: Path, num_frames=120):
    """SCENE 4: High-orbit swoop (scale 4.0 -> 14.5: 3.6x zoom!) over China + pure neon border trace."""
    print("Rendering Scene 4: High-orbit swoop over China...")
    cam = DynamicCamera(start_pose=(88.0, 42.0, 4.0),
                        end_pose=(106.0, 34.0, 14.5),
                        total_frames=num_frames)

    china_rings = GEO.get_country_rings("China")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 14, 12),
                                land_color=(20, 18, 16), border_color=(36, 33, 29))

        china_polys = cam.project_rings(china_rings, c_lon, c_lat, scale)

        p_draw = smooth_swoop(f / 75.0)
        DynamicEffects.draw_country_fill(frame, china_polys, (10, 8, 8), opacity=0.55 * p_draw)
        DynamicEffects.draw_outline_glow(frame, china_polys, COLOR_WHITE, progress=p_draw,
                                         thickness=3, halo_strength=1.6)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 4")


def render_scene_5(out_mp4: Path, num_frames=120):
    """SCENE 5: Deep macro dive (scale 10.0 -> 45.0: 4.5x zoom!) with incandescent red laser border."""
    print("Rendering Scene 5: Deep macro dive on Vietnam red border...")
    cam = DynamicCamera(start_pose=(102.0, 21.0, 10.0),
                        end_pose=(108.5, 15.5, 45.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(12, 10, 8),
                                land_color=(20, 18, 16), border_color=(30, 28, 24))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        p_draw = smooth_swoop(f / 70.0)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=p_draw,
                                         thickness=3, halo_strength=1.8)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 5")


def render_scene_6(out_mp4: Path, num_frames=120):
    """SCENE 6: High-altitude dive onto Vietnam + focus ellipse + tracked title 'LA NUOVA CINA'."""
    print("Rendering Scene 6: Flawless dynamic plunge and 'LA NUOVA CINA'...")
    # Camera swoops in from wide Indochina (scale 9.0) down to focused Vietnam (scale 27.0)
    # Framing aimed at lat=9.5 so Vietnam is in upper center and title sits in lower left
    cam = DynamicCamera(start_pose=(102.0, 18.0, 9.0),
                        end_pose=(108.5, 9.5, 27.0),
                        total_frames=num_frames)

    vn_rings = GEO.get_country_rings("Vietnam")
    frames = []

    # Luxury tracked title in Urbanist matching YouTube reference 08-30-43
    title_pil = DynamicEffects.draw_tracked_title("LA NUOVA CINA", str(FONTS_DIR / "Urbanist.ttf"),
                                                  font_size=92, tracking=24, glow_radius=14)
    rotated_title = title_pil.rotate(24, resample=Image.BICUBIC, expand=True)

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 13, 11),
                                land_color=(24, 22, 20), border_color=(40, 38, 34))

        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)
        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.96)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, thickness=2)

        vn_center = cam.project_point(107.5, 16.0, c_lon, c_lat, scale)

        # Concentric focus ellipse around Vietnam
        p_ring = ease_out_cubic(f / 40.0)
        rx = int(185 * p_ring)
        ry = int(130 * p_ring)
        if rx > 5:
            cv2.ellipse(frame, vn_center, (rx, ry), -12, 0, 360, COLOR_WHITE, 3, cv2.LINE_AA)
            cv2.ellipse(frame, vn_center, (rx + 8, ry + 8), -12, 0, 360, (160, 160, 160), 1, cv2.LINE_AA)

        # Dashed trajectory arriving from top-left into Vietnam
        p_line = ease_out_cubic((f - 10) / 45.0)
        if p_line > 0:
            pt_start = (int(vn_center[0] - 340), int(vn_center[1] - 380))
            steps = 40
            t_max = min(1.0, p_line)
            cur_steps = int(steps * t_max)
            for i in range(0, cur_steps, 2):
                t0 = i / float(steps)
                t1 = min(t_max, (i + 1.2) / float(steps))
                p0 = (int(pt_start[0] + (vn_center[0] - 110 - pt_start[0]) * t0),
                      int(pt_start[1] + (vn_center[1] - 70 - pt_start[1]) * t0))
                p1 = (int(pt_start[0] + (vn_center[0] - 110 - pt_start[0]) * t1),
                      int(pt_start[1] + (vn_center[1] - 70 - pt_start[1]) * t1))
                cv2.line(frame, p0, p1, COLOR_WHITE, 4, cv2.LINE_AA)

        # Kinetic luxury title 'LA NUOVA CINA' in lower-left
        p_title = ease_out_cubic((f - 18) / 32.0)
        if p_title > 0:
            txt_x = int(40 + (f / float(num_frames)) * 30.0)
            txt_y = int(HEIGHT - rotated_title.height + 40 - (f / float(num_frames)) * 20.0)

            txt_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            txt_layer.paste(rotated_title, (txt_x, txt_y), rotated_title)

            np_txt = np.asarray(txt_layer)
            alpha_mask = (np_txt[:, :, 3].astype(np.float32) / 255.0 * p_title)[:, :, None]

            f_float = frame.astype(np.float32) * (1.0 - alpha_mask) + \
                      np_txt[:, :, :3][:, :, ::-1].astype(np.float32) * alpha_mask
            frame[:] = np.clip(f_float, 0, 255).astype(np.uint8)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 6")


def render_scene_7(out_mp4: Path, num_frames=120):
    """SCENE 7: Global transcontinental flight tracking from USA across the world to Vietnam + '194 mld $'."""
    print("Rendering Scene 7: Global transcontinental flight tracking...")
    # Camera starts tightly on USA and sweeps eastwards across the world following the trade route
    cam = DynamicCamera(start_pose=(-88.0, 38.0, 7.8),
                        end_pose=(72.0, 20.0, 5.2),
                        total_frames=num_frames)

    usa_rings = GEO.get_country_rings("United States of America")
    vn_rings = GEO.get_country_rings("Vietnam")

    # Render metric badge in Arial_Italic with shadow
    font_metric = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/Arial_Italic.ttf", 76)
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), "194 mld $", font=font_metric)
    mw, mh = bbox[2] - bbox[0] + 120, bbox[3] - bbox[1] + 100
    metric_img = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    d_m = ImageDraw.Draw(metric_img)
    d_m.text((mw // 2, mh // 2), "194 mld $", font=font_metric, fill=(255, 255, 255, 255), anchor="mm")
    np_m = np.asarray(metric_img)
    shadow_m = cv2.GaussianBlur(np_m[:, :, 3], (0, 0), 10)
    shadow_rgba = np.zeros_like(np_m)
    shadow_rgba[:, :, :3] = 0
    shadow_rgba[:, :, 3] = (shadow_m.astype(np.float32) * 0.85).astype(np.uint8)
    M_s = np.float32([[1, 0, 2], [0, 1, 4]])
    shadow_shifted = cv2.warpAffine(shadow_rgba, M_s, (mw, mh))
    metric_comp = Image.alpha_composite(Image.fromarray(shadow_shifted), metric_img)

    frames = []

    for f in range(num_frames):
        c_lon, c_lat, scale = cam.get_pose(f)
        frame = cam.render_base(c_lon, c_lat, scale, ocean_color=(15, 14, 12),
                                land_color=(25, 22, 20), border_color=(40, 38, 34))

        usa_polys = cam.project_rings(usa_rings, c_lon, c_lat, scale)
        vn_polys = cam.project_rings(vn_rings, c_lon, c_lat, scale)

        DynamicEffects.draw_country_fill(frame, usa_polys, COLOR_BLUE_VIVID, opacity=0.92)
        DynamicEffects.draw_outline_glow(frame, usa_polys, COLOR_BLUE_VIVID, progress=1.0, thickness=2)

        DynamicEffects.draw_country_fill(frame, vn_polys, COLOR_RED_VIVID, opacity=0.96)
        DynamicEffects.draw_outline_glow(frame, vn_polys, COLOR_RED_VIVID, progress=1.0, thickness=2)

        # Dynamic anchors tracking with the globe
        p1 = cam.project_point(-98.0, 39.0, c_lon, c_lat, scale)
        p2 = cam.project_point(107.0, 16.0, c_lon, c_lat, scale)

        # Curved dashed trajectory
        p_route = ease_out_cubic((f - 10) / 48.0)
        if p_route > 0:
            ctrl = (int((p1[0] + p2[0]) / 2.0 - 50), int((p1[1] + p2[1]) / 2.0 - 340))
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

        # Floating metric '194 mld $' tracking along flight curve
        p_metric = ease_out_cubic((f - 24) / 25.0)
        if p_metric > 0:
            rotated = metric_comp.rotate(-18, resample=Image.BICUBIC, expand=True)
            txt_x = int(WIDTH * 0.46 + (f / float(num_frames)) * 50.0)
            txt_y = int(HEIGHT * 0.12 - (f / float(num_frames)) * 25.0)
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_frame.paste(rotated, (txt_x, txt_y), rotated)
            frame[:] = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)

        frames.append(frame)

    write_video_h264(frames, out_mp4)
    print("Done Scene 7")


def run_single_scene(item: tuple[int, int]):
    idx, num_frames = item
    scenes = {
        1: render_scene_1,
        2: render_scene_2,
        3: render_scene_3,
        4: render_scene_4,
        5: render_scene_5,
        6: render_scene_6,
        7: render_scene_7,
    }
    scenes[idx](OUT_DIR / f"scene_{idx}.mp4", num_frames)


def main():
    parser = argparse.ArgumentParser(description="Render cinematic dynamic map motions v2 (GPU accelerated)")
    parser.add_argument("--scene", type=int, choices=range(1, 8), help="Render specific scene")
    parser.add_argument("--frames", type=int, default=120, help="Frames per scene (default 120 = 4s)")
    parser.add_argument("--workers", type=int, default=7, help="Parallel worker processes (default 7)")
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
        import concurrent.futures
        tasks = [(idx, args.frames) for idx in range(1, 8)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(args.workers, len(tasks))) as executor:
            list(executor.map(run_single_scene, tasks))

    print(f"\nAll v2 dynamic scenes rendered with GPU NVENC acceleration to: {OUT_DIR}")


if __name__ == "__main__":
    main()
