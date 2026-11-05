#!/usr/bin/env python3
"""Verify the ten chapter-card renders before upload."""
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

JOB = Path(os.environ.get(
    "CHAPTER_CARDS_JOB",
    str(Path(__file__).resolve().parents[2] / "out" / "chapter_cards_showcase_v1")))
ART = JOB / "mp4"
CATALOG = json.loads((JOB / "plans" / "showcase.json").read_text())
SLUGS = [v["slug"] for v in CATALOG["variants"]]


def probe(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
         "-show_entries", "format=duration", "-of", "json", str(path)], text=True)
    return json.loads(out)


def final_stats(path, tmp):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "5.6", "-i", str(path),
                    "-frames:v", "1", str(tmp / "final.png")], check=True)
    im = Image.open(tmp / "final.png").convert("RGB")
    counts = Counter(im.getdata())
    bg = counts.most_common(1)[0][0]
    light = sum(n for c, n in counts.items() if sum(c) > 480)
    ink = sum(n for c, n in counts.items() if sum(c) < 240)
    accent = sum(n for c, n in counts.items() if max(c) - min(c) > 18)
    return {"nonbg": im.width * im.height - counts[bg], "light": light,
            "ink": ink, "accent": accent}


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
            stats = final_stats(path, Path(td))
        # The minimal set is paper-on-ink: measure ink instead of the old
        # light-on-dark metric, and do not require a coloured accent (half of
        # the cards are deliberately monochrome).
        paper = os.environ.get("CHAPTER_CARDS_VERIFY_PAPER") == "1"
        # The minimal cards hold on a static composition after a short reveal,
        # so they legitimately have fewer unique frames than the busy set.
        min_unique = 30 if paper else 70
        common = (w == 1920 and h == 1080 and fps == "30/1" and nb == 180 and
                  dur >= 5.95 and uniq > min_unique and stats["nonbg"] > 6000)
        if paper:
            ok = common and stats["ink"] > 1200
        else:
            ok = common and stats["light"] > 1200 and stats["accent"] > 400
        print(f"{'PASS' if ok else 'FAIL'} {slug}: {w}x{h} {fps} frames={nb} "
              f"dur={dur:.3f}s unique={uniq} nonbg={stats['nonbg']} "
              f"light={stats['light']} ink={stats['ink']} accent={stats['accent']}")
        if not ok:
            failures.append((slug, "verification thresholds"))
    if failures:
        print(f"\n{len(failures)} failure(s): {failures}")
        return 1
    print(f"\nAll {len(SLUGS)} chapter cards verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
