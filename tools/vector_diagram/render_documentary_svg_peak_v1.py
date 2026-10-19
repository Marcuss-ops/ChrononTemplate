#!/usr/bin/env python3
"""Render an imported-SVG documentary graph animation with Chronon3D."""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from documentary_svg_peak_registry import build_plan, load_preset

ROOT = Path(__file__).resolve().parents[2]


def plan(preset: dict | None = None) -> dict:
    return build_plan(preset)


def run(args: list[str]) -> None:
    subprocess.run([str(x) for x in args], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=Path(os.environ.get("CHRONON_CLI", "")))
    parser.add_argument("--preset", default="documentary_svg_peak_v1",
                        help="preset id from the documentary SVG scene catalog")
    parser.add_argument("--keep-raw", action="store_true",
                        help="retain the full RGBA render for forensic inspection")
    args = parser.parse_args()
    if not args.cli.is_file():
        parser.error("pass --cli or set CHRONON_CLI to an SVG-enabled chronon3d_cli")
    preset = load_preset(args.preset)
    render_plan = plan(preset)
    width = render_plan["canvas"]["width"]
    height = render_plan["canvas"]["height"]
    fps = render_plan["canvas"]["fps_num"]
    frames = render_plan["canvas"]["duration_frames"]
    trim_start = int(preset["trim"]["start_frame"])
    trim_end = int(preset["trim"]["end_frame"])
    marker_start = int(preset["marker"]["start_frame"])
    marker_end = int(preset["marker"]["end_frame"])
    out = ROOT / "artifacts" / args.preset
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / f"{args.preset}.plan.json"
    svg_source = (ROOT / preset["asset"]).resolve()
    plan_path.write_text(json.dumps(render_plan, indent=2) + "\n")
    (out / Path(preset["asset"]).name).write_bytes(svg_source.read_bytes())
    raw = out / f"{args.preset}.rgba"
    run([args.cli, "validate", "--plan", plan_path, "--assets-root", out])
    run([args.cli, "render", "--plan", plan_path,
         "--assets-root", out, "--backend", "software", "--video-sink", "raw",
         "--pipe-pixfmt", "rgba", "--fps", fps, "--start-frame", 0,
         "--end-frame", frames-1, "--log-level", "warn", "--output", raw])
    frame_bytes = width * height * 4
    raw_data = raw.read_bytes()
    if len(raw_data) != frame_bytes * frames:
        raise RuntimeError(f"expected {frames} full frames, got {len(raw_data)//frame_bytes}")
    with tempfile.TemporaryDirectory(prefix=f"{args.preset}_repeat_") as temp_dir:
        repeated_raw = Path(temp_dir) / "repeat.rgba"
        run([args.cli, "render", "--plan", plan_path,
             "--assets-root", out, "--backend", "software", "--video-sink", "raw",
             "--pipe-pixfmt", "rgba", "--fps", fps, "--start-frame", 0,
             "--end-frame", frames-1, "--log-level", "warn", "--output", repeated_raw])
        if not filecmp.cmp(raw, repeated_raw, shallow=False):
            raise RuntimeError("repeated 150-frame SVG graph renders differ pixel-for-pixel")
    print(f"SVG-08 full-plan repeat: PASS ({frames} raw RGBA frames match exactly)")
    white_counts = []
    yellow_centroids = []
    check_frames = tuple(sorted(set((0, trim_start,
        (trim_start + trim_end) // 2, trim_end, marker_start,
        marker_end, frames - 1))))
    for frame_index in check_frames:
        frame = raw_data[frame_index * frame_bytes:(frame_index + 1) * frame_bytes]
        white = yellow = sx = sy = 0
        for offset in range(0, len(frame), 4):
            red, green, blue, alpha = frame[offset:offset + 4]
            pixel = offset // 4
            x, y = pixel % width, pixel // width
            if red > 200 and green > 200 and blue > 205 and alpha > 128:
                white += 1
            if red > 225 and green > 160 and blue < 100 and alpha > 160:
                yellow += 1
                sx += x
                sy += y
        white_counts.append(white)
        if frame_index >= marker_start:
            if not yellow:
                raise RuntimeError(f"moving yellow marker missing at frame {frame_index}")
            yellow_centroids.append((frame_index, sx / yellow, sy / yellow))
    trim_start_index = check_frames.index(trim_start)
    if white_counts[trim_start_index] != 0 or max(white_counts) < 1000:
        raise RuntimeError(f"SVG Trim Paths visibility/reveal failed: {white_counts}")
    if white_counts[-1] < 1000:
        raise RuntimeError(f"SVG pixels disappeared after the marker moved: {white_counts}")
    if len({(round(x), round(y)) for _, x, y in yellow_centroids}) < 4:
        raise RuntimeError(f"yellow marker did not travel through the graph: {yellow_centroids}")
    video_path = out / f"{args.preset}.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
         "-pixel_format", "rgba", "-video_size", f"{width}x{height}", "-framerate", fps,
         "-i", raw, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         video_path])
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)
    sample_frames = tuple(sorted(set((0, min(45, frames-1), min(90, frames-1), frames-1))))
    contact = Image.new("RGB", (width, height * len(sample_frames)), "#101216")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(contact)
    for row, frame_index in enumerate(sample_frames):
        png = frames_dir / f"frame_{frame_index:03d}.png"
        Image.frombytes("RGBA", (width, height),
                        raw_data[frame_index*frame_bytes:(frame_index+1)*frame_bytes]).save(png)
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i",
             video_path, "-vf",
             f"select='eq(n,{frame_index})'", "-frames:v", 1, "-update", 1,
             frames_dir / f"encoded_{frame_index:03d}.png"])
        image = Image.open(frames_dir / f"encoded_{frame_index:03d}.png").convert("RGB")
        contact.paste(image, (0, height * row))
        draw.rectangle((0, height*row, 145, height*row+28), fill="#101216")
        draw.text((10, height*row+6), f"frame {frame_index}", fill="#E8EBF0")
    contact.save(out / "contact_sheet.png")
    if not args.keep_raw:
        raw.unlink()
    Path(str(raw) + ".timing.json").unlink(missing_ok=True)
    print(f"SVG path white pixels at {check_frames}: {white_counts}")
    print(f"Rendered {video_path} ({width}x{height}, {fps} fps, {frames/fps:.1f}s)")
    print(f"Contact sheet: {out / 'contact_sheet.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
