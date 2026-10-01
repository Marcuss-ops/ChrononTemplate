#!/usr/bin/env python3
"""
Chronon Multi-Image Trio V1 Engine & Showcase Suite
Implements multi_image_trio_v1 (3 images together):
- Layout: 3 cards (500x680) @ X = -540, 0, +540 (Screen: 420, 960, 1500)
- Safe area margins: 170px left/right, 200px top/bottom
- 5 Motion Presets (1920x1080, 5.0s @ 30fps):
  1. trio_fan_reveal
  2. trio_center_priority
  3. trio_ladder_stagger
  4. trio_arc_focus
  5. trio_depth_peel

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
OUT_DIR = BASE_DIR / "ChrononTemplate/out/multi_image_trio_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1X0nyiF82tMihNfRTAlij__bv7LwzZJ75"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150

CARD_W = 500
CARD_H = 680
LEFT_X = -540
MID_X = 0
RIGHT_X = 540

IMG_1 = "assets/images/card_trio_1.png"
IMG_2 = "assets/images/card_trio_2.png"
IMG_3 = "assets/images/card_trio_3.png"


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
    boundary = "-------ChrononMultiImageTrioUpload"
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
# 1. trio_fan_reveal
# Cards fan out from center, then focus traverses Left -> Mid -> Right -> Settle
# =============================================================================
def build_01_trio_fan_reveal():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "trio_fan_reveal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "trio_fan_reveal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card 1: Left
            make_card("card_left", IMG_1, [LEFT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": 540.0},
                    {"frame": 24, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 24, "value": 1.0},
                    {"frame": 36, "value": 1.05},
                    {"frame": 60, "value": 1.05},
                    {"frame": 72, "value": 0.96},
                    {"frame": 120, "value": 0.96},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0},
                    {"frame": 60, "value": 1.0},
                    {"frame": 72, "value": 0.75},
                    {"frame": 120, "value": 0.75},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card 2: Mid
            make_card("card_mid", IMG_2, [MID_X, 0], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24, "value": 1.0},
                    {"frame": 60, "value": 0.96},
                    {"frame": 72, "value": 1.05},
                    {"frame": 96, "value": 1.05},
                    {"frame": 108, "value": 0.96},
                    {"frame": 120, "value": 0.96},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0},
                    {"frame": 60, "value": 0.75},
                    {"frame": 72, "value": 1.0},
                    {"frame": 96, "value": 1.0},
                    {"frame": 108, "value": 0.75},
                    {"frame": 120, "value": 0.75},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card 3: Right
            make_card("card_right", IMG_3, [RIGHT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": -540.0},
                    {"frame": 24, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 24, "value": 1.0},
                    {"frame": 96, "value": 0.96},
                    {"frame": 108, "value": 1.05},
                    {"frame": 124, "value": 1.05},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0},
                    {"frame": 96, "value": 0.75},
                    {"frame": 108, "value": 1.0},
                    {"frame": 124, "value": 1.0},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ])
        ]
    }


# =============================================================================
# 2. trio_center_priority
# Center card is prominent Hero; flanks are secondary; locks firmly in hero
# =============================================================================
def build_02_trio_center_priority():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "trio_center_priority",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "trio_center_priority.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card Left (Flank)
            make_card("card_left", IMG_1, [LEFT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": -160.0},
                    {"frame": 24, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.88},
                    {"frame": 24, "value": 0.94},
                    {"frame": 36, "value": 1.02},
                    {"frame": 56, "value": 1.02},
                    {"frame": 70, "value": 0.92},
                    {"frame": 149, "value": 0.92}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.80},
                    {"frame": 36, "value": 1.0},
                    {"frame": 56, "value": 1.0},
                    {"frame": 70, "value": 0.72},
                    {"frame": 149, "value": 0.72}
                ]}
            ]),
            # Card Right (Flank)
            make_card("card_right", IMG_3, [RIGHT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": 160.0},
                    {"frame": 24, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.88},
                    {"frame": 24, "value": 0.92},
                    {"frame": 60, "value": 0.92},
                    {"frame": 74, "value": 1.02},
                    {"frame": 94, "value": 1.02},
                    {"frame": 108, "value": 0.92},
                    {"frame": 149, "value": 0.92}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.72},
                    {"frame": 60, "value": 0.72},
                    {"frame": 74, "value": 1.0},
                    {"frame": 94, "value": 1.0},
                    {"frame": 108, "value": 0.72},
                    {"frame": 149, "value": 0.72}
                ]}
            ]),
            # Card Mid (Hero)
            make_card("card_mid", IMG_2, [MID_X, 0], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24, "value": 1.02},
                    {"frame": 100, "value": 1.02},
                    {"frame": 116, "value": 1.08},
                    {"frame": 149, "value": 1.08}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ])
        ]
    }


# =============================================================================
# 3. trio_ladder_stagger
# Stepped ladder entrance: Left (F0) -> Mid (F18) -> Right (F36)
# =============================================================================
def build_03_trio_ladder_stagger():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "trio_ladder_stagger",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "trio_ladder_stagger.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card Left
            make_card("card_left", IMG_1, [LEFT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 0, "value": -320.0},
                    {"frame": 22, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 22, "value": 1.04},
                    {"frame": 46, "value": 1.04},
                    {"frame": 60, "value": 0.96},
                    {"frame": 120, "value": 0.96},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0},
                    {"frame": 46, "value": 1.0},
                    {"frame": 60, "value": 0.75},
                    {"frame": 120, "value": 0.75},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Mid
            make_card("card_mid", IMG_2, [MID_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 18, "value": -320.0},
                    {"frame": 40, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 18, "value": 0.92},
                    {"frame": 40, "value": 1.04},
                    {"frame": 74, "value": 1.04},
                    {"frame": 88, "value": 0.96},
                    {"frame": 120, "value": 0.96},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.0},
                    {"frame": 34, "value": 1.0},
                    {"frame": 74, "value": 1.0},
                    {"frame": 88, "value": 0.75},
                    {"frame": 120, "value": 0.75},
                    {"frame": 134, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Right
            make_card("card_right", IMG_3, [RIGHT_X, 0], [
                {"property": "position_x", "easing": "out_cubic", "keyframes": [
                    {"frame": 36, "value": -320.0},
                    {"frame": 58, "value": 0.0},
                    {"frame": 149, "value": 0.0}
                ]},
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 36, "value": 0.92},
                    {"frame": 58, "value": 1.04},
                    {"frame": 110, "value": 1.04},
                    {"frame": 124, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 36, "value": 0.0},
                    {"frame": 52, "value": 1.0},
                    {"frame": 110, "value": 1.0},
                    {"frame": 124, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ])
        ]
    }


# =============================================================================
# 4. trio_arc_focus
# Parabolic vertical displacement: Center elevated (Y = -28), flanks lowered (Y = +28)
# Focus wave traverses smoothly along the curve
# =============================================================================
def build_04_trio_arc_focus():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "trio_arc_focus",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "trio_arc_focus.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card Left: Y = +28
            make_card("card_left", IMG_1, [LEFT_X, 28], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24, "value": 1.04},
                    {"frame": 52, "value": 1.04},
                    {"frame": 66, "value": 0.96},
                    {"frame": 124, "value": 0.96},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 1.0},
                    {"frame": 52, "value": 1.0},
                    {"frame": 66, "value": 0.74},
                    {"frame": 124, "value": 0.74},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Mid: Y = -28
            make_card("card_mid", IMG_2, [MID_X, -28], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24, "value": 0.96},
                    {"frame": 52, "value": 0.96},
                    {"frame": 66, "value": 1.05},
                    {"frame": 92, "value": 1.05},
                    {"frame": 106, "value": 0.96},
                    {"frame": 124, "value": 0.96},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 0.74},
                    {"frame": 52, "value": 0.74},
                    {"frame": 66, "value": 1.0},
                    {"frame": 92, "value": 1.0},
                    {"frame": 106, "value": 0.74},
                    {"frame": 124, "value": 0.74},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Right: Y = +28
            make_card("card_right", IMG_3, [RIGHT_X, 28], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.92},
                    {"frame": 24, "value": 0.96},
                    {"frame": 92, "value": 0.96},
                    {"frame": 106, "value": 1.04},
                    {"frame": 124, "value": 1.04},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 20, "value": 0.74},
                    {"frame": 92, "value": 0.74},
                    {"frame": 106, "value": 1.0},
                    {"frame": 124, "value": 1.0},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ])
        ]
    }


# =============================================================================
# 5. trio_depth_peel
# 3 depth tiers; each peel forward successively into foreground prominence
# =============================================================================
def build_05_trio_depth_peel():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "trio_depth_peel",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "trio_depth_peel.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card Left
            make_card("card_left", IMG_1, [LEFT_X, 0], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 24, "value": 1.06},
                    {"frame": 48, "value": 1.06},
                    {"frame": 64, "value": 0.95},
                    {"frame": 124, "value": 0.95},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 1.0},
                    {"frame": 48, "value": 1.0},
                    {"frame": 64, "value": 0.75},
                    {"frame": 124, "value": 0.75},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Mid
            make_card("card_mid", IMG_2, [MID_X, 0], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 24, "value": 0.95},
                    {"frame": 52, "value": 0.95},
                    {"frame": 68, "value": 1.06},
                    {"frame": 92, "value": 1.06},
                    {"frame": 106, "value": 0.95},
                    {"frame": 124, "value": 0.95},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.75},
                    {"frame": 52, "value": 0.75},
                    {"frame": 68, "value": 1.0},
                    {"frame": 92, "value": 1.0},
                    {"frame": 106, "value": 0.75},
                    {"frame": 124, "value": 0.75},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ]),
            # Card Right
            make_card("card_right", IMG_3, [RIGHT_X, 0], [
                {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.90},
                    {"frame": 24, "value": 0.95},
                    {"frame": 92, "value": 0.95},
                    {"frame": 108, "value": 1.06},
                    {"frame": 124, "value": 1.06},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]},
                {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                    {"frame": 0, "value": 0.0},
                    {"frame": 18, "value": 0.75},
                    {"frame": 92, "value": 0.75},
                    {"frame": 108, "value": 1.0},
                    {"frame": 124, "value": 1.0},
                    {"frame": 136, "value": 1.0},
                    {"frame": 149, "value": 1.0}
                ]}
            ])
        ]
    }


PRESETS = [
    ("trio_fan_reveal", build_01_trio_fan_reveal),
    ("trio_center_priority", build_02_trio_center_priority),
    ("trio_ladder_stagger", build_03_trio_ladder_stagger),
    ("trio_arc_focus", build_04_trio_arc_focus),
    ("trio_depth_peel", build_05_trio_depth_peel)
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
    print("CHRONON MULTI-IMAGE TRIO V1 SUITE")
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

    manifest_path = OUT_DIR / "multi_image_trio_v1_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(uploaded, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
