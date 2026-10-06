#!/usr/bin/env python3
"""
Chronon Dual Entity Image V1 Showcase Suite
Generates, validates, renders, and uploads 1920x1080 5.0-second (150 frames @ 30fps)
dual-image animations demonstrating simultaneous multi-entity / dual card presentation:

1. dual_split_converge    (Bilateral lateral split entrance: Left -1200->-440, Right 1200->440 with yaw settle)
2. dual_depth_stagger     (3D depth pop & staggered push-pull: Left Z:-300->0, Right Z:-250->0 with overshoot)
3. dual_flip_unfold       (3D dossier book-unfold: Left yaw +35°->0°, Right yaw -35°->0° with depth settle)
4. dual_cascade_diagonal  (Diagonal cascade & continuous 2.5D parallax drift)
5. dual_compare_versus    (Versus / face-to-face punch impact with center energy divider & focal pulse)

Target Google Drive Folder: 1X0nyiF82tMihNfRTAlij__bv7LwzZJ75
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/dual_entity_image_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1X0nyiF82tMihNfRTAlij__bv7LwzZJ75"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Scene constants
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # Exactly 5.0 seconds
CARD_W = 540
CARD_H = 540
RADIUS = 0.0  # Pre-baked with 4x Lanczos anti-aliased alpha mask to eliminate Chronon rasterizer edge halo
LEFT_X = -440
RIGHT_X = 440

IMAGE_LEFT = "assets/images/dual_entity_left.png"
IMAGE_RIGHT = "assets/images/dual_entity_right.png"


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
    boundary = "-------ChrononDualEntityUpload31415"
    fname = file_path.name
    metadata = {
        "name": fname,
        "parents": [folder_id]
    }
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


def make_bg_layer():
    return {
        "id": "studio_dark_bg",
        "type": "color",
        "color": [0.025, 0.035, 0.065, 1.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    }


# =============================================================================
# 1. dual_split_converge: Bilateral Lateral Convergence
# =============================================================================
def build_01_split_converge():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "dual_split_converge",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "dual_split_converge.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -760.0},
                            {"frame": 32, "value": 0.0}
                        ]},
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -22.0},
                            {"frame": 36, "value": 0.0},
                            {"frame": 149, "value": -1.5}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.90},
                            {"frame": 32, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 4, "value": 760.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 4, "value": 22.0},
                            {"frame": 40, "value": 0.0},
                            {"frame": 149, "value": 1.5}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 4, "value": 0.90},
                            {"frame": 36, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 4, "value": 0.0},
                            {"frame": 24, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 2. dual_depth_stagger: 3D Depth Pop & Stagger Settle
# =============================================================================
def build_02_depth_stagger():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "dual_depth_stagger",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "dual_depth_stagger.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card - Arrives first from deep Z
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -320.0},
                            {"frame": 28, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.86},
                            {"frame": 28, "value": 1.0},
                            {"frame": 149, "value": 1.025}
                        ]},
                        {"property": "rotation_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -12.0},
                            {"frame": 28, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card - Staggered entrance with pop overshoot
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 12, "value": -300.0},
                            {"frame": 40, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 12, "value": 0.85},
                            {"frame": 36, "value": 1.03},
                            {"frame": 46, "value": 1.0},
                            {"frame": 149, "value": 1.025}
                        ]},
                        {"property": "rotation_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 12, "value": 12.0},
                            {"frame": 40, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 12, "value": 0.0},
                            {"frame": 30, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 3. dual_flip_unfold: 3D Bilateral Dossier Unfold
# =============================================================================
def build_03_flip_unfold():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "dual_flip_unfold",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "dual_flip_unfold.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card - Angled inward at start, unfolds forward
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 38.0},
                            {"frame": 38, "value": 0.0},
                            {"frame": 90, "value": -2.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.90},
                            {"frame": 38, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 22, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card - Angled opposite, unfolds in sync
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -38.0},
                            {"frame": 38, "value": 0.0},
                            {"frame": 90, "value": 2.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.90},
                            {"frame": 38, "value": 1.0},
                            {"frame": 149, "value": 1.015}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 22, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 4. dual_cascade_diagonal: Diagonal Dynamic Sweep & Parallax Drift
# =============================================================================
def build_04_cascade_diagonal():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "dual_cascade_diagonal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "dual_cascade_diagonal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card - Sweeps from top-left with subtle roll
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -420.0},
                            {"frame": 35, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -260.0},
                            {"frame": 35, "value": 0.0},
                            {"frame": 149, "value": -14.0}
                        ]},
                        {"property": "rotation_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 6.0},
                            {"frame": 35, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 35, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 22, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card - Sweeps from bottom-right with subtle counter-roll
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 420.0},
                            {"frame": 43, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 260.0},
                            {"frame": 43, "value": 0.0},
                            {"frame": 149, "value": 14.0}
                        ]},
                        {"property": "rotation_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": -6.0},
                            {"frame": 43, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 0.92},
                            {"frame": 43, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 0.0},
                            {"frame": 30, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 5. dual_compare_versus: Face-to-Face Versus Impact with Center Accent
# =============================================================================
def build_05_compare_versus():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "dual_compare_versus",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "dual_compare_versus.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Center subtle luminous divider line
            {
                "id": "center_divider",
                "type": "shape",
                "size": [10, 540],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [0, -270]},
                        {"type": "line_to", "point": [0, 270]}
                    ],
                    "stroke": {"color": "#38BDF8", "width": 3.0}
                },
                "effects": [
                    {"type": "glow", "radius": 16.0, "intensity": 0.6, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 10, "value": 0.0},
                            {"frame": 28, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 10, "value": 0.0},
                            {"frame": 25, "value": 0.8},
                            {"frame": 45, "value": 0.45}
                        ]}
                    ]
                }
            },
            # Left Card - Swift punch deceleration from left
            {
                "id": "card_left",
                "type": "image",
                "asset": IMAGE_LEFT,
                "size": [CARD_W, CARD_H],
                "position": [LEFT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -580.0},
                            {"frame": 22, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 22, "value": 1.035},
                            {"frame": 32, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card - Swift punch deceleration from right
            {
                "id": "card_right",
                "type": "image",
                "asset": IMAGE_RIGHT,
                "size": [CARD_W, CARD_H],
                "position": [RIGHT_X, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 580.0},
                            {"frame": 22, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 22, "value": 1.035},
                            {"frame": 32, "value": 1.0},
                            {"frame": 149, "value": 1.02}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


PRESET_SUITE = [
    ("dual_split_converge", build_01_split_converge),
    ("dual_depth_stagger", build_02_depth_stagger),
    ("dual_flip_unfold", build_03_flip_unfold),
    ("dual_cascade_diagonal", build_04_cascade_diagonal),
    ("dual_compare_versus", build_05_compare_versus),
]


def main():
    print(f"=== Starting Chronon Dual Entity Image V1 Suite ({len(PRESET_SUITE)} items) ===", flush=True)

    # 1. Author and validate plans
    plan_files = []
    for item_id, builder in PRESET_SUITE:
        plan_data = builder()
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2))

        vcmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS_ROOT)]
        vres = subprocess.run(vcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if vres.returncode != 0:
            print(f"  [VALIDATION FAIL] {item_id}: {vres.stderr}\n{vres.stdout}")
            sys.exit(1)
        plan_files.append((item_id, plan_path))
        print(f"  ✓ [Validated] {plan_path.name}")

    # 2. Render compositions concurrently
    def render_worker(item):
        item_id, plan_path = item
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        out_png = OUT_DIR / f"{item_id}.png"

        cmd = [
            str(CHRONON_CLI),
            "render",
            "--backend", "software",
            "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT),
            "-o", str(out_mp4),
            "--ffmpeg-mode", "pipe",
            "--codec", "h264",
            "--encode-preset", "fast"
        ]
        print(f"[Starting Render] {item_id} (150 frames @ 30fps)...", flush=True)
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"  [ERROR] {item_id}: {res.stderr}\n{res.stdout}", flush=True)
            return []

        sz = out_mp4.stat().st_size if out_mp4.exists() else 0
        print(f"  ✓ Rendered {item_id}.mp4 in {dt:.1f}s ({sz:,} bytes)", flush=True)

        # Extract PNG poster at 2.5s (frame 75)
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02.500", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out_items = [out_mp4]
        if out_png.exists():
            out_items.append(out_png)
        return out_items

    print(f"\n=== Rendering {len(plan_files)} compositions (max_workers=3) ===", flush=True)
    t_start = time.time()
    rendered_files = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(render_worker, item): item for item in plan_files}
        for future in as_completed(futures):
            item = futures[future]
            try:
                files = future.result()
                rendered_files.extend(files)
            except Exception as e:
                print(f"  [EXCEPTION] {item[0]}: {e}", flush=True)
    print(f"=== All renders ready in {time.time() - t_start:.1f}s ===", flush=True)

    # 3. Upload to Google Drive folder 1X0nyiF82tMihNfRTAlij__bv7LwzZJ75
    print(f"\n=== Checking and Updating Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = refresh_drive_token()

    # List existing files in folder
    q = urllib.parse.quote(f"'{DRIVE_FOLDER_ID}' in parents and trashed = false")
    list_url = f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name,webViewLink)"
    req = urllib.request.Request(list_url, headers={"Authorization": f"Bearer {token}"})
    existing = {}
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            for f in data.get("files", []):
                existing[f["name"]] = f
    except Exception as e:
        print(f"Could not list folder: {e}")

    def update_drive_file(token, file_id, file_path):
        mime_type = "video/mp4" if file_path.name.endswith(".mp4") else "image/png"
        file_bytes = file_path.read_bytes()
        url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
        req = urllib.request.Request(
            url,
            data=file_bytes,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": mime_type,
                "Content-Length": str(len(file_bytes))
            },
            method="PATCH"
        )
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)

    uploads = []
    for fpath in rendered_files:
        fname = fpath.name
        if fname in existing:
            meta = existing[fname]
            fid = meta["id"]
            print(f"Updating existing {fname} in Google Drive (ID: {fid})...", flush=True)
            update_drive_file(token, fid, fpath)
            print(f"  ✓ Updated in place: {fname} Link: {meta.get('webViewLink')}")
            uploads.append(meta)
        else:
            print(f"Uploading {fname} ({fpath.stat().st_size:,} bytes)...", flush=True)
            meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
            uploads.append(meta)
            print(f"  ✓ Uploaded! ID: {meta.get('id')} Link: {meta.get('webViewLink')}")

    print("\n=== COMPLETE SUMMARY OF ALL 5 DUAL ENTITY DELIVERABLES ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")


if __name__ == "__main__":
    main()
