#!/usr/bin/env python3
"""Render the ten location/map entity motion presets as a single gallery."""
import json
import math
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
CATALOG = Path(__file__).resolve().parents[2] / "catalog/entity_motion_families.v1.json"
ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
OUT = ROOT / "out/editorial_v1"
PRESETS = [
    "location_map_pin_reveal", "location_map_fly_pin", "location_region_highlight",
    "location_route_draw", "location_tilt_focus", "location_radar_ping",
    "location_cluster_reveal", "location_marker_drop", "location_geo_card_split",
    "location_follow_route_push",
]
ACCENTS = ["#69D7C6", "#83C8F2", "#D2B66F", "#E6B86A", "#9BC6B8",
           "#76CFC3", "#9BC5ED", "#E8BA72", "#A8C4BB", "#8BD1C5"]
BG = [0.018, 0.032, 0.038, 1]
MAP_ASSET = "assets/canary/nasa-blue-marble.png"
BOUNDARY_ASSET = "assets/canary/natural-earth-boundaries.png"
TILT_ASSET = "assets/canary/nasa-blue-marble-perspective.png"
TILT_BOUNDARY_ASSET = "assets/canary/natural-earth-boundaries-perspective.png"
MAP_SIZE = [1480, 630]
MAP_Y = 0
GEOJSON = Path(__file__).resolve().parents[2] / "catalog/ne_50m_admin_0_countries.geojson"
LON_MIN, LON_MAX = -100.0, 50.0
LAT_MIN, LAT_MAX = 8.0, 72.0
SEGMENT = 48
FPS = 24


def tr(prop, keys, easing="out_cubic"):
    normalized = dict(keys)
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": normalized[f]} for f in sorted(normalized)]}


def rgba(h, alpha=1):
    h = h.lstrip("#")
    return [int(h[n:n+2], 16) / 255 for n in (0, 2, 4)] + [alpha]


def geo_xy(lon, lat):
    """Project lon/lat into the fixed 2D atlas coordinate system."""
    x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * MAP_SIZE[0]
    y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * MAP_SIZE[1]
    return [x - MAP_SIZE[0] / 2, y - MAP_SIZE[1] / 2]


def homography(src, dst):
    """Solve an 8-parameter projective transform from four point pairs."""
    rows, values = [], []
    for (x, y), (u, v) in zip(src, dst):
        rows.extend(([x, y, 1, 0, 0, 0, -u*x, -u*y],
                     [0, 0, 0, x, y, 1, -v*x, -v*y]))
        values.extend((u, v))
    a = [row[:] + [value] for row, value in zip(rows, values)]
    for col in range(8):
        pivot = max(range(col, 8), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [n / divisor for n in a[col]]
        for row in range(8):
            if row == col: continue
            factor = a[row][col]
            a[row] = [v - factor * p for v, p in zip(a[row], a[col])]
    return [a[i][8] for i in range(8)] + [1.0]


def transform_point(point, matrix):
    x, y = point
    den = matrix[6]*x + matrix[7]*y + matrix[8]
    return [(matrix[0]*x + matrix[1]*y + matrix[2]) / den,
            (matrix[3]*x + matrix[4]*y + matrix[5]) / den]


def tilt_matrix():
    w, h = MAP_SIZE
    source = [(0, 0), (w, 0), (w, h), (0, h)]
    # The far edge narrows and lifts; the near edge stays broad like a tilted map plane.
    target = [(205, 142), (w-205, 142), (w-8, h-34), (8, h-34)]
    return homography(source, target)


def prepare_atlas():
    """Use NASA satellite texture and georeferenced Natural Earth boundaries."""
    geo = json.loads(GEOJSON.read_text())
    source = Path(__file__).resolve().parents[2] / "catalog/nasa_blue_marble_north_atlantic.png"
    image = Image.open(source).convert("RGB")
    out = ASSETS / MAP_ASSET
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)

    # Fine, actual country borders sit over the imagery without invented fills.
    scale = 2
    boundary = Image.new("RGBA", (MAP_SIZE[0]*scale, MAP_SIZE[1]*scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(boundary)
    def pixel(point):
        return ((point[0]-LON_MIN)/(LON_MAX-LON_MIN)*MAP_SIZE[0]*scale,
                (LAT_MAX-point[1])/(LAT_MAX-LAT_MIN)*MAP_SIZE[1]*scale)
    for feature in geo["features"]:
        geom = feature.get("geometry")
        if not geom: continue
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            ring = poly[0]
            for first, second in zip(ring, ring[1:]):
                if (min(first[0], second[0]) <= LON_MAX and max(first[0], second[0]) >= LON_MIN
                        and min(first[1], second[1]) <= LAT_MAX and max(first[1], second[1]) >= LAT_MIN):
                    draw.line((pixel(first), pixel(second)), fill=(229, 230, 217, 145), width=2)
    boundary = boundary.resize(tuple(MAP_SIZE), Image.Resampling.LANCZOS)
    boundary.save(ASSETS / BOUNDARY_ASSET, optimize=True)

    inverse = homography([(205, 142), (MAP_SIZE[0]-205, 142),
                          (MAP_SIZE[0]-8, MAP_SIZE[1]-34), (8, MAP_SIZE[1]-34)],
                         [(0, 0), (MAP_SIZE[0], 0), (MAP_SIZE[0], MAP_SIZE[1]), (0, MAP_SIZE[1])])
    tilted = image.transform(tuple(MAP_SIZE), Image.Transform.PERSPECTIVE, inverse[:8],
                             resample=Image.Resampling.BICUBIC, fillcolor=(4, 8, 15))
    tilted.save(ASSETS / TILT_ASSET)
    tilted_boundary = boundary.transform(tuple(MAP_SIZE), Image.Transform.PERSPECTIVE, inverse[:8],
                                         resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))
    tilted_boundary.save(ASSETS / TILT_BOUNDARY_ASSET, optimize=True)
    return geo


def country_shape(geo, name, ident, start, duration, color):
    feature = next(f for f in geo["features"] if f["properties"].get("ADMIN") == name)
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    path = []
    for poly in polys:
        ring = poly[0]
        points = [geo_xy(p[0], p[1]) for p in ring if LON_MIN <= p[0] <= LON_MAX and LAT_MIN <= p[1] <= LAT_MAX]
        if len(points) < 3:
            continue
        path.append({"type": "move_to", "point": points[0]})
        path.extend({"type": "line_to", "point": point} for point in points[1:])
        path.append({"type": "close"})
    common = {"type": "shape", "size": MAP_SIZE, "position": [640, 360 + MAP_Y],
              "start_frame": start, "duration_frames": duration}
    fade = [tr("opacity", [(0, 0), (10, 1), (duration-9, .88), (duration-1, 0)])]
    # Layered strokes provide a restrained emissive edge with current primitives.
    return [
        {**common, "id": f"{ident}-halo", "shape": {"type": "path", "path": path,
         "fill": rgba(color, 0), "stroke": {"color": color, "width": 13}}, "animation": {"tracks": fade}},
        {**common, "id": f"{ident}-edge", "shape": {"type": "path", "path": path,
         "fill": rgba(color, 0), "stroke": {"color": color, "width": 7}}, "animation": {"tracks": fade}},
        {**common, "id": ident, "shape": {"type": "path", "path": path,
         "fill": rgba(color, 0), "stroke": {"color": color, "width": 2.2}}, "animation": {"tracks": fade}},
    ]


def radial_country_fill(geo, name, start, color, steps=18):
    """Create short alpha-mask frames that grow from the country capital outward."""
    feature = next(f for f in geo["features"] if f["properties"].get("ADMIN") == name)
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    mask = Image.new("L", tuple(MAP_SIZE), 0)
    draw = ImageDraw.Draw(mask)
    for poly in polys:
        points = [((p[0]-LON_MIN)/(LON_MAX-LON_MIN)*MAP_SIZE[0],
                   (LAT_MAX-p[1])/(LAT_MAX-LAT_MIN)*MAP_SIZE[1]) for p in poly[0]]
        if len(points) >= 3:
            draw.polygon(points, fill=255)
    mask_np = np.asarray(mask, dtype=np.float32)
    yy, xx = np.mgrid[0:MAP_SIZE[1], 0:MAP_SIZE[0]]
    cx = (2.352-LON_MIN)/(LON_MAX-LON_MIN)*MAP_SIZE[0]
    cy = (LAT_MAX-48.857)/(LAT_MAX-LAT_MIN)*MAP_SIZE[1]
    distance = np.sqrt((xx-cx)**2 + (yy-cy)**2)
    max_radius = max(float(distance[mask_np > 0].max()), 1)
    rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    result = []
    for index in range(steps):
        radius = max_radius * (index + 1) / steps
        coverage = np.clip((radius + 5 - distance) / 10, 0, 1) * (mask_np / 255) * 0.78
        rgba_frame = np.zeros((MAP_SIZE[1], MAP_SIZE[0], 4), dtype=np.uint8)
        rgba_frame[:, :, :3] = rgb
        rgba_frame[:, :, 3] = np.asarray(coverage * 255, dtype=np.uint8)
        asset = f"assets/canary/france-radial-{index:02d}.png"
        Image.fromarray(rgba_frame, "RGBA").save(ASSETS / asset)
        result.append(image(f"{name.lower()}-radial-{index}", MAP_SIZE, [0, 0], start + index,
                            [tr("opacity", [(0, 1)])], duration=1, asset=asset))
    return result


def route_courier(id_, a, b, color, start, duration=SEGMENT, curve=-72):
    frames = sorted(set([0, 5, 10, 15, 20, min(25, duration-1), duration-1]))
    tracks_x, tracks_y = [], []
    for frame in frames:
        t = frame / max(1, duration - 1)
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t + curve * math.sin(math.pi * t)
        tracks_x.append((frame, x-a[0]))
        tracks_y.append((frame, y-a[1]))
    return marker(id_, a, color, start, duration, radius=6,
                  tracks=[tr("position_x", tracks_x, "in_out_cubic"),
                          tr("position_y", tracks_y, "in_out_cubic"),
                          tr("opacity", [(0, 0), (2, 1), (duration-3, 1), (duration-1, 0)]),
                          tr("scale", [(0, .5), (4, 1), (duration-3, 1), (duration-1, .5)])],
                  stroke="#F5F4E9")


def image(id_, size, position, start, tracks, duration=SEGMENT, fit="contain", enable_3d=False, asset=MAP_ASSET):
    return {"id": id_, "type": "image", "asset": asset, "size": size, "position": position,
            "fit": fit, "start_frame": start, "duration_frames": duration,
            "animation": {"tracks": tracks}, **({"enable_3d": True} if enable_3d else {})}


def text(id_, value, size, offset, start, duration, style, tracks):
    return {"id": id_, "type": "text", "text": value, "size": size,
            "position": [640 + offset[0], 360 + offset[1]], "start_frame": start,
            "duration_frames": duration, "style": style, "animation": {"tracks": tracks}}


def marker(id_, offset, color, start, duration=SEGMENT, radius=13, tracks=None, stroke="#F1F5F2"):
    return {"id": id_, "type": "shape", "size": [radius * 2, radius * 2],
            "position": [640 + offset[0], 360 + offset[1]],
            "start_frame": start, "duration_frames": duration,
            "shape": {"type": "ellipse", "fill": rgba(color),
                      "stroke": {"color": stroke, "width": 2}},
            "animation": {"tracks": tracks or [tr("scale", [(0, .1), (16, 1), (39, 1), (47, .1)])]}}


def line(id_, start_pt, end_pt, color, start, duration=SEGMENT, width=3, opacity=True):
    dx, dy = end_pt[0] - start_pt[0], end_pt[1] - start_pt[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
    tracks = [tr("scale", [(0, .01), (22, 1), (39, 1), (47, .01)])]
    if abs(angle) > .1:
        tracks.append(tr("rotation_z", [(0, angle), (22, angle), (39, angle), (47, angle)]))
    return {"id": id_, "type": "shape", "size": [length, width],
            "position": [640 + (start_pt[0] + end_pt[0]) / 2, 360 + (start_pt[1] + end_pt[1]) / 2],
            "start_frame": start, "duration_frames": duration,
            "shape": {"type": "rect", "fill": rgba(color, .90)},
            "animation": {"tracks": tracks}}


def route_dots(id_prefix, a, b, color, start, count=24, curve=-68, reveal_start=6):
    result = []
    for j in range(count):
        t = (j + .5) / count
        x = a[0] + (b[0] - a[0]) * t
        y = a[1] + (b[1] - a[1]) * t + curve * math.sin(math.pi * t)
        reveal = reveal_start + int(16 * t)
        live = SEGMENT - reveal
        result.append(marker(f"{id_prefix}-{j:02d}", [x, y], color,
                             start + reveal, live, radius=3,
                             tracks=[tr("opacity", [(0, 0), (2, .96), (live - 5, .96), (live, 0)]),
                                     tr("scale", [(0, .4), (4, 1), (live - 5, 1), (live, .5)])],
                             stroke=color))
    return result


def pin_label(layers, ident, name, point, color, start, duration=SEGMENT):
    layers.append(marker(f"{ident}-pin", point, color, start, duration, radius=10))
    layers.append(text(f"{ident}-name", name.upper(), [210, 28], [point[0] + 18, point[1] - 26],
                       start + 7, duration - 7,
                       {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 13, "fill": color},
                       [tr("opacity", [(0, 0), (7, 1), (39, 1), (47, 0)])]))


def map_motion(preset):
    base = [tr("opacity", [(0, 0), (12, 1), (39, 1), (47, 0)])]
    # Keep the atlas static while geographic overlays enter. This makes every
    # pin, label and route share the same exact projected map coordinates.
    return base


def build():
    catalog = json.loads(CATALOG.read_text())
    family = next(item for item in catalog["families"] if item["entity_type"] == "LOCATION")
    assert family["presets"] == PRESETS, "Location catalog and renderer preset order diverged"
    requested = os.environ.get("LOCATION_ONLY_PRESET")
    selected = [requested] if requested else PRESETS
    if requested not in (None, *PRESETS):
        raise ValueError(f"unknown location preset: {requested}")
    total_frames = len(selected) * SEGMENT
    geo = prepare_atlas()
    layers = [{"id": "night-atlas", "type": "color", "color": BG, "size": [1280, 720],
               "start_frame": 0, "duration_frames": total_frames}]
    cities = {"new_york": geo_xy(-74.006, 40.713), "london": geo_xy(-.128, 51.507),
              "paris": geo_xy(2.352, 48.857), "rome": geo_xy(12.496, 41.903),
              "lisbon": geo_xy(-9.139, 38.722), "berlin": geo_xy(13.405, 52.520)}
    names = ["London, United Kingdom", "London", "France", "Atlantic route",
             "Rome, Italy", "London", "Europe network", "Paris, France",
             "Northern Europe", "Transatlantic corridor"]
    small_tag = {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 12, "fill": "#B3C0BF"}
    title_style = {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 31, "fill": "#F4F6F2",
                   "fit_mode": "shrink_only", "min_font_size": 20, "max_font_size": 31}
    for scene_index, preset in enumerate(selected):
        i = PRESETS.index(preset)
        start = scene_index * SEGMENT
        accent = ACCENTS[i]
        atlas = TILT_ASSET if preset == "location_tilt_focus" else MAP_ASSET
        map_layer = image(f"atlas-{i}", MAP_SIZE, [0, MAP_Y], start, map_motion(preset), asset=atlas)
        layers.append(map_layer)
        boundary_asset = TILT_BOUNDARY_ASSET if preset == "location_tilt_focus" else BOUNDARY_ASSET
        layers.append(image(f"country-borders-{i}", MAP_SIZE, [0, MAP_Y], start,
                            map_motion(preset), asset=boundary_asset))

        # The header and footer remain open on the map; no card or HUD panel.
        layers.append(text(f"geo-kicker-{i}", "FIELD NOTE   /   LOCATION", [400, 24], [-400, -293],
                           start + 3, SEGMENT - 3, {**small_tag, "fill": accent},
                           [tr("opacity", [(0, 0), (9, 1), (38, 1), (45, 0)])]))
        layers.append(text(f"geo-title-{i}", names[i], [550, 54], [-255 if preset == "location_geo_card_split" else 0, -252],
                           start + 5, SEGMENT - 5, title_style,
                           [tr("opacity", [(0, 0), (12, 1), (39, 1), (47, 0)]),
                            tr("position_y", [(0, 12), (17, 0), (39, 0), (47, 8)])]))
        layers.append(text(f"geo-preset-{i}", preset, [520, 24], [0, 290], start + 7, SEGMENT - 7,
                           {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 12, "fill": "#839191"},
                           [tr("opacity", [(0, 0), (8, 1), (34, 1), (41, 0)])]))

        if preset in ("location_map_pin_reveal", "location_map_fly_pin"):
            focus = cities["london"]
            delay = 22 if preset.endswith("fly_pin") else 10
            pin_label(layers, f"london-{i}", "London", focus, accent, start + delay, SEGMENT - delay)
            layers.append(line(f"pin-leader-{i}", [focus[0], focus[1] - 5], [focus[0] + 54, focus[1] - 58], accent,
                               start + 9, SEGMENT - 9, width=2))
            if preset == "location_map_fly_pin":
                layers.append(text(f"fly-latlon-{i}", "51.507°N   0.128°W", [250, 24], [focus[0] + 115, focus[1] - 67],
                                   start + 22, 22, small_tag,
                                   [tr("opacity", [(0, 0), (8, 1), (18, 1), (22, 0)])]))

        elif preset == "location_region_highlight":
            layers.extend(country_shape(geo, "France", f"france-region-{i}", start + 5, SEGMENT - 5, accent))
            layers.extend(radial_country_fill(geo, "France", start + 6, accent))
            region = geo_xy(2.2, 46.2)
            pin_label(layers, f"region-focus-{i}", "France", region, accent,
                      start + 15, SEGMENT - 15)

        elif preset in ("location_route_draw", "location_follow_route_push"):
            a, b = cities["new_york"], cities["london"]
            route_delay = 12 if preset == "location_follow_route_push" else 8
            layers.extend(route_dots(f"transatlantic-route-{i}", a, b, accent,
                                     start, count=28, reveal_start=route_delay,
                                     curve=-90 if preset == "location_follow_route_push" else -72))
            layers.append(route_courier(f"route-courier-{i}", a, b, accent, start + route_delay,
                                        SEGMENT - route_delay,
                                        curve=-90 if preset == "location_follow_route_push" else -72))
            pin_label(layers, f"origin-{i}", "New York", a, "#F0C179", start + 4, SEGMENT - 4)
            pin_label(layers, f"destination-{i}", "London", b, accent, start + 15, SEGMENT - 15)
            if preset == "location_follow_route_push":
                layers.append(text(f"route-distance-{i}", "5,570 km     ·     7h 05m", [350, 28], [0, 203], start + 9, SEGMENT - 9,
                                   {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 14, "fill": "#CFD8D5"},
                                   [tr("opacity", [(0, 0), (18, 1), (37, 1), (39, 0)])]))

        elif preset == "location_tilt_focus":
            matrix = tilt_matrix()
            source_point = [cities["rome"][0] + MAP_SIZE[0] / 2, cities["rome"][1] + MAP_SIZE[1] / 2]
            projected = transform_point(source_point, matrix)
            focus = [projected[0] - MAP_SIZE[0] / 2, projected[1] - MAP_SIZE[1] / 2]
            pin_label(layers, f"rome-{i}", "Rome", focus, accent, start + 9, SEGMENT - 9)
            layers.append(text(f"rome-coords-{i}", "41.90°N   12.50°E", [250, 25], [focus[0] + 100, focus[1] + 12],
                               start + 14, SEGMENT - 14, small_tag,
                               [tr("opacity", [(0, 0), (10, 1), (30, 1), (37, 0)])]))

        elif preset == "location_radar_ping":
            focus = cities["london"]
            pin_label(layers, f"radar-core-{i}", "London", focus, accent, start + 5, SEGMENT - 5)
            for j, (delay, diameter) in enumerate(((5, 74), (12, 132), (19, 198))):
                live = SEGMENT - delay
                layers.append({"id": f"radar-wave-{i}-{j}", "type": "shape", "size": [diameter, diameter],
                               "position": [640 + focus[0], 360 + focus[1]],
                               "start_frame": start + delay, "duration_frames": live,
                               "shape": {"type": "ellipse", "fill": rgba(accent, .055),
                                         "stroke": {"color": accent, "width": 1.7}},
                               "animation": {"tracks": [tr("scale", [(0, .28), (live - 1, 1)]),
                                                           tr("opacity", [(0, .68), (max(1, live // 2), .36), (live - 1, .08)])]}})

        elif preset == "location_cluster_reveal":
            for j, city in enumerate(("london", "paris", "rome", "lisbon", "berlin")):
                color = accent if city == "rome" else "#C2D0CB"
                delay = 5 + j * 4
                layers.append(marker(f"cluster-{city}-{i}", cities[city], color, start + delay,
                                     SEGMENT - delay, radius=8 if city != "rome" else 12))
            layers.append(line(f"cluster-spine-{i}", cities["london"], cities["rome"], accent,
                               start + 8, SEGMENT - 8, width=1))
            layers.append(text(f"cluster-focus-{i}", "ROME  /  5 LOCATIONS", [250, 26], [260, 36],
                               start + 18, SEGMENT - 18,
                               {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 13, "fill": accent},
                               [tr("opacity", [(0, 0), (8, 1), (25, 1), (29, 0)])]))

        elif preset == "location_marker_drop":
            focus = cities["paris"]
            layers.append({"id": f"paris-drop-{i}", "type": "shape", "size": [28, 28],
                           "position": [640 + focus[0], 360 + focus[1]],
                           "start_frame": start + 8, "duration_frames": SEGMENT - 8,
                           "shape": {"type": "ellipse", "fill": rgba(accent), "stroke": {"color": "#F1F5F2", "width": 2}},
                           "animation": {"tracks": [tr("position_y", [(0, -118), (16, 0), (39, 0), (47, -10)]),
                                                       tr("scale", [(0, .55), (16, 1), (39, 1), (47, .86)])]}})
            layers.append(line(f"paris-drop-leader-{i}", [focus[0], focus[1] + 12], [focus[0], focus[1] + 64], accent,
                               start + 16, SEGMENT - 16, width=2))
            layers.append(text(f"paris-drop-label-{i}", "PARIS  /  FRANCE", [260, 28], [focus[0] + 100, focus[1] + 72],
                               start + 16, SEGMENT - 16, {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 14, "fill": accent},
                               [tr("opacity", [(0, 0), (7, 1), (25, 1), (31, 0)])]))

        elif preset == "location_geo_card_split":
            focus = geo_xy(12.568, 55.676)
            layers.append(marker(f"split-map-pin-{i}", focus, accent, start + 12, SEGMENT - 12, radius=10))
            layers.append(text(f"split-place-{i}", "Copenhagen", [420, 56], [345, -34], start + 8, SEGMENT - 8,
                               {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 31, "fill": "#F2F5F1"},
                               [tr("opacity", [(0, 0), (13, 1), (39, 1), (47, 0)]),
                                tr("position_x", [(0, 32), (18, 0), (39, 0), (47, 24)])]))
            layers.append(text(f"split-coords-{i}", "55.676°N  /  12.568°E", [380, 28], [345, 13], start + 13, SEGMENT - 13,
                               small_tag, [tr("opacity", [(0, 0), (11, 1), (32, 1), (39, 0)])]))
            layers.append(line(f"split-rule-{i}", [175, 45], [485, 45], accent, start + 11, SEGMENT - 11, width=2))

    # Clip local animation keyframes to shortened, deliberately staggered layer spans.
    for layer in layers:
        span = layer.get("duration_frames", SEGMENT)
        for track in layer.get("animation", {}).get("tracks", []):
            by_frame = {}
            for key in track.get("keyframes", []):
                by_frame[min(key["frame"], span - 1)] = key["value"]
            track["keyframes"] = [{"frame": frame, "value": by_frame[frame]} for frame in sorted(by_frame)]

    job_id = (f"{requested}_canary" if requested else "location_family_v3_perspective_gallery")
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
            "canvas": {"width": 1280, "height": 720, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": total_frames},
            "layers": layers, "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"}}
    plans, renders = OUT / "plans", OUT / "renders"
    plans.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    plan_file = plans / f"{job_id}.plan.json"
    output = renders / f"{job_id}.mp4"
    plan_file.write_text(json.dumps(plan, indent=2) + "\n")
    subprocess.run([str(CLI), "render-plan", "--input", str(plan_file), "--assets-root", str(ASSETS),
                    "--output", str(output), "--backend", "software", "--encode-preset", "veryfast",
                    "--trace", str(renders / f"{job_id}.pftrace")], check=True, cwd=ROOT)
    print(output)


if __name__ == "__main__":
    build()
