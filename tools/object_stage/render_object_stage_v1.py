#!/usr/bin/env python3
"""object_stage_v1 — three archival cut-outs as physical dossier cards.

The whole scene is authored as a `chronon.render-plan.v3` plan and contains
only image layers:

  * a 4K desk plate with out-of-focus papers, dust and a faint archive circle;
  * three baked dossier cards (rounded corners, gold frame, warm monochrome
    portrait, name / role / years) at three different Z depths;
  * a spring-damper camera with a slight overshoot and a low-frequency
    breathing drift, sampled per frame into `camera_samples`.

All text lives inside the PNGs.  The renderer's 3D text layout is not used.

Usage:
  python3 tools/object_stage/render_object_stage_v1.py --assets
  python3 tools/object_stage/render_object_stage_v1.py --preview
  python3 tools/object_stage/render_object_stage_v1.py --render
  python3 tools/object_stage/render_object_stage_v1.py --compose
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CLI = (WORKSPACE / "Chronon3d/build/chronon/linux-video-release/apps/"
       "chronon3d_cli/chronon3d_cli").resolve()
ASSETS = ROOT
OUT = ROOT / "out/object_stage_v1"

WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 300

# cards sit in the lower half; x/y are authored in the renderer's 960x540
# position space (they are doubled on the 1920x1080 canvas).
CARDS = [
    # id, png, x, y, z, rot_z, enter_frame
    ("ada", "card_ada.png", -310.0, 50.0, 95.0, -1.1, 16),
    ("curie", "card_curie.png", 0.0, 54.0, 45.0, 0.5, 6),
    ("tesla", "card_tesla.png", 310.0, 47.0, 120.0, 1.2, 24),
]


def spring_series(start: float, target: float, frames: int,
                  frequency_hz: float, damping: float, dt: float = 1.0 / 30.0) -> list[float]:
    """Semi-implicit spring-damper sampled once per frame."""
    omega = 2.0 * math.pi * frequency_hz
    k = omega * omega
    c = 2.0 * damping * omega
    x, v = start, 0.0
    out: list[float] = []
    for _ in range(frames):
        a = k * (target - x) - c * v
        v += a * dt
        x += v * dt
        out.append(x)
    return out


def build_camera() -> list[dict]:
    # one slow crane / dolly: high and wide, settling low and close.
    x = spring_series(-55.0, 13.0, FRAMES, 0.10, 0.92)
    y = spring_series(330.0, 8.0, FRAMES, 0.14, 0.90)
    z = spring_series(-2250.0, -1400.0, FRAMES, 0.13, 0.91)
    pitch = spring_series(12.5, 2.3, FRAMES, 0.15, 0.91)
    yaw = spring_series(-2.8, 0.5, FRAMES, 0.11, 0.92)

    samples = []
    for f in range(FRAMES):
        t = f / FPS
        # sub-degree breathing: the held frame is never mathematically still
        bx = 2.4 * math.sin(2.0 * math.pi * 0.083 * t + 0.4)
        by = 1.9 * math.sin(2.0 * math.pi * 0.061 * t + 1.7)
        bz = 1.5 * math.sin(2.0 * math.pi * 0.047 * t + 2.6)
        byaw = 0.10 * math.sin(2.0 * math.pi * 0.071 * t + 0.9)
        roll = 0.075 * math.sin(2.0 * math.pi * 0.055 * t + 2.1)
        camera = {
            "type": "perspective",
            "position": [round(x[f] + bx, 5), round(y[f] + by, 5), round(z[f] + bz, 5)],
            "rotation_deg": [round(pitch[f], 5), round(yaw[f] + byaw, 5), round(roll, 5)],
            "fov_deg": round(45.6 + 0.30 * math.sin(2.0 * math.pi * 0.039 * t), 5),
            "near": 1, "far": 20000, "zoom": 1,
            "sensor_width_mm": 36, "lens_shift": [0, 0],
        }
        samples.append({"frame": f, "camera": camera})
    return samples


def card_layer(card_id: str, png: str, x: float, y: float, z: float,
               rot_z: float, enter: int) -> dict:
    return {
        "id": f"card_{card_id}",
        "type": "image",
        "asset": f"assets/object_stage_v1/{png}",
        "size": [540, 698],
        "position": [x, y, z],
        "rotation": [0, 0, rot_z],
        "fit": "contain",
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": FRAMES,
        "animation": {"tracks": [
            {"property": "opacity", "easing": "out_cubic",
             "keyframes": [{"frame": enter, "value": 0.0},
                           {"frame": enter + 24, "value": 1.0}]},
            {"property": "position_y", "easing": "out_cubic",
             "keyframes": [{"frame": enter, "value": y + 72.0},
                           {"frame": enter + 34, "value": y}]},
            {"property": "scale", "easing": "out_cubic",
             "keyframes": [{"frame": enter, "value": 0.95},
                           {"frame": enter + 34, "value": 1.0}]},
        ]},
    }


def build_plan() -> dict:
    camera_samples = build_camera()
    layers: list[dict] = [
        {
            "id": "desk",
            "type": "image",
            "asset": "assets/object_stage_v1/desk_bg_v2.png",
            "size": [1920, 1080],
            "position": [0, 0, 560.0],
            "fit": "cover",
            "enable_3d": True,
            "scale": [2.6, 2.6, 1],
            "start_frame": 0,
            "duration_frames": FRAMES,
        },
    ]
    for card in CARDS:
        layers.append(card_layer(*card))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "object_stage_v1",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": FRAMES},
        "camera": camera_samples[0]["camera"],
        "camera_samples": camera_samples,
        "layers": layers,
        "output": {"path": "object_stage_v1.mp4", "format": "mp4", "codec": "h264"},
    }


def render(plan_path: Path, output: Path, first: int, last: int) -> None:
    subprocess.run([
        str(CLI), "render-plan", "--input", str(plan_path),
        "--assets-root", str(ASSETS), "--output", str(output),
        "--backend", "software", "--start-frame", str(first),
        "--end-frame", str(last), "--encode-preset", "veryfast",
        "--crf", "17",
    ], check=True, cwd=WORKSPACE)


def compose(scene: Path, title: Path, output: Path) -> None:
    filt = (
        "[1:v]format=rgba,fade=t=in:st=0.35:d=0.85:alpha=1[ttl];"
        "[0:v][ttl]overlay=0:0:format=auto,format=yuv420p[v]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", str(scene), "-loop", "1", "-i", str(title),
        "-filter_complex", filt, "-map", "[v]", "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-movflags", "+faststart", "-t", f"{FRAMES / FPS:.3f}", str(output),
    ], check=True, cwd=WORKSPACE)


def preview_full(plan_path: Path, frames: list[int]) -> None:
    """Render stills and composite the title on them for a complete frame check."""
    from PIL import Image

    title = Image.open(ASSETS / "assets/object_stage_v1/title_overlay.png").convert("RGBA")
    for frame in frames:
        raw = OUT / f"preview_{frame:03d}.png"
        render(plan_path, raw, frame, frame)
        base = Image.open(raw).convert("RGBA")
        base.alpha_composite(title)
        base.convert("RGB").save(OUT / f"preview_{frame:03d}_full.jpg", quality=94)
        print(f"preview {frame}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--compose", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    if args.assets:
        subprocess.run(["python3", str(ROOT / "tools/object_stage/build_stage_assets.py")],
                       check=True, cwd=ROOT)
        return

    plan = build_plan()
    plan_path = OUT / "object_stage_v1.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"plan: {plan_path}")

    if args.preview:
        preview_full(plan_path, [0, 24, 60, 120, 220, 299])
    if args.render:
        scene = OUT / "object_stage_v1_scene.mp4"
        render(plan_path, scene, 0, FRAMES - 1)
        print(f"scene: {scene}")
    if args.compose:
        scene = OUT / "object_stage_v1_scene.mp4"
        final = OUT / "object_stage_v1_final.mp4"
        compose(scene, ASSETS / "assets/object_stage_v1/title_overlay.png", final)
        print(f"final: {final}")


if __name__ == "__main__":
    main()
