#!/usr/bin/env python3
"""
Generate a complete, high-end suite of 12 Web Cursor Motion Animations
for Chronon3D with Vulkan GPU acceleration.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import ImageFont

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "cursor_animations"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_POPPINS_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_INTER_BOLD = "assets/fonts/Inter-Bold.ttf"

def get_pil_font(font_rel_path: str, size: int) -> ImageFont.FreeTypeFont:
    abs_path = BASE_DIR / "Chronon3d" / font_rel_path
    return ImageFont.truetype(str(abs_path), int(size))

def make_bg(color: list[float], duration: int) -> dict:
    return {
        "id": "background",
        "type": "color",
        "color": color,
        "start_frame": 0,
        "duration_frames": duration
    }

# -------------------------------------------------------------------------
# SCENE 01: Ultra-Thin Modern Web Caret (2.5px Electric Cyan)
# Minimal SaaS hero header with fine hairline caret gliding smoothly
# -------------------------------------------------------------------------
def build_scene_01(dur=85):
    font = get_pil_font(FONT_POPPINS_BOLD, 74)
    w1, w2 = font.getlength("Engineered"), font.getlength("for Speed")
    gap = 26.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    # Timeline:
    # 0..10: Initial caret blink
    # 12: Word 1 appears
    # 12..30: Caret glides to end of word 1
    # 30..42: Brief pause & blink
    # 44: Word 2 appears
    # 44..62: Caret glides to end of word 2
    # 62..75: Settled breathing blink
    # 75..84: Whip exit
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 10, "value": st_x},
        {"frame": 28, "value": st_x + w1 + 6.0},
        {"frame": 42, "value": st_x + w1 + 6.0},
        {"frame": 60, "value": st_x + tot_w + 6.0},
        {"frame": 75, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    opacity_kfs = []
    for f in range(dur):
        if f >= 75:
            op = 0.0
        elif (10 <= f <= 28) or (42 <= f <= 60):
            op = 1.0  # solid while moving/typing
        else:
            op = 1.0 if (f // 5) % 2 == 0 else 0.0
        opacity_kfs.append({"frame": f, "value": op})
        
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_01",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            # Category label
            {
                "id": "label", "type": "text", "text": "01 / MINIMAL CARET", "size": [400, 50],
                "position": [960, 380, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#00F0FF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 1
            {
                "id": "t1", "type": "text", "text": "Engineered", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 74.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 12, "value": 40.0}, {"frame": 22, "value": 0.0}, {"frame": 75, "value": 0.0}, {"frame": dur - 1, "value": -200.0}]}
                ]}
            },
            # Word 2
            {
                "id": "t2", "type": "text", "text": "for Speed", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 74.0, "fill": "#00F0FF", "glow": {"radius": 24.0, "intensity": 0.7, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 44, "value": 0.0}, {"frame": 50, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 44, "value": 40.0}, {"frame": 54, "value": 0.0}, {"frame": 75, "value": 0.0}, {"frame": dur - 1, "value": -200.0}]}
                ]}
            },
            # Caret
            {
                "id": "caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 1.2, "fill": [0.0, 0.94, 1.0, 1.0]},
                "size": [2.8, 70.0], "position": [st_x, y - 35.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "hold", "keyframes": opacity_kfs}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_01.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 02: Chunky Terminal Block Cursor (34px Phosphor Green █)
# Retro dev CLI prompt with mechanical hold-step typing
# -------------------------------------------------------------------------
def build_scene_02(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 60)
    prompt = "> chronon"
    arg1 = "init"
    arg2 = "--gpu-vulkan"
    
    w_p = font.getlength(prompt)
    w_a1 = font.getlength(arg1)
    w_a2 = font.getlength(arg2)
    gap = 20.0
    tot_w = w_p + gap + w_a1 + gap + w_a2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 10, "value": st_x},
        {"frame": 18, "value": st_x + w_p + 4.0},
        {"frame": 32, "value": st_x + w_p + 4.0},
        {"frame": 40, "value": st_x + w_p + gap + w_a1 + 4.0},
        {"frame": 52, "value": st_x + w_p + gap + w_a1 + 4.0},
        {"frame": 64, "value": st_x + tot_w + 4.0},
        {"frame": 80, "value": st_x + tot_w + 4.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    opacity_kfs = []
    for f in range(dur):
        if f >= 80:
            op = 0.0
        elif (10 <= f <= 18) or (32 <= f <= 40) or (52 <= f <= 64):
            op = 1.0
        else:
            op = 1.0 if (f // 6) % 2 == 0 else 0.0
        opacity_kfs.append({"frame": f, "value": op})
        
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_02",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.02, 0.04, 0.03, 1.0], dur),
            # Terminal Window Card Frame
            {
                "id": "term_frame", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 24.0, "fill": [0.04, 0.08, 0.06, 0.95]},
                "size": [tot_w + 140.0, 240.0], "position": [960.0 - (tot_w + 140.0)/2.0, y - 120.0],
                "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Traffic Light: Red
            {
                "id": "dot_red", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 7.0, "fill": [0.95, 0.3, 0.3, 1.0]},
                "size": [14.0, 14.0], "position": [960.0 - (tot_w + 140.0)/2.0 + 30.0, y - 85.0],
                "start_frame": 0, "duration_frames": dur
            },
            # Traffic Light: Yellow
            {
                "id": "dot_yellow", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 7.0, "fill": [0.95, 0.8, 0.2, 1.0]},
                "size": [14.0, 14.0], "position": [960.0 - (tot_w + 140.0)/2.0 + 52.0, y - 85.0],
                "start_frame": 0, "duration_frames": dur
            },
            # Traffic Light: Green
            {
                "id": "dot_green", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 7.0, "fill": [0.2, 0.85, 0.4, 1.0]},
                "size": [14.0, 14.0], "position": [960.0 - (tot_w + 140.0)/2.0 + 74.0, y - 85.0],
                "start_frame": 0, "duration_frames": dur
            },
            # Prompt text
            {
                "id": "t_prompt", "type": "text", "text": prompt, "size": [w_p + 10, 110],
                "position": [st_x + w_p / 2.0, y + 10.0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 60.0, "fill": "#4ADE80", "glow": {"radius": 22.0, "intensity": 0.6, "color": "#22C55E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Arg 1
            {
                "id": "t_a1", "type": "text", "text": arg1, "size": [w_a1 + 10, 110],
                "position": [st_x + w_p + gap + w_a1 / 2.0, y + 10.0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 60.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 36, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Arg 2
            {
                "id": "t_a2", "type": "text", "text": arg2, "size": [w_a2 + 10, 110],
                "position": [st_x + w_p + gap + w_a1 + gap + w_a2 / 2.0, y + 10.0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 60.0, "fill": "#F59E0B", "glow": {"radius": 20.0, "intensity": 0.5, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 58, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Chunky Block Caret
            {
                "id": "caret_block", "type": "shape",
                "shape": {"type": "rect", "fill": [0.13, 0.77, 0.37, 1.0]},
                "size": [34.0, 64.0], "position": [st_x, y - 22.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "hold", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "hold", "keyframes": opacity_kfs}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_02.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 03: Dynamic Color-Shifting Caret (Cyan -> Violet -> Hot Pink)
# Seamless color transition cross-fade synced to keyword typing
# -------------------------------------------------------------------------
def build_scene_03(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 70)
    w1, w2, w3 = font.getlength("Design."), font.getlength("Code."), font.getlength("Deploy.")
    gap = 28.0
    tot_w = w1 + gap + w2 + gap + w3
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 10, "value": st_x},
        {"frame": 24, "value": st_x + w1 + 6.0},
        {"frame": 36, "value": st_x + w1 + 6.0},
        {"frame": 50, "value": st_x + w1 + gap + w2 + 6.0},
        {"frame": 60, "value": st_x + w1 + gap + w2 + 6.0},
        {"frame": 72, "value": st_x + tot_w + 6.0},
        {"frame": 80, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_03",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.025, 0.038, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "03 / RGB COLOR SHIFT", "size": [400, 50],
                "position": [960, 380, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#A855F7", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#A855F7"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 1: Design (Cyan)
            {
                "id": "w1", "type": "text", "text": "Design.", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#00F0FF", "glow": {"radius": 22.0, "intensity": 0.6, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 12, "value": [0.6, 0.6, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            # Word 2: Code (Purple)
            {
                "id": "w2", "type": "text", "text": "Code.", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#A855F7", "glow": {"radius": 22.0, "intensity": 0.6, "color": "#A855F7"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 38, "value": 0.0}, {"frame": 44, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 38, "value": [0.6, 0.6, 1.0]}, {"frame": 48, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            # Word 3: Deploy (Pink)
            {
                "id": "w3", "type": "text", "text": "Deploy.", "size": [w3 + 10, 130],
                "position": [st_x + w1 + gap + w2 + gap + w3 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#F43F5E", "glow": {"radius": 22.0, "intensity": 0.7, "color": "#F43F5E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 62, "value": 0.0}, {"frame": 68, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 62, "value": [0.6, 0.6, 1.0]}, {"frame": 72, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            # Layer A: Cyan Caret
            {
                "id": "caret_cyan", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 3.0, "fill": [0.0, 0.94, 1.0, 1.0]},
                "size": [6.0, 68.0], "position": [st_x, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "in_out_quad", "keyframes": [{"frame": 0, "value": 1.0}, {"frame": 28, "value": 1.0}, {"frame": 40, "value": 0.0}]}
                ]}
            },
            # Layer B: Purple Caret
            {
                "id": "caret_purple", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 3.0, "fill": [0.65, 0.35, 0.98, 1.0]},
                "size": [6.0, 68.0], "position": [st_x, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "in_out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 28, "value": 0.0}, {"frame": 40, "value": 1.0}, {"frame": 52, "value": 1.0}, {"frame": 64, "value": 0.0}]}
                ]}
            },
            # Layer C: Pink Caret
            {
                "id": "caret_pink", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 3.0, "fill": [0.96, 0.22, 0.62, 1.0]},
                "size": [6.0, 68.0], "position": [st_x, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "in_out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 52, "value": 0.0}, {"frame": 64, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_03.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 04: Dynamic Thickness Morph (Fine 2.5px -> Fat 14px -> Solid Block 38px)
# Real-time animated scale_x dynamic thickness alteration
# -------------------------------------------------------------------------
def build_scene_04(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 70)
    w1, w2, w3 = font.getlength("Adaptive"), font.getlength("Stroke"), font.getlength("Weight")
    gap = 26.0
    tot_w = w1 + gap + w2 + gap + w3
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 10, "value": st_x},
        {"frame": 24, "value": st_x + w1 + 6.0},
        {"frame": 38, "value": st_x + w1 + 6.0},
        {"frame": 50, "value": st_x + w1 + gap + w2 + 6.0},
        {"frame": 62, "value": st_x + w1 + gap + w2 + 6.0},
        {"frame": 74, "value": st_x + tot_w + 6.0},
        {"frame": 80, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    # Scale_x starts at 0.25 (2.5px), expands to 1.4 (14px), then 3.8 (38px)
    scale_x_kfs = [
        {"frame": 0, "value": 0.25},
        {"frame": 28, "value": 0.25},
        {"frame": 38, "value": 1.4},   # Morph to fat bar
        {"frame": 54, "value": 1.4},
        {"frame": 64, "value": 3.8},   # Morph to solid block
        {"frame": dur - 1, "value": 3.8}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_04",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.04, 0.04, 0.06, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "04 / DYNAMIC THICKNESS MORPH", "size": [500, 50],
                "position": [960, 380, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#F59E0B", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 1
            {
                "id": "w1", "type": "text", "text": "Adaptive", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 2
            {
                "id": "w2", "type": "text", "text": "Stroke", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 40, "value": 0.0}, {"frame": 46, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 3
            {
                "id": "w3", "type": "text", "text": "Weight", "size": [w3 + 10, 130],
                "position": [st_x + w1 + gap + w2 + gap + w3 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#F59E0B", "glow": {"radius": 24.0, "intensity": 0.8, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": 70, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Morphing Caret
            {
                "id": "caret_morph", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.5, "fill": [0.96, 0.62, 0.04, 1.0]},
                "size": [10.0, 68.0], "position": [st_x, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "scale_x", "easing": "out_back", "keyframes": scale_x_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_04.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 05: Selection Highlight Morph (Caret Expands into Keyword Selection Pill)
# Caret types phrase, then stretches horizontally into semi-transparent selection capsule
# -------------------------------------------------------------------------
def build_scene_05(dur=95):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2 = font.getlength("Select the"), font.getlength("Extraordinary")
    gap = 26.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 8, "value": st_x},
        {"frame": 22, "value": st_x + w1 + 6.0},
        {"frame": 30, "value": st_x + w1 + 6.0},
        {"frame": 46, "value": st_x + tot_w + 6.0},
        {"frame": 80, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    # Word 2 selection highlight capsule
    w2_x = st_x + w1 + gap
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_05",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "05 / SELECTION HIGHLIGHT MORPH", "size": [500, 50],
                "position": [960, 370, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#3B82F6", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#3B82F6"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Selection Highlight Shape Layer (behind Word 2)
            {
                "id": "selection_pill", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 14.0, "fill": [0.23, 0.51, 0.96, 0.35]},
                "size": [w2 + 28.0, 92.0], "position": [w2_x - 14.0, y - 46.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale_x", "easing": "out_back", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 52, "value": 0.0}, {"frame": 66, "value": 1.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 52, "value": 0.0}, {"frame": 58, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 1
            {
                "id": "w1", "type": "text", "text": "Select the", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 2
            {
                "id": "w2", "type": "text", "text": "Extraordinary", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 24.0, "intensity": 0.6, "color": "#3B82F6"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 32, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Blinking / Snapping Caret
            {
                "id": "caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.23, 0.51, 0.96, 1.0]},
                "size": [4.0, 72.0], "position": [st_x, y - 36.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "hold", "keyframes": [
                        {"frame": 0, "value": 1.0}, {"frame": 52, "value": 1.0}, {"frame": 66, "value": 0.0}, {"frame": 75, "value": 1.0}, {"frame": 80, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_05.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 06: Figma Collaborative Pointer & User Tag ([Pierone] Royal Violet)
# Multiplayer design tool pointer swooping over glass UI card with native badge
# -------------------------------------------------------------------------
def build_scene_06(dur=90):
    card_w, card_h = 520.0, 240.0
    card_x, card_y = 960.0 - card_w / 2.0, 540.0 - card_h / 2.0
    
    ptr_kfs_x = [
        {"frame": 0, "value": 1500.0},
        {"frame": 28, "value": 940.0},
        {"frame": 42, "value": 940.0},
        {"frame": 70, "value": 1040.0},
        {"frame": dur - 1, "value": 300.0}
    ]
    ptr_kfs_y = [
        {"frame": 0, "value": 200.0},
        {"frame": 28, "value": 520.0},
        {"frame": 42, "value": 520.0},
        {"frame": 70, "value": 480.0},
        {"frame": dur - 1, "value": 950.0}
    ]
    
    click_scale = [
        {"frame": 0, "value": [1.0, 1.0, 1.0]},
        {"frame": 36, "value": [1.0, 1.0, 1.0]},
        {"frame": 40, "value": [0.80, 0.80, 1.0]},
        {"frame": 46, "value": [1.14, 1.14, 1.0]},
        {"frame": 52, "value": [1.0, 1.0, 1.0]}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_06",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.035, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "06 / COLLABORATIVE MULTIPLAYER", "size": [500, 50],
                "position": [960, 330, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#A855F7", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#A855F7"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Glass UI Card Frame
            {
                "id": "card_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 24.0, "fill": [0.08, 0.09, 0.15, 0.95]},
                "size": [card_w, card_h], "position": [card_x, card_y], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.7, 0.7, 1.0]}, {"frame": 20, "value": [1.0, 1.0, 1.0]},
                        {"frame": 40, "value": [0.96, 0.96, 1.0]}, {"frame": 46, "value": [1.05, 1.05, 1.0]}, {"frame": 52, "value": [1.0, 1.0, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Card Header Title
            {
                "id": "card_title", "type": "text", "text": "Hero Section [v2.4]", "size": [440, 60],
                "position": [960, 510, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 36.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Card Status Pill
            {
                "id": "status_pill", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 14.0, "fill": [0.65, 0.35, 0.98, 0.25]},
                "size": [190.0, 36.0], "position": [960.0 - 95.0, 560.0 - 18.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "status_txt", "type": "text", "text": "Live Editing", "size": [180, 30],
                "position": [960, 560, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 18.0, "fill": "#C084FC"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 20, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Pointer Arrow Head (Sleek capsule pointer)
            {
                "id": "ptr_head", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 6.0, "fill": [0.65, 0.35, 0.98, 1.0]},
                "size": [14.0, 26.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": ptr_kfs_x},
                    {"property": "position_y", "easing": "out_expo", "keyframes": ptr_kfs_y},
                    {"property": "scale", "easing": "out_back", "keyframes": click_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # User Badge Pill ([Pierone])
            {
                "id": "user_badge_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [0.65, 0.35, 0.98, 0.95]},
                "size": [120.0, 36.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 20.0} for k in ptr_kfs_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 16.0} for k in ptr_kfs_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "user_badge_txt", "type": "text", "text": "Pierone", "size": [110, 30],
                "position": [0, 0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 20.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 80.0} for k in ptr_kfs_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 34.0} for k in ptr_kfs_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_06.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 07: Magnetic Floating Dot Cursor (Awwwards Web Agency Style)
# Minimal floating trailing dot that locks magnetically to interactive button
# -------------------------------------------------------------------------
def build_scene_07(dur=90):
    btn_w, btn_h = 320.0, 76.0
    btn_x, btn_y = 960.0 - btn_w / 2.0, 540.0 - btn_h / 2.0
    
    # Dot trajectory: wanders from left, snaps magnetically to button center
    dot_x_kfs = [
        {"frame": 0, "value": 400.0},
        {"frame": 18, "value": 720.0},
        {"frame": 35, "value": 960.0},
        {"frame": 68, "value": 960.0},
        {"frame": dur - 1, "value": 1500.0}
    ]
    dot_y_kfs = [
        {"frame": 0, "value": 700.0},
        {"frame": 18, "value": 620.0},
        {"frame": 35, "value": 540.0},
        {"frame": 68, "value": 540.0},
        {"frame": dur - 1, "value": 300.0}
    ]
    
    # Scale: small dot (12px) expands to 110px magnetic ring around button!
    dot_scale = [
        {"frame": 0, "value": [1.0, 1.0, 1.0]},
        {"frame": 28, "value": [1.0, 1.0, 1.0]},
        {"frame": 38, "value": [6.5, 6.5, 1.0]},
        {"frame": 65, "value": [6.5, 6.5, 1.0]},
        {"frame": 74, "value": [1.0, 1.0, 1.0]}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_07",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.025, 0.035, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "07 / MAGNETIC DOT HOVER", "size": [500, 50],
                "position": [960, 370, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#FFFFFF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Interactive Button Base
            {
                "id": "btn", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 38.0, "fill": [0.08, 0.09, 0.14, 0.9]},
                "size": [btn_w, btn_h], "position": [btn_x, btn_y], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.8, 0.8, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]},
                        {"frame": 36, "value": [1.08, 1.08, 1.0]}, {"frame": 66, "value": [1.08, 1.08, 1.0]}, {"frame": 75, "value": [1.0, 1.0, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Button Text
            {
                "id": "btn_txt", "type": "text", "text": "Explore Work >", "size": [280, 50],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 28.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Magnetic Dot Cursor
            {
                "id": "mag_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [1.0, 1.0, 1.0, 0.85]},
                "size": [16.0, 16.0], "position": [400.0, 700.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": dot_x_kfs},
                    {"property": "position_y", "easing": "out_expo", "keyframes": dot_y_kfs},
                    {"property": "scale", "easing": "out_back", "keyframes": dot_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 0.9}, {"frame": 36, "value": 0.25}, {"frame": 66, "value": 0.25}, {"frame": 74, "value": 0.9}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_07.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 08: Code Editor / IDE Caret with Autocomplete Popup
# Modern AI Code Editor interface with instant tab completion
# -------------------------------------------------------------------------
def build_scene_08(dur=95):
    font = get_pil_font(FONT_POPPINS_BOLD, 54)
    code_p1 = "const pipeline ="
    code_p2 = "useGPU();"
    w1, w2 = font.getlength(code_p1), font.getlength(code_p2)
    gap = 18.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 500.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 8, "value": st_x},
        {"frame": 24, "value": st_x + w1 + 6.0},
        {"frame": 48, "value": st_x + w1 + 6.0},
        {"frame": 60, "value": st_x + tot_w + 6.0},
        {"frame": 80, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_08",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.02, 0.03, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "08 / IDE AUTOCOMPLETE CARET", "size": [500, 50],
                "position": [960, 330, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#38BDF8", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#38BDF8"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Code Part 1
            {
                "id": "c1", "type": "text", "text": code_p1, "size": [w1 + 10, 100],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 54.0, "fill": "#E2E8F0"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Autocomplete Suggestion Dropdown Pill
            {
                "id": "ac_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 12.0, "fill": [0.08, 0.12, 0.20, 0.95]},
                "size": [360.0, 56.0], "position": [st_x + w1 + 10.0, y + 54.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.6, 0.6, 1.0]}, {"frame": 28, "value": [0.6, 0.6, 1.0]}, {"frame": 36, "value": [1.0, 1.0, 1.0]}, {"frame": 52, "value": [1.0, 1.0, 1.0]}, {"frame": 56, "value": [0.0, 0.0, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 28, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 52, "value": 1.0}, {"frame": 56, "value": 0.0}
                    ]}
                ]}
            },
            # Autocomplete Text
            {
                "id": "ac_txt", "type": "text", "text": "> useGPU() [Tab]", "size": [340, 40],
                "position": [st_x + w1 + 190.0, y + 82.0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 22.0, "fill": "#38BDF8"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 28, "value": 0.0}, {"frame": 36, "value": 1.0}, {"frame": 52, "value": 1.0}, {"frame": 56, "value": 0.0}
                    ]}
                ]}
            },
            # Code Part 2 (Accepted Completion)
            {
                "id": "c2", "type": "text", "text": code_p2, "size": [w2 + 10, 100],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 54.0, "fill": "#38BDF8", "glow": {"radius": 22.0, "intensity": 0.7, "color": "#38BDF8"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 54, "value": 0.0}, {"frame": 58, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 54, "value": [0.7, 0.7, 1.0]}, {"frame": 62, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            # Caret
            {
                "id": "caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.22, 0.74, 0.97, 1.0]},
                "size": [4.0, 56.0], "position": [st_x, y - 28.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "hold", "keyframes": [
                        {"frame": 0, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_08.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 09: Capsule Pill Caret (Smooth Amber Floating Inertia)
# Fully rounded capsule pill cursor gliding with subtle inertial tilt
# -------------------------------------------------------------------------
def build_scene_09(dur=85):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2 = font.getlength("Global Liquid"), font.getlength("Capital")
    gap = 26.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 10, "value": st_x},
        {"frame": 28, "value": st_x + w1 + 8.0},
        {"frame": 40, "value": st_x + w1 + 8.0},
        {"frame": 58, "value": st_x + tot_w + 8.0},
        {"frame": 75, "value": st_x + tot_w + 8.0},
        {"frame": dur - 1, "value": st_x + tot_w + 900.0}
    ]
    
    tilt_kfs = [
        {"frame": 0, "value": 0.0},
        {"frame": 12, "value": 6.0},
        {"frame": 28, "value": 0.0},
        {"frame": 42, "value": 6.0},
        {"frame": 58, "value": 0.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_09",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "09 / CAPSULE PILL CARET", "size": [500, 50],
                "position": [960, 370, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#F59E0B", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 1
            {
                "id": "w1", "type": "text", "text": "Global Liquid", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Word 2
            {
                "id": "w2", "type": "text", "text": "Capital", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#F59E0B", "glow": {"radius": 24.0, "intensity": 0.7, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 42, "value": 0.0}, {"frame": 48, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Capsule Pill Caret
            {
                "id": "caret_pill", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 7.0, "fill": [0.96, 0.62, 0.04, 1.0]},
                "size": [14.0, 70.0], "position": [st_x, y - 35.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 75, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_09.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 10: Interactive Web Pointer with Click Wave
# Pointer sweeps in, clicks button, and triggers expanding circular shockwave
# -------------------------------------------------------------------------
def build_scene_10(dur=90):
    btn_w, btn_h = 360.0, 84.0
    btn_x, btn_y = 960.0 - btn_w / 2.0, 540.0 - btn_h / 2.0
    
    ptr_kfs_x = [
        {"frame": 0, "value": 450.0},
        {"frame": 30, "value": 960.0},
        {"frame": 65, "value": 960.0},
        {"frame": dur - 1, "value": 1600.0}
    ]
    ptr_kfs_y = [
        {"frame": 0, "value": 850.0},
        {"frame": 30, "value": 540.0},
        {"frame": 65, "value": 540.0},
        {"frame": dur - 1, "value": 200.0}
    ]
    
    click_scale = [
        {"frame": 0, "value": [1.0, 1.0, 1.0]},
        {"frame": 36, "value": [1.0, 1.0, 1.0]},
        {"frame": 40, "value": [0.75, 0.75, 1.0]},
        {"frame": 46, "value": [1.15, 1.15, 1.0]},
        {"frame": 52, "value": [1.0, 1.0, 1.0]}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_10",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "10 / CLICK RIPPLE INTERACTION", "size": [500, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#00F0FF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Click Ripple Wave (expands on frame 40)
            {
                "id": "ripple", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 75.0, "fill": [0.0, 0.94, 1.0, 0.45]},
                "size": [150.0, 150.0], "position": [960.0 - 75.0, 540.0 - 75.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_expo", "keyframes": [
                        {"frame": 0, "value": [0.1, 0.1, 1.0]}, {"frame": 39, "value": [0.1, 0.1, 1.0]}, {"frame": 58, "value": [2.4, 2.4, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 39, "value": 0.85}, {"frame": 58, "value": 0.0}
                    ]}
                ]}
            },
            # Button Base
            {
                "id": "btn", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 42.0, "fill": [0.0, 0.72, 0.96, 0.95]},
                "size": [btn_w, btn_h], "position": [btn_x, btn_y], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.7, 0.7, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]},
                        {"frame": 40, "value": [0.93, 0.93, 1.0]}, {"frame": 46, "value": [1.07, 1.07, 1.0]}, {"frame": 52, "value": [1.0, 1.0, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Button Text
            {
                "id": "btn_txt", "type": "text", "text": "Launch Project >", "size": [320, 50],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 30.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Native Pointer Indicator (Wedge pointer)
            {
                "id": "ptr_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 12.0, "fill": [1.0, 1.0, 1.0, 0.95]},
                "size": [24.0, 24.0], "position": [450.0 - 12.0, 850.0 - 12.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 12.0} for k in ptr_kfs_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 12.0} for k in ptr_kfs_y]},
                    {"property": "scale", "easing": "out_back", "keyframes": click_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_10.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 11: Seamless Shape Shift (Dot Pointer Morphs into Text Caret)
# Pointer glides over search field, clicks, and seamlessly transforms into caret
# -------------------------------------------------------------------------
def build_scene_11(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 56)
    query = "Vulkan GPU Architecture"
    w_q = font.getlength(query)
    box_w, box_h = 760.0, 90.0
    box_x, box_y = 960.0 - box_w / 2.0, 540.0 - box_h / 2.0
    text_st_x = box_x + 40.0
    
    caret_kfs = [
        {"frame": 0, "value": text_st_x},
        {"frame": 36, "value": text_st_x},
        {"frame": 56, "value": text_st_x + w_q + 6.0},
        {"frame": 75, "value": text_st_x + w_q + 6.0},
        {"frame": dur - 1, "value": text_st_x + w_q + 900.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_11",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "11 / POINTER TO CARET MORPH", "size": [500, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#EC4899", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#EC4899"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Search Box Frame
            {
                "id": "search_box", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 22.0, "fill": [0.08, 0.09, 0.14, 0.95]},
                "size": [box_w, box_h], "position": [box_x, box_y], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.8, 0.8, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Search Query Text
            {
                "id": "query_txt", "type": "text", "text": query, "size": [w_q + 10, 80],
                "position": [text_st_x + w_q / 2.0, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 56.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 36, "value": 0.0}, {"frame": 42, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            },
            # Pointer Dot (fades out at frame 32 as it morphs into caret)
            {
                "id": "ptr_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 10.0, "fill": [0.96, 0.22, 0.62, 1.0]},
                "size": [20.0, 20.0], "position": [500, 700], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": 0, "value": 500.0}, {"frame": 28, "value": text_st_x}]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": 0, "value": 700.0}, {"frame": 28, "value": 540.0 - 10.0}]},
                    {"property": "opacity", "easing": "in_out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 26, "value": 1.0}, {"frame": 32, "value": 0.0}
                    ]}
                ]}
            },
            # Text Caret (fades in at frame 28 exactly where pointer clicked)
            {
                "id": "caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.96, 0.22, 0.62, 1.0]},
                "size": [4.0, 58.0], "position": [text_st_x, 540.0 - 29.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "in_out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 28, "value": 0.0}, {"frame": 32, "value": 1.0}, {"frame": 78, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_11.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 12: Dual Collaborative Multiplayer Sync
# Two users (Pierone in Cyan, Elena in Pink) interacting synchronously
# -------------------------------------------------------------------------
def build_scene_12(dur=95):
    u1_x = [
        {"frame": 0, "value": 300.0},
        {"frame": 28, "value": 720.0},
        {"frame": 60, "value": 850.0},
        {"frame": dur - 1, "value": 100.0}
    ]
    u1_y = [
        {"frame": 0, "value": 200.0},
        {"frame": 28, "value": 480.0},
        {"frame": 60, "value": 520.0},
        {"frame": dur - 1, "value": 900.0}
    ]
    
    u2_x = [
        {"frame": 0, "value": 1600.0},
        {"frame": 32, "value": 1180.0},
        {"frame": 64, "value": 1050.0},
        {"frame": dur - 1, "value": 1800.0}
    ]
    u2_y = [
        {"frame": 0, "value": 800.0},
        {"frame": 32, "value": 560.0},
        {"frame": 64, "value": 520.0},
        {"frame": dur - 1, "value": 100.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_12",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.03, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "12 / DUAL MULTIPLAYER SYNC", "size": [500, 50],
                "position": [960, 320, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#00F0FF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Canvas Heading Text
            {
                "id": "hero_txt", "type": "text", "text": "Real-Time Collaboration", "size": [900, 110],
                "position": [960, 520, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 66.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # User 1: Pierone (Cyan Pointer Capsule)
            {
                "id": "u1_wedge", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 6.0, "fill": [0.0, 0.94, 1.0, 1.0]},
                "size": [14.0, 24.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": u1_x},
                    {"property": "position_y", "easing": "out_expo", "keyframes": u1_y},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # User 1: Badge Pill
            {
                "id": "u1_badge_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [0.0, 0.75, 0.95, 0.95]},
                "size": [116.0, 34.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 20.0} for k in u1_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 16.0} for k in u1_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "u1_badge_txt", "type": "text", "text": "Pierone", "size": [106, 28],
                "position": [0, 0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 18.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 78.0} for k in u1_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 33.0} for k in u1_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # User 2: Elena (Pink Pointer Capsule)
            {
                "id": "u2_wedge", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 6.0, "fill": [0.96, 0.22, 0.62, 1.0]},
                "size": [14.0, 24.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": u2_x},
                    {"property": "position_y", "easing": "out_expo", "keyframes": u2_y},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # User 2: Badge Pill
            {
                "id": "u2_badge_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [0.96, 0.22, 0.62, 0.95]},
                "size": [100.0, 34.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 20.0} for k in u2_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 16.0} for k in u2_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "u2_badge_txt", "type": "text", "text": "Elena", "size": [90, 28],
                "position": [0, 0, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 18.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 70.0} for k in u2_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 33.0} for k in u2_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 80, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_12.mp4"), "format": "mp4", "codec": "h264"}
    }

BUILDERS = [
    build_scene_01,
    build_scene_02,
    build_scene_03,
    build_scene_04,
    build_scene_05,
    build_scene_06,
    build_scene_07,
    build_scene_08,
    build_scene_09,
    build_scene_10,
    build_scene_11,
    build_scene_12,
]

def main():
    print(f"Emitting 12 Web Cursor Animation plans to {OUT_DIR}...")
    for idx, builder in enumerate(BUILDERS, 1):
        plan = builder()
        plan_path = OUT_DIR / f"cursor_scene_{idx:02d}.plan.json"
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"  [Scene {idx:02d}] Wrote {plan_path.name}")
    print("All 12 cursor plans emitted successfully!")

if __name__ == "__main__":
    main()
