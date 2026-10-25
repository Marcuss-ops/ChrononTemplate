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
for p in (str(ROOT / "ChrononPlugin/plugins/maps/tools/cartography"), str(HERE)):
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
    if os.environ.get("CHRONON_OPENCL_FRAME_RENDER") == "1":
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            raise RuntimeError("OpenCL GPU frame rendering did not initialize in a worker")
        device = (cv2.ocl.Device.getDefault() if hasattr(cv2.ocl, "Device")
                  else cv2.ocl.Device_getDefault())
        if "NVIDIA" not in device.vendorName().upper():
            raise RuntimeError(f"OpenCL worker selected unexpected device: {device.name()}")


def _render_block(args) -> tuple[bytes, int]:
    f0, f1 = args
    builder = _S["builder"]
    sampler = _S["sampler"]
    parts = []
    fallbacks_before = sampler.fallback_count
    lo_only_before = sampler.lo_only_blend_count
    if getattr(sampler, "gpu_map_enabled", False):
        # OpenCL operations are queued asynchronously. Keep several complete
        # UMat frames alive before downloading the oldest one so CPU-side
        # camera/effect setup for later frames can overlap GPU execution.
        # This does not change pixels or ordering; the only host readback is
        # still the single ordered handoff required by FFmpeg's stdin pipe.
        pending = []
        for f in range(f0, min(f1, builder.TOTAL_FRAMES)):
            pending.append(builder.render_frame_fast(sampler, f))
        for frame in pending:
            if hasattr(frame, "get"):
                frame = frame.get()
            parts.append(frame.tobytes())
    else:
        # CPU samplers reuse scratch arrays, so serialize their copy into the
        # pipe payload before asking for the next frame.
        for f in range(f0, min(f1, builder.TOTAL_FRAMES)):
            frame = builder.render_frame_fast(sampler, f)
            if hasattr(frame, "get"):
                frame = frame.get()
            parts.append(frame.tobytes())
    return (b"".join(parts), sampler.fallback_count - fallbacks_before,
            sampler.lo_only_blend_count - lo_only_before)


def _iter_gpu_block_frames(args):
    """Render an ordered GPU block and yield each host frame exactly once.

    Keep the UMat queueing used to overlap camera/effect setup with OpenCL,
    but do not join the readbacks into a second block-sized bytes object. At
    4K, joining eight BGR frames temporarily duplicates roughly 200 MB before
    FFmpeg has consumed any of them.
    """
    f0, f1 = args
    builder = _S["builder"]
    sampler = _S["sampler"]
    pending = []
    for frame_idx in range(f0, min(f1, builder.TOTAL_FRAMES)):
        pending.append(builder.render_frame_fast(sampler, frame_idx))
    for frame in pending:
        if hasattr(frame, "get"):
            frame = frame.get()
        # NumPy exposes its contiguous pixel storage through the buffer
        # protocol. Passing a memoryview to the pipe avoids allocating and
        # copying a second full-frame `bytes` object after UMat readback.
        if not frame.flags.c_contiguous:
            frame = np.ascontiguousarray(frame)
        yield memoryview(frame)


# ---- reusable pipeline (used by main() and by programmatic callers) -------
def build_sampler(builder):
    """Prefetch the pyramid and prepare union plates for a builder module."""
    import cv2  # noqa: PLC0415
    cv2.setNumThreads(1)
    import dynamic_tile_pyramid as dyn
    import fast_plate_sampler as fast

    provider = getattr(builder, "tile_provider", "esri_sat")
    release = getattr(builder, "wayback_release", None)
    pyramid = dyn.DynamicTilePyramid(provider=provider, wayback_release=release)
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
        cmd += ["-c:v", "h264_nvenc", "-gpu", "0", "-preset", preset,
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
    stderr_tail = deque(maxlen=2)

    def drain_stderr() -> None:
        while True:
            chunk = proc.stderr.read(4096)
            if not chunk:
                return
            stderr_tail.append(chunk)

    stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
    stderr_thread.start()
    fallback_frames = 0
    lo_only_frames = 0
    try:
        if getattr(sampler, "gpu_map_enabled", False):
            # Editorial GPU compositions share one process-local OpenCL
            # context. Do not fork that context: enqueue a small ordered batch
            # of frames per call and overlap its asynchronous GPU work with
            # host-side camera/effect preparation instead.
            # Queue enough frames to keep OpenCL busy across the ordered
            # readback/pipe handoff, without materializing a full clip on GPU.
            # Final UMat frames are small relative to the prepared map plates.
            # Keep the live GPU output pool bounded even when CPU callers
            # configure larger process-pool blocks.
            gpu_block = 16
            gpu_blocks = [(f0, min(f0 + gpu_block, total))
                          for f0 in range(0, total, gpu_block)]
            for block_args in gpu_blocks:
                begin_batch = getattr(sampler, "begin_opencl_frame_batch", None)
                if begin_batch is not None:
                    frame_count = block_args[1] - block_args[0]
                    begin_batch(frame_count, sampler.W, sampler.H)
                # Dual-epoch scenes sample a second prepared map for every
                # output frame. Give that sampler its own frame destinations
                # so the queued UMat results remain live until ordered readback.
                epoch_sampler = getattr(builder, "epoch_before_sampler", None)
                begin_epoch_batch = getattr(epoch_sampler, "begin_opencl_frame_batch", None)
                if begin_epoch_batch is not None:
                    begin_epoch_batch(block_args[1] - block_args[0],
                                      epoch_sampler.W, epoch_sampler.H)
                fallbacks_before = sampler.fallback_count
                lo_only_before = sampler.lo_only_blend_count
                for frame_bytes in _iter_gpu_block_frames(block_args):
                    proc.stdin.write(frame_bytes)
                end_batch = getattr(sampler, "end_opencl_frame_batch", None)
                if end_batch is not None:
                    end_batch()
                end_epoch_batch = getattr(epoch_sampler, "end_opencl_frame_batch", None)
                if end_epoch_batch is not None:
                    end_epoch_batch()
                block_fallbacks = sampler.fallback_count - fallbacks_before
                fallback_frames += block_fallbacks
                lo_only_frames += sampler.lo_only_blend_count - lo_only_before
                if block_fallbacks:
                    raise RuntimeError(f"map sampling used slow fallback in {block_fallbacks} frame(s)")
        else:
            with ctx.Pool(processes=workers, initializer=_worker_init) as pool:
                for data, block_fallbacks, block_lo_only in pool.imap(_render_block, blocks):  # submission order
                    fallback_frames += block_fallbacks
                    lo_only_frames += block_lo_only
                    if block_fallbacks:
                        raise RuntimeError(f"map sampling used slow fallback in {block_fallbacks} frame(s)")
                    proc.stdin.write(data)
        produced = time.perf_counter() - t0
        try:
            proc.stdin.close()
        except BrokenPipeError:
            # FFmpeg may exit before consuming all frames; preserve its
            # diagnostic/status as the primary failure below.
            pass
        stderr_thread.join()
        return_code = proc.wait()
    except BrokenPipeError as exc:
        # Keep FFmpeg's stderr and exit status when NVENC closes its input
        # early. Killing the encoder here used to hide the real initialization
        # or device-loss error behind a generic BrokenPipeError.
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        try:
            return_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            return_code = proc.wait()
        stderr_thread.join()
        diagnostic = b"".join(stderr_tail).decode("utf-8", errors="replace")
        raise RuntimeError(
            f"ffmpeg closed the frame pipe early (status {return_code}): {diagnostic}"
        ) from exc
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
             "preset": preset, "quality": crf,
             # Rendering and encoding overlap while raw frames are streamed;
             # this is only the post-production tail, not exclusive encoder CPU.
             "post_frame_tail_s": max(0.0, elapsed - produced),
             # Retained for dynamic-map telemetry v1 compatibility. Sampling
             # is fail-closed, so any missing plate aborts before encoding.
             "engine_fallback_frames": 0}
    encoder = "h264_nvenc" if gpu_required else "libx264"
    stats["encoder"] = encoder
    stats["gpu_encoder"] = gpu_required
    stats["engine_fallback_frames"] = fallback_frames
    stats["lo_only_blend_frames"] = lo_only_frames
    print(f"frame production: {produced:.2f}s ({stats['production_fps']:.1f} FPS) | "
          f"total incl. encode: {elapsed:.2f}s ({stats['total_fps']:.1f} FPS, "
          f"{stats['bytes']:,} bytes) | "
          f"{'1 OpenCL process' if getattr(sampler, 'gpu_map_enabled', False) else f'{workers} CPU workers'}, "
          f"{encoder}", flush=True)
    return stats


def verify_against_sampler(builder, sampler) -> bool:
    """Check prepared-plate coverage at representative fast-render frames."""
    print("=== verify: prepared-plate coverage and deterministic fast frames ===", flush=True)
    bad = 0
    for f in sorted({0, builder.TOTAL_FRAMES // 2, builder.TOTAL_FRAMES - 1}):
        first = builder.render_frame_fast(sampler, f)
        second = builder.render_frame_fast(sampler, f)
        if hasattr(first, "get"):
            first = first.get()
        if hasattr(second, "get"):
            second = second.get()
        if first.shape != second.shape or first.tobytes() != second.tobytes():
            bad += 1
            print(f"  frame {f}: NON-DETERMINISTIC or invalid shape", flush=True)
    checked = len(sorted({0, builder.TOTAL_FRAMES // 2, builder.TOTAL_FRAMES - 1}))
    print(f"  {checked - bad}/{checked} representative frames deterministic; "
          "all sampler misses raise before encode", flush=True)
    return bad == 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--builder", default="render_geo_camera_canary",
                    help="module defining WIDTH/HEIGHT/FPS/TOTAL_FRAMES, ANCHORS, "
                         "PREPARE_ZMIN/PREPARE_ZMAX, render_frame_fast(sampler, f), "
                         "optional run_acceptance_fast(sampler)")
    ap.add_argument("--out", required=True, help="output mp4 path")
    ap.add_argument("--workers", type=int, default=min(12, (os.cpu_count() or 4) // 2))
    ap.add_argument("--block", type=int, default=2,
                    help="frames per worker task; warp frames cost ~3x a nadir "
                         "frame, so small blocks keep the tail balanced")
    ap.add_argument("--preset", default="veryfast",
                    help="x264 preset; ultrafast shows the raw production speed")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--verify", action="store_true",
                    help="verify prepared-plate coverage and run fast acceptance before encoding")
    args = ap.parse_args()

    import importlib
    builder = importlib.import_module(args.builder)

    # Build and prepare everything ONCE, in the parent; the forked pool
    # inherits it copy-on-write.
    sampler = build_sampler(builder)

    if args.verify:
        if not verify_against_sampler(builder, sampler):
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
