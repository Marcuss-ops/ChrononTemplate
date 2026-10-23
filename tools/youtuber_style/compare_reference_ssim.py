#!/usr/bin/env python3
"""Compare generated frames to same-named frames in named reference folders.

Uses folder and frame names as the mapping key, resizes (never crops) to 960x540,
and reports SSIM for first/middle/last frames per animation or every frame.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

REF = Path(r"C:/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Youtuberstle/Reference")
OUT = Path(r"C:/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Youtuberstle/Final")
SIZE = (960, 540)


def rgb(path: Path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, default=REF)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--csv", type=Path, default=Path("artifacts/youtuberstle_rebuild_v1/ssim_first_mid_last.csv"))
    ap.add_argument("--all", action="store_true", help="score every matched frame, not only first/middle/last")
    args = ap.parse_args()

    rows = []
    for ref_dir in sorted(p for p in args.reference.iterdir() if p.is_dir()):
        ref_frames = sorted((ref_dir / "frames").glob("frame_*.png"))
        if not ref_frames:
            continue
        if args.all:
            selected = ref_frames
        else:
            selected = list(dict.fromkeys((ref_frames[0], ref_frames[len(ref_frames)//2], ref_frames[-1])))
        generated_dir = args.output / ref_dir.name
        for ref in selected:
            generated = generated_dir / ref.name
            if not generated.is_file():
                rows.append((ref_dir.name, ref.name, "MISSING", ""))
                continue
            a, b = rgb(ref), rgb(generated)
            score = structural_similarity(a, b, channel_axis=2, data_range=255)
            rows.append((ref_dir.name, ref.name, "OK", f"{score:.6f}"))

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("animation", "frame", "status", "ssim_960x540"))
        writer.writerows(rows)
    groups: dict[str, list[float]] = {}
    for animation, _, status, value in rows:
        if status == "OK":
            groups.setdefault(animation, []).append(float(value))
    for name, scores in groups.items():
        print(f"{name}: mean SSIM {sum(scores)/len(scores):.4f} ({len(scores)} frames)")
    valid = [float(value) for _, _, status, value in rows if status == "OK"]
    missing = sum(status == "MISSING" for _, _, status, _ in rows)
    print(f"overall: mean SSIM {sum(valid)/len(valid):.4f} ({len(valid)} scored; {missing} missing); CSV: {args.csv}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
