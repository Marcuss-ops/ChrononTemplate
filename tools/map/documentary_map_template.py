#!/usr/bin/env python3
"""Data-driven documentary map template.

A JSON spec describes one scene: a highlighted country, a city marker, a
connector line to a black label box, and a large editorial line. The scene is
built from the same native RenderPlan primitives and shared camera transform as
build_documentary_map_v1.py, so swapping the spec regenerates a new map.

Spec format (see specs/italy_rome_1_milione.json):
  {
    "job_id": str,                     # output name, [a-z0-9_]+
    "highlight_country": str,          # Natural Earth ADMIN name, e.g. "Italy"
    "bbox": [west, east, south, north],# lon/lat window that keeps the country's parts
    "camera": {"zoom": float, "lon": float, "lat": float},
    "city": {"name": str, "lon": float, "lat": float},
    "label": str,                      # text inside the black box
    "editorial_text": str,             # large text, e.g. "1 milione"
    "caption": str                     # bottom caption
  }

Usage:
  python3 ChrononTemplate/tools/map/documentary_map_template.py --spec SPEC.json
  python3 ChrononTemplate/tools/map/documentary_map_template.py --spec SPEC.json --render
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_documentary_map_v1 as base  # noqa: E402  (shared primitives)

from build_documentary_map_v1 import (  # noqa: E402
    AMBER, CATALOG, CYAN, EXTENT, FONT, FRAMES, INK, PAPER,
    append_boundary_segments, attach_geo, base_plan, douglas_peucker,
    geo_xy, layer_map_motion, map_base, prepare_map_plate,
    rgba, segment_layer, track,
)

PLANS = HERE.parent.parent / "out" / "documentary_map_template_v1"
REQUIRED = ("job_id", "highlight_country", "bbox", "camera", "city",
            "label", "editorial_text", "caption")


class SpecError(ValueError):
    pass


def _num(spec: dict, path: str, lo: float | None = None, hi: float | None = None) -> float:
    keys = path.split(".")
    value: Any = spec
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise SpecError(f"missing field: {path}")
        value = value[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpecError(f"{path} must be a number")
    value = float(value)
    if lo is not None and value < lo or hi is not None and value > hi:
        raise SpecError(f"{path}={value} outside [{lo}, {hi}]")
    return value


def validate_spec(spec: dict) -> dict:
    """Fail closed on malformed specs; returns the normalized spec."""
    if not isinstance(spec, dict):
        raise SpecError("spec must be a JSON object")
    for key in REQUIRED:
        if key not in spec:
            raise SpecError(f"missing field: {key}")
    if not re.fullmatch(r"[a-z0-9_]+", str(spec["job_id"])):
        raise SpecError("job_id must match [a-z0-9_]+")
    country = spec["highlight_country"]
    if not isinstance(country, str) or not country.strip():
        raise SpecError("highlight_country must be a non-empty string")
    bbox = spec["bbox"]
    if not (isinstance(bbox, list) and len(bbox) == 4
            and all(isinstance(v, (int, float)) for v in bbox)):
        raise SpecError("bbox must be [west, east, south, north]")
    west, east, south, north = map(float, bbox)
    if not (EXTENT[0] <= west < east <= EXTENT[1] and EXTENT[2] <= south < north <= EXTENT[3]):
        raise SpecError(f"bbox {bbox} must lie inside the map extent {list(EXTENT)}")
    _num(spec, "camera.zoom", 1.0, 6.0)
    _num(spec, "camera.lon", EXTENT[0], EXTENT[1])
    _num(spec, "camera.lat", EXTENT[2], EXTENT[3])
    _num(spec, "city.lon", EXTENT[0], EXTENT[1])
    _num(spec, "city.lat", EXTENT[2], EXTENT[3])
    if not isinstance(spec["city"].get("name"), str) or not spec["city"]["name"].strip():
        raise SpecError("city.name must be a non-empty string")
    for key in ("label", "editorial_text", "caption"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise SpecError(f"{key} must be a non-empty string")
    return spec


def country_rings(country: str, bbox: list[float]) -> list[list[tuple[float, float]]]:
    """Projected outer rings of a country, restricted to the bbox window."""
    west, east, south, north = bbox
    data = json.loads((CATALOG / "ne_50m_admin_0_countries.geojson").read_text())
    feature = next((f for f in data["features"]
                    if f["properties"].get("ADMIN") == country), None)
    if feature is None:
        raise SpecError(f"highlight_country not found in catalog: {country}")
    geom = feature["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    result = []
    for polygon in polygons:
        ring = polygon[0]
        if not ring:
            continue
        mean_lon = sum(p[0] for p in ring) / len(ring)
        mean_lat = sum(p[1] for p in ring) / len(ring)
        if not (west <= mean_lon <= east and south <= mean_lat <= north):
            continue
        projected = [geo_xy(float(lon), float(lat)) for lon, lat in ring
                     if EXTENT[0] <= lon <= EXTENT[1] and EXTENT[2] <= lat <= EXTENT[3]]
        simplified = douglas_peucker(projected, 2.0)
        if len(simplified) > 3:
            result.append(simplified)
    if not result:
        raise SpecError(f"no polygons of {country} inside bbox {bbox}")
    return result


HIGHLIGHT_FILL = "#FFD23F"  # bright editorial yellow for the highlighted country


def country_fill_layer(rings: list[list[tuple[float, float]]],
                       focus: tuple[float, float], zoom: float, end: int) -> dict:
    """Filled yellow country shape, moved with the same camera as the plate."""
    xs = [x for ring in rings for x, _ in ring]
    ys = [y for ring in rings for _, y in ring]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    commands: list[dict] = []
    for ring in rings:
        points = [(x - min_x, y - min_y) for x, y in ring]
        commands.append({"type": "move_to", "point": list(points[0])})
        commands.extend({"type": "line_to", "point": list(p)} for p in points[1:])
        commands.append({"type": "close"})
    layer = {
        "id": "country-fill", "type": "shape",
        "size": [round(max_x - min_x, 3), round(max_y - min_y, 3)],
        "position": [round(center[0], 3), round(center[1], 3)],
        "start_frame": 0, "duration_frames": FRAMES,
        "shape": {"type": "path", "path": commands, "fill": rgba(HIGHLIGHT_FILL, 0.92),
                  "stroke": {"color": "#B8791C", "width": 2}, "operators": []},
        "animation": {"tracks": [track("opacity", [(0, 0), (40, 0), (58, 1), (FRAMES - 1, 1)])]},
    }
    return attach_geo(layer, center, zoom, end, focus, keep_size=False)


def build_plan(spec: dict) -> dict:
    spec = validate_spec(spec)
    zoom = float(spec["camera"]["zoom"])
    focus = geo_xy(float(spec["camera"]["lon"]), float(spec["camera"]["lat"]))
    end = 76
    motion = layer_map_motion(focus, zoom, end)
    layers = map_base(motion, spec["caption"])

    rings = country_rings(spec["highlight_country"], [float(v) for v in spec["bbox"]])
    layers.append(country_fill_layer(rings, focus, zoom, end))
    append_boundary_segments(layers, rings, "country-border", 58, 44, focus, zoom, end)

    city = spec["city"]
    p = geo_xy(float(city["lon"]), float(city["lat"]))
    # Marker pops in once the country outline has drawn.
    layers.append(attach_geo({
        "id": "city-marker", "type": "shape", "size": [22 * zoom, 22 * zoom], "position": p,
        "start_frame": 0, "duration_frames": FRAMES,
        "shape": {"type": "ellipse", "fill": rgba(AMBER),
                  "stroke": {"color": "#FFF0CB", "width": 3}},
        "animation": {"tracks": [track("opacity", [(0, 0), (100, 0), (112, 1), (FRAMES - 1, 1)])]},
    }, p, zoom, end, focus))

    # Label box sits up-right of the city; connector line runs from marker to box.
    box_c = (p[0] + 60, p[1] - 40)
    layers.append(segment_layer("city-connector", p, box_c, CYAN, 3.0, 116, focus, zoom, end))
    layers.append(attach_geo({
        "id": "label-box", "type": "shape", "size": [280 * zoom, 64 * zoom], "position": box_c,
        "start_frame": 0, "duration_frames": FRAMES,
        "shape": {"type": "rounded_rect", "fill": rgba(INK), "radius": 6,
                  "stroke": {"color": CYAN, "width": 2}},
        "animation": {"tracks": [track("opacity", [(0, 0), (126, 0), (138, 1), (FRAMES - 1, 1)])]},
    }, box_c, zoom, end, focus, keep_size=True))
    # Native sizes are multiplied by zoom because attach_geo counter-scales by 1/zoom.
    layers.append(attach_geo({
        "id": "label-text", "type": "text", "text": spec["label"].upper(),
        "size": [260 * zoom, 40 * zoom], "position": box_c,
        "start_frame": 0, "duration_frames": FRAMES,
        "style": {"font": FONT, "font_size": 26 * zoom, "min_font_size": 26 * zoom,
                  "max_font_size": 26 * zoom, "fit_mode": "shrink_only", "fill": PAPER,
                  "stroke": {"color": "#10202B", "width": 2}},
        "animation": {"tracks": [track("opacity", [(0, 0), (138, 0), (148, 1), (FRAMES - 1, 1)])]},
    }, box_c, zoom, end, focus))

    # Large editorial line sits below the label box.
    ed = (box_c[0], box_c[1] - 80)
    layers.append(attach_geo({
        "id": "editorial-text", "type": "text", "text": spec["editorial_text"],
        "size": [600 * zoom, 90 * zoom], "position": ed, "start_frame": 0, "duration_frames": FRAMES,
        "style": {"font": FONT, "font_size": 64 * zoom, "min_font_size": 64 * zoom,
                  "max_font_size": 64 * zoom,
                  "fit_mode": "shrink_only", "fill": AMBER,
                  "stroke": {"color": "#10202B", "width": 2}},
        "animation": {"tracks": [track("opacity", [(0, 0), (140, 0), (148, 1), (FRAMES - 1, 1)])]},
    }, ed, zoom, end, focus))
    return base_plan(spec["job_id"], layers)


def write_plan(spec: dict, out_dir: Path) -> Path:
    plan = build_plan(spec)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{spec['job_id']}.plan.json"
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=PLANS)
    parser.add_argument("--render", action="store_true",
                        help="also render the plan with the Chronon CLI")
    args = parser.parse_args()
    try:
        spec = json.loads(args.spec.read_text())
        spec = validate_spec(spec)
    except (SpecError, json.JSONDecodeError, OSError) as exc:
        print(f"invalid spec: {exc}", file=sys.stderr)
        return 2
    prepare_map_plate()
    path = write_plan(spec, args.out_dir)
    print(path)
    if args.render:
        import subprocess
        cmd = [str(base.CLI), "render", "--plan", str(path), "--assets-root", str(base.WORKSPACE),
               "--backend", "vulkan", "--hardware", "none", "--fps", "30", "--crf", "18",
               "--preset", "veryfast", "--log-level", "error",
               "--output", str(args.out_dir / f"{spec['job_id']}.mp4")]
        subprocess.run(cmd, cwd=base.WORKSPACE, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
