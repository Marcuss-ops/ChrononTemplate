#!/usr/bin/env python3
"""profile_fast_geo_stages - per-stage CPU cost of one fast-camera frame.

Why: the harness sweeps said "DRAM-bandwidth bound" but the honest claim
needs the per-stage numbers behind it. This tool decomposes
render_frame_fast into its arithmetic (crop, resize lo/hi, blend, warp,
each overlay pass, tobytes) and reports the min-of-N wall time per stage
on representative frames of the trajectory:

  0/20/40/60  nadir, single level        (cheap frames)
  80/88/92    nadir, cross-fade active   (two levels)
  96/110/120  warp phase, tilt ramping   (oversize sample + warpPerspective)
  130/140/149 orbit phase                 (warp + roll)

min-of-N: this box runs a compile farm in the background, so min is the
only robust estimator - the floor IS the cost we can optimize.

Usage:
  python3 ChrononTemplate/tools/profile_fast_geo_stages.py \
      [--builder render_geo_camera_canary] [--repeats 5] [--frames 40,110]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT / "Chronon3d/tools/cartography"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENCV_NUM_THREADS"] = "1"

DEFAULT_FRAMES = (0, 20, 40, 60, 80, 88, 92, 96, 100, 110, 120, 130, 140, 149)


def best_of(fn, repeats: int) -> float:
    """min wall seconds over `repeats` runs (noise floor of this box)."""
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best * 1000.0  # ms


def main() -> None:
    import cv2  # noqa: PLC0415
    cv2.setNumThreads(1)

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--builder", default="render_geo_camera_canary")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--frames", default=",".join(str(f) for f in DEFAULT_FRAMES))
    args = ap.parse_args()

    import importlib
    builder = importlib.import_module(args.builder)

    import dynamic_tile_pyramid as dyn
    import fast_plate_sampler as fast

    pyramid = dyn.DynamicTilePyramid(provider="esri_sat")
    pyramid.prefetch_pyramid(*builder.ANCHORS[0], min_zoom=5,
                             max_zoom=builder.PREPARE_ZMAX,
                             tile_radius_x=9, tile_radius_y=9)
    sampler = fast.FastPlateSampler(pyramid, builder.WIDTH, builder.HEIGHT)
    sampler.prepare(builder.ANCHORS, builder.PREPARE_ZMIN, builder.PREPARE_ZMAX)

    from dynamic_tile_pyramid import latlon_to_global_px
    LAT, LON = builder.ANCHORS[0]

    frames = [int(f) for f in args.frames.split(",") if f != ""]
    print(f"{'frame':>5} {'phase':>6} {'zoom':>6} | {'crop+rs.lo':>10} {'crop+rs.hi':>10} "
          f"{'blend':>7} {'warp':>7} {'metric':>7} {'hud(vign)':>9} {'hud(rest)':>9} "
          f"{'chain':>6} {'tobytes':>8} | {'full':>7} | {'fallback':>8}", flush=True)

    for f in frames:
        zoom = builder.zoom_at(f)
        pitch, yaw = builder.pitch_at(f), builder.yaw_at(f)
        roll = builder.ROLL_AT((f - builder.DIVE_END) / max(1, builder.TOTAL_FRAMES - builder.DIVE_END)) \
            if f > builder.DIVE_END else 0.0
        phase = "nadir" if pitch < 0.5 else "warp"
        W, H = builder.WIDTH, builder.HEIGHT
        ow, oh = int(W * builder.OVERSIZE), int(H * builder.OVERSIZE)
        tw, th = (W, H) if phase == "nadir" else (ow, oh)

        # -- decompose sampler.sample exactly as fast_plate_sampler does ----
        z_lo = int(np.floor(zoom))
        t = zoom - z_lo
        alpha = t * t * (3.0 - 2.0 * t)
        scale_lo = 2.0 ** t
        scale_hi = 2.0 ** (t - 1.0)
        w_lo = int(round(tw / scale_lo)) + 4
        h_lo = int(round(th / scale_lo)) + 4
        lo_px = latlon_to_global_px(LAT, LON, z_lo)

        def stage_lo():
            crop = sampler._crop(z_lo, lo_px, w_lo, h_lo)
            if crop is None:
                return None
            return cv2.resize(crop, (tw, th), interpolation=cv2.INTER_LINEAR)

        t_lo = best_of(stage_lo, args.repeats)
        plate_lo = stage_lo()

        t_hi = t_blend = 0.0
        plate_hi = None
        if alpha > 0.001:
            hi_px = latlon_to_global_px(LAT, LON, z_lo + 1)
            w_hi = int(round(tw / scale_hi)) + 4
            h_hi = int(round(th / scale_hi)) + 4

            def stage_hi():
                crop = sampler._crop(z_lo + 1, hi_px, w_hi, h_hi)
                if crop is None:
                    return None
                return cv2.resize(crop, (tw, th), interpolation=cv2.INTER_LINEAR)

            t_hi = best_of(stage_hi, args.repeats)
            plate_hi = stage_hi()
            if plate_lo is not None and plate_hi is not None:
                t_blend = best_of(lambda: cv2.addWeighted(
                    plate_lo, 1.0 - alpha, plate_hi, alpha, 0.0), args.repeats)

        # -- warp ------------------------------------------------------------
        t_warp = 0.0
        warped = None
        if phase == "warp" and plate_lo is not None:
            H_eff = builder.warp_matrix(pitch, yaw, roll)
            src = cv2.addWeighted(plate_lo, 1.0 - alpha, plate_hi, alpha, 0.0) \
                if plate_hi is not None else plate_lo
            t_warp = best_of(lambda: cv2.warpPerspective(
                src, H_eff, (W, H), flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT_101), args.repeats)
            warped = cv2.warpPerspective(src, H_eff, (W, H),
                                         flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_REFLECT_101)

        base = warped if warped is not None else plate_lo
        if base is None:  # sampler fell back to the engine: mark it honestly
            fallback = "ENGINE"
        else:
            fallback = f"{len(base):d}px-ok"

        # -- overlays on a static base ---------------------------------------
        anchor = (W / 2.0, H / 2.0)
        progress = f / (builder.TOTAL_FRAMES - 1)

        def stage_metric():
            fr = base.copy()
            builder.draw_metric_reveal(fr, anchor, progress)
        t_metric = best_of(stage_metric, args.repeats)

        hud_frame = base.copy()
        builder.draw_metric_reveal(hud_frame, anchor, progress)

        def stage_vignette():
            fr = hud_frame.copy()
            h, w = fr.shape[:2]
            overlay = fr.copy()
            cv2.circle(overlay, (w // 2, h // 2), int(w * 0.75), (0, 0, 0), -1)
            fr[:] = cv2.addWeighted(fr, 0.85, overlay, 0.15, 0)
        t_vignette = best_of(stage_vignette, args.repeats)

        def stage_hud_rest():
            fr = hud_frame.copy()
            builder.draw_hud_overlay(fr, LAT, LON, zoom, progress,
                                     target_title="COLOSSEUM (GEO CAMERA V1)")
        t_hud_full = best_of(stage_hud_rest, args.repeats)
        t_hud_rest = max(0.0, t_hud_full - t_vignette)

        def stage_chain():
            fr = hud_frame.copy()
            builder.draw_chain_tag(fr, zoom)
        t_chain = best_of(stage_chain, args.repeats)

        t_copy = best_of(lambda: base.copy(), args.repeats)

        # -- the real full frame ---------------------------------------------
        t_full = best_of(lambda: builder.render_frame_fast(sampler, f), args.repeats)
        t_tobytes = best_of(lambda: builder.render_frame_fast(
            sampler, f).tobytes(), args.repeats) - t_full

        print(f"{f:>5} {phase:>6} {zoom:>6.2f} | {t_lo:>9.1f}ms {t_hi:>9.1f}ms "
              f"{t_blend:>6.1f}ms {t_warp:>6.1f}ms {t_metric:>6.1f}ms "
              f"{t_vignette:>8.1f}ms {t_hud_rest:>8.1f}ms {t_chain:>5.1f}ms "
              f"{t_tobytes:>7.1f}ms | {t_full:>6.1f}ms | {fallback:>8}", flush=True)

    print("\nNote: ms are min-of-N on a box with background compile load; "
          "absolute values are upper bounds, RATIOS are trustworthy.", flush=True)


if __name__ == "__main__":
    main()
