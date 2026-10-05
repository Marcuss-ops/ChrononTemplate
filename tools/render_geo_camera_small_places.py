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
    """Pulsing cyan ring and bright center point with an optional area halo."""
    import cv2
    import numpy as np
    cx, cy = point
    t = max(0.0, min(1.0, progress))
    pulse = 0.5 + 0.5 * math.sin(t * math.tau * 1.7)
    radius = 40 + int(6 * pulse)
    cyan = (213, 226, 82)
    # Keep the ring crisp while adding a soft halo in the same map accent.
    light = np.zeros_like(frame)
    cv2.circle(light, (cx, cy), radius, cyan, 4, cv2.LINE_AA)
    cv2.circle(light, (cx, cy), radius + 12, cyan, 2, cv2.LINE_AA)
    light = cv2.GaussianBlur(light, (0, 0), 16)
    cv2.addWeighted(frame, 1.0, light, 0.66, 0, dst=frame)
    cv2.circle(frame, (cx, cy), radius, cyan, 3, cv2.LINE_AA)
    if area_radius_px > 2:
        ring = np.zeros_like(frame)
        cv2.circle(ring, (cx, cy), area_radius_px, (180, 110, 30), 3, cv2.LINE_AA)
        cv2.circle(ring, (cx, cy), area_radius_px, (255, 150, 45), 3, cv2.LINE_AA)
        ring = cv2.GaussianBlur(ring, (0, 0), 10)
        cv2.addWeighted(frame, 1.0, ring, 0.22, 0, dst=frame)
        cv2.circle(frame, (cx, cy), area_radius_px, (255, 175, 70), 2, cv2.LINE_AA)
    # Bright center dot reads clearly against both the imagery and the ring.
    cv2.circle(frame, (cx, cy), 10, (8, 30, 36), -1, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 7, (248, 252, 250), -1, cv2.LINE_AA)


MAP_LABEL_ANIMATIONS = (
    "gentle_fade", "soft_glow", "clean_fade", "word_soft_fade",
    "slow_fade", "quiet_bloom", "quick_fade", "silky_fade",
    "subtle_halo", "cinematic_fade",
)


def draw_map_marker_label(frame: np.ndarray, point: tuple[int, int], text: str,
                          progress: float, animation: str = "gentle_fade") -> None:
    """Draw the city name directly below its animated beacon."""
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    label = " ".join(str(text or "").split())
    if not label or animation == "none":
        return
    if animation not in MAP_LABEL_ANIMATIONS:
        raise ValueError(f"unknown map label animation: {animation}")
    h, w = frame.shape[:2]
    cx, cy = point
    # Each treatment changes only the opacity/glow timing. The type remains
    # the same size and at the same screen coordinate for every frame.
    timing = {
        "gentle_fade": (0.50, 0.23), "soft_glow": (0.52, 0.18),
        "clean_fade": (0.49, 0.24), "word_soft_fade": (0.51, 0.26),
        "slow_fade": (0.50, 0.20), "quiet_bloom": (0.48, 0.22),
        "quick_fade": (0.53, 0.18), "silky_fade": (0.50, 0.25),
        "subtle_halo": (0.51, 0.22), "cinematic_fade": (0.49, 0.20),
    }
    start, duration = timing[animation]
    t = max(0.0, min(1.0, (progress - start) / duration))
    ease = t * t * (3.0 - 2.0 * t)
    alpha = ease
    if not label or alpha <= 0.005:
        return
    font_path = BASE_DIR / "Chronon3d/assets/fonts/Inter-SemiBold.ttf"
    font = ImageFont.truetype(str(font_path), 42)
    bbox = font.getbbox(label)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # Keep the name centered below the ring with a short connector to its point.
    text_x = max(20, min(w - tw - 20, cx - tw // 2))
    text_y = max(20, min(h - th - 20, cy + 68))
    connector = np.zeros_like(frame)
    connector_top = text_y - 6
    if connector_top > cy + 53:
        cv2.line(connector, (cx, cy + 53), (cx, connector_top), (213, 226, 82), 2, cv2.LINE_AA)
        cv2.addWeighted(frame, 1.0, connector, alpha * 0.8, 0, dst=frame)
    x0, y0 = max(0, text_x - 8), max(0, text_y - 8)
    x1, y1 = min(w, text_x + tw + 8), min(h, text_y + th + 8)
    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return
    label_image = Image.new("RGBA", (roi.shape[1], roi.shape[0]), (0, 0, 0, 0))
    draw = ImageDraw.Draw(label_image)
    local = (text_x - x0 - bbox[0], text_y - y0 - bbox[1])
    draw.text(local, label, font=font, fill=(255, 255, 255, 255),
              stroke_width=2, stroke_fill=(6, 20, 28, 240))
    alpha_mask = np.asarray(label_image)[:, :, 3]
    overlay = np.asarray(label_image)[:, :, :3][:, :, ::-1].copy()
    mask = (alpha_mask.astype(np.float32) / 255.0 * alpha)[:, :, None]
    roi[:] = np.clip(roi.astype(np.float32) * (1.0 - mask) + overlay * mask,
                     0, 255).astype(np.uint8)


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
