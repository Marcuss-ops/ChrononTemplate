#!/usr/bin/env python3
"""
Harmonious Multi-Entity Chained Timeline Engine
Demonstrates modern documentary-grade choreography across heterogeneous entity types:
1. Image with Text (Person / Portrait Cutout + Pill Badge)
2. Timeline Date (Key Historical Milestone)
3. Quantitative Metric / Number (High-impact Stat + Tag)
4. Geolocation Map (Topographic / Satellite Plate + Coordinate Reticle)

Architecture:
- Dynamic Spatial Slots: Hero Focus Slot (Right / Center) <-> Companion Receding Slot (Left)
- Continuous Stage Continuity: Zero jump cuts, zero caption bounding collisions.
- Unified 3D Easing: out_cubic transitions with synchronized opacity & scale attenuation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Paths
BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing").resolve()
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "out"
PLAN_PATH = OUT_DIR / "harmonious_multi_entity_chain.plan.json"
OUTPUT_MP4 = OUT_DIR / "harmonious_multi_entity_chain_demo.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 360  # 12.0 seconds

# Slot definitions (relative to canvas center (960, 540)):
HERO_X = 360.0        # Canvas X = 1320
COMPANION_X = -460.0   # Canvas X = 500
CENTER_X = 0.0         # Canvas X = 960 (for initial solo entrance)

FONT_BOLD = "assets/fonts/Inter-Bold.ttf"
FONT_REGULAR = "assets/fonts/Inter-Regular.ttf"
PORTRAIT_ASSET = "assets/images/premium_sample_portrait.png"
MAP_ASSET = "assets/maps/alps_basemap_doc.png"


def kf(frame: int, value: float | int | list) -> dict:
    return {"frame": frame, "value": value}


def track(prop: str, keyframes: list[dict], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing, "keyframes": keyframes}


def build_plan() -> dict:
    layers = []

    # -------------------------------------------------------------------------
    # 0. Global Canvas Background & Documentary Accent Frame
    # -------------------------------------------------------------------------
    layers.append({
        "id": "bg_canvas",
        "type": "color",
        "color": [0.024, 0.028, 0.038, 1.0],
        "size": [WIDTH, HEIGHT],
        "position": [0, 0],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    })

    # Subtle top documentary category bar
    layers.append({
        "id": "header_pill",
        "type": "color",
        "color": [0.07, 0.10, 0.15, 0.85],
        "size": [620, 42],
        "position": [0, -470],
        "radius": 21,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    })
    layers.append({
        "id": "header_text",
        "type": "text",
        "text": "DOCUMENTARY CONTINUITY ENGINE  •  CHRONON MOTION",
        "size": [600, 36],
        "position": [960, 70],
        "style": {
            "font": FONT_BOLD,
            "font_size": 17,
            "fill": "#00F0FF",
            "fit_mode": "shrink_only",
        },
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    })

    # Timeline rail at the bottom
    layers.append({
        "id": "timeline_rail",
        "type": "color",
        "color": [0.12, 0.16, 0.22, 0.6],
        "size": [1600, 3],
        "position": [0, 460],
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    })

    # =========================================================================
    # 1. ENTITY 1: PERSON (Image with Text)
    # Active Window: Frames 0 -> 180 (0.0s -> 6.0s)
    # Enters Center (Frames 0-30), glides to Left Companion Slot (Frames 75-105)
    # =========================================================================
    e1_start = 0
    e1_dur = 180

    e1_pos_x_tracks = [
        kf(0, 0.0),
        kf(75, 0.0),
        kf(105, COMPANION_X),
        kf(179, COMPANION_X),
    ]
    e1_scale_tracks = [
        kf(0, 0.92),
        kf(28, 1.0),
        kf(75, 1.0),
        kf(105, 0.84),
        kf(179, 0.84),
    ]
    e1_opacity_tracks = [
        kf(0, 0.0),
        kf(20, 1.0),
        kf(75, 1.0),
        kf(105, 0.45),
        kf(150, 0.45),
        kf(175, 0.0),
    ]

    # E1 Card Background Plinth
    layers.append({
        "id": "e1_card_bg",
        "type": "color",
        "color": [0.05, 0.07, 0.10, 0.95],
        "size": [440, 560],
        "position": [0, -20],
        "radius": 24,
        "start_frame": e1_start,
        "duration_frames": e1_dur,
        "animation": {
            "tracks": [
                track("position_x", e1_pos_x_tracks),
                track("scale", e1_scale_tracks),
                track("opacity", e1_opacity_tracks),
            ]
        },
    })

    # E1 Portrait Image
    layers.append({
        "id": "e1_portrait",
        "type": "image",
        "asset": PORTRAIT_ASSET,
        "size": [400, 420],
        "position": [0, -65],
        "fit": "cover",
        "radius": 18,
        "start_frame": e1_start,
        "duration_frames": e1_dur,
        "animation": {
            "tracks": [
                track("position_x", e1_pos_x_tracks),
                track("scale", e1_scale_tracks),
                track("opacity", e1_opacity_tracks),
            ]
        },
    })

    # E1 Name Pill Badge
    layers.append({
        "id": "e1_pill_bg",
        "type": "color",
        "color": [0.08, 0.12, 0.18, 0.95],
        "size": [360, 48],
        "position": [0, 195],
        "radius": 24,
        "start_frame": e1_start,
        "duration_frames": e1_dur,
        "animation": {
            "tracks": [
                track("position_x", e1_pos_x_tracks),
                track("scale", e1_scale_tracks),
                track("opacity", e1_opacity_tracks),
            ]
        },
    })

    # E1 Name Label Text
    layers.append({
        "id": "e1_name_text",
        "type": "text",
        "text": "ALAN TURING",
        "size": [340, 40],
        "position": [960, 735],
        "style": {
            "font": FONT_BOLD,
            "font_size": 22,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e1_start,
        "duration_frames": e1_dur,
        "animation": {
            "tracks": [
                track("position_x", e1_pos_x_tracks),
                track("scale", e1_scale_tracks),
                track("opacity", e1_opacity_tracks),
            ]
        },
    })

    # =========================================================================
    # 2. ENTITY 2: DATE (Timeline Milestone)
    # Active Window: Frames 75 -> 265 (2.5s -> 8.8s)
    # Enters Hero Slot (X=360), then glides to Left Companion Slot (X=-460) at Frame 165
    # =========================================================================
    e2_start = 75
    e2_dur = 190

    e2_pos_x_tracks = [
        kf(0, HERO_X + 60.0),
        kf(30, HERO_X),
        kf(90, HERO_X),
        kf(120, COMPANION_X),
        kf(189, COMPANION_X),
    ]
    e2_scale_tracks = [
        kf(0, 0.88),
        kf(30, 1.0),
        kf(90, 1.0),
        kf(120, 0.84),
        kf(189, 0.84),
    ]
    e2_opacity_tracks = [
        kf(0, 0.0),
        kf(22, 1.0),
        kf(90, 1.0),
        kf(120, 0.45),
        kf(165, 0.45),
        kf(189, 0.0),
    ]

    # E2 Card Container
    layers.append({
        "id": "e2_card_bg",
        "type": "color",
        "color": [0.06, 0.09, 0.14, 0.95],
        "size": [500, 420],
        "position": [0, -20],
        "radius": 24,
        "start_frame": e2_start,
        "duration_frames": e2_dur,
        "animation": {
            "tracks": [
                track("position_x", e2_pos_x_tracks),
                track("scale", e2_scale_tracks),
                track("opacity", e2_opacity_tracks),
            ]
        },
    })

    # E2 Eyebrow Accent
    layers.append({
        "id": "e2_eyebrow",
        "type": "text",
        "text": "HISTORICAL TIMELINE",
        "size": [440, 30],
        "position": [960, 420],
        "style": {
            "font": FONT_BOLD,
            "font_size": 18,
            "fill": "#00F0FF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e2_start,
        "duration_frames": e2_dur,
        "animation": {
            "tracks": [
                track("position_x", e2_pos_x_tracks),
                track("scale", e2_scale_tracks),
                track("opacity", e2_opacity_tracks),
            ]
        },
    })

    # E2 Big Date Value
    layers.append({
        "id": "e2_date_val",
        "type": "text",
        "text": "MAY 1940",
        "size": [440, 90],
        "position": [960, 500],
        "style": {
            "font": FONT_BOLD,
            "font_size": 64,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e2_start,
        "duration_frames": e2_dur,
        "animation": {
            "tracks": [
                track("position_x", e2_pos_x_tracks),
                track("scale", e2_scale_tracks),
                track("opacity", e2_opacity_tracks),
            ]
        },
    })

    # E2 Context Label
    layers.append({
        "id": "e2_label",
        "type": "text",
        "text": "BLETCHLEY PARK • BOMBE DEPLOYED",
        "size": [440, 36],
        "position": [960, 580],
        "style": {
            "font": FONT_REGULAR,
            "font_size": 20,
            "fill": "#A0B0C4",
            "fit_mode": "shrink_only",
        },
        "start_frame": e2_start,
        "duration_frames": e2_dur,
        "animation": {
            "tracks": [
                track("position_x", e2_pos_x_tracks),
                track("scale", e2_scale_tracks),
                track("opacity", e2_opacity_tracks),
            ]
        },
    })

    # =========================================================================
    # 3. ENTITY 3: METRIC / NUMBER (Quantitative Stat)
    # Active Window: Frames 165 -> 350 (5.5s -> 11.6s)
    # Enters Hero Slot (X=360), then glides to Left Companion Slot (X=-460) at Frame 255
    # =========================================================================
    e3_start = 165
    e3_dur = 185

    e3_pos_x_tracks = [
        kf(0, HERO_X + 60.0),
        kf(30, HERO_X),
        kf(90, HERO_X),
        kf(120, COMPANION_X),
        kf(184, COMPANION_X),
    ]
    e3_scale_tracks = [
        kf(0, 0.88),
        kf(30, 1.0),
        kf(90, 1.0),
        kf(120, 0.84),
        kf(184, 0.84),
    ]
    e3_opacity_tracks = [
        kf(0, 0.0),
        kf(22, 1.0),
        kf(90, 1.0),
        kf(120, 0.45),
        kf(160, 0.45),
        kf(184, 0.0),
    ]

    # E3 Card Background
    layers.append({
        "id": "e3_card_bg",
        "type": "color",
        "color": [0.05, 0.09, 0.08, 0.95],
        "size": [500, 420],
        "position": [0, -20],
        "radius": 24,
        "start_frame": e3_start,
        "duration_frames": e3_dur,
        "animation": {
            "tracks": [
                track("position_x", e3_pos_x_tracks),
                track("scale", e3_scale_tracks),
                track("opacity", e3_opacity_tracks),
            ]
        },
    })

    # E3 Eyebrow Accent
    layers.append({
        "id": "e3_eyebrow",
        "type": "text",
        "text": "INTELLIGENCE RATE",
        "size": [440, 30],
        "position": [960, 420],
        "style": {
            "font": FONT_BOLD,
            "font_size": 18,
            "fill": "#50FA7B",
            "fit_mode": "shrink_only",
        },
        "start_frame": e3_start,
        "duration_frames": e3_dur,
        "animation": {
            "tracks": [
                track("position_x", e3_pos_x_tracks),
                track("scale", e3_scale_tracks),
                track("opacity", e3_opacity_tracks),
            ]
        },
    })

    # E3 Big Number Value
    layers.append({
        "id": "e3_num_val",
        "type": "text",
        "text": "84,000 / mo",
        "size": [440, 90],
        "position": [960, 500],
        "style": {
            "font": FONT_BOLD,
            "font_size": 60,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e3_start,
        "duration_frames": e3_dur,
        "animation": {
            "tracks": [
                track("position_x", e3_pos_x_tracks),
                track("scale", e3_scale_tracks),
                track("opacity", e3_opacity_tracks),
            ]
        },
    })

    # E3 Context Tag Label
    layers.append({
        "id": "e3_label",
        "type": "text",
        "text": "DECRYPTED AXIS DISPATCHES (+340%)",
        "size": [440, 36],
        "position": [960, 580],
        "style": {
            "font": FONT_REGULAR,
            "font_size": 20,
            "fill": "#A0B8A8",
            "fit_mode": "shrink_only",
        },
        "start_frame": e3_start,
        "duration_frames": e3_dur,
        "animation": {
            "tracks": [
                track("position_x", e3_pos_x_tracks),
                track("scale", e3_scale_tracks),
                track("opacity", e3_opacity_tracks),
            ]
        },
    })

    # =========================================================================
    # 4. ENTITY 4: MAP (Geolocation Plate)
    # Active Window: Frames 255 -> 360 (8.5s -> 12.0s)
    # Enters Hero Slot (X=360), settles as final climax
    # =========================================================================
    e4_start = 255
    e4_dur = 105

    e4_pos_x_tracks = [
        kf(0, HERO_X + 60.0),
        kf(30, HERO_X),
        kf(104, HERO_X),
    ]
    e4_scale_tracks = [
        kf(0, 0.90),
        kf(30, 1.0),
        kf(104, 1.02),
    ]
    e4_opacity_tracks = [
        kf(0, 0.0),
        kf(22, 1.0),
        kf(104, 1.0),
    ]

    # E4 Map Background Plate
    layers.append({
        "id": "e4_card_bg",
        "type": "color",
        "color": [0.06, 0.08, 0.12, 0.95],
        "size": [500, 480],
        "position": [0, -20],
        "radius": 24,
        "start_frame": e4_start,
        "duration_frames": e4_dur,
        "animation": {
            "tracks": [
                track("position_x", e4_pos_x_tracks),
                track("scale", e4_scale_tracks),
                track("opacity", e4_opacity_tracks),
            ]
        },
    })

    # E4 Map Plate Image (Topographic Satellite)
    layers.append({
        "id": "e4_map_plate",
        "type": "image",
        "asset": MAP_ASSET,
        "size": [460, 270],
        "position": [0, -85],
        "fit": "cover",
        "radius": 16,
        "start_frame": e4_start,
        "duration_frames": e4_dur,
        "animation": {
            "tracks": [
                track("position_x", e4_pos_x_tracks),
                track("scale", e4_scale_tracks),
                track("opacity", e4_opacity_tracks),
            ]
        },
    })

    # E4 Map Radar Pin Dot
    layers.append({
        "id": "e4_pin_dot",
        "type": "color",
        "color": [0.0, 0.94, 1.0, 1.0],
        "size": [14, 14],
        "position": [0, -85],
        "radius": 7,
        "start_frame": e4_start,
        "duration_frames": e4_dur,
        "animation": {
            "tracks": [
                track("position_x", e4_pos_x_tracks),
                track("scale", [kf(0, 1.0), kf(30, 1.4), kf(60, 1.0), kf(90, 1.4), kf(104, 1.0)]),
            ]
        },
    })

    # E4 Location Title
    layers.append({
        "id": "e4_loc_title",
        "type": "text",
        "text": "BLETCHLEY PARK, UK",
        "size": [440, 40],
        "position": [960, 615],
        "style": {
            "font": FONT_BOLD,
            "font_size": 24,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e4_start,
        "duration_frames": e4_dur,
        "animation": {
            "tracks": [
                track("position_x", e4_pos_x_tracks),
                track("scale", e4_scale_tracks),
                track("opacity", e4_opacity_tracks),
            ]
        },
    })

    # E4 Coordinates Pill
    layers.append({
        "id": "e4_coords",
        "type": "text",
        "text": "51.997° N  •  0.741° W  (STATION X)",
        "size": [440, 32],
        "position": [960, 665],
        "style": {
            "font": FONT_REGULAR,
            "font_size": 17,
            "fill": "#00F0FF",
            "fit_mode": "shrink_only",
        },
        "start_frame": e4_start,
        "duration_frames": e4_dur,
        "animation": {
            "tracks": [
                track("position_x", e4_pos_x_tracks),
                track("scale", e4_scale_tracks),
                track("opacity", e4_opacity_tracks),
            ]
        },
    })

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "harmonious_multi_entity_chain_demo",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES,
        },
        "output": {
            "path": str(OUTPUT_MP4),
            "format": "mp4",
            "codec": "h264",
        },
        "layers": layers,
    }
    return plan


def main():
    print(f"Building Chronon Plan for Harmonious Multi-Entity Chain...")
    plan = build_plan()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PLAN_PATH, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"Plan saved to {PLAN_PATH} ({len(plan['layers'])} layers, {DURATION_FRAMES} frames)")

    print(f"Invoking chronon3d_cli render...")
    t0 = time.time()
    cmd = [
        str(CHRONON_CLI),
        "render",
        "--plan", str(PLAN_PATH),
        "-o", str(OUTPUT_MP4),
        "--assets-root", str(ASSETS_ROOT),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"Error rendering plan: {res.stderr}\n{res.stdout}")
        sys.exit(1)

    print(f"Render completed successfully in {dt:.2f}s!")
    print(f"MP4 output written to: {OUTPUT_MP4} ({OUTPUT_MP4.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
