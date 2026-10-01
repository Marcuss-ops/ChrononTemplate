#!/usr/bin/env python3
"""
Chronon Multi-Phrase Layout V1 Engine & Showcase Suite
Implements the multi_phrase_layout_v1 architecture:
- 3 Semantic Reading States: PRIMARY (active hero), SECONDARY (dimmed preview), HISTORY (calm context)
- Never removes previous context abruptly; maintains viewer comprehension and narrative rhythm
- 5 Production-grade Motion Presets (1920x1080, 5.0s @ 30fps):
  1. phrase_vertical_focus_stack
  2. phrase_ladder_priority
  3. phrase_dual_side_compare
  4. phrase_stagger_keep_alive
  5. phrase_center_with_history

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
OUT_DIR = BASE_DIR / "ChrononTemplate/out/multi_phrase_stack_v1"
TOKEN_PATH = BASE_DIR / "refactored/token.json"
CREDS_PATH = BASE_DIR / "refactored/credentials.json"
DRIVE_FOLDER_ID = "1X0nyiF82tMihNfRTAlij__bv7LwzZJ75"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Scene constants
WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # Exactly 5.0 seconds
FONT_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_REGULAR = "assets/fonts/Poppins-Regular.ttf"
FONT_INTER = "assets/fonts/Inter-SemiBold.ttf"


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
    boundary = "-------ChrononMultiPhraseUpload"
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


def clean_keyframes(keys):
    by_frame = {}
    for k in keys:
        by_frame[k["frame"]] = k["value"]
    return [{"frame": f, "value": by_frame[f]} for f in sorted(by_frame.keys())]


def make_bg_layer():
    return {
        "id": "studio_dark_bg",
        "type": "color",
        "color": [0.03, 0.04, 0.07, 1.0],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    }


# =============================================================================
# 1. phrase_vertical_focus_stack
# 3 phrases in a vertical stack (Y1=360, Y2=540, Y3=720)
# Timeline:
# 0.0 - 0.7s: Phrase 1 enters -> PRIMARY
# 0.7 - 1.8s: Phrase 1 holds PRIMARY, Phrase 2 prepares as SECONDARY
# 1.8 - 2.8s: Phrase 2 steps into PRIMARY, Phrase 1 transitions to HISTORY
# 2.8 - 3.8s: Phrase 3 steps into PRIMARY, Phrase 1 & 2 in HISTORY
# 3.8 - 5.0s: All three balance into a harmonious overview
# =============================================================================
def build_01_phrase_vertical_focus_stack():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_vertical_focus_stack",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_vertical_focus_stack.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Phrase 1: Top
            {
                "id": "phrase_top",
                "type": "text",
                "text": "01. Next-Generation Autonomous Systems",
                "position": [960, 360],
                "size": [1500, 140],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 46,
                    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 16}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -30.0},
                            {"frame": 22, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 22, "value": 1.04},
                            {"frame": 52, "value": 1.04},
                            {"frame": 66, "value": 0.98},
                            {"frame": 114, "value": 0.98},
                            {"frame": 128, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 52, "value": 1.0},
                            {"frame": 66, "value": 0.52},
                            {"frame": 114, "value": 0.52},
                            {"frame": 128, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            },
            # Phrase 2: Center
            {
                "id": "phrase_mid",
                "type": "text",
                "text": "02. Real-Time Spatial Reasoning Engines",
                "position": [960, 540],
                "size": [1500, 140],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 46,
                    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 16}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 20.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 24, "value": 0.96},
                            {"frame": 52, "value": 0.96},
                            {"frame": 66, "value": 1.04},
                            {"frame": 84, "value": 1.04},
                            {"frame": 98, "value": 0.98},
                            {"frame": 114, "value": 0.98},
                            {"frame": 128, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 24, "value": 0.35},
                            {"frame": 52, "value": 0.35},
                            {"frame": 66, "value": 1.0},
                            {"frame": 84, "value": 1.0},
                            {"frame": 98, "value": 0.52},
                            {"frame": 114, "value": 0.52},
                            {"frame": 128, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            },
            # Phrase 3: Bottom
            {
                "id": "phrase_bottom",
                "type": "text",
                "text": "03. Continuous Multi-Agent Verification",
                "position": [960, 720],
                "size": [1500, 140],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 46,
                    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 16}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 20.0},
                            {"frame": 54, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.96},
                            {"frame": 54, "value": 0.96},
                            {"frame": 84, "value": 0.96},
                            {"frame": 98, "value": 1.04},
                            {"frame": 114, "value": 1.04},
                            {"frame": 128, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 54, "value": 0.35},
                            {"frame": 84, "value": 0.35},
                            {"frame": 98, "value": 1.0},
                            {"frame": 114, "value": 1.0},
                            {"frame": 128, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 2. phrase_ladder_priority
# Stepped staircase indentation with sequential traversal
# Phrase 1: X = 840, Y = 360
# Phrase 2: X = 940, Y = 540
# Phrase 3: X = 1040, Y = 720
# =============================================================================
def build_02_phrase_ladder_priority():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_ladder_priority",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_ladder_priority.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Step 1
            {
                "id": "step_1",
                "type": "text",
                "text": "STEP 1  *  Extract Entity Semantics",
                "position": [840, 360],
                "size": [1200, 130],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 44,
                    "glow": {"color": "#60A5FA", "intensity": 0.60, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -120.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.95},
                            {"frame": 24, "value": 1.03},
                            {"frame": 48, "value": 1.03},
                            {"frame": 64, "value": 0.98},
                            {"frame": 120, "value": 0.98},
                            {"frame": 134, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0},
                            {"frame": 48, "value": 1.0},
                            {"frame": 64, "value": 0.50},
                            {"frame": 120, "value": 0.50},
                            {"frame": 134, "value": 0.88},
                            {"frame": 149, "value": 0.88}
                        ]}
                    ]
                }
            },
            # Step 2
            {
                "id": "step_2",
                "type": "text",
                "text": "STEP 2  *  Synthesize Multi-Channel Layout",
                "position": [940, 540],
                "size": [1200, 130],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 44,
                    "glow": {"color": "#60A5FA", "intensity": 0.60, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 20, "value": -120.0},
                            {"frame": 44, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.95},
                            {"frame": 48, "value": 0.95},
                            {"frame": 64, "value": 1.03},
                            {"frame": 84, "value": 1.03},
                            {"frame": 98, "value": 0.98},
                            {"frame": 120, "value": 0.98},
                            {"frame": 134, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 36, "value": 0.40},
                            {"frame": 48, "value": 0.40},
                            {"frame": 64, "value": 1.0},
                            {"frame": 84, "value": 1.0},
                            {"frame": 98, "value": 0.50},
                            {"frame": 120, "value": 0.50},
                            {"frame": 134, "value": 0.88},
                            {"frame": 149, "value": 0.88}
                        ]}
                    ]
                }
            },
            # Step 3
            {
                "id": "step_3",
                "type": "text",
                "text": "STEP 3  *  Synchronize Unified Motion",
                "position": [1040, 720],
                "size": [1200, 130],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 44,
                    "glow": {"color": "#60A5FA", "intensity": 0.60, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 44, "value": -120.0},
                            {"frame": 68, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.95},
                            {"frame": 84, "value": 0.95},
                            {"frame": 98, "value": 1.03},
                            {"frame": 120, "value": 1.03},
                            {"frame": 134, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 68, "value": 0.40},
                            {"frame": 84, "value": 0.40},
                            {"frame": 98, "value": 1.0},
                            {"frame": 120, "value": 1.0},
                            {"frame": 134, "value": 0.88},
                            {"frame": 149, "value": 0.88}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 3. phrase_dual_side_compare
# Two distinct columns for comparative statements: Left vs Right
# Left: Statement (X = 540, Y = 540)
# Right: Counterstatement (X = 1380, Y = 540)
# =============================================================================
def build_03_phrase_dual_side_compare():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_dual_side_compare",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_dual_side_compare.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Header
            {
                "id": "left_badge",
                "type": "text",
                "text": "TRADITIONAL MODEL",
                "position": [540, 420],
                "size": [680, 80],
                "style": {
                    "fill": "#F87171",
                    "font": FONT_BOLD,
                    "font_size": 28
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "linear", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 16, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            },
            # Left Body
            {
                "id": "left_body",
                "type": "text",
                "text": "Sequential cuts drop viewer focus and fragment contextual narrative continuity.",
                "position": [540, 560],
                "size": [680, 240],
                "style": {
                    "fill": "#F1F5F9",
                    "font": FONT_INTER,
                    "font_size": 36
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": -80.0},
                            {"frame": 24, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.95},
                            {"frame": 24, "value": 1.03},
                            {"frame": 54, "value": 1.03},
                            {"frame": 72, "value": 0.97},
                            {"frame": 114, "value": 0.97},
                            {"frame": 128, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 20, "value": 1.0},
                            {"frame": 54, "value": 1.0},
                            {"frame": 72, "value": 0.55},
                            {"frame": 114, "value": 0.55},
                            {"frame": 128, "value": 0.95},
                            {"frame": 149, "value": 0.95}
                        ]}
                    ]
                }
            },
            # Right Header
            {
                "id": "right_badge",
                "type": "text",
                "text": "CHRONON MULTI-ENTITY",
                "position": [1380, 420],
                "size": [680, 80],
                "style": {
                    "fill": "#38BDF8",
                    "font": FONT_BOLD,
                    "font_size": 28
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "linear", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 54, "value": 0.0},
                            {"frame": 70, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            },
            # Right Body
            {
                "id": "right_body",
                "type": "text",
                "text": "Unified simultaneous choreography anchors entities with active priority shifts.",
                "position": [1380, 560],
                "size": [680, 240],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_INTER,
                    "font_size": 36,
                    "glow": {"color": "#38BDF8", "intensity": 0.50, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "out_cubic", "keyframes": [
                            {"frame": 48, "value": 80.0},
                            {"frame": 72, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.95},
                            {"frame": 48, "value": 0.95},
                            {"frame": 72, "value": 1.03},
                            {"frame": 114, "value": 1.03},
                            {"frame": 128, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 48, "value": 0.0},
                            {"frame": 72, "value": 1.0},
                            {"frame": 114, "value": 1.0},
                            {"frame": 128, "value": 0.95},
                            {"frame": 149, "value": 0.95}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 4. phrase_stagger_keep_alive
# 4 sequential points enter rhythmically; NONE disappear; all remain crisp and live
# =============================================================================
def build_04_phrase_stagger_keep_alive():
    items = [
        ("item_1", "+ High-Throughput Parallel Pipeline Architecture", 320, 0),
        ("item_2", "+ Sub-Pixel Multi-Layer Coordinate Placement", 460, 16),
        ("item_3", "+ Dynamic Visual Priority Focus Scheduling", 600, 32),
        ("item_4", "+ Direct Streamline Hardware Encoding", 740, 48)
    ]
    layers = [make_bg_layer()]
    for item_id, text, y_pos, start_f in items:
        scale_keys = []
        opacity_keys = []
        if start_f > 0:
            scale_keys.append({"frame": 0, "value": 0.96})
            scale_keys.append({"frame": start_f, "value": 0.96})
            opacity_keys.append({"frame": 0, "value": 0.0})
            opacity_keys.append({"frame": start_f, "value": 0.0})
        else:
            scale_keys.append({"frame": 0, "value": 0.96})
            opacity_keys.append({"frame": 0, "value": 0.0})

        scale_keys.extend([
            {"frame": start_f + 16, "value": 1.02},
            {"frame": start_f + 32, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])
        opacity_keys.extend([
            {"frame": start_f + 14, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])

        layers.append({
            "id": item_id,
            "type": "text",
            "text": text,
            "position": [960, y_pos],
            "size": [1500, 110],
            "style": {
                "fill": "#FFFFFF",
                "font": FONT_BOLD,
                "font_size": 38,
                "glow": {"color": "#38BDF8", "intensity": 0.45, "radius": 12}
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "position_y", "easing": "out_cubic", "keyframes": [
                        {"frame": start_f, "value": 24.0},
                        {"frame": start_f + 18, "value": 0.0},
                        {"frame": 149, "value": 0.0}
                    ]},
                    {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                    {"property": "opacity", "easing": "out_cubic", "keyframes": opacity_keys}
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_stagger_keep_alive",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_stagger_keep_alive.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 5. phrase_center_with_history
# Active hero statement stays center, previous ascends to history stack above
# Settles into unified summary
# =============================================================================
def build_05_phrase_center_with_history():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_center_with_history",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_center_with_history.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Phrase 1: Begins as Hero Center (Y: 540), ascends to History (Y: 380)
            {
                "id": "hero_phrase_1",
                "type": "text",
                "text": "1. Multi-Entity Dynamic Composition",
                "position": [960, 540],
                "size": [1500, 140],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 48,
                    "glow": {"color": "#38BDF8", "intensity": 0.50, "radius": 16}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 30.0},
                            {"frame": 20, "value": 0.0},
                            {"frame": 52, "value": 0.0},
                            {"frame": 74, "value": -160.0},
                            {"frame": 149, "value": -160.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 20, "value": 1.05},
                            {"frame": 52, "value": 1.05},
                            {"frame": 74, "value": 0.92},
                            {"frame": 120, "value": 0.92},
                            {"frame": 134, "value": 0.98},
                            {"frame": 149, "value": 0.98}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 16, "value": 1.0},
                            {"frame": 52, "value": 1.0},
                            {"frame": 74, "value": 0.52},
                            {"frame": 120, "value": 0.52},
                            {"frame": 134, "value": 0.90},
                            {"frame": 149, "value": 0.90}
                        ]}
                    ]
                }
            },
            # Phrase 2: Begins below (Y: 700), steps into Hero Center (Y: 540)
            {
                "id": "hero_phrase_2",
                "type": "text",
                "text": "2. Zero Dropouts * Full Screen Retention",
                "position": [960, 540],
                "size": [1500, 140],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 48,
                    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 16}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 160.0},
                            {"frame": 52, "value": 160.0},
                            {"frame": 74, "value": 0.0},
                            {"frame": 149, "value": 0.0}
                        ]},
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.92},
                            {"frame": 52, "value": 0.92},
                            {"frame": 74, "value": 1.05},
                            {"frame": 120, "value": 1.05},
                            {"frame": 134, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 52, "value": 0.0},
                            {"frame": 74, "value": 1.0},
                            {"frame": 120, "value": 1.0},
                            {"frame": 134, "value": 0.95},
                            {"frame": 149, "value": 0.95}
                        ]}
                    ]
                }
            },
            # Subtitle / Conclusion Tag below
            {
                "id": "summary_tag",
                "type": "text",
                "text": "VELOX INTEGRATED NARRATIVE ARCHITECTURE",
                "position": [960, 700],
                "size": [1500, 80],
                "style": {
                    "fill": "#60A5FA",
                    "font": FONT_INTER,
                    "font_size": 28
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 105, "value": 0.0},
                            {"frame": 126, "value": 0.85},
                            {"frame": 149, "value": 0.85}
                        ]}
                    ]
                }
            }
        ]
    }


# =============================================================================
# 6. phrase_quote_strip
# 3 horizontal quote blocks across the canvas with progressive focus sweep
# =============================================================================
def build_06_phrase_quote_strip():
    quotes = [
        ("q_1", "\"Velocity is our compass\"", 460, 0),
        ("q_2", "\"Simultaneous orchestration\"", 960, 48),
        ("q_3", "\"Clarity defines precision\"", 1460, 92)
    ]
    layers = [make_bg_layer()]
    for q_id, text, x_pos, focus_start in quotes:
        focus_end = focus_start + 40
        if focus_start == 0:
            scale_keys = [
                {"frame": 0, "value": 0.92},
                {"frame": 12, "value": 1.05},
                {"frame": focus_end, "value": 1.05},
                {"frame": focus_end + 10, "value": 0.96},
                {"frame": 132, "value": 0.96},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": 12, "value": 1.0},
                {"frame": focus_end, "value": 1.0},
                {"frame": focus_end + 10, "value": 0.70},
                {"frame": 132, "value": 0.70},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
        else:
            scale_keys = [
                {"frame": 0, "value": 0.92},
                {"frame": 20, "value": 0.96},
                {"frame": focus_start, "value": 0.96},
                {"frame": focus_start + 10, "value": 1.05},
                {"frame": focus_end, "value": 1.05},
                {"frame": min(focus_end + 10, 132), "value": 0.96},
                {"frame": 132, "value": 0.96},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": 20, "value": 0.70},
                {"frame": focus_start, "value": 0.70},
                {"frame": focus_start + 10, "value": 1.0},
                {"frame": focus_end, "value": 1.0},
                {"frame": min(focus_end + 10, 132), "value": 0.70},
                {"frame": 132, "value": 0.70},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]

        layers.append({
            "id": q_id,
            "type": "text",
            "text": text,
            "position": [x_pos, 540],
            "size": [480, 240],
            "style": {
                "fill": "#FFFFFF",
                "font": FONT_BOLD,
                "font_size": 36,
                "glow": {"color": "#38BDF8", "intensity": 0.50, "radius": 14}
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "scale", "easing": "in_out_cubic", "keyframes": clean_keyframes(scale_keys)},
                    {"property": "opacity", "easing": "in_out_cubic", "keyframes": clean_keyframes(opacity_keys)}
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_quote_strip",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_quote_strip.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 7. phrase_timeline_reveal
# 3 chronological milestone statements revealing in progression
# =============================================================================
def build_07_phrase_timeline_reveal():
    milestones = [
        ("m_1", "2024  *  NEURAL SHADERS & ATOMICS", 360, 0),
        ("m_2", "2025  *  MULTI-AGENT SPATIAL REASONING", 540, 40),
        ("m_3", "2026  *  DIRECT HARDWARE YUV MUXING", 720, 80)
    ]
    layers = [make_bg_layer()]
    for m_id, text, y_pos, start_f in milestones:
        if start_f == 0:
            pos_keys = [
                {"frame": 0, "value": 20.0},
                {"frame": 18, "value": 0.0},
                {"frame": 149, "value": 0.0}
            ]
            scale_keys = [
                {"frame": 0, "value": 0.94},
                {"frame": 16, "value": 1.04},
                {"frame": 36, "value": 1.04},
                {"frame": 48, "value": 0.97},
                {"frame": 128, "value": 0.97},
                {"frame": 138, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": 14, "value": 1.0},
                {"frame": 36, "value": 1.0},
                {"frame": 48, "value": 0.60},
                {"frame": 128, "value": 0.60},
                {"frame": 138, "value": 0.95},
                {"frame": 149, "value": 0.95}
            ]
        else:
            pos_keys = [
                {"frame": 0, "value": 20.0},
                {"frame": start_f, "value": 20.0},
                {"frame": start_f + 18, "value": 0.0},
                {"frame": 149, "value": 0.0}
            ]
            scale_keys = [
                {"frame": 0, "value": 0.94},
                {"frame": start_f, "value": 0.94},
                {"frame": start_f + 16, "value": 1.04},
                {"frame": start_f + 36, "value": 1.04},
                {"frame": min(start_f + 48, 128), "value": 0.97},
                {"frame": 128, "value": 0.97},
                {"frame": 138, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": start_f, "value": 0.0},
                {"frame": start_f + 14, "value": 1.0},
                {"frame": start_f + 36, "value": 1.0},
                {"frame": min(start_f + 48, 128), "value": 0.60},
                {"frame": 128, "value": 0.60},
                {"frame": 138, "value": 0.95},
                {"frame": 149, "value": 0.95}
            ]

        layers.append({
            "id": m_id,
            "type": "text",
            "text": text,
            "position": [960, y_pos],
            "size": [1500, 130],
            "style": {
                "fill": "#FFFFFF",
                "font": FONT_BOLD,
                "font_size": 42,
                "glow": {"color": "#60A5FA", "intensity": 0.55, "radius": 14}
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "position_y", "easing": "out_cubic", "keyframes": clean_keyframes(pos_keys)},
                    {"property": "scale", "easing": "in_out_cubic", "keyframes": clean_keyframes(scale_keys)},
                    {"property": "opacity", "easing": "in_out_cubic", "keyframes": clean_keyframes(opacity_keys)}
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_timeline_reveal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_timeline_reveal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 8. phrase_marker_highlight_cycle
# 3 phrases with clean visual highlight / glow accent cycle
# =============================================================================
def build_08_phrase_marker_highlight_cycle():
    items = [
        ("h_1", "1. Sub-Pixel Kinetic Layout Alignment", 380, 0),
        ("h_2", "2. Dynamic Focus Priority Scheduling", 540, 45),
        ("h_3", "3. Complete Zero-Dropout Retention", 700, 90)
    ]
    layers = [make_bg_layer()]
    for h_id, text, y_pos, active_start in items:
        active_end = active_start + 40
        if active_start == 0:
            scale_keys = [
                {"frame": 0, "value": 0.95},
                {"frame": 10, "value": 1.05},
                {"frame": active_end, "value": 1.05},
                {"frame": active_end + 10, "value": 0.98},
                {"frame": 132, "value": 0.98},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": 10, "value": 1.0},
                {"frame": active_end, "value": 1.0},
                {"frame": active_end + 10, "value": 0.65},
                {"frame": 132, "value": 0.65},
                {"frame": 142, "value": 0.95},
                {"frame": 149, "value": 0.95}
            ]
        else:
            scale_keys = [
                {"frame": 0, "value": 0.95},
                {"frame": 18, "value": 0.98},
                {"frame": active_start, "value": 0.98},
                {"frame": active_start + 8, "value": 1.05},
                {"frame": active_end, "value": 1.05},
                {"frame": min(active_end + 8, 132), "value": 0.98},
                {"frame": 132, "value": 0.98},
                {"frame": 142, "value": 1.0},
                {"frame": 149, "value": 1.0}
            ]
            opacity_keys = [
                {"frame": 0, "value": 0.0},
                {"frame": 18, "value": 0.70},
                {"frame": active_start, "value": 0.70},
                {"frame": active_start + 8, "value": 1.0},
                {"frame": active_end, "value": 1.0},
                {"frame": min(active_end + 8, 132), "value": 0.65},
                {"frame": 132, "value": 0.65},
                {"frame": 142, "value": 0.95},
                {"frame": 149, "value": 0.95}
            ]

        layers.append({
            "id": h_id,
            "type": "text",
            "text": text,
            "position": [960, y_pos],
            "size": [1500, 130],
            "style": {
                "fill": "#FFFFFF",
                "font": FONT_BOLD,
                "font_size": 44,
                "glow": {"color": "#38BDF8", "intensity": 0.50, "radius": 14}
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "scale", "easing": "in_out_cubic", "keyframes": clean_keyframes(scale_keys)},
                    {"property": "opacity", "easing": "in_out_cubic", "keyframes": clean_keyframes(opacity_keys)}
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_marker_highlight_cycle",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_marker_highlight_cycle.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 9. phrase_compact_columns
# 4 concise points in a balanced 2-column matrix
# =============================================================================
def build_09_phrase_compact_columns():
    items = [
        ("c_1", "01 / Parallel Batch Dispatch", 620, 420, 0),
        ("c_2", "02 / Sub-Pixel Alignment", 620, 640, 24),
        ("c_3", "03 / Priority Scheduling", 1300, 420, 48),
        ("c_4", "04 / Direct Stream Encoding", 1300, 640, 72)
    ]
    layers = [make_bg_layer()]
    for c_id, text, x_pos, y_pos, start_f in items:
        scale_keys = []
        opacity_keys = []
        if start_f > 0:
            scale_keys.append({"frame": 0, "value": 0.94})
            scale_keys.append({"frame": start_f, "value": 0.94})
            opacity_keys.append({"frame": 0, "value": 0.0})
            opacity_keys.append({"frame": start_f, "value": 0.0})
        else:
            scale_keys.append({"frame": 0, "value": 0.94})
            opacity_keys.append({"frame": 0, "value": 0.0})
        scale_keys.extend([
            {"frame": start_f + 16, "value": 1.04},
            {"frame": start_f + 32, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])
        opacity_keys.extend([
            {"frame": start_f + 14, "value": 1.0},
            {"frame": 149, "value": 1.0}
        ])

        layers.append({
            "id": c_id,
            "type": "text",
            "text": text,
            "position": [x_pos, y_pos],
            "size": [600, 160],
            "style": {
                "fill": "#FFFFFF",
                "font": FONT_BOLD,
                "font_size": 36,
                "glow": {"color": "#38BDF8", "intensity": 0.45, "radius": 12}
            },
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "scale", "easing": "in_out_cubic", "keyframes": scale_keys},
                    {"property": "opacity", "easing": "in_out_cubic", "keyframes": opacity_keys}
                ]
            }
        })

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_compact_columns",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_compact_columns.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


# =============================================================================
# 10. phrase_focus_swap_hold
# Two major thesis statements swap focus and settle into an extended comparison hold
# =============================================================================
def build_10_phrase_focus_swap_hold():
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "phrase_focus_swap_hold",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "phrase_focus_swap_hold.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            make_bg_layer(),
            # Left Card
            {
                "id": "swap_left",
                "type": "text",
                "text": "STATEMENT A\nFragmented single-entity overlays disrupt narrative pacing and immersion.",
                "position": [540, 540],
                "size": [680, 320],
                "style": {
                    "fill": "#F1F5F9",
                    "font": FONT_BOLD,
                    "font_size": 36,
                    "glow": {"color": "#60A5FA", "intensity": 0.50, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 22, "value": 1.04},
                            {"frame": 54, "value": 1.04},
                            {"frame": 72, "value": 0.96},
                            {"frame": 105, "value": 0.96},
                            {"frame": 120, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 18, "value": 1.0},
                            {"frame": 54, "value": 1.0},
                            {"frame": 72, "value": 0.60},
                            {"frame": 105, "value": 0.60},
                            {"frame": 120, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            },
            # Right Card
            {
                "id": "swap_right",
                "type": "text",
                "text": "STATEMENT B\nUnified multi-entity choreography preserves total contextual comprehension.",
                "position": [1380, 540],
                "size": [680, 320],
                "style": {
                    "fill": "#FFFFFF",
                    "font": FONT_BOLD,
                    "font_size": 36,
                    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 14}
                },
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.94},
                            {"frame": 54, "value": 0.94},
                            {"frame": 72, "value": 1.04},
                            {"frame": 105, "value": 1.04},
                            {"frame": 120, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]},
                        {"property": "opacity", "easing": "in_out_cubic", "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 54, "value": 0.0},
                            {"frame": 72, "value": 1.0},
                            {"frame": 105, "value": 1.0},
                            {"frame": 120, "value": 1.0},
                            {"frame": 149, "value": 1.0}
                        ]}
                    ]
                }
            }
        ]
    }


PRESETS = [
    ("phrase_vertical_focus_stack", build_01_phrase_vertical_focus_stack),
    ("phrase_ladder_priority", build_02_phrase_ladder_priority),
    ("phrase_dual_side_compare", build_03_phrase_dual_side_compare),
    ("phrase_stagger_keep_alive", build_04_phrase_stagger_keep_alive),
    ("phrase_center_with_history", build_05_phrase_center_with_history),
    ("phrase_quote_strip", build_06_phrase_quote_strip),
    ("phrase_timeline_reveal", build_07_phrase_timeline_reveal),
    ("phrase_marker_highlight_cycle", build_08_phrase_marker_highlight_cycle),
    ("phrase_compact_columns", build_09_phrase_compact_columns),
    ("phrase_focus_swap_hold", build_10_phrase_focus_swap_hold)
]


def validate_plan(plan_path):
    cmd = [
        str(CHRONON_CLI),
        "validate",
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
        str(CHRONON_CLI),
        "render",
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
    print("CHRONON MULTI-PHRASE LAYOUT V1 SUITE")
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

    manifest_path = OUT_DIR / "multi_phrase_v1_manifest.json"
    uploaded = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                uploaded = json.load(f)
        except Exception:
            pass

    # 2. Sequential / Parallel Render phase
    print("\n--- PHASE 2: Chronon3d High-Speed Rendering ---")
    results = {}
    for name, plan_path in plans:
        mp4_path = OUT_DIR / f"{name}.mp4"
        poster_path = OUT_DIR / f"{name}_poster.png"
        if mp4_path.exists() and name in uploaded:
            print(f"  [CACHED] {name} already rendered and uploaded.")
            results[name] = {"mp4": mp4_path, "poster": poster_path, "cached": True}
            continue
        print(f"  Rendering {name} ...", end="", flush=True)
        ok, dt = render_plan(plan_path)
        if ok and mp4_path.exists():
            size_mb = mp4_path.stat().st_size / (1024 * 1024)
            extract_poster(mp4_path, poster_path)
            print(f" DONE in {dt:.2f}s ({size_mb:.2f} MB)")
            results[name] = {"mp4": mp4_path, "poster": poster_path, "time": dt, "size": size_mb, "cached": False}
        else:
            print(f" FAILED!")

    # 3. Google Drive Upload phase
    print("\n--- PHASE 3: Google Drive Upload ---")
    token = refresh_drive_token()
    print(f"  Drive token refreshed successfully.")
    for name, data in results.items():
        if data.get("cached") and name in uploaded:
            continue
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
        with open(manifest_path, "w") as f:
            json.dump(uploaded, f, indent=2)

    print(f"\nManifest saved to {manifest_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
