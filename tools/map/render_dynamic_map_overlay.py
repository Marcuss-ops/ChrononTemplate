#!/usr/bin/env python3
"""Render a production map overlay from grounded points using the Chronon tile pyramid.

Input is a JSON object containing width, height, fps_num, fps_den,
duration_us and pins (id, label, latitude, longitude). The output is an opaque
H.264 MP4 for use as a full-canvas RenderingGen video background.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# The production worker's /usr/bin/python3 also sees a newer NumPy installed
# under /usr/local, while its distro OpenCV extension was built against NumPy
# 1.x. Prefer the distro package directory so cv2 and NumPy load as a matched
# pair; the rest of the interpreter's site-packages remain available afterward.
SYSTEM_DIST_PACKAGES = Path("/usr/lib/python3/dist-packages")
if SYSTEM_DIST_PACKAGES.is_dir():
    sys.path.insert(0, str(SYSTEM_DIST_PACKAGES))
sys.path.insert(0, str(ROOT / "Chronon3d/tools/cartography"))
sys.path.insert(0, str(HERE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    if args.summary_output is None:
        args.summary_output = args.output.with_suffix(".telemetry.json")
    render_started = time.perf_counter()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    width, height = int(payload["width"]), int(payload["height"])
    # Preserve the media contract exactly; the map renderer must match the
    # source timeline's frame rate for deterministic overlay synchronization.
    fps_num, fps_den = int(payload["fps_num"]), int(payload["fps_den"])
    duration_us = int(payload["duration_us"])
    route_timing = payload.get("route_timing")
    country_context = payload.get("country_context")
    if country_context is not None:
        if not isinstance(country_context, dict):
            raise ValueError("country_context must be an object")
        try:
            country_context = {
                "iso": str(country_context["iso"]).upper(),
                "latitude": float(country_context["latitude"]),
                "longitude": float(country_context["longitude"]),
                "zoom": float(country_context.get("zoom", 5.8)),
                "hold_seconds": float(country_context["hold_seconds"]),
                "travel_seconds": float(country_context["travel_seconds"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("country_context requires iso, center, hold_seconds and travel_seconds") from exc
        if route_timing is None:
            raise ValueError("country_context requires explicit route_timing")
        if (not all(math.isfinite(v) for v in country_context.values()
                    if isinstance(v, float))
                or not -85 < country_context["latitude"] < 85
                or not -180 <= country_context["longitude"] <= 180
                or country_context["zoom"] < 5.0
                or country_context["hold_seconds"] <= 0
                or country_context["travel_seconds"] <= 0):
            raise ValueError("country_context camera/timing values are outside valid ranges")
    if route_timing is not None:
        if not isinstance(route_timing, dict):
            raise ValueError("route_timing must be an object")
        try:
            route_stop_seconds = float(route_timing["seconds_per_city"])
            route_travel_seconds = float(route_timing["travel_seconds"])
            route_final_hold_seconds = float(route_timing.get("final_hold_seconds", 0.0))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("route_timing requires numeric seconds_per_city and travel_seconds") from exc
        if (not all(math.isfinite(v) for v in
                    (route_stop_seconds, route_travel_seconds, route_final_hold_seconds))
                or route_stop_seconds <= 0 or route_travel_seconds <= 0
                or route_final_hold_seconds < 0):
            raise ValueError("route_timing durations must be finite, with positive city/travel times and nonnegative final hold")
    raw_pins = payload.get("pins", [])
    # Keep a route map focused: repeated mentions of the same place are one
    # stop, and no tour may contain more than five distinct stops. This cap
    # is part of the camera's authored 6.5-second route budget; seven stops
    # cannot preserve the 1.5-second terminal hold inside that window.
    pins = []
    seen_pin_coords = set()
    for pin in raw_pins:
        coordinate_key = (round(float(pin["latitude"]), 4), round(float(pin["longitude"]), 4))
        if coordinate_key in seen_pin_coords:
            continue
        seen_pin_coords.add(coordinate_key)
        pins.append(pin)
        if len(pins) == 5:
            break
    if len(pins) != len(raw_pins):
        print(f"[dynamic-map] limited route to {len(pins)} unique stops from {len(raw_pins)} mentions", flush=True)
    area_glow_radius_km = float(payload.get("area_glow_radius_km", 0.0))
    camera_animations = {"signature_dive", "tilt_reveal", "orbit_arrival",
                         "slow_approach", "wide_context", "steady_hold",
                         "fast_push"}
    from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS
    from map_compositions import MAP_COMPOSITIONS, MULTI_PIN_SYSTEMS
    from map_editorial import MAP_EDITORIAL_SCENES, MULTI_PIN_SCENES
    from map_editorial_gpu import reset_gpu_counters, gpu_counters, geo_project
    camera_animation = str(payload.get("camera_animation", "signature_dive"))
    label_animation = str(payload.get("label_animation", "gentle_fade"))
    map_animation = str(payload.get("map_animation", "") or "")
    basemap = str(payload.get("basemap", "esri_sat"))
    if camera_animation not in camera_animations:
        raise ValueError(f"unsupported camera_animation: {camera_animation}")
    if label_animation != "none" and label_animation not in MAP_LABEL_ANIMATIONS:
        raise ValueError(f"unsupported label_animation: {label_animation}")
    if map_animation and map_animation not in MAP_COMPOSITIONS \
            and map_animation not in MAP_EDITORIAL_SCENES:
        raise ValueError(f"unsupported map_animation: {map_animation}")
    if map_animation in MULTI_PIN_SYSTEMS and len(pins) < 2:
        raise ValueError(f"map_animation {map_animation} requires at least two pins")
    if map_animation in MULTI_PIN_SCENES and len(pins) < 2:
        raise ValueError(f"map_animation {map_animation} requires at least two pins")
    if map_animation == "ed_yemen_markers" and len(pins) != 3:
        raise ValueError("ed_yemen_markers requires exactly three grounded pins")
    if map_animation in MAP_EDITORIAL_SCENES and label_animation != "none":
        raise ValueError("certified editorial map scenes require label_animation='none'")
    # Photo slots only accept real assets: a specified photo that does not
    # exist fails closed; an absent photo compacts the card (never generated).
    for pin in pins:
        photo = str(pin.get("photo") or "")
        if photo and not Path(photo).is_file():
            raise ValueError(f"map pin photo asset not found: {photo}")
        value = pin.get("value", None)
        if value is not None:
            try:
                if not math.isfinite(float(value)):
                    raise ValueError(f"map pin value must be finite: {value}")
            except (TypeError, ValueError):
                raise ValueError(f"map pin value must be a number: {value}")
    if width < 16 or height < 16 or fps_num <= 0 or fps_den <= 0 or duration_us <= 0 or not pins:
        raise ValueError("dynamic map requires valid canvas, frame rate, duration and at least one pin")
    if route_timing is not None and len(pins) < 2:
        raise ValueError("route_timing requires at least two unique city stops")
    if not math.isfinite(area_glow_radius_km) or not 0.0 <= area_glow_radius_km <= 1000.0:
        raise ValueError("area_glow_radius_km must be finite and in [0, 1000]")
    if any(not math.isfinite(float(p[k])) for p in pins for k in ("latitude", "longitude")):
        raise ValueError("map coordinates must be finite")

    import cv2
    import geo_runtime as geo
    import fast_geo_camera as harness
    import dynamic_tile_pyramid as dyn
    import fast_plate_sampler as fast
    # Map motion and pixel composition run through OpenCV's OpenCL kernels on
    # the NVIDIA device; NVENC remains the encoded-video writer.
    if not cv2.ocl.haveOpenCL():
        raise RuntimeError("GPU map rendering requires an active OpenCL device")
    # Keep OpenCL disabled through the CPU-only acceptance gate. The actual
    # encoder streams frames from this process, so its OpenCL context is never
    # inherited by forked workers.
    cv2.ocl.setUseOpenCL(False)
    # The runtime picks the basemap style per render; an id outside the
    # certified palette is a hard failure, never a silent fallback to satellite.
    if not dyn.is_basemap_style(basemap):
        raise ValueError(f"unsupported basemap: {basemap}")
    cv2.setNumThreads(1)
    geo.WIDTH, geo.HEIGHT, geo.FPS = width, height, fps_num / fps_den
    total_frames = max(2, round(duration_us * fps_num / (1_000_000 * fps_den)))
    if route_timing is not None:
        expected_seconds = (route_stop_seconds * len(pins)
                            + route_travel_seconds * (len(pins) - 1)
                            + route_final_hold_seconds
                            + (country_context["hold_seconds"]
                               + country_context["travel_seconds"]
                               if country_context else 0.0))
        expected_frames = round(expected_seconds * fps_num / fps_den)
        if abs(expected_frames - total_frames) > 1:
            raise ValueError(
                f"duration_us gives {total_frames} frames but route_timing requires "
                f"{expected_frames} ({expected_seconds:.3f}s)"
            )
    stops = [geo.Place(
        query=str(pin.get("label") or pin["id"]),
        display_name=str(pin.get("label") or pin["id"]),
        lat=float(pin["latitude"]), lon=float(pin["longitude"]), ok=True,
    ) for pin in pins]

    def map_level(pin):
        scope = str(pin.get("scope") or "").strip().lower()
        if scope in {"continent", "country", "region", "municipality", "city"}:
            return scope
        return "city"

    # Keep country and region maps at a broad reference scale. City maps land
    # near street level; 17.0 is within the certified local tile pyramid.
    level_zoom = {"continent": 2.5, "country": 5.0, "region": 8.0,
                  "municipality": 10.5, "city": 17.0}
    stop_zooms = [level_zoom[map_level(pin)] for pin in pins]
    municipal_outline = bool(payload.get("municipal_outline", False))
    municipal_zoom = float(payload.get("municipal_outline_zoom", 10.5))
    municipal_glow_zoom = float(payload.get("municipal_glow_zoom", 10.9))
    municipal_city_zoom = float(payload.get("municipal_city_zoom", 12.2))
    # Each municipal stop opens wide enough to read its own perimeter, then
    # spends the spoken two-second beat moving into the city itself.
    if municipal_outline:
        stop_zooms = [municipal_city_zoom if map_level(pin) == "municipality" else zoom
                      for pin, zoom in zip(pins, stop_zooms)]
    # A short map beat cannot carry a multi-stop tour and still reserve the
    # authored final hold. Keep the lead location as a single animated map
    # instead of failing the whole video during TourBuilder's strict gate.
    # Dedicated multi-pin compositions keep their pins and fail closed above.
    minimum_tour_seconds = 3.0 + 4.5 * (len(stops) - 1)
    if (
        len(stops) > 1
        and total_frames / geo.FPS < minimum_tour_seconds
        and route_timing is None
        and map_animation not in MULTI_PIN_SYSTEMS
        and map_animation not in MULTI_PIN_SCENES
    ):
        print(
            f"[dynamic-map] short beat ({total_frames / geo.FPS:.2f}s): "
            f"using lead location {stops[0].display_name!r} instead of "
            f"a {len(stops)}-stop tour",
            flush=True,
        )
        pins = pins[:1]
        stops = stops[:1]
        stop_zooms = stop_zooms[:1]
    # Candidate-area bounds keep each authored camera focused on its subject.
    editorial_country_scenes = set(MAP_EDITORIAL_SCENES)
    scene_camera_bounds = {
        "ed_saudi_base": (16.0, 34.0, 33.0, 56.0),
        "ed_iran_glow": (23.5, 46.0, 32.5, 57.0),
        "ed_yemen_fill": (11.0, 42.0, 20.0, 53.0),
        "ed_yemen_markers": (12.2, 40.5, 19.8, 47.0),
        "ed_hormuz_routes": (5.0, 37.0, 29.0, 75.0),
        "ed_mocha_tactical": (12.4, 42.0, 15.8, 45.2),
    }
    bounds_telemetry = None
    if map_animation in editorial_country_scenes:
        from geo_runtime import Place
        from map_editorial_gpu import fit_geo_bounds
        if map_animation in ("location_focus", "location_pulse"):
            # Frame a grounded town-scale context around the actual spoken pin.
            focus = stops[0]
            bounds = (focus.lat-.020, focus.lon-.030,
                      focus.lat+.020, focus.lon+.030)
        else:
            bounds = scene_camera_bounds.get(map_animation,
                        (6.0, 36.0, 40.0, 66.0))
        if map_animation == "ed_yemen_fill":
            width_fraction, height_fraction = 0.55, 0.86
        elif map_animation in ("location_focus", "location_pulse"):
            width_fraction, height_fraction = 0.70, 0.72
        elif map_animation == "ed_yemen_markers":
            width_fraction, height_fraction = 0.70, 0.74
        elif map_animation == "ed_iran_glow":
            width_fraction, height_fraction = 0.76, 0.76
        elif map_animation == "ed_mocha_tactical":
            width_fraction, height_fraction = 0.76, 0.72
        else:
            width_fraction, height_fraction = (0.74 if map_animation=="ed_saudi_base" else 0.78), (0.90 if map_animation=="ed_saudi_base" else 0.72)
        center_lat, center_lon, fitted_zoom, bounds_telemetry = fit_geo_bounds(
            bounds,width,height,width_fraction=width_fraction,
            height_fraction=height_fraction,min_zoom=5.0,
            max_zoom=15.0 if map_animation in ("location_focus", "location_pulse") else 8.0)
        camera_place = Place(query="Editorial map bounds", display_name="Editorial map bounds",
                             lat=center_lat, lon=center_lon, ok=True)
        builder = geo._ShotBuilder(camera_place, "dive", total_frames)
        builder.start_zoom = max(8.0,fitted_zoom-(1.8 if map_animation in ("location_focus", "location_pulse") else 0.32))
        builder.end_zoom = fitted_zoom
        builder.ANCHORS = tuple((s.lat,s.lon) for s in stops) + ((center_lat,center_lon),)
        builder.PREPARE_ZMIN, builder.PREPARE_ZMAX = 5, max(8,math.ceil(fitted_zoom)+1)
        builder.full_duration_zoom = True
        builder.terminal_hold_frames = round(total_frames*(.48 if map_animation in ("location_focus", "location_pulse") else .52))
        builder._editorial_stops = stops
    elif len(stops) == 1:
        preset = {"tilt_reveal": "tilt", "orbit_arrival": "orbit"}.get(camera_animation, "dive")
        builder = geo._ShotBuilder(stops[0], preset, total_frames)
        builder.end_zoom = stop_zooms[0]
        # Start city approaches at metro scale and finish at street scale;
        # regional and national views stay at their authored overview zoom.
        # City maps should arrive at a useful street scale quickly. The old
        # wide_context target stayed two zoom levels above the destination,
        # making the place feel distant even at the end of the clip.
        if map_level(pins[0]) == "city":
            builder.end_zoom = min(17.0, stop_zooms[0])
            if camera_animation == "signature_dive":
                # Classic wide satellite dive: opens far above town scale.
                # Explicit choice only (never in the Go random pool).
                builder.start_zoom = max(8.0, builder.end_zoom - 5.5)
            elif camera_animation == "steady_hold":
                # Nearly static: a 0.8-level drift, then a long readable hold.
                builder.start_zoom = max(8.0, builder.end_zoom - 0.8)
            elif camera_animation == "fast_push":
                # Quicker 2-level push for short map beats.
                builder.start_zoom = max(8.0, builder.end_zoom - 2.0)
            elif camera_animation == "slow_approach":
                # Keep the town readable while it approaches. Three zoom
                # levels in the opening beat still felt abrupt on small
                # places, so this explicit calm move travels only 1.4 levels.
                builder.start_zoom = max(8.0, builder.end_zoom - 1.4)
            else:
                # Open closer to town scale: a 5.5-level dive reads as a
                # sudden drop and the clip feels rushed. A 3-level approach
                # keeps the same arrival window but nearly halves peak zoom
                # velocity, so the flight stays readable.
                builder.start_zoom = max(8.0, builder.end_zoom - 3.0)
        else:
            if camera_animation == "wide_context":
                builder.end_zoom = max(5.8, stop_zooms[0] - 2.0)
            elif camera_animation == "slow_approach":
                builder.end_zoom = max(5.8, stop_zooms[0] - 0.9)
            elif camera_animation == "signature_dive":
                builder.end_zoom = max(5.8, stop_zooms[0])
                builder.start_zoom = max(5.8, builder.end_zoom - 5.5)
            elif camera_animation == "steady_hold":
                builder.end_zoom = max(5.8, stop_zooms[0] - 0.5)
                builder.start_zoom = max(5.8, builder.end_zoom - 0.8)
            elif camera_animation == "fast_push":
                builder.end_zoom = max(5.8, stop_zooms[0] - 0.5)
                builder.start_zoom = max(5.8, builder.end_zoom - 2.0)
            else:
                builder.start_zoom = max(5.8, builder.end_zoom - 1.5)
            if camera_animation not in ("signature_dive", "steady_hold", "fast_push"):
                builder.start_zoom = max(5.8, builder.end_zoom - 1.5)
            # Overview scopes (country/continent) sit at or below the 5.8
            # framing floor, which clamps start and end to the same zoom:
            # a static shot the velocity gate rightly rejects. Repair with a
            # gentle 0.5-level push-in fully above the z=5 sampler floor
            # instead of weakening the gate or faking motion elsewhere.
            if abs(builder.start_zoom - builder.end_zoom) < 1e-9:
                builder.start_zoom = 5.0
                builder.end_zoom = 5.5
        # Complete the approach in the opening 42%, then hold the destination
        # long enough for the target marker and place name to read clearly.
        builder.full_duration_zoom = True
        if camera_animation == "steady_hold":
            builder.terminal_hold_frames = round(total_frames * 0.70)
        elif camera_animation == "slow_approach":
            # Use 60% of the clip for the approach, then hold the target for
            # the remaining 40%. This gives the early pin and label time to
            # arrive while the camera is still moving.
            builder.terminal_hold_frames = round(total_frames * 0.40)
        elif camera_animation in ("fast_push", "signature_dive"):
            builder.terminal_hold_frames = round(total_frames * 0.50)
        else:
            builder.terminal_hold_frames = round(total_frames * 0.58)
    else:
        if route_timing is not None:
            camera_stops = list(stops)
            camera_stop_zooms = list(stop_zooms)
            if country_context:
                from map_editorial import load_border
                load_border(country_context["iso"])
                camera_stops.insert(0, geo.Place(
                    query=country_context["iso"],
                    display_name=country_context["iso"],
                    lat=country_context["latitude"],
                    lon=country_context["longitude"], ok=True,
                ))
                camera_stop_zooms.insert(0, country_context["zoom"])
            builder = geo.TourBuilder(
                camera_stops,
                seconds_per_stop=route_stop_seconds,
                travel_seconds=route_travel_seconds,
                end_zoom=max(camera_stop_zooms),
            )
            builder.stop_end_zooms = camera_stop_zooms
            if municipal_outline:
                builder.stop_start_zooms = [
                    municipal_zoom if map_level(pin) == "municipality" else zoom
                    for pin, zoom in zip(pins, camera_stop_zooms)
                ]
                builder.stop_reveal_zooms = [
                    municipal_glow_zoom if map_level(pin) == "municipality" else zoom
                    for pin, zoom in zip(pins, camera_stop_zooms)
                ]
                builder.stop_reveal_start_fraction = 0.25
                builder.stop_reveal_hold_fraction = 0.35
            # Begin already settled on the first town. Each stop then remains
            # on screen for exactly the spoken duration before the slow flight
            # to the following destination.
            builder.initial_zoom_fraction = 1.0
            builder.stop_dive_fraction = 1.0
            builder.end_zoom = max(camera_stop_zooms)
            if country_context:
                builder.country_intro = True
                builder.initial_stop_frames = round(country_context["hold_seconds"] * geo.FPS)
                builder.initial_travel_seconds = country_context["travel_seconds"]
                builder.PREPARE_ZMIN = 5
                builder.PREPARE_ZMAX = 18
                builder.hidden_stop_indices = {0}
                builder.country_outline_iso = country_context["iso"]
            builder.TOTAL_FRAMES = total_frames
            builder.FRAMES_TOTAL = total_frames
            geo.check_velocity_strict(builder)
        else:
            # Keep the previous five-second camera tour, then hold the final
            # destination for another 1.5 seconds. The builder's timeline ends
            # before TOTAL_FRAMES, so its final-pose fallback supplies that hold.
            tour_seconds = max(1.0, duration_us / 1_000_000 - 1.5)
            # Give close-zoom transitions a little more room: the strict camera
            # velocity gate caught a small zoom snap at a five-stop city route.
            # Keep the authored tour duration fixed by taking that time from the
            # per-stop holds, and reserve the final 1.5 s for the destination hold.
            # Five-stop close-zoom routes need at least 1.2 s per leg to stay
            # inside the strict zoom-velocity gate. Multi-stop tours involve more
            # ground to cover, so give each leg 1.8-2.4 s: slower legs stay far
            # inside the gate and remain readable. Borrow the extra time from
            # per-stop holds; keep the authored tour and final 1.5 s hold intact.
            travel_seconds = min(2.4, max(1.8, tour_seconds / (1.9 * (len(stops) - 1))))
            stop_seconds = max(0.15, (tour_seconds - travel_seconds * (len(stops) - 1)) / len(stops))
            builder = geo.TourBuilder(stops, seconds_per_stop=stop_seconds,
                                      travel_seconds=travel_seconds, end_zoom=max(stop_zooms))
            builder.stop_end_zooms = stop_zooms
            # Start much closer to the first city: this avoids a steep opening
            # zoom step on short, multi-stop routes and matches the requested
            # city-first framing.
            builder.initial_zoom_fraction = 0.90
            # Use the full stop window for each city dive. The default short
            # 0.58 fraction quantized to fewer than two useful frames on dense
            # five-stop routes and tripped the strict velocity gate at frame 0.
            builder.stop_dive_fraction = 1.0
            if camera_animation == "tilt_reveal":
                builder.initial_zoom_fraction = 0.90
                builder.stop_dive_fraction = 1.0
            elif camera_animation == "orbit_arrival":
                builder.initial_zoom_fraction = 0.90
                builder.stop_dive_fraction = 1.0
            elif camera_animation == "slow_approach":
                builder.initial_zoom_fraction = 0.90
                builder.stop_dive_fraction = 1.0
            elif camera_animation in ("signature_dive", "steady_hold", "fast_push"):
                builder.initial_zoom_fraction = 0.90
                builder.stop_dive_fraction = 1.0
            elif camera_animation == "wide_context":
                builder.stop_end_zooms = [max(5.8, zoom - 1.7) for zoom in stop_zooms]
            builder.end_zoom = max(builder.stop_end_zooms)
            # Honor the frozen overlay duration exactly; the tour builder computes
            # its own frame count from stop/travel phases.
            builder.TOTAL_FRAMES = total_frames
            builder.FRAMES_TOTAL = total_frames
            geo.fit_initial_stop_frames(builder, minimum_final_hold_frames=round(1.5 * builder.FPS))

    camera_stops = list(getattr(builder, "stops", stops))
    camera_stop_zooms = list(getattr(builder, "stop_end_zooms", stop_zooms))

    # Production map overlays are clean satellite imagery. Editorial country
    # scenes get one fixed regional view rather than a stop-by-stop city tour;
    # their geographies are projected against this live camera pose.
    builder.minimal_map = True
    builder.map_basemap = basemap
    builder.map_area_glow_radius_km = area_glow_radius_km
    builder.map_label_animation = label_animation
    builder.municipal_outline = municipal_outline
    builder.map_composition = map_animation
    builder.editorial_bounds_telemetry = bounds_telemetry
    builder.editorial_pins = [dict(pin) for pin in pins]
    builder.map_pin_extras = [{
        "latitude": float(pin["latitude"]),
        "longitude": float(pin["longitude"]),
        "label": str(pin.get("label") or pin["id"]),
        "subtitle": str(pin.get("subtitle") or "")[:40],
        "category": str(pin.get("category") or "")[:24],
        "color": str(pin.get("color") or "")[:16],
        "value": pin.get("value", None),
        "unit": str(pin.get("unit") or "")[:12],
        "photo": str(pin.get("photo") or ""),
        "location": str(pin.get("location") or "")[:40],
    } for pin in pins]
    builder.map_typography = payload.get("typography", {})
    builder.editorial_mode = map_animation in editorial_country_scenes
    # Required for the hard fail-closed GPU compositor; no automatic ndarray
    # fallback is permitted for editorial scene renders.
    builder.require_gpu_editorial = bool(map_animation in editorial_country_scenes)

    if builder.WIDTH != width or builder.HEIGHT != height:
        raise ValueError("Chronon geo camera output dimensions do not match the overlay canvas")
    pyramid = dyn.DynamicTilePyramid(provider=basemap)
    anchors = list(builder.ANCHORS)
    # The camera pans through each route midpoint. Include each midpoint in the
    # plate union so every camera center on a linearly interpolated route is
    # covered by the coarse leg plate.
    for index in range(len(camera_stops) - 1):
        a, b = camera_stops[index], camera_stops[index + 1]
        anchors.append(((a.lat + b.lat) / 2, (a.lon + b.lon) / 2))
    # Only prepare levels the animation can sample. Fractional zoom blends
    # z and z+1, so include the next integer above the deepest stop.
    prepare_zmin = min(builder.PREPARE_ZMIN, max(0, math.floor(min(camera_stop_zooms))))
    # The current frame sampler cannot consume zooms below its historic z=5
    # floor; clamp the authored flight to that certified floor instead of
    # allocating world-sized plates or falling back during a coarse shot.
    if prepare_zmin < 5:
        if len(camera_stops) == 1:
            builder.end_zoom = max(5.0, builder.end_zoom)
        else:
            builder.stop_end_zooms = [max(5.0, zoom) for zoom in builder.stop_end_zooms]
            builder.end_zoom = max(builder.stop_end_zooms)
        camera_stop_zooms = [max(5.0, zoom) for zoom in camera_stop_zooms]
        prepare_zmin = 5
    # Regional routes use a lower zoom while crossing distance, but each stop
    # still needs its local high-zoom tiles for the city arrival. Do not cap
    # the prepared pyramid at the route builder's broad-span limit.
    prepare_zmax = min(18, max(builder.PREPARE_ZMAX,
                               6, math.ceil(max(camera_stop_zooms)) + 1))
    if prepare_zmax < prepare_zmin:
        prepare_zmax = prepare_zmin

    # The camera may zoom out to show an entire route leg. Validate its actual
    # frame trajectory at the integer-sampling boundary before encoding; never
    # rely on the sampler's slow fallback to hide an undersized plate.
    if map_animation not in editorial_country_scenes:
      for leg_index in range(len(camera_stops) - 1):
        a, b = camera_stops[leg_index], camera_stops[leg_index + 1]
        ax, ay = dyn.latlon_to_global_px(a.lat, a.lon, 5)
        bx, by = dyn.latlon_to_global_px(b.lat, b.lon, 5)
        leg_zoom = max(5.2, min(max(camera_stop_zooms), 5.0 + math.log2(
            (0.72 * width) / max(math.hypot(bx - ax, by - ay), 1.0))))
        prepare_zmax = max(prepare_zmax, math.ceil(leg_zoom) + 1)

    sampler = fast.FastPlateSampler(pyramid, width, height)
    sampler.gpu_map_enabled = False
    sampler.prepare(anchors, prepare_zmin, prepare_zmax)
    for frame_idx in range(total_frames):
        if map_animation in editorial_country_scenes:
            zoom = builder.pose(frame_idx)[0]
            lat, lon = builder.place.lat, builder.place.lon
        elif len(camera_stops) > 1:
            lat, lon, zoom = builder.pose(frame_idx)
        else:
            lat, lon = camera_stops[0].lat, camera_stops[0].lon
            zoom = builder.pose(frame_idx)[0]
        if not sampler.can_sample(lat, lon, zoom, width, height):
            raise RuntimeError(
                f"prepared map plates do not cover camera frame {frame_idx} "
                f"at zoom {zoom:.3f}; refusing slow fallback")
        if map_animation in editorial_country_scenes:
            def project(y, x, _a=(lat, lon), _z=zoom):
                return geo_project(y,x,_a,_z,width,height)
            project.anchor=(lat,lon)
            project.zoom=zoom
            visible_geometries = {
                "location_focus": [(float(pin["latitude"]),float(pin["longitude"])) for pin in pins],
                "location_pulse": [(float(pin["latitude"]),float(pin["longitude"])) for pin in pins],
                "ed_saudi_base": [(24.7136,46.6753)],
                "ed_iran_glow": [(32.0,53.0)],
                "ed_yemen_fill": [(15.3,47.0)],
                "ed_yemen_markers": [(float(pin["latitude"]),float(pin["longitude"])) for pin in pins],
                "ed_hormuz_routes": [(26.55,56.27),(12.58,43.35),(7.0,72.5)],
                "ed_mocha_tactical": [(13.3167,43.25)],
            }[map_animation]
            offscreen = [point for point in visible_geometries
                         if not (-40 <= project(*point)[0] <= width+40
                                 and -40 <= project(*point)[1] <= height+40)]
            if offscreen:
                raise RuntimeError(f"scene {map_animation} has off-screen key geography at frame {frame_idx}: {offscreen}")
            if map_animation in scene_camera_bounds:
                geometry_bounds = scene_camera_bounds[map_animation]
                south,west,north,east=geometry_bounds
                bound_points=[project(y,x) for y in (south,north) for x in (west,east)]
                xs=[p[0] for p in bound_points];ys=[p[1] for p in bound_points]
                if min(xs)<0 or max(xs)>width or min(ys)<0 or max(ys)>height:
                    raise RuntimeError(f"scene bounds leave frame at camera frame {frame_idx}: {geometry_bounds}")
    if sampler.fallback_count != 0:
        raise RuntimeError("geometry-only sampler coverage check invoked the slow renderer")
    print(f"[dynamic-map] prepared zooms {sampler.z_min}..{sampler.z_max}", flush=True)
    if pyramid.telemetry["late_tile_fetches"] != 0:
        raise RuntimeError(f"plate composition performed {pyramid.telemetry['late_tile_fetches']} late tile fetches")
    if pyramid.telemetry["tile_fallbacks"] != 0:
        raise RuntimeError(f"tile prefetch produced {pyramid.telemetry['tile_fallbacks']} fallback tiles")
    gate_started = time.perf_counter()
    # Determinism/velocity gate stays CPU-only for classic scenes. Editorial
    # requires UMat from the first probe and asserts OpenCL composite counters.
    if map_animation in MAP_EDITORIAL_SCENES:
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            raise RuntimeError("OpenCL GPU map renderer failed to initialize")
        gpu_plate_bytes = sampler.prepare_opencl()
        sampler.gpu_map_enabled = True
        sampler.editorial_gpu_enabled = True
        sampler.editorial_scene = map_animation
        reset_gpu_counters()
        geo.gate_builder(builder, sampler, "production-map-overlay-gpu")
        gpu_gate_counts = gpu_counters()
        if gpu_gate_counts.get("opencl", 0) <= 0 or gpu_gate_counts.get("composites", 0) <= 0:
            raise RuntimeError(f"GPU acceptance gate observed no editorial composites: {gpu_gate_counts}")
    else:
        geo.gate_builder(builder, sampler, "production-map-overlay")
        gpu_plate_bytes = 0
    gate_ms = (time.perf_counter() - gate_started) * 1000.0
    if sampler.fallback_count != 0:
        raise RuntimeError(f"map acceptance gate used {sampler.fallback_count} slow-engine fallback frames")
    # Actual video frames use OpenCL on NVIDIA and encode to NVENC when the
    # requested scene requires GPU; CPU render is a classic-scene path only.
    cv2.ocl.setUseOpenCL(True)
    if not cv2.ocl.useOpenCL():
        raise RuntimeError("OpenCL GPU map renderer failed to initialize")
    # The distro OpenCV 4.5 API exposes Device_getDefault directly, while
    # newer builds expose Device.getDefault.
    if hasattr(cv2.ocl, "Device"):
        device = cv2.ocl.Device.getDefault()
    else:
        device = cv2.ocl.Device_getDefault()
    if "NVIDIA" not in device.vendorName().upper():
        raise RuntimeError(f"GPU map renderer selected unexpected device: {device.name()}")
    print(f"[dynamic-map] GPU frame renderer: OpenCL / {device.name()}", flush=True)
    if not sampler.gpu_map_enabled:
        gpu_plate_bytes = sampler.prepare_opencl()
        sampler.gpu_map_enabled = True
    print(f"[dynamic-map] uploaded {gpu_plate_bytes} map plate bytes to GPU", flush=True)
    sampler.editorial_gpu_enabled = bool(map_animation in MAP_EDITORIAL_SCENES)
    sampler.editorial_scene = map_animation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if map_animation in MAP_EDITORIAL_SCENES:
        # Artistically complex editorial overlays must remain GPU-rendered;
        # rejecting unavailable devices/fallbacks is part of this mode.
        sampler.editorial_gpu_enabled = True
        sampler.editorial_scene = map_animation
    reset_gpu_counters()
    stats = harness.encode_with_pool(builder, sampler, args.output,
                                     workers=min(2, max(1, (os.cpu_count() or 2) // 2)),
                                     block=2, preset="slow", crf=15,
                                     gpu_required=True)
    if stats.get("engine_fallback_frames", 0):
        raise RuntimeError(f"map sampler used fallback imagery in {stats['engine_fallback_frames']} frames")
    overlay_counts = gpu_counters()
    if map_animation in MAP_EDITORIAL_SCENES and (
            overlay_counts.get("opencl", 0) <= 0 or
            overlay_counts.get("composites", 0) <= 0):
        raise RuntimeError(f"editorial GPU scene did not register OpenCL composites: {overlay_counts}")
    if isinstance(builder, geo.TourBuilder):
        # A multi-stop map is a TourBuilder: its camera pose is (lat, lon,
        # zoom), and it has no single-place start_zoom/place fields.
        start_zoom = float(builder.pose(0)[2])
        end_zoom = float(builder.pose(total_frames - 1)[2])
        center = [builder.stops[0].lat, builder.stops[0].lon]
        terminal_hold_frames = max(0, total_frames - builder._schedule()[-1][1])
    else:
        start_zoom = float(builder.start_zoom)
        end_zoom = float(builder.end_zoom)
        center = [builder.place.lat, builder.place.lon]
        terminal_hold_frames = int(getattr(builder, "terminal_hold_frames", 0))
    summary = {
        "schema": "chronon.dynamic-map-telemetry.v1",
        "basemap": basemap,
        "frames": total_frames,
        "dimensions": {"width": width, "height": height},
        "fps": {"num": fps_num, "den": fps_den},
        "tile": dict(pyramid.telemetry),
        "camera": {"start_zoom": start_zoom,
                   "end_zoom": end_zoom,
                   "terminal_hold_frames": terminal_hold_frames,
                   "center": center,
                   "fit_bounds": getattr(builder,"editorial_bounds_telemetry",None)},
        "plates": dict(sampler.prepare_telemetry),
        "gate_ms": gate_ms,
        "frame_pipeline_s": stats["production_s"],
        "render_encode_wall_s": stats["total_s"],
        "post_frame_tail_s": stats["post_frame_tail_s"],
        "engine_fallback_frames": stats["engine_fallback_frames"],
        "output_bytes": stats["bytes"],
        "video_encoder": stats["encoder"],
        "gpu_encoder": stats["gpu_encoder"],
        "gpu_frame_renderer": "opencv_opencl",
        "gpu_overlay_compositor": "opencv_umat_opencl" if map_animation in MAP_EDITORIAL_SCENES else "legacy",
        "gpu_overlay_counts": overlay_counts,
        "opencl_device": device.name(),
        "gpu_plate_bytes": gpu_plate_bytes,
        "renderer_wall_s": time.perf_counter() - render_started,
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"DYNAMIC_MAP_PASS frames={total_frames} provider={basemap} output={args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
