#!/usr/bin/env python3
"""
Harmonious Multi-Entity Documentary Timeline Engine (Runtime Quality)
Implements user-directed narrative choreography:
1. Alan Turing (Image 1): Full 3D entrance (depth float, 3D yaw unfold, pill badge).
2. Connected Timeline (Date 1940): Emerges directly below Turing, tying the event
   ("1940 • ENIGMA CIPHER BROKEN") directly to the subject.
3. Ada Lovelace (Image 2 - Same Semantic Group): Does NOT wipe out the date or Turing;
   Turing slides left, Ada enters on the right with full 3D animation, forming an
   interconnected dual-portrait pair over the timeline rail.
4. London Map (Map with Full Cinematic Animation): Camera transition into a tactical
   map zoom over London, animated radar beacon, tactical reticle, and coordinate callout.
5. Realistic Cinematic Background: Real documentary video background with atmospheric grade.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing").resolve()
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "out"
PLAN_PATH = OUT_DIR / "documentary_narrative_runtime.plan.json"
OUTPUT_MP4 = OUT_DIR / "documentary_narrative_runtime_demo.mp4"
UPLOADER = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS = Path("/home/pierone/.config/velox/credentials.json")
TOKEN = Path("/home/pierone/.config/velox/token.json")
DRIVE_FOLDER_ID = "1UEUnH1G35Zyhdq7iH2VN0GkyrPiHgMUN"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 390  # 13.0 seconds

BG_VIDEO = "assets/backgrounds/documentary_bg.mp4"
FONT_BOLD = "assets/fonts/Inter-Bold.ttf"
FONT_REGULAR = "assets/fonts/Inter-Regular.ttf"
TURING_IMG = "assets/images/alan_turing.png"
ADA_IMG = "assets/images/ada_lovelace.jpg"
MAP_PLATE = "assets/maps/t4_plate2.png"
MAP_RETICLE = "assets/maps/doc_reticle.png"


def kf(frame: int, value: float | int | list) -> dict:
    return {"frame": frame, "value": value}


def track(prop: str, keyframes: list[dict], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing, "keyframes": keyframes}


def build_plan() -> dict:
    layers = []

    # =========================================================================
    # 0. Background: Real Documentary Video Loop + Atmospheric Grade
    # =========================================================================
    layers.append({
        "id": "bg_video",
        "type": "video",
        "source": BG_VIDEO,
        "size": [WIDTH, HEIGHT],
        "position": [0, 0],
        "fit": "cover",
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "loop": True,
    })

    # Dark atmospheric grade plate
    layers.append({
        "id": "bg_tint",
        "type": "color",
        "color": [0.012, 0.018, 0.028, 0.75],
        "size": [WIDTH, HEIGHT],
        "position": [0, 0],
        "screen_space": True,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
    })

    # Header category badge
    layers.append({
        "id": "header_pill_bg",
        "type": "color",
        "color": [0.06, 0.09, 0.14, 0.88],
        "size": [640, 42],
        "position": [0, -470],
        "radius": 21,
        "start_frame": 0,
        "duration_frames": 260,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(240, 1.0), kf(259, 0.0)])
            ]
        }
    })
    layers.append({
        "id": "header_text",
        "type": "text",
        "text": "HISTORICAL CHRONOLOGY  •  BRITISH INTELLIGENCE",
        "size": [620, 36],
        "position": [960, 70],
        "style": {
            "font": FONT_BOLD,
            "font_size": 17,
            "fill": "#00F0FF",
            "fit_mode": "shrink_only",
        },
        "start_frame": 0,
        "duration_frames": 260,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(240, 1.0), kf(259, 0.0)])
            ]
        }
    })

    # =========================================================================
    # 1. ENTITY 1: ALAN TURING (Full 3D Entrance + Solo Focus -> Duo Handoff)
    # Starts at Frame 0, holds center, slides left at Frame 160 as Ada enters
    # Fades out at Frame 260 for map transition
    # =========================================================================
    turing_start = 0
    turing_dur = 260

    # Unified keyframe timeline for Turing's multi-axis transforms:
    # Keyframes: [0, 32, 150, 185, 240, 259]
    turing_pos_x_kfs = [kf(0, 0.0), kf(32, 0.0), kf(150, 0.0), kf(185, -430.0), kf(240, -430.0), kf(259, -430.0)]
    turing_pos_y_kfs = [kf(0, 0.0), kf(32, 0.0), kf(150, 0.0), kf(185, 0.0), kf(240, 0.0), kf(259, 0.0)]
    turing_pos_z_kfs = [kf(0, -280.0), kf(32, 0.0), kf(150, 0.0), kf(185, 0.0), kf(240, 0.0), kf(259, 120.0)]

    turing_rot_x_kfs = [kf(0, 0.0), kf(32, 0.0), kf(150, 0.0), kf(185, 0.0), kf(240, 0.0), kf(259, 0.0)]
    turing_rot_y_kfs = [kf(0, -24.0), kf(32, 0.0), kf(150, 0.0), kf(185, -1.5), kf(240, -1.5), kf(259, -1.5)]
    turing_rot_z_kfs = [kf(0, 0.0), kf(32, 0.0), kf(150, 0.0), kf(185, 0.0), kf(240, 0.0), kf(259, 0.0)]

    turing_scale_kfs = [kf(0, 0.88), kf(32, 1.0), kf(150, 1.0), kf(185, 0.88), kf(240, 0.88), kf(259, 0.78)]
    turing_opacity_kfs = [kf(0, 0.0), kf(32, 1.0), kf(150, 1.0), kf(185, 1.0), kf(240, 1.0), kf(259, 0.0)]

    turing_3d_tracks = [
        track("position_x", turing_pos_x_kfs),
        track("position_y", turing_pos_y_kfs),
        track("position_z", turing_pos_z_kfs),
        track("rotation_x", turing_rot_x_kfs),
        track("rotation_y", turing_rot_y_kfs),
        track("rotation_z", turing_rot_z_kfs),
        track("scale", turing_scale_kfs),
        track("opacity", turing_opacity_kfs),
    ]

    # Turing Card Plinth
    layers.append({
        "id": "turing_card_bg",
        "type": "color",
        "color": [0.05, 0.07, 0.11, 0.95],
        "size": [480, 520],
        "position": [0, -80],
        "radius": 24,
        "enable_3d": True,
        "start_frame": turing_start,
        "duration_frames": turing_dur,
        "animation": {"tracks": turing_3d_tracks},
    })

    # Turing Portrait
    layers.append({
        "id": "turing_portrait",
        "type": "image",
        "asset": TURING_IMG,
        "size": [440, 410],
        "position": [0, -120],
        "fit": "cover",
        "radius": 18,
        "enable_3d": True,
        "start_frame": turing_start,
        "duration_frames": turing_dur,
        "animation": {"tracks": turing_3d_tracks},
    })

    # Turing Pill Badge
    layers.append({
        "id": "turing_pill_bg",
        "type": "color",
        "color": [0.08, 0.12, 0.18, 0.95],
        "size": [420, 50],
        "position": [0, 130],
        "radius": 25,
        "enable_3d": True,
        "start_frame": turing_start,
        "duration_frames": turing_dur,
        "animation": {"tracks": turing_3d_tracks},
    })

    # Turing Name Text
    layers.append({
        "id": "turing_name_text",
        "type": "text",
        "text": "ALAN TURING  •  CRYPTANALYST",
        "size": [400, 40],
        "position": [960, 670],
        "style": {
            "font": FONT_BOLD,
            "font_size": 20,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": turing_start,
        "duration_frames": turing_dur,
        "animation": {
            "tracks": [
                track("position_x", turing_pos_x_kfs),
                track("scale", turing_scale_kfs),
                track("opacity", turing_opacity_kfs),
            ]
        },
    })

    # =========================================================================
    # 2. CONNECTED TIMELINE SOTTO (Data 1940 - Collegata al 100% all'immagine)
    # Starts at Frame 75 directly below Alan Turing
    # Expands horizontally: "1940 • ENIGMA CIPHER BROKEN"
    # =========================================================================
    timeline_start = 75
    timeline_dur = 185  # 75 -> 260

    # Timeline Container Bar
    layers.append({
        "id": "timeline_bar_bg",
        "type": "color",
        "color": [0.06, 0.09, 0.14, 0.92],
        "size": [960, 76],
        "position": [0, 270],
        "radius": 20,
        "start_frame": timeline_start,
        "duration_frames": timeline_dur,
        "animation": {
            "tracks": [
                track("scale_x", [kf(0, 0.05), kf(28, 1.0), kf(184, 1.0)]),
                track("opacity", [kf(0, 0.0), kf(18, 1.0), kf(165, 1.0), kf(184, 0.0)]),
            ]
        },
    })

    # Timeline Cyan Accent Line
    layers.append({
        "id": "timeline_rail_line",
        "type": "color",
        "color": [0.0, 0.94, 1.0, 0.85],
        "size": [900, 3],
        "position": [0, 246],
        "start_frame": timeline_start,
        "duration_frames": timeline_dur,
        "animation": {
            "tracks": [
                track("scale_x", [kf(0, 0.01), kf(28, 1.0), kf(184, 1.0)]),
                track("opacity", [kf(0, 0.0), kf(18, 1.0), kf(165, 1.0), kf(184, 0.0)]),
            ]
        },
    })

    # Timeline Year Callout Pill ("1940")
    layers.append({
        "id": "timeline_year_pill",
        "type": "color",
        "color": [0.0, 0.94, 1.0, 1.0],
        "size": [130, 36],
        "position": [-350, 275],
        "radius": 18,
        "start_frame": timeline_start,
        "duration_frames": timeline_dur,
        "animation": {
            "tracks": [
                track("scale", [kf(0, 0.5), kf(22, 1.08), kf(32, 1.0), kf(184, 1.0)]),
                track("opacity", [kf(0, 0.0), kf(16, 1.0), kf(165, 1.0), kf(184, 0.0)]),
            ]
        },
    })

    layers.append({
        "id": "timeline_year_text",
        "type": "text",
        "text": "1940",
        "size": [120, 32],
        "position": [610, 815],
        "style": {
            "font": FONT_BOLD,
            "font_size": 22,
            "fill": "#0A0D14",
            "fit_mode": "shrink_only",
        },
        "start_frame": timeline_start,
        "duration_frames": timeline_dur,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(16, 1.0), kf(165, 1.0), kf(184, 0.0)]),
            ]
        },
    })

    # Milestone Text
    layers.append({
        "id": "timeline_desc_text",
        "type": "text",
        "text": "ENIGMA CIPHER CRACKED  •  BOMBE MACHINE DEPLOYED",
        "size": [700, 36],
        "position": [1080, 815],
        "style": {
            "font": FONT_BOLD,
            "font_size": 20,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": timeline_start,
        "duration_frames": timeline_dur,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(24, 1.0), kf(165, 1.0), kf(184, 0.0)]),
            ]
        },
    })

    # =========================================================================
    # 3. ENTITY 2: ADA LOVELACE (Second Image in Same Group - Duo Pairing)
    # Starts at Frame 155 on Right Slot (+430)
    # Full 3D entrance mirroring Turing, creating a connected Duo!
    # =========================================================================
    ada_start = 155
    ada_dur = 105  # 155 -> 260

    # Unified keyframe timeline for Ada:
    # Keyframes: [0, 32, 85, 104]
    ada_pos_x_kfs = [kf(0, 430.0 + 80.0), kf(32, 430.0), kf(85, 430.0), kf(104, 430.0)]
    ada_pos_y_kfs = [kf(0, 0.0), kf(32, 0.0), kf(85, 0.0), kf(104, 0.0)]
    ada_pos_z_kfs = [kf(0, -280.0), kf(32, 0.0), kf(85, 0.0), kf(104, 120.0)]

    ada_rot_x_kfs = [kf(0, 0.0), kf(32, 0.0), kf(85, 0.0), kf(104, 0.0)]
    ada_rot_y_kfs = [kf(0, 24.0), kf(32, 0.0), kf(85, 1.5), kf(104, 1.5)]
    ada_rot_z_kfs = [kf(0, 0.0), kf(32, 0.0), kf(85, 0.0), kf(104, 0.0)]

    ada_scale_kfs = [kf(0, 0.88), kf(32, 0.88), kf(85, 0.88), kf(104, 0.78)]
    ada_opacity_kfs = [kf(0, 0.0), kf(32, 1.0), kf(85, 1.0), kf(104, 0.0)]

    ada_3d_tracks = [
        track("position_x", ada_pos_x_kfs),
        track("position_y", ada_pos_y_kfs),
        track("position_z", ada_pos_z_kfs),
        track("rotation_x", ada_rot_x_kfs),
        track("rotation_y", ada_rot_y_kfs),
        track("rotation_z", ada_rot_z_kfs),
        track("scale", ada_scale_kfs),
        track("opacity", ada_opacity_kfs),
    ]

    # Ada Card Frame
    layers.append({
        "id": "ada_card_bg",
        "type": "color",
        "color": [0.05, 0.07, 0.11, 0.95],
        "size": [480, 520],
        "position": [0, -80],
        "radius": 24,
        "enable_3d": True,
        "start_frame": ada_start,
        "duration_frames": ada_dur,
        "animation": {"tracks": ada_3d_tracks},
    })

    # Ada Portrait Photo
    layers.append({
        "id": "ada_portrait",
        "type": "image",
        "asset": ADA_IMG,
        "size": [440, 410],
        "position": [0, -120],
        "fit": "cover",
        "radius": 18,
        "enable_3d": True,
        "start_frame": ada_start,
        "duration_frames": ada_dur,
        "animation": {"tracks": ada_3d_tracks},
    })

    # Ada Pill Badge
    layers.append({
        "id": "ada_pill_bg",
        "type": "color",
        "color": [0.08, 0.12, 0.18, 0.95],
        "size": [420, 50],
        "position": [0, 130],
        "radius": 25,
        "enable_3d": True,
        "start_frame": ada_start,
        "duration_frames": ada_dur,
        "animation": {"tracks": ada_3d_tracks},
    })

    layers.append({
        "id": "ada_name_text",
        "type": "text",
        "text": "ADA LOVELACE  •  ALGORITHM PIONEER",
        "size": [400, 40],
        "position": [1390, 670],
        "style": {
            "font": FONT_BOLD,
            "font_size": 20,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": ada_start,
        "duration_frames": ada_dur,
        "animation": {
            "tracks": [
                track("position_x", [kf(0, 80.0), kf(32, 0.0), kf(85, 0.0), kf(104, 0.0)]),
                track("scale", ada_scale_kfs),
                track("opacity", ada_opacity_kfs),
            ]
        },
    })

    # Duo Synergic Header Callout
    layers.append({
        "id": "duo_link_badge",
        "type": "color",
        "color": [0.07, 0.11, 0.16, 0.92],
        "size": [380, 36],
        "position": [0, -320],
        "radius": 18,
        "start_frame": 180,
        "duration_frames": 80,
        "animation": {
            "tracks": [
                track("scale", [kf(0, 0.7), kf(24, 1.0), kf(60, 1.0), kf(79, 1.0)]),
                track("opacity", [kf(0, 0.0), kf(18, 1.0), kf(60, 1.0), kf(79, 0.0)]),
            ]
        },
    })
    layers.append({
        "id": "duo_link_text",
        "type": "text",
        "text": "THEORETICAL FOUNDATION DUO",
        "size": [360, 30],
        "position": [960, 220],
        "style": {
            "font": FONT_BOLD,
            "font_size": 16,
            "fill": "#50FA7B",
            "fit_mode": "shrink_only",
        },
        "start_frame": 180,
        "duration_frames": 80,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(18, 1.0), kf(60, 1.0), kf(79, 0.0)]),
            ]
        },
    })

    # =========================================================================
    # 4. MAP ANIMATION: LONDON, UK (Cinematic Flyover / Tactical Zoom on London)
    # Active Window: Frames 255 -> 390 (8.5s -> 13.0s)
    # Tactical map plate with Ken Burns zoom, pulsing radar beacon, reticle,
    # and London Admiralty coordinate card.
    # =========================================================================
    map_start = 255
    map_dur = 135  # 255 -> 390

    # Keyframes for map position and scale: [0, 30, 134]
    map_pos_x_kfs = [kf(0, 0.0), kf(30, 0.0), kf(134, 0.0)]
    map_pos_y_kfs = [kf(0, 30.0), kf(30, 0.0), kf(134, -40.0)]
    map_scale_kfs = [kf(0, 1.02), kf(30, 1.15), kf(134, 1.32)]
    map_opacity_kfs = [kf(0, 0.0), kf(24, 1.0), kf(134, 1.0)]

    layers.append({
        "id": "map_plate",
        "type": "image",
        "asset": MAP_PLATE,
        "size": [1920, 1080],
        "position": [0, 0],
        "fit": "cover",
        "start_frame": map_start,
        "duration_frames": map_dur,
        "animation": {
            "tracks": [
                track("position_x", map_pos_x_kfs),
                track("position_y", map_pos_y_kfs),
                track("scale", map_scale_kfs),
                track("opacity", map_opacity_kfs),
            ]
        },
    })

    # Vignette overlay for map focus
    layers.append({
        "id": "map_vignette",
        "type": "color",
        "color": [0.02, 0.03, 0.05, 0.45],
        "size": [WIDTH, HEIGHT],
        "position": [0, 0],
        "screen_space": True,
        "start_frame": map_start,
        "duration_frames": map_dur,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(24, 0.45), kf(134, 0.45)])
            ]
        }
    })

    # Radar Pulsing Dot at London Center
    layers.append({
        "id": "radar_dot",
        "type": "color",
        "color": [0.0, 0.94, 1.0, 1.0],
        "size": [18, 18],
        "position": [60, -30],
        "radius": 9,
        "start_frame": map_start + 15,
        "duration_frames": map_dur - 15,
        "animation": {
            "tracks": [
                track("scale", [
                    kf(0, 0.0),
                    kf(15, 1.6),
                    kf(30, 1.0),
                    kf(45, 1.6),
                    kf(60, 1.0),
                    kf(75, 1.6),
                    kf(90, 1.0),
                    kf(119, 1.4),
                ]),
                track("opacity", [kf(0, 0.0), kf(15, 1.0), kf(119, 1.0)]),
            ]
        },
    })

    # Tactical Radar Ring around London
    layers.append({
        "id": "radar_ring",
        "type": "color",
        "color": [0.0, 0.94, 1.0, 0.35],
        "size": [80, 80],
        "position": [60, -30],
        "radius": 40,
        "start_frame": map_start + 15,
        "duration_frames": map_dur - 15,
        "animation": {
            "tracks": [
                track("scale", [
                    kf(0, 0.2),
                    kf(35, 1.8),
                    kf(40, 0.2),
                    kf(75, 1.8),
                    kf(80, 0.2),
                    kf(119, 1.8),
                ]),
                track("opacity", [
                    kf(0, 0.8),
                    kf(35, 0.0),
                    kf(40, 0.8),
                    kf(75, 0.0),
                    kf(80, 0.8),
                    kf(119, 0.0),
                ]),
            ]
        },
    })

    # Tactical Target Reticle
    layers.append({
        "id": "map_reticle",
        "type": "image",
        "asset": MAP_RETICLE,
        "size": [120, 120],
        "position": [60, -30],
        "fit": "contain",
        "start_frame": map_start + 10,
        "duration_frames": map_dur - 10,
        "animation": {
            "tracks": [
                track("rotation_z", [kf(0, -90.0), kf(40, 0.0), kf(124, 45.0)]),
                track("scale", [kf(0, 1.8), kf(30, 1.0), kf(124, 1.05)]),
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(124, 1.0)]),
            ]
        },
    })

    # Location Information Card (Bottom Left Callout)
    layers.append({
        "id": "london_card_bg",
        "type": "color",
        "color": [0.05, 0.08, 0.13, 0.95],
        "size": [620, 170],
        "position": [-580, 360],
        "radius": 22,
        "start_frame": map_start + 20,
        "duration_frames": map_dur - 20,
        "animation": {
            "tracks": [
                track("position_x", [kf(0, -60.0), kf(28, 0.0), kf(114, 0.0)]),
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(114, 1.0)]),
            ]
        },
    })

    layers.append({
        "id": "london_eyebrow",
        "type": "text",
        "text": "TACTICAL GEOGRAPHIC LOCATION",
        "size": [560, 30],
        "position": [380, 835],
        "style": {
            "font": FONT_BOLD,
            "font_size": 17,
            "fill": "#00F0FF",
            "fit_mode": "shrink_only",
        },
        "start_frame": map_start + 20,
        "duration_frames": map_dur - 20,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(114, 1.0)])
            ]
        },
    })

    layers.append({
        "id": "london_title",
        "type": "text",
        "text": "LONDON, UK",
        "size": [560, 52],
        "position": [380, 880],
        "style": {
            "font": FONT_BOLD,
            "font_size": 42,
            "fill": "#FFFFFF",
            "fit_mode": "shrink_only",
        },
        "start_frame": map_start + 20,
        "duration_frames": map_dur - 20,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(114, 1.0)])
            ]
        },
    })

    layers.append({
        "id": "london_sub",
        "type": "text",
        "text": "51.5074° N  •  0.1278° W  (ADMIRALTY & WAR CABINET)",
        "size": [560, 32],
        "position": [380, 935],
        "style": {
            "font": FONT_REGULAR,
            "font_size": 18,
            "fill": "#A0B8D0",
            "fit_mode": "shrink_only",
        },
        "start_frame": map_start + 20,
        "duration_frames": map_dur - 20,
        "animation": {
            "tracks": [
                track("opacity", [kf(0, 0.0), kf(20, 1.0), kf(114, 1.0)])
            ]
        },
    })

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "documentary_narrative_runtime_demo",
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
    print("Building Chronon Plan for Narrative Runtime Documentary...")
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
        print(f"Error rendering plan:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)

    print(f"Render completed successfully in {dt:.2f}s!")
    size_mb = OUTPUT_MP4.stat().st_size / 1024 / 1024
    print(f"MP4 output written to: {OUTPUT_MP4} ({size_mb:.2f} MB)")

    # Upload to Google Drive via drive-upload
    print(f"Uploading to Google Drive folder {DRIVE_FOLDER_ID}...")
    up_cmd = [
        str(UPLOADER),
        "-credentials", str(CREDS),
        "-token", str(TOKEN),
        "-folder", DRIVE_FOLDER_ID,
        "-file", str(OUTPUT_MP4),
        "-name", "documentary_narrative_runtime_demo.mp4",
    ]
    up_res = subprocess.run(up_cmd, capture_output=True, text=True)
    print(f"Drive upload output:\n{up_res.stdout}")
    if up_res.returncode != 0:
        print(f"Upload failed: {up_res.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    main()
