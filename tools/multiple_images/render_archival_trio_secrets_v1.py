#!/usr/bin/env python3
"""Archival Trio Secrets V1 — True 3-Photo Parallax & Slide-Under Choreography.

Recreates the reference 3-photo archival sequence in ChrononTemplate with 3
independent high-resolution archival photo layers (Operation Sea-Spray bay,
1950s laboratory tracer desk, Greenbrier underground bunker vault) over a
textured warm taupe-grey archival paper plate:
  - Phase 1 (frames 0..24): Left card slides rightward and slightly upward,
    tucking its right border underneath the left border of the Center hero card.
  - Phase 2 (frames 24..149): All 3 cards + background paper perform a smooth,
    continuous leftward parallax drift at distinct depth speeds (-220.5 px for
    Center, -159.0 px for Right, -99.0 px for Left from its initial position /
    -255.0 px from its frame-23 peak, and -109.5 px for the paper plate).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
ASSETS_DIR = TEMPLATE / "assets" / "archival_trio_secrets_v1"
OUT_DIR = TEMPLATE / "out" / "archival_trio_secrets_v1"
EXAMPLES_DIR = TEMPLATE / "examples" / "shutter_lifetime_v1"
TRAJ_PATH = ASSETS_DIR / "trajectories_720p.json"
CLI_DEFAULT = ROOT / "Chronon3d-mainfix/build/chronon/win-gpu-vs18/apps/chronon3d_cli/Release/chronon3d_cli.exe"

W, H, FPS, FRAMES = 1920, 1080, 30, 150


def compress_keyframes(values: list[float]) -> list[dict]:
    """Keep frame 0, frame N-1, and frames where the value changes slope."""
    out = [{"frame": 0, "value": round(float(values[0]), 2)}]
    for f in range(1, len(values) - 1):
        v_prev, v_cur, v_next = values[f - 1], values[f], values[f + 1]
        if abs((v_cur - v_prev) - (v_next - v_cur)) > 1e-4:
            out.append({"frame": f, "value": round(float(v_cur), 2)})
    out.append({"frame": len(values) - 1, "value": round(float(values[-1]), 2)})
    return out


def build_plan() -> dict:
    traj = json.loads(TRAJ_PATH.read_text(encoding="utf-8"))

    # Scale factor from 1280x720 reference measurements to 1920x1080 canvas = 1.5
    s = 1.5
    dx_L = [p[0] * s for p in traj["L"]]
    dy_L = [p[1] * s for p in traj["L"]]
    dx_C = [p[0] * s for p in traj["C"]]
    dy_C = [p[1] * s for p in traj["C"]]
    dx_R = [p[0] * s for p in traj["R"]]
    dy_R = [p[1] * s for p in traj["R"]]

    # Background paper plate gentle leftward drift (matches Center curve scaled by 73/147)
    bg_scale = 73.0 / 147.0
    dx_BG = [round(v * bg_scale, 2) for v in dx_C]

    layers = [
        {
            "id": "archival_paper_bg",
            "type": "image",
            "asset": "ChrononTemplate/assets/archival_trio_secrets_v1/bg_paper_plate.png",
            "size": [2040, 1080],
            "position": [60.0, 0.0],
            "radius": 0.0,
            "fit": "cover",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position_x",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dx_BG),
                    }
                ]
            },
        },
        {
            "id": "card_left_sea_spray",
            "type": "image",
            "asset": "ChrononTemplate/assets/archival_trio_secrets_v1/photo_01_sea_spray_bay.png",
            "size": [656, 477],
            "position": [-602.25, 18.0],
            "radius": 0.0,
            "fit": "cover",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position_x",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dx_L),
                    },
                    {
                        "property": "position_y",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dy_L),
                    },
                ]
            },
        },
        {
            "id": "card_right_bunker_vault",
            "type": "image",
            "asset": "ChrononTemplate/assets/archival_trio_secrets_v1/photo_03_bunker_vault.png",
            "size": [598, 435],
            "position": [492.75, -1.5],
            "radius": 0.0,
            "fit": "cover",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position_x",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dx_R),
                    },
                    {
                        "property": "position_y",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dy_R),
                    },
                ]
            },
        },
        {
            "id": "card_center_lab_hero",
            "type": "image",
            "asset": "ChrononTemplate/assets/archival_trio_secrets_v1/photo_02_lab_desk_hero.png",
            "size": [656, 474],
            "position": [110.25, -1.5],
            "radius": 0.0,
            "fit": "cover",
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position_x",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dx_C),
                    },
                    {
                        "property": "position_y",
                        "easing": "linear",
                        "keyframes": compress_keyframes(dy_C),
                    },
                ]
            },
        },
    ]

    out_mp4 = OUT_DIR / "archival_trio_secrets_v1.mp4"
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "archival_trio_secrets_v1",
        "canvas": {
            "width": W,
            "height": H,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": FRAMES,
        },
        "output": {
            "path": str(out_mp4),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": layers,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan = build_plan()
    plan_path = OUT_DIR / "archival_trio_secrets_v1.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"[written] {plan_path}")

    cli = CLI_DEFAULT
    if not cli.is_file():
        print(f"CLI not found at {cli}", file=sys.stderr)
        return 1

    val = subprocess.run(
        [str(cli), "validate", "--plan", str(plan_path), "--assets-root", str(ROOT)],
        capture_output=True,
        text=True,
    )
    if val.returncode != 0:
        print(f"[FAIL] validate:\n{val.stderr}\n{val.stdout}", file=sys.stderr)
        return 1
    print("[OK] validate archival_trio_secrets_v1")

    ren = subprocess.run(
        [
            str(cli),
            "render",
            "--plan",
            str(plan_path),
            "--assets-root",
            str(ROOT),
            "--backend",
            "vulkan",
            "--gpu-hot-path-mode",
            "require_gpu_native",
            "--encoder-backend",
            "native",
            "--pipe-pixfmt",
            "rgba",
            "--hardware",
            "nvenc",
            "--output",
            str(OUT_DIR / "archival_trio_secrets_v1.mp4"),
        ],
        capture_output=True,
        text=True,
    )
    if ren.returncode != 0:
        print(f"[FAIL] render:\n{ren.stderr}\n{ren.stdout}", file=sys.stderr)
        return 1
    print(f"[OK] rendered {OUT_DIR / 'archival_trio_secrets_v1.mp4'}")
    if EXAMPLES_DIR.exists():
        (EXAMPLES_DIR / "plans").mkdir(parents=True, exist_ok=True)
        (EXAMPLES_DIR / "renders").mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan_path, EXAMPLES_DIR / "plans" / "archival_trio_secrets_v1.plan.json")
        shutil.copy2(OUT_DIR / "archival_trio_secrets_v1.mp4", EXAMPLES_DIR / "renders" / "archival_trio_secrets_v1.mp4")
        shutil.copy2(OUT_DIR / "archival_trio_secrets_v1.mp4", EXAMPLES_DIR / "renders" / "chronons_archival_triptych_shutter_focus.mp4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
