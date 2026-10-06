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

def build_horizon_ground_plan():
    layers = []
    
    # 1. Base dark background (setupBackgroundPlane & frustumCoverage concept)
    layers.append({
        "id": "deep_space_bg",
        "type": "color",
        "color": [0.015, 0.02, 0.035, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    })
    
    # 2. Horizon ground grid plane
    # Demonstrating Presets_Environment::horizonGrid(layer, floorY=780, depthZ=-200, tilt=83 deg)
    # and Presets_Environment::groundTravel(layer, distanceZ=600)
    grid_travel_keys = []
    for f in range(0, DURATION_FRAMES + 1, 10):
        prog = f / DURATION_FRAMES
        # Moving along Z
        z_pos = -150.0 + prog * 450.0
        grid_travel_keys.append({
            "frame": f,
            "value": [960.0, 780.0, z_pos]
        })
        
    layers.append({
        "id": "ground_grid",
        "type": "image",
        "asset": "assets/images/grid_tile.png",
        "size": [3200, 2400],
        "position": [960.0, 780.0, -150.0],
        "rotation": [83.0, 0.0, 0.0],  # 83 deg tilt towards horizon
        "opacity": 0.75,
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "animation": {
            "tracks": [
                {
                    "property": "position",
                    "easing": "linear",
                    "keyframes": grid_travel_keys
                },
                {
                    "property": "opacity",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 0.0},
                        {"frame": 20, "value": 0.8},
                        {"frame": 100, "value": 0.8},
                        {"frame": 119, "value": 0.0}
                    ]
                }
            ]
        }
    })
    
    # 3. Floating 3D horizon markers/pillars (ambientDriftField)
    num_markers = 8
    marker_colors = [
        [0.2, 0.75, 1.0, 0.85],   # Cyan
        [0.65, 0.35, 1.0, 0.85],  # Purple
        [0.95, 0.3, 0.7, 0.85],   # Pink
        [0.2, 0.85, 0.6, 0.85]    # Emerald
    ]
    
    for i in range(num_markers):
        x = 360.0 + i * 180.0 + (i % 2) * 50.0
        base_y = 660.0 + (i % 3) * 20.0
        base_z = -200.0 + (i % 4) * 80.0
        col = marker_colors[i % len(marker_colors)]
        
        pos_keys = []
        seed = 101
        phase_x = ((seed ^ (i * 7919)) % 360) * math.pi / 180.0
        phase_y = ((seed ^ (i * 6271 + 13)) % 360) * math.pi / 180.0
        phase_z = ((seed ^ (i * 3571 + 29)) % 360) * math.pi / 180.0
        
        for f in range(0, DURATION_FRAMES + 1, 10):
            prog = f / DURATION_FRAMES
            angle = prog * 2.0 * math.pi
            dx = math.sin(angle * 1.1 + phase_x) * 25.0
            dy = math.cos(angle * 1.3 + phase_y) * 25.0
            dz = math.sin(angle * 0.9 + phase_z) * 40.0 + (prog * 300.0) # moving forward
            pos_keys.append({
                "frame": f,
                "value": [x + dx, base_y + dy, base_z + dz]
            })
            
        layers.append({
            "id": f"horizon_marker_{i}",
            "type": "color",
            "color": col,
            "size": [8, 120 + (i % 3) * 40],
            "position": [x, base_y, base_z],
            "enable_3d": True,
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "animation": {
                "tracks": [
                    {
                        "property": "position",
                        "easing": "linear",
                        "keyframes": pos_keys
                    },
                    {
                        "property": "opacity",
                        "easing": "in_out_cubic",
                        "keyframes": [
                            {"frame": 0, "value": 0.0},
                            {"frame": 15, "value": 0.9},
                            {"frame": 105, "value": 0.9},
                            {"frame": 119, "value": 0.0}
                        ]
                    }
                ]
            }
        })
        
    # 4. Hero Title
    layers.append({
        "id": "hero_title",
        "type": "text",
        "text": "HORIZON GRID & TRAVEL",
        "size": [1600, 140],
        "position": [960, 440, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Poppins-Bold.ttf",
            "font_size": 88.0,
            "fill": "#FFFFFF",
            "stroke": {
                "color": "#090D16",
                "width": 3.0
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
                        {"frame": 22, "value": 1.0},
                        {"frame": 100, "value": 1.0},
                        {"frame": 119, "value": 0.0}
                    ]
                },
                {
                    "property": "position_z",
                    "easing": "out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -160.0},
                        {"frame": 28, "value": 0.0},
                        {"frame": 119, "value": 50.0}
                    ]
                }
            ]
        }
    })
    
    # 5. Subtitle
    layers.append({
        "id": "subtitle",
        "type": "text",
        "text": "3D PERSPECTIVE GROUND PLANE WITH SEAMLESS FRUSTUM EXTENTS",
        "size": [1600, 80],
        "position": [960, 535, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 30.0,
            "fill": "#38BDF8"
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
                        {"frame": 18, "value": 0.0},
                        {"frame": 35, "value": 0.95},
                        {"frame": 100, "value": 0.95},
                        {"frame": 119, "value": 0.0}
                    ]
                }
            ]
        }
    })
    
    # Camera Rig
    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": "chrononmotion_horizon_ground",
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
            "far": 6000.0,
            "position": [960.0, 540.0, -1100.0],
            "rotation_deg": [0.0, 0.0, 0.0],
            "zoom": 1.0
        },
        "camera_animation": {
            "tracks": [
                {
                    "property": "camera_position_z",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": -1100.0},
                        {"frame": 119, "value": -880.0}
                    ]
                },
                {
                    "property": "camera_position_y",
                    "easing": "in_out_cubic",
                    "keyframes": [
                        {"frame": 0, "value": 520.0},
                        {"frame": 60, "value": 550.0},
                        {"frame": 119, "value": 530.0}
                    ]
                }
            ]
        },
        "layers": layers,
        "output": {
            "path": str(OUT_DIR / "chrononmotion_horizon_ground.mp4"),
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    plan_path = OUT_DIR / "chrononmotion_horizon_ground.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Created {plan_path}")
    return plan_path

if __name__ == "__main__":
    build_horizon_ground_plan()
