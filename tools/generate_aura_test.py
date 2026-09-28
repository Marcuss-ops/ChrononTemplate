#!/usr/bin/env python3
import json
import math
from pathlib import Path

OUT_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/out/env_showcase")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FPS = 30
DURATION_FRAMES = 120
WIDTH = 1920
HEIGHT = 1080

def build_aura_autofocus_plan():
    layers = []
    
    # Base dark background
    layers.append({
        "id": "bg_dark",
        "type": "color",
        "color": [0.02, 0.025, 0.04, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    })
    
    # 3 Aura Blobs using auraBlobMotion (Lissajous curves)
    blobs = [
        {"color": "#7C3AED", "radius": 480.0, "intensity": 2.8, "center": [800.0, 420.0, -150.0], "rad": [380.0, 180.0], "freq": 0.8, "seed": 10},
        {"color": "#06B6D4", "radius": 440.0, "intensity": 2.4, "center": [1120.0, 620.0, -120.0], "rad": [320.0, 160.0], "freq": 1.1, "seed": 75},
        {"color": "#EC4899", "radius": 360.0, "intensity": 2.0, "center": [960.0, 500.0, -80.0], "rad": [240.0, 200.0], "freq": 1.4, "seed": 140}
    ]
    
    for idx, b in enumerate(blobs):
        pos_keys = []
        phase = (b["seed"] % 360) * math.pi / 180.0
        for f in range(0, DURATION_FRAMES + 1, 8):
            prog = f / DURATION_FRAMES
            angle = prog * 2.0 * math.pi * b["freq"] + phase
            x = b["center"][0] + math.sin(angle) * b["rad"][0]
            y = b["center"][1] + math.sin(angle * 1.5 + 0.5) * b["rad"][1]
            z = b["center"][2] + math.cos(angle * 0.7) * (min(b["rad"][0], b["rad"][1]) * 0.25)
            pos_keys.append({
                "frame": f,
                "value": [x, y, z]
            })
            
        layers.append({
            "id": f"aura_blob_{idx}",
            "type": "light",
            "enable_3d": True,
            "light": {
                "radius": b["radius"],
                "color": b["color"],
                "intensity": b["intensity"]
            },
            "position": b["center"],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position",
                        "easing": "in_out_cubic",
                        "keyframes": pos_keys
                    }
                ]
            }
        })
        
    # Hero Title with 3D camera travel
    layers.append({
        "id": "hero_title",
        "type": "text",
        "text": "FLUID AURA & MESH GLOW",
        "size": [1600, 140],
        "position": [960, 480, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Poppins-Bold.ttf",
            "font_size": 86.0,
            "fill": "#FFFFFF",
            "stroke": {
                "color": "#0F172A",
                "width": 3.0
            },
            "glow": {
                "radius": 28.0,
                "intensity": 0.6,
                "color": "#A855F7"
            }
        },
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 24, "value": 1.0},
                        {"frame": 100, "value": 1.0},
                        {"frame": 119, "value": 0.0}
                    ]
                },
                {
                    "property": "position_z",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -140.0},
                        {"frame": 28, "value": 0.0},
                        {"frame": 119, "value": 40.0}
                    ]
                }
            ]
        }
    })
    
    # Subtitle
    layers.append({
        "id": "subtitle",
        "type": "text",
        "text": "ORGANIC LISSAJOUS BACKGROUND GLOW & CAMERA AUTOFOCUS",
        "size": [1600, 80],
        "position": [960, 580, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 32.0,
            "fill": "#CBD5E1"
        },
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 15, "value": 0.0},
                        {"frame": 35, "value": 0.95},
                        {"frame": 100, "value": 0.95},
                        {"frame": 119, "value": 0.0}
                    ]
                },
                {
                    "property": "position_y",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 15, "value": 605.0},
                        {"frame": 35, "value": 580.0}
                    ]
                }
            ]
        }
    })
    
    # Camera push & subtle tilt
    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": "chrononmotion_fluid_aura",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "camera": {
            "type": "perspective",
            "fov_deg": 52.0,
            "near": 1.0,
            "far": 5000.0,
            "position": [960.0, 540.0, -1150.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "zoom": 1.0
        },
        "camera_animation": {
            "tracks": [
                {
                    "property": "camera_position_z",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -1150.0},
                        {"frame": 119, "value": -920.0}
                    ]
                },
                {
                    "property": "camera_rotation_z",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -1.2},
                        {"frame": 60, "value": 1.0},
                        {"frame": 119, "value": 0.0}
                    ]
                }
            ]
        },
        "layers": layers,
        "output": {
            "path": str(OUT_DIR / "chrononmotion_fluid_aura.mp4"),
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    plan_path = OUT_DIR / "chrononmotion_fluid_aura.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Created {plan_path}")
    return plan_path

build_aura_autofocus_plan()
