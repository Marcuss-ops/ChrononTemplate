#!/usr/bin/env python3
"""
render_editorial_didone_canary.py
Production reference-matching renderer for # editorial_didone_titles_v1.

Comprehensive Optical Finishing & Kinematics Architecture:
1. Exact reference mapping:
   - ref1.png -> Scene 1: didone_title_red_bar_reveal ("Non poteva accettare / ciò che era" + red bar)
   - ref3.png -> Scene 2: didone_checklist_stagger ("Ferrovie ✓ / Oleodotti ✓ / Raffinerie ✓" in #FF1018 on deep burgundy)
   - ref2.png -> Scene 3: didone_inline_emphasis ("Non accettare / la propria / condizione." with "accettare" in #FF1018)
   - ref4.png -> Scene 4: didone_hero_statement ("è il valore più grande / di ogni business" with "ogni business" in #FF1018)
2. Pinned Didone Face:
   - didone_font_playfair_display_italic.ttf — use the selected Playfair Display Italic face without synthetic weight or glyph dilation.
3. Auto-fit / Responsive Bounds:
   - Typography fills 76%–87% of viewport width edge-to-edge, matching editorial documentary hero statements.
   - Tight negative tracking (-2.5px to -3.5px) for magazine-grade letter proximity.
4. Optical Finishing Pass:
   - High-threshold, low-intensity bloom on cream highlights; clean red glyphs have no alpha-mask halo.
   - Fine native grain and a restrained radial vignette; no CPU post-render grain filter.
   - Flat text and shape planes preserve the aligned layout; perspective is not faked with per-layer tilt.
5. Strict Animation Convergence:
   - Every additive motion offset decays strictly to 0.0 at resting pose (progress = 1.0 -> offset = 0, opacity = 1.0).
6. Deliverables:
   - 4 individual 5s MP4s (150 frames @ 30fps), 20s master reel, milestone step frames and side-by-side comparisons.
     Google Drive upload requires the explicit --upload flag.
"""

import argparse
import os
import sys
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont

CLI_PATH = os.path.abspath("Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
if not os.path.exists(CLI_PATH):
    CLI_PATH = os.path.abspath("Chronon3d/build/chronon/linux-release-validation/apps/chronon3d_cli/chronon3d_cli")

ASSETS_ROOT = os.path.abspath("ChrononTemplate")
FONT_BLACK_REL = "assets/fonts/didone_font_playfair_display_italic.ttf"
FONT_BLACK_ABS = os.path.join(ASSETS_ROOT, FONT_BLACK_REL)

OUT_DIR = os.path.abspath("ChrononTemplate/out/editorial_didone_reference_match_v1")
REF_DIR = os.path.abspath("assets/references_didone")

os.makedirs(OUT_DIR, exist_ok=True)

# Unified Style Tokens
RED_HEX = "#FF1018"
WHITE_CREAM_HEX = "#F7F4EF"
RED_RGBA = [0.988, 0.063, 0.094, 1.0]

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_FRAMES = 150  # 5.0 seconds at 30 fps

# Canonical closed filled polygon checkmark path (scaled)
CHECK_SCALE = 1.45
CHECK_PATH = [
    {"type": "move_to", "point": [-24.0 * CHECK_SCALE, -2.0 * CHECK_SCALE]},
    {"type": "line_to", "point": [-6.0 * CHECK_SCALE, 24.0 * CHECK_SCALE]},
    {"type": "line_to", "point": [38.0 * CHECK_SCALE, -24.0 * CHECK_SCALE]},
    {"type": "line_to", "point": [32.0 * CHECK_SCALE, -29.0 * CHECK_SCALE]},
    {"type": "line_to", "point": [-6.0 * CHECK_SCALE, 14.0 * CHECK_SCALE]},
    {"type": "line_to", "point": [-19.0 * CHECK_SCALE, -7.0 * CHECK_SCALE]},
    {"type": "close"}
]


def make_track(prop, easing, kf_list):
    """Creates an animation track with strictly sorted and deduplicated keyframes."""
    seen_frames = {}
    for item in kf_list:
        seen_frames[item["frame"]] = item["value"]
    unique_kfs = [{"frame": f, "value": seen_frames[f]} for f in sorted(seen_frames.keys())]
    return {
        "property": prop,
        "easing": easing,
        "keyframes": unique_kfs
    }


def compute_autofit_font_size(font_path, text, target_width, min_sz=50, max_sz=350):
    """Auto-fit font size calculation ensuring precise target bounding box occupancy."""
    test_font = ImageFont.truetype(font_path, 100)
    test_w = test_font.getlength(text)
    if test_w <= 0:
        return 100
    est = int(round(100.0 * (target_width / test_w)))
    refined_font = ImageFont.truetype(font_path, est)
    refined_w = refined_font.getlength(text)
    if refined_w > 0:
        est = int(round(est * (target_width / refined_w)))
    return max(min_sz, min(max_sz, est))


def make_text_layer(layer_id, text, size, pos, font_path, font_size, fill_color,
                    tracking=-2.5, effects=None, animation=None, enable_3d=False):
    """Build a flat Chronon text layer with explicit tracking and optional effects."""
    byte_len = len(text.encode("utf-8"))
    layer = {
        "id": layer_id,
        "type": "text",
        "text": text,
        "size": size,
        "position": pos,
        "start_frame": 0,
        "duration_frames": DURATION_FRAMES,
        "enable_3d": enable_3d,
        "style": {
            "font": font_path,
            "font_size": font_size,
            "fill": fill_color
        },
        "spans": [
            {"start": 0, "end": byte_len, "style": {"tracking": tracking}}
        ]
    }
    if effects:
        layer["effects"] = effects
    if animation:
        layer["animation"] = animation
    return layer


# ── SCENE PLANS ──────────────────────────────────────────────────────────────

def make_scene1_plan():
    """
    Scene 1: didone_title_red_bar_reveal (Ref 1: ref1.png)
    "Non poteva accettare" (top line, 77% width)
    "ciò che era" (bottom hero line, 81% width)
    Red highlight bar behind the bottom text with a left-to-right wipe.
    Atmosphere: native fine grain + radial vignette.
    """
    font_path = FONT_BLACK_ABS
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Pinned Didone font is missing: {font_path}")
    target_w0 = WIDTH * 0.77
    target_w1 = WIDTH * 0.81
    fs0 = compute_autofit_font_size(font_path, "Non poteva accettare", target_w0)
    fs1 = compute_autofit_font_size(font_path, "ciò che era", target_w1)

    center_x = 960
    line0_y = 390
    line1_y = 585

    font1 = ImageFont.truetype(font_path, fs1)
    actual_w1 = font1.getlength("ciò che era")
    bar_w = actual_w1 + 50.0
    bar_h = fs1 * 0.38
    bar_y = line1_y + fs1 * 0.12

    layers = [
        # Background: Atmospheric dark charcoal with film grain and radial vignette
        {
            "id": "bg",
            "type": "shape",
            "size": [WIDTH, HEIGHT],
            "position": [WIDTH / 2, HEIGHT / 2],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "shape": {
                "type": "rect",
                "fill": [0.004, 0.004, 0.005, 1.0]
            },
            "effects": [
                {"type": "vignette", "radius": 0.58, "softness": 0.55, "amount": 0.30},
                {"type": "noise", "amount": 0.008, "size": 1.0, "color_mode": "monochrome"}
            ]
        },
        # Red Highlight Bar: behind text, reveals from a fixed left edge
        {
            "id": "red_bar",
            "type": "shape",
            "size": [bar_w, bar_h],
            "position": [center_x, bar_y],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "enable_3d": False,
            "shape": {
                "type": "rect",
                "fill": RED_RGBA
            },
            "animation": {
                "tracks": [
                    make_track("scale_x", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 8, "value": 0.0},
                        {"frame": 26, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ]),
                    make_track("position_x", "out_cubic", [
                        {"frame": 0, "value": -bar_w / 2.0},
                        {"frame": 8, "value": -bar_w / 2.0},
                        {"frame": 26, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "linear", [
                        {"frame": 0, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            }
        },
        # Top Line: "Non poteva accettare" (white cream with restrained bloom)
        make_text_layer(
            "line0", "Non poteva accettare", [1850, 220], [center_x, line0_y],
            FONT_BLACK_REL, fs0, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 35.0},
                        {"frame": 18, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 18, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Hero Line: "ciò che era" (oversized, lowercase accent with restrained bloom)
        make_text_layer(
            "line1", "ciò che era", [1850, 360], [center_x, line1_y],
            FONT_BLACK_REL, fs1, WHITE_CREAM_HEX, tracking=-2.0,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 16.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 45.0},
                        {"frame": 10, "value": 45.0},
                        {"frame": 30, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 10, "value": 0.0},
                        {"frame": 30, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        )
    ]

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "didone_scene1_red_bar_reveal",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "output": {
            "path": os.path.join(OUT_DIR, "scene1_didone_title_red_bar_reveal.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": layers
    }
    return plan


def make_scene2_plan():
    """
    Scene 2: didone_checklist_stagger (Ref 3: ref3.png)
    "Ferrovie ✓ / Oleodotti ✓ / Raffinerie ✓"
    All words and checkmarks rendered in vibrant editorial red (#FF1018) with optical glow.
    Background: Rich deep burgundy (#140205) with subtle grain and vignette.
    """
    font_path = FONT_BLACK_ABS
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Pinned Didone font is missing: {font_path}")
    font_size = 158
    font = ImageFont.truetype(font_path, font_size)

    w_fer = font.getlength("Ferrovie")
    w_ole = font.getlength("Oleodotti")
    w_raf = font.getlength("Raffinerie")

    base_x = 225
    y0, y1, y2 = 180, 540, 900

    items = [
        ("Ferrovie", base_x + w_fer / 2.0, y0, base_x + w_fer + 75.0, y0 - 5.0, 0, 18, 16, 26),
        ("Oleodotti", base_x + w_ole / 2.0, y1, base_x + w_ole + 75.0, y1 - 5.0, 20, 38, 36, 46),
        ("Raffinerie", base_x + w_raf / 2.0, y2, base_x + w_raf + 75.0, y2 - 5.0, 40, 58, 56, 66)
    ]

    layers = [
        # Background: Deep rich burgundy with atmospheric vignette and fine grain
        {
            "id": "bg",
            "type": "shape",
            "size": [WIDTH, HEIGHT],
            "position": [WIDTH / 2, HEIGHT / 2],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "shape": {
                "type": "rect",
                "fill": [0.075, 0.012, 0.018, 1.0]  # Deep burgundy
            },
            "effects": [
                {"type": "vignette", "radius": 0.55, "softness": 0.55, "amount": 0.30},
                {"type": "noise", "amount": 0.008, "size": 1.0, "color_mode": "monochrome"}
            ]
        }
    ]

    for i, (text_str, tx, ty, cx, cy, t_start, t_end, c_start, c_end) in enumerate(items):
        # Text layer with red glow
        layers.append(
            make_text_layer(
                f"text_{i}", text_str, [1000, 220], [tx, ty],
                FONT_BLACK_REL, font_size, RED_HEX, tracking=-2.5,
                effects=[{"type": "glow", "radius": 24.0, "intensity": 0.08, "color": [1.0, 0.06, 0.09, 1.0]}],
                animation={
                    "tracks": [
                        make_track("position_y", "out_cubic", [
                            {"frame": 0, "value": 30.0},
                            {"frame": t_start, "value": 30.0},
                            {"frame": t_end, "value": 0.0},
                            {"frame": DURATION_FRAMES - 1, "value": 0.0}
                        ]),
                        make_track("opacity", "out_cubic", [
                            {"frame": 0, "value": 0.0},
                            {"frame": t_start, "value": 0.0},
                            {"frame": t_end, "value": 1.0},
                            {"frame": DURATION_FRAMES - 1, "value": 1.0}
                        ])
                    ]
                },
            )
        )

        # Checkmark layer: closed polygon path with red glow
        layers.append({
            "id": f"check_{i}",
            "type": "shape",
            "size": [WIDTH, HEIGHT],
            "position": [cx, cy],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "enable_3d": False,
            "shape": {
                "type": "path",
                "path": CHECK_PATH,
                "fill": [1.0, 0.063, 0.094, 1.0]
            },
            "effects": [{"type": "glow", "radius": 22.0, "intensity": 0.07, "color": [1.0, 0.06, 0.09, 1.0]}],
            "animation": {
                "tracks": [
                    make_track("scale_x", "out_back", [
                        {"frame": 0, "value": 0.0},
                        {"frame": c_start, "value": 0.0},
                        {"frame": c_end, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ]),
                    make_track("scale_y", "out_back", [
                        {"frame": 0, "value": 0.0},
                        {"frame": c_start, "value": 0.0},
                        {"frame": c_end, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ]),
                    make_track("opacity", "linear", [
                        {"frame": 0, "value": 0.0},
                        {"frame": c_start, "value": 0.0},
                        {"frame": min(c_start + 3, DURATION_FRAMES - 1), "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            }
        })

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "didone_scene2_checklist_stagger",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "output": {
            "path": os.path.join(OUT_DIR, "scene2_didone_checklist_stagger.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": layers
    }
    return plan


def make_scene3_plan():
    """
    Scene 3: didone_inline_emphasis (Ref 2: ref2.png)
    "Non accettare / la propria / condizione."
    Line 0: "Non " (white cream with bloom) + "accettare" (red #FF1018 with red glow).
    Oversized layout (82% width), subpixel tracking, dark slate paper with grain & vignette.
    """
    font_path = FONT_BLACK_ABS
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Pinned Didone font is missing: {font_path}")
    target_w = WIDTH * 0.82
    font_size = compute_autofit_font_size(font_path, "Non accettare", target_w)
    font = ImageFont.truetype(font_path, font_size)

    w0_full = font.getlength("Non accettare")
    w0_non = font.getlength("Non")
    w0_space = font.getlength(" ")
    w0_acc = font.getlength("accettare")

    x0_left = 960.0 - w0_full / 2.0
    x0_non = x0_left + w0_non / 2.0
    x0_acc = (x0_left + w0_non + w0_space) + w0_acc / 2.0

    line0_y = 330
    line1_y = 535
    line2_y = 740

    layers = [
        # Background: restrained charcoal field with native fine grain and vignette
        {
            "id": "bg",
            "type": "shape",
            "size": [WIDTH, HEIGHT],
            "position": [WIDTH / 2, HEIGHT / 2],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "shape": {
                "type": "rect",
                "fill": [0.004, 0.004, 0.005, 1.0]
            },
            "effects": [
                {"type": "vignette", "radius": 0.58, "softness": 0.55, "amount": 0.30},
                {"type": "noise", "amount": 0.008, "size": 1.0, "color_mode": "monochrome"}
            ]
        },
        # Line 0 - Part 1: "Non" (white cream with bloom)
        make_text_layer(
            "line0_non", "Non", [1850, 280], [x0_non, line0_y],
            FONT_BLACK_REL, font_size, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 35.0},
                        {"frame": 20, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 20, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Line 0 - Part 2: "accettare" (editorial red with rich glow)
        make_text_layer(
            "line0_acc", "accettare", [1850, 280], [x0_acc, line0_y],
            FONT_BLACK_REL, font_size, RED_HEX, tracking=-2.5,
                        animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 35.0},
                        {"frame": 20, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 20, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Line 1: "la propria" (white cream with bloom)
        make_text_layer(
            "line1", "la propria", [1850, 280], [960, line1_y],
            FONT_BLACK_REL, font_size, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 35.0},
                        {"frame": 14, "value": 35.0},
                        {"frame": 34, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 14, "value": 0.0},
                        {"frame": 34, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Line 2: "condizione." (white cream with bloom)
        make_text_layer(
            "line2", "condizione.", [1850, 280], [960, line2_y],
            FONT_BLACK_REL, font_size, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 35.0},
                        {"frame": 28, "value": 35.0},
                        {"frame": 48, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 28, "value": 0.0},
                        {"frame": 48, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        )
    ]

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "didone_scene3_inline_emphasis",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "output": {
            "path": os.path.join(OUT_DIR, "scene3_didone_inline_emphasis.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": layers
    }
    return plan


def make_scene4_plan():
    """
    Scene 4: didone_hero_statement (Ref 4: ref4.png)
    "è il valore più grande / di ogni business"
    Line 0: "è il valore più grande" (87% viewport width)
    Line 1: "di " (white cream) + "ogni business" (red #FF1018 with optical glow)
    Atmospheric cinematic dark charcoal with film grain, vignette, and micro 3D tilt.
    """
    font_path = FONT_BLACK_ABS
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Pinned Didone font is missing: {font_path}")
    target_w0 = WIDTH * 0.87
    target_w1 = WIDTH * 0.84
    fs0 = compute_autofit_font_size(font_path, "è il valore più grande", target_w0)
    fs1 = compute_autofit_font_size(font_path, "di ogni business", target_w1)

    font1 = ImageFont.truetype(font_path, fs1)
    w1_full = font1.getlength("di ogni business")
    w1_di = font1.getlength("di")
    w1_space = font1.getlength(" ")
    w1_ob = font1.getlength("ogni business")

    x1_left = 960.0 - w1_full / 2.0
    x1_di = x1_left + w1_di / 2.0
    x1_ob = (x1_left + w1_di + w1_space) + w1_ob / 2.0

    line0_y = 410
    line1_y = 635

    layers = [
        # Background: Atmospheric cinematic dark charcoal
        {
            "id": "bg",
            "type": "shape",
            "size": [WIDTH, HEIGHT],
            "position": [WIDTH / 2, HEIGHT / 2],
            "start_frame": 0,
            "duration_frames": DURATION_FRAMES,
            "shape": {
                "type": "rect",
                "fill": [0.004, 0.004, 0.005, 1.0]
            },
            "effects": [
                {"type": "vignette", "radius": 0.60, "softness": 0.55, "amount": 0.30},
                {"type": "noise", "amount": 0.008, "size": 1.0, "color_mode": "monochrome"}
            ]
        },
        # Line 0: "è il valore più grande" (oversized, white cream with bloom)
        make_text_layer(
            "line0", "è il valore più grande", [1880, 260], [960, line0_y],
            FONT_BLACK_REL, fs0, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 40.0},
                        {"frame": 22, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 22, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Line 1 - Part 1: "di" (white cream with bloom)
        make_text_layer(
            "line1_di", "di", [1880, 280], [x1_di, line1_y],
            FONT_BLACK_REL, fs1, WHITE_CREAM_HEX, tracking=-2.5,
            effects=[{"type": "bloom", "threshold": 0.90, "radius": 14.0, "intensity": 0.16}],
            animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 40.0},
                        {"frame": 14, "value": 40.0},
                        {"frame": 36, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 14, "value": 0.0},
                        {"frame": 36, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        ),
        # Line 1 - Part 2: "ogni business" (editorial red with rich optical glow)
        make_text_layer(
            "line1_ob", "ogni business", [1880, 280], [x1_ob, line1_y],
            FONT_BLACK_REL, fs1, RED_HEX, tracking=-2.5,
                        animation={
                "tracks": [
                    make_track("position_y", "out_cubic", [
                        {"frame": 0, "value": 40.0},
                        {"frame": 14, "value": 40.0},
                        {"frame": 36, "value": 0.0},
                        {"frame": DURATION_FRAMES - 1, "value": 0.0}
                    ]),
                    make_track("opacity", "out_cubic", [
                        {"frame": 0, "value": 0.0},
                        {"frame": 14, "value": 0.0},
                        {"frame": 36, "value": 1.0},
                        {"frame": DURATION_FRAMES - 1, "value": 1.0}
                    ])
                ]
            },
        )
    ]

    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "didone_scene4_hero_statement",
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": DURATION_FRAMES
        },
        "output": {
            "path": os.path.join(OUT_DIR, "scene4_didone_hero_statement.mp4"),
            "format": "mp4",
            "codec": "h264"
        },
        "layers": layers
    }
    return plan


# ── RENDER & COMPOSITING PIPELINE ───────────────────────────────────────────

def render_scene(plan, scene_idx, scene_name):
    plan_path = os.path.join(OUT_DIR, f"scene{scene_idx}_{scene_name}.plan.json")
    mp4_path = os.path.join(OUT_DIR, f"scene{scene_idx}_{scene_name}.mp4")

    plan["output"] = {
        "path": mp4_path,
        "format": "mp4",
        "codec": "h264"
    }

    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)

    cmd = [
        CLI_PATH,
        "render",
        "--plan", plan_path,
        "--assets-root", ASSETS_ROOT,
        "--backend", "vulkan",
        "--gpu-hot-path-mode", "auto",
        "--hardware", "none",
        "--encoder-backend", "pipe",
        "-o", mp4_path
    ]
    print(f"[*] Rendering Scene {scene_idx} ({scene_name}) to MP4 (150 frames @ 30fps)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(mp4_path):
        print(f"[!] Error rendering scene {scene_idx}:")
        print(res.stderr)
        print(res.stdout)
        raise RuntimeError(f"Render failed for scene {scene_idx}")

    file_sz = os.path.getsize(mp4_path)
    print(f"[+] Rendered MP4: {mp4_path} ({file_sz} bytes)")

    # Film grain is authored as a native layer effect in the render plan.
    # Do not re-encode through a CPU noise filter after the Vulkan render.

    # Extract milestone step frames: 0%, 25%, 50%, 100%
    step_frames = {}
    timestamps = [
        ("0pct", "00:00:00.000"),
        ("25pct", "00:00:01.250"),
        ("50pct", "00:00:02.500"),
        ("100pct", "00:00:04.900")
    ]
    for tag, ts in timestamps:
        frame_out = os.path.join(OUT_DIR, f"scene{scene_idx}_{scene_name}_{tag}.png")
        sub_cmd = [
            "ffmpeg", "-y",
            "-ss", ts,
            "-i", mp4_path,
            "-vframes", "1",
            frame_out
        ]
        subprocess.run(sub_cmd, capture_output=True, check=True)
        step_frames[tag] = frame_out

    return mp4_path, step_frames


def create_side_by_side(ref_path, rendered_path, out_composite_path, title):
    """
    Creates a clean side-by-side composite comparing Reference Target vs Optical Chronon Render.
    """
    ref_img = Image.open(ref_path).convert("RGBA")
    rend_img = Image.open(rendered_path).convert("RGBA")

    target_h = 540
    ref_scale = target_h / ref_img.height
    ref_w = int(ref_img.width * ref_scale)
    ref_resized = ref_img.resize((ref_w, target_h), Image.Resampling.LANCZOS)

    rend_scale = target_h / rend_img.height
    rend_w = int(rend_img.width * rend_scale)
    rend_resized = rend_img.resize((rend_w, target_h), Image.Resampling.LANCZOS)

    header_h = 60
    total_w = ref_w + rend_w + 30
    total_h = target_h + header_h + 30

    composite = Image.new("RGBA", (total_w, total_h), (16, 16, 18, 255))
    draw = ImageDraw.Draw(composite)

    # Labels
    draw.text((20, 18), f"REFERENCE TARGET ({title})", fill=(200, 200, 200, 255))
    draw.text((ref_w + 35, 18), f"CHRONON Vulkan (Playfair Display Italic; restrained optical finish)", fill=(255, 60, 65, 255))

    # Paste images
    composite.paste(ref_resized, (15, header_h))
    composite.paste(rend_resized, (ref_w + 30, header_h))

    # Borders
    draw.rectangle([14, header_h - 1, 15 + ref_w, header_h + target_h], outline=(60, 60, 60, 255), width=1)
    draw.rectangle([ref_w + 29, header_h - 1, ref_w + 30 + rend_w, header_h + target_h], outline=(255, 16, 24, 255), width=2)

    composite.save(out_composite_path)
    print(f"[+] Saved comparison composite: {out_composite_path}")


def upload_to_drive(file_path, folder_id="1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"):
    uploader = os.path.abspath("RenderingGen/bin/drive-upload")
    cred = "/home/pierone/.config/velox/credentials.json"
    tok = "/home/pierone/.config/velox/token.json"
    if not os.path.exists(uploader):
        print(f"[!] Drive uploader not found at {uploader}")
        return None
    cmd = [
        uploader,
        "-credentials", cred,
        "-token", tok,
        "-folder", folder_id,
        "-file", file_path
    ]
    print(f"[*] Uploading {os.path.basename(file_path)} to Drive folder {folder_id}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Upload error: {res.stderr}")
        return None
    out = res.stdout.strip()
    print(f"[+] {out}")
    return out


def concat_master_video(video_files, out_master_path):
    """
    Concatenates the 4 individual 5s MP4 videos into a single 20s master reel.
    """
    concat_list = os.path.join(OUT_DIR, "concat_list.txt")
    with open(concat_list, "w") as f:
        for vf in video_files:
            f.write(f"file '{vf}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        out_master_path
    ]
    print(f"[*] Assembling master video: {out_master_path}...")
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"[+] Master video created: {out_master_path} ({os.path.getsize(out_master_path)} bytes)")
    return out_master_path


def main():
    parser = argparse.ArgumentParser(description="Render and locally verify the Didone reference canary")
    parser.add_argument("--upload", action="store_true",
                        help="explicitly upload verified deliverables to Google Drive")
    args = parser.parse_args()

    print("=== Editorial Didone Titles Canary v6 (reference matched) ===")
    print("Typography: Playfair Display Italic | Vulkan render graph + pipe encoder | restrained glow | radial paper + grain")
    print("-------------------------------------------------------------------------------")
    scenes = [
        (1, make_scene1_plan(), os.path.join(REF_DIR, "ref1.png"), "didone_title_red_bar_reveal"),
        (2, make_scene2_plan(), os.path.join(REF_DIR, "ref3.png"), "didone_checklist_stagger"),
        (3, make_scene3_plan(), os.path.join(REF_DIR, "ref2.png"), "didone_inline_emphasis"),
        (4, make_scene4_plan(), os.path.join(REF_DIR, "ref4.png"), "didone_hero_statement"),
    ]

    video_files = []
    comparisons = []
    frames_to_upload = []

    for idx, plan, ref_path, name in scenes:
        mp4_path, step_frames = render_scene(plan, idx, name)
        video_files.append(mp4_path)

        final_frame = step_frames["100pct"]
        comp_path = os.path.join(OUT_DIR, f"comparison_scene{idx}_{name}.png")
        create_side_by_side(ref_path, final_frame, comp_path, name)
        comparisons.append(comp_path)

        frames_to_upload.append(step_frames["0pct"])
        frames_to_upload.append(step_frames["25pct"])
        frames_to_upload.append(step_frames["50pct"])
        frames_to_upload.append(step_frames["100pct"])

    # Assemble the 20-second Master Reel
    master_mp4 = os.path.join(OUT_DIR, "editorial_didone_4scenes_master_20s.mp4")
    concat_master_video(video_files, master_mp4)

    print("\n[✓] All 4 Didone Canary reference matches rendered and composited with optical finish!")
    for c in comparisons:
        print(f"  - {c}")

    if args.upload:
        drive_folder = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
        print(f"\n[*] Uploading results to Google Drive folder: {drive_folder}")
        upload_manifest = []
        all_artifacts = comparisons + [master_mp4] + video_files + frames_to_upload
        for item in all_artifacts:
            if os.path.exists(item):
                res = upload_to_drive(item, drive_folder)
                if res:
                    upload_manifest.append(res)
        with open(os.path.join(OUT_DIR, "drive_upload_manifest.txt"), "w") as f:
            f.write("\n".join(upload_manifest) + "\n")
        print(f"[✓] Completed upload of {len(upload_manifest)} items to Drive.")
    else:
        print("[*] Local render complete; Drive upload was not requested (pass --upload to opt in).")


if __name__ == "__main__":
    main()
