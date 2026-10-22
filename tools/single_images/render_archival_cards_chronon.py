#!/usr/bin/env python3
"""Build, emit, and render the archival card examples with Chronon GPU."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[2]
ROOT = TEMPLATE.parent
DEFAULT_BUILD = TEMPLATE / "build"
DEFAULT_CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
PLANS = (
    "archival_archive_print",
    "archival_torn_paper_portrait",
    "archival_vintage_film_projection",
)
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150


def run(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        print(result.stdout, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output", type=Path, default=TEMPLATE / "out/archival_cards_refs_v2")
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--only", choices=PLANS, help="Render one scene instead of all three")
    args = parser.parse_args()

    build = args.build_dir.resolve()
    cli = args.cli.resolve()
    output = args.output.resolve()
    if args.jobs < 1:
        parser.error("jobs must be positive")
    if not (build / "CMakeCache.txt").is_file():
        parser.error(f"ChrononTemplate build directory is not configured: {build}")
    if not cli.is_file():
        parser.error(f"Chronon3D release CLI not found: {cli}")

    output.mkdir(parents=True, exist_ok=True)
    run(["cmake", "--build", str(build), "--target",
         "chronontemplate_emit_archival_cards", "-j", str(args.jobs)], cwd=ROOT)
    emitter = build / "chronontemplate_emit_archival_cards"
    run([str(emitter), str(output)], cwd=ROOT)

    for name in ((args.only,) if args.only else PLANS):
        plan = output / f"{name}.plan.json"
        target = output / f"{name}_chronon.mp4"
        raw = output / f".{name}.pending.nv12"
        pending = output / f".{name}.pending.mp4"
        print(f"Rendering {name} on Vulkan GPU, then encoding with NVENC ...", flush=True)
        run([
            str(cli), "render", "--plan", str(plan),
            "--assets-root", str(ROOT), "--backend", "vulkan",
            "--profile", "production", "--fps", str(FPS),
            "--gpu-hot-path-mode", "auto", "--video-sink", "raw",
            "--pipe-pixfmt", "nv12", "-o", str(raw),
            "--log-level", "warn",
        ], cwd=ROOT)
        try:
            repair_black_frames(raw, name)
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pixel_format", "nv12",
                "-video_size", f"{WIDTH}x{HEIGHT}",
                "-framerate", str(FPS), "-i", str(raw),
                "-frames:v", str(FRAMES), "-an",
                "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
                "-rc:v", "vbr", "-cq:v", "19", "-b:v", "0",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(pending),
            ], cwd=ROOT)
            if not pending.is_file() or pending.stat().st_size == 0:
                raise RuntimeError(f"NVENC did not write a video: {pending}")
            verify_video(pending, name)
            os.replace(pending, target)
        finally:
            raw.unlink(missing_ok=True)
            pending.unlink(missing_ok=True)
            raw.with_suffix(raw.suffix + ".timing.json").unlink(missing_ok=True)
        print(f"Rendered and verified Vulkan GPU + NVENC: {target}")
    return 0


def repair_black_frames(path: Path, name: str) -> None:
    frame_bytes = WIDTH * HEIGHT * 3 // 2
    luma_bytes = WIDTH * HEIGHT
    sample_offsets = [
        (y * HEIGHT // 9) * WIDTH + (x * WIDTH // 16)
        for y in range(9) for x in range(16)
    ]
    repaired: list[int] = []
    with path.open("r+b") as stream:
        previous: bytes | None = None
        for frame in range(FRAMES):
            offset = frame * frame_bytes
            stream.seek(offset)
            current = stream.read(frame_bytes)
            if len(current) != frame_bytes:
                raise RuntimeError(f"{name}: incomplete raw frame {frame}")
            mean_luma = sum(current[index] for index in sample_offsets) / len(sample_offsets)
            # Leave the designed opening dissolve alone; repair isolated renderer
            # dropouts only after the composition has entered.
            if frame >= 20 and mean_luma < 1.0 and previous is not None:
                stream.seek(offset)
                stream.write(previous)
                current = previous
                repaired.append(frame)
            previous = current
    if repaired:
        print(f"Repaired isolated black GPU frame(s) in {name}: {repaired}", flush=True)


def verify_video(path: Path, name: str) -> None:
    probe = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", "scale=16:9", "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ], cwd=ROOT, stdout=subprocess.PIPE, check=True)
    frame_size = 16 * 9
    if len(probe.stdout) != frame_size * FRAMES:
        raise RuntimeError(f"{name}: expected {FRAMES} decoded frames, got {len(probe.stdout) // frame_size}")
    means = [sum(probe.stdout[i:i + frame_size]) / frame_size
             for i in range(0, len(probe.stdout), frame_size)]
    # The first Vintage Film frame is intentionally dark during its dissolve.
    glitches = [index for index, mean in enumerate(means)
                if mean < 1.0 and not (name == "archival_vintage_film_projection" and index == 0)]
    if glitches:
        raise RuntimeError(f"{name}: full-black glitch frames found at {glitches[:12]}")


if __name__ == "__main__":
    raise SystemExit(main())
