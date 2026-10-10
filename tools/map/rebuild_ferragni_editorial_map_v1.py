#!/usr/bin/env python3
"""Rebuild the Ferragni Lombardy map scene from accurate topo tiles and borders."""
from __future__ import annotations

import json
import math
import shutil
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
CATALOG = ROOT / "catalog"
SCENE = CATALOG / "vintage_documentary_map_italy"
ASSETS = SCENE / "assets"
OUT = SCENE / "out"
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150
ZOOM = 9
OVERVIEW = (5.3, 13.62, 43.4, 46.7)  # west, east, south, north
DETAIL = (7.5, 12.3, 44.2, 46.1)
MILANO = (9.1900, 45.4642)
CREMONA = (10.0227, 45.1332)
INK = "#211B16"
PAPER = "#F3EBDD"
MUTED = "#D8CBB4"
RED = "#9D2E22"
FONT = "ChrononTemplate/assets/fonts/Inter-Bold.ttf"


def world_x(lon: float) -> float:
    return (lon + 180.0) / 360.0 * 256 * (2**ZOOM)


def world_y(lat: float) -> float:
    rad = math.radians(lat)
    return (1.0 - math.asinh(math.tan(rad)) / math.pi) / 2.0 * 256 * (2**ZOOM)


def track(prop: str, points: list[tuple[int, float]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in points]}


def download(url: str, path: Path) -> bytes:
    if path.exists() and path.stat().st_size:
        return path.read_bytes()
    request = urllib.request.Request(url, headers={
        "User-Agent": "ChrononTemplate/1.0 (editorial map reconstruction; OpenTopoMap attribution included)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def load_tiles() -> tuple[Image.Image, tuple[int, int]]:
    tile_cache = Path("/tmp/chronon_ferragni_opentopo_z9")
    x0 = math.floor(world_x(OVERVIEW[0]) / 256)
    x1 = math.floor((world_x(OVERVIEW[1]) - 0.001) / 256)
    y0 = math.floor(world_y(OVERVIEW[3]) / 256)
    y1 = math.floor((world_y(OVERVIEW[2]) - 0.001) / 256)
    mosaic = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            path = tile_cache / f"{x}_{y}.png"
            url = f"https://tile.opentopomap.org/{ZOOM}/{x}/{y}.png"
            raw = download(url, path)
            from io import BytesIO
            mosaic.paste(Image.open(BytesIO(raw)).convert("RGB"), ((x-x0)*256, (y-y0)*256))
            time.sleep(0.08)
    return mosaic, (x0, y0)


def raw_crop(mosaic: Image.Image, tile_origin: tuple[int, int], bounds: tuple[float, float, float, float]) -> Image.Image:
    west, east, south, north = bounds
    ox, oy = tile_origin
    crop = (round(world_x(west) - ox*256), round(world_y(north) - oy*256),
            round(world_x(east) - ox*256), round(world_y(south) - oy*256))
    return mosaic.crop(crop)


def antique_grade(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    # The tile source keeps precise roads, contours, and labels; a restrained
    # warm monochrome grade brings it into the supplied editorial palette.
    low = np.array([50, 42, 34], dtype=np.float32)
    high = np.array([245, 235, 216], dtype=np.float32)
    normalized = np.clip((gray.astype(np.float32) - 42.0) / 200.0, 0.0, 1.0)[..., None]
    result = low + (high - low) * normalized
    blue_water = (rgb[..., 2].astype(np.int16) - rgb[..., 0].astype(np.int16) > 18) & (rgb[..., 2] > 145)
    water = np.array([66, 56, 45], dtype=np.float32)
    result[blue_water] = result[blue_water] * .25 + water * .75
    result = np.clip(result, 0, 255).astype(np.uint8)
    # Light local contrast retains the fine contour detail after final scaling.
    graded = Image.fromarray(result, "RGB")
    graded = ImageEnhance.Contrast(graded).enhance(1.08)
    return ImageEnhance.Color(graded).enhance(.86)


def crop_plate(mosaic: Image.Image, origin: tuple[int, int], bounds: tuple[float, float, float, float], path: Path) -> None:
    plate = antique_grade(raw_crop(mosaic, origin, bounds))
    plate = ImageOps.fit(plate, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    # A fine paper grain softens the raster tiles without obscuring cartography.
    arr = np.asarray(plate, dtype=np.float32)
    rng = np.random.default_rng(20261010)
    grain = rng.normal(0.0, 1.15, (HEIGHT, WIDTH, 1)).astype(np.float32)
    plate = Image.fromarray(np.clip(arr + grain, 0, 255).astype(np.uint8), "RGB")
    plate.save(path, optimize=True)


def point_on_map(lon: float, lat: float, bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    west, east, south, north = bounds
    # The source is fitted with a centered crop to 16:9. Both authored bounds
    # already match that projected ratio, so this remains an affine mapping.
    return ((world_x(lon)-world_x(west)) / (world_x(east)-world_x(west)) * WIDTH,
            (world_y(lat)-world_y(north)) / (world_y(south)-world_y(north)) * HEIGHT)


def province_overlay(path: Path) -> None:
    geo_path = Path("/tmp/geoBoundaries-ITA-ADM3_simplified.geojson")
    if not geo_path.exists():
        metadata = json.loads(urllib.request.urlopen(
            "https://www.geoboundaries.org/api/current/gbOpen/ITA/ADM3/", timeout=30).read())
        request = urllib.request.Request(metadata["simplifiedGeometryGeoJSON"], headers={
            "User-Agent": "ChrononTemplate/1.0 (editorial map reconstruction; geoBoundaries attribution included)"})
        geo_path.write_bytes(urllib.request.urlopen(request, timeout=60).read())
    collection = json.loads(geo_path.read_text())
    feature = next(f for f in collection["features"] if f["properties"].get("shapeName") == "Cremona")
    geometry = feature["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    west, east, south, north = DETAIL

    def project(point: list[float]) -> tuple[float, float]:
        return ((world_x(point[0])-world_x(west)) / (world_x(east)-world_x(west)) * WIDTH,
                (world_y(point[1])-world_y(north)) / (world_y(south)-world_y(north)) * HEIGHT)

    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_edge = ImageDraw.Draw(Image.new("RGBA", (WIDTH, HEIGHT)))
    rings: list[list[tuple[float, float]]] = []
    for polygon in polygons:
        outer = [project(pt) for pt in polygon[0]]
        if max(x for x, _ in outer) < 0 or min(x for x, _ in outer) > WIDTH or max(y for _, y in outer) < 0 or min(y for _, y in outer) > HEIGHT:
            continue
        draw_mask.polygon(outer, fill=255)
        rings.append(outer)
        for hole in polygon[1:]:
            draw_mask.polygon([project(pt) for pt in hole], fill=0)
    tint = Image.new("RGBA", (WIDTH, HEIGHT), (150, 38, 27, 255))
    tint.putalpha(Image.eval(mask, lambda value: value * 74 // 255))
    hatch = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    hatch_draw = ImageDraw.Draw(hatch)
    for x in range(-HEIGHT, WIDTH + HEIGHT, 20):
        hatch_draw.line((x, HEIGHT, x+HEIGHT, 0), fill=(151, 43, 31, 190), width=3)
    hatch.putalpha(ImageChops_multiply(hatch.getchannel("A"), mask))
    edges = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edges)
    for ring in rings:
        edge_draw.line(ring + [ring[0]], fill=(139, 35, 25, 245), width=5, joint="curve")
    result = Image.alpha_composite(tint, hatch)
    result = Image.alpha_composite(result, edges)
    result.save(path, optimize=True)


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    # Small local helper avoids carrying RGB channels through a mask operation.
    from PIL import ImageChops
    return ImageChops.multiply(a, b)


def full_canvas_overlay(path: Path, kind: str) -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if kind == "map_wash":
        for y in range(HEIGHT):
            alpha = round(24 + 30 * (y / HEIGHT) ** 2)
            draw.line((0, y, WIDTH, y), fill=(35, 27, 19, alpha))
        for y in range(535, HEIGHT):
            t = (y-535)/(HEIGHT-535)
            alpha = round(205 * min(1.0, t/.55))
            draw.line((0, y, WIDTH, y), fill=(24, 19, 15, alpha))
        # Soft vignette around the outside edge.
        vignette = Image.new("L", (WIDTH, HEIGHT), 0)
        px = vignette.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                edge = min(x, WIDTH-1-x, y, HEIGHT-1-y)
                if edge < 170:
                    px[x, y] = round(42 * (1-edge/170) ** 1.8)
        dark = Image.new("RGBA", (WIDTH, HEIGHT), (32, 23, 16, 0))
        dark.putalpha(vignette)
        image = Image.alpha_composite(image, dark)
        # Integrated timeline guides avoid allocating another full-screen GPU image.
        guide = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        guide_draw = ImageDraw.Draw(guide)
        guide_draw.line((140, 850, 1780, 850), fill=(229, 218, 195, 205), width=2)
        for year in range(2006, 2017):
            x = 140 + (year-2006)*164
            focus = year == 2009
            guide_draw.line((x, 840 if focus else 845, x, 880 if focus else 861),
                            fill=(164, 55, 41, 255) if focus else (211, 196, 171, 190),
                            width=4 if focus else 2)
        image = Image.alpha_composite(image, guide)
    elif kind == "timeline":
        # A transparent ink fade anchors the final timeline while preserving the map.
        for y in range(520, HEIGHT):
            t = (y-520)/(HEIGHT-520)
            alpha = round(220 * min(1.0, t/.28))
            draw.line((0, y, WIDTH, y), fill=(31, 25, 19, alpha))
        draw.line((140, 850, 1780, 850), fill=(229, 218, 195, 205), width=2)
        for year in range(2006, 2017):
            x = 140 + (year-2006)*164
            focus = year == 2009
            draw.line((x, 840 if focus else 845, x, 880 if focus else 861),
                      fill=(164, 55, 41, 255) if focus else (211, 196, 171, 190), width=4 if focus else 2)
    image.save(path, optimize=True)


def city_banner(path: Path, label: str, width: int) -> None:
    from PIL import ImageFont

    image = Image.new("RGBA", (width, 98), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((7, 7, width-8, 88), radius=3, fill=(157, 46, 34, 246),
                           outline=(241, 230, 210, 220), width=2)
    font = ImageFont.truetype(str(WORKSPACE / FONT), 38)
    box = draw.textbbox((0, 0), label, font=font, stroke_width=0)
    x = (width - (box[2]-box[0])) / 2
    y = (98 - (box[3]-box[1])) / 2 - box[1]
    draw.text((x, y), label, font=font, fill=(248, 239, 221, 255))
    image.save(path, optimize=True)


def image_layer(id: str, asset: str, size: tuple[int, int], start: int, duration: int,
                position: tuple[float, float] = (0, 0), animation: list[dict] | None = None,
                screen_space: bool = False) -> dict:
    layer = {"id": id, "type": "image", "asset": asset, "size": list(size),
             "position": list(position), "fit": "contain", "start_frame": start,
             "duration_frames": duration}
    if screen_space:
        layer["screen_space"] = True
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def text_layer(id: str, value: str, position: tuple[float, float], size: tuple[int, int],
               font_size: int, start: int, duration: int,
               animation: list[dict] | None = None, fill: str = PAPER,
               stroke: str = INK, stroke_width: int = 3, font: str = FONT) -> dict:
    layer = {"id": id, "type": "text", "text": value, "size": list(size),
             "position": list(position), "start_frame": start, "duration_frames": duration,
             "style": {"font": font, "font_size": font_size, "min_font_size": font_size,
                       "max_font_size": font_size, "fit_mode": "shrink_only", "fill": fill,
                       "stroke": {"color": stroke, "width": stroke_width}}}
    if animation:
        layer["animation"] = {"tracks": animation}
    return layer


def add_map_city(layers: list[dict], city: str, lonlat: tuple[float, float], bounds: tuple[float, float, float, float],
                 tag_asset: str, start: int, duration: int, label: str | None = None,
                 fade_at: int | None = None) -> None:
    x, y = point_on_map(*lonlat, bounds)
    pin_size = (78, 112)
    pin_x, pin_y = x, y - 60
    end = duration - 1
    opacity_keys = [(0, 0), (8, 1)]
    if fade_at is not None:
        opacity_keys.extend([(fade_at, 1), (end, 0)])
    else:
        opacity_keys.append((end, 1))
    pin_anim = [track("position_y", [(0, 65), (13, -7), (20, 0)]),
                track("scale", [(0, .55), (13, 1.12), (21, 1)]),
                track("opacity", opacity_keys)]
    # Image positions are centered relative to the 1920x1080 screen-space canvas.
    layer_key = f"{city.lower()}_{start}"
    layers.append(image_layer(f"{layer_key}_pin", "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/pin_marker_red.png",
                              pin_size, start, duration, (x-WIDTH/2, HEIGHT/2-pin_y), pin_anim, True))
    plaque_w, plaque_h = (240, 78) if city == "MILANO" else (280, 78)
    plaque_x, plaque_y = x + plaque_w/2 + 28, y - 78
    label_dur = min(duration, 150-start)
    label_opacity = [(0, 0), (10, 1)]
    if fade_at is not None:
        label_opacity.extend([(max(10, fade_at-10), 1), (label_dur-1, 0)])
    else:
        label_opacity.append((label_dur-1, 1))
    tag_anim = [track("position_x", [(0, -55), (15, 0)]), track("opacity", label_opacity)]
    layers.append(image_layer(f"{layer_key}_tag", tag_asset, (plaque_w, plaque_h), start+5,
                              label_dur-5, (plaque_x-WIDTH/2, HEIGHT/2-plaque_y), tag_anim, True))


def build_plan() -> dict:
    ASSETS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    mosaic, origin = load_tiles()
    crop_plate(mosaic, origin, OVERVIEW, ASSETS / "opentopo_north_italy_overview.png")
    crop_plate(mosaic, origin, DETAIL, ASSETS / "opentopo_lombardy_detail.png")
    shutil.copyfile(ASSETS / "opentopo_lombardy_detail.png", CATALOG / "maps/white_claude_map.png")
    province_overlay(ASSETS / "cremona_province_accurate.png")
    full_canvas_overlay(ASSETS / "map_editorial_wash.png", "map_wash")
    full_canvas_overlay(ASSETS / "timeline_ink_panel.png", "timeline")
    city_banner(ASSETS / "banner_milano.png", "MILANO", 302)
    city_banner(ASSETS / "banner_cremona.png", "CREMONA", 341)

    layers: list[dict] = []
    layers.append(image_layer("map_overview", "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/opentopo_north_italy_overview.png",
                              (WIDTH, HEIGHT), 0, 78, animation=[track("scale", [(0, 1.02), (35, 1), (60, 1.02), (77, 1.03)]),
                                                                  track("position_x", [(0, 0), (35, -4), (60, 4), (77, 8)]),
                                                                  track("opacity", [(0, 1), (60, 1), (77, 0)])], screen_space=True))
    layers.append(image_layer("map_detail", "ChrononTemplate/catalog/maps/white_claude_map.png",
                              (WIDTH, HEIGHT), 58, 92, animation=[track("scale", [(0, 1.04), (26, 1), (91, 1.01)]),
                                                                  track("opacity", [(0, 0), (18, 1), (91, 1)])], screen_space=True))
    layers.append(image_layer("map_editorial_wash", "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/map_editorial_wash.png",
                              (WIDTH, HEIGHT), 0, FRAMES, animation=[track("opacity", [(0, .12), (100, .12), (120, .95), (149, .95)])], screen_space=True))

    add_map_city(layers, "MILANO", MILANO, OVERVIEW,
                 "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/banner_milano.png", 8, 68,
                 fade_at=53)
    # Large economic figure arrives over the southern map negative space.
    layers.append(text_layer("stat_75", "75", (342, 760), (400, 190), 170, 30, 58,
        [track("position_y", [(0, 80), (20, 0)]), track("opacity", [(0, 0), (12, 1), (42, 1), (58, 0)])],
        stroke_width=4))
    layers.append(text_layer("stat_milioni", "MILIONI", (752, 778), (700, 125), 92, 36, 54,
        [track("position_x", [(0, -65), (23, 0)]), track("opacity", [(0, 0), (14, 1), (37, 1), (54, 0)])],
        stroke_width=3))
    layers.append(text_layer("stat_di_euro", "DI EURO", (384, 900), (420, 62), 43, 48, 40,
        [track("position_y", [(0, 36), (16, 0)]), track("opacity", [(0, 0), (14, .96), (28, .96), (40, 0)])],
        fill="#E3D6BF", stroke_width=2))

    # The map crossfades to a closer, still geographically accurate view of Lombardy.
    layers.append(image_layer("cremona_province", "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/cremona_province_accurate.png",
                              (WIDTH, HEIGHT), 69, 81, animation=[track("scale", [(0, 1.12), (18, 1), (80, 1)]),
                                                                  track("opacity", [(0, 0), (18, .96), (62, .96), (80, 0)])], screen_space=True))
    add_map_city(layers, "MILANO", MILANO, DETAIL,
                 "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/banner_milano.png", 67, 37,
                 fade_at=24)
    add_map_city(layers, "CREMONA", CREMONA, DETAIL,
                 "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/banner_cremona.png", 76, 74,
                 fade_at=52)
    # The Polaroid photograph arrives after the Cremona marker and holds into the closing timeline.
    layers.append(image_layer("torrazzo_polaroid", "ChrononTemplate/catalog/vintage_documentary_map_italy/assets/photo_card_torrazzo.png",
                              (345, 450), 85, 65, (600, -165),
                              [track("position_y", [(0, -85), (20, 0)]),
                               track("scale", [(0, .68), (18, 1.04), (25, 1)]),
                               track("opacity", [(0, 0), (12, 1), (44, 1), (64, 0)])], True))
    layers.append(text_layer("photo_caption", "IL TORRAZZO  ·  CREMONA", (1510, 676), (390, 34), 20, 98, 52,
        [track("opacity", [(0, 0), (10, .95), (30, .95), (51, 0)])], fill="#EFE5D1", stroke_width=2))

    # Final chronological beat, designed as a real text/timeline composition.
    layers.append(text_layer("timeline_date", "12 OTTOBRE", (492, 634), (620, 60), 46, 101, 49,
        [track("position_y", [(0, 34), (13, 0)]), track("opacity", [(0, 0), (10, 1)])], stroke_width=3))
    layers.append(text_layer("timeline_year", "2009", (490, 742), (700, 190), 185, 106, 44,
        [track("scale", [(0, .78), (17, 1)]), track("opacity", [(0, 0), (11, 1)])], stroke_width=5))
    layers.append(text_layer("timeline_name", "CHIARA FERRAGNI", (1320, 802), (780, 65), 44, 122, 28,
        [track("position_y", [(0, 26), (13, 0)]), track("opacity", [(0, 0), (10, 1)])], stroke_width=3))
    for year in range(2006, 2017):
        x = 140 + (year-2006)*164
        is_focus = year == 2009
        layers.append(text_layer(f"timeline_year_{year}", str(year), (x, 904), (90, 34), 24 if is_focus else 21,
            111, 39, [track("opacity", [(0, 0), (10, 1)])],
            fill="#E7DCC8" if is_focus else "#C8B99E", stroke_width=2))
    layers.append(text_layer("map_credit", "© OpenStreetMap · OpenTopoMap  |  Confini ISTAT 2023 / geoBoundaries",
        (960, 1050), (1120, 26), 14, 0, FRAMES,
        [track("opacity", [(0, .74), (149, .74)])], fill="#D7C8AE", stroke_width=1))

    return {"schema": "chronon.render-plan.v2", "version": 2,
            "job_id": "ferragni_north_italy_editorial_map_5s",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": "vintage_documentary_map_italy.mp4", "format": "mp4", "codec": "h264"}}


def main() -> None:
    plan = build_plan()
    plan_path = SCENE / "vintage_documentary_map_italy.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {plan_path} with {len(plan['layers'])} animated layers")


if __name__ == "__main__":
    main()
