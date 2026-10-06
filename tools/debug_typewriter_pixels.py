#!/usr/bin/env python3
"""Dump pixel evidence for flagged frames: what is bright, where, and its color."""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "out/typewriter_modern_v1"


def frame(mp4: Path, f: int) -> np.ndarray:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf",
                        f"select='eq(n\\,{f})'", "-vsync", "0",
                        "-frames:v", "1", str(Path(td) / "o.png")],
                       check=True, capture_output=True)
        return np.asarray(Image.open(Path(td) / "o.png").convert("RGB"), dtype=np.int16)


def bright(rgb):
    r, g, b = rgb[..., 0].astype(np.int32), rgb[..., 1].astype(np.int32), rgb[..., 2].astype(np.int32)
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
    return (mn > 120) & (mx - mn < 60) & ~((g > r + 25) & (g > b + 25)) & ~(b > r + 40) & ~(r > g + 60)


def cursor(rgb):
    r, g, b = rgb[..., 0].astype(np.int32), rgb[..., 1].astype(np.int32), rgb[..., 2].astype(np.int32)
    return (r > 140) & (g < 110) & (b < 110)


def dump(name, f):
    rgb = frame(OUT / f"{name}.mp4", f)
    t = bright(rgb); c = cursor(rgb)
    t[:, 1880:] = False
    tcols = np.nonzero(t.any(axis=0))[0]
    ccols = np.nonzero(c.any(axis=0))[0]
    crow = np.nonzero(c.any(axis=1))[0]
    print(f"== {name} f{f}")
    print(f"   cursor px={int(c.sum())} cols={list(ccols[:3])}..{list(ccols[-3:]) if ccols.size else []}"
          f" rows={list(crow[:2])}..{list(crow[-2:]) if crow.size else []}")
    if tcols.size:
        # cluster text columns into runs
        runs = []
        start = prev = int(tcols[0])
        for col in tcols[1:]:
            col = int(col)
            if col - prev > 12:
                runs.append((start, prev)); start = col
            prev = col
        runs.append((start, prev))
        print(f"   text px={int(t.sum())} runs={runs[:14]}")
        # sample colors in the right-most run
        r0, r1 = runs[-1]
        ys, xs = np.nonzero(t[:, r0:r1 + 1])
        if len(xs):
            i = len(xs) // 2
            px = rgb[ys[i], xs[i] + r0]
            print(f"   rightmost run {r0}-{r1} sample rgb={tuple(int(v) for v in px)}")
    else:
        print("   text px=0")


CASES = [
    ("01_monospace_block_cursor", [4, 10, 54, 100, 130, 149]),
    ("03_soft_opacity_ramp", [52]),
    ("07_word_snap", [40]),
    ("09_highlighter_expansion", [18, 52]),
    ("12_glitch_pop", [4]),
    ("14_focal_blur_dissolve", [0]),
    ("15_paper_punch_stencil", [52]),
]
for name, frames in CASES:
    for f in frames:
        dump(name, f)
