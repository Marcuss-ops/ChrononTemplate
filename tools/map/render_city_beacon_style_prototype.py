#!/usr/bin/env python3
"""Standalone prototype for the city-location animation treatment.

This is intentionally isolated from runtime wiring. It renders an 8 second
Manaus sample: a 6.5 second nearby camera move followed by a 1.5 second hold.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Chronon3d/tools/cartography"))
from dynamic_tile_pyramid import DynamicTilePyramid  # noqa: E402

WIDTH, HEIGHT, FPS = 1280, 720, 30
DURATION_FRAMES = 240
MOVE_FRAMES = 195  # 6.5 seconds
CITY = "Manaus"
TARGET = ( -3.1190, -60.0217 )
START = ( -1.85, -62.35 )
OUT = ROOT / "ChrononTemplate/out/city_beacon_style_prototype.mp4"
FONT = ROOT / "Chronon3d/assets/fonts/DM-Serif-Display-Italic.ttf"


def smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def camera_at(frame: int) -> tuple[float, float, float]:
    p = smootherstep(frame / max(1, MOVE_FRAMES - 1))
    lat = START[0] + (TARGET[0] - START[0]) * p
    lon = START[1] + (TARGET[1] - START[1]) * p
    zoom = 8.8 + (12.0 - 8.8) * p
    return lat, lon, zoom


def grade_map(frame: np.ndarray) -> np.ndarray:
    # Preserve satellite detail while borrowing the reference's dark green look.
    f = frame.astype(np.float32)
    f *= np.array([0.56, 0.77, 0.46], dtype=np.float32)  # BGR green grade
    f *= 0.73
    f += np.array([0.0, 5.0, 0.0], dtype=np.float32)
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    nx = (xx - WIDTH * 0.5) / (WIDTH * 0.72)
    ny = (yy - HEIGHT * 0.5) / (HEIGHT * 0.72)
    vignette = np.clip(1.0 - 0.22 * (nx * nx + ny * ny), 0.68, 1.0)
    f *= vignette[:, :, None]
    return np.clip(f, 0, 255).astype(np.uint8)


def draw_grid(frame: np.ndarray, phase: float) -> None:
    overlay = frame.copy()
    color = (44, 91, 48)
    spacing = 80
    shift_x = int((phase * 12) % spacing)
    shift_y = int((phase * 7) % spacing)
    for x in range(-spacing + shift_x, WIDTH + spacing, spacing):
        cv2.line(overlay, (x, 0), (x, HEIGHT), color, 1, cv2.LINE_AA)
    for y in range(-spacing + shift_y, HEIGHT + spacing, spacing):
        cv2.line(overlay, (0, y), (WIDTH, y), color, 1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.34, frame, 0.66, 0, dst=frame)


def draw_beacon(frame: np.ndarray, point: tuple[int, int], progress: float) -> None:
    x, y = point
    fade = smootherstep((progress - 0.68) / 0.12)
    if fade <= 0:
        return
    pulse = 0.5 + 0.5 * math.sin((progress - 0.68) * math.tau * 1.15)
    # Broad, low-opacity bloom with an irregular soft edge instead of a pin.
    glow = np.zeros_like(frame)
    cv2.circle(glow, (x, y), int(48 + 5 * pulse), (16, 16, 245), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 28)
    cv2.addWeighted(frame, 1.0, glow, 0.7 * fade, 0, dst=frame)

    haze = np.zeros_like(frame)
    cv2.ellipse(haze, (x, y), (35, 25), -12, 0, 360, (20, 26, 240), -1, cv2.LINE_AA)
    haze = cv2.GaussianBlur(haze, (0, 0), 13)
    cv2.addWeighted(frame, 1.0, haze, (0.42 + pulse * 0.10) * fade, 0, dst=frame)

    ring_alpha = fade * (0.48 + 0.24 * pulse)
    ring = np.zeros_like(frame)
    cv2.circle(ring, (x, y), int(23 + 8 * pulse), (16, 30, 248), 2, cv2.LINE_AA)
    cv2.addWeighted(frame, 1.0, ring, ring_alpha, 0, dst=frame)
    cv2.circle(frame, (x, y), 5, (25, 45, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 2, (115, 154, 255), -1, cv2.LINE_AA)


def draw_city_name(frame: np.ndarray, point: tuple[int, int], progress: float) -> None:
    x, y = point
    fade = smootherstep((progress - 0.76) / 0.13)
    if fade <= 0:
        return
    font = ImageFont.truetype(str(FONT), 58)
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), CITY, font=font, stroke_width=1)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = max(24, min(WIDTH - tw - 24, x - tw // 2))
    ty = max(24, min(HEIGHT - th - 24, y + 48))
    draw.text((tx - bbox[0], ty - bbox[1]), CITY, font=font,
              fill=(250, 249, 238, int(255 * fade)),
              stroke_width=2, stroke_fill=(0, 18, 11, int(235 * fade)))
    rgba = np.asarray(canvas)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    rgb = rgba[:, :, :3][:, :, ::-1].copy()
    frame[:] = np.clip(frame.astype(np.float32) * (1 - alpha) + rgb * alpha,
                       0, 255).astype(np.uint8)


def render_frame(pyramid: DynamicTilePyramid, frame_no: int) -> np.ndarray:
    p = frame_no / (DURATION_FRAMES - 1)
    lat, lon, zoom = camera_at(frame_no)
    frame = pyramid.sample_continuous(lat, lon, zoom, WIDTH, HEIGHT)
    frame = grade_map(frame)
    draw_grid(frame, p)
    # The point is fixed geographically, so it travels naturally with the map
    # while the camera approaches and then settles over the city.
    from dynamic_tile_pyramid import latlon_to_global_px
    z0 = math.floor(zoom)
    frac = zoom - z0
    scale = 2.0 ** frac
    gx, gy = latlon_to_global_px(TARGET[0], TARGET[1], z0)
    ax, ay = latlon_to_global_px(lat, lon, z0)
    point = (int(round(WIDTH / 2 + (gx - ax) * scale)),
             int(round(HEIGHT / 2 + (gy - ay) * scale)))
    draw_beacon(frame, point, p)
    draw_city_name(frame, point, p)
    return frame


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pyramid = DynamicTilePyramid(provider="esri_sat")
    # Warm only the nearby camera corridor and the destination city scale.
    for lat, lon in (START, TARGET):
        pyramid.prefetch_pyramid(lat, lon, min_zoom=8, max_zoom=12,
                                 tile_radius_x=4, tile_radius_y=4)
    command = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
               "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "18", "-pix_fmt", "yuv420p", str(OUT)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for f in range(DURATION_FRAMES):
        proc.stdin.write(render_frame(pyramid, f).tobytes())
        if f % FPS == 0:
            print(f"rendered {f}/{DURATION_FRAMES} frames", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")
    print(f"prototype: {OUT}", flush=True)


if __name__ == "__main__":
    main()
