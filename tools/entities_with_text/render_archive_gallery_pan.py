#!/usr/bin/env python3
"""Archive gallery pan: N archive photos in a row under a moving camera.

Builds a ``chronon.render-plan.v3`` plan with N archive-style photo cards on a
peach paper plate row plus a persistent top-left ``Archive image`` label, then
(optionally) validates and renders it with the Chronon3D CLI.  All photo
motion comes from resolved ``camera_samples`` — a slow left-to-right dolly
pan with a gentle push-in — so the whole sequence renders through the native
GPU camera path.

Example::

    python render_archive_gallery_pan.py                      # plan only
    python render_archive_gallery_pan.py --render             # GPU render
    python render_archive_gallery_pan.py --render --backend vulkan
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
FPS, WIDTH, HEIGHT = 30, 1920, 1080

FONT_HEADER = "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_CAPTION = "ChrononTemplate/assets/fonts/didone_font_playfair_display_italic.ttf"

DEFAULT_IMAGES = [
    ("ChrononTemplate/assets/famous_people_trio_v1/neil_armstrong.png", "Neil Armstrong"),
    ("ChrononTemplate/assets/famous_people_trio_v1/john_glenn.png", "John Glenn"),
    ("ChrononTemplate/assets/famous_people_trio_v1/sally_ride.png", "Sally Ride"),
    ("ChrononTemplate/assets/archival_refs_v2/al_capone_trio_source.png", "Al Capone"),
    ("ChrononTemplate/assets/archival_refs_v2/von_puckler_source.png", "Von Puckler"),
    ("ChrononTemplate/assets/archival_refs_v2/chicago_building_source.png", "Chicago 1929"),
    ("ChrononTemplate/assets/ai_tabletop/02_rain_bridge.png", "Rain Bridge"),
    ("ChrononTemplate/assets/ai_tabletop/03_samurai_armor.png", "Samurai Armor"),
]

# Archive paper plate: cream card on peach paper, dark sepia caption.
PAPER_COLOR = [0.937, 0.780, 0.639, 1.0]     # peach paper background
PLATE_COLOR = [0.954, 0.922, 0.874, 1.0]     # cream photo card
CAPTION_COLOR = "#2b1b12"

PLATE_WIDTH, PLATE_HEIGHT = 1240, 880
IMAGE_WIDTH, IMAGE_HEIGHT = 1080, 620
IMAGE_LIFT = 40.0                            # image centre above plate centre (Y up)
CAPTION_DROP = 350.0                         # caption centre below plate centre (Y up)
PITCH = PLATE_WIDTH + 260                    # horizontal card pitch (world = px)

OPEN_PAD = 300.0                             # lead-in margin at pan start/end


def _hex_rgba(hex_color: str) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def _camera(position_z: float) -> dict:
    return {
        "type": "perspective",
        "position": [0.0, 0.0, position_z],
        "rotation_deg": [0.0, 0.0, 0.0],
        "fov_deg": 55.0,
        "near": 1.0,
        "far": 10000.0,
        "zoom": 1.0,
        "sensor_width_mm": 36.0,
        "lens_shift": [0.0, 0.0],
    }


def build_plan(images: list[tuple[str, str]], frames_per_photo: int) -> dict:
    """One static card row; every motion is the camera pan/push.

    Verified conventions (pixel probes, software backend):
    every enable_3d layer position is centre-relative world space —
    X right, Y up, positive Z farther from the camera — and one world
    unit is roughly one pixel on the z=0 plane at camera z=-1080, fov 55.
    Plain text layers keep canvas coordinates (X right, Y down).
    """
    count = len(images)
    centers = [(index - (count - 1) / 2) * PITCH for index in range(count)]
    start_x = centers[0] - OPEN_PAD
    end_x = centers[-1] + OPEN_PAD
    total_frames = frames_per_photo * count + 32

    layers = [
        {"id": "gallery-paper", "type": "color", "color": PAPER_COLOR,
         "size": [WIDTH, HEIGHT], "screen_space": True,
         "start_frame": 0, "duration_frames": total_frames},
        {"id": "gallery-archive-label", "type": "text", "text": "Archive image",
         "size": [640, 84], "position": [300, 120],
         "start_frame": 0, "duration_frames": total_frames,
         "style": {"font": FONT_HEADER, "font_size": 34, "fill": "#1f1710"}},
        {"id": "gallery-archive-rule", "type": "shape",
         "size": [300, 4], "position": [300, 168],
         "start_frame": 0, "duration_frames": total_frames,
         "shape": {"type": "rect", "fill": [0.12, 0.09, 0.06, 1.0]}},
    ]

    # NOTE: no per-image effect stack — the strict native-GPU path refuses
    # EffectStackNode fallbacks, and the archive tone is kept by the paper
    # palette instead.

    for index, (asset, caption) in enumerate(images):
        x_world = centers[index]
        depth = 90.0 if index % 2 else 0.0        # alternate card depth -> parallax
        tilt = 1.6 if index % 3 == 0 else -1.6    # hand-placed card angle
        plate_z = depth + 2.0                     # plate sits just behind the photo
        layers.append({
            "id": f"archive-card-{index:02d}", "type": "shape",
            "size": [PLATE_WIDTH, PLATE_HEIGHT],
            "position": [x_world, 0.0, plate_z],
            "rotation": [0.0, 0.0, tilt],
            "enable_3d": True, "start_frame": 0, "duration_frames": total_frames,
            "shape": {"type": "rect", "fill": PLATE_COLOR},
        })
        layers.append({
            "id": f"archive-photo-{index:02d}", "type": "image", "asset": asset,
            "size": [IMAGE_WIDTH, IMAGE_HEIGHT],
            "position": [x_world, IMAGE_LIFT, depth],
            "rotation": [0.0, 0.0, tilt],
            "fit": "cover", "enable_3d": True,
            "start_frame": 0, "duration_frames": total_frames,
        })
        layers.append({
            "id": f"archive-caption-{index:02d}", "type": "text", "text": caption,
            "size": [PLATE_WIDTH - 120, 92],
            "position": [x_world, -CAPTION_DROP, plate_z],
            "rotation": [0.0, 0.0, tilt],
            "enable_3d": True,
            "start_frame": 0, "duration_frames": total_frames,
            "style": {"font": FONT_CAPTION, "font_size": 54, "fill": CAPTION_COLOR},
        })

    camera = _camera(-1180.0)
    camera_samples = []
    for frame in range(total_frames):
        t = frame / max(total_frames - 1, 1)
        resolved = _camera(-1180.0 + 150.0 * t)      # slow push-in while panning
        resolved["position"] = [start_x + (end_x - start_x) * t, 0.0,
                                -1180.0 + 150.0 * t]
        camera_samples.append({"frame": frame, "camera": resolved})

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "archive_gallery_pan_v1",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": total_frames},
        "camera": camera,
        "camera_samples": camera_samples,
        "layers": layers,
        "output": {"path": "archive_gallery_pan_v1.mp4",
                   "format": "mp4", "codec": "h264"},
    }


def _yuv_glitch_frames(yuv: Path) -> list[int]:
    """Frame indices whose paper backdrop went dark (engine backdrop loss)."""
    try:
        from PIL import Image
    except ImportError:
        return []                      # cannot verify without Pillow
    scan = yuv.with_suffix(".scan")
    scan.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "rawvideo", "-pix_fmt", "yuv420p",
                    "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", str(yuv),
                    "-vf", "scale=480:270", str(scan / "f%05d.png")],
                   check=True, cwd=WORKSPACE)
    bad = []
    for index, path in enumerate(sorted(scan.glob("f*.png"))):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        corners = [im.getpixel((3, 3)), im.getpixel((w - 4, 3)),
                   im.getpixel((3, h - 4)), im.getpixel((w - 4, h - 4))]
        dark = sum(1 for c in corners if sum(c) < 200)
        if dark >= 3:
            bad.append(index)
    for path in scan.glob("*.png"):
        path.unlink()
    scan.rmdir()
    return bad


def _render_chunked(cli: Path, plan_path: Path, video: Path,
                    total_frames: int, chunk_frames: int,
                    max_attempts: int) -> None:
    """Render on the Vulkan path in bounded chunks, then encode with NVENC.

    Two engine defects shape this pipeline:
    - long single-session Vulkan exports die deterministically at
      session-relative frame ~127 (``FrameArena strict capacity exhausted``,
      the per-frame host arena shows cross-frame growth), so each session is
      capped well below that threshold;
    - the native NVENC *pipe* route drops the paper backdrop on ~10% of
      frames (intermittent surface-backdrop loss, see
      TICKET-RENDERPLAN-COORDINATE-AND-GPU-PARITY.md), while the verified
      stable GPU route is Vulkan rendering + ``--video-sink raw`` YUV420p
      readback (40/40 clean frames on a glitch-prone range). Chunks are
      therefore rendered to raw YUV and encoded by ``ffmpeg`` with
      ``h264_nvenc`` (the GPU still does the encode), then losslessly
      concatenated.

    Since the backdrop loss is nondeterministic (~1 frame per few hundred
    even on the raw route), every chunk is frame-scanned before encoding and
    re-rendered until clean (up to --max-attempts).
    """
    scratch = video.parent / (video.stem + "_chunks")
    scratch.mkdir(parents=True, exist_ok=True)
    parts = []
    for start in range(0, total_frames, chunk_frames):
        end = min(start + chunk_frames - 1, total_frames - 1)
        part = scratch / f"part_{start:05d}_{end:05d}.mp4"
        parts.append(part)
        if not part.is_file():
            for attempt in range(1, max_attempts + 1):
                yuv = part.with_suffix(".yuv")
                cmd = [str(cli), "render", "--backend", "vulkan",
                       "--plan", str(plan_path), "--assets-root", str(WORKSPACE),
                       "-o", str(yuv), "--video-sink", "raw",
                       "--pipe-pixfmt", "yuv420p",
                       "--start-frame", str(start), "--end-frame", str(end)]
                log = part.with_suffix(".log")
                print(f"[chunk] frames {start}-{end} attempt {attempt} "
                      f"-> {part.name}", flush=True)
                t0 = time.monotonic()
                subprocess.run(cmd, check=True, cwd=WORKSPACE,
                               stdout=open(log, "w"), stderr=subprocess.STDOUT)
                bad = _yuv_glitch_frames(yuv)
                if not bad:
                    break
                yuv.unlink()
                print(f"[chunk] backdrop loss on frames "
                      f"{[start + i for i in bad]}, re-rendering", flush=True)
            else:
                raise SystemExit(
                    f"chunk {start}-{end} stayed glitchy after "
                    f"{max_attempts} attempts")
            encode = ["ffmpeg", "-y", "-v", "error",
                      "-f", "rawvideo", "-pix_fmt", "yuv420p",
                      "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
                      "-i", str(yuv), "-c:v", "h264_nvenc", str(part)]
            subprocess.run(encode, check=True, cwd=WORKSPACE)
            yuv.unlink()
            print(f"[chunk] {end - start + 1} frames in "
                  f"{time.monotonic() - t0:.1f}s", flush=True)

    listing = scratch / "concat.txt"
    listing.write_text("\n".join(
        f"file '{part.resolve().as_posix()}'" for part in parts) + "\n",
        encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
           "-i", str(listing), "-c", "copy", str(video)]
    if shutil.which("ffmpeg"):
        subprocess.run(cmd, check=True, cwd=WORKSPACE)
        for part in parts:
            part.unlink()
        listing.unlink()
    else:
        shutil.copy(str(parts[0]), str(video))
        print("ffmpeg not on PATH: kept chunk MP4s in", scratch)


def _default_cli() -> Path:
    override = os.environ.get("CHRONON_CLI")
    if override:
        return Path(override)
    suffix = ".exe" if sys.platform.startswith("win") else ""
    build = WORKSPACE / "Chronon3d/build/chronon"
    candidates = sorted(build.glob(f"*/apps/chronon3d_cli/chronon3d_cli{suffix}"))
    if not candidates:
        raise SystemExit(
            f"chronon3d CLI not found under {build}; set CHRONON_CLI")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true",
                        help="validate and render with the Chronon3D CLI")
    parser.add_argument("--backend", choices=("software", "vulkan"),
                        default="vulkan", help="Chronon3D render backend")
    parser.add_argument("--frames-per-photo", type=int, default=56,
                        help="camera dwell per photo, frames at 30 fps")
    parser.add_argument("--out", type=Path, default=ROOT / "out/archive_gallery_pan_v1")
    parser.add_argument("--chunk", type=int, default=80,
                        help="frames per Vulkan export session (chunked concat; "
                             "large sessions exhaust the engine frame arena)")
    parser.add_argument("--max-attempts", type=int, default=5,
                        help="re-render retries for a glitchy chunk")
    parser.add_argument("--cli", type=Path, default=None)
    parser.add_argument("--images", nargs="+", metavar="PATH[:CAPTION]",
                        help="override the default archive photo set")
    args = parser.parse_args()
    args.out = args.out.resolve()
    cli: Path | None
    if args.render:
        cli = (args.cli or _default_cli()).resolve()
    else:
        cli = args.cli

    images = []
    if args.images:
        for token in args.images:
            path, _, caption = token.partition(":")
            images.append((path, caption or Path(path).stem))
    else:
        images = [list(item) for item in DEFAULT_IMAGES]

    plan = build_plan(images, args.frames_per_photo)
    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / "archive_gallery_pan_v1.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {plan_path}")
    if not args.render:
        return 0
    if args.render:
        if not cli or not cli.is_file():
            raise SystemExit(f"Chronon3D CLI not found: {cli}")

    subprocess.run([str(cli), "validate", "--plan", str(plan_path),
                    "--assets-root", str(WORKSPACE), "--profile", "preview"],
                   check=True, cwd=WORKSPACE)
    video = args.out / "archive_gallery_pan_v1.mp4"
    total = plan["canvas"]["duration_frames"]
    if args.backend == "vulkan":
        _render_chunked(cli, plan_path, video, total, args.chunk,
                        args.max_attempts)
    else:
        subprocess.run([str(cli), "render", "--backend", args.backend,
                        "--plan", str(plan_path), "--assets-root", str(WORKSPACE),
                        "-o", str(video), "--codec", "h264",
                        "--ffmpeg-mode", "pipe", "--encode-preset", "fast"],
                       check=True, cwd=WORKSPACE)
    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_read_frames", "-of", "json", str(video)],
        text=True)
    stream = json.loads(probe)["streams"][0]
    expected = plan["canvas"]["duration_frames"]
    if (stream.get("width"), stream.get("height"),
            int(stream.get("nb_read_frames", 0))) != (WIDTH, HEIGHT, expected):
        raise SystemExit(f"render metadata mismatch: {stream}")
    print(f"Rendered {video} ({stream['width']}x{stream['height']}, {expected} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
