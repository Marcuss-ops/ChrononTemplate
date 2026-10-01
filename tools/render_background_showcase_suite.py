#!/usr/bin/env python3
"""
Comprehensive Chronon Background Showcase Suite - V2 (Certified)
Updated with:
1. Dynamic, smooth looping animation on ALL procedural backgrounds.
2. Perfect mathematical centering for all shape and device mockup elements.
3. Native Chronon position_x / position_y additive offset keyframes.
4. Clean, non-intrusive top-left corner HUD badges so the center showcase is 100% visible.
5. Correct 2D/3D schema compliance (rotation_z scalar, shaft/head ratio for arrow).
6. Automatic render to 1080p MP4 + PNG snapshots, followed by direct Google Drive upload.
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
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "background_showcase"
TOKEN_PATH = BASE_DIR / "refactored" / "token.json"
CREDS_PATH = BASE_DIR / "refactored" / "credentials.json"
DRIVE_FOLDER_ID = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"

OUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 60  # 2.0 seconds: optimal for seamless looping and fast execution

def loop_cos(min_val, max_val, frame, total_frames=DURATION_FRAMES):
    """Seamless cosine loop: frame 0 == frame total_frames == min_val, frame total_frames/2 == max_val"""
    ratio = (1.0 - math.cos(2.0 * math.pi * frame / total_frames)) * 0.5
    return min_val + (max_val - min_val) * ratio

def title_card_layers(title_text, subtitle_text):
    """Clean typography badge placed top-left so central graphics are unobstructed.
    In Chronon, position is the center of the bounding box.
    Tag box is 600x24: center at [60 + 300, 45 + 12] = [360, 57]
    Title box is 800x44: center at [60 + 400, 75 + 22] = [460, 97]
    """
    return [
        {
            "id": "label_tag",
            "type": "text",
            "text": subtitle_text.upper(),
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
            "id": "label_title",
            "type": "text",
            "text": title_text,
            "size": [800, 44],
            "position": [460, 97],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "style": {
                "font": "assets/fonts/Poppins-Bold.ttf",
                "font_size": 28.0,
                "fill": "#FFFFFF",
                "glow": {
                    "radius": 10.0,
                    "intensity": 0.35,
                    "color": "#38BDF8"
                }
            }
        }
    ]

# ─────────────────────────────────────────────────────────────────────────────
# 1. Crime Doc Noir Grain & Vignette (Animated Breathing Pulse)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_01_crime_doc():
    scale_keys = []
    opacity_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        s = loop_cos(1.0, 1.08, f)
        op = loop_cos(0.78, 0.94, f)
        scale_keys.append({"frame": f, "value": s})
        opacity_keys.append({"frame": f, "value": op})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_01_crime_doc_grain_vignette",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_01_crime_doc_grain_vignette.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_base",
                "type": "color",
                "color": [0.015, 0.02, 0.03, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "vignette_layer",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.05, 0.07, 0.10, 0.85]
                },
                "effects": [
                    {"type": "vignette"},
                    {"type": "noise", "amount": 0.20}
                ],
                "animation": {
                    "tracks": [
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys},
                        {"property": "opacity", "easing": "linear", "keyframes": opacity_keys}
                    ]
                }
            }
        ] + title_card_layers("Crime Doc Noir & Film Grain", "Chronon Procedural Background • Test 01")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 2. Minimal Tech Dot Grid (Animated Scanning Sweep Bar)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_02_dot_grid():
    scan_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        x_off = -1100.0 + (f / DURATION_FRAMES) * 2200.0
        scan_keys.append({"frame": f, "value": x_off})

    dot_opac_keys = []
    for f in range(0, DURATION_FRAMES + 1, 4):
        op = loop_cos(0.40, 0.75, f)
        dot_opac_keys.append({"frame": f, "value": op})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_02_tech_dot_grid",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_02_tech_dot_grid.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.02, 0.03, 0.05, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "dot_grid_layer",
                "type": "shape",
                "size": [WIDTH, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "dot_grid",
                    "spacing": 120.0,
                    "dot_radius": 4.0,
                    "fill": [0.22, 0.58, 0.95, 0.65]
                },
                "animation": {
                    "tracks": [
                        {"property": "opacity", "easing": "linear", "keyframes": dot_opac_keys}
                    ]
                }
            },
            {
                "id": "scan_bar",
                "type": "shape",
                "size": [120, HEIGHT],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rect",
                    "fill": [0.22, 0.75, 1.0, 0.15],
                    "stroke": {"color": "#38BDF8", "width": 2.0}
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": scan_keys}
                    ]
                }
            }
        ] + title_card_layers("Cyber Minimal Dot Grid", "Chronon Procedural Background • Test 02")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 3. Blueprint Coordinate Line Grid (Continuous Seamless Drift + Reticle Spin)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_03_line_grid():
    grid_x_keys = []
    grid_y_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        prog = f / DURATION_FRAMES
        grid_x_keys.append({"frame": f, "value": -prog * 80.0})
        grid_y_keys.append({"frame": f, "value": -prog * 80.0})

    rot_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        deg = (f / DURATION_FRAMES) * 360.0
        rot_keys.append({"frame": f, "value": deg})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_03_blueprint_line_grid",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_03_blueprint_line_grid.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.015, 0.025, 0.045, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "grid_lines",
                "type": "shape",
                "size": [WIDTH + 160, HEIGHT + 160],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "grid",
                    "spacing": 80.0,
                    "stroke": {
                        "width": 1.4,
                        "color": [0.15, 0.50, 0.90, 0.35]
                    }
                },
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": grid_x_keys},
                        {"property": "position_y", "easing": "linear", "keyframes": grid_y_keys}
                    ]
                }
            },
            {
                "id": "center_reticle",
                "type": "shape",
                "size": [280, 280],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arc",
                    "start_degrees": 0.0,
                    "sweep_degrees": 300.0,
                    "stroke": {
                        "width": 3.0,
                        "color": [0.22, 0.78, 1.0, 0.85]
                    }
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys}
                    ]
                }
            }
        ] + title_card_layers("Technical Blueprint Coordinate Grid", "Chronon Procedural Background • Test 03")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 4. 3D Fluid Aura Ambient (Orbiting Volumetric Light Orbs)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_04_fluid_aura():
    blobs = [
        {"color": "#7C3AED", "radius": 440.0, "intensity": 0.85, "cx": 740.0, "cy": 500.0, "bz": -260.0, "rx": 220.0, "ry": 120.0},
        {"color": "#06B6D4", "radius": 390.0, "intensity": 0.75, "cx": 1180.0, "cy": 580.0, "bz": -150.0, "rx": 200.0, "ry": 140.0},
        {"color": "#EC4899", "radius": 320.0, "intensity": 0.65, "cx": 960.0, "cy": 450.0, "bz": -50.0, "rx": 160.0, "ry": 100.0}
    ]
    layers = [
        {
            "id": "base_bg",
            "type": "color",
            "color": [0.02, 0.025, 0.04, 1.0],
            "size": [WIDTH, HEIGHT],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES
        }
    ]
    for idx, b in enumerate(blobs):
        pos_keys = []
        for f in range(0, DURATION_FRAMES + 1, 3):
            angle = (f / DURATION_FRAMES) * 2.0 * math.pi
            x = b["cx"] + math.sin(angle) * b["rx"]
            y = b["cy"] + math.cos(angle) * b["ry"]
            z = b["bz"] + math.sin(angle) * 30.0
            pos_keys.append({"frame": f, "value": [x, y, z]})
        layers.append({
            "id": f"aura_{idx}",
            "type": "light",
            "enable_3d": True,
            "light": {"radius": b["radius"], "color": b["color"], "intensity": b["intensity"]},
            "position": [b["cx"], b["cy"], b["bz"]],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [{"property": "position", "easing": "linear", "keyframes": pos_keys}]
            }
        })
    layers.extend(title_card_layers("Volumetric 3D Fluid Aura", "Chronon Procedural Background • Test 04"))
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_04_3d_fluid_aura",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_04_3d_fluid_aura.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. 3D Ambient Bokeh Orbs
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_05_ambient_bokeh():
    layers = [
        {
            "id": "bokeh_base",
            "type": "color",
            "color": [0.018, 0.022, 0.038, 1.0],
            "size": [WIDTH, HEIGHT],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES
        }
    ]
    bokeh_specs = [
        {"color": "#F59E0B", "rad": 260.0, "int": 0.55, "x": 650.0, "y": 420.0, "z": -200.0, "dx": 60.0, "dy": -40.0},
        {"color": "#3B82F6", "rad": 310.0, "int": 0.50, "x": 1280.0, "y": 620.0, "z": -140.0, "dx": -50.0, "dy": 50.0},
        {"color": "#10B981", "rad": 240.0, "int": 0.45, "x": 920.0, "y": 680.0, "z": -80.0, "dx": 40.0, "dy": -30.0},
        {"color": "#8B5CF6", "rad": 280.0, "int": 0.48, "x": 1050.0, "y": 360.0, "z": -110.0, "dx": -40.0, "dy": 40.0}
    ]
    for i, s in enumerate(bokeh_specs):
        pos_keys = []
        for f in range(0, DURATION_FRAMES + 1, 3):
            prog = f / DURATION_FRAMES
            x = s["x"] + math.sin(prog * math.pi * 2) * s["dx"]
            y = s["y"] + math.cos(prog * math.pi * 2) * s["dy"]
            pos_keys.append({"frame": f, "value": [x, y, s["z"]]})
        layers.append({
            "id": f"bokeh_{i}",
            "type": "light",
            "enable_3d": True,
            "light": {"radius": s["rad"], "color": s["color"], "intensity": s["int"]},
            "position": [s["x"], s["y"], s["z"]],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [{"property": "position", "easing": "linear", "keyframes": pos_keys}]
            }
        })
    layers.extend(title_card_layers("Ambient Glowing Bokeh Orbs", "Chronon Procedural Background • Test 05"))
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_05_3d_ambient_bokeh",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_05_3d_ambient_bokeh.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }

# ─────────────────────────────────────────────────────────────────────────────
# 6. 3D Cyber Horizon Floor Travel
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_06_horizon_grid():
    grid_travel_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        prog = f / DURATION_FRAMES
        z_pos = -150.0 + prog * 300.0
        grid_travel_keys.append({"frame": f, "value": [960.0, 780.0, z_pos]})
    layers = [
        {
            "id": "deep_space_bg",
            "type": "color",
            "color": [0.015, 0.02, 0.035, 1.0],
            "size": [WIDTH, HEIGHT],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES
        },
        {
            "id": "ground_grid",
            "type": "image",
            "asset": "assets/images/grid_tile.png",
            "size": [3200, 2400],
            "position": [960.0, 780.0, -150.0],
            "rotation": [83.0, 0.0, 0.0],
            "opacity": 0.85,
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {"property": "position", "easing": "linear", "keyframes": grid_travel_keys}
                ]
            }
        },
        {
            "id": "horizon_glow",
            "type": "light",
            "enable_3d": True,
            "light": {"radius": 600.0, "color": "#06B6D4", "intensity": 0.8},
            "position": [960.0, 750.0, -180.0],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES
        }
    ]
    layers.extend(title_card_layers("3D Cyber Horizon Floor Travel", "Chronon Procedural Background • Test 06"))
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_06_3d_cyber_horizon",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "camera": {
            "type": "perspective",
            "fov_deg": 52.0,
            "position": [960.0, 540.0, -1100.0],
            "rotation_deg": [0.0, 0.0, 0.0]
        },
        "output": {"path": str(OUT_DIR / "bg_06_3d_cyber_horizon.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }

# ─────────────────────────────────────────────────────────────────────────────
# 7. Modern Phone Device Mockup (Centered + Smooth Float & Ambient Pulse)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_07_phone_mockup():
    pos_keys = []
    rot_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        y_off = loop_cos(-20.0, 20.0, f)
        tilt = loop_cos(-2.5, 2.5, f)
        pos_keys.append({"frame": f, "value": y_off})
        rot_keys.append({"frame": f, "value": tilt})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_07_device_mockup_phone",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_07_device_mockup_phone.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "studio_bg",
                "type": "color",
                "color": [0.025, 0.035, 0.055, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "phone_backdrop_halo",
                "type": "shape",
                "size": [650, 650],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.15, 0.55, 0.95, 0.25]
                },
                "effects": [
                    {"type": "bloom"}
                ]
            },
            {
                "id": "phone_frame",
                "type": "shape",
                "size": [440, 840],
                "position": [1180, 960],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "device_frame",
                    "device": "phone",
                    "chrome": True,
                    "fill": [0.08, 0.12, 0.20, 0.95]
                },
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": pos_keys},
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys}
                    ]
                }
            }
        ] + title_card_layers("Modern Phone Device Mockup", "Chronon Procedural Background • Test 07")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 8. Modern Browser Device Mockup (Centered + Smooth Float & Glow)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_08_device_mockup():
    pos_keys = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        y_off = loop_cos(-15.0, 15.0, f)
        s = loop_cos(1.0, 1.025, f)
        pos_keys.append({"frame": f, "value": y_off})
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_08_device_mockup_browser",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_08_device_mockup_browser.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "studio_bg",
                "type": "color",
                "color": [0.03, 0.04, 0.065, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "browser_halo",
                "type": "shape",
                "size": [1300, 760],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rounded_rect",
                    "radius": 40.0,
                    "fill": [0.10, 0.45, 0.90, 0.18]
                },
                "effects": [
                    {"type": "bloom"}
                ]
            },
            {
                "id": "browser_frame",
                "type": "shape",
                "size": [1200, 680],
                "position": [1560, 880],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "device_frame",
                    "device": "browser",
                    "chrome": True,
                    "fill": [0.08, 0.12, 0.18, 0.95]
                },
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": pos_keys},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            }
        ] + title_card_layers("Modern Browser Device Mockup", "Chronon Procedural Background • Test 08")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 9. Glassmorphism Card & Geometric Accents (Centered Card + Spinning Accents)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_09_glass_card():
    pos_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        y_off = loop_cos(-12.0, 12.0, f)
        pos_keys.append({"frame": f, "value": y_off})

    star_rot_keys = []
    arc_rot_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        deg = (f / DURATION_FRAMES) * 360.0
        star_rot_keys.append({"frame": f, "value": deg})
        arc_rot_keys.append({"frame": f, "value": -deg})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_09_glass_card_geometric_accents",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_09_glass_card_geometric_accents.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.02, 0.025, 0.04, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "glass_card",
                "type": "shape",
                "size": [1100, 580],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "rounded_rect",
                    "radius": 28.0,
                    "fill": [0.08, 0.12, 0.22, 0.75],
                    "stroke": {
                        "width": 2.5,
                        "color": [0.25, 0.65, 1.0, 0.85]
                    }
                },
                "animation": {
                    "tracks": [
                        {"property": "position_y", "easing": "linear", "keyframes": pos_keys}
                    ]
                }
            },
            {
                "id": "accent_star",
                "type": "shape",
                "size": [100, 100],
                "position": [610, 390],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "star",
                    "points": 5,
                    "inner_radius_ratio": 0.45,
                    "fill": [1.0, 0.82, 0.2, 0.95]
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": star_rot_keys}
                    ]
                }
            },
            {
                "id": "accent_arc",
                "type": "shape",
                "size": [160, 160],
                "position": [1310, 690],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arc",
                    "start_degrees": 20.0,
                    "sweep_degrees": 280.0,
                    "stroke": {
                        "width": 5.0,
                        "color": [0.2, 0.9, 0.8, 0.9]
                    }
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": arc_rot_keys}
                    ]
                }
            }
        ] + title_card_layers("Glassmorphism Card & Geometric Accents", "Chronon Procedural Background • Test 09")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 10. Procedural Vector Direction Arrow (Centered + Forward Thrust Flow)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_10_vector_arrow():
    pos_keys = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        x_off = loop_cos(-40.0, 40.0, f)
        s = loop_cos(0.98, 1.06, f)
        pos_keys.append({"frame": f, "value": x_off})
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_10_procedural_vector_arrow",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_10_procedural_vector_arrow.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "arrow_bg",
                "type": "color",
                "color": [0.02, 0.025, 0.038, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "arrow_halo",
                "type": "shape",
                "size": [700, 700],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.15, 0.65, 0.95, 0.22]
                },
                "effects": [
                    {"type": "bloom"}
                ]
            },
            {
                "id": "arrow_shape",
                "type": "shape",
                "size": [580, 290],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "arrow",
                    "shaft_ratio": 0.32,
                    "head_ratio": 0.85,
                    "fill": [0.15, 0.75, 0.95, 0.90]
                },
                "effects": [
                    {"type": "bloom"}
                ],
                "animation": {
                    "tracks": [
                        {"property": "position_x", "easing": "linear", "keyframes": pos_keys},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            }
        ] + title_card_layers("Procedural Vector Direction Arrow", "Chronon Procedural Background • Test 10")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 11. Volumetric Radiant Light Rays (Sweeping Angular Beams)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_11_light_rays():
    rot_keys = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        r = loop_cos(-25.0, 25.0, f)
        s = loop_cos(1.0, 1.25, f)
        rot_keys.append({"frame": f, "value": r})
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_11_volumetric_light_rays",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_11_volumetric_light_rays.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_stage",
                "type": "color",
                "color": [0.015, 0.02, 0.035, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "source_light",
                "type": "shape",
                "size": [440, 440],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "ellipse",
                    "fill": [0.35, 0.75, 1.0, 0.90]
                },
                "effects": [
                    {"type": "light_rays"},
                    {"type": "bloom"}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_keys},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            }
        ] + title_card_layers("Volumetric Radiant Light Rays", "Chronon Procedural Background • Test 11")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# 12. Procedural Polygon Prism (Centered Spinning Geometric Prism)
# ─────────────────────────────────────────────────────────────────────────────
def build_plan_12_polygon_prism():
    rot_cw = []
    rot_ccw = []
    scale_keys = []
    for f in range(0, DURATION_FRAMES + 1, 3):
        deg = (f / DURATION_FRAMES) * 360.0
        s = loop_cos(0.92, 1.08, f)
        rot_cw.append({"frame": f, "value": deg})
        rot_ccw.append({"frame": f, "value": -deg})
        scale_keys.append({"frame": f, "value": s})

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bg_12_procedural_polygon_prism",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": DURATION_FRAMES},
        "output": {"path": str(OUT_DIR / "bg_12_procedural_polygon_prism.mp4"), "format": "mp4", "codec": "h264"},
        "layers": [
            {
                "id": "dark_bg",
                "type": "color",
                "color": [0.018, 0.022, 0.035, 1.0],
                "size": [WIDTH, HEIGHT],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES
            },
            {
                "id": "polygon_outer",
                "type": "shape",
                "size": [520, 520],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "polygon",
                    "points": 8,
                    "fill": [0.10, 0.25, 0.45, 0.70],
                    "stroke": {
                        "width": 3.5,
                        "color": [0.35, 0.80, 1.0, 0.95]
                    }
                },
                "effects": [
                    {"type": "bloom"}
                ],
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_cw},
                        {"property": "scale", "easing": "linear", "keyframes": scale_keys}
                    ]
                }
            },
            {
                "id": "polygon_inner_star",
                "type": "shape",
                "size": [240, 240],
                "position": [960, 540],
                "start_frame": 0,
                "duration_frames": DURATION_FRAMES,
                "shape": {
                    "type": "star",
                    "points": 8,
                    "inner_radius_ratio": 0.55,
                    "fill": [0.20, 0.65, 0.95, 0.85],
                    "stroke": {
                        "width": 2.0,
                        "color": [0.90, 0.95, 1.0, 0.90]
                    }
                },
                "animation": {
                    "tracks": [
                        {"property": "rotation_z", "easing": "linear", "keyframes": rot_ccw}
                    ]
                }
            }
        ] + title_card_layers("Procedural Octagon Geometric Prism", "Chronon Procedural Background • Test 12")
    }
    return plan

# ─────────────────────────────────────────────────────────────────────────────
# DRIVE UPLOAD HELPERS
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
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
SUITE = [
    ("bg_01_crime_doc_grain_vignette", build_plan_01_crime_doc),
    ("bg_02_tech_dot_grid", build_plan_02_dot_grid),
    ("bg_03_blueprint_line_grid", build_plan_03_line_grid),
    ("bg_04_3d_fluid_aura", build_plan_04_fluid_aura),
    ("bg_05_3d_ambient_bokeh", build_plan_05_ambient_bokeh),
    ("bg_06_3d_cyber_horizon", build_plan_06_horizon_grid),
    ("bg_07_device_mockup_phone", build_plan_07_phone_mockup),
    ("bg_08_device_mockup_browser", build_plan_08_device_mockup),
    ("bg_09_glass_card_geometric_accents", build_plan_09_glass_card),
    ("bg_10_procedural_vector_arrow", build_plan_10_vector_arrow),
    ("bg_11_volumetric_light_rays", build_plan_11_light_rays),
    ("bg_12_procedural_polygon_prism", build_plan_12_polygon_prism),
]

def main():
    print(f"=== Starting Chronon Background Showcase Suite V2 (Certified) ({len(SUITE)} items) ===", flush=True)
    
    # 1. Write all plan files
    plan_files = []
    for item_id, builder in SUITE:
        plan_data = builder()
        plan_path = OUT_DIR / f"{item_id}.plan.json"
        plan_path.write_text(json.dumps(plan_data, indent=2))
        plan_files.append((item_id, plan_path))
        print(f"  [Plan] Wrote {plan_path.name}")
        
    # 2. Render each plan to MP4
    rendered_videos = []
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
            rendered_videos.append(out_mp4)
            # Generate still PNG poster at 1.0s
            out_png = OUT_DIR / f"{item_id}.png"
            subprocess.run(["ffmpeg", "-y", "-ss", "00:00:01", "-i", str(out_mp4), "-vframes", "1", str(out_png)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_png.exists():
                rendered_videos.append(out_png)

    # 3. Upload to Google Drive
    print(f"\n=== Uploading {len(rendered_videos)} media files to Google Drive ({DRIVE_FOLDER_ID}) ===", flush=True)
    token = get_drive_access_token()
    uploads = []
    for fpath in rendered_videos:
        print(f"Uploading {fpath.name} ({fpath.stat().st_size:,} bytes)...", flush=True)
        meta = upload_to_drive(token, fpath, DRIVE_FOLDER_ID)
        uploads.append(meta)
        print(f"  ✓ Uploaded! ID: {meta.get('id')}")

    print("\n=== SUMMARY OF COMPLETED UPLOADS ===")
    for u in uploads:
        print(f"- {u.get('name')}: {u.get('id')} ({u.get('webViewLink')})")

if __name__ == "__main__":
    main()
