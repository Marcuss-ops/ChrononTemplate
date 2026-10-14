#!/usr/bin/env python3
"""
geo_camera_v1 - small places showcase.

Proves the global pyramid works for places Google Maps barely bothers with:

  lughetto_pure_dive      space -> a 422-soul frazione, landing z=18
  campagna_lupia_dive     space -> the comune, landing z=17.8
  venezia_dive_then_tilt  space -> San Marco, then the 35-degree horizon
  lagoon_medley           dive to the lagoon scale, a glow route walks from
                          Campagna Lupia to Lughetto, then the camera pans
                          and dives after the route into the village itself

Every shot is gated (strict zoom-velocity continuity on each dive segment,
byte determinism) before it encodes, and uploaded to Drive.
"""

import sys
import math
import time
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import cv2

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
sys.path.insert(0, str(BASE_DIR / "Chronon3d/tools/cartography"))
sys.path.insert(0, str(BASE_DIR / "ChrononTemplate/tools"))

from dynamic_tile_pyramid import (  # noqa: E402
    DynamicTilePyramid, draw_hud_overlay, latlon_to_global_px,
)
from render_dynamic_map_3d_orbit_colosseum import (  # noqa: E402
    refresh_drive_token, upload_to_drive, DRIVE_FOLDER_ID,
)
from render_geo_camera_canary import (  # noqa: E402
    warp_matrix, smootherstep, OVERSIZE,
)

WIDTH, HEIGHT, FPS = 1920, 1080, 30


def _blend_layer_at(frame: np.ndarray, rgba: np.ndarray, ox: int = 0, oy: int = 0) -> None:
    """Composite an RGBA Pillow/NumPy layer over a uint8 BGR frame.

    Same arithmetic as the historical float32 full-frame blend
    (frame*(1-a) + layer*a), restricted to the layer's nonzero-alpha
    bounding box and evaluated in uint16 with rounded integer division:
    a caption rail covering a few percent of the frame no longer pays
    six-million-voxel float maths per frame. Deviation vs the float path
    is at most 1 LSB on the blended channels.
    """
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        return
    alpha = rgba[:, :, 3]
    if not alpha.any():
        return
    ys, xs = np.nonzero(alpha)
    ay0, ay1 = int(ys.min()), int(ys.max()) + 1
    ax0, ax1 = int(xs.min()), int(xs.max()) + 1
    a = alpha[ay0:ay1, ax0:ax1].astype(np.uint32)[:, :, None]
    bgr = rgba[ay0:ay1, ax0:ax1, :3][:, :, ::-1].astype(np.uint32)
    fy0, fy1, fx0, fx1 = ay0 + oy, ay1 + oy, ax0 + ox, ax1 + ox
    roi = frame[fy0:fy1, fx0:fx1]
    out = ((roi.astype(np.uint32) * (255 - a) + bgr * a + 127) // 255).astype(np.uint8)
    frame[fy0:fy1, fx0:fx1] = out


@lru_cache(maxsize=64)
def _label_font(path: str, size: int):
    """Hair been per-frame: Pillow keeps no glyph cache across truetype loads,
    and markers reloaded the same .ttf for every frame of a clip."""
    from PIL import ImageFont
    return ImageFont.truetype(path, size)
CYAN = (0, 240, 255)

LUG = (45.38271, 12.12881)     # Lughetto - frazione, 422 anime
CLP = (45.35430, 12.09640)     # Campagna Lupia - comune
VCE = (45.4408, 12.3155)       # Venezia - San Marco
MID = ((LUG[0] + CLP[0]) / 2, (LUG[1] + CLP[1]) / 2)  # route midpoint

OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PYRAMID: DynamicTilePyramid = None  # set in main()


def roll_bank(p: float) -> float:
    return -8.0 * math.sin(max(0.0, min(1.0, p)) * math.pi)


def geo_to_screen(lat: float, lon: float, anchor: tuple[float, float],
                  zoom: float, width: int = WIDTH, height: int = HEIGHT) -> tuple[int, int]:
    """Where a geographic point lands on the current frame (nadir plates).

    Same math the pyramid composes with: the anchor's global pixel sits at the
    frame centre, every other point scales out from there.
    """
    zf = math.floor(zoom)
    scale = 2.0 ** (zoom - zf)
    gx, gy = latlon_to_global_px(lat, lon, int(zf))
    ax, ay = latlon_to_global_px(anchor[0], anchor[1], int(zf))
    return (int(round(width / 2 + (gx - ax) * scale)),
            int(round(height / 2 + (gy - ay) * scale)))


def glass_card(frame: np.ndarray, lines: list[tuple[str, int, float, tuple, int]],
               alpha: float, corner: str = "bl") -> None:
    """Frosted glass info card, clamped inside the frame."""
    if alpha <= 0.02:
        return
    card_w, card_h = 620, 40 + 26 * len(lines)
    card_x = 60 if corner == "bl" else WIDTH - card_w - 60
    card_y = HEIGHT - card_h - 80
    sub = frame[card_y:card_y + card_h, card_x:card_x + card_w]
    if sub.shape[0] == card_h and sub.shape[1] == card_w:
        blurred = cv2.GaussianBlur(sub, (21, 21), 0)
        tint = np.full((card_h, card_w, 3), (15, 20, 32), dtype=np.uint8)
        glass = cv2.addWeighted(blurred, 0.4, tint, 0.6, 0)
        frame[card_y:card_y + card_h, card_x:card_x + card_w] = cv2.addWeighted(
            sub, 1.0 - alpha, glass, alpha, 0)
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h),
                  CYAN, 2, cv2.LINE_AA)
    for text, dy, scale, col, thick in lines:
        cv2.putText(frame, text, (card_x + 24, card_y + dy),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, col, thick, cv2.LINE_AA)


def draw_chain(frame: np.ndarray, zoom: float, bands: tuple) -> None:
    """The geographic chain tag: the band that owns this scale, fading out
    as the next one takes over."""
    for lo, hi, name in bands:
        if lo <= zoom < hi:
            fade = min(zoom - lo, hi - zoom)
            alpha = max(0.0, min(1.0, fade / 0.25))
            if alpha <= 0.02:
                return
            col = (int(160 * alpha), int(220 * alpha), int(255 * alpha))
            (tw, _), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
            cv2.putText(frame, name, ((WIDTH - tw) // 2, 96),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, 2, cv2.LINE_AA)
            return


def draw_spring_pin(frame: np.ndarray, point: tuple[int, int], progress: float,
                    fire: float = 0.70, span: float = 0.16) -> None:
    """Drop pin with overshoot spring, then landing pulse."""
    if progress < fire:
        return
    t = min(1.0, (progress - fire) / span)
    omega, zeta = 15.0, 0.52
    wd = omega * math.sqrt(1.0 - zeta * zeta)
    bounce = 1.0 - math.exp(-zeta * omega * t) * math.cos(wd * t) if t < 1.0 else 1.0
    cx, cy = point
    drop = int(240 * (1.0 - bounce))
    head_y = cy - drop
    cv2.ellipse(frame, (cx, cy), (26, 9), 0, 0, 360, (20, 30, 40), -1)
    cv2.line(frame, (cx, head_y), (cx, cy), CYAN, 2, cv2.LINE_AA)
    cv2.circle(frame, (cx, head_y), 13, (0, 60, 200), -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, head_y), 13, (255, 255, 255), 2, cv2.LINE_AA)
    if t >= 1.0:
        ph = (progress * 2.0) % 1.0
        r = int(12 + 60 * ph)
        a = max(0.0, 1.0 - ph)
        cv2.circle(frame, (cx, cy), r, (int(0 * a), int(240 * a), int(255 * a)), 2, cv2.LINE_AA)


def draw_location_glow(frame: np.ndarray, point: tuple[int, int], progress: float,
                       area_radius_px: int = 0) -> None:
    """Pulsing amber beacon with a bright core and optional area halo."""
    cx, cy = point
    t = max(0.0, min(1.0, progress))
    pulse = 0.5 + 0.5 * math.sin(t * math.tau * 1.7)
    radius = 40 + int(6 * pulse)
    # OpenCV uses BGR: this is #FFD166. Keep the center visibly warm instead
    # of drawing the near-black target dot that disappeared on dark basemaps.
    accent = (102, 209, 255)
    # Both blurred sprites interact with the frame only inside radius +
    # kernel-half of the sigma-16 blur (ksize 97 on CV_8U), so render and
    # blend them in a small local window with a generous margin instead of
    # two full-frame zeros_like + GaussianBlur + addWeighted passes per
    # frame (the historical path cost over 200ms/frame at 1080p).
    m = radius + 6 * 16 + 4
    h, w = frame.shape[:2]
    x0, x1 = max(0, cx - m), min(w, cx + m)
    y0, y1 = max(0, cy - m), min(h, cy + m)
    if x0 >= x1 or y0 >= y1:
        return
    roi = frame[y0:y1, x0:x1]
    lx, ly = cx - x0, cy - y0
    # Keep the ring crisp while adding a soft halo in the same map accent.
    light = np.zeros_like(roi)
    cv2.circle(light, (lx, ly), radius, accent, 4, cv2.LINE_AA)
    light = cv2.GaussianBlur(light, (0, 0), 16)
    roi[:] = cv2.addWeighted(roi, 1.0, light, 0.66, 0)
    cv2.circle(roi, (lx, ly), radius, accent, 3, cv2.LINE_AA)
    # Keep the geographic cue as a hollow beacon. A filled center reads as a
    # pin/dot at this scale, so use only a quiet diffuse core and thin ring.
    core = np.zeros_like(roi)
    cv2.circle(core, (lx, ly), 13, accent, -1, cv2.LINE_AA)
    core = cv2.GaussianBlur(core, (0, 0), 8)
    roi[:] = cv2.addWeighted(roi, 1.0, core, 0.42, 0)
    cv2.circle(roi, (lx, ly), 8, accent, 2, cv2.LINE_AA)


MAP_LABEL_ANIMATIONS = (
    "gentle_fade", "soft_glow", "clean_fade", "word_soft_fade",
    "slow_fade", "quiet_bloom", "quick_fade", "silky_fade",
    "subtle_halo", "cinematic_fade", "diffuse_city_beacon",
    "rise_up", "pop_in", "soft_tracking",
    "title_top", "badge_side", "huge_center",
    "small_above", "caption_card", "editorial_serif",
    "gpin_bubble", "card_glass", "bare_big", "glow_react", "editorial_tag",
    "ribbon", "dot_ring", "outline_box",
)

# Distinct-geometry label styles: different size, position and typeface.
# The ten calm fades share one geometry; these six do not.
NEW_LABEL_GEOMETRIES = (
    "title_top", "badge_side", "huge_center",
    "small_above", "caption_card", "editorial_serif",
)

# Full marker compositions: own marker + own text shape, no standard beacon,
# no bottom rail (the rail is suppressed for these in
# draw_editorial_map_caption). gpin_bubble is a Google-style red pin with a
# white bubble; card_glass a frosted card; bare_big naked display type;
# ribbon a full-width band; dot_ring an ultra-minimal dot; outline_box an
# empty wireframe box with corner ticks.
COMPOSITION_STYLES = (
    "gpin_bubble", "card_glass", "bare_big",
    "ribbon", "dot_ring", "outline_box",
)

# Styles drawn through the marker path in production minimal_map renders
# (geo_runtime calls draw_map_location_marker at the camera nadir for
# these): the 6 distinct geometries plus the 6 full compositions. Every
# other animation keeps the approved rail-only production look.
MARKER_DRAWN_STYLES = NEW_LABEL_GEOMETRIES + COMPOSITION_STYLES + ("glow_react", "editorial_tag")


def apply_city_beacon_map_style(frame: np.ndarray, progress: float) -> None:
    """Soft green satellite grade and fine reference-style screen grid.

    The grade stays readable on bright documentary footage: the frame keeps
    ~77% of its luminance (plus a light green lift) instead of the former
    ~63%, so tile detail survives final-video compression. The GPU LUT below
    encodes the exact same transfer — keep the two in sync.
    """
    h, w = frame.shape[:2]
    green_tint = np.empty_like(frame)
    green_tint[:] = (14, 42, 16)  # BGR
    cv2.addWeighted(frame, 0.86, green_tint, 0.14, 0, dst=frame)
    frame[:] = np.clip(frame.astype(np.float32) * 0.90, 0, 255).astype(np.uint8)
    step = max(1, round(min(h, w) / 13.5))
    grid = np.zeros_like(frame)
    color = (32, 78, 39)
    for x in range(0, w, step):
        cv2.line(grid, (x, 0), (x, h - 1), color, 1, cv2.LINE_AA)
    for y in range(0, h, step):
        cv2.line(grid, (0, y), (w - 1, y), color, 1, cv2.LINE_AA)
    cv2.addWeighted(frame, 1.0, grid, 0.38, 0, dst=frame)


_OPENCL_GRID_CACHE = {}
_OPENCL_LABEL_CACHE = {}
_OPENCL_LUT = None
_OPENCL_BEACON_CACHE = {}


def apply_city_beacon_map_style_opencl(frame, progress: float):
    """GPU path for the city basemap grade and grid; returns a UMat."""
    global _OPENCL_LUT
    import cv2
    import numpy as np
    h, w = HEIGHT, WIDTH
    if _OPENCL_LUT is None:
        lut = np.empty((1, 256, 3), dtype=np.uint8)
        tint = (14, 42, 16)
        for channel in range(3):
            values = np.arange(256, dtype=np.float32) * 0.774 + tint[channel] * 0.126
            lut[0, :, channel] = np.clip(values, 0, 255).astype(np.uint8)
        _OPENCL_LUT = lut
    frame = cv2.LUT(frame, _OPENCL_LUT)
    cache_key = (w, h)
    grid = _OPENCL_GRID_CACHE.get(cache_key)
    if grid is None:
        grid_host = np.zeros((h, w, 3), dtype=np.uint8)
        step = max(1, round(min(h, w) / 13.5))
        for x in range(0, w, step):
            cv2.line(grid_host, (x, 0), (x, h - 1), (32, 78, 39), 1, cv2.LINE_AA)
        for y in range(0, h, step):
            cv2.line(grid_host, (0, y), (w - 1, y), (32, 78, 39), 1, cv2.LINE_AA)
        grid = cv2.UMat(grid_host)
        _OPENCL_GRID_CACHE[cache_key] = grid
    return cv2.addWeighted(frame, 1.0, grid, 0.38, 0.0)


def draw_map_location_marker_opencl(frame, point: tuple[int, int], name: str,
                                    progress: float, animation: str = "diffuse_city_beacon",
                                    area_radius_px: int = 0):
    """Draw the beacon and label on the GPU-rendered UMat map frame."""
    import cv2
    import numpy as np
    h, w = HEIGHT, WIDTH
    cx, cy = point
    # Start the target as the camera settles, instead of leaving a tiny glow
    # until the last seconds of the map clip.
    fade = max(0.0, min(1.0, (progress - 0.44) / 0.10))
    fade = fade * fade * (3.0 - 2.0 * fade)
    pulse = 0.5 + 0.5 * math.sin(max(0.0, progress - 0.68) * math.tau * 1.2)
    radius = max(24, round(min(h, w) * 0.052))
    key = (w, h, cx, cy, radius)
    cached = _OPENCL_BEACON_CACHE.get(key)
    if cached is None:
        glow_host = np.zeros((h, w, 3), dtype=np.uint8)
        accent = (18, 174, 255)  # vivid amber in OpenCV's BGR order
        cv2.circle(glow_host, (cx, cy), radius + 12, accent, -1, cv2.LINE_AA)
        glow_host = cv2.GaussianBlur(glow_host, (0, 0), max(8.0, radius * 0.62))
        marker_host = np.zeros((h, w, 3), dtype=np.uint8)
        marker_mask = np.zeros((h, w), dtype=np.uint8)
        # Opaque strokes stay visible over pale topographic tiles; the
        # previous additive-only treatment washed into the white roads.
        cv2.circle(marker_host, (cx, cy), radius, (30, 24, 18), 8, cv2.LINE_AA)
        cv2.circle(marker_mask, (cx, cy), radius, 255, 10, cv2.LINE_AA)
        cv2.circle(marker_host, (cx, cy), radius, (0, 165, 255), 4, cv2.LINE_AA)
        cv2.circle(marker_mask, (cx, cy), radius, 255, 6, cv2.LINE_AA)
        cv2.circle(marker_host, (cx, cy), 8, (0, 70, 255), -1, cv2.LINE_AA)
        cv2.circle(marker_mask, (cx, cy), 8, 255, -1, cv2.LINE_AA)
        cv2.circle(marker_host, (cx, cy), 8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.circle(marker_mask, (cx, cy), 8, 255, 3, cv2.LINE_AA)
        point_host = np.zeros((h, w, 3), dtype=np.uint8)
        point_mask = np.zeros((h, w), dtype=np.uint8)
        # Keep the original exact-location point visible from frame one;
        # the larger target ring is a later emphasis around this point.
        cv2.circle(point_host, (cx, cy), 12, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(point_mask, (cx, cy), 12, 255, -1, cv2.LINE_AA)
        cv2.circle(point_host, (cx, cy), 8, (25, 25, 235), -1, cv2.LINE_AA)
        cv2.circle(point_host, (cx, cy), 3, (255, 220, 175), -1, cv2.LINE_AA)
        cached = (cv2.UMat(glow_host), cv2.UMat(marker_host),
                  cv2.UMat(marker_mask), cv2.UMat(point_host),
                  cv2.UMat(point_mask))
        _OPENCL_BEACON_CACHE[key] = cached
    glow, marker, marker_mask, point, point_mask = cached
    frame = cv2.copyTo(point, point_mask, frame)
    if fade > 0.001:
        frame = cv2.addWeighted(frame, 1.0, glow, fade * (0.78 + 0.18 * pulse), 0.0)
        frame = cv2.copyTo(marker, marker_mask, frame)

    label = " ".join(str(name or "").split())
    t = max(0.0, min(1.0, (progress - 0.56) / 0.12))
    alpha = t * t * (3.0 - 2.0 * t)
    if label and alpha > 0.005:
        key = (w, h, label)
        overlay = _OPENCL_LABEL_CACHE.get(key)
        if overlay is None:
            font_face = cv2.FONT_HERSHEY_SIMPLEX
            font_scale, text_thickness = 1.15, 2
            (tw, th), baseline = cv2.getTextSize(label, font_face, font_scale, text_thickness)
            x = max(20, min(w - tw - 20, cx - tw // 2))
            y = min(h - baseline - 16, cy + radius + th + 36)
            shadow_host = np.zeros((h, w, 3), dtype=np.uint8)
            shadow_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.putText(shadow_host, label, (x + 2, y + 3), font_face, font_scale,
                        (0, 0, 0), 9, cv2.LINE_AA)
            cv2.putText(shadow_mask, label, (x + 2, y + 3), font_face, font_scale,
                        255, 11, cv2.LINE_AA)
            text_host = np.zeros((h, w, 3), dtype=np.uint8)
            text_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.putText(text_host, label, (x, y), font_face, font_scale,
                        (255, 255, 255), text_thickness, cv2.LINE_AA)
            cv2.putText(text_mask, label, (x, y), font_face, font_scale,
                        255, text_thickness + 2, cv2.LINE_AA)
            overlay = (cv2.UMat(shadow_host), cv2.UMat(255 - shadow_mask),
                       cv2.UMat(text_host), cv2.UMat(255 - text_mask))
            _OPENCL_LABEL_CACHE[key] = overlay
        shadow, shadow_outside, text, text_outside = overlay
        blended = cv2.addWeighted(frame, 1.0 - alpha, shadow, alpha, 0.0)
        frame = cv2.copyTo(frame, shadow_outside, blended)
        blended = cv2.addWeighted(frame, 1.0 - alpha, text, alpha, 0.0)
        frame = cv2.copyTo(frame, text_outside, blended)
        frame = blended
    return frame


def draw_diffuse_city_beacon(frame: np.ndarray, point: tuple[int, int],
                             progress: float, area_radius_px: int = 0) -> None:
    """A loose red glow over the city, with a small center and soft pulse."""
    h, w = frame.shape[:2]
    cx, cy = point
    fade = max(0.0, min(1.0, (progress - 0.68) / 0.12))
    fade = fade * fade * (3.0 - 2.0 * fade)
    if fade <= 0.001:
        return
    pulse = 0.5 + 0.5 * math.sin(max(0.0, progress - 0.68) * math.tau * 1.2)
    radius = max(24, round(min(h, w) * (0.044 + 0.005 * pulse)))
    halo_extent = max(round(radius * 0.62 * 6) + radius + 2,
                      (area_radius_px + max(4, area_radius_px // 5 * 3) + 2
                       if area_radius_px > 0 else 0))
    x0, x1 = max(0, cx - halo_extent), min(w, cx + halo_extent + 1)
    y0, y1 = max(0, cy - halo_extent), min(h, cy + halo_extent + 1)
    if x0 >= x1 or y0 >= y1:
        return
    roi = frame[y0:y1, x0:x1]
    local = (cx - x0, cy - y0)
    glow = np.zeros_like(roi)
    cv2.circle(glow, local, radius, (8, 20, 245), -1, cv2.LINE_AA)
    cv2.ellipse(glow, (local[0] - radius // 5, local[1] + radius // 8),
                (int(radius * 0.75), int(radius * 0.52)), -17, 0, 360,
                (8, 12, 255), -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), max(8.0, radius * 0.62))
    cv2.addWeighted(roi, 1.0, glow, fade * (0.78 + 0.18 * pulse), 0, dst=roi)
    if area_radius_px > 0:
        area = np.zeros_like(roi)
        cv2.circle(area, local, area_radius_px, (8, 18, 210), 2, cv2.LINE_AA)
        area = cv2.GaussianBlur(area, (0, 0), max(4, area_radius_px // 5))
        cv2.addWeighted(roi, 1.0, area, fade * 0.34, 0, dst=roi)
    cv2.circle(roi, local, 4, (12, 26, 255), -1, cv2.LINE_AA)
    cv2.circle(roi, local, 2, (135, 165, 255), -1, cv2.LINE_AA)


def draw_reaction_glow(frame: np.ndarray, point: tuple[int, int],
                       progress: float) -> None:
    """Animate a luminous map target with a soft bloom and expanding ripples."""
    h, w = frame.shape[:2]
    cx, cy = point
    p = max(0.0, min(1.0, float(progress)))
    reveal = max(0.0, min(1.0, p / 0.20))
    reveal = reveal * reveal * (3.0 - 2.0 * reveal)
    if reveal <= 0.001:
        return

    pulse = 0.5 + 0.5 * math.sin(math.tau * p * 1.8)
    accent = (18, 72, 255)  # vivid coral red in OpenCV BGR

    # Keep blur/compositing local to the beacon. Full-frame glow buffers made
    # this lightweight marker dominate each 1080p route frame's render time.
    extent = 144
    x0, x1 = max(0, cx - extent), min(w, cx + extent + 1)
    y0, y1 = max(0, cy - extent), min(h, cy + extent + 1)
    roi = frame[y0:y1, x0:x1]
    center = (cx - x0, cy - y0)
    bloom = np.zeros_like(roi)
    cv2.circle(bloom, center, 58 + round(9 * pulse), accent, -1, cv2.LINE_AA)
    bloom = cv2.GaussianBlur(bloom, (0, 0), 27)
    cv2.addWeighted(roi, 1.0, bloom, reveal * (0.52 + 0.16 * pulse), 0, dst=roi)

    # Two staggered waves keep the point alive during the spoken city beat.
    for offset in (0.0, 0.5):
        phase = (p * 1.10 + offset) % 1.0
        radius = 12 + round(62 * phase)
        ring = np.zeros_like(roi)
        cv2.circle(ring, center, radius, accent, 3, cv2.LINE_AA)
        ring = cv2.GaussianBlur(ring, (0, 0), 3.5)
        cv2.addWeighted(roi, 1.0, ring, reveal * (0.82 * (1.0 - phase)),
                        0, dst=roi)

    # A crisp luminous core provides a precise target without a pin silhouette.
    cv2.circle(roi, center, 10 + round(2 * pulse), accent, -1, cv2.LINE_AA)
    cv2.circle(roi, center, 5, (238, 248, 255), -1, cv2.LINE_AA)


def draw_map_location_marker(frame: np.ndarray, point: tuple[int, int],
                             name: str, progress: float,
                             animation: str = "gentle_fade",
                             area_radius_px: int = 0) -> None:
    if animation in COMPOSITION_STYLES:
        # Compositions own their marker: no standard amber beacon, otherwise
        # every treatment would share the same glow and look identical.
        draw_map_marker_label(frame, point, name, progress, animation)
        return
    if animation == "glow_react":
        draw_reaction_glow(frame, point, progress)
        draw_map_marker_label(frame, point, name, progress, animation)
        return
    if animation == "editorial_tag":
        draw_map_marker_label(frame, point, name, progress, animation)
        return
    if animation == "diffuse_city_beacon":
        draw_diffuse_city_beacon(frame, point, progress, area_radius_px)
    else:
        draw_location_glow(frame, point, progress, area_radius_px)
    draw_map_marker_label(frame, point, name, progress, animation)


def draw_editorial_map_caption(frame: np.ndarray, text: str, progress: float,
                              typography: dict | None = None,
                              animation: str = "gentle_fade") -> np.ndarray:
    """Render the place name in a Chronon-style rail below the map imagery."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    # The classic dynamic-map renderer keeps OpenCL frames in cv2.UMat until
    # its final caption pass. Pillow/NumPy need a host array, so round-trip the
    # frame here and restore UMat on return; callers can continue using the GPU
    # encode path without relying on UMat exposing ndarray.shape/astype.
    was_umat = isinstance(frame, cv2.UMat)
    if was_umat:
        frame = frame.get()

    def restore_frame(value: np.ndarray) -> np.ndarray:
        return cv2.UMat(value) if was_umat else value

    label = " ".join(str(text or "").split())
    if not label or animation == "none" or animation in MARKER_DRAWN_STYLES:
        # Marker-drawn styles carry their own name at the camera nadir
        # (drawn by draw_map_location_marker); the standard rail would
        # duplicate it and make every treatment look the same.
        return restore_frame(frame)
    h, w = frame.shape[:2]
    # These values come from the run-level OverlayStyle payload projected by
    # PipelineGen; fallback values match its canonical Bricolage phrase style.
    style = typography or {}
    font_files = {
        "bricolage_grotesque": "Bricolage-Grotesque.ttf",
        "inter": "Inter.ttf", "inter_bold": "Inter-Bold.ttf",
        "poppins": "Poppins-Bold.ttf", "dejavu_sans": "DejaVuSans.ttf",
        "playfair_display_italic": "PlayfairDisplay-Italic.ttf",
    }
    family = str(style.get("font_family", "bricolage_grotesque"))
    if family not in font_files:
        raise ValueError(f"unsupported runtime typography font_family: {family}")
    font_path = BASE_DIR / "RenderingGen/renderinggen/assets/fonts" / font_files[family]
    font_size = max(32, round(float(style.get("font_size_px", 92)) * w / 1920))
    font = _editorial_caption_font(str(font_path), font_size)
    stroke_width = max(0, round(float(style.get("stroke_size", 2))))
    shadow_blur = max(0, round(float(style.get("shadow_blur_px", 14)) * w / 1920))
    shadow_opacity = max(0.0, min(1.0, float(style.get("shadow_opacity", 0.7))))
    glow_size = max(0, round(float(style.get("glow_size", 10)) * w / 1920))
    glow_intensity = max(0.0, min(1.0, float(style.get("glow_intensity", 0.4))))
    fill = str(style.get("fill", "#F8F5EA"))
    shadow_color = str(style.get("shadow_color", "#000000"))
    glow_color = str(style.get("glow_color", "#FFFFFF"))
    bbox = font.getbbox(label, stroke_width=stroke_width)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rail_h = max(132, round(h * 0.16))
    rail_y = h - rail_h - max(26, round(h * 0.025))
    rail_margin = max(48, round(w * 0.06))
    rail = (rail_margin, 0, w - rail_margin, rail_h)
    center_x = w // 2
    text_x = center_x - text_w // 2
    text_y = (rail_h - text_h) // 2 - bbox[1]
    animation_timing = {
        "gentle_fade": (0.78, 0.16), "soft_glow": (0.75, 0.20),
        "clean_fade": (0.81, 0.13), "word_soft_fade": (0.76, 0.18),
        "slow_fade": (0.67, 0.29), "quiet_bloom": (0.72, 0.22),
        "quick_fade": (0.84, 0.08), "silky_fade": (0.74, 0.21),
        "subtle_halo": (0.77, 0.17), "cinematic_fade": (0.70, 0.25),
        "diffuse_city_beacon": (0.78, 0.16),
        "rise_up": (0.74, 0.20), "pop_in": (0.82, 0.10),
        "soft_tracking": (0.68, 0.26),
        "title_top": (0.70, 0.22), "badge_side": (0.78, 0.16),
        "huge_center": (0.66, 0.28), "small_above": (0.80, 0.14),
        "caption_card": (0.74, 0.20), "editorial_serif": (0.72, 0.22),
    }
    if animation not in animation_timing:
        raise ValueError(f"unknown map caption animation: {animation}")
    start, duration = animation_timing[animation]
    reveal = max(0.0, min(1.0, (progress - start) / duration))
    alpha = int(255 * reveal * reveal * (3.0 - 2.0 * reveal))
    if alpha <= 0:
        return restore_frame(frame)

    # 01_ed_saudi_base capsule style:
    # Compact rounded box with Gaussian blurred drop shadow, 1px keyline,
    # uppercase condensed bold font with tracking (+2px) and 8px upward drift.
    label_upper = label.upper()
    pad_x = max(18, round(22.0 * w / 1920))
    pad_y = max(8, round(10.0 * h / 1080))
    letter_spacing = max(1, round(2.0 * w / 1920))

    # Measure tracked title width
    tracked_w = 0
    char_boxes = []
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)
    for ch in label_upper:
        cb = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
        char_boxes.append((cb[2] - cb[0], cb))
        tracked_w += (cb[2] - cb[0]) + letter_spacing
    if tracked_w > 0:
        tracked_w -= letter_spacing

    th = text_h
    box_w = tracked_w + 2 * pad_x
    box_h = th + 2 * pad_y

    # Position at bottom-center with safe margin
    safe_bottom = max(36, round(h * 0.08))
    box_x0 = (w - box_w) // 2
    box_y0 = h - box_h - safe_bottom

    # Upward drift during entrance (8px lift decaying with ease)
    ease_v = reveal * reveal * (3.0 - 2.0 * reveal)
    y_lift = int(round((1.0 - ease_v) * 8))
    box_y0_eff = box_y0 + y_lift
    box_y1_eff = box_y0_eff + box_h
    box_x1 = box_x0 + box_w

    # Canvas-localized render: the capsule, its shadow and the tracked text
    # all live inside box extents + shadow spill + entrance drift, so the
    # 1920x1080 Pillow surface (and its full-frame GaussianBlur) collapses
    # here to a window a few hundred pixels tall.
    blur_r = max(4, round(8 * w / 1920))
    margin = 4 * blur_r + 8
    lx0 = max(0, box_x0 - margin)
    ly0 = max(0, box_y0_eff - margin)
    lx1 = min(w, box_x1 + margin)
    ly1 = min(h, box_y1_eff + 4 + 3 * blur_r + margin)
    ow, oh = lx1 - lx0, ly1 - ly0
    if ow <= 0 or oh <= 0:
        return restore_frame(frame)
    TX, TY = lx0, ly0  # frame -> canvas translation

    layer = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))

    # 1. Soft blurred drop shadow (radius 5, blur 8, alpha up to 130)
    shadow = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (box_x0 - TX, box_y0_eff + 4 - TY, box_x1 - TX, box_y1_eff + 4 - TY),
        radius=max(4, round(5 * w / 1920)),
        fill=(0, 0, 0, int(130 * reveal)),
    )
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur_r)))

    # 2. Translucent dark capsule box + 1px subtle keyline
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(
        (box_x0 - TX, box_y0_eff - TY, box_x1 - TX, box_y1_eff - TY),
        radius=max(4, round(4 * w / 1920)),
        fill=(10, 16, 22, int(242 * reveal)),
        outline=(221, 230, 232, int(100 * reveal)),
        width=1,
    )

    # 3. Tracked uppercase text with 1px stroke
    tx = box_x0 + pad_x - TX
    ty = box_y0_eff + pad_y - bbox[1] - TY
    ink = (242, 244, 238, int(255 * reveal))
    stroke_ink = (3, 8, 12, int(210 * reveal))
    for ch, (cw, cb) in zip(label_upper, char_boxes):
        draw.text(
            (tx, ty), ch, font=font, fill=ink,
            stroke_width=1, stroke_fill=stroke_ink,
        )
        tx += cw + letter_spacing

    _blend_layer_at(frame, np.asarray(layer), ox=lx0, oy=ly0)
    return restore_frame(frame)


@lru_cache(maxsize=16)
def _editorial_caption_font(path: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def _draw_composition(frame: np.ndarray, point: tuple[int, int],
                      label: str, t: float, ease: float, animation: str) -> None:
    """Draw a full marker composition: own marker + own text shape.

    No standard amber beacon and no bottom rail (suppressed upstream), so
    each composition reads as a different video, not a different fade.
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    h, w = frame.shape[:2]
    cx, cy = point

    def font(name: str, size: int):
        return _label_font(str(BASE_DIR / "Chronon3d/assets/fonts" / name), size)

    overlay = None
    draw = None

    overlay_origin = None

    def ensure_overlay(bounds: tuple[int, int, int, int]):
        nonlocal overlay, draw, overlay_origin
        x0, y0, x1, y1 = bounds
        margin = 24
        ox0, oy0 = max(0, x0 - margin), max(0, y0 - margin)
        ox1, oy1 = min(w, x1 + margin), min(h, y1 + margin)
        if overlay is not None:
            old_x0, old_y0, old_x1, old_y1 = overlay_origin
            if old_x0 <= ox0 and old_y0 <= oy0 and old_x1 >= ox1 and old_y1 >= oy1:
                return overlay_origin
            ox0, oy0 = min(ox0, old_x0), min(oy0, old_y0)
            ox1, oy1 = max(ox1, old_x1), max(oy1, old_y1)
            expanded = Image.new("RGBA", (ox1 - ox0, oy1 - oy0), (0, 0, 0, 0))
            expanded.alpha_composite(overlay, (old_x0 - ox0, old_y0 - oy0))
            overlay = expanded
        else:
            overlay = Image.new("RGBA", (ox1 - ox0, oy1 - oy0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        overlay_origin = (ox0, oy0, ox1, oy1)
        return overlay_origin

    def composite() -> None:
        if overlay is not None:
            _blend_layer_at(frame, np.asarray(overlay), ox=overlay_origin[0],
                            oy=overlay_origin[1])

    if animation == "gpin_bubble":
        # Google-style red teardrop pin dropping onto the point, white
        # bubble with dark text above it.
        import math
        drop = 1.0 - (1.0 - t) ** 3
        py = cy - round(170 * (1.0 - drop))
        pa = int(255 * drop)
        if pa > 1:
            overlay_origin = ensure_overlay((cx - 32, py - 70, cx + 32, py + 10))
            ox, oy = overlay_origin[:2]
            draw.ellipse((cx - 30 - ox, py - 68 - oy, cx + 30 - ox, py - 8 - oy),
                         fill=(220, 30, 30, pa))
            draw.polygon([(cx - 23 - ox, py - 26 - oy),
                          (cx + 23 - ox, py - 26 - oy), (cx - ox, py + 8 - oy)],
                         fill=(220, 30, 30, pa))
            draw.ellipse((cx - 11 - ox, py - 49 - oy, cx + 11 - ox, py - 29 - oy),
                         fill=(255, 255, 255, pa))
        # Bring the place name in almost with the falling pin. The camera is
        # still moving at this point, so the label reads as part of the arrival.
        tb = max(0.0, min(1.0, (t - 0.05) / 0.70))
        tb = tb * tb * (3.0 - 2.0 * tb)
        over = 1.0 + 0.25 * math.sin(min(1.0, tb * 1.15) * math.pi)
        ba = max(0.0, min(1.0, tb * over))
        if ba > 0.01:
            f = font("Inter-SemiBold.ttf", 36)
            bbox = f.getbbox(label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            bw, bh = tw + 72, th + 40
            bx0 = max(10, min(w - bw - 10, cx - bw // 2))
            by1 = py - 84
            by0 = by1 - bh
            bia = int(255 * ba)
            overlay_origin = ensure_overlay((min(bx0, cx - 32), min(by0, py - 70),
                                              max(bx0 + bw, cx + 32), max(by1 + 20, py + 10)))
            ox, oy = overlay_origin[:2]
            draw.rounded_rectangle((bx0 - ox, by0 - oy, bx0 + bw - ox, by1 - oy), radius=22,
                                   fill=(255, 255, 255, bia))
            draw.polygon([(cx - 12 - ox, by1 - 2 - oy), (cx + 12 - ox, by1 - 2 - oy),
                          (cx - ox, by1 + 20 - oy)], fill=(255, 255, 255, bia))
            draw.text((bx0 + 36 - bbox[0] - ox, by0 + 20 - bbox[1] - oy), label, font=f,
                      fill=(17, 24, 39, bia))
    elif animation == "card_glass":
        # Frosted dark card, left-center, cyan border, white text.
        import cv2
        a = int(255 * ease)
        if a > 1:
            f = font("Inter-SemiBold.ttf", 54)
            bbox = f.getbbox(label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x0, y0 = 120, h // 2 - 95
            x1, y1 = min(w - 120, x0 + tw + 140), y0 + th + 96
            roi = frame[y0:y1, x0:x1]
            if roi.size > 0:
                blurred = cv2.GaussianBlur(roi, (31, 31), 0)
                tint = np.full_like(roi, (12, 22, 30))
                frame[y0:y1, x0:x1] = cv2.addWeighted(blurred, 0.45, tint, 0.55, 0)
            overlay_origin = ensure_overlay((x0 - 20, y0 - 20, x1 + 20, y1 + 20))
            ox, oy = overlay_origin[:2]
            draw.rounded_rectangle((x0 - ox, y0 - oy, x1 - ox, y1 - oy), radius=20,
                                   outline=(102, 209, 255, a), width=3)
            draw.line((x0 + 34 - ox, y0 + th + 78 - oy, x0 + 134 - ox, y0 + th + 78 - oy),
                      fill=(102, 209, 255, a), width=4)
            draw.text((x0 + 60 - bbox[0] - ox, y0 + 34 - bbox[1] - oy), label, font=f,
                      fill=(255, 255, 255, a))
            draw.ellipse((cx - 7 - ox, cy - 7 - oy, cx + 7 - ox, cy + 7 - oy),
                         fill=(255, 255, 255, a))
    elif animation == "bare_big":
        # Naked display type, no rectangle, no stroke, soft offset shadow.
        a = int(255 * ease)
        if a > 1:
            f = font("Inter-Light.ttf", 120)
            bbox = f.getbbox(label)
            tw = bbox[2] - bbox[0]
            x = max(20, min(w - tw - 20, w // 2 - tw // 2))
            y = int(h * 0.40)
            overlay_origin = ensure_overlay((min(x - 8, cx - 8), y - 8,
                                             max(x + tw + 8, cx + 8), int(h * 0.40) + 128))
            ox, oy = overlay_origin[:2]
            draw.text((x - bbox[0] + 5 - ox, y - bbox[1] + 7 - oy), label, font=f,
                      fill=(0, 0, 0, int(120 * ease)))
            draw.text((x - bbox[0] - ox, y - bbox[1] - oy), label, font=f,
                      fill=(255, 255, 255, a))
            draw.ellipse((cx - 6 - ox, cy - 6 - oy, cx + 6 - ox, cy + 6 - oy),
                         fill=(255, 255, 255, a))
    elif animation == "ribbon":
        # Full-width band wiping in from the left, centered bold text.
        a = int(255 * ease)
        if a > 1:
            f = font("Inter-Bold.ttf", 64)
            bbox = f.getbbox(label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            band_h, band_y = 170, 210
            cut = int(w * ease)
            overlay_origin = ensure_overlay((0, band_y - 4, max(1, cut), band_y + band_h + 4))
            ox, oy = overlay_origin[:2]
            local_cut = max(0, min(overlay.width, cut - ox))
            draw.rectangle((0, band_y - oy, local_cut, band_y + band_h - oy),
                           fill=(7, 16, 24, int(205 * ease)))
            draw.line((0, band_y - oy, local_cut, band_y - oy), fill=(102, 209, 255, a), width=4)
            draw.line((0, band_y + band_h - oy, local_cut, band_y + band_h - oy),
                      fill=(102, 209, 255, a), width=4)
            draw.text((w // 2 - tw // 2 - bbox[0] - ox,
                       band_y + (band_h - th) // 2 - bbox[1] - oy),
                      label, font=f, fill=(255, 255, 255, a))
            draw.ellipse((cx - 7 - ox, cy - 7 - oy, cx + 7 - ox, cy + 7 - oy),
                         fill=(255, 255, 255, a))
    elif animation == "dot_ring":
        # Ultra-minimal: small dot, thin pulsing ring, tiny text, nothing else.
        import math
        a = int(255 * ease)
        if a > 1:
            pulse = 0.5 + 0.5 * math.sin(t * math.tau * 1.5)
            r = int(14 + 12 * pulse)
            f = font("Inter-Medium.ttf", 28)
            bbox = f.getbbox(label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            overlay_origin = ensure_overlay((cx - r - 4, cy - r - 4,
                                             cx + 30 + tw + 5, cy + r + 4))
            ox, oy = overlay_origin[:2]
            draw.ellipse((cx - r - ox, cy - r - oy, cx + r - ox, cy + r - oy),
                         outline=(102, 209, 255, a), width=2)
            draw.ellipse((cx - 6 - ox, cy - 6 - oy, cx + 6 - ox, cy + 6 - oy),
                         fill=(255, 255, 255, a))
            draw.text((cx + 30 - bbox[0] - ox, cy - 44 - bbox[1] - oy), label, font=f,
                      fill=(255, 255, 255, a), stroke_width=2,
                      stroke_fill=(6, 20, 28, int(230 * ease)))
    elif animation == "outline_box":
        # Empty wireframe box with white corner ticks around the text.
        a = int(255 * ease)
        if a > 1:
            f = font("Inter-SemiBold.ttf", 56)
            bbox = f.getbbox(label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pad = 30
            x = max(20, min(w - tw - 20, cx - tw // 2))
            y = max(20, min(h - th - 20, cy + 76))
            x0, y0, x1, y1 = x - pad, y - pad + 6, x + tw + pad, y + th + pad + 6
            overlay_origin = ensure_overlay((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
            ox, oy = overlay_origin[:2]
            draw.rectangle((x0 - ox, y0 - oy, x1 - ox, y1 - oy),
                           outline=(102, 209, 255, a), width=2)
            L = 26
            for px, py, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                                   (x0, y1, 1, -1), (x1, y1, -1, -1)):
                draw.line((px - ox, py - oy, px + dx * L - ox, py - oy),
                          fill=(255, 255, 255, a), width=5)
                draw.line((px - ox, py - oy, px - ox, py + dy * L - oy),
                          fill=(255, 255, 255, a), width=5)
            draw.text((x - bbox[0] - ox, y - bbox[1] - oy), label, font=f,
                      fill=(255, 255, 255, a))
            draw.ellipse((cx - 6 - ox, cy - 6 - oy, cx + 6 - ox, cy + 6 - oy),
                         fill=(255, 255, 255, a))
    else:
        return
    composite()


def _draw_distinct_label_style(frame: np.ndarray, point: tuple[int, int],
                               label: str, alpha: float, ease: float,
                               animation: str) -> None:
    """Draw one of the distinct-geometry label styles (size/position/typeface).

    Unlike the ten calm fades (same 42px Inter below the beacon), each style
    here owns its geometry: title_top is a large top title, badge_side a
    pill right of the beacon, huge_center a display face high on the frame,
    small_above a small caption over the beacon, caption_card a top-left
    card, editorial_serif a large roman face below the beacon.
    """
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    h, w = frame.shape[:2]
    cx, cy = point
    a = int(255 * max(0.0, min(1.0, alpha)))
    if a <= 1:
        return
    overlay = None
    draw = None
    ox0 = oy0 = 0

    def font(name: str, size: int):
        return _label_font(str(BASE_DIR / "Chronon3d/assets/fonts" / name), size)

    def begin_roi(bounds: tuple[int, int, int, int]) -> None:
        nonlocal overlay, draw, ox0, oy0
        x0, y0, x1, y1 = bounds
        margin = 24
        ox0, oy0 = max(0, x0 - margin), max(0, y0 - margin)
        ox1, oy1 = min(w, x1 + margin), min(h, y1 + margin)
        overlay = Image.new("RGBA", (ox1 - ox0, oy1 - oy0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

    def composite() -> None:
        if overlay is not None:
            _blend_layer_at(frame, np.asarray(overlay), ox=ox0, oy=oy0)

    if animation == "title_top":
        f = font("Inter-Bold.ttf", 84)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(20, min(w - tw - 20, w // 2 - tw // 2))
        begin_roi((x - 5, 105, x + tw + 5, 110 + th + 8))
        draw.text((x - bbox[0] - ox0, 110 - bbox[1] - oy0), label, font=f,
                  fill=(255, 255, 255, a), stroke_width=3,
                  stroke_fill=(6, 20, 28, int(230 * alpha)))
    elif animation == "badge_side":
        f = font("Inter-SemiBold.ttf", 34)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        padx, pady = 24, 12
        x0, y0 = cx + 66, cy - th // 2 - pady - 10
        x1, y1 = x0 + tw + padx * 2, y0 + th + pady * 2
        begin_roi((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
        x0 -= ox0; x1 -= ox0; y0 -= oy0; y1 -= oy0
        draw.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) // 2,
                               fill=(7, 16, 24, int(225 * alpha)),
                               outline=(102, 209, 255, a), width=3)
        draw.text((x0 + padx - bbox[0], y0 + pady - bbox[1]), label, font=f,
                  fill=(255, 255, 255, a))
    elif animation == "huge_center":
        f = font("AbrilFatface-Regular.ttf", 150)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(20, min(w - tw - 20, w // 2 - tw // 2))
        y = int(h * 0.24)
        begin_roi((x - 8, y - 8, x + tw + 8, y + th + 10))
        draw.text((x - bbox[0] + 4 - ox0, y - bbox[1] + 6 - oy0), label, font=f,
                  fill=(0, 0, 0, int(110 * alpha)))
        draw.text((x - bbox[0] - ox0, y - bbox[1] - oy0), label, font=f,
                  fill=(250, 246, 235, a), stroke_width=2,
                  stroke_fill=(6, 20, 28, int(200 * alpha)))
    elif animation == "small_above":
        f = font("Inter-Medium.ttf", 30)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = max(20, min(w - tw - 20, cx - tw // 2))
        y = max(20, cy - 122)
        begin_roi((x - 4, y - 4, x + tw + 4, y + th + 14))
        draw.text((x - bbox[0] - ox0, y - bbox[1] - oy0), label, font=f,
                  fill=(255, 255, 255, a), stroke_width=2,
                  stroke_fill=(6, 20, 28, int(230 * alpha)))
        draw.line((x - ox0, y + th + 8 - oy0, x + tw - ox0, y + th + 8 - oy0),
                  fill=(102, 209, 255, a), width=3)
    elif animation == "caption_card":
        f = font("Inter-SemiBold.ttf", 46)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x0, y0 = 60, 128
        x1, y1 = x0 + tw + 120, y0 + th + 56
        begin_roi((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
        x0 -= ox0; x1 -= ox0; y0 -= oy0; y1 -= oy0
        draw.rounded_rectangle((x0, y0, x1, y1), radius=18,
                               fill=(7, 16, 20, int(224 * alpha)))
        draw.rounded_rectangle((x0 + 20, y0 + 22, x0 + 28, y1 - 22), radius=4,
                               fill=(248, 245, 234, int(200 * alpha)))
        ty = y0 + (y1 - y0 - th) // 2
        draw.text((x0 + 52 - bbox[0], ty - bbox[1]), label, font=f,
                  fill=(255, 255, 255, a))
    elif animation == "editorial_serif":
        f = font("DM-Serif-Display.ttf", 76)
        bbox = f.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        slide = round(20 * (1.0 - ease))
        x = max(20, min(w - tw - 20, cx - tw // 2))
        y = max(20, min(h - th - 20, cy + 72 + slide))
        begin_roi((x - 6, y - 6, x + tw + 6, y + th + 6))
        draw.text((x - bbox[0] + 3 - ox0, y - bbox[1] + 4 - oy0), label, font=f,
                  fill=(0, 0, 0, int(140 * alpha)))
        draw.text((x - bbox[0] - ox0, y - bbox[1] - oy0), label, font=f,
                  fill=(250, 249, 238, a), stroke_width=2,
                  stroke_fill=(0, 14, 7, int(230 * alpha)))
    else:
        return
    composite()


def draw_map_marker_label(frame: np.ndarray, point: tuple[int, int], text: str,
                          progress: float, animation: str = "gentle_fade") -> None:
    """Draw the city name with the requested label treatment."""
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    label = " ".join(str(text or "").split())
    if not label or animation == "none":
        return
    if animation not in MAP_LABEL_ANIMATIONS:
        raise ValueError(f"unknown map label animation: {animation}")
    h, w = frame.shape[:2]
    cx, cy = point
    # Each treatment changes only the opacity/glow timing. The type remains
    # the same size and at the same screen coordinate for every frame.
    # The camera has settled at 62% and the marker has been visible since
    # 68%; delay every label treatment until 80% so it cannot race the zoom.
    timing = {
        "gentle_fade": (0.80, 0.16), "soft_glow": (0.80, 0.16),
        "clean_fade": (0.80, 0.16), "word_soft_fade": (0.80, 0.16),
        "slow_fade": (0.80, 0.16), "quiet_bloom": (0.80, 0.16),
        "quick_fade": (0.80, 0.16), "silky_fade": (0.80, 0.16),
        "subtle_halo": (0.80, 0.16), "cinematic_fade": (0.80, 0.16),
        "diffuse_city_beacon": (0.80, 0.13),
        "rise_up": (0.76, 0.18), "pop_in": (0.82, 0.10),
        "soft_tracking": (0.72, 0.22),
        "title_top": (0.70, 0.22), "badge_side": (0.78, 0.16),
        "huge_center": (0.66, 0.28), "small_above": (0.80, 0.14),
        "caption_card": (0.74, 0.20), "editorial_serif": (0.72, 0.22),
        # Show the location pin and its text while the slow camera is still
        # approaching. Waiting until 60% meant the marker only appeared after
        # the camera had already settled on short map clips.
        "gpin_bubble": (0.12, 0.36), "card_glass": (0.70, 0.20),
        "glow_react": (0.0, 0.18),
        "editorial_tag": (0.08, 0.24),
        "bare_big": (0.72, 0.22), "ribbon": (0.68, 0.20),
        "dot_ring": (0.76, 0.16), "outline_box": (0.74, 0.20),
    }
    start, duration = timing[animation]
    t = max(0.0, min(1.0, (progress - start) / duration))
    ease = t * t * (3.0 - 2.0 * t)
    alpha = ease
    if not label or alpha <= 0.005:
        return
    if animation in COMPOSITION_STYLES:
        _draw_composition(frame, point, label, t, ease, animation)
        return
    if animation == "editorial_tag":
        # Yemen/Saudi/Iran editorial callout: tracked condensed uppercase,
        # dark plate, red accent bar, fine leader and a restrained target.
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        font_path = BASE_DIR / "Chronon3d/assets/fonts/Oswald-Bold.ttf"
        if not font_path.is_file():
            font_path = BASE_DIR / "Chronon3d/assets/fonts/Inter-Bold.ttf"
        font = ImageFont.truetype(str(font_path), max(24, round(34 * h / 1080)))
        title = label.upper()
        spacing = max(1, round(2 * w / 1920))
        dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bounds = [dummy.textbbox((0, 0), ch, font=font) for ch in title]
        widths = [b[2] - b[0] for b in bounds]
        text_w = sum(widths) + spacing * max(0, len(title) - 1)
        text_h = font.getbbox(title)[3] - font.getbbox(title)[1]
        pad_x, pad_y = max(16, round(20 * w / 1920)), max(7, round(9 * h / 1080))
        box_w, box_h = text_w + 2 * pad_x + 5, text_h + 2 * pad_y
        box_x = max(18, min(w - box_w - 18, cx - box_w // 2))
        box_y = cy + max(48, round(56 * h / 1080))
        if box_y + box_h > h - 18:
            box_y = max(18, cy - max(48, round(56 * h / 1080)) - box_h)
        x0, x1 = max(0, box_x - 36), min(w, box_x + box_w + 36)
        y0, y1 = max(0, min(cy, box_y) - 32), min(h, max(cy + 12, box_y + box_h) + 32)
        base = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)).convert("RGBA")
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        bx0, by0, bx1, by1 = box_x - x0, box_y - y0, box_x - x0 + box_w, box_y - y0 + box_h
        ax, ay = cx - x0, cy - y0
        edge_y = by0 if by0 > ay else by1
        draw.line((ax, ay, ax, edge_y),
                  fill=(245, 247, 250, int(245 * alpha)), width=2)
        shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((bx0, by0 + 7, bx1, by1 + 7),
            radius=4, fill=(0, 0, 0, int(145 * alpha)))
        layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=4,
            fill=(10, 16, 22, int(242 * alpha)),
            outline=(221, 230, 232, int(100 * alpha)), width=1)
        draw.rectangle((bx0 + 1, by0 + 4, bx0 + 5, by1 - 4),
                       fill=(242, 48, 38, int(255 * alpha)))
        tx = bx0 + pad_x + 5
        ty = by0 + pad_y - font.getbbox(title)[1]
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        gx = tx
        for ch, cw in zip(title, widths):
            glow_draw.text((gx, ty), ch, font=font,
                fill=(220, 238, 255, int(105 * alpha)))
            gx += cw + spacing
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(5)))
        draw = ImageDraw.Draw(layer)
        for ch, cw, cb in zip(title, widths, bounds):
            draw.text((tx, ty), ch, font=font,
                fill=(242, 244, 238, int(255 * alpha)), stroke_width=1,
                stroke_fill=(3, 8, 12, int(210 * alpha)))
            tx += cw + spacing
        base.alpha_composite(layer)
        frame[y0:y1, x0:x1] = cv2.cvtColor(np.asarray(base.convert("RGB")), cv2.COLOR_RGB2BGR)
        return
    if animation == "glow_react":
        scale, thickness = 1.12, 2
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                             scale, thickness)
        x = max(28, min(w - tw - 28, cx - tw // 2))
        base_y = max(th + baseline + 12, cy - 86)
        tx0, tx1 = max(0, x - 8), min(w, x + tw + 8)
        ty0, ty1 = max(0, base_y - th - baseline - 6), min(h, base_y + 6)
        text_roi = frame[ty0:ty1, tx0:tx1]
        text_layer = text_roi.copy()
        local_origin = (x - tx0, base_y - ty0)
        cv2.putText(text_layer, label, (local_origin[0] + 2, local_origin[1] + 3),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2,
                    cv2.LINE_AA)
        cv2.putText(text_layer, label, local_origin, cv2.FONT_HERSHEY_SIMPLEX,
                    scale, (255, 255, 255), thickness, cv2.LINE_AA)
        cv2.addWeighted(text_roi, 1.0 - alpha, text_layer, alpha, 0, dst=text_roi)
        return
    if animation in NEW_LABEL_GEOMETRIES:
        _draw_distinct_label_style(frame, point, label, alpha, ease, animation)
        return
    if animation == "diffuse_city_beacon":
        font_path = BASE_DIR / "Chronon3d/assets/fonts/DM-Serif-Display-Italic.ttf"
        font = _label_font(str(font_path), max(24, round(min(h, w) * 0.052)))
        bbox = font.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = max(20, min(w - tw - 20, cx - tw // 2))
        text_y = max(20, min(h - th - 20, cy + max(52, round(h * 0.065))))
        margin = 8
        x0, y0 = max(0, text_x - margin), max(0, text_y - margin)
        x1, y1 = min(w, text_x + tw + margin), min(h, text_y + th + margin)
        overlay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.text((text_x - bbox[0] - x0, text_y - bbox[1] - y0), label, font=font,
                  fill=(250, 249, 238, int(255 * alpha)),
                  stroke_width=max(1, round(min(h, w) / 540)),
                  stroke_fill=(0, 14, 7, int(230 * alpha)))
        _blend_layer_at(frame, np.asarray(overlay), ox=x0, oy=y0)
        return
    # 01_ed_saudi_base capsule style for marker label:
    label_upper = label.upper()
    font_path = BASE_DIR / "Chronon3d/assets/fonts/Oswald-Bold.ttf"
    if not font_path.is_file():
        font_path = BASE_DIR / "Chronon3d/assets/fonts/Inter-Bold.ttf"
    font_size = max(24, round(32.0 * min(w, h) / 1080))
    font = _label_font(str(font_path), font_size)

    pad_x = max(14, round(18.0 * w / 1920))
    pad_y = max(6, round(8.0 * h / 1080))
    letter_spacing = max(1, round(2.0 * w / 1920))

    # Measure tracked label width
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)
    tracked_w = 0
    char_boxes = []
    for ch in label_upper:
        cb = dummy_draw.textbbox((0, 0), ch, font=font, stroke_width=1)
        char_boxes.append((cb[2] - cb[0], cb))
        tracked_w += (cb[2] - cb[0]) + letter_spacing
    if tracked_w > 0:
        tracked_w -= letter_spacing

    bbox = font.getbbox(label_upper)
    th = bbox[3] - bbox[1]
    box_w = tracked_w + 2 * pad_x
    box_h = th + 2 * pad_y

    # Position centered below the marker pin
    box_x0 = max(20, min(w - box_w - 20, cx - box_w // 2))
    base_y0 = cy + 56
    if animation == "rise_up":
        base_y0 += round(20 * (1.0 - ease))
    elif animation == "pop_in":
        overshoot = 1.0 + 0.35 * math.sin(min(1.0, t * 1.2) * math.pi)
        alpha = max(0.0, min(1.0, ease * overshoot))

    y_lift = int(round((1.0 - ease) * 8))
    box_y0_eff = max(20, min(h - box_h - 20, base_y0 + y_lift))
    box_y1_eff = box_y0_eff + box_h
    box_x1 = box_x0 + box_w

    # Allocate a clipped local canvas around the leader, capsule and shadow.
    roi_margin = 24
    rx0 = max(0, min(cx, box_x0) - roi_margin)
    ry0 = max(0, min(cy + 10, box_y0_eff) - roi_margin)
    rx1 = min(w, max(cx + 1, box_x1) + roi_margin)
    ry1 = min(h, max(cy + 10, box_y1_eff + 10) + roi_margin)
    overlay = Image.new("RGBA", (rx1 - rx0, ry1 - ry0), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    if box_y0_eff > cy + 10:
        draw_ov.line(
            (cx - rx0, cy + 10 - ry0, cx - rx0, box_y0_eff - ry0),
            fill=(221, 230, 232, int(160 * alpha)),
            width=1,
        )

    # 1. Soft blurred drop shadow
    shadow = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (box_x0 - rx0, box_y0_eff + 4 - ry0,
         box_x1 - rx0, box_y1_eff + 4 - ry0),
        radius=4,
        fill=(0, 0, 0, int(130 * alpha)),
    )
    overlay.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))

    # 2. Translucent dark rounded box + 1px subtle keyline
    draw_ov = ImageDraw.Draw(overlay)
    draw_ov.rounded_rectangle(
        (box_x0 - rx0, box_y0_eff - ry0,
         box_x1 - rx0, box_y1_eff - ry0),
        radius=4,
        fill=(10, 16, 22, int(242 * alpha)),
        outline=(221, 230, 232, int(100 * alpha)),
        width=1,
    )

    # 3. Tracked uppercase bold text
    tx = box_x0 + pad_x - rx0
    ty = box_y0_eff + pad_y - bbox[1] - ry0
    ink = (242, 244, 238, int(255 * alpha))
    stroke_ink = (3, 8, 12, int(210 * alpha))
    for ch, (cw, cb) in zip(label_upper, char_boxes):
        draw_ov.text(
            (tx, ty), ch, font=font, fill=ink,
            stroke_width=1, stroke_fill=stroke_ink,
        )
        tx += cw + letter_spacing

    _blend_layer_at(frame, np.asarray(overlay), ox=rx0, oy=ry0)


def draw_route_glow(frame: np.ndarray, frm: tuple[float, float], to: tuple[float, float],
                    anchor: tuple[float, float], zoom: float, reveal: float) -> None:
    """Glow sprites walking the straight mercator line from frm to to."""
    if reveal <= 0.01:
        return
    sprites = 26
    front = reveal * (sprites + 4)
    overlay = np.zeros_like(frame)
    for i in range(sprites):
        if i > front:
            break
        t = i / (sprites - 1)
        lat = frm[0] + (to[0] - frm[0]) * t
        lon = frm[1] + (to[1] - frm[1]) * t
        sx, sy = geo_to_screen(lat, lon, anchor, zoom)
        if not (0 <= sx < WIDTH and 0 <= sy < HEIGHT):
            continue
        head = max(0.0, 1.0 - abs(front - i) * 0.35)
        strength = 0.55 + 0.45 * head
        for r, a in ((18, 0.20 * strength), (10, 0.45 * strength), (4, 0.95 * strength)):
            overlay = cv2.circle(overlay, (sx, sy), r,
                                 (int(60 * a), int(240 * a), int(255 * a)), -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 1.0, frame, 1.0, 0, dst=frame)


# ----------------------------------------------------------------------------
# Shots. Each returns per-frame (anchor_lat, anchor_lon, zoom, pitch, yaw, roll)
# plus its own overlay pass. All curves are smootherstep: C2, no snap.
# ----------------------------------------------------------------------------
def pure_dive_motion(anchor, z0, z1, frames):
    def at(f):
        e = smootherstep(f / max(1, frames - 1))
        return anchor[0], anchor[1], z0 + (z1 - z0) * e, 0.0, 0.0, 0.0
    return at


def dive_tilt_motion(anchor, z0, z1, dive_end, tilt_end, tilt_deg, frames):
    def at(f):
        if f <= dive_end:
            e = smootherstep(f / max(1, dive_end))
            return anchor[0], anchor[1], z0 + (z1 - z0) * e, 0.0, 0.0, 0.0
        p = (f - dive_end) / max(1, tilt_end - dive_end)
        e = smootherstep(p)
        return (anchor[0], anchor[1], z1, tilt_deg * e, 0.0, roll_bank(p))
    return at


def medley_motion(frames, a_end, b_end):
    """dive 5.2->14 (space to lagoon scale) | route hold | dive 14->18 while
    panning the anchor from the route midpoint into Lughetto itself."""
    def at(f):
        if f < a_end:
            e = smootherstep(f / max(1, a_end))
            return MID[0], MID[1], 5.2 + (14.0 - 5.2) * e, 0.0, 0.0, 0.0
        if f < b_end:
            return MID[0], MID[1], 14.0, 0.0, 0.0, 0.0
        p = smootherstep((f - b_end) / max(1, frames - 1 - b_end))
        lat = MID[0] + (LUG[0] - MID[0]) * p
        lon = MID[1] + (LUG[1] - MID[1]) * p
        return lat, lon, 14.0 + (18.0 - 14.0) * p, 0.0, 0.0, 0.0
    return at


def medley_overlay(frame, f, p, anchor, zoom):
    frames, a_end, b_end = 180, 84, 120
    if f < b_end:
        draw_route_glow(frame, CLP, LUG, anchor, zoom,
                        (f - a_end) / max(1, b_end - 4 - a_end))
    else:
        draw_route_glow(frame, CLP, LUG, anchor, zoom, 1.0)
    lug_xy = geo_to_screen(LUG[0], LUG[1], anchor, zoom)
    if f >= b_end:
        draw_spring_pin(frame, lug_xy, f / (frames - 1), fire=150 / 179.0, span=0.10)
    if f >= 160:
        a = min(1.0, (f - 160) / 14.0)
        glass_card(frame, [
            ("LUGHETTO - FRAZIONE DI CAMPAGNA LUPIA", 34, 0.52, CYAN, 1),
            ("422 ANIME - CITTA' METROPOLITANA DI VENEZIA", 64, 0.60, (255, 255, 255), 2),
            ("WGS84 45.38271 N  12.12881 E - VENETO, ITALIA", 92, 0.44, (180, 200, 220), 1),
        ], a)


def shots() -> list[dict]:
    bands_lug = ((5.2, 8.0, "EUROPE"), (8.0, 11.0, "ITALIA"),
                 (11.0, 13.5, "VENETO"), (13.5, 16.0, "CAMPAGNA LUPIA"),
                 (16.0, 99.0, "LUGHETTO"))
    bands_clp = ((5.2, 8.0, "EUROPE"), (8.0, 11.0, "ITALIA"),
                 (11.0, 14.0, "VENETO"), (14.0, 99.0, "CAMPAGNA LUPIA"))
    bands_vce = ((5.2, 8.0, "EUROPE"), (8.0, 11.0, "ITALIA"),
                 (11.0, 14.0, "VENETO"), (14.0, 99.0, "VENEZIA"))
    bands_med = ((5.2, 8.0, "EUROPE"), (8.0, 11.0, "ITALIA"),
                 (11.0, 13.0, "VENETO"), (13.0, 14.6, "LAGUNA SUD"),
                 (14.6, 15.6, "CAMPAGNA LUPIA  ->  LUGHETTO"),
                 (15.6, 99.0, "LUGHETTO"))
    return [
        dict(name="lughetto_pure_dive", motion=pure_dive_motion(LUG, 5.2, 18.0, 120),
             bands=bands_lug, frames=120,
             overlay=lambda fr, f, p, a, z: (
                 draw_spring_pin(fr, (WIDTH // 2, HEIGHT // 2), p, fire=0.80, span=0.12),
                 glass_card(fr, [
                     ("LUGHETTO - FRAZIONE DI CAMPAGNA LUPIA", 34, 0.52, CYAN, 1),
                     ("422 ANIME - 8192x DIVE FROM ORBIT", 64, 0.60, (255, 255, 255), 2),
                     ("WGS84 45.38271 N  12.12881 E", 92, 0.44, (180, 200, 220), 1),
                 ], min(1.0, max(0.0, (p - 0.86) / 0.10))))),
        dict(name="campagna_lupia_dive", motion=pure_dive_motion(CLP, 5.2, 17.8, 120),
             bands=bands_clp, frames=120,
             overlay=lambda fr, f, p, a, z: glass_card(fr, [
                 ("CAMPAGNA LUPIA", 34, 0.60, (255, 255, 255), 2),
                 ("COMUNE - CITTA' METROPOLITANA DI VENEZIA - VENETO", 64, 0.48, CYAN, 1),
                 ("WGS84 45.35430 N  12.09640 E", 92, 0.44, (180, 200, 220), 1),
             ], min(1.0, max(0.0, (p - 0.84) / 0.12)))),
        dict(name="venezia_dive_then_tilt", motion=dive_tilt_motion(VCE, 5.2, 17.3, 93, 120, 35.0, 150),
             bands=bands_vce, frames=150,
             overlay=lambda fr, f, p, a, z: glass_card(fr, [
                 ("VENEZIA - SAN MARCO", 34, 0.58, (255, 255, 255), 2),
                 ("THE 35-DEGREE HORIZON - GEO CAMERA V1", 64, 0.48, CYAN, 1),
                 ("WGS84 45.44080 N  12.31550 E", 92, 0.44, (180, 200, 220), 1),
             ], min(1.0, max(0.0, (p - 0.84) / 0.12)))),
        dict(name="lagoon_medley_route_and_chase", motion=medley_motion(180, 84, 120),
             bands=bands_med, frames=180, overlay=medley_overlay),
    ]


def render_shot_frame(shot: dict, f: int) -> np.ndarray:
    lat, lon, zoom, pitch, yaw, roll = shot["motion"](f)
    progress = f / (shot["frames"] - 1)
    if pitch < 0.5:
        frame = PYRAMID.sample_continuous(lat, lon, zoom, WIDTH, HEIGHT)
    else:
        ow, oh = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
        plate = PYRAMID.sample_continuous(lat, lon, zoom, ow, oh)
        H = warp_matrix(pitch, yaw, roll)
        frame = cv2.warpPerspective(plate, H, (WIDTH, HEIGHT),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT_101)
    shot["overlay"](frame, f, progress, (lat, lon), zoom)
    draw_hud_overlay(frame, lat, lon, zoom, progress,
                     target_title=shot["name"].upper().replace("_", " "))
    draw_chain(frame, zoom, shot["bands"])
    return frame


def gate(shot: dict) -> bool:
    """Strict velocity continuity per dive segment + byte determinism.

    Segments are maximal runs where the zoom actually moves; a hold phase
    (constant zoom: the tilt window of a shaped shot) is never mixed into a
    moving segment, or it would deflate the mean step and fake a pass.
    """
    frames = shot["frames"]
    zooms = [shot["motion"](f)[2] for f in range(frames)]
    segments = []
    f = 0
    while f < frames - 1:
        if zooms[f] != zooms[f + 1]:
            s0 = f
            while f < frames - 1 and zooms[f] != zooms[f + 1]:
                f += 1
            segments.append((s0, f))
        else:
            f += 1
    ok_v = bool(segments)
    for s0, s1 in segments:
        mean_step = abs(zooms[s1] - zooms[s0]) / (s1 - s0)
        max_step = max(abs(zooms[f] - zooms[f - 1]) for f in range(s0 + 1, s1 + 1))
        ok = max_step <= 1.8751 * mean_step + 1e-6
        ok_v &= ok
        print(f"    dive {s0}..{s1}: max step {max_step:.4f} "
              f"<= 1.8751 x {mean_step:.4f} -> {'PASS' if ok else 'FAIL'}", flush=True)
    a = render_shot_frame(shot, 30)
    b = render_shot_frame(shot, 30)
    ok_d = a.tobytes() == b.tobytes()
    print(f"    determinism: {'PASS' if ok_d else 'FAIL'}", flush=True)
    return ok_v and ok_d


def render_and_upload(shot: dict, token: str) -> str:
    out = OUT_DIR / f"geo_camera_v1_small_places_{shot['name']}.mp4"
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
           "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for f in range(shot["frames"]):
        proc.stdin.write(render_shot_frame(shot, f).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"  rendered in {time.time() - t0:.1f}s ({out.stat().st_size:,} bytes)", flush=True)
    res = upload_to_drive(out, token, DRIVE_FOLDER_ID)
    return f"https://drive.google.com/file/d/{res.get('id')}/view?usp=drivesdk"


def main() -> None:
    global PYRAMID
    print("=== geo_camera_v1 small places: Lughetto, Campagna Lupia, Venezia ===", flush=True)
    # A three-anchor pyramid: the widest union window covers the ~3 km that
    # separates the two villages plus Venice to the east.
    PYRAMID = DynamicTilePyramid(provider="esri_sat")
    print("Step 1: prefetching pyramids for all three anchors...", flush=True)
    for lat, lon in (LUG, CLP, VCE):
        PYRAMID.prefetch_pyramid(lat, lon, min_zoom=5, max_zoom=16,
                                 tile_radius_x=9, tile_radius_y=9)
        PYRAMID.prefetch_pyramid(lat, lon, min_zoom=17, max_zoom=18,
                                 tile_radius_x=9, tile_radius_y=9)

    token = refresh_drive_token()
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    links = []
    for shot in shots():
        if only and shot["name"] not in only:
            continue
        print(f"\n--- {shot['name']} ({shot['frames']} frames) ---", flush=True)
        if not gate(shot):
            print("  GATE FAILED - shot skipped", flush=True)
            continue
        links.append((shot["name"], render_and_upload(shot, token)))

    print("\n=== small places: all renders ===", flush=True)
    for name, link in links:
        print(f"  {name}: {link}", flush=True)


if __name__ == "__main__":
    main()
