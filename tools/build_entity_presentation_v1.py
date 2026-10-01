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

METRIC_SAMPLES = ("42", "42.5", "-12", "+18.7", "42%", "$3.4B", "€12.5M", "1,250,000")
DATE_SAMPLES = ("2026", "March 2026", "30 September 2026", "Q4 2026", "2010–2020", "1999/2000")
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


def layer_text(layer_id: str, value: str, size: list[int], position: list[int], start: int, duration: int, *, font=FONT, font_size=54, min_font_size=None, fill="#F5F7FA", tracks=None) -> dict:
    style = {"font": font, "font_size": font_size, "fill": fill, "fit_mode": "shrink_only"}
    if min_font_size is not None:
        style.update(min_font_size=min_font_size, max_font_size=font_size)
    motion = tracks or [track("opacity", [(0, 1), (duration - 1, 1)], "linear")]
    layer = {"id": layer_id, "type": "text", "text": value, "size": size, "position": position,
             "start_frame": start, "duration_frames": duration, "style": style,
             "animation": {"tracks": motion}}
    # A layer carrying camera-backed tracks must opt into the 3D render path
    # or the Chronon decoder rejects the plan.
    if any(item["property"] in THREE_D_PROPERTIES for item in motion):
        layer["enable_3d"] = True
    return layer


def color_layer(layer_id: str, size: list[int], position: list[int], start: int, duration: int, color: list[float], tracks=None) -> dict:
    value = {"id": layer_id, "type": "color", "color": color, "size": size, "position": position,
             "start_frame": start, "duration_frames": duration}
    if tracks:
        value["animation"] = {"tracks": tracks}
    return value


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
                      "animation": {"keyframes": [{"frame": 0, "value": [0, 0, 0]},
                                                       {"frame": 48, "value": [0, 1, 0]}]}}}]},
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
        layers.append(layer_text(f"{preset['id']}-eyebrow", "METRIC V1 MOTION GALLERY", [760, 42], [960, 330], start, duration, font=SMALL_FONT, font_size=24, fill="#91A5AD", tracks=[track("opacity", [(0, 0), (18, 1), (71, 1)], "out_cubic")]))
        # Discrete deterministic counter values keep the render-plan text static
        # per layer while implementing a visible count-up in the renderer.
        if index == 0:
            value_layer = layer_text(f"{preset['id']}-value", "{{value}}", [900, 150], [960, 515], start, duration, font_size=88, tracks=with_motion_tracks(preset["tracks"], duration))
            value_layer["text_counter"] = {"token": "{{value}}", "counter": {"from": 0, "to": 0.42, "start_frame": 0, "duration_frames": 48, "format": "percent", "decimals": 0}}
            layers.append(value_layer)
        elif preset["id"] == "metric_multi_stat_focus":
            for stat_index, (label, value) in enumerate((("REVENUE", "$3.4B"), ("USERS", "2.1M"), ("GROWTH", "42%"))):
                cx = 600 + stat_index * 360
                emphasis = [(0, 1), (12 + stat_index * 16, 1.045), (26 + stat_index * 16, 1), (71, 1)]
                layers.append(layer_text(f"{preset['id']}-label-{stat_index}", label, [300, 40], [cx, 410], start, duration, font=SMALL_FONT, font_size=22, fill="#91A5AD", tracks=[track("opacity", [(0, 1), (71, 1)], "linear")]))
                layers.append(layer_text(f"{preset['id']}-value-{stat_index}", value, [320, 100], [cx, 520], start, duration, font_size=58, tracks=[track("opacity", [(0, 1), (71, 1)], "linear"), track("scale", emphasis)]))
        else:
            display = sample if preset["id"] != "metric_before_after" else "$2.1B   →   $3.4B"
            if preset["id"] == "metric_ring_draw":
                display = "72%"
                layers.append(ring_path_layer("metric-ring-draw-arc", 250, [960, 725], start, duration))
            layers.append(layer_text(f"{preset['id']}-value", display, [1060, 150], [960, 515], start, duration, font_size=82, min_font_size=46, tracks=with_motion_tracks(preset["tracks"], duration)))
        layers.append(layer_text(f"{preset['id']}-label", "REVENUE GROWTH", [820, 56], [960, 630], start, duration, font=SMALL_FONT, font_size=27, fill="#A8BAC0", tracks=[track("opacity", [(0, 0), (25, 1), (71, 1)], "out_cubic")]))
        if preset["id"] == "metric_bar_grow":
            layers.extend([color_layer(f"{preset['id']}-bar-track", [560, 9], [960, 710], start, duration, [0.20, 0.26, 0.30, 1]), color_layer(f"{preset['id']}-bar-fill", [403, 9], [881, 710], start, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (35, 0.72), (71, 1)], "out_cubic")])])
        if preset["id"] == "metric_delta_reveal":
            layers.append(layer_text("metric-delta-badge", "+12.8%", [220, 60], [1420, 450], start + 20, duration - 20, font_size=30, fill="#6ED6C3", tracks=[track("opacity", [(0, 0), (12, 1), (51, 1)], "out_cubic")]))
        if preset["id"] == "metric_before_after":
            layers.append(layer_text("metric-before-value", "$2.1B", [360, 100], [660, 540], start, duration, font_size=52, fill="#91A5AD", tracks=[track("opacity", [(0, 1), (71, 0.65)], "out_cubic"), track("scale", [(0, 1), (40, 0.92), (71, 0.92)], "out_cubic")]))
            layers.append(layer_text("metric-before-after-arrow", "→", [100, 80], [960, 540], start, duration, font_size=48, fill="#6ED6C3", tracks=[track("opacity", [(0, 0), (20, 1), (71, 1)], "out_cubic")]))
            layers.append(layer_text("metric-after-value", "$3.4B", [360, 100], [1260, 540], start, duration, font_size=58, tracks=[track("opacity", [(0, 0), (22, 1), (71, 1)], "out_cubic"), track("scale", [(0, 0.94), (30, 1), (71, 1)], "out_cubic")]))
    return scene_plan("metric_v1_gallery_10", layers, len(presets) * duration)


def build_date_gallery(family: dict) -> dict:
    presets, duration = family["presets"], 72
    layers = [color_layer("gallery-background", [1920, 1080], [960, 540], 0, len(presets) * duration, [0.04, 0.036, 0.031, 1])]
    for index, preset in enumerate(presets):
        start = index * duration
        sample = DATE_SAMPLES[index % len(DATE_SAMPLES)]
        if preset["id"] == "date_year_count":
            sample = "2026"
        elif preset["id"] == "date_range_draw":
            sample = "2010–2020"
        layers.append(layer_text(f"{preset['id']}-eyebrow", "DATE MOTION GALLERY", [900, 42], [960, 330], start, duration, font=SMALL_FONT, font_size=22, fill="#B4A99B", tracks=[track("opacity", [(0, 0), (18, 1), (71, 1)], "out_cubic")]))
        date_tracks = with_motion_tracks(preset["tracks"], duration)
        date_layer = layer_text(f"{preset['id']}-date", sample.upper(), [1040, 132], [960, 505], start, duration, font_size=66, min_font_size=40, fill="#F3EFE7", tracks=date_tracks)
        if preset["id"] == "date_year_count":
            date_layer["text_counter"] = {"token": "{{value}}", "counter": {"from": 1990, "to": 2026, "start_frame": 0, "duration_frames": 34, "format": "plain", "decimals": 0}}
            date_layer["text"] = "{{value}}"
        elif preset["id"] == "date_range_draw":
            date_layer["text_counter"] = {"token": "{{value}}", "counter": {"from": 2010, "to": 2020, "start_frame": 0, "duration_frames": 34, "format": "plain", "decimals": 0}}
            date_layer["text"] = "{{value}}"
            # The renderer's native Trim Paths operator owns the line draw;
            # labels mark the actual start/end year of this range.
            layers.append(trim_path_layer("date_range_draw-trim", 680, [960, 735], start, duration))
            for year, x in ((2010, 620), (2020, 1300)):
                layers.append(layer_text(f"date_range_draw-endpoint-{year}", str(year), [160, 34], [x, 785], start, duration, font=SMALL_FONT, font_size=18, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (34, 1), (71, 1)], "out_cubic")]))
        layers.append(date_layer)
        layers.append(layer_text(f"{preset['id']}-event", "PRODUCT LAUNCH", [700, 48], [960, 615], start, duration, font=SMALL_FONT, font_size=25, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (25, 1), (71, 1)], "out_cubic")]))
        if preset["id"] in {"date_timeline_tick", "date_range_draw", "date_chronology_focus", "date_history_stack"}:
            layers.append(color_layer(f"{preset['id']}-timeline", [680, 4], [960, 735], start, duration, [0.38, 0.34, 0.29, 1], [track("scale_x", [(0, 0.01), (32, 1), (71, 1)], "out_cubic")]))
            if preset["id"] == "date_range_draw":
                layers.append(color_layer("date_range_draw-range", [680, 16], [960, 735], start, duration, [0.43, 0.84, 0.76, 1], [track("scale_x", [(0, 0.01), (34, 1), (71, 1)], "out_cubic")]))
            years = (2010, 2020) if preset["id"] == "date_range_draw" else (1990, 2000, 2010, 2020)
            for tick_index, year in enumerate(years):
                x = 620 + tick_index * (680 / max(1, len(years) - 1))
                layers.append(color_layer(f"{preset['id']}-tick-{year}", [8, 20], [x, 735], start, duration, [0.51, 0.79, 0.91, 1], [track("scale_y", [(0, 0.01), (24 + tick_index * 3, 1), (71, 1)], "out_cubic")]))
                layers.append(layer_text(f"{preset['id']}-year-{year}", str(year), [160, 34], [x, 785], start, duration, font=SMALL_FONT, font_size=18, fill="#BEB4A6", tracks=[track("opacity", [(0, 0), (24 + tick_index * 3, 1), (71, 1)], "out_cubic")]))
    return scene_plan("date_v1_gallery_10", layers, len(presets) * duration)


def add_entity_image_frame(layer: dict, *, image_radius: int = 24, stroke_width: int = 4) -> dict:
    """Add a rounded image mask and an exactly aligned padded frame plate."""
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
            layers.append(add_entity_image_frame({"id": f"{preset['id']}-portrait-{card_index}", "type": "image", "asset": CANARY_IMAGE,
                           "size": [image_w, image_h], "fit": "cover", "position": [int(cx), bottom_y - 105], "start_frame": start,
                           "duration_frames": duration, "enable_3d": any(t["property"] in {"position_z", "rotation_x", "rotation_y"} for t in preset["tracks"]),
                           "animation": {"tracks": with_motion_tracks(preset["tracks"], duration)}}))
            caption_tracks = [track("opacity", [(0, 0), (22 + (card_index % 3) * 3, 1), (71, 1)], "out_cubic"),
                             track("position_y", [(0, 18), (28 + (card_index % 3) * 3, 0), (71, 0)], "out_cubic")]
            if preset["id"] in {"entity_depth_caption", "entity_yaw_caption", "entity_split_side", "entity_name_pill"}:
                caption_tracks = with_motion_tracks(preset["tracks"], duration)
            layers.append(caption_text_layer(f"{preset['id']}-name-{card_index}", name, [440, 68], [int(cx), bottom_y + 75], start, duration, tracks=caption_tracks))
        for side_index, name in enumerate(ENTITY_SAMPLES[4:]):
            card_index = 4 + side_index
            if side_index == 0:
                image_x, caption_side = side_start_x + image_w / 2, 1
            else:
                image_x = side_start_x + image_w + (gutter + caption_w) + 60 + image_w + (gutter + caption_w) - image_w / 2
                caption_side = -1
            caption_x = image_x + caption_side * (image_w / 2 + gutter + caption_w / 2)
            layers.append(add_entity_image_frame({"id": f"{preset['id']}-portrait-{card_index}", "type": "image", "asset": CANARY_IMAGE,
                           "size": [image_w, image_h], "fit": "cover", "position": [int(image_x), side_y - 60], "start_frame": start,
                           "duration_frames": duration, "enable_3d": any(t["property"] in {"position_z", "rotation_x", "rotation_y"} for t in preset["tracks"]),
                           "animation": {"tracks": with_motion_tracks(preset["tracks"], duration)}}))
            layers.append(caption_text_layer(f"{preset['id']}-name-{card_index}", name, [caption_w, caption_h], [int(caption_x), side_y - 60], start, duration, tracks=caption_tracks))
        layers.append(layer_text(f"{preset['id']}-preset", preset["id"], [700, 32], [960, 1010], start + 5, duration - 5, font=SMALL_FONT, font_size=18, fill="#9FB0C2", tracks=[track("opacity", [(0, 0), (12, 1), (66, 1)], "out_cubic")]))
    return scene_plan("entity_card_v1_gallery_10x6", layers, len(presets) * duration)


def build_two_entity_canary() -> dict:
    duration = 120
    layers = [color_layer("background", [1920, 1080], [960, 540], 0, duration, [0.035, 0.047, 0.067, 1])]
    for index, (name, cx) in enumerate((("PERSON A", 480), ("PERSON B", 1440))):
        layers.append(add_entity_image_frame({"id": f"entity-{index}-image", "type": "image", "asset": CANARY_IMAGE,
                       "size": [500, 590], "fit": "cover", "position": [cx, 485], "start_frame": 0,
                       "duration_frames": duration, "animation": {"tracks": [track("opacity", [(0, 0), (24, 1), (119, 1)]), track("scale", [(0, 0.94), (30, 1), (119, 1)])]}}))
        layers.append(layer_text(f"entity-{index}-caption", name, [460, 72], [cx, 835], 0, duration, font_size=34,
                                 tracks=[track("opacity", [(0, 0), (28, 1), (119, 1)]), track("position_y", [(0, 22), (32, 0), (119, 0)])]))
    return scene_plan("entity_card_v1_two_entities_one_scene", layers, duration)


def load_families() -> dict[str, dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    families = {family["id"]: family for family in data["families"]}
    if set(families) != {"metric_v1", "date_v1", "entity_card_v1"}:
        raise ValueError("presentation catalog must define exactly metric_v1, date_v1 and entity_card_v1")
    return families


def build_plans() -> dict[str, dict]:
    families = load_families()
    return {
        "metric_v1_gallery_10": build_metric_gallery(families["metric_v1"]),
        "date_v1_gallery_10": build_date_gallery(families["date_v1"]),
        "entity_card_v1_gallery_10x6": build_entity_gallery(families["entity_card_v1"]),
        "entity_card_v1_two_entities_one_scene": build_two_entity_canary(),
    }


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
