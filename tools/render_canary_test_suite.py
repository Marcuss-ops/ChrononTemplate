#!/usr/bin/env python3
"""
Chronon Canary & Procedural Test Backgrounds Suite
Renders the dedicated test background plans directly from the test suite:
1. canary_01_documentary_investigative (Rect + Linear Gradient + Fractal Noise + Grain + Grid)
2. canary_02_floating_glass_media_card (Rounded Rect + Neon Stroke + Floating Hover)
3. canary_03_radar_telemetry_grid (Procedural Radar Reticle + Grid + Scan Beam)
4. canary_04_procedural_star_constellation (5-Point Star + 360 Spin + Dual Halo)
5. canary_05_procedural_hexprism_polygon (6-Point Hexagon + Concentric Counter-Orbit)
6. canary_06_hud_circular_arc_meter (270deg Arc Meter + Rotation + Glowing Stroke)
7. canary_07_bezier_vector_path_wave (Custom SVG Bezier Path + Wave Undulation)
8. canary_08_radial_spotlight_studio (Radial Gradient Dark Spotlight + Pulse)

Renders each to 1080p MP4 + snapshot PNG, and uploads to Google Drive folder 1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS.
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

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "canary_backgrounds"
TOKEN_PATH = BASE_DIR / "refactored" / "token.json"
CREDS_PATH = BASE_DIR / "refactored" / "credentials.json"
DRIVE_FOLDER_ID = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 60  # 2.0s seamless loop

def loop_cos(min_val, max_val, frame, total_frames=DURATION_FRAMES):
    ratio = (1.0 - math.cos(2.0 * math.pi * frame / total_frames)) * 0.5
    return min_val + (max_val - min_val) * ratio

def hud_badge(title, category):
    return [
        {
            "id": "hud_tag",
            "type": "text",
            "text": category.upper(),
            "size": [600, 24],
            "position": [360, 57],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "style": {
                "font": "assets/fonts/Inter-Bold.ttf",
                "font_size": 13.0,
                "fill": "#38BDF8"
            }
        },
        {
            "id": "hud_title",
            "type": "text",
            "text": title,
            "size": [800, 44],
            "position": [460, 97],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "style": {
                "font": "assets/fonts/Poppins-Bold.ttf",
                "font_size": 28.0,
                "fill": "#FFFFFF"
            }
        }
    ]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Canary A: Documentary Background (Go Test: TestDocumentaryBackgroundE2E)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_01_documentary():
    grid_x_keys = []
    grid_y_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        prog = f / DURATION_FRAMES
        grid_x_keys.append({"frame": f, "value": -prog * 64.0})
        grid_y_keys.append({"frame": f, "value": -prog * 32.0})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_01_documentary_investigative",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_01_documentary_investigative.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "doc_base",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": {
                        "type": "linear",
                        "start": [0.0, 0.0],
                        "end": [0.0, 1.0],
                        "color_stops": [
                            {"position": 0.0, "color": [0.035, 0.05, 0.08, 1.0]},
                            {"position": 1.0, "color": [0.075, 0.10, 0.16, 1.0]}
                        ]
                    }
                },
                "effects": [
                    {"type": "fractal_noise", "amplitude": 0.06},
                    {"type": "vignette"},
                    {"type": "noise", "amount": 0.04}
                ]
            },
            {
                "id": "doc_grid",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "opacity": 0.45,
                "shape": {
                    "type": "grid",
                    "spacing": 64.0,
                    "stroke": {"color": "#1C2738", "width": 1.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": grid_x_keys},
                        {"property": "position_y", "easing": "linear", "keyframes": grid_y_keys}
                    ]
                }
            }
        ] + hud_badge("Documentary Investigative Canary", "Canary Suite • Test A")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 2. Canary B: Floating Glass Media Card (Go Test: TestMediaCardBackgroundE2E)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_02_mediacard():
    y_keys = []
    pulse_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        y_off = loop_cos(-18.0, 18.0, f)
        y_keys.append({"frame": f, "value": y_off})
        s = loop_cos(1.0, 1.02, f)
        pulse_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_02_floating_glass_media_card",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_02_floating_glass_media_card.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "bg_dark",
                "type": "color",
                "color": [0.03, 0.04, 0.07, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "card_halo",
                "type": "shape",
                "size": [840, 540],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rounded_rect",
                    "radius": 40.0,
                    "fill": [0.22, 0.74, 0.97, 0.12]
                },
                "effects": [
                    {"type": "gaussian_blur", "radius": 32.0}
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": y_keys},
                        {"property": "scale", "easing": "linear", "keyframes": pulse_keys}
                    ]
                }
            },
            {
                "id": "media_card",
                "type": "shape",
                "size": [816, 516],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rounded_rect",
                    "radius": 32.0,
                    "fill": [0.04, 0.06, 0.11, 0.92],
                    "stroke": {"color": "#38BDF8", "width": 4.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": y_keys}
                    ]
                }
            }
        ] + hud_badge("Floating Glass Media Card", "Canary Suite • Test B")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 3. Canary C: Radar Telemetry Network (Coordinate Grid + Rotating Sensor Beam)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_03_telemetry():
    beam_rot = []
    pulse_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        deg = (f / DURATION_FRAMES) * 360.0
        beam_rot.append({"frame": f, "value": deg})
        op = loop_cos(0.4, 0.8, f)
        pulse_keys.append({"frame": f, "value": op})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_03_radar_telemetry_grid",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_03_radar_telemetry_grid.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_radar_base",
                "type": "color",
                "color": [0.02, 0.03, 0.06, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "radar_grid",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "opacity": 0.35,
                "shape": {
                    "type": "grid",
                    "spacing": 80.0,
                    "stroke": {"color": "#0E7490", "width": 1.0}
                }
            },
            {
                "id": "reticle_outer",
                "type": "shape",
                "size": [640, 640],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.0, 0.0, 0.0, 0.0],
                    "stroke": {"color": "#06B6D4", "width": 2.0}
                }
            },
            {
                "id": "radar_beam",
                "type": "shape",
                "size": [600, 600],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arc",
                    "start_degrees": 0.0,
                    "sweep_degrees": 90.0,
                    "stroke": {"color": "#22D3EE", "width": 8.0}
                },
                "effects": [
                    {"type": "gaussian_blur", "radius": 12.0}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": beam_rot}
                    ]
                }
            }
        ] + hud_badge("Telemetry Radar Sweep", "Canary Suite • Test C")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 4. Star Constellation (Go Test: TestStarCompiles)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_04_star():
    rot_keys = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        deg = (f / DURATION_FRAMES) * 360.0
        rot_keys.append({"frame": f, "value": deg})
        s = loop_cos(0.92, 1.08, f)
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_04_procedural_star_constellation",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_04_procedural_star_constellation.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_void",
                "type": "color",
                "color": [0.03, 0.02, 0.06, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "star_halo",
                "type": "shape",
                "size": [580, 580],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "star",
                    "points": 5,
                    "inner_radius_ratio": 0.45,
                    "fill": [0.98, 0.75, 0.18, 0.15]
                },
                "effects": [
                    {"type": "gaussian_blur", "radius": 24.0}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys}
                    ]
                }
            },
            {
                "id": "star_hero",
                "type": "shape",
                "size": [480, 480],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "star",
                    "points": 5,
                    "inner_radius_ratio": 0.45,
                    "fill": [0.98, 0.75, 0.18, 0.90],
                    "stroke": {"color": "#FFFBEB", "width": 4.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            }
        ] + hud_badge("Procedural Star Constellation", "Shape Test Suite • Star")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 5. Hexagon Prism Core (Go Test: TestPolygonCompiles)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_05_polygon():
    rot_fwd = []
    rot_rev = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        deg = (f / DURATION_FRAMES) * 360.0
        rot_fwd.append({"frame": f, "value": deg})
        rot_rev.append({"frame": f, "value": -deg})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_05_procedural_hexprism_polygon",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_05_procedural_hexprism_polygon.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_violet",
                "type": "color",
                "color": [0.04, 0.02, 0.07, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "outer_hex",
                "type": "shape",
                "size": [620, 620],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "polygon",
                    "points": 6,
                    "fill": [0.55, 0.15, 0.90, 0.10],
                    "stroke": {"color": "#C084FC", "width": 3.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_rev}
                    ]
                }
            },
            {
                "id": "inner_hex",
                "type": "shape",
                "size": [440, 440],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "polygon",
                    "points": 6,
                    "fill": [0.75, 0.20, 0.95, 0.35],
                    "stroke": {"color": "#F472B6", "width": 4.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_fwd}
                    ]
                }
            }
        ] + hud_badge("Procedural Hexagon Prism Core", "Shape Test Suite • Polygon")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 6. HUD Circular Arc Meter (Go Test: TestArcCompiles)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_06_arc():
    rot_keys = []
    pulse_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        deg = (f / DURATION_FRAMES) * 360.0
        rot_keys.append({"frame": f, "value": deg})
        s = loop_cos(0.95, 1.05, f)
        pulse_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_06_hud_circular_arc_meter",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_06_hud_circular_arc_meter.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.02, 0.03, 0.06, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "arc_glow",
                "type": "shape",
                "size": [560, 560],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arc",
                    "start_degrees": 45.0,
                    "sweep_degrees": 270.0,
                    "stroke": {"color": "#00F0FF", "width": 24.0}
                },
                "effects": [
                    {"type": "gaussian_blur", "radius": 20.0}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys}
                    ]
                }
            },
            {
                "id": "arc_solid",
                "type": "shape",
                "size": [520, 520],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arc",
                    "start_degrees": 45.0,
                    "sweep_degrees": 270.0,
                    "stroke": {"color": "#E0F2FE", "width": 16.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys},
                        {"property": "scale", "easing": "linear", "keyframes": pulse_keys}
                    ]
                }
            }
        ] + hud_badge("Circular Telemetry Arc Meter", "Shape Test Suite • Arc")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 7. Bezier Vector Path Wave (Go Test: TestPathCompiles)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_07_path():
    y_keys = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        y_off = loop_cos(-25.0, 25.0, f)
        y_keys.append({"frame": f, "value": y_off})
        s = loop_cos(0.96, 1.04, f)
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_07_bezier_vector_path_wave",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_07_bezier_vector_path_wave.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.02, 0.04, 0.05, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "vector_wave",
                "type": "shape",
                "size": [1200, 480],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "path",
                    "path": [
                        {"type": "move_to", "point": [-600.0, 0.0]},
                        {"type": "cubic_to", "point": [0.0, 0.0], "control1": [-300.0, -120.0], "control2": [-150.0, 120.0]},
                        {"type": "cubic_to", "point": [600.0, 0.0], "control1": [150.0, -120.0], "control2": [300.0, 120.0]},
                        {"type": "line_to", "point": [600.0, 240.0]},
                        {"type": "line_to", "point": [-600.0, 240.0]},
                        {"type": "close"}
                    ],
                    "fill": [0.08, 0.65, 0.55, 0.70],
                    "stroke": {"color": "#5EEAD4", "width": 4.0}
                },
                "effects": [
                    {"type": "gaussian_blur", "radius": 4.0}
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": y_keys},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            }
        ] + hud_badge("Bezier Vector Path Undulation", "Shape Test Suite • Path")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 8. Radial Spotlight Studio (Go Test: TestRadialGradientCompiles)
# ─────────────────────────────────────────────────────────────────────────────
def build_canary_08_radial():
    pulse_keys = []
    opacity_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        s = loop_cos(0.95, 1.08, f)
        pulse_keys.append({"frame": f, "value": s})
        op = loop_cos(0.85, 1.0, f)
        opacity_keys.append({"frame": f, "value": op})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "canary_08_radial_spotlight_studio",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "canary_08_radial_spotlight_studio.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "radial_spot",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": {
                        "type": "radial",
                        "center": [0.5, 0.5],
                        "radius": 1.0,
                        "color_stops": [
                            {"position": 0.0, "color": [0.12, 0.16, 0.23, 1.0]},
                            {"position": 1.0, "color": [0.02, 0.03, 0.07, 1.0]}
                        ]
                    }
                },
                "effects": [
                    {"type": "vignette"},
                    {"type": "noise", "amount": 0.05}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "linear", "keyframes": pulse_keys},
                        {"property": "opacity", "easing": "linear", "keyframes": opacity_keys}
                    ]
                }
            }
        ] + hud_badge("Radial Gradient Studio Spotlight", "Shape Test Suite • Radial")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# Drive Helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_drive_access_token():
    with open(TOKEN_PATH) as f:
        tok_data = json.load(f)
    with open(CREDS_PATH) as f:
        creds = json.load(f)
    client_info = creds.get("installed") or creds.get("web")
    params = {
        "client_id": client_info["client_id"],
        "client_secret": client_info["client_secret"],
        "refresh_token": tok_data.get("refresh_token"),
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

# ─────────────────────────────────────────────────────────────────────────────
# Main Suite Execution
# ─────────────────────────────────────────────────────────────────────────────
CANARY_SUITE = [
    ("canary_01_documentary_investigative", build_canary_01_documentary),
    ("canary_02_floating_glass_media_card", build_canary_02_mediacard),
    ("canary_03_radar_telemetry_grid", build_canary_03_telemetry),
    ("canary_04_procedural_star_constellation", build_canary_04_star),
    ("canary_05_procedural_hexprism_polygon", build_canary_05_polygon),
    ("canary_06_hud_circular_arc_meter", build_canary_06_arc),
    ("canary_07_bezier_vector_path_wave", build_canary_07_path),
    ("canary_08_radial_spotlight_studio", build_canary_08_radial),
]

def main():
    print(f"=== Starting Chronon Canary & Test Backgrounds Suite ({len(CANARY_SUITE)} items) ===", flush=True)
    
    # 1. Write plans and validate
    plan_files = []
    for item_id, builder in CANARY_SUITE:
        plan_data = builder()
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2))
        
        # Validate
        vcmd = [str(CHRONON_CLI), "validate", "--plan", str(plan_path), "--assets-root", str(ASSETS_ROOT)]
        vres = subprocess.run(vcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if vres.returncode != 0:
            print(f"  [VALIDATION FAIL] {item_id}: {vres.stderr}")
            sys.exit(1)
        plan_files.append((item_id, plan_path))
        print(f"  ✓ [Validated] {plan_path.name}")

    # 2. Render each to MP4
    rendered_files = []
    for item_id, plan_path in plan_files:
        out_mp4 = OUT_DIR / f"{item_id}.mp4"
        cmd = [
            str(CHRONON_CLI),
            "render",
            "--plan", str(plan_path),
            "--assets-root", str(ASSETS_ROOT),
            "--backend", "software",
            "--hardware", "none",
            "--encoder-backend", "pipe",
            "-o", str(out_mp4)
        ]
        print(f"\n[Rendering] {item_id} -> {out_mp4.name}...", flush=True)
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dt = time.time() - t0
        if res.returncode != 0:
            print(f"  [ERROR] {res.stderr}\n{res.stdout}")
        else:
            sz = out_mp4.stat().st_size if out_mp4.exists() else 0
            print(f"  ✓ Rendered in {dt:.1f}s ({sz:,} bytes)")
            rendered_files.append(out_mp4)
            
            # Extract PNG poster at 1.0s
            out_png = OUT_DIR / f"{item_id}.png"
            subprocess.run(["ffmpeg", "-y", "-ss", "00:00:01", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_png.exists():
                rendered_files.append(out_png)

    # 3. Upload to Google Drive
    print(f"\n=== Uploading {len(rendered_files)} canary media files to Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = get_drive_access_token()
    uploads = []
    for fpath in rendered_files:
        print(f"Uploading {fpath.name} ({fpath.stat().st_size:,} bytes)...", flush=True)
        meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
        uploads.append(meta)
        print(f"  ✓ Uploaded! ID: {meta.get('id')}")

    print("\n=== SUMMARY OF COMPLETED CANARY UPLOADS ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")

if __name__ == "__main__":
    main()
