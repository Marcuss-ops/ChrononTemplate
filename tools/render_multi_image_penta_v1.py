#!/usr/bin/env python3
"""
Chronon Multi-Image Penta V1 Engine & Showcase Suite
Implements multi_image_penta_v1 (5 images simultaneously on screen):
- Layout: 5 cards (320x580) @ X = -680, -340, 0, 340, 680
- Safe margins: 120px left/right, 250px top/bottom
- 5 Motion Presets (1920x1080, 5.0s @ 30fps):
  1. penta_hero_plus_four
  2. penta_carousel_focus
  3. penta_cluster_expand
  4. penta_strip_wave
  5. penta_priority_cycle

Target Google Drive Folder: 1X0nyiF82tMihNfRTAlij__bv7LwzZJ75
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/multi_image_penta_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1X0nyiF82tMihNfRTAlij__bv7LwzZJ75"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150

CARD_W = 320
CARD_H = 580

POSITIONS = [-680, -340, 0, 340, 680]
IMAGES = [f"assets/images/card_penta_{i+1}.png" for i in range(5)]


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


def upload_to_drive(token, file_path, folder_id):
    boundary = "-------ChrononMultiImagePentaUpload"
    fname = file_path.name
    metadata = {"name": fname, "parents": [folder_id]}
    meta_json = json.dumps(metadata)
    file_bytes = file_path.read_bytes()
    mime_type = "video/mp4" if fname.endswith(".mp4") else "image/png"

    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{meta_json}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
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


def make_bg_layer():
    return {
        "id": "studio_dark_bg",
        "type": "color",
        "color": [0.03, 0.04, 0.07, 1.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    }


def make_card(layer_id, asset_path, base_pos, animation_tracks):
    return {
        "id": layer_id,
        "type": "image",
        "asset": asset_path,
        "size": [CARD_W, CARD_H],
        "position": base_pos,
        "radius": 0.0,
        "fit": "cover",
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {"tracks": animation_tracks}
    }


# =============================================================================
# 1. penta_hero_plus_four
# Card 3 (Center) is hero (larger, elevated); 4 flanking cards flank symmetrically
# =============================================================================
def build_01_penta_hero_plus_four():
    layers = [make_bg_layer()]
    for i in range(5):
        is_hero = (i == 2)
        base_x = POSITIONS[i]
        scale_keys = [
            {"frame": 0, "value": 0.90},
            {"frame": 24, "value": 1.08 if is_hero else 0.94},
            {"frame": 120, "value": 1.08 if is_hero else 0.94},
            {"frame": 136, "value": 1.06 if is_hero else 0.98},
            {"frame": 149, "value": 1.06 if is_hero else 0.98}
        ]
        opacity_keys = [
            {"frame": 0, "value": 0.0},
            {"frame": 18, "value": 1.0 if is_hero else 0.74},
            {"frame": 120, "value": 1.0 if is_hero else 0.74},
            {"frame": 136, "value": 1.0 if is_hero else 0.95},
            {"frame": 149, "value": 1.0 if is_hero else 0.95}
        ]
        pos_x_keys = [
            {"frame": 0, "value": (base_x * 0.4) - base_x},
            {"frame": 24, "value": 0.0},
            {"frame": 149, "value": 0.0}
        ]
        layers.append(make_card(
            f"card_{i+1}", IMAGES[i], [base_x, 0],
            [
                {"property": "position_x", "easing": "out_cubic", "keyframes": pos_x_keys},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys}
            ]
        ))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "penta_hero_plus_four",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "penta_hero_plus_four.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 2. penta_carousel_focus
# All 5 visible; focus steps forward 1 -> 2 -> 3 -> 4 -> 5 in clean 24-frame cycles
# =============================================================================
def build_02_penta_carousel_focus():
    layers = [make_bg_layer()]
    for i in range(5):
        base_x = POSITIONS[i]
        focus_start = 24 + (i * 20)
        focus_end = focus_start + 18

        scale_keys = [
            {"frame": 0, "value": 0.90},
            {"frame": 20, "value": 0.94}
        ]
        opacity_keys = [
            {"frame": 0, "value": 0.0},
            {"frame": 16, "value": 0.72}
        ]

        if focus_start > 20:
            scale_keys.append({"frame": focus_start, "value": 0.94})
            opacity_keys.append({"frame": focus_start, "value": 0.72})

        scale_keys.extend([
            {"frame": focus_start + 8, "value": 1.06},
            {"frame": focus_end, "value": 1.06},
            {"frame": focus_end + 8, "value": 0.94},
            {"frame": 132, "value": 0.94},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])
        opacity_keys.extend([
            {"frame": focus_start + 8, "value": 1.0},
            {"frame": focus_end, "value": 1.0},
            {"frame": focus_end + 8, "value": 0.72},
            {"frame": 132, "value": 0.72},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])

        layers.append(make_card(
            f"card_{i+1}", IMAGES[i], [base_x, 0],
            [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys}
            ]
        ))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "penta_carousel_focus",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "penta_carousel_focus.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 3. penta_cluster_expand
# Starts clustered tightly at center, then blossoms outwards into 5-strip
# =============================================================================
def build_03_penta_cluster_expand():
    layers = [make_bg_layer()]
    for i in range(5):
        base_x = POSITIONS[i]
        layers.append(make_card(
            f"card_{i+1}", IMAGES[i], [base_x, 0],
            [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": -base_x},
                    {"frame": 28, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.85},
                    {"frame": 28, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]
        ))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "penta_cluster_expand",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "penta_cluster_expand.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 4. penta_strip_wave
# Continuous wave traversal of scale and elevation across the horizontal strip
# =============================================================================
def build_04_penta_strip_wave():
    layers = [make_bg_layer()]
    for i in range(5):
        base_x = POSITIONS[i]
        wave_peak = 30 + (i * 18)
        scale_keys = [
            {"frame": 0, "value": 0.90},
            {"frame": 20, "value": 0.95}
        ]
        if wave_peak - 10 > 20:
            scale_keys.append({"frame": wave_peak - 10, "value": 0.95})
        scale_keys.extend([
            {"frame": wave_peak, "value": 1.06},
            {"frame": wave_peak + 10, "value": 0.95},
            {"frame": 130, "value": 0.95},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])
        opacity_keys = [
            {"frame": 0, "value": 0.0},
            {"frame": 16, "value": 0.75}
        ]
        if wave_peak - 10 > 16:
            opacity_keys.append({"frame": wave_peak - 10, "value": 0.75})
        opacity_keys.extend([
            {"frame": wave_peak, "value": 1.0},
            {"frame": wave_peak + 10, "value": 0.75},
            {"frame": 130, "value": 0.75},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])

        layers.append(make_card(
            f"card_{i+1}", IMAGES[i], [base_x, 0],
            [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys}
            ]
        ))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "penta_strip_wave",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "penta_strip_wave.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 5. penta_priority_cycle
# Sequential entity priority cycle 1 -> 5, settling in complete 5-entity harmony
# =============================================================================
def build_05_penta_priority_cycle():
    layers = [make_bg_layer()]
    for i in range(5):
        base_x = POSITIONS[i]
        enter_f = i * 8
        scale_keys = [
            {"frame": 0, "value": 0.90},
            {"frame": enter_f + 16, "value": 1.05},
            {"frame": enter_f + 32, "value": 0.95},
            {"frame": 132, "value": 0.95},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ]
        opacity_keys = [
            {"frame": 0, "value": 0.0}
        ]
        if enter_f > 0:
            opacity_keys.append({"frame": enter_f, "value": 0.0})
        opacity_keys.extend([
            {"frame": enter_f + 14, "value": 1.0},
            {"frame": enter_f + 32, "value": 0.75},
            {"frame": 132, "value": 0.75},
            {"frame": 142, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])

        layers.append(make_card(
            f"card_{i+1}", IMAGES[i], [base_x, 0],
            [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys}
            ]
        ))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "penta_priority_cycle",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "penta_priority_cycle.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


PRESETS = [
    ("penta_hero_plus_four", build_01_penta_hero_plus_four),
    ("penta_carousel_focus", build_02_penta_carousel_focus),
    ("penta_cluster_expand", build_03_penta_cluster_expand),
    ("penta_strip_wave", build_04_penta_strip_wave),
    ("penta_priority_cycle", build_05_penta_priority_cycle)
]


def validate_plan(plan_path):
    cmd = [
        str(CHRONON_CLI), "validate",
        "--plan", str(plan_path),
        "--assets-root", str(ASSETS_ROOT)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Validation FAILED for {plan_path.name}:\n{proc.stderr}\n{proc.stdout}", file=sys.stderr)
        return False
    return True


def render_plan(plan_path):
    cmd = [
        str(CHRONON_CLI), "render",
        "--plan", str(plan_path),
        "--assets-root", str(ASSETS_ROOT)
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if proc.returncode != 0:
        print(f"Render FAILED for {plan_path.name} ({dt:.2f}s):\n{proc.stderr}\n{proc.stdout}", file=sys.stderr)
        return False, dt
    return True, dt


def extract_poster(video_path, poster_path, timestamp="00:00:02.5"):
    cmd = [
        "ffmpeg", "-y",
        "-ss", timestamp,
        "-i", str(video_path),
        "-vframes", "1",
        str(poster_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def main():
    print("=" * 70)
    print("CHRONON MULTI-IMAGE PENTA V1 SUITE")
    print(f"Output directory: {OUT_DIR}")
    print(f"Resolution: {WIDTH}x{HEIGHT} @ {FPS}fps, Duration: {DURATION_FRAMES / FPS:.1f}s")
    print("=" * 70)

    plans = []
    for name, builder_func in PRESETS:
        plan_dict = builder_func()
        plan_path = OUT_DIR / f"{name}.plan.json"
        with open(plan_path, "w") as f:
            json.dump(plan_dict, f, indent=2)
        plans.append((name, plan_path))

    # 1. Validation phase
    print("\n--- PHASE 1: Plan Validation ---")
    all_valid = True
    for name, plan_path in plans:
        ok = validate_plan(plan_path)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if not ok:
            all_valid = False

    if not all_valid:
        print("\nAborting due to validation errors.", file=sys.stderr)
        sys.exit(1)

    # 2. Render phase
    print("\n--- PHASE 2: Chronon3d High-Speed Rendering ---")
    results = {}
    for name, plan_path in plans:
        mp4_path = OUT_DIR / f"{name}.mp4"
        poster_path = OUT_DIR / f"{name}_poster.png"
        print(f"  Rendering {name} ...", end="", flush=True)
        ok, dt = render_plan(plan_path)
        if ok and mp4_path.exists():
            size_mb = mp4_path.stat().st_size / (1024 * 1024)
            extract_poster(mp4_path, poster_path)
            print(f" DONE in {dt:.2f}s ({size_mb:.2f} MB)")
            results[name] = {"mp4": mp4_path, "poster": poster_path, "time": dt, "size": size_mb}
        else:
            print(f" FAILED!")

    # 3. Upload to Google Drive
    print("\n--- PHASE 3: Google Drive Upload ---")
    token = refresh_drive_token()
    print(f"  Drive token refreshed successfully.")
    uploaded = {}
    for name, data in results.items():
        print(f"  Uploading {name} video & poster to Drive...")
        v_res = upload_to_drive(token, data["mp4"], DRIVE_FOLDER_ID)
        p_res = upload_to_drive(token, data["poster"], DRIVE_FOLDER_ID)
        v_link = v_res.get("webViewLink") or f"https://drive.google.com/file/d/{v_res.get('id')}/view"
        p_link = p_res.get("webViewLink") or f"https://drive.google.com/file/d/{p_res.get('id')}/view"
        uploaded[name] = {
            "video_id": v_res.get("id"),
            "video_link": v_link,
            "poster_id": p_res.get("id"),
            "poster_link": p_link
        }
        print(f"    Video:  {v_link}")
        print(f"    Poster: {p_link}")

    manifest_path = OUT_DIR / "multi_image_penta_v1_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(uploaded, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
