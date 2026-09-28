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

def build_bokeh_v2():
    layers = []
    
    # 1. Base dark background
    layers.append({
        "id": "bg_dark",
        "type": "color",
        "color": [0.025, 0.03, 0.05, 1.0],
        "size": [WIDTH, HEIGHT],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES
    })
    
    # 2. Bokeh Orbs using ambientDriftField with stratified depth tiers
    palette = [
        ("#38BDF8", 0.75),  # Cyan
        ("#A855F7", 0.70),  # Purple
        ("#EC4899", 0.65),  # Pink
        ("#3B82F6", 0.70),  # Royal Blue
        ("#06B6D4", 0.75)   # Turquoise
    ]
    
    # 8 stratified bokeh orbs spanning depths from -450 to -80
    num_particles = 8
    for i in range(num_particles):
        hex_col, base_intensity = palette[i % len(palette)]
        # Distribute horizontally across screen
        base_x = 400.0 + (i * 160.0) + math.sin(i * 1.5) * 80.0
        base_y = 350.0 + math.cos(i * 2.1) * 200.0
        base_z = -420.0 + (i * 45.0)  # Stratified Z depths (never cross!)
        radius = 160.0 + (i % 3) * 40.0
        
        seed = 42
        phase_x = ((seed ^ (i * 7919)) % 360) * math.pi / 180.0
        phase_y = ((seed ^ (i * 6271 + 13)) % 360) * math.pi / 180.0
        phase_z = ((seed ^ (i * 3571 + 29)) % 360) * math.pi / 180.0
        freq_x = 0.8 + 0.15 * ((i % 4) - 1.5)
        freq_y = 0.9 + 0.15 * ((i % 3) - 1.0)
        max_rad = 35.0
        
        pos_keys = []
        opac_keys = []
        for f in range(0, DURATION_FRAMES + 1, 2):
            t = f / FPS
            angle = t * 2.0 * math.pi
            dx = math.sin(angle * freq_x + phase_x) * max_rad
            dy = math.cos(angle * freq_y + phase_y) * max_rad
            dz = math.sin(angle * 0.7 + phase_z) * 12.0  # safe small drift, never crosses neighbor (45px apart)
            
            # Breathing pulse
            pulse = 0.7 + 0.3 * math.sin(angle * 1.2 + phase_x)
            
            # Global scene fade in / out
            prog = f / DURATION_FRAMES
            if prog < 0.12:
                fade = prog / 0.12
            elif prog > 0.88:
                fade = (1.0 - prog) / 0.12
            else:
                fade = 1.0
                
            pos_keys.append({"frame": f, "value": [base_x + dx, base_y + dy, base_z + dz]})
            opac_keys.append({"frame": f, "value": pulse * fade})
            
        layers.append({
            "id": f"bokeh_{i}",
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
                        "easing": "linear",
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
    title_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        prog = f / DURATION_FRAMES
        # Smooth camera-coupled push
        z = -120.0 * (1.0 - min(1.0, prog / 0.22))**2 + prog * 45.0
        title_keys.append({"frame": f, "value": [260.0, 440.0, z]})
        
    title_opac = [
        {"frame": 0, "value": 0.0},
        {"frame": 22, "value": 1.0},
        {"frame": 158, "value": 1.0},
        {"frame": 179, "value": 0.0}
    ]
    
    layers.append({
        "id": "hero_title",
        "type": "text",
        "text": "AMBIENT DRIFT & BOKEH 3D",
        "size": [1400, 120],
        "position": [260, 440, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Poppins-Bold.ttf",
            "font_size": 76.0,
            "fill": "#FFFFFF",
            "stroke": {
                "color": "#080C14",
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
    sub_opac = [
        {"frame": 0, "value": 0.0},
        {"frame": 18, "value": 0.0},
        {"frame": 36, "value": 0.9},
        {"frame": 158, "value": 0.9},
        {"frame": 179, "value": 0.0}
    ]
    layers.append({
        "id": "subtitle",
        "type": "text",
        "text": "MULTI-HARMONIC BROWNIAN FIELD • SILKY 60 FPS • CHRONONMOTION 3D",
        "size": [1400, 60],
        "position": [260, 545, 0],
        "enable_3d": True,
        "style": {
            "font": "assets/fonts/Inter-Bold.ttf",
            "font_size": 25.0,
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
    
    # Camera: Smooth continuous dolly push in 60fps
    cam_keys = []
    for f in range(0, DURATION_FRAMES + 1, 2):
        prog = f / DURATION_FRAMES
        smooth_p = prog * prog * (3.0 - 2.0 * prog)
        cam_z = -1200.0 + smooth_p * 260.0
        cam_keys.append({"frame": f, "value": cam_z})
        
    plan = {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": "chrononmotion_ambient_bokeh_v2",
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
            "path": str(OUT_DIR / "chrononmotion_ambient_bokeh_60fps_smooth.mp4"),
            "format": "mp4",
            "codec": "h264"
        }
    }
    
    plan_path = OUT_DIR / "chrononmotion_ambient_bokeh_v2.plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Created {plan_path}")

if __name__ == "__main__":
    build_bokeh_v2()
