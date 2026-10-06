#!/usr/bin/env python3
"""
Chronon image_frame_premium_v1 Motion Showcase Suite
Generates, validates, renders, and uploads 1920x1080 overlays demonstrating the 10 premium image card animations:
1. image_glow_depth_in        (Depth Z + glow entrance & settle)
2. image_border_draw_in       (Stroke reveal via Trim Path on rounded rect)
3. image_soft_yaw_glow        (Editorial 3D Yaw rotationY -14°->0° + entering glow)
4. image_tilt_frame_in        (Synchronized tilt rotationX/Y + scale .96->1)
5. image_frame_scale_reveal   (Border first, image delayed scale .96->1)
6. image_glow_pulse_settle    (Image enters, glow single pulse .35->.08)
7. image_neon_trace           (Second luminous stroke travels perimeter once)
8. image_parallax_frame       (2.5D layer depth separation Z:-20, Z:15, Z:45 + drift)
9. image_mask_wipe_border     (Border locked, image reveals from left to right)
10. image_caption_frame_combo (Card reveal -> border draw -> caption rise -> underline)

Target Google Drive Folder: 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
"""

import os
import sys
import json
import math
import time
import subprocess
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/image_frame_premium_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI"
SAMPLE_IMAGE = "assets/images/premium_sample_portrait.png"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 75  # 2.5 seconds (0-36f motion + steady presentation)
CARD_W = 640
CARD_H = 640
RADIUS = 32.0

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
    boundary = "-------314159265358979323846"
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
        return json.load(resp)

def build_rounded_rect_path(w, h, r):
    k = 0.5522847498 * r
    x0, x1 = -w / 2.0, w / 2.0
    y0, y1 = -h / 2.0, h / 2.0
    return [
        {"type": "move_to", "point": [x0 + r, y0]},
        {"type": "line_to", "point": [x1 - r, y0]},
        {"type": "cubic_to", "control1": [x1 - r + k, y0], "control2": [x1, y0 + r - k], "point": [x1, y0 + r]},
        {"type": "line_to", "point": [x1, y1 - r]},
        {"type": "cubic_to", "control1": [x1, y1 - r + k], "control2": [x1 - r + k, y1], "point": [x1 - r, y1]},
        {"type": "line_to", "point": [x0 + r, y1]},
        {"type": "cubic_to", "control1": [x0 + r - k, y1], "control2": [x0, y1 - r + k], "point": [x0, y1 - r]},
        {"type": "line_to", "point": [x0, y0 + r]},
        {"type": "cubic_to", "control1": [x0, y0 + r - k], "control2": [x0 + r - k, y0], "point": [x0 + r, y0]},
        {"type": "close"}
    ]

def make_bg_layer():
    return {
        "id": "studio_bg",
        "type": "color",
        "color": [0.03, 0.04, 0.08, 1.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    }

# ─────────────────────────────────────────────────────────────────────────────
# 1. image_glow_depth_in
# ─────────────────────────────────────────────────────────────────────────────
def build_01_glow_depth_in():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_glow_depth_in",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_glow_depth_in.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -140.0},
                            {"frame": 14, "value": -40.0},
                            {"frame": 28, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 14, "value": 0.985},
                            {"frame": 28, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 14, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Synchronized border + glowing accent
            {
                "id": "card_glow_border",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#38BDF8", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.45, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -140.0},
                            {"frame": 14, "value": -40.0},
                            {"frame": 28, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 14, "value": 0.985},
                            {"frame": 28, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 14, "value": 1.0},
                            {"frame": 28, "value": 0.45}
                        ]}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 2. image_border_draw_in
# ─────────────────────────────────────────────────────────────────────────────
def build_02_border_draw_in():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_border_draw_in",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_border_draw_in.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image (fade + micro scale)
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 24, "value": 1.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.98},
                            {"frame": 30, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Drawn rounded rect border via Trim Path
            {
                "id": "card_drawn_border",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#38BDF8", "width": 2.5},
                    "operators": [
                        {
                            "kind": "trim",
                            "params": {
                                "start": 0.0,
                                "end": 1.0,
                                "animation": {
                                    "easing": "out_cubic",
                                    "keyframes": [
                                        {"frame": 0, "value": [0.0, 0.0]},
                                        {"frame": 32, "value": [0.0, 1.0]}
                                    ]
                                }
                            }
                        }
                    ]
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ]
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. image_soft_yaw_glow
# ─────────────────────────────────────────────────────────────────────────────
def build_03_soft_yaw_glow():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_soft_yaw_glow",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_soft_yaw_glow.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image with 3D yaw
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -14.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -80.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Border + Yaw lighting glow
            {
                "id": "card_border_yaw",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#67E8F9", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.45, "color": [0.1, 0.8, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -14.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "position_z", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -80.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 0.90},
                            {"frame": 36, "value": 0.35}
                        ]}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. image_tilt_frame_in
# ─────────────────────────────────────────────────────────────────────────────
def build_04_tilt_frame_in():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_tilt_frame_in",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_tilt_frame_in.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image tilted
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "rotation_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 6.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -7.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 36, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Synchronous border
            {
                "id": "card_border_tilt",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#F8FAFC", "width": 2.0}
                },
                "effects": [
                    {"type": "glow", "radius": 10.0, "intensity": 0.30, "color": [0.8, 0.9, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 6.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "rotation_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -7.0},
                            {"frame": 36, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 36, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 0.85}
                        ]}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. image_frame_scale_reveal
# ─────────────────────────────────────────────────────────────────────────────
def build_05_frame_scale_reveal():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_frame_scale_reveal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_frame_scale_reveal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image (delayed reveal)
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 0.96},
                            {"frame": 28, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 8, "value": 0.0},
                            {"frame": 22, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Frame appears first (0-18f)
            {
                "id": "card_frame_first",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#38BDF8", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 18, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 12, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6. image_glow_pulse_settle
# ─────────────────────────────────────────────────────────────────────────────
def build_06_glow_pulse_settle():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_glow_pulse_settle",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_glow_pulse_settle.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image enters
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 20, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 14, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Base subtle border
            {
                "id": "card_border_base",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#64748B", "width": 1.8}
                },
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 14, "value": 0.70}
                        ]}
                    ]
                }
            },
            # Single glow pulse: 0 -> 0.35 (f10) -> 0.08 (f22)
            {
                "id": "card_pulse_glow",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#38BDF8", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 14.0, "intensity": 0.40, "color": [0.1, 0.8, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "in_out_quad", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 10, "value": 0.85},
                            {"frame": 22, "value": 0.15}
                        ]}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 7. image_neon_trace
# ─────────────────────────────────────────────────────────────────────────────
def build_07_neon_trace():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_neon_trace",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_neon_trace.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Base border
            {
                "id": "card_border_base",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#475569", "width": 1.8}
                },
                "opacity": 0.60
            },
            # Second luminous stroke (14% perimeter window travelling once)
            {
                "id": "card_neon_chase",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#00F0FF", "width": 3.0},
                    "operators": [
                        {
                            "kind": "trim",
                            "params": {
                                "start": 0.0,
                                "end": 1.0,
                                "animation": {
                                    "easing": "linear",
                                    "keyframes": [
                                        {"frame": 10, "value": [0.0, 0.0]},
                                        {"frame": 20, "value": [0.0, 0.14]},
                                        {"frame": 50, "value": [0.86, 1.0]},
                                        {"frame": 58, "value": [1.0, 1.0]}
                                    ]
                                }
                            }
                        }
                    ]
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.45, "color": [0.0, 0.9, 1.0, 1.0]}
                ]
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 8. image_parallax_frame
# ─────────────────────────────────────────────────────────────────────────────
def build_08_parallax_frame():
    # Subtle 2.5D drift keyframes (component tracks must share keyframe times)
    rot_y_keys = [
        {"frame": 0, "value": -2.0},
        {"frame": 36, "value": 2.0},
        {"frame": 74, "value": 0.0}
    ]
    rot_x_keys = [
        {"frame": 0, "value": 1.5},
        {"frame": 36, "value": -1.5},
        {"frame": 74, "value": 0.0}
    ]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_parallax_frame",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_parallax_frame.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Layer 1: Background Plate at Z = -20
            {
                "id": "card_bg_plate",
                "type": "shape",
                "size": [CARD_W + 24, CARD_H + 24],
                "position": [960, 540],
                "color": [0.06, 0.08, 0.14, 0.90],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W + 24, CARD_H + 24, RADIUS + 6),
                    "stroke": {"color": "#1E293B", "width": 2.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "position_z", "keyframes": [{"frame": 0, "value": -20.0}]},
                        {"property": "rotation_y", "easing": "in_out_sine", "keyframes": rot_y_keys},
                        {"property": "rotation_x", "easing": "in_out_sine", "keyframes": rot_x_keys}
                    ]
                }
            },
            # Layer 2: Main Image at Z = 15
            {
                "id": "card_image_depth",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_z", "keyframes": [{"frame": 0, "value": 15.0}]},
                        {"property": "rotation_y", "easing": "in_out_sine", "keyframes": rot_y_keys},
                        {"property": "rotation_x", "easing": "in_out_sine", "keyframes": rot_x_keys}
                    ]
                }
            },
            # Layer 3: Foreground Accent Badge at Z = 45 (drifts with pronounced parallax)
            {
                "id": "card_fg_badge",
                "type": "shape",
                "size": [220, 48],
                "position": [960, 800],
                "color": [0.03, 0.05, 0.10, 0.90],
                "enable_3d": True,
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(220, 48, 14.0),
                    "stroke": {"color": "#38BDF8", "width": 1.5}
                },
                "effects": [
                    {"type": "glow", "radius": 10.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_z", "keyframes": [{"frame": 0, "value": 45.0}]},
                        {"property": "rotation_y", "easing": "in_out_sine", "keyframes": rot_y_keys},
                        {"property": "rotation_x", "easing": "in_out_sine", "keyframes": rot_x_keys}
                    ]
                }
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 9. image_mask_wipe_border
# ─────────────────────────────────────────────────────────────────────────────
def build_09_mask_wipe_border():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_mask_wipe_border",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_mask_wipe_border.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Card image: slides horizontally into position while border is fixed
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [CARD_W, CARD_H],
                "position": [0, 0],
                "radius": RADIUS,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -140.0},
                            {"frame": 28, "value": 0.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 22, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Border: anchored and visible from frame 0
            {
                "id": "card_fixed_border",
                "type": "shape",
                "size": [CARD_W, CARD_H],
                "position": [960, 540],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(CARD_W, CARD_H, RADIUS),
                    "stroke": {"color": "#38BDF8", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "opacity": 0.85
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 10. image_caption_frame_combo
# ─────────────────────────────────────────────────────────────────────────────
def build_10_caption_frame_combo():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "image_caption_frame_combo",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "image_caption_frame_combo.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # 0-12f: Frame enters (card at [0, -60] for image, [960, 480] for shape)
            {
                "id": "card_frame",
                "type": "shape",
                "size": [560, 560],
                "position": [960, 480],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": build_rounded_rect_path(560, 560, 28.0),
                    "stroke": {"color": "#38BDF8", "width": 2.5}
                },
                "effects": [
                    {"type": "glow", "radius": 12.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 12, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 12, "value": 1.0}
                        ]}
                    ]
                }
            },
            # 5-18f: Image appears
            {
                "id": "card_image",
                "type": "image",
                "asset": SAMPLE_IMAGE,
                "size": [560, 560],
                "position": [0, -60],
                "radius": 28.0,
                "fit": "cover",
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "out_cubic", "keyframes": [
                            {"frame": 5, "value": 0.97},
                            {"frame": 18, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 5, "value": 0.0},
                            {"frame": 18, "value": 1.0}
                        ]}
                    ]
                }
            },
            # 14-26f: Caption rises
            {
                "id": "caption_title",
                "type": "text",
                "text": "ELON MUSK",
                "size": [600, 48],
                "position": [960, 810],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Poppins-Bold.ttf",
                    "font_size": 32.0,
                    "fill": "#FFFFFF"
                },
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 14, "value": 830.0},
                            {"frame": 26, "value": 810.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 14, "value": 0.0},
                            {"frame": 24, "value": 1.0}
                        ]}
                    ]
                }
            },
            {
                "id": "caption_role",
                "type": "text",
                "text": "CHIEF EXECUTIVE OFFICER • PRODUCT ARCHITECT",
                "size": [600, 28],
                "position": [960, 850],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "style": {
                    "font": "assets/fonts/Inter-Regular.ttf",
                    "font_size": 15.0,
                    "fill": "#94A3B8"
                },
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 18, "value": 0.0},
                            {"frame": 28, "value": 1.0}
                        ]}
                    ]
                }
            },
            # 20-34f: Accent underline draws
            {
                "id": "caption_accent_line",
                "type": "shape",
                "size": [360, 4],
                "position": [960, 885],
                "color": [0.0, 0.0, 0.0, 0.0],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-180.0, 0.0]},
                        {"type": "line_to", "point": [180.0, 0.0]}
                    ],
                    "stroke": {
                        "color": "#38BDF8",
                        "width": 2.0
                    }
                },
                "effects": [
                    {"type": "glow", "radius": 10.0, "intensity": 0.35, "color": [0.2, 0.7, 1.0, 1.0]}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 20, "value": 0.0},
                            {"frame": 34, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 20, "value": 0.0},
                            {"frame": 26, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }

SHOWCASE_SUITE = [
    ("image_glow_depth_in", build_01_glow_depth_in),
    ("image_border_draw_in", build_02_border_draw_in),
    ("image_soft_yaw_glow", build_03_soft_yaw_glow),
    ("image_tilt_frame_in", build_04_tilt_frame_in),
    ("image_frame_scale_reveal", build_05_frame_scale_reveal),
    ("image_glow_pulse_settle", build_06_glow_pulse_settle),
    ("image_neon_trace", build_07_neon_trace),
    ("image_parallax_frame", build_08_parallax_frame),
    ("image_mask_wipe_border", build_09_mask_wipe_border),
    ("image_caption_frame_combo", build_10_caption_frame_combo),
]

def main():
    print(f"=== Starting Chronon image_frame_premium_v1 Showcase Suite ({len(SHOWCASE_SUITE)} items) ===", flush=True)

    # 1. Author and validate each plan
    plan_files = []
    for item_id, builder in SHOWCASE_SUITE:
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
        print(f"[Starting Render] {item_id}...", flush=True)
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"  [ERROR] {item_id}: {res.stderr}\n{res.stdout}", flush=True)
            return []

        sz = out_mp4.stat().st_size if out_mp4.exists() else 0
        print(f"  ✓ Rendered & Encoded {item_id} in {dt:.1f}s ({sz:,} bytes)", flush=True)

        # Extract PNG poster at 2.0s
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
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
    print(f"=== All renders completed in {time.time() - t_start:.1f}s ===", flush=True)

    # 3. Upload to Google Drive folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
    print(f"\n=== Uploading {len(rendered_files)} media files to Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = refresh_drive_token()
    uploads = []
    for fpath in rendered_files:
        print(f"Uploading {fpath.name} ({fpath.stat().st_size:,} bytes)...", flush=True)
        meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
        uploads.append(meta)
        print(f"  ✓ Uploaded! ID: {meta.get('id')}")

    print("\n=== SUMMARY OF COMPLETED IMAGE FRAME PREMIUM V1 DELIVERABLES ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")

if __name__ == "__main__":
    main()
