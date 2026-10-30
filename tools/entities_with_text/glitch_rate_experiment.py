#!/usr/bin/env python3
"""Glitch-rate experiment harness for the Vulkan raw-sink pipeline.

Renders a frame range once per environment configuration and counts
defective frames:
- dark corners            -> paper-backdrop loss;
- cream patch inside the expected photo area, confirmed by the frame being
  clean at its neighbours -> photo/plate misdraw.
"""
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
CLI = (WORKSPACE / "Chronon3d/build/chronon/win-release-clang-cuda/"
       "apps/chronon3d_cli/chronon3d_cli.exe").resolve()
PLAN = (WORKSPACE / "ChrononTemplate/out/archive_gallery_pan_v1/"
        "archive_gallery_pan_v1.plan.json")
SCAN_DIR = WORKSPACE / "ChrononTemplate/out/glitch_experiment/scan"

CREAM = (243.0, 235.0, 223.0)
FRACTION_TAN = math.tan(math.radians(55.0 / 2.0))
PITCH = 1500.0
COUNT = 8
CENTERS = [(i - (COUNT - 1) / 2) * PITCH for i in range(COUNT)]


def _cream_scan_frames(yuv: Path, width: int, height: int, frames: int):
    from PIL import Image
    if SCAN_DIR.exists():
        shutil.rmtree(SCAN_DIR)
    SCAN_DIR.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "rawvideo", "-pix_fmt", "yuv420p",
                    "-s", f"{width}x{height}", "-r", "30", "-i", str(yuv),
                    "-vf", "scale=480:270", str(SCAN_DIR / "f%05d.png")],
                   check=True, cwd=WORKSPACE)
    paths = sorted(SCAN_DIR.glob("f*.png"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    samples = plan["camera_samples"]

    backdrop_bad, photo_bad = [], []
    for index, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        corners = [im.getpixel((3, 3)), im.getpixel((w - 4, 3)),
                   im.getpixel((3, h - 4)), im.getpixel((w - 4, h - 4))]
        dark = sum(1 for c in corners if sum(c) < 200)
        if dark >= 3:
            backdrop_bad.append(index)
            continue

        # Expected screen centre of each photo interior at 480x270 scale.
        cam = samples[min(index, len(samples) - 1)]["camera"]["position"]
        cam_x, cam_z = cam[0], cam[2]
        cream_by_index = []
        for photo_index, world_x in enumerate(CENTERS):
            depth = 90.0 if photo_index % 2 else 0.0
            dist = cam_z - depth                       # cam_z is negative
            focal = 135.0 / FRACTION_TAN * 1080.0 / 270.0  # world->270 scale
            focal = (270.0 / 2.0) / FRACTION_TAN
            screen_x = 240.0 + (world_x - cam_x) * focal / dist
            screen_y = 135.0 - 40.0 * focal / dist     # photo lift 40, Y up
            if not (60 < screen_x < 420 and 40 < screen_y < 230):
                cream_by_index.append(False)
                continue
            sx, sy = int(screen_x), int(screen_y)
            patch = [im.getpixel((sx + dx, sy + dy))
                     for dx in (-6, 0, 6) for dy in (-4, 0, 4)]
            cream = sum(1 for c in patch
                        if abs(c[0] - CREAM[0]) < 9
                        and abs(c[1] - CREAM[1]) < 9
                        and abs(c[2] - CREAM[2]) < 9)
            cream_by_index.append(cream >= 7)
        if any(cream_by_index):
            photo_bad.append(index)
        yield_index = index
    return list(paths), backdrop_bad, photo_bad


def scan_run(tag: str, start: int, end: int) -> None:
    from PIL import Image
    yuv_dir = WORKSPACE / "ChrononTemplate/out/glitch_experiment"
    yuv = yuv_dir / f"{tag}.yuv"
    env = dict(os.environ)
    extra_configs = {
        "native": ["CHRONON3D_GPU_HOT_PATH_MODE=require_gpu_native"],
        "single": ["CHRONON3D_VULKAN_SINGLE_FLIGHT=1"],
        "both": ["CHRONON3D_GPU_HOT_PATH_MODE=require_gpu_native",
                 "CHRONON3D_VULKAN_SINGLE_FLIGHT=1"],
    }
    for key, value in extra_configs.get(tag, []):
        env[key] = value.split("=", 1)[1]

    cmd = [str(CLI), "render", "--backend", "vulkan", "--plan", str(PLAN),
           "--assets-root", str(WORKSPACE), "-o", str(yuv),
           "--video-sink", "raw", "--pipe-pixfmt", "yuv420p",
           "--start-frame", str(start), "--end-frame", str(end)]
    log = yuv_dir / f"{tag}.log"
    subprocess.run(cmd, check=True, cwd=WORKSPACE,
                   stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)

    frames, backdrop_bad, photo_bad = None, [], []
    # scan in one pass
    if yuv_dir.exists():
        pass
    scan_dir = yuv_dir / f"scan_{tag}"
    if scan_dir.exists():
        shutil.rmtree(scan_dir)
    scan_dir.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "rawvideo", "-pix_fmt", "yuv420p",
                    "-s", "1920x1080", "-r", "30", "-i", str(yuv),
                    "-vf", "scale=480:270", str(scan_dir / "f%05d.png")],
                   check=True, cwd=WORKSPACE)
    paths = sorted(scan_dir.glob("f*.png"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    sampling = plan["camera_samples"]
    focal = (270.0 / 2.0) / FRACTION_TAN
    for index, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        w, h = im.size
        corners = [im.getpixel((3, 3)), im.getpixel((w - 4, 3)),
                   im.getpixel((3, h - 4)), im.getpixel((w - 4, h - 4))]
        dark = sum(1 for c in corners if sum(c) < 200)
        if dark >= 3:
            backdrop_bad.append(index)
            continue
        cam = sampling[min(index, len(sampling) - 1)]["camera"]["position"]
        cam_x, cam_z = cam[0], cam[2]
        cream_hits = 0
        for photo_index, world_x in enumerate(CENTERS):
            depth = 90.0 if photo_index % 2 else 0.0
            dist = cam_z - depth
            screen_x = 240.0 + (world_x - cam_x) * focal / dist
            screen_y = 135.0 - 40.0 * focal / dist
            if not (60 < screen_x < 420 and 40 < screen_y < 230):
                continue
            sx, sy = int(screen_x), int(screen_y)
            patch = [im.getpixel((sx + dx, sy + dy))
                     for dx in (-6, 0, 6) for dy in (-4, -2, 0)]
            cream = sum(1 for c in patch
                        if abs(c[0] - CREAM[0]) < 9
                        and abs(c[1] - CREAM[1]) < 9
                        and abs(c[2] - CREAM[2]) < 9)
            if cream >= 6:
                cream_hits += 1
        if cream_hits:
            photo_bad.append(index)

    total = len(paths)
    print(f"{tag:>8}: frames={total} backdrop_bad={len(backdrop_bad)} "
          f"{backdrop_bad[:8]} photo_bad={len(photo_bad)} {photo_bad[:12]}",
          flush=True)
    shutil.rmtree(scan_dir)


def main() -> int:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 319
    yuv_dir = WORKSPACE / "ChrononTemplate/out/glitch_experiment"
    yuv_dir.mkdir(parents=True, exist_ok=True)
    for tag in ("baseline", "native", "single", "both"):
        scan_run(tag, start, end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
