#!/usr/bin/env python3
"""Verify the modern 4-date render (near-black neon variant)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

JOB = Path(__file__).resolve().parents[2] / "renders" / "date_focus_4dates_modern"
VIDEO = JOB / "focus_4dates_modern.mp4"
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
        bright_by_frame = {}
        for i, fr in enumerate(FRAMES, start=1):
            im = Image.open(tmp / f"f_{i:02d}.png").convert("RGB")
            px = list(im.getdata())
            bright = sum(1 for p in px if sum(p) > 600)
            colored = sum(1 for p in px if max(p) - min(p) > 30)
            bright_by_frame[fr] = bright
            print(f"frame {fr:3d}: bright={bright:6d} colored={colored:6d}")
            im.thumbnail((640, 360))
            thumbs.append(im)
        cols, rows = 3, 4
        sheet = Image.new("RGB", (640 * cols, 360 * rows), (0, 0, 0))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
        sheet.save(JOB / "focus_modern_keyframes_sheet.png")
        print("sheet:", JOB / "focus_modern_keyframes_sheet.png")

    required_bright = {0: 20000, 40: 20000, 90: 20000, 160: 20000,
                       240: 20000, 280: 20000}
    ok = (w == 1920 and h == 1080 and fps == "30/1" and nb == 320
          and dur >= 10.5 and uniq >= 120
          and all(bright_by_frame.get(f, 0) >= v for f, v in required_bright.items()))
    print(f"{'PASS' if ok else 'FAIL'} {VIDEO.name}: {w}x{h} {fps} frames={nb} "
          f"dur={dur:.3f}s unique={uniq} bytes={VIDEO.stat().st_size}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
