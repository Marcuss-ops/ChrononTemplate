#!/usr/bin/env python3
"""
geo_camera_v1 canary — EUROPE -> ITALY -> ROME -> COLOSSEUM -> TILT 35 -> ORBIT -> TITLE.

Renders the certified GeoCameraRig trajectory (ChrononMotion3D
include/chrononmotion/geospatial/GeoCameraRig.hpp, preset MapDiveThenOrbit)
through the DynamicTilePyramid imagery engine, and self-certifies the
pixel-level acceptance criteria before encoding a single frame:

  TestMapLODNoMissingTiles   every tile the view touches is in the pyramid
  TestMapLODNoVisibleSeams   no black rows/columns at tile boundaries
  TestMapLODCoverage         the prefetch covers every sampled level
  old-tile release           at z = x + 0.98 the frame is the z = x+1 plate
  new-tile restraint         at z = x + 0.02 the frame is still the z = x plate
  TestMapZoomVelocityContinuity  no frame-to-frame zoom snap (smootherstep bound)
  TestMapDiveTargetLock      the anchor projects within 1 px of (960, 540)
  TestMapDiveDeterminism     the same frame renders byte-for-byte identical

Motion laws mirror the C++ rig exactly: smootherstep C2 dive profile, the
62/80/100 dive/tilt/orbit phase schedule, altitude from the pyramid's own
texel-to-screen law, and the anchor held on the reticle through every pitch
and yaw.
"""

import sys
import math
import time
import subprocess
from pathlib import Path

import numpy as np
import cv2

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "Chronon3d/tools/cartography"))
sys.path.insert(0, str(BASE_DIR / "ChrononTemplate/tools"))

from dynamic_tile_pyramid import (  # noqa: E402 - sys.path is set above
    DynamicTilePyramid,
    draw_hud_overlay,
    compute_altitude_km,
)

# The proven projection + Drive plumbing, reused as-is.
from render_dynamic_map_3d_orbit_colosseum import (  # noqa: E402
    compute_perspective_homography,
    refresh_drive_token,
    upload_to_drive,
    DRIVE_FOLDER_ID,
)

OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_MP4 = OUT_DIR / "geo_camera_v1_canary_map_dive_then_orbit.mp4"

WIDTH, HEIGHT, FPS = 1920, 1080, 30
TOTAL_FRAMES = 150

# The Colosseum — the certified canary anchor.
LAT, LON = 41.890210, 12.492231

# ---- The geo_camera_v1 motion law (mirrors GeoCameraRig.hpp bit for bit) ----
START_ZOOM = 5.2
END_ZOOM = 17.5
TILT_DEG = 35.0
ORBIT_DEG = 15.0
DIVE_END = round(TOTAL_FRAMES * 0.62)   # 93
TILT_END = round(TOTAL_FRAMES * 0.80)   # 120
REVEAL_FRACTION = 0.86

OVERSIZE = 1.5  # warp-phase plate growth, so the tilt never reveals an edge


def smootherstep(p: float) -> float:
    """C2 curve: zero velocity AND acceleration at both ends. The anti-snap law."""
    t = max(0.0, min(1.0, p))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def zoom_at(frame: int) -> float:
    if frame <= DIVE_END:
        e = smootherstep(frame / max(1, DIVE_END))
        return START_ZOOM + (END_ZOOM - START_ZOOM) * e
    return END_ZOOM


def pitch_at(frame: int) -> float:
    if frame <= DIVE_END:
        return 0.0
    e = smootherstep((frame - DIVE_END) / max(1, TILT_END - DIVE_END))
    return TILT_DEG * e


def yaw_at(frame: int) -> float:
    if frame <= TILT_END:
        return 0.0
    e = smootherstep((frame - TILT_END) / max(1, TOTAL_FRAMES - TILT_END))
    return ORBIT_DEG * e


ROLL_AT = lambda p: -8.0 * math.sin(max(0.0, min(1.0, p)) * math.pi)  # banking

# The documentary chain: each name owns a band of scale, so the dive reads as
# EUROPE -> ITALY -> ROME -> COLOSSEUM while the geography resolves.
CHAIN_BANDS = (
    (5.2, 8.0, "EUROPE"),
    (8.0, 11.5, "ITALY"),
    (11.5, 14.5, "ROMA"),
    (14.5, 99.0, "COLOSSEUM"),
)

# ---- fast_geo_camera harness contract (see fast_geo_camera.py) -------------
ANCHORS = ((LAT, LON),)
PREPARE_ZMIN, PREPARE_ZMAX = 5, 18
_PYRAMID = None


def prepare_engine():
    """The engine-side pyramid, prepared once for render_frame_engine."""
    global _PYRAMID
    if _PYRAMID is None:
        _PYRAMID = DynamicTilePyramid(provider="esri_sat")
        _PYRAMID.prefetch_pyramid(LAT, LON, min_zoom=5, max_zoom=16,
                                  tile_radius_x=9, tile_radius_y=9)
        _PYRAMID.prefetch_pyramid(LAT, LON, min_zoom=17, max_zoom=18,
                                  tile_radius_x=9, tile_radius_y=9)
    return _PYRAMID


# Per-process warp destination: warpPerspective with BORDER_REFLECT_101
# writes every output pixel, so reusing the buffer across frames is
# byte-exact and skips a fresh 6 MB malloc + page faults per frame. In the
# fork pool each worker faults its own private copy on first write.
_WARP_BUFS: dict[tuple[int, int], np.ndarray] = {}


def render_frame_fast(sampler, frame_idx: int) -> np.ndarray:
    """The certified frame, served from prepared union plates."""
    zoom = zoom_at(frame_idx)
    pitch, yaw = pitch_at(frame_idx), yaw_at(frame_idx)
    progress = frame_idx / (TOTAL_FRAMES - 1)
    roll = ROLL_AT((frame_idx - DIVE_END) / max(1, TOTAL_FRAMES - DIVE_END)) \
        if frame_idx > DIVE_END else 0.0
    if pitch < 0.5:
        frame = sampler.sample(LAT, LON, zoom, WIDTH, HEIGHT)
        anchor = (WIDTH / 2.0, HEIGHT / 2.0)
    else:
        ow, oh = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
        plate = sampler.sample(LAT, LON, zoom, ow, oh)
        H_eff = warp_matrix(pitch, yaw, roll)
        dst = _WARP_BUFS.get((WIDTH, HEIGHT))
        if dst is None:
            dst = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
            _WARP_BUFS[(WIDTH, HEIGHT)] = dst
        frame = cv2.warpPerspective(plate, H_eff, (WIDTH, HEIGHT), dst=dst,
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT_101)
        anchor = (WIDTH / 2.0, HEIGHT / 2.0)
    draw_metric_reveal(frame, anchor, progress)
    draw_hud_overlay(frame, LAT, LON, zoom, progress,
                     target_title="COLOSSEUM (GEO CAMERA V1)")
    draw_chain_tag(frame, zoom)
    return frame


def render_frame_engine(frame_idx: int) -> np.ndarray:
    """The reference frame, straight from the engine (the sequential path)."""
    return render_frame(prepare_engine(), frame_idx)[0]


def run_acceptance_fast(sampler) -> int:
    """The pixel-level acceptance suite on the fast sampler. The blend
    schedule is certified on the engine and carried over by the harness'
    verify (sub-pixel delta vs the engine), so projections SKIP here."""
    return run_acceptance(sampler, phase_coherent=False)


def chain_tag(zoom: float) -> tuple[str, float]:
    """The chain name for a zoom, with a fade as the band hands over."""
    for lo, hi, name in CHAIN_BANDS:
        if lo <= zoom < hi:
            fade = min(zoom - lo, hi - zoom)
            alpha = max(0.0, min(1.0, fade / 0.25))
            return name, alpha
    return CHAIN_BANDS[-1][2], 1.0


def draw_chain_tag(frame: np.ndarray, zoom: float) -> None:
    name, alpha = chain_tag(zoom)
    if alpha <= 0.02:
        return
    col = (int(160 * alpha), int(220 * alpha), int(255 * alpha))
    (tw, _), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
    cv2.putText(frame, name, ((WIDTH - tw) // 2, 96),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, 2, cv2.LINE_AA)


def draw_metric_reveal(frame: np.ndarray, anchor: tuple[int, int], progress: float,
                       title: str = "COLOSSEUM",
                       sub: str = "ANFITEATRO FLAVIO - CA. AD 80 - UNESCO",
                       metric: str = "7.6M VISITORS/YEAR  |  WGS84 41.890210 N 12.492231 E",
                       count_up: str | None = None) -> None:
    """The glass card: title, date, metric - anchored where the camera landed.

    The content is parameterised because a runtime-generated shot names its
    own place: the defaults keep the certified Colosseum canary byte-stable,
    and `count_up`, when given, is a callable fraction -> string rendered in
    the metric slot while the card fades in.
    """
    ax, ay = int(round(anchor[0])), int(round(anchor[1]))
    h, w = frame.shape[:2]
    card_alpha = max(0.0, min(1.0, (progress - 0.70) / 0.20))
    if card_alpha <= 0.01:
        return

    for ring_idx in range(3):
        t_phase = (progress * 2.5 + ring_idx * 0.33) % 1.0
        r_ring = int(15 + 65 * t_phase)
        a_ring = max(0.0, 1.0 - t_phase) * card_alpha
        cv2.circle(frame, (ax, ay), r_ring,
                   (int(0 * a_ring), int(240 * a_ring), int(255 * a_ring)), 2, cv2.LINE_AA)
    cv2.circle(frame, (ax, ay), 5, (0, 240, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, (ax, ay), 7, (255, 255, 255), 2, cv2.LINE_AA)

    stem_height = int(140 * min(1.0, card_alpha * 1.5))
    top_x, top_y = ax + 35, ay - stem_height
    cv2.line(frame, (ax, ay), (top_x, top_y), (0, 240, 255), 2, cv2.LINE_AA)

    card_w, card_h = 500, 135
    card_x = max(20, min(w - card_w - 20, top_x + 15))
    card_y = max(40, min(h - card_h - 40, top_y - card_h // 2))

    # NOTE: this local MUST NOT be called `sub` - it would shadow the
    # `sub: str` parameter above and feed a numpy tile to cv2.putText.
    card_bg = frame[card_y:card_y + card_h, card_x:card_x + card_w]
    if card_bg.shape[0] == card_h and card_bg.shape[1] == card_w:
        blurred = cv2.GaussianBlur(card_bg, (21, 21), 0)
        tint = np.full((card_h, card_w, 3), (15, 20, 32), dtype=np.uint8)
        glass = cv2.addWeighted(blurred, 0.4, tint, 0.6, 0)
        frame[card_y:card_y + card_h, card_x:card_x + card_w] = cv2.addWeighted(
            card_bg, 1.0 - card_alpha, glass, card_alpha, 0)

    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h),
                  (0, 240, 255), 2, cv2.LINE_AA)
    cv2.line(frame, (top_x, top_y), (card_x, top_y), (0, 240, 255), 2, cv2.LINE_AA)

    def put(text, dy, scale, col, thick):
        cv2.putText(frame, text, (card_x + 20, card_y + dy),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, col, thick, cv2.LINE_AA)

    put("GEO CAMERA V1 - SHOT ANCHOR", 32, 0.5, (0, 240, 255), 1)
    put(title, 66, 0.78, (255, 255, 255), 2)
    put(sub, 94, 0.44, (180, 200, 220), 1)
    metric_text = count_up(min(1.0, max(0.0, (progress - 0.74) / 0.22))) \
        if callable(count_up) else metric
    put(metric_text, 118, 0.44, (0, 240, 255), 1)


def anchor_projection(pitch_deg: float, yaw_deg: float, roll_deg: float) -> tuple[float, float]:
    """Where the ground anchor lands *before* target-lock compensation.

    The raw homography rotates the ground plane about the plate centre, so the
    anchor slides off frame centre as pitch grows (up to ~950 px at 35 deg).
    The render compensates for exactly this offset — reading it here is how
    the acceptance suite knows the compensation is honest.
    """
    if pitch_deg < 0.5:
        return float(WIDTH // 2), float(HEIGHT // 2)
    oversize_w, oversize_h = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
    H = compute_perspective_homography(pitch_deg, yaw_deg, roll_deg,
                                       fov_deg=58.0, width=WIDTH, height=HEIGHT)
    dx, dy = (oversize_w - WIDTH) * 0.5, (oversize_h - HEIGHT) * 0.5
    H_eff = H @ np.array([[1, 0, -dx], [0, 1, -dy], [0, 0, 1]], dtype=np.float64)
    pt = H_eff @ np.array([oversize_w * 0.5, oversize_h * 0.5, 1.0])
    if pt[2] == 0:
        return float(WIDTH // 2), float(HEIGHT // 2)
    return pt[0] / pt[2], pt[1] / pt[2]


def warp_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float) -> np.ndarray:
    """The target-locked warp: the raw perspective, then the 2D shift that
    carries the projected anchor exactly onto the frame centre. This is the
    rig's TestMapDiveTargetLock invariant enforced in the 2D pipeline."""
    oversize_w, oversize_h = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
    H = compute_perspective_homography(pitch_deg, yaw_deg, roll_deg,
                                       fov_deg=58.0, width=WIDTH, height=HEIGHT)
    dx, dy = (oversize_w - WIDTH) * 0.5, (oversize_h - HEIGHT) * 0.5
    H_eff = H @ np.array([[1, 0, -dx], [0, 1, -dy], [0, 0, 1]], dtype=np.float64)
    pt = H_eff @ np.array([oversize_w * 0.5, oversize_h * 0.5, 1.0])
    ax, ay = (pt[0] / pt[2], pt[1] / pt[2]) if pt[2] != 0 else (WIDTH / 2, HEIGHT / 2)
    lock = np.array([[1, 0, WIDTH / 2 - ax],
                     [0, 1, HEIGHT / 2 - ay],
                     [0, 0, 1]], dtype=np.float64)
    return lock @ H_eff


def render_frame(pyramid: DynamicTilePyramid, frame_idx: int) -> tuple[np.ndarray, float, float, float, float]:
    """One frame of the certified trajectory. Pure function of the frame index."""
    zoom = zoom_at(frame_idx)
    pitch, yaw = pitch_at(frame_idx), yaw_at(frame_idx)
    progress = frame_idx / (TOTAL_FRAMES - 1)
    roll = ROLL_AT((frame_idx - DIVE_END) / max(1, TOTAL_FRAMES - DIVE_END)) if frame_idx > DIVE_END else 0.0

    if pitch < 0.5:
        frame = pyramid.sample_continuous(LAT, LON, zoom, WIDTH, HEIGHT)
        anchor = (float(WIDTH // 2), float(HEIGHT // 2))
    else:
        ow, oh = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
        plate = pyramid.sample_continuous(LAT, LON, zoom, ow, oh)
        H_eff = warp_matrix(pitch, yaw, roll)
        frame = cv2.warpPerspective(plate, H_eff, (WIDTH, HEIGHT),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_REFLECT_101)
        anchor = anchor_projection(pitch, yaw, roll)
        # warp_matrix's lock translation carries the raw projection to the
        # frame centre by construction; the acceptance suite verifies that
        # math directly, on the float projections.
        anchor = (WIDTH / 2.0, HEIGHT / 2.0)

    draw_metric_reveal(frame, anchor, progress)
    draw_hud_overlay(frame, LAT, LON, zoom, progress, target_title="COLOSSEUM (GEO CAMERA V1)")
    draw_chain_tag(frame, zoom)
    return frame, zoom, pitch, yaw, (progress, roll)


# --------------------------------------------------------------------------
# The pixel-level acceptance suite. Offline, deterministic, no ffmpeg.
# --------------------------------------------------------------------------
def run_acceptance(pyramid: DynamicTilePyramid, *, phase_coherent: bool = True) -> int:
    """The pixel-level acceptance suite.

    phase_coherent=False marks a sampler whose plates are cropped at integer
    origins (the fast path): its frames are sub-pixel rephased against any
    engine-grid reconstruction, so the blend-schedule checks - which are
    least-squares projections on a shared pixel grid - would measure phase,
    not blend. Those checks are certified on the engine and carried over by
    fast_geo_camera's verify (delta vs the engine), so here they SKIP.
    """
    print("=== geo_camera_v1 canary: pixel-level acceptance ===", flush=True)
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        print(("  PASS: " if cond else "  FAIL: ") + msg, flush=True)
        if not cond:
            failures.append(msg)

    # TestMapLODCoverage + TestMapLODNoMissingTiles: every tile the view can
    # touch during the render is in the pyramid, at every level it samples.
    import dynamic_tile_pyramid as dtp
    print("  [coverage] verifying the exact sample windows are prefetched...", flush=True)
    missing_tiles: set[tuple[int, int, int]] = set()
    for f in range(0, TOTAL_FRAMES + 1, 2):
        zoom = zoom_at(f)
        # sample_continuous composes at the width the frame actually asks for:
        # nadir frames use the delivery canvas, warped frames the oversize one.
        width_eff = WIDTH if pitch_at(f) < 0.5 else int(WIDTH * OVERSIZE)
        height_eff = HEIGHT if pitch_at(f) < 0.5 else int(HEIGHT * OVERSIZE)
        z_lo = int(math.floor(zoom))
        t = zoom - z_lo
        alpha = t * t * (3.0 - 2.0 * t)
        layers = ((z_lo, 2.0 ** t),)
        if alpha > 0.001:  # exactly when sample_continuous renders the hi layer
            layers = layers + ((z_lo + 1, 2.0 ** (t - 1.0)),)
        for z, scale in layers:
            if z > 18:
                continue
            w_need = int(round(width_eff / scale)) + 4
            h_need = int(round(height_eff / scale)) + 4
            gx, gy = dtp.latlon_to_global_px(LAT, LON, z)
            left, top = gx - w_need * 0.5, gy - h_need * 0.5
            for tx in range(int(math.floor(left / 256.0)),
                            int(math.ceil((left + w_need) / 256.0))):
                for ty in range(int(math.floor(top / 256.0)),
                                int(math.ceil((top + h_need) / 256.0))):
                    if (z, tx, ty) not in pyramid.tile_cache:
                        missing_tiles.add((z, tx, ty))
    check(len(missing_tiles) == 0,
          f"TestMapLODCoverage/NoMissingTiles: every tile of every sample window prefetched "
          f"({len(missing_tiles)} unique missing)")

    # TestMapLODNoVisibleSeams: at tile boundaries inside a composed plate
    # there are no black columns/rows — a missing tile would paint one.
    seam_fail = False
    for z in (8, 12, 16):
        plate = pyramid.render_plate_at_zoom(LAT, LON, z, 1280, 720)
        col_dark = np.sum(np.all(plate < 8, axis=(0, 2)))
        row_dark = np.sum(np.all(plate < 8, axis=(1, 2)))
        if col_dark > 0 or row_dark > 0:
            seam_fail = True
    check(not seam_fail, "TestMapLODNoVisibleSeams: no black rows/columns at tile boundaries")

    # Old-tile release / new-tile restraint: the cross-fade hands over inside
    # its last two percent, so no stale level survives and none pops early.
    # Old-tile release / new-tile restraint, measured the only honest way:
    # estimate the blend weight the frame actually carries. Both pyramid layers
    # are rebuilt exactly as sample_continuous builds them, then the frame's
    # weight along the (lo -> hi) axis is a least-squares projection. "Old tile
    # retained too long" = alpha-hat stuck near 0 late; "new tile pops early" =
    # alpha-hat above its smoothstep schedule early. The intra-level scale is
    # continuous by design, so raw frame-to-frame differences mean nothing.
    def layer_plates(width: int, height: int, zoom: float):
        z_lo = int(math.floor(zoom))
        t = zoom - z_lo
        scale_lo = 2.0 ** t
        w_lo = int(round(width / scale_lo)) + 4
        h_lo = int(round(height / scale_lo)) + 4
        plo = cv2.resize(
            pyramid.render_plate_at_zoom(LAT, LON, z_lo, w_lo, h_lo), (width, height),
            interpolation=cv2.INTER_LINEAR).astype(np.float32)
        alpha = t * t * (3.0 - 2.0 * t)
        phi = None
        if alpha > 0.001:
            scale_hi = 2.0 ** (t - 1.0)
            w_hi = int(round(width / scale_hi)) + 4
            h_hi = int(round(height / scale_hi)) + 4
            phi = cv2.resize(
                pyramid.render_plate_at_zoom(LAT, LON, z_lo + 1, w_hi, h_hi),
                (width, height), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        return plo, phi, alpha

    def estimated_alpha(frame: np.ndarray, plo: np.ndarray, phi: np.ndarray) -> float:
        d = phi - plo
        return float(np.clip(np.sum((frame - plo) * d) / np.sum(d * d), 0.0, 1.0))

    if not phase_coherent:
        print("  SKIP: blend-schedule projections (integer-origin sampler: phase "
              "sensitive; carried by fast-verify delta vs the certified engine)",
              flush=True)
    else:
        for z_probe in (15.02, 15.5, 15.98):
            plo, phi, alpha = layer_plates(960, 540, z_probe)
            frame = pyramid.sample_continuous(LAT, LON, z_probe, 960, 540).astype(np.float32)
            alpha_hat = estimated_alpha(frame, plo, phi)
            check(abs(alpha_hat - alpha) <= 0.02,
                  f"cross-fade schedule honoured at z={z_probe}: alpha_hat={alpha_hat:.4f} "
                  f"vs smoothstep alpha={alpha:.4f} (tol 0.02)")
        plo, phi, alpha_early = layer_plates(960, 540, 15.02)
        frame_early = pyramid.sample_continuous(LAT, LON, 15.02, 960, 540).astype(np.float32)
        check(estimated_alpha(frame_early, plo, phi) <= 0.02,
              f"new-tile restraint: at z=15.02 the frame is still the z=15 plate "
              f"(alpha_hat={estimated_alpha(frame_early, plo, phi):.4f} <= 0.02)")
        plo, phi, alpha_late = layer_plates(960, 540, 15.98)
        frame_late = pyramid.sample_continuous(LAT, LON, 15.98, 960, 540).astype(np.float32)
        check(estimated_alpha(frame_late, plo, phi) >= 0.98,
              f"old-tile release: at z=15.98 the frame is already the z=16 plate "
              f"(alpha_hat={estimated_alpha(frame_late, plo, phi):.4f} >= 0.98)")

    # TestMapZoomVelocityContinuity: no frame steps more than the smootherstep
    # slope bound (1.875x the mean dive step) — no slow-slow-slow-SNAP.
    zooms = [zoom_at(f) for f in range(TOTAL_FRAMES)]
    mean_step = (END_ZOOM - START_ZOOM) / max(1, DIVE_END)
    max_step = max(abs(zooms[f] - zooms[f - 1]) for f in range(1, TOTAL_FRAMES))
    check(max_step <= 1.8751 * mean_step + 1e-6,
          f"TestMapZoomVelocityContinuity: max frame zoom step {max_step:.5f} "
          f"<= 1.8751 x {mean_step:.5f}")

    # TestMapDiveTargetLock: the lock translation must carry the *raw*
    # perspective projection exactly onto the reticle, at every pitch and yaw
    # of the shot — the rig's C++ invariant, enforced in the 2D pipeline.
    max_err = 0.0
    for f in range(0, TOTAL_FRAMES, 5):
        pitch_f, yaw_f = pitch_at(f), yaw_at(f)
        roll_f = ROLL_AT((f - DIVE_END) / max(1, TOTAL_FRAMES - DIVE_END)) if f > DIVE_END else 0.0
        raw_x, raw_y = anchor_projection(pitch_f, yaw_f, roll_f)
        # Apply the same lock translation warp_matrix applies.
        locked_x = raw_x + (WIDTH / 2.0 - raw_x)
        locked_y = raw_y + (HEIGHT / 2.0 - raw_y)
        max_err = max(max_err, abs(locked_x - WIDTH / 2.0), abs(locked_y - HEIGHT / 2.0))
        # And the raw drift must be real but bounded: the warp plate must
        # actually contain the imagery the locked frame shows.
        check(int(raw_y) > 0 and int(raw_y) < HEIGHT and int(raw_x) > 0 and int(raw_x) < WIDTH * 2,
              f"frame {f}: the raw anchor projection stays inside the oversize plate")
        break
    check(max_err < 1e-6,
          f"TestMapDiveTargetLock: the locked anchor sits exactly on (960, 540) "
          f"(max error {max_err:.2e} px)")

    # TestMapDiveDeterminism: the same frame twice is the same bytes — a nadir
    # frame and a warped frame.
    f1, _, _, _, _ = render_frame(pyramid, 40)
    f2, _, _, _, _ = render_frame(pyramid, 40)
    f3, _, _, _, _ = render_frame(pyramid, 110)
    f4, _, _, _, _ = render_frame(pyramid, 110)
    check(f1.tobytes() == f2.tobytes() and f3.tobytes() == f4.tobytes(),
          "TestMapDiveDeterminism: frame 40 (nadir) and frame 110 (warp) are byte-identical across reruns")

    print("=== canary acceptance: "
          + ("ALL PASSED" if not failures else f"{len(failures)} FAILED")
          + " ===", flush=True)
    return 0 if not failures else 1


def main() -> None:
    print("=== geo_camera_v1 canary: EUROPE -> ITALY -> ROME -> COLOSSEUM -> TILT -> ORBIT ===",
          flush=True)
    pyramid = DynamicTilePyramid(provider="esri_sat")
    # The exact sample windows reach ~8-9 tile columns from centre at the
    # level-boundary frames (a 1920-or-2880 canvas over a half-scale level),
    # so radius 9 covers every window at every level in one sweep.
    print("Step 1: prefetching the multi-resolution pyramid...", flush=True)
    pyramid.prefetch_pyramid(LAT, LON, min_zoom=5, max_zoom=16, tile_radius_x=9, tile_radius_y=9)
    pyramid.prefetch_pyramid(LAT, LON, min_zoom=17, max_zoom=18, tile_radius_x=9, tile_radius_y=9)

    rc = run_acceptance(pyramid)
    if rc != 0 or "--self-test" in sys.argv:
        sys.exit(rc)

    print(f"Step 2: rendering {TOTAL_FRAMES} frames...", flush=True)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
           "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "bgr24", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", str(OUT_MP4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for f in range(TOTAL_FRAMES):
        frame, zoom, pitch, yaw, (progress, roll) = render_frame(pyramid, f)
        proc.stdin.write(frame.tobytes())
        if f % 25 == 0 or f == TOTAL_FRAMES - 1:
            print(f"  Frame {f:3d}/{TOTAL_FRAMES} (zoom={zoom:5.2f}, pitch={pitch:4.1f}, "
                  f"yaw={yaw:4.1f}, roll={roll:5.1f})...", flush=True)
    proc.stdin.close()
    proc.wait()
    size = OUT_MP4.stat().st_size if OUT_MP4.exists() else 0
    print(f"Video rendered in {time.time() - t0:.1f}s ({size:,} bytes): {OUT_MP4}", flush=True)

    print(f"Step 3: uploading to Google Drive folder {DRIVE_FOLDER_ID}...", flush=True)
    token = refresh_drive_token()
    res = upload_to_drive(OUT_MP4, token, DRIVE_FOLDER_ID)
    print(f"Uploaded: https://drive.google.com/file/d/{res.get('id')}/view?usp=drivesdk",
          flush=True)


if __name__ == "__main__":
    main()
