#!/usr/bin/env python3
"""
ChrononMotion3D Camera Motion V1 Showcase Suite
Renders 1920x1080 30fps MP4 videos demonstrating all 15 authoritative camera recipes
plus the 16.0s master canary showcase, and uploads them to Google Drive.

Target Google Drive Folder: 1Ui83Bp9du7EFkROX6qdq3S0G-_sT5MmP
"""

import os
import sys
import json
import math
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import cv2

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
TRAJECTORIES_JSON = BASE_DIR / "ChrononMotion3D/out/camera_motion_trajectories.json"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/camera_motion_v2"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"

WIDTH = 1920
HEIGHT = 1080
FPS = 30

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Pre-bake base dark canvas with vertical gradient once
_base = np.full((HEIGHT, WIDTH, 3), (12, 16, 26), dtype=np.uint8)
_grad = np.linspace(0.85, 1.15, HEIGHT)[:, None, None]
BASE_CANVAS = np.clip(_base.astype(np.float32) * _grad, 0, 255).astype(np.uint8)


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


def quat_to_matrix(quat):
    x, y, z, w = quat
    return np.array([
        [1.0 - 2.0*(y**2 + z**2), 2.0*(x*y - z*w),       2.0*(x*z + y*w)],
        [2.0*(x*y + z*w),       1.0 - 2.0*(x**2 + z**2), 2.0*(y*z - x*w)],
        [2.0*(x*z - y*w),       2.0*(y*z + x*w),       1.0 - 2.0*(x**2 + y**2)]
    ], dtype=np.float32)


def project_point(pt, cam_pos, R, fov):
    rel = pt - cam_pos
    cam_space = R.T @ rel
    # In Three.js camera space: -Z is optical forward, +X is right, +Y is up
    if cam_space[2] >= -0.05:
        return None, cam_space[2] # Behind or clipping camera

    dist = -cam_space[2]
    tan_half_fov = math.tan(math.radians(fov * 0.5))
    aspect = WIDTH / HEIGHT

    ndc_x = cam_space[0] / (dist * tan_half_fov * aspect)
    ndc_y = cam_space[1] / (dist * tan_half_fov)

    screen_x = (ndc_x + 1.0) * 0.5 * WIDTH
    screen_y = (1.0 - ndc_y) * 0.5 * HEIGHT
    return (screen_x, screen_y), dist


def hex_to_bgr(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (b, g, r)
    return (255, 255, 255)


def create_card_texture(entity, w_px=960, h_px=640):
    tex = np.zeros((h_px, w_px, 4), dtype=np.uint8)
    bgr = hex_to_bgr(entity.get("color", "#00F0FF"))

    # Glass background fill with gradient
    for y in range(h_px):
        alpha_val = int(220 + 30 * (y / h_px))
        dark_factor = 0.08 + 0.04 * (y / h_px)
        tex[y, :, 0] = int(14 * (1.0 - dark_factor) + bgr[0] * dark_factor)
        tex[y, :, 1] = int(20 * (1.0 - dark_factor) + bgr[1] * dark_factor)
        tex[y, :, 2] = int(32 * (1.0 - dark_factor) + bgr[2] * dark_factor)
        tex[y, :, 3] = alpha_val

    # Glowing outer border
    cv2.rectangle(tex, (6, 6), (w_px - 7, h_px - 7), (*bgr, 255), 4, cv2.LINE_AA)
    cv2.rectangle(tex, (12, 12), (w_px - 13, h_px - 13), (*[int(c * 0.6) for c in bgr], 200), 2, cv2.LINE_AA)

    # Corner brackets
    bracket_len = 50
    for cx, cy, sx, sy in [(16, 16, 1, 1), (w_px - 17, 16, -1, 1), (16, h_px - 17, 1, -1), (w_px - 17, h_px - 17, -1, -1)]:
        cv2.line(tex, (cx, cy), (cx + sx * bracket_len, cy), (255, 255, 255, 255), 3, cv2.LINE_AA)
        cv2.line(tex, (cx, cy), (cx, cy + sy * bracket_len), (255, 255, 255, 255), 3, cv2.LINE_AA)

    # Top Header Pill
    cat_text = entity.get("category", "ENTITY COMPONENT").upper()
    cv2.rectangle(tex, (40, 40), (440, 84), (*bgr, 220), -1)
    cv2.circle(tex, (64, 62), 7, (255, 255, 255, 255), -1)
    cv2.putText(tex, cat_text, (85, 70), cv2.FONT_HERSHEY_DUPLEX, 0.75, (10, 15, 25, 255), 2, cv2.LINE_AA)

    # Tag Badge
    tag_text = entity.get("tag", "NODE").upper()
    cv2.putText(tex, tag_text, (w_px - 280, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (*bgr, 255), 2, cv2.LINE_AA)

    # Large Main Title
    title = entity.get("title", "SUBJECT").upper()
    cv2.putText(tex, title, (45, 180), cv2.FONT_HERSHEY_DUPLEX, 1.8, (250, 252, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(tex, title, (45, 180), cv2.FONT_HERSHEY_DUPLEX, 1.8, (*bgr, 255), 1, cv2.LINE_AA)

    # Subtitle separator
    cv2.line(tex, (45, 215), (w_px - 45, 215), (80, 100, 130, 200), 2, cv2.LINE_AA)

    # Metadata & Coordinates
    pos = entity.get("position", [0, 0, 0])
    coord_str = f"WORLD XYZ:  [{pos[0]:+.2f}m,  {pos[1]:+.2f}m,  {pos[2]:+.2f}m]"
    cv2.putText(tex, coord_str, (45, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (180, 200, 225, 255), 2, cv2.LINE_AA)

    status_str = f"ID: {entity.get('id', 'N/A')}  |  OPTICAL TRACKING: LOCKED  |  ANCHOR: PRIMARY"
    cv2.putText(tex, status_str, (45, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (130, 160, 195, 255), 1, cv2.LINE_AA)

    # Visual Accent Graphic (Mini Grid / Waveform)
    grid_ox, grid_oy, grid_w, grid_h = 45, 360, w_px - 90, 220
    cv2.rectangle(tex, (grid_ox, grid_oy), (grid_ox + grid_w, grid_oy + grid_h), (35, 45, 65, 180), -1)
    cv2.rectangle(tex, (grid_ox, grid_oy), (grid_ox + grid_w, grid_oy + grid_h), (*[int(c * 0.5) for c in bgr], 200), 1)

    # Internal tech grid lines
    for gx in range(grid_ox, grid_ox + grid_w, 40):
        cv2.line(tex, (gx, grid_oy), (gx, grid_oy + grid_h), (45, 55, 80, 100), 1)
    for gy in range(grid_oy, grid_oy + grid_h, 30):
        cv2.line(tex, (grid_ox, gy), (grid_ox + grid_w, gy), (45, 55, 80, 100), 1)

    # Stylized waveform inside graphic box
    pts = []
    for i in range(120):
        x = grid_ox + 20 + int(i * (grid_w - 40) / 119)
        y = grid_oy + int(grid_h * 0.5 + math.sin(i * 0.25) * 45.0 * math.cos(i * 0.1))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        cv2.line(tex, pts[i], pts[i+1], (*bgr, 255), 2, cv2.LINE_AA)

    return tex


def render_scene(scene_data, out_mp4_path):
    print(f"-> Rendering scene: {scene_data['id']} ({scene_data['duration_frames']} frames)...", flush=True)
    t0 = time.time()

    # Pre-render card textures
    card_textures = {}
    for ent in scene_data["entities"]:
        card_textures[ent["id"]] = create_card_texture(ent)

    # FFmpeg pipe
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out_mp4_path)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    total_frames = scene_data["duration_frames"]

    for f_idx in range(total_frames):
        frame_data = scene_data["frames"][f_idx]
        cam_pos = np.array(frame_data["position"], dtype=np.float32)
        quat = frame_data["quaternion"]
        R = quat_to_matrix(quat)
        fov = frame_data["fov"]
        focus_dist = frame_data["focus_distance"]
        aperture = frame_data["aperture"]
        target_pos = np.array(frame_data["target"], dtype=np.float32)

        # Base canvas: dark studio background
        frame = BASE_CANVAS.copy()

        # 1. 3D Spatial Floor Grid
        grid_y = -3.8
        grid_lines = []
        for x in range(-35, 40, 5):
            p1 = np.array([x, grid_y, -60.0], dtype=np.float32)
            p2 = np.array([x, grid_y, 20.0], dtype=np.float32)
            sp1, d1 = project_point(p1, cam_pos, R, fov)
            sp2, d2 = project_point(p2, cam_pos, R, fov)
            if sp1 and sp2 and d1 > 0.5 and d2 > 0.5:
                grid_lines.append((sp1, sp2, (35, 45, 65)))
        for z in range(-60, 25, 5):
            p1 = np.array([-35.0, grid_y, z], dtype=np.float32)
            p2 = np.array([35.0, grid_y, z], dtype=np.float32)
            sp1, d1 = project_point(p1, cam_pos, R, fov)
            sp2, d2 = project_point(p2, cam_pos, R, fov)
            if sp1 and sp2 and d1 > 0.5 and d2 > 0.5:
                grid_lines.append((sp1, sp2, (35, 45, 65)))

        for (x1, y1), (x2, y2), col in grid_lines:
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), col, 1, cv2.LINE_AA)

        # 2. Project and sort Entities along depth
        render_entities = []
        for ent in scene_data["entities"]:
            e_pos = np.array(ent["position"], dtype=np.float32)
            e_rot = ent.get("rotation_deg", [0, 0, 0])
            w, h = ent.get("size", [4.8, 3.2])
            w2, h2 = w * 0.5, h * 0.5

            # Local corner points
            corners_local = [
                np.array([-w2,  h2, 0.0], dtype=np.float32),
                np.array([ w2,  h2, 0.0], dtype=np.float32),
                np.array([ w2, -h2, 0.0], dtype=np.float32),
                np.array([-w2, -h2, 0.0], dtype=np.float32),
            ]

            # Full 3D rotation (Rx, Ry, Rz)
            rx, ry, rz = [math.radians(a) for a in e_rot]
            Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]], dtype=np.float32)
            Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]], dtype=np.float32)
            Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]], dtype=np.float32)
            R_ent = Ry @ Rx @ Rz

            world_corners = [e_pos + R_ent @ c for c in corners_local]

            # Project corners
            proj_corners = []
            dists = []
            valid = True
            for wc in world_corners:
                sp, d = project_point(wc, cam_pos, R, fov)
                if sp is None or d < 0.2:
                    valid = False
                    break
                proj_corners.append(sp)
                dists.append(d)

            if valid:
                center_dist = float(np.mean(dists))
                render_entities.append((center_dist, ent, proj_corners))

        # Sort far to near (painter's algorithm)
        render_entities.sort(key=lambda item: item[0], reverse=True)

        # Draw Entities with Bounding-Box Alpha Slicing for maximum speed
        for center_dist, ent, proj_corners in render_entities:
            tex = card_textures[ent["id"]]
            th, tw = tex.shape[:2]

            # Calculate Depth of Field (defocus blur)
            if aperture > 0.0:
                dist_delta = abs(center_dist - focus_dist)
                blur_r = int(min(28, dist_delta * aperture * 0.5))
                if blur_r >= 2:
                    ksize = (blur_r * 2 + 1)
                    active_tex = cv2.GaussianBlur(tex, (ksize, ksize), 0)
                else:
                    active_tex = tex
            else:
                active_tex = tex

            src_pts = np.array([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]], dtype=np.float32)
            dst_pts = np.array(proj_corners, dtype=np.float32)

            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            warped = cv2.warpPerspective(active_tex, M, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

            # Fast bounding box alpha blend
            alpha_channel = warped[:, :, 3]
            mask = alpha_channel > 0
            if np.any(mask):
                ys, xs = np.where(mask)
                y1, y2 = ys.min(), ys.max() + 1
                x1, x2 = xs.min(), xs.max() + 1

                sub_frame = frame[y1:y2, x1:x2].astype(np.float32)
                sub_warped = warped[y1:y2, x1:x2]
                sub_alpha = (sub_warped[:, :, 3:4].astype(np.float32)) / 255.0
                sub_rgb = sub_warped[:, :, :3].astype(np.float32)
                frame[y1:y2, x1:x2] = (sub_frame * (1.0 - sub_alpha) + sub_rgb * sub_alpha).astype(np.uint8)

        # 3. HUD Target Lock Indicator
        tgt_screen, tgt_dist = project_point(target_pos, cam_pos, R, fov)
        if tgt_screen:
            tx, ty = int(tgt_screen[0]), int(tgt_screen[1])
            if 40 <= tx < WIDTH - 40 and 40 <= ty < HEIGHT - 40:
                reticle_color = (255, 240, 0) # Cyan in BGR
                box_sz = 24
                # Crosshair corners
                cv2.line(frame, (tx - box_sz, ty - box_sz), (tx - box_sz + 10, ty - box_sz), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx - box_sz, ty - box_sz), (tx - box_sz, ty - box_sz + 10), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx + box_sz, ty - box_sz), (tx + box_sz - 10, ty - box_sz), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx + box_sz, ty - box_sz), (tx + box_sz, ty - box_sz + 10), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx - box_sz, ty + box_sz), (tx - box_sz + 10, ty + box_sz), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx - box_sz, ty + box_sz), (tx - box_sz, ty + box_sz - 10), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx + box_sz, ty + box_sz), (tx + box_sz - 10, ty + box_sz), reticle_color, 2, cv2.LINE_AA)
                cv2.line(frame, (tx + box_sz, ty + box_sz), (tx + box_sz, ty + box_sz - 10), reticle_color, 2, cv2.LINE_AA)
                cv2.circle(frame, (tx, ty), 3, reticle_color, -1)
                lock_text = f"TARGET [{tgt_dist:.1f}m]"
                cv2.putText(frame, lock_text, (tx - 40, ty - box_sz - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.50, reticle_color, 1, cv2.LINE_AA)

        # 4. Cinematic Telemetry & Header HUD
        # Top Header Bar
        cv2.rectangle(frame, (0, 0), (WIDTH, 90), (8, 12, 20), -1)
        cv2.line(frame, (0, 90), (WIDTH, 90), (0, 240, 255), 2)

        # Brand / Recipe Title
        cv2.putText(frame, "CHRONONMOTION 3D // CAMERA RIG V1", (45, 36), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 240, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"RECIPE: {scene_data['title'].upper()}", (45, 72), cv2.FONT_HERSHEY_DUPLEX, 0.95, (250, 252, 255), 2, cv2.LINE_AA)

        # Timecode & Frame
        elapsed_sec = f_idx / FPS
        total_sec = total_frames / FPS
        timecode_str = f"TC  {elapsed_sec:05.2f}s / {total_sec:05.2f}s  |  FRAME {f_idx + 1:03d}/{total_frames:03d}"
        cv2.putText(frame, timecode_str, (WIDTH - 480, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 220, 245), 2, cv2.LINE_AA)

        # Bottom-Left Live Camera Telemetry Box
        hud_w, hud_h = 560, 160
        hud_x, hud_y = 45, HEIGHT - hud_h - 40
        overlay = frame.copy()
        cv2.rectangle(overlay, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), (8, 12, 22), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (hud_x, hud_y), (hud_x + hud_w, hud_y + hud_h), (60, 90, 130), 1)

        # Telemetry Lines (clean ascii formatting)
        pos_line = f"CAM POS:   X:{cam_pos[0]:+06.2f}m   Y:{cam_pos[1]:+06.2f}m   Z:{cam_pos[2]:+06.2f}m"
        tgt_line = f"TARGET:    X:{target_pos[0]:+06.2f}m   Y:{target_pos[1]:+06.2f}m   Z:{target_pos[2]:+06.2f}m"
        opt_line = f"OPTICS:    FOV {fov:04.1f} deg   |   FOCAL 35mm EQUIV"
        dof_line = f"DOF / AF:  FOCUS {focus_dist:05.2f}m   |   APERTURE {aperture:04.1f}"

        cv2.putText(frame, pos_line, (hud_x + 20, hud_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 240, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, tgt_line, (hud_x + 20, hud_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (220, 230, 245), 1, cv2.LINE_AA)
        cv2.putText(frame, opt_line, (hud_x + 20, hud_y + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (180, 205, 230), 1, cv2.LINE_AA)
        cv2.putText(frame, dof_line, (hud_x + 20, hud_y + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 230, 120), 1, cv2.LINE_AA)

        # Bottom Timeline Progress Scrubber
        cv2.rectangle(frame, (0, HEIGHT - 8), (WIDTH, HEIGHT), (20, 25, 35), -1)
        prog_w = int(WIDTH * (f_idx + 1) / total_frames)
        cv2.rectangle(frame, (0, HEIGHT - 8), (prog_w, HEIGHT), (0, 240, 255), -1)

        # Write frame to FFmpeg
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    dt = time.time() - t0
    sz = out_mp4_path.stat().st_size if out_mp4_path.exists() else 0
    print(f"  ✓ Finished {out_mp4_path.name} in {dt:.1f}s ({sz:,} bytes)", flush=True)


def upload_to_drive(file_path, token, folder_id):
    boundary = "-------ChrononCameraSuiteUpload31415"
    fname = file_path.name
    metadata = {
        "name": fname,
        "parents": [folder_id]
    }
    meta_json = json.dumps(metadata)
    file_bytes = file_path.read_bytes()

    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta_json}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body))
        }
    )
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
        fid = res.get("id")
        # Ensure public link access
        try:
            perm_url = f"https://www.googleapis.com/drive/v3/files/{fid}/permissions"
            perm_req = urllib.request.Request(
                perm_url,
                data=json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(perm_req):
                pass
        except Exception:
            pass
        return res


def main():
    print(f"=== ChrononMotion Camera Motion V1 Showcase Suite ===", flush=True)
    if not TRAJECTORIES_JSON.exists():
        print(f"Error: {TRAJECTORIES_JSON} does not exist!")
        sys.exit(1)

    with open(TRAJECTORIES_JSON) as f:
        data = json.load(f)

    scenes = [s for s in data["scenes"] if s["id"].split("_")[0].isdigit() and int(s["id"].split("_")[0]) >= 17]
    print(f"Loaded {len(scenes)} new scenes (V2 Suite: 17-31) from trajectory data.")

    # 1. Render all MP4s concurrently
    rendered_files = []
    t_start = time.time()

    def do_render(sc):
        out_mp4 = OUT_DIR / f"{sc['id']}.mp4"
        render_scene(sc, out_mp4)
        return out_mp4

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(do_render, sc): sc for sc in scenes}
        for fut in as_completed(futures):
            try:
                mp4 = fut.result()
                if mp4.exists():
                    rendered_files.append(mp4)
            except Exception as e:
                print(f"Render error: {e}", flush=True)

    rendered_files.sort(key=lambda p: p.name)
    total_render_time = time.time() - t_start
    print(f"\nAll {len(rendered_files)} videos rendered in {total_render_time:.1f}s.")

    # 2. Upload to Google Drive
    print(f"\n=== Uploading {len(rendered_files)} videos to Google Drive folder {DRIVE_FOLDER_ID} ===", flush=True)
    token = refresh_drive_token()
    upload_results = {}

    for idx, fpath in enumerate(rendered_files, 1):
        print(f"[{idx}/{len(rendered_files)}] Uploading {fpath.name} ({fpath.stat().st_size:,} bytes)...", flush=True)
        res = upload_to_drive(fpath, token, DRIVE_FOLDER_ID)
        fid = res.get("id")
        link = f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk"
        upload_results[fpath.name] = link
        print(f"  -> Uploaded! {link}", flush=True)

    print("\n=======================================================")
    print("=== COMPLETE GOOGLE DRIVE VIDEO SHOWCASE DELIVERIES ===")
    print("=======================================================")
    for fname, link in upload_results.items():
        print(f"{fname:<40} : {link}")


if __name__ == "__main__":
    main()
