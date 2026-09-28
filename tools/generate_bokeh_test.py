#!/usr/bin/env python3
import json
import math
import subprocess
from pathlib import Path

OUT_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/out/env_showcase")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Build Ambient Bokeh Scene
FPS = 30
DURATION_FRAMES = 120
WIDTH = 1920
HEIGHT = 1080

def build_ambient_bokeh_plan():
    layers = []
    
    # Base background
    layers.append({
        "id": "bg_dark",
        "type": "color",
        "color": [0.035, 0.045, 0.07, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    })
    
    # Particles / Bokeh Orbs using ambientDriftField formula
    # seed=42, multi-harmonic 3D drift
    palette_hex = [
        ("#38BDF8", 1.8),  # Sky cyan
        ("#A855F7", 1.6),  # Purple
        ("#EC4899", 1.5),  # Pink
        ("#3B82F6", 1.6),  # Blue
        ("#F59E0B", 1.4)   # Amber
    ]
    
    num_particles = 12
    for i in range(num_particles):
        hex_col, base_intensity = palette_hex[i % len(palette_hex)]
        base_x = 960.0 + (math.sin(i * 1.7) * 700.0)
        base_y = 540.0 + (math.cos(i * 2.3) * 380.0)
        base_z = -450.0 + (i * 65.0)  # Z from -450 to +300
        radius = 180.0 + (i % 4) * 60.0
        
        # ambientDriftField math from ChrononMotion3D
        seed = 42
        phase_x = ((seed ^ (i * 7919)) % 360) * math.pi / 180.0
        phase_y = ((seed ^ (i * 6271 + 13)) % 360) * math.pi / 180.0
        phase_z = ((seed ^ (i * 3571 + 29)) % 360) * math.pi / 180.0
        freq_x = 1.0 + 0.3 * ((i % 5) - 2)
        freq_y = 1.2 + 0.25 * ((i % 4) - 1)
        freq_z = 0.8 + 0.2 * ((i % 3) - 1)
        max_rad = 45.0
        
        pos_keyframes = []
        opac_keyframes = []
        for f in range(0, DURATION_FRAMES + 1, 10):
            prog = f / DURATION_FRAMES
            angle = prog * 2.0 * math.pi
            dx = math.sin(angle * freq_x + phase_x) * max_rad
            dy = math.cos(angle * freq_y + phase_y) * max_rad
            dz = math.sin(angle * freq_z + phase_z) * (max_rad * 0.5)
            
            # Breathing pulse
            pulse = 0.7 + 0.3 * math.sin(angle * 1.5 + phase_x)
            
            pos_keyframes.append({
                "frame": f,
                "value": [base_x + dx, base_y + dy, base_z + dz]
            })
            opac_keyframes.append({
                "frame": f,
                "value": pulse
            })
            
        layers.append({
            "id": f"bokeh_light_{i}",
            "type": "light",
            "enable_3d": True,
            "light": {
                "radius": radius,
                "color": hex_col,
                "intensity": base_intensity
            },
            "position": [base_x, base_y, base_z],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position",
                        "easing": "in_out_cubic",
                        "keyframes": pos_keyframes
                    },
                    {
                        "property": "opacity",
                        "easing": "linear",
                        "keyframes": opac_keyframes
                    }
                ]
            }
        })
        
    # Text Layer: Main Title
    layers.append({
        "id": "hero_title",
        "type": "text",
        "text": "CHRONONMOTION 3D",
        "size": [1600, 140],
        "position": [960, 480, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Poppins-Bold.ttf",
            "font_size": 92.0,
            "fill": "#FFFFFF",
            "stroke": {
                "color": "#0B0F19",
                "width": 3.0
            },
            "glow": {
                "radius": 24.0,
                "intensity": 0.5,
                "color": "#38BDF8"
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
                        {"frame": 0, "value": -180.0},
                        {"frame": 30, "value": 0.0},
                        {"frame": 119, "value": 60.0}
                    ]
                }
            ]
        }
    })
    
    # Text Layer: Subtitle
    layers.append({
        "id": "subtitle",
        "type": "text",
        "text": "AMBIENT 3D DRIFT FIELD & VOLUMETRIC DEPTH",
        "size": [1600, 80],
        "position": [960, 590, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 34.0,
            "fill": "#94A3B8"
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
                        {"frame": 35, "value": 0.9},
                        {"frame": 100, "value": 0.9},
                        {"frame": 119, "value": 0.0}
                    ]
                },
                {
                    "property": "position_y",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 15, "value": 615.0},
                        {"frame": 35, "value": 590.0}
                    ]
                }
            ]
        }
    })
    
    # Camera push & subtle pan
    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": "chrononmotion_ambient_bokeh",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "camera": {
            "type": "perspective",
            "fov_deg": 55.0,
            "near": 1.0,
            "far": 5000.0,
            "position": [960.0, 540.0, -1200.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "zoom": 1.0
        },
        "camera_animation": {
            "tracks": [
                {
                    "property": "camera_position_z",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -1200.0},
                        {"frame": 119, "value": -950.0}
                    ]
                },
                {
                    "property": "camera_position_x",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 940.0},
                        {"frame": 60, "value": 980.0},
                        {"frame": 119, "value": 960.0}
                    ]
                }
            ]
        },
        "layers": layers,
        "output": {
            "path": str(OUT_DIR / "chrononmotion_ambient_bokeh.mp4"),
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    plan_path = OUT_DIR / "chrononmotion_ambient_bokeh.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Created {plan_path}")
    return plan_path

build_ambient_bokeh_plan()
