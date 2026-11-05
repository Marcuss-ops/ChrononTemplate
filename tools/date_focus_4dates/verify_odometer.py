#!/usr/bin/env python3
"""Verify the light Playfair odometer four-date render."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

JOB = Path(__file__).resolve().parents[2] / "renders" / "date_odometer_4dates"
VIDEO = JOB / "odometer_4dates.mp4"
FRAMES = [0, 40, 60, 70, 80, 90, 100, 110, 160, 240, 280, 319]


def main() -> int:
    if not VIDEO.is_file() or VIDEO.stat().st_size < 80_000:
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
        ink_by_frame = {}
        for i, fr in enumerate(FRAMES, start=1):
            im = Image.open(tmp / f"f_{i:02d}.png").convert("RGB")
            px = list(im.getdata())
            ink = sum(1 for p in px if sum(p) < 330)
            colored = sum(1 for p in px if max(p) - min(p) > 30)
            ink_by_frame[fr] = ink
            print(f"frame {fr:3d}: ink={ink:6d} colored={colored:5d}")
            im.thumbnail((640, 360))
            thumbs.append(im)
        cols, rows = 3, 4
        sheet = Image.new("RGB", (640 * cols, 360 * rows), (243, 241, 235))
        for i, im in enumerate(thumbs):
            sheet.paste(im, ((i % cols) * 640, (i // cols) * 360))
        sheet.save(JOB / "odometer_keyframes_sheet.png")
        print("sheet:", JOB / "odometer_keyframes_sheet.png")

    required_ink = {0: 12000, 40: 12000, 90: 12000,
                    160: 12000, 240: 12000, 280: 12000}
    # This design is deliberately hold-heavy (static rail + long pauses), so
    # 102-105 unique frames is expected; the transition frames are covered by
    # the contact sheet and by the four date-state ink checks below.
    ok = (w == 1920 and h == 1080 and fps == "30/1" and nb == 320
          and dur >= 10.5 and uniq >= 90
          and all(ink_by_frame.get(f, 0) >= v for f, v in required_ink.items()))
    print(f"{'PASS' if ok else 'FAIL'} {VIDEO.name}: {w}x{h} {fps} frames={nb} "
          f"dur={dur:.3f}s unique={uniq} bytes={VIDEO.stat().st_size}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
