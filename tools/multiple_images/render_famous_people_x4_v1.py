#!/usr/bin/env python3
"""
Chronon Famous People X4 Suite: 4 Individual Portrait Reveals & 2x2 Quad Composition

Generates, validates, renders, and uploads 1920x1080 historical portrait animations:
  01. 01_albert_einstein_reveal           - Albert Einstein (1879–1955)
  02. 02_marie_curie_reveal               - Marie Curie (1867–1934)
  03. 03_nikola_tesla_reveal              - Nikola Tesla (1856–1943)
  04. 04_abraham_lincoln_reveal           - Abraham Lincoln (1809–1865)
  05. 05_famous_people_quad_composition   - Staggered 2x2 Assemble & Spotlight Showcase

Uploads deliverables via RenderingGen's verified drive-upload CLI into Drive folder:
  1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS
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
OUT_DIR = BASE_DIR / "ChrononTemplate/out/famous_people_x4_v1"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
DRIVE_FOLDER_ID = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # 5.0 seconds
END_FRAME = DURATION_FRAMES - 1

BG_COLOR = [0.025, 0.031, 0.045, 1.0]

ASSET_EINSTEIN = "assets/images/famous_people_x4_v1/albert_einstein_1947.jpg"
ASSET_CURIE = "assets/images/famous_people_x4_v1/marie_curie_portrait_1900.jpg"
ASSET_TESLA = "assets/images/famous_people_x4_v1/nikola_tesla_sarony_c1893.jpg"
ASSET_LINCOLN = "assets/images/famous_people_x4_v1/abraham_lincoln_gardner_1863.jpg"


def make_bg_layer(layer_id: str = "archive_background") -> dict:
    return {
        "id": layer_id,
        "type": "color",
        "color": BG_COLOR,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    }


def build_01_einstein() -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "famous_einstein_image_reveal_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / "01_albert_einstein_reveal.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": [
            make_bg_layer(),
            {
                "id": "portrait_einstein",
                "type": "image",
                "asset": ASSET_EINSTEIN,
                "size": [650, 795],
                "position": [0, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": False,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {
                            "property": "position_y",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 30.0},
                                {"frame": 26, "value": 0.0},
                                {"frame": END_FRAME, "value": 0.0},
                            ],
                        },
                        {
                            "property": "scale",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.90},
                                {"frame": 30, "value": 1.0},
                                {"frame": 90, "value": 1.035},
                                {"frame": END_FRAME, "value": 1.055},
                            ],
                        },
                        {
                            "property": "opacity",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.0},
                                {"frame": 20, "value": 1.0},
                                {"frame": END_FRAME, "value": 1.0},
                            ],
                        },
                    ]
                },
            },
        ],
    }


def build_02_curie() -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "famous_curie_image_reveal_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / "02_marie_curie_reveal.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": [
            make_bg_layer(),
            {
                "id": "portrait_curie",
                "type": "image",
                "asset": ASSET_CURIE,
                "size": [560, 820],
                "position": [0, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": False,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {
                            "property": "position_y",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 25.0},
                                {"frame": 28, "value": 0.0},
                                {"frame": END_FRAME, "value": 0.0},
                            ],
                        },
                        {
                            "property": "scale",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.92},
                                {"frame": 32, "value": 1.0},
                                {"frame": 90, "value": 1.025},
                                {"frame": END_FRAME, "value": 1.045},
                            ],
                        },
                        {
                            "property": "opacity",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.0},
                                {"frame": 22, "value": 1.0},
                                {"frame": END_FRAME, "value": 1.0},
                            ],
                        },
                    ]
                },
            },
        ],
    }


def build_03_tesla() -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "famous_tesla_image_reveal_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / "03_nikola_tesla_reveal.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": [
            make_bg_layer(),
            {
                "id": "portrait_tesla",
                "type": "image",
                "asset": ASSET_TESLA,
                "size": [550, 830],
                "position": [0, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": False,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {
                            "property": "position_y",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": -25.0},
                                {"frame": 26, "value": 0.0},
                                {"frame": END_FRAME, "value": 0.0},
                            ],
                        },
                        {
                            "property": "scale",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.91},
                                {"frame": 30, "value": 1.0},
                                {"frame": 90, "value": 1.03},
                                {"frame": END_FRAME, "value": 1.05},
                            ],
                        },
                        {
                            "property": "opacity",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.0},
                                {"frame": 20, "value": 1.0},
                                {"frame": END_FRAME, "value": 1.0},
                            ],
                        },
                    ]
                },
            },
        ],
    }


def build_04_lincoln() -> dict:
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "famous_lincoln_image_reveal_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / "04_abraham_lincoln_reveal.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": [
            make_bg_layer(),
            {
                "id": "portrait_lincoln",
                "type": "image",
                "asset": ASSET_LINCOLN,
                "size": [650, 800],
                "position": [0, 0],
                "radius": 0.0,
                "fit": "cover",
                "enable_3d": False,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {
                            "property": "position_y",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 30.0},
                                {"frame": 28, "value": 0.0},
                                {"frame": END_FRAME, "value": 0.0},
                            ],
                        },
                        {
                            "property": "scale",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.90},
                                {"frame": 30, "value": 1.0},
                                {"frame": 90, "value": 1.028},
                                {"frame": END_FRAME, "value": 1.048},
                            ],
                        },
                        {
                            "property": "opacity",
                            "easing": "out_cubic",
                            "keyframes": [
                                {"frame": 0, "value": 0.0},
                                {"frame": 22, "value": 1.0},
                                {"frame": END_FRAME, "value": 1.0},
                            ],
                        },
                    ]
                },
            },
        ],
    }


def build_05_quad() -> dict:
    card_w = 540
    card_h = 400
    tl_pos = [-360, -225]
    tr_pos = [360, -225]
    bl_pos = [-360, 225]
    br_pos = [360, 225]

    def quad_card(card_id: str, asset: str, pos: list[float], tracks: list[dict]) -> dict:
        return {
            "id": card_id,
            "type": "image",
            "asset": asset,
            "size": [card_w, card_h],
            "position": pos,
            "radius": 8.0,
            "fit": "cover",
            "enable_3d": False,
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {"tracks": tracks},
        }

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "famous_people_quad_composition_v1",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUT_DIR / "05_famous_people_quad_composition.mp4"),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": [
            make_bg_layer(),
            # TL: Albert Einstein
            quad_card("card_einstein_tl", ASSET_EINSTEIN, tl_pos, [
                {
                    "property": "position_x",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -300.0},
                        {"frame": 24, "value": 0.0},
                        {"frame": END_FRAME, "value": 0.0},
                    ],
                },
                {
                    "property": "scale",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.92},
                        {"frame": 24, "value": 1.04},
                        {"frame": 48, "value": 1.04},
                        {"frame": 60, "value": 0.97},
                        {"frame": 120, "value": 0.97},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
                {
                    "property": "opacity",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 18, "value": 1.0},
                        {"frame": 48, "value": 1.0},
                        {"frame": 60, "value": 0.80},
                        {"frame": 120, "value": 0.80},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
            ]),
            # TR: Marie Curie
            quad_card("card_curie_tr", ASSET_CURIE, tr_pos, [
                {
                    "property": "position_x",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 6, "value": 300.0},
                        {"frame": 30, "value": 0.0},
                        {"frame": END_FRAME, "value": 0.0},
                    ],
                },
                {
                    "property": "scale",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.92},
                        {"frame": 30, "value": 1.0},
                        {"frame": 52, "value": 0.97},
                        {"frame": 66, "value": 1.04},
                        {"frame": 84, "value": 1.04},
                        {"frame": 96, "value": 0.97},
                        {"frame": 120, "value": 0.97},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
                {
                    "property": "opacity",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 6, "value": 0.0},
                        {"frame": 24, "value": 0.80},
                        {"frame": 52, "value": 0.80},
                        {"frame": 66, "value": 1.0},
                        {"frame": 84, "value": 1.0},
                        {"frame": 96, "value": 0.80},
                        {"frame": 120, "value": 0.80},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
            ]),
            # BL: Nikola Tesla
            quad_card("card_tesla_bl", ASSET_TESLA, bl_pos, [
                {
                    "property": "position_x",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 12, "value": -300.0},
                        {"frame": 36, "value": 0.0},
                        {"frame": END_FRAME, "value": 0.0},
                    ],
                },
                {
                    "property": "scale",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.92},
                        {"frame": 36, "value": 0.97},
                        {"frame": 88, "value": 0.97},
                        {"frame": 100, "value": 1.04},
                        {"frame": 118, "value": 1.04},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
                {
                    "property": "opacity",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 12, "value": 0.0},
                        {"frame": 30, "value": 0.80},
                        {"frame": 88, "value": 0.80},
                        {"frame": 100, "value": 1.0},
                        {"frame": 118, "value": 1.0},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
            ]),
            # BR: Abraham Lincoln
            quad_card("card_lincoln_br", ASSET_LINCOLN, br_pos, [
                {
                    "property": "position_x",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 18, "value": 300.0},
                        {"frame": 42, "value": 0.0},
                        {"frame": END_FRAME, "value": 0.0},
                    ],
                },
                {
                    "property": "scale",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.92},
                        {"frame": 42, "value": 0.97},
                        {"frame": 120, "value": 0.97},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
                {
                    "property": "opacity",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 18, "value": 0.0},
                        {"frame": 36, "value": 0.80},
                        {"frame": 120, "value": 0.80},
                        {"frame": 134, "value": 1.0},
                        {"frame": END_FRAME, "value": 1.0},
                    ],
                },
            ]),
        ],
    }


ITEMS = [
    ("01_albert_einstein_reveal", build_01_einstein),
    ("02_marie_curie_reveal", build_02_curie),
    ("03_nikola_tesla_reveal", build_03_tesla),
    ("04_abraham_lincoln_reveal", build_04_lincoln),
    ("05_famous_people_quad_composition", build_05_quad),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_poster(mp4_path: Path, poster_path: Path):
    if poster_path.exists():
        return
    cmd = [
        "ffmpeg", "-y",
        "-ss", "00:00:02.500",
        "-i", str(mp4_path),
        "-vframes", "1",
        str(poster_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def upload_via_drive_upload_cli(file_path: Path, name: str | None = None, folder_id: str | None = None) -> dict:
    if not DRIVE_UPLOAD_CLI.is_file():
        raise FileNotFoundError(f"Uploader binary not found at {DRIVE_UPLOAD_CLI}")
    target_name = name or file_path.name
    expected_sha = sha256_of(file_path)
    target_folder = folder_id or DRIVE_FOLDER_ID

    cmd = [
        str(DRIVE_UPLOAD_CLI),
        "-credentials", str(CREDS_PATH),
        "-token", str(TOKEN_PATH),
        "-folder", target_folder,
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
    parser = argparse.ArgumentParser(description="Build, validate, render and upload Famous People X4 Suite.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate plans with chronon3d_cli")
    parser.add_argument("--render-only", action="store_true", help="Validate and render MP4s without upload")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing MP4s and posters to Drive")
    parser.add_argument("--force-render", action="store_true", help="Re-render even if MP4 exists")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: validate -> render -> poster -> upload")
    parser.add_argument("--drive-folder", type=str, default="1Oi6AT0CZlV9EuM-ScJGFnbhTB8mlnHHk", help="Target Google Drive folder ID")
    args = parser.parse_args()

    drive_folder = args.drive_folder

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== Famous People X4 Suite ===")
    print(f"Output directory: {OUT_DIR}")
    print(f"Assets root:      {ASSETS_ROOT}")
    print(f"Drive Folder ID:  {drive_folder}")

    # 1. Write plans
    written_plans: dict[str, Path] = {}
    for name, builder in ITEMS:
        plan_dict = builder()
        plan_file = OUT_DIR / f"{name}.plan.json"
        plan_file.write_text(json.dumps(plan_dict, indent=2))
        written_plans[name] = plan_file
        print(f"  [plan] {name}.plan.json written")

    # 2. Validate plans
    print("\n--- Validating Plans with Chronon3d CLI ---")
    for name, plan_file in written_plans.items():
        cmd = [
            str(CHRONON_CLI), "validate",
            "--plan", str(plan_file),
            "--assets-root", str(ASSETS_ROOT),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  [FAIL] {name}: {res.stderr or res.stdout}", file=sys.stderr)
            return 1
        print(f"  [OK] {name} validated successfully")

    if args.validate_only:
        print("\nAll plans validated successfully.")
        return 0

    # 3. Render MP4s
    if not args.upload_only:
        print("\n--- Rendering MP4s ---")
        for name, plan_file in written_plans.items():
            mp4_file = OUT_DIR / f"{name}.mp4"
            if mp4_file.exists() and not args.force_render and mp4_file.stat().st_size > 100000:
                print(f"  [SKIP] {name}.mp4 exists ({mp4_file.stat().st_size} bytes)")
                continue

            print(f"  [RENDER] Rendering {name}...")
            t0 = time.time()
            cmd = [
                str(CHRONON_CLI), "render",
                "--plan", str(plan_file),
                "--assets-root", str(ASSETS_ROOT),
                "--backend", "software",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            dt = time.time() - t0
            if res.returncode != 0:
                print(f"  [FAIL] {name} render failed ({dt:.2f}s):\n{res.stderr or res.stdout}", file=sys.stderr)
                return 1
            print(f"  [OK] {name}.mp4 rendered in {dt:.2f}s ({mp4_file.stat().st_size} bytes)")

    # 4. Generate Posters
    print("\n--- Generating Posters ---")
    for name, _ in ITEMS:
        mp4_file = OUT_DIR / f"{name}.mp4"
        if not mp4_file.exists():
            print(f"  [WARN] Missing {mp4_file}, skipping poster")
            continue
        poster_file = OUT_DIR / f"{name}_poster.png"
        generate_poster(mp4_file, poster_file)
        print(f"  [poster] {poster_file.name} ready ({poster_file.stat().st_size} bytes)")

    if args.render_only:
        print("\nRendering & posters complete (render-only mode).")
        return 0

    # 5. Upload to Google Drive using RenderingGen/bin/drive-upload
    wants_upload = args.all or args.upload_only or (not args.render_only and not args.validate_only)
    if wants_upload:
        print("\n--- Uploading Deliverables to Drive via RenderingGen uploader ---")
        upload_manifest = {}
        for name, _ in ITEMS:
            mp4_file = OUT_DIR / f"{name}.mp4"
            poster_file = OUT_DIR / f"{name}_poster.png"

            if mp4_file.exists():
                print(f"  Uploading {mp4_file.name}...")
                res_mp4 = upload_via_drive_upload_cli(mp4_file, folder_id=drive_folder)
                print(f"    -> ID: {res_mp4.get('id')} | Link: {res_mp4.get('link')}")
                upload_manifest[mp4_file.name] = res_mp4

            if poster_file.exists():
                print(f"  Uploading {poster_file.name}...")
                res_poster = upload_via_drive_upload_cli(poster_file, folder_id=drive_folder)
                print(f"    -> ID: {res_poster.get('id')} | Link: {res_poster.get('link')}")
                upload_manifest[poster_file.name] = res_poster

        # Also upload sources.json
        sources_path = BASE_DIR / "ChrononTemplate/assets/famous_people_x4_v1/sources.json"
        if sources_path.exists():
            print(f"  Uploading sources.json...")
            res_src = upload_via_drive_upload_cli(sources_path, "sources.json", folder_id=drive_folder)
            upload_manifest["sources.json"] = res_src

        manifest_file = OUT_DIR / "upload_manifest.json"
        manifest_file.write_text(json.dumps(upload_manifest, indent=2))
        print(f"\nUpload manifest saved to {manifest_file}")

    print("\n=== Pipeline finished successfully ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
