#!/usr/bin/env python3
"""Author and optionally render six original Chronon editorial benchmark scenes.

These are storyboard compositions, not motion-preset samples. Every timing curve
and scene beat is authored here so the benchmark measures editorial orchestration.
Rendering is deliberately sequential and software-only to keep peak memory bounded.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CHRONON = WORKSPACE / "Chronon3d"
CLI = CHRONON / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
OUT = ROOT / "out/editorial_benchmark_v1"
W, H, FPS, FRAMES = 1280, 720, 24, 360  # 15 seconds; one scene rendered at a time.
PAPER = [0.965, 0.953, 0.918, 1.0]
INK = "#202321"
MUTED = "#686B65"
RED = "#D84A35"
BLUE = "#446B83"
GOLD = "#D9A441"
FONT = "assets/fonts/Instrument-Sans.ttf"
FONT_BOLD = "assets/fonts/Inter-Bold.ttf"


def text(i: str, words: str, x: float, y: float, size: float, color: str = INK,
         *, width: float = 850, start: int = 0, end: int = FRAMES,
         tracks: list | None = None, font: str = FONT_BOLD) -> dict:
    layer = {
        "id": i, "type": "text", "text": words, "size": [width, size * 1.5],
        "position": [x + width / 2, y + size * 0.75], "start_frame": start, "duration_frames": end - start,
        "style": {"font": font, "font_size": size, "fill": color},
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def rect(i: str, x: float, y: float, width: float, height: float,
         fill: list[float], *, radius: float = 0, stroke: dict | None = None,
         start: int = 0, end: int = FRAMES, tracks: list | None = None) -> dict:
    shape = {"type": "rounded_rect" if radius else "rect", "fill": fill}
    if radius:
        shape["radius"] = radius
    if stroke:
        shape["stroke"] = stroke
    layer = {
        "id": i, "type": "shape", "size": [width, height], "position": [x, y],
        "start_frame": start, "duration_frames": end - start, "shape": shape,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def base(job: str, bg: list[float] = PAPER) -> dict:
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": job,
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "output": {"path": f"{job}.mp4", "format": "mp4", "codec": "h264"},
        "layers": [{"id": "paper", "type": "color", "color": bg,
                    "size": [W, H],
                    "start_frame": 0, "duration_frames": FRAMES}],
    }


def label(layers: list, chapter: str, title: str, deck: str) -> None:
    layers.extend([
        text("chapter", chapter.upper(), 82, 50, 15, RED, width=460, font=FONT_BOLD),
        text("headline", title, 82, 112, 48, INK, width=1060),
        text("deck", deck, 84, 170, 21, MUTED, width=1080, font=FONT),
        rect("headline_rule", 82, 211, 64, 4, [0.847, 0.29, 0.207, 1.0]),
    ])


def map_scene() -> dict:
    p = base("editorial_01_map_explainer", [0.93, 0.92, 0.87, 1.0])
    label(p["layers"], "01 / Trade route", "A route can redraw a region", "Container traffic links two coasts — and concentrates risk along the way.")
    pan_x = {"property": "position_x", "easing": "in_out_cubic", "keyframes": [
        {"frame": 0, "value": 0}, {"frame": 220, "value": 0}, {"frame": 359, "value": -250}]}
    pan_y = {"property": "position_y", "easing": "in_out_cubic", "keyframes": [
        {"frame": 0, "value": 0}, {"frame": 220, "value": 0}, {"frame": 359, "value": 90}]}
    # Existing georeferenced documentary basemap; all later graphic overlays are
    # positioned in its image coordinates. Camera push and pan are new authored tracks.
    p["layers"].append({
        "id": "atlantic_basemap", "type": "image", "asset": "assets/maps/italy_usa_basemap.png",
        "size": [1600, 800], "position": [0, -106], "fit": "contain", "enable_3d": True,
        "start_frame": 0, "duration_frames": FRAMES,
        "animation": {"tracks": [
            dict(pan_x), dict(pan_y),
        ]},
    })
    # Reveal the route along a freshly authored cubic using short connected
    # path spans. Opacity staging preserves the shape bounds throughout render.
    def bezier(t: float) -> list[float]:
        u = 1.0 - t
        return [u**3 * 215 + 3*u*u*t * 400 + 3*u*t*t * 720 + t**3 * 945,
                u**3 * 302 + 3*u*u*t * 180 + 3*u*t*t * 400 + t**3 * 275]
    for segment in range(40):
        point = bezier((segment + 0.5) / 40)
        at = 28 + segment * 5
        p["layers"].append(rect(f"trade_route_{segment:02d}", point[0], point[1],
            7, 7, [0.847, 0.29, 0.207, 1], radius=3, start=at,
            tracks=[dict(pan_x), dict(pan_y)]))
    p["layers"].extend([
        rect("origin_pin", 215, 302, 17, 17, [0.847, 0.29, 0.207, 1], radius=8, start=32,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 32, "value": 0}, {"frame": 54, "value": 1.0}]}, dict(pan_x), dict(pan_y)]),
        rect("destination_pin", 945, 275, 17, 17, [0.847, 0.29, 0.207, 1], radius=8, start=150,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 150, "value": 0}, {"frame": 175, "value": 1.0}]}, dict(pan_x), dict(pan_y)]),
        text("origin", "NEW YORK", 252, 322, 16, INK, width=170, start=65, tracks=[dict(pan_x), dict(pan_y)]),
        text("destination", "GENOA", 880, 239, 16, INK, width=130, start=182, tracks=[dict(pan_x), dict(pan_y)]),
        text("map_stat", "2 ports  /  1 corridor", 90, 626, 18, MUTED, width=430, start=220, font=FONT),
    ])
    # Map first; editorial type and geographic marks remain legible above it.
    map_layer = next(layer for layer in p["layers"] if layer["id"] == "atlantic_basemap")
    p["layers"].remove(map_layer)
    p["layers"].insert(1, map_layer)
    return p


def data_scene() -> dict:
    p = base("editorial_02_data_explainer")
    label(p["layers"], "02 / Trade data", "Exports climbed 158%", "An illustrative constant dollar series — with one year doing most of the work.")
    chart_left, baseline = 206, 548
    values = [("2010", 138, [0.67, 0.68, 0.64, 1]), ("2017", 238, [0.67, 0.68, 0.64, 1]), ("2025", 360, [0.847, 0.29, 0.207, 1])]
    for idx, (year, height, color) in enumerate(values):
        x = chart_left + idx * 272
        segments = max(1, round(height / 14))
        segment_height = height / segments
        for segment in range(segments):
            at = 34 + idx * 27 + segment * 4
            p["layers"].append(rect(f"bar_{year}_{segment}", x,
                baseline - (segment + 0.5) * segment_height, 104, segment_height + 0.5, color,
                start=at, tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [
                    {"frame": at, "value": 0}, {"frame": at + 8, "value": 1.0}]}]))
        p["layers"].append(text(f"year_{year}", year, x - 70, 594, 19, MUTED, width=140, font=FONT))
    p["layers"].append(rect("chart_baseline", 128, baseline + 4, 860, 2, [0.22, 0.23, 0.22, 0.4]))
    for idx, (amount, start) in enumerate((("$12B", 32), ("$19B", 102), ("$31B", 173))):
        p["layers"].append(text(f"counter_{idx}", amount, 750, 328, 80, RED, width=390,
            start=start, end=360 if idx == 2 else start + 73))
    p["layers"].extend([
        text("counter_label", "ANNUAL EXPORTS", 759, 452, 16, MUTED, width=300, font=FONT),
        text("growth", "+158%", 911, 492, 35, RED, width=230, start=206),
        text("source", "ILLUSTRATIVE SERIES  /  constant 2025 USD", 84, 678, 13, MUTED, width=690, font=FONT),
    ])
    return p


def photo_scene() -> dict:
    p = base("editorial_03_photo_investigative", [0.92, 0.90, 0.85, 1])
    label(p["layers"], "03 / Field notes", "The port never really sleeps", "Aerial records show activity continuing long after the last scheduled shift.")
    p["layers"].append(rect("photo_mount", 622, 453, 1010, 433, [1, 1, 1, 1], radius=8,
                             stroke={"color": "#333632", "width": 1}))
    p["layers"].append({"id": "port_photo", "type": "image",
        "asset": "assets/editorial/industrial_port_dawn.png", "size": [984, 407],
        "position": [-18, 85], "fit": "cover",
        "start_frame": 0, "duration_frames": FRAMES,
        "animation": {"tracks": [
            {"property": "position_x", "easing": "in_out_sine", "keyframes": [
                {"frame": 0, "value": 0}, {"frame": 359, "value": 12}]},
        ]}})
    p["layers"].extend([
        rect("photo_frame", 622, 445, 984, 407, [0, 0, 0, 0], stroke={"color": "#343631", "width": 1}),
        text("field_note", "02:17  /  EAST QUAY", 126, 350, 14, RED, width=280),
        text("callout", "AIS pings\ncontinue overnight", 146, 426, 24, INK, width=320,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 64, "value": 0}, {"frame": 86, "value": 1}]}]),
        *[rect(f"leader_{n}", 403 + (n + 0.5) * 13, 434, 13.5, 2,
             [0.847, 0.29, 0.207, 1], start=80 + n,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [
                 {"frame": 80 + n, "value": 0}, {"frame": 84 + n, "value": 1}]}]) for n in range(12)],
        text("photo_caption", "Port of Genoa • 06:12 local time", 632, 680, 15, MUTED, width=600, font=FONT),
        text("source", "FIELD IMAGE  /  Editorial reconstruction", 126, 628, 12, MUTED, width=480, font=FONT),
    ])
    return p


def document_scene() -> dict:
    p = base("editorial_04_document_highlight", [0.90, 0.885, 0.84, 1])
    label(p["layers"], "04 / The record", "One sentence changed the story", "The filing’s footnote describes a second shipment window — omitted from the summary.")
    p["layers"].append(rect("page_shadow", 640, 475, 744, 486, [0.79, 0.77, 0.72, 0.65], radius=5))
    p["layers"].append(rect("document", 624, 457, 744, 486, [0.99, 0.982, 0.952, 1], radius=3,
                             stroke={"color": "#A5A197", "width": 1}))
    p["layers"].extend([
        text("doc_header", "SAMPLE EXHIBIT  /  QUARTERLY FILING", 344, 270, 13, MUTED, width=520, font=FONT),
        text("doc_title", "Schedule exceptions", 344, 320, 29, INK, width=540),
    ])
    for n, y, width in ((1, 374, 515), (2, 405, 495), (3, 436, 536), (4, 493, 512), (5, 524, 448), (6, 555, 520)):
        p["layers"].append(rect(f"doc_line_{n}", 344 + width / 2, y, width, 5, [0.40, 0.41, 0.39, 0.47], radius=2))
    for stripe in range(24):
        at = 62 + stripe
        p["layers"].append(rect(f"highlight_{stripe}", 354 + (stripe + 0.5) * 22.5, 464,
            23, 38, [0.92, 0.77, 0.34, 0.38], radius=1, start=at,
            tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [
                {"frame": at, "value": 0}, {"frame": at + 5, "value": 1.0}]}]))
    p["layers"].extend([
        text("highlight_quote", "A second night window remained in effect.", 364, 464, 18, INK, width=520,
             start=96, font=FONT),
        rect("zoom_frame", 624, 464, 540, 62, [0, 0, 0, 0], radius=3,
             stroke={"color": "#D84A35", "width": 2}, start=114,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [
                 {"frame": 114, "value": 0}, {"frame": 141, "value": 1.0}]}]),
        text("source", "EXHIBIT 4B  /  Filed 12 March", 344, 619, 13, MUTED, width=430, font=FONT),
        text("annotation", "The qualifier is in the footnote.", 880, 583, 18, RED, width=350),
    ])
    return p


def timeline_scene() -> dict:
    p = base("editorial_05_timeline")
    label(p["layers"], "05 / Sequence", "Four decisions, one expanding route", "The timeline follows the policy changes that opened the corridor.")
    for segment in range(32):
        at = 18 + segment * 3
        p["layers"].append(rect(f"timeline_rule_{segment}", 155 + segment * 30.3, 458, 31, 3,
            [0.29, 0.31, 0.29, 0.65], start=at,
            tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": at, "value": 0}, {"frame": at + 4, "value": 1}]}]))
    events = [
        ("2010", "Pilot route", "Three weekly sailings", 165),
        ("2014", "Port upgrade", "Night access approved", 455),
        ("2019", "New operator", "Capacity doubles", 745),
        ("2025", "Second window", "24-hour schedule", 1035),
    ]
    for i, (year, title, detail, x) in enumerate(events):
        at = 38 + i * 58
        p["layers"].append(rect(f"event_{i}", x, 458, 17, 17, [0.847, 0.29, 0.207, 1], radius=8, start=at,
            tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": at, "value": 0}, {"frame": at + 12, "value": 1}]}]))
        p["layers"].append(text(f"year_{i}", year, x, 411, 23, RED, width=150, start=at, font=FONT_BOLD))
        p["layers"].append(text(f"title_{i}", title, x, 510, 19, INK, width=220, start=at + 12))
        p["layers"].append(text(f"detail_{i}", detail, x, 547, 14, MUTED, width=230, start=at + 22, font=FONT))
    p["layers"].append(text("follow_label", "FOLLOW THE POLICY, NOT JUST THE SHIPS", 160, 636, 13, MUTED, width=550, font=FONT))
    return p


def kinetic_scene() -> dict:
    p = base("editorial_06_kinetic_typography", [0.96, 0.947, 0.914, 1])
    p["layers"].extend([
        text("eyebrow", "THE FIGURE THAT MATTERS", 118, 154, 15, RED, width=480),
        text("line_1", "Trade routes", 440, 278, 72, INK, width=1020,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 10, "value": 0}, {"frame": 35, "value": 1}]}]),
        text("line_2a", "do not", 318, 382, 72, INK, width=440, start=38,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 38, "value": 0}, {"frame": 56, "value": 1}]}]),
        text("line_2b", "grow evenly.", 670, 382, 72, RED, width=540, start=57,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 57, "value": 0}, {"frame": 77, "value": 1}]}]),
        *[rect(f"underline_{n}", 675 + (n + 0.5) * 24.8, 468, 25, 4,
             [0.847, 0.29, 0.207, 1], start=76 + n,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [
                 {"frame": 76 + n, "value": 0}, {"frame": 81 + n, "value": 1}]}]) for n in range(21)],
        text("stat", "+158%", 887, 520, 60, INK, width=380, start=112,
             tracks=[{"property": "opacity", "easing": "out_cubic", "keyframes": [{"frame": 112, "value": 0}, {"frame": 136, "value": 1.0}]}]),
        text("qualifier", "over fifteen years", 903, 617, 19, MUTED, width=410, start=132, font=FONT),
        text("source", "A measure needs a time span — and its source.", 118, 650, 15, MUTED, width=690, start=162, font=FONT),
    ])
    return p


SCENES = [map_scene, data_scene, photo_scene, document_scene, timeline_scene, kinetic_scene]


def check_scene_contract(plan: dict) -> str | None:
    """Fail closed on timing, scene completeness, and render-memory envelope."""
    if plan["canvas"] != {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                          "duration_frames": FRAMES}:
        return "canvas timing/resolution drifted from the 15 s editorial benchmark"
    layers = plan["layers"]
    if len(layers) > 96:
        return f"layer budget exceeded ({len(layers)} > 96)"
    ids = {layer["id"] for layer in layers}
    required = {
        "editorial_01_map_explainer": {"atlantic_basemap", "trade_route_00", "trade_route_39", "origin_pin", "destination_pin"},
        "editorial_02_data_explainer": {"bar_2010_0", "bar_2017_0", "bar_2025_0", "counter_0", "counter_2", "growth", "source"},
        "editorial_03_photo_investigative": {"port_photo", "photo_mount", "photo_frame", "callout", "source"},
        "editorial_04_document_highlight": {"document", "highlight_0", "highlight_23", "highlight_quote", "zoom_frame", "source"},
        "editorial_05_timeline": {"event_0", "event_1", "event_2", "event_3", "timeline_rule_0", "timeline_rule_31"},
        "editorial_06_kinetic_typography": {"line_1", "line_2a", "line_2b", "underline_0", "underline_20", "stat"},
    }
    missing = sorted(required[plan["job_id"]] - ids)
    if missing:
        return f"missing semantic layers: {', '.join(missing)}"
    if not any(layer.get("animation") or layer.get("start_frame", 0) > 0 for layer in layers):
        return "scene has no authored temporal beats"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-only", action="store_true", help="write deterministic plans only")
    parser.add_argument("--validate-only", action="store_true", help="write and validate plans; do not render")
    parser.add_argument("--render", action="store_true", help="render all six 15s previews sequentially")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--scene", help="render one scene by its job id after writing and validating all plans")
    parser.add_argument("--cli", type=Path, default=CLI, help="Chronon3D CLI used for contract validation/render")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    plans: list[tuple[dict, Path]] = []
    for build in SCENES:
        plan = build()
        contract_problem = check_scene_contract(plan)
        if contract_problem:
            print(f"FAIL contract {plan['job_id']}: {contract_problem}", file=sys.stderr)
            return 1
        plan_path = args.output_dir / f"{plan['job_id']}.plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
        result = subprocess.run([str(args.cli), "validate", "--plan", str(plan_path), "--assets-root", str(CHRONON)],
                                capture_output=True, text=True)
        if result.returncode:
            print(f"FAIL {plan['job_id']}:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return result.returncode
        print(f"PASS validate {plan['job_id']} ({FRAMES} frames, {FRAMES / FPS:g}s)", flush=True)
        plans.append((plan, plan_path))

    manifest = {"suite": "editorial_canary_v1", "resolution": [W, H], "fps": FPS,
                "duration_frames": FRAMES, "duration_seconds": FRAMES / FPS,
                "scenes": [{"id": plan["job_id"], "plan": path.name, "render": f"{plan['job_id']}.mp4"}
                           for plan, path in plans]}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.write_only or args.validate_only or not args.render:
        return 0

    selected = [(p, path) for p, path in plans if args.scene is None or args.scene == p["job_id"]]
    if args.scene and not selected:
        print(f"unknown scene id: {args.scene}", file=sys.stderr)
        return 2
    for plan, path in selected:
        output = args.output_dir / f"{plan['job_id']}.mp4"
        command = [str(args.cli), "render", "--plan", str(path), "--assets-root", str(CHRONON),
                   "--backend", "software", "--hardware", "none", "--profile", "preview",
                   "--encoder-backend", "pipe", "--chunks", "1", "-o", str(output)]
        print(f"RENDER {plan['job_id']} sequentially -> {output.name}", flush=True)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode or not output.exists() or output.stat().st_size == 0:
            print(f"FAIL render {plan['job_id']}:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return result.returncode or 1
        print(f"PASS render {output.name} ({output.stat().st_size} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
