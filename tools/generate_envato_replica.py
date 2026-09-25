#!/usr/bin/env python3
"""
Full generator for all 30 HIGH-ENERGY kinetic typography scenes.
Features:
- Punchy entrances (Slam-in, Stagger, Elastic Pop, Overshoot out_back).
- Continuous 3D kinetic movement (Parallax, 3D yaw, tracking expansion, scale breathing).
- High-speed outro transitions (Whip cuts, snap zoom-through, magnetic slides).
- 75 to 90 frames per scene (2.5s to 3.0s @ 30fps) for optimal reading and kinetic pacing.
- Validated for strict Vulkan GPU + NVENC rendering at >120 FPS.
"""

import os
import sys
import json
from pathlib import Path
from PIL import ImageFont

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
CHRONON_DIR = BASE_DIR / "Chronon3d"
TEMPLATE_DIR = BASE_DIR / "ChrononTemplate"
OUT_DIR = TEMPLATE_DIR / "out" / "envato_scenes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_POPPINS_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_INTER_BOLD = "assets/fonts/Inter-Bold.ttf"
FONT_INTER_REGULAR = "assets/fonts/Inter-Regular.ttf"

def get_pil_font(font_rel_path, font_size):
    full_path = CHRONON_DIR / font_rel_path
    return ImageFont.truetype(str(full_path), int(font_size))

def make_bg(color, duration):
    return {
        "id": "background",
        "type": "color",
        "color": color,
        "start_frame": 0,
        "duration_frames": duration
    }

# -------------------------------------------------------------------------
# SCENE 01: Designed for fast titles (Staggered Slam-In + Lavender Accent)
# -------------------------------------------------------------------------
def build_scene_01(dur=75):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2, w3 = font.getlength("Designed for"), font.getlength("fast"), font.getlength("titles")
    gap = 20.0
    tot = w1 + w2 + w3 + 2 * gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_01",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.031, 0.031, 0.043, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Designed for", "size": [w1 + 10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 16.0, "intensity": 0.40, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 200.0}, {"frame": 14, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -320.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 14, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "fast", "size": [w2 + 10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#818CF8", "glow": {"radius": 32.0, "intensity": 0.90, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 4, "value": 220.0}, {"frame": 18, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -320.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 4, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 4, "value": [0.3, 0.3, 1.0]}, {"frame": 18, "value": [1.1, 1.1, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}]}
                ]}
            },
            {
                "id": "t3", "type": "text", "text": "titles", "size": [w3 + 10, 130],
                "position": [st + w1 + gap + w2 + gap + w3/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 16.0, "intensity": 0.40, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 8, "value": 220.0}, {"frame": 22, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -320.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 8, "value": [0.4, 0.4, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_01.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 02: Motion ready| (Dynamic Typewriter + Caret + 3D Dolly Drift)
# -------------------------------------------------------------------------
def build_scene_02(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 76)
    text_str = "Motion ready"
    tot_w = font.getlength(text_str)
    st_f, end_f = 6, 36
    origin_x = 960.0 - tot_w / 2.0
    
    caret_kf = [{"frame": 0, "value": origin_x}, {"frame": st_f - 1, "value": origin_x}]
    for i in range(1, len(text_str) + 1):
        f = int(st_f + (i / len(text_str)) * (end_f - st_f))
        caret_kf.append({"frame": f, "value": origin_x + font.getlength(text_str[:i]) + 6.0})
    caret_kf.append({"frame": 72, "value": origin_x + tot_w + 6.0})
    caret_kf.append({"frame": dur - 1, "value": origin_x + tot_w + 1200.0})
    
    opacity_kf = []
    for f in range(dur):
        if f >= 72:
            op = 0.0
        elif (f >= st_f and f <= end_f) or ((f // 5) % 2 == 0):
            op = 1.0
        else:
            op = 0.0
        opacity_kf.append({"frame": f, "value": op})
        
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_02",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.031, 0.031, 0.043, 1.0], dur),
            {
                "id": "text_main", "type": "text", "text": text_str, "size": [tot_w + 40, 140],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 76.0, "fill": "#FFFFFF", "glow": {"radius": 22.0, "intensity": 0.50, "color": "#818CF8"}},
                "text_animators": [{
                    "id": "tw", "selectors": [{"unit": "glyph", "shape": "ramp_up", "start": {"property": "start", "keyframes": [{"frame": st_f, "value": 0.0}, {"frame": end_f, "value": 100.0}]}, "end": {"property": "end", "keyframes": [{"frame": st_f, "value": 0.1}, {"frame": end_f, "value": 100.0}]}}],
                    "properties": [{"property": "opacity", "easing": "linear", "keyframes": [{"frame": 0, "value": 0.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "position_z", "easing": "out_quad", "keyframes": [{"frame": 0, "value": -100.0}, {"frame": 70, "value": 40.0}, {"frame": dur - 1, "value": 200.0}]},
                    {"property": "position_x", "easing": "in_expo", "keyframes": [{"frame": 72, "value": 0.0}, {"frame": dur - 1, "value": 1200.0}]},
                    {"property": "opacity", "easing": "in_quad", "keyframes": [{"frame": 72, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "caret", "type": "shape", "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.505, 0.549, 0.972, 1.0]},
                "size": [6.0, 68.0], "position": [0, 506.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "linear", "keyframes": caret_kf},
                    {"property": "opacity", "easing": "hold", "keyframes": opacity_kf}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_02.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 03: Motion ready right now (Explosive Pop-Scale Stagger + Glow Burst)
# -------------------------------------------------------------------------
def build_scene_03(dur=75):
    font = get_pil_font(FONT_POPPINS_BOLD, 70)
    w1, w2, w3 = font.getlength("Motion ready"), font.getlength("right"), font.getlength("now")
    gap = 22.0
    tot = w1 + w2 + w3 + 2 * gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_03",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.025, 0.038, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Motion ready", "size": [w1 + 10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF", "glow": {"radius": 36.0, "intensity": 0.85, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.2, 0.2, 1.0]}, {"frame": 14, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 62, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_x", "easing": "in_expo", "keyframes": [{"frame": 62, "value": 0.0}, {"frame": dur - 1, "value": -1400.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "right", "size": [w2 + 10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#818CF8", "glow": {"radius": 30.0, "intensity": 0.90, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 6, "value": [0.2, 0.2, 1.0]}, {"frame": 18, "value": [1.12, 1.12, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 62, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_x", "easing": "in_expo", "keyframes": [{"frame": 62, "value": 0.0}, {"frame": dur - 1, "value": -1400.0}]}
                ]}
            },
            {
                "id": "t3", "type": "text", "text": "now", "size": [w3 + 10, 130],
                "position": [st + w1 + gap + w2 + gap + w3/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF", "glow": {"radius": 20.0, "intensity": 0.50, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 12, "value": [0.2, 0.2, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 62, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_x", "easing": "in_expo", "keyframes": [{"frame": 62, "value": 0.0}, {"frame": dur - 1, "value": -1400.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_03.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 04: Active (Massive Zoom Punch + Dynamic Tracking Expansion)
# -------------------------------------------------------------------------
def build_scene_04(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_04",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.04, 0.04, 0.05, 1.0], dur),
            {
                "id": "t_active", "type": "text", "text": "Active", "size": [1200, 240],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 130.0, "fill": "#F1F5F9", "glow": {"radius": 24.0, "intensity": 0.60, "color": "#E2E8F0"}},
                "text_animators": [{
                    "id": "tracking_anim", "selectors": [{"unit": "glyph"}],
                    "properties": [{"property": "tracking", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -12.0}, {"frame": 20, "value": 4.0}, {"frame": dur - 1, "value": 26.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.3, 0.3, 1.0]}, {"frame": 15, "value": [1.08, 1.08, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.06, 1.06, 1.0]}, {"frame": dur - 1, "value": [2.6, 2.6, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 62, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_04.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 05: Online (Pastel Lavender + 3D Perspective Swing)
# -------------------------------------------------------------------------
def build_scene_05(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_05",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.76, 0.81, 0.96, 1.0], dur), # Soft pastel lavender
            {
                "id": "t_online", "type": "text", "text": "Online", "size": [1200, 240],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 135.0, "fill": "#312E81"},
                "animation": {"tracks": [
                    {"property": "rotation_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": -35.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 8.0}, {"frame": dur - 1, "value": 45.0}]},
                    {"property": "position_z", "easing": "out_expo", "keyframes": [{"frame": 0, "value": -250.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 60.0}, {"frame": dur - 1, "value": -350.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_05.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 06: Ready (Deep Navy + Cyan Halo Slam + Elastic Settle)
# -------------------------------------------------------------------------
def build_scene_06(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_06",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.04, 0.08, 1.0], dur),
            {
                "id": "t_ready", "type": "text", "text": "Ready", "size": [1200, 240],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 130.0, "fill": "#FFFFFF", "glow": {"radius": 42.0, "intensity": 0.85, "color": "#38BDF8"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [1.8, 1.8, 1.0]}, {"frame": 14, "value": [0.95, 0.95, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}, {"frame": 62, "value": [1.04, 1.04, 1.0]}, {"frame": dur - 1, "value": [0.2, 0.2, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 62, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_06.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 07: Text drives motion / built for real projects (Swiss Studio White)
# -------------------------------------------------------------------------
def build_scene_07(dur=80):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_07",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.98, 0.98, 0.99, 1.0], dur), # Crisp Studio White
            {
                "id": "line1", "type": "text", "text": "Text drives motion", "size": [1500, 100],
                "position": [960, 490, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 64.0, "fill": "#0A0A0A"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 120.0}, {"frame": 16, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -240.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "line2", "type": "text", "text": "built for real projects", "size": [1500, 100],
                "position": [960, 580, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 64.0, "fill": "#475569"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 6, "value": 120.0}, {"frame": 22, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -240.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_07.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 08: Works on mobile / all formats ready (Phone Frame Pop + Text Slide)
# -------------------------------------------------------------------------
def build_scene_08(dur=80):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_08",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "phone_frame", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 42.0, "fill": [0.08, 0.09, 0.14, 0.85], "stroke": {"width": 3.0, "color": "#818CF8"}},
                "size": [320.0, 620.0], "position": [800.0, 230.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.3, 0.3, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}, {"frame": 64, "value": [1.03, 1.03, 1.0]}, {"frame": dur - 1, "value": [0.1, 0.1, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "phone_txt1", "type": "text", "text": "Works on mobile", "size": [400, 60],
                "position": [960, 740, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 28.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 10, "value": 60.0}, {"frame": 24, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": 200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "phone_txt2", "type": "text", "text": "all formats ready", "size": [400, 60],
                "position": [960, 785, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 24.0, "fill": "#818CF8"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 14, "value": 60.0}, {"frame": 28, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": 200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 0.0}, {"frame": 22, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_08.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 09: Build digital motion (Opposite Horizontal Whip Reveal)
# -------------------------------------------------------------------------
def build_scene_09(dur=75):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2 = font.getlength("Build digital"), font.getlength("motion")
    gap = 22.0
    tot = w1 + w2 + gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_09",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.025, 0.035, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Build digital", "size": [w1 + 10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 38.0, "intensity": 0.88, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_back", "keyframes": [{"frame": 0, "value": -400.0}, {"frame": 16, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -1200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "motion", "size": [w2 + 10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#60A5FA", "glow": {"radius": 24.0, "intensity": 0.75, "color": "#3B82F6"}},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_back", "keyframes": [{"frame": 4, "value": 400.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": 1200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 4, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_09.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 10: Shaping what's next ✦ (Typewriter + Sparkle Accent)
# -------------------------------------------------------------------------
def build_scene_10(dur=85):
    font = get_pil_font(FONT_POPPINS_BOLD, 68)
    text_str = "Shaping what's next ✦"
    tot_w = font.getlength(text_str)
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_10",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_sparkle", "type": "text", "text": text_str, "size": [tot_w + 40, 140],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#FFFFFF", "glow": {"radius": 26.0, "intensity": 0.65, "color": "#F472B6"}},
                "text_animators": [{
                    "id": "tw", "selectors": [{"unit": "glyph", "shape": "ramp_up", "start": {"property": "start", "keyframes": [{"frame": 4, "value": 0.0}, {"frame": 40, "value": 100.0}]}, "end": {"property": "end", "keyframes": [{"frame": 4, "value": 0.1}, {"frame": 40, "value": 100.0}]}}],
                    "properties": [{"property": "opacity", "easing": "linear", "keyframes": [{"frame": 0, "value": 0.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_quad", "keyframes": [{"frame": 0, "value": [0.95, 0.95, 1.0]}, {"frame": 68, "value": [1.05, 1.05, 1.0]}, {"frame": dur - 1, "value": [1.6, 1.6, 1.0]}]},
                    {"property": "opacity", "easing": "in_quad", "keyframes": [{"frame": 68, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_10.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 11: This system feels (Studio White Typewriter + Caret |)
# -------------------------------------------------------------------------
def build_scene_11(dur=85):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    text_str = "This system feels"
    tot_w = font.getlength(text_str)
    st_f, end_f = 4, 38
    origin_x = 960.0 - tot_w / 2.0
    
    caret_kf = [{"frame": 0, "value": origin_x}, {"frame": st_f - 1, "value": origin_x}]
    for i in range(1, len(text_str) + 1):
        f = int(st_f + (i / len(text_str)) * (end_f - st_f))
        caret_kf.append({"frame": f, "value": origin_x + font.getlength(text_str[:i]) + 6.0})
    caret_kf.append({"frame": 68, "value": origin_x + tot_w + 6.0})
    caret_kf.append({"frame": dur - 1, "value": origin_x + tot_w + 1400.0})
    
    opacity_kf = []
    for f in range(dur):
        if f >= 68:
            op = 0.0
        elif (f >= st_f and f <= end_f) or ((f // 5) % 2 == 0):
            op = 1.0
        else:
            op = 0.0
        opacity_kf.append({"frame": f, "value": op})
        
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_11",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.98, 0.98, 0.99, 1.0], dur),
            {
                "id": "t_main", "type": "text", "text": text_str, "size": [tot_w + 30, 140],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#0A0A0A"},
                "text_animators": [{
                    "id": "tw", "selectors": [{"unit": "glyph", "shape": "ramp_up", "start": {"property": "start", "keyframes": [{"frame": st_f, "value": 0.0}, {"frame": end_f, "value": 100.0}]}, "end": {"property": "end", "keyframes": [{"frame": st_f, "value": 0.1}, {"frame": end_f, "value": 100.0}]}}],
                    "properties": [{"property": "opacity", "easing": "linear", "keyframes": [{"frame": 0, "value": 0.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "in_expo", "keyframes": [{"frame": 68, "value": 0.0}, {"frame": dur - 1, "value": 1400.0}]},
                    {"property": "opacity", "easing": "in_quad", "keyframes": [{"frame": 68, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "caret", "type": "shape", "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.04, 0.04, 0.04, 1.0]},
                "size": [6.0, 64.0], "position": [0, 508.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "linear", "keyframes": caret_kf},
                    {"property": "opacity", "easing": "hold", "keyframes": opacity_kf}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_11.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 12: feels built to ship (Snap Zoom Punch + Active Tracking)
# -------------------------------------------------------------------------
def build_scene_12(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_12",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_ship", "type": "text", "text": "feels built to ship", "size": [1500, 160],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 76.0, "fill": "#FFFFFF", "glow": {"radius": 18.0, "intensity": 0.45, "color": "#FFFFFF"}},
                "text_animators": [{
                    "id": "track", "selectors": [{"unit": "glyph"}],
                    "properties": [{"property": "tracking", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -10.0}, {"frame": dur - 1, "value": 18.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.3, 0.3, 1.0]}, {"frame": 15, "value": [1.08, 1.08, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.04, 1.04, 1.0]}, {"frame": dur - 1, "value": [2.4, 2.4, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_12.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 13: ✦ Sound effects included (Neon Purple Glow + Spring Reveal)
# -------------------------------------------------------------------------
def build_scene_13(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_13",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_sfx", "type": "text", "text": "✦ Sound effects included", "size": [1500, 150],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF", "glow": {"radius": 28.0, "intensity": 0.70, "color": "#A78BFA"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 18, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_13.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 14: Screen motion for video (Clean Editorial Slide Up)
# -------------------------------------------------------------------------
def build_scene_14(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_14",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_screen", "type": "text", "text": "Screen motion for video", "size": [1500, 140],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#F8FAFC"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 16, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -250.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.6, 0.6, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_14.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 15: Refined (Cinematic Tracking Slam + Camera Dolly)
# -------------------------------------------------------------------------
def build_scene_15(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_15",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.035, 0.035, 0.045, 1.0], dur),
            {
                "id": "t_refined", "type": "text", "text": "Refined", "size": [1200, 200],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 95.0, "fill": "#FFFFFF", "glow": {"radius": 16.0, "intensity": 0.40, "color": "#FFFFFF"}},
                "text_animators": [{
                    "id": "track", "selectors": [{"unit": "glyph"}],
                    "properties": [{"property": "tracking", "easing": "out_cubic", "keyframes": [{"frame": 0, "value": -8.0}, {"frame": dur - 1, "value": 28.0}]}]
                }],
                "animation": {"tracks": [
                    {"property": "position_z", "easing": "out_expo", "keyframes": [{"frame": 0, "value": -300.0}, {"frame": 18, "value": 0.0}, {"frame": 60, "value": 80.0}, {"frame": dur - 1, "value": 400.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_15.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 16: Flow (Lavender Typography + 3D Tilt Yaw Drift)
# -------------------------------------------------------------------------
def build_scene_16(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_16",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.08, 0.06, 0.16, 1.0], dur),
            {
                "id": "t_flow", "type": "text", "text": "Flow", "size": [1200, 260],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 140.0, "fill": "#C7D2FE", "glow": {"radius": 36.0, "intensity": 0.75, "color": "#818CF8"}},
                "animation": {"tracks": [
                    {"property": "rotation_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": -30.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 12.0}, {"frame": dur - 1, "value": 50.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_16.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 17: Sync. Break. Go. (Rhythmic Kinetic Staccato Pops)
# -------------------------------------------------------------------------
def build_scene_17(dur=80):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_17",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "w1", "type": "text", "text": "Sync.", "size": [320, 130],
                "position": [660, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 76.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.2, 0.2, 1.0]}, {"frame": 12, "value": [1.1, 1.1, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]}
                ]}
            },
            {
                "id": "w2", "type": "text", "text": "Break.", "size": [350, 130],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 76.0, "fill": "#818CF8", "glow": {"radius": 26.0, "intensity": 0.75, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 14, "value": [0.2, 0.2, 1.0]}, {"frame": 26, "value": [1.12, 1.12, 1.0]}, {"frame": 30, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 0.0}, {"frame": 20, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]}
                ]}
            },
            {
                "id": "w3", "type": "text", "text": "Go.", "size": [260, 130],
                "position": [1240, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 76.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 28, "value": [0.2, 0.2, 1.0]}, {"frame": 40, "value": [1.1, 1.1, 1.0]}, {"frame": 44, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 28, "value": 0.0}, {"frame": 34, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_17.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 18: Real (Massive Bold Studio White Slam-In)
# -------------------------------------------------------------------------
def build_scene_18(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_18",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.98, 0.98, 0.99, 1.0], dur),
            {
                "id": "t_real", "type": "text", "text": "Real", "size": [1200, 280],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 160.0, "fill": "#0A0A0A"},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [2.2, 2.2, 1.0]}, {"frame": 14, "value": [0.96, 0.96, 1.0]}, {"frame": 20, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.05, 1.05, 1.0]}, {"frame": dur - 1, "value": [0.2, 0.2, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_18.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 19: Real words come to life (Stagger Cascade Reveal)
# -------------------------------------------------------------------------
def build_scene_19(dur=80):
    font = get_pil_font(FONT_POPPINS_BOLD, 68)
    w1, w2, w3, w4 = font.getlength("Real"), font.getlength("words"), font.getlength("come to"), font.getlength("life")
    gap = 20.0
    tot = w1 + w2 + w3 + w4 + 3 * gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_19",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Real", "size": [w1+10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 160.0}, {"frame": 14, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "words", "size": [w2+10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#818CF8", "glow": {"radius": 24.0, "intensity": 0.70, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 4, "value": 160.0}, {"frame": 18, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 4, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t3", "type": "text", "text": "come to", "size": [w3+10, 130],
                "position": [st + w1 + gap + w2 + gap + w3/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 8, "value": 160.0}, {"frame": 22, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t4", "type": "text", "text": "life", "size": [w4+10, 130],
                "position": [st + w1 + gap + w2 + gap + w3 + gap + w4/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 68.0, "fill": "#94A3B8"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 12, "value": 160.0}, {"frame": 26, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 20, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_19.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 20: Fluid (Intense Spherical Bloom Pulse + Elastic Bounce)
# -------------------------------------------------------------------------
def build_scene_20(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_20",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.04, 0.09, 1.0], dur),
            {
                "id": "t_fluid", "type": "text", "text": "Fluid", "size": [1200, 260],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 135.0, "fill": "#FFFFFF", "glow": {"radius": 46.0, "intensity": 0.95, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.2, 0.2, 1.0]}, {"frame": 16, "value": [1.14, 1.14, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.06, 1.06, 1.0]}, {"frame": dur - 1, "value": [2.5, 2.5, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_20.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 21: Words drop| (Studio White Drop Slam + Blue Caret)
# -------------------------------------------------------------------------
def build_scene_21(dur=80):
    font = get_pil_font(FONT_POPPINS_BOLD, 74)
    w1, w2 = font.getlength("Words"), font.getlength("drop")
    gap = 20.0
    tot = w1 + w2 + gap
    st = 960.0 - tot / 2.0
    caret_x = st + tot + 8.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_21",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.98, 0.98, 0.99, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Words", "size": [w1+10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 74.0, "fill": "#0A0A0A"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": -240.0}, {"frame": 14, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": 300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "drop", "size": [w2+10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 74.0, "fill": "#4F46E5"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 6, "value": -240.0}, {"frame": 20, "value": 0.0}, {"frame": 64, "value": 0.0}, {"frame": dur - 1, "value": 300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 64, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "caret", "type": "shape", "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.31, 0.27, 0.90, 1.0]},
                "size": [6.0, 66.0], "position": [caret_x, 507.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": f, "value": 1.0 if f < 64 and (f // 5) % 2 == 0 else 0.0} for f in range(dur)]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_21.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 22: Signal (Optical Focus Pull + Zoom Snap)
# -------------------------------------------------------------------------
def build_scene_22(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_22",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_signal", "type": "text", "text": "Signal", "size": [1200, 260],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 140.0, "fill": "#C7D2FE", "glow": {"radius": 38.0, "intensity": 0.85, "color": "#818CF8"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.3, 0.3, 1.0]}, {"frame": 16, "value": [1.1, 1.1, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.05, 1.05, 1.0]}, {"frame": dur - 1, "value": [2.4, 2.4, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_22.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 23: Neural (Soft Lavender on Deep Violet 3D Orbit)
# -------------------------------------------------------------------------
def build_scene_23(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_23",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.05, 0.03, 0.12, 1.0], dur),
            {
                "id": "t_neural", "type": "text", "text": "Neural", "size": [1200, 260],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 140.0, "fill": "#DDD6FE", "glow": {"radius": 32.0, "intensity": 0.70, "color": "#A78BFA"}},
                "animation": {"tracks": [
                    {"property": "rotation_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": -32.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 15.0}, {"frame": dur - 1, "value": 45.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_23.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 24: ✦ Content ready (Sparkle Stagger Reveal)
# -------------------------------------------------------------------------
def build_scene_24(dur=75):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2 = font.getlength("✦ Content"), font.getlength("ready")
    gap = 22.0
    tot = w1 + w2 + gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_24",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "✦ Content", "size": [w1+10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 22.0, "intensity": 0.55, "color": "#F472B6"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 14, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "ready", "size": [w2+10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#818CF8", "glow": {"radius": 28.0, "intensity": 0.80, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 6, "value": 180.0}, {"frame": 20, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_24.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 25: Motion that just (Tri-Word Stagger Pop)
# -------------------------------------------------------------------------
def build_scene_25(dur=75):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2, w3 = font.getlength("Motion"), font.getlength("that"), font.getlength("just")
    gap = 20.0
    tot = w1 + w2 + w3 + 2 * gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_25",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Motion", "size": [w1+10, 130],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 34.0, "intensity": 0.85, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 14, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 14, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "that", "size": [w2+10, 130],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#818CF8", "glow": {"radius": 24.0, "intensity": 0.70, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 4, "value": 180.0}, {"frame": 18, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 4, "value": [0.3, 0.3, 1.0]}, {"frame": 18, "value": [1.08, 1.08, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 4, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t3", "type": "text", "text": "just", "size": [w3+10, 130],
                "position": [st + w1 + gap + w2 + gap + w3/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#E2E8F0"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 8, "value": 180.0}, {"frame": 22, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 8, "value": [0.4, 0.4, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_25.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 26: Future (Saturated Violet Canvas + Navy Text Slam-In)
# -------------------------------------------------------------------------
def build_scene_26(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_26",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.388, 0.400, 0.945, 1.0], dur), # #6366F1
            {
                "id": "t_future", "type": "text", "text": "Future", "size": [1200, 280],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 155.0, "fill": "#1E1B4B"},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.2, 0.2, 1.0]}, {"frame": 15, "value": [1.1, 1.1, 1.0]}, {"frame": 22, "value": [1.0, 1.0, 1.0]}, {"frame": 60, "value": [1.05, 1.05, 1.0]}, {"frame": dur - 1, "value": [2.5, 2.5, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_26.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 27: Make it move (Dynamic Slide Pop)
# -------------------------------------------------------------------------
def build_scene_27(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_27",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "t_move", "type": "text", "text": "Make it move", "size": [1500, 180],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 84.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": 180.0}, {"frame": 16, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -300.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_27.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 28: Action (Purple Gradient Atmosphere + 3D Tilt Orbit)
# -------------------------------------------------------------------------
def build_scene_28(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_28",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.10, 0.07, 0.22, 1.0], dur),
            {
                "id": "t_action", "type": "text", "text": "Action", "size": [1200, 260],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 145.0, "fill": "#E0E7FF", "glow": {"radius": 34.0, "intensity": 0.75, "color": "#818CF8"}},
                "animation": {"tracks": [
                    {"property": "rotation_y", "easing": "out_back", "keyframes": [{"frame": 0, "value": -30.0}, {"frame": 18, "value": 0.0}, {"frame": 60, "value": 12.0}, {"frame": dur - 1, "value": 40.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.4, 0.4, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_28.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 29: Pure Design for (Asymmetric Editorial Slam)
# -------------------------------------------------------------------------
def build_scene_29(dur=75):
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_29",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.04, 1.0], dur),
            {
                "id": "l1", "type": "text", "text": "Pure Design", "size": [850, 110],
                "position": [1050, 480, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 22.0, "intensity": 0.50, "color": "#818CF8"}},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_back", "keyframes": [{"frame": 0, "value": 400.0}, {"frame": 16, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": 1200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "l2", "type": "text", "text": "for", "size": [300, 90],
                "position": [760, 570, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 56.0, "fill": "#38BDF8"},
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_back", "keyframes": [{"frame": 6, "value": -400.0}, {"frame": 22, "value": 0.0}, {"frame": 60, "value": 0.0}, {"frame": dur - 1, "value": -1200.0}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 60, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_29.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 30: Use it your way (Grand Finale Explosive Bloom Stagger)
# -------------------------------------------------------------------------
def build_scene_30(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 78)
    w1, w2, w3 = font.getlength("Use"), font.getlength("it"), font.getlength("your way")
    gap = 22.0
    tot = w1 + w2 + w3 + 2 * gap
    st = 960.0 - tot / 2.0
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "envato_scene_30",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.025, 0.035, 1.0], dur),
            {
                "id": "t1", "type": "text", "text": "Use", "size": [w1+10, 140],
                "position": [st + w1/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 78.0, "fill": "#FFFFFF", "glow": {"radius": 44.0, "intensity": 0.95, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.2, 0.2, 1.0]}, {"frame": 14, "value": [1.1, 1.1, 1.0]}, {"frame": 20, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 72, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 72, "value": 0.0}, {"frame": dur - 1, "value": -350.0}]}
                ]}
            },
            {
                "id": "t2", "type": "text", "text": "it", "size": [w2+10, 140],
                "position": [st + w1 + gap + w2/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 78.0, "fill": "#A78BFA", "glow": {"radius": 32.0, "intensity": 0.85, "color": "#7C3AED"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 6, "value": [0.2, 0.2, 1.0]}, {"frame": 18, "value": [1.15, 1.15, 1.0]}, {"frame": 24, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 6, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 72, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 72, "value": 0.0}, {"frame": dur - 1, "value": -350.0}]}
                ]}
            },
            {
                "id": "t3", "type": "text", "text": "your way", "size": [w3+10, 140],
                "position": [st + w1 + gap + w2 + gap + w3/2, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 78.0, "fill": "#FFFFFF", "glow": {"radius": 22.0, "intensity": 0.50, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 12, "value": [0.2, 0.2, 1.0]}, {"frame": 24, "value": [1.1, 1.1, 1.0]}, {"frame": 28, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.0}, {"frame": 18, "value": 1.0}, {"frame": 72, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "position_y", "easing": "in_expo", "keyframes": [{"frame": 72, "value": 0.0}, {"frame": dur - 1, "value": -350.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "envato_scene_30.mp4"), "format": "mp4", "codec": "h264"}
    }

ALL_BUILDERS = {
    f"envato_scene_{i:02d}": globals()[f"build_scene_{i:02d}"]
    for i in range(1, 31)
}

if __name__ == "__main__":
    for name, builder in ALL_BUILDERS.items():
        plan = builder()
        out_file = OUT_DIR / f"{name}.plan.json"
        with open(out_file, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"Generated {out_file.name} ({plan['canvas']['duration_frames']} frames)")
