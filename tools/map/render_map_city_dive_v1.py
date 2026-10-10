#!/usr/bin/env python3
"""Render a real multilevel basemap dive from high altitude to central Milan."""
from __future__ import annotations

import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BASE / "Chronon3d/tools/cartography"))
from dynamic_tile_pyramid import DynamicTilePyramid, compute_altitude_km, latlon_to_global_px  # noqa: E402

W, H, FPS, FRAMES = 1920, 1080, 30, 150
LAT, LON = 45.4642, 9.1900
Z_START, Z_END = 3.0, 17.5
OUT = BASE / "ChrononTemplate/catalog/maps/samples"
FONT = ImageFont.truetype(str(BASE / "ChrononTemplate/assets/fonts/Inter-Bold.ttf"), 28)
SMALL = ImageFont.truetype(str(BASE / "ChrononTemplate/assets/fonts/Inter-Bold.ttf"), 16)

MAPS = [
    ("natural_earth_hypso_relief_water", "esri_topo", "NATURAL EARTH · RELIEF", "ESRI WORLD TOPOGRAPHIC MAP", (229, 191, 118)),
    ("natural_earth_landcover_relief_water", "esri_natgeo", "NATURAL EARTH · LANDCOVER", "ESRI NATGEO → WORLD TOPOGRAPHIC DETAIL", (213, 202, 129)),
    ("nasa_blue_marble_august", "esri_sat", "BLUE MARBLE · SATELLITE", "ESRI WORLD IMAGERY", (120, 194, 226)),
    ("white_claude_map", "esri_topo", "WHITE CLAUDE MAP", "ESRI TOPOGRAPHIC DATA · WARM RELIEF GRADE", (226, 195, 150)),
]


def smootherstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def zoom_at(frame: int) -> float:
    return Z_START + (Z_END - Z_START) * smootherstep(frame / (FRAMES - 1))


def coverage_tiles(zoom_min: float = Z_START, zoom_max: float = Z_END) -> set[tuple[int, int, int]]:
    result: set[tuple[int, int, int]] = set()
    for frame in range(FRAMES):
        zoom = zoom_at(frame)
        if zoom < zoom_min or zoom > zoom_max:
            continue
        z0 = math.floor(zoom)
        t = zoom - z0
        levels = [(z0, 2.0**t)]
        if t * t * (3.0 - 2.0 * t) > 0.001:
            levels.append((z0 + 1, 2.0 ** (t - 1.0)))
        for z, scale in levels:
            width = int(round(W / scale)) + 4
            height = int(round(H / scale)) + 4
            gx, gy = latlon_to_global_px(LAT, LON, z)
            left, top = gx - width / 2, gy - height / 2
            x0, x1 = math.floor(left / 256), math.ceil((left + width) / 256)
            y0, y1 = math.floor(top / 256), math.ceil((top + height) / 256)
            for y in range(y0, y1):
                if 0 <= y < 2**z:
                    for x in range(x0, x1):
                        result.add((z, x % (2**z), y))
    return result


def warm_relief_grade(frame: np.ndarray) -> np.ndarray:
    """Give the White Claude variant a paper and ink treatment, preserving map detail."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    gray = np.clip((gray - 0.04) * 1.10, 0.0, 1.0)[..., None]
    # OpenCV frames are BGR: red must remain stronger than blue for warm paper.
    dark_bgr = np.array([29.0, 35.0, 43.0], dtype=np.float32)
    light_bgr = np.array([197.0, 216.0, 241.0], dtype=np.float32)
    return np.clip(dark_bgr + gray * (light_bgr - dark_bgr), 0, 255).astype(np.uint8)


def phase_for(zoom: float) -> str:
    if zoom < 7.4:
        return "EUROPE"
    if zoom < 11.6:
        return "ITALIA"
    if zoom < 14.7:
        return "LOMBARDIA"
    return "MILANO"


def overlay(frame: np.ndarray, zoom: float, title: str, source: str, accent: tuple[int, int, int]) -> np.ndarray:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    canvas = Image.fromarray(rgb).convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    stage = phase_for(zoom)
    altitude = compute_altitude_km(zoom, LAT)

    # Compact, steady locator. The map remains the full canvas; only the locator is overlaid.
    alpha = 232
    x, y = 62, 54
    draw.rounded_rectangle((x, y, x + 700, y + 94), radius=15,
                           fill=(7, 15, 21, alpha), outline=(*accent, 220), width=2)
    draw.rounded_rectangle((x, y + 17, x + 6, y + 77), radius=3, fill=(*accent, 255))
    draw.text((x + 24, y + 13), f"{stage}  /  {title}", font=FONT, fill=(248, 247, 241, 255))
    draw.text((x + 25, y + 56), f"ALTITUDE  {altitude:,.0f} KM", font=SMALL, fill=(198, 211, 213, 255))

    # Keep the attribution legible and away from the central target.
    credit = source
    box = draw.textbbox((0, 0), credit, font=SMALL)
    credit_w = box[2] - box[0]
    bx, by = W - credit_w - 76, H - 66
    draw.rounded_rectangle((bx - 12, by - 6, W - 58, by + 30), radius=8, fill=(7, 15, 21, 205))
    draw.text((bx, by), credit, font=SMALL, fill=(241, 238, 227, 242))

    # Location lock resolves only during the final approach to the city.
    if zoom >= 14.5:
        p = min(1.0, max(0.0, (zoom - 14.5) / 2.0))
        cx, cy = W // 2, H // 2
        pulse = 0.5 + 0.5 * math.sin(zoom * 7.0)
        radius = int(12 + 10 * pulse)
        draw.ellipse((cx - radius - 15, cy - radius - 15, cx + radius + 15, cy + radius + 15),
                     outline=(*accent, int(95 + 110 * pulse)), width=3)
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(*accent, 255), outline=(255, 255, 250, 255), width=2)
        if p > 0.65:
            label = "MILANO  ·  45.4642° N  9.1900° E"
            tx, ty = 62, H - 133
            draw.rounded_rectangle((tx, ty, tx + 500, ty + 52), radius=12,
                                   fill=(7, 15, 21, int(190 * p)), outline=(*accent, int(210 * p)), width=2)
            draw.text((tx + 18, ty + 11), label, font=SMALL, fill=(248, 247, 241, int(255 * p)))
    return cv2.cvtColor(np.asarray(canvas.convert("RGB")), cv2.COLOR_RGB2BGR)


def render_one(ident: str, provider: str, title: str, source: str, accent: tuple[int, int, int]) -> None:
    detail_pyramid = None
    print(f"[{ident}] prepare {provider} tile pyramid", flush=True)
    pyramid = DynamicTilePyramid(provider=provider)
    if ident == "natural_earth_landcover_relief_water":
        # Esri's National Geographic layer stops providing Milan detail at z12.
        # Hand off to the detailed topographic pyramid before its unavailable tiles begin.
        pyramid.prefetch_tiles(coverage_tiles(zoom_max=11.95), max_workers=10)
        detail_pyramid = DynamicTilePyramid(provider="esri_topo")
        print(f"[{ident}] prepare topographic detail for the final approach", flush=True)
        detail_pyramid.prefetch_tiles(coverage_tiles(zoom_min=11.45), max_workers=10)
    else:
        pyramid.prefetch_tiles(coverage_tiles(), max_workers=10)
    tmp = OUT / f"{ident}_5s.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    started = time.time()
    for f in range(FRAMES):
        z = zoom_at(f)
        if detail_pyramid is not None and z > 11.45:
            detailed = detail_pyramid.sample_continuous(LAT, LON, z, W, H)
            if z < 11.95:
                broad = pyramid.sample_continuous(LAT, LON, z, W, H)
                blend = smootherstep((z - 11.45) / 0.50)
                frame = cv2.addWeighted(broad, 1.0 - blend, detailed, blend, 0.0)
            else:
                frame = detailed
        else:
            frame = pyramid.sample_continuous(LAT, LON, z, W, H)
        if ident == "white_claude_map":
            frame = warm_relief_grade(frame)
        frame = overlay(frame, z, title, source, accent)
        assert encoder.stdin is not None
        encoder.stdin.write(frame.tobytes())
        if f % 30 == 0 or f == FRAMES - 1:
            print(f"[{ident}] frame {f}/{FRAMES} zoom={z:.2f} altitude={compute_altitude_km(z, LAT):.1f}km", flush=True)
    assert encoder.stdin is not None
    encoder.stdin.close()
    status = encoder.wait()
    if status:
        raise RuntimeError(f"NVENC failed for {ident}: exit={status}")
    late = pyramid.telemetry.get("late_tile_fetches", 0)
    if detail_pyramid is not None:
        late += detail_pyramid.telemetry.get("late_tile_fetches", 0)
    if late:
        raise RuntimeError(f"{ident}: sampled late tiles ({late})")
    print(f"[{ident}] wrote {tmp.stat().st_size:,} bytes in {time.time()-started:.1f}s", flush=True)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    selected = [spec for spec in MAPS if only is None or spec[0] == only]
    if only and not selected:
        raise SystemExit(f"unknown map id: {only}")
    for spec in selected:
        render_one(*spec)
