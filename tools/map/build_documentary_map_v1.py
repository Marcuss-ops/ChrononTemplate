#!/usr/bin/env python3
"""Author and render reusable native Chronon documentary map scenes.

The map base is Natural Earth's checked-in relief plate. Country borders,
route strokes, arrowheads, pins, labels, and their motion are native Chronon
RenderPlan layers. Geographic coordinates use the shared plate projection
(-100..50 longitude, 8..72 latitude), so every overlay follows the same map
camera transform.

Usage:
  python3 ChrononTemplate/tools/map/build_documentary_map_v1.py --plans
  python3 ChrononTemplate/tools/map/build_documentary_map_v1.py --render
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent
WORKSPACE = TEMPLATE.parent
CHRONON = WORKSPACE / "Chronon3d"
CATALOG = TEMPLATE / "catalog"
OUT = TEMPLATE / "out/documentary_map_v1"
PLANS = TEMPLATE / "golden_plans/documentary_map_v1"
CLI_CANDIDATES = [
    CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    CHRONON / "build/chronon/linux-release-validation/apps/chronon3d_cli/chronon3d_cli",
]
CLI = Path(os.environ.get("CHRONON_CLI", str(
    next((p for p in CLI_CANDIDATES if p.is_file()), CLI_CANDIDATES[-1]))))
W, H, FPS, FRAMES = 1920, 1080, 30, 150
MAP_W, MAP_H = 1480, 630
MAP_X, MAP_Y = (W - MAP_W) / 2, (H - MAP_H) / 2
EXTENT = (-100.0, 50.0, 8.0, 72.0)  # west, east, south, north
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"
PAPER = "#EEE9DB"
INK = "#142332"
MUTED = "#64717A"
AMBER = "#F3B85B"
CYAN = "#71D8D0"


def rgba(value: str, alpha: float = 1.0) -> list[float]:
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def track(prop: str, keys: list[tuple[int, Any]], easing: str = "in_out_cubic") -> dict:
    unique = {int(frame): value for frame, value in keys}
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": unique[frame]}
                          for frame in sorted(unique)]}


def geo_xy(lon: float, lat: float) -> tuple[float, float]:
    west, east, south, north = EXTENT
    return (MAP_X + (lon - west) / (east - west) * MAP_W,
            MAP_Y + (north - lat) / (north - south) * MAP_H)


def layer_map_motion(target: tuple[float, float] | None = None,
                     end_zoom: float = 1.0, end_frame: int = 78) -> dict:
    """Shared editorial camera move; all geo layers receive identical tracks."""
    if target is None:
        target = (W / 2, H / 2)
    fx, fy = target
    keys = [(0, 1.0), (max(1, end_frame), end_zoom), (FRAMES - 1, end_zoom)]
    x_end = end_zoom * (W / 2 - fx)
    y_end = end_zoom * (H / 2 - fy)
    xkeys = [(0, 0.0), (max(1, end_frame), round(x_end, 4)),
             (FRAMES - 1, round(x_end, 4))]
    ykeys = [(0, 0.0), (max(1, end_frame), round(y_end, 4)),
             (FRAMES - 1, round(y_end, 4))]
    return {"tracks": [track("scale", keys), track("position_x", xkeys),
                       track("position_y", ykeys)]}


def apply_motion(layer: dict, motion: dict, opacity: list[tuple[int, float]] | None = None) -> dict:
    anim = {"tracks": list(motion["tracks"])}
    if opacity is not None:
        anim["tracks"].append(track("opacity", opacity))
    layer["animation"] = anim
    return layer


def map_base(motion: dict, frame_caption: str) -> list[dict]:
    return [
        {"id": "night-field", "type": "color", "color": [0.025, 0.043, 0.057, 1],
         "size": [W, H], "screen_space": True, "start_frame": 0, "duration_frames": FRAMES},
        apply_motion({"id": "relief-map", "type": "image", "asset": "ChrononTemplate/assets/documentary_map_v1/map_plate.png",
                      # Image layers use centered world coordinates directly;
                      # the resolver adds the canvas center for unpinned 2D.
                      "size": [MAP_W, MAP_H], "position": [0, 0], "fit": "contain",
                      "start_frame": 0, "duration_frames": FRAMES}, motion),
        {"id": "top-rule", "type": "shape", "size": [78, 2], "position": [W / 2, 112],
         "start_frame": 0, "duration_frames": FRAMES,
         "shape": {"type": "rect", "fill": [0.953, 0.722, 0.357, 1.0]}},
        {"id": "section-kicker", "type": "text", "text": "FIELD NOTES   /   GEOGRAPHIC EXPLAINER",
         "size": [1000, 30], "position": [W / 2, 79], "start_frame": 0,
         "duration_frames": FRAMES,
         "style": {"font": FONT, "font_size": 17, "fill": CYAN}},
        {"id": "scene-caption", "type": "text", "text": frame_caption,
         "size": [1450, 42], "position": [W / 2, 985], "start_frame": 0,
         "duration_frames": FRAMES,
         "style": {"font": FONT, "font_size": 20, "fill": PAPER}},
    ]


def layer_pos(layer_id: str, point: tuple[float, float], text: str,
              color: str, start: int, size: int = 25) -> dict:
    x, y = point
    return {"id": layer_id, "type": "text", "text": text,
            "size": [360, size * 2.3], "position": [x, y - 36],
            "start_frame": 0, "duration_frames": FRAMES,
            "style": {"font": FONT, "font_size": size, "min_font_size": size,
                      "max_font_size": size, "fit_mode": "shrink_only", "fill": color,
                      "stroke": {"color": "#10202B", "width": 2}},
            "animation": {"tracks": [track("opacity", [(0, 0), (start, 0),
                                                               (start + 12, 1),
                                                               (FRAMES - 1, 1)])]}}


def attach_geo(layer: dict, point: tuple[float, float], zoom: float,
               end_frame: int, focus: tuple[float, float] = (W / 2, H / 2),
               keep_size: bool = True, start_frame: int = 0,
               y_up: bool = False) -> dict:
    """Move a geographic anchor with the same camera transform as the plate."""
    x, y = point
    layer_x, layer_y = layer.get("position", point)
    if start_frame >= end_frame:
        start_zoom, start_target = zoom, focus
    else:
        p = max(0.0, min(1.0, start_frame / max(1, end_frame)))
        p = p * p * (3.0 - 2.0 * p)
        start_zoom = 1.0 + (zoom - 1.0) * p
        start_target = (W / 2 + (focus[0] - W / 2) * p,
                        H / 2 + (focus[1] - H / 2) * p)
    local_end = max(0, end_frame - start_frame)
    duration = max(1, FRAMES - start_frame)
    x_start = W / 2 + start_zoom * (layer_x - start_target[0]) - layer_x
    y_start = H / 2 + start_zoom * (layer_y - start_target[1]) - layer_y
    x_final = W / 2 + zoom * (layer_x - focus[0]) - layer_x
    y_final = H / 2 + zoom * (layer_y - focus[1]) - layer_y
    if y_up:
        y_start = -(H / 2 + start_zoom * (y - start_target[1]) - y)
        y_final = -(H / 2 + zoom * (y - focus[1]) - y)
    x_offset = [(0, round(x_start, 4)), (local_end, round(x_final, 4)),
                (duration - 1, round(x_final, 4))]
    y_offset = [(0, round(y_start, 4)), (local_end, round(y_final, 4)),
                (duration - 1, round(y_final, 4))]
    anim = layer.setdefault("animation", {"tracks": []})
    anim["tracks"].extend([track("position_x", x_offset), track("position_y", y_offset)])
    scale_from = 1.0 / start_zoom if keep_size else start_zoom
    scale_to = 1.0 / zoom if keep_size else zoom
    anim["tracks"].append(track("scale", [(0, scale_from), (local_end, scale_to),
                                           (duration - 1, scale_to)]))
    return layer


def douglas_peucker(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) > 3 and points[0] == points[-1]:
        ring = points[:-1]
        pivot = max(range(1, len(ring)),
                    key=lambda i: (ring[i][0] - ring[0][0]) ** 2 + (ring[i][1] - ring[0][1]) ** 2)
        first = douglas_peucker(ring[:pivot + 1], tolerance)
        second = douglas_peucker(ring[pivot:] + [ring[0]], tolerance)
        return first[:-1] + second
    if len(points) <= 2:
        return points
    x1, y1 = points[0]
    x2, y2 = points[-1]
    dx, dy = x2 - x1, y2 - y1
    denom = math.hypot(dx, dy) or 1.0
    best_i, best_d = 0, -1.0
    for i, (x, y) in enumerate(points[1:-1], 1):
        distance = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / denom
        if distance > best_d:
            best_i, best_d = i, distance
    if best_d <= tolerance:
        return [points[0], points[-1]]
    left = douglas_peucker(points[:best_i + 1], tolerance)
    right = douglas_peucker(points[best_i:], tolerance)
    return left[:-1] + right


def resample_open(points: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    if len(points) <= 2 or count <= 2:
        return points
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    total = lengths[-1]
    result = []
    segment = 0
    for i in range(count):
        target = total * i / (count - 1)
        while segment < len(lengths) - 2 and lengths[segment + 1] < target:
            segment += 1
        span = lengths[segment + 1] - lengths[segment]
        t = 0.0 if span <= 1.0e-9 else (target - lengths[segment]) / span
        a, b = points[segment], points[segment + 1]
        result.append((a[0] + (b[0] - a[0]) * t,
                       a[1] + (b[1] - a[1]) * t))
    return result


def country_paths(country: str = "France") -> list[list[tuple[float, float]]]:
    data = json.loads((CATALOG / "ne_50m_admin_0_countries.geojson").read_text())
    feature = next(f for f in data["features"]
                   if f["properties"].get("ADMIN") == country)
    geom = feature["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    result = []
    for polygon in polygons:
        ring = polygon[0]
        if not ring:
            continue
        mean_lon = sum(p[0] for p in ring) / len(ring)
        mean_lat = sum(p[1] for p in ring) / len(ring)
        # This scene focuses on metropolitan France and Corsica.
        if not (-6.0 <= mean_lon <= 10.0 and 41.0 <= mean_lat <= 52.0):
            continue
        projected = [geo_xy(float(lon), float(lat)) for lon, lat in ring
                     if EXTENT[0] <= lon <= EXTENT[1] and EXTENT[2] <= lat <= EXTENT[3]]
        simplified = douglas_peucker(projected, 2.0)
        if len(simplified) > 3:
            result.append(simplified)
    return result


def segment_layer(layer_id: str, a: tuple[float, float], b: tuple[float, float],
                  color: str, thickness: float, reveal: int,
                  camera_focus: tuple[float, float] = (W / 2, H / 2),
                  zoom: float = 1.0, camera_end: int = 1,
                  alpha: float = 1.0) -> dict:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    # Rounded rectangles end in half-circles; extend through each join so the
    # sampled native segments form a continuous line at every scale.
    shape_size = max(thickness, length + thickness * 2.0)
    layer = {
        "id": layer_id, "type": "shape", "shape": {
            "type": "rounded_rect", "fill": rgba(color, alpha),
            "radius": thickness / 2.0},
        "size": [round(shape_size, 3), thickness],
        "position": [round(cx, 3), round(H - cy, 3)],
        "enable_3d": True,
        # The map lies in XY, so planar segment direction is a Z rotation.
        "rotation": [0.0, 0.0, math.degrees(math.atan2(-dy, dx))],
        "start_frame": reveal, "duration_frames": max(1, FRAMES - reveal),
        "animation": {"tracks": [track("opacity", [
            (0, 0.0), (2, 1.0), (max(2, FRAMES - reveal - 1), 1.0)], "out_cubic")]},
    }
    attach_geo(layer, (cx, cy), zoom, camera_end, camera_focus,
               keep_size=False, start_frame=reveal, y_up=True)
    return layer


def append_boundary_segments(layers: list[dict], rings: list[list[tuple[float, float]]],
                             prefix: str, reveal_start: int, reveal_span: int,
                             motion_focus: tuple[float, float], zoom: float,
                             camera_end: int) -> None:
    segments = []
    for ring in rings:
        count = max(8, min(42, round(sum(math.dist(a, b) for a, b in
                                        zip(ring, ring[1:] + ring[:1])) / 28)))
        samples = resample_open(ring + [ring[0]], count + 1)
        segments.extend(zip(samples, samples[1:]))
    total = max(1, len(segments))
    for index, (a, b) in enumerate(segments):
        reveal = reveal_start + round(reveal_span * index / total)
        layers.append(segment_layer(f"{prefix}-edge-{index:02d}", a, b,
                                    "#A96D32", 4.5, reveal, motion_focus,
                                    zoom, camera_end, 1.0))


def country_focus_plan() -> dict:
    france = country_paths()
    focus = geo_xy(2.2, 46.4)
    motion = layer_map_motion(focus, 2.05, 76)
    layers = map_base(motion, "01   /   A country takes shape through its borders.")
    append_boundary_segments(layers, france, "france-border", 58, 44,
                             focus, 2.05, 76)
    p = geo_xy(2.3522, 48.8566)
    layers.append(attach_geo({"id": "paris-marker", "type": "shape", "size": [22, 22],
                   "position": p, "start_frame": 0, "duration_frames": FRAMES,
                   "shape": {"type": "ellipse", "fill": rgba(AMBER),
                             "stroke": {"color": "#FFF0CB", "width": 3}},
                   "animation": {"tracks": [track("opacity", [(0, 0), (92, 0), (105, 1), (149, 1)])]}},
                   p, 2.05, 78, focus))
    layers.append(attach_geo(layer_pos("paris-label", p, "PARIS", PAPER, 101, 24),
                             p, 2.05, 78, focus))
    return base_plan("documentary_map_country_focus_v1", layers)


def route_plan() -> dict:
    motion = layer_map_motion(None, 1.0, 1)
    layers = map_base(motion, "02   /   A line turns distance into a story.")
    start, end = geo_xy(-74.0060, 40.7128), geo_xy(-0.1276, 51.5072)
    control = ((start[0] + end[0]) / 2, min(start[1], end[1]) - 105)
    route_points = []
    for index in range(45):
        t = index / 44
        u = 1 - t
        route_points.append((u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                             u * u * start[1] + 2 * u * t * control[1] + t * t * end[1]))
    route_segments = list(zip(route_points, route_points[1:]))
    for index, (a, b) in enumerate(route_segments):
        reveal = 40 + round(48 * index / len(route_segments))
        layers.append(segment_layer(f"route-core-{index:02d}", a, b,
                                    "#197F7B", 5.0, reveal))
    end_angle = math.atan2(end[1] - control[1], end[0] - control[0])
    for side in (-1, 1):
        a = (end[0] - 24 * math.cos(end_angle + math.pi + side * 0.55),
             end[1] - 24 * math.sin(end_angle + math.pi + side * 0.55))
        layers.append(segment_layer(f"route-arrow-arm-{side}", a, end,
                                    CYAN, 3.0, 87))
    for id_, p, name, color, began in [
        ("new-york", start, "NEW YORK", PAPER, 28),
        ("london", end, "LONDON", CYAN, 91),
    ]:
        layers.append({"id": f"{id_}-pin", "type": "shape", "size": [14, 14],
                       "position": p, "start_frame": 0, "duration_frames": FRAMES,
                       "shape": {"type": "ellipse", "fill": rgba(color),
                                 "stroke": {"color": "#142332", "width": 2}},
                       "animation": {"tracks": [track("opacity", [(0, 0), (began, 0), (began + 8, 1), (149, 1)])]}})
        layers.append(layer_pos(f"{id_}-label", p, name, color, began, 22))
    return base_plan("documentary_map_route_draw_v1", layers)


def camera_shot_plan() -> dict:
    focus = geo_xy(2.2, 46.4)
    motion = layer_map_motion(focus, 2.05, 78)
    layers = map_base(motion, "03   /   Establishing view → country → capital.")
    append_boundary_segments(layers, country_paths(), "france-outline", 62, 36,
                             focus, 2.05, 78)
    for layer_id, coords, label, when in [
        ("france", (2.2, 46.4), "FRANCE", 39),
        ("paris", (2.3522, 48.8566), "PARIS", 99),
    ]:
        point = geo_xy(*coords)
        # A geographic label follows map pan/zoom and counter-scales to remain legible.
        label_layer = layer_pos(layer_id + "-label", point, label, PAPER, when, 22)
        layers.append(attach_geo(label_layer, point, 2.05, 78, focus))
    return base_plan("documentary_map_camera_shots_v1", layers)


def base_plan(job: str, layers: list[dict]) -> dict:
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job,
            "canvas": {"width": W, "height": H, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": f"{job}.mp4", "format": "mp4", "codec": "h264"}}


def prepare_map_plate() -> Path:
    target = TEMPLATE / "assets/documentary_map_v1/map_plate.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    source = Image.open(CATALOG / "maps/natural_earth_hypso_relief_water.jpg").convert("RGB")
    # Slightly lower saturation and warm the plate to make the luminous linework read.
    source = ImageEnhance.Color(source).enhance(0.74)
    tint = Image.new("RGB", source.size, (230, 221, 197))
    source = Image.blend(source, tint, 0.11)
    source.save(target, optimize=True)
    return target


def build_plans() -> list[Path]:
    prepare_map_plate()
    PLANS.mkdir(parents=True, exist_ok=True)
    plans = [country_focus_plan(), route_plan(), camera_shot_plan()]
    paths = []
    for plan in plans:
        path = PLANS / f"{plan['job_id']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        paths.append(path)
    return paths


def render() -> list[Path]:
    if not CLI.is_file():
        raise FileNotFoundError(f"Chronon CLI not found: {CLI}")
    paths = build_plans()
    OUT.mkdir(parents=True, exist_ok=True)
    backend = os.environ.get("CHRONON_MAP_BACKEND", "vulkan").strip().lower()
    if backend not in {"vulkan", "software"}:
        raise ValueError("CHRONON_MAP_BACKEND must be 'vulkan' or 'software'")
    results = []
    for plan in paths:
        output = OUT / (plan.stem.removesuffix(".plan") + ".mp4")
        output.unlink(missing_ok=True)
        output.with_name(output.stem + ".partial" + output.suffix).unlink(missing_ok=True)
        cmd = [str(CLI), "render", "--plan", str(plan), "--assets-root", str(WORKSPACE),
               "--backend", backend,
               "--hardware", "none", "--fps", "30", "--crf", "18", "--preset", "veryfast",
               "--log-level", "error", "--output", str(output)]
        print("[documentary-map]", " ".join(cmd), flush=True)
        try:
            subprocess.run(cmd, cwd=WORKSPACE, check=True)
        except subprocess.CalledProcessError:
            if backend != "vulkan":
                raise
            output.with_name(output.stem + ".partial" + output.suffix).unlink(missing_ok=True)
            fallback_cmd = cmd.copy()
            fallback_cmd[fallback_cmd.index("vulkan")] = "software"
            print("[documentary-map] Vulkan render failed; retrying this example with software", flush=True)
            subprocess.run(fallback_cmd, cwd=WORKSPACE, check=True)
        results.append(output)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plans", action="store_true", help="write the reusable RenderPlan examples")
    group.add_argument("--render", action="store_true", help="write plans and render all 5-second examples")
    args = parser.parse_args()
    if args.render:
        for path in render():
            print(path)
    else:
        for path in build_plans():
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
