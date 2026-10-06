#!/usr/bin/env python3
"""Verify rendered multi_image_duo_v1 videos and write a compact evidence manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

PRESET_IDS = (
    "duo_split_reveal",
    "duo_depth_stagger",
    "duo_cross_focus",
    "duo_parallax_balance",
    "duo_compare_hold",
)
WIDTH, HEIGHT, FPS, FRAMES, DURATION = 1920, 1080, "30/1", 150, 5.0


def probe_video(path: Path) -> tuple[dict, float]:
    result = json.loads(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                "-show_entries", "format=duration", "-of", "json", str(path),
            ],
            text=True,
        )
    )
    return result["streams"][0], float(result["format"]["duration"])


def read_frame(video: Path, frame: int, output: Path) -> np.ndarray:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(video),
            "-vf", f"select='eq(n\\,{frame})'", "-vsync", "0",
            "-frames:v", "1", str(output),
        ],
        check=True,
    )
    return np.asarray(Image.open(output).convert("RGB"), dtype=np.int16)


def verify_video(path: Path, frames_dir: Path) -> dict:
    stream, duration = probe_video(path)
    actual = (
        int(stream["width"]), int(stream["height"]), stream["r_frame_rate"], int(stream["nb_frames"])
    )
    expected = (WIDTH, HEIGHT, FPS, FRAMES)
    if actual != expected or abs(duration - DURATION) > 0.02:
        raise AssertionError(f"{path.name}: expected {expected} and 5s, got {actual} and {duration:.3f}s")

    middle = read_frame(path, 75, frames_dir / f"{path.stem}_middle.png")
    background = np.asarray(middle[5, 5], dtype=np.int16)
    different = np.sqrt(np.sum((middle.astype(np.float32) - background) ** 2, axis=2)) > 35

    # Cards are centered at x=480 and x=1440, with a conservative focus-state
    # scale bound of 1.05. These windows omit the middle divider and canvas edge.
    left = different[170:910, 120:810]
    right = different[170:910, 1110:1800]
    left_coverage = float(np.count_nonzero(left)) / left.size
    right_coverage = float(np.count_nonzero(right)) / right.size
    if left_coverage < 0.20 or right_coverage < 0.20:
        raise AssertionError(
            f"{path.name}: both left/right cards must be visible at frame 75; "
            f"coverage={left_coverage:.3f}/{right_coverage:.3f}"
        )
    occupied_y, occupied_x = np.where(different)
    if not len(occupied_x):
        raise AssertionError(f"{path.name}: rendered frame is empty")
    bbox = [int(occupied_x.min()), int(occupied_y.min()), int(occupied_x.max()), int(occupied_y.max())]
    if bbox[0] < 40 or bbox[1] < 40 or bbox[2] > WIDTH - 40 or bbox[3] > HEIGHT - 40:
        raise AssertionError(f"{path.name}: visible content is clipped or outside safe inset: {bbox}")

    return {
        "file": path.name,
        "width": actual[0],
        "height": actual[1],
        "fps": actual[2],
        "frames": actual[3],
        "duration_s": round(duration, 4),
        "left_card_coverage": round(left_coverage, 4),
        "right_card_coverage": round(right_coverage, 4),
        "visible_bbox": bbox,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "render_dir", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[2] / "out/multi_image_duo_v1",
    )
    parser.add_argument("--canaries", action="store_true", help="also require and verify people/brand/generic canary renders")
    parser.add_argument("--canaries-only", action="store_true", help="verify only the three people/brand/generic canary renders")
    args = parser.parse_args(argv)
    render_dir = args.render_dir.resolve()
    if args.canaries and args.canaries_only:
        parser.error("--canaries and --canaries-only are mutually exclusive")
    paths = [] if args.canaries_only else [render_dir / f"{preset}.mp4" for preset in PRESET_IDS]
    if args.canaries or args.canaries_only:
        paths.extend(render_dir / f"canary_{variant}_duo_compare_hold.mp4" for variant in ("people", "brand", "generic"))

    manifest = []
    frames_dir = render_dir / "verify_frames"
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing required canary render: {path}")
        record = verify_video(path, frames_dir)
        manifest.append(record)
        print(
            f"verified {path.name}: {record['width']}x{record['height']} "
            f"{record['duration_s']}s; left/right coverage "
            f"{record['left_card_coverage']}/{record['right_card_coverage']}"
        )

    manifest_path = render_dir / "multi_image_duo_v1_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"PASS: verified {len(manifest)} duo renders; manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
