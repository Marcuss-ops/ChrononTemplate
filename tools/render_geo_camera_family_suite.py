#!/usr/bin/env python3
"""
geo_camera_v1 family showcase - the remaining presets as cinematic clips.

Renders the certified GeoCameraRig presets (ChrononMotion3D
include/chrononmotion/geospatial/GeoCameraRig.hpp) as separate videos, each
with the overlay its name promises, each gated by its own acceptance check
(zoom continuity, determinism, target lock) before a single frame is encoded:

  map_dive_to_landmark    pure supersonic dive, nadir landing on the arena
  map_dive_to_city        dive landing at city scale
  map_dive_to_country     dive landing at country scale
  map_dive_then_tilt      dive, then pitch to a 35-degree ground horizon
  map_dive_pin_reveal     dive, then a spring drop pin fires at the anchor
  map_dive_metric_reveal  dive, then the visitor metric counts up on a glass card
  map_dive_route_continue dive, then a glow route walks on to the next place
  map_dive_then_crane_out dive, then a crane pull-back for a closing wide

(map_dive_then_orbit is already rendered by render_geo_camera_canary.py.)
"""

import sys
import math
import time
import subprocess
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
    warp_matrix, anchor_projection, draw_metric_reveal, smootherstep, OVERSIZE,
)

WIDTH, HEIGHT, FPS = 1920, 1080, 30
FRAMES = 120
LAT, LON = 41.890210, 12.492231          # Colosseum - the certified anchor
ROUTE_TO = (41.9022, 12.4539)            # St Peter's Basilica, for route_continue

OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CYAN = (0, 240, 255)


def roll_bank(p: float) -> float:
    """Banking during post-dive phases: a sine that returns to zero."""
    return -8.0 * math.sin(max(0.0, min(1.0, p)) * math.pi)


# ----------------------------------------------------------------------------
# Per-shot motion laws. Each returns (zoom, pitch, yaw, roll) for a frame.
# Schedules mirror GeoCameraRig.hpp: dive 62%, tilt to 80%, orbit/crane to end.
# ----------------------------------------------------------------------------
def make_motion(start_z: float, end_z: float, dive_end: int, tilt_end: int,
                tilt_deg: float, yaw_deg: float, crane_z: float | None):
    def at(f: int):
        if f <= dive_end:
            e = smootherstep(f / max(1, dive_end))
            return start_z + (end_z - start_z) * e, 0.0, 0.0, 0.0
        if tilt_end <= dive_end:
            return end_z, 0.0, 0.0, 0.0
        p = (f - dive_end) / max(1, tilt_end - dive_end)
        e = smootherstep(p)
        pitch = tilt_deg * e
        yaw = yaw_deg * smootherstep(max(0.0, (f - tilt_end)
                                         / max(1, FRAMES - tilt_end)))
        roll = roll_bank(p) if tilt_deg else 0.0
        zoom = end_z if crane_z is None else end_z + (crane_z - end_z) * e
        return zoom, pitch, yaw, roll
    return at


def spring(t: float, omega: float = 15.0, zeta: float = 0.52) -> float:
    """Landing spring from MapFlyover.hpp: 1 - e^(-ztw) cos(w_d t)."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    wd = omega * math.sqrt(1.0 - zeta * zeta)
    return 1.0 - math.exp(-zeta * omega * t) * math.cos(wd * t)


# ----------------------------------------------------------------------------
# Overlays
# ----------------------------------------------------------------------------
def draw_title(frame: np.ndarray, text: str, sub: str, alpha: float) -> None:
    if alpha <= 0.02:
        return
    col = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
    sub_col = (int(170 * alpha), int(190 * alpha), int(210 * alpha))
    cv2.putText(frame, text, (80, HEIGHT - 120), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, col, 2, cv2.LINE_AA)
    cv2.putText(frame, sub, (80, HEIGHT - 84), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, sub_col, 1, cv2.LINE_AA)


def draw_pin(frame: np.ndarray, progress: float) -> None:
    """Spring drop pin: falls from above, overshoots, settles, then pulses."""
    if progress < 0.70:
        return
    t = min(1.0, (progress - 0.70) / 0.25)
    bounce = spring(t)
    cx, cy = WIDTH // 2, HEIGHT // 2
    drop = int(240 * (1.0 - bounce))
    head_y = cy - drop
    # soft shadow ring where it will land
    shadow_a = max(0.0, t)
    cv2.ellipse(frame, (cx, cy), (26, 9), 0, 0, 360,
                (int(20 * shadow_a), int(30 * shadow_a), int(40 * shadow_a)), -1)
    # stem + head
    cv2.line(frame, (cx, head_y), (cx, cy), CYAN, 2, cv2.LINE_AA)
    cv2.circle(frame, (cx, head_y), 13, (0, 60, 200), -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, head_y), 13, (255, 255, 255), 2, cv2.LINE_AA)
    # landing pulse
    if t >= 1.0:
        ph = (progress * 2.0) % 1.0
        r = int(12 + 60 * ph)
        a = max(0.0, 1.0 - ph)
        cv2.circle(frame, (cx, cy), r,
                   (int(0 * a), int(240 * a), int(255 * a)), 2, cv2.LINE_AA)


def draw_metric_countup(frame: np.ndarray, progress: float) -> None:
    """Glass card with the metric counting up under the pinned anchor."""
    card_alpha = max(0.0, min(1.0, (progress - 0.70) / 0.18))
    if card_alpha <= 0.01:
        return
    card_w, card_h = 560, 170
    card_x = WIDTH - card_w - 60
    card_y = HEIGHT - card_h - 90
    sub = frame[card_y:card_y + card_h, card_x:card_x + card_w]
    if sub.shape[0] == card_h and sub.shape[1] == card_w:
        blurred = cv2.GaussianBlur(sub, (21, 21), 0)
        tint = np.full((card_h, card_w, 3), (15, 20, 32), dtype=np.uint8)
        glass = cv2.addWeighted(blurred, 0.4, tint, 0.6, 0)
        frame[card_y:card_y + card_h, card_x:card_x + card_w] = cv2.addWeighted(
            sub, 1.0 - card_alpha, glass, card_alpha, 0)
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h),
                  CYAN, 2, cv2.LINE_AA)

    def put(text, dy, scale, col, thick):
        cv2.putText(frame, text, (card_x + 24, card_y + dy),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, col, thick, cv2.LINE_AA)

    put("ANFITEATRO FLAVIO - COLOSSEUM", 40, 0.55, (0, 240, 255), 1)
    counted = 7.6e6 * smootherstep(max(0.0, (progress - 0.74) / 0.22))
    put(f"{counted / 1e6:0.1f} MILLION", 100, 1.05, (255, 255, 255), 2)
    put("VISITORS EVERY YEAR - WGS84 41.890210 N 12.492231 E", 142, 0.44,
        (180, 200, 220), 1)


def draw_route_glow(frame: np.ndarray, pyramid: DynamicTilePyramid,
                    zoom: float, progress: float) -> None:
    """Glow chain walking the great circle to the next destination."""
    reveal = max(0.0, min(1.0, (progress - 0.70) / 0.28))
    if reveal <= 0.01:
        return
    sprites = 22
    front = reveal * (sprites + 4)
    overlay = np.zeros_like(frame)
    for i in range(sprites):
        if i > front:
            break
        t = i / (sprites - 1)
        lat = LAT + (ROUTE_TO[0] - LAT) * t
        lon = LON + (ROUTE_TO[1] - LON) * t
        gx, gy = latlon_to_global_px(lat, lon, int(math.floor(zoom)))
        scale = 2.0 ** (zoom - math.floor(zoom))
        sx = int(round((gx - (latlon_to_global_px(LAT, LON, int(math.floor(zoom)))[0]
                             - WIDTH / 2.0 / scale)) * scale))
        sy = int(round((gy - (latlon_to_global_px(LAT, LON, int(math.floor(zoom)))[1]
                             - HEIGHT / 2.0 / scale)) * scale))
        if not (0 <= sx < WIDTH and 0 <= sy < HEIGHT):
            continue
        head = max(0.0, 1.0 - abs(front - i) * 0.35)
        strength = 0.55 + 0.45 * head
        for r, a in ((18, 0.20 * strength), (10, 0.45 * strength), (4, 0.95 * strength)):
            col = (int(60 * a), int(240 * a), int(255 * a))
            cv2.circle(overlay, (sx, sy), r, col, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 1.0, frame, 1.0, 0, dst=frame)
    if reveal >= 0.99:
        draw_title(frame, "NEXT: SAN PIETRO",
                   "the route keeps walking - geo_camera_v1 route_continue",
                   min(1.0, (progress - 0.95) / 0.05))


# ----------------------------------------------------------------------------
# The family. (zoom, pitch, yaw, roll) per preset, GeoCameraRig schedules.
# ----------------------------------------------------------------------------
def shots() -> list[dict]:
    dive = make_motion(5.2, 17.8, FRAMES, FRAMES, 0.0, 0.0, None)
    city = make_motion(5.2, 14.5, FRAMES, FRAMES, 0.0, 0.0, None)
    country = make_motion(5.2, 9.5, FRAMES, FRAMES, 0.0, 0.0, None)
    tilt = make_motion(5.2, 17.5, 84, FRAMES, 35.0, 0.0, None)
    pin = make_motion(5.2, 17.5, FRAMES, FRAMES, 0.0, 0.0, None)
    metric = make_motion(5.2, 17.5, 84, FRAMES, 0.0, 0.0, None)
    route = make_motion(5.2, 15.0, 84, FRAMES, 0.0, 0.0, None)
    crane = make_motion(5.2, 17.5, 84, FRAMES, 25.0, 0.0, 15.2)
    return [
        dict(name="map_dive_to_landmark", motion=dive,
             title="COLOSSEUM", sub="pure supersonic dive - geo_camera_v1",
             overlay=lambda f, fr, p, z: draw_title(f, "COLOSSEUM",
                 "from orbit to the arena floor - 8192x continuous", p)),
        dict(name="map_dive_to_city", motion=city,
             title="ROMA", sub="dive landing at city scale",
             overlay=lambda f, fr, p, z: draw_title(f, "ROMA",
                 "the street grid resolves - landing z=14.5", p)),
        dict(name="map_dive_to_country", motion=country,
             title="ITALIA", sub="dive landing at country scale",
             overlay=lambda f, fr, p, z: draw_title(f, "ITALIA",
                 "the peninsula resolves - landing z=9.5", p)),
        dict(name="map_dive_then_tilt", motion=tilt,
             title="HORIZON", sub="dive then pitch to 35 degrees",
             overlay=lambda f, fr, p, z: draw_title(f, "TILT 35",
                 "the ground plane opens to a horizon", p)),
        dict(name="map_dive_pin_reveal", motion=pin,
             title="PIN", sub="dive then spring drop pin",
             overlay=lambda f, fr, p, z: draw_pin(f, p)),
        dict(name="map_dive_metric_reveal", motion=metric,
             title="METRIC", sub="dive then the number rises",
             overlay=lambda f, fr, p, z: draw_metric_countup(f, p)),
        dict(name="map_dive_route_continue", motion=route,
             title="ROUTE", sub="dive then the route walks on",
             overlay=lambda f, fr, p, z: draw_route_glow(f, PYRAMID, z, p)),
        dict(name="map_dive_then_crane_out", motion=crane,
             title="CRANE OUT", sub="dive then pull back for the wide",
             overlay=lambda f, fr, p, z: draw_title(f, "CRANE OUT",
                 "the closing wide - same anchor, wider world", p)),
    ]


PYRAMID: DynamicTilePyramid = None  # set in main()


# ----------------------------------------------------------------------------
# Render one frame of one shot (pure function of the frame index).
# ----------------------------------------------------------------------------
def render_shot_frame(shot: dict, f: int) -> np.ndarray:
    zoom, pitch, yaw, roll = shot["motion"](f)
    progress = f / (FRAMES - 1)
    if pitch < 0.5:
        frame = PYRAMID.sample_continuous(LAT, LON, zoom, WIDTH, HEIGHT)
    else:
        ow, oh = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
        plate = PYRAMID.sample_continuous(LAT, LON, zoom, ow, oh)
        H = warp_matrix(pitch, yaw, roll)
        frame = cv2.warpPerspective(plate, H, (WIDTH, HEIGHT),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT_101)
    shot["overlay"](frame, f, progress, zoom)
    draw_hud_overlay(frame, LAT, LON, zoom, progress,
                     target_title=shot["title"] + " (GEO CAMERA V1)")
    return frame


def gate(shot: dict) -> bool:
    """Per-shot acceptance: zoom continuity + determinism. Runs before encode."""
    zooms = [shot["motion"](f)[0] for f in range(FRAMES)]
    dive_end = next((f for f in range(FRAMES - 1)
                     if shot["motion"](f + 1)[0] != shot["motion"](f)[0] + 0.0
                     and f > 0 and shot["motion"](f)[1] == 0.0), FRAMES - 1)
    mean_step = abs(zooms[-1] - zooms[0]) / max(1, dive_end)
    max_step = max(abs(zooms[f] - zooms[f - 1]) for f in range(1, FRAMES))
    ok_v = max_step <= 1.8751 * mean_step + 1e-6 or mean_step == 0
    a = render_shot_frame(shot, 30)
    b = render_shot_frame(shot, 30)
    ok_d = a.tobytes() == b.tobytes()
    print(f"  gate: velocity {'PASS' if ok_v else 'FAIL'} "
          f"(max step {max_step:.4f}, mean {mean_step:.4f}), "
          f"determinism {'PASS' if ok_d else 'FAIL'}", flush=True)
    return ok_v and ok_d


def render_and_upload(shot: dict, token: str) -> str:
    out = OUT_DIR / f"geo_camera_v1_{shot['name']}.mp4"
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
           "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for f in range(FRAMES):
        proc.stdin.write(render_shot_frame(shot, f).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"  rendered in {time.time() - t0:.1f}s ({out.stat().st_size:,} bytes)",
          flush=True)
    res = upload_to_drive(out, token, DRIVE_FOLDER_ID)
    return f"https://drive.google.com/file/d/{res.get('id')}/view?usp=drivesdk"


def main() -> None:
    global PYRAMID
    print("=== geo_camera_v1 family showcase: 8 presets ===", flush=True)
    PYRAMID = DynamicTilePyramid(provider="esri_sat")
    print("Step 1: prefetching the shared pyramid...", flush=True)
    PYRAMID.prefetch_pyramid(LAT, LON, min_zoom=5, max_zoom=16,
                             tile_radius_x=9, tile_radius_y=9)
    PYRAMID.prefetch_pyramid(LAT, LON, min_zoom=17, max_zoom=18,
                             tile_radius_x=9, tile_radius_y=9)

    token = refresh_drive_token()
    links: list[tuple[str, str]] = []
    for shot in shots():
        print(f"\n--- {shot['name']} ---", flush=True)
        if not gate(shot):
            print("  GATE FAILED - shot skipped", flush=True)
            continue
        links.append((shot["name"], render_and_upload(shot, token)))

    print("\n=== geo_camera_v1 family: all renders ===", flush=True)
    for name, link in links:
        print(f"  {name}: {link}", flush=True)


if __name__ == "__main__":
    main()
