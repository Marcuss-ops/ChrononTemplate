#!/usr/bin/env python3
"""Render and Upload the 3 Glow Line comparison videos to Google Drive.

Produces:
  01 GlowLine_Basic.mp4        (Baseline neon tube)
  02 GlowLine_Cinematic.mp4    (Multi-layer glow + bloom)
  03 GlowLine_DocusPremium.mp4 (Full documentary motion graphics flagship)

Renders with Chronon3D CLI: 1920x1080 @ 30 FPS, 150 frames (5.0s).
Uploads to Google Drive folder: 1ZShFShvCn5Lyf57XD0HfVBKhgYJxbMP_
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple, List

# Add current dir to python path
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOL_DIR)

from glow_line_composers import (
    build_glow_line_basic_plan,
    build_glow_line_cinematic_plan,
    build_glow_line_docus_premium_plan,
    W, H, FPS, DURATION_FRAMES
)

BASE_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
CLI_PATH = os.path.join(
    BASE_DIR, "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
)
UPLOADER = os.path.join(BASE_DIR, "RenderingGen/bin/drive-upload")
DRIVE_FOLDER = "1ZShFShvCn5Lyf57XD0HfVBKhgYJxbMP_"
CREDS_JSON = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN_JSON = os.path.expanduser("~/.config/velox/token.json")

PLANS_DIR = os.path.join(BASE_DIR, "ChrononTemplate/catalog/glow_line/plans")
OUT_DIR = os.path.join(BASE_DIR, "output/glow_line_showcase")
os.makedirs(PLANS_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def upload_file(local_path: str, file_name: str, subfolder: str = None) -> str:
    """Upload file to Google Drive using drive-upload binary."""
    if not os.path.exists(local_path):
        print(f"[DRIVE ERROR] File not found: {local_path}")
        return ""
    cmd = [
        UPLOADER,
        "-credentials", CREDS_JSON,
        "-token", TOKEN_JSON,
        "-folder", DRIVE_FOLDER,
        "-file", local_path,
        "-name", file_name
    ]
    if subfolder:
        cmd.extend(["-subfolder", subfolder])

    print(f"\n[DRIVE] Uploading {file_name} ({os.path.getsize(local_path) / 1024:.1f} KB) to folder {DRIVE_FOLDER}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    print(f"[DRIVE] {out}")
    if res.stderr.strip():
        print(f"[DRIVE STDERR] {res.stderr.strip()}")

    link = ""
    for token in out.split():
        if token.startswith("link="):
            link = token.split("link=")[1]
    return link


def render_plan(plan_path: str, output_mp4: str) -> Tuple[bool, float]:
    """Execute chronon3d_cli render on plan."""
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)
    cmd = [
        CLI_PATH, "render",
        "--assets-root", BASE_DIR,
        "--plan", plan_path,
        "-v", "warn",
        "-o", output_mp4
    ]
    print(f"\n[RENDER] Invoking Chronon3D CLI on {os.path.basename(plan_path)} -> {os.path.basename(output_mp4)}...")
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"[RENDER ERROR] returncode={res.returncode}")
        print(f"[STDERR]\n{res.stderr[-600:]}")
        return False, elapsed

    size_kb = os.path.getsize(output_mp4) / 1024.0 if os.path.exists(output_mp4) else 0.0
    print(f"[RENDER SUCCESS] Took {elapsed:.2f}s | Output size: {size_kb:.1f} KB")
    return True, elapsed


def extract_preview_stills(video_path: str, base_name: str, frames: List[int]) -> List[str]:
    """Extract key still frames from rendered video in milliseconds using ffmpeg."""
    stills = []
    for f in frames:
        out_png = os.path.join(OUT_DIR, f"{base_name}_frame_{f:03d}.png")
        t_sec = f / float(FPS)
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{t_sec:.3f}",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_png
        ]
        subprocess.run(cmd, capture_output=True)
        if os.path.exists(out_png):
            stills.append(out_png)
    return stills



def main():
    print("=" * 72)
    print("DOCUS GLOW LINE 3-TIER COMPARISON GENERATOR & RENDERER")
    print(f"Canvas: {W}x{H} @ {FPS}fps | Duration: {DURATION_FRAMES} frames (5.0s)")
    print(f"Destination Drive Folder: {DRIVE_FOLDER}")
    print("=" * 72)

    tier_specs = [
        ("01_Basic", "GlowLine_Basic", build_glow_line_basic_plan),
        ("02_Cinematic", "GlowLine_Cinematic", build_glow_line_cinematic_plan),
        ("03_DocusPremium", "GlowLine_DocusPremium", build_glow_line_docus_premium_plan),
    ]

    manifest = []

    for tier_tag, name, builder in tier_specs:
        print(f"\n-------------------------------------------------------------")
        print(f"PREPARING: {name} ({tier_tag})")
        print(f"-------------------------------------------------------------")

        # 1. Build and serialize plan JSON
        plan = builder()
        plan_file = os.path.join(PLANS_DIR, f"{name}.plan.json")
        out_mp4 = os.path.join(OUT_DIR, f"{name}.mp4")
        plan["output"]["path"] = out_mp4

        with open(plan_file, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"[PLAN] Written plan to {plan_file} ({len(plan['layers'])} layers)")

        # 2. Render MP4
        ok, elapsed = render_plan(plan_file, out_mp4)
        if not ok or not os.path.exists(out_mp4):
            print(f"[ERROR] Failed rendering {out_mp4}")
            continue

        # 3. Render preview stills at frame 60 (mid-transit) and frame 105 (arrival)
        stills = extract_preview_stills(out_mp4, name, [60, 105])
        print(f"[STILLS] Rendered {len(stills)} verification stills")

        # 4. Upload MP4 to Google Drive
        drive_name = f"{name}.mp4"
        link = upload_file(out_mp4, drive_name)

        manifest.append({
            "tier": tier_tag,
            "name": drive_name,
            "local_path": out_mp4,
            "plan_path": plan_file,
            "drive_link": link,
            "file_size_bytes": os.path.getsize(out_mp4),
            "render_time_seconds": round(elapsed, 2)
        })

    # Save manifest
    manifest_path = os.path.join(OUT_DIR, "glow_line_upload_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 72)
    print("ALL 3 GLOW LINE VIDEOS RENDERED AND UPLOADED!")
    print(f"Manifest written to: {manifest_path}")
    print("=" * 72)
    for entry in manifest:
        print(f" • [{entry['tier']}] {entry['name']}")
        print(f"   Drive Link : {entry['drive_link']}")
        print(f"   Render Time: {entry['render_time_seconds']}s | Size: {entry['file_size_bytes'] / 1024:.1f} KB\n")


if __name__ == "__main__":
    from typing import Tuple, List
    main()
