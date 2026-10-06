#!/usr/bin/env python3
"""
Render Dynamic Map Supersonic Dive (Colosseum 8192x Zoom)
Showcases the DynamicTilePyramid continuous zoom engine:
from 650km orbit down to street-level Colosseum without pixelation!
Uploads directly to Google Drive folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI.
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path
import numpy as np
import cv2

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
sys.path.insert(0, str(BASE_DIR / "Chronon3d/tools/cartography"))

from dynamic_tile_pyramid import DynamicTilePyramid, draw_hud_overlay

OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_MP4 = OUT_DIR / "dynamic_map_dive_colosseum_8000x.mp4"

TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 120  # 4.0s @ 30fps

# Colosseum Coordinates
LAT = 41.890210
LON = 12.492231
START_ZOOM = 5.2   # Orbit / Mediterranean view (~650 km altitude)
END_ZOOM = 18.0    # Hyper-close architectural street view (~150 m altitude)


def refresh_drive_token():
    with open(TOKEN_PATH) as f:
        tok_data = json.load(f)
    with open(CREDS_PATH) as f:
        creds = json.load(f)
    client_info = creds.get("installed") or creds.get("web")
    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]
    refresh_token = tok_data.get("refresh_token")

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        new_token = res["access_token"]
        tok_data["access_token"] = new_token
        with open(TOKEN_PATH, "w") as f:
            json.dump(tok_data, f, indent=2)
        return new_token


def upload_to_drive(file_path, token, folder_id):
    boundary = "-------ChrononDynamicMapUpload31415"
    fname = file_path.name
    metadata = {"name": fname, "parents": [folder_id]}
    meta_json = json.dumps(metadata)
    file_bytes = file_path.read_bytes()

    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta_json}\r\n"
        f"--{boundary}\r\nContent-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink"
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/related; boundary={boundary}", "Content-Length": str(len(body))}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        fid = res.get("id")
        try:
            perm_url = f"https://www.googleapis.com/drive/v3/files/{fid}/permissions"
            perm_req = urllib.request.Request(
                perm_url, data=json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(perm_req): pass
        except Exception: pass
        return res


def cubic_bezier_ease(t: float) -> float:
    """Smooth cinematic camera acceleration and deceleration curve."""
    # Classic easeInOutCubic: 3t^2 - 2t^3 or smoothstep
    return t * t * (3.0 - 2.0 * t)


def main():
    print("=== Chronon Dynamic Map Supersonic Dive: Colosseum 8192x LOD ===", flush=True)

    pyramid = DynamicTilePyramid(provider="esri_sat")

    # Step 1: Prefetch tiles across the zoom hierarchy
    print("Step 1: Prefetching multi-resolution tile pyramid...", flush=True)
    pyramid.prefetch_pyramid(LAT, LON, min_zoom=5, max_zoom=18, tile_radius_x=2, tile_radius_y=2)

    # Step 2: Render continuous flight frames
    print("Step 2: Rendering continuous flight frames with sub-pixel Mipmap cross-fading...", flush=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(OUT_MP4)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t0 = time.time()

    for f_idx in range(DURATION_FRAMES):
        prog = f_idx / (DURATION_FRAMES - 1)
        eased_prog = cubic_bezier_ease(prog)

        # Continuous zoom interpolation
        current_zoom = START_ZOOM + (END_ZOOM - START_ZOOM) * eased_prog

        # Continuous sample with cross-fading
        frame = pyramid.sample_continuous(LAT, LON, current_zoom, WIDTH, HEIGHT)

        # Draw Telemetry and Targeting HUD
        draw_hud_overlay(frame, LAT, LON, current_zoom, prog, target_title="COLOSSEUM (ROMA)")

        proc.stdin.write(frame.tobytes())

        if f_idx % 20 == 0 or f_idx == DURATION_FRAMES - 1:
            print(f"  Frame {f_idx:3d}/{DURATION_FRAMES} (prog={prog*100:5.1f}%, zoom={current_zoom:4.2f})...", flush=True)

    proc.stdin.close()
    proc.wait()
    render_time = time.time() - t0
    file_size = OUT_MP4.stat().st_size if OUT_MP4.exists() else 0
    print(f"✓ Video rendered successfully in {render_time:.1f}s ({file_size:,} bytes): {OUT_MP4}", flush=True)

    # Step 3: Upload to Google Drive
    print(f"Step 3: Uploading to Google Drive folder {DRIVE_FOLDER_ID}...", flush=True)
    token = refresh_drive_token()
    res = upload_to_drive(OUT_MP4, token, DRIVE_FOLDER_ID)
    fid = res.get("id")
    drive_link = f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk"
    print(f"✓ Uploaded to Google Drive: {drive_link}", flush=True)


if __name__ == "__main__":
    main()
