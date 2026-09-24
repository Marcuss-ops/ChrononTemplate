#!/usr/bin/env python3
"""Visual gate for the native ChrononTemplate phrase pack.

This command is intentionally local-only.  It never uploads, deletes or
mutates Drive.  It checks the rendered MP4s against the C++-emitted style
contract and writes contact sheets/report data for human approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


SAMPLE_FRAMES = (0, 24, 60, 111, 119)
VISIBLE_FRAMES = (24, 60, 111)
WIDTH = 1920
HEIGHT = 1080
FPS = "24/1"
EXPECTED_FRAMES = 120


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True)


def ffprobe(path: Path) -> dict[str, Any]:
    data = json.loads(
        run(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=size,duration:stream=codec_name,width,height,avg_frame_rate,nb_frames",
            "-select_streams",
            "v:0",
            "-of",
            "json",
            str(path),
        )
    )
    stream = data.get("streams", [{}])[0]
    return {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": stream.get("avg_frame_rate"),
        "frames": int(stream.get("nb_frames", 0)),
        "bytes": int(float(data.get("format", {}).get("size", 0))),
        "duration": float(data.get("format", {}).get("duration", 0)),
    }


def extract_frame(video: Path, frame: int, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            f"select=eq(n\\,{frame})",
            "-frames:v",
            "1",
            str(destination),
        ],
        check=True,
    )


def frame_hash(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def foreground_bbox(path: Path) -> list[int] | None:
    with Image.open(path).convert("RGB") as image:
        # Bbox is a visual gate, not a pixel-perfect compositor test. Scan a
        # bounded proxy and map the result back to the source coordinates so
        # the full 1080p pack remains quick to audit.
        max_width = 480
        scale = min(1.0, max_width / image.width)
        probe = image if scale == 1.0 else image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.BILINEAR,
        )
        pixels = probe.load()
        background = pixels[0, 0]
        points: list[tuple[int, int]] = []
        for y in range(probe.height):
            for x in range(probe.width):
                r, g, b = pixels[x, y]
                if (
                    abs(r - background[0])
                    + abs(g - background[1])
                    + abs(b - background[2])
                    > 42
                ):
                    points.append((x, y))
        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return [
            round(min(xs) / scale),
            round(min(ys) / scale),
            round((max(xs) + 1) / scale),
            round((max(ys) + 1) / scale),
        ]


def make_contact_sheet(frames: list[tuple[int, Path]], destination: Path) -> None:
    tile_size = (320, 180)
    label_height = 24
    sheet = Image.new("RGB", (tile_size[0] * len(frames), tile_size[1] + label_height), "#111827")
    draw = ImageDraw.Draw(sheet)
    for column, (frame, path) in enumerate(frames):
        with Image.open(path).convert("RGB") as image:
            image.thumbnail(tile_size)
            x = column * tile_size[0] + (tile_size[0] - image.width) // 2
            y = label_height + (tile_size[1] - image.height) // 2
            sheet.paste(image, (x, y))
        draw.text((column * tile_size[0] + 8, 5), f"frame {frame}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)


def style_projection(plan: dict[str, Any]) -> dict[str, Any]:
    layer = next(layer for layer in plan["layers"] if layer.get("id") == "phrase")
    return {
        "font": layer["style"]["font"],
        "font_size": layer["style"]["font_size"],
        "box": layer["size"],
        "position": layer["position"],
        "background": next(layer for layer in plan["layers"] if layer.get("id") == "background")["color"],
        "fill": layer["style"]["fill"],
        "stroke": layer["style"]["stroke"],
        "glow": layer["style"]["glow"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--style-catalog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--contact-sheets", type=Path, required=True)
    args = parser.parse_args()

    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise SystemExit("verify gate requires ffprobe and ffmpeg")

    emitted = json.loads(args.style_catalog.read_text())
    expected_style = emitted["native_phrase_style"]
    videos = sorted(args.pack.glob("*.mp4"))
    if not videos:
        raise SystemExit(f"no MP4 files in {args.pack}")

    failures: list[str] = []
    clips: list[dict[str, Any]] = []
    for video in videos:
        clip_failures: list[str] = []
        meta = ffprobe(video)
        if (meta["width"], meta["height"], meta["fps"], meta["frames"]) != (
            WIDTH,
            HEIGHT,
            FPS,
            EXPECTED_FRAMES,
        ):
            clip_failures.append(f"invalid video metadata: {meta}")
        plan_path = args.plans / f"{video.stem}.plan.json"
        if not plan_path.exists():
            clip_failures.append("missing matching render plan")
            plan = None
        else:
            plan = json.loads(plan_path.read_text())
            projected = style_projection(plan)
            if projected != expected_style:
                clip_failures.append("plan style differs from native_phrase_style")
            if "#00C8FF" in plan_path.read_text().upper():
                clip_failures.append("cyan glow found in render plan")

        frame_dir = args.contact_sheets / video.stem
        frame_dir.mkdir(parents=True, exist_ok=True)
        frames: list[tuple[int, Path]] = []
        hashes: dict[str, str] = {}
        bboxes: dict[str, list[int] | None] = {}
        for frame in SAMPLE_FRAMES:
            path = frame_dir / f"frame-{frame:03d}.png"
            extract_frame(video, frame, path)
            frames.append((frame, path))
            hashes[str(frame)] = frame_hash(path)
            bboxes[str(frame)] = foreground_bbox(path)

        if len({hashes[str(frame)] for frame in SAMPLE_FRAMES}) < 3:
            clip_failures.append("sampled frames are effectively static")
        for left, right in zip(SAMPLE_FRAMES, SAMPLE_FRAMES[1:]):
            if hashes[str(left)] == hashes[str(right)]:
                clip_failures.append(f"expected motion missing: frame {left} == frame {right}")

        position = expected_style["position"]
        box = expected_style["box"]
        for frame in VISIBLE_FRAMES:
            bbox = bboxes[str(frame)]
            if bbox is None:
                clip_failures.append(f"no visible text foreground at frame {frame}")
                continue
            x0, y0, x1, y1 = bbox
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0
            if abs(center_x - position[0]) > box[0] * 0.35 or abs(center_y - position[1]) > box[1] * 0.55:
                clip_failures.append(f"bbox center outside style box at frame {frame}: {bbox}")
            if x0 < 0 or y0 < 0 or x1 > WIDTH or y1 > HEIGHT:
                clip_failures.append(f"text clipped at frame {frame}: {bbox}")

        contact_sheet = args.contact_sheets / f"{video.stem}-contact.png"
        make_contact_sheet(frames, contact_sheet)
        failures.extend(f"{video.name}: {failure}" for failure in clip_failures)
        clips.append(
            {
                "name": video.name,
                "metadata": meta,
                "sample_frames": list(SAMPLE_FRAMES),
                "hashes": hashes,
                "bboxes": bboxes,
                "contact_sheet": str(contact_sheet),
                "failures": clip_failures,
            }
        )

    report = {
        "gate": "native-phrase-visual-v1",
        "upload_allowed": not failures,
        "style_source": str(args.style_catalog),
        "expected_style": expected_style,
        "clips": clips,
        "failures": failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"upload_allowed": not failures, "clips": len(clips), "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
