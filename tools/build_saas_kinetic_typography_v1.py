#!/usr/bin/env python3
"""SaaS Kinetic Typography V1 — six archetype canaries + one gallery.

Replicates the reference preview's kinetic-type beats with renderer-native
primitives only (per-glyph selector windows, layer masks, shape gradients,
spring/bezier easings).  ChrononTemplate owns composition and timing;
Chronon3D owns shaping, rasterization and pixels — no per-glyph layout is
computed here beyond PIL word measurement for multi-word staggers.

Archetypes (one canary each):
  1. saas_velocity_drop          — per-glyph vertical fall, velocity-synced blur
  2. saas_word_stagger_stretch   — per-word stagger with tracking stretch
  3. saas_split_decapitation     — vertical split mask, halves slide apart
  4. saas_underline_spring       — phrase pop + elastic vector underline draw
  5. saas_glossy_shimmer         — gradient gloss + animated specular sweep
  6. saas_rotation_snap          — kinetic rotation snap (spring settle)
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DEFAULT_OUT = ROOT / "golden_plans" / "saas_kinetic_typography_v1"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
FONT_POPPINS = "Chronon3d/assets/fonts/Poppins-Bold.ttf"
FONT_INTER = "Chronon3d/assets/fonts/Inter-Bold.ttf"

BG_DARK = [0.028, 0.028, 0.048, 1.0]      # #07070C
INK = "#F5F6FA"
INK_SOFT = "#C7D2FE"
ACCENT = "#818CF8"
ACCENT_DEEP = "#6D28D9"
SNAPPY_OUT = [0.16, 1.0, 0.3, 1.0]         # cubic-bezier(0.16, 1, 0.3, 1)


# ═══════════════════════════════════════════════════════════════ helpers ═══
def _rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    color = hex_color.lstrip("#")
    if len(color) != 6:
        raise ValueError(f"expected #RRGGBB, got {hex_color!r}")
    return [int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def _track(prop: str, keys: list[tuple[int, Any]], easing: str = "out_cubic",
           **extra: Any) -> dict[str, Any]:
    track: dict[str, Any] = {"property": prop, "easing": easing,
        "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}
    track.update(extra)
    return track


def _anim(name: str, selector: dict[str, Any], properties: list[dict[str, Any]],
          ) -> dict[str, Any]:
    return {"id": name, "selectors": [selector], "properties": properties}


def _prop(prop: str, keys: list[tuple[int, Any]], easing: str = "linear",
          **extra: Any) -> dict[str, Any]:
    # RenderPlan V3 text-animator property tracks deliberately freeze easing
    # to linear; custom easing belongs on layer tracks. Keep this boundary
    # explicit so generated plans fail neither schema nor renderer validation.
    del easing, extra
    return {"property": prop, "easing": "linear",
        "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def _full_window(unit: str = "glyph", duration: int = 90) -> dict[str, Any]:
    return {"id": "all", "unit": unit, "shape": "square", "order": "forward",
            "combine": "replace", "exclude_spaces": True,
            "amount": {"easing": "linear", "keyframes": [
                {"frame": 0, "value": 100},{ "frame": duration - 1, "value": 100}]}}


def _measure(text: str, font_size: int, font: str = FONT_POPPINS) -> float:
    return ImageFont.truetype(str(WORKSPACE / font), font_size).getlength(text)


def _text_layer(layer_id: str, text: str, *, center: tuple[float, float],
                font_size: int, fill: str = INK, font: str = FONT_POPPINS,
                duration: int, start_frame: int = 0, opacity: float = 1.0,
                tracks: list[dict[str, Any]] | None = None,
                animators: list[dict[str, Any]] | None = None,
                style_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    width = _measure(text, font_size, font)
    layer: dict[str, Any] = {
        "id": layer_id, "type": "text", "text": text,
        "size": [round(width + 80), round(font_size * 2.2)],
        "position": [center[0], center[1]], "start_frame": start_frame,
        "duration_frames": duration, "opacity": opacity,
        "style": {"font": font, "font_size": float(font_size),
                  "min_font_size": max(12, font_size // 3),
                  "max_font_size": float(font_size), "fit_mode": "shrink_only",
                  "fill": fill},
    }
    if style_extra:
        layer["style"].update(style_extra)
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if animators:
        layer["text_animators"] = animators
    return layer


def _bg(duration: int, color: list[float] | None = None,
        layer_id: str = "background") -> dict[str, Any]:
    return {"id": layer_id, "type": "color", "color": color or BG_DARK,
            "size": [WIDTH, HEIGHT], "start_frame": 0, "duration_frames": duration}


def _plan(job_id: str, layers: list[dict[str, Any]], duration: int) -> dict[str, Any]:
    plan = {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                   "fps_den": 1, "duration_frames": duration},
        "layers": layers,
        "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"},
    }
    validate_plan(plan)
    return plan


# ══════════════════════════════════════════════════════════════ validator ═══
def _check_track_frames(track: dict[str, Any], duration: int, where: str) -> None:
    for key in track.get("keyframes", []):
        frame = key["frame"]
        if not 0 <= frame <= duration - 1:
            raise ValueError(f"{where}: keyframe frame {frame} outside [0, {duration - 1}]")
        value = key["value"]
        values = value if isinstance(value, list) else [value]
        for component in values:
            if not isinstance(component, (int, float)) or component != component \
                    or component in (float("inf"), float("-inf")):
                raise ValueError(f"{where}: non-finite keyframe value {value!r}")


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema") != "chronon.render-plan.v3" or plan.get("version") != 3:
        raise ValueError("plans must use chronon.render-plan.v3")
    job = plan.get("job_id", "?")
    canvas = plan.get("canvas", {})
    if (canvas.get("width"), canvas.get("height"),
            canvas.get("fps_num"), canvas.get("fps_den")) != (WIDTH, HEIGHT, FPS, 1):
        raise ValueError(f"{job}: canvas must be 1920x1080 at 30fps")
    duration = canvas.get("duration_frames", 0)
    layers = plan.get("layers", [])
    ids = [layer.get("id") for layer in layers]
    if not duration or len(ids) != len(set(ids)):
        raise ValueError(f"{job}: duration and unique layer ids are required")
    if len(layers) > 32:
        raise ValueError(f"{job}: layer budget exceeded ({len(layers)} > 32)")
    text_ids = {layer["id"] for layer in layers if layer.get("type") == "text"}
    for layer in layers:
        where = f"{job}/{layer.get('id')}"
        for track in layer.get("animation", {}).get("tracks", []):
            _check_track_frames(track, duration, where)
        for animator in layer.get("text_animators", []):
            for track in animator.get("properties", []):
                _check_track_frames(track, duration, where)
            for selector in animator.get("selectors", []):
                for bound in ("start", "end", "offset", "amount"):
                    _check_track_frames(selector[bound], duration,
                                        f"{where}/{bound}") if bound in selector else None
        for mask in layer.get("masks", []):
            if mask.get("type") == "text":
                if mask.get("source") not in text_ids:
                    raise ValueError(f"{where}: text mask source is not a text layer")
            for bound in ("feather_track", "expansion_track", "opacity_track"):
                if bound in mask:
                    _check_track_frames(mask[bound], duration, f"{where}/{bound}")
        gradient_anim = layer.get("fill_gradient_animation")
        if gradient_anim:
            base_fill = layer.get("shape", {}).get("fill")
            if not isinstance(base_fill, dict) or base_fill.get("type") != \
                    gradient_anim["keyframes"][0]["value"]["type"]:
                raise ValueError(f"{where}: fill_gradient_animation base fill type mismatch")
            for key in gradient_anim.get("keyframes", []):
                if not 0 <= key["frame"] <= duration - 1:
                    raise ValueError(f"{where}: gradient keyframe outside duration")
        if layer.get("type") == "text" and "style" not in layer:
            raise ValueError(f"{where}: text layer requires style")


# ═════════════════════════════════════════════════════════════════ scenes ═══
# ── Archetype 1: per-glyph vertical fall + velocity-synced blur ──────────
def scene_velocity_drop_layers(duration: int = 90) -> list[dict[str, Any]]:
    """'Busy': glyphs drop from above; each glyph's blur pulses while it moves
    fastest (a round band trails the reveal frontier) and decays as it settles.
    The shared fall value curve uses the snappy-out bezier from the spec."""
    reveal = max(10, round(duration * 0.22))          # frontier sweep end
    settle = max(reveal + 4, round(duration * 0.42))  # fall value reaches 0
    exit_at = round(duration * 0.80)
    hero = _text_layer(
        "drop-hero", "Busy", center=(960, 540), font_size=200, duration=duration,
        tracks=[
            _track("opacity", [(0, 0), (6, 1), (exit_at, 1), (duration - 1, 0)], "out_quad"),
            _track("scale", [(0, 1.0), (exit_at, 1.0), (duration - 1, 2.5)], "in_expo"),
        ],
        animators=[
            # Visibility gate: the not-yet-revealed suffix holds opacity 0.
            _anim("drop-gate",
                  {"id": "gate", "unit": "grapheme", "shape": "square",
                   "order": "forward", "combine": "replace", "exclude_spaces": True,
                   "start": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 0}, {"frame": reveal, "value": 100},
                       {"frame": duration - 1, "value": 100}]},
                   "end": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 100},
                       {"frame": duration - 1, "value": 100}]}},
                  [_prop("opacity", [(0, 0), (duration - 1, 0)])]),
            # Fall: revealed glyphs ride one snappy-out curve from -300 to 0.
            _anim("drop-fall",
                  {"id": "fall", "unit": "grapheme", "shape": "ramp_down",
                   "order": "forward", "combine": "replace", "exclude_spaces": True,
                   "start": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 0}, {"frame": reveal, "value": 100},
                       {"frame": duration - 1, "value": 100}]},
                   "end": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 100},
                       {"frame": duration - 1, "value": 100}]}},
                  [_prop("position_y", [(0, -300), (settle, 0)], "bezier",
                          bezier_curve=SNAPPY_OUT)]),
            # Motion blur: a round band leads the frontier; weight peaks just
            # after each glyph reveals, so blur tracks the fastest motion.
            _anim("drop-blur-band",
                  {"id": "band", "unit": "grapheme", "shape": "round",
                   "order": "forward", "combine": "replace", "exclude_spaces": True,
                   "start": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 0}, {"frame": reveal, "value": 100},
                       {"frame": duration - 1, "value": 100}]},
                   "end": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 13}, {"frame": reveal, "value": 100},
                       {"frame": duration - 1, "value": 100}]}},
                  [_prop("blur", [(0, 24), (duration - 1, 24)])]),
            # Zoom-through exit blur.
            _anim("drop-exit-blur",
                  {**_full_window(duration=duration), "id": "exit"},
                  [_prop("blur", [(exit_at, 0), (duration - 1, 18)], "in_quad")]),
        ])
    return [_bg(duration), hero]


# ── Archetype 2: per-word stagger with tracking stretch ──────────────────
def scene_word_stagger_layers(duration: int = 90) -> list[dict[str, Any]]:
    """'Busy isn't productive': word-per-layer stagger; each word enters with
    an opacity ramp, a tracking stretch collapsing 34px -> 0 and a 1.18 -> 1
    zoom settle.  The emphasised word carries the indigo accent + glow."""
    words = [("Busy", INK, False), ("isn't", INK, False), ("productive", ACCENT, True)]
    font_size, gap, stagger = 118, 26, 6
    widths = [_measure(word, font_size) for word, _, _ in words]
    total = sum(widths) + gap * (len(words) - 1)
    x = 960.0 - total / 2.0
    layers: list[dict[str, Any]] = [_bg(duration)]
    for index, (word, fill, accent) in enumerate(words):
        start = index * stagger
        local_duration = duration - start
        center_x = x + widths[index] / 2.0
        style_extra: dict[str, Any] = {}
        if accent:
            style_extra["glow"] = {"radius": 30.0, "intensity": 0.85,
                                   "color": ACCENT}
        layers.append(_text_layer(
            f"word-{index}", word, center=(center_x, 540), font_size=font_size,                fill=fill, duration=local_duration, start_frame=start,
            tracks=[
                _track("opacity", [(0, 0), (6, 1),
                                    (local_duration - 1, 1)], "out_quad"),
                _track("scale", [(0, 1.18), (14, 1.0),
                                  (local_duration - 1, 1.0)], "out_cubic"),
                _track("position_y", [(0, -16), (12, 0),
                                        (local_duration - 1, 0)], "out_cubic"),
            ],
            animators=[_anim(
                "tracking-stretch",
                _full_window("word", duration),
                [_prop("tracking", [(0, 34), (16, 0),
                                     (local_duration - 1, 0)], "out_cubic")]),
            ],
            style_extra=style_extra))
        x += widths[index] + gap
    return layers


# ── Archetype 3: vertical split (decapitation) with masked halves ────────
def scene_split_decapitation_layers(duration: int = 90) -> list[dict[str, Any]]:
    """'Stop': the intact word holds, then a feathered horizontal cut at the
    optical centre splits it — the top half slides up, the bottom half slides
    down while its mask dissolves into the background."""
    font_size = 210
    width = _measure("Stop", font_size)
    box_w, box_h = round(width + 80), round(font_size * 2.2)
    split = round(duration * 0.50)
    slide_end = min(duration - 1, split + round(duration * 0.36))
    base_tracks = [
        _track("opacity", [(0, 0), (6, 1), (split, 1), (split + 1, 0),
                            (duration - 1, 0)], "out_quad"),
        _track("scale", [(0, 0.72), (12, 1.0), (duration - 1, 1.0)], "out_back"),
    ]
    base = _text_layer("split-base", "Stop", center=(960, 540),
                       font_size=font_size, duration=duration, tracks=base_tracks)
    top_mask = {"type": "rect", "mode": "add",
                "position": [0, -box_h / 4], "size": [box_w + 160, box_h / 2 + 10],
                "feather": 4.0}
    bottom_mask = {"type": "rect", "mode": "add",
                   "position": [0, box_h / 4], "size": [box_w + 160, box_h / 2 + 10],
                   "feather": 4.0,
                   "opacity_track": {"easing": "linear", "keyframes": [
                       {"frame": 0, "value": 1}, {"frame": round(duration * 0.62), "value": 1},
                       {"frame": duration - 1, "value": 0}]}}
    common = dict(center=(960, 540), font_size=font_size, duration=duration)
    top = _text_layer(
        "split-top", "Stop", tracks=[
            _track("opacity", [(0, 0), (split, 0), (split + 1, 1),
                                (round(duration * 0.86), 0.92), (duration - 1, 0)],
                   "out_quad"),
            _track("position_y", [(0, 0), (split, 0), (slide_end, -64),
                                    (duration - 1, -64)], "out_cubic"),
        ], **common)
    top["masks"] = [top_mask]
    bottom = _text_layer(
        "split-bottom", "Stop", tracks=[
            _track("opacity", [(0, 0), (split, 0), (split + 1, 1),
                                (round(duration * 0.80), 0), (duration - 1, 0)],
                   "out_quad"),
            _track("position_y", [(0, 0), (split, 0), (slide_end + 2, 74),
                                    (duration - 1, 74)], "out_cubic"),
        ],
        animators=[_anim("bottom-blur", {**_full_window(duration=duration), "id": "blur"},
                         [_prop("blur", [(split, 0), (round(duration * 0.85), 12)],
                                "out_cubic")])],
        **common)
    bottom["masks"] = [bottom_mask]
    return [_bg(duration), base, top, bottom]


# ── Archetype 4: phrase pop + elastic vector underline (trim draw) ───────
def scene_underline_spring_layers(duration: int = 90) -> list[dict[str, Any]]:
    """\"There's a smarter way\": the phrase springs in while an underline is
    drawn left-to-right with a spring curve (trim-draw feel, ~18% overshoot)."""
    font_size = 96
    phrase = "There's a smarter way"
    width = _measure(phrase, font_size)
    underline_w, exit_at = width * 0.86, round(duration * 0.82)
    fade_end = duration - 1
    phrase_layer = _text_layer(
        "underline-phrase", phrase, center=(960, 500), font_size=font_size,
        duration=duration,
        tracks=[
            _track("opacity", [(0, 0), (8, 1), (exit_at, 1), (fade_end, 0)],
                   "out_quad"),
            _track("position_y", [(0, 30), (20, 0), (fade_end, 0)], "spring",
                   spring={"mass": 1.0, "stiffness": 170.0, "damping": 13.0}),
            _track("scale", [(0, 0.94), (20, 1.0), (fade_end, 1.0)], "spring",
                   spring={"mass": 1.0, "stiffness": 170.0, "damping": 13.0}),
        ])

    def underline(identifier: str, height: float, max_opacity: float) -> dict[str, Any]:
        layer = {
            "id": identifier, "type": "shape",
            "shape": {"type": "rounded_rect", "fill": _rgba(ACCENT),
                      "radius": height / 2},
            "size": [underline_w, height], "position": [960, 596],
            "start_frame": 0, "duration_frames": duration, "opacity": max_opacity,
            "animation": {"tracks": [
                _track("scale_x", [(0, 0.0), (18, 1.0), (fade_end, 1.0)],
                       "spring", spring={"mass": 1.0, "stiffness": 110.0,
                                          "damping": 9.0}),
                _track("position_x", [(0, -underline_w / 2), (18, 0),
                                        (fade_end, 0)], "spring",
                       spring={"mass": 1.0, "stiffness": 110.0, "damping": 9.0}),
                _track("opacity", [(0, 0), (10, max_opacity),
                                     (exit_at, max_opacity), (fade_end, 0)],
                       "out_quad"),
            ]}}
        return layer

    return [_bg(duration), phrase_layer,
            underline("underline-afterglow", 22, 0.35),
            underline("underline-core", 8, 1.0)]


# ── Archetype 5: gradient gloss + animated specular shimmer ──────────────
def scene_glossy_shimmer_layers(duration: int = 90) -> list[dict[str, Any]]:
    """'Clarity': a white base carries a vertical white->violet gloss gradient
    and an animated radial specular sweep through a text mask; a stroked copy
    underneath provides the bevel edge."""
    font_size = 230
    word = "Clarity"
    width = _measure(word, font_size)
    box = [round(width + 120), round(font_size * 2.4)]
    rise_end, exit_at, fade_end = 12, round(duration * 0.84), duration - 1
    rise = _track("position_y", [(0, 18), (rise_end, 0), (fade_end, 0)], "out_cubic")

    def envelope(opacity_peak: float) -> list[dict[str, Any]]:
        return [rise, _track("opacity", [(0, 0), (10, opacity_peak),
                                          (exit_at, opacity_peak), (fade_end, 0)],
                              "out_quad")]

    stroke_copy = _text_layer(
        "glossy-stroke", word, center=(960, 540), font_size=font_size,
        fill="#C7D2FE", duration=duration, opacity=0.9,
        tracks=envelope(0.9),
        style_extra={"stroke": {"color": "#A5B4FC", "width": 3.0},
                     "shadow": {"color": "#1E1B4B", "opacity": 0.8,
                                 "blur": 18.0, "offset": [0.0, 10.0]}})
    base_copy = _text_layer(
        "glossy-base", word, center=(960, 540), font_size=font_size,
        fill="#F8FAFC", duration=duration, tracks=envelope(1.0))
    text_mask = {"type": "text", "mode": "add", "source": "glossy-base"}
    gloss_base = {
        "id": "glossy-gradient", "type": "shape", "shape": {
            "type": "rect",
            "fill": {"type": "linear", "start": [0.0, 0.0], "end": [0.0, 1.0],
                     "spread": "pad", "color_stops": [
                         {"position": 0.02, "color": _rgba("#FFFFFF")},
                         {"position": 0.48, "color": _rgba("#E0E7FF")},
                         {"position": 0.98, "color": _rgba(ACCENT_DEEP)}]}},
        "size": box, "position": [960, 540], "start_frame": 0,
        "duration_frames": duration, "masks": [text_mask],
        "animation": {"tracks": envelope(1.0)},
    }
    shimmer_stops = [{"position": 0.0, "color": _rgba("#FFFFFF", 0.95)},
                     {"position": 1.0, "color": _rgba("#FFFFFF", 0.0)}]
    sweep = round(duration * 0.32)
    shimmer = {
        "id": "glossy-shimmer", "type": "shape", "shape": {
            "type": "rect",
            "fill": {"type": "radial", "center": [0.08, 0.45], "radius": 0.5,
                     "spread": "pad", "color_stops": shimmer_stops}},
        "size": box, "position": [960, 540], "start_frame": 0,
        "duration_frames": duration, "masks": [dict(text_mask)],
        "animation": {"tracks": envelope(0.85)},
        "fill_gradient_animation": {"easing": "linear", "keyframes": [
            {"frame": 0, "value": {"type": "radial", "center": [0.05, 0.45],
                                    "radius": 0.5, "spread": "pad",
                                    "color_stops": shimmer_stops}},
            {"frame": sweep, "value": {"type": "radial", "center": [0.5, 0.45],
                                        "radius": 0.5, "spread": "pad",
                                        "color_stops": shimmer_stops}},
            {"frame": sweep * 2, "value": {"type": "radial", "center": [0.95, 0.45],
                                            "radius": 0.5, "spread": "pad",
                                            "color_stops": shimmer_stops}},
            {"frame": fade_end, "value": {"type": "radial", "center": [0.95, 0.45],
                                           "radius": 0.5, "spread": "pad",
                                           "color_stops": shimmer_stops}},
        ]},
    }
    return [_bg(duration, layer_id="glossy-bg"), stroke_copy, base_copy,
            gloss_base, shimmer]


# ── Archetype 6: kinetic rotation snap (spring settle) ───────────────────
def scene_rotation_snap_layers(duration: int = 90) -> list[dict[str, Any]]:
    """'Start today': the phrase swings in ~26deg and snaps to 0 on a spring,
    then snap-zooms out through the cut."""
    settle, exit_at, fade_end = 16, round(duration * 0.84), duration - 1
    spring = {"mass": 1.0, "stiffness": 190.0, "damping": 12.0}
    hero = _text_layer(
        "snap-hero", "Start today", center=(960, 540), font_size=130,
        duration=duration,
        tracks=[
            _track("rotation_z", [(0, 26.0), (settle, 0.0), (fade_end, 0.0)],
                   "spring", spring=spring),
            _track("scale", [(0, 0.85), (settle, 1.0), (exit_at, 1.0),
                              (fade_end, 0.12)], "spring", spring=spring),
            _track("opacity", [(0, 0), (8, 1), (exit_at, 1), (fade_end, 0)],
                   "out_quad"),
        ],
        animators=[_anim("snap-exit-blur", {**_full_window(duration=duration), "id": "exit"},
                         [_prop("blur", [(exit_at, 0), (fade_end, 16)], "in_quad")])])
    return [_bg(duration), hero]


# ── Gallery: one linked sequence showing all six animation grammars ──────
SCENES = [
    ("saas_velocity_drop", scene_velocity_drop_layers),
    ("saas_word_stagger_stretch", scene_word_stagger_layers),
    ("saas_split_decapitation", scene_split_decapitation_layers),
    ("saas_underline_spring", scene_underline_spring_layers),
    ("saas_glossy_shimmer", scene_glossy_shimmer_layers),
    ("saas_rotation_snap", scene_rotation_snap_layers),
]


def build_scene(scene_id: str, duration: int = 90) -> dict[str, Any]:
    for key, builder in SCENES:
        if key == scene_id:
            return _plan(scene_id, builder(duration), duration)
    raise ValueError(f"unknown SaaS kinetic type scene: {scene_id}")


def build_gallery() -> dict[str, Any]:
    """Single plan gallery; non-overlapping 3-second beats, consistent canvas."""
    duration, beat = len(SCENES) * 90, 90
    layers: list[dict[str, Any]] = []
    for index, (scene_id, builder) in enumerate(SCENES):
        offset = index * beat
        local = builder(beat)
        for layer in local:
            # Each beat is a 90-frame clip placed on the gallery timeline;
            # track and animator keyframes remain clip-local, like start_frame.
            layer = copy.deepcopy(layer)
            old_id = layer["id"]
            layer["id"] = f"{scene_id}-{old_id}"
            if "masks" in layer:
                for mask in layer["masks"]:
                    if mask.get("type") == "text":
                        mask["source"] = f"{scene_id}-{mask['source']}"
            layer["start_frame"] = layer.get("start_frame", 0) + offset
            layers.append(layer)
    return _plan("saas_kinetic_typography_gallery_v1", layers, duration)


def all_plans() -> list[dict[str, Any]]:
    plans = [build_scene(scene_id) for scene_id, _ in SCENES]
    plans.append(build_gallery())
    return plans


def write_plans(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for plan in all_plans():
        path = out_dir / f"{plan['job_id']}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scene", choices=[key for key, _ in SCENES])
    parser.add_argument("--validate-only", action="store_true",
                        help="build and check plans without writing files")
    parser.add_argument("--cli", type=Path,
                        help="optional Chronon3D CLI for native plan validation")
    parser.add_argument("--assets-root", type=Path, default=WORKSPACE,
                        help="absolute asset root passed to chronon3d_cli")
    parser.add_argument("--render", action="store_true",
                        help="render all plans with chronon3d_cli")
    args = parser.parse_args()

    plans = [build_scene(args.scene)] if args.scene else all_plans()
    if args.render and not args.cli:
        raise SystemExit("--render requires --cli")
    if args.validate_only and not args.cli:
        print(f"SAAS_KINETIC_VALIDATE_PASS plans={len(plans)}")
        return 0

    cli = args.cli.resolve() if args.cli else None
    if cli is not None and not cli.is_file():
        raise SystemExit(f"Chronon3D CLI not found: {cli}")

    def validate_paths(paths: list[Path]) -> None:
        assert cli is not None
        for path in paths:
            command = [str(cli), "validate", "--plan", str(path.resolve()),
                       "--assets-root", str(args.assets_root.resolve())]
            subprocess.run(command, cwd=WORKSPACE, check=True)
        print(f"CHRONON3D_VALIDATE_PASS plans={len(paths)}")

    if args.validate_only:
        with tempfile.TemporaryDirectory(prefix="saas_kinetic_plans_") as temp_dir:
            paths = []
            for plan in plans:
                path = Path(temp_dir) / f"{plan['job_id']}.plan.json"
                path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
                paths.append(path)
            validate_paths(paths)
        print(f"SAAS_KINETIC_VALIDATE_PASS plans={len(plans)}")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    paths = []
    for plan in plans:
        path = args.out / f"{plan['job_id']}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
        print(f"WROTE {path}")
    if cli is not None:
        validate_paths(paths)
        if args.render:
            for path in paths:
                command = [str(cli), "render", "--plan", str(path.resolve()),
                           "--assets-root", str(args.assets_root.resolve())]
                subprocess.run(command, cwd=WORKSPACE, check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError) as error:
        print(f"SAAS_KINETIC_VALIDATE_FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)


# CHUNK_TAIL
