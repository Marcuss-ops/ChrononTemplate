#!/usr/bin/env python3
"""Generate golden plans for metric_v1, date_v1 and entity_card_v1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "ChrononTemplate"
CATALOG = TEMPLATE / "catalog/entity_presentation.v1.json"
DEFAULT_ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
DEFAULT_OUT = TEMPLATE / "golden_plans/entity_presentation_v1"
CANARY_IMAGE = "assets/canary/people-demo-portrait.png"
FONT = "assets/fonts/Poppins-Bold.ttf"
SMALL_FONT = "assets/fonts/DejaVuSans.ttf"

METRIC_SAMPLES = (
    "42%", "$3.4B", "42", "1.25M", "+18.6%", "72%", "1.2M", "9.8x",
    "€12.5M", "120 km", "1,250,000", "42.5", "-12", "+18.7",
    "$8.2M", "−$12.4M", "68%", "3.7x", "18,420", "2026 vs 2025",
)
DATE_SAMPLES = (
    "2026", "March 2026", "30 September 2026", "Q4 2026", "2010–2020", "1999/2000",
    "12 October 2026", "JULY · 2026", "1990 → 2026", "18 MAY 2026",
    "2024 / 2026", "2001–2025", "12 DEC 2025", "FY 2026", "Q1 → Q4",
    "1998", "2026 EDITION", "1980—2026", "31/12/2026", "2030",
)
METRIC_COUNTERS = {
    "metric_counter_rise": {"from": 0, "to": 0.42, "format": "percent", "decimals": 0},
    "metric_counter_scale_settle": {"from": 0, "to": 3.4e9, "format": "compact", "decimals": 1, "prefix": "$"},
    "metric_odometer_vertical": {"from": 0, "to": 42, "format": "plain", "decimals": 0},
    "metric_digits_stagger": {"from": 0, "to": 1.25e6, "format": "compact", "decimals": 2},
    "metric_bar_grow": {"from": 0, "to": 0.186, "format": "percent", "decimals": 1, "prefix": "+"},
    "metric_ring_draw": {"from": 0, "to": 0.72, "format": "percent", "decimals": 0},
    "metric_delta_reveal": {"from": 0, "to": 1.2e6, "format": "compact", "decimals": 1},
    "metric_focus_punch": {"from": 0, "to": 9.8, "format": "plain", "decimals": 1, "suffix": "x"},
    "metric_count_flip": {"from": 0, "to": 8.2e6, "format": "compact", "decimals": 1},
    "metric_split_odometer": {"from": 0, "to": 18420, "format": "plain", "decimals": 0},
    "metric_bounce_settle": {"from": 0, "to": 0.68, "format": "percent", "decimals": 0},
    "metric_digit_cascade": {"from": 0, "to": 1250000, "format": "compact", "decimals": 2},
    "metric_pulse_hold": {"from": 0, "to": 3.7, "format": "plain", "decimals": 1, "suffix": "x"},
    "metric_debt_flip": {"from": 0, "to": 12.4e6, "format": "compact", "decimals": 1, "prefix": "−$"},
}
ENTITY_SAMPLES = (
    "Ada Lovelace", "Alexander Jonathan Montgomery Williams", "José Mourinho",
    "François Hollande", "李小龍", "محمد علي",
)

# Script-aware caption font. The gallery captions include Latin, CJK and
# Arabic names; a Latin-only face cannot shape those, so the font is chosen
# from the caption's script while the name itself is never rewritten. The
# mapping is deterministic: one caption, one font, always.
CJK_PATTERN = tuple(range(0x2E80, 0x9FFF + 1))
ARABIC_PATTERN = tuple(range(0x0600, 0x06FF + 1))
CJK_FONT = "assets/fonts/NotoSansCJK-Regular.ttc"
# DejaVuSans is the renderer bundle's Arabic-capable fallback and keeps the
# canary renderable in isolated job workspaces without an extra font asset.
ARABIC_FONT = SMALL_FONT


def caption_font(name: str) -> str:
    """Pick the font that can shape `name` without changing the name."""
    for character in name:
        code = ord(character)
        if CJK_PATTERN[0] <= code <= CJK_PATTERN[-1] and character.isprintable():
            return CJK_FONT
        if ARABIC_PATTERN[0] <= code <= ARABIC_PATTERN[-1]:
            return ARABIC_FONT
    return SMALL_FONT


def caption_text_layer(layer_id: str, name: str, size: list[int], position: list[int], start: int, duration: int, *, font_size: int = 25, tracks=None) -> dict:
    """A name caption: never rewritten, always laid out inside the canvas."""
    return layer_text(layer_id, name, size, position, start, duration,
                      font=caption_font(name), font_size=font_size, min_font_size=16, tracks=tracks)


def track(prop: str, keys: list[tuple[int, object]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "keyframes": [{"frame": frame, "value": value} for frame, value in keys], "easing": easing}


def shift_tracks(tracks: list[dict], start: int) -> list[dict]:
    if start == 0:
        return tracks
    return [{**item, "keyframes": [
        {**key, "frame": key["frame"] + start} for key in item["keyframes"]
    ]} for item in tracks]


def unique_frames(keys: list[tuple[int, object]]) -> list[tuple[int, object]]:
    """Drop later keys whose frame repeats an earlier one; the renderer's
    decoder rejects duplicate keyframe frames, and a repeated frame with the
    same value is always redundant."""
    seen: set[int] = set()
    out: list[tuple[int, object]] = []
    for frame, value in keys:
        if frame in seen:
            continue
        seen.add(frame)
        out.append((frame, value))
    return out


THREE_D_PROPERTIES = {"position_z", "rotation_x", "rotation_y"}
BASE_SEGMENT_FRAMES = 72
SHOWCASE_SEGMENT_FRAMES = 150  # 5 seconds at the canonical 30 fps.


def layer_text(layer_id: str, value: str, size: list[int], position: list[int], start: int, duration: int, *, font=FONT, font_size=54, min_font_size=None, fill="#F5F7FA", tracks=None) -> dict:
    style = {"font": font, "font_size": font_size, "fill": fill, "fit_mode": "shrink_only"}
    if min_font_size is not None:
        style.update(min_font_size=min_font_size, max_font_size=font_size)
    motion = tracks or [track("opacity", [(0, 1), (duration - 1, 1)], "linear")]
    motion = shift_tracks(motion, start)
    layer = {"id": layer_id, "type": "text", "text": value, "size": size, "position": position,
             "start_frame": start, "duration_frames": duration, "style": style,
             "animation": {"tracks": motion}}
    # A layer carrying camera-backed tracks must opt into the 3D render path
    # or the Chronon decoder rejects the plan.
    if any(item["property"] in THREE_D_PROPERTIES for item in motion):
        layer["enable_3d"] = True
    return layer


def renderer_center_position(position: list[int | float]) -> list[float]:
    """Convert canvas pixels to Chronon layer coordinates for image/color layers."""
    return [float(position[0]) - 960.0, float(position[1]) - 540.0]


def canvas_position(layer: dict) -> list[float]:
    """Resolve a plan layer's encoded position back to top-left canvas pixels."""
    x, y = layer["position"]
    if layer["type"] in {"image", "color"}:
        return [float(x) + 960.0, float(y) + 540.0]
    return [float(x), float(y)]


def color_layer(layer_id: str, size: list[int], position: list[int], start: int, duration: int, color: list[float], tracks=None) -> dict:
    value = {"id": layer_id, "type": "color", "color": color, "size": size, "position": renderer_center_position(position),
             "start_frame": start, "duration_frames": duration}
    if tracks:
        value["animation"] = {"tracks": shift_tracks(tracks, start)}
    return value


def trim_path_layer_at(layer_id: str, width: int, position: list[int], start: int, duration: int) -> dict:
    layer = trim_path_layer(layer_id, width, position, start, duration)
    animation = layer["shape"]["operators"][0]["params"]["animation"]
    for key in animation["keyframes"]:
        key["frame"] += start
    return layer



def ring_path_layer(layer_id: str, diameter: int, position: list[int], start: int, duration: int) -> dict:
    radius = diameter * 0.42
    handle = radius * 0.55228475
    path = [
        {"type": "move_to", "point": [0, -radius]},
        {"type": "cubic_to", "control1": [handle, -radius], "control2": [radius, -handle], "point": [radius, 0]},
        {"type": "cubic_to", "control1": [radius, handle], "control2": [handle, radius], "point": [0, radius]},
        {"type": "cubic_to", "control1": [-handle, radius], "control2": [-radius, handle], "point": [-radius, 0]},
        {"type": "cubic_to", "control1": [-radius, -handle], "control2": [-handle, -radius], "point": [0, -radius]},
    ]
    return {
        "id": layer_id, "type": "shape", "size": [diameter, diameter], "position": position,
        "start_frame": start, "duration_frames": duration,
        "shape": {"type": "path", "path": path, "stroke": {"color": "#6ED6C3", "width": 8},
                  "operators": [{"kind": "trim", "params": {"start": 0, "end": 1,
                      "animation": {"keyframes": [{"frame": start, "value": [0, 0, 0]},
                                                       {"frame": start + 48, "value": [0, 1, 0]}]}}}]},
    }


def trim_path_layer(layer_id: str, width: int, position: list[int], start: int, duration: int) -> dict:
    """Native Chronon stroked path with a frame-zero-to-one Trim Paths draw."""
    half_width = width / 2
    return {
        "id": layer_id, "type": "shape", "size": [width, 8], "position": position,
        "start_frame": start, "duration_frames": duration,
        "shape": {
            "type": "path",
            "path": [
                {"type": "move_to", "point": [-half_width, 0]},
                {"type": "line_to", "point": [half_width, 0]},
            ],
            "stroke": {"color": "#6ED6C3", "width": 4},
            "operators": [{"kind": "trim", "params": {
                "start": 0, "end": 1,
                "animation": {"keyframes": [
                    {"frame": 0, "value": [0, 0, 0]},
                    {"frame": 34, "value": [0, 1, 0]},
                ]},
            }}],
        },
    }


def scene_plan(job_id: str, layers: list[dict], frames: int) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
            "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1, "duration_frames": frames},
            "layers": layers, "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"}}


def retime_plan(plan: dict) -> dict:
    """Stretch each authored 72-frame showcase segment to five seconds.

    Temporal galleries keep their per-preset boundaries while single-scene
    canaries (including the 120-frame duo) stretch across one five-second
    segment. Every animation/counter/trim key is retimed with its layer, so the
    motion remains visible throughout the longer output rather than freezing
    after the original short entrance.
    """
    old_total = plan["canvas"]["duration_frames"]
    segmented = old_total >= BASE_SEGMENT_FRAMES and old_total % BASE_SEGMENT_FRAMES == 0
    old_segment = BASE_SEGMENT_FRAMES if segmented else old_total
    new_segment = SHOWCASE_SEGMENT_FRAMES

    def map_frame(frame: int) -> int:
        segment_index, local = divmod(frame, old_segment)
        local = min(local, old_segment - 1)
        scaled_local = round(local * (new_segment - 1) / (old_segment - 1))
        return segment_index * new_segment + scaled_local

    for layer in plan["layers"]:
        old_start = layer["start_frame"]
        old_duration = layer["duration_frames"]
        old_end = old_start + old_duration - 1
        new_start = map_frame(old_start)
        new_end = map_frame(old_end)
        layer["start_frame"] = new_start
        layer["duration_frames"] = new_end - new_start + 1
        for animation_track in layer.get("animation", {}).get("tracks", []):
            for key in animation_track["keyframes"]:
                key["frame"] = map_frame(key["frame"])
        for operator in layer.get("shape", {}).get("operators", []):
            for key in operator.get("params", {}).get("animation", {}).get("keyframes", []):
                key["frame"] = map_frame(key["frame"])
        if layer.get("text_counter"):
            counter = layer["text_counter"]["counter"]
            counter["start_frame"] = new_start
            # Keep native counting live over the full five-second layer window.
            counter["duration_frames"] = layer["duration_frames"]

    plan["canvas"]["duration_frames"] = (
        old_total // old_segment * new_segment if segmented else new_segment
    )
    return plan


def with_motion_tracks(catalog_tracks: list[dict], duration: int, offset: int = 0) -> list[dict]:
    adjusted = []
    for item in catalog_tracks:
        frames = []
        for key in item["keyframes"]:
            frame = min(max(key["frame"] - offset, 0), duration - 1)
            if frames and frame <= frames[-1]["frame"]:
                continue
            frames.append({"frame": frame, "value": key["value"]})
        if not frames or frames[0]["frame"] != 0:
            frames.insert(0, {"frame": 0, "value": item["keyframes"][0]["value"]})
        if len(frames) == 1:
            frames.append({"frame": duration - 1, "value": frames[0]["value"]})
        elif frames[-1]["frame"] < duration - 1:
            frames.append({"frame": duration - 1, "value": frames[-1]["value"]})
        adjusted.append({"property": item["property"], "keyframes": frames, "easing": item.get("easing", "out_cubic")})
    return adjusted


def build_metric_gallery(family: dict) -> dict:
    presets, duration = family["presets"], 72
    layers = [color_layer("gallery-background", [1920, 1080], [960, 540], 0, len(presets) * duration, [0.018, 0.032, 0.043, 1])]
    for index, preset in enumerate(presets):
        start = index * duration
        sample = METRIC_SAMPLES[index % len(METRIC_SAMPLES)]
        if preset["id"] == "metric_before_after":
            sample = ""
        layers.append(layer_text(f"{preset['id']}-eyebrow", "METRIC V1 MOTION GALLERY", [760, 42], [960, 330], start, duration, font=SMALL_FONT, font_size=24, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (18, 1), (71, 1)], "out_cubic")]))
        # Discrete deterministic counter values keep the render-plan text static
        # per layer while implementing a visible count-up in the renderer.
        if preset["id"] in METRIC_COUNTERS:
            counter = METRIC_COUNTERS[preset["id"]]
            value_layer = layer_text(f"{preset['id']}-value", "{{value}}", [1060, 150], [960, 515], start, duration, font_size=82, min_font_size=46, tracks=with_motion_tracks(preset["tracks"], duration))
            value_layer["text_counter"] = {
                "token": "{{value}}",
                "counter": {**counter, "start_frame": start, "duration_frames": 48},
            }
            layers.append(value_layer)
        elif preset["id"] == "metric_multi_stat_focus":
            for stat_index, (stat_label, stat_value) in enumerate((("REVENUE", "$3.4B"), ("USERS", "2.1M"), ("GROWTH", "42%"))):
                cx = 600 + stat_index * 360
                emphasis = [(0, 1), (12 + stat_index * 4, 1.045), (26 + stat_index * 4, 1), (71, 1)]
                layers.append(layer_text(f"{preset['id']}-label-{stat_index}", stat_label, [300, 40], [cx, 410], start, duration, font=SMALL_FONT, font_size=22, fill="#91A5AD", tracks=[track("opacity", [(0, 1), (71, 1)], "linear")]))
                layers.append(layer_text(f"{preset['id']}-value-{stat_index}", stat_value, [320, 100], [cx, 520], start, duration, font_size=58, tracks=[track("opacity", [(0, 1), (71, 1)], "linear"), track("scale", emphasis)]))
        elif preset["id"] not in {"metric_before_after", "metric_compare_wipe"}:
            layers.append(layer_text(f"{preset['id']}-value", sample, [1060, 150], [960, 515], start, duration, font_size=82, min_font_size=46, tracks=with_motion_tracks(preset["tracks"], duration)))
        if preset["id"] in {"metric_ring_draw", "metric_arc_sweep"}:
            ring_id = "metric-ring-draw" if preset["id"] == "metric_ring_draw" else "metric-arc-sweep"
            layers.append(ring_path_layer(f"{ring_id}-arc", 250, [960, 725], start, duration))
            ring_label = "72%" if preset["id"] == "metric_ring_draw" else "1.8x"
            layers.append(layer_text(f"{ring_id}-label", ring_label, [170, 44], [960, 725], start, duration, font_size=34, tracks=with_motion_tracks(preset["tracks"], duration)))
        if preset["id"] == "metric_digits_stagger":
            layers.append(layer_text("metric_digits_stagger-intermediate", "1.25M", [300, 70], [960, 650], start, duration, font_size=30, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (30, 1), (71, 1)], "out_cubic")]))
        layers.append(layer_text(f"{preset['id']}-label", "REVENUE GROWTH", [820, 56], [960, 630], start, duration, font=SMALL_FONT, font_size=27, fill="#A8BAC0", tracks=[track("opacity", [(0, 0), (25, 1), (71, 1)], "out_cubic")]))

        if preset["id"] == "metric_bar_grow":
            layers.append(layer_text("metric_bar_grow-secondary", "+18.6%", [320, 60], [960, 665], start, duration, font_size=30, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (30, 1), (71, 1)], "out_cubic")]))
            layers.extend([color_layer(f"{preset['id']}-bar-track", [560, 9], [960, 710], start, duration, [0.20, 0.26, 0.30, 1]), color_layer(f"{preset['id']}-bar-fill", [403, 9], [881, 710], start, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (35, 0.72), (71, 1)], "out_cubic")])])
        if preset["id"] == "metric_delta_reveal":
            layers.append(layer_text("metric-delta-badge", "+12.8%", [220, 60], [1420, 450], start + 20, duration - 20, font_size=30, fill="#6ED6C3", tracks=[track("opacity", [(0, 0), (12, 1), (51, 1)], "out_cubic")]))
            layers.append(layer_text("metric-delta-audience-sample", "AUDIENCE · 1.2M", [360, 44], [960, 700], start + 24, duration - 24, font=SMALL_FONT, font_size=22, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (14, 1), (47, 1)], "out_cubic")]))
        if preset["id"] == "metric_focus_punch":
            layers.append(layer_text("metric-focus-distance-sample", "DISTANCE · 120 km", [380, 44], [960, 700], start + 16, duration - 16, font=SMALL_FONT, font_size=22, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (14, 1), (55, 1)], "out_cubic")]))
        if preset["id"] == "metric_multi_stat_focus":
            layers.append(layer_text("metric-multi-stat-distance", "DISTANCE · 120 km", [380, 42], [960, 700], start + 12, duration - 12, font=SMALL_FONT, font_size=20, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (16, 1), (59, 1)], "out_cubic")]))
        if preset["id"] == "metric_focus_punch":
            layers.append(layer_text("metric-focus-punch-sample", "9.8x", [180, 42], [960, 758], start + 18, duration - 18, font_size=24, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (16, 1), (53, 1)], "out_cubic")]))
        if preset["id"] == "metric_multi_stat_focus":
            layers.append(layer_text("metric-multi-stat-audience", "1.2M", [180, 42], [960, 758], start + 18, duration - 18, font_size=24, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (20, 1), (53, 1)], "out_cubic")]))
        if preset["id"] == "metric_before_after":
            layers.append(layer_text("metric-before-value", "$2.1B", [360, 100], [660, 540], start, duration, font_size=52, fill="#91A5AD", tracks=[track("opacity", [(0, 1), (71, 0.65)], "out_cubic"), track("scale", [(0, 1), (40, 0.92), (71, 0.92)], "out_cubic")]))
            layers.append(layer_text("metric-before-after-arrow", "→", [100, 80], [960, 540], start, duration, font_size=48, fill="#6ED6C3", tracks=[track("opacity", [(0, 0), (20, 1), (71, 1)], "out_cubic")]))
            layers.append(layer_text("metric-after-value", "$3.4B", [360, 100], [1260, 540], start, duration, font_size=58, tracks=[track("opacity", [(0, 0), (22, 1), (71, 1)], "out_cubic"), track("scale", [(0, 0.94), (30, 1), (71, 1)], "out_cubic")]))
    return scene_plan("metric_v1_gallery_20", layers, len(presets) * duration)


def metric_counter_layer(layer_id: str, preset: dict, counter: dict, position: list[int], *, size: list[int] = [300, 88], font_size: int = 50) -> dict:
    value = layer_text(layer_id, "{{value}}", size, position, 0, 72, font_size=font_size,
                       min_font_size=28, tracks=with_motion_tracks(preset["tracks"], 72))
    value["text_counter"] = {"token": "{{value}}", "counter": {**counter, "start_frame": 0, "duration_frames": 48}}
    return value


def build_metric_five_value_canary(family: dict) -> dict:
    """One simultaneous scene for the five requested representative metrics."""
    presets = {preset["id"]: preset for preset in family["presets"]}
    samples = (
        ("metric_counter_rise", "42%", {"from": 0, "to": 0.42, "format": "percent", "decimals": 0}, "GROWTH", (340, 330)),
        ("metric_counter_scale_settle", "$3.4B", {"from": 0, "to": 3.4e9, "format": "compact", "decimals": 1, "prefix": "$"}, "REVENUE", (960, 330)),
        ("metric_bar_grow", "+18.6%", {"from": 0, "to": 0.186, "format": "percent", "decimals": 1, "prefix": "+"}, "YEAR OVER YEAR", (1580, 330)),
        ("metric_delta_reveal", "1.2M", {"from": 0, "to": 1.2e6, "format": "compact", "decimals": 1}, "AUDIENCE", (650, 790)),
        ("metric_ring_draw", "72%", {"from": 0, "to": 0.72, "format": "percent", "decimals": 0}, "COMPLETION", (1270, 790)),
    )
    duration = 72
    layers = [color_layer("background", [1920, 1080], [960, 540], 0, duration, [0.018, 0.032, 0.043, 1])]
    for preset_id, display, counter, label, (cx, cy) in samples:
        preset = presets[preset_id]
        layers.append(color_layer(f"{preset_id}-card", [500, 300], [cx, cy], 0, duration, [0.055, 0.078, 0.092, 1]))
        if preset_id == "metric_delta_reveal":
            layers.append(metric_counter_layer(f"{preset_id}-value", preset, counter, [cx, cy - 42]))
            layers.append(layer_text(f"{preset_id}-badge", "+12.8%", [180, 36], [cx + 145, cy - 95], 18, 54, font_size=24, fill="#6ED6C3", tracks=[track("opacity", [(0, 0), (12, 1), (53, 1)], "out_cubic")]))
        else:
            layers.append(metric_counter_layer(f"{preset_id}-value", preset, counter, [cx, cy - 46]))
        layers.append(layer_text(f"{preset_id}-label", label, [400, 38], [cx, cy + 22], 0, duration, font=SMALL_FONT, font_size=20, fill="#A8BAC0", tracks=[track("opacity", [(0, 0), (24, 1), (71, 1)], "out_cubic")]))
        if preset_id == "metric_bar_grow":
            layers.extend([color_layer("metric-five-bar-track", [300, 8], [cx, cy + 88], 0, duration, [0.20, 0.26, 0.30, 1]),
                           color_layer("metric-five-bar-fill", [186, 8], [cx - 57, cy + 88], 0, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (35, 0.72), (71, 1)], "out_cubic")])])
        if preset_id == "metric_ring_draw":
            layers.append(ring_path_layer("metric-five-ring-arc", 120, [cx, cy + 105], 0, duration))
    return scene_plan("metric_v1_canary_five_values", layers, duration)


def build_metric_gallery_2x5(family: dict) -> dict:
    """Twenty concurrent metric alternatives in a safe 4x5 editorial grid."""
    positions = [(190 + column * 385, 180 + row * 240)
                 for row in range(4) for column in range(5)]
    duration = 72
    layers = [color_layer("background", [1920, 1080], [960, 540], 0, duration, [0.018, 0.032, 0.043, 1]),
              layer_text("gallery-title", "METRIC V1 · 4 × 5 · 20 ALTERNATIVES", [1200, 38], [960, 34], 0, duration, font=SMALL_FONT, font_size=22, fill="#A8BAC0")]
    for preset, (cx, cy) in zip(family["presets"], positions):
        preset_id = preset["id"]
        sample = METRIC_SAMPLES[family["presets"].index(preset)]
        layers.append(color_layer(f"{preset_id}-tile", [350, 205], [cx, cy], 0, duration, [0.055, 0.078, 0.092, 1]))

        if preset_id in METRIC_COUNTERS:
            counter = METRIC_COUNTERS[preset_id]
            value = metric_counter_layer(f"{preset_id}-value", preset, counter, [cx, cy - 92], size=[320, 90], font_size=46)
            layers.append(value)
        elif preset_id == "metric_multi_stat_focus":
            for column, (label, value) in enumerate((("REVENUE", "$3.4B"), ("USERS", "1.2M"), ("GROWTH", "42%"))):
                stat_x = cx + (column - 1) * 106
                layers.append(layer_text(f"{preset_id}-stat-label-{column}", label, [100, 24], [stat_x, cy - 115], 0, duration, font=SMALL_FONT, font_size=12, fill="#91A5AD"))
                layers.append(layer_text(f"{preset_id}-stat-value-{column}", value, [102, 48], [stat_x, cy - 75], 0, duration, font_size=22))
        elif preset_id in {"metric_before_after", "metric_compare_wipe"}:
            old_value, new_value = ("$2.1B", "$3.4B") if preset_id == "metric_before_after" else ("$2.8B", "$3.4B")
            layers.append(layer_text(f"{preset_id}-old", old_value, [135, 52], [cx - 76, cy - 92], 0, duration, font_size=27, fill="#91A5AD"))
            layers.append(layer_text(f"{preset_id}-arrow", "→", [40, 52], [cx, cy - 92], 0, duration, font_size=28, fill="#6ED6C3"))
            layers.append(layer_text(f"{preset_id}-new", new_value, [135, 52], [cx + 76, cy - 92], 0, duration, font_size=27))
        else:
            layers.append(layer_text(f"{preset_id}-value", sample, [320, 90], [cx, cy - 75], 0, duration, font_size=42, min_font_size=24, tracks=with_motion_tracks(preset["tracks"], duration)))
        layers.append(layer_text(f"{preset_id}-label", "REVENUE GROWTH", [320, 28], [cx, cy - 17], 0, duration, font=SMALL_FONT, font_size=15, fill="#A8BAC0"))
        layers.append(layer_text(f"{preset_id}-preset", preset_id, [330, 32], [cx, cy + 28], 0, duration, font=SMALL_FONT, font_size=14, fill="#91A5AD"))
        if preset_id == "metric_bar_grow":
            layers.extend([color_layer("metric-grid-bar-track", [250, 7], [cx, cy + 104], 0, duration, [0.20, 0.26, 0.30, 1]),
                           color_layer("metric-grid-bar-fill", [180, 7], [cx - 35, cy + 104], 0, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (35, 0.72), (71, 1)], "out_cubic")])])
        if preset_id in {"metric_ring_draw", "metric_arc_sweep"}:
            layers.append(ring_path_layer(f"{preset_id}-grid-arc", 64, [cx, cy + 103], 0, duration))
        if preset_id == "metric_delta_reveal":
            layers.append(layer_text("metric-grid-delta-badge", "+12.8%", [130, 30], [cx + 94, cy - 122], 18, 54, font_size=19, fill="#6ED6C3"))
    return scene_plan("metric_v1_gallery_4x5", layers, duration)


def build_date_gallery(family: dict) -> dict:
    presets, duration = family["presets"], 72
    layers = [color_layer("gallery-background", [1920, 1080], [960, 540], 0, len(presets) * duration, [0.04, 0.036, 0.031, 1])]
    for index, preset in enumerate(presets):
        start = index * duration
        sample = DATE_SAMPLES[index % len(DATE_SAMPLES)]
        date_samples = {
            "date_fade_rise": "March 2024",
            "date_year_count": "2026",
            "date_calendar_flip": "30 September 2026",
            "date_segment_stagger": "12 Jan 2026",
            "date_timeline_tick": "2026",
            "date_range_draw": "2010–2020",
            "date_marker_drop": "2024",
            "date_underline_focus": "SEPTEMBER 2008",
            "date_history_stack": "1998",
            "date_chronology_focus": "1990–2020",
            "date_page_turn": "30 SEPTEMBER 2026",
            "date_calendar_drop": "12 OCTOBER 2026",
            "date_month_wipe": "JULY · 2026",
            "date_timeline_sweep": "1990 → 2026",
            "date_marker_pop": "18 MAY 2026",
            "date_split_year": "2024 / 2026",
            "date_bracket_draw": "2001–2025",
            "date_stamp_reveal": "12 DEC 2025",
            "date_era_zoom": "FY 2026",
            "date_digit_flip": "31/12/2026",
        }
        sample = date_samples[preset["id"]]
        layers.append(layer_text(f"{preset['id']}-eyebrow", "DATE MOTION GALLERY", [900, 42], [960, 330], start, duration, font=SMALL_FONT, font_size=22, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (18, 1), (71, 1)], "out_cubic")]))
        date_tracks = with_motion_tracks(preset["tracks"], duration)
        date_layer = layer_text(f"{preset['id']}-date", sample.upper(), [1040, 132], [960, 505], start, duration, font_size=66, min_font_size=40, fill="#F3EFE7", tracks=date_tracks)
        if preset["id"] == "date_year_count":
            date_layer["text_counter"] = {"token": "{{value}}", "counter": {"from": 1990, "to": 2026, "start_frame": start, "duration_frames": 34, "format": "plain", "decimals": 0}}
            date_layer["text"] = "{{value}}"
        elif preset["id"] == "date_range_draw":
            date_layer["text_counter"] = {"token": "{{value}}", "counter": {"from": 2010, "to": 2020, "start_frame": start, "duration_frames": 34, "format": "plain", "decimals": 0}}
            date_layer["text"] = "{{value}}"
            # The renderer's native Trim Paths operator owns the line draw;
            # labels mark the actual start/end year of this range.
            layers.append(trim_path_layer_at("date_range_draw-trim", 680, [960, 735], start, duration))
            for year, x in ((2010, 620), (2020, 1300)):
                layers.append(layer_text(f"date_range_draw-endpoint-{year}", str(year), [160, 34], [x, 785], start, duration, font=SMALL_FONT, font_size=18, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (34, 1), (71, 1)], "out_cubic")]))
            layers.append(layer_text("date_range_draw-normalized-sample", "2010–2020", [260, 38], [960, 845], start, duration, font=SMALL_FONT, font_size=20, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (36, 1), (71, 1)], "out_cubic")]))
        layers.append(date_layer)
        layers.append(layer_text(f"{preset['id']}-event", "PRODUCT LAUNCH", [700, 48], [960, 615], start, duration, font=SMALL_FONT, font_size=25, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (25, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_calendar_flip":
            layers.append(layer_text("date-calendar-quarter-sample", "Q4 2025", [360, 44], [960, 700], start + 22, duration - 22, font_size=28, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (17, 1), (49, 1)], "out_cubic")]))
        if preset["id"] in {"date_calendar_drop", "date_page_turn"}:
            layers.append(color_layer(f"{preset['id']}-calendar-plate", [390, 150], [960, 690], start, duration, [0.075, 0.095, 0.12, 1], [track("scale_y", [(0, 0.01), (24, 0.76), (44, 1), (71, 1)], "out_cubic")]))
            layers.append(layer_text(f"{preset['id']}-calendar-caption", "EDITORIAL DATE", [300, 34], [960, 690], start, duration, font=SMALL_FONT, font_size=18, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (30, 1), (71, 1)], "out_cubic")]))
        if preset["id"] in {"date_month_wipe", "date_bracket_draw"}:
            layers.append(trim_path_layer_at(f"{preset['id']}-accent-trim", 520, [960, 620], start, duration))
        if preset["id"] == "date_timeline_sweep":
            layers.append(color_layer("date_timeline_sweep-rail", [680, 5], [960, 735], start, duration, [0.38, 0.34, 0.29, 1], [track("scale_x", [(0, 0.01), (28, 0.42), (52, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_marker_pop":
            layers.append(color_layer("date_marker_pop-marker", [26, 26], [960, 700], start, duration, [0.43, 0.84, 0.76, 1], [track("scale", [(0, 0.25), (22, 1.18), (38, 0.96), (52, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_split_year":
            layers.append(layer_text("date_split_year-baseline", "Q1                    Q4", [420, 36], [960, 690], start, duration, font=SMALL_FONT, font_size=20, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (28, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_stamp_reveal":
            layers.append(color_layer("date_stamp_reveal-stamp", [430, 6], [960, 630], start, duration, [0.43, 0.84, 0.76, 1]))
        if preset["id"] == "date_era_zoom":
            layers.append(layer_text("date_era_zoom-caption", "FISCAL YEAR", [300, 34], [960, 690], start, duration, font=SMALL_FONT, font_size=18, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (30, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_digit_flip":
            layers.append(layer_text("date_digit_flip-alt", "31 DEC · MIDNIGHT", [460, 36], [960, 690], start, duration, font=SMALL_FONT, font_size=20, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (26, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_marker_drop":
            marker_motion = [track("position_y", [(0, -36), (28, -3), (48, 0), (71, 0)], "out_cubic")]
            layers.append(color_layer("date_marker_drop-stem", [4, 72], [960, 690], start, duration, [0.38, 0.34, 0.29, 1], marker_motion))
            layers.append(color_layer("date_marker_drop-dot", [22, 22], [960, 735], start, duration, [0.43, 0.84, 0.76, 1], marker_motion))
        if preset["id"] == "date_underline_focus":
            layers.append(trim_path_layer_at("date_underline_focus-trim", 680, [960, 600], start, duration))
        if preset["id"] == "date_history_stack":
            for history_index, year in enumerate((1998, 2005, 2012, 2026)):
                row_y = 470 + history_index * 78
                layers.append(layer_text(f"date_history_stack-event-{year}", str(year), [180, 52], [780, row_y], start, duration, font_size=34, fill="#F3EFE7", tracks=[track("opacity", [(0, 0), (18 + history_index * 8, 1), (71, 1)], "out_cubic"), track("position_x", [(0, -18), (25 + history_index * 8, 0), (71, 0)], "out_cubic")]))
                layers.append(layer_text(f"date_history_stack-label-{year}", "PRODUCT LAUNCH", [380, 40], [1070, row_y], start, duration, font=SMALL_FONT, font_size=18, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (22 + history_index * 8, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "date_history_stack":
            continue
        if preset["id"] in {"date_timeline_tick", "date_range_draw", "date_chronology_focus"}:
            layers.append(color_layer(f"{preset['id']}-timeline", [680, 4], [960, 735], start, duration, [0.38, 0.34, 0.29, 1], [track("scale_x", [(0, 0.01), (32, 1), (71, 1)], "out_cubic")]))
            if preset["id"] == "date_range_draw":
                layers.append(color_layer("date_range_draw-range", [680, 16], [960, 735], start, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (34, 1), (71, 1)], "out_cubic")]))
            years = (2010, 2020) if preset["id"] == "date_range_draw" else (1990, 2000, 2010, 2020)
            for tick_index, year in enumerate(years):
                x = 620 + tick_index * (680 / max(1, len(years) - 1))
                layers.append(color_layer(f"{preset['id']}-tick-{year}", [8, 20], [x, 735], start, duration, [0.51, 0.79, 0.91, 1], [track("scale_y", [(0, 0.01), (24 + tick_index * 3, 1), (71, 1)], "out_cubic")]))
                layers.append(layer_text(f"{preset['id']}-year-{year}", str(year), [160, 34], [x, 785], start, duration, font=SMALL_FONT, font_size=18, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (24 + tick_index * 3, 1), (71, 1)], "out_cubic")]))
    return scene_plan("date_v1_gallery_20", layers, len(presets) * duration)


def build_date_gallery_4x5(family: dict) -> dict:
    """Twenty concurrent date alternatives in a five-second 4x5 grid."""
    positions = [(190 + column * 385, 180 + row * 240)
                 for row in range(4) for column in range(5)]
    duration = 72
    date_samples = {
        "date_fade_rise": "MARCH 2024",
        "date_year_count": "2026",
        "date_calendar_flip": "30 SEP 2026",
        "date_segment_stagger": "12 JAN 2026",
        "date_timeline_tick": "Q4 2026",
        "date_range_draw": "2010–2020",
        "date_marker_drop": "2024",
        "date_underline_focus": "SEP 2008",
        "date_history_stack": "1998",
        "date_chronology_focus": "1990–2020",
        "date_page_turn": "30 SEP 2026",
        "date_calendar_drop": "12 OCT 2026",
        "date_month_wipe": "JULY · 2026",
        "date_timeline_sweep": "1990 → 2026",
        "date_marker_pop": "18 MAY 2026",
        "date_split_year": "2024 / 2026",
        "date_bracket_draw": "2001–2025",
        "date_stamp_reveal": "12 DEC 2025",
        "date_era_zoom": "FY 2026",
        "date_digit_flip": "31/12/2026",
    }
    layers = [color_layer("background", [1920, 1080], [960, 540], 0, duration, [0.04, 0.036, 0.031, 1]),
              layer_text("gallery-title", "DATE V1 · 4 × 5 · 20 ALTERNATIVES", [1200, 38], [960, 34], 0, duration, font=SMALL_FONT, font_size=22, fill="#BEB4A6")]
    for preset, (cx, cy) in zip(family["presets"], positions):
        preset_id = preset["id"]
        layers.append(color_layer(f"{preset_id}-tile", [350, 205], [cx, cy], 0, duration, [0.075, 0.068, 0.06, 1]))
        layers.append(layer_text(f"{preset_id}-date", date_samples[preset_id], [320, 70], [cx, cy - 32], 0, duration,
                                 font_size=34, min_font_size=22, fill="#F3EFE7",
                                 tracks=with_motion_tracks(preset["tracks"], duration)))
        layers.append(layer_text(f"{preset_id}-event", "PRODUCT LAUNCH", [250, 24], [cx, cy + 27], 0, duration,
                                 font=SMALL_FONT, font_size=14, fill="#BEB4A6"))
        layers.append(layer_text(f"{preset_id}-preset", preset_id, [330, 28], [cx, cy + 72], 0, duration,
                                 font=SMALL_FONT, font_size=13, fill="#D6CABB"))
        if preset_id in {"date_month_wipe", "date_bracket_draw", "date_stamp_reveal"}:
            accent_track = track("scale_x", [(0, 0.02), (24, 0.56), (48, 1), (71, 1)], "out_cubic")
            layers.append(color_layer(f"{preset_id}-accent", [210, 4], [cx, cy + 7], 0, duration,
                                      [0.43, 0.84, 0.76, 1], [accent_track]))
        if preset_id in {"date_timeline_tick", "date_timeline_sweep", "date_split_year"}:
            layers.append(color_layer(f"{preset_id}-timeline", [250, 3], [cx, cy + 7], 0, duration,
                                      [0.38, 0.34, 0.29, 1], [track("scale_x", [(0, 0.02), (32, 1), (71, 1)], "out_cubic")]))
            for tick_index, offset_x in enumerate((-100, 0, 100)):
                layers.append(color_layer(f"{preset_id}-tick-{tick_index}", [4, 13], [cx + offset_x, cy + 7], 0, duration,
                                          [0.51, 0.79, 0.91, 1], [track("scale_y", [(0, 0.02), (20 + tick_index * 5, 1), (71, 1)], "out_cubic")]))
        if preset_id in {"date_marker_drop", "date_marker_pop"}:
            layers.append(color_layer(f"{preset_id}-marker", [13, 13], [cx, cy + 7], 0, duration,
                                      [0.43, 0.84, 0.76, 1], [track("scale", [(0, 0.2), (22, 1.15), (38, 0.96), (52, 1), (71, 1)], "out_cubic")]))
    return scene_plan("date_v1_gallery_4x5", layers, duration)


def entity_image_tracks(preset: dict, duration: int) -> list[dict]:
    """Apply each preset's subject motion to the portrait/frame, not its caption."""
    preset_id = preset["id"]
    if preset_id == "entity_caption_rise":
        return [track("opacity", [(0, 0), (22, 1), (duration - 1, 1)], "out_cubic"),
                track("scale", [(0, 0.94), (30, 1), (duration - 1, 1)], "out_cubic")]
    if preset_id == "entity_border_then_caption":
        return [track("opacity", [(0, 0), (34, 0), (48, 1), (duration - 1, 1)], "out_cubic"),
                track("scale", [(0, 0.98), (48, 1), (duration - 1, 1)], "out_cubic")]
    return with_motion_tracks(preset["tracks"], duration)


def entity_caption_tracks(preset: dict, duration: int, *, mirror_split: bool = False) -> list[dict]:
    """Keep caption motion independent while preserving each preset's intent."""
    preset_id = preset["id"]
    if preset_id == "entity_caption_rise":
        return [track("opacity", [(0, 0), (30, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 24), (34, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_depth_caption":
        return [track("opacity", [(0, 0), (28, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 12), (32, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_yaw_caption":
        return [track("opacity", [(0, 0), (30, 0), (42, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 16), (42, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_split_side":
        sign = -1 if mirror_split else 1
        return [track("opacity", [(0, 0), (24, 1), (duration - 1, 1)], "out_cubic"),
                track("position_x", [(0, sign * 72), (30, sign * 6), (52, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_border_then_caption":
        return [track("opacity", [(0, 0), (34, 0), (50, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 16), (50, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_name_underline":
        return [track("opacity", [(0, 0), (24, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 8), (28, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_name_pill":
        return [track("opacity", [(0, 0), (22, 1), (duration - 1, 1)], "out_cubic"),
                track("scale", [(0, 0.92), (30, 1), (duration - 1, 1)], "out_cubic")]
    if preset_id == "entity_parallax_caption":
        return [track("opacity", [(0, 0), (22, 1), (duration - 1, 1)], "out_cubic"),
                track("position_y", [(0, 18), (30, 0), (duration - 1, 0)], "out_cubic")]
    if preset_id == "entity_focus_frame":
        return [track("opacity", [(0, 0), (22, 1), (duration - 1, 1)], "out_cubic"),
                track("scale", [(0, 1), (32, 1.045), (54, 1), (duration - 1, 1)], "out_cubic")]
    if preset_id == "entity_glow_focus":
        return with_motion_tracks(preset["tracks"], duration)
    return with_motion_tracks(preset["tracks"], duration)


def add_entity_image_frame(layer: dict, *, image_radius: int = 24, stroke_width: int = 4) -> dict:
    """Add a rounded image mask and exactly aligned padded frame plate."""
    layer["radius"] = image_radius
    layer["style"] = {"background": {
        "color": "#D8E1EA",
        "radius": image_radius + stroke_width,
        "padding": [stroke_width, stroke_width],
    }}
    return layer


def build_entity_gallery(family: dict) -> dict:
    presets, duration = family["presets"], 72
    layers = [color_layer("gallery-background", [1920, 1080], [960, 540], 0, len(presets) * duration, [0.035, 0.047, 0.067, 1])]
        # Row 1 exercises the bottom-caption layout with four cards (short, long
    # and two Latin-Unicode names); row 2 exercises the side-caption layout
    # with two cards (CJK caption right of its image, Arabic caption left of
    # its image — mirrored around the canvas centre). Positions are computed,
    # not hand-tuned, so image spans, caption spans and the gutter between
    # them cannot overlap by construction.
    image_w, image_h, gutter = 300, 215, 12
    caption_w, caption_h = 240, 64

    bottom_names = ENTITY_SAMPLES[:4]
    bottom_total = len(bottom_names) * image_w + (len(bottom_names) - 1) * 140
    bottom_start_x = (1920 - bottom_total) / 2 + image_w / 2
    bottom_y = 280

    side_total = 2 * image_w + 2 * (gutter + caption_w) + 60
    side_start_x = (1920 - side_total) / 2
    side_y = 800

    for index, preset in enumerate(presets):
        start = index * duration
        for card_index, name in enumerate(bottom_names):
            cx = bottom_start_x + card_index * (image_w + 140)
            if preset["id"] == "entity_border_then_caption":
                layers.append(trim_path_layer_at(f"{preset['id']}-frame-draw-{card_index}", image_w + 8, [int(cx), bottom_y - 105], start, duration))
            layers.append(add_entity_image_frame({"id": f"{preset['id']}-portrait-{card_index}", "type": "image", "asset": CANARY_IMAGE,
                           "size": [image_w, image_h], "fit": "cover", "position": renderer_center_position([int(cx), bottom_y - 105]), "start_frame": start,
                           "duration_frames": duration, "enable_3d": any(t["property"] in {"position_z", "rotation_x", "rotation_y"} for t in preset["tracks"]),
                           "animation": {"tracks": shift_tracks(entity_image_tracks(preset, duration), start)},
                           "effects": ([{"type": "glow", "radius": 18, "intensity": 0.2, "color": [0.431, 0.839, 0.765, 1.0]}]
                                       if preset["id"] == "entity_glow_focus" else [])}))
            caption_tracks = entity_caption_tracks(preset, duration)
            caption = caption_text_layer(f"{preset['id']}-name-{card_index}", name, [440, 68], [int(cx), bottom_y + 75], start, duration, tracks=caption_tracks)
            if preset["id"] == "entity_name_pill":
                caption["style"]["background"] = {"color": "#243442", "radius": 28, "padding": [14, 8]}
            if preset["id"] == "entity_name_underline":
                layers.append(trim_path_layer_at(f"{preset['id']}-underline-{card_index}", 300, [int(cx), bottom_y + 120], start, duration))
            layers.append(caption)
        for side_index, name in enumerate(ENTITY_SAMPLES[4:]):
            card_index = 4 + side_index
            if side_index == 0:
                image_x, caption_side = side_start_x + image_w / 2, 1
            else:
                image_x = side_start_x + image_w + (gutter + caption_w) + 60 + image_w + (gutter + caption_w) - image_w / 2
                caption_side = -1
            caption_x = image_x + caption_side * (image_w / 2 + gutter + caption_w / 2)
            if preset["id"] == "entity_border_then_caption":
                layers.append(trim_path_layer_at(f"{preset['id']}-frame-draw-{card_index}", image_w + 8, [int(image_x), side_y - 60], start, duration))
            layers.append(add_entity_image_frame({"id": f"{preset['id']}-portrait-{card_index}", "type": "image", "asset": CANARY_IMAGE,
                           "size": [image_w, image_h], "fit": "cover", "position": renderer_center_position([int(image_x), side_y - 60]), "start_frame": start,
                           "duration_frames": duration, "enable_3d": any(t["property"] in {"position_z", "rotation_x", "rotation_y"} for t in preset["tracks"]),
                           "animation": {"tracks": shift_tracks(entity_image_tracks(preset, duration), start)},
                           "effects": ([{"type": "glow", "radius": 18, "intensity": 0.2, "color": [0.431, 0.839, 0.765, 1.0]}]
                                       if preset["id"] == "entity_glow_focus" else [])}))
            caption = caption_text_layer(f"{preset['id']}-name-{card_index}", name, [caption_w, caption_h], [int(caption_x), side_y - 60], start, duration, tracks=entity_caption_tracks(preset, duration, mirror_split=caption_side < 0))
            if preset["id"] == "entity_name_pill":
                caption["style"]["background"] = {"color": "#243442", "radius": 28, "padding": [14, 8]}
            if preset["id"] == "entity_name_underline":
                layers.append(trim_path_layer_at(f"{preset['id']}-underline-{card_index}", 220, [int(caption_x), side_y - 12], start, duration))
            layers.append(caption)
        layers.append(layer_text(f"{preset['id']}-preset", preset["id"], [700, 32], [960, 1010], start + 5, duration - 5, font=SMALL_FONT, font_size=18, fill="#9FB0C2", tracks=[track("opacity", [(0, 0), (12, 1), (66, 1)], "out_cubic")]))
    return scene_plan("entity_card_v1_gallery_10x6", layers, len(presets) * duration)


def build_two_entity_canary() -> dict:
    duration = SHOWCASE_SEGMENT_FRAMES
    layers = [color_layer("background", [1920, 1080], [960, 540], 0, duration, [0.035, 0.047, 0.067, 1])]
    for index, (name, cx) in enumerate((("PERSON A", 480), ("PERSON B", 1440))):
        layers.append(add_entity_image_frame({"id": f"entity-{index}-image", "type": "image", "asset": CANARY_IMAGE,
                       "size": [500, 590], "fit": "cover", "position": renderer_center_position([cx, 485]), "start_frame": 0,
                       "duration_frames": duration, "animation": {"tracks": [track("opacity", [(0, 0), (50, 1), (149, 1)]), track("scale", [(0, 0.94), (62, 1), (149, 1)])]}}))
        layers.append(layer_text(f"entity-{index}-caption", name, [460, 72], [cx, 835], 0, duration, font_size=34,
                                 tracks=[track("opacity", [(0, 0), (54, 1), (149, 1)]), track("position_y", [(0, 22), (60, 0), (149, 0)])]))
    return scene_plan("entity_card_v1_two_entities_one_scene", layers, duration)


def load_families() -> dict[str, dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    families = {family["id"]: family for family in data["families"]}
    if set(families) != {"metric_v1", "date_v1", "entity_card_v1"}:
        raise ValueError("presentation catalog must define exactly metric_v1, date_v1 and entity_card_v1")
    return families


def build_plans() -> dict[str, dict]:
    families = load_families()
    plans = {
        "metric_v1_gallery_20": build_metric_gallery(families["metric_v1"]),
        "metric_v1_canary_five_values": build_metric_five_value_canary(families["metric_v1"]),
        "metric_v1_gallery_4x5": build_metric_gallery_2x5(families["metric_v1"]),
        "date_v1_gallery_20": build_date_gallery(families["date_v1"]),
        "date_v1_gallery_4x5": build_date_gallery_4x5(families["date_v1"]),
        "entity_card_v1_gallery_10x6": build_entity_gallery(families["entity_card_v1"]),
        "entity_card_v1_two_entities_one_scene": build_two_entity_canary(),
    }
    return {job_id: retime_plan(plan) for job_id, plan in plans.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--assets-root", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--cli", type=Path, help="optional Chronon CLI to validate generated golden plans")
    args = parser.parse_args(argv)
    plans = build_plans()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for job_id, plan in plans.items():
        destination = args.output_dir / f"{job_id}.plan.json"
        destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.cli:
            import subprocess
            subprocess.run([str(args.cli), "validate", "--plan", str(destination), "--assets-root", str(args.assets_root)], check=True)
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
