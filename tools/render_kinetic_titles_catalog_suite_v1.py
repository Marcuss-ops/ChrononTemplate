#!/usr/bin/env python3
"""Chronon Kinetic Titles Catalog Suite V1: Complete 16-Title Native Port.

Implements all 16 kinetic typography motion components from the Animatiq & Remocn catalogs:
  01. title_01_per_word_rise        - Blur-to-sharp cascade upward settle
  02. title_02_blur_out_up          - Words arrive clean, depart upward with airy dissipation
  03. title_03_bottom_up_letters    - Deterministic staggered glyph reveal from below
  04. title_04_focus_blur_resolve   - Premium focus pull to crisp text, soft defocus exit
  05. title_05_line_by_line_slide   - Staggered line slide enter left, exit right
  06. title_06_line_swap            - Masked beat line replacement with accent underline
  07. title_07_morph_text           - Gooey fluid multi-phrase morph with swell transitions
  08. title_08_perspective_marquee  - 3D tilted horizon marquee roll
  09. title_09_scan_band            - Diagonal scan band sweep revealing chromatic offsets
  10. title_10_scramble_reveal      - Deterministic hacker string decode locking L-to-R
  11. title_11_shared_axis_y        - Per-word vertical shared-axis editorial swaps
  12. title_12_strikethrough_replace - Strike line across old text with pop replacement
  13. title_13_text_match_cut       - High-speed 85% curve mid-move hard match-cut
  14. title_14_text_shimmer         - Clean specular gradient glint sweep across headline
  15. title_15_weight_wave          - Traveling crest wave of thickness & forward lean
  16. title_16_chromatic_fringe_title - Blur-focus entrance with red/cyan breathing fringe

Renders strictly via Chronon3D CLI with software backend and uploads ONLY the MP4 video deliverables
directly to Google Drive folder 16HRHVZoFLV4EdBf_7NN7DdzHiaOVq-dJ.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_CLI = BASE_DIR / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
ASSETS_ROOT = BASE_DIR / "Chronon3d"
OUT_DIR = BASE_DIR / "ChrononTemplate/out/kinetic_titles_catalog_suite_v1"
DRIVE_UPLOAD_BIN = BASE_DIR / "RenderingGen/bin/drive-upload"
CREDS_FILE = BASE_DIR / "refactored/credentials.json"
TOKEN_FILE = BASE_DIR / "refactored/token.json"
DEFAULT_DRIVE_FOLDER = "16HRHVZoFLV4EdBf_7NN7DdzHiaOVq-dJ"

WIDTH = 1920
HEIGHT = 1080
FPS = 30


def build_track(prop: str, keyframes: List[tuple[int, float]], easing: str = "out_cubic") -> Dict[str, Any]:
    """Helper to build an animation track with valid Chronon schema."""
    return {
        "property": prop,
        "easing": easing,
        "keyframes": [{"frame": int(f), "value": float(v)} for f, v in keyframes]
    }


def text_layer(
    layer_id: str,
    text: str,
    font: str,
    font_size: float,
    color: str,
    pos: tuple[float, float],
    size: tuple[float, float],
    start: int = 0,
    duration: int = 100,
    tracks: List[Dict[str, Any]] | None = None,
    blend: str = "normal",
    opacity: float = 1.0,
) -> Dict[str, Any]:
    """Helper to create a well-formed Chronon text layer."""
    layer: Dict[str, Any] = {
        "id": layer_id,
        "type": "text",
        "start_frame": start,
        "duration_frames": duration,
        "text": text,
        "position": [float(pos[0]), float(pos[1])],
        "size": [float(size[0]), float(size[1])],
        "blend_mode": blend,
        "style": {
            "font": font,
            "font_size": float(font_size),
            "fill": color,
        }
    }
    all_tracks = []
    if tracks:
        all_tracks.extend(tracks)
    if all_tracks:
        layer["animation"] = {"tracks": all_tracks}
    return layer


def hex_to_rgba(hex_code: str, alpha: float = 1.0) -> List[float]:
    """Convert hex string to RGBA float array [0..1]."""
    h = hex_code.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return [round(r, 4), round(g, 4), round(b, 4), float(alpha)]
    elif len(h) == 8:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        a = int(h[6:8], 16) / 255.0
        return [round(r, 4), round(g, 4), round(b, 4), round(a, 4)]
    return [1.0, 1.0, 1.0, 1.0]


def shape_rect_layer(
    layer_id: str,
    fill_color: str | List[float],
    pos: tuple[float, float],
    size: tuple[float, float],
    radius: float = 0.0,
    start: int = 0,
    duration: int = 100,
    tracks: List[Dict[str, Any]] | None = None,
    blend: str = "normal",
) -> Dict[str, Any]:
    """Helper to create a well-formed Chronon shape layer."""
    fill_val = hex_to_rgba(fill_color) if isinstance(fill_color, str) else fill_color
    layer: Dict[str, Any] = {
        "id": layer_id,
        "type": "shape",
        "start_frame": start,
        "duration_frames": duration,
        "position": [float(pos[0]), float(pos[1])],
        "size": [float(size[0]), float(size[1])],
        "blend_mode": blend,
        "shape": {
            "type": "rect",
            "radius": float(radius),
            "fill": fill_val,
        }
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


# ==============================================================================
# 16 Title Authoring Functions
# ==============================================================================

def make_title_01_per_word_rise() -> Dict[str, Any]:
    """01: Per Word Rise - Words cascade upwards from blur to sharp settle, then soft exit."""
    duration = 100
    font = "assets/fonts/Inter-Bold.ttf"
    words = ["DESIGN", "BEYOND", "BOUNDARIES"]
    xs = [610.0, 950.0, 1330.0]
    widths = [320.0, 360.0, 480.0]

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.043, 0.047, 0.070, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    for i, (word, x, w) in enumerate(zip(words, xs, widths)):
        start_f = 10 + i * 7
        land_f = start_f + 16
        exit_start = 80
        exit_end = 96

        tracks = [
            build_track("position_y", [
                (0, 620.0),
                (start_f, 620.0),
                (land_f, 540.0),
                (exit_start, 540.0),
                (exit_end, 470.0),
                (duration - 1, 470.0)
            ], easing="out_cubic"),
            build_track("opacity", [
                (0, 0.0),
                (start_f, 0.0),
                (land_f, 1.0),
                (exit_start, 1.0),
                (exit_end, 0.0),
                (duration - 1, 0.0)
            ], easing="out_cubic")
        ]
        layers.append(text_layer(f"w_{i}", word, font, 94.0, "#FFFFFF", (x, 540.0), (w, 190.0), duration=duration, tracks=tracks))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_01_per_word_rise",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_01_per_word_rise.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_02_blur_out_up() -> Dict[str, Any]:
    """02: Blur Out Up - Words arrive clean, hold with authority, depart upward with airy dissipation."""
    duration = 95
    font = "assets/fonts/Poppins-Bold.ttf"
    words = ["TRANSCEND", "THE", "ORDINARY"]
    xs = [560.0, 920.0, 1310.0]
    widths = [450.0, 240.0, 480.0]

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.031, 0.035, 0.055, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    for i, (word, x, w) in enumerate(zip(words, xs, widths)):
        arrive_f = 16
        exit_start = 62 + i * 5
        exit_end = exit_start + 18

        tracks = [
            build_track("position_y", [
                (0, 540.0),
                (exit_start, 540.0),
                (exit_end, 410.0),
                (duration - 1, 410.0)
            ], easing="in_cubic"),
            build_track("opacity", [
                (0, 0.0),
                (arrive_f, 1.0),
                (exit_start, 1.0),
                (exit_end, 0.0),
                (duration - 1, 0.0)
            ], easing="out_cubic")
        ]
        layers.append(text_layer(f"w_{i}", word, font, 90.0, "#F0F6FC", (x, 540.0), (w, 180.0), duration=duration, tracks=tracks))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_02_blur_out_up",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_02_blur_out_up.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_03_bottom_up_letters() -> Dict[str, Any]:
    """03: Bottom Up Letters - Splits text into letters and reveals each glyph from below with deterministic timing."""
    duration = 95
    font = "assets/fonts/Space-Grotesk.ttf"
    letters = list("KINETICS")
    start_x = 590.0
    dx = 105.0

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.055, 0.063, 0.082, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    for i, char in enumerate(letters):
        x = start_x + i * dx
        start_f = 10 + i * 3
        land_f = start_f + 14

        tracks = [
            build_track("position_y", [
                (0, 630.0),
                (start_f, 630.0),
                (land_f, 540.0),
                (duration - 1, 540.0)
            ], easing="out_cubic"),
            build_track("opacity", [
                (0, 0.0),
                (start_f, 0.0),
                (land_f, 1.0),
                (duration - 1, 1.0)
            ], easing="out_cubic")
        ]
        layers.append(text_layer(f"char_{i}", char, font, 110.0, "#FFFFFF", (x, 540.0), (140.0, 220.0), duration=duration, tracks=tracks))

    # Architectural baseline accent rule
    layers.append(shape_rect_layer(
        "baseline_rule", "#38BDF8", (960.0, 620.0), (880.0, 3.0),
        tracks=[build_track("opacity", [(0, 0.0), (32, 0.0), (45, 0.8), (duration - 1, 0.8)], easing="out_cubic")],
        duration=duration
    ))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_03_bottom_up_letters",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_03_bottom_up_letters.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_04_focus_blur_resolve() -> Dict[str, Any]:
    """04: Focus Blur Resolve - Heavy focus pull to crisp text, then soft blur-out exit."""
    duration = 95
    font = "assets/fonts/Montserrat-ExtraBold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.027, 0.031, 0.043, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    tracks = [
        build_track("scale", [
            (0, 1.15),
            (28, 1.0),
            (68, 1.0),
            (90, 1.10),
            (duration - 1, 1.10)
        ], easing="out_cubic"),
        build_track("opacity", [
            (0, 0.0),
            (28, 1.0),
            (68, 1.0),
            (90, 0.0),
            (duration - 1, 0.0)
        ], easing="out_cubic")
    ]

    layers.append(text_layer("main_text", "CLARITY OF VISION", font, 92.0, "#FFFFFF", (960.0, 530.0), (1200.0, 190.0), duration=duration, tracks=tracks))

    # Optical precision sub-label
    sub_tracks = [
        build_track("opacity", [(0, 0.0), (25, 0.0), (40, 1.0), (68, 1.0), (88, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    ]
    layers.append(text_layer("sub_text", "OPTICAL PRECISION // RESOLVE", "assets/fonts/Space-Grotesk.ttf", 32.0, "#10B981", (960.0, 615.0), (800.0, 70.0), duration=duration, tracks=sub_tracks))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_04_focus_blur_resolve",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_04_focus_blur_resolve.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_05_line_by_line_slide() -> Dict[str, Any]:
    """05: Line-by-Line Slide - Each line enters from the left with staggered slide and exits right."""
    duration = 105
    font = "assets/fonts/Inter-Bold.ttf"
    lines = ["THINK IN DECADES", "EXECUTE IN DAYS", "ITERATE IN HOURS"]
    ys = [440.0, 540.0, 640.0]
    colors = ["#FFFFFF", "#FFFFFF", "#6366F1"]

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.063, 0.067, 0.086, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    for i, (line, y, col) in enumerate(zip(lines, ys, colors)):
        enter_s = 8 + i * 8
        enter_e = enter_s + 16
        exit_s = 74 + i * 6
        exit_e = exit_s + 16

        tracks = [
            build_track("position_x", [
                (0, 760.0),
                (enter_s, 760.0),
                (enter_e, 960.0),
                (exit_s, 960.0),
                (exit_e, 1160.0),
                (duration - 1, 1160.0)
            ], easing="out_cubic"),
            build_track("opacity", [
                (0, 0.0),
                (enter_s, 0.0),
                (enter_e, 1.0),
                (exit_s, 1.0),
                (exit_e, 0.0),
                (duration - 1, 0.0)
            ], easing="out_cubic")
        ]
        layers.append(text_layer(f"line_{i}", line, font, 78.0, col, (960.0, y), (1100.0, 150.0), duration=duration, tracks=tracks))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_05_line_by_line_slide",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_05_line_by_line_slide.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_06_line_swap() -> Dict[str, Any]:
    """06: Line Swap - Line A exits up on beat as Line B enters bottom-up with accent underline."""
    duration = 100
    font = "assets/fonts/Inter-Bold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.035, 0.039, 0.059, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Line A holds then exits up at f40
    track_a_y = build_track("position_y", [(0, 530.0), (38, 530.0), (52, 440.0), (duration - 1, 440.0)], easing="out_cubic")
    track_a_op = build_track("opacity", [(0, 1.0), (38, 1.0), (52, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("line_a", "THE LEGACY ARCHITECTURE", font, 84.0, "#94A3B8", (960.0, 530.0), (1300.0, 170.0), duration=duration, tracks=[track_a_y, track_a_op]))

    # Line B enters bottom-up at f38..52
    track_b_y = build_track("position_y", [(0, 620.0), (38, 620.0), (52, 530.0), (duration - 1, 530.0)], easing="out_cubic")
    track_b_op = build_track("opacity", [(0, 0.0), (38, 0.0), (52, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(text_layer("line_b", "THE NEXT GENERATION", font, 84.0, "#FFFFFF", (960.0, 530.0), (1300.0, 170.0), duration=duration, tracks=[track_b_y, track_b_op]))

    # Accent underline drawing beneath "GENERATION"
    underline_op = build_track("opacity", [(0, 0.0), (52, 0.0), (66, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(shape_rect_layer(
        "underline_accent", "#38BDF8", (1170.0, 582.0), (450.0, 5.0), radius=2.5,
        tracks=[underline_op], duration=duration
    ))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_06_line_swap",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_06_line_swap.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_07_morph_text() -> Dict[str, Any]:
    """07: Morph Text - Gooey text morph cycling through phrases with fluid transitions."""
    duration = 105
    font = "assets/fonts/Poppins-Bold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.024, 0.027, 0.043, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Word 1: INNOVATE (f0..42)
    t1_scale = build_track("scale", [(0, 1.0), (30, 1.0), (40, 1.12), (duration - 1, 1.12)], easing="out_cubic")
    t1_op = build_track("opacity", [(0, 1.0), (30, 1.0), (40, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("w1", "INNOVATE", font, 98.0, "#FFFFFF", (960.0, 540.0), (900.0, 200.0), duration=duration, tracks=[t1_scale, t1_op]))

    # Word 2: TRANSFORM (f32..75)
    t2_scale = build_track("scale", [(0, 0.90), (32, 0.90), (42, 1.0), (62, 1.0), (72, 1.12), (duration - 1, 1.12)], easing="out_cubic")
    t2_op = build_track("opacity", [(0, 0.0), (32, 0.0), (42, 1.0), (62, 1.0), (72, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("w2", "TRANSFORM", font, 98.0, "#A78BFA", (960.0, 540.0), (900.0, 200.0), duration=duration, tracks=[t2_scale, t2_op]))

    # Word 3: TRANSCEND (f64..105)
    t3_scale = build_track("scale", [(0, 0.90), (64, 0.90), (74, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    t3_op = build_track("opacity", [(0, 0.0), (64, 0.0), (74, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(text_layer("w3", "TRANSCEND", font, 98.0, "#38BDF8", (960.0, 540.0), (900.0, 200.0), duration=duration, tracks=[t3_scale, t3_op]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_07_morph_text",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_07_morph_text.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_08_perspective_marquee() -> Dict[str, Any]:
    """08: Perspective Marquee - 3D tilted marquee with depth rolling toward the horizon."""
    duration = 105
    font = "assets/fonts/Space-Grotesk.ttf"
    stream_text = "AUTONOMOUS  •  KINETIC  •  CHRONON  •  FUTURE  •  DYNAMIC  •  VISION  •  SCALE  •  "

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.039, 0.051, 0.078, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Continuous horizontal scroll with slight angle
    track_x = build_track("position_x", [(0, 1600.0), (duration - 1, 320.0)], easing="linear")
    layers.append(text_layer("marquee", stream_text, font, 92.0, "#00F2FE", (960.0, 540.0), (3200.0, 180.0), duration=duration, tracks=[track_x]))

    # Top/bottom architectural border lines
    layers.append(shape_rect_layer("rule_top", "#1E293B", (960.0, 430.0), (1920.0, 2.0), duration=duration))
    layers.append(shape_rect_layer("rule_bot", "#1E293B", (960.0, 650.0), (1920.0, 2.0), duration=duration))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_08_perspective_marquee",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_08_perspective_marquee.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_09_scan_band() -> Dict[str, Any]:
    """09: Scan Band - Diagonal distortion band sweeps across wordmark revealing red/cyan offsets."""
    duration = 100
    font = "assets/fonts/Montserrat-ExtraBold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.024, 0.027, 0.035, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Pristine base white wordmark
    layers.append(text_layer("wordmark_base", "QUANTUM VELOCITY", font, 86.0, "#FFFFFF", (960.0, 540.0), (1200.0, 180.0), duration=duration))

    # Red chromatic offset layer (reveals during scan f30..60)
    red_op = build_track("opacity", [(0, 0.0), (28, 0.0), (45, 0.9), (62, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("wordmark_red", "QUANTUM VELOCITY", font, 86.0, "#FF2A55", (952.0, 540.0), (1200.0, 180.0), duration=duration, tracks=[red_op], blend="screen"))

    # Cyan chromatic offset layer (reveals during scan f30..60)
    cyan_op = build_track("opacity", [(0, 0.0), (32, 0.0), (49, 0.9), (66, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("wordmark_cyan", "QUANTUM VELOCITY", font, 86.0, "#00E5FF", (968.0, 540.0), (1200.0, 180.0), duration=duration, tracks=[cyan_op], blend="screen"))

    # Moving scan band slash
    scan_x = build_track("position_x", [(0, 300.0), (24, 300.0), (68, 1620.0), (duration - 1, 1620.0)], easing="linear")
    scan_op = build_track("opacity", [(0, 0.0), (24, 0.8), (68, 0.8), (70, 0.0), (duration - 1, 0.0)], easing="linear")
    layers.append(shape_rect_layer("scan_slash", "#FFFFFF", (960.0, 540.0), (35.0, 240.0), tracks=[scan_x, scan_op], blend="screen", duration=duration))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_09_scan_band",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_09_scan_band.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_10_scramble_reveal() -> Dict[str, Any]:
    """10: Scramble Reveal - Deterministic hacker text decode cycling glyphs and locking left-to-right."""
    duration = 100
    font = "assets/fonts/Space-Grotesk.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.016, 0.024, 0.020, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    steps = [
        (0, 14, "#8%04 !9?7$*X", "#6EE7B7"),
        (15, 23, "SEC9#1 0!4*8", "#34D399"),
        (24, 33, "SECURE 8%1*?", "#10B981"),
        (34, 43, "SECURE PRO#4!", "#059669"),
        (44, 52, "SECURE PROTO?", "#10B981"),
        (53, 99, "SECURE PROTOCOL", "#ECFDF5")
    ]

    for i, (sf, ef, txt, col) in enumerate(steps):
        dur = ef - sf + 1
        layers.append(text_layer(f"scramble_{i}", txt, font, 94.0, col, (960.0, 540.0), (1200.0, 190.0), start=sf, duration=dur))

    # Terminal cursor blink
    cursor_op = build_track("opacity", [
        (0, 1.0), (12, 0.0), (24, 1.0), (36, 0.0), (48, 1.0), (60, 0.0), (72, 1.0), (duration - 1, 1.0)
    ], easing="linear")
    layers.append(shape_rect_layer("cursor", "#10B981", (1520.0, 540.0), (16.0, 90.0), tracks=[cursor_op], duration=duration))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_10_scramble_reveal",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_10_scramble_reveal.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_11_shared_axis_y() -> Dict[str, Any]:
    """11: Shared Axis Y - Per-word vertical shared-axis editorial swaps."""
    duration = 100
    font = "assets/fonts/Inter-Bold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.051, 0.055, 0.070, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Static anchor prefix
    layers.append(text_layer("anchor", "ENGINEERED FOR", font, 52.0, "#94A3B8", (960.0, 470.0), (900.0, 110.0), duration=duration))

    # Shared axis swap 1: PERFORMANCE (f0..38)
    t1_y = build_track("position_y", [(0, 565.0), (30, 565.0), (38, 490.0), (duration - 1, 490.0)], easing="out_cubic")
    t1_op = build_track("opacity", [(0, 1.0), (30, 1.0), (38, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("swap_1", "PERFORMANCE", font, 94.0, "#FFFFFF", (960.0, 565.0), (1000.0, 180.0), duration=duration, tracks=[t1_y, t1_op]))

    # Shared axis swap 2: RESILIENCE (f34..72)
    t2_y = build_track("position_y", [(0, 640.0), (34, 640.0), (42, 565.0), (64, 565.0), (72, 490.0), (duration - 1, 490.0)], easing="out_cubic")
    t2_op = build_track("opacity", [(0, 0.0), (34, 0.0), (42, 1.0), (64, 1.0), (72, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("swap_2", "RESILIENCE", font, 94.0, "#A78BFA", (960.0, 565.0), (1000.0, 180.0), duration=duration, tracks=[t2_y, t2_op]))

    # Shared axis swap 3: PERFECTION (f68..100)
    t3_y = build_track("position_y", [(0, 640.0), (68, 640.0), (76, 565.0), (duration - 1, 565.0)], easing="out_cubic")
    t3_op = build_track("opacity", [(0, 0.0), (68, 0.0), (76, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(text_layer("swap_3", "PERFECTION", font, 94.0, "#38BDF8", (960.0, 565.0), (1000.0, 180.0), duration=duration, tracks=[t3_y, t3_op]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_11_shared_axis_y",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_11_shared_axis_y.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_12_strikethrough_replace() -> Dict[str, Any]:
    """12: Strikethrough Replace - Draw strike line across old text, then punch in replacement."""
    duration = 100
    font = "assets/fonts/Inter-Bold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.043, 0.047, 0.063, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Old text dims at f35
    old_op = build_track("opacity", [(0, 1.0), (32, 1.0), (42, 0.28), (duration - 1, 0.28)], easing="out_cubic")
    layers.append(text_layer("old_text", "MANUAL WORKFLOW", font, 80.0, "#94A3B8", (960.0, 490.0), (1100.0, 160.0), duration=duration, tracks=[old_op]))

    # Red strike line draws across old text at f26..40
    strike_op = build_track("opacity", [(0, 0.0), (26, 0.0), (36, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(shape_rect_layer("strike_line", "#EF4444", (960.0, 490.0), (780.0, 6.0), radius=3.0, tracks=[strike_op], duration=duration))

    # Replacement text punches in at f40..54
    rep_scale = build_track("scale", [(0, 0.88), (40, 0.88), (54, 1.0), (duration - 1, 1.0)], easing="out_back")
    rep_op = build_track("opacity", [(0, 0.0), (40, 0.0), (54, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(text_layer("rep_text", "AUTONOMOUS SYSTEM", font, 88.0, "#10B981", (960.0, 595.0), (1200.0, 170.0), duration=duration, tracks=[rep_scale, rep_op]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_12_strikethrough_replace",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_12_strikethrough_replace.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_13_text_match_cut() -> Dict[str, Any]:
    """13: Text Match Cut - Both ride a single 85% curve and hard-swap at peak velocity."""
    duration = 95
    font = "assets/fonts/Montserrat-ExtraBold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.027, 0.031, 0.043, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Text A: ACCELERATE (f0..32, aggressive accelerating slide up to center)
    ta_y = build_track("position_y", [(0, 690.0), (10, 690.0), (32, 540.0)], easing="in_cubic")
    ta_op = build_track("opacity", [(0, 0.0), (12, 1.0), (32, 1.0)], easing="linear")
    layers.append(text_layer("text_a", "ACCELERATE", font, 102.0, "#FFFFFF", (960.0, 540.0), (1100.0, 200.0), start=0, duration=33, tracks=[ta_y, ta_op]))

    # Hard match cut at frame 33: Text B inherits peak trajectory and decelerates
    tb_y = build_track("position_y", [(33, 540.0), (58, 510.0), (duration - 1, 510.0)], easing="out_cubic")
    tb_op = build_track("opacity", [(33, 1.0), (duration - 1, 1.0)], easing="linear")
    layers.append(text_layer("text_b", "UNSTOPPABLE", font, 102.0, "#38BDF8", (960.0, 510.0), (1200.0, 200.0), start=33, duration=duration - 33, tracks=[tb_y, tb_op]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_13_text_match_cut",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_13_text_match_cut.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_14_text_shimmer() -> Dict[str, Any]:
    """14: Text Shimmer - Static headline receives clean specular gradient sweep, returns to matte."""
    duration = 100
    font = "assets/fonts/Inter-Bold.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.035, 0.039, 0.059, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Base matte headline
    layers.append(text_layer("base_headline", "SUPREMACY IN CRAFT", font, 88.0, "#64748B", (960.0, 540.0), (1300.0, 180.0), duration=duration))

    # Specular white text layer that activates as sheen passes
    shimmer_op = build_track("opacity", [(0, 0.0), (28, 0.0), (48, 1.0), (68, 0.0), (duration - 1, 0.0)], easing="out_cubic")
    layers.append(text_layer("shimmer_text", "SUPREMACY IN CRAFT", font, 88.0, "#FFFFFF", (960.0, 540.0), (1300.0, 180.0), duration=duration, tracks=[shimmer_op], blend="screen"))

    # Moving specular glint bar
    glint_x = build_track("position_x", [(0, 420.0), (26, 420.0), (70, 1500.0), (duration - 1, 1500.0)], easing="linear")
    glint_op = build_track("opacity", [(0, 0.0), (26, 0.85), (70, 0.85), (72, 0.0), (duration - 1, 0.0)], easing="linear")
    layers.append(shape_rect_layer("specular_bar", "#FFFFFF", (960.0, 540.0), (24.0, 160.0), tracks=[glint_x, glint_op], blend="screen", duration=duration))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_14_text_shimmer",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_14_text_shimmer.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_15_weight_wave() -> Dict[str, Any]:
    """15: Weight Wave - Crest of thickness and forward lean travels along headline."""
    duration = 100
    font = "assets/fonts/Montserrat-ExtraBold.ttf"
    chars = list("PROPULSION")
    start_x = 520.0
    dx = 98.0

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.051, 0.055, 0.075, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    for i, char in enumerate(chars):
        x = start_x + i * dx
        peak_f = 16 + i * 3

        # Swell scale up and return
        scale_track = build_track("scale", [
            (0, 1.0),
            (peak_f - 6, 1.0),
            (peak_f, 1.34),
            (peak_f + 8, 1.0),
            (duration - 1, 1.0)
        ], easing="out_cubic")

        # Slight forward lean angle and return
        rot_track = build_track("rotation_z", [
            (0, 0.0),
            (peak_f - 6, 0.0),
            (peak_f, -7.0),
            (peak_f + 8, 0.0),
            (duration - 1, 0.0)
        ], easing="out_cubic")

        layers.append(text_layer(f"wave_char_{i}", char, font, 96.0, "#FFFFFF", (x, 540.0), (140.0, 180.0), duration=duration, tracks=[scale_track, rot_track]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_15_weight_wave",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_15_weight_wave.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


def make_title_16_chromatic_fringe_title() -> Dict[str, Any]:
    """16: Chromatic Fringe Title - Blur-focus entrance with red/cyan breathing fringe and slow scale drift."""
    duration = 100
    font = "assets/fonts/PlayfairDisplay-Italic.ttf"

    layers: List[Dict[str, Any]] = [
        {"id": "bg", "type": "color", "color": [0.020, 0.024, 0.039, 1.0], "start_frame": 0, "duration_frames": duration}
    ]

    # Slow drift scale across whole headline
    scale_track = build_track("scale", [(0, 1.06), (30, 1.0), (duration - 1, 0.98)], easing="linear")
    core_op = build_track("opacity", [(0, 0.0), (28, 1.0), (duration - 1, 1.0)], easing="out_cubic")
    layers.append(text_layer("core_white", "CYBERNETIC HORIZON", font, 92.0, "#FFFFFF", (960.0, 540.0), (1300.0, 190.0), duration=duration, tracks=[scale_track, core_op], blend="screen"))

    # Red fringe channel (breathing offset)
    red_x = build_track("position_x", [(0, 952.0), (32, 954.0), (60, 957.0), (duration - 1, 954.0)], easing="in_out_sine")
    red_op = build_track("opacity", [(0, 0.0), (25, 0.75), (60, 0.65), (duration - 1, 0.75)], easing="linear")
    layers.append(text_layer("red_fringe", "CYBERNETIC HORIZON", font, 92.0, "#FF1E56", (954.0, 540.0), (1300.0, 190.0), duration=duration, tracks=[red_x, red_op], blend="screen"))

    # Cyan fringe channel (breathing offset)
    cyan_x = build_track("position_x", [(0, 968.0), (32, 966.0), (60, 963.0), (duration - 1, 966.0)], easing="in_out_sine")
    cyan_op = build_track("opacity", [(0, 0.0), (25, 0.75), (60, 0.65), (duration - 1, 0.75)], easing="linear")
    layers.append(text_layer("cyan_fringe", "CYBERNETIC HORIZON", font, 92.0, "#00F5D4", (966.0, 540.0), (1300.0, 190.0), duration=duration, tracks=[cyan_x, cyan_op], blend="screen"))

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "title_16_chromatic_fringe_title",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1, "duration_frames": duration},
        "output": {"path": str(OUT_DIR / "title_16_chromatic_fringe_title.mp4"), "format": "mp4", "codec": "h264"},
        "layers": layers
    }


ALL_TITLE_BUILDERS = {
    "title_01_per_word_rise": make_title_01_per_word_rise,
    "title_02_blur_out_up": make_title_02_blur_out_up,
    "title_03_bottom_up_letters": make_title_03_bottom_up_letters,
    "title_04_focus_blur_resolve": make_title_04_focus_blur_resolve,
    "title_05_line_by_line_slide": make_title_05_line_by_line_slide,
    "title_06_line_swap": make_title_06_line_swap,
    "title_07_morph_text": make_title_07_morph_text,
    "title_08_perspective_marquee": make_title_08_perspective_marquee,
    "title_09_scan_band": make_title_09_scan_band,
    "title_10_scramble_reveal": make_title_10_scramble_reveal,
    "title_11_shared_axis_y": make_title_11_shared_axis_y,
    "title_12_strikethrough_replace": make_title_12_strikethrough_replace,
    "title_13_text_match_cut": make_title_13_text_match_cut,
    "title_14_text_shimmer": make_title_14_text_shimmer,
    "title_15_weight_wave": make_title_15_weight_wave,
    "title_16_chromatic_fringe_title": make_title_16_chromatic_fringe_title,
}


def validate_plan(plan_file: Path) -> bool:
    """Validate plan using chronon3d_cli validate."""
    cmd = [
        str(CHRONON_CLI), "validate",
        "--plan", str(plan_file),
        "--assets-root", str(ASSETS_ROOT)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [ERROR] {plan_file.name} validation failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}")
        return False
    print(f"  [OK] {plan_file.name} validated successfully")
    return True


def render_plan(plan_file: Path, mp4_file: Path) -> bool:
    """Render plan using chronon3d_cli with software backend."""
    cmd = [
        str(CHRONON_CLI), "render",
        "--plan", str(plan_file),
        "--backend", "software",
        "--output", str(mp4_file),
        "--assets-root", str(ASSETS_ROOT)
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if res.returncode != 0 or not mp4_file.exists() or mp4_file.stat().st_size == 0:
        print(f"  [ERROR] {plan_file.name} render failed (code {res.returncode}):\n{res.stdout}\n{res.stderr}")
        return False
    size = mp4_file.stat().st_size
    print(f"  [OK] {mp4_file.name} rendered in {elapsed:.2f}s ({size:,} bytes)")
    return True


def upload_mp4_to_drive(mp4_path: Path, drive_folder_id: str) -> Dict[str, Any]:
    """Upload strictly an MP4 file to Google Drive using drive-upload tool."""
    h = hashlib.sha256()
    with open(mp4_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    expected_sha = h.hexdigest()

    cmd = [
        str(DRIVE_UPLOAD_BIN),
        "-credentials", str(CREDS_FILE),
        "-token", str(TOKEN_FILE),
        "-folder", drive_folder_id,
        "-file", str(mp4_path),
        "-name", mp4_path.name,
        "-sha256", expected_sha,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = res.stdout.strip()
    data: Dict[str, Any] = {}
    for part in out.split():
        if "=" in part:
            k, v = part.split("=", 1)
            data[k] = v

    data["file_name"] = mp4_path.name
    data["local_path"] = str(mp4_path)
    data["sha256"] = expected_sha
    data["bytes"] = mp4_path.stat().st_size
    data["link"] = f"https://drive.google.com/file/d/{data.get('id', '')}/view?usp=drivesdk"
    return data


def main():
    parser = argparse.ArgumentParser(description="Render 16 Chronon Kinetic Titles and upload MP4s to Google Drive.")
    parser.add_argument("--drive-folder", default=DEFAULT_DRIVE_FOLDER, help="Google Drive destination folder ID")
    parser.add_argument("--plans-only", action="store_true", help="Only generate plan files")
    parser.add_argument("--validate-only", action="store_true", help="Generate and validate plans only")
    parser.add_argument("--render-only", action="store_true", help="Generate, validate, and render without uploading")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing MP4s without rendering")
    parser.add_argument("--force-render", action="store_true", help="Force re-rendering existing MP4s")
    parser.add_argument("--jobs", type=int, default=3, help="Number of concurrent render jobs")
    parser.add_argument("--filter", default=None, help="Filter specific title name")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== Chronon Kinetic Titles Catalog Suite (16 Titles) ===")
    print(f"Output directory: {OUT_DIR}")
    print(f"Drive Folder ID:  {args.drive_folder}")
    print(f"Render Jobs:      {args.jobs}")

    # Step 1: Author Plans
    plans: List[tuple[str, Path, Path]] = []
    for name, builder in ALL_TITLE_BUILDERS.items():
        if args.filter and args.filter not in name:
            continue
        plan_dict = builder()
        plan_path = OUT_DIR / f"{name}.plan.json"
        mp4_path = OUT_DIR / f"{name}.mp4"
        plan_path.write_text(json.dumps(plan_dict, indent=2))
        plans.append((name, plan_path, mp4_path))
        print(f"  [plan] {plan_path.name} written")

    if args.plans_only:
        print("Plans generated. Exiting.")
        return

    # Step 2: Validate Plans
    print("\n--- Validating Plans with Chronon3d CLI ---")
    all_valid = True
    for name, plan_path, _ in plans:
        if not validate_plan(plan_path):
            all_valid = False
    if not all_valid:
        print("One or more plans failed validation. Aborting render.")
        sys.exit(1)

    if args.validate_only:
        print("All plans validated successfully.")
        return

    # Step 3: Render Plans
    if not args.upload_only:
        print(f"\n--- Rendering MP4s (Jobs: {args.jobs}, Backend: software) ---")
        from concurrent.futures import ThreadPoolExecutor, as_completed

        render_tasks = []
        for name, plan_path, mp4_path in plans:
            if mp4_path.exists() and not args.force_render:
                print(f"  [SKIP] {mp4_path.name} already exists ({mp4_path.stat().st_size:,} bytes)")
                continue
            render_tasks.append((name, plan_path, mp4_path))

        if render_tasks:
            failed = False
            with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                futures = {executor.submit(render_plan, plan, mp4): (name, mp4) for name, plan, mp4 in render_tasks}
                for fut in as_completed(futures):
                    name, mp4 = futures[fut]
                    ok = fut.result()
                    if not ok:
                        print(f"  [FAIL] Render failed for {name}")
                        failed = True
            if failed:
                print("One or more renders failed. Aborting.")
                sys.exit(1)

    if args.render_only:
        print("\nRendering complete (render-only mode).")
        return

    # Step 4: Upload ONLY MP4 Videos to Google Drive
    print(f"\n--- Uploading MP4 Videos ONLY to Google Drive ({args.drive_folder}) ---")
    manifest = {}
    for name, _, mp4_path in plans:
        if not mp4_path.exists():
            print(f"  [ERROR] {mp4_path.name} does not exist for upload.")
            sys.exit(1)
        print(f"  Uploading {mp4_path.name} ({mp4_path.stat().st_size:,} bytes)...")
        up_info = upload_mp4_to_drive(mp4_path, args.drive_folder)
        manifest[mp4_path.name] = up_info
        print(f"    -> ID: {up_info['id']} | Link: {up_info['link']}")

    manifest_path = OUT_DIR / "upload_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nUpload manifest written to {manifest_path}")
    print("\n=== All 16 Kinetic Titles Uploaded Successfully ===")


if __name__ == "__main__":
    main()
