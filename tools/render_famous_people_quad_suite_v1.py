#!/usr/bin/env python3
"""
Chronon Famous People Quad Suite V1: 10 Multi-Entity 4-Person Animations

All 4 historical figures remain on screen simultaneously in every clip (1920x1080 @ 30fps, 5.0s):
  - Top-Left:     Albert Einstein   (1879–1955)
  - Top-Right:    Marie Curie       (1867–1934)
  - Bottom-Left:  Nikola Tesla      (1856–1943)
  - Bottom-Right: Abraham Lincoln   (1809–1865)

10 distinct multi-entity motion recipes:
  01. quad_01_grid_assemble     - Staggered slide-in assembly with progressive focus
  02. quad_02_corner_converge    - Inward convergence from 4 corners
  03. quad_03_pair_focus         - Row-by-row focus shift (Top row -> Bottom row -> All)
  04. quad_04_mosaic_spotlight   - Clockwise spotlight tour (Einstein -> Curie -> Lincoln -> Tesla)
  05. quad_05_crossflow          - Diagonal sweep (Einstein+Lincoln, then Curie+Tesla)
  06. quad_06_depth_breath       - Multi-plane 3D depth pulsation across all 4 cards
  07. quad_07_float_orbit        - Harmonic organic floating motion
  08. quad_08_pendulum_sway      - Subtle elegant angular sway between card pairs
  09. quad_09_spring_pop         - Staggered elastic pop entrance with overshoot settle
  10. quad_10_rack_focus         - Chronological archival focus (Lincoln -> Tesla -> Curie -> Einstein)

Uploads ONLY the MP4 videos (no PNG posters) to Drive folder:
  1Oi6AT0CZlV9EuM-ScJGFnbhTB8mlnHHk
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing").resolve()
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
DRIVE_UPLOAD_CLI = BASE_DIR / "RenderingGen/bin/drive-upload"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/famous_people_quad_suite_v1"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "1Oi6AT0CZlV9EuM-ScJGFnbhTB8mlnHHk"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # 5.0 seconds
END = DURATION_FRAMES - 1

BG_COLOR = [0.025, 0.031, 0.045, 1.0]

CARD_W = 540
CARD_H = 400

# 4 card definitions: (id, asset, position, name)
CARDS = (
    ("card_einstein_tl", "assets/images/famous_people_x4_v1/albert_einstein_1947.jpg", [-360, -225], "Albert Einstein"),
    ("card_curie_tr", "assets/images/famous_people_x4_v1/marie_curie_portrait_1900.jpg", [360, -225], "Marie Curie"),
    ("card_tesla_bl", "assets/images/famous_people_x4_v1/nikola_tesla_sarony_c1893.jpg", [-360, 225], "Nikola Tesla"),
    ("card_lincoln_br", "assets/images/famous_people_x4_v1/abraham_lincoln_gardner_1863.jpg", [360, 225], "Abraham Lincoln"),
)


def make_bg_layer() -> dict:
    return {
        "id": "archive_background",
        "type": "color",
        "color": BG_COLOR,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    }


def clean_keyframes(kfs: list[dict]) -> list[dict]:
    seen = {}
    for kf in kfs:
        seen[kf["frame"]] = kf["value"]
    return [{"frame": f, "value": seen[f]} for f in sorted(seen.keys())]


def _tracks(recipe: str, idx: int) -> list[dict]:
    # idx: 0=TL (Einstein), 1=TR (Curie), 2=BL (Tesla), 3=BR (Lincoln)
    phase = idx * 6
    sign_x = -1.0 if idx in (0, 2) else 1.0
    sign_y = -1.0 if idx in (0, 1) else 1.0

    if recipe == "grid_assemble":
        delay = idx * 6
        x_offset = sign_x * 300.0
        return [
            {
                "property": "position_x",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": delay, "value": x_offset},
                    {"frame": 24 + delay, "value": 0.0},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "scale",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24 + delay, "value": 1.04},
                    {"frame": 48 + delay, "value": 1.04},
                    {"frame": 60 + delay, "value": 0.97},
                    {"frame": 120, "value": 0.97},
                    {"frame": 134, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": delay, "value": 0.0},
                    {"frame": 18 + delay, "value": 1.0},
                    {"frame": 48 + delay, "value": 1.0},
                    {"frame": 60 + delay, "value": 0.80},
                    {"frame": 120, "value": 0.80},
                    {"frame": 134, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "corner_converge":
        x_off = sign_x * 240.0
        y_off = sign_y * 150.0
        return [
            {
                "property": "position_x",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": x_off},
                    {"frame": 26, "value": 0.0},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "position_y",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": y_off},
                    {"frame": 26, "value": 0.0},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "scale",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 26, "value": 1.02},
                    {"frame": 75, "value": 0.99},
                    {"frame": 120, "value": 1.01},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "pair_focus":
        # Top pair (0, 1) focus first; Bottom pair (2, 3) focus second
        is_top = idx in (0, 1)
        scale_keys = [
            {"frame": 0, "value": 0.94},
            {"frame": 24, "value": 1.04 if is_top else 0.96},
            {"frame": 60, "value": 1.04 if is_top else 0.96},
            {"frame": 74, "value": 0.96 if is_top else 1.04},
            {"frame": 114, "value": 0.96 if is_top else 1.04},
            {"frame": 134, "value": 1.0},
            {"frame": END, "value": 1.0},
        ]
        opacity_keys = [
            {"frame": 0, "value": 0.0},
            {"frame": 20, "value": 1.0 if is_top else 0.75},
            {"frame": 60, "value": 1.0 if is_top else 0.75},
            {"frame": 74, "value": 0.75 if is_top else 1.0},
            {"frame": 114, "value": 0.75 if is_top else 1.0},
            {"frame": 134, "value": 1.0},
            {"frame": END, "value": 1.0},
        ]
        return [
            {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
            {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys},
        ]

    if recipe == "mosaic_spotlight":
        # Clockwise tour order: 0 (TL, F0..45), 1 (TR, F45..75), 3 (BR, F75..105), 2 (BL, F105..130)
        order_map = {0: 0, 1: 1, 3: 2, 2: 3}
        step = order_map[idx]
        start_f = 6 + step * 30
        peak_f = start_f + 8
        hold_f = start_f + 24
        drop_f = start_f + 32

        return [
            {
                "property": "scale",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.95},
                    {"frame": start_f, "value": 0.96},
                    {"frame": peak_f, "value": 1.05},
                    {"frame": hold_f, "value": 1.05},
                    {"frame": drop_f, "value": 0.96},
                    {"frame": 132, "value": 0.96},
                    {"frame": 142, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.74},
                    {"frame": start_f, "value": 0.74},
                    {"frame": peak_f, "value": 1.0},
                    {"frame": hold_f, "value": 1.0},
                    {"frame": drop_f, "value": 0.74},
                    {"frame": 132, "value": 0.74},
                    {"frame": 142, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "crossflow":
        # Diagonal A (0, 3): Einstein & Lincoln; Diagonal B (1, 2): Curie & Tesla
        is_diag_a = idx in (0, 3)
        return [
            {
                "property": "scale",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.94},
                    {"frame": 24, "value": 1.04 if is_diag_a else 0.96},
                    {"frame": 54, "value": 1.04 if is_diag_a else 0.96},
                    {"frame": 70, "value": 0.96 if is_diag_a else 1.04},
                    {"frame": 114, "value": 0.96 if is_diag_a else 1.04},
                    {"frame": 134, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0 if is_diag_a else 0.75},
                    {"frame": 54, "value": 1.0 if is_diag_a else 0.75},
                    {"frame": 70, "value": 0.75 if is_diag_a else 1.0},
                    {"frame": 114, "value": 0.75 if is_diag_a else 1.0},
                    {"frame": 134, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "depth_breath":
        # 3D Depth breathing: opposing cards pulse in scale and subtle vertical offset
        delay = (idx % 2) * 36
        return [
            {
                "property": "scale",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": 0.95},
                    {"frame": 18, "value": 1.0},
                    {"frame": 36 + delay, "value": 1.04},
                    {"frame": 72 + delay, "value": 0.97},
                    {"frame": 108 + delay, "value": 1.03},
                    {"frame": 140, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "position_y",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": sign_y * 14.0},
                    {"frame": 36 + delay, "value": -sign_y * 8.0},
                    {"frame": 72 + delay, "value": sign_y * 8.0},
                    {"frame": 108 + delay, "value": -sign_y * 4.0},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18 + phase, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "float_orbit":
        # Harmonic floating motion
        lift = sign_y * 16.0
        drift = sign_x * 12.0
        frames_common = [0, 38, 76, 114, END]
        return [
            {
                "property": "position_y",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": lift},
                    {"frame": 38, "value": -lift * 0.7},
                    {"frame": 76, "value": lift * 0.8},
                    {"frame": 114, "value": -lift * 0.4},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "position_x",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": drift},
                    {"frame": 38, "value": -drift * 0.7},
                    {"frame": 76, "value": drift * 0.8},
                    {"frame": 114, "value": -drift * 0.4},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "scale",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": 0.96},
                    {"frame": 38, "value": 1.02},
                    {"frame": 76, "value": 0.99},
                    {"frame": 114, "value": 1.01},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18 + phase, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "pendulum_sway":
        # Subtle angular rotation sway
        rot = sign_x * 4.0
        return [
            {
                "property": "rotation_z",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": rot},
                    {"frame": 32, "value": -rot * 0.75},
                    {"frame": 68, "value": rot * 0.45},
                    {"frame": 104, "value": -rot * 0.20},
                    {"frame": 136, "value": 0.0},
                    {"frame": END, "value": 0.0},
                ],
            },
            {
                "property": "scale",
                "easing": "in_out_sine",
                "keyframes": [
                    {"frame": 0, "value": 0.95},
                    {"frame": 28, "value": 1.02},
                    {"frame": 70, "value": 0.99},
                    {"frame": 110, "value": 1.01},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 16 + phase, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "spring_pop":
        delay = idx * 8
        return [
            {
                "property": "scale",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.75},
                    {"frame": delay, "value": 0.75},
                    {"frame": 22 + delay, "value": 1.06},
                    {"frame": 36 + delay, "value": 0.98},
                    {"frame": 52 + delay, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": delay, "value": 0.0},
                    {"frame": 16 + delay, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    if recipe == "rack_focus":
        # Chronological tour: Lincoln (idx=3) -> Tesla (idx=2) -> Curie (idx=1) -> Einstein (idx=0)
        chrono_order = {3: 0, 2: 1, 1: 2, 0: 3}
        step = chrono_order[idx]
        start_f = 6 + step * 32
        peak_f = start_f + 8
        hold_f = start_f + 24
        drop_f = start_f + 32

        return [
            {
                "property": "scale",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.95},
                    {"frame": start_f, "value": 0.96},
                    {"frame": peak_f, "value": 1.05},
                    {"frame": hold_f, "value": 1.05},
                    {"frame": drop_f, "value": 0.96},
                    {"frame": 136, "value": 0.96},
                    {"frame": 144, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
            {
                "property": "opacity",
                "easing": "in_out_cubic",
                "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 16, "value": 0.74},
                    {"frame": start_f, "value": 0.74},
                    {"frame": peak_f, "value": 1.0},
                    {"frame": hold_f, "value": 1.0},
                    {"frame": drop_f, "value": 0.74},
                    {"frame": 136, "value": 0.74},
                    {"frame": 144, "value": 1.0},
                    {"frame": END, "value": 1.0},
                ],
            },
        ]

    raise ValueError(f"Unknown quad animation recipe: {recipe}")


def build_plan(job_id: str, recipe: str) -> dict:
    layers = [make_bg_layer()]
    for idx, (card_id, asset_path, pos, _) in enumerate(CARDS):
        tracks = _tracks(recipe, idx)
        for t in tracks:
            t["keyframes"] = clean_keyframes(t["keyframes"])
        layers.append({
            "id": card_id,
            "type": "image",
            "asset": asset_path,
            "size": [CARD_W, CARD_H],
            "position": pos,
            "radius": 8.0,
            "fit": "cover",
            "enable_3d": False,
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {"tracks": tracks},
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / f"{job_id}.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": layers,
    }


PRESETS = [
    ("quad_01_grid_assemble", "grid_assemble"),
    ("quad_02_corner_converge", "corner_converge"),
    ("quad_03_pair_focus", "pair_focus"),
    ("quad_04_mosaic_spotlight", "mosaic_spotlight"),
    ("quad_05_crossflow", "crossflow"),
    ("quad_06_depth_breath", "depth_breath"),
    ("quad_07_float_orbit", "float_orbit"),
    ("quad_08_pendulum_sway", "pendulum_sway"),
    ("quad_09_spring_pop", "spring_pop"),
    ("quad_10_rack_focus", "rack_focus"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def upload_via_drive_upload_cli(file_path: Path, name: str | None = None, folder_id: str = DEFAULT_DRIVE_FOLDER) -> dict:
    if not DRIVE_UPLOAD_CLI.is_file():
        raise FileNotFoundError(f"Uploader binary not found at {DRIVE_UPLOAD_CLI}")
    target_name = name or file_path.name
    expected_sha = sha256_of(file_path)

    cmd = [
        str(DRIVE_UPLOAD_CLI),
        "-credentials", str(CREDS_PATH),
        "-token", str(TOKEN_PATH),
        "-folder", folder_id,
        "-file", str(file_path),
        "-name", target_name,
        "-sha256", expected_sha,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    # Output format: DRIVE_UPLOAD_PASS id=<id> link=<link> parent=<folder> sha256=<sha> bytes=<bytes>
    data = {}
    for part in out.split():
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v
    data["local_path"] = str(file_path)
    data["sha256"] = expected_sha
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Render and upload 10 multi-entity 4-person quad animations.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate plans with chronon3d_cli")
    parser.add_argument("--render-only", action="store_true", help="Validate and render MP4s without upload")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing MP4s to Drive")
    parser.add_argument("--force-render", action="store_true", help="Re-render even if MP4 exists")
    parser.add_argument("--drive-folder", type=str, default=DEFAULT_DRIVE_FOLDER, help="Target Google Drive folder ID")
    parser.add_argument("--jobs", type=int, default=2, help="Number of concurrent renders")
    args = parser.parse_args()

    drive_folder = args.drive_folder
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== Chronon Famous People Quad Suite (10 Multi-Entity Animations) ===")
    print(f"Output directory: {OUT_DIR}")
    print(f"Assets root:      {ASSETS_ROOT}")
    print(f"Drive Folder ID:  {drive_folder}")

    # 1. Write plans
    written_plans: dict[str, Path] = {}
    for job_id, recipe in PRESETS:
        plan_dict = build_plan(job_id, recipe)
        plan_file = OUT_DIR / f"{job_id}.plan.json"
        plan_file.write_text(json.dumps(plan_dict, indent=2))
        written_plans[job_id] = plan_file
        print(f"  [plan] {job_id}.plan.json written")

    # 2. Validate plans
    print("\n--- Validating Plans with Chronon3d CLI ---")
    for job_id, plan_file in written_plans.items():
        cmd = [
            str(CHRONON_CLI), "validate",
            "--plan", str(plan_file),
            "--assets-root", str(ASSETS_ROOT),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] {job_id}: {res.stderr or res.stdout}", file=sys.stderr)
            return 1
        print(f"  [OK] {job_id} validated")

    if args.validate_only:
        print("\nAll 10 multi-entity plans validated successfully.")
        return 0

    # 3. Render MP4s
    if not args.upload_only:
        print(f"\n--- Rendering MP4s (Jobs: {args.jobs}, Backend: software) ---")
        todo = []
        for job_id, plan_file in written_plans.items():
            mp4_file = OUT_DIR / f"{job_id}.mp4"
            if mp4_file.exists() and not args.force_render and mp4_file.stat().st_size > 500000:
                print(f"  [SKIP] {job_id}.mp4 already exists ({mp4_file.stat().st_size} bytes)")
            else:
                todo.append((job_id, plan_file, mp4_file))

        def _do_render(item):
            jid, pfile, mfile = item
            t0 = time.time()
            cmd = [
                str(CHRONON_CLI), "render",
                "--plan", str(pfile),
                "--assets-root", str(ASSETS_ROOT),
                "--backend", "software",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            dt = time.time() - t0
            if res.returncode != 0:
                return (jid, False, dt, res.stderr or res.stdout, 0)
            return (jid, True, dt, "", mfile.stat().st_size if mfile.exists() else 0)

        if todo:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
                futures = {pool.submit(_do_render, item): item[0] for item in todo}
                for fut in as_completed(futures):
                    jid, ok, dt, err, sz = fut.result()
                    if not ok:
                        print(f"  [FAIL] {jid} render failed ({dt:.2f}s):\n{err}", file=sys.stderr)
                        return 1
                    print(f"  [OK] {jid}.mp4 rendered in {dt:.2f}s ({sz:,} bytes)")

    if args.render_only:
        print("\nRendering complete (render-only mode).")
        return 0

    # 4. Upload MP4s ONLY (NO PNGs) to Google Drive
    print(f"\n--- Uploading MP4 Videos ONLY to Google Drive ({drive_folder}) ---")
    manifest = {}
    for job_id, _ in PRESETS:
        mp4_file = OUT_DIR / f"{job_id}.mp4"
        if not mp4_file.exists():
            print(f"  [WARN] {mp4_file} not found, skipping upload")
            continue
        print(f"  Uploading {mp4_file.name} ({mp4_file.stat().st_size:,} bytes)...")
        res = upload_via_drive_upload_cli(mp4_file, folder_id=drive_folder)
        print(f"    -> ID: {res.get('id')} | Link: {res.get('link')}")
        manifest[mp4_file.name] = res

    manifest_file = OUT_DIR / "upload_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    print(f"\nUpload manifest written to {manifest_file}")
    print("\n=== All 10 Multi-Entity Quad Videos Uploaded Successfully ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
