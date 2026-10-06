#!/usr/bin/env python3
"""
Chronon Kinetic Center Build Suite V1: Native HyperFrames Port

Recreates the Remocn / HyperFrames "Kinetic Center Build" kinetic typography style:
Words enter from the right with an offset while existing words shift left, keeping
every intermediate phrase dynamically centered at X=0 until the final phrase locks.

Variations:
  01. kinetic_01_words_push_left       - "Words push left." (Canonical Remocn Studio Light)
  02. kinetic_02_precision_flow        - "Create with precision." (Darkroom Obsidian + Indigo Accent)
  03. kinetic_03_four_words_momentum   - "Focus creates real momentum." (4-word High-Contrast Monochrome)
  04. kinetic_04_speed_advantage       - "Speed is your advantage." (Dark Carbon + Electric Cyan Highlight)
  05. kinetic_05_simplicity_scales     - "Simplicity scales without limits." (Warm Luxury + Amber Highlight)

Target Google Drive folder:
  16HRHVZoFLV4EdBf_7NN7DdzHiaOVq-dJ
Uploads ONLY MP4 videos (no PNGs).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from PIL import ImageFont

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing").resolve()
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
DRIVE_UPLOAD_CLI = BASE_DIR / "RenderingGen/bin/drive-upload"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/kinetic_center_build_suite_v1"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "16HRHVZoFLV4EdBf_7NN7DdzHiaOVq-dJ"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 120  # 4.0 seconds
END = DURATION_FRAMES - 1


def clean_keyframes(kfs: list[dict]) -> list[dict]:
    seen = {}
    for kf in kfs:
        seen[kf["frame"]] = kf["value"]
    return [{"frame": f, "value": seen[f]} for f in sorted(seen.keys())]


def build_kinetic_center_plan(
    job_id: str,
    text: str,
    *,
    font_path: str = "assets/fonts/Inter-Bold.ttf",
    font_size: int = 84,
    gap_ratio: float = 0.28,
    entry_offset: float = 88.0,
    bg_color: list[float] = [0.95, 0.95, 0.96, 1.0],
    text_color: str = "#171717",
    accent_word_idx: int | None = None,
    accent_color: str | None = None,
    step_duration: int = 16,
    anim_duration: int = 12,
    y_center: float = 540.0,
) -> dict:
    abs_font_path = ASSETS_ROOT / font_path
    pil_font = ImageFont.truetype(str(abs_font_path), font_size)

    words = text.strip().split()
    N = len(words)
    widths = [pil_font.getlength(w) for w in words]
    gap = font_size * gap_ratio

    # Calculate exact center position of each word at each stage k (0 <= k < N)
    def pos(k: int, j: int) -> float:
        total_w = sum(widths[: k + 1]) + k * gap
        left = (WIDTH / 2.0) - (total_w / 2.0)
        return left + sum(widths[:j]) + j * gap + (widths[j] / 2.0)

    layers = [
        {
            "id": "background",
            "type": "color",
            "color": bg_color,
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
        }
    ]

    for j in range(N):
        base_x = pos(N - 1, j)
        start_f = j * step_duration

        pos_x_kfs = []
        opacity_kfs = []
        scale_kfs = []

        # Before entry, word is completely hidden
        if start_f > 0:
            opacity_kfs.append({"frame": 0, "value": 0.0})
            opacity_kfs.append({"frame": start_f, "value": 0.0})

        # Entry keyframes for word j
        entry_val = (pos(j, j) - base_x) + entry_offset
        land_val = pos(j, j) - base_x

        pos_x_kfs.append({"frame": start_f, "value": round(entry_val, 2)})
        pos_x_kfs.append({"frame": start_f + anim_duration, "value": round(land_val, 2)})

        opacity_kfs.append({"frame": start_f, "value": 0.0})
        opacity_kfs.append({"frame": start_f + min(6, anim_duration), "value": 1.0})

        scale_kfs.append({"frame": start_f, "value": 0.96})
        scale_kfs.append({"frame": start_f + anim_duration, "value": 1.0})

        # Subsequent steps k > j: word j shifts left as new words enter from the right
        for k in range(j + 1, N):
            shift_start = k * step_duration
            shift_end = shift_start + anim_duration
            from_val = pos(k - 1, j) - base_x
            to_val = pos(k, j) - base_x
            pos_x_kfs.append({"frame": shift_start, "value": round(from_val, 2)})
            pos_x_kfs.append({"frame": shift_end, "value": round(to_val, 2)})

        # Final hold keyframe at end of composition
        pos_x_kfs.append({"frame": END, "value": 0.0})
        opacity_kfs.append({"frame": END, "value": 1.0})
        scale_kfs.append({"frame": END, "value": 1.0})

        fill = accent_color if (accent_word_idx is not None and j == accent_word_idx) else text_color

        layers.append({
            "id": f"word_{j}",
            "type": "text",
            "text": words[j],
            "size": [round(widths[j] + 80), round(font_size * 2.0)],
            "position": [round(base_x, 2), y_center],
            "style": {
                "font": font_path,
                "font_size": float(font_size),
                "fill": fill,
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "position_x", "easing": "out_cubic", "keyframes": clean_keyframes(pos_x_kfs)},
                    {"property": "opacity", "easing": "out_cubic", "keyframes": clean_keyframes(opacity_kfs)},
                    {"property": "scale", "easing": "out_cubic", "keyframes": clean_keyframes(scale_kfs)},
                ]
            },
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
    # 01: Canonical Remocn reference phrase in Studio Light
    (
        "kinetic_01_words_push_left",
        lambda: build_kinetic_center_plan(
            "kinetic_01_words_push_left",
            "Words push left.",
            font_path="assets/fonts/Inter-Bold.ttf",
            font_size=92,
            bg_color=[0.95, 0.95, 0.96, 1.0],  # #F2F3F5
            text_color="#171717",
            entry_offset=88.0,
            step_duration=18,
            anim_duration=13,
        ),
    ),
    # 02: Modern Darkroom Obsidian + Indigo Accent
    (
        "kinetic_02_precision_flow",
        lambda: build_kinetic_center_plan(
            "kinetic_02_precision_flow",
            "Create with precision.",
            font_path="assets/fonts/Poppins-Bold.ttf",
            font_size=88,
            bg_color=[0.047, 0.051, 0.071, 1.0],  # #0C0D12
            text_color="#F8FAFC",
            accent_word_idx=2,  # "precision."
            accent_color="#818CF8",
            entry_offset=90.0,
            step_duration=18,
            anim_duration=13,
        ),
    ),
    # 03: 4-word High-Contrast Monochrome Impact
    (
        "kinetic_03_four_words_momentum",
        lambda: build_kinetic_center_plan(
            "kinetic_03_four_words_momentum",
            "Focus creates real momentum.",
            font_path="assets/fonts/Inter-Bold.ttf",
            font_size=78,
            bg_color=[0.02, 0.02, 0.03, 1.0],  # #050508
            text_color="#FFFFFF",
            entry_offset=80.0,
            step_duration=16,
            anim_duration=12,
        ),
    ),
    # 04: Dark Carbon + Electric Cyan Highlight
    (
        "kinetic_04_speed_advantage",
        lambda: build_kinetic_center_plan(
            "kinetic_04_speed_advantage",
            "Speed is your advantage.",
            font_path="assets/fonts/Space-Grotesk.ttf",
            font_size=80,
            bg_color=[0.059, 0.067, 0.090, 1.0],  # #0F1117
            text_color="#E2E8F0",
            accent_word_idx=3,  # "advantage."
            accent_color="#38BDF8",
            entry_offset=85.0,
            step_duration=16,
            anim_duration=12,
        ),
    ),
    # 05: Warm Luxury Studio + Amber Bronze Highlight
    (
        "kinetic_05_simplicity_scales",
        lambda: build_kinetic_center_plan(
            "kinetic_05_simplicity_scales",
            "Simplicity scales without limits.",
            font_path="assets/fonts/Montserrat-Bold.ttf",
            font_size=74,
            bg_color=[0.976, 0.973, 0.965, 1.0],  # #F9F8F6
            text_color="#1C1917",
            accent_word_idx=3,  # "limits."
            accent_color="#D97706",
            entry_offset=76.0,
            step_duration=15,
            anim_duration=11,
        ),
    ),
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
    data = {}
    for part in out.split():
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v
    data["local_path"] = str(file_path)
    data["sha256"] = expected_sha
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Render and upload Kinetic Center Build typography suite.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate plans with chronon3d_cli")
    parser.add_argument("--render-only", action="store_true", help="Validate and render MP4s without upload")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing MP4s to Drive")
    parser.add_argument("--force-render", action="store_true", help="Re-render even if MP4 exists")
    parser.add_argument("--drive-folder", type=str, default=DEFAULT_DRIVE_FOLDER, help="Target Google Drive folder ID")
    parser.add_argument("--jobs", type=int, default=2, help="Parallel renders")
    args = parser.parse_args()

    drive_folder = args.drive_folder
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== Chronon Kinetic Center Build Suite (Native HyperFrames Port) ===")
    print(f"Output directory: {OUT_DIR}")
    print(f"Assets root:      {ASSETS_ROOT}")
    print(f"Drive Folder ID:  {drive_folder}")

    # 1. Write plans
    written_plans: dict[str, Path] = {}
    for job_id, builder in PRESETS:
        plan_dict = builder()
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
        print(f"  [OK] {job_id} validated successfully")

    if args.validate_only:
        print("\nAll plans validated successfully.")
        return 0

    # 3. Render MP4s
    if not args.upload_only:
        print(f"\n--- Rendering MP4s (Jobs: {args.jobs}, Backend: software) ---")
        todo = []
        for job_id, plan_file in written_plans.items():
            mp4_file = OUT_DIR / f"{job_id}.mp4"
            if mp4_file.exists() and not args.force_render and mp4_file.stat().st_size > 100000:
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

    # 4. Upload MP4 Videos ONLY to Google Drive
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
    print("\n=== All Kinetic Center Build Videos Uploaded Successfully ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
