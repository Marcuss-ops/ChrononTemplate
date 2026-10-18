#!/usr/bin/env python3
"""geo_runtime - runtime generation of geo_camera_v1 renders.

The pipeline, end to end:

    text ("Roma, poi il Colosseo, infine Venezia")
      -> extract_places        LLM-free, heuristic + gazetteer geography parser
      -> geocode               checked-in offline catalog (Nominatim is opt-in)
      -> render                geo_camera_v1 shots (fast pool, verified sampler)
      -> concat                one continuous tour mp4 (ffmpeg concat demuxer)

Programmatic:

    from geo_runtime import GeoRuntime
    rt = GeoRuntime()
    tour = rt.render_tour("Roma poi Venezia con tilt", out=Path("out/tour.mp4"))
    print(tour.mp4, tour.stops[0].display_name)

CLI:

    geo_runtime.py "Roma poi il Colosseo e infine Venezia" --verify
    geo_runtime.py --repl

Place extraction is heuristic rather than NLP: quote names with lowercase
particles when ambiguity matters (for example, "Piazza dei Miracoli").
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

from geo_places import Place, Tour, extract_places, geocode
from geo_catalog import GeographicCatalog

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # the repo root (VeloxEditing), two levels up
for p in (str(ROOT / "Chronon3d/tools/cartography"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

WIDTH, HEIGHT, FPS = 1920, 1080, 30


def covered_zoom(sampler, lat: float, lon: float, zoom: float,
                 width: int = WIDTH, height: int = HEIGHT) -> float:
    """Return the zoom a prepared plate can actually show for this camera pose.

    When the camera zooms beyond the prepared tile coverage, the frame is
    rendered at the closest covered zoom instead of aborting the whole run.
    A RuntimeWarning is emitted so the lower detail is visible in the logs.
    """
    if sampler.can_sample(lat, lon, zoom, width, height):
        return zoom
    import warnings
    z_min = float(sampler.z_min)
    candidate = float(zoom)
    while candidate > z_min:
        candidate = max(z_min, candidate - 0.05)
        if sampler.can_sample(lat, lon, candidate, width, height):
            break
    warnings.warn(
        f"map zoom {zoom:.3f} is not covered by the prepared plates; "
        f"rendering at zoom {candidate:.3f} instead (lower detail)",
        RuntimeWarning, stacklevel=2)
    return candidate

# ---------------------------------------------------------------------------
# Place parsing and catalog/Nominatim lookup live in geo_places; keep these
# imported names visible here as a compatibility facade for existing map scripts.
# ---------------------------------------------------------------------------
def _format_wgs84(lat: float, lon: float) -> str:
    """Format coordinates without assuming the northern/eastern hemispheres."""
    lat_hemi = "N" if lat >= 0.0 else "S"
    lon_hemi = "E" if lon >= 0.0 else "W"
    return f"WGS84 {abs(lat):.6f} {lat_hemi} {abs(lon):.6f} {lon_hemi}"


def _smootherstep(p: float) -> float:
    """Module-level smootherstep: the C2 law, shared by the builders (and
    mirrored, not imported, inside the dependency-free self-test)."""
    t = max(0.0, min(1.0, p))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _latlon_to_global_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Pure Web Mercator projection matching dynamic_tile_pyramid exactly.

    The tour pose/gate only needs coordinate math, not the tile engine. Keeping
    this small operation local preserves the offline contract and avoids
    importing OpenCV just to compute a route zoom.
    """
    lat = max(-85.05112878, min(85.05112878, lat))
    lon = max(-180.0, min(180.0, lon))
    scale = 256.0 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) * 0.5 * scale
    return x, y



def _draw_country_outline(frame, iso: str, anchor, zoom: float, alpha: float) -> None:
    """Draw a real Natural Earth country border over the live tile camera."""
    import cv2
    import numpy as np
    from map_editorial import load_border
    from map_editorial_gpu import geo_project

    height, width = frame.shape[:2]
    border = load_border(iso)
    stroke = np.zeros_like(frame)
    for ring in border["polygons"]:
        pts = np.asarray([
            geo_project(lat, lon, anchor, zoom, width, height)
            for lon, lat in ring
        ], dtype=np.int32)
        if len(pts) < 4:
            continue
        if (pts[:, 0].max() < -8 or pts[:, 0].min() > width + 8 or
                pts[:, 1].max() < -8 or pts[:, 1].min() > height + 8):
            continue
        cv2.polylines(stroke, [pts.reshape(-1, 1, 2)], True,
                      (247, 249, 250), 2, cv2.LINE_AA)
    if not np.any(stroke):
        return
    from glow_primitive import composite_halo
    composite_halo(frame, stroke[:, :, 0], (250, 252, 255), sigma=5.0,
                   intensity=0.32 * alpha)
    cv2.addWeighted(frame, 1.0, stroke, 0.86 * alpha, 0, dst=frame)


_MUNICIPAL_BOUNDARIES = None


def _draw_municipal_outline(frame, municipality: str, anchor, zoom: float,
                            alpha: float) -> None:
    """Draw only the selected Italian comune perimeter on the live map."""
    import cv2
    import numpy as np
    from pathlib import Path
    from map_editorial_gpu import geo_project

    global _MUNICIPAL_BOUNDARIES
    if _MUNICIPAL_BOUNDARIES is None:
        path = (Path(__file__).resolve().parents[2] / "catalog" /
                "municipal_boundaries_garlasco_vigevano_pavia.geojson")
        _MUNICIPAL_BOUNDARIES = json.loads(path.read_text(encoding="utf-8"))
    key = " ".join(str(municipality).casefold().replace("’", "'").split())
    feature = next((f for f in _MUNICIPAL_BOUNDARIES["features"]
                    if " ".join(f["properties"]["name"].casefold().split()) == key), None)
    if feature is None:
        return
    height, width = frame.shape[:2]
    geometry = feature["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    stroke = np.zeros_like(frame)
    for polygon in polygons:
        # The first ring is the commune's exterior; holes are not borders to
        # emphasize in this city locator treatment.
        ring = polygon[0]
        pts = np.asarray([geo_project(lat, lon, anchor, zoom, width, height)
                          for lon, lat in ring], dtype=np.int32)
        if len(pts) < 4 or (pts[:, 0].max() < -8 or pts[:, 0].min() > width + 8 or
                            pts[:, 1].max() < -8 or pts[:, 1].min() > height + 8):
            continue
        cv2.polylines(stroke, [pts.reshape(-1, 1, 2)], True,
                      (247, 249, 250), 2, cv2.LINE_AA)
    if np.any(stroke):
        from glow_primitive import composite_halo
        composite_halo(frame, stroke[:, :, 0], (250, 252, 255), sigma=5.0,
                       intensity=0.20 * alpha)
        cv2.addWeighted(frame, 1.0, stroke, 0.90 * alpha, 0, dst=frame)


def _roll_bank(p: float) -> float:
    """Banking during post-dive phases: a sine that returns to zero."""
    return -8.0 * math.sin(max(0.0, min(1.0, p)) * math.pi)


def _draw_map_attribution(frame, basemap: str = "esri_sat") -> None:  # noqa: ANN001 - numpy/OpenCV image
    import cv2
    if basemap == "chronon_editorial":
        # Offline vector plate: no provider raster, so no credit is burnt
        # into the frame. Provenance (Natural Earth, ISTAT/geoBoundaries)
        # rides the render telemetry instead.
        return
    credits = {
        "esri_street": "Sources: Esri, DeLorme, HERE, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), MapmyIndia, TomTom",
        "esri_topo": "Sources: Esri, DeLorme, HERE, TomTom, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, swisstopo, MapmyIndia, GIS User Community",
        "esri_sat": "Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    }
    text = credits.get(basemap, "Sources: Esri and the GIS User Community")
    scale = max(0.25, min(0.36, frame.shape[1] / 1920 * 0.34))
    (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = 18, 20 + text_h
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - 8, y - text_h - 7),
                  (x + text_w + 8, y + baseline + 5), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, dst=frame)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale,
                (248, 246, 236), 1, cv2.LINE_AA)


def _draw_minimal_location_name(frame, name: str) -> None:  # noqa: ANN001 - numpy/OpenCV image
    """Add only the current place name, without the diagnostic HUD/card."""
    import cv2
    label = str(name or "").strip()
    if not label:
        return
    x, y = 44, frame.shape[0] - 44
    cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.78,
                (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.78,
                (255, 255, 255), 2, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Rendering: a ShotSpec builder per preset, honouring the fast harness contract
# ---------------------------------------------------------------------------
class _ShotBuilder:
    """Duck-types the fast_geo_camera builder contract for one shot."""

    def __init__(self, place: Place, preset: str, frames: int):
        if frames < 2:
            raise ValueError("a shot requires at least two frames")
        if preset not in {"dive", "tilt", "orbit", "metric", "earthrise", "space_to_street"}:
            raise ValueError(f"unsupported shot preset: {preset}")
        self.place = place
        self.preset = preset
        self.documentary_layers = {}
        # The fast_geo_camera harness contract (attribute names included).
        self.WIDTH, self.HEIGHT, self.FPS = WIDTH, HEIGHT, FPS
        self.TOTAL_FRAMES = frames
        self.FRAMES_TOTAL = frames          # legacy alias
        self.ZOOM_INDEX = 0                 # pose = (zoom, pitch, yaw, roll)
        self.allow_zoom_hold = preset == "metric"
        self.start_zoom = 5.2
        self.end_zoom = {"dive": 17.8, "tilt": 17.3, "orbit": 17.5,
                         "metric": 17.5}.get(preset, 17.5)
        self.ANCHORS = ((place.lat, place.lon),)
        self.PREPARE_ZMIN, self.PREPARE_ZMAX = 5, 18
    # -- motion law (GeoCameraRig schedules: dive 62% / tilt to 80%) ---------
    def pose(self, f: int):
        smootherstep, ROLL_AT = _smootherstep, _roll_bank
        motion_frames = max(2, self.TOTAL_FRAMES - getattr(self, "terminal_hold_frames", 0))
        # Keep any authored terminal hold stationary at the destination while
        # preserving the original camera move timing.
        f = min(f, motion_frames - 1)
        if getattr(self, "full_duration_zoom", False) and self.preset not in ("earthrise", "space_to_street"):
            e = smootherstep(f / max(1, motion_frames - 1))
            zoom = self.start_zoom + (self.end_zoom - self.start_zoom) * e
            return zoom, 0.0, 0.0, 0.0
        dive_end = round(motion_frames * 0.62)
        tilt_end = round(motion_frames * 0.80)
        if self.preset in ("earthrise", "space_to_street"):
            from geo_documentary import earthrise_zoom, space_to_street_zoom
            if self.preset == "earthrise":
                zoom, _route_draw_on = earthrise_zoom(
                    self.end_zoom, self.start_zoom, f / max(1, motion_frames - 1))
            else:
                zoom = space_to_street_zoom(
                    f / max(1, motion_frames - 1), self.start_zoom, self.end_zoom)
            return zoom, 0.0, 0.0, 0.0
        if self.preset == "dive" or f <= dive_end:
            e = smootherstep(f / max(1, dive_end))
            return self.start_zoom + (self.end_zoom - self.start_zoom) * e, 0.0, 0.0, 0.0
        if self.preset == "metric":
            return self.end_zoom, 0.0, 0.0, 0.0
        e = smootherstep((f - dive_end) / max(1, tilt_end - dive_end))
        yaw = (15.0 if self.preset == "orbit" else 0.0) * \
            smootherstep(max(0.0, (f - tilt_end) / max(1, motion_frames - tilt_end)))
        pitch = (35.0 if self.preset in ("tilt", "orbit") else 0.0) * e
        return self.end_zoom, pitch, yaw, ROLL_AT((f - dive_end) / max(1, tilt_end - dive_end))

    # -- frame rendering (the certified overlay stack, minus the chain tag) --
    def render_frame_fast(self, sampler, f: int):
        from render_geo_camera_canary import (
            draw_metric_reveal, draw_hud_overlay, warp_matrix, OVERSIZE,
        )
        from render_geo_camera_small_places import (
            draw_map_location_marker, draw_editorial_map_caption,
            MARKER_DRAWN_STYLES,
        )
        import cv2
        zoom, pitch, yaw, roll = self.pose(f)
        progress = f / (self.TOTAL_FRAMES - 1)
        gpu_map = bool(getattr(self, "minimal_map", False) and
                       getattr(sampler, "gpu_map_enabled", False))
        sample = sampler.sample_opencl if gpu_map else getattr(sampler, "sample", None)
        if sample is None:
            sample = sampler.sample_continuous
        if pitch < 0.5:
            frame = sample(self.place.lat, self.place.lon, zoom, WIDTH, HEIGHT)
        else:
            ow, oh = int(WIDTH * OVERSIZE), int(HEIGHT * OVERSIZE)
            plate = sample(self.place.lat, self.place.lon, zoom, ow, oh)
            H = warp_matrix(pitch, yaw, roll)
            frame = cv2.warpPerspective(plate, H, (WIDTH, HEIGHT),
                                        flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_REFLECT_101)
        # NOTE: chronon_editorial plates arrive as vector paper from
        # VectorPlatePyramid (offline boundaries, no Esri raster): no recolor
        # here, and no provider credit burnt into the frame. Provenance
        # (Natural Earth, ISTAT/geoBoundaries) rides the render telemetry.
        if getattr(self, "minimal_map", False):
            if getattr(self, "require_gpu_editorial", False) and not gpu_map:
                raise RuntimeError("editorial map requires the OpenCL GPU map sampler")
            # No map pin/beacon: use the same editorial title rail as the
            # Chronon map template, with the place name below the map image.
            composition = getattr(self, "map_composition", "") or ""
            from map_editorial import MAP_EDITORIAL_SCENES
            if composition in MAP_EDITORIAL_SCENES:
                from map_editorial_gpu import draw_editorial_scene_gpu
                from map_editorial_gpu import geo_project
                extras = list(getattr(self, "map_pin_extras", [{}]))
                pin_records = [{
                    "latitude": float(p.get("latitude", self.place.lat)),
                    "longitude": float(p.get("longitude", self.place.lon)),
                    "label": str(p.get("label", p.get("name", self.place.display_name or self.place.query))),
                    **(extras[i] if i < len(extras) else {}),
                } for i,p in enumerate(getattr(self, "editorial_pins", []))]
                if not pin_records:
                    pin_records = [{
                        "latitude": self.place.lat,
                        "longitude": self.place.lon,
                        "label": self.place.display_name or self.place.query,
                        **(extras[0] if extras else {}),
                    }]
                # Editorial scene: fixed country geography projected around
                # the camera anchor; all caller pins remain grounded.
                anchor = (self.place.lat, self.place.lon)

                def _project(lat, lon, _a=anchor, _z=zoom):
                    return geo_project(lat, lon, _a, _z, WIDTH, HEIGHT)

                frame = draw_editorial_scene_gpu(frame, composition, {
                    "W": WIDTH, "H": HEIGHT, "project": _project,
                    "pins": pin_records,
                    "basemap": getattr(self, "map_basemap", "esri_street"),
                }, progress)
                from map_editorial_gpu import gpu_counters
                self._last_gpu_overlay_counters = gpu_counters()
                return frame
            elif composition:
                from map_compositions import MAP_COMPOSITIONS
                if composition not in MAP_COMPOSITIONS:
                    raise ValueError(f"unsupported map composition: {composition}")
                from map_compositions import draw_composition
                from map_editorial_gpu import geo_project
                if isinstance(frame, cv2.UMat):
                    frame = frame.get()
                anchor = (self.place.lat, self.place.lon)
                extras = list(getattr(self, "map_pin_extras", []))
                source_pins = list(getattr(self, "editorial_pins", [])) or [{
                    "latitude": self.place.lat, "longitude": self.place.lon,
                    "label": self.place.display_name or self.place.query,
                }]
                pins = []
                for i, p in enumerate(source_pins):
                    lat = float(p.get("latitude", self.place.lat))
                    lon = float(p.get("longitude", self.place.lon))
                    x, y = geo_project(lat, lon, anchor, zoom, WIDTH, HEIGHT)
                    pins.append({**p, **(extras[i] if i < len(extras) else {}),
                                 "x": int(round(x)), "y": int(round(y)),
                                 "label": str(p.get("label") or p.get("id") or "Location")})
                draw_composition(frame, composition, pins, progress, WIDTH, HEIGHT,
                                 basemap=getattr(self, "map_basemap", ""))
                _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
                return cv2.UMat(frame) if gpu_map else frame
            # The standard caption/marker helpers use NumPy and Pillow. OpenCL
            # sampling returns cv2.UMat, so download only this fallback frame
            # before applying those CPU overlays.
            if gpu_map:
                frame = frame.get()
            label_animation = getattr(self, "map_label_animation", "none")
            frame = draw_editorial_map_caption(
                frame, self.place.display_name or self.place.query, progress,
                getattr(self, "map_typography", {}), label_animation)
            if label_animation in MARKER_DRAWN_STYLES:
                # Distinct styles own marker + text at the camera nadir
                # (the rail stays suppressed for them upstream).
                draw_map_location_marker(
                    frame, (WIDTH // 2, HEIGHT // 2),
                    self.place.display_name or self.place.query,
                    progress, label_animation)
            _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
            return frame
        if self.preset == "earthrise":
            from render_geo_camera_small_places import draw_route_glow
            from geo_documentary import earthrise_zoom
            route_progress = earthrise_zoom(self.start_zoom, self.end_zoom, progress)[1]
            route_end = (self.place.lat + 0.08, self.place.lon + 0.12)
            route_to = (self.place.lat + (route_end[0] - self.place.lat) * route_progress,
                        self.place.lon + (route_end[1] - self.place.lon) * route_progress)
            draw_route_glow(frame, (self.place.lat, self.place.lon), route_to,
                            (self.place.lat, self.place.lon), zoom, route_progress)
        documentary = self.documentary_layers
        pose = self.pose(f)
        camera_project = documentary.get("pose_project")
        if camera_project is not None:
            from geo_documentary import pose_label_anchor
            documentary["project"] = lambda lon, lat: pose_label_anchor(
                lat, lon, pose, camera_project)
        if self.preset == "space_to_street":
            from geo_documentary import draw_space_to_street
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.place.lon)*10000),
                                  round(HEIGHT/2 - (lat-self.place.lat)*10000)))
            draw_space_to_street(frame, project, progress,
                                 documentary.get("route_geojson"))
        elif documentary.get("route_geojson"):
            from geo_documentary import draw_geojson_lines
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.place.lon)*10000),
                                  round(HEIGHT/2 - (lat-self.place.lat)*10000)))
            draw_geojson_lines(frame, documentary["route_geojson"], project, progress,
                               color_bgr=tuple(documentary.get("route_color_bgr", (80,220,255))),
                               width=int(documentary.get("route_width", 3)))
        if documentary.get("camera_labels"):
            from geo_documentary import draw_camera_aligned_label
            for label in documentary["camera_labels"]:
                draw_camera_aligned_label(
                    frame, (float(label["latitude"]), float(label["longitude"])),
                    str(label["text"]), pose, documentary["pose_project"], progress,
                    color=tuple(label.get("color_bgr", (255,255,255))))
        if documentary.get("regions"):
            from geo_documentary import draw_geojson_regions
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.place.lon)*10000),
                                  round(HEIGHT/2 - (lat-self.place.lat)*10000)))
            draw_geojson_regions(frame, documentary["regions"], project, progress,
                                 values=documentary.get("values"),
                                 value_range=documentary.get("value_range"),
                                 fill_alpha=float(documentary.get("fill_alpha", .32)))
        if documentary.get("hotspots"):
            from geo_documentary import draw_radar_pulse
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.place.lon)*10000),
                                  round(HEIGHT/2 - (lat-self.place.lat)*10000)))
            for hot in documentary["hotspots"]:
                point = project(float(hot["longitude"]), float(hot["latitude"]))
                draw_radar_pulse(frame, (round(point[0]), round(point[1])), progress,
                                 color_bgr=tuple(hot.get("color_bgr", (40,80,255))))
        if documentary.get("hillshade") is not None:
            from geo_documentary import apply_hillshade
            frame = apply_hillshade(frame, documentary["hillshade"],
                                    float(documentary.get("hillshade_alpha", .25)))
        if self.preset == "metric":
            # Never fabricate a statistic: the runtime has no trusted metric
            # source yet, so make the missing data explicit in the reveal.
            draw_metric_reveal(
                frame, (WIDTH / 2, HEIGHT / 2), progress,
                title=self.place.short_name,
                sub=self.place.subtitle,
                metric="METRIC DATA NOT PROVIDED",
            )
        else:
            draw_metric_reveal(
                frame, (WIDTH / 2, HEIGHT / 2), progress,
                title=self.place.short_name,
                sub=self.place.subtitle,
                metric=_format_wgs84(self.place.lat, self.place.lon),
            )
        draw_hud_overlay(frame, self.place.lat, self.place.lon, zoom, progress,
                         target_title=f"{self.place.short_name} (GEO CAMERA V1)")
        _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
        return frame


class TourBuilder:
    """One continuous shot: dive to each stop in sequence, glow-route leg
    between stops, spring pin on arrival. The 'subsequent animation'."""

    def __init__(self, stops: list[Place], seconds_per_stop: float = 5.0,
                 travel_seconds: float = 3.0, end_zoom: float = 16.5,
                 beat_events: list[dict] | None = None):
        if seconds_per_stop <= 0.0 or travel_seconds <= 0.0:
            raise ValueError("tour stop and travel durations must be positive")
        self.stops = [s for s in stops if s.ok]
        if not self.stops:
            raise ValueError("a tour requires at least one geocoded stop")
        self.sps = seconds_per_stop
        self.travel = travel_seconds
        self.end_zoom = end_zoom
        self.WIDTH, self.HEIGHT, self.FPS = WIDTH, HEIGHT, FPS
        leg = max(1, int(travel_seconds * FPS))
        self.TOTAL_FRAMES = max(2, int(seconds_per_stop * FPS) * len(self.stops)
                                + leg * (len(self.stops) - 1))
        self.FRAMES_TOTAL = self.TOTAL_FRAMES
        self.ZOOM_INDEX = 2                    # pose = (lat, lon, zoom)
        # Integer frame boundaries quantize short travel legs; allow a small
        # discrete overshoot over the nominal 2.0 continuity bound.
        self.ZOOM_VELOCITY_LIMIT = 2.1
        self.ANCHORS = tuple((s.lat, s.lon) for s in self.stops)
        span = max(abs(self.stops[0].lat - s.lat) + abs(self.stops[0].lon - s.lon)
                   for s in self.stops)
        # Wider tours need coarser landing zooms to stay inside the plate budget.
        self.PREPARE_ZMIN, self.PREPARE_ZMAX = 5, (17 if span < 0.5 else 15)
        self.end_zoom = min(end_zoom, 17 if span < 0.5 else 15.0)
        self.stop_end_zooms = [self.end_zoom] * len(self.stops)
        self.initial_zoom_fraction = 0.0
        self.stop_dive_fraction = 1.0
        # Route glow samples are static geographic points. Cache their base
        # zoom projection once; each integer map zoom is an exact power-of-two
        # scale of this Web Mercator pixel grid.
        self._route_points_by_zoom = {
            zoom: [
                tuple(_latlon_to_global_px(
                    a.lat + (b.lat - a.lat) * (sample / 25.0),
                    a.lon + (b.lon - a.lon) * (sample / 25.0), zoom)
                      for sample in range(26))
                for a, b in zip(self.stops, self.stops[1:])
            ]
            for zoom in range(5, 19)
        }
        self._stop_points_by_zoom = {
            zoom: tuple(_latlon_to_global_px(stop.lat, stop.lon, zoom)
                        for stop in self.stops)
            for zoom in range(5, 19)
        }
        self._route_overlay_buffer = None
        self.beat_events = [dict(event) for event in (beat_events or [])]
        schedule_end = self._schedule_end_frame()
        for event in self.beat_events:
            frame = int(event["frame"])
            if frame < 0 or frame >= schedule_end:
                raise ValueError(f"beat event frame {frame} exceeds tour schedule end {schedule_end}")

    def _schedule_end_frame(self) -> int:
        if getattr(self, "country_intro", False):
            return int(self.TOTAL_FRAMES)
        reductions = getattr(self, "_stop_frame_reductions", ())
        total = 0
        for i in range(len(self.stops)):
            stop_frames = (max(2, int(getattr(self, "initial_stop_frames", int(self.sps * self.FPS))))
                           if i == 0 else int(self.sps * self.FPS))
            if i < len(reductions):
                stop_frames = max(2, stop_frames - int(reductions[i]))
            total += stop_frames
            if i < len(self.stops)-1:
                travel_seconds = (getattr(self, "initial_travel_seconds", self.travel)
                                  if i == 0 and getattr(self, "country_intro", False)
                                  else self.travel)
                total += max(1, int(round(travel_seconds * self.FPS)))
        return total

    # timeline: [dive i][travel i->i+1][dive i+1]...
    def _schedule(self):
        frames_per = int(self.sps * self.FPS)

        initial_frames = max(2, int(getattr(self, "initial_stop_frames", frames_per)))
        marks = []
        f = 0
        reductions = getattr(self, "_stop_frame_reductions", ())
        for i in range(len(self.stops)):
            stop_frames = initial_frames if i == 0 else frames_per
            if i < len(reductions):
                stop_frames -= int(reductions[i])
            stop_frames = max(2, stop_frames)
            marks.append((f, f + stop_frames, i))
            f += stop_frames
            if i < len(self.stops) - 1:
                travel_seconds = (getattr(self, "initial_travel_seconds", self.travel)
                                  if i == 0 and getattr(self, "country_intro", False)
                                  else self.travel)
                leg = max(1, int(round(travel_seconds * self.FPS)))
                marks.append((f, f + leg, i, i + 1))
                f += leg
        # Beat events annotate authored route/pin actions; keep them out of
        # the contiguous camera-phase list so pose and velocity gates remain
        # an exact partition of the timeline.
        return marks

    def _beat_events_at(self, frame: int) -> list[dict]:
        return [event for event in self.beat_events
                if int(event["frame"]) == frame]

    def _zoom_gate_phases(self):
        """Split a route leg's pullback and dive into separate zoom laws.

        The geographic pan between them intentionally holds zoom steady; it
        must not dilute either smootherstep phase's velocity budget.
        """
        phases = []
        for mark in self._schedule():
            if len(mark) == 3 and isinstance(mark[2], int):
                active_end = (mark[0] + round((mark[1] - mark[0]) * self.stop_dive_fraction)
                              if self.stop_dive_fraction < 1.0 else mark[1])
                stop_reveal_zooms = getattr(self, "stop_reveal_zooms", None)
                if stop_reveal_zooms is not None:
                    span = min(mark[1], max(mark[0] + 1, active_end)) - mark[0]
                    first = mark[0] + max(1, round(span * self.stop_reveal_start_fraction))
                    second = mark[0] + max(first - mark[0] + 1,
                                           round(span * self.stop_reveal_hold_fraction))
                    phases.extend(((mark[0], min(first, active_end)),
                                   (min(second, active_end - 1), active_end)))
                else:
                    phases.append((mark[0], min(mark[1], max(mark[0] + 1, active_end))))
                continue
            start, end = mark[0], mark[1]
            if (len(mark) == 4 and isinstance(mark[2], int) and mark[2] == 0
                    and getattr(self, "country_intro", False)):
                phases.append((start, end))
                continue
            span = end - start
            out_end = min(end - 2, max(start + 1, start + round(span * 0.40)))
            in_start = min(end - 1, max(out_end + 1, start + round(span * 0.60)))
            phases.extend(((start, out_end), (in_start, end)))
        return phases

    def pose(self, f: int):
        smootherstep = _smootherstep
        for m in self._schedule():
            if m[0] <= f < m[1]:
                if len(m) == 3 and isinstance(m[2], int):  # dive/hold on stop i
                    i = m[2]
                    s = self.stops[i]
                    target = self.stop_end_zooms[i]
                    stop_start_zooms = getattr(self, "stop_start_zooms", None)
                    if stop_start_zooms is not None:
                        z_start = stop_start_zooms[i]
                    else:
                        z_start = (5.2 + (target - 5.2) * self.initial_zoom_fraction
                                   if i == 0 else self.stop_end_zooms[i - 1])
                    if getattr(self, "country_intro", False) and i == 1:
                        z_start = target
                    active_end = (m[0] + round((m[1] - m[0]) * self.stop_dive_fraction)
                                  if self.stop_dive_fraction < 1.0 else m[1])
                    active_end = min(m[1], max(m[0] + 1, active_end))
                    active_frames = active_end - m[0]
                    phase = (1.0 if active_frames <= 1 else
                             (f - m[0]) / (active_frames - 1))
                    reveal_zooms = getattr(self, "stop_reveal_zooms", None)
                    if reveal_zooms is not None:
                        reveal_zoom = reveal_zooms[i]
                        reveal_start = self.stop_reveal_start_fraction
                        reveal_hold_end = self.stop_reveal_hold_fraction
                        if phase < reveal_start:
                            q = smootherstep(phase / max(reveal_start, 1e-6))
                            zoom_here = z_start + (reveal_zoom - z_start) * q
                        elif phase < reveal_hold_end:
                            zoom_here = reveal_zoom
                        else:
                            q = smootherstep((phase - reveal_hold_end) /
                                             max(1e-6, 1.0 - reveal_hold_end))
                            zoom_here = reveal_zoom + (target - reveal_zoom) * q
                        return (s.lat, s.lon, zoom_here)
                    dive = smootherstep(min(1.0, phase))
                    return (s.lat, s.lon, z_start + (target - z_start) * dive)
                # travel leg i -> i+1: pull out to the midpoint zoom, glide,
                # re-dive. The zoom eases the RAW fraction once per half -
                # easing the already-smoothed p would compound the slopes
                # (smootherstep o smootherstep peaks at 3.5x the mean) and
                # snap past the gate.
                i, j = m[2], m[3]
                a, b = self.stops[i], self.stops[j]
                raw = (f - m[0]) / max(1, m[1] - m[0] - 1)
                if i == 0 and getattr(self, "country_intro", False):
                    p = smootherstep(raw)
                    start_zoom = self.stop_end_zooms[0]
                    end_zoom = self.stop_end_zooms[1]
                    return (a.lat + (b.lat - a.lat) * p,
                            a.lon + (b.lon - a.lon) * p,
                            start_zoom + (end_zoom - start_zoom) * p)
                # Pull back before panning so the complete leg stays visible,
                # then dive toward the next stop. The old 1.2-level pullback
                # left the camera nearly at street scale while crossing whole
                # regions, which looked like a broken infinite zoom.
                ax, ay = _latlon_to_global_px(a.lat, a.lon, 5)
                bx, by = _latlon_to_global_px(b.lat, b.lon, 5)
                distance = math.hypot(bx - ax, by - ay)
                route_zoom = 5.0 + math.log2((0.72 * self.WIDTH) / max(distance, 1.0))
                route_zoom = max(5.2, min(self.end_zoom, route_zoom))
                # Nearby destinations already fit at the landing scale. A
                # fractional-level pullback creates a visible bobble and a
                # non-zero phase seam; pan smoothly at constant zoom instead.
                stop_start_zooms = getattr(self, "stop_start_zooms", None)
                settled_start_i = (self.stop_end_zooms[i] if stop_start_zooms is None
                                   else stop_start_zooms[i])
                settled_start_j = (self.stop_end_zooms[j] if stop_start_zooms is None
                                   else stop_start_zooms[j])
                if (abs(self.stop_end_zooms[i] - self.stop_end_zooms[j]) < 1e-9
                        and abs(settled_start_i - self.stop_end_zooms[i]) < 1e-9
                        and abs(settled_start_j - self.stop_end_zooms[j]) < 1e-9
                        and route_zoom >= self.stop_end_zooms[i] - 1.0):
                    p = smootherstep(raw)
                    return (a.lat + (b.lat - a.lat) * p,
                            a.lon + (b.lon - a.lon) * p,
                            self.stop_end_zooms[i])
                stop_start_zooms = getattr(self, "stop_start_zooms", None)
                arrival_zoom = (stop_start_zooms[j] if stop_start_zooms is not None
                                else (self.stop_end_zooms[j - 1] if j > 0 else self.end_zoom))
                out_end = min(m[1] - 2, max(m[0] + 1,
                                            m[0] + round((m[1] - m[0]) * 0.40)))
                in_start = min(m[1] - 1, max(out_end + 1,
                                              m[0] + round((m[1] - m[0]) * 0.60)))
                if f < out_end:
                    out_frames = out_end - m[0]
                    e = (1.0 if out_frames <= 1 else
                         smootherstep((f - m[0]) / (out_frames - 1)))
                    return (a.lat, a.lon,
                            self.stop_end_zooms[i] + (route_zoom - self.stop_end_zooms[i]) * e)
                if f < in_start:
                    pan_frames = in_start - out_end
                    e = (1.0 if pan_frames <= 1 else
                         smootherstep((f - out_end) / (pan_frames - 1)))
                    return (a.lat + (b.lat - a.lat) * e,
                            a.lon + (b.lon - a.lon) * e, route_zoom)
                dive_frames = m[1] - in_start
                e = (1.0 if dive_frames <= 1 else
                     smootherstep((f - in_start) / (dive_frames - 1)))
                return (b.lat, b.lon,
                        route_zoom + (arrival_zoom - route_zoom) * e)
        s = self.stops[-1]
        return (s.lat, s.lon, self.end_zoom)

    def render_frame_fast(self, sampler, f: int):
        import math as _math
        import numpy as np
        import cv2
        from render_geo_camera_canary import draw_metric_reveal, draw_hud_overlay
        from render_geo_camera_small_places import (
            draw_map_location_marker, draw_editorial_map_caption,
            MARKER_DRAWN_STYLES,
            draw_route_glow, draw_spring_pin,
        )
        lat, lon, zoom = self.pose(f)
        zoom = covered_zoom(sampler, lat, lon, zoom, WIDTH, HEIGHT)
        progress = f / (self.FRAMES_TOTAL - 1)
        gpu_map = bool(getattr(self, "minimal_map", False) and
                       getattr(sampler, "gpu_map_enabled", False))
        if gpu_map:
            frame = sampler.sample_opencl(lat, lon, zoom, WIDTH, HEIGHT)
        else:
            frame = sampler.sample(lat, lon, zoom, WIDTH, HEIGHT)
        epoch_sampler = getattr(self, "epoch_before_sampler", None)
        if epoch_sampler is not None:
            from geo_documentary import diagonal_wipe
            if not gpu_map:
                raise RuntimeError("dual-epoch comparison requires the OpenCL map sampler")
            before = epoch_sampler.sample_opencl(lat, lon, zoom, WIDTH, HEIGHT)
            frame = diagonal_wipe(before, frame, progress, frame_shape=(HEIGHT, WIDTH))
        if getattr(self, "minimal_map", False):
            if getattr(self, "require_gpu_editorial", False) and not gpu_map:
                raise RuntimeError("editorial map requires the OpenCL GPU map sampler")
            location_name = ""
            active_stop = None
            label_progress = progress
            for mark in self._schedule():
                if (len(mark) == 3 and isinstance(mark[2], int)
                        and mark[0] <= f < mark[1]):
                    if mark[2] in getattr(self, "hidden_stop_indices", ()):
                        break
                    active_stop = self.stops[mark[2]]
                    location_name = active_stop.display_name or active_stop.query
                    label_progress = (f - mark[0]) / max(1, mark[1] - mark[0] - 1)
                    break
            # Keep the final city visible during the renderer's reserved tail
            # hold. During travel, hide the previous pin/label so it cannot
            # appear to identify the destination the camera is approaching.
            schedule = self._schedule()
            if active_stop is None and self.stops and f >= schedule[-1][1]:
                active_stop = self.stops[-1]
                location_name = active_stop.display_name or active_stop.query
                label_progress = 1.0
            composition = getattr(self, "map_composition", "") or ""
            if composition:
                # Geo-anchored outlines/routes use the identical tile-sampler
                # projection at each current camera pose. Keep frame pixels as
                # UMat through all full-frame effects and composites.
                from map_editorial_gpu import (
                    draw_editorial_scene_gpu, geo_project, gpu_counters,
                )
                from map_editorial import MAP_EDITORIAL_SCENES
                if composition in MAP_EDITORIAL_SCENES:
                    lat_c, lon_c, zoom_c = lat, lon, zoom
                    extras = list(getattr(self, "map_pin_extras", []))
                    pins = []
                    for i, s in enumerate(self.stops):
                        sx, sy = geo_project(s.lat, s.lon, (lat_c, lon_c),
                                             zoom_c, WIDTH, HEIGHT)
                        if composition in ("ed_yemen_markers",):
                            ex = extras[i] if i < len(extras) else {}
                            pins.append({"latitude": s.lat, "longitude": s.lon,
                                         "label": s.display_name or s.query, **ex})
                        elif -200 <= sx <= WIDTH + 200 and -200 <= sy <= HEIGHT + 200:
                            ex = extras[i] if i < len(extras) else {}
                            pins.append({"latitude": s.lat, "longitude": s.lon,
                                         "label": s.display_name or s.query, **ex})
                    if pins or composition in ("ed_saudi_base", "ed_iran_glow",
                                                 "ed_yemen_fill", "ed_hormuz_routes",
                                                 "ed_mocha_tactical"):
                        anchor = (lat_c, lon_c)

                        def _project(lat, lon, _a=anchor, _z=zoom_c):
                            return geo_project(lat, lon, _a, _z, WIDTH, HEIGHT)

                        frame = draw_editorial_scene_gpu(frame, composition, {
                            "W": WIDTH, "H": HEIGHT, "project": _project,
                            "pins": pins,
                        }, progress)
                    self._last_gpu_overlay_counters = gpu_counters()
                    return frame
                # The production path uses OpenCL for its tile plate. Classic
                # compositions without a dedicated GPU scene keep their camera
                # move and use the standard GPU-safe place caption.
                from map_compositions import MAP_COMPOSITIONS
                if composition not in MAP_COMPOSITIONS:
                    raise ValueError(f"unsupported map composition: {composition}")
                from map_compositions import draw_composition
                from map_editorial_gpu import geo_project
                was_gpu_frame = isinstance(frame, cv2.UMat)
                if was_gpu_frame:
                    frame = frame.get()
                extras = list(getattr(self, "map_pin_extras", []))
                pins = []
                for i, stop in enumerate(self.stops):
                    x, y = geo_project(stop.lat, stop.lon, (lat, lon), zoom,
                                       WIDTH, HEIGHT)
                    ex = extras[i] if i < len(extras) else {}
                    pins.append({"latitude": stop.lat, "longitude": stop.lon,
                                 "label": stop.display_name or stop.query,
                                 **ex, "x": int(round(x)), "y": int(round(y))})
                draw_composition(frame, composition, pins, progress, WIDTH, HEIGHT,
                                 basemap=getattr(self, "map_basemap", ""))
                _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
                return cv2.UMat(frame) if was_gpu_frame else frame
            # Editorial captions and the attribution helper are Pillow/NumPy
            # overlays and inspect ndarray dimensions. Keep the tile sample
            # and camera on OpenCL, but cross to host memory for these final
            # layers, then restore UMat for the GPU encoder.
            was_gpu_frame = isinstance(frame, cv2.UMat)
            if was_gpu_frame:
                frame = frame.get()
            label_animation = getattr(self, "map_label_animation", "none")
            frame = draw_editorial_map_caption(
                frame, location_name, label_progress, getattr(self, "map_typography", {}),
                label_animation)
            if label_animation in MARKER_DRAWN_STYLES:
                draw_map_location_marker(
                    frame, (WIDTH // 2, HEIGHT // 2), location_name,
                    label_progress, label_animation)
            country_iso = getattr(self, "country_outline_iso", "")
            if country_iso and zoom <= 8.2:
                outline_alpha = min(1.0, (f + 1) / max(1.0, self.FPS * 0.25))
                _draw_country_outline(frame, country_iso, (lat, lon), zoom,
                                      outline_alpha)
            municipal_outline = bool(getattr(self, "municipal_outline", False))
            if municipal_outline and active_stop is not None:
                # First settle on the comune, reveal its border, then dissolve
                # the border during the final city zoom. Travel frames have no
                # active_stop, so neither the outline nor previous tag leaks
                # into the next destination.
                glow_start = getattr(self, "stop_reveal_start_fraction", 0.25)
                glow_end = glow_start + 0.05
                outline_alpha = min(1.0, max(0.0,
                                     (label_progress - glow_start) / (glow_end - glow_start)))
                fade = max(0.0, min(1.0, (11.8 - zoom) / 0.9))
                outline_alpha *= fade
                _draw_municipal_outline(frame, active_stop.query,
                                        (lat, lon), zoom, outline_alpha)
            _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
            # The host copy is already needed for Pillow labels and CPU-only
            # border layers. Return it directly: re-uploading only for the
            # encoder to download again added a redundant GPU round trip.
            return frame

        # the route so far, glowing under the camera
        zf = int(zoom // 1)
        scale = 2.0 ** (zoom - zf)
        ax, ay = _latlon_to_global_px(lat, lon, zf)
        route_points = self._route_points_by_zoom.get(zf)
        stop_points = self._stop_points_by_zoom.get(zf)
        if route_points is None or stop_points is None:
            # Production cameras are clamped to integer zooms 5..18; retain a
            # correct uncommon out-of-band behavior for direct API callers.
            route_points = [
                tuple(_latlon_to_global_px(
                    a.lat + (b.lat - a.lat) * (sample / 25.0),
                    a.lon + (b.lon - a.lon) * (sample / 25.0), zf)
                      for sample in range(26))
                for a, b in zip(self.stops, self.stops[1:])
            ]
            stop_points = tuple(_latlon_to_global_px(stop.lat, stop.lon, zf)
                                for stop in self.stops)
        overlay = getattr(self, "_route_overlay_buffer", None)
        if overlay is None or overlay.shape != frame.shape or overlay.dtype != frame.dtype:
            overlay = np.empty_like(frame)
            self._route_overlay_buffer = overlay
        overlay.fill(0)
        done_until = f
        for (m0, m1, *idx) in self._schedule():
            if len(idx) == 2 and isinstance(idx[0], int) and m1 <= f:  # finished travel leg: full glow
                for px, py in route_points[idx[0]]:
                    sx, sy = int(WIDTH / 2 + (px - ax) * scale), int(HEIGHT / 2 + (py - ay) * scale)
                    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                        cv2.circle(overlay, (sx, sy), 4, (60, 240, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.85, frame, 1.0, 0, dst=frame)

        # arrival pin on the stop the camera is diving into
        for (m0, m1, *idx) in self._schedule():
            if len(idx) == 1 and isinstance(idx[0], int) and m0 <= f < m1 + int(0.4 * self.FPS):
                stop_px, stop_py = stop_points[idx[0]]
                sx = int(WIDTH / 2 + (stop_px - ax) * scale)
                sy = int(HEIGHT / 2 + (stop_py - ay) * scale)
                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                    draw_spring_pin(frame, (sx, sy), (f - m0 + int(0.4 * self.FPS))
                                    / (m1 - m0 + int(0.4 * self.FPS)), fire=0.80, span=0.12)

        for event in getattr(self, "beat_events", []):
            if int(event["frame"]) != f:
                continue
            action = event.get("action", "pin")
            if action == "route":
                draw_route_glow(frame, (lat, lon),
                                (lat + 0.02, lon + 0.02), (lat, lon), zoom, 1.0)
            elif action == "pin":
                draw_spring_pin(frame, (WIDTH // 2, HEIGHT // 2), 1.0,
                                fire=0.9, span=0.12)
            else:
                raise ValueError(f"unsupported beat event action: {action!r}")

        documentary = getattr(self, "documentary_layers", {})
        if documentary.get("route_geojson"):
            from geo_documentary import draw_geojson_lines
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.stops[0].lon)*10000),
                                  round(HEIGHT/2 - (lat-self.stops[0].lat)*10000)))
            draw_geojson_lines(frame, documentary["route_geojson"], project,
                               progress, color_bgr=tuple(documentary.get("route_color_bgr", (80,220,255))),
                               width=int(documentary.get("route_width", 3)))
        if documentary.get("regions"):
            from geo_documentary import draw_geojson_regions
            project = documentary.get("project") or (
                lambda lon, lat: (round(WIDTH/2 + (lon-self.stops[0].lon)*10000),
                                  round(HEIGHT/2 - (lat-self.stops[0].lat)*10000)))
            draw_geojson_regions(
                frame, documentary["regions"], project, progress,
                values=documentary.get("values"),
                value_range=documentary.get("value_range"),
                fill_alpha=float(documentary.get("fill_alpha", 0.32)))
        if documentary.get("hotspots"):
            from geo_documentary import draw_radar_pulse
            for hot in documentary["hotspots"]:
                project = documentary.get("project") or (
                    lambda lon, lat: (round(WIDTH/2 + (lon-self.stops[0].lon)*10000),
                                      round(HEIGHT/2 - (lat-self.stops[0].lat)*10000)))
                hx, hy = project(float(hot["longitude"]), float(hot["latitude"]))
                draw_radar_pulse(frame, (round(hx), round(hy)), progress,
                                 color_bgr=tuple(hot.get("color_bgr", (40,80,255))))
        if documentary.get("hillshade") is not None:
            from geo_documentary import apply_hillshade
            frame = apply_hillshade(frame, documentary["hillshade"],
                                    float(documentary.get("hillshade_alpha", 0.25)))
        draw_hud_overlay(frame, lat, lon, zoom, progress,
                         target_title="GEO RUNTIME TOUR")
        _draw_map_attribution(frame, getattr(self, "map_basemap", "esri_sat"))
        return frame



# ---------------------------------------------------------------------------
# The acceptance gate. No render leaves this module without it.
# ---------------------------------------------------------------------------
_NOISE = 1e-9  # float noise floor: a hold still jitters its last ulp


def _zoom_tv(zooms: list[float], s0: int, s1: int) -> float:
    """Total variation of the zoom trace over [s0, s1), counting only steps
    above float noise: a smootherstep hold still jitters its last ulp around
    the landing value, and that noise would otherwise inflate the TV of short
    phases and deflate the velocity bound built on it."""
    return sum(d for g in range(s0 + 1, s1)
               if (d := abs(zooms[g] - zooms[g - 1])) > 1e-9)


def _pose_zoom(builder, frame: int) -> float:  # noqa: ANN001 - duck-typed builder
    """Read zoom from the explicitly documented pose layout of each builder."""
    pose = builder.pose(frame)
    zoom_index = getattr(builder, "ZOOM_INDEX", None)

    if zoom_index is None:
        raise TypeError(f"{type(builder).__name__} must declare ZOOM_INDEX")
    return float(pose[zoom_index])


def fit_initial_stop_frames(builder, minimum_final_hold_frames: int = 0) -> int:  # noqa: ANN001 - duck-typed builder
    """Choose the shortest first-stop duration that passes the strict gate.

    Tour stop durations are quantized to whole frames. For particular zoom
    spans, an even/odd frame count can put the sampled smootherstep peak just
    above the relative velocity bound. Try only the next few frame counts and
    never consume the caller's reserved final hold. Other stop/travel durations
    remain untouched. Raises the original gate error when no fit exists.
    """
    base_frames = max(int(builder.sps * builder.FPS),
                      int(getattr(builder, "initial_stop_frames", 0)))
    builder.initial_stop_frames = base_frames
    base_stop_frames = max(2, int(builder.sps * builder.FPS))
    first_error = None
    for candidate in range(base_frames, base_frames + 8):
        # Opening-frame quantization can miss the strict slope limit by a
        # fraction of one frame. Reclaim those frame(s) from later camera
        # holds so the authored shot duration and reserved destination hold
        # remain unchanged; never relax the velocity gate.
        extra = candidate - base_frames
        reductions = [0] * len(builder.stops)
        remaining = extra
        for index in sorted(range(1, len(builder.stops)),
                            key=lambda i: (base_stop_frames - reductions[i], -i),
                            reverse=True):
            available = max(0, base_stop_frames - 2 - reductions[index])
            taken = min(available, remaining)
            reductions[index] += taken
            remaining -= taken
            if remaining == 0:
                break
        if remaining:
            break
        builder.initial_stop_frames = candidate
        builder._stop_frame_reductions = reductions
        scheduled_end = builder._schedule()[-1][1]
        if builder.TOTAL_FRAMES - scheduled_end < minimum_final_hold_frames:
            continue
        try:
            check_velocity_strict(builder)
            return candidate
        except RuntimeError as exc:
            if first_error is None:
                first_error = exc
    builder._stop_frame_reductions = [0] * len(builder.stops)
    builder.initial_stop_frames = base_frames
    if first_error is not None:
        raise first_error
    raise RuntimeError("no initial stop duration fits before the reserved final hold")


def check_velocity_strict(builder) -> int:  # noqa: ANN001 - duck-typed builder
    """Strict zoom-velocity continuity, phase-aware.

    The law 'max frame step <= 1.8751 x mean step' is the smootherstep slope
    and only means anything WITHIN one motion law. A tour is a sequence of
    laws, so when the builder exposes its phase schedule each phase is
    bounded on its own zoom TOTAL VARIATION (a leg that dives out and back
    in has near-zero net displacement but real velocity, and only TV sees
    it), and every junction between phases is checked separately: both ends
    of a smootherstep law have zero velocity, so a junction step must be a
    small fraction of the neighbouring phase's budget - a snap cannot hide
    there. Builders without a schedule fall back to monotone-run
    segmentation, where each run is exactly one law. Returns the phase count.
    """
    n = builder.TOTAL_FRAMES
    zooms = [_pose_zoom(builder, f) for f in range(n)]

    phase_schedule = getattr(builder, "_zoom_gate_phases", None)
    schedule = getattr(builder, "_schedule", None)
    if schedule is not None:
        spans = (phase_schedule() if phase_schedule is not None else
                 [(m[0], m[1] - 1) for m in schedule() if m[1] - m[0] >= 4])
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            # Route phases are sampled on integer frames. At a short or
            # stationary phase boundary, both local budgets can quantize to
            # zero even when the seam contains one quantized camera step. Keep
            # the strict relative bound for ordinary motion, with a 0.10-level
            # floor for short authored shots. At 24 fps this bounds a one-frame
            # scale change to about 7%; larger jumps still fail the gate.
            lim = max(0.10, min(
                0.8 * _zoom_tv(zooms, a0, a1) / max(1, a1 - a0),
                0.8 * _zoom_tv(zooms, b0, b1) / max(1, b1 - b0),
            ))
            # A hold can separate two active zoom phases. Comparing their
            # endpoints across that hold mistakes legitimate travel for a
            # single-frame jump. Check the actual one-frame seams instead.
            if b0 > a1:
                seam_steps = []
                if a1 < n:
                    seam_steps.append(abs(zooms[a1] - zooms[a1 - 1]))
                if b0 < n:
                    seam_steps.append(abs(zooms[b0] - zooms[b0 - 1]))
                step = max(seam_steps, default=0.0)
            else:
                step = abs(zooms[b0] - zooms[a1 - 1])
            if step > lim + 1e-4:
                raise RuntimeError(
                    f"velocity discontinuity at the {a1}/{b0} junction "
                    f"(step {step:.4f} > {lim:.4f})")
    else:
        spans = []
        f = 0
        while f < n - 1:
            if zooms[f] != zooms[f + 1]:
                s0 = f
                while f < n - 1 and zooms[f] != zooms[f + 1]:
                    f += 1
                spans.append((s0, f))
            else:
                f += 1
    if not spans:
        if getattr(builder, "allow_zoom_hold", False):
            return 0
        raise RuntimeError("the shot never moves")
    for s0, s1 in spans:
        tv = _zoom_tv(zooms, s0, s1)
        if tv <= 0.0:
            continue
        bound = getattr(builder, "ZOOM_VELOCITY_LIMIT", 1.8751) * tv / (s1 - s0)
        max_step = max(abs(zooms[g] - zooms[g - 1]) for g in range(s0 + 1, s1))
        if max_step > bound + 1e-6:
            raise RuntimeError(
                f"zoom snap in segment {s0}..{s1} (max {max_step:.4f} > "
                f"{getattr(builder, 'ZOOM_VELOCITY_LIMIT', 1.8751):.4f} x TV/span {bound:.4f})")
    return len(spans)


def gate_builder(builder, sampler, label: str) -> None:
    """The acceptance gate every render must pass before encoding."""
    n_seg = check_velocity_strict(builder)
    probe = builder.TOTAL_FRAMES // 2
    frame_a = builder.render_frame_fast(sampler, probe)
    frame_b = builder.render_frame_fast(sampler, probe)
    if hasattr(frame_a, "get"):
        frame_a = frame_a.get()

    if hasattr(frame_b, "get"):
        frame_b = frame_b.get()
    a, b = frame_a.tobytes(), frame_b.tobytes()
    if a != b:
        raise RuntimeError(f"[{label}] gate: frame {probe} is not deterministic")
    print(f"[gate] {label}: {n_seg} phase(s) velocity-strict PASS, "
          f"determinism PASS (frame {probe})", flush=True)


# ---------------------------------------------------------------------------
# The runtime facade
# ---------------------------------------------------------------------------
class GeoRuntime:
    def __init__(self, out_root: Path | None = None, workers: int = 4,
                 block: int = 10, preset_x264: str = "veryfast",
                 crf: int = 18, keep_individual: bool = False,
                          upload: bool = False, strict_native: bool = False,
                 wayback_release: int | None = None,
                 geographic_catalog_path: Path | None = None,
                 offline_geocoding: bool = True):
        # Canonical output home, next to every other camera_motion_v2 render.
        if workers < 1 or block < 1:
            raise ValueError("workers and block must be positive integers")
        self.out_root = Path(out_root or (HERE.parent / "out/camera_motion_v2/geo_runtime"))
        self.out_root.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.block = block
        self.preset_x264 = preset_x264
        self.crf = crf
        self.keep_individual = keep_individual
        self.upload = upload
        self.strict_native = bool(strict_native)
        self.wayback_release = wayback_release
        self.geographic_catalog_path = geographic_catalog_path
        self.offline_geocoding = bool(offline_geocoding)
        self._geographic_catalog = None
        self._geographic_catalog_unavailable = False
        if geographic_catalog_path is not None:
            self._geographic_catalog = GeographicCatalog(geographic_catalog_path)
        if wayback_release is not None and int(wayback_release) <= 0:
            raise ValueError("wayback_release must be positive")

    def _resolve_place(self, place: Place) -> Place:
        catalog = self._geographic_catalog
        if catalog is None and not self._geographic_catalog_unavailable:
            try:
                catalog = GeographicCatalog()
                self._geographic_catalog = catalog
            except FileNotFoundError:
                self._geographic_catalog_unavailable = True
        return geocode(place, offline_only=self.offline_geocoding,
                       catalog=catalog)

    def close(self) -> None:
        if self._geographic_catalog is not None:
            self._geographic_catalog.close()
            self._geographic_catalog = None

    def __enter__(self) -> "GeoRuntime":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- text -> resolved places ---------------------------------------------
    def resolve(self, text: str) -> Tour:
        tour = Tour(text=text)
        places = extract_places(text)
        if not places:
            raise ValueError(f"no places found in: {text!r}")
        print(f"[resolve] {len(places)} candidate(s): "
              f"{[p.query for p in places]}", flush=True)
        for pl in places:
            tour.stops.append(self._resolve_place(pl))
        return tour

    # -- one place -> one shot mp4 --------------------------------------------
    def render_place(self, place: Place, frames: int = 120,
                     out: Path | None = None, verify: bool = False) -> dict:
        if not place.ok:
            raise ValueError(f"place is not geocoded: {place.query}")
        if self.wayback_release is not None and place.preset != "earthrise":
            raise ValueError("wayback_release requires the earthrise preset")
        if place.preset not in {"dive", "tilt", "orbit", "metric", "earthrise", "space_to_street"}:
            raise ValueError(f"unsupported shot preset: {place.preset}")
        import fast_geo_camera as harness
        builder = _ShotBuilder(place, place.preset, frames)
        builder.documentary_layers = dict(getattr(place, "_documentary_layers", {}))
        builder.beat_events = [dict(event) for event in getattr(place, "_beat_events", [])]
        builder.epoch_before_sampler = None
        for event in builder.beat_events:
            event_frame = int(event["frame"])
            if event_frame < 0 or event_frame >= frames:
                raise ValueError(f"beat event frame {event_frame} exceeds shot length {frames}")
        if "hillshade_path" in builder.documentary_layers:
            import cv2
            hillshade_path = Path(builder.documentary_layers.pop("hillshade_path"))
            hillshade = cv2.imread(str(hillshade_path), cv2.IMREAD_GRAYSCALE)
            if hillshade is None:
                raise ValueError(f"could not read hillshade image: {hillshade_path}")
            builder.documentary_layers["hillshade"] = cv2.resize(
                hillshade, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
        documentary_provider = builder.documentary_layers.pop("provider", None)
        documentary_release = builder.documentary_layers.pop("wayback_release", None)
        builder.tile_provider = (str(documentary_provider) if documentary_provider else
                                 ("esri_wayback" if self.wayback_release is not None else "esri_sat"))
        builder.wayback_release = (self.wayback_release if self.wayback_release is not None
                                   else documentary_release)
        if builder.tile_provider == "esri_wayback" and builder.wayback_release is None:
            raise ValueError("esri_wayback documentary provider requires wayback_release")
        if builder.tile_provider == "esri_wayback" and place.preset != "earthrise":
            raise ValueError("Wayback tile provider requires the earthrise preset")
        builder.FPS = FPS
        builder.TOTAL_FRAMES = builder.FRAMES_TOTAL = int(frames)
        if place.preset in ("earthrise", "space_to_street"):
            builder.start_zoom, builder.end_zoom = (17.5, 5.5) if place.preset == "earthrise" else (5.0, 18.0)
        epoch_provider = builder.documentary_layers.pop("epoch_before_provider", None)
        epoch_release = builder.documentary_layers.pop("epoch_before_release", None)
        if epoch_provider is not None:
            from geo_documentary import build_epoch_sampler
            builder.epoch_before_sampler = build_epoch_sampler(
                str(epoch_provider), epoch_release, WIDTH, HEIGHT, builder.ANCHORS,
                builder.PREPARE_ZMIN, builder.PREPARE_ZMAX)
        self._check_native_runtime()
        sampler = harness.build_sampler(builder)
        if self.strict_native or builder.epoch_before_sampler is not None:
            builder.minimal_map = True
            builder.require_gpu_editorial = True
            sampler.prepare_opencl()
            sampler.gpu_map_enabled = True
            if builder.epoch_before_sampler is not None:
                builder.epoch_before_sampler.prepare_opencl()
                builder.epoch_before_sampler.gpu_map_enabled = True
        self._assert_no_fallback(sampler)
        gate_builder(builder, sampler, label=place.query)
        if verify:
            if not harness.verify_against_sampler(builder, sampler):
                raise RuntimeError(f"verify failed for {place.query}")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", place.query).strip("._") or "place"
        out = Path(out or (self.out_root / f"{safe_name}_{place.preset}.mp4"))
        out.parent.mkdir(parents=True, exist_ok=True)
        stats = harness.encode_with_pool(builder, sampler, out,
                                         self.workers, self.block,
                                         self.preset_x264, self.crf,
                                         gpu_required=self.strict_native)
        if getattr(sampler.pyr, "fallback_tile_count", 0):
            self._assert_no_fallback(sampler)
        if builder.epoch_before_sampler is not None:
            self._assert_no_fallback(builder.epoch_before_sampler)
        return stats

    def _assert_no_fallback(self, sampler) -> None:
        pyramid = getattr(sampler, "pyr", sampler)
        missing_tiles = int(getattr(pyramid, "fallback_tile_count", 0))
        if missing_tiles:
            raise RuntimeError(
                f"GeoRuntime fail-closed sampling gate failed: "
                f"fallback_tiles={missing_tiles}")

    def _check_native_runtime(self) -> None:
        if not self.strict_native:
            return
        import cv2
        import shutil
        if not cv2.ocl.haveOpenCL():
            raise RuntimeError("--strict-native requires OpenCL support")
        import numpy as np
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            raise RuntimeError("--strict-native could not activate OpenCL")
        probe = cv2.add(cv2.UMat(np.zeros((1,1), np.uint8)),
                        cv2.UMat(np.ones((1,1), np.uint8))).get()
        if int(probe[0, 0]) != 1:
            raise RuntimeError("--strict-native OpenCL probe did not produce the expected result")
        # OpenCV wheels expose the default device through two API spellings.
        device = (cv2.ocl.Device.getDefault() if hasattr(cv2.ocl, "Device")
                  else cv2.ocl.Device_getDefault())
        if "NVIDIA" not in device.vendorName().upper():
            raise RuntimeError(f"--strict-native requires NVIDIA OpenCL, got {device.name()}")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("--strict-native requires ffmpeg with h264_nvenc")
        probe = __import__("subprocess").run(
            [ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
            text=True, check=False)

        if probe.returncode or "h264_nvenc" not in probe.stdout:
            raise RuntimeError("--strict-native requires the h264_nvenc encoder")

    # -- tour -> concatenated mp4 ----------------------------------------------
    def render_tour(self, text: str, out: Path | None = None,
                    verify: bool = False) -> Tour:
        import fast_geo_camera as harness
        tour = self.resolve(text)
        stops = [s for s in tour.stops if s.ok]
        if not stops:
            raise RuntimeError("no geocodable stops")
        if len(stops) != len(tour.stops):
            unresolved = [s.query for s in tour.stops if not s.ok]
            raise RuntimeError("could not geocode every requested stop: "
                               + ", ".join(unresolved))

        if len(stops) == 1:
            builder = _ShotBuilder(stops[0], stops[0].preset, 120)
        else:
            beat_events = list(getattr(stops[0], "_beat_events", []))
            builder = TourBuilder(stops, beat_events=beat_events)
        self._check_native_runtime()
        sampler = harness.build_sampler(builder)
        if self.strict_native:
            builder.minimal_map = True
            builder.require_gpu_editorial = True
            sampler.prepare_opencl()
            sampler.gpu_map_enabled = True
        self._assert_no_fallback(sampler)
        # The gate always runs: velocity continuity per segment + determinism.
        gate_builder(builder, sampler, label=" ".join(s.short_name for s in stops))
        if verify and isinstance(builder, _ShotBuilder):
            # The independent slow engine path has been removed. The fast
            # sampler's coverage and deterministic-frame gate is authoritative.
            if not harness.verify_against_sampler(builder, sampler):
                raise RuntimeError("prepared-plate verification failed")
        elif verify and len(stops) > 1:
            print("[verify] multi-stop tour has no independent frame renderer; "
                  "phase and determinism gates passed instead", flush=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = Path(out or (self.out_root / f"tour_{stamp}.mp4"))
        out.parent.mkdir(parents=True, exist_ok=True)
        tour_stats = harness.encode_with_pool(
            builder, sampler, out, self.workers, self.block,
            self.preset_x264, self.crf, gpu_required=self.strict_native)
        if getattr(sampler.pyr, "fallback_tile_count", 0):
            self._assert_no_fallback(sampler)
        tour.stats.append(tour_stats)
        tour.mp4 = out
        if self.upload:
            from render_dynamic_map_3d_orbit_colosseum import (
                refresh_drive_token, upload_to_drive, DRIVE_FOLDER_ID)
            token = refresh_drive_token()
            res = upload_to_drive(out, token, DRIVE_FOLDER_ID)
            print(f"[drive] https://drive.google.com/file/d/{res.get('id')}/view",
                  flush=True)
        return tour

    # -- REPL --------------------------------------------------------------
    def repl(self) -> None:
        print("GeoRuntime REPL - scrivi un tour ('Roma poi Venezia con tilt'), "
              "'quit' per uscire.", flush=True)
        while True:
            try:
                line = input("geo> ").strip()
            except EOFError:
                break
            if line.lower() in ("", "quit", "exit", "q"):
                break
            try:
                tour = self.render_tour(line)
                print(f"  -> {tour.mp4}", flush=True)
            except Exception as exc:
                print(f"  error: {exc}", flush=True)


def self_test() -> int:
    """Offline acceptance: extraction, tour schedule, pose continuity.

    Dependency-free on purpose (standard library only, and the smootherstep
    law is mirrored locally rather than imported): a build gate runs on the
    interpreter CMake found with nothing installed into it, and an offline
    test that imported numpy would silently skip everywhere (see the
    map_cartography gate for the same discipline).
    """
    print("=== geo_runtime self-test (offline, stdlib-only) ===", flush=True)
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        print(("  PASS: " if cond else "  FAIL: ") + msg, flush=True)
        if not cond:
            failures.append(msg)

    # 1. Extraction: connectors split places, adjacency joins names,
    #    preset keywords attach forward, or backward after a comma.
    cases = [
        ("Roma poi il Colosseo e infine Venezia",
         [("Roma", "dive"), ("Colosseo", "dive"), ("Venezia", "dive")]),
        ("Lughetto, Campagna Lupia con tilt, Piazza San Marco",
         [("Lughetto", "dive"), ("Campagna Lupia", "tilt"),
          ("Piazza San Marco", "dive")]),
        ("Machu Picchu con orbita e poi Giza",
         [("Machu Picchu", "orbit"), ("Giza", "dive")]),
        ("Venezia con tilt", [("Venezia", "tilt")]),

        ("\"Piazza dei Miracoli\" con metric",
         [("Piazza dei Miracoli", "metric")]),
        ("Piazza dei Miracoli, Pisa",
         [("Piazza dei Miracoli", "dive"), ("Pisa", "dive")]),
        ("Stazione di Santa Lucia con orbita",
         [("Stazione di Santa Lucia", "orbit")]),
    ]
    for text, expected in cases:
        got = [(p.query, p.preset) for p in extract_places(text)]
        check(got == expected, f"extract {text!r} -> {got}")
    check(_format_wgs84(-33.8688, -151.2093)
          == "WGS84 33.868800 S 151.209300 W",
          "coordinate overlay formats southern and western hemispheres")

    # 2. Tour schedule: every frame belongs to exactly one phase; the last
    #    frame lands on the final stop at the landing zoom.
    stops = [Place(query="A", display_name="A", lat=45.38, lon=12.12, ok=True),
             Place(query="B", display_name="B", lat=45.35, lon=12.09, ok=True),
             Place(query="C", display_name="C", lat=45.44, lon=12.33, ok=True)]
    tb = TourBuilder(stops)
    phases = tb._schedule()

    covered = sum(m[1] - m[0] for m in phases)
    contiguous = (phases[0][0] == 0 and phases[-1][1] == tb.TOTAL_FRAMES
                  and all(a[1] == b[0] for a, b in zip(phases, phases[1:])))
    check(covered == tb.TOTAL_FRAMES and contiguous,
          f"tour phases cover the timeline without gaps/overlaps "
          f"({covered} == {tb.TOTAL_FRAMES})")
    route_points_exact = all(
        cached == tuple(_latlon_to_global_px(
            a.lat + (b.lat - a.lat) * (sample / 25.0),
            a.lon + (b.lon - a.lon) * (sample / 25.0), zoom)
                        for sample in range(26))
        for zoom, routes in tb._route_points_by_zoom.items()
        for route_index, (a, b) in enumerate(zip(stops, stops[1:]))
        for cached in (routes[route_index],)
    )
    check(route_points_exact,
          "cached tour glow projections exactly match the Web Mercator route geometry")
    last = tb.pose(tb.TOTAL_FRAMES - 1)
    check(abs(last[0] - stops[-1].lat) < 1e-9 and abs(last[1] - stops[-1].lon) < 1e-9
          and abs(last[2] - tb.end_zoom) < 1e-9,
          "the tour ends framed on its final stop at landing zoom")

    # 3. Production short-route quantization: a five-stop, 8-second shot at
    #    24 fps has an 8-frame first stop that fails the strict relative peak
    #    bound, while the next (9-frame) duration passes. Preserve the
    #    explicit 1.5-second final destination hold while fitting it.
    fit_stops = [Place(query=str(i), lat=45.5 - i * 0.05, lon=9.0 + i * 0.2, ok=True)
                 for i in range(5)]
    fit = TourBuilder(fit_stops, seconds_per_stop=0.34, travel_seconds=1.2, end_zoom=16.0)
    fit.FPS = 24
    fit.TOTAL_FRAMES = 192
    fit.FRAMES_TOTAL = 192
    fit.stop_end_zooms = [16.0] * len(fit_stops)
    fit.initial_zoom_fraction = 0.90
    fit.stop_dive_fraction = 1.0
    try:
        selected = fit_initial_stop_frames(fit, minimum_final_hold_frames=36)
        check(selected == 9 and check_velocity_strict(fit) > 0,
              f"short five-stop camera selects {selected} opening frames without weakening the gate")
        check(fit.TOTAL_FRAMES - fit._schedule()[-1][1] >= 36,
              "short five-stop camera preserves the full 1.5-second final hold")
    except RuntimeError as exc:
        check(False, f"short five-stop camera frame fit: {exc}")

    # Production route-count regressions: a three-stop itinerary fits its
    # 6.5-second camera window and preserves the reserved label hold, whereas
    # seven stops cannot fit and must fail closed (the production renderer caps
    # tours at five unique stops).
    for stop_count, should_fit in ((3, True), (7, False)):
        route_stops = [Place(query=str(i), lat=45.5 - i * 0.03,
                             lon=9.0 + i * 0.05, ok=True)
                       for i in range(stop_count)]
        route_travel = min(1.6, max(1.2, 6.5 / (1.9 * (stop_count - 1))))
        route_stop = max(0.15, (6.5 - route_travel * (stop_count - 1)) / stop_count)
        route = TourBuilder(route_stops, seconds_per_stop=route_stop,
                            travel_seconds=route_travel, end_zoom=17.0)
        route.FPS = 24
        route.TOTAL_FRAMES = 192
        route.FRAMES_TOTAL = 192
        route.stop_end_zooms = [17.0] * stop_count
        route.initial_zoom_fraction = 0.90
        route.stop_dive_fraction = 1.0
        try:
            opening_frames = fit_initial_stop_frames(route, minimum_final_hold_frames=36)
            remaining = route.TOTAL_FRAMES - route._schedule()[-1][1]
            route_passed = (check_velocity_strict(route) > 0 and remaining >= 36
                            and route.TOTAL_FRAMES == 192)
            check(should_fit and route_passed,
                  f"{stop_count}-stop production route keeps 192 frames and a 36-frame final hold "
                  f"(opening={opening_frames}, hold={remaining})")
        except RuntimeError as exc:
            check(not should_fit,
                  f"{stop_count}-stop production route frame fit: {exc}")

    # 4. Pose continuity: the same phase-aware strict bound the render gate
    #    enforces, checked offline on the schedule and every single-shot preset.
    #    A pure dive/metric shot exposes one phase without a schedule; verify
    #    its own zoom trace, not pitch/yaw/roll.
    try:
        n_seg = check_velocity_strict(tb)
        check(True, f"tour zoom velocity strictly continuous in all {n_seg} phases")
    except RuntimeError as exc:
        check(False, f"tour zoom velocity: {exc}")
    for preset in ("dive", "tilt", "orbit", "metric", "earthrise", "space_to_street"):
        try:
            single = _ShotBuilder(stops[0], preset, 120)
            if preset in ("earthrise", "space_to_street"):
                single.start_zoom, single.end_zoom = (17.5, 5.5) if preset == "earthrise" else (5.0, 18.0)
            n_seg = check_velocity_strict(single)
            zoom_trace = [_pose_zoom(single, f) for f in range(single.TOTAL_FRAMES)]
            if preset in ("tilt", "orbit"):
                zoom_holds = all(abs(z - single.end_zoom) <= 1e-9
                                 for z in zoom_trace[round(single.TOTAL_FRAMES * 0.62):])
                check(zoom_holds,
                      f"{preset} preserves the landing zoom during tilt/orbit")
            else:
                check(abs(zoom_trace[-1] - single.end_zoom) < 1e-9,
                      f"{preset} reaches the authored landing zoom")
            check(True, f"{preset} shot zoom is continuous in {n_seg} phase(s)")
        except RuntimeError as exc:
            check(False, f"{preset} shot zoom continuity: {exc}")

    print("=== geo_runtime self-test: "
          + ("ALL PASSED" if not failures else f"{len(failures)} FAILED") + " ===",
          flush=True)
    return 0 if not failures else 1


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="geo_runtime: text -> places -> mp4")
    ap.add_argument("text", nargs="*", help="e.g. 'Roma poi il Colosseo e Venezia'")
    ap.add_argument("--out", default=None, help="output MP4 path")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--block", type=int, default=10)
    ap.add_argument("--preset", default="veryfast",
                    help="encoder preset; documentary shot preset is selected with --shot-preset")
    ap.add_argument("--shot-preset", choices=("dive", "earthrise", "tilt", "orbit", "metric", "space_to_street"),
                    default=None, help="repeatable camera motion preset for --place")
    ap.add_argument("--place", help="single explicit place query (offline catalog by default)")
    ap.add_argument("--offline-geocoding", dest="offline_geocoding", action="store_true",
                    default=True,
                    help="resolve only from the offline geography catalog (default); never call Nominatim")
    ap.add_argument("--online-geocoding", dest="offline_geocoding", action="store_false",
                    help="allow Nominatim fallback for places missing from the offline catalog")
    ap.add_argument("--geographic-catalog", type=Path, default=None,
                    help="override the checked-in geographic catalog path")
    ap.add_argument("--strict-native", action="store_true",
                    help="fail unless NVIDIA OpenCL and NVENC are available")
    ap.add_argument("--wayback-release", type=int, default=None,
                    help="explicit Esri Wayback release number; no release is guessed")
    ap.add_argument("--documentary", type=Path, default=None,
                    help="JSON layers: regions/routes/values/hotspots/hillshade_path; provider and epoch_before_provider are optional")

    ap.add_argument("--beat-times", type=Path, default=None,
                    help="JSON array of beat times in seconds, used to snap route events")
    ap.add_argument("--beats-offset", type=float, default=0.0,
                    help="offset in seconds between beat JSON and shot start")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--verify", action="store_true",
                    help="compare single-place fast frames with independent tile-engine frames")
    ap.add_argument("--upload", action="store_true", help="upload to Drive")
    ap.add_argument("--repl", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="offline: extraction table, tour schedule, pose continuity")
    args = ap.parse_args()

    if args.wayback_release is not None and args.wayback_release <= 0:
        ap.error("--wayback-release must be a positive release number")
    if args.wayback_release is not None and not args.place:
        ap.error("--wayback-release is supported with --place")
    if args.wayback_release is not None and args.shot_preset not in (None, "earthrise"):
        ap.error("--wayback-release requires --shot-preset earthrise")
    if args.self_test:
        sys.exit(self_test())
    rt = GeoRuntime(workers=args.workers, block=args.block,
                    preset_x264=args.preset, crf=args.crf, upload=args.upload,
                    strict_native=args.strict_native,
                    wayback_release=args.wayback_release,
                    geographic_catalog_path=args.geographic_catalog,
                    offline_geocoding=args.offline_geocoding)
    if args.place:
        if args.text:
            ap.error("use either --place or free-text tour arguments")
        shot = args.shot_preset or "dive"
        place = rt._resolve_place(Place(args.place, preset=shot))
        if not place.ok:
            raise RuntimeError(f"could not geocode requested place: {args.place}")
        if args.documentary:
            config = json.loads(args.documentary.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                ap.error("--documentary JSON root must be an object")
            place._documentary_layers = config
        if args.beat_times:
            beat_times = json.loads(args.beat_times.read_text(encoding="utf-8"))
            if not isinstance(beat_times, list):
                ap.error("--beat-times JSON root must be an array of seconds")
            if any(float(t) < args.beats_offset for t in beat_times):
                ap.error("beat time precedes --beats-offset; align the beat track first")
            place._beat_events = __import__("geo_documentary").beat_schedule(
                [{"id": "route", "action": "route", "time_s": args.beats_offset}],
                beat_times, FPS)
        report = rt.render_place(place, frames=round(8 * FPS),
                                 out=Path(args.out) if args.out else None,
                                 verify=args.verify)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.repl or not args.text:
        rt.repl()
        return
    tour = rt.render_tour(" ".join(args.text), out=Path(args.out) if args.out else None,
                          verify=args.verify)
    print(json.dumps({"mp4": str(tour.mp4),
                      "stops": [{"name": s.short_name, "lat": s.lat, "lon": s.lon,
                                 "preset": s.preset} for s in tour.stops]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
