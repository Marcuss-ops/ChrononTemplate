#!/usr/bin/env python3
"""Build and verify the ChrononTemplate Kinetic Type Editorial V1 canaries.

ChrononTemplate owns these recipes and emits ordinary V3 render plans. Chronon3D
continues to own text shaping, span layout, procedural effects and pixels; this
module never creates glyph layers or renders text itself. Gallery exports are
serialized and rendered one at a time to keep peak memory bounded.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from fractions import Fraction
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CHRONON3D = WORKSPACE / "Chronon3d"
DEFAULT_OUT = ROOT / "build" / "kinetic_type_editorial_v1"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
SCENE_FRAMES = 90
GALLERY_SCENE_FRAMES = 54
GALLERY_OVERLAP_FRAMES = 12
MIN_VULKAN_CHUNK_FRAMES = 1
FONT_BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_REGULAR = "Chronon3d/assets/fonts/Inter-Regular.ttf"

# Stable editorial tokens: values are authored as CSS hex colors and converted
# only at the render-plan boundary when a primitive requires normalized RGBA.
EDITORIAL_COLOR_TOKENS = {
    "bg.base.black": "#050308",
    "bg.blob.magenta": "#D91C8D",
    "bg.blob.hot_pink": "#F03AA8",
    "bg.blob.purple": "#6B1DFF",
    "bg.blob.deep_violet": "#38106D",
    "bg.blob.blue_violet": "#3D3DFF",
    "bg.blob.red_magenta": "#C71D4D",
    "bg.blob.coral": "#FF6A63",
    "text.primary.white": "#F5F3F7",
    "text.secondary.gray": "#D8D4DD",
    "accent.yellow": "#FFD83D",
    "accent.coral": "#FF6D5E",
    "accent.lavender": "#D7B8FF",
}

TYPOGRAPHY_TOKENS = {
    # Headlines now follow viewport hierarchy: single words occupy a third to
    # half of the frame; sentence lines remain deliberately smaller.
    "display_xl": {"font": FONT_BOLD, "font_size": 420, "min_font_size": 240, "max_font_size": 420},
    "display_l": {"font": FONT_BOLD, "font_size": 146, "min_font_size": 64, "max_font_size": 146},
    "display_hero": {"font": FONT_BOLD, "font_size": 480, "min_font_size": 300, "max_font_size": 480},
    "body_m": {"font": FONT_REGULAR, "font_size": 38, "min_font_size": 28, "max_font_size": 38},
    "label_xs": {"font": FONT_BOLD, "font_size": 18, "min_font_size": 14, "max_font_size": 18},
}

# These named looks are recipe parameters over native image and motion layers.
BACKGROUND_PRESETS = {
    "bg_aurora_soft_drift": {
        "seed": 91, "evolution": 0.10, "warp": 0.018, "vignette": 0.0,
        "blobs": [
            {"color": "bg.blob.magenta", "center": [0.24, 0.36], "size": [1.18, 0.92], "opacity": 0.55},
            {"color": "bg.blob.purple", "center": [0.76, 0.34], "size": [1.12, 0.94], "opacity": 0.48},
            {"color": "bg.blob.blue_violet", "center": [0.54, 0.82], "size": [1.10, 0.64], "opacity": 0.36},
            {"color": "bg.blob.red_magenta", "center": [0.50, 0.48], "size": [0.72, 0.62], "opacity": 0.34},
            {"color": "bg.blob.hot_pink", "center": [0.12, 0.78], "size": [0.62, 0.60], "opacity": 0.29},
            {"color": "bg.blob.deep_violet", "center": [0.90, 0.74], "size": [0.72, 0.64], "opacity": 0.36},
        ],
    },
    "bg_aurora_breathe": {
        "seed": 92, "evolution": 0.08, "warp": 0.014, "vignette": 0.04,
        "blobs": [
            {"color": "bg.blob.hot_pink", "center": [0.30, 0.42], "size": [0.70, 0.54], "opacity": 0.32},
            {"color": "bg.blob.deep_violet", "center": [0.72, 0.44], "size": [0.74, 0.58], "opacity": 0.34},
            {"color": "bg.blob.red_magenta", "center": [0.52, 0.72], "size": [0.58, 0.42], "opacity": 0.20},
        ],
    },
    "bg_aurora_focus_swell": {
        "seed": 93, "evolution": 0.12, "warp": 0.022, "vignette": 0.06,
        "blobs": [
            {"color": "bg.blob.magenta", "center": [0.30, 0.42], "size": [0.72, 0.54], "opacity": 0.28},
            {"color": "bg.blob.purple", "center": [0.70, 0.43], "size": [0.68, 0.56], "opacity": 0.28},
            {"color": "bg.blob.coral", "center": [0.50, 0.49], "size": [0.45, 0.40], "opacity": 0.25},
        ],
    },
    "bg_aurora_crossfade": {
        "seed": 94, "evolution": 0.14, "warp": 0.020, "vignette": 0.03,
        "blobs": [
            {"color": "bg.blob.magenta", "center": [0.25, 0.45], "size": [0.74, 0.56], "opacity": 0.34},
            {"color": "bg.blob.blue_violet", "center": [0.75, 0.44], "size": [0.76, 0.58], "opacity": 0.32},
            {"color": "bg.blob.coral", "center": [0.52, 0.69], "size": [0.54, 0.44], "opacity": 0.18},
        ],
    },
    "bg_aurora_shift_left_right": {
        "seed": 95, "evolution": 0.09, "warp": 0.016, "vignette": 0.02,
        "blobs": [
            {"color": "bg.blob.red_magenta", "center": [0.22, 0.44], "size": [0.70, 0.54], "opacity": 0.33},
            {"color": "bg.blob.purple", "center": [0.78, 0.43], "size": [0.72, 0.56], "opacity": 0.32},
            {"color": "bg.blob.blue_violet", "center": [0.50, 0.72], "size": [0.58, 0.44], "opacity": 0.20},
        ],
    },
    "bg_aurora_center_bloom": {
        "seed": 96, "evolution": 0.07, "warp": 0.012, "vignette": 0.05,
        "blobs": [
            {"color": "bg.blob.deep_violet", "center": [0.28, 0.42], "size": [0.64, 0.52], "opacity": 0.26},
            {"color": "bg.blob.magenta", "center": [0.72, 0.43], "size": [0.64, 0.52], "opacity": 0.26},
            {"color": "bg.blob.hot_pink", "center": [0.50, 0.50], "size": [0.52, 0.42], "opacity": 0.29},
        ],
    },
    "bg_aurora_corner_heat": {
        "seed": 97, "evolution": 0.10, "warp": 0.018, "vignette": 0.04,
        "blobs": [
            {"color": "bg.blob.coral", "center": [0.12, 0.14], "size": [0.70, 0.60], "opacity": 0.31},
            {"color": "bg.blob.purple", "center": [0.72, 0.54], "size": [0.70, 0.56], "opacity": 0.29},
            {"color": "bg.blob.red_magenta", "center": [0.32, 0.75], "size": [0.55, 0.40], "opacity": 0.18},
        ],
    },
    "bg_aurora_deep_vignette": {
        "seed": 98, "evolution": 0.06, "warp": 0.010, "vignette": 0.28,
        "blobs": [
            {"color": "bg.blob.deep_violet", "center": [0.27, 0.43], "size": [0.62, 0.50], "opacity": 0.24},
            {"color": "bg.blob.red_magenta", "center": [0.73, 0.43], "size": [0.62, 0.50], "opacity": 0.22},
            {"color": "bg.blob.blue_violet", "center": [0.50, 0.70], "size": [0.56, 0.40], "opacity": 0.17},
        ],
    },
}

TEXT_MOTION_IDS = (
    "text_word_pop_focus",
    "text_phrase_soft_rise",
    "text_accent_word_swap",
    "text_keyword_color_emphasis",
    "text_underline_draw",
    "text_word_replace_same_line",
    "text_large_to_small_handoff",
    "text_stagger_phrase_segments",
    "text_trailing_word_reveal",
    "text_crossfade_phrase",
)

SCENE_RECIPES = {
    "recipe_editorial_hero_word": {
        "background": "bg_aurora_focus_swell", "motion": "text_word_pop_focus",
        "text": "Simplicity", "accent": "accent.coral",
    },
    "recipe_editorial_statement": {
        "background": "bg_aurora_breathe", "motion": "text_phrase_soft_rise",
        "text": "Form follows function", "accent_word": "function", "accent": "accent.yellow",
        "combine": ["text_keyword_color_emphasis"],
    },
    "recipe_editorial_underline": {
        "background": "bg_aurora_focus_swell", "motion": "text_phrase_soft_rise",
        "text": "Form follows function", "accent_word": "function", "accent": "accent.coral",
        "combine": ["text_underline_draw"],
    },
    "recipe_editorial_progressive_concept": {
        "background": "bg_aurora_crossfade", "motion": "text_stagger_phrase_segments",
        "segments": ["Text is a", "design", "element"], "accent_segment": 1,
        "accent": "accent.lavender",
    },
    "recipe_editorial_large_to_secondary": {
        "background": "bg_aurora_deep_vignette", "motion": "text_large_to_small_handoff",
        "text": "CREATE", "secondary": "Create with intention", "accent": "accent.coral",
    },
}

GALLERY_SCENES = (
    ("word", "word", None),
    ("weight", "weight", None),
    ("simplicity", "Simplicity", None),
    ("make_it_simple", "Make it simple", "simple"),
    ("form_follows_function", "Form follows function", "function"),
    ("design_is_intelligence", "Design is intelligence", "intelligence"),
    ("think", "Think", None),
    ("repeat", "Repeat", None),
    ("good_design_effortless", "Good design feels effortless", "effortless"),
    ("text_design_element", "Text is a design element", "design"),
    ("create", "Create", None),
    ("create_with_intention", "Create with intention", "intention"),
    ("thanks_for_watching", "Thanks for watching", "watching"),
)


def _rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"expected #RRGGBB, got {hex_color!r}")
    return [int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def _track(prop: str, keys: list[tuple[int, Any]], easing: str = "out_cubic") -> dict[str, Any]:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def _span(text: str, word: str, color_token: str, semantic_id: str = "accent-word") -> dict[str, Any]:
    start = text.find(word)
    if start < 0 or text.find(word, start + len(word)) >= 0:
        raise ValueError(f"accent word {word!r} must appear exactly once in {text!r}")
    byte_start = len(text[:start].encode("utf-8"))
    byte_end = byte_start + len(word.encode("utf-8"))
    # The semantic range begins in the ordinary headline color; the attached
    # fill_color animator is the single authority that introduces the accent.
    if color_token not in EDITORIAL_COLOR_TOKENS:
        raise ValueError(f"unknown editorial color token: {color_token}")
    return {"start": byte_start, "end": byte_end, "semantic_id": semantic_id,
            "style": {"color": EDITORIAL_COLOR_TOKENS["text.primary.white"]}}


def _segmented_gradient_spans(text: str, word: str, semantic_prefix: str,
                             colors: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    start = text.find(word)
    if start < 0 or text.find(word, start + len(word)) >= 0:
        raise ValueError(f"gradient word {word!r} must appear exactly once in {text!r}")
    groups = min(len(colors), len(word))
    result_spans, result_animators = [], []
    for index in range(groups):
        begin = start + round(index * len(word) / groups)
        end = start + round((index + 1) * len(word) / groups)
        semantic_id = f"{semantic_prefix}-{index}"
        byte_start = len(text[:begin].encode("utf-8"))
        byte_end = len(text[:end].encode("utf-8"))
        result_spans.append({"start": byte_start, "end": byte_end,
            "semantic_id": semantic_id,
            "style": {"color": EDITORIAL_COLOR_TOKENS["text.primary.white"]}})
        result_animators.append(_keyword_animator(semantic_id,
            EDITORIAL_COLOR_TOKENS["text.primary.white"], colors[index]))
    return result_spans, result_animators


def _keyword_animator(semantic_id: str, color: str, accent: str) -> dict[str, Any]:
    from_rgba, to_rgba = _rgba(color), _rgba(accent)
    return {"id": f"{semantic_id}-color-emphasis",
            "selectors": [{"id": f"{semantic_id}-selector", "unit": "glyph",
                           "semantic_id": semantic_id, "shape": "square", "order": "forward",
                           "combine": "replace", "exclude_spaces": True,
                           "amount": {"easing": "linear", "keyframes": [
                               {"frame": 0, "value": 0}, {"frame": 12, "value": 100}]} }],
            "properties": [{"property": "fill_color", "easing": "linear",
                            "keyframes": [{"frame": 0, "value": from_rgba},
                                          {"frame": 18, "value": to_rgba}]}]}


def _span_motion_animator(semantic_id: str, properties: list[dict[str, Any]],
                          *, amount_keys: list[tuple[int, float]] | None = None) -> dict[str, Any]:
    return {"id": f"{semantic_id}-per-span-motion", "selectors": [{
        "id": f"{semantic_id}-motion-selector", "unit": "glyph",
        "semantic_id": semantic_id, "shape": "square", "order": "forward",
        "combine": "replace", "exclude_spaces": True,
        "amount": {"easing": "linear", "keyframes": [
            {"frame": frame, "value": value}
            for frame, value in (amount_keys or [(0, 100)])]}}],
        "properties": properties}


def _pop_blur_animator(duration: int, *, start: int = 0, tracking: float = 20.0,
                       peak_blur: float = 6.0, exit_blur: float = 6.0) -> dict[str, Any]:
    settle = min(duration - 1, start + min(12, max(4, duration // 7)))
    exit_start = max(settle + 1, duration - min(12, duration // 5))
    blur_keys = ([{"frame": 0, "value": peak_blur}] if start == 0 else
                 [{"frame": 0, "value": peak_blur}, {"frame": start, "value": peak_blur}])
    blur_keys.extend([{"frame": settle, "value": 0}, {"frame": exit_start, "value": 0},
                      {"frame": duration - 1, "value": exit_blur}])
    tracking_keys = ([{"frame": 0, "value": tracking}] if start == 0 else
                     [{"frame": 0, "value": tracking}, {"frame": start, "value": tracking}])
    tracking_keys.extend([{"frame": settle, "value": 0},
                          {"frame": duration - 1, "value": 0}])
    return {"id": "kinetic-blur-tracking", "selectors": [{
        "id": "all-glyphs", "unit": "glyph", "shape": "square",
        "order": "forward", "combine": "replace", "exclude_spaces": True,
        "amount": {"easing": "linear", "keyframes": [
            {"frame": 0, "value": 100}, {"frame": duration - 1, "value": 100}]}}],
        "properties": [
            {"property": "blur", "easing": "linear", "keyframes": blur_keys},
            {"property": "tracking", "easing": "linear", "keyframes": tracking_keys},
        ]}


def _text_layer(layer_id: str, text: str, *, center: tuple[float, float] = (960, 510),
                role: str = "display_l", fill: str | None = None, opacity: float = 1.0,
                start_frame: int = 0, duration: int = SCENE_FRAMES,
                tracks: list[dict[str, Any]] | None = None,
                spans: list[dict[str, Any]] | None = None,
                animators: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    type_style = TYPOGRAPHY_TOKENS[role]
    layer: dict[str, Any] = {
        "id": layer_id, "type": "text", "text": text,
        "size": [1800 if role == "display_hero" else 1640,
                 700 if role == "display_hero" else
                 350 if role.startswith("display") else 90],
        "position": [center[0], center[1]], "start_frame": start_frame,
        "duration_frames": duration, "opacity": opacity,
        "style": {"font": type_style["font"], "font_size": type_style["font_size"],
                  "min_font_size": type_style["min_font_size"],
                  "max_font_size": type_style["max_font_size"], "fit_mode": "shrink_only",
                  "fill": fill or EDITORIAL_COLOR_TOKENS["text.primary.white"]},
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if spans:
        layer["spans"] = spans
    if animators:
        layer["text_animators"] = animators
    return layer


def _aurora_layers(preset_id: str, duration: int) -> list[dict[str, Any]]:
    preset = BACKGROUND_PRESETS[preset_id]
    dark = _rgba(EDITORIAL_COLOR_TOKENS["bg.base.black"])
    base: dict[str, Any] = {
        "id": "editorial-black-base", "type": "color", "color": dark,
        "size": [WIDTH, HEIGHT], "start_frame": 0, "duration_frames": duration,
    }
    # Six broad, overlapping image emitters create the large irregular aurora
    # masses while keeping the scene Vulkan-native and deterministic.
    layers = [base]
    emitters = [dict(blob) for blob in preset["blobs"]]
    orbit = ((0.12, 0.08), (0.88, 0.12), (0.83, 0.86), (0.18, 0.84),
             (0.48, 0.16), (0.52, 0.88))
    while len(emitters) < 6:
        index = len(emitters)
        source = preset["blobs"][index % len(preset["blobs"])]
        ox, oy = orbit[index % len(orbit)]
        emitters.append({"color": source["color"], "center": [ox, oy],
                         "size": [0.72 + 0.08 * (index % 3), 0.68 + 0.06 * (index % 2)],
                         "opacity": source["opacity"] * 0.60})
    for index, blob in enumerate(emitters):
        x, y = blob["center"]
        sx, sy = blob["size"]
        move = 52 if preset_id in {"bg_aurora_soft_drift", "bg_aurora_shift_left_right"} else 28
        if preset_id == "bg_aurora_shift_left_right":
            move *= 1.8
        tracks = [
            _track("position_x", [(0, -move), (duration // 2, move), (duration - 1, -move)], "in_out_sine"),
            _track("position_y", [(0, 18 if index % 2 else -18),
                                   (duration // 2, -18 if index % 2 else 18),
                                   (duration - 1, 18 if index % 2 else -18)], "in_out_sine"),
        ]
        if preset_id == "bg_aurora_breathe":
            tracks.extend([
                _track("scale", [(0, 0.94), (duration // 2, 1.04), (duration - 1, 0.94)], "in_out_sine"),
                _track("opacity", [(0, blob["opacity"] * 0.8),
                                   (duration // 2, blob["opacity"]),
                                   (duration - 1, blob["opacity"] * 0.8)], "in_out_sine"),
            ])
        elif preset_id == "bg_aurora_focus_swell" and index == 2:
            tracks.extend([
                _track("scale", [(0, 0.72), (24, 1.08), (duration - 1, 0.72)], "in_out_sine"),
                _track("opacity", [(0, blob["opacity"] * 0.55), (24, blob["opacity"]),
                                   (duration - 1, blob["opacity"] * 0.55)], "in_out_sine"),
            ])
        elif preset_id == "bg_aurora_center_bloom" and index == 2:
            tracks.extend([
                _track("scale", [(0, 0.65), (duration // 2, 1.12), (duration - 1, 0.65)], "in_out_sine"),
                _track("opacity", [(0, blob["opacity"] * 0.65),
                                   (duration // 2, blob["opacity"]),
                                   (duration - 1, blob["opacity"] * 0.65)], "in_out_sine"),
            ])
        elif preset_id == "bg_aurora_crossfade":
            if index == 0:
                tracks.append(_track("opacity", [(0, blob["opacity"]),
                                                   (duration - 1, blob["opacity"] * 0.45)], "in_out_sine"))
            elif index == 1:
                tracks.append(_track("opacity", [(0, blob["opacity"] * 0.45),
                                                   (duration - 1, blob["opacity"])], "in_out_sine"))
        texture_name = blob["color"].split(".", 2)[-1] + ".png"
        layers.append({
            "id": f"aurora-blob-{index}", "type": "image",
            "asset": f"ChrononTemplate/assets/kinetic_type_editorial_v1/{texture_name}",
            "size": [round(WIDTH * sx), round(HEIGHT * sy)],
            # Image layer position is its top-left anchor, unlike text/shape.
            "position": [round(WIDTH * x - WIDTH * sx / 2),
                         round(HEIGHT * y - HEIGHT * sy / 2)],
            "start_frame": 0, "duration_frames": duration,
            "opacity": blob["opacity"], "fit": "stretch",
            "animation": {"tracks": tracks},
        })
    return layers


def _underline_layers(layer_id: str, x: float, y: float, width: float,
                      color_token: str, duration: int) -> list[dict[str, Any]]:
    color = EDITORIAL_COLOR_TOKENS[color_token]
    draw = min(18, duration - 1)
    overshoot = min(duration - 1, draw + 5)

    def line(identifier: str, line_width: float, height: float, max_opacity: float,
             *, halo: bool) -> dict[str, Any]:
        left_offset = -line_width / 2
        shape = {"type": "rounded_rect", "fill": _rgba(color), "radius": height / 2}
        return {"id": identifier, "type": "shape", "size": [line_width, height],
            "position": [x, y], "start_frame": 0, "duration_frames": duration,
            "opacity": max_opacity, "shape": shape,
            "animation": {"tracks": [
                _track("scale_x", [(0, 0.0), (draw, 1.12), (overshoot, 1.0),
                                    (duration - 1, 1.0)], "out_cubic"),
                _track("position_x", [(0, left_offset), (draw, line_width * 0.06),
                                       (overshoot, 0), (duration - 1, 0)], "out_cubic"),
                _track("opacity", [(0, 0.0), (draw, max_opacity),
                                    (overshoot, max_opacity * (0.50 if halo else 1.0)),
                                    (duration - 1, max_opacity * (0.50 if halo else 1.0))],
                       "out_cubic"),
            ]}}
    glow = line(f"{layer_id}-afterglow", width * 1.06, 22, 0.40, halo=True)
    core = line(layer_id, width, 6, 1.0, halo=False)
    return [glow, core]


def _primary_phrase(layer_id: str, text: str, duration: int, *, accent_word: str | None = None,
                    accent_token: str = "accent.coral", motion: str | None = None,
                    start_frame: int = 0, opacity_keys: list[tuple[int, float]] | None = None,
                    role: str = "display_l") -> dict[str, Any]:
    spans = [_span(text, accent_word, accent_token)] if accent_word else None
    animators = [_keyword_animator("accent-word", EDITORIAL_COLOR_TOKENS["text.primary.white"],
                                  EDITORIAL_COLOR_TOKENS[accent_token])] if accent_word else None
    tracks: list[dict[str, Any]] = []
    motion_animators: list[dict[str, Any]] = []
    if accent_word:
        semantic = "accent-word"
        motion_animators.append(_span_motion_animator(semantic, [
            {"property": "scale", "easing": "linear", "keyframes": [
                {"frame": 0, "value": [0.82]}, {"frame": 8, "value": [1.12]},
                {"frame": 18, "value": [1.0]}, {"frame": duration - 1, "value": [1.0]}]},
            {"property": "blur", "easing": "linear", "keyframes": [
                {"frame": 0, "value": 10}, {"frame": 12, "value": 0},
                {"frame": duration - 1, "value": 0}]},
            {"property": "tracking", "easing": "linear", "keyframes": [
                {"frame": 0, "value": 12}, {"frame": 16, "value": 0},
                {"frame": duration - 1, "value": 0}]},
        ]))
    if opacity_keys is not None:
        # Explicit handoff opacity is the complete visibility motion; applying
        # a generic entrance as well would make both replacement words visible.
        tracks = [_track("opacity", opacity_keys, "linear")]
        if motion == "text_word_pop_focus":
            tracks.extend([
                _track("scale", [(0, 0.35), (5, 1.18), (10, 0.96), (16, 1.0),
                                  (duration - 1, 1.0)], "out_cubic"),
                _track("position_y", [(0, 28), (9, -5), (16, 0), (duration - 1, 0)], "out_cubic"),
            ])
            motion_animators.append(_pop_blur_animator(duration))
        elif motion in {"text_phrase_soft_rise", "text_keyword_color_emphasis"}:
            active_start = next((frame for frame, opacity in opacity_keys if opacity > 0), 0)
            peak = min(duration - 1, active_start + 7)
            settle = min(duration - 1, active_start + 16)
            tracks.extend([
                _track("scale", [(0, 0.88), (active_start, 0.88), (peak, 1.08),
                                  (settle, 1.0),
                                  (duration - 1, 1.0)], "out_cubic"),
                _track("position_y", [(0, 56), (active_start, 56), (peak, -7),
                                       (settle, 0),
                                       (duration - 1, 0)], "out_cubic"),
            ])
            motion_animators.append(_pop_blur_animator(duration, start=active_start, tracking=9,
                                                       peak_blur=12, exit_blur=0))
    elif motion == "text_word_pop_focus":
        tracks = [_track("scale", [(0, 0.35), (5, 1.18), (10, 0.96), (16, 1.0),
                                    (duration - 13, 1.0), (duration - 1, 4.6)], "out_cubic"),
                  _track("position_y", [(0, 28), (9, -5), (16, 0), (duration - 13, 0),
                                        (duration - 1, -120)], "out_cubic"),
                  _track("opacity", [(0, 0), (5, 1), (duration - 13, 1),
                                     (duration - 1, 0)], "out_cubic")]
        motion_animators.append(_pop_blur_animator(duration))
    elif motion in {"text_phrase_soft_rise", "text_keyword_color_emphasis", "text_trailing_word_reveal"}:
        tracks = [_track("position_y", [(0, 56), (12, -7), (24, 0),
                                        (duration - 1, 0)], "out_cubic"),
                  _track("scale", [(0, 0.88), (12, 1.04), (22, 1.0),
                                   (duration - 1, 1.0)], "out_cubic"),
                  _track("opacity", [(0, 0), (8, 1), (duration - 1, 1)], "out_cubic")]
        motion_animators.append(_pop_blur_animator(duration, tracking=9, peak_blur=12,
                                                   exit_blur=0))
    layer = _text_layer(layer_id, text, role=role, start_frame=start_frame,
                        duration=duration, tracks=tracks, spans=spans,
                        animators=[*(animators or []), *motion_animators])
    return layer


def _single_motion_layers(motion_id: str, duration: int, *, text: str | None = None,
                          accent_word: str | None = None, accent_token: str = "accent.coral",
                          segments: list[str] | None = None,
                          secondary: str | None = None) -> list[dict[str, Any]]:
    if motion_id == "text_word_pop_focus":
        return [_primary_phrase("headline", text or "Think", duration, motion=motion_id,
                                role="display_hero")]
    if motion_id == "text_phrase_soft_rise":
        return [_primary_phrase("headline", text or "Create with intention", duration, motion=motion_id)]
    if motion_id == "text_keyword_color_emphasis":
        phrase = text or "Form follows function"
        word = accent_word or "function"
        return [_primary_phrase("headline", phrase, duration, accent_word=word,
                                accent_token=accent_token, motion=motion_id)]
    if motion_id == "text_accent_word_swap":
        phrase = text or "Design is intelligence"
        first_word, second_word = "Design", phrase.split()[-1]
        swap_in = max(24, duration // 2)
        first_span = _span(phrase, first_word, accent_token, "focus-word-a")
        second_span = _span(phrase, second_word, accent_token, "focus-word-b")
        def color_animator(semantic_id: str, keys: list[tuple[int, str]]) -> dict[str, Any]:
            return {"id": f"{semantic_id}-swap-color", "selectors": [{
                "id": f"{semantic_id}-selector", "unit": "glyph", "semantic_id": semantic_id,
                "shape": "square", "order": "forward", "combine": "replace",
                "exclude_spaces": True,
                "amount": {"easing": "linear", "keyframes": [{"frame": 0, "value": 100}]}}],
                "properties": [{"property": "fill_color", "easing": "linear",
                    "keyframes": [{"frame": frame, "value": _rgba(color)} for frame, color in keys]}]}
        white = EDITORIAL_COLOR_TOKENS["text.primary.white"]
        accent = EDITORIAL_COLOR_TOKENS[accent_token]
        swap_end = min(duration - 1, swap_in + 16)
        def focus_motion(semantic_id: str, is_second: bool) -> dict[str, Any]:
            enter = swap_in if is_second else 0
            peak = min(duration - 1, enter + 7)
            settle = min(duration - 1, enter + 16)
            scale_keys = ([{"frame": 0, "value": [1.0]}, {"frame": enter, "value": [0.82]},
                           {"frame": peak, "value": [1.16]}, {"frame": settle, "value": [1.0]},
                           {"frame": duration - 1, "value": [1.0]}] if is_second else
                          [{"frame": 0, "value": [0.82]}, {"frame": peak, "value": [1.16]},
                           {"frame": settle, "value": [1.0]}, {"frame": duration - 1, "value": [1.0]}])
            blur_keys = ([{"frame": 0, "value": 0}, {"frame": enter, "value": 6},
                          {"frame": settle, "value": 0}, {"frame": duration - 1, "value": 0}]
                         if is_second else [{"frame": 0, "value": 6},
                          {"frame": settle, "value": 0}, {"frame": duration - 1, "value": 0}])
            tracking_keys = ([{"frame": 0, "value": 0}, {"frame": enter, "value": 10},
                              {"frame": settle, "value": 0}, {"frame": duration - 1, "value": 0}]
                             if is_second else [{"frame": 0, "value": 10},
                              {"frame": settle, "value": 0}, {"frame": duration - 1, "value": 0}])
            return _span_motion_animator(semantic_id, [
                {"property": "scale", "easing": "linear", "keyframes": scale_keys},
                {"property": "blur", "easing": "linear", "keyframes": blur_keys},
                {"property": "tracking", "easing": "linear", "keyframes": tracking_keys},
            ])
        return [_text_layer("headline", phrase, duration=duration, spans=[first_span, second_span],
                tracks=[_track("opacity", [(0, 0), (6, 1), (duration - 1, 1)])],
                animators=[
                    color_animator("focus-word-a", [(0, accent), (swap_in, accent), (swap_end, white)]),
                    color_animator("focus-word-b", [(0, white), (swap_in, white), (swap_end, accent)]),
                    focus_motion("focus-word-a", False), focus_motion("focus-word-b", True),
                ])]
    if motion_id == "text_underline_draw":
        phrase = text or "Form follows function"
        word = accent_word or phrase.split()[-1]
        return [_primary_phrase("headline", phrase, duration, accent_word=word,
                                accent_token=accent_token, motion="text_phrase_soft_rise"),
                *_underline_layers("keyword-underline", 1400, 620, 560, accent_token, duration)]
    if motion_id == "text_word_replace_same_line":
        first, second = text or "Think", secondary or "Repeat"
        swap = max(26, duration // 2)
        second_layer = _primary_phrase("word-b", second, duration,
            opacity_keys=[(0, 0), (swap, 0), (swap + 8, 1), (duration - 1, 1)])
        second_layer["animation"]["tracks"].append(
            _track("scale", [(0, 0.74), (swap + 4, 0.74), (swap + 8, 1.14),
                              (swap + 15, 1.0), (duration - 1, 1.0)], "out_cubic"))
        second_layer["animation"]["tracks"].append(
            _track("position_x", [(0, 42), (swap + 8, 0), (duration - 1, 0)], "out_cubic"))
        second_layer.setdefault("text_animators", []).append(
            _pop_blur_animator(duration, tracking=16, peak_blur=6, exit_blur=0))
        first_layer = _primary_phrase("word-a", first, duration,
            opacity_keys=[(0, 0), (6, 1), (swap, 1), (swap + 8, 0), (duration - 1, 0)])
        first_layer["animation"]["tracks"].append(
            _track("scale", [(0, 0.9), (10, 1.08), (17, 1.0), (swap, 1.0),
                              (swap + 8, 0.82), (duration - 1, 0.82)], "out_cubic"))
        first_layer["animation"]["tracks"].append(
            _track("position_x", [(0, -20), (10, 0), (swap, 0), (swap + 8, -46),
                                   (duration - 1, -46)], "out_cubic"))
        first_layer.setdefault("text_animators", []).append(
            _pop_blur_animator(duration, tracking=8, peak_blur=5, exit_blur=10))
        return [
            first_layer,
            second_layer,
        ]
    if motion_id == "text_large_to_small_handoff":
        hero = text or "CREATE"
        subtitle = secondary or "Create with intention"
        change = max(30, duration // 2)
        hero_layer = _text_layer("hero-word", hero, role="display_hero", center=(960, 500),
            duration=duration, tracks=[
                _track("scale", [(0, 2.6), (5, 2.85), (change, 0.46),
                                 (duration - 1, 0.46)], "in_out_cubic"),
                _track("position_y", [(0, 80), (5, 0), (change, -138),
                                       (duration - 1, -138)], "in_out_cubic"),
                _track("opacity", [(0, 0), (5, 1), (duration - 13, 1),
                                    (duration - 1, 0)])],
            animators=[_pop_blur_animator(duration, tracking=10, peak_blur=6, exit_blur=8)])
        sub_layer = _text_layer("secondary-phrase", subtitle, role="display_l", center=(960, 660),
            duration=duration, opacity=0.0, tracks=[
                _track("scale", [(0, 0.84), (change, 0.84), (change + 5, 1.08),
                                 (change + 12, 1.0), (duration - 1, 1.0)]),
                _track("position_y", [(0, 40), (change, 40), (change + 12, 0),
                                       (duration - 1, 0)]),
                _track("opacity", [(0, 0), (change, 0), (change + 10, 1),
                                    (duration - 1, 1)])],
            animators=[_pop_blur_animator(duration, tracking=10, peak_blur=6, exit_blur=0)])
        return [hero_layer, sub_layer]
    if motion_id == "text_stagger_phrase_segments":
        rows = segments or ["Text is a", "design", "element"]
        delay = max(6, (duration - 30) // max(1, len(rows)))
        layers = []
        for index, row in enumerate(rows):
            at = index * delay
            is_accent = index == (len(rows) // 2)
            layers.append(_text_layer(f"segment-{index}", row,
                center=(960, 355 + index * 165), role="display_l",
                fill=EDITORIAL_COLOR_TOKENS[accent_token] if is_accent else None,
                duration=duration, tracks=[
                    _track("position_y", [(0, 60), (at + 5, -8), (at + 12, 0),
                                           (duration - 1, 0)], "out_cubic"),
                    _track("scale", [(0, 0.72), (at + 6, 1.12), (at + 14, 1.0),
                                      (duration - 1, 1.0)], "out_cubic"),
                    _track("opacity", [(0, 0), (at + 5, 1), (duration - 1, 1)], "out_cubic")],
                animators=[_pop_blur_animator(duration, tracking=13, peak_blur=7, exit_blur=0)]))
        return layers
    if motion_id == "text_trailing_word_reveal":
        phrase = text or "Good design feels effortless"
        word = accent_word or phrase.split()[-1]
        layer = _text_layer("headline", phrase, role="display_l", duration=duration,
                            spans=[_span(phrase, word, accent_token, "trailing-word")],
                            animators=[{"id": "trailing-word-reveal", "selectors": [{
                                "id": "trailing-word-selector", "unit": "glyph", "semantic_id": "trailing-word",
                                "shape": "square", "order": "forward", "combine": "replace",
                                "exclude_spaces": True,
                                "amount": {"easing": "linear", "keyframes": [
                                    {"frame": 0, "value": 0}, {"frame": 28, "value": 100}]}}],
                                "properties": [{"property": "opacity", "easing": "linear",
                                    "keyframes": [{"frame": 0, "value": 0}, {"frame": 28, "value": 1}]}]}])
        layer["text_animators"].append(_span_motion_animator("trailing-word", [
            {"property": "scale", "easing": "linear", "keyframes": [
                {"frame": 0, "value": [0.72]}, {"frame": 22, "value": [0.72]},
                {"frame": 30, "value": [1.14]}, {"frame": 38, "value": [1.0]},
                {"frame": duration - 1, "value": [1.0]}]},
            {"property": "blur", "easing": "linear", "keyframes": [
                {"frame": 0, "value": 7}, {"frame": 28, "value": 7},
                {"frame": 36, "value": 0}, {"frame": duration - 1, "value": 0}]},
            {"property": "tracking", "easing": "linear", "keyframes": [
                {"frame": 0, "value": 14}, {"frame": 28, "value": 14},
                {"frame": 42, "value": 0}, {"frame": duration - 1, "value": 0}]},
        ], amount_keys=[(0, 0), (22, 0), (30, 100)]))
        layer["animation"] = {"tracks": [_track("opacity", [(0, 0), (10, 1), (duration - 1, 1)])]}
        return [layer]
    if motion_id == "text_crossfade_phrase":
        first, second = text or "Make it simple", secondary or "Thanks for watching"
        swap = max(26, duration // 2)
        outgoing = _primary_phrase("phrase-a", first, duration,
            opacity_keys=[(0, 0), (6, 1), (swap, 1), (swap + 10, 0),
                          (duration - 1, 0)], motion="text_phrase_soft_rise")
        outgoing["animation"]["tracks"] = [track for track in outgoing["animation"]["tracks"]
                                            if track["property"] != "scale"]
        outgoing["animation"]["tracks"].append(
            _track("scale", [(0, 0.92), (6, 1.0), (swap, 1.0),
                              (swap + 10, 1.24), (duration - 1, 1.24)], "in_out_cubic"))
        incoming = _primary_phrase("phrase-b", second, duration,
            opacity_keys=[(0, 0), (swap, 0), (swap + 10, 1),
                          (duration - 1, 1)], motion="text_phrase_soft_rise")
        incoming["animation"]["tracks"] = [track for track in incoming["animation"]["tracks"]
                                            if track["property"] != "scale"]
        incoming["animation"]["tracks"].append(
            _track("scale", [(0, 0.82), (swap, 0.82), (swap + 6, 1.08),
                              (swap + 15, 1.0), (duration - 1, 1.0)], "out_cubic"))
        return [outgoing, incoming]
    raise ValueError(f"unknown editorial text motion: {motion_id}")


def _recipe_layers(recipe_id: str, duration: int) -> list[dict[str, Any]]:
    recipe = SCENE_RECIPES[recipe_id]
    motion = recipe["motion"]
    if motion == "text_stagger_phrase_segments":
        layers = _single_motion_layers(motion, duration, segments=recipe["segments"],
                                       accent_token=recipe["accent"])
    elif motion == "text_large_to_small_handoff":
        layers = _single_motion_layers(motion, duration, text=recipe["text"],
                                       secondary=recipe["secondary"])
    else:
        layers = _single_motion_layers(motion, duration, text=recipe["text"],
            accent_word=recipe.get("accent_word"), accent_token=recipe["accent"])
    combined = recipe.get("combine", [])
    if "text_keyword_color_emphasis" in combined:
        for layer in layers:
            if layer.get("type") == "text" and layer.get("text") == recipe.get("text"):
                spans = layer.setdefault("spans", [])
                if not spans:
                    spans.append(_span(recipe["text"], recipe["accent_word"], recipe["accent"]))
                if not any(item.get("id") == "accent-word-color-emphasis"
                           for item in layer.get("text_animators", [])):
                    layer.setdefault("text_animators", []).append(_keyword_animator(
                        "accent-word", EDITORIAL_COLOR_TOKENS["text.primary.white"],
                        EDITORIAL_COLOR_TOKENS[recipe["accent"]]))
    if "text_underline_draw" in combined:
        for layer in layers:
            if layer.get("type") == "text" and layer.get("text") == recipe.get("text"):
                spans = layer.setdefault("spans", [])
                if not spans:
                    spans.append(_span(recipe["text"], recipe["accent_word"], recipe["accent"]))
                if not any(item.get("id") == "accent-word-color-emphasis"
                           for item in layer.get("text_animators", [])):
                    layer.setdefault("text_animators", []).append(_keyword_animator(
                        "accent-word", EDITORIAL_COLOR_TOKENS["text.primary.white"],
                        EDITORIAL_COLOR_TOKENS[recipe["accent"]]))
        if not any(layer["id"] == "keyword-underline" for layer in layers):
            layers.extend(_underline_layers("keyword-underline", 1400, 620, 560, recipe["accent"], duration))
    return layers


def _plan(job_id: str, background_id: str, content_layers: list[dict[str, Any]],
          duration: int, *, gallery: bool = False) -> dict[str, Any]:
    layers = _aurora_layers(background_id, duration)
    # A semantic accent span drives a synchronized magenta light source behind
    # the phrase. The image remains an ordinary Vulkan image layer; no CPU FX.
    accent_fill = next((track["keyframes"][-1]["value"]
        for layer in content_layers for animator in layer.get("text_animators", [])
        for track in animator.get("properties", [])
        if track.get("property") == "fill_color" and track.get("keyframes")), _rgba("#FF6D5E"))
    texture_token = min(("accent.coral", "accent.yellow", "accent.lavender"),
        key=lambda token: sum((accent_fill[channel] - _rgba(EDITORIAL_COLOR_TOKENS[token])[channel]) ** 2
                              for channel in range(3)))
    texture_name = texture_token.replace(".", "_") + ".png"
    if any(layer.get("spans") for layer in content_layers):
        layers.append({
            "id": "accent-light-reaction", "type": "image",
            "asset": f"ChrononTemplate/assets/kinetic_type_editorial_v1/{texture_name}",
            "size": [1060, 620], "position": [430, 235], "fit": "stretch",
            "start_frame": 0, "duration_frames": duration, "opacity": 0.44,
            "animation": {"tracks": [
                _track("opacity", [(0, 0.12), (12, 0.58),
                                    (24, 0.30), (duration - 1, 0.22)], "out_cubic"),
                _track("scale", [(0, 0.82), (18, 1.12),
                                 (duration - 1, 0.94)], "in_out_sine"),
            ]},
        })
    label = _text_layer("editorial-label", "CHRONON  /  KINETIC TYPE", center=(320, 112),
                        role="label_xs", fill=EDITORIAL_COLOR_TOKENS["text.secondary.gray"],
                        duration=duration)
    label["size"] = [360, 48]
    layers.append(label)
    layers.extend(content_layers)
    plan = {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": duration},
        "layers": layers,
        "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"},
    }
    validate_plan(plan)
    return plan


def build_motion_plan(motion_id: str) -> dict[str, Any]:
    examples = {
        "text_word_pop_focus": {"text": "Think", "background": "bg_aurora_focus_swell"},
        "text_phrase_soft_rise": {"text": "Create with intention", "background": "bg_aurora_breathe"},
        "text_accent_word_swap": {"text": "Design is intelligence", "background": "bg_aurora_crossfade"},
        "text_keyword_color_emphasis": {"text": "Form follows function", "accent_word": "function", "background": "bg_aurora_soft_drift"},
        "text_underline_draw": {"text": "Form follows function", "accent_word": "function", "background": "bg_aurora_focus_swell"},
        "text_word_replace_same_line": {"text": "Think", "secondary": "Repeat", "background": "bg_aurora_shift_left_right"},
        "text_large_to_small_handoff": {"text": "CREATE", "secondary": "Create with intention", "background": "bg_aurora_deep_vignette"},
        "text_stagger_phrase_segments": {"segments": ["Text is a", "design", "element"], "background": "bg_aurora_crossfade"},
        "text_trailing_word_reveal": {"text": "Good design feels effortless", "accent_word": "effortless", "background": "bg_aurora_corner_heat"},
        "text_crossfade_phrase": {"text": "Make it simple", "secondary": "Thanks for watching", "background": "bg_aurora_soft_drift"},
    }
    if motion_id not in examples:
        raise ValueError(f"unknown editorial text motion: {motion_id}")
    example = examples[motion_id]
    layers = _single_motion_layers(motion_id, SCENE_FRAMES, **{
        key: value for key, value in example.items() if key != "background"})
    return _plan(f"canary_{motion_id}", example["background"], layers, SCENE_FRAMES)


def build_background_plan(background_id: str) -> dict[str, Any]:
    if background_id not in BACKGROUND_PRESETS:
        raise ValueError(f"unknown editorial background: {background_id}")
    return _plan(f"canary_{background_id}", background_id,
                 [_text_layer("background-label", "EDITORIAL AURORA", role="display_l",
                              duration=SCENE_FRAMES,
                              tracks=[_track("opacity", [(0, 0), (12, 1),
                                                          (SCENE_FRAMES - 1, 1)])])],
                 SCENE_FRAMES)


def build_recipe_plan(recipe_id: str) -> dict[str, Any]:
    if recipe_id not in SCENE_RECIPES:
        raise ValueError(f"unknown editorial recipe: {recipe_id}")
    recipe = SCENE_RECIPES[recipe_id]
    return _plan(f"canary_{recipe_id}", recipe["background"],
                 _recipe_layers(recipe_id, SCENE_FRAMES), SCENE_FRAMES)


def build_gallery_plan() -> dict[str, Any]:
    duration = (len(GALLERY_SCENES) - 1) * (GALLERY_SCENE_FRAMES - GALLERY_OVERLAP_FRAMES) + GALLERY_SCENE_FRAMES
    layers = []
    for index, (scene_id, phrase, accent_word) in enumerate(GALLERY_SCENES):
        start = index * (GALLERY_SCENE_FRAMES - GALLERY_OVERLAP_FRAMES)
        end = GALLERY_SCENE_FRAMES - 1
        fade = GALLERY_OVERLAP_FRAMES
        fade_in = fade
        opacity = [(0, 0.0), (fade_in, 1.0), (end - fade, 1.0), (end, 0.0)]
        motion = "text_word_pop_focus" if len(phrase.split()) == 1 else "text_phrase_soft_rise"
        layer = _primary_phrase(f"gallery-{scene_id}", phrase, GALLERY_SCENE_FRAMES,
                                accent_word=accent_word, accent_token="accent.coral",
                                start_frame=start, opacity_keys=opacity, motion=motion,
                                role="display_hero" if motion == "text_word_pop_focus" else "display_l")
        if scene_id == "design_is_intelligence":
            gradient_spans, gradient_animators = _segmented_gradient_spans(
                phrase, "Design", "gradient-design",
                [EDITORIAL_COLOR_TOKENS["accent.coral"],
                 EDITORIAL_COLOR_TOKENS["bg.blob.hot_pink"],
                 EDITORIAL_COLOR_TOKENS["bg.blob.magenta"]])
            layer["spans"] = [*gradient_spans, *layer.get("spans", [])]
            layer["text_animators"].extend(gradient_animators)
        layer["position"] = [960, 520]
        layers.append(layer)
    return _plan("editorial_typography_gallery_v1", "bg_aurora_soft_drift",
                 layers, duration, gallery=True)


def all_plans() -> list[dict[str, Any]]:
    plans = [build_motion_plan(motion_id) for motion_id in TEXT_MOTION_IDS]
    plans.extend(build_background_plan(background_id) for background_id in BACKGROUND_PRESETS)
    plans.extend(build_recipe_plan(recipe_id) for recipe_id in SCENE_RECIPES)
    plans.append(build_gallery_plan())
    ids = [plan["job_id"] for plan in plans]
    if len(ids) != len(set(ids)):
        raise ValueError("editorial canary plan ids must be unique")
    return plans


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema") != "chronon.render-plan.v3" or plan.get("version") != 3:
        raise ValueError("editorial plans must use chronon.render-plan.v3")
    canvas = plan.get("canvas", {})
    if (canvas.get("width"), canvas.get("height"), canvas.get("fps_num"), canvas.get("fps_den")) != (WIDTH, HEIGHT, FPS, 1):
        raise ValueError(f"{plan.get('job_id')}: canvas must be 1920x1080 at 30fps")
    duration = canvas.get("duration_frames", 0)
    layers = plan.get("layers", [])
    ids = [layer.get("id") for layer in layers]
    if not duration or len(ids) != len(set(ids)):
        raise ValueError(f"{plan.get('job_id')}: duration and unique layer ids are required")
    if len(layers) > 32:
        raise ValueError(f"{plan.get('job_id')}: layer budget exceeded ({len(layers)} > 32)")
    for layer in layers:
        start = layer.get("start_frame", 0)
        layer_duration = layer.get("duration_frames", duration)
        if start < 0 or layer_duration < 1 or start + layer_duration > duration:
            raise ValueError(f"{plan['job_id']}/{layer['id']}: layer lifetime escapes the canvas timeline")
        if layer.get("type") == "text":
            x, y = layer["position"][:2]
            width, height = layer["size"][:2]
            if layer["id"] == "editorial-label":
                if x - width / 2 < 120 or x + width / 2 > WIDTH - 120:
                    raise ValueError(f"{plan['job_id']}/{layer['id']}: label exceeds horizontal safe area")
                if y - height / 2 < 80 or y + height / 2 > HEIGHT - 100:
                    raise ValueError(f"{plan['job_id']}/{layer['id']}: label exceeds vertical safe area")
            else:
                intentional_hero_crop = layer.get("style", {}).get("font_size", 0) >= 400
                if not intentional_hero_crop and (x - width / 2 < 120 or x + width / 2 > WIDTH - 120):
                    raise ValueError(f"{plan['job_id']}/{layer['id']}: text exceeds horizontal safe area")
                if y - height / 2 < 100 or y + height / 2 > HEIGHT - 100:
                    raise ValueError(f"{plan['job_id']}/{layer['id']}: text exceeds vertical safe area")
        animation = layer.get("animation", {})
        tracks = animation.get("tracks", [])
        for track in tracks:
            keys = track.get("keyframes", [])
            frames = [key["frame"] for key in keys]
            if frames != sorted(set(frames)) or any(frame < 0 or frame >= layer_duration for frame in frames):
                raise ValueError(f"{plan['job_id']}/{layer['id']}: invalid {track.get('property')} keyframe timeline")
        for animator in layer.get("text_animators", []):
            for track in animator.get("properties", []):
                frames = [key["frame"] for key in track.get("keyframes", [])]
                if frames != sorted(set(frames)) or any(frame < 0 or frame >= layer_duration for frame in frames):
                    raise ValueError(f"{plan['job_id']}/{layer['id']}: invalid text animator timeline")
        for span in layer.get("spans", []):
            if span["start"] < 0 or span["end"] <= span["start"] or span["end"] > len(layer["text"].encode("utf-8")):
                raise ValueError(f"{plan['job_id']}/{layer['id']}: span byte range is outside its UTF-8 text")


def write_plans(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    plans = all_plans()
    paths = []
    for plan in plans:
        destination = out_dir / f"{plan['job_id']}.plan.json"
        destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(destination)
    manifest = {
        "schema": "chronontemplate.kinetic-type-editorial.v1",
        "family": "Kinetic Type Editorial V1",
        "renderer": "ChrononTemplate -> chronon.render-plan.v3 -> Chronon3D",
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "color_tokens": EDITORIAL_COLOR_TOKENS,
        "typography_tokens": TYPOGRAPHY_TOKENS,
        "background_presets": sorted(BACKGROUND_PRESETS),
        "text_motions": list(TEXT_MOTION_IDS),
        "scene_recipes": sorted(SCENE_RECIPES),
        "gallery_scenes": [scene[0] for scene in GALLERY_SCENES],
        "render_policy": "Vulkan rendering with NVIDIA NVENC encoding, bounded sequential chunks",
        "plans": [path.name for path in paths],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def _run_cli(cli: Path, paths: list[Path], *, render_scene: str | None = None,
             render_all: bool = False, render_backend: str = "vulkan",
             render_chunk_frames: int = 30,
             render_from: str | None = None) -> int:
    plan_ids = [path.stem.removesuffix(".plan") for path in paths]
    if render_all:
        selected = list(zip(plan_ids, paths))
    elif render_scene:
        selected = [(plan_id, path) for plan_id, path in zip(plan_ids, paths)
                    if plan_id == render_scene or plan_id.removeprefix("canary_") == render_scene]
        if not selected:
            print(f"unknown canary scene {render_scene!r}; choose one of {plan_ids}", file=sys.stderr)
            return 2
    else:
        selected = list(zip(plan_ids, paths))
    if render_from is not None:
        indexes = [i for i, (plan_id, _) in enumerate(selected) if plan_id == render_from]
        if not indexes:
            print(f"unknown --render-from plan {render_from!r}; choose one of {plan_ids}", file=sys.stderr)
            return 2
        selected = selected[indexes[0]:]
    for plan_id, path in selected:
        command = [str(cli), "validate", "--plan", str(path), "--assets-root", str(WORKSPACE), "--profile", "preview"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            print(f"FAIL validate {plan_id}:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return result.returncode
        print(f"PASS validate {plan_id}", flush=True)
    if render_scene is not None or render_all:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if render_backend == "vulkan" and (not ffmpeg or not ffprobe):
            print("FAIL segmented Vulkan rendering requires ffmpeg and ffprobe", file=sys.stderr)
            return 2
        if render_backend == "vulkan":
            encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"],
                                      capture_output=True, text=True)
            if encoders.returncode or "h264_nvenc" not in encoders.stdout:
                print("FAIL Vulkan delivery requires FFmpeg h264_nvenc; CPU encoding is disabled",
                      file=sys.stderr)
                return 2
        for plan_id, path in selected:
            output = path.with_suffix(".mp4")
            if render_backend == "vulkan":
                plan = json.loads(path.read_text(encoding="utf-8"))
                canvas = plan["canvas"]
                if (canvas.get("width"), canvas.get("height")) != (WIDTH, HEIGHT):
                    print(f"FAIL render {plan_id}: expected {WIDTH}x{HEIGHT} canvas", file=sys.stderr)
                    return 1
                total_frames = int(canvas["duration_frames"])
                segment_dir = Path(tempfile.mkdtemp(prefix=f"{plan_id}.segments.", dir=path.parent))
                segment_paths = []
                pending_ranges = [(start, min(start + render_chunk_frames, total_frames) - 1)
                                  for start in range(0, total_frames, render_chunk_frames)]
                print(f"RENDER Vulkan → NV12 raw → NVENC {plan_id}: {total_frames} frames in <= {render_chunk_frames}-frame jobs",
                      flush=True)
                while pending_ranges:
                    start, end = pending_ranges.pop(0)
                    segment = segment_dir / f"segment_{start:06d}_{end:06d}.raw"
                    command = [str(cli), "render", "--plan", str(path), "--assets-root", str(WORKSPACE),
                               "--backend", "vulkan", "--profile", "preview",
                               "--fps", str(FPS), "--video-sink", "raw", "--pipe-pixfmt", "nv12",
                               "--chunks", "1",
                               "--fb-pool-budget-mb", "512", "--fb-pool-clear-policy", "trim-after-job",
                               "--start-frame", str(start), "--end-frame", str(end),
                               "-o", str(segment)]
                    result = subprocess.run(command, capture_output=True, text=True)
                    if result.returncode or not segment.exists() or segment.stat().st_size == 0:
                        lower_limit = min(MIN_VULKAN_CHUNK_FRAMES, render_chunk_frames)
                        if end - start + 1 > lower_limit:
                            segment.unlink(missing_ok=True)
                            midpoint = (start + end) // 2
                            smaller = [(start, midpoint), (midpoint + 1, end)]
                            pending_ranges = smaller + pending_ranges
                            print(f"RETRY Vulkan {plan_id} frames {start}-{end} as "
                                  f"{smaller[0][0]}-{smaller[0][1]} and {smaller[1][0]}-{smaller[1][1]}",
                                  flush=True)
                            continue
                        detail = (result.stderr or result.stdout).splitlines()[-12:]
                        print(f"FAIL render {plan_id} frames {start}-{end}:\n" + "\n".join(detail),
                              file=sys.stderr)
                        shutil.rmtree(segment_dir, ignore_errors=True)
                        return result.returncode or 1
                    segment_paths.append(segment)
                raw_path = segment_dir / "joined.nv12"
                with raw_path.open("wb") as joined_raw:
                    for segment in segment_paths:
                        with segment.open("rb") as raw_part:
                            shutil.copyfileobj(raw_part, joined_raw, length=1024 * 1024)
                expected_raw_bytes = total_frames * WIDTH * HEIGHT * 3 // 2
                if raw_path.stat().st_size != expected_raw_bytes:
                    print(f"FAIL raw frame stream {plan_id}: got {raw_path.stat().st_size} bytes, "
                          f"expected {expected_raw_bytes}", file=sys.stderr)
                    shutil.rmtree(segment_dir, ignore_errors=True)
                    return 1
                encoded = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "rawvideo",
                                         "-pixel_format", "nv12", "-video_size", f"{WIDTH}x{HEIGHT}",
                                         "-framerate", str(FPS), "-i", str(raw_path),
                                         "-frames:v", str(total_frames), "-vsync", "cfr",
                                         "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "18", "-b:v", "0",
                                         "-pix_fmt", "yuv420p", "-r", str(FPS),
                                         "-video_track_timescale", str(FPS * 1000), str(output)],
                                        capture_output=True, text=True)
                shutil.rmtree(segment_dir, ignore_errors=True)
                if encoded.returncode:
                    print(f"FAIL NVENC encode {plan_id}:\n{encoded.stderr}", file=sys.stderr)
                    return encoded.returncode
                probe = subprocess.run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                                        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames",
                                        "-of", "json", str(output)], capture_output=True, text=True)
                if probe.returncode:
                    print(f"FAIL probe {plan_id}:\n{probe.stderr}", file=sys.stderr)
                    return probe.returncode
                stream = json.loads(probe.stdout)["streams"][0]
                actual = (int(stream["width"]), int(stream["height"]), int(stream["nb_read_frames"]),
                          Fraction(stream["avg_frame_rate"]))
                expected = (WIDTH, HEIGHT, total_frames, Fraction(FPS, 1))
                if actual != expected:
                    print(f"FAIL output {plan_id}: got {actual}, expected {expected}", file=sys.stderr)
                    return 1
            else:
                command = [str(cli), "render", "--plan", str(path), "--assets-root", str(WORKSPACE),
                           "--backend", render_backend, "--hardware", "none", "--profile", "preview",
                           "--fps", str(FPS), "--encoder-backend", "pipe", "--chunks", "1",
                           "--fb-pool-budget-mb", "256", "--fb-pool-clear-policy", "trim-after-job",
                           "-o", str(output)]
                print(f"RENDER sequentially {plan_id} -> {output.name}", flush=True)
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode or not output.exists() or output.stat().st_size == 0:
                    print(f"FAIL render {plan_id}:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
                    return result.returncode or 1
            print(f"PASS render {output.name} ({output.stat().st_size} bytes)", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="directory for plans and manifest")
    parser.add_argument("--validate-only", action="store_true", help="validate every generated plan with Chronon3D")
    parser.add_argument("--cli", type=Path, help="Chronon3D CLI used for validation and rendering")
    parser.add_argument("--render", action="store_true", help="render only the hero-word canary unless --scene is set")
    parser.add_argument("--render-all", action="store_true", help="render every plan sequentially (one renderer process at a time)")
    parser.add_argument("--render-backend", choices=("vulkan", "software"), default="vulkan",
                        help="renderer backend for video exports (default: vulkan)")
    parser.add_argument("--render-chunk-frames", type=int, default=30,
                        help="maximum frames per Vulkan renderer process before automatic subdivision (default: 30)")
    parser.add_argument("--scene", help="motion, recipe or gallery plan id to validate/render")
    parser.add_argument("--render-from", help="with --render-all, resume rendering from this plan id")
    args = parser.parse_args()
    if (args.validate_only or args.render or args.render_all) and not args.cli:
        parser.error("--validate-only/--render requires --cli")
    if args.render and args.render_all:
        parser.error("choose --render or --render-all")
    if args.render_chunk_frames < 1:
        parser.error("--render-chunk-frames must be at least 1")
    if args.render_from and not args.render_all:
        parser.error("--render-from requires --render-all")
    paths = write_plans(args.out)
    print(f"PASS wrote {len(paths)} deterministic V3 plans and manifest to {args.out}")
    if args.validate_only or args.render or args.render_all:
        return _run_cli(args.cli.resolve(), paths,
                        render_scene=(args.scene or "canary_text_word_pop_focus") if args.render else None,
                        render_all=args.render_all, render_backend=args.render_backend,
                        render_chunk_frames=args.render_chunk_frames, render_from=args.render_from)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
