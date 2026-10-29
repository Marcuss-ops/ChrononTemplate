#!/usr/bin/env python3
"""Build the Match Cut fast-intro RenderPlan (chronon.render-plan.v3) and render it with Chronon.

24 s @ 30 fps, 6 blocks of 120 frames: news wide / news tall / news wide / web wide / web tall / web wide.
Each block = 12 shots (8 quick whip crops + 4 held "hero" pages). Chronon owns every motion:
slide whips, blur, push-ins, vignette and the 9:16 pillarbox.

    python build_match_cut_plan.py            # write plan, render with the native Windows CLI, encode with ffmpeg
    python build_match_cut_plan.py --plan-only
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
ROOT = TEMPLATE.parent
ASSET_DIR = "ChrononTemplate/assets/fast_intro_match_cut"
OUT = TEMPLATE / "out" / "fast_intro_match_cut"
W, H, FPS = 1920, 1080, 30
BLOCK = 120
PAD = 3  # frames of overlap on each side of a shot (whip travel)

NEWS = [  # (plate, kind)
    ("crop_news_silent", "q"), ("news_masthead", "h"), ("crop_news_harmony", "q"),
    ("crop_news_stories", "q"), ("news_storytelling", "h"), ("crop_news_scene", "q"),
    ("crop_news_motion", "q"), ("news_truth", "h"), ("crop_news_harmony", "q"),
    ("crop_news_viewer", "q"), ("news_discover", "h"), ("crop_news_magic", "q"),
]
WEB = [
    ("web_sports", "q"), ("web_essay", "h"), ("web_news_red", "q"),
    ("web_push_red", "q"), ("web_fashion", "h"), ("web_green_news", "q"),
    ("web_google", "q"), ("web_numbered", "h"), ("web_wiki", "q"),
    ("web_dev", "q"), ("web_wild", "h"), ("web_design", "q"),
]
BLOCKS = [("news", False), ("news", True), ("news", False), ("web", False), ("web", True), ("web", False)]


def make_vignette() -> None:
    p = TEMPLATE / "assets" / "fast_intro_match_cut" / "_vignette.png"
    xs = np.linspace(-1, 1, W)[None, :]
    ys = np.linspace(-1, 1, H)[:, None]
    r = np.clip((xs ** 2 * 0.8 + ys ** 2) / 1.8, 0, 1)
    a = (0.62 * r ** 2.2 * 255).astype(np.uint8)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(p)


def shot_lengths(shots):
    """Rows of (quick, hold, quick) = 8 + 15 + 7 frames, alternating 7/8 for the quick shots."""
    out = []
    for row in range(4):
        out += [8, 15, 7] if row % 2 == 0 else [7, 15, 8]
    return out


def track(prop, easing, kfs):
    return {"property": prop, "easing": easing, "keyframes": [{"frame": f, "value": v} for f, v in kfs]}


def shot_layer(lid, plate, kind, start, length, variant):
    s, e = max(0, start - PAD), min(start + length + PAD, 6 * BLOCK - 1)
    x0 = W / 2
    hold = kind == "h"
    dirn = 1 if variant % 2 == 0 else -1  # alternate whip direction between repeated blocks
    enter, leave = x0 + dirn * 1500, x0 - dirn * 1500
    drift = -dirn * (26 if hold else 60)
    # Render-plan animation keyframes are local to the layer window. Convert
    # the timeline's absolute shot frames to offsets from this padded layer start.
    enter_frame = 0
    entry = x0 if s == start else enter
    settle_frame = max(1, start - s)
    leave_frame = e - s
    exit_start_frame = min(start + length - s, leave_frame - 1)
    exit_start_frame = max(settle_frame + 1, exit_start_frame)
    tracks = [
        track("position", "smoothstep", [(enter_frame, [entry, H / 2, 0]), (settle_frame, [x0, H / 2, 0]), (exit_start_frame, [x0 + drift, H / 2, 0]), (leave_frame, [leave, H / 2, 0])]),
        track("scale", "linear", [(enter_frame, [1.0, 1.0, 1.0]), (leave_frame, [1.0, 1.0, 1.0])]),
        track("blur", "linear", [(enter_frame, 0), (leave_frame, 0)]),
    ]
    return {
        "id": lid, "type": "image", "asset": f"{ASSET_DIR}/{plate}.png",
        "position": [x0, H / 2], "size": [W, H],
        "start_frame": s, "duration_frames": e + 1 - s,
        "animation": {"tracks": tracks},
    }


def build() -> dict:
    layers = [{"id": "ground", "type": "color", "color": [0, 0, 0, 1], "position": [W / 2, H / 2],
               "size": [W, H], "start_frame": 0, "duration_frames": 6 * BLOCK}]
    lens = shot_lengths(None)
    seen = {}
    for bi, (kind, tall) in enumerate(BLOCKS):
        shots = NEWS if kind == "news" else WEB
        t = bi * BLOCK
        for si, ((plate, k), n) in enumerate(zip(shots, lens)):
            seen[plate] = seen.get(plate, 0) + 1
            layers.append(shot_layer(f"b{bi}_s{si}_{plate}", plate, k, t, n, bi))
            t += n
    layers.append({"id": "vignette", "type": "image", "asset": f"{ASSET_DIR}/_vignette.png",
                   "position": [W / 2, H / 2], "size": [W, H], "start_frame": 0, "duration_frames": 6 * BLOCK})
    bar_w = (W - H * 9 / 16) / 2
    for bi, (_, tall) in enumerate(BLOCKS):
        if not tall:
            continue
        for side, cx in (("l", bar_w / 2), ("r", W - bar_w / 2)):
            layers.append({"id": f"pillar_{bi}_{side}", "type": "color", "color": [0, 0, 0, 1],
                           "position": [cx, H / 2], "size": [bar_w, H],
                           "start_frame": bi * BLOCK, "duration_frames": BLOCK})
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": "fast_intro_match_cut",
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": 6 * BLOCK},
            "layers": layers, "output": {"path": "fast_intro_match_cut.mp4", "format": "mp4"}}





DEFAULT_CLI_GLOBS = (
    "Chronon3d/build/chronon/win-release-clang/apps/chronon3d_cli/chronon3d_cli.exe",
    "Chronon3d/build/chronon/rapdaily-release/apps/chronon3d_cli/Release/chronon3d_cli.exe",
    "Chronon3d/build/chronon/rapdaily-release/**/chronon3d_cli.exe",
)


def find_cli() -> Path:
    for g in DEFAULT_CLI_GLOBS:
        for p in ROOT.glob(g):
            return p
    raise SystemExit("chronon3d_cli.exe not found: pass --cli (native build still running?)")


def run(cmd, **kw):
    print(" ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode:
        raise SystemExit(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--backend", default="vulkan", choices=("auto", "software", "vulkan"))
    ap.add_argument("--cli", type=Path, default=None)
    ap.add_argument("--keep-raw", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    make_vignette()
    plan = OUT / "fast_intro_match_cut.plan.json"
    plan.write_text(json.dumps(build(), indent=1), encoding="utf8")
    print("plan:", plan, len(build()["layers"]), "layers")
    if args.plan_only:
        return 0
    cli = (args.cli or find_cli()).resolve()
    raw = OUT / "fast_intro_match_cut.nv12"
    mp4 = OUT / "fast_intro_match_cut.mp4"
    run([cli, "render-plan", "--input", plan, "--assets-root", ROOT, "--backend", args.backend,
         "--fps-num", FPS, "--fps-den", 1, "--video-sink", "raw", "--pipe-pixfmt", "nv12",
         "--output", raw], cwd=ROOT)
    enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq:v", "19", "-b:v", "0"] if shutil.which("nvidia-smi") else \
        ["-c:v", "libx264", "-crf", "17", "-preset", "medium"]
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "nv12",
         "-video_size", f"{W}x{H}", "-framerate", FPS, "-i", raw, "-an", *enc,
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4])
    if not args.keep_raw:
        raw.unlink(missing_ok=True)
    print("done:", mp4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
