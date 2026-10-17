#!/usr/bin/env python3
"""Editorial map scenes for the whole world, RenderingGen-compatible.

Same look as reference_map_italy.py (light plate, yellow highlight, black
label box with leader line, red Bodoni figure, grey caption), but:

- highlights resolve worldwide: any Natural Earth country (ISO3), any ADM1
  region with catalog geometry, or Italian ADM2/ADM3 from ISTAT/geoBoundaries;
- markers resolve from the offline GeoNames catalog (exact, conservative);
- the static plate is rendered in TRUE Web Mercator with the exact math of
  RenderingGen's internal/geo (LatLonToGlobalPixel/CenteredOn/Contains), so
  an exported plate is pixel-compatible with the map contract validator;
- --export-renderinggen emits a ready-to-compile renderinggen.overlay-plan.v1
  static map item (local PNG basemap + grounded pin + attribution).

Usage:
    python3 editorial_world_map.py --list
    python3 editorial_world_map.py --scene francia --still 140 --out frame.png
    python3 editorial_world_map.py --scene francia --out out.mp4
    python3 editorial_world_map.py --scene francia --export-renderinggen --out-dir ../../out/world_maps_v1
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

import reference_map_italy as rm
from geo_catalog import GeographicCatalog

HERE = Path(__file__).resolve().parent
CATALOG_DIR = HERE.parents[1] / "catalog"
COUNTRIES = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
ADMIN_DIR = CATALOG_DIR / "italy_admin"

W, H, FPS, FRAMES = rm.W, rm.H, rm.FPS, rm.FRAMES

# RenderingGen map contract bounds mirrored here so the exporter fails fast
# instead of emitting a plan the worker would reject.
MAX_ZOOM = 18
WEB_MERCATOR_LAT_LIMIT = 85.05112877980659
TILE = 256.0

# kind "country": ISO3 highlight. kind "region": ADM1 name + country_iso2.
# kind "italy_admin": ADM2/ADM3 shapeName (same data as reference_map_italy).
WORLD_SCENES: list[dict] = [
    {"slug": "francia", "kind": "country", "iso3": "FRA", "area": "Francia",
     "city": "Paris", "country_iso2": "FR",
     "label": "rete", "figure": "2 milioni", "caption": "in contanti"},
    {"slug": "spagna", "kind": "country", "iso3": "ESP", "area": "Spagna",
     "city": "Madrid", "country_iso2": "ES",
     "label": "rotta", "figure": "900 chili", "caption": "di hashish"},
    {"slug": "germania", "kind": "country", "iso3": "DEU", "area": "Germania",
     "city": "Berlin", "country_iso2": "DE",
     "label": "logistica", "figure": "1,5 milioni", "caption": "in nero"},
    {"slug": "regno-unito", "kind": "country", "iso3": "GBR", "area": "Regno Unito",
     "city": "London", "country_iso2": "GB",
     "label": "riciclaggio", "figure": "7 milioni", "caption": "in immobili"},
    {"slug": "giappone", "kind": "country", "iso3": "JPN", "area": "Giappone",
     "city": "Tokyo", "country_iso2": "JP",
     "label": "porto", "figure": "250 chili", "caption": "di cocaina"},
    {"slug": "egitto", "kind": "country", "iso3": "EGY", "area": "Egitto",
     "city": "Cairo", "country_iso2": "EG",
     "label": "rotta", "figure": "1 tonnellata", "caption": "di eroina"},
    {"slug": "india", "kind": "country", "iso3": "IND", "area": "India",
     "city": "Mumbai", "country_iso2": "IN",
     "label": "rete", "figure": "4 milioni", "caption": "in fatture"},
    {"slug": "australia", "kind": "country", "iso3": "AUS", "area": "Australia",
     "city": "Sydney", "country_iso2": "AU",
     "label": "approdo", "figure": "600 chili", "caption": "di cocaina"},
    {"slug": "argentina", "kind": "country", "iso3": "ARG", "area": "Argentina",
     "city": "Buenos Aires", "country_iso2": "AR",
     "label": "rotta", "figure": "2 tonnellate", "caption": "di cocaina"},
    {"slug": "usa-new-york", "kind": "country", "iso3": "USA", "area": "Stati Uniti",
     "city": "New York City", "country_iso2": "US",
     "label": "famiglia", "figure": "12 milioni", "caption": "in contanti"},
    {"slug": "texas", "kind": "region", "region": "Texas", "country_iso2": "US",
     "area": "Texas", "city": "Fort Worth", "city_country_iso2": "US",
     "label": "deposito", "figure": "800 chili", "caption": "di marijuana"},
    {"slug": "baviera", "kind": "region", "region": "Bavaria", "country_iso2": "DE",
     "area": "Baviera", "city": "Munich", "city_country_iso2": "DE",
     "label": "cantiere", "figure": "3 milioni", "caption": "in nero"},
]

SCENES: list[dict] = (
    [{**s, "kind": "italy_admin", "level": s["level"]} for s in rm.SCENES]
    + WORLD_SCENES
)


# ---------------------------------------------------------------------------
# Web Mercator: exact port of RenderingGen internal/geo (same ops, same order)
# ---------------------------------------------------------------------------

def _clamp_lat(lat: float) -> float:
    return min(max(lat, -WEB_MERCATOR_LAT_LIMIT), WEB_MERCATOR_LAT_LIMIT)


def latlon_to_global(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    scale = TILE * math.pow(2.0, float(zoom))
    lon = min(max(lon, -180.0), 180.0)
    lat = _clamp_lat(lat)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = lat * math.pi / 180.0
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) * 0.5 * scale
    return x, y


def global_to_latlon(x: float, y: float, zoom: int) -> tuple[float, float]:
    scale = TILE * math.pow(2.0, float(zoom))
    lon = (x / scale) * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * (y / scale)
    lat = math.atan(math.sinh(n)) * 180.0 / math.pi
    return lat, lon


@dataclass(frozen=True)
class Window:
    zoom: int
    top_left_x: float
    top_left_y: float

    @staticmethod
    def centered_on(lat: float, lon: float, zoom: int, width: int, height: int) -> "Window":
        cx, cy = latlon_to_global(lat, lon, zoom)
        return Window(zoom, cx - width / 2.0, cy - height / 2.0)

    def to_raster(self, lat: float, lon: float) -> tuple[float, float]:
        gx, gy = latlon_to_global(lat, lon, self.zoom)
        return gx - self.top_left_x, gy - self.top_left_y

    def contains(self, lat: float, lon: float) -> bool:
        x, y = self.to_raster(lat, lon)
        return 0 <= x <= W and 0 <= y <= H


# ---------------------------------------------------------------------------
# highlight geometry
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _countries(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["features"]


def _polygons(geometry: dict) -> list:
    if geometry.get("type") == "Polygon":
        return [geometry["coordinates"]]
    if geometry.get("type") == "MultiPolygon":
        return geometry["coordinates"]
    return []


def country_features(iso3: str) -> list[dict]:
    # Match the administrative unit first: SOV_A3 would also pull in overseas
    # departments (e.g. French Guiana for FRA) and blow up the camera bbox.
    code = iso3.upper()
    all_features = _countries(str(COUNTRIES))
    matches = [f for f in all_features
               if str(f.get("properties", {}).get("ADM0_A3", "")).upper() == code]
    if not matches:
        matches = [f for f in all_features
                   if str(f.get("properties", {}).get("ISO_A3", "")).upper() == code]
    if not matches:
        raise KeyError(f"country ISO3 not in Natural Earth 50m: {iso3!r}")
    return matches


def region_features(name: str, country_iso2: str) -> list[dict]:
    with GeographicCatalog() as geo:
        rows = geo.find_regions(name, include_geometry=True)
    matches = [r for r in rows if r["country_iso2"] == country_iso2.upper() and r.get("geometry")]
    if not matches:
        raise KeyError(f"ADM1 region without catalog geometry: {name!r} [{country_iso2}]")
    return [{"type": "Feature", "properties": {"name": r["name"]}, "geometry": r["geometry"]}
            for r in matches]


def italy_admin_features(level: str, area: str) -> list[dict]:
    name = {"ADM2": "geoBoundaries_ITA_ADM2", "ADM3": "geoBoundaries_ITA_ADM3"}[level]
    with open(ADMIN_DIR / f"{name}.simplified.geojson", encoding="utf-8") as f:
        features = json.load(f)["features"]
    matches = [f for f in features if f["properties"].get("shapeName") == area]
    if not matches:
        raise KeyError(f"italy_admin area not found: {area!r}")
    return matches


def highlight_features(scene: dict) -> tuple[list[dict], str]:
    """Return (features, provenance_tag) for a scene."""
    kind = scene["kind"]
    if kind == "country":
        return country_features(scene["iso3"]), "ne"
    if kind == "region":
        return region_features(scene["region"], scene["country_iso2"]), "ne+geonames"
    if kind == "italy_admin":
        return italy_admin_features(scene["level"], scene["area"]), "istat+ne"
    raise KeyError(f"unknown scene kind {kind!r}")


def city_point(name: str, country_iso2: str | None = None) -> tuple[float, float]:
    with GeographicCatalog() as geo:
        city = geo.exact_city(name, country_iso2=country_iso2)
    if city is None:
        raise KeyError(f"city not resolved in catalog: {name!r} [{country_iso2}]")
    return float(city["longitude"]), float(city["latitude"])


def scene_bounds(features: list[dict]) -> tuple[float, float, float, float]:
    lons, lats = [], []
    for feature in features:
        for polygon in _polygons(feature.get("geometry") or {}):
            for lon, lat in polygon[0]:
                lons.append(lon)
                lats.append(lat)
    if not lons:
        raise ValueError("highlight has no rings")
    return min(lons), max(lons), min(lats), max(lats)


def main_territory_bounds(features: list[dict]) -> tuple[float, float, float, float]:
    """BBox of the largest polygon only.

    Natural Earth bakes overseas departments into the sovereign feature
    (France+Guiana, USA+Alaska); the camera frames the main territory while
    every polygon is still drawn, so nothing is silently dropped."""
    best: tuple[float, float, float, float] | None = None
    best_area = -1.0
    for feature in features:
        for polygon in _polygons(feature.get("geometry") or {}):
            ring = polygon[0]
            lons = [pt[0] for pt in ring]
            ys = [math.degrees(math.log(math.tan(math.pi / 4 + math.radians(
                min(max(pt[1], -WEB_MERCATOR_LAT_LIMIT), WEB_MERCATOR_LAT_LIMIT)) / 2)))
                  for pt in ring]
            area = (max(lons) - min(lons)) * (max(ys) - min(ys))
            if area > best_area:
                best_area = area
                lats = [pt[1] for pt in ring]
                best = (min(lons), max(lons), min(lats), max(lats))
    if best is None:
        raise ValueError("highlight has no rings")
    return best


def fit_window(lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> Window:
    """Deepest Web Mercator zoom where the bbox fits 0.6W x 0.7H with margin."""
    lat_min, lat_max = _clamp_lat(lat_min), _clamp_lat(lat_max)
    for zoom in range(MAX_ZOOM, -1, -1):
        x0, y0 = latlon_to_global(lat_max, lon_min, zoom)
        x1, y1 = latlon_to_global(lat_min, lon_max, zoom)
        if (x1 - x0) <= W * 0.6 and (y1 - y0) <= H * 0.7:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            clat, clon = global_to_latlon(cx, cy, zoom)
            return Window.centered_on(clat, clon, zoom, W, H)
    clat, clon = global_to_latlon(
        *[(a + b) / 2 for a, b in zip(
            latlon_to_global(lat_max, lon_min, 0),
            latlon_to_global(lat_min, lon_max, 0))], 0)
    return Window.centered_on(clat, clon, 0, W, H)


# ---------------------------------------------------------------------------
# static plate (Web Mercator) + animated overlay (same look as Italy scenes)
# ---------------------------------------------------------------------------

def _draw_ring(draw: ImageDraw.ImageDraw, win: Window, ring, fill, ss: int, width: float) -> None:
    pts = []
    for lon, lat in ring:
        x, y = win.to_raster(lat, lon)
        pts.append((x * ss, y * ss))
    if len(pts) > 1:
        draw.line(pts + [pts[0]], fill=fill, width=max(1, int(width * ss)), joint="curve")


def build_static(scene: dict, win: Window, ss: int = rm.SS):
    from PIL import Image
    big = (W * ss, H * ss)
    base = Image.new("RGB", big, rm.SEA)
    draw = ImageDraw.Draw(base)
    step = 160 * ss
    for x in range(0, big[0], step):
        draw.line([(x, 0), (x, big[1])], fill=rm.GRID, width=ss)
    for y in range(0, big[1], step):
        draw.line([(0, y), (big[0], y)], fill=rm.GRID, width=ss)

    features, _ = highlight_features(scene)
    highlight_ids = {id(f) for f in features}
    for feature in _countries(str(COUNTRIES)):
        if id(feature) in highlight_ids or (
                scene["kind"] == "country" and feature in features):
            continue
        for polygon in _polygons(feature.get("geometry") or {}):
            outer = [win.to_raster(lat, lon) for lon, lat in polygon[0]]
            draw.polygon([(x * ss, y * ss) for x, y in outer], fill=rm.LAND)

    if scene["kind"] == "italy_admin":
        # Italian regions as land context (same as reference_map_italy).
        name = "geoBoundaries_ITA_ADM2"
        with open(ADMIN_DIR / f"{name}.simplified.geojson", encoding="utf-8") as f:
            adm2 = json.load(f)["features"]
        for feature in adm2:
            for polygon in _polygons(feature["geometry"]):
                outer = [win.to_raster(lat, lon) for lon, lat in polygon[0]]
                draw.polygon([(x * ss, y * ss) for x, y in outer], fill=rm.LAND)

    for feature in _countries(str(COUNTRIES)):
        for polygon in _polygons(feature.get("geometry") or {}):
            for ring in polygon:
                _draw_ring(draw, win, ring, rm.BORDER, ss, 2)

    fill = Image.new("L", big, 0)
    line = Image.new("L", big, 0)
    fill_draw = ImageDraw.Draw(fill)
    line_draw = ImageDraw.Draw(line)
    for feature in features:
        for polygon in _polygons(feature.get("geometry") or {}):
            outer = [win.to_raster(lat, lon) for lon, lat in polygon[0]]
            outer_ss = [(x * ss, y * ss) for x, y in outer]
            fill_draw.polygon(outer_ss, fill=255)
            for hole in polygon[1:]:
                hole_ss = [(x * ss, y * ss) for x, y in
                           (win.to_raster(lat, lon) for lon, lat in hole)]
                fill_draw.polygon(hole_ss, fill=0)
            for ring in polygon:
                pts = [win.to_raster(lat, lon) for lon, lat in ring]
                pts_ss = [(x * ss, y * ss) for x, y in pts]
                line_draw.line(pts_ss + [pts_ss[0]], fill=255, width=2 * ss, joint="curve")

    down = (W, H)
    return (base.resize(down, Image.LANCZOS),
            fill.resize(down, Image.LANCZOS),
            line.resize(down, Image.LANCZOS))


# ---------------------------------------------------------------------------
# animated overlay (same timeline and look as the Italy scenes)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Layout:
    win: Window
    marker: tuple[float, float]
    city_lat: float
    city_lon: float
    zoom: int
    box: tuple[float, float, float, float]
    box_mid_y: float


def layout_for(scene: dict, win: Window) -> Layout:
    # Italian scenes carry no country key; their cities are Italian by construction.
    iso = (scene.get("city_country_iso2") or scene.get("country_iso2")
           or ("IT" if scene["kind"] == "italy_admin" else None))
    lon, lat = city_point(scene["city"], iso)
    mx, my = win.to_raster(lat, lon)
    box_font = rm._font("Inter-SemiBold.ttf", 34)
    text_w = box_font.getlength(scene["label"])
    pad, box_h = 26, 60
    right = min(max(mx + rm.BOX_DX, 20 + text_w + 2 * pad), W - 20)
    mid = min(max(my + rm.BOX_DY, 20 + box_h / 2), H - 20 - box_h / 2)
    left = right - (text_w + 2 * pad)
    top = mid - box_h / 2
    return Layout(win=win, marker=(mx, my), city_lat=lat, city_lon=lon,
                  zoom=win.zoom, box=(left, top, right, top + box_h), box_mid_y=mid)


def compose_frame(frame: int, scene: dict, layout: Layout, base: Image.Image,
                  fill_mask: Image.Image, line_mask: Image.Image) -> Image.Image:
    from PIL import ImageChops
    land_a = rm._ramp(frame, 0, 20)
    area_a = rm._ramp(frame, 30, 50)

    img = Image.blend(Image.new("RGB", (W, H), rm.SEA), base, land_a)
    if area_a > 0:
        img.paste(rm.YELLOW, (0, 0), fill_mask.point(lambda v: int(v * area_a)))
        img.paste(rm.ITA_LINE, (0, 0), line_mask.point(lambda v: int(v * area_a)))
    img = img.convert("RGBA")

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    def add(layer: Image.Image) -> None:
        nonlocal overlay
        overlay = Image.alpha_composite(overlay, layer)

    mx, my = layout.marker
    left, top, right, bottom = layout.box
    box_mid = layout.box_mid_y

    leader_p = rm._ramp(frame, 62, 76)
    if leader_p > 0:
        ex = right + (mx - right) * leader_p
        ey = box_mid + (my - box_mid) * leader_p
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).line([(right, box_mid), (ex, ey)],
                                   fill=rm.INK + (255,), width=2)
        add(layer)

    dot_r = 7.0 * rm._ramp(frame, 55, 65)
    if dot_r > 0.5:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((mx - dot_r, my - dot_r, mx + dot_r, my + dot_r),
                                      fill=rm.INK + (255,))
        add(layer)

    box_a = rm._ramp(frame, 70, 84)
    box_font = rm._font("Inter-SemiBold.ttf", 34)
    if box_a > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle((left, top, right, bottom),
                                        fill=rm.INK + (int(255 * box_a),))
        add(layer)
        add(rm._text_layer(scene["label"], box_font, (255, 255, 255),
                           (left + 26, box_mid + 12), alpha=box_a))

    city_a = rm._ramp(frame, 80, 92)
    if city_a > 0:
        place = (scene["area"] if scene["city"] == scene["area"]
                 else f"{scene['area']} · {scene['city']}")
        add(rm._text_layer(place, rm._font("Inter-Regular.ttf", 30), rm.GREY_TEXT,
                           (rm.FIG_X, rm.FIG_Y - 110), alpha=city_a))

    figure_font = rm.ImageFont.truetype(str(rm.FONT_DIR / "BodoniModa-Italic.ttf"), 96)
    caption_font = rm._font("Inter-Regular.ttf", 40)
    fx, fy = rm.FIG_X, rm.FIG_Y
    fig_w = figure_font.getlength(scene["figure"])
    reveal = rm._ramp(frame, 100, 126)
    if reveal > 0:
        add(rm._text_layer(scene["figure"], figure_font, rm.RED, (fx, fy),
                           clip_x=fx + fig_w * reveal))
    cap_a = rm._ramp(frame, 122, 142)
    if cap_a > 0:
        add(rm._text_layer(scene["caption"], caption_font, rm.GREY_TEXT,
                           (fx + fig_w + 14, fy), alpha=cap_a))

    return Image.alpha_composite(img, overlay).convert("RGB")


# ---------------------------------------------------------------------------
# scene plumbing
# ---------------------------------------------------------------------------

def scene_by_slug(slug: str) -> dict:
    for scene in SCENES:
        if scene["slug"] == slug:
            return scene
    raise KeyError(f"unknown scene {slug!r}")


def prepare(scene: dict):
    features, _ = highlight_features(scene)
    lon_min, lon_max, lat_min, lat_max = main_territory_bounds(features)
    win = fit_window(lon_min, lon_max, lat_min, lat_max)
    base, fill_mask, line_mask = build_static(scene, win)
    return layout_for(scene, win), base, fill_mask, line_mask


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


# ---------------------------------------------------------------------------
# RenderingGen exporter: plate PNG + overlay-plan.v1 static map item
# ---------------------------------------------------------------------------

def attribution_for(scene: dict) -> tuple[str, str, str]:
    if scene["kind"] == "italy_admin":
        return ("editorial-world-map/istat-ne",
                "ISTAT/geoBoundaries CC BY 3.0; Natural Earth public domain; GeoNames CC BY 4.0",
                "Boundaries: ISTAT/geoBoundaries, Natural Earth. Places: GeoNames (www.geonames.org).")
    return ("editorial-world-map/ne-geonames",
            "Natural Earth public domain; GeoNames CC BY 4.0",
            "Boundaries: Natural Earth. Places: GeoNames (www.geonames.org).")


def export_renderinggen(scene: dict, out_dir: Path) -> tuple[Path, Path]:
    """Write <slug>_basemap.png and <slug>_renderinggen_map.json.

    The plate is the highlight-only geographic render (no text overlay) at
    the scene's fitted Web Mercator window; the JSON mirrors the worker's
    own georeferencedMapPlan test shape with real provenance, center, zoom
    and a pin grounded on the scene city. Raises if the pin would fall
    outside the contract window.
    """
    from PIL import ImageChops
    out_dir.mkdir(parents=True, exist_ok=True)
    layout, base, fill_mask, line_mask = prepare(scene)
    win = layout.win
    plate = base.copy()
    plate.paste(rm.YELLOW, (0, 0), fill_mask)
    plate.paste(rm.ITA_LINE, (0, 0), line_mask)
    png_path = out_dir / f"{scene['slug']}_basemap.png"
    plate.save(png_path)
    digest = hashlib.sha256(png_path.read_bytes()).hexdigest()

    clat, clon = global_to_latlon(win.top_left_x + W / 2, win.top_left_y + H / 2, win.zoom)
    if not win.contains(layout.city_lat, layout.city_lon):
        raise ValueError(f"city pin outside contract window for {scene['slug']}")
    source_id, source_license, attribution = attribution_for(scene)
    plan = {
        "schema_version": "renderinggen.overlay-plan.v1",
        "plan_id": f"editorial-world-{scene['slug']}",
        "video_id": f"editorial-world-{scene['slug']}",
        "width": W, "height": H, "fps_num": FPS, "fps_den": 1,
        "items": [{
            "id": f"map-{scene['slug']}", "kind": "map", "template_id": "MAP",
            "start_ms": 0, "end_ms": 5000,
            "asset_refs": [{
                "asset_id": f"{scene['slug']}-basemap",
                "sha256": digest,
                "url": f"assets/maps/{scene['slug']}_basemap.png",
                "media_type": "image/png",
            }],
            "map": {
                "provider": "local",
                "source_id": source_id,
                "source_license": source_license,
                "center": {"latitude": clat, "longitude": clon},
                "zoom": win.zoom,
                "width": W, "height": H,
                "attribution": attribution,
                "pins": [{
                    "id": scene["slug"], "label": scene["city"],
                    "latitude": layout.city_lat, "longitude": layout.city_lon,
                    "color": "#161616", "radius_px": 7.0,
                }],
            },
        }],
    }
    plan_path = out_dir / f"{scene['slug']}_renderinggen_map.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {png_path}")
    print(f"wrote {plan_path}")
    return png_path, plan_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list scene slugs")
    parser.add_argument("--scene", help="render one scene slug")
    parser.add_argument("--all", action="store_true", help="render every scene")
    parser.add_argument("--out", type=Path, help="output MP4 (or PNG with --still)")
    parser.add_argument("--out-dir", type=Path, help="output folder for --all / --export-renderinggen")
    parser.add_argument("--still", type=int, default=None, help="render one frame as PNG")
    parser.add_argument("--export-renderinggen", action="store_true",
                        help="emit basemap PNG + overlay-plan.v1 map JSON instead of MP4")
    args = parser.parse_args()

    if args.list:
        for scene in SCENES:
            print(scene["slug"])
        return 0
    if args.export_renderinggen:
        out_dir = args.out_dir or (HERE.parents[1] / "out" / "world_maps_v1")
        if args.scene:
            export_renderinggen(scene_by_slug(args.scene), out_dir)
        elif args.all:
            for scene in SCENES:
                export_renderinggen(scene, out_dir)
        else:
            parser.error("--export-renderinggen needs --scene or --all")
        return 0
    if args.all:
        out_dir = args.out_dir or (HERE.parents[1] / "out" / "world_maps_v1")
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
