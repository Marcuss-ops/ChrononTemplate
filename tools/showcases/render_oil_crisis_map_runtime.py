#!/usr/bin/env python3
"""Render the Sinai map from Natural Earth country geometry on every frame."""
from __future__ import annotations

import json
import math
import io
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = ROOT / "ChrononTemplate/out/oil_crisis_1973_animation_samples"
GEOJSON = ROOT / "ChrononTemplate/catalog/ne_50m_admin_0_countries.geojson"
TILE_CACHE = ROOT / "Chronon3d/assets/maps/cache/pyramid/esri_topo"
FONT_BOLD = ROOT / "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_REGULAR = ROOT / "Chronon3d/assets/fonts/Inter-Regular.ttf"
FONT_DIDONE = ROOT / "Chronon3d/assets/fonts/Didot-Italic.ttf"
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150

PAPER = (246, 245, 239)
INK = (22, 31, 34)
MUTED = (103, 113, 111)
WATER = (213, 230, 231)
LAND = (230, 228, 219)
BORDER = (250, 249, 243)
CORAL = (216, 78, 65)
PALETTE = {
    "Egypt": (214, 160, 66),
    "Israel": (221, 83, 74),
    "Palestine": (181, 87, 78),
    "Jordan": (110, 132, 184),
    "Saudi Arabia": (48, 145, 128),
    "Syria": (157, 119, 155),
    "Iraq": (145, 157, 94),
    "Lebanon": (197, 124, 89),
}
REVEALS = {
    "Egypt": (76, 91), "Israel": (83, 98), "Palestine": (88, 103),
    "Jordan": (94, 109), "Syria": (99, 114), "Lebanon": (102, 117),
    "Saudi Arabia": (107, 124), "Iraq": (113, 130),
}
EXTENT = (22.0, 47.5, 17.5, 38.0)  # W, E, S, N: Sinai, Levant and northern Arabia
CENTER_LON = (EXTENT[0] + EXTENT[1]) / 2
CENTER_LAT = (EXTENT[2] + EXTENT[3]) / 2
TILE_ZOOM = 6
MAP_RECT = (116, 140, 1188, 994)
MAP_X, MAP_Y = MAP_RECT[0], MAP_RECT[1]
MAP_WIDTH, MAP_HEIGHT = MAP_RECT[2] - MAP_RECT[0], MAP_RECT[3] - MAP_RECT[1]
CAMERA_START_ZOOM, CAMERA_END_ZOOM = 3.40, 6.10
CAMERA_START_CENTER, CAMERA_END_CENTER = (25.0, 31.0), (34.75, 27.75)


def world_px(lon: float, lat: float, zoom: int = TILE_ZOOM) -> tuple[float, float]:
    lat = max(-85.05112878, min(85.05112878, lat))
    scale = 256.0 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) * 0.5 * scale
    return x, y


def get_topographic_tile(z: int, x: int, y: int) -> Image.Image:
    max_idx = 2 ** z
    x %= max_idx
    path = TILE_CACHE / str(z) / str(x) / f"{y}.jpg"
    if path.is_file():
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            path.unlink(missing_ok=True)
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
    request = urllib.request.Request(url, headers={"User-Agent": "ChrononTemplate/1.0 regional map render"})
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read()
    tile = Image.open(io.BytesIO(raw)).convert("RGB")
    if tile.size != (256, 256):
        raise RuntimeError(f"Esri Topographic tile {z}/{x}/{y} is not 256x256")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return tile


def camera_pose(frame_num: int) -> tuple[float, float, float]:
    # A broad regional view descends to Sinai over the first 2.5 seconds.
    progress = ease((frame_num / (FRAMES - 1) - 0.035) / 0.50)
    zoom = CAMERA_START_ZOOM + (CAMERA_END_ZOOM - CAMERA_START_ZOOM) * progress
    lon = CAMERA_START_CENTER[0] + (CAMERA_END_CENTER[0] - CAMERA_START_CENTER[0]) * progress
    lat = CAMERA_START_CENTER[1] + (CAMERA_END_CENTER[1] - CAMERA_START_CENTER[1]) * progress
    return zoom, lon, lat


def prepare_topographic_pyramid() -> dict[int, tuple[Image.Image, float, float]]:
    # Cache just the tile bounds touched by the rendered camera path, at both
    # neighboring source levels so fractional zooms can crossfade smoothly.
    bounds: dict[int, list[float]] = {}
    for frame_num in range(FRAMES):
        zoom, lon, lat = camera_pose(frame_num)
        for z in {max(1, math.floor(zoom)), min(8, math.floor(zoom) + 1)}:
            cx, cy = world_px(lon, lat, z)
            scale = 2 ** (z - zoom)
            half_w = MAP_WIDTH * scale / 2 + 140
            half_h = MAP_HEIGHT * scale / 2 + 140
            if z not in bounds:
                bounds[z] = [cx-half_w, cy-half_h, cx+half_w, cy+half_h]
            else:
                b = bounds[z]
                b[0] = min(b[0], cx-half_w); b[1] = min(b[1], cy-half_h)
                b[2] = max(b[2], cx+half_w); b[3] = max(b[3], cy+half_h)
    plates = {}
    for z, (left_px, top_px, right_px, bottom_px) in bounds.items():
        tx0, ty0 = math.floor(left_px/256), math.floor(top_px/256)
        tx1, ty1 = math.floor(right_px/256), math.floor(bottom_px/256)
        cols, rows = tx1-tx0+1, ty1-ty0+1
        keys = [(z, tx0+ix, ty0+iy) for iy in range(rows) for ix in range(cols)
                if 0 <= ty0+iy < 2**z]
        print(f"Preparing Esri World Topographic base: {len(keys)} tiles at z{z}", flush=True)
        with ThreadPoolExecutor(max_workers=12) as pool:
            tiles = list(pool.map(lambda key: get_topographic_tile(*key), keys))
        mosaic = Image.new("RGB", (cols*256, rows*256), WATER)
        for index, tile in enumerate(tiles):
            ix, iy = index % cols, index // cols
            if 0 <= ty0+iy < 2**z:
                mosaic.paste(tile, (ix*256, iy*256))
        plates[z] = (mosaic, tx0*256, ty0*256)
    return plates


def sample_topographic(plates: dict[int, tuple[Image.Image, float, float]],
                       zoom: float, center_lon: float, center_lat: float) -> Image.Image:
    z0 = max(1, math.floor(zoom))
    z1 = min(8, z0 + 1)
    fraction = ease(zoom-z0)
    samples = []
    for z in (z0, z1):
        mosaic, left, top = plates[z]
        cx, cy = world_px(center_lon, center_lat, z)
        scale = 2 ** (z-zoom)
        cw, ch = round(MAP_WIDTH*scale), round(MAP_HEIGHT*scale)
        x0, y0 = round(cx-left-cw/2), round(cy-top-ch/2)
        crop = mosaic.crop((x0, y0, x0+cw, y0+ch)).resize((MAP_WIDTH, MAP_HEIGHT), Image.LANCZOS)
        samples.append(crop)
    return Image.blend(samples[0], samples[1], fraction).convert("RGBA")


def font(size: int, path: Path = FONT_BOLD) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def project(lon: float, lat: float, zoom: float,
            center_lon: float = CENTER_LON, center_lat: float = CENTER_LAT) -> tuple[int, int]:
    # Use the same Web Mercator transform as ChrononTemplate's tile runtime.
    x, y = world_px(lon, lat, TILE_ZOOM)
    center_x, center_y = world_px(center_lon, center_lat, TILE_ZOOM)
    scale = 2 ** (zoom-TILE_ZOOM)
    return round(MAP_WIDTH / 2 + (x - center_x) * scale), round(MAP_HEIGHT / 2 + (y - center_y) * scale)


def coords_to_screen(ring: list[list[float]], zoom: float,
                     center_lon: float, center_lat: float) -> list[tuple[int, int]]:
    return [project(float(p[0]), float(p[1]), zoom, center_lon, center_lat) for p in ring]


def polygons(geometry: dict) -> list[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    return []


def intersects_view(poly: list[list[list[float]]]) -> bool:
    ring = poly[0]
    west, east, south, north = EXTENT
    return not (max(p[0] for p in ring) < west or min(p[0] for p in ring) > east or
                max(p[1] for p in ring) < south or min(p[1] for p in ring) > north)


def draw_map(frame: Image.Image, selected: dict[str, dict], t: float, frame_num: int,
             plates: dict[int, tuple[Image.Image, float, float]]) -> None:
    zoom, center_lon, center_lat = camera_pose(frame_num)
    base = sample_topographic(plates, zoom, center_lon, center_lat)
    overlay = Image.new("RGBA", (MAP_WIDTH, MAP_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")

    # Highlight colors fade over genuine topographic tiles. Natural Earth
    # national polygons are projected in Web Mercator, matching the tile base.
    active_polygons = []
    for name, feature in selected.items():
        begin, finish = REVEALS[name]
        alpha = round(150 * ease((frame_num - begin) / max(1, finish - begin)))
        for poly in polygons(feature["geometry"]):
            if not intersects_view(poly):
                continue
            outer = coords_to_screen(poly[0], zoom, center_lon, center_lat)
            if len(outer) >= 3:
                d.polygon(outer, fill=(*PALETTE[name], alpha))
                active_polygons.append((outer, alpha))

    # Draw the highlighted national edges above translucent fills.
    for outer, alpha in active_polygons:
        if len(outer) > 2 and alpha:
            d.line(outer + [outer[0]], fill=(255, 249, 230, min(245, alpha + 80)), width=2, joint="curve")

    # Town markers are geographic coordinates. Their labels get small offsets
    # so neighboring places remain readable without changing the marker point.
    places = [
        ("IL CAIRO", 31.2357, 30.0444, -68, -23), ("SUEZ", 32.55, 29.97, 40, 10),
        ("GAZA", 34.4668, 31.5017, -69, -34), ("GERUSALEMME", 35.2137, 31.7683, 114, -42),
        ("DAMASCO", 36.2765, 33.5138, 83, -30), ("AMMAN", 35.9284, 31.9539, 104, 39),
        ("RIYADH", 46.6753, 24.7136, -69, 20),
    ]
    for idx, (label, lon, lat, dx, dy) in enumerate(places):
        px, py = project(lon, lat, zoom, center_lon, center_lat)
        if not (8 < px < MAP_WIDTH - 8 and 8 < py < MAP_HEIGHT - 8):
            continue
        if frame_num < 78 + idx * 5:
            continue
        r = 6
        d.ellipse((px-r-2, py-r-2, px+r+2, py+r+2), fill=(250, 248, 239, 245))
        d.ellipse((px-r, py-r, px+r, py+r), fill=(*CORAL, 255))
        # Topographic tiles already label the regional cities; add Italian tags
        # only for the three key places in this scene to keep the map uncluttered.
        if idx > 2:
            continue
        f = font(14)
        tw = d.textlength(label, font=f)
        tx, ty = px + dx, py + dy
        d.rounded_rectangle((tx-tw/2-6, ty-11, tx+tw/2+6, ty+11), radius=5, fill=(249, 248, 241, 238))
        d.text((tx, ty), label, font=f, fill=INK, anchor="mm")

    merged = Image.alpha_composite(base, overlay)
    mask = Image.new("L", (MAP_WIDTH, MAP_HEIGHT), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, MAP_WIDTH-1, MAP_HEIGHT-1), radius=20, fill=255)
    frame.paste(merged.convert("RGB"), (MAP_X, MAP_Y), mask)
    ImageDraw.Draw(frame).rounded_rectangle(MAP_RECT, radius=20, outline=(213, 216, 208), width=2)


def frame_for(t: float, i: int, geo: dict,
              plates: dict[int, tuple[Image.Image, float, float]]) -> Image.Image:
    # Near-white paper gives the vector geography a clean documentary finish.
    im = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, WIDTH, 12), fill=(19, 48, 53))
    d.text((112, 55), "ATLANTE STORICO   /   1973", font=font(17), fill=(88, 104, 102))
    d.text((112, 82), "IL FRONTE DEL SINAI", font=font(39), fill=INK)
    d.rounded_rectangle((110, 128, 286, 135), radius=3, fill=CORAL)
    draw_map(im, geo, t, i, plates)

    # Sidebar builds the political context in step with the corresponding map highlights.
    d.text((1260, 190), "GUERRA DEL KIPPUR", font=font(18), fill=CORAL)
    d.multiline_text((1260, 230), "La linea\ndel Canale", font=font(49, FONT_DIDONE), fill=INK, spacing=-4)
    d.multiline_text((1260, 355), "Il 6 ottobre 1973 l’offensiva\negiziana attraversa il Canale\ndi Suez verso il Sinai.",
                     font=font(22, FONT_REGULAR), fill=(63, 75, 76), spacing=9)
    d.line((1260, 485, 1810, 485), fill=(207, 209, 201), width=2)

    events = [
        (12, "01", "EGITTO", "attraversamento del Canale", "Egypt"),
        (30, "02", "ISRAELE", "fronte del Sinai", "Israel"),
        (48, "03", "SIRIA · GIORDANIA", "fronte settentrionale", "Syria"),
        (67, "04", "ARABIA SAUDITA", "crisi petrolifera regionale", "Saudi Arabia"),
    ]
    for start, n, title, desc, country in events:
        p = ease((i - start) / 15)
        if p <= 0:
            continue
        y = 535 + (int(n) - 1) * 108
        alpha_color = PALETTE[country]
        x = 1260 - round((1 - p) * 18)
        d.ellipse((x, y+3, x+35, y+38), fill=alpha_color)
        d.text((x+17, y+20), n, font=font(13), fill=(255,255,255), anchor="mm")
        d.text((x+53, y), title, font=font(19), fill=INK)
        d.text((x+53, y+31), desc, font=font(16, FONT_REGULAR), fill=MUTED)

    d.text((1260, 967), "Cartografia: Esri · HERE · Garmin · NOAA · USGS", font=font(13, FONT_REGULAR), fill=(125, 130, 124))
    d.text((1260, 987), "Confini Natural Earth · luoghi WGS84", font=font(13, FONT_REGULAR), fill=(125, 130, 124))
    d.text((1807, 1010), f"{i / FPS:04.1f}s", font=font(13, FONT_REGULAR), fill=(125, 130, 124), anchor="ra")
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    countries = {}
    for feature in data["features"]:
        name = feature.get("properties", {}).get("ADMIN", "")
        if name in PALETTE:
            countries[name] = feature

    plates = prepare_topographic_pyramid()

    target = OUT / "map_middle_east_oil_focus.mp4"
    temp = OUT / "map_middle_east_oil_focus.runtime.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(FRAMES):
            proc.stdin.write(frame_for(i / (FRAMES - 1), i, countries, plates).tobytes())
            if i % 30 == 0:
                print(f"render frame {i + 1}/{FRAMES}", flush=True)
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed while encoding the map")
    temp.replace(target)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
