#!/usr/bin/env python3
"""Render typewriter previews using the renderer's raw sink plus local FFmpeg."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
OUT = ROOT / "out/typewriter_modern_v1"
CLI = PROJECT / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
IDS = [
    "01_monospace_block_cursor", "02_kinetic_scramble", "03_soft_opacity_ramp",
    "04_character_bounce", "05_backspace_correction", "06_glow_beam_sweep",
    "07_word_snap", "08_mechanical_y_shift", "09_highlighter_expansion",
    "10_weight_ramp", "11_dynamic_auto_wrap", "12_glitch_pop",
    "13_elastic_leading_cursor", "14_focal_blur_dissolve", "15_paper_punch_stencil",
]


def run(cmd: list[str], log: Path) -> None:
    with log.open("w") as stream:
        proc = subprocess.run(cmd, cwd=PROJECT, stdout=stream, stderr=subprocess.STDOUT)
    if proc.returncode:
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-10:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{tail}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for ident in IDS:
        plan = OUT / f"{ident}.plan.json"
        raw = OUT / f".{ident}.rgba"
        temp_mp4 = OUT / f".{ident}.partial.mp4"
        target = OUT / f"{ident}.mp4"
        print(f"RENDER {ident}", flush=True)
        try:
            run([str(CLI), "render", "--plan", str(plan), "--output", str(raw),
                 "--assets-root", str(PROJECT / "Chronon3d"), "--backend", "vulkan",
                 "--hardware", "none", "--fps", "30", "--profile", "preview",
                 "--video-sink", "raw"], OUT / "logs" / f"{ident}.final-raw-render.log")
            expected_bytes = 1920 * 1080 * 4 * 150
            if not raw.exists() or raw.stat().st_size != expected_bytes:
                raise RuntimeError(f"raw output size incorrect: {raw.stat().st_size if raw.exists() else 'missing'}; expected {expected_bytes}")
            run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgba",
                 "-video_size", "1920x1080", "-framerate", "30", "-i", str(raw),
                 "-frames:v", "150", "-an", "-c:v", "libx264", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp_mp4)],
                OUT / "logs" / f"{ident}.final-ffmpeg-encode.log")
            temp_mp4.replace(target)
            print(f"PASS {ident} bytes={target.stat().st_size}", flush=True)
        except Exception as exc:
            print(f"FAIL {ident}: {exc}", file=sys.stderr, flush=True)
            return 1
        finally:
            raw.unlink(missing_ok=True)
    print("ALL_FINAL_RENDERS_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
