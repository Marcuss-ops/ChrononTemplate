#!/usr/bin/env python3
"""Editorial map scenes over Italian regions and provinces.

Each scene highlights one ADM2 region (regione) or ADM3 province (provincia),
drops a marker on a city (comune capoluogo) and animates a black label with a
leader line, a city name, a red Bodoni figure and a grey Inter caption.

Geometry: ISTAT/geoBoundaries (CC BY 3.0) ADM2/ADM3 polygons in
catalog/italy_admin/, Natural Earth 50m countries for context, city points from
the offline GeoNames catalog. Pure PIL + numpy; frames are piped to ffmpeg.

Usage:
    python3 reference_map_italy.py --list
    python3 reference_map_italy.py --scene lombardia --still 140 --out frame.png
    python3 reference_map_italy.py --all --out-dir ../../out/italy_admin_maps_v3
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from geo_catalog import GeographicCatalog

HERE = Path(__file__).resolve().parent
CATALOG_DIR = HERE.parents[1] / "catalog"
COUNTRIES = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
ADMIN_DIR = CATALOG_DIR / "italy_admin"
FONT_DIR = HERE.parents[2] / "Chronon3d" / "assets" / "fonts"

W, H, FPS, FRAMES = 1920, 1080, 30, 150
SS = 2  # supersampling for static geometry

SEA = (247, 247, 245)
LAND = (226, 226, 224)
BORDER = (190, 190, 188)
PROVINCE_LINE = (206, 206, 204)
GRID = (236, 236, 234)
YELLOW = (242, 181, 28)
ITA_LINE = (58, 46, 16)
INK = (22, 22, 22)
RED = (214, 40, 57)
GREY_TEXT = (98, 98, 98)

# Label box sits up-left of the marker, as in the reference frame.
BOX_DX, BOX_DY = -57.0, 89.0
# Figure and caption sit in a fixed band at the bottom left, clear of the map.
FIG_X, FIG_Y = 120.0, 940.0

# level: "ADM2" = regione, "ADM3" = provincia.
SCENES: list[dict] = [
    {"slug": "lombardia", "level": "ADM2", "area": "Lombardia", "city": "Milano",
     "label": "narcotrafficante", "figure": "1 milione", "caption": "in contanti"},
    {"slug": "sicilia", "level": "ADM2", "area": "Sicilia", "city": "Palermo",
     "label": "porto", "figure": "3 tonnellate", "caption": "di cocaina"},
    {"slug": "campania", "level": "ADM2", "area": "Campania", "city": "Napoli",
     "label": "clan", "figure": "500 chili", "caption": "di hashish"},
    {"slug": "calabria", "level": "ADM2", "area": "Calabria", "city": "Reggio Calabria",
     "label": "rotta", "figure": "2 milioni", "caption": "in fatture"},
    {"slug": "puglia", "level": "ADM2", "area": "Puglia", "city": "Bari",
     "label": "approdo", "figure": "800 mila", "caption": "euro in nero"},
    {"slug": "lazio", "level": "ADM2", "area": "Lazio", "city": "Roma",
     "label": "riciclaggio", "figure": "5 milioni", "caption": "in immobili"},
    {"slug": "veneto", "level": "ADM2", "area": "Veneto", "city": "Verona",
     "label": "deposito", "figure": "12 chili", "caption": "di eroina"},
    {"slug": "piemonte", "level": "ADM2", "area": "Piemonte", "city": "Torino",
     "label": "cantiere", "figure": "2,5 milioni", "caption": "in nero"},
    {"slug": "emilia-romagna", "level": "ADM2", "area": "Emilia-Romagna", "city": "Bologna",
     "label": "logistica", "figure": "40 chili", "caption": "di cocaina"},
    {"slug": "toscana", "level": "ADM2", "area": "Toscana", "city": "Firenze",
     "label": "società", "figure": "700 mila", "caption": "euro in fatture"},
    {"slug": "liguria", "level": "ADM2", "area": "Liguria", "city": "Genova",
     "label": "porto", "figure": "6 tonnellate", "caption": "di hashish"},
    {"slug": "sardegna", "level": "ADM2", "area": "Sardegna", "city": "Cagliari",
     "label": "approdo", "figure": "150 chili", "caption": "di marijuana"},
    {"slug": "provincia-napoli", "level": "ADM3", "area": "Napoli", "city": "Napoli",
     "label": "clan", "figure": "30 milioni", "caption": "di euro"},
    {"slug": "provincia-palermo", "level": "ADM3", "area": "Palermo", "city": "Palermo",
     "label": "famiglia", "figure": "8 chili", "caption": "di eroina"},
    {"slug": "provincia-foggia", "level": "ADM3", "area": "Foggia", "city": "Foggia",
     "label": "traffico", "figure": "4 tonnellate", "caption": "di tabacco"},
    {"slug": "provincia-milano", "level": "ADM3", "area": "Milano", "city": "Milano",
     "label": "rete", "figure": "10 milioni", "caption": "in contanti"},
]


# ---------------------------------------------------------------------------
# projection and camera
# ---------------------------------------------------------------------------

def mercator_y(lat: float) -> float:
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


@dataclass(frozen=True)
class Camera:
    cx: float  # lon of canvas centre
    cy: float  # mercator y of canvas centre
    scale: float  # pixels per degree of longitude

    def project(self, lon: float, lat: float, ss: int = 1) -> tuple[float, float]:
        x = (lon - self.cx) * self.scale + W / 2
        y = H / 2 - (mercator_y(lat) - self.cy) * self.scale
        return x * ss, y * ss


def fit_camera(lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> Camera:
    """Centre on a bounding box and zoom so it fills most of the canvas."""
    cx = (lon_min + lon_max) / 2
    cy = (mercator_y(lat_min) + mercator_y(lat_max)) / 2
    span_x = max(lon_max - lon_min, 1e-3)
    span_y = max(mercator_y(lat_max) - mercator_y(lat_min), 1e-3)
    scale = min(W * 0.6 / span_x, H * 0.7 / span_y)
    return Camera(cx, cy, min(max(scale, 30.0), 260.0))


# ---------------------------------------------------------------------------
# data and fonts
# ---------------------------------------------------------------------------

def _ramp(frame: int, start: int, end: int) -> float:
    t = min(1.0, max(0.0, (frame - start) / float(end - start)))
    return t * t * (3 - 2 * t)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _polygons(geometry: dict) -> list[list[list[list[float]]]]:
    if geometry.get("type") == "Polygon":
        return [geometry["coordinates"]]
    if geometry.get("type") == "MultiPolygon":
        return geometry["coordinates"]
    return []


@functools.lru_cache(maxsize=None)
def _geojson(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["features"]


def _italian_features(level: str) -> list[dict]:
    name = {"ADM2": "geoBoundaries_ITA_ADM2", "ADM3": "geoBoundaries_ITA_ADM3"}[level]
    return _geojson(str(ADMIN_DIR / f"{name}.simplified.geojson"))


def highlight_features(scene: dict) -> list[dict]:
    """Features of the scene's area; raises if the name does not resolve."""
    matches = [f for f in _italian_features(scene["level"])
               if f["properties"].get("shapeName") == scene["area"]]
    if not matches:
        raise KeyError(f"{scene['level']} area not found: {scene['area']!r}")
    return matches


def city_point(name: str) -> tuple[float, float]:
    with GeographicCatalog() as geo:
        city = geo.exact_city(name, country_iso2="IT")
    if city is None:
        raise KeyError(f"city not resolved in catalog: {name!r}")
    return float(city["longitude"]), float(city["latitude"])


def scene_bounds(features: list[dict]) -> tuple[float, float, float, float]:
    lons, lats = [], []
    for feature in features:
        for polygon in _polygons(feature["geometry"]):
            for lon, lat in polygon[0]:
                lons.append(lon)
                lats.append(lat)
    return min(lons), max(lons), min(lats), max(lats)


# ---------------------------------------------------------------------------
# static layers
# ---------------------------------------------------------------------------

def _draw_ring(draw: ImageDraw.ImageDraw, cam: Camera, ring, fill, ss: int, width: float) -> None:
    pts = [cam.project(lon, lat, ss) for lon, lat in ring]
    if len(pts) > 1:
        draw.line(pts + [pts[0]], fill=fill, width=max(1, int(width * ss)), joint="curve")


def build_static(scene: dict, cam: Camera, ss: int = SS):
    """Return (base RGB, highlight fill mask L, highlight outline mask L) at 1x."""
    big = (W * ss, H * ss)
    base = Image.new("RGB", big, SEA)
    draw = ImageDraw.Draw(base)

    step = 160 * ss
    for x in range(0, big[0], step):
        draw.line([(x, 0), (x, big[1])], fill=GRID, width=ss)
    for y in range(0, big[1], step):
        draw.line([(0, y), (big[0], y)], fill=GRID, width=ss)

    # Context: Natural Earth countries except Italy, which is drawn from ISTAT.
    countries = _geojson(str(COUNTRIES))
    for feature in countries:
        if feature.get("properties", {}).get("ADM0_A3") == "ITA":
            continue
        for polygon in _polygons(feature.get("geometry") or {}):
            draw.polygon([cam.project(lon, lat, ss) for lon, lat in polygon[0]], fill=LAND)
            for hole in polygon[1:]:
                draw.polygon([cam.project(lon, lat, ss) for lon, lat in hole], fill=SEA)
        for polygon in _polygons(feature.get("geometry") or {}):
            for ring in polygon:
                _draw_ring(draw, cam, ring, BORDER, ss, 2)

    # Italy: regions as land, provinces as fine lines.
    for feature in _italian_features("ADM2"):
        for polygon in _polygons(feature["geometry"]):
            draw.polygon([cam.project(lon, lat, ss) for lon, lat in polygon[0]], fill=LAND)
    for feature in _italian_features("ADM3"):
        for polygon in _polygons(feature["geometry"]):
            for ring in polygon:
                _draw_ring(draw, cam, ring, PROVINCE_LINE, ss, 1)

    fill = Image.new("L", big, 0)
    line = Image.new("L", big, 0)
    fill_draw = ImageDraw.Draw(fill)
    line_draw = ImageDraw.Draw(line)
    for feature in highlight_features(scene):
        for polygon in _polygons(feature["geometry"]):
            outer = [cam.project(lon, lat, ss) for lon, lat in polygon[0]]
            fill_draw.polygon(outer, fill=255)
            for hole in polygon[1:]:
                fill_draw.polygon([cam.project(lon, lat, ss) for lon, lat in hole], fill=0)
            for ring in polygon:
                pts = [cam.project(lon, lat, ss) for lon, lat in ring]
                line_draw.line(pts + [pts[0]], fill=255, width=2 * ss, joint="curve")

    down = (W, H)
    return (base.resize(down, Image.LANCZOS),
            fill.resize(down, Image.LANCZOS),
            line.resize(down, Image.LANCZOS))


# ---------------------------------------------------------------------------
# animated overlay
# ---------------------------------------------------------------------------

def _text_layer(text: str, font, color, xy, anchor="ls", alpha=1.0, clip_x=None):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=font, fill=color + (255,), anchor=anchor)
    if clip_x is not None:
        clip = Image.new("L", (W, H), 0)
        ImageDraw.Draw(clip).rectangle((0, 0, clip_x, H), fill=255)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), clip))
    if alpha < 1.0:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    return layer


@dataclass(frozen=True)
class Layout:
    marker: tuple[float, float]
    box: tuple[float, float, float, float]  # left, top, right, bottom
    box_mid_y: float


def layout_for(scene: dict, cam: Camera) -> Layout:
    lon, lat = city_point(scene["city"])
    mx, my = cam.project(lon, lat)
    box_font = _font("Inter-SemiBold.ttf", 34)
    text_w = box_font.getlength(scene["label"])
    pad, box_h = 26, 60
    right = min(max(mx + BOX_DX, 20 + text_w + 2 * pad), W - 20)
    mid = min(max(my + BOX_DY, 20 + box_h / 2), H - 20 - box_h / 2)
    left = right - (text_w + 2 * pad)
    top = mid - box_h / 2
    return Layout(marker=(mx, my), box=(left, top, right, top + box_h), box_mid_y=mid)


def compose_frame(frame: int, scene: dict, layout: Layout, base: Image.Image,
                  fill_mask: Image.Image, line_mask: Image.Image) -> Image.Image:
    land_a = _ramp(frame, 0, 20)
    area_a = _ramp(frame, 30, 50)

    img = Image.blend(Image.new("RGB", (W, H), SEA), base, land_a)
    if area_a > 0:
        img.paste(YELLOW, (0, 0), fill_mask.point(lambda v: int(v * area_a)))
        img.paste(ITA_LINE, (0, 0), line_mask.point(lambda v: int(v * area_a)))
    img = img.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def add(layer: Image.Image) -> None:
        nonlocal overlay
        overlay = Image.alpha_composite(overlay, layer)

    mx, my = layout.marker
    left, top, right, bottom = layout.box
    box_mid = layout.box_mid_y

    leader_p = _ramp(frame, 62, 76)
    if leader_p > 0:
        ex = right + (mx - right) * leader_p
        ey = box_mid + (my - box_mid) * leader_p
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).line([(right, box_mid), (ex, ey)], fill=INK + (255,), width=2)
        add(layer)

    dot_r = 7.0 * _ramp(frame, 55, 65)
    if dot_r > 0.5:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((mx - dot_r, my - dot_r, mx + dot_r, my + dot_r),
                                      fill=INK + (255,))
        add(layer)

    box_a = _ramp(frame, 70, 84)
    box_font = _font("Inter-SemiBold.ttf", 34)
    if box_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle((left, top, right, bottom),
                                        fill=INK + (int(255 * box_a),))
        add(layer)
        add(_text_layer(scene["label"], box_font, (255, 255, 255),
                        (left + 26, box_mid + 12), alpha=box_a))

    city_a = _ramp(frame, 80, 92)
    if city_a > 0:
        place = scene["area"] if scene["city"] == scene["area"] else f"{scene['area']} · {scene['city']}"
        add(_text_layer(place, _font("Inter-Regular.ttf", 30), GREY_TEXT,
                        (FIG_X, FIG_Y - 110), alpha=city_a))

    figure_font = ImageFont.truetype(str(FONT_DIR / "BodoniModa-Italic.ttf"), 96)
    caption_font = _font("Inter-Regular.ttf", 40)
    fx, fy = FIG_X, FIG_Y
    fig_w = figure_font.getlength(scene["figure"])
    reveal = _ramp(frame, 100, 126)
    if reveal > 0:
        add(_text_layer(scene["figure"], figure_font, RED, (fx, fy),
                        clip_x=fx + fig_w * reveal))
    cap_a = _ramp(frame, 122, 142)
    if cap_a > 0:
        add(_text_layer(scene["caption"], caption_font, GREY_TEXT,
                        (fx + fig_w + 14, fy), alpha=cap_a))

    return Image.alpha_composite(img, overlay).convert("RGB")


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def scene_by_slug(slug: str) -> dict:
    for scene in SCENES:
        if scene["slug"] == slug:
            return scene
    raise KeyError(f"unknown scene {slug!r}")


def prepare(scene: dict):
    features = highlight_features(scene)
    lon_min, lon_max, lat_min, lat_max = scene_bounds(features)
    cam = fit_camera(lon_min, lon_max, lat_min, lat_max)
    base, fill_mask, line_mask = build_static(scene, cam)
    return layout_for(scene, cam), base, fill_mask, line_mask


def render_scene(scene: dict, out: Path) -> None:
    layout, base, fill_mask, line_mask = prepare(scene)
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for f in range(FRAMES):
            proc.stdin.write(compose_frame(f, scene, layout, base, fill_mask, line_mask).tobytes())
    finally:
        proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise SystemExit(code)
    print(f"wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list scene slugs")
    parser.add_argument("--scene", help="render one scene slug")
    parser.add_argument("--all", action="store_true", help="render every scene")
    parser.add_argument("--out", type=Path, help="output MP4 (or PNG with --still)")
    parser.add_argument("--out-dir", type=Path, help="output folder for --all")
    parser.add_argument("--still", type=int, default=None, help="render one frame as PNG")
    args = parser.parse_args()

    if args.list:
        for scene in SCENES:
            print(scene["slug"])
        return 0
    if args.all:
        out_dir = args.out_dir or (HERE.parents[1] / "out" / "italy_admin_maps_v3")
        out_dir.mkdir(parents=True, exist_ok=True)
        for scene in SCENES:
            render_scene(scene, out_dir / f"{scene['slug']}.mp4")
        return 0
    if not args.scene or not args.out:
        parser.error("--scene and --out are required (or use --all / --list)")
    scene = scene_by_slug(args.scene)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.still is not None:
        layout, base, fill_mask, line_mask = prepare(scene)
        compose_frame(args.still, scene, layout, base, fill_mask, line_mask).save(args.out)
        print(f"wrote {args.out}")
        return 0
    render_scene(scene, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
