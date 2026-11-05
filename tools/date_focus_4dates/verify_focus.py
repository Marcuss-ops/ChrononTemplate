#!/usr/bin/env python3
"""Verify the focus 4-date render and build a keyframe contact sheet."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

JOB = Path(__file__).resolve().parents[2] / "renders" / "date_focus_4dates"
VIDEO = JOB / "focus_4dates.mp4"
FRAMES = [0, 40, 60, 70, 80, 90, 100, 110, 160, 240, 280, 319]


def main() -> int:
    if not VIDEO.is_file() or VIDEO.stat().st_size < 100_000:
        print(f"FAIL missing/short {VIDEO}")
        return 1
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-show_entries", "format=duration,size", "-of", "json", str(VIDEO)],
        text=True,
    ))
    st, fmt = info["streams"][0], info["format"]
    w, h, fps = st["width"], st["height"], st["r_frame_rate"]
    nb = int(st.get("nb_frames") or 0)
    dur = float(fmt.get("duration") or 0)
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(VIDEO), "-vf",
         "scale=320:180,format=gray", "-f", "rawvideo", "-"],
    )
    n = 320 * 180
    chunks = [raw[i:i + n] for i in range(0, len(raw), n) if len(raw[i:i + n]) == n]
    uniq = len({hashlib.sha1(c).hexdigest() for c in chunks})

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        expr = "+".join(f"eq(n,{f})" for f in FRAMES)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(VIDEO), "-vf",
             f"select='{expr}'", "-vsync", "0", str(tmp / "f_%02d.png")],
            check=True,
        )
        thumbs = []
        dark_by_frame = {}
        for i, fr in enumerate(FRAMES, start=1):
            im = Image.open(tmp / f"f_{i:02d}.png").convert("RGB")
            px = list(im.getdata())
            dark = sum(1 for p in px if sum(p) < 330)
            colored = sum(1 for p in px if max(p) - min(p) > 25 and max(p) > 60)
            dark_by_frame[fr] = dark
            print(f"frame {fr:3d}: dark={dark:6d} colored={colored:5d}")
            im.thumbnail((640, 360))
            thumbs.append(im)
        cols, rows = 3, 4
        sheet = Image.new("RGB", (640 * cols, 360 * rows), (255, 255, 255))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
        sheet.save(JOB / "focus_keyframes_sheet.png")
        print("sheet:", JOB / "focus_keyframes_sheet.png")

    # Hold-heavy timeline: many frames repeat during the pauses, so a high
    # unique-frame count is not the right signal. Check format, real motion,
    # and that each of the four date states actually contains the big type.
    required_dark = {0: 7000, 40: 8000, 90: 8000, 160: 8000,
                     240: 8000, 280: 8000}
    ok = (w == 1920 and h == 1080 and fps == "30/1" and nb == 320
          and dur >= 10.5 and uniq >= 120
          and all(dark_by_frame.get(f, 0) >= v for f, v in required_dark.items()))
    print(f"{'PASS' if ok else 'FAIL'} {VIDEO.name}: {w}x{h} {fps} frames={nb} "
          f"dur={dur:.3f}s unique={uniq} bytes={VIDEO.stat().st_size}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
