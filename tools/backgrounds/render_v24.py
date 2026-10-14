#!/usr/bin/env python3
"""Render v24 true-animation backgrounds. Camera locked, no pan.

Usage: render_v24.py [PRESET...]  (default: all 15)
Out: out/docbg_v24/<pid>_bg.mp4 (1920x1080, 30fps, 8s, CRF23 veryfast)
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from documentary_background_v24 import (
    IDS, FRAMES, FPS, W, H, get_static, get_assets, render_frame,
)

ROOT = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT = ROOT / "out" / "docbg_v24"
OUT.mkdir(parents=True, exist_ok=True)


def render_one(pid: str) -> bool:
    static = get_static(pid)
    assets = get_assets(pid)
    dst = OUT / f"{pid}_bg.mp4"
    # -tune grain: keep per-frame live grain alive through H.264 (default
    # settings freeze grain into P-frames). -g 48: 2s GOP for seeking.
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-crf", "25", "-preset", "veryfast",
           "-tune", "grain", "-g", "48",
           "-pix_fmt", "yuv420p", "-r", str(FPS), str(dst)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(FRAMES):
            fr = render_frame(pid, i, static, assets)
            p.stdin.write(fr.tobytes())
    finally:
        try:
            p.stdin.close()
        except BrokenPipeError:
            pass
    rc = p.wait()
    if rc != 0 or not dst.exists() or dst.stat().st_size == 0:
        print(f"FAIL {pid} rc={rc}")
        return False
    print(f"ok {dst.name} ({dst.stat().st_size // 1024} KB)", flush=True)
    return True


if __name__ == "__main__":
    jobs = sys.argv[1:] or IDS
    bad = [j for j in jobs if not render_one(j)]
    sys.exit(1 if bad else 0)
