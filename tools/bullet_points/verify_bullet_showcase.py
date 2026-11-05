#!/usr/bin/env python3
"""Verify the ten bullet-point renders before upload.

Checks the container (1920x1080, 30 fps, 180 frames, 6 s), that the frame
really contains the list (non-background and light ink pixels), that the accent
glow is present, and that the clip animates (unique frame hashes).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from PIL import Image

JOB = Path(os.environ.get("BULLET_JOB", str(Path(__file__).resolve().parents[2] / "out" / "bullet_points_showcase_v1")))
ART = JOB / "mp4"
CATALOG = json.loads((JOB / "plans" / "showcase.json").read_text())
SLUGS = [v["slug"] for v in CATALOG["variants"]]


def probe(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-show_entries", "format=duration", "-of", "json", str(path)], text=True)
    return json.loads(out)


def frames(path, numbers, tmp):
    expr = "+".join(f"eq(n,{n})" for n in numbers)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf",
                    f"select='{expr}'", "-vsync", "0", str(tmp / "f_%02d.png")],
                   check=True)
    out = []
    for i in range(1, len(numbers) + 1):
        im = Image.open(tmp / f"f_{i:02d}.png").convert("RGB")
        counts = Counter(im.getdata())
        bg = counts.most_common(1)[0][0]
        light = sum(n for c, n in counts.items() if sum(c) > 500)
        accentish = sum(n for c, n in counts.items() if max(c) - min(c) > 20)
        out.append({"frame": numbers[i - 1], "bg": bg, "nonbg": im.width * im.height - counts[bg],
                    "light": light, "accent": accentish})
    return out


def unique_hashes(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
                                   "scale=320:180,format=gray", "-f", "rawvideo", "-"])
    n = 320 * 180
    return len({hashlib.sha1(raw[i:i + n]).hexdigest()
                for i in range(0, len(raw), n) if len(raw[i:i + n]) == n})


def main():
    failures = []
    for slug in SLUGS:
        path = ART / f"{slug}.mp4"
        if not path.is_file() or path.stat().st_size < 10_000:
            failures.append((slug, "missing or short file"))
            print(f"FAIL {slug}: missing or short file")
            continue
        info = probe(path)
        st, fmt = info["streams"][0], info["format"]
        w, h = st["width"], st["height"]
        fps = st.get("r_frame_rate")
        nb = int(st.get("nb_frames") or 0)
        dur = float(fmt.get("duration") or 0)
        uniq = unique_hashes(path)
        with tempfile.TemporaryDirectory() as td:
            stats = frames(path, [10, 60, 110, 175], Path(td))
        final = stats[-1]
        ok = (w == 1920 and h == 1080 and fps == "30/1" and nb == 180 and
              dur >= 5.95 and uniq > 80 and
              final["light"] > 2500 and final["accent"] > 1500 and
              final["nonbg"] > 15000)
        print(f"{'PASS' if ok else 'FAIL'} {slug}: {w}x{h} {fps} frames={nb} "
              f"dur={dur:.3f}s unique={uniq} final_nonbg={final['nonbg']} "
              f"light={final['light']} accent={final['accent']}")
        if not ok:
            failures.append((slug, "verification thresholds"))
    if failures:
        print(f"\n{len(failures)} failure(s): {failures}")
        return 1
    print(f"\nAll {len(SLUGS)} bullet-point variants verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
