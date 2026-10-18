#!/usr/bin/env python3
"""vector_plate_pyramid - offline vector tiles for the Chronon editorial map.

The editorial basemap (``chronon_editorial``) is NOT an Esri raster: every
256x256 tile is rendered locally from offline boundary data on warm paper,
with the same grammar as the Egypt/1-tonnellata scene (reference_map_italy:
SEA/LAND/BORDER/GRID). Zero network traffic, zero provider attribution
burnt into the frame.

Boundary sources (also recorded in render telemetry):
- Natural Earth 50m Admin 0 countries (public domain)
- ISTAT administrative boundaries via geoBoundaries, simplified (CC BY),
  drawn only over Italy
- No city labels, no roads: pins come from the grounded payload.

Interface mirrors DynamicTilePyramid exactly where FastPlateSampler and
render_dynamic_map_overlay touch it: ``tile_cache``, ``telemetry``,
``record_telemetry``, ``_fetch_single_tile`` and ``prefetch_tiles`` with the
same return shape, so the fail-closed gates (late fetches, fallbacks) keep
working unchanged. Tiles are cached on disk as PNG (lossless, deterministic).

All drawing is deterministic (no random): the acceptance gate requires
byte-identical frames.
"""

from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from threading import Lock

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
CATALOG_DIR = HERE.parents[1] / "catalog"
NE_COUNTRIES = CATALOG_DIR / "ne_50m_admin_0_countries.geojson"
ITALY_ADMIN_DIR = CATALOG_DIR / "italy_admin"

# NOTE: distro OpenCV (4.5.4) ships no PNG writer, so tiles cache as
# high-quality JPEG like the Esri tile cache. Rendering stays a pure
# function of (z, x, y): same input bytes decode identically every run,
# so the determinism gate is unaffected.
CACHE_DIR = Path("~/.cache/chronon-vector-plates").expanduser()
TILE_SUFFIX = ".jpg"
TILE_IMWRITE_PARAMS = [int(cv2.IMWRITE_JPEG_QUALITY), 95]

# BGR (cv2) paper palette, same grammar as reference_map_italy (RGB values
# converted): SEA paper, LAND fill, BORDER stroke, GRID graticule.
SEA = (245, 247, 247)
LAND = (224, 226, 226)
BORDER = (188, 190, 190)
GRID = (234, 236, 236)
ITALY_ADMIN_LINE = (170, 172, 172)

ITALY_BBOX = (6.5, 18.5, 35.0, 47.5)  # lon_min, lon_max, lat_min, lat_max

PROVENANCE = (
    "Natural Earth 50m Admin 0 (public domain); "
    "ISTAT administrative boundaries via geoBoundaries (CC BY 3.0); "
    "graticule rendered locally; no third-party raster tiles"
)

WEB_MERCATOR_LAT_LIMIT = 85.05112878


def _clamp_lat(lat: float) -> float:
    return min(max(lat, -WEB_MERCATOR_LAT_LIMIT), WEB_MERCATOR_LAT_LIMIT)


def _global_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    scale = 256.0 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(_clamp_lat(lat))
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) * 0.5 * scale
    return x, y


def _tile_latlon(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Lon/lat bbox of one tile (lon_min, lon_max, lat_min, lat_max)."""
    scale = 256.0 * (2 ** z)
    lon_min = (x * 256.0 / scale) * 360.0 - 180.0
    lon_max = ((x + 1) * 256.0 / scale) * 360.0 - 180.0
    n_top = math.pi - 2.0 * math.pi * (y * 256.0 / scale)
    n_bot = math.pi - 2.0 * math.pi * ((y + 1) * 256.0 / scale)
    lat_max = math.degrees(math.atan(math.sinh(n_top)))
    lat_min = math.degrees(math.atan(math.sinh(n_bot)))
    return lon_min, lon_max, lat_min, lat_max


def _graticule_step_deg(zoom: int) -> float:
    if zoom <= 6:
        return 10.0
    if zoom <= 8:
        return 5.0
    if zoom <= 10:
        return 2.0
    return 1.0


_countries_cache: list | None = None
_countries_lock = Lock()
_admin2_cache: list | None = None
# zoom -> list of (minx, maxx, miny, maxy, int32 global-px ring). Projected
# ONCE per zoom so per-tile work is bbox checks + cv2 rasterization (which
# releases the GIL); per-vertex Python projection per tile never happens.
_projected_cache: dict = {}
_projected_lock = Lock()


def _load_countries() -> list:
    global _countries_cache
    if _countries_cache is None:
        with _countries_lock:
            if _countries_cache is None:
                with open(NE_COUNTRIES, encoding="utf-8") as f:
                    features = json.load(f)["features"]
                _countries_cache = features
    assert _countries_cache is not None
    return _countries_cache


def _load_admin2() -> list:
    global _admin2_cache
    if _admin2_cache is None:
        path = ITALY_ADMIN_DIR / "geoBoundaries_ITA_ADM2.simplified.geojson"
        with open(path, encoding="utf-8") as f:
            _admin2_cache = json.load(f)["features"]
    assert _admin2_cache is not None
    return _admin2_cache


def _polygons(geometry: dict) -> list:
    if geometry.get("type") == "Polygon":
        return [geometry["coordinates"]]
    if geometry.get("type") == "MultiPolygon":
        return geometry["coordinates"]
    return []


def _ring_bbox(ring) -> tuple[float, float, float, float]:
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return min(lons), max(lons), min(lats), max(lats)


def _projected_rings(z: int) -> tuple[list, list]:
    """(country_rings, admin2_rings) pre-projected to global px at zoom z."""
    key = int(z)
    rings = _projected_cache.get(key)
    if rings is not None:
        return rings
    with _projected_lock:
        rings = _projected_cache.get(key)
        if rings is not None:
            return rings

        def project(features) -> list:
            out = []
            for feature in features:
                for polygon in _polygons(feature.get("geometry") or {}):
                    ring = polygon[0]
                    if len(ring) < 3:
                        continue
                    pts = np.array(
                        [_global_px(lat, lon, key) for lon, lat in ring],
                        dtype=np.float64,
                    )
                    out.append((pts[:, 0].min(), pts[:, 0].max(),
                                pts[:, 1].min(), pts[:, 1].max(),
                                np.round(pts).astype(np.int32)))
            return out

        rings = (project(_load_countries()), project(_load_admin2()))
        _projected_cache[key] = rings
        return rings


def render_vector_tile(z: int, x: int, y: int):
    """Render one 256x256 BGR paper tile. Pure function of (z, x, y)."""
    max_idx = 2 ** z
    img = np.full((256, 256, 3), SEA, dtype=np.uint8)
    if y < 0 or y >= max_idx:
        return img
    x = x % max_idx
    lon_min, lon_max, lat_min, lat_max = _tile_latlon(z, x, y)
    ox, oy = x * 256, y * 256

    # Graticule under the geography.
    step = _graticule_step_deg(z)
    lon = math.ceil(lon_min / step) * step
    while lon <= lon_max:
        gx, _ = _global_px(0.0, lon, z)
        px = int(round(gx - x * 256.0))
        if 0 <= px < 256:
            cv2.line(img, (px, 0), (px, 255), GRID, 1, cv2.LINE_AA)
        lon += step
    lat = math.ceil(lat_min / step) * step
    while lat <= lat_max:
        _, gy = _global_px(lat, 0.0, z)
        py = int(round(gy - y * 256.0))
        if 0 <= py < 256:
            cv2.line(img, (0, py), (255, py), GRID, 1, cv2.LINE_AA)
        lat += step

    country_rings, admin2_rings = _projected_rings(z)
    x0, x1 = ox, ox + 256
    y0, y1 = oy, oy + 256
    # Country land fill, then borders.
    for minx, maxx, miny, maxy, pts in country_rings:
        if maxx < x0 or minx > x1 or maxy < y0 or miny > y1:
            continue
        cv2.fillPoly(img, [pts - (ox, oy)], LAND, cv2.LINE_AA)
    for minx, maxx, miny, maxy, pts in country_rings:
        if maxx < x0 or minx > x1 or maxy < y0 or miny > y1:
            continue
        cv2.polylines(img, [pts - (ox, oy)], True, BORDER, 1, cv2.LINE_AA)
    # Italian provinces where the tile meets Italy.
    it = ITALY_BBOX
    if not (it[1] < lon_min or it[0] > lon_max or it[3] < lat_min or it[2] > lat_max):
        for minx, maxx, miny, maxy, pts in admin2_rings:
            if maxx < x0 or minx > x1 or maxy < y0 or miny > y1:
                continue
            cv2.polylines(img, [pts - (ox, oy)], True, ITALY_ADMIN_LINE, 1, cv2.LINE_AA)
    return img


class VectorPlatePyramid:
    """Offline drop-in for DynamicTilePyramid (editorial basemap only)."""

    def __init__(self):
        self.tile_cache: dict = {}
        self.telemetry = {
            "tile_disk_cache_hits": 0,
            "tile_disk_cache_misses": 0,
            "tile_network_fetches": 0,
            "tile_fallbacks": 0,
            "tile_bytes_downloaded": 0,
            "tile_fetch_ms": 0.0,
            "prefetch_tiles_requested": 0,
            "prefetch_tiles_memory_hits": 0,
            "prefetch_ms": 0.0,
            "late_tile_fetches": 0,
            # Tiles drawn locally by this renderer (never downloaded).
            # The Go validator admits them via misses ==
            # downloads + fallbacks + rendered_locally, only for the
            # editorial basemap.
            "tile_rendered_locally": 0,
        }
        self._telemetry_lock = Lock()
        self._cache_io_lock = Lock()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def record_telemetry(self, name: str, value=1) -> None:
        with self._telemetry_lock:
            self.telemetry[name] = self.telemetry.get(name, 0) + value

    def _fetch_single_tile(self, z: int, x: int, y: int):
        fetch_started = time.perf_counter()
        max_idx = 2 ** z
        x = x % max_idx
        if y < 0 or y >= max_idx:
            blank = np.full((256, 256, 3), SEA, dtype=np.uint8)
            return (z, x, y), blank
        tile_path = CACHE_DIR / str(z) / str(x) / f"{y}{TILE_SUFFIX}"
        with self._cache_io_lock:
            cached = tile_path.exists()
        if cached:
            try:
                img = cv2.imread(str(tile_path), cv2.IMREAD_COLOR)
                if img is not None and img.shape == (256, 256, 3):
                    self.record_telemetry("tile_disk_cache_hits")
                    self.record_telemetry("tile_fetch_ms",
                                          (time.perf_counter() - fetch_started) * 1000.0)
                    return (z, x, y), img
            except Exception:
                pass
            self.record_telemetry("tile_disk_cache_misses")
        else:
            self.record_telemetry("tile_disk_cache_misses")
        img = render_vector_tile(z, x, y)
        self.record_telemetry("tile_rendered_locally")
        try:
            with self._cache_io_lock:
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = tile_path.with_name(
                    f"{tile_path.stem}.{os.getpid()}.tmp{TILE_SUFFIX}")
                if not cv2.imwrite(str(tmp), img, TILE_IMWRITE_PARAMS):
                    raise RuntimeError(f"tile encode failed for {tile_path}")
                os.replace(tmp, tile_path)
        except Exception as exc:
            print(f"[VectorPlatePyramid] tile cache write failed z={z} x={x} y={y}: {exc}",
                  flush=True)
        self.record_telemetry("tile_fetch_ms",
                              (time.perf_counter() - fetch_started) * 1000.0)
        return (z, x, y), img

    def prefetch_tiles(self, tile_keys, max_workers: int = 12):
        started = time.perf_counter()
        normalized = set()
        for z, x, y in tile_keys:
            if z < 0:
                raise ValueError(f"invalid tile zoom {z}")
            max_idx = 2 ** z
            if 0 <= y < max_idx:
                normalized.add((z, x % max_idx, y))
        requested = len(normalized)
        missing = sorted(key for key in normalized if key not in self.tile_cache)
        self.record_telemetry("prefetch_tiles_requested", requested)
        self.record_telemetry("prefetch_tiles_memory_hits", requested - len(missing))
        if not missing:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self.record_telemetry("prefetch_ms", elapsed_ms)
            return {"requested": requested, "memory_hits": requested, "fetched": 0,
                    "elapsed_ms": elapsed_ms}
        workers = max(1, int(max_workers))
        print(f"[VectorPlatePyramid] Rendering exact plate coverage: {len(missing)} tiles, workers={workers}...",
              flush=True)
        fetched = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = {}
            next_key = iter(missing)
            for _ in range(min(len(missing), workers * 2)):
                key = next(next_key, None)
                if key is None:
                    break
                pending[pool.submit(self._fetch_single_tile, *key)] = key
            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    pending.pop(future)
                    key, image = future.result()
                    self.tile_cache[key] = image
                    fetched += 1
                    nxt = next(next_key, None)
                    if nxt is not None:
                        pending[pool.submit(self._fetch_single_tile, *nxt)] = nxt
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.record_telemetry("prefetch_ms", elapsed_ms)
        print(f"[VectorPlatePyramid] Exact tile render complete: requested={requested} fetched={fetched} "
              f"memory_hits={requested - len(missing)} elapsed_ms={elapsed_ms:.1f}.", flush=True)
        return {"requested": requested, "memory_hits": requested - len(missing),
                "fetched": fetched, "elapsed_ms": elapsed_ms}
