#!/usr/bin/env python3
"""Visual Accents V1 — family galleries and their sequential canaries.

Emits seven self-contained chronon.render-plan.v3 documents (1920x1080, 30fps)
that exercise the whole 48-motion vocabulary plus the supporting primitives:

    canary_brush_v1        12 brush traits over a document scene
    canary_web_rect_v1     12 web cards over a browser scene
    canary_paint_v1        12 field-mask reveals over a photo scene
    canary_light_leak_v1   12 leak plates over a mixed-content scene
    canary_abstract_background_v1  10 procedural field backgrounds
    canary_abstract_background_torture_v1  continuous cross-fade stress plan
    canary_visual_accents_mega  the 15-20s mega canary (48 motions across scenes)

The galleries write plans only; rendering happens through chronon3d_cli
(validate + render --backend software) so every frame passes the same
deterministic software rasterizer the certified batches use.

Usage:
    tools/backgrounds/render_visual_accents_canary.py --plans      write the plans
    tools/backgrounds/render_visual_accents_canary.py --validate   write + validate plans
    tools/backgrounds/render_visual_accents_canary.py --render     write + validate + render
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI_CANDIDATES = (
    REPO / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    REPO / "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)
CLI = next((candidate for candidate in CLI_CANDIDATES if candidate.is_file()), CLI_CANDIDATES[0])
ASSETS = REPO / "Chronon3d"
OUT = REPO / "ChrononTemplate/out/visual_accents_v1"

W, H, FPS = 1920, 1080, 30


def base_plan(job_id, frames, layers, output_name):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": job_id,
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": frames},
        "output": {"path": str(OUT / output_name), "format": "mp4", "codec": "h264"},
        "layers": layers,
    }


def rect_layer(layer_id, size, position, fill, frames, radius=0.0, stroke=None,
               opacity=None, blend=None, effects=None, tracks=None, masks=None):
    layer = {
        "id": layer_id, "type": "shape",
        "size": list(size), "position": list(position),
        "start_frame": 0, "duration_frames": frames,
        "shape": {"type": "rect", "fill": fill},
    }
    if masks:
        layer["masks"] = masks
    if radius:
        layer["shape"]["radius"] = radius
    if stroke:
        layer["shape"]["stroke"] = stroke
    if opacity is not None:
        layer["opacity"] = opacity
    if blend:
        layer["blend_mode"] = blend
    if effects:
        layer["effects"] = effects
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def path_layer(layer_id, size, position, commands, stroke, frames, trim=None,
               opacity=None, blend=None, tracks=None, effects=None):
    layer = {
        "id": layer_id, "type": "shape",
        "size": list(size), "position": list(position),
        "start_frame": 0, "duration_frames": frames,
        "shape": {"type": "path", "path": commands, "stroke": stroke},
    }
    if trim:
        # Accept the {start, end, animation} form or a bare animation dict.
        animation = trim.get("animation", trim)
        params = {"start": trim.get("start", 0.0), "end": trim.get("end", 1.0),
                  "animation": animation}
        layer["shape"]["operators"] = [{"kind": "trim", "params": params}]
    if opacity is not None:
        layer["opacity"] = opacity
    if blend:
        layer["blend_mode"] = blend
    if effects:
        layer["effects"] = effects
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def ellipse_glow(layer_id, size, position, fill, frames, opacity=0.8,
                 effects=None, tracks=None, blend=None):
    layer = {
        "id": layer_id, "type": "shape",
        "size": list(size), "position": list(position),
        "start_frame": 0, "duration_frames": frames,
        "shape": {"type": "ellipse", "fill": fill},
        "opacity": opacity,
        "effects": effects or [
            {"type": "gaussian_blur", "radius": 96},
            {"type": "glow", "radius": 64, "intensity": 0.5,
             "color": [1.0, 0.8, 0.5, 1.0]},
        ],
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if blend:
        layer["blend_mode"] = blend
    return layer


def text_layer(layer_id, text, size, position, font_size, color, frames,
               font="assets/fonts/Inter-Bold.ttf", opacity=None, effects=None):
    layer = {
        "id": layer_id, "type": "text", "text": text,
        "size": list(size), "position": list(position),
        "start_frame": 0, "duration_frames": frames,
        "style": {"font": font, "font_size": font_size, "fill": color},
    }
    if opacity is not None:
        layer["opacity"] = opacity
    if effects:
        layer["effects"] = effects
    return layer


def trim_keys(draw_frames, total):
    return {"easing": "in_out_quad", "keyframes": [
        {"frame": 0, "value": 0.0},
        {"frame": draw_frames, "value": 1.0},
        {"frame": total, "value": 1.0},
    ]}


def fade_keys(enter, total, peak=1.0):
    return {"easing": "out_cubic", "keyframes": [
        {"frame": 0, "value": 0.0},
        {"frame": enter, "value": peak},
        {"frame": total, "value": peak},
    ]}


def line_commands(width):
    return [
        {"type": "move_to", "point": [-width / 2, 0]},
        {"type": "line_to", "point": [width / 2, 0]},
    ]


def circle_commands(radius):
    k = 0.5522847498 * radius
    return [
        {"type": "move_to", "point": [0, -radius]},
        {"type": "cubic_to", "control1": [k, -radius], "control2": [radius, -k], "point": [radius, 0]},
        {"type": "cubic_to", "control1": [radius, k], "control2": [k, radius], "point": [0, radius]},
        {"type": "cubic_to", "control1": [-k, radius], "control2": [-radius, k], "point": [-radius, 0]},
        {"type": "cubic_to", "control1": [-radius, -k], "control2": [-k, -radius], "point": [0, -radius]},
        {"type": "close"},
    ]


def rounded_rect_commands(width, height, radius):
    x0, x1, y0, y1 = -width / 2, width / 2, -height / 2, height / 2
    k = 0.5522847498 * radius
    return [
        {"type": "move_to", "point": [x0 + radius, y0]},
        {"type": "line_to", "point": [x1 - radius, y0]},
        {"type": "cubic_to", "control1": [x1 - radius + k, y0], "control2": [x1, y0 + radius - k], "point": [x1, y0 + radius]},
        {"type": "line_to", "point": [x1, y1 - radius]},
        {"type": "cubic_to", "control1": [x1, y1 - radius + k], "control2": [x1 - radius + k, y1], "point": [x1 - radius, y1]},
        {"type": "line_to", "point": [x0 + radius, y1]},
        {"type": "cubic_to", "control1": [x0 + radius - k, y1], "control2": [x0, y1 - radius + k], "point": [x0, y1 - radius]},
        {"type": "line_to", "point": [x0, y0 + radius]},
        {"type": "cubic_to", "control1": [x0, y0 + radius - k], "control2": [x0 + radius - k, y0], "point": [x0 + radius, y0]},
        {"type": "close"},
    ]


def check_commands(size):
    s = size / 2
    return [
        {"type": "move_to", "point": [-s, 0]},
        {"type": "line_to", "point": [-s * 0.2, s * 0.7]},
        {"type": "line_to", "point": [s, -s * 0.7]},
    ]


def cross_commands(size):
    s = size / 2
    return [
        {"type": "move_to", "point": [-s, -s]}, {"type": "line_to", "point": [s, s]},
        {"type": "move_to", "point": [s, -s]}, {"type": "line_to", "point": [-s, s]},
        {"type": "close"},
    ]


def wave_commands(width, amplitude, periods=2):
    commands = [{"type": "move_to", "point": [-width / 2, 0]}]
    steps = periods * 8
    import math
    for i in range(1, steps + 1):
        x = -width / 2 + width * i / steps
        y = math.sin(i / steps * periods * 2 * math.pi) * amplitude
        commands.append({"type": "line_to", "point": [x, y]})
    return commands


def field_mask(seed, generator, feather, enter, hold, frequency=3.0, octaves=4,
               operators=None, width=420, height=240):
    field = {"generator": generator, "seed": seed, "frequency": frequency}
    if octaves != 4:
        field["octaves"] = octaves
    if operators:
        field["operators"] = operators
    return {
        "type": "field", "mode": "add", "feather": feather,
        "size": [width, height],
        "field": field,
        "expansion_track": {"keyframes": [
            {"frame": 0, "value": -(2.0 + feather)},
            {"frame": enter, "value": 0.0},
            {"frame": enter + hold, "value": 0.0}]},
        "opacity_track": {"keyframes": [
            {"frame": 0, "value": 0.0},
            {"frame": enter, "value": 1.0},
            {"frame": enter + hold, "value": 1.0}]},
    }


def abstract_neon_ramp():
    return {
        "type": "linear", "start": [0.0, 0.5], "end": [1.0, 0.5],
        "color_stops": [
            {"position": 0.0, "color": [0.015, 0.025, 0.16, 1.0]},
            {"position": 0.32, "color": [0.24, 0.035, 0.58, 1.0]},
            {"position": 0.62, "color": [0.88, 0.055, 0.68, 1.0]},
            {"position": 0.82, "color": [0.12, 0.7, 0.94, 1.0]},
            {"position": 1.0, "color": [1.0, 0.68, 0.92, 1.0]},
        ],
    }


# ── Gallery 1: brush_v1 ─────────────────────────────────────────────────────


def brush_gallery():
    frames = 12 * 90  # 12 traits x 3s each
    ink = {"color": "#0F172A", "width": 6}
    layers = [
        rect_layer("paper", [W, H], [W / 2, H / 2], [0.97, 0.98, 0.99, 1], frames),
        text_layer("doc", "Revenue increased by 42%", [1400, 120], [W / 2, H / 2 - 200],
                   64, "#0F172A", frames, font="assets/fonts/Poppins-Bold.ttf"),
    ]
    trait_specs = [
        ("marker", "multiply", "#FACC15", 64, line_commands(360), 46, 26),
        ("underline", "normal", "#0F172A", 6, line_commands(420), 42, 24),
        ("circle", "normal", "#0F172A", 6, circle_commands(200), 44, 26),
        ("arrow", "normal", "#0F172A", 8, [
            {"type": "move_to", "point": [-220, 120]}, {"type": "line_to", "point": [120, -60]},
            {"type": "move_to", "point": [120, -60]}, {"type": "line_to", "point": [40, -40]},
            {"type": "move_to", "point": [120, -60]}, {"type": "line_to", "point": [90, 20]},
            {"type": "close"}], 40, 26),
        ("check", "normal", "#16A34A", 12, check_commands(140), 34, 24),
        ("cross", "normal", "#DC2626", 10, cross_commands(160), 40, 24),
        ("scribble", "normal", "#94A3B8", 5, rounded_rect_commands(640, 320, 24), 46, 26),
        ("double", "normal", "#0F172A", 5, line_commands(420), 42, 24),
        ("corner", "normal", "#0F172A", 5, check_commands(80), 36, 24),
        ("wave", "normal", "#7C3AED", 6, wave_commands(520, 18), 46, 26),
        ("chalk", "normal", "#F8FAFC", 9, circle_commands(170), 44, 26),
        ("pencil", "normal", "#0F172A", 4, circle_commands(150), 42, 24),
    ]
    for index, (name, blend, color, width, commands, draw, hold) in enumerate(trait_specs):
        y = 240 + (index % 4) * 200
        x = 320 + (index % 3) * 560
        stroke = {"color": color, "width": width}
        effects = None
        if name == "chalk":
            effects = [{"type": "noise", "amount": 0.12, "seed": 7}]
        if name == "double":
            layers.append(path_layer(f"brush_{name}_a", [560, 60], [x, y], commands,
                                     stroke, frames, trim=trim_keys(draw - 8, frames),
                                     opacity=0.9))
            layers.append(path_layer(f"brush_{name}_b", [560, 60], [x, y + 26], commands,
                                     stroke, frames,
                                     trim={"start": 0.0, "end": 1.0,
                                           "animation": {"easing": "in_out_quad", "keyframes": [
                                               {"frame": 6, "value": 0.0},
                                               {"frame": draw + 8, "value": 1.0},
                                               {"frame": frames, "value": 1.0}]}},
                                     opacity=0.9))
            continue
        layers.append(path_layer(f"brush_{name}", [640, 120], [x, y], commands, stroke,
                                 frames, trim=trim_keys(draw, frames), opacity=0.88,
                                 blend=blend, effects=effects))
    return base_plan("canary_brush_v1", frames, layers, "canary_brush_v1.mp4")


# ── Gallery 2: web_rect_v1 ──────────────────────────────────────────────────


def web_rect_gallery():
    frames = 12 * 84
    border = {"color": "#E2E8F0", "width": 2}
    layers = [
        rect_layer("bg", [W, H], [W / 2, H / 2], [0.04, 0.06, 0.12, 1], frames),
    ]
    specs = [
        ("scale_in", [{"property": "scale", "easing": "out_cubic",
                       "keyframes": [{"frame": 0, "value": 0.94}, {"frame": 36, "value": 1.0}]}]),
        ("slide_up", [{"property": "position_y", "easing": "out_cubic",
                       "keyframes": [{"frame": 0, "value": 46}, {"frame": 38, "value": 0.0}]}]),
        ("depth_push", [{"property": "position_z", "easing": "out_cubic",
                         "keyframes": [{"frame": 0, "value": -150}, {"frame": 44, "value": 0.0}]},
                        {"property": "scale", "easing": "out_cubic",
                         "keyframes": [{"frame": 0, "value": 0.96}, {"frame": 44, "value": 1.0}]}]),
        ("yaw_open", [{"property": "rotation_y", "easing": "out_cubic",
                       "keyframes": [{"frame": 0, "value": -15}, {"frame": 44, "value": 0.0}]}]),
        ("tilt_settle", [{"property": "rotation_x", "easing": "out_cubic",
                          "keyframes": [{"frame": 0, "value": 6}, {"frame": 42, "value": 0.0}]},
                         {"property": "rotation_y", "easing": "out_cubic",
                          "keyframes": [{"frame": 0, "value": -4}, {"frame": 42, "value": 0.0}]}]),
        ("border_trace", [{"property": "opacity", "easing": "out_cubic",
                           "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 10, "value": 1.0}]}]),
        ("mask_reveal", [{"property": "opacity", "easing": "out_cubic",
                          "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 12, "value": 1.0}]}]),
        ("stack_fan", [{"property": "rotation_z", "easing": "out_cubic",
                        "keyframes": [{"frame": 0, "value": -4}, {"frame": 46, "value": 0.0}]}]),
        ("grid_assemble", [{"property": "position_y", "easing": "out_cubic",
                            "keyframes": [{"frame": 0, "value": 30}, {"frame": 46, "value": 0.0}]},
                           {"property": "scale", "easing": "out_cubic",
                            "keyframes": [{"frame": 0, "value": 0.97}, {"frame": 46, "value": 1.0}]}]),
        ("focus_expand", [{"property": "scale", "easing": "out_cubic",
                           "keyframes": [{"frame": 0, "value": 0.94}, {"frame": 44, "value": 1.0}]}]),
        ("section_zoom", [{"property": "scale", "easing": "out_cubic",
                           "keyframes": [{"frame": 0, "value": 1.06}, {"frame": 46, "value": 1.0}]}]),
        ("split_panel", [{"property": "position_x", "easing": "out_cubic",
                          "keyframes": [{"frame": 0, "value": -24}, {"frame": 44, "value": 0.0}]}]),
    ]
    for index, (name, tracks) in enumerate(specs):
        cell_x = 340 + (index % 4) * 430
        cell_y = 250 + (index // 4) * 300
        card_size = [380, 240]
        enable3d = name in ("depth_push", "yaw_open", "tilt_settle")
        card = rect_layer(f"web_{name}", card_size, [cell_x, cell_y], [1, 1, 1, 1], frames,
                          radius=18, stroke=border,
                          effects=[{"type": "drop_shadow", "offset": [0, 18], "radius": 32,
                                    "color": [0, 0, 0, 0.28]}],
                          tracks=tracks)
        if enable3d:
            card["enable_3d"] = True
        layers.append(card)
        layers.append(text_layer(f"web_{name}_label", name, [340, 40], [cell_x, cell_y + 60],
                                 20, "#94A3B8", frames))
        if name == "border_trace":
            layers.append(path_layer(f"web_{name}_trace", card_size, [cell_x, cell_y],
                                     rounded_rect_commands(card_size[0], card_size[1], 18),
                                     {"color": "#38BDF8", "width": 3}, frames,
                                     trim=trim_keys(40, frames)))
        if name == "mask_reveal":
            shade = rect_layer(f"web_{name}_shade", card_size, [cell_x, cell_y],
                               [0.06, 0.09, 0.16, 1.0], frames, radius=18,
                               tracks=[{"property": "opacity", "easing": "in_out_sine",
                                        "keyframes": [{"frame": 0, "value": 1.0},
                                                      {"frame": 40, "value": 0.0}]}])
            layers.append(shade)
    return base_plan("canary_web_rect_v1", frames, layers, "canary_web_rect_v1.mp4")


# ── Gallery 3: paint_v1 ─────────────────────────────────────────────────────


def paint_gallery():
    frames = 12 * 78
    layers = [
        rect_layer("photo_bg", [W, H], [W / 2, H / 2], [0.12, 0.14, 0.18, 1], frames),
    ]
    specs = [
        ("brush_wipe", "perlin", 2.5, 48, [{"kind": "warp", "amount": 0.35}], 4),
        ("blob_reveal", "simplex", 3.5, 56, None, 4),
        ("ink_spread", "fractal", 4.0, 40, None, 5),
        ("dry_brush", "fractal", 5.0, 72, None, 5),
        ("edge_crawl", "stripes", 3.0, 36, [{"kind": "smoothstep", "edge": 0.5, "softness": 0.3}], 4),
        ("color_swipe", "linear", 1.0, 40, [{"kind": "warp", "amount": 0.25}], 4),
        ("splash_focus", "radial", 3.0, 52, None, 4),
        ("mask_morph", "cellular", 3.5, 44, None, 4),
        ("duotone", "perlin", 3.0, 64, None, 4),
        ("peel_reveal", "linear", 1.5, 30, [{"kind": "warp", "amount": 0.4}], 4),
        ("wave_fill", "rings", 3.0, 48, None, 4),
        ("multi_blob", "simplex", 4.5, 44, None, 4),
    ]
    for index, (name, generator, frequency, feather, operators, octaves) in enumerate(specs):
        cell_x = 480 + (index % 3) * 480
        cell_y = 250 + (index // 3) * 280
        tile = rect_layer(f"paint_{name}", [420, 240], [cell_x, cell_y],
                          [0.95, 0.55, 0.25, 1.0], frames, radius=12,
                          masks=[field_mask(11 + index * 7, generator, feather,
                                            42, 20, frequency=frequency,
                                            octaves=octaves, operators=operators,
                                            width=420, height=240)])
        layers.append(tile)
        layers.append(text_layer(f"paint_{name}_label", name, [400, 36], [cell_x, cell_y + 150],
                                 22, "#E2E8F0", frames))
    return base_plan("canary_paint_v1", frames, layers, "canary_paint_v1.mp4")


# ── Gallery 4: light_leak_v1 ────────────────────────────────────────────────


def light_leak_gallery():
    frames = 12 * 84
    warm = [1.0, 0.72, 0.35, 1.0]
    amber = [1.0, 0.82, 0.55, 1.0]
    cool = [0.62, 0.80, 1.0, 1.0]
    white = [1.0, 1.0, 1.0, 1.0]
    layers = [
        # Reference strips: black / white / red / blue / skin / text — the
        # blend certification scene the light leak family asserts against.
        rect_layer("strip_black", [W, 90], [W / 2, 90], [0, 0, 0, 1], frames),
        rect_layer("strip_white", [W, 90], [W / 2, 190], [1, 1, 1, 1], frames),
        rect_layer("strip_red", [W, 90], [W / 2, 290], [0.85, 0.15, 0.15, 1], frames),
        rect_layer("strip_blue", [W, 90], [W / 2, 390], [0.15, 0.35, 0.85, 1], frames),
        rect_layer("strip_skin", [W, 90], [W / 2, 490], [0.90, 0.72, 0.58, 1], frames),
        text_layer("strip_text", "SDR WHITE MUST NOT EXPLODE — 42% Revenue", [1500, 70],
                   [W / 2, 590], 44, "#FFFFFF", frames),
    ]
    specs = [
        ("edge_warm", warm, [0.55, 2.4], 0.9, [{"property": "position_x", "easing": "out_cubic",
                                                "keyframes": [{"frame": 0, "value": -700}, {"frame": 48, "value": 0.0}]}]),
        ("corner_bloom", amber, [1.6, 1.6], 0.75, [{"property": "scale", "easing": "out_cubic",
                                                    "keyframes": [{"frame": 0, "value": 0.6}, {"frame": 52, "value": 1.0}]}]),
        ("horizontal_sweep", warm, [2.2, 0.5], 0.85, [{"property": "position_x", "easing": "in_out_sine",
                                                       "keyframes": [{"frame": 0, "value": -900}, {"frame": 54, "value": 900.0}]}]),
        ("diagonal_sweep", amber, [2.2, 0.5], 0.85, [{"property": "position_x", "easing": "in_out_sine",
                                                      "keyframes": [{"frame": 0, "value": -900}, {"frame": 54, "value": 900.0}]},
                                                     {"property": "position_y", "easing": "in_out_sine",
                                                      "keyframes": [{"frame": 0, "value": 500}, {"frame": 54, "value": -500.0}]}]),
        ("dual_edge", warm, [0.5, 2.2], 0.7, [{"property": "position_x", "easing": "out_cubic",
                                               "keyframes": [{"frame": 0, "value": -650}, {"frame": 52, "value": -80.0}]}]),
        ("prismatic", white, [1.8, 0.45], 0.8, [{"property": "position_x", "easing": "in_out_sine",
                                                 "keyframes": [{"frame": 0, "value": -800}, {"frame": 50, "value": 0.0}]}]),
        ("pulse", warm, [1.5, 1.5], 0.8, [{"property": "scale", "easing": "in_out_sine",
                                           "keyframes": [{"frame": 0, "value": 0.7}, {"frame": 24, "value": 1.05}, {"frame": 46, "value": 1.0}]}]),
        ("film_burn", white, [2.6, 2.6], 1.0, [{"property": "opacity", "easing": "in_out_sine",
                                                "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 26, "value": 1.0},
                                                              {"frame": 44, "value": 1.0}, {"frame": 60, "value": 1.0}]},
                                               {"property": "scale", "easing": "in_out_sine",
                                                "keyframes": [{"frame": 0, "value": 0.4}, {"frame": 44, "value": 1.3}, {"frame": 60, "value": 1.0}]}]),
        ("soft_flare", amber, [2.0, 2.0], 0.55, [{"property": "scale", "easing": "out_cubic",
                                                  "keyframes": [{"frame": 0, "value": 0.85}, {"frame": 52, "value": 1.0}]}]),
        ("focus_glow", amber, [1.4, 1.4], 0.55, [{"property": "scale", "easing": "out_cubic",
                                                  "keyframes": [{"frame": 0, "value": 0.7}, {"frame": 46, "value": 1.1}]}]),
        ("anamorphic", cool, [3.2, 0.18], 0.75, [{"property": "opacity", "easing": "out_cubic",
                                                  "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 20, "value": 1.0},
                                                                {"frame": 50, "value": 1.0}]}]),
        ("bokeh", amber, [0.28, 0.28], 0.5, [{"property": "position_y", "easing": "linear",
                                              "keyframes": [{"frame": 0, "value": 0.0}, {"frame": 50, "value": -60.0}]}]),
    ]
    for index, (name, color, size_scale, opacity, tracks) in enumerate(specs):
        y = 720 + (index % 2) * 150
        x = 260 + (index % 6) * 290
        size = [1200 * size_scale[0], 500 * size_scale[1]]
        effects = [{"type": "gaussian_blur", "radius": 96},
                   {"type": "glow", "radius": 80, "intensity": 0.5,
                    "color": [color[0], color[1], color[2], 1.0]}]
        if name == "prismatic":
            effects = [{"type": "gaussian_blur", "radius": 96},
                       {"type": "chromatic_aberration", "mode": "constant", "amount": 0.03}]
        layers.append(ellipse_glow(f"leak_{name}", size, [x, y], color, frames,
                                   opacity=opacity, effects=effects, tracks=tracks,
                                   blend="screen"))
    return base_plan("canary_light_leak_v1", frames, layers, "canary_light_leak_v1.mp4")


def abstract_background_gallery():
    frames = 10 * FPS
    layers = [rect_layer("abstract_backplate", [W, H], [W / 2, H / 2],
                         [0.008, 0.01, 0.024, 1.0], frames)]
    scenes = [
        ("aurora", "fractal", 2.4, [0.34, 0.08, 0.72, 0.9],
         [{"kind": "warp", "amount": 0.12}]),
        ("liquid", "fractal", 3.2, [0.82, 0.08, 0.62, 0.82],
         [{"kind": "warp", "amount": 0.2}]),
        ("metaball", "cellular", 3.0, [0.52, 0.14, 0.86, 0.8],
         [{"kind": "smoothstep", "edge": 0.44, "softness": 0.22}]),
        ("glass", "radial", 1.0, [0.7, 0.22, 1.0, 0.68], []),
        ("contours", "rings", 10.0, [0.86, 0.92, 1.0, 0.7],
         [{"kind": "warp", "amount": 0.1},
          {"kind": "smoothstep", "edge": 0.94, "softness": 0.08}]),
        ("flowlines", "stripes", 72.0, [0.58, 0.76, 1.0, 0.62],
         [{"kind": "warp", "amount": 0.004}]),
        ("folded", "stripes", 6.0, [0.62, 0.3, 0.94, 0.82],
         [{"kind": "warp", "amount": 0.06}]),
        ("fan", "conic", 1.0, [0.7, 0.48, 0.96, 0.56], []),
        ("blue_atmosphere", "radial", 1.0, [0.05, 0.32, 0.72, 0.72], []),
        ("mega_mix", "fractal", 2.0, [0.72, 0.18, 0.9, 0.74],
         [{"kind": "warp", "amount": 0.16}]),
    ]
    for index, (name, generator, frequency, color, operators) in enumerate(scenes):
        layer = rect_layer(f"abstract_{name}", [W, H], [W / 2, H / 2], color, frames,
                           blend="screen", effects=[{"type": "gaussian_blur", "radius": 18}])
        layer["start_frame"] = index * FPS
        layer["duration_frames"] = FPS
        layer["shape"]["field"] = {
            "generator": generator, "seed": 101 + index,
            "frequency": frequency, "octaves": 5,
            "operators": operators,
        }
        layer["shape"]["field_render_scale"] = 4
        layer["shape"]["field_drift"] = [0.008, -0.004]
        if name in {"liquid", "mega_mix"}:
            layer["shape"]["field_ramp"] = abstract_neon_ramp()
        layer["animation"] = {"tracks": [{"property": "opacity", "easing": "linear",
            "keyframes": [{"frame": index * FPS, "value": 0.0},
                          {"frame": index * FPS + 4, "value": 1.0},
                          {"frame": (index + 1) * FPS - 4, "value": 1.0},
                          {"frame": (index + 1) * FPS, "value": 0.0}]}]}
        layers.append(layer)
    return base_plan("canary_abstract_background_v1", frames, layers,
                     "canary_abstract_background_v1.mp4")


def abstract_background_torture():
    frames = 13 * FPS
    layers = [rect_layer("abstract_torture_backplate", [W, H], [W / 2, H / 2],
                         [0.005, 0.008, 0.02, 1.0], frames)]
    stages = [
        ("aurora", "fractal", 2.0, [0.38, 0.08, 0.84, 0.8], 0),
        ("liquid", "fractal", 3.5, [0.92, 0.08, 0.62, 0.72], 2),
        ("metaball", "cellular", 3.0, [0.4, 0.1, 0.9, 0.7], 4),
        ("contours", "rings", 9.0, [0.86, 0.92, 1.0, 0.62], 6),
        ("flow", "stripes", 64.0, [0.16, 0.55, 1.0, 0.62], 8),
        ("fold", "stripes", 6.0, [0.9, 0.34, 0.12, 0.7], 10),
    ]
    for name, generator, frequency, color, start_seconds in stages:
        start = start_seconds * FPS
        layer = rect_layer(f"torture_{name}", [W, H], [W / 2, H / 2], color, frames,
                           blend="screen")
        layer["shape"]["field"] = {"generator": generator, "seed": 211 + start,
            "frequency": frequency, "octaves": 5,
            "operators": ([{"kind": "warp", "amount": 0.09}]
                          if generator in {"fractal", "rings", "stripes"} else [])}
        layer["shape"]["field_render_scale"] = 4
        layer["shape"]["field_drift"] = [-0.006, 0.005]
        if name == "liquid":
            layer["shape"]["field_ramp"] = abstract_neon_ramp()
        layer["animation"] = {"tracks": [{"property": "opacity", "easing": "in_out_sine",
            "keyframes": [{"frame": start, "value": 0.0},
                          {"frame": start + 30, "value": 1.0},
                          {"frame": start + 60, "value": 1.0},
                          {"frame": start + 90, "value": 0.0}]}]}
        layers.append(layer)
    return base_plan("canary_abstract_background_torture", frames, layers,
                     "canary_abstract_background_torture_v1.mp4")


# ── Mega canary ─────────────────────────────────────────────────────────────


def mega_canary():
    frames = 20 * 30  # 20 seconds
    amber = [1.0, 0.82, 0.55, 1.0]
    layers = [
        rect_layer("scene_bg", [W, H], [W / 2, H / 2], [0.05, 0.07, 0.10, 1], frames),
        # Document scene: marker highlight + underline on the key number.
        text_layer("mega_doc", "Revenue increased by 42%", [1500, 130], [W / 2, 240],
                   72, "#F1F5F9", frames, font="assets/fonts/Poppins-Bold.ttf"),
        path_layer("mega_marker", [420, 120], [1105, 250], line_commands(380),
                   {"color": "#FACC15", "width": 64}, frames, opacity=0.85,
                   blend="multiply",
                   trim={"start": 0.0, "end": 1.0,
                         "animation": {"easing": "in_out_quad", "keyframes": [
                             {"frame": 20, "value": 0.0}, {"frame": 60, "value": 1.0},
                             {"frame": frames, "value": 1.0}]}}),
        path_layer("mega_underline", [520, 60], [820, 300], line_commands(480),
                   {"color": "#F1F5F9", "width": 6}, frames, opacity=0.9,
                   trim={"start": 0.0, "end": 1.0,
                         "animation": {"easing": "in_out_quad", "keyframes": [
                             {"frame": 0, "value": 0.0}, {"frame": 40, "value": 1.0},
                             {"frame": frames, "value": 1.0}]}}),
    ]
    # Web screenshot scene: rounded depth reveal + border trace.
    web_card = rect_layer("mega_web", [760, 420], [560, 620], [1, 1, 1, 1], frames,
                          radius=20, stroke={"color": "#E2E8F0", "width": 2},
                          effects=[{"type": "drop_shadow", "offset": [0, 24], "radius": 40,
                                    "color": [0, 0, 0, 0.32]}],
                          tracks=[{"property": "position_z", "easing": "out_cubic",
                                   "keyframes": [{"frame": 60, "value": -150}, {"frame": 110, "value": 0.0}]},
                                  {"property": "scale", "easing": "out_cubic",
                                   "keyframes": [{"frame": 60, "value": 0.96}, {"frame": 110, "value": 1.0}]}])
    web_card["enable_3d"] = True
    layers.append(web_card)
    layers.append(path_layer("mega_trace", [760, 420], [560, 620],
                                 rounded_rect_commands(760, 420, 20),
                                 {"color": "#38BDF8", "width": 3}, frames,
                                 trim={"start": 0.0, "end": 1.0,
                                       "animation": {"easing": "in_out_quad", "keyframes": [
                                           {"frame": 90, "value": 0.0}, {"frame": 140, "value": 1.0},
                                           {"frame": frames, "value": 1.0}]}}))
    # Photo scene: paint wipe reveal + brush accent + caption.
    photo = rect_layer("mega_photo", [700, 460], [1400, 620], [0.95, 0.55, 0.25, 1],
                       frames, radius=16,
                       masks=[field_mask(99, "perlin", 48, 150, 20, frequency=2.5,
                                         operators=[{"kind": "warp", "amount": 0.35}],
                                         width=700, height=460)])
    layers.append(photo)
    layers.append(text_layer("mega_caption", "Field report — October", [600, 44],
                             [1400, 880], 26, "#E2E8F0", frames))
    # Scene transition: film light leak flood.
    layers.append(ellipse_glow("mega_burn", [2600, 2600], [W / 2, H / 2], [1, 1, 1, 1],
                               frames, opacity=1.0,
                               effects=[{"type": "gaussian_blur", "radius": 160},
                                        {"type": "glow", "radius": 120, "intensity": 0.8,
                                         "color": [1.0, 0.8, 0.5, 1.0]}],
                               tracks=[{"property": "opacity", "easing": "in_out_sine",
                                        "keyframes": [{"frame": 300, "value": 0.0},
                                                      {"frame": 340, "value": 1.0},
                                                      {"frame": 380, "value": 1.0},
                                                      {"frame": 430, "value": 0.0}]},
                                       {"property": "scale", "easing": "in_out_sine",
                                        "keyframes": [{"frame": 300, "value": 0.4},
                                                      {"frame": 430, "value": 1.4}]}]))
    # Metric scene: radial focus leak breathing behind the number.
    layers.append(ellipse_glow("mega_focus", [900, 900], [W / 2, 240], amber, frames,
                               opacity=0.55,
                               effects=[{"type": "gaussian_blur", "radius": 140},
                                        {"type": "glow", "radius": 96, "intensity": 0.6,
                                         "color": [1.0, 0.82, 0.55, 1.0]}],
                               tracks=[{"property": "scale", "easing": "in_out_sine",
                                        "keyframes": [{"frame": 440, "value": 0.7},
                                                      {"frame": 500, "value": 1.1}]}]))
    layers.append(text_layer("mega_metric", "+42%", [600, 140], [W / 2, 240], 96,
                                 "#FFFFFF", frames, font="assets/fonts/Poppins-Bold.ttf",
                                 effects=[{"type": "glow", "radius": 48, "intensity": 0.4,
                                           "color": [1.0, 0.82, 0.55, 1.0]}]))
    # Final image: border trace + brush corner accents.
    final_card = rect_layer("mega_final", [640, 360], [W / 2, 700], [1, 1, 1, 1],
                            frames, radius=18, stroke={"color": "#E2E8F0", "width": 2},
                            tracks=[{"property": "opacity", "easing": "out_cubic",
                                     "keyframes": [{"frame": 520, "value": 0.0},
                                                   {"frame": 560, "value": 1.0}]}])
    layers.append(final_card)
    layers.append(path_layer("mega_final_trace", [640, 360], [W / 2, 700],
                             rounded_rect_commands(640, 360, 18),
                             {"color": "#7C3AED", "width": 3}, frames,
                             trim={"start": 0.0, "end": 1.0,
                                   "animation": {"easing": "in_out_quad", "keyframes": [
                                       {"frame": 540, "value": 0.0}, {"frame": 590, "value": 1.0},
                                       {"frame": frames, "value": 1.0}]}}))
    return base_plan("canary_visual_accents_mega", frames, layers,
                     "canary_visual_accents_mega.mp4")


PLANS = {
    "canary_brush_v1.plan.json": brush_gallery,
    "canary_web_rect_v1.plan.json": web_rect_gallery,
    "canary_paint_v1.plan.json": paint_gallery,
    "canary_light_leak_v1.plan.json": light_leak_gallery,
    "canary_abstract_background_v1.plan.json": abstract_background_gallery,
    "canary_abstract_background_torture_v1.plan.json": abstract_background_torture,
    "canary_visual_accents_mega.plan.json": mega_canary,
}


def write_plans() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, builder in PLANS.items():
        path = OUT / name
        path.write_text(json.dumps(builder(), indent=2) + "\n")
        print(f"  wrote {path}")
        paths.append(path)
    return paths


def validate(paths: list[Path]) -> bool:
    ok = True
    for path in paths:
        result = subprocess.run(
            [str(CLI), "validate", "--plan", str(path), "--assets-root", str(ASSETS)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            ok = False
            print(f"  VALIDATION FAIL {path.name}:\n{result.stderr}\n{result.stdout}")
        else:
            print(f"  validated {path.name}")
    return ok


def render(paths: list[Path]) -> bool:
    ok = True
    for path in paths:
        output = path.with_suffix("").with_suffix(".mp4")
        result = subprocess.run(
            [str(CLI), "render", "--backend", "software", "--plan", str(path),
             "--assets-root", str(ASSETS), "-o", str(output)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0 or not output.exists():
            ok = False
            print(f"  RENDER FAIL {path.name}:\n{result.stderr[-2000:]}\n{result.stdout[-2000:]}")
        else:
            print(f"  rendered {output.name} ({output.stat().st_size:,} bytes)")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans", action="store_true", help="write the five plans")
    parser.add_argument("--validate", action="store_true", help="write + validate")
    parser.add_argument("--render", action="store_true", help="write + validate + render")
    args = parser.parse_args()
    if not (args.plans or args.validate or args.render):
        parser.error("choose --plans, --validate or --render")

    paths = write_plans()
    if args.validate or args.render:
        if not validate(paths):
            sys.exit(1)
    if args.render:
        if not render(paths):
            sys.exit(1)


if __name__ == "__main__":
    main()
