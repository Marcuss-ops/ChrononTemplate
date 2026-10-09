#!/usr/bin/env python3
"""geo_runtime - runtime generation of geo_camera_v1 renders.

The pipeline, end to end:

    text ("Roma, poi il Colosseo, infine Venezia")
      -> extract_places        LLM-free, heuristic + gazetteer geography parser
      -> geocode               Nominatim/OpenStreetMap (free, no key)
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
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # the repo root (VeloxEditing), two levels up
for p in (str(ROOT / "Chronon3d/tools/cartography"), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

WIDTH, HEIGHT, FPS = 1920, 1080, 30

# ---------------------------------------------------------------------------
# Place extraction
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "poi", "e", "ed", "infine", "quindi", "dopo", "con", "a", "al", "alla",
    "in", "nel", "nella", "da", "dal", "per", "tra", "fra", "su", "il", "lo",
    "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della", "dei",
    "delle", "che", "mostra", "voglio", "fare", "video", "tour", "poi-",
    "con", "poi.",
}

# Lowercase name particles may connect adjacent capitalised place-name words.
# Tour connectors (e, poi, infine, ...) deliberately remain hard boundaries.
_INTERNAL_NAME_PARTICLES = {
    "di", "del", "dello", "della", "dei", "degli", "delle", "da", "dal",
    "dallo", "dalla", "dai", "dagli", "dalle", "in", "nel", "nello",
    "nella", "nei", "negli", "nelle", "sul", "sullo", "sulla", "sui",
    "sugli", "sulle", "of", "the",
}

# Multi-word anchors that must win over their single-word parts.
_TOUR_WORDS = {"tour", "itinerario", "viaggio", "giro"}


@dataclass
class Place:
    query: str                      # what the user wrote
    display_name: str = ""          # Nominatim's answer
    lat: float = 0.0
    lon: float = 0.0
    preset: str = "dive"            # dive | tilt | orbit | metric
    ok: bool = False

    @property
    def short_name(self) -> str:
        if not self.display_name:
            return self.query.upper()
        return self.display_name.split(",")[0].strip().upper()

    @property
    def subtitle(self) -> str:
        """A compact first locality component that fits the reveal card."""
        return (self.display_name or self.query).split(",")[0].strip().upper()[:36]


@dataclass
class Tour:
    text: str
    stops: list[Place] = field(default_factory=list)
    mp4: Path | None = None
    stats: list[dict] = field(default_factory=list)


def extract_places(text: str) -> list[Place]:
    """Pull place candidates from free Italian/English text.

    Heuristic, LLM-free: capitalised runs (or quoted names) are candidates,
    stop-words are stripped, and preset keywords ride along with the place
    they precede/follow. "Roma, poi il Colosseo con tilt" -> Roma(dive),
    Colosseo(tilt).
    """
    text = text.replace("\u201c", "\"").replace("\u201d", "\"")
    quoted = re.findall(r"\"([^\"]{2,60})\"", text)
    for q in quoted:
        text = text.replace(f"\"{q}\"", " " + q.replace(" ", "_") + " ")

    tokens = re.findall(r"[A-Za-z_][A-Za-z_'\-]*|,", text)
    places: list[Place] = []
    run: list[str] = []            # the capitalised run being assembled
    pending = {"preset": "dive"}   # preset keyword waiting for its place
    comma_since = {"flag": False}  # a comma has passed since the last name

    def flush_run():
        if run:
            places.append(Place(query=" ".join(run), preset=pending["preset"]))
            run.clear()
            pending["preset"] = "dive"
            comma_since["flag"] = False

    for i, token in enumerate(tokens):
        if token == ",":
            flush_run()
            comma_since["flag"] = True
            continue
        low = token.lower().replace("_", " ")
        if low in ("tilt", "orbita", "orbit", "metric", "metrica"):
            flush_run()
            preset_now = ("tilt" if low == "tilt"
                          else "orbit" if low in ("orbita", "orbit") else "metric")
            # A preset keyword retargets the place just named: "Machu Picchu
            # con orbita" orbits Machu Picchu, "Campagna Lupia con tilt"
            # tilts Campagna Lupia. It only rides FORWARD when no place has
            # been named yet ("con tilt Venezia"), via the pending slot.
            if places:
                places[-1].preset = preset_now
            else:
                pending["preset"] = preset_now
            continue
        if low in _STOPWORDS or low in _TOUR_WORDS:
            # Keep lowercase particles only inside a capitalised place name,
            # e.g. "Piazza dei Miracoli"; ordinary connectors still split.
            next_is_name = (i + 1 < len(tokens)
                            and tokens[i + 1] != ","
                            and (tokens[i + 1][0].isupper() or "_" in tokens[i + 1]))
            if run and low in _INTERNAL_NAME_PARTICLES and next_is_name:
                run.append(low)
            else:
                # A connector breaks adjacency: 'Roma poi Colosseo' are two places.
                flush_run()
            continue
        if token[0].isupper() or "_" in token:
            run.append(token.replace("_", " "))
        else:
            flush_run()
    flush_run()
    # A preset keyword left unconsumed at the end of the text retargets the
    # last place: "Venezia con tilt" means Venezia, tilted.
    if pending["preset"] != "dive" and places:
        places[-1].preset = pending["preset"]
    return places


def geocode(place: Place, language: str = "it") -> Place:
    """Nominatim (OpenStreetMap): free, keyless, respects the usage policy."""
    q = urllib.parse.urlencode({"q": place.query, "format": "json", "limit": 1,
                                "accept-language": language})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{q}",
        headers={"User-Agent": "ChrononGeoCameraRuntime/1.0"})
    try:
        rows = json.load(urllib.request.urlopen(req, timeout=12))
    except Exception as exc:  # offline: keep the place unresolvable
        print(f"  [geocode] {place.query}: UNREACHABLE ({exc})", flush=True)
        return place
    if not rows:
        print(f"  [geocode] {place.query}: NOT FOUND", flush=True)
        return place
    row = rows[0]
    place.display_name = row["display_name"]
    place.lat, place.lon = float(row["lat"]), float(row["lon"])
    place.ok = True
    print(f"  [geocode] {place.query} -> {place.display_name.split(',')[0]} "
          f"({place.lat:.5f}, {place.lon:.5f})", flush=True)
    return place


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


def _roll_bank(p: float) -> float:
    """Banking during post-dive phases: a sine that returns to zero."""
    return -8.0 * math.sin(max(0.0, min(1.0, p)) * math.pi)


def _draw_map_attribution(frame) -> None:  # noqa: ANN001 - numpy/OpenCV image
    import cv2
    text = "Esri, Vantor, Earthstar Geographics, and the GIS User Community"
    cv2.putText(frame, text, (28, frame.shape[0] - 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (238, 238, 238), 1,
                cv2.LINE_AA)


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
        self.place = place
        self.preset = preset
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
        self._engine = None

    # Lazily prepare the independent per-frame reference path for --verify.
    def engine(self):
        if self._engine is None:
            import dynamic_tile_pyramid as dyn
            self._engine = dyn.DynamicTilePyramid(provider="esri_sat")
            self._engine.prefetch_pyramid(
                self.place.lat, self.place.lon, min_zoom=self.PREPARE_ZMIN,
                max_zoom=self.PREPARE_ZMAX, tile_radius_x=9, tile_radius_y=9)
        return self._engine

    # -- motion law (GeoCameraRig schedules: dive 62% / tilt to 80%) ---------
    def pose(self, f: int):
        smootherstep, ROLL_AT = _smootherstep, _roll_bank
        motion_frames = max(2, self.TOTAL_FRAMES - getattr(self, "terminal_hold_frames", 0))
        # Keep any authored terminal hold stationary at the destination while
        # preserving the original camera move timing.
        f = min(f, motion_frames - 1)
        if getattr(self, "full_duration_zoom", False):
            e = smootherstep(f / max(1, motion_frames - 1))
            zoom = self.start_zoom + (self.end_zoom - self.start_zoom) * e
            return zoom, 0.0, 0.0, 0.0
        dive_end = round(motion_frames * 0.62)
        tilt_end = round(motion_frames * 0.80)
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
            apply_city_beacon_map_style, draw_map_location_marker,
            apply_city_beacon_map_style_opencl, draw_map_location_marker_opencl,
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
        if getattr(self, "minimal_map", False):
            # The one-stop path uses _ShotBuilder (rather than TourBuilder),
            # so keep its marker treatment identical to multi-stop arrivals.
            # Finish the level dive (62% of the clip) before revealing the
            # location beacon. The name fade starts later in
            # draw_map_marker_label, preserving camera -> point -> label.
            radius_km = float(getattr(self, "map_area_glow_radius_km", 0.0))
            area_px = 0
            if radius_km > 0:
                area_px = int(radius_km / (40075.017 * max(0.01, math.cos(math.radians(self.place.lat))))
                              * (256 * (2.0 ** zoom)))
            animation = getattr(self, "map_label_animation", "gentle_fade")
            if animation == "diffuse_city_beacon":
                if gpu_map:
                    frame = apply_city_beacon_map_style_opencl(frame, progress)
                else:
                    apply_city_beacon_map_style(frame, progress)
            if gpu_map:
                frame = draw_map_location_marker_opencl(
                    frame, (WIDTH // 2, HEIGHT // 2),
                    self.place.display_name or self.place.query,
                    progress, animation, area_px)
                return frame.get()
            draw_map_location_marker(frame, (WIDTH // 2, HEIGHT // 2),
                                     self.place.display_name or self.place.query,
                                     progress, animation, area_px)
            return frame
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
        _draw_map_attribution(frame)
        return frame

    def render_frame_engine(self, f: int):
        """Reference renderer: recompose each frame from the tile engine."""
        return self.render_frame_fast(self.engine(), f)


class TourBuilder:
    """One continuous shot: dive to each stop in sequence, glow-route leg
    between stops, spring pin on arrival. The 'subsequent animation'."""

    def __init__(self, stops: list[Place], seconds_per_stop: float = 5.0,
                 travel_seconds: float = 3.0, end_zoom: float = 16.5):
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
        self.FRAMES_TOTAL = self.TOTAL_FRAMES  # legacy alias
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

    # timeline: [dive i][travel i->i+1][dive i+1]...
    def _schedule(self):
        frames_per = int(self.sps * self.FPS)
        leg = max(1, int(self.travel * self.FPS))
        marks = []
        f = 0
        for i in range(len(self.stops)):
            marks.append((f, f + frames_per, i))
            f += frames_per
            if i < len(self.stops) - 1:
                marks.append((f, f + leg, i, i + 1))
                f += leg
        return marks

    def _zoom_gate_phases(self):
        """Split a route leg's pullback and dive into separate zoom laws.

        The geographic pan between them intentionally holds zoom steady; it
        must not dilute either smootherstep phase's velocity budget.
        """
        phases = []
        for mark in self._schedule():
            if len(mark) == 3:
                active_end = (mark[0] + round((mark[1] - mark[0]) * self.stop_dive_fraction)
                              if self.stop_dive_fraction < 1.0 else mark[1])
                phases.append((mark[0], min(mark[1], max(mark[0] + 1, active_end))))
                continue
            start, end = mark[0], mark[1]
            span = end - start
            out_end = min(end - 2, max(start + 1, start + round(span * 0.40)))
            in_start = min(end - 1, max(out_end + 1, start + round(span * 0.60)))
            phases.extend(((start, out_end), (in_start, end)))
        return phases

    def pose(self, f: int):
        smootherstep = _smootherstep
        for m in self._schedule():
            if m[0] <= f < m[1]:
                if len(m) == 3:  # dive/hold on stop i
                    i = m[2]
                    s = self.stops[i]
                    target = self.stop_end_zooms[i]
                    z_start = (5.2 + (target - 5.2) * self.initial_zoom_fraction
                               if i == 0 else self.stop_end_zooms[i - 1])
                    active_end = (m[0] + round((m[1] - m[0]) * self.stop_dive_fraction)
                                  if self.stop_dive_fraction < 1.0 else m[1])
                    active_end = min(m[1], max(m[0] + 1, active_end))
                    active_frames = active_end - m[0]
                    phase = (1.0 if active_frames <= 1 else
                             (f - m[0]) / (active_frames - 1))
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
                # Pull back before panning so the complete leg stays visible,
                # then dive toward the next stop. The old 1.2-level pullback
                # left the camera nearly at street scale while crossing whole
                # regions, which looked like a broken infinite zoom.
                from dynamic_tile_pyramid import latlon_to_global_px
                ax, ay = latlon_to_global_px(a.lat, a.lon, 5)
                bx, by = latlon_to_global_px(b.lat, b.lon, 5)
                distance = math.hypot(bx - ax, by - ay)
                route_zoom = 5.0 + math.log2((0.72 * self.WIDTH) / max(distance, 1.0))
                route_zoom = max(5.2, min(self.end_zoom, route_zoom))
                # Nearby destinations already fit at the landing scale. A
                # fractional-level pullback creates a visible bobble and a
                # non-zero phase seam; pan smoothly at constant zoom instead.
                if (abs(self.stop_end_zooms[i] - self.stop_end_zooms[j]) < 1e-9
                        and route_zoom >= self.stop_end_zooms[i] - 1.0):
                    p = smootherstep(raw)
                    return (a.lat + (b.lat - a.lat) * p,
                            a.lon + (b.lon - a.lon) * p,
                            self.stop_end_zooms[i])
                arrival_zoom = self.stop_end_zooms[j - 1] if j > 0 else self.end_zoom
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
            apply_city_beacon_map_style, draw_map_location_marker,
            apply_city_beacon_map_style_opencl, draw_map_location_marker_opencl,
            draw_route_glow, draw_spring_pin,
        )
        from dynamic_tile_pyramid import latlon_to_global_px

        lat, lon, zoom = self.pose(f)
        progress = f / (self.FRAMES_TOTAL - 1)
        gpu_map = bool(getattr(self, "minimal_map", False) and
                       getattr(sampler, "gpu_map_enabled", False))
        frame = (sampler.sample_opencl(lat, lon, zoom, WIDTH, HEIGHT)
                 if gpu_map else sampler.sample(lat, lon, zoom, WIDTH, HEIGHT))

        if getattr(self, "minimal_map", False):
            animation = getattr(self, "map_label_animation", "gentle_fade")
            if animation == "diffuse_city_beacon":
                if gpu_map:
                    frame = apply_city_beacon_map_style_opencl(frame, progress)
                else:
                    apply_city_beacon_map_style(frame, progress)
            location_name = ""
            active_stop = None
            for mark in self._schedule():
                if len(mark) == 3 and mark[0] <= f < mark[1]:
                    active_stop = self.stops[mark[2]]
                    location_name = active_stop.display_name or active_stop.query
                    break
            if active_stop is not None:
                zf = int(zoom // 1)
                scale = 2.0 ** (zoom - zf)
                ax, ay = latlon_to_global_px(lat, lon, zf)
                px, py = latlon_to_global_px(active_stop.lat, active_stop.lon, zf)
                sx = int(WIDTH / 2 + (px - ax) * scale)
                sy = int(HEIGHT / 2 + (py - ay) * scale)
                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                    radius_km = float(getattr(self, "map_area_glow_radius_km", 0.0))
                    area_px = 0
                    if radius_km > 0:
                        earth_km = 40075.017
                        area_px = int(radius_km / (earth_km * max(0.01, math.cos(math.radians(active_stop.lat))))
                                      * (256 * (2.0 ** zoom)))
                    if gpu_map:
                        frame = draw_map_location_marker_opencl(
                            frame, (sx, sy), location_name, progress, animation, area_px)
                    else:
                        draw_map_location_marker(frame, (sx, sy), location_name,
                                                 progress, animation, area_px)
            return frame.get() if gpu_map else frame

        # the route so far, glowing under the camera
        zf = int(zoom // 1)
        scale = 2.0 ** (zoom - zf)
        ax, ay = latlon_to_global_px(lat, lon, zf)
        overlay = np.zeros_like(frame)
        done_until = f
        for (m0, m1, *idx) in self._schedule():
            if len(idx) == 2 and m1 <= f:  # finished travel leg: full glow
                a, b = self.stops[idx[0]], self.stops[idx[1]]
                for t in range(26):
                    tt = t / 25
                    px, py = latlon_to_global_px(a.lat + (b.lat - a.lat) * tt,
                                                 a.lon + (b.lon - a.lon) * tt, zf)
                    sx, sy = int(WIDTH / 2 + (px - ax) * scale), int(HEIGHT / 2 + (py - ay) * scale)
                    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                        cv2.circle(overlay, (sx, sy), 4, (60, 240, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.85, frame, 1.0, 0, dst=frame)

        # arrival pin on the stop the camera is diving into
        for (m0, m1, *idx) in self._schedule():
            if len(idx) == 1 and m0 <= f < m1 + int(0.4 * self.FPS):
                s = self.stops[idx[0]]
                sx = int(WIDTH / 2 + (latlon_to_global_px(s.lat, s.lon, zf)[0] - ax) * scale)
                sy = int(HEIGHT / 2 + (latlon_to_global_px(s.lat, s.lon, zf)[1] - ay) * scale)
                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                    draw_spring_pin(frame, (sx, sy), (f - m0 + int(0.4 * self.FPS))
                                    / (m1 - m0 + int(0.4 * self.FPS)), fire=0.80, span=0.12)

        draw_hud_overlay(frame, lat, lon, zoom, progress,
                         target_title="GEO RUNTIME TOUR")
        _draw_map_attribution(frame)
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
    a = builder.render_frame_fast(sampler, probe).tobytes()
    b = builder.render_frame_fast(sampler, probe).tobytes()
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
                 upload: bool = False):
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

    # -- text -> resolved places ---------------------------------------------
    def resolve(self, text: str) -> Tour:
        tour = Tour(text=text)
        places = extract_places(text)
        if not places:
            raise ValueError(f"no places found in: {text!r}")
        print(f"[resolve] {len(places)} candidate(s): "
              f"{[p.query for p in places]}", flush=True)
        for pl in places:
            tour.stops.append(geocode(pl))
        return tour

    # -- one place -> one shot mp4 --------------------------------------------
    def render_place(self, place: Place, frames: int = 120,
                     out: Path | None = None, verify: bool = False) -> dict:
        if not place.ok:
            raise ValueError(f"place is not geocoded: {place.query}")
        import fast_geo_camera as harness
        builder = _ShotBuilder(place, place.preset, frames)
        sampler = harness.build_sampler(builder)
        gate_builder(builder, sampler, label=place.query)
        if verify:
            if not harness.verify_against_engine(builder, sampler):
                raise RuntimeError(f"verify failed for {place.query}")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", place.query).strip("._") or "place"
        out = Path(out or (self.out_root / f"{safe_name}_{place.preset}.mp4"))
        out.parent.mkdir(parents=True, exist_ok=True)
        stats = harness.encode_with_pool(builder, sampler, out,
                                         self.workers, self.block,
                                         self.preset_x264, self.crf)
        return stats

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
            builder = TourBuilder(stops)
        sampler = harness.build_sampler(builder)
        # The gate always runs: velocity continuity per segment + determinism.
        gate_builder(builder, sampler, label=" ".join(s.short_name for s in stops))
        if verify and isinstance(builder, _ShotBuilder):
            # A single-place shot has an independent per-frame engine reference.
            # A multi-stop tour has no separate engine implementation; its strict
            # phase/junction and deterministic-frame gates are authoritative.
            if not harness.verify_against_engine(builder, sampler):
                raise RuntimeError("single-place engine comparison failed")
        elif verify and len(stops) > 1:
            print("[verify] multi-stop tour has no independent frame renderer; "
                  "phase and determinism gates passed instead", flush=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = Path(out or (self.out_root / f"tour_{stamp}.mp4"))
        out.parent.mkdir(parents=True, exist_ok=True)
        tour.stats.append(harness.encode_with_pool(
            builder, sampler, out, self.workers, self.block,
            self.preset_x264, self.crf))
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
    last = tb.pose(tb.TOTAL_FRAMES - 1)
    check(abs(last[0] - stops[-1].lat) < 1e-9 and abs(last[1] - stops[-1].lon) < 1e-9
          and abs(last[2] - tb.end_zoom) < 1e-9,
          "the tour ends framed on its final stop at landing zoom")

    # 3. Pose continuity: the same phase-aware strict bound the render gate
    #    enforces, checked offline on the schedule and every single-shot preset.
    #    A pure dive/metric shot exposes one phase without a schedule; verify
    #    its own zoom trace, not pitch/yaw/roll.
    try:
        n_seg = check_velocity_strict(tb)
        check(True, f"tour zoom velocity strictly continuous in all {n_seg} phases")
    except RuntimeError as exc:
        check(False, f"tour zoom velocity: {exc}")
    for preset in ("dive", "tilt", "orbit", "metric"):
        try:
            single = _ShotBuilder(stops[0], preset, 120)
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
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--verify", action="store_true",
                    help="compare single-place fast frames with independent tile-engine frames")
    ap.add_argument("--upload", action="store_true", help="upload to Drive")
    ap.add_argument("--repl", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="offline: extraction table, tour schedule, pose continuity")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    rt = GeoRuntime(workers=args.workers, block=args.block,
                    preset_x264=args.preset, crf=args.crf, upload=args.upload)
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
