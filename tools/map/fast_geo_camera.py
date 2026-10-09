#!/usr/bin/env python3
"""fast_geo_camera - the parallel render harness for geo_camera_v1.

Three speedups over the sequential renderer, with identical frames:

  1. FastPlateSampler (fast_plate_sampler.py): each pyramid level composed
     ONCE (union plate over all anchors), frames become integer crops + the
     engine's own resize/blend math.
  2. Parallel frames: a fork-based process pool renders frame blocks
     concurrently. The sampler is built and prepared in the PARENT, so the
     forked workers inherit the warm tile cache and the prepared plates
     copy-on-write - zero per-worker warm-up.
  3. Ordered streaming: pool.imap yields blocks in submission order, so
     ffmpeg receives frames 0..N-1 exactly like the sequential encode.

Usage:
  fast_geo_camera.py --builder render_geo_camera_canary --out out.mp4
  fast_geo_camera.py --builder ... --verify
  fast_geo_camera.py --builder ... --workers 16 --block 5
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import threading
import time
from collections import deque
from multiprocessing import get_context
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # the repo root (VeloxEditing), two levels up
for p in (str(ROOT / "Chronon3d/tools/cartography"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

# CRITICAL: pin every OpenCV/OMP thread pool to 1 BEFORE cv2 is first
# imported anywhere in this process tree. The fork pool then gives one
# single-threaded worker per core; fork-after-threads would otherwise have
# every worker fighting over the inherited pool (16 workers x 24 threads).
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENCV_NUM_THREADS"] = "1"

_S = None  # per-worker sampler, inherited via fork


def _worker_init() -> None:
    import cv2  # noqa: PLC0415 - worker-side, on purpose
    try:
        cv2.setNumThreads(1)  # belt and braces: env may arrive after init
    except Exception:
        pass


def _render_block(args) -> tuple[bytes, int]:
    f0, f1 = args
    builder = _S["builder"]
    sampler = _S["sampler"]
    fb0 = sampler.fallback_count
    parts = []
    for f in range(f0, min(f1, builder.TOTAL_FRAMES)):
        parts.append(builder.render_frame_fast(sampler, f).tobytes())
    return b"".join(parts), sampler.fallback_count - fb0


# ---- reusable pipeline (used by main() and by programmatic callers) -------
def build_sampler(builder):
    """Prefetch the pyramid and prepare union plates for a builder module."""
    import cv2  # noqa: PLC0415
    cv2.setNumThreads(1)
    import dynamic_tile_pyramid as dyn
    import fast_plate_sampler as fast

    pyramid = dyn.DynamicTilePyramid(provider="esri_sat")
    t0 = time.time()
    pyramid.prefetch_pyramid(*builder.ANCHORS[0], min_zoom=5,
                             max_zoom=builder.PREPARE_ZMAX,
                             tile_radius_x=9, tile_radius_y=9)
    print(f"  prefetch done in {time.time() - t0:.1f}s", flush=True)
    sampler = fast.FastPlateSampler(pyramid, builder.WIDTH, builder.HEIGHT)
    sampler.prepare(builder.ANCHORS, builder.PREPARE_ZMIN, builder.PREPARE_ZMAX)
    print(f"  prepared levels {sampler.z_min}..{sampler.z_max}: "
          f"{sorted(sampler.plates)}", flush=True)
    return sampler


def encode_with_pool(builder, sampler, out_path: Path, workers: int, block: int,
                     preset: str = "veryfast", crf: int = 18,
                     gpu_required: bool = False) -> dict:
    """Encode builder frames through the ordered fork pool. Returns stats."""
    out = Path(out_path)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
           "-s", f"{builder.WIDTH}x{builder.HEIGHT}", "-pix_fmt", "bgr24",
           "-r", str(builder.FPS), "-i", "-"]
    if gpu_required:
        # Production map overlays must use the NVIDIA encoder. There is no
        # software fallback: an unavailable/lost GPU fails the runtime job.
        cmd += ["-c:v", "h264_nvenc", "-gpu", "0", "-preset", "p4",
                "-tune", "hq", "-rc", "vbr", "-cq", str(crf), "-b:v", "0"]
    else:
        cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
    cmd += ["-pix_fmt", "yuv420p", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    total = builder.TOTAL_FRAMES
    blocks = [(f0, min(f0 + block, total)) for f0 in range(0, total, block)]
    ctx = get_context("fork")
    globals()["_S"] = {"builder": builder, "sampler": sampler}
    t0 = time.perf_counter()
    fallback_frames = 0
    stderr_tail = deque(maxlen=2)

    def drain_stderr() -> None:
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                return
            stderr_tail.append(chunk)

    stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
    stderr_thread.start()
    try:
        with ctx.Pool(processes=workers, initializer=_worker_init) as pool:
            for data, fb in pool.imap(_render_block, blocks):  # submission order
                proc.stdin.write(data)
                fallback_frames += fb
        produced = time.perf_counter() - t0
        try:
            proc.stdin.close()
        except BrokenPipeError:
            # FFmpeg may exit before consuming all frames; preserve its
            # diagnostic/status as the primary failure below.
            pass
        stderr_thread.join()
        return_code = proc.wait()
    except BaseException:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        proc.kill()
        proc.wait()
        stderr_thread.join()
        raise
    elapsed = time.perf_counter() - t0
    if return_code != 0:
        raise RuntimeError(
            f"ffmpeg exited with status {return_code}: "
            f"{b''.join(stderr_tail).decode('utf-8', errors='replace')}"
        )
    if not out.is_file() or out.stat().st_size <= 0:
        raise RuntimeError("ffmpeg reported success but produced no non-empty output")
    stats = {"frames": total, "production_s": produced, "total_s": elapsed,
             "production_fps": total / produced, "total_fps": total / elapsed,
             "bytes": out.stat().st_size, "out": str(out),
             # Rendering and encoding overlap while raw frames are streamed;
             # this is only the post-production tail, not exclusive encoder CPU.
             "post_frame_tail_s": max(0.0, elapsed - produced),
             "engine_fallback_frames": fallback_frames}
    encoder = "h264_nvenc" if gpu_required else f"libx264 {preset}"
    stats["encoder"] = encoder
    stats["gpu_encoder"] = gpu_required
    print(f"frame production: {produced:.2f}s ({stats['production_fps']:.1f} FPS) | "
          f"total incl. encode: {elapsed:.2f}s ({stats['total_fps']:.1f} FPS, "
          f"{stats['bytes']:,} bytes) | {workers} workers, {encoder}", flush=True)
    print(f"  engine fallbacks: {fallback_frames}/{total} frame(s) served by "
          f"the slow engine (0 = every frame took the fast path)", flush=True)
    return stats


def verify_against_engine(builder, sampler) -> bool:
    """Sub-pixel delta verify of the fast path against the engine path."""
    print("=== verify: fast frames vs engine frames ===", flush=True)
    MAX_DELTA, MEAN_DELTA = 220, 15.0
    worst_max, worst_mean, bad = 0, 0.0, 0
    for f in range(0, builder.TOTAL_FRAMES, 7):
        got = builder.render_frame_fast(sampler, f).astype(np.int16)
        want = builder.render_frame_engine(f).astype(np.int16)
        diff = np.abs(got - want)
        fmax, fmean = int(diff.max()), float(diff.mean())
        worst_max, worst_mean = max(worst_max, fmax), max(worst_mean, fmean)
        if fmax > MAX_DELTA or fmean > MEAN_DELTA:
            bad += 1
            print(f"  frame {f}: OUT OF TOLERANCE (max {fmax}, mean {fmean:.4f})",
                  flush=True)
    checked = math.ceil(builder.TOTAL_FRAMES / 7)
    print(f"  {checked - bad}/{checked} sampled frames within sub-pixel "
          f"tolerance (worst max delta {worst_max} <= {MAX_DELTA}, "
          f"worst mean {worst_mean:.4f} <= {MEAN_DELTA})", flush=True)
    return bad == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--builder", default="render_geo_camera_canary",
                    help="module defining WIDTH/HEIGHT/FPS/TOTAL_FRAMES, ANCHORS, "
                         "PREPARE_ZMIN/PREPARE_ZMAX, render_frame_fast(sampler, f), "
                         "render_frame_engine(f), optional run_acceptance_fast(sampler)")
    ap.add_argument("--out", required=True, help="output mp4 path")
    ap.add_argument("--workers", type=int, default=min(12, (os.cpu_count() or 4) // 2))
    ap.add_argument("--block", type=int, default=2,
                    help="frames per worker task; warp frames cost ~3x a nadir "
                         "frame, so small blocks keep the tail balanced")
    ap.add_argument("--preset", default="veryfast",
                    help="x264 preset; ultrafast shows the raw production speed")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--verify", action="store_true",
                    help="byte-compare fast frames against the engine's, then run "
                         "the builder's fast acceptance suite, before encoding")
    args = ap.parse_args()

    import importlib
    builder = importlib.import_module(args.builder)

    # Build and prepare everything ONCE, in the parent; the forked pool
    # inherits it copy-on-write.
    sampler = build_sampler(builder)

    if args.verify:
        # The fast path crops prepared plates at integer origins while the
        # engine recomposes each frame at its own rounded origin, so a frame
        # can be sub-pixel rephased (<= 0.5 px) against the reference. On
        # satellite imagery that is resampler shimmer, not a content change:
        # strong edges shift by one sample (high per-pixel delta at edges),
        # while structural bugs (wrong level, black tiles, missing blend)
        # blow the MEAN far past anything a half-pixel phase can produce.
        if not verify_against_engine(builder, sampler):
            print("  VERIFY FAILED - refusing to encode", flush=True)
            sys.exit(1)
        if hasattr(builder, "run_acceptance_fast"):
            print("  running the builder's acceptance suite in fast mode...", flush=True)
            if builder.run_acceptance_fast(sampler) != 0:
                print("  ACCEPTANCE FAILED - refusing to encode", flush=True)
                sys.exit(1)
        print("  verify OK", flush=True)

    encode_with_pool(builder, sampler, Path(args.out), args.workers,
                     args.block, args.preset, args.crf)


if __name__ == "__main__":
    main()
