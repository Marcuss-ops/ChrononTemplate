#!/usr/bin/env python3
"""Consume map_motion_v1 and author deterministic family gallery render plans."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CATALOG = ROOT / "catalog/map_motion_v1.json"
GEOJSON = ROOT / "catalog/ne_50m_admin_0_countries.geojson"
OUT = ROOT / "out/map_motion_v1"
CLI_CANDIDATES = (
    ROOT.parent / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
    ROOT.parent / "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)
W, H, FPS, SEGMENT = 1280, 720, 24, 72
MAP_W, MAP_H = 1280.0, 545.0
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = -100.0, 50.0, 8.0, 72.0
ACCENTS = ("#D2B66F", "#69D7C6", "#83C8F2", "#E6B86A", "#9BC6B8", "#76CFC3", "#9BC5ED")
FONT = "Chronon3d/assets/fonts/Poppins-Regular.ttf"


def rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    value = hex_color.lstrip("#")
    return [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def projected(lon: float, lat: float) -> tuple[float, float]:
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * MAP_W - MAP_W / 2
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * MAP_H - MAP_H / 2
    return x, y


def track(prop: str, keys: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}


def layer(id_: str, typ: str, start: int, duration: int, **kwargs) -> dict:
    return {"id": id_, "type": typ, "start_frame": start,
            "duration_frames": duration, **kwargs}


def text_layer(id_: str, value: str, start: int, duration: int, y: float,
               color: str, size: int, opacity_keys=None) -> dict:
    animations = [track("opacity", opacity_keys or [(0, 0), (8, 1), (duration-8, 1), (duration-1, 0)])]
    return layer(id_, "text", start, duration, text=value,
                 size=[1120, max(26, size + 12)], position=[640, y],
                 style={"font": FONT, "font_size": size, "fill": color,
                        "fit_mode": "shrink_only", "min_font_size": max(12, size-8), "max_font_size": size},
                 animation={"tracks": animations})


def shape_layer(id_: str, start: int, duration: int, position: tuple[float, float],
                path: list[dict], color: str, width: float, *, trim=False,
                opacity=1.0, animation=None) -> dict:
    operators = []
    if trim:
        operators.append({"kind": "trim", "params": {"start": 0, "end": 1,
                          "animation": {"easing": "out_cubic", "keyframes": [
                              {"frame": 0, "value": [0, 0, 0]},
                              {"frame": min(43, duration-1), "value": [0, 1, 0]}]}}})
    return layer(id_, "shape", start, duration, size=[MAP_W, MAP_H], position=[640, 360],
                 shape={"type": "path", "path": path, "fill": [0, 0, 0, 0],
                        "stroke": {"color": color, "width": width}, "operators": operators},
                 opacity=opacity, animation={"tracks": animation or [
                     track("opacity", [(0, 0), (min(8, duration-1), opacity),
                                        (duration-1, opacity)])]})


def france_path(geo: dict) -> list[dict]:
    feature = next(f for f in geo["features"] if f.get("properties", {}).get("ADMIN") == "France")
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    commands: list[dict] = []
    for poly in polys:
        ring = poly[0]
        # The focus crop clips overseas territories naturally and keeps plans compact.
        points = [projected(p[0], p[1]) for p in ring
                  if LON_MIN <= p[0] <= LON_MAX and LAT_MIN <= p[1] <= LAT_MAX]
        if len(points) < 3:
            continue
        # Simplify deterministically to a maximum of ~180 vertices per ring.
        stride = max(1, math.ceil(len(points) / 180))
        points = points[::stride]
        commands.append({"type": "move_to", "point": list(points[0])})
        commands.extend({"type": "line_to", "point": list(point)} for point in points[1:])
        commands.append({"type": "close"})
    return commands


def city_marker(id_: str, start: int, duration: int, name: str,
                lon: float, lat: float, accent: str) -> list[dict]:
    px, py = projected(lon, lat)
    marker = layer(id_ + "-pin", "shape", start + 13, duration - 13,
                   size=[24, 24], position=[640 + px, 360 + py],
                   shape={"type": "ellipse", "fill": rgba(accent),
                          "stroke": {"color": "#F5F4E9", "width": 2}},
                   animation={"tracks": [track("scale", [(0, .1), (12, 1), (duration-14, 1)]),
                                          track("opacity", [(0, 0), (8, 1), (duration-14, 1)])]})
    label = layer(id_ + "-label", "text", start + 15, duration - 15,
                  text=name.upper(), size=[220, 34], position=[640 + px + 32, 360 + py - 26],
                  style={"font": FONT, "font_size": 17, "fill": accent},
                  animation={"tracks": [track("opacity", [(0, 0), (7, 1), (duration-16, 1)])]})
    return [marker, label]


def route_layers(id_: str, start: int, duration: int, accent: str) -> list[dict]:
    # NYC–London great-circle-like cubic in the common equirectangular projection.
    a, b = projected(-74.006, 40.713), projected(-0.128, 51.507)
    path = [{"type": "move_to", "point": list(a)},
            {"type": "cubic_to", "point": list(b),
             "control1": [a[0] + 145, a[1] - 82], "control2": [b[0] - 145, b[1] - 82]}]
    route = shape_layer(id_ + "-route", start + 4, duration - 4, (0, 0), path,
                        accent, 3.2, trim=True)
    # Sample the exact same cubic parameter used by the trim animation. The arrow
    # follows the tangent and therefore remains coupled to route progress.
    def cubic(t: float):
        p0, p1 = a, [a[0] + 145, a[1] - 82]
        p2, p3 = [b[0] - 145, b[1] - 82], b
        u = 1-t
        x = u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0]
        y = u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]
        dx = 3*u*u*(p1[0]-p0[0]) + 6*u*t*(p2[0]-p1[0]) + 3*t*t*(p3[0]-p2[0])
        dy = 3*u*u*(p1[1]-p0[1]) + 6*u*t*(p2[1]-p1[1]) + 3*t*t*(p3[1]-p2[1])
        return x, y, math.degrees(math.atan2(dy, dx))
    keys = [6, 15, 25, 36, 48]
    coords = [cubic((f-6)/42) for f in keys]
    arrow = layer(id_ + "-route-head", "shape", start + 4, duration - 4,
                  size=[24, 18], position=[640 + coords[0][0], 360 + coords[0][1]],
                  shape={"type": "polygon", "points": 3, "rotation_degrees": 90,
                         "fill": rgba(accent)},
                  animation={"tracks": [track("position_x", [(f, 640+x) for f,(x,_,_) in zip(keys,coords)]),
                                         track("position_y", [(f, 360+y) for f,(_,y,_) in zip(keys,coords)]),
                                         track("rotation_z", [(f, angle) for f,(_,_,angle) in zip(keys,coords)])]})
    return [route, arrow, *city_marker(id_+"-origin", start, duration, "New York", -74.006, 40.713, "#E6B86A"),
            *city_marker(id_+"-destination", start, duration, "London", -0.128, 51.507, accent)]


def item_layers(item: dict, family: str, index: int, geo: dict) -> list[dict]:
    start, duration = index * SEGMENT, SEGMENT
    ident, title = item["id"], item["title"]
    accent = ACCENTS[index % len(ACCENTS)]
    map_asset = ("ChrononTemplate/catalog/maps/nasa_blue_marble_august.jpg"
                 if item.get("source") == "nasa" else
                 "ChrononTemplate/catalog/maps/natural_earth_hypso_relief_water.jpg")
    layers = [layer(f"{ident}-base", "image", start, duration, asset=map_asset,
                    size=[1280, 545], position=[640, 360], fit="cover",
                    animation={"tracks": [track("scale", [(0, 1.0), (duration-1, 1.045)], "in_out_sine")]})]
    layers.append(layer(f"{ident}-shade", "color", start, duration, color=[.015, .029, .036, .24],
                        size=[1280, 720], position=[640, 360]))
    layers.extend([
        text_layer(f"{ident}-eyebrow", family.replace("_", " ").upper(), start+2, duration-2, 64, accent, 15),
        text_layer(f"{ident}-title", title, start+5, duration-5, 112, "#F4F6F2", 34),
        text_layer(f"{ident}-id", ident, start+9, duration-9, 665, "#A8B8B6", 14),
    ])
    lower = ident.lower()
    if any(word in lower for word in ("country", "outline", "region", "border", "historical")):
        layers.append(shape_layer(f"{ident}-france-outline", start+7, duration-7,
                                  (0, 0), france_path(geo), accent, 2.5, trim=True))
    if any(word in lower for word in ("route", "arc", "destination", "chain")):
        layers.extend(route_layers(ident, start, duration, accent))
    elif any(word in lower for word in ("city", "pin", "radar", "spotlight", "label", "location", "focus")):
        city = ("London", -0.128, 51.507) if "london" in title.lower() or "route" in lower else ("Paris", 2.352, 48.857)
        if "multi" in lower or "trio" in lower or "quad" in lower or "cluster" in lower:
            for name, lon, lat in (("London", -0.128, 51.507), ("Paris", 2.352, 48.857), ("Rome", 12.496, 41.903)):
                layers.extend(city_marker(f"{ident}-{name.lower()}", start, duration, name, lon, lat, accent))
        else:
            layers.extend(city_marker(ident, start, duration, *city, accent))
    if "bubble" in lower or "choropleth" in lower or "metric" in lower:
        # Mark synthetic values as illustrative in-plan; no factual metrics are implied.
        for j, (lon, lat, radius) in enumerate(((-0.128,51.507,20),(2.352,48.857,15),(12.496,41.903,12))):
            x,y=projected(lon,lat)
            layers.append(layer(f"{ident}-data-{j}", "shape", start+12+j*4, duration-12-j*4,
                                size=[radius*2,radius*2], position=[640+x,360+y],
                                shape={"type":"ellipse","fill":rgba(accent,.38),"stroke":{"color":accent,"width":2}},
                                animation={"tracks":[track("scale",[(0,.4),(12,1)])]}))
        layers.append(text_layer(f"{ident}-disclaimer", "ILLUSTRATIVE DESIGN STUDY · NOT EMPIRICAL DATA",
                                 start+10, duration-10, 622, "#E6B86A", 13))
    note = item.get("note")
    if note:
        layers.append(text_layer(f"{ident}-note", note, start+12, duration-12, 615, "#E9C97B", 12))
    return layers


def build_plans(catalog=None, geo=None) -> dict[str, dict]:
    catalog = catalog or json.loads(CATALOG.read_text())
    geo = geo or json.loads(GEOJSON.read_text())
    if catalog.get("schema") != "chronontemplate.map-motion-family.v1" or catalog.get("catalog_id") != "map_motion_v1":
        raise ValueError("unsupported map-motion catalog schema/id")
    plans = {}
    seen = set()
    for family_index, family in enumerate(catalog.get("families", [])):
        items = family.get("items", [])
        if not items:
            raise ValueError(f"empty family: {family.get('id')}")
        for item in items:
            ident = item.get("id")
            if not ident or ident in seen:
                raise ValueError(f"missing/duplicate map-motion id: {ident}")
            seen.add(ident)
        duration = SEGMENT * len(items)
        layers = [layer("map-motion-background", "color", 0, duration,
                        color=[.012,.024,.032,1], size=[W,H], position=[W/2,H/2])]
        for index, item in enumerate(items):
            layers.extend(item_layers(item, family["id"], index, geo))
        job_id = f"canary_{family['id']}"
        plans[job_id] = {"schema":"chronon.render-plan.v3", "version":3, "job_id":job_id,
                         "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":duration},
                         "layers":layers,
                         "output":{"path":f"{job_id}.mp4","format":"mp4","codec":"h264"}}
    expected = {entry["id"] for fam in catalog["families"] for entry in fam["items"]}
    if seen != expected:
        raise ValueError("not every catalog item has a consumer")
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plans", action="store_true", help="write all family plans")
    mode.add_argument("--validate", action="store_true", help="write and validate every family plan")
    mode.add_argument("--render", action="store_true", help="write, validate and render every family plan")
    parser.add_argument("--family", help="restrict to a family id")
    parser.add_argument("--preset", help="restrict to a map motion id")
    parser.add_argument("--cli", type=Path, help="chronon3d_cli path")
    args = parser.parse_args()
    plans = build_plans()
    catalog = json.loads(CATALOG.read_text())
    item_to_family = {item["id"]: f["id"] for f in catalog["families"] for item in f["items"]}
    family = args.family or item_to_family.get(args.preset)
    if args.preset and args.preset not in item_to_family:
        parser.error(f"unknown map preset: {args.preset}")
    if family and family not in plans and f"canary_{family}" not in plans:
        parser.error(f"unknown map family: {family}")
    selected = {key:value for key,value in plans.items()
                if not family or key == f"canary_{family}"}
    if args.preset:
        source = next(f for f in catalog["families"] if f["id"] == family)
        item_index = next(i for i,item in enumerate(source["items"]) if item["id"] == args.preset)
        begin, end = item_index*SEGMENT, (item_index+1)*SEGMENT
        selected = {f"canary_{args.preset}": plans[f"canary_{family}"]}
        plan = selected[f"canary_{args.preset}"]
        plan["job_id"] = f"canary_{args.preset}"
        plan["canvas"]["duration_frames"] = SEGMENT
        plan["layers"] = [l for l in plan["layers"] if l["start_frame"] < end and l["start_frame"]+l["duration_frames"] > begin]
        for l in plan["layers"]:
            old_start = l["start_frame"]
            l["start_frame"] = max(0, old_start-begin)
            l["duration_frames"] = min(l["duration_frames"]-(l["start_frame"]-max(0,old_start-begin)), SEGMENT-l["start_frame"])
            # Family-specific layers use local keyframes; preserve them when clipping.
        plan["output"]["path"] = f"canary_{args.preset}.mp4"
    OUT.mkdir(parents=True, exist_ok=True)
    for job_id, plan in selected.items():
        path = OUT / f"{job_id}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"wrote {path}")
    if args.validate or args.render:
        cli = args.cli or next((p for p in CLI_CANDIDATES if p.is_file()), None)
        if cli is None:
            parser.error("chronon3d_cli not found; pass --cli")
        for job_id in selected:
            path = OUT / f"{job_id}.plan.json"
            subprocess.run([str(cli), "validate", "--plan", str(path), "--assets-root", str(WORKSPACE)], check=True)
            print(f"validated {job_id}", flush=True)
            if args.render:
                subprocess.run([str(cli), "render", "--plan", str(path), "--assets-root", str(WORKSPACE),
                                "--output", str(OUT / f"{job_id}.mp4"), "--backend", "software"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
