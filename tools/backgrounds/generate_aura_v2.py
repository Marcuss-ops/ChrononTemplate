#!/usr/bin/env python3
import json
import math
from pathlib import Path

OUT_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/out/env_showcase")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FPS = 60
DURATION_FRAMES = 180  # 3.0 seconds at 60fps
WIDTH = 1920
HEIGHT = 1080

def build_aura_v2():
    layers = []
    
    # 1. Base dark background
    layers.append({
        "id": "bg_dark",
        "type": "color",
        "color": [0.03, 0.035, 0.055, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    })
    
    # 2. 3 Aura Blobs with strictly separated Z depths (ZERO Z-crossing glitches!)
    # and linear continuous sampling (ZERO easing stops/scatti!)
    blobs = [
        # Deep background aura (Z = -280)
        {"color": "#7C3AED", "radius": 420.0, "intensity": 0.85, "center_x": 750.0, "center_y": 500.0, "base_z": -280.0, "rad_x": 220.0, "rad_y": 120.0, "freq": 0.75, "phase": 0.0},
        # Midground glow (Z = -160)
        {"color": "#06B6D4", "radius": 380.0, "intensity": 0.75, "center_x": 1170.0, "center_y": 580.0, "base_z": -160.0, "rad_x": 200.0, "rad_y": 140.0, "freq": 1.0, "phase": 2.1},
        # Foreground ambient accent (Z = -60)
        {"color": "#EC4899", "radius": 320.0, "intensity": 0.65, "center_x": 960.0, "center_y": 460.0, "base_z": -60.0, "rad_x": 160.0, "rad_y": 100.0, "freq": 1.25, "phase": 4.2}
    ]
    
    for idx, b in enumerate(blobs):
        pos_keys = []
        opac_keys = []
        # Sample smoothly at 60 fps every 2 frames with linear interpolation
        for f in range(0, DURATION_FRAMES + 1, 2):
            t = f / FPS
            angle = t * 2.0 * math.pi * b["freq"] + b["phase"]
            x = b["center_x"] + math.sin(angle) * b["rad_x"]
            y = b["center_y"] + math.cos(angle * 1.3) * b["rad_y"]
            z = b["base_z"] + math.sin(angle * 0.8) * 20.0  # Safe oscillation within +/-20, depths never cross!
            
            # Smooth fade in and out
            prog = f / DURATION_FRAMES
            if prog < 0.15:
                alpha = prog / 0.15
            elif prog > 0.85:
                alpha = (1.0 - prog) / 0.15
            else:
                alpha = 1.0
                
            pos_keys.append({"frame": f, "value": [x, y, z]})
            opac_keys.append({"frame": f, "value": alpha})
            
        layers.append({
            "id": f"aura_blob_{idx}",
            "type": "light",
            "enable_3d": True,
            "light": {
                "radius": b["radius"],
                "color": b["color"],
                "intensity": b["intensity"]
            },
            "position": [b["center_x"], b["center_y"], b["base_z"]],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position",
                        "easing": "linear",  # Continuous smooth derivative!
                        "keyframes": pos_keys
                    },
                    {
                        "property": "opacity",
                        "easing": "linear",
                        "keyframes": opac_keys
                    }
                ]
            }
        })
        
    # 3. Hero Title: Exactly Centered in 3D
    # size: 1400x120 -> position: (1920-1400)/2 = 260, (1080-120)/2 - 40 = 440
    title_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        prog = f / DURATION_FRAMES
        # Smooth camera-coupled parallax push
        z = -100.0 * (1.0 - min(1.0, prog / 0.25))**2 + prog * 40.0
        title_keys.append({"frame": f, "value": [260.0, 440.0, z]})
        
    title_opac = [
        {"frame": 0, "value": 0.0},
        {"frame": 25, "value": 1.0},
        {"frame": 155, "value": 1.0},
        {"frame": 179, "value": 0.0}
    ]
    
    layers.append({
        "id": "hero_title",
        "type": "text",
        "text": "FLUID AURA & MESH GLOW",
        "size": [1400, 120],
        "position": [260, 440, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Poppins-Bold.ttf",
            "font_size": 76.0,
            "fill": "#FFFFFF",
            "stroke": {
                "color": "#090D16",
                "width": 2.0
            }
        },
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {
            "tracks": [
                {
                    "property": "position",
                    "easing": "linear",
                    "keyframes": title_keys
                },
                {
                    "property": "opacity",
                    "easing": "linear",
                    "keyframes": title_opac
                }
            ]
        }
    })
    
    # 4. Subtitle: Exactly Centered
    # size: 1400x60 -> position: (1920-1400)/2 = 260, 545
    sub_opac = [
        {"frame": 0, "value": 0.0},
        {"frame": 20, "value": 0.0},
        {"frame": 40, "value": 0.9},
        {"frame": 155, "value": 0.9},
        {"frame": 179, "value": 0.0}
    ]
    layers.append({
        "id": "subtitle",
        "type": "text",
        "text": "SMOOTH 60 FPS CONTINUOUS LISSAJOUS FIELD • CHRONONMOTION 3D",
        "size": [1400, 60],
        "position": [260, 545, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 26.0,
            "fill": "#38BDF8"
        },
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "linear",
                    "keyframes": sub_opac
                }
            ]
        }
    })
    
    # Camera Rig: Smooth continuous dolly push in 60fps
    cam_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        prog = f / DURATION_FRAMES
        # Smooth ease in and ease out using smoothstep 3*p^2 - 2*p^3
        smooth_p = prog * prog * (3.0 - 2.0 * prog)
        cam_z = -1200.0 + smooth_p * 250.0  # -1200 to -950
        cam_keys.append({"frame": f, "value": cam_z})
        
    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": "chrononmotion_fluid_aura_v2",
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
            "position": [960.0, 540.0, -1200.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "zoom": 1.0
        },
        "camera_animation": {
            "tracks": [
                {
                    "property": "camera_position_z",
                    "easing": "linear",
                    "keyframes": cam_keys
                }
            ]
        },
        "layers": layers,
        "output": {
            "path": str(OUT_DIR / "chrononmotion_fluid_aura_60fps_smooth.mp4"),
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    plan_path = OUT_DIR / "chrononmotion_fluid_aura_v2.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Created {plan_path}")

if __name__ == "__main__":
    build_aura_v2()
