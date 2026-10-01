#!/usr/bin/env python3
"""
Dynamic 3D Geospatial Fly-In & 3D Perspective Orbit Reveal (Colosseum).
Combines:
1. Supersonic 8192x continuous dive from orbit (z=5.2 -> 17.5) with DynamicTilePyramid.
2. Smooth transition to true 3D perspective flight (50° tilt pitch, 60° orbital sweep).
3. 3D holographic floating glass callout card locked to ShotAnchor with spring physics.
Uploads directly to Google Drive folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI.
"""

import sys
import math
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

from dynamic_tile_pyramid import DynamicTilePyramid, draw_hud_overlay, compute_altitude_km, latlon_to_global_px

OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_MP4 = OUT_DIR / "dynamic_map_3d_orbit_colosseum_epic.mp4"

TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
TOTAL_FRAMES = 150  # 5.0 seconds @ 30fps

# Colosseum Coordinates
LAT = 41.890210
LON = 12.492231


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
    boundary = "-------ChrononDynamicMapUpload3D777"
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


def compute_perspective_homography(pitch_deg: float, yaw_deg: float, roll_deg: float,
                                  fov_deg: float = 60.0, width: int = 1920, height: int = 1080) -> np.ndarray:
    """Computes exact 3D camera ground-plane projection homography matrix."""
    f = (height * 0.5) / math.tan(math.radians(fov_deg * 0.5))
    cx, cy = width * 0.5, height * 0.5

    rx = math.radians(pitch_deg)
    ry = math.radians(yaw_deg)
    rz = math.radians(roll_deg)

    # 3D Euler rotation
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]], dtype=np.float64)
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]], dtype=np.float64)
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]], dtype=np.float64)
    R = Rz @ Rx @ Ry

    # Camera looking at ground plane Z=0 from height h_cam
    h_cam = f
    t = np.array([0, 0, h_cam], dtype=np.float64)

    # Intrinsic matrix
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], dtype=np.float64)

    # Ground plane homography columns (r1, r2, t)
    H_3d = K @ np.column_stack((R[:, 0], R[:, 1], t))
    H_norm = H_3d / H_3d[2, 2]
    return H_norm


def draw_3d_holographic_pin_and_card(frame: np.ndarray, anchor_screen: tuple[int, int],
                                     progress: float, title: str = "ANFITEATRO FLAVIO (COLOSSEO)"):
    """Draws a glowing 3D anchor beacon, vertical leader line, and floating frosted glass card."""
    ax, ay = anchor_screen
    h, w = frame.shape[:2]

    # Spring reveal factor
    card_alpha = min(1.0, max(0.0, (progress - 0.70) / 0.20))
    if card_alpha <= 0.01:
        return

    # 1. Ground Pulse Rings
    for ring_idx in range(3):
        t_phase = (progress * 2.5 + ring_idx * 0.33) % 1.0
        r_ring = int(15 + 65 * t_phase)
        a_ring = max(0.0, 1.0 - t_phase) * card_alpha
        col_ring = (int(0 * a_ring), int(240 * a_ring), int(255 * a_ring))
        cv2.circle(frame, (ax, ay), r_ring, col_ring, 2, cv2.LINE_AA)

    # Ground core dot
    cv2.circle(frame, (ax, ay), 5, (0, 240, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, (ax, ay), 7, (255, 255, 255), 2, cv2.LINE_AA)

    # 2. Vertical 3D Leader Line extending upward into the air
    stem_height = int(140 * min(1.0, card_alpha * 1.5))
    top_x = ax + 35
    top_y = ay - stem_height

    cv2.line(frame, (ax, ay), (top_x, top_y), (0, 240, 255), 2, cv2.LINE_AA)
    cv2.circle(frame, (top_x, top_y), 4, (0, 240, 255), -1, cv2.LINE_AA)

    # 3. Floating Glass Hologram Card
    card_w = 480
    card_h = 135
    card_x = top_x + 15
    card_y = top_y - card_h // 2

    # Clamped on screen
    card_x = max(20, min(w - card_w - 20, card_x))
    card_y = max(40, min(h - card_h - 40, card_y))

    # Frosted glass background
    sub = frame[card_y:card_y + card_h, card_x:card_x + card_w]
    if sub.shape[0] == card_h and sub.shape[1] == card_w:
        blurred = cv2.GaussianBlur(sub, (21, 21), 0)
        # Dark tint
        glass_tint = np.full((card_h, card_w, 3), (15, 20, 32), dtype=np.uint8)
        composite_glass = cv2.addWeighted(blurred, 0.4, glass_tint, 0.6, 0)
        # Apply card_alpha fade
        frame[card_y:card_y + card_h, card_x:card_x + card_w] = cv2.addWeighted(
            sub, 1.0 - card_alpha, composite_glass, card_alpha, 0
        )

    # Card border with cyan glow
    cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 240, 255), 2, cv2.LINE_AA)
    cv2.rectangle(frame, (card_x - 1, card_y - 1), (card_x + card_w + 1, card_y + card_h + 1), (30, 60, 90), 1, cv2.LINE_AA)

    # Horizontal connector rule
    cv2.line(frame, (top_x, top_y), (card_x, top_y), (0, 240, 255), 2, cv2.LINE_AA)

    # Text content inside card
    cv2.putText(frame, "GEOSPATIAL SHOT ANCHOR", (card_x + 20, card_y + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, title, (card_x + 20, card_y + 64),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "ROMA IMPERIALE • CA. AD 80 • PATRIMONIO UNESCO", (card_x + 20, card_y + 92),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 200, 220), 1, cv2.LINE_AA)
    cv2.putText(frame, f"WGS84: {LAT:.6f}° N, {LON:.6f}° E  |  ELEV: 50m", (card_x + 20, card_y + 116),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 240, 255), 1, cv2.LINE_AA)


def main():
    print("=== Chronon Dynamic Map: 3D Supersonic Dive + 3D Orbit Reveal ===", flush=True)

    pyramid = DynamicTilePyramid(provider="esri_sat")

    # Step 1: Prefetch multi-resolution tile pyramid (radius 3 to ensure wide coverage during 3D tilt)
    print("Step 1: Prefetching multi-resolution tile pyramid (z=5..18)...", flush=True)
    pyramid.prefetch_pyramid(LAT, LON, min_zoom=5, max_zoom=18, tile_radius_x=3, tile_radius_y=3)

    # Step 2: Render continuous 3D camera trajectory
    print(f"Step 2: Rendering {TOTAL_FRAMES} frames (Dive + 3D Perspective Orbit)...", flush=True)

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

    for f_idx in range(TOTAL_FRAMES):
        prog = f_idx / (TOTAL_FRAMES - 1)

        # Trajectory phases:
        # Phase 1: 0.0 -> 0.65 : Supersonic dive from z=5.2 to z=17.5 (altitude 650km -> 200m)
        # Phase 2: 0.65 -> 1.00 : 3D perspective pitch tilt (0° -> 46°) and orbital yaw sweep (0° -> 55°)
        if prog <= 0.65:
            dive_p = prog / 0.65
            eased_dive = dive_p * dive_p * (3.0 - 2.0 * dive_p)
            current_zoom = 5.2 + (17.5 - 5.2) * eased_dive
            pitch_deg = 0.0
            yaw_deg = 0.0
            roll_deg = 0.0
        else:
            orbit_p = (prog - 0.65) / 0.35
            eased_orbit = orbit_p * orbit_p * (3.0 - 2.0 * orbit_p)
            current_zoom = 17.5 + 0.3 * eased_orbit
            pitch_deg = 48.0 * eased_orbit
            yaw_deg = 52.0 * eased_orbit
            roll_deg = -8.0 * math.sin(eased_orbit * math.pi)  # dynamic banking

        # Render base plate
        if pitch_deg < 0.5:
            # Nadir orthogonal continuous sample
            frame = pyramid.sample_continuous(LAT, LON, current_zoom, WIDTH, HEIGHT)
            anchor_screen = (WIDTH // 2, HEIGHT // 2)
        else:
            # 3D Perspective Flight!
            # Render oversized canvas at current zoom level to avoid edge clipping during 3D warp
            oversize_w = int(WIDTH * 1.5)
            oversize_h = int(HEIGHT * 1.5)
            base_plate = pyramid.sample_continuous(LAT, LON, current_zoom, oversize_w, oversize_h)

            # 3D homography matrix
            H = compute_perspective_homography(pitch_deg, yaw_deg, roll_deg, fov_deg=58.0, width=WIDTH, height=HEIGHT)

            # Center shift offset
            dx = (oversize_w - WIDTH) * 0.5
            dy = (oversize_h - HEIGHT) * 0.5
            T_shift = np.array([[1, 0, -dx], [0, 1, -dy], [0, 0, 1]], dtype=np.float64)
            H_eff = H @ T_shift

            # Warp perspective
            frame = cv2.warpPerspective(base_plate, H_eff, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

            # Projected ShotAnchor position
            center_pt = np.array([oversize_w * 0.5, oversize_h * 0.5, 1.0], dtype=np.float64)
            proj_pt = H_eff @ center_pt
            if proj_pt[2] != 0:
                ax = int(round(proj_pt[0] / proj_pt[2]))
                ay = int(round(proj_pt[1] / proj_pt[2]))
            else:
                ax, ay = WIDTH // 2, HEIGHT // 2
            anchor_screen = (ax, ay)

        # 3D Holographic Pin and Floating Glass Card (in phase 2)
        draw_3d_holographic_pin_and_card(frame, anchor_screen, prog, title="ANFITEATRO FLAVIO (COLOSSEO)")

        # Documentary Telemetry HUD
        draw_hud_overlay(frame, LAT, LON, current_zoom, prog, target_title="COLOSSEUM (ROMA 3D)")

        proc.stdin.write(frame.tobytes())

        if f_idx % 25 == 0 or f_idx == TOTAL_FRAMES - 1:
            print(f"  Frame {f_idx:3d}/{TOTAL_FRAMES} (prog={prog*100:5.1f}%, zoom={current_zoom:4.2f}, pitch={pitch_deg:4.1f}°, yaw={yaw_deg:4.1f}°)...", flush=True)

    proc.stdin.close()
    proc.wait()

    render_time = time.time() - t0
    file_size = OUT_MP4.stat().st_size if OUT_MP4.exists() else 0
    print(f"✓ Epic 3D Video rendered successfully in {render_time:.1f}s ({file_size:,} bytes): {OUT_MP4}", flush=True)

    # Step 3: Upload to Google Drive
    print(f"Step 3: Uploading to Google Drive folder {DRIVE_FOLDER_ID}...", flush=True)
    token = refresh_drive_token()
    res = upload_to_drive(OUT_MP4, token, DRIVE_FOLDER_ID)
    fid = res.get("id")
    drive_link = f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk"
    print(f"✓ Uploaded Epic 3D Video to Google Drive: {drive_link}", flush=True)


if __name__ == "__main__":
    main()
