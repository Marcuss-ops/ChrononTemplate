#!/usr/bin/env python3
"""Render 14 five-second GPU sample animations for the 1973 oil-crisis pack."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2]
ROOT = TEMPLATE.parent
OUT = ROOT / "ChrononTemplate/out/oil_crisis_1973_animation_samples"
ASSETS = OUT / "assets"
PLANS = OUT / "plans"
CLI = ROOT / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
FPS, FRAMES, WIDTH, HEIGHT = 30, 150, 1920, 1080
FONT_BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_REGULAR = "Chronon3d/assets/fonts/Inter-Regular.ttf"
FONT_DIDONE = "Chronon3d/assets/fonts/Didot-Italic.ttf"
INK = "#111315"
YELLOW = "#F2E500"
CORAL = "#F14D36"


def track(prop: str, points: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in points]}


def color(hex_color: str, alpha: float = 1.0) -> list[float]:
    v = hex_color.lstrip("#")
    return [int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [alpha]


def shape(id_: str, x: float, y: float, w: float, h: float, fill: str,
          start: int = 0, opacity: float = 1.0, radius: float = 0,
          motion: list[dict] | None = None) -> dict:
    geometry = {"type": "rounded_rect" if radius else "rect", "fill": color(fill),
                **({"radius": radius} if radius else {})}
    layer = {"id": id_, "type": "shape", "shape": geometry, "size": [w, h],
             "position": [x, y], "opacity": opacity, "start_frame": start,
             "duration_frames": FRAMES, "screen_space": True}
    if motion:
        layer["animation"] = {"tracks": motion}
    return layer


def text(id_: str, label: str, x: float, y: float, w: float, h: float,
         size: float, fill: str = INK, font: str = FONT_BOLD,
         start: int = 0, motion: list[dict] | None = None,
         align: str = "left", max_size: float | None = None) -> dict:
    layer = {"id": id_, "type": "text", "text": label, "size": [w, h],
             "position": [x + w / 2, y + h / 2], "style": {"font": font, "font_size": size,
             "min_font_size": size, "max_font_size": max_size or size,
             "fit_mode": "shrink_only", "fill": fill},
             "start_frame": start, "duration_frames": FRAMES - start, "screen_space": True}
    if motion:
        layer["animation"] = {"tracks": motion}
    return layer


def image(id_: str, asset: str, x: float, y: float, w: float, h: float,
          motion: list[dict] | None = None, opacity: float = 1.0,
          start: int = 0, fit: str = "contain") -> dict:
    layer = {"id": id_, "type": "image", "asset": asset, "size": [w, h],
             "position": [x - w / 2, y - h / 2], "fit": fit, "opacity": opacity,
             "start_frame": start, "duration_frames": FRAMES, "screen_space": True}
    if motion:
        layer["animation"] = {"tracks": motion}
    return layer


def background(asset: str | None = None, fill: str = "#F7F7F5") -> list[dict]:
    if asset:
        return [image("paper", asset, 960, 540, WIDTH, HEIGHT, fit="cover")]
    return [{"id": "paper", "type": "color", "color": color(fill),
             "size": [WIDTH, HEIGHT], "start_frame": 0, "duration_frames": FRAMES,
             "screen_space": True}]


def write_plan(id_: str, layers: list[dict]) -> Path:
    PLANS.mkdir(parents=True, exist_ok=True)
    path = PLANS / f"{id_}.plan.json"
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": id_,
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": f"ChrononTemplate/out/oil_crisis_1973_animation_samples/{id_}.mp4",
                       "format": "mp4", "codec": "h264"}}
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    return path


def render(plan: Path, force: bool = False) -> Path:
    target = OUT / f"{plan.stem.removesuffix('.plan')}.mp4"
    if plan.stem.removesuffix(".plan") == "map_middle_east_oil_focus":
        # Keep the national geometry live: this renderer projects the checked-in
        # Natural Earth polygons anew on each frame before encoding the video.
        runtime_map = HERE.with_name("render_oil_crisis_map_runtime.py")
        subprocess.run(["python3", str(runtime_map)], cwd=ROOT, check=True)
        return target
    if not force and target.is_file() and target.stat().st_size > 100_000:
        return target
    command = [str(CLI), "render", "--plan", str(plan), "--assets-root", str(ROOT),
               "--backend", "vulkan", "--profile", "production",
               "--rate-control", "crf", "--crf", "19", "--preset", "medium",
               "--encoder-backend", "pipe", "--gpu-hot-path-mode", "auto",
               "--fps", "30", "-o", str(target)]
    subprocess.run(command, cwd=ROOT, check=True)
    return target


def make_noise_plates() -> dict[str, str]:
    import random
    import numpy as np
    random.seed(1973)
    paths = {}
    for key, base, grain, specks in [
        ("dark", (12, 14, 15), 11, 1200),
        ("paper", (248, 247, 242), 5, 380),
    ]:
        rng = np.random.default_rng(1973 if key == "dark" else 1974)
        noise = rng.integers(-grain, grain + 1, size=(HEIGHT, WIDTH, 1), dtype=np.int16)
        pixels = np.clip(np.asarray(base, dtype=np.int16)[None, None, :] + noise, 0, 255).astype(np.uint8)
        pix = Image.fromarray(np.broadcast_to(pixels, (HEIGHT, WIDTH, 3)).copy(), "RGB")
        d = ImageDraw.Draw(pix, "RGBA")
        for _ in range(specks):
            x, y = random.randrange(WIDTH), random.randrange(HEIGHT)
            r = random.choice((1, 1, 1, 2, 3))
            a = random.randrange(10, 60)
            d.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255, a))
        pix = pix.filter(ImageFilter.GaussianBlur(.18))
        path = ASSETS / f"{key}_grain.png"
        pix.save(path)
        paths[key] = f"ChrononTemplate/out/oil_crisis_1973_animation_samples/assets/{path.name}"
    return paths


def polygons(geometry: dict):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return [poly for poly in geometry["coordinates"]]
    return []


MAP_EXTENT = (20.0, 42.5, 20.0, 38.0)  # west, east, south, north


def map_project(lon: float, lat: float) -> tuple[float, float]:
    return 960.0 + (lon - 31.0) * 82.0, 535.0 - (lat - 29.0) * 65.0


def map_path_point(lon: float, lat: float) -> tuple[float, float]:
    x, y = map_project(lon, lat)
    return x - WIDTH/2, y - HEIGHT/2


def clip_country_ring(ring: list[list[float]]) -> list[tuple[float, float]]:
    west, east, south, north = MAP_EXTENT
    points = [(float(p[0]), float(p[1])) for p in ring]
    edges = ((0, west, True), (0, east, False), (1, south, True), (1, north, False))
    for axis, edge, greater in edges:
        if not points:
            break
        result = []
        inside = lambda p: p[axis] >= edge if greater else p[axis] <= edge
        previous = points[-1]
        for current in points:
            prev_in, cur_in = inside(previous), inside(current)
            if prev_in != cur_in:
                delta = current[axis] - previous[axis]
                t = 0.0 if abs(delta) < 1e-12 else (edge - previous[axis]) / delta
                cross = (previous[0] + t * (current[0]-previous[0]),
                         previous[1] + t * (current[1]-previous[1]))
                result.append(cross)
            if cur_in:
                result.append(current)
            previous = current
        points = result
    return points


def country_path_commands(feature: dict) -> list[dict]:
    # Vulkan native fill currently handles a single contour with 3–8 points.
    # Use the country's main polygon and simplify its outline while preserving
    # the geographic silhouette, so the fill is actually rendered at runtime.
    west, east, south, north = MAP_EXTENT
    candidates = []
    for polygon in polygons(feature["geometry"]):
        ring = [(float(p[0]), float(p[1])) for p in polygon[0]]
        if not ring:
            continue
        bounds = (min(p[0] for p in ring), max(p[0] for p in ring),
                  min(p[1] for p in ring), max(p[1] for p in ring))
        if bounds[1] < west or bounds[0] > east or bounds[3] < south or bounds[2] > north:
            continue
        candidates.append((abs(sum(ring[i][0]*ring[(i+1)%len(ring)][1] -
                                   ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))), ring))
    if not candidates:
        return []
    ring = max(candidates, key=lambda item: item[0])[1]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    stride = max(1, math.ceil(len(ring) / 800))
    ring = ring[::stride]
    if len(ring) > 8:
        # Sample vertices by perimeter distance for a stable, evenly distributed outline.
        lengths = [math.hypot(ring[(i+1)%len(ring)][0]-p[0], ring[(i+1)%len(ring)][1]-p[1])
                   for i,p in enumerate(ring)]
        total = sum(lengths)
        selected, cursor, edge, accumulated = [], 0.0, 0, 0.0
        for target in [total*i/8 for i in range(8)]:
            while edge < len(lengths)-1 and accumulated + lengths[edge] < target:
                accumulated += lengths[edge]
                edge += 1
            selected.append(ring[edge])
        ring = selected
    points = [map_path_point(lon, lat) for lon, lat in ring]
    if len(points) < 3:
        return []
    return ([{"type":"move_to","point":list(points[0])}] +
            [{"type":"line_to","point":list(p)} for p in points[1:]] + [{"type":"close"}])


def map_vector_layer(id_: str, commands: list[dict], fill: str, start: int) -> dict:
    return {"id": id_, "type": "shape", "shape": {"type": "path", "path": commands,
            "fill": color(fill), "stroke": {"color": "#FAF9F4", "width": 2.0}},
            "size": [WIDTH, HEIGHT], "position": [WIDTH/2, HEIGHT/2], "start_frame": start,
            "duration_frames": FRAMES-start, "screen_space": True,
            "animation": {"tracks": [track("opacity", [(0, 0), (8, 1), (FRAMES-start-1, 1)])]}}


def inside_screen_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for i, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(i + 1) % len(polygon)]
        if (ay > y) != (by > y) and x < (bx-ax) * (y-ay) / (by-ay+1e-12) + ax:
            inside = not inside
    return inside


def build_date_dark(plates: dict[str, str]) -> Path:
    layers = background(plates["dark"])
    # A thin red editorial bracket anchors the date like the reference frame.
    layers += [shape("bracket-horizontal", 455, 785, 880, 6, CORAL,
                     motion=[track("scale_x", [(0, .01), (48, 1), (149, 1)])]),
               shape("bracket-vertical", 895, 670, 6, 235, CORAL,
                     motion=[track("opacity", [(0, 0), (48, 1), (149, 1)])]),
               shape("date-stamp", 960, 540, 890, 170, CORAL, radius=2,
                     motion=[track("scale_x", [(0, .02), (17, 1.04), (25, 1), (149, 1)]),
                             track("opacity", [(0, 0), (12, 1), (149, 1)])]),
               text("date", "6 ottobre 1973", 515, 474, 890, 132, 104, "#FFF9EE",
                    FONT_DIDONE, motion=[track("opacity", [(0, 0), (22, 1), (149, 1)]),
                                         track("position_y", [(0, 20), (24, 0), (149, 0)])],
                    align="center")]
    return write_plan("date_oil_crisis_stamp", layers)


def build_map(base: str | None = None, selected: str | None = None) -> Path:
    # The countries remain native Chronon paths. GeoJSON is projected when the
    # plan is built, and place labels/markers use the same lon/lat transform.
    del base, selected
    layers = background(fill="#D1E2E7")
    graticule = []
    for lon in range(20, 43, 2):
        graticule.extend([{"type": "move_to", "point": list(map_path_point(lon, 20))},
                          {"type": "line_to", "point": list(map_path_point(lon, 38))}])
    for lat in range(20, 39, 2):
        graticule.extend([{"type": "move_to", "point": list(map_path_point(20, lat))},
                          {"type": "line_to", "point": list(map_path_point(42, lat))}])
    layers.append({"id": "map-graticule", "type": "shape",
                   "shape": {"type": "path", "path": graticule, "fill": [0, 0, 0, 0],
                             "stroke": {"color": "#BDD3D9", "width": 1.0}},
                   "size": [WIDTH, HEIGHT], "position": [WIDTH/2, HEIGHT/2], "start_frame": 0,
                   "duration_frames": FRAMES, "screen_space": True})

    geo = json.loads((TEMPLATE / "catalog/ne_50m_admin_0_countries.geojson").read_text())
    palette = {"Egypt": "#25897C", "Israel": "#D95258", "Palestine": "#D95258",
               "Jordan": "#6176D5", "Saudi Arabia": "#C89863", "Lebanon": "#D8D8D3",
               "Syria": "#D8D8D3", "Iraq": "#D8D8D3", "Sudan": "#D8D8D3", "Libya": "#D8D8D3"}
    draw_order = ["Libya", "Sudan", "Egypt", "Syria", "Lebanon", "Israel", "Palestine", "Jordan", "Saudi Arabia", "Iraq"]
    features = {f.get("properties", {}).get("ADMIN"): f for f in geo["features"]}
    for order, name in enumerate(draw_order):
        feature = features.get(name)
        if feature:
            commands = country_path_commands(feature)
            if commands:
                layers.append(map_vector_layer(f"country-{name.lower().replace(' ', '-')}", commands,
                                                palette[name], 8 + order * 3))

    # Highlight Sinai inside Egypt with an accurate geographic outline and
    # hatch strokes clipped to the region; no baked map image is used.
    sinai_geo = [(32.45, 31.08), (34.35, 31.15), (34.82, 29.75),
                 (34.55, 28.65), (33.40, 27.85), (32.45, 29.30)]
    sinai = [map_project(lon, lat) for lon, lat in sinai_geo]
    sinai_local = [(x-WIDTH/2,y-HEIGHT/2) for x,y in sinai]
    sinai_commands = [{"type": "move_to", "point": list(sinai_local[0])}]
    sinai_commands.extend({"type": "line_to", "point": list(p)} for p in sinai_local[1:])
    sinai_commands.append({"type": "close"})
    layers.append({"id": "sinai-boundary", "type": "shape",
                   "shape": {"type": "path", "path": sinai_commands, "fill": [0, 0, 0, 0],
                             "stroke": {"color": "#174D47", "width": 3.0}},
                   "size": [WIDTH, HEIGHT], "position": [WIDTH/2, HEIGHT/2], "start_frame": 25,
                   "duration_frames": FRAMES-25, "screen_space": True,
                   "animation": {"tracks": [track("opacity", [(0, 0), (22, 1), (FRAMES-26, 1)])]}})
    hatch = []
    min_x, max_x = min(p[0] for p in sinai), max(p[0] for p in sinai)
    min_y, max_y = min(p[1] for p in sinai), max(p[1] for p in sinai)
    for x0 in range(round(min_x-200), round(max_x+200), 22):
        run = []
        for y in range(round(min_y), round(max_y)+1, 5):
            point = (x0 + (y-round(min_y))*.55, float(y))
            if inside_screen_polygon(point, sinai):
                run.append(point)
            elif len(run) > 1:
                hatch.extend([{"type": "move_to", "point": [run[0][0]-WIDTH/2,run[0][1]-HEIGHT/2]},
                              {"type": "line_to", "point": [run[-1][0]-WIDTH/2,run[-1][1]-HEIGHT/2]}]); run = []
        if len(run) > 1:
            hatch.extend([{"type": "move_to", "point": [run[0][0]-WIDTH/2,run[0][1]-HEIGHT/2]},
                          {"type": "line_to", "point": [run[-1][0]-WIDTH/2,run[-1][1]-HEIGHT/2]}])
    layers.append({"id": "sinai-hatch", "type": "shape",
                   "shape": {"type": "path", "path": hatch, "fill": [0, 0, 0, 0],
                             "stroke": {"color": "#174D47", "width": 2.0}},
                   "size": [WIDTH, HEIGHT], "position": [WIDTH/2, HEIGHT/2], "start_frame": 34,
                   "duration_frames": FRAMES-34, "screen_space": True,
                   "animation": {"tracks": [track("opacity", [(0, 0), (18, 1), (FRAMES-35, 1)])]}})

    # Region labels and the locator dots all share the same geographic projection.
    for id_, label, lon, lat, w, h, size, fill, start in [
        ("egypt-label", "Egitto", 28.2, 27.4, 390, 96, 68, "#F9F7F1", 16),
        ("israel-label", "Israele", 34.9, 32.55, 260, 66, 43, "#161616", 28),
        ("sinai-label", "Deserto del Sinai", 33.55, 27.45, 400, 52, 30, "#101819", 50),
    ]:
        x, y = map_project(lon, lat)
        layers.append(text(id_, label, x-w/2, y-h/2, w, h, size, fill,
                           FONT_BOLD if id_ != "sinai-label" else FONT_REGULAR,
                           start=start, motion=[track("opacity", [(0, 0), (12, 1), (FRAMES-start-1, 1)])]))
    places = [("cairo", "Il Cairo", 31.2357, 30.0444, -130, -32),
              ("suez", "Suez", 32.55, 29.97, 32, 28),
              ("gaza", "Gaza", 34.4668, 31.5017, 40, -25)]
    for index, (id_, label, lon, lat, dx, dy) in enumerate(places):
        x, y = map_project(lon, lat)
        start = 54 + index * 8
        layers.append({"id": f"{id_}-marker", "type": "shape",
                       "shape": {"type": "ellipse", "fill": color(CORAL),
                                 "stroke": {"color": "#FFFDF7", "width": 3}},
                       "size": [18, 18], "position": [x, y], "start_frame": start,
                       "duration_frames": FRAMES-start, "screen_space": True,
                       "animation": {"tracks": [track("scale", [(0, .1), (10, 1)]),
                                                   track("opacity", [(0, 0), (8, 1), (FRAMES-start-1, 1)])]}})
        w, h = (140, 38)
        tag = text(f"{id_}-label", label, x+dx-w/2, y+dy-h/2, w, h, 24,
                   "#151515", FONT_BOLD, start=start+5,
                   motion=[track("opacity", [(0, 0), (10, 1), (FRAMES-start-6, 1)])])
        tag["style"]["background"] = {"color": "#F7F5EF", "opacity": .92,
                                        "radius": 5, "padding": [7, 4]}
        layers.append(tag)
    layers.extend([
        shape("map-accent-rule", 105, 165, 150, 8, CORAL,
              motion=[track("scale_x", [(0, .01), (48, 1), (149, 1)])]),
        text("map-heading", "IL FRONTE DEL SINAI", 105, 90, 820, 70, 38, "#171B1C",
             FONT_BOLD, motion=[track("opacity", [(0, 0), (32, 1), (149, 1)])]),
    ])
    return write_plan("map_middle_east_oil_focus", layers)


def build_highlighter(plates: dict[str, str]) -> Path:
    layers = background(plates["paper"])
    bold = ImageFont.truetype(ROOT / FONT_BOLD, 66)
    first = "Nell’ultimo anno,"
    highlighted = "la Germania ha perso"
    prefix_w = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(first + " ", font=bold)
    high_w = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(highlighted, font=bold)
    x, y = 54, 170
    total_w = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(first + " " + highlighted, font=bold)
    highlight_x = WIDTH / 2 - total_w / 2 + prefix_w + high_w / 2
    layers += [shape("yellow-line-1", highlight_x, y + 54, high_w + 20, 76, YELLOW,
                     radius=4, motion=[track("scale_x", [(0, .001), (31, 1), (149, 1)])]),
               shape("yellow-line-2", 54 + 690, 292 + 54, 1400, 78, YELLOW,
                     radius=4, motion=[track("scale_x", [(0, .001), (43, 1), (149, 1)])]),
               text("statement-line-1", first + " " + highlighted, x, y, 1920-x*2, 92, 66,
                    motion=[track("opacity", [(0, 0), (12, 1), (149, 1)])]),
               text("statement-line-2", "144mila posti di lavoro", 54, 292, 1490, 100, 72,
                    motion=[track("opacity", [(0, 0), (27, 1), (149, 1)])]),
               text("statement-line-3", "nel settore industriale.", 54, 412, 1500, 100, 72,
                    motion=[track("opacity", [(0, 0), (39, 1), (149, 1)])]),
               text("source", "GERMANIA · INDUSTRIA", 58, 910, 760, 44, 24, "#777771", FONT_REGULAR,
                    motion=[track("opacity", [(0, 0), (60, .8), (149, .8)])])]
    return write_plan("phrase_yellow_highlighter_sweep", layers)


DATA_IDS = ["data_histogram_stagger_up", "data_histogram_wave", "data_histogram_center_out",
            "data_bar_compare_reveal", "data_line_trace", "data_peak_callout", "data_counter_roll",
            "data_grid_assemble", "data_area_fill_rise", "data_chart_focus_pulse"]
VALUES = [81, 79, 78, 77, 76, 74, 71, 67]


def make_data_art() -> str:
    img = Image.new("RGBA", (1500, 450), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pts = [(80 + i * 185, 365 - v * 4.4) for i, v in enumerate(VALUES)]
    d.polygon([(80, 390), *pts, (1400, 390)], fill=(242, 229, 0, 100))
    d.line(pts, fill=(24, 29, 32, 255), width=7, joint="curve")
    for x, y in pts:
        d.ellipse((x-9, y-9, x+9, y+9), fill=(24, 29, 32, 255))
    path = ASSETS / "data_area_2024.png"; img.save(path)
    return f"ChrononTemplate/out/oil_crisis_1973_animation_samples/assets/{path.name}"


def build_data_chart(id_: str, area_asset: str) -> Path:
    layers = background(fill="#F8F8F5")
    # The chart area sits below a large editorial headline and a crisp statistic.
    layers += [text("headline", "L’OCCUPAZIONE INDUSTRIALE TEDESCA", 120, 82, 1600, 70, 38,
                    fill="#323635", font=FONT_REGULAR),
               text("main-stat", "−144.000", 110, 164, 720, 156, 130, fill=INK),
               text("stat-unit", "POSTI DI LAVORO IN UN ANNO", 125, 305, 950, 50, 29,
                    fill="#696D6A", font=FONT_REGULAR),
               shape("stat-accent", 120, 365, 330, 7, CORAL,
                     motion=[track("scale_x", [(0, .01), (36, 1), (149, 1)])])]
    base_y, left, gap, bw = 835, 280, 148, 82
    maxh = 360
    # Light horizontal rules keep the charts data-first and match the reference grid.
    for j, y in enumerate((475, 565, 655, 745, 835)):
        layers.append(shape(f"grid-{j}", 960, y, 1320, 2, "#DDDEDA", opacity=.9,
                            motion=[track("opacity", [(0, 0), (20 + j*4, .9), (149, .9)])]))
    peak = 7
    for i, val in enumerate(VALUES):
        h = maxh * val / max(VALUES)
        x = left + i * gap
        delay = i * 7
        if id_ == "data_histogram_center_out":
            delay = abs(i - 3.5) * 11
        start_scale = .01 if id_ in ("data_histogram_center_out", "data_bar_compare_reveal") else .025
        bar_tracks = [track("scale_y", [(0, start_scale), (24 + int(delay), .86),
                                         (45 + int(delay), 1), (149, 1)])]
        if id_ == "data_histogram_wave":
            bar_tracks = [track("scale_y", [(0, .02), (21+int(delay), 1.08),
                                             (33+int(delay), .91), (47+int(delay), 1), (149, 1)])]
        if id_ == "data_bar_compare_reveal":
            bar_tracks = [track("scale_x", [(0, .01), (30 + int(delay), 1), (149, 1)])]
        if id_ in ("data_peak_callout", "data_chart_focus_pulse") and i == peak:
            bar_tracks = [track("scale_y", [(0, 1), (18, 1.07), (34, 1), (55, 1.05), (72, 1), (149, 1)])]
        fill = CORAL if i == peak and id_ in ("data_peak_callout", "data_chart_focus_pulse") else "#F2E500"
        # Center-based scaling grows the columns in place; chart baseline remains a clean shared ruler.
        layers.append(shape(f"bar-{i}", x, base_y - h/2, bw, h, fill, opacity=1,
                            radius=5, motion=bar_tracks))
        layers.append(text(f"year-{i}", str(2017+i), x-45, 862, 100, 42, 22,
                           fill="#666A67", font=FONT_REGULAR,
                           motion=[track("opacity", [(0, 0), (50+int(delay), .9), (149, .9)])], align="center"))
    # Meaningful differences between the ten named recipes.
    if id_ == "data_line_trace":
        layers.append(image("trace", area_asset, 960, 635, 1500, 450,
                            motion=[track("scale_x", [(0, .001), (80, 1), (149, 1)]),
                                    track("opacity", [(0, 0), (42, 1), (149, 1)])]))
    elif id_ == "data_area_fill_rise":
        layers.append(image("area", area_asset, 960, 635, 1500, 450,
                            motion=[track("scale_y", [(0, .01), (68, 1), (149, 1)]),
                                    track("opacity", [(0, 0), (48, 1), (149, 1)])]))
    if id_ == "data_counter_roll":
        layers.append(text("counter-label", "DAL 2017 AL 2024", 1170, 190, 520, 70, 36,
                           fill=CORAL, font=FONT_BOLD,
                           motion=[track("opacity", [(0, 0), (24, 1), (149, 1)]),
                                   track("position_y", [(0, 28), (24, 0), (149, 0)])], align="right"))
    if id_ == "data_peak_callout":
        layers.append(shape("peak-pill", 1510, 445, 270, 68, CORAL, radius=28,
                            motion=[track("scale", [(0, .7), (28, 1.08), (39, 1), (149, 1)]),
                                    track("opacity", [(0, 0), (26, 1), (149, 1)])]))
        layers.append(text("peak-pill-label", "−3,1%", 1380, 420, 260, 58, 32, "#FFFFFF",
                           start=24, align="center", motion=[track("opacity", [(0, 0), (10, 1), (149, 1)])]))
    if id_ == "data_histogram_center_out":
        layers.append(text("chart-label", "OGNI COLONNA = 18MILA LAVORATORI", 280, 424, 1000, 48, 25,
                           fill="#777A77", font=FONT_REGULAR,
                           motion=[track("opacity", [(0, 0), (48, 1), (149, 1)])]))
    return write_plan(id_, layers)


def prep_photo() -> str:
    source = Image.open("/tmp/oil_ref.png").convert("RGB")
    photo = source.crop((204, 99, 1612, 912)).resize((1300, 730), Image.Resampling.LANCZOS)
    alpha = Image.new("L", photo.size, 0)
    ImageDraw.Draw(alpha).rounded_rectangle((0, 0, photo.width-1, photo.height-1), radius=15, fill=255)
    photo.putalpha(alpha)
    path = ASSETS / "refinery_rounded.png"; photo.save(path)
    return f"ChrononTemplate/out/oil_crisis_1973_animation_samples/assets/{path.name}"


def build_image_accent(plates: dict[str, str], photo: str) -> Path:
    plate = Image.open(ASSETS / "dark_grain.png").convert("RGB")
    photo_image = Image.open(ASSETS / "refinery_rounded.png").convert("RGBA")
    card_x, card_y = 300, 175
    accent = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(accent).rounded_rectangle((card_x + 22, card_y, card_x + 1322, card_y + 730),
                                               radius=18, fill=CORAL)
    plate_rgba = plate.convert("RGBA")
    plate_rgba.alpha_composite(accent)
    plate_rgba.alpha_composite(photo_image, (card_x, card_y))
    path = ASSETS / "refinery_one_sided_accent.png"
    plate_rgba.convert("RGB").save(path)
    asset = f"ChrononTemplate/out/oil_crisis_1973_animation_samples/assets/{path.name}"
    layers = [image("one-sided-rounded-card", asset, 960, 540, WIDTH, HEIGHT,
                    motion=[track("opacity", [(0, 0), (18, 1), (149, 1)]),
                            track("scale", [(0, .97), (25, 1), (149, 1)])], fit="contain")]
    return write_plan("image_one_sided_rounded_accent", layers)


def main() -> None:
    if not CLI.is_file():
        raise SystemExit(f"missing Chronon3D CLI: {CLI}")
    ASSETS.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    plates = make_noise_plates()
    area = make_data_art()
    photo = prep_photo()
    plans = [build_date_dark(plates), build_map(), build_highlighter(plates)]
    plans.extend(build_data_chart(id_, area) for id_ in DATA_IDS)
    plans.append(build_image_accent(plates, photo))
    manifest = []
    for index, plan in enumerate(plans, 1):
        print(f"[{index:02d}/{len(plans):02d}] Vulkan GPU render: {plan.stem}", flush=True)
        output = render(plan, force=plan.stem == "map_middle_east_oil_focus")
        manifest.append({"id": output.stem, "file": output.name, "resolution": "1920x1080",
                         "fps": 30, "duration_seconds": 5, "renderer": "Vulkan", "encoder": "H.264"})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Completed {len(manifest)} 5-second samples in {OUT}", flush=True)


if __name__ == "__main__":
    main()
