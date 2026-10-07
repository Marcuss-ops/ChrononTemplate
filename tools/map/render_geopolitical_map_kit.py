#!/usr/bin/env python3
"""Geopolitical Map Motion Kit using OpenCV, NumPy and authoritative GeoJSON.

Pixel-faithful recreation of all 7 documentary reference styles:
- SCENE 1: Vietnam highlight red + Vietnam flag top + USA flag right + magenta connector bars
- SCENE 2: Latin America cluster (Mexico, Colombia, Brazil) + blue ocean + grid + white callout pins + diagonal striped indicator
- SCENE 3: Ho Chi Minh City -> Intel callout (glowing red Vietnam, white city pin, orthogonal 90 deg connector, massive glowing 'intel' logo)
- SCENE 4: China country outline drawn with pure glowing white rim on dark charcoal map
- SCENE 5: Vietnam outline red glow with deep black ocean & subtle land
- SCENE 6: 2.5D tilted map + Vietnam red + double white focus ring + massive glowing 'LA NUOVA CINA' typography
- SCENE 7: Curved dashed transcontinental trade route USA (blue) -> Vietnam (red) + massive floating metric '194 mld $'
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions
WIDTH = 1920
HEIGHT = 1080
FPS = 30

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
CHRONON_TEMPLATE = HERE.parents[1]
CATALOG_DIR = CHRONON_TEMPLATE / "catalog"
GEOJSON_PATH = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
FONTS_DIR = PROJECT_ROOT / "Chronon3d/assets/fonts"
OUT_DIR = CHRONON_TEMPLATE / "out/geopolitical_maps_opencv"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Shared palettes (BGR for OpenCV)
COLOR_DARK_OCEAN = (20, 18, 16)       # Deep charcoal black
COLOR_BLUE_OCEAN = (120, 68, 42)      # Steel blue ocean for LatAm scene #2A4478
COLOR_DARK_LAND = (15, 14, 12)        # Land darker or lighter
COLOR_BORDER_GREY = (55, 52, 48)      # Boundaries
COLOR_GRID_BLUE = (145, 90, 60)       # LatAm grid line
COLOR_GRID_DARK = (38, 35, 32)        # Subtle grid line
COLOR_RED_VIVID = (18, 20, 245)       # High-saturation red #F51412
COLOR_BLUE_VIVID = (245, 45, 15)      # High-saturation blue #0F2DF5
COLOR_MAGENTA_NEON = (210, 40, 240)   # Neon pink/magenta #F028D2
COLOR_WHITE = (255, 255, 255)

def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)

def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


class GeoProjector:
    """Equirectangular / Mercator projector with pan and zoom."""

    def __init__(self, center_lon: float, center_lat: float, zoom_scale: float,
                 w: int = WIDTH, h: int = HEIGHT):
        self.center_lon = center_lon
        self.center_lat = center_lat
        self.scale = zoom_scale
        self.w = w
        self.h = h

    def project(self, lon: float, lat: float) -> tuple[int, int]:
        x = self.w / 2.0 + (lon - self.center_lon) * self.scale
        lat_clamped = max(-85.0, min(85.0, lat))
        c_lat_clamped = max(-85.0, min(85.0, self.center_lat))
        y_m = math.log(math.tan(math.pi / 4.0 + math.radians(lat_clamped) / 2.0))
        cy_m = math.log(math.tan(math.pi / 4.0 + math.radians(c_lat_clamped) / 2.0))
        y = self.h / 2.0 - (y_m - cy_m) * self.scale * (180.0 / math.pi)
        return int(round(x)), int(round(y))


class GeoDataLoader:
    """Loads authoritative admin 0 boundaries from Natural Earth GeoJSON."""

    def __init__(self, path: Path = GEOJSON_PATH):
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.countries = {}
        for feature in self.data["features"]:
            name = feature.get("properties", {}).get("ADMIN")
            if name:
                self.countries[name] = feature["geometry"]

    def get_rings(self, country_name: str) -> list[np.ndarray]:
        geom = self.countries.get(country_name)
        if not geom:
            return []
        coords = []
        if geom["type"] == "Polygon":
            coords = geom["coordinates"]
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                coords.extend(poly)

        res = []
        for r in coords:
            if len(r) < 3:
                continue
            arr = np.asarray(r, dtype=np.float64)
            stride = max(1, math.ceil(len(arr) / 1200))
            arr = arr[::stride]
            if len(arr) >= 3:
                res.append(arr)
        return res

    def get_all_land_rings(self) -> list[np.ndarray]:
        all_rings = []
        for feature in self.data["features"]:
            geom = feature["geometry"]
            coords = []
            if geom["type"] == "Polygon":
                coords = geom["coordinates"]
            elif geom["type"] == "MultiPolygon":
                for poly in geom["coordinates"]:
                    coords.extend(poly)
            for r in coords:
                if len(r) >= 3:
                    arr = np.asarray(r, dtype=np.float64)
                    stride = max(1, math.ceil(len(arr) / 400))
                    arr = arr[::stride]
                    if len(arr) >= 3:
                        all_rings.append(arr)
        return all_rings


GEO_LOADER = GeoDataLoader()
ALL_LAND = GEO_LOADER.get_all_land_rings()


class MapKit:
    """High-fidelity rendering kit for geopolitical map animations."""

    @staticmethod
    def render_plate(proj: GeoProjector, ocean_color=COLOR_DARK_OCEAN,
                     land_color=COLOR_DARK_LAND, border_color=COLOR_BORDER_GREY,
                     grid_color=COLOR_GRID_DARK, with_grid=True) -> np.ndarray:
        """Render base geographical plate."""
        canvas = np.zeros((proj.h, proj.w, 3), dtype=np.uint8)
        canvas[:] = ocean_color

        land_polys = []
        for r in ALL_LAND:
            screen_pts = np.asarray([proj.project(lon, lat) for lon, lat in r], dtype=np.int32)
            if np.any((screen_pts[:, 0] >= -300) & (screen_pts[:, 0] <= proj.w + 300) &
                      (screen_pts[:, 1] >= -300) & (screen_pts[:, 1] <= proj.h + 300)):
                land_polys.append(screen_pts)

        if land_polys:
            cv2.fillPoly(canvas, land_polys, land_color)
            cv2.polylines(canvas, land_polys, True, border_color, 1, cv2.LINE_AA)

        if with_grid:
            grid_layer = np.zeros_like(canvas)
            # Longitude lines
            for lon in range(-180, 181, 10):
                pts = [proj.project(lon, lat) for lat in range(-80, 81, 5)]
                for i in range(len(pts) - 1):
                    p1, p2 = pts[i], pts[i + 1]
                    if -100 <= p1[0] <= proj.w + 100 or -100 <= p2[0] <= proj.w + 100:
                        cv2.line(grid_layer, p1, p2, grid_color, 1, cv2.LINE_AA)
            # Latitude lines
            for lat in range(-75, 76, 10):
                pts = [proj.project(lon, lat) for lat in range(-180, 181, 10)]
                for i in range(len(pts) - 1):
                    p1, p2 = pts[i], pts[i + 1]
                    if -100 <= p1[1] <= proj.h + 100 or -100 <= p2[1] <= proj.h + 100:
                        cv2.line(grid_layer, p1, p2, grid_color, 1, cv2.LINE_AA)
            cv2.addWeighted(canvas, 1.0, grid_layer, 0.45, 0, dst=canvas)

        return canvas

    @staticmethod
    def fill_country(canvas: np.ndarray, proj: GeoProjector, country_name: str,
                     color_bgr: tuple[int, int, int], opacity: float = 1.0,
                     add_inner_glow: bool = True):
        """Solid saturated country fill matching references."""
        if opacity <= 0.001:
            return
        rings = GEO_LOADER.get_rings(country_name)
        if not rings:
            return

        polys = [np.asarray([proj.project(lon, lat) for lon, lat in r], dtype=np.int32) for r in rings]
        mask = np.zeros((proj.h, proj.w), dtype=np.uint8)
        cv2.fillPoly(mask, polys, 255)

        overlay = np.zeros_like(canvas)
        overlay[:] = color_bgr

        if add_inner_glow:
            # Subtle edge highlight on top of the fill
            edge = np.zeros((proj.h, proj.w), dtype=np.uint8)
            cv2.polylines(edge, polys, True, 255, 2, cv2.LINE_AA)
            halo = cv2.GaussianBlur(edge, (0, 0), 6).astype(np.float32) / 255.0

        alpha = max(0.0, min(1.0, opacity))
        fg = cv2.addWeighted(canvas, 1.0 - alpha, overlay, alpha, 0)
        canvas[mask > 0] = fg[mask > 0]

    @staticmethod
    def outline_glow(canvas: np.ndarray, proj: GeoProjector, country_name: str,
                     color_bgr: tuple[int, int, int], thickness: int = 2,
                     progress: float = 1.0, halo_strength: float = 1.0):
        """Draw illuminated vector boundary with multi-pass Gaussian halo."""
        if progress <= 0.001:
            return
        rings = GEO_LOADER.get_rings(country_name)
        if not rings:
            return

        polys = [np.asarray([proj.project(lon, lat) for lon, lat in r], dtype=np.int32) for r in rings]
        edge = np.zeros((proj.h, proj.w), dtype=np.uint8)

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

        # Layered glow
        base_f = canvas.astype(np.float32)
        c_f = np.asarray(color_bgr, dtype=np.float32)[None, None, :]
        for sigma, weight in [(24, 0.45 * halo_strength), (10, 0.65 * halo_strength), (3, 0.90 * halo_strength)]:
            halo = cv2.GaussianBlur(edge, (0, 0), sigma).astype(np.float32) / 255.0
            a = (halo * weight)[:, :, None]
            base_f = base_f * (1.0 - a) + c_f * a

        rim = (edge.astype(np.float32) / 255.0)[:, :, None]
        bright = np.clip(c_f * 0.6 + 255.0 * 0.4, 0, 255)
        base_f = base_f * (1.0 - rim) + bright * rim
        canvas[:] = np.clip(base_f, 0, 255).astype(np.uint8)

    @staticmethod
    def draw_flag_card(canvas: np.ndarray, center: tuple[int, int], country_code: str,
                       progress: float, size: tuple[int, int] = (130, 85)):
        """Realistic flag card with shadow and border."""
        if progress <= 0.001:
            return
        p = max(0.0, min(1.0, progress))
        w, h = int(size[0] * p), int(size[1] * p)
        if w < 12 or h < 8:
            return

        x1 = center[0] - w // 2
        y1 = center[1] - h // 2
        card = np.zeros((h, w, 3), dtype=np.uint8)

        if country_code == "VN":
            # Red flag with centered gold star
            card[:] = (18, 20, 240)
            cx, cy = w // 2, h // 2
            r_outer = int(h * 0.35)
            r_inner = int(r_outer * 0.38)
            star = []
            for i in range(10):
                angle = -math.pi / 2.0 + i * math.pi / 5.0
                r = r_outer if i % 2 == 0 else r_inner
                star.append((int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle))))
            cv2.fillPoly(card, [np.array(star, dtype=np.int32)], (20, 230, 255))
        elif country_code == "USA":
            # USA flag stripes & canton
            card[:] = (255, 255, 255)
            sh = h / 13.0
            for i in range(13):
                if i % 2 == 0:
                    cv2.rectangle(card, (0, int(i * sh)), (w, int((i + 1) * sh)), (20, 24, 200), -1)
            cw = int(w * 0.46)
            ch = int(sh * 7)
            cv2.rectangle(card, (0, 0), (cw, ch), (150, 40, 20), -1)
            for r_idx in range(4):
                for c_idx in range(5):
                    cv2.circle(card, (int((c_idx + 1) * (cw / 6.0)), int((r_idx + 1) * (ch / 5.0))),
                               1, (255, 255, 255), -1)

        # Crisp outline
        cv2.rectangle(card, (0, 0), (w - 1, h - 1), (255, 255, 255), 1)

        # Place onto canvas
        if 0 <= x1 and x1 + w <= canvas.shape[1] and 0 <= y1 and y1 + h <= canvas.shape[0]:
            canvas[y1:y1 + h, x1:x1 + w] = card

    @staticmethod
    def draw_white_pin_card(canvas: np.ndarray, text: str, anchor_pt: tuple[int, int],
                           progress: float):
        """Crisp white label card with bottom pointer (Ref 1 LatAm style)."""
        if progress <= 0.001:
            return
        p = max(0.0, min(1.0, progress))
        alpha = ease_out(p)

        card_w = 110
        card_h = 42
        cx, cy = anchor_pt[0], anchor_pt[1] - 40

        x1 = cx - card_w // 2
        y1 = cy - card_h // 2
        x2 = x1 + card_w
        y2 = y1 + card_h

        # Little triangle pointer down to anchor
        triangle = np.array([[cx - 8, y2], [cx + 8, y2], [cx, anchor_pt[1] - 6]], dtype=np.int32)
        cv2.fillPoly(canvas, [triangle], COLOR_WHITE)

        # Card body
        cv2.rectangle(canvas, (x1, y1), (x2, y2), COLOR_WHITE, -1)

        # Text in crisp black
        pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=20)
        draw.text((cx, cy), text, font=font, fill=(15, 18, 24), anchor="mm")
        canvas[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def draw_diagonal_arrow_marker(canvas: np.ndarray, target_pt: tuple[int, int],
                                  progress: float):
        """The iconic striped metallic diagonal callout arrow in Ref 1."""
        if progress <= 0.001:
            return
        p = max(0.0, min(1.0, progress))
        # Points from top-right towards target
        start_pt = (target_pt[0] + 160, target_pt[1] - 160)
        curr_x = int(start_pt[0] + (target_pt[0] - start_pt[0]) * p)
        curr_y = int(start_pt[1] + (target_pt[1] - start_pt[1]) * p)

        # Striped gradient line
        steps = 20
        for i in range(steps):
            t1 = i / float(steps)
            t2 = (i + 1) / float(steps)
            if t1 > p:
                break
            p1 = (int(start_pt[0] + (target_pt[0] - start_pt[0]) * t1),
                  int(start_pt[1] + (target_pt[1] - start_pt[1]) * t1))
            p2 = (int(start_pt[0] + (target_pt[0] - start_pt[0]) * min(p, t2)),
                  int(start_pt[1] + (target_pt[1] - start_pt[1]) * min(p, t2)))
            col = (255, 255, 255) if (i % 2 == 0) else (180, 180, 180)
            cv2.line(canvas, p1, p2, col, 8, cv2.LINE_AA)

        # Arrowhead
        if p > 0.8:
            cv2.circle(canvas, target_pt, 6, COLOR_WHITE, -1, cv2.LINE_AA)

    @staticmethod
    def draw_intel_brand_callout(canvas: np.ndarray, city_pt: tuple[int, int],
                                 logo_center: tuple[int, int], progress: float):
        """Ho Chi Minh City callout with orthogonal elbow and glowing Intel logo (Ref 3)."""
        # City pin card
        p_pin = ease_out(min(1.0, progress * 1.5))
        # White dot at city
        cv2.circle(canvas, city_pt, 8, COLOR_WHITE, -1, cv2.LINE_AA)
        cv2.circle(canvas, city_pt, 14, COLOR_WHITE, 2, cv2.LINE_AA)

        # Label box 'Ho Chi Minh City'
        card_w, card_h = 240, 52
        cx, cy = city_pt[0] - 8, city_pt[1] - 46
        x1, y1 = cx - card_w // 2, cy - card_h // 2
        cv2.rectangle(canvas, (x1, y1), (x1 + card_w, y1 + card_h), COLOR_WHITE, -1)

        pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=24)
        draw.text((cx, cy), "Ho Chi Minh City", font=font, fill=(15, 18, 22), anchor="mm")
        canvas[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

        # Orthogonal line from city_pt to logo
        p_line = ease_in_out(max(0.0, min(1.0, (progress - 0.2) * 1.8)))
        if p_line > 0:
            corner_pt = (logo_center[0] - 120, city_pt[1])
            end_pt = (logo_center[0] - 120, logo_center[1] + 100)

            len1 = corner_pt[0] - city_pt[0]
            len2 = corner_pt[1] - end_pt[1]
            tot = len1 + len2
            budget = tot * p_line

            if budget <= len1:
                cur_x = int(city_pt[0] + budget)
                cv2.line(canvas, city_pt, (cur_x, city_pt[1]), COLOR_WHITE, 4, cv2.LINE_AA)
            else:
                cv2.line(canvas, city_pt, corner_pt, COLOR_WHITE, 4, cv2.LINE_AA)
                cur_y = int(corner_pt[1] - (budget - len1))
                cv2.line(canvas, corner_pt, (corner_pt[0], cur_y), COLOR_WHITE, 4, cv2.LINE_AA)

        # Massive glowing Intel logo
        p_logo = ease_out(max(0.0, min(1.0, (progress - 0.4) * 2.0)))
        if p_logo > 0:
            pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            f_intel = ImageFont.truetype(str(FONTS_DIR / "Montserrat-Bold.ttf"), size=150)

            # Draw white text
            tx, ty = logo_center
            draw.text((tx, ty), "intel", font=f_intel, fill=(255, 255, 255), anchor="mm")
            # Registered trademark symbol
            f_reg = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=24)
            draw.text((tx + 225, ty + 20), "®", font=f_reg, fill=(255, 255, 255), anchor="mm")

            rendered = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

            # Soft glow halo around intel logo
            mask = np.zeros((canvas.shape[0], canvas.shape[1]), dtype=np.uint8)
            cv2.putText(mask, "intel", (tx - 210, ty + 50), cv2.FONT_HERSHEY_DUPLEX, 4.5, 255, 12, cv2.LINE_AA)
            halo = cv2.GaussianBlur(mask, (0, 0), 22).astype(np.float32) / 255.0
            halo_rgb = (halo * 0.65)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)

            base = rendered.astype(np.float32) + halo_rgb
            canvas[:] = np.clip(base, 0, 255).astype(np.uint8)


# -----------------------------------------------------------------------------
# THE 7 SCENES
# -----------------------------------------------------------------------------

def render_scene_1(output_mp4: Path, num_frames: int = 90):
    """SCENE 1: Vietnam highlight red + VN flag top + USA flag right + magenta connector bars."""
    print(f"Rendering Scene 1 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=108.0, center_lat=16.0, zoom_scale=32.0)
    base = MapKit.render_plate(proj, ocean_color=(20, 18, 16), land_color=(28, 25, 22),
                               border_color=(45, 42, 38), with_grid=True)

    vn_flag_pt = (WIDTH // 2 - 200, 180)
    us_flag_pt = (WIDTH // 2 + 380, 480)

    for f in range(num_frames):
        frame = base.copy()
        p_fill = ease_out(f / 30.0)

        # Vietnam vivid red fill
        MapKit.fill_country(frame, proj, "Vietnam", COLOR_RED_VIVID, opacity=0.92 * p_fill)
        MapKit.outline_glow(frame, proj, "Vietnam", COLOR_RED_VIVID, thickness=2, progress=1.0, halo_strength=0.9)

        # Magenta connection bars
        p_bars = ease_out((f - 18) / 30.0)
        if p_bars > 0:
            vn_center_top = proj.project(106.0, 21.0)
            vn_center_mid = proj.project(108.2, 16.0)

            # Bar 1 from top Vietnam to USA flag area
            cv2.line(frame, vn_center_top,
                     (int(vn_center_top[0] + (us_flag_pt[0] - 60 - vn_center_top[0]) * p_bars),
                      int(vn_center_top[1] + (us_flag_pt[1] - 80 - vn_center_top[1]) * p_bars)),
                     COLOR_MAGENTA_NEON, 14, cv2.LINE_AA)

            # Bar 2 from mid Vietnam to USA flag area
            cv2.line(frame, vn_center_mid,
                     (int(vn_center_mid[0] + (us_flag_pt[0] - 60 - vn_center_mid[0]) * p_bars),
                      int(vn_center_mid[1] + (us_flag_pt[1] + 40 - vn_center_mid[1]) * p_bars)),
                     COLOR_MAGENTA_NEON, 14, cv2.LINE_AA)

        # Flags pop in
        p_vn = ease_out((f - 10) / 25.0)
        MapKit.draw_flag_card(frame, vn_flag_pt, "VN", p_vn, size=(160, 105))

        p_us = ease_out((f - 22) / 25.0)
        MapKit.draw_flag_card(frame, us_flag_pt, "USA", p_us, size=(160, 105))

        out.write(frame)

    out.release()
    print("Done Scene 1")


def render_scene_2(output_mp4: Path, num_frames: int = 90):
    """SCENE 2: Latin America cluster (Mexico, Colombia, Brazil) + blue ocean + grid + pins."""
    print(f"Rendering Scene 2 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=-68.0, center_lat=2.0, zoom_scale=8.5)
    base = MapKit.render_plate(proj, ocean_color=COLOR_BLUE_OCEAN, land_color=(16, 14, 12),
                               border_color=(45, 42, 40), grid_color=COLOR_GRID_BLUE, with_grid=True)

    mex_anchor = proj.project(-101.0, 22.0)
    col_anchor = proj.project(-73.5, 4.0)
    bra_anchor = proj.project(-51.0, -12.0)

    for f in range(num_frames):
        frame = base.copy()

        # Mexico
        p_mex = ease_out(f / 25.0)
        MapKit.fill_country(frame, proj, "Mexico", COLOR_RED_VIVID, opacity=0.95 * p_mex)
        MapKit.draw_white_pin_card(frame, "Mexico", mex_anchor, ease_out((f - 8) / 20.0))

        # Colombia
        p_col = ease_out((f - 15) / 25.0)
        MapKit.fill_country(frame, proj, "Colombia", COLOR_RED_VIVID, opacity=0.95 * p_col)
        MapKit.draw_white_pin_card(frame, "Colombia", col_anchor, ease_out((f - 20) / 20.0))

        # Brazil
        p_bra = ease_out((f - 30) / 25.0)
        MapKit.fill_country(frame, proj, "Brazil", COLOR_RED_VIVID, opacity=0.95 * p_bra)
        MapKit.draw_white_pin_card(frame, "Brazil", bra_anchor, ease_out((f - 35) / 20.0))

        # Diagonal arrow indicator into Colombia
        p_arr = ease_out((f - 25) / 30.0)
        MapKit.draw_diagonal_arrow_marker(frame, (col_anchor[0], col_anchor[1] - 45), p_arr)

        out.write(frame)

    out.release()
    print("Done Scene 2")


def render_scene_3(output_mp4: Path, num_frames: int = 90):
    """SCENE 3: Ho Chi Minh City -> Intel callout (glowing red Vietnam, orthogonal elbow line)."""
    print(f"Rendering Scene 3 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=110.0, center_lat=15.0, zoom_scale=30.0)
    base = MapKit.render_plate(proj, ocean_color=(20, 18, 16), land_color=(28, 25, 22),
                               border_color=(45, 42, 38), with_grid=True)

    hcm_pt = proj.project(106.63, 10.82)
    intel_logo_center = (WIDTH // 2 + 380, HEIGHT // 2 - 120)

    for f in range(num_frames):
        frame = base.copy()

        # Vietnam solid red with glow
        MapKit.fill_country(frame, proj, "Vietnam", COLOR_RED_VIVID, opacity=0.95)
        MapKit.outline_glow(frame, proj, "Vietnam", COLOR_RED_VIVID, thickness=2, progress=1.0)

        # Callout animation
        p = f / float(num_frames)
        MapKit.draw_intel_brand_callout(frame, hcm_pt, intel_logo_center, p)

        out.write(frame)

    out.release()
    print("Done Scene 3")


def render_scene_4(output_mp4: Path, num_frames: int = 90):
    """SCENE 4: China country outline drawn with pure glowing white rim on dark charcoal map."""
    print(f"Rendering Scene 4 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=105.0, center_lat=35.0, zoom_scale=11.0)
    base = MapKit.render_plate(proj, ocean_color=(15, 14, 12), land_color=(20, 18, 16),
                               border_color=(35, 32, 28), with_grid=False)

    for f in range(num_frames):
        frame = base.copy()
        p_draw = ease_in_out(f / 65.0)

        # Inner darkened land mass for China
        MapKit.fill_country(frame, proj, "China", (10, 8, 8), opacity=0.55 * p_draw, add_inner_glow=False)

        # Intense pure white outline with luminous bloom
        MapKit.outline_glow(frame, proj, "China", COLOR_WHITE, thickness=3,
                            progress=p_draw, halo_strength=1.4)

        out.write(frame)

    out.release()
    print("Done Scene 4")


def render_scene_5(output_mp4: Path, num_frames: int = 90):
    """SCENE 5: Vietnam outline red glow with deep black ocean & subtle land."""
    print(f"Rendering Scene 5 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=107.5, center_lat=16.0, zoom_scale=36.0)
    base = MapKit.render_plate(proj, ocean_color=(14, 12, 10), land_color=(22, 20, 18),
                               border_color=(32, 30, 26), with_grid=False)

    for f in range(num_frames):
        frame = base.copy()
        p_draw = ease_in_out(f / 60.0)

        # Intense red glow outline
        MapKit.outline_glow(frame, proj, "Vietnam", COLOR_RED_VIVID, thickness=3,
                            progress=p_draw, halo_strength=1.5)

        out.write(frame)

    out.release()
    print("Done Scene 5")


def render_scene_6(output_mp4: Path, num_frames: int = 90):
    """SCENE 6: 2.5D tilted map + Vietnam red + focus ring + massive glowing 'LA NUOVA CINA'."""
    print(f"Rendering Scene 6 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    proj = GeoProjector(center_lon=108.0, center_lat=16.0, zoom_scale=24.0)
    base_2d = MapKit.render_plate(proj, ocean_color=(16, 14, 12), land_color=(24, 22, 20),
                                  border_color=(40, 38, 34), with_grid=False)

    # Add red Vietnam to 2D plate before tilt
    MapKit.fill_country(base_2d, proj, "Vietnam", COLOR_RED_VIVID, opacity=0.98)
    MapKit.outline_glow(base_2d, proj, "Vietnam", COLOR_RED_VIVID, thickness=2, progress=1.0)

    # 2.5D Perspective Warp Matrix
    src_pts = np.float32([[0, 0], [WIDTH, 0], [WIDTH, HEIGHT], [0, HEIGHT]])
    tilt_margin = int(WIDTH * 0.16)
    dst_pts = np.float32([[tilt_margin, int(HEIGHT * 0.12)],
                          [WIDTH - tilt_margin, int(HEIGHT * 0.12)],
                          [WIDTH + 60, HEIGHT],
                          [-60, HEIGHT]])
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Warped background plate
    tilted_plate = cv2.warpPerspective(base_2d, M, (WIDTH, HEIGHT))

    # Center of Vietnam on tilted plate
    vn_screen_2d = proj.project(107.8, 16.0)
    v_homo = np.array([vn_screen_2d[0], vn_screen_2d[1], 1.0], dtype=np.float32)
    v_warped = M.dot(v_homo)
    ring_center = (int(v_warped[0] / v_warped[2]), int(v_warped[1] / v_warped[2]))

    for f in range(num_frames):
        frame = tilted_plate.copy()

        # Double White Focus Ring
        p_ring = ease_out(f / 35.0)
        rx, ry = int(140 * p_ring), int(140 * p_ring)
        if rx > 5:
            cv2.ellipse(frame, ring_center, (rx, ry), -15, 0, 360, COLOR_WHITE, 4, cv2.LINE_AA)
            cv2.ellipse(frame, ring_center, (rx + 6, ry + 6), -15, 0, 360, (180, 180, 180), 1, cv2.LINE_AA)

        # Diagonal accent dashes pointing outwards
        if p_ring > 0.4:
            cv2.line(frame, (ring_center[0] - 120, ring_center[1] - 120),
                     (ring_center[0] - 190, ring_center[1] - 190), COLOR_WHITE, 3, cv2.LINE_AA)
            cv2.line(frame, (ring_center[0] - 210, ring_center[1] - 210),
                     (ring_center[0] - 270, ring_center[1] - 270), COLOR_WHITE, 3, cv2.LINE_AA)

        # Massive Glowing Title 'LA NUOVA CINA' (rotated ~ 25 degrees)
        p_title = ease_out((f - 18) / 30.0)
        if p_title > 0:
            txt_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_layer)
            font = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=130)

            # Draw rotated text on temporary canvas
            temp_txt = Image.new("RGBA", (1400, 300), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(temp_txt)
            t_draw.text((700, 150), "LA NUOVA CINA", font=font,
                        fill=(255, 255, 255, int(255 * p_title)), anchor="mm")
            # Rotate with perspective slant
            rotated = temp_txt.rotate(22, resample=Image.BICUBIC, expand=True)

            txt_x = int(WIDTH * 0.10)
            txt_y = int(HEIGHT * 0.50)
            txt_layer.paste(rotated, (txt_x, txt_y), rotated)

            np_txt = np.asarray(txt_layer)
            alpha_mask = np_txt[:, :, 3].astype(np.float32) / 255.0

            # Luminous bloom around text
            glow = cv2.GaussianBlur((alpha_mask * 255).astype(np.uint8), (0, 0), 18).astype(np.float32) / 255.0
            bloom = (glow * 0.55)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)

            f_float = frame.astype(np.float32) * (1.0 - alpha_mask[:, :, None]) + \
                      np_txt[:, :, :3][:, :, ::-1].astype(np.float32) * alpha_mask[:, :, None] + bloom
            frame[:] = np.clip(f_float, 0, 255).astype(np.uint8)

        out.write(frame)

    out.release()
    print("Done Scene 6")


def render_scene_7(output_mp4: Path, num_frames: int = 90):
    """SCENE 7: Trade route USA (blue) -> Vietnam (red) + massive floating metric '194 mld $'."""
    print(f"Rendering Scene 7 -> {output_mp4.name} ...")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_mp4), fourcc, FPS, (WIDTH, HEIGHT))

    # Global projection centered to show both USA and Eurasia
    proj = GeoProjector(center_lon=20.0, center_lat=30.0, zoom_scale=4.4)
    base = MapKit.render_plate(proj, ocean_color=(15, 14, 12), land_color=(25, 22, 20),
                               border_color=(40, 38, 34), with_grid=False)

    usa_pt = proj.project(-98.0, 39.0)
    vn_pt = proj.project(107.0, 16.0)

    # Flip / wrap USA into view on the left:
    # USA coords on the left, Vietnam on the right
    p1 = (180, 280)    # USA location
    p2 = (1750, 850)   # Vietnam location

    # Precompute USA and Vietnam country overlays on base plate
    usa_layer = np.zeros_like(base)
    MapKit.fill_country(usa_layer, proj, "United States of America", COLOR_BLUE_VIVID, opacity=0.90)
    MapKit.outline_glow(usa_layer, proj, "United States of America", COLOR_BLUE_VIVID, thickness=2, progress=1.0)
    usa_mask = (usa_layer > 0).any(axis=2)

    vn_layer = np.zeros_like(base)
    MapKit.fill_country(vn_layer, proj, "Vietnam", COLOR_RED_VIVID, opacity=0.95)
    MapKit.outline_glow(vn_layer, proj, "Vietnam", COLOR_RED_VIVID, thickness=2, progress=1.0)
    vn_mask = (vn_layer > 0).any(axis=2)

    for f in range(num_frames):
        frame = base.copy()
        p_in = ease_out(f / 25.0)

        # Blend precomputed USA & Vietnam with fade-in
        if p_in > 0:
            frame[usa_mask] = cv2.addWeighted(frame, 1.0 - p_in, usa_layer, p_in, 0)[usa_mask]
            frame[vn_mask] = cv2.addWeighted(frame, 1.0 - p_in, vn_layer, p_in, 0)[vn_mask]

        # Long curved dashed trajectory from USA across Atlantic & Europe down to Vietnam
        p_route = ease_in_out((f - 12) / 45.0)
        if p_route > 0:
            ctrl = (int((p1[0] + p2[0]) / 2.0 + 100), int((p1[1] + p2[1]) / 2.0 - 280))
            steps = 120
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

        # Massive floating metric '194 mld $' tilted along the route
        p_metric = ease_out((f - 30) / 25.0)
        if p_metric > 0:
            temp_txt = Image.new("RGBA", (800, 200), (0, 0, 0, 0))
            t_draw = ImageDraw.Draw(temp_txt)
            f_val = ImageFont.truetype(str(FONTS_DIR / "Inter-Bold.ttf"), size=80)
            t_draw.text((400, 100), "194 mld $", font=f_val,
                        fill=(255, 255, 255, int(255 * p_metric)), anchor="mm")

            # Slanted rotation ~ 18 degrees matching trajectory
            rotated = temp_txt.rotate(-18, resample=Image.BICUBIC, expand=True)

            txt_x = 920
            txt_y = 120
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            pil_frame.paste(rotated, (txt_x, txt_y), rotated)

            rendered = cv2.cvtColor(np.asarray(pil_frame), cv2.COLOR_RGB2BGR)

            # Luminous halo around metric
            mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
            cv2.putText(mask, "194 mld $", (txt_x + 100, txt_y + 120),
                        cv2.FONT_HERSHEY_DUPLEX, 2.5, 255, 8, cv2.LINE_AA)
            halo = cv2.GaussianBlur(mask, (0, 0), 20).astype(np.float32) / 255.0
            bloom = (halo * 0.70)[:, :, None] * np.array([255, 255, 255], dtype=np.float32)
            frame[:] = np.clip(rendered.astype(np.float32) + bloom, 0, 255).astype(np.uint8)

        out.write(frame)

    out.release()
    print("Done Scene 7")


def export_stills():
    """Extract sample reference stills at keyframe 70 for visual inspection."""
    print("Extracting stills for visual audit...")
    for i in range(1, 8):
        mp4_path = OUT_DIR / f"scene_{i}.mp4"
        if not mp4_path.exists():
            continue
        cap = cv2.VideoCapture(str(mp4_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 70)
        ret, frame = cap.read()
        cap.release()
        if ret:
            img_path = OUT_DIR / f"scene_{i}_still.png"
            cv2.imwrite(str(img_path), frame)
            print(f"Saved {img_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Render geopolitical map kit with OpenCV")
    parser.add_argument("--scene", type=int, choices=range(1, 8), help="Render specific scene")
    parser.add_argument("--frames", type=int, default=90, help="Total frames")
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

    export_stills()
    print(f"\nAll renders complete! Output directory: {OUT_DIR}")


if __name__ == "__main__":
    main()
