#!/usr/bin/env python3
"""
Generate the complete catalogue of 16 High-End Cursor Animations in Chronon v3 schema.
- Perfectly Centered Composition (Golden Zone: 960, 540).
- No erratic wandering or off-screen departures.
- 100% Vulkan GPU Native Shape & MTSDF Text pipeline compliant.
- Categorized into:
  - Categoria A: Morphing Geometrico & Adattivo [Scenes 01-04]
  - Categoria B: Fisica Liquida, Inerzia & Deformazione Direzionale [Scenes 05-08]
  - Categoria C: Cinetica Tipografica & Interazione con il Testo [Scenes 09-12]
  - Categoria D: Prospettiva 3D, Spazio & Materiali [Scenes 13-16]
"""

import json
from pathlib import Path
from PIL import ImageFont

BASE_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing")
OUT_DIR = BASE_DIR / "ChrononTemplate" / "out" / "cursor_catalog_16"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_POPPINS_BOLD = "assets/fonts/Poppins-Bold.ttf"
FONT_INTER_BOLD = "assets/fonts/Inter-Bold.ttf"

def get_pil_font(font_path_rel, size):
    abs_p = BASE_DIR / "Chronon3d" / font_path_rel
    try:
        return ImageFont.truetype(str(abs_p), int(size))
    except Exception:
        return ImageFont.load_default()

def make_bg(color_rgba, dur):
    return {
        "id": "background",
        "type": "color",
        "color": color_rgba,
        "start_frame": 0,
        "duration_frames": dur
    }

# =========================================================================
# CATEGORIA A: Morphing Geometrico & Adattivo (Apple & visionOS Style)
# =========================================================================

# -------------------------------------------------------------------------
# SCENE 01: Il Pill Morph Magnetico (Button Lock)
# -------------------------------------------------------------------------
def build_scene_01(dur=90):
    btn_w, btn_h = 320.0, 72.0
    btn_x, btn_y = 960.0 - btn_w / 2.0, 540.0 - btn_h / 2.0
    
    # Cursor starts nearby at (850, 470), glides smoothly to center (960, 540)
    dot_x_kfs = [
        {"frame": 0, "value": 850.0},
        {"frame": 8, "value": 850.0},
        {"frame": 28, "value": 960.0},
        {"frame": 82, "value": 960.0},
        {"frame": dur - 1, "value": 960.0}
    ]
    dot_y_kfs = [
        {"frame": 0, "value": 470.0},
        {"frame": 8, "value": 470.0},
        {"frame": 28, "value": 540.0},
        {"frame": 82, "value": 540.0},
        {"frame": dur - 1, "value": 540.0}
    ]
    
    # Morph: dot [16, 16] stretches to button capsule [328, 76]
    morph_scale_x = [
        {"frame": 0, "value": 1.0},
        {"frame": 18, "value": 1.0},
        {"frame": 32, "value": 20.5},
        {"frame": 82, "value": 20.5},
        {"frame": dur - 1, "value": 20.5}
    ]
    morph_scale_y = [
        {"frame": 0, "value": 1.0},
        {"frame": 18, "value": 1.0},
        {"frame": 32, "value": 4.75},
        {"frame": 82, "value": 4.75},
        {"frame": dur - 1, "value": 4.75}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_01",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.035, 0.04, 0.055, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "01 / PILL MORPH MAGNETICO (BUTTON LOCK)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#3B82F6", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#3B82F6"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "btn_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 36.0, "fill": [0.08, 0.11, 0.18, 0.95]},
                "size": [btn_w, btn_h], "position": [btn_x, btn_y], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.9, 0.9, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]},
                        {"frame": 28, "value": [1.03, 1.03, 1.0]}, {"frame": 82, "value": [1.03, 1.03, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "btn_txt", "type": "text", "text": "Explore Features >", "size": [300, 50],
                "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 28.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "morph_cursor", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [0.23, 0.51, 0.96, 0.35]},
                "size": [16.0, 16.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_back", "keyframes": [{"frame": k["frame"], "value": k["value"] - 8.0} for k in dot_x_kfs]},
                    {"property": "position_y", "easing": "out_back", "keyframes": [{"frame": k["frame"], "value": k["value"] - 8.0} for k in dot_y_kfs]},
                    {"property": "scale_x", "easing": "out_back", "keyframes": morph_scale_x},
                    {"property": "scale_y", "easing": "out_back", "keyframes": morph_scale_y},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 6, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_01.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 02: L'I-Beam a Fisarmonica (Text Focus)
# -------------------------------------------------------------------------
def build_scene_02(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 72)
    w1, w2 = font.getlength("Dynamic"), font.getlength("Typography")
    gap = 26.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    # Cursor starts at st_x, traverses words smoothly, and settles at the center target
    caret_x_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 12, "value": st_x},
        {"frame": 30, "value": st_x + w1 + 6.0},
        {"frame": 44, "value": st_x + w1 + 6.0},
        {"frame": 64, "value": st_x + tot_w + 6.0},
        {"frame": 82, "value": st_x + tot_w + 6.0},
        {"frame": dur - 1, "value": st_x + tot_w + 6.0}
    ]
    
    scale_x_kfs = [
        {"frame": 0, "value": 1.0},
        {"frame": 12, "value": 1.0},
        {"frame": 22, "value": 3.25},  # 6.5px accordion swell
        {"frame": 36, "value": 3.25},
        {"frame": 44, "value": 1.0},
        {"frame": 52, "value": 3.25},
        {"frame": 62, "value": 3.25},
        {"frame": 70, "value": 0.9},   # Settles to refined 1.8px
        {"frame": dur - 1, "value": 0.9}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_02",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.035, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "02 / I-BEAM A FISARMONICA (ACCORDION STROKE)", "size": [700, 50],
                "position": [960, 370, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#00F0FF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "w1", "type": "text", "text": "Dynamic", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 0.0}, {"frame": 20, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "w2", "type": "text", "text": "Typography", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#00F0FF", "glow": {"radius": 24.0, "intensity": 0.7, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 46, "value": 0.0}, {"frame": 52, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "accordion_caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 1.0, "fill": [0.0, 0.94, 1.0, 1.0]},
                "size": [2.0, 72.0], "position": [0, y - 36.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_x_kfs},
                    {"property": "scale_x", "easing": "out_back", "keyframes": scale_x_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_02.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 03: Il Text Highlighter Fluid (Capsule Drag)
# -------------------------------------------------------------------------
def build_scene_03(dur=95):
    font = get_pil_font(FONT_POPPINS_BOLD, 70)
    w1, w2 = font.getlength("Select the"), font.getlength("Extraordinary")
    gap = 26.0
    tot_w = w1 + gap + w2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    sel_start_x = st_x + w1 + gap - 10.0
    sel_target_w = w2 + 20.0
    
    caret_x_kfs = [
        {"frame": 0, "value": sel_start_x},
        {"frame": 18, "value": sel_start_x},
        {"frame": 52, "value": sel_start_x + sel_target_w},
        {"frame": 84, "value": sel_start_x + sel_target_w},
        {"frame": dur - 1, "value": sel_start_x + sel_target_w}
    ]
    
    pill_scale_x = [
        {"frame": 0, "value": 0.0},
        {"frame": 18, "value": 0.0},
        {"frame": 52, "value": 1.0},
        {"frame": dur - 1, "value": 1.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_03",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "03 / TEXT HIGHLIGHTER FLUID (CAPSULE DRAG)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#C084FC", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#C084FC"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 84, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "selection_capsule", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 16.0, "fill": [0.65, 0.35, 0.98, 0.45]},
                "size": [sel_target_w, 84.0], "position": [sel_start_x, y - 42.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale_x", "easing": "out_expo", "keyframes": pill_scale_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 18, "value": 0.0}, {"frame": 24, "value": 1.0}, {"frame": 84, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "w1", "type": "text", "text": "Select the", "size": [w1 + 10, 130],
                "position": [st_x + w1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 84, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "w2", "type": "text", "text": "Extraordinary", "size": [w2 + 10, 130],
                "position": [st_x + w1 + gap + w2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 70.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 84, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "drag_caret", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.75, 0.45, 1.0, 1.0]},
                "size": [4.0, 76.0], "position": [0, y - 38.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": caret_x_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 84, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_03.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 04: Il Loupe / Lens Expansion (Macro Zoom)
# -------------------------------------------------------------------------
def build_scene_04(dur=90):
    badge_x, badge_y = 960.0, 540.0
    
    # Cursor approaches glyph from (880, 480) directly into center (960, 540)
    dot_x = [
        {"frame": 0, "value": 880.0},
        {"frame": 10, "value": 880.0},
        {"frame": 30, "value": badge_x},
        {"frame": 82, "value": badge_x},
        {"frame": dur - 1, "value": badge_x}
    ]
    dot_y = [
        {"frame": 0, "value": 480.0},
        {"frame": 10, "value": 480.0},
        {"frame": 30, "value": badge_y},
        {"frame": 82, "value": badge_y},
        {"frame": dur - 1, "value": badge_y}
    ]
    
    ring_scale = [
        {"frame": 0, "value": [0.2, 0.2, 1.0]},
        {"frame": 20, "value": [0.2, 0.2, 1.0]},
        {"frame": 36, "value": [1.0, 1.0, 1.0]},
        {"frame": 82, "value": [1.0, 1.0, 1.0]}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_04",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "04 / LOUPE / LENS EXPANSION (MACRO ZOOM)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#F59E0B", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "target_glyph", "type": "text", "text": "[KINETIC_CORE]", "size": [500, 70],
                "position": [badge_x, badge_y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 42.0, "fill": "#64748B"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "zoomed_glyph", "type": "text", "text": "[KINETIC_CORE]", "size": [650, 90],
                "position": [badge_x, badge_y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 56.0, "fill": "#FBBF24", "glow": {"radius": 24.0, "intensity": 0.8, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 30, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "loupe_ring", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 48.0, "fill": [0.96, 0.62, 0.04, 0.22]},
                "size": [96.0, 96.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_cubic", "keyframes": [{"frame": k["frame"], "value": k["value"] - 48.0} for k in dot_x]},
                    {"property": "position_y", "easing": "out_cubic", "keyframes": [{"frame": k["frame"], "value": k["value"] - 48.0} for k in dot_y]},
                    {"property": "scale", "easing": "out_back", "keyframes": ring_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_04.mp4"), "format": "mp4", "codec": "h264"}
    }

# =========================================================================
# CATEGORIA B: Fisica Liquida, Inerzia & Deformazione Direzionale
# =========================================================================

# -------------------------------------------------------------------------
# SCENE 05: Velocity Teardrop Stretch (Inerzia Balistica)
# -------------------------------------------------------------------------
def build_scene_05(dur=90):
    # Centered ballistic trajectory along track: surges from 760 to 1160 across viewport center
    st_x = 760.0
    end_x = 1160.0
    y = 540.0
    
    pos_kfs = [
        {"frame": 0, "value": [st_x - 12.0, y - 12.0, 0.0]},
        {"frame": 14, "value": [st_x - 12.0, y - 12.0, 0.0]},
        {"frame": 42, "value": [end_x - 12.0, y - 12.0, 0.0]},
        {"frame": 82, "value": [end_x - 12.0, y - 12.0, 0.0]},
        {"frame": dur - 1, "value": [end_x - 12.0, y - 12.0, 0.0]}
    ]
    
    trail_pos_kfs = [
        {"frame": 0, "value": [st_x - 12.0, y - 12.0, 0.0]},
        {"frame": 18, "value": [st_x - 12.0, y - 12.0, 0.0]},
        {"frame": 46, "value": [end_x - 12.0, y - 12.0, 0.0]},
        {"frame": 82, "value": [end_x - 12.0, y - 12.0, 0.0]},
        {"frame": dur - 1, "value": [end_x - 12.0, y - 12.0, 0.0]}
    ]
    
    scale_x_kfs = [
        {"frame": 0, "value": 1.0},
        {"frame": 14, "value": 1.0},
        {"frame": 24, "value": 3.2}, # Max velocity teardrop stretch
        {"frame": 38, "value": 3.2},
        {"frame": 44, "value": 0.8}, # Impact squish
        {"frame": 52, "value": 1.05},
        {"frame": 60, "value": 1.0},
        {"frame": dur - 1, "value": 1.0}
    ]
    scale_y_kfs = [
        {"frame": 0, "value": 1.0},
        {"frame": 14, "value": 1.0},
        {"frame": 24, "value": 0.6}, # Thin out during stretch
        {"frame": 38, "value": 0.6},
        {"frame": 44, "value": 1.25}, # Impact squish
        {"frame": 52, "value": 0.95},
        {"frame": 60, "value": 1.0},
        {"frame": dur - 1, "value": 1.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_05",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "05 / VELOCITY TEARDROP STRETCH (BALLISTIC INERTIA)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#EC4899", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#EC4899"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # Visual Speed Track Rail
            {
                "id": "speed_rail", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 3.0, "fill": [0.22, 0.15, 0.28, 0.5]},
                "size": [480.0, 6.0], "position": [960.0 - 240.0, y - 3.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.8}, {"frame": 80, "value": 0.8}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            # HUD Metric Text
            {
                "id": "speed_metric", "type": "text", "text": "VELOCITY: 3,200 PX/S", "size": [400, 30],
                "position": [960, 600, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 16.0, "fill": "#F472B6"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 16, "value": 0.9}, {"frame": 80, "value": 0.9}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "trail_ghost", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 12.0, "fill": [0.96, 0.22, 0.62, 0.35]},
                "size": [24.0, 24.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position", "easing": "out_expo", "keyframes": trail_pos_kfs},
                    {"property": "scale_x", "easing": "out_quad", "keyframes": scale_x_kfs},
                    {"property": "scale_y", "easing": "out_quad", "keyframes": scale_y_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 18, "value": 0.5}, {"frame": 44, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "teardrop_core", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 12.0, "fill": [0.96, 0.22, 0.62, 1.0]},
                "size": [24.0, 24.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position", "easing": "out_expo", "keyframes": pos_kfs},
                    {"property": "scale_x", "easing": "out_quad", "keyframes": scale_x_kfs},
                    {"property": "scale_y", "easing": "out_quad", "keyframes": scale_y_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_05.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 06: Jelly Squish & Recoil (Il Click a Molla)
# -------------------------------------------------------------------------
def build_scene_06(dur=90):
    target_x, target_y = 960.0, 540.0
    
    # Cursor starts at (870, 480), glides directly into center (960, 540)
    dot_x = [
        {"frame": 0, "value": 870.0},
        {"frame": 20, "value": target_x},
        {"frame": 82, "value": target_x},
        {"frame": dur - 1, "value": target_x}
    ]
    dot_y = [
        {"frame": 0, "value": 480.0},
        {"frame": 20, "value": target_y},
        {"frame": 82, "value": target_y},
        {"frame": dur - 1, "value": target_y}
    ]
    
    squish_kfs = [
        {"frame": 0, "value": [1.0, 1.0, 1.0]},
        {"frame": 26, "value": [1.0, 1.0, 1.0]},
        {"frame": 30, "value": [1.38, 0.62, 1.0]},  # Max squish
        {"frame": 36, "value": [0.82, 1.28, 1.0]},  # High recoil overshoot
        {"frame": 44, "value": [1.12, 0.92, 1.0]},  # Rebound oscillation 1
        {"frame": 52, "value": [0.96, 1.04, 1.0]},  # Rebound oscillation 2
        {"frame": 60, "value": [1.0, 1.0, 1.0]}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_06",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "06 / JELLY SQUISH & RECOIL (SPRING CLICK)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#F59E0B", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#F59E0B"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "target_card", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 24.0, "fill": [0.08, 0.10, 0.16, 0.9]},
                "size": [440.0, 160.0], "position": [target_x - 220.0, target_y - 80.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.9, 0.9, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]},
                        {"frame": 30, "value": [0.96, 0.96, 1.0]}, {"frame": 38, "value": [1.03, 1.03, 1.0]}, {"frame": 46, "value": [1.0, 1.0, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "card_txt", "type": "text", "text": "Execute Action", "size": [360, 50],
                "position": [target_x, target_y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 32.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "flash_ring", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 40.0, "fill": [1.0, 0.8, 0.2, 0.35]},
                "size": [80.0, 80.0], "position": [target_x - 40.0, target_y - 40.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_expo", "keyframes": [
                        {"frame": 0, "value": [0.1, 0.1, 1.0]}, {"frame": 30, "value": [0.1, 0.1, 1.0]}, {"frame": 46, "value": [1.8, 1.8, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 30, "value": 1.0}, {"frame": 46, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "jelly_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 12.0, "fill": [0.96, 0.62, 0.04, 1.0]},
                "size": [24.0, 24.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 12.0} for k in dot_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 12.0} for k in dot_y]},
                    {"property": "scale", "easing": "out_back", "keyframes": squish_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 8, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_06.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 07: Orbiting Comet / Trail di Particelle a Bassa Persistenza
# -------------------------------------------------------------------------
def build_scene_07(dur=90):
    # Tight, elegant orbital ellipse centered directly around (960, 540)
    import math
    orbit_x = []
    orbit_y = []
    for f in range(dur):
        angle = (f / 70.0) * 2.0 * math.pi
        ox = 960.0 + 130.0 * math.cos(angle)
        oy = 540.0 + 55.0 * math.sin(angle)
        orbit_x.append({"frame": f, "value": ox})
        orbit_y.append({"frame": f, "value": oy})

    layers = [
        make_bg([0.025, 0.025, 0.04, 1.0], dur),
        {
            "id": "label", "type": "text", "text": "07 / ORBITING COMET (LOW PERSISTENCE TRAIL)", "size": [700, 50],
            "position": [960, 340, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
            "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#818CF8", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#818CF8"}},
            "animation": {"tracks": [
                {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
            ]}
        },
        {
            "id": "center_txt", "type": "text", "text": "Orbital Dynamics", "size": [700, 80],
            "position": [960, 540, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
            "style": {"font": FONT_POPPINS_BOLD, "font_size": 58.0, "fill": "#FFFFFF"},
            "animation": {"tracks": [
                {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
            ]}
        }
    ]
    
    ghost_configs = [
        {"delay": 6, "size": 6.0, "color": [0.4, 0.2, 0.8, 0.25]},
        {"delay": 4, "size": 10.0, "color": [0.65, 0.35, 0.98, 0.45]},
        {"delay": 2, "size": 14.0, "color": [0.0, 0.94, 1.0, 0.70]},
    ]
    for i, g in enumerate(ghost_configs):
        d = g["delay"]
        half = g["size"] / 2.0
        layers.append({
            "id": f"comet_ghost_{i}", "type": "shape",
            "shape": {"type": "rounded_rect", "radius": half, "fill": g["color"]},
            "size": [g["size"], g["size"]], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
            "animation": {"tracks": [
                {"property": "position_x", "easing": "linear", "keyframes": [{"frame": k["frame"], "value": orbit_x[max(0, k["frame"] - d)]["value"] - half} for k in orbit_x]},
                {"property": "position_y", "easing": "linear", "keyframes": [{"frame": k["frame"], "value": orbit_y[max(0, k["frame"] - d)]["value"] - half} for k in orbit_y]},
                {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12 + d, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
            ]}
        })
        
    layers.append({
        "id": "comet_nucleus", "type": "shape",
        "shape": {"type": "rounded_rect", "radius": 9.0, "fill": [1.0, 1.0, 1.0, 1.0]},
        "size": [18.0, 18.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
        "animation": {"tracks": [
            {"property": "position_x", "easing": "linear", "keyframes": [{"frame": k["frame"], "value": k["value"] - 9.0} for k in orbit_x]},
            {"property": "position_y", "easing": "linear", "keyframes": [{"frame": k["frame"], "value": k["value"] - 9.0} for k in orbit_y]},
            {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
        ]}
    })

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_07",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": layers,
        "output": {"path": str(OUT_DIR / "cursor_scene_07.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 08: Liquid Blob Fusion (Metaball Cursor)
# -------------------------------------------------------------------------
def build_scene_08(dur=90):
    fixed_x, fixed_y = 960.0, 540.0
    
    # Mobile blob moves from (820, 540) to center (960, 540) to merge
    mob_x = [
        {"frame": 0, "value": 820.0},
        {"frame": 16, "value": 820.0},
        {"frame": 40, "value": fixed_x},
        {"frame": 82, "value": fixed_x},
        {"frame": dur - 1, "value": fixed_x}
    ]
    mob_y = [
        {"frame": 0, "value": 540.0},
        {"frame": 16, "value": 540.0},
        {"frame": 40, "value": fixed_y},
        {"frame": 82, "value": fixed_y},
        {"frame": dur - 1, "value": fixed_y}
    ]
    
    bridge_scale_x = [
        {"frame": 0, "value": 0.0},
        {"frame": 22, "value": 0.0},
        {"frame": 34, "value": 1.0},
        {"frame": 44, "value": 0.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_08",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "08 / LIQUID BLOB FUSION (METABALL UNION)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#10B981", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#10B981"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "fixed_blob", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 20.0, "fill": [0.06, 0.72, 0.51, 1.0]},
                "size": [40.0, 40.0], "position": [fixed_x - 20.0, fixed_y - 20.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.8, 0.8, 1.0]}, {"frame": 16, "value": [1.0, 1.0, 1.0]},
                        {"frame": 36, "value": [1.18, 1.18, 1.0]}, {"frame": 44, "value": [1.35, 1.35, 1.0]}, {"frame": 82, "value": [1.35, 1.35, 1.0]}
                    ]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "liquid_bridge", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 14.0, "fill": [0.06, 0.72, 0.51, 0.85]},
                "size": [140.0, 28.0], "position": [820.0, fixed_y - 14.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale_x", "easing": "in_out_quad", "keyframes": bridge_scale_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 24, "value": 0.9}, {"frame": 44, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "mobile_blob", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 16.0, "fill": [0.2, 0.85, 0.6, 1.0]},
                "size": [32.0, 32.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 16.0} for k in mob_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 16.0} for k in mob_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 44, "value": 0.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_08.mp4"), "format": "mp4", "codec": "h264"}
    }

# =========================================================================
# CATEGORIA C: Cinetica Tipografica & Interazione con il Testo
# =========================================================================

# -------------------------------------------------------------------------
# SCENE 09: Staccato Beat-Snap (Typewriter Companion)
# -------------------------------------------------------------------------
def build_scene_09(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 54)
    prompt = "> chronon"
    arg1 = "compile"
    arg2 = "--gpu"
    
    w_p = font.getlength(prompt)
    w_a1 = font.getlength(arg1)
    w_a2 = font.getlength(arg2)
    gap = 20.0
    tot_w = w_p + gap + w_a1 + gap + w_a2
    st_x = 960.0 - tot_w / 2.0
    y = 540.0
    
    caret_kfs = [
        {"frame": 0, "value": st_x},
        {"frame": 14, "value": st_x},
        {"frame": 22, "value": st_x + w_p + 4.0},
        {"frame": 36, "value": st_x + w_p + 4.0},
        {"frame": 44, "value": st_x + w_p + gap + w_a1 + 4.0},
        {"frame": 56, "value": st_x + w_p + gap + w_a1 + 4.0},
        {"frame": 64, "value": st_x + tot_w + 4.0},
        {"frame": 82, "value": st_x + tot_w + 4.0},
        {"frame": dur - 1, "value": st_x + tot_w + 4.0}
    ]
    
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_09",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.035, 0.04, 0.035, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "09 / STACCATO BEAT-SNAP (TYPEWRITER STEP)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#22C55E", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#22C55E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t_prompt", "type": "text", "text": prompt, "size": [w_p + 10, 90],
                "position": [st_x + w_p / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 54.0, "fill": "#4ADE80", "glow": {"radius": 20.0, "intensity": 0.5, "color": "#22C55E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 16, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t_a1", "type": "text", "text": arg1, "size": [w_a1 + 10, 90],
                "position": [st_x + w_p + gap + w_a1 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 54.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 38, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "t_a2", "type": "text", "text": arg2, "size": [w_a2 + 10, 90],
                "position": [st_x + w_p + gap + w_a1 + gap + w_a2 / 2.0, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 54.0, "fill": "#22C55E", "glow": {"radius": 22.0, "intensity": 0.6, "color": "#22C55E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "hold", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 58, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "staccato_block", "type": "shape",
                "shape": {"type": "rect", "fill": [0.13, 0.77, 0.37, 1.0]},
                "size": [14.0, 58.0], "position": [0, y - 29.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "hold", "keyframes": caret_kfs},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_09.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 10: Split Cursor (Dual Bracket Anchor)
# -------------------------------------------------------------------------
def build_scene_10(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 74)
    word = "ARCHITECT"
    w = font.getlength(word)
    st_x = 960.0 - w / 2.0
    end_x = 960.0 + w / 2.0
    y = 540.0
    
    left_x = [
        {"frame": 0, "value": 960.0},
        {"frame": 20, "value": 960.0},
        {"frame": 44, "value": st_x - 24.0},
        {"frame": 50, "value": st_x - 14.0},
        {"frame": 82, "value": st_x - 14.0},
        {"frame": dur - 1, "value": st_x - 14.0}
    ]
    right_x = [
        {"frame": 0, "value": 960.0},
        {"frame": 20, "value": 960.0},
        {"frame": 44, "value": end_x + 24.0},
        {"frame": 50, "value": end_x + 14.0},
        {"frame": 82, "value": end_x + 14.0},
        {"frame": dur - 1, "value": end_x + 14.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_10",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "10 / SPLIT CURSOR (DUAL BRACKET ANCHOR)", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#38BDF8", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#38BDF8"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "hero_word", "type": "text", "text": word, "size": [w + 20, 130],
                "position": [960, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 74.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "bracket_left", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.22, 0.74, 0.97, 1.0]},
                "size": [5.0, 74.0], "position": [0, y - 37.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": left_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "bracket_right", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 2.0, "fill": [0.22, 0.74, 0.97, 1.0]},
                "size": [5.0, 74.0], "position": [0, y - 37.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": right_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 20, "value": 0.0}, {"frame": 24, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_10.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 11: Pulse Halo / Ripple Shockwave (Il "Click d'Autore")
# -------------------------------------------------------------------------
def build_scene_11(dur=90):
    click_x, click_y = 960.0, 540.0
    
    core_scale = [
        {"frame": 0, "value": [1.0, 1.0, 1.0]},
        {"frame": 26, "value": [1.0, 1.0, 1.0]},
        {"frame": 30, "value": [0.0, 0.0, 1.0]},
        {"frame": 46, "value": [1.0, 1.0, 1.0]}
    ]
    
    ring1_scale = [
        {"frame": 0, "value": [0.05, 0.05, 1.0]},
        {"frame": 30, "value": [0.05, 0.05, 1.0]},
        {"frame": 56, "value": [2.8, 2.8, 1.0]}
    ]
    ring2_scale = [
        {"frame": 0, "value": [0.05, 0.05, 1.0]},
        {"frame": 34, "value": [0.05, 0.05, 1.0]},
        {"frame": 62, "value": [2.4, 2.4, 1.0]}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_11",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.03, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "11 / PULSE HALO / RIPPLE SHOCKWAVE", "size": [700, 50],
                "position": [960, 340, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#00F0FF", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "hero_txt", "type": "text", "text": "RESONANCE", "size": [700, 110],
                "position": [click_x, click_y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 72.0, "fill": "#FFFFFF", "glow": {"radius": 24.0, "intensity": 0.7, "color": "#00F0FF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]},
                    {"property": "scale", "easing": "out_back", "keyframes": [
                        {"frame": 0, "value": [0.8, 0.8, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]},
                        {"frame": 30, "value": [0.94, 0.94, 1.0]}, {"frame": 36, "value": [1.08, 1.08, 1.0]}, {"frame": 46, "value": [1.0, 1.0, 1.0]}
                    ]}
                ]}
            },
            {
                "id": "shockwave_1", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 55.0, "fill": [0.0, 0.94, 1.0, 0.25]},
                "size": [110.0, 110.0], "position": [click_x - 55.0, click_y - 55.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_expo", "keyframes": ring1_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 30, "value": 1.0}, {"frame": 56, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "shockwave_2", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 55.0, "fill": [0.65, 0.35, 0.98, 0.20]},
                "size": [110.0, 110.0], "position": [click_x - 55.0, click_y - 55.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_expo", "keyframes": ring2_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 34, "value": 0.9}, {"frame": 62, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "click_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [1.0, 1.0, 1.0, 1.0]},
                "size": [16.0, 16.0], "position": [click_x - 8.0, click_y - 8.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": core_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_11.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 12: Caret Glitch & Chroma Split
# -------------------------------------------------------------------------
def build_scene_12(dur=90):
    font = get_pil_font(FONT_POPPINS_BOLD, 64)
    code_txt = "SYS.EXEC_CORE()"
    w = font.getlength(code_txt)
    st_x = 960.0 - w / 2.0
    y = 540.0
    
    caret_st = st_x + w + 8.0
    
    center_x = [
        {"frame": 0, "value": caret_st},
        {"frame": 32, "value": caret_st},
        {"frame": 36, "value": caret_st + 3.0},
        {"frame": 40, "value": caret_st - 3.0},
        {"frame": 44, "value": caret_st + 2.0},
        {"frame": 48, "value": caret_st},
        {"frame": 82, "value": caret_st},
        {"frame": dur - 1, "value": caret_st}
    ]
    
    red_x = [{"frame": k["frame"], "value": k["value"] + 5.0} for k in center_x]
    cyan_x = [{"frame": k["frame"], "value": k["value"] - 5.0} for k in center_x]
    
    glitch_opacity = [
        {"frame": 0, "value": 0.0},
        {"frame": 32, "value": 0.0},
        {"frame": 36, "value": 0.85},
        {"frame": 50, "value": 0.85},
        {"frame": 54, "value": 0.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_12",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "12 / CARET GLITCH & CHROMA SPLIT", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#F43F5E", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#F43F5E"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "code_line", "type": "text", "text": code_txt, "size": [w + 20, 110],
                "position": [960, y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 64.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "caret_red", "type": "shape",
                "shape": {"type": "rect", "fill": [0.96, 0.25, 0.37, 1.0]},
                "size": [3.5, 68.0], "position": [0, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": red_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": glitch_opacity}
                ]}
            },
            {
                "id": "caret_cyan", "type": "shape",
                "shape": {"type": "rect", "fill": [0.0, 0.94, 1.0, 1.0]},
                "size": [3.5, 68.0], "position": [0, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": cyan_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": glitch_opacity}
                ]}
            },
            {
                "id": "caret_white", "type": "shape",
                "shape": {"type": "rect", "fill": [1.0, 1.0, 1.0, 1.0]},
                "size": [3.5, 68.0], "position": [0, y - 34.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": center_x},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_12.mp4"), "format": "mp4", "codec": "h264"}
    }

# =========================================================================
# CATEGORIA D: Prospettiva 3D, Spazio & Materiali
# =========================================================================

# -------------------------------------------------------------------------
# SCENE 13: 3D Tilt Plane (Paper Plane)
# -------------------------------------------------------------------------
def build_scene_13(dur=90):
    ptr_x = [
        {"frame": 0, "value": 860.0},
        {"frame": 12, "value": 860.0},
        {"frame": 36, "value": 980.0},
        {"frame": 82, "value": 980.0},
        {"frame": dur - 1, "value": 980.0}
    ]
    ptr_y = [
        {"frame": 0, "value": 460.0},
        {"frame": 12, "value": 460.0},
        {"frame": 36, "value": 530.0},
        {"frame": 82, "value": 530.0},
        {"frame": dur - 1, "value": 530.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_13",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.03, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "13 / 3D TILT PLANE (PAPER PLANE PROJECTION)", "size": [700, 50],
                "position": [960, 330, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#6366F1", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#6366F1"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "spatial_txt", "type": "text", "text": "Spatial Architecture", "size": [800, 110],
                "position": [960, 530, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 66.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "plane_shadow", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [0.0, 0.0, 0.0, 0.35]},
                "size": [28.0, 16.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 2.0} for k in ptr_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] + 16.0} for k in ptr_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 12, "value": 0.8}, {"frame": 82, "value": 0.8}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "plane_pointer", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 4.0, "fill": [0.39, 0.40, 0.95, 1.0]},
                "size": [18.0, 26.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 9.0} for k in ptr_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 13.0} for k in ptr_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_13.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 14: Frosted Glass Puck (visionOS Style)
# -------------------------------------------------------------------------
def build_scene_14(dur=90):
    puck_x = [
        {"frame": 0, "value": 850.0},
        {"frame": 12, "value": 850.0},
        {"frame": 36, "value": 960.0},
        {"frame": 82, "value": 960.0},
        {"frame": dur - 1, "value": 960.0}
    ]
    puck_y = [
        {"frame": 0, "value": 460.0},
        {"frame": 12, "value": 460.0},
        {"frame": 36, "value": 540.0},
        {"frame": 82, "value": 540.0},
        {"frame": dur - 1, "value": 540.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_14",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.03, 0.035, 0.05, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "14 / FROSTED GLASS PUCK (VISIONOS HOVER)", "size": [700, 50],
                "position": [960, 340, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#E2E8F0", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#FFFFFF"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "card_bg", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 24.0, "fill": [0.08, 0.10, 0.16, 0.95]},
                "size": [560.0, 220.0], "position": [960.0 - 280.0, 540.0 - 110.0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "scale", "easing": "out_back", "keyframes": [{"frame": 0, "value": [0.9, 0.9, 1.0]}, {"frame": 18, "value": [1.0, 1.0, 1.0]}]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "card_title", "type": "text", "text": "visionOS Telemetry", "size": [480, 60],
                "position": [960, 510, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 36.0, "fill": "#FFFFFF"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "card_sub", "type": "text", "text": "Latency: 0.12ms | Ray Marching Active", "size": [480, 40],
                "position": [960, 560, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 18.0, "fill": "#94A3B8"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 14, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "glass_puck", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 32.0, "fill": [1.0, 1.0, 1.0, 0.22]},
                "size": [64.0, 64.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 32.0} for k in puck_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 32.0} for k in puck_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_14.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 15: Crosshair Tactical Snapping (Precise Focus)
# -------------------------------------------------------------------------
def build_scene_15(dur=90):
    target_x, target_y = 960.0, 540.0
    
    # Crosshair arrives from (870, 480) into exact center (960, 540)
    cross_x = [
        {"frame": 0, "value": 870.0},
        {"frame": 20, "value": target_x},
        {"frame": 82, "value": target_x},
        {"frame": dur - 1, "value": target_x}
    ]
    cross_y = [
        {"frame": 0, "value": 480.0},
        {"frame": 20, "value": target_y},
        {"frame": 82, "value": target_y},
        {"frame": dur - 1, "value": target_y}
    ]
    
    tick_offset_kfs = [
        {"frame": 0, "value": 24.0},
        {"frame": 18, "value": 24.0},
        {"frame": 26, "value": 9.0},  # Sharp inward clamp on center target
        {"frame": 82, "value": 9.0},
        {"frame": dur - 1, "value": 9.0}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_15",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.035, 0.03, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "15 / CROSSHAIR TACTICAL SNAPPING", "size": [700, 50],
                "position": [960, 360, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#10B981", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#10B981"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "metric_txt", "type": "text", "text": "99.98% GPU RESIDENCY", "size": [700, 70],
                "position": [target_x, target_y, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 48.0, "fill": "#FFFFFF", "glow": {"radius": 22.0, "intensity": 0.6, "color": "#10B981"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "cross_dot", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 3.0, "fill": [0.06, 0.72, 0.51, 1.0]},
                "size": [6.0, 6.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 3.0} for k in cross_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 3.0} for k in cross_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "tick_top", "type": "shape",
                "shape": {"type": "rect", "fill": [0.06, 0.72, 0.51, 1.0]},
                "size": [2.0, 10.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 1.0} for k in cross_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": cross_y[i]["frame"], "value": cross_y[i]["value"] - tick_offset_kfs[i]["value"] - 10.0} for i in range(len(cross_y))]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "tick_bottom", "type": "shape",
                "shape": {"type": "rect", "fill": [0.06, 0.72, 0.51, 1.0]},
                "size": [2.0, 10.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "out_expo", "keyframes": [{"frame": k["frame"], "value": k["value"] - 1.0} for k in cross_x]},
                    {"property": "position_y", "easing": "out_expo", "keyframes": [{"frame": cross_y[i]["frame"], "value": cross_y[i]["value"] + tick_offset_kfs[i]["value"]} for i in range(len(cross_y))]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_15.mp4"), "format": "mp4", "codec": "h264"}
    }

# -------------------------------------------------------------------------
# SCENE 16: Dynamic Gradient Aura (Velocità -> Spettro)
# -------------------------------------------------------------------------
def build_scene_16(dur=90):
    # Centered kinetic micro-arc: starts at (870, 540), accelerates into center loop (960, 540)
    aura_x = [
        {"frame": 0, "value": 870.0},
        {"frame": 18, "value": 870.0},
        {"frame": 36, "value": 1020.0},
        {"frame": 54, "value": 960.0},
        {"frame": 82, "value": 960.0},
        {"frame": dur - 1, "value": 960.0}
    ]
    aura_y = [
        {"frame": 0, "value": 540.0},
        {"frame": 18, "value": 540.0},
        {"frame": 36, "value": 490.0},
        {"frame": 54, "value": 540.0},
        {"frame": 82, "value": 540.0},
        {"frame": dur - 1, "value": 540.0}
    ]
    
    aura_scale = [
        {"frame": 0, "value": [0.2, 0.2, 1.0]},
        {"frame": 18, "value": [0.2, 0.2, 1.0]},
        {"frame": 36, "value": [2.6, 2.6, 1.0]},
        {"frame": 54, "value": [0.2, 0.2, 1.0]},
        {"frame": dur - 1, "value": 0.2}
    ]

    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "cursor_scene_16",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": dur},
        "layers": [
            make_bg([0.025, 0.03, 0.045, 1.0], dur),
            {
                "id": "label", "type": "text", "text": "16 / DYNAMIC GRADIENT AURA (VELOCITY SPECTRUM)", "size": [700, 50],
                "position": [960, 340, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_INTER_BOLD, "font_size": 20.0, "fill": "#A855F7", "glow": {"radius": 14.0, "intensity": 0.5, "color": "#A855F7"}},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "spectrum_txt", "type": "text", "text": "Kinetic Energy -> Spectral Bloom", "size": [700, 70],
                "position": [960, 620, 0], "enable_3d": True, "start_frame": 0, "duration_frames": dur,
                "style": {"font": FONT_POPPINS_BOLD, "font_size": 36.0, "fill": "#94A3B8"},
                "animation": {"tracks": [
                    {"property": "opacity", "easing": "out_quad", "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}]}
                ]}
            },
            {
                "id": "spectral_aura", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 35.0, "fill": [0.65, 0.35, 0.98, 0.45]},
                "size": [70.0, 70.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "in_out_quad", "keyframes": [{"frame": k["frame"], "value": k["value"] - 35.0} for k in aura_x]},
                    {"property": "position_y", "easing": "in_out_quad", "keyframes": [{"frame": k["frame"], "value": k["value"] - 35.0} for k in aura_y]},
                    {"property": "scale", "easing": "out_expo", "keyframes": aura_scale},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 20, "value": 0.85}, {"frame": 54, "value": 0.0}
                    ]}
                ]}
            },
            {
                "id": "aura_core", "type": "shape",
                "shape": {"type": "rounded_rect", "radius": 8.0, "fill": [1.0, 1.0, 1.0, 1.0]},
                "size": [16.0, 16.0], "position": [0, 0], "start_frame": 0, "duration_frames": dur,
                "animation": {"tracks": [
                    {"property": "position_x", "easing": "in_out_quad", "keyframes": [{"frame": k["frame"], "value": k["value"] - 8.0} for k in aura_x]},
                    {"property": "position_y", "easing": "in_out_quad", "keyframes": [{"frame": k["frame"], "value": k["value"] - 8.0} for k in aura_y]},
                    {"property": "opacity", "easing": "out_quad", "keyframes": [
                        {"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}, {"frame": 82, "value": 1.0}, {"frame": dur - 1, "value": 0.0}
                    ]}
                ]}
            }
        ],
        "output": {"path": str(OUT_DIR / "cursor_scene_16.mp4"), "format": "mp4", "codec": "h264"}
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
    build_scene_13,
    build_scene_14,
    build_scene_15,
    build_scene_16,
]

def main():
    print(f"Emitting all 16 Centered Cursor plans to {OUT_DIR}...")
    for idx, builder in enumerate(BUILDERS, 1):
        plan = builder()
        plan_path = OUT_DIR / f"cursor_scene_{idx:02d}.plan.json"
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"  [Scene {idx:02d}] Wrote {plan_path.name}")
    print("All 16 centered cursor plans emitted successfully!")

if __name__ == "__main__":
    main()
