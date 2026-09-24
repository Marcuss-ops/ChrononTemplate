#!/usr/bin/env python3
"""Verify software-rendered image_25d_clean_v1 matrix clips and emit evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def probe_video(path: Path) -> tuple[dict, float]:
    result = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]))
    return result["streams"][0], float(result["format"]["duration"])


def read_frame(video: Path, frame: int, output: Path) -> np.ndarray:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(video),
        "-vf", f"select='eq(n\\,{frame})'", "-vsync", "0",
        "-frames:v", "1", str(output),
    ], check=True)
    return np.asarray(Image.open(output).convert("RGB"), dtype=np.int32)


def verify(video: Path, frames_dir: Path) -> tuple[dict, Image.Image]:
    stream, duration = probe_video(video)
    expected = (1920, 1080, "30/1", "150")
    actual = (stream["width"], stream["height"], stream["r_frame_rate"], stream["nb_frames"])
    if actual != expected or abs(duration - 5.0) > 0.02:
        raise AssertionError(f"{video.name}: expected 1920x1080, 30 fps, 150 frames, 5s; got {actual}, {duration}s")

    mid = read_frame(video, 75, frames_dir / f"{video.stem}_mid.png")
    first = read_frame(video, 0, frames_dir / f"{video.stem}_f0.png")
    frame30 = read_frame(video, 30, frames_dir / f"{video.stem}_f30.png")
    background = mid[5, 5]
    distance = np.sqrt(np.sum((mid - background) ** 2, axis=2))
    ys, xs = np.where(distance > 35)
    if not len(xs):
        raise AssertionError(f"{video.name}: no visible pixels differ from the background")
    ink_pct = 100.0 * len(xs) / (1920 * 1080)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    diff_pct = 100.0 * np.count_nonzero(np.sum(np.abs(first - frame30), axis=2) > 30) / (1920 * 1080)
    if not 15.0 <= ink_pct <= 45.0:
        raise AssertionError(f"{video.name}: visible-pixel coverage {ink_pct:.2f}% is outside [15,45]")
    if abs(center[0] - 960) > 40 or abs(center[1] - 540) > 40:
        raise AssertionError(f"{video.name}: visible bounds center {center} is outside 40px tolerance")
    if diff_pct <= 0.1:
        raise AssertionError(f"{video.name}: frame 0 vs 30 pixel difference {diff_pct:.3f}% is too small")

    record = {
        "file": video.name,
        "duration_s": duration,
        "width": stream["width"],
        "height": stream["height"],
        "fps": stream["r_frame_rate"],
        "frames": int(stream["nb_frames"]),
        "ink_pct": round(float(ink_pct), 2),
        "bbox": bbox,
        "center": [round(center[0]), round(center[1])],
        "frame0_vs_30_diff_pct": round(float(diff_pct), 3),
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
    }
    thumb = Image.open(frames_dir / f"{video.stem}_mid.png").convert("RGB")
    thumb.thumbnail((480, 270))
    return record, thumb.copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix_dir", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1] / "out/image_25d_clean_v1/verify_matrix_v2")
    args = parser.parse_args()
    matrix_dir = args.matrix_dir.resolve()
    videos = sorted(matrix_dir.glob("*.mp4"))
    if len(videos) != 24:
        raise AssertionError(f"expected 24 matrix videos, found {len(videos)} in {matrix_dir}")
    frames_dir = matrix_dir / "frames"
    records, thumbnails = [], []
    blur_thumbnails = []
    for video in videos:
        record, thumbnail = verify(video, frames_dir)
        records.append(record)
        thumbnails.append((video.stem, thumbnail))
        if video.stem.startswith("image_25d_blur_"):
            blur_frame = read_frame(video, 8, frames_dir / f"{video.stem}_blur8.png")
            blur_thumb = Image.fromarray(blur_frame.astype(np.uint8))
            blur_thumb.thumbnail((480, 270))
            blur_thumbnails.append((video.stem, blur_thumb.copy()))
        print(f"verified {video.name}: ink={record['ink_pct']:.2f}%, center={record['center']}, diff={record['frame0_vs_30_diff_pct']:.3f}%")

    sheet = Image.new("RGB", (1440, 2400), (17, 21, 31))
    draw = ImageDraw.Draw(sheet)
    for index, (name, thumbnail) in enumerate(thumbnails):
        x, y = index % 3 * 480, index // 3 * 300
        sheet.paste(thumbnail, (x, y + 24))
        draw.text((x + 8, y + 5), name, fill="white")
    sheet.save(matrix_dir / "contact_sheet.png")
    blur_sheet = Image.new("RGB", (1440, 600), (17, 21, 31))
    blur_draw = ImageDraw.Draw(blur_sheet)
    for index, (name, thumbnail) in enumerate(blur_thumbnails):
        x, y = index % 3 * 480, index // 3 * 300
        blur_sheet.paste(thumbnail, (x, y + 24))
        blur_draw.text((x + 8, y + 5), f"frame 8 · {name}", fill="white")
    blur_sheet.save(matrix_dir / "blur_entrance_contact_sheet.png")
    (matrix_dir / "manifest_sha256.json").write_text(json.dumps(records, indent=2) + "\n")
    ink = [record["ink_pct"] for record in records]
    print(f"PASS: {len(records)} clips; ink range {min(ink):.2f}–{max(ink):.2f}%; contact sheet and SHA manifest written to {matrix_dir}")


if __name__ == "__main__":
    main()
