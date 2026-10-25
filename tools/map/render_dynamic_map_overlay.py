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


def resolve_encoder_profile(profile):
    """Validate the closed map encoder contract and return its canonical fields."""
    if not isinstance(profile, dict):
        raise ValueError("encoder_profile must be an object")
    codec = profile.get("codec")
    certified = {
        "h264_nvenc": {"codec": "h264_nvenc", "gpu": True, "preset": "p6", "quality": 15},
        "libx264": {"codec": "libx264", "gpu": False, "preset": "veryfast", "quality": 23},
    }
    if codec not in certified or profile != certified[codec]:
        raise ValueError(f"unsupported or incomplete dynamic-map encoder profile: {profile!r}")
    return dict(profile)


def resolve_map_sampler(sampler):
    """Validate the sampler field explicitly passed by PipelineGen."""
    if sampler not in ("opencv_opencl", "cpu"):
        raise ValueError(f"unsupported declared map sampler: {sampler!r}")
    return sampler


def default_map_sampler(encoder_profile):
    """Choose the certified default sampler consistent with the encoder."""
    if not isinstance(encoder_profile, dict):
        raise ValueError("encoder_profile must be an object")
    if encoder_profile.get("codec") == "h264_nvenc" and encoder_profile.get("gpu") is True:
        return "opencv_opencl"
    if encoder_profile.get("codec") == "libx264" and encoder_profile.get("gpu") is False:
        return "cpu"
    raise ValueError("encoder profile codec/GPU declaration is inconsistent")


def sampler_requires_opencl(sampler, codec, editorial_gpu_composition):
    """Whether this declared render needs OpenCL initialization."""
    return sampler == "opencv_opencl" or codec == "h264_nvenc" or editorial_gpu_composition


def validate_encoder_sampler(encoder_profile, sampler, editorial=False):
    """Reject execution combinations that contradict the certified profile."""
    profile = resolve_encoder_profile(encoder_profile)
    sampler = resolve_map_sampler(sampler)
    if profile["codec"] == "h264_nvenc" and sampler != "opencv_opencl":
        raise ValueError("NVENC map encode profile requires the OpenCL map sampler")
    if editorial and sampler != "opencv_opencl":
        raise ValueError("editorial map compositions require the OpenCL GPU sampler")
    return sampler


def encoder_arguments(profile):
    """Build the exact ffmpeg video-encoder arguments for a certified profile."""
    profile = resolve_encoder_profile(profile)
    if profile["gpu"]:
        return ["-c:v", profile["codec"], "-gpu", "0", "-preset", profile["preset"],
                "-tune", "hq", "-rc", "vbr", "-cq", str(profile["quality"]), "-b:v", "0"]
    return ["-c:v", profile["codec"], "-preset", profile["preset"], "-crf", str(profile["quality"])]


def frame_workers() -> int:
    """Forked CPU frame workers; OpenCL editorial scenes remain process-local."""
    raw = os.environ.get("DYNAMIC_MAP_WORKERS")
    if raw:
        return max(1, int(raw))
    return min(12, max(1, (os.cpu_count() or 2) // 2))


# One map group may show at most this many unique stops: it is the camera's
# authored route budget (the planner splits larger groups into consecutive
# map groups, losing no place). Exceeding it here is a FAIL-CLOSED error — the
# renderer never silently drops a grounded place.
MAX_UNIQUE_STOPS = 5


def normalize_map_pins(raw_pins):
    """Deduplicate repeated mentions (one stop per coordinate) and fail closed
    above the five-stop budget, naming every stop that would be lost."""
    pins = []
    seen_pin_coords = set()
    for pin in raw_pins:
        coordinate_key = (round(float(pin["latitude"]), 4), round(float(pin["longitude"]), 4))
        if coordinate_key in seen_pin_coords:
            continue
        seen_pin_coords.add(coordinate_key)
        pins.append(pin)
    if len(pins) > MAX_UNIQUE_STOPS:
        dropped = [str(pin.get("label") or pin.get("id")) for pin in pins[MAX_UNIQUE_STOPS:]]
        raise ValueError(
            f"dynamic-map: {len(pins)} unique stops exceed the {MAX_UNIQUE_STOPS}-stop "
            f"budget; would drop {dropped!r}. Split the map group — the renderer "
            f"never drops a grounded place silently.")
    return pins


def parse_pin_timing(pins, pin_timing, duration_us):
    """Validate the voiceover's per-pin schedule and return it aligned with
    pins as a list of (start_s, duration_s). Every grounded pin must be timed;
    the schedule must fit inside the clip. Absent timing returns None."""
    if pin_timing is None:
        return None
    if not isinstance(pin_timing, list):
        raise ValueError("pin_timing must be a list of {id,start_s,duration_s} entries")
    clip_seconds = duration_us / 1_000_000.0
    by_id = {}
    for entry in pin_timing:
        if not isinstance(entry, dict):
            raise ValueError("pin_timing entries must be objects")
        try:
            pin_id = str(entry["id"])
            start_s = float(entry["start_s"])
            duration_s = float(entry["duration_s"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("pin_timing entries require numeric start_s and duration_s") from exc
        if (not math.isfinite(start_s) or not math.isfinite(duration_s)
                or start_s < 0.0 or duration_s <= 0.0):
            raise ValueError(f"pin_timing entry {pin_id!r} has non-finite or non-positive timing")
        if start_s + duration_s > clip_seconds + 1e-6:
            raise ValueError(f"pin_timing entry {pin_id!r} runs past the {clip_seconds:.3f}s clip")
        if pin_id in by_id:
            raise ValueError(f"pin_timing duplicates pin id {pin_id!r}")
        by_id[pin_id] = (start_s, duration_s)
    schedule = []
    for pin in pins:
        pin_id = str(pin.get("id"))
        if pin_id not in by_id:
            raise ValueError(f"pin_timing is missing grounded pin {pin_id!r}")
        schedule.append(by_id[pin_id])
    return schedule


def tour_timing_from_pin_timing(schedule, fps):
    """Project the spoken schedule onto the tour builder: every stop is held
    exactly while its place is spoken, and travel legs take the spoken gaps.
    Returns (seconds_per_stop, travel_seconds, stop_frame_reductions)."""
    durations = [duration for _, duration in schedule]
    seconds_per_stop = max(durations)
    gaps = []
    for index in range(len(schedule) - 1):
        current_end = schedule[index][0] + schedule[index][1]
        gaps.append(max(0.0, schedule[index + 1][0] - current_end))
    travel_seconds = (min(2.4, max(1.0, sum(gaps) / len(gaps))) if gaps else 1.5)
    reductions = tuple(max(0, int(round((seconds_per_stop - duration) * fps)))
                       for duration in durations)
    return seconds_per_stop, travel_seconds, reductions


def resolve_declared_composition(map_animation, fallbacks, pin_count,
                                 certified, multi_pin_systems, certified_scenes, multi_pin_scenes):
    """Resolve the composition honoring DECLARED fallbacks: an explicit id is
    validated and fails closed when its documented pin count cannot run; only
    then may the first compatible DECLARED fallback replace it, and the swap
    is returned as (composition, source) — never silent."""
    requested = str(map_animation or "").strip()
    if requested and requested not in certified and requested not in certified_scenes:
        raise ValueError(f"unsupported map_animation: {requested}")

    def compatible(composition):
        if composition in multi_pin_systems and pin_count < 2:
            return False
        if composition in multi_pin_scenes and pin_count < 2:
            return False
        if composition == "ed_yemen_markers" and pin_count != 3:
            return False
        return True

    if requested:
        if compatible(requested):
            return requested, "explicit"
        for fallback in fallbacks or []:
            candidate = str(fallback or "").strip()
            if candidate and candidate in certified and compatible(candidate):
                print(f"[dynamic-map] declared fallback {candidate!r} replaces incompatible {requested!r}",
                      flush=True)
                return candidate, "declared_fallback"
        raise ValueError(
            f"map_animation {requested!r} cannot run for {pin_count} pins and no "
            f"declared fallback is compatible")
    return "", "none"


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
    encoder_profile = resolve_encoder_profile(payload.get(
        "encoder_profile", {"codec": "h264_nvenc", "gpu": True, "preset": "p6", "quality": 15}))
    expected_sampler = resolve_map_sampler(payload.get(
        "sampler", default_map_sampler(encoder_profile)))
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
    # Repeated mentions are one stop per coordinate. Above the five-stop
    # budget the renderer FAILS CLOSED (see normalize_map_pins): it never
    # silently drops a grounded place — the planner splits the map group.
    pins = normalize_map_pins(raw_pins)
    if len(pins) != len(raw_pins):
        print(f"[dynamic-map] folded {len(raw_pins)} mentions into {len(pins)} unique stops", flush=True)
    # The voiceover's own per-pin schedule: every place activates exactly when
    # it is spoken. The renderer follows it; it never invents timing.
    pin_timing = parse_pin_timing(pins, payload.get("pin_timing"), duration_us)
    area_glow_radius_km = float(payload.get("area_glow_radius_km", 0.0))
    # Keep one predictable camera move available while map compositions are
    # being reviewed. Other camera variants are retired from runtime selection.
    camera_animations = {"slow_approach"}
    from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS
    from map_compositions import MAP_COMPOSITIONS, MULTI_PIN_SYSTEMS
    from map_editorial import MAP_EDITORIAL_SCENES, MULTI_PIN_SCENES
    from map_editorial_gpu import reset_gpu_counters, gpu_counters, geo_project
    camera_animation = str(payload.get("camera_animation", "slow_approach"))
    label_animation = str(payload.get("label_animation", "none"))
    map_animation = str(payload.get("map_animation", "") or "")
    basemap = str(payload.get("basemap", "esri_sat"))
    if camera_animation not in camera_animations:
        raise ValueError(f"unsupported camera_animation: {camera_animation}")
    if label_animation != "none" and label_animation not in MAP_LABEL_ANIMATIONS:
        raise ValueError(f"unsupported label_animation: {label_animation}")
    # Composition admission honors DECLARED fallbacks: an explicit id that
    # cannot run for this pin count is replaced only by a declared compatible
    # fallback (recorded below), and otherwise fails closed.
    map_animation, composition_source = resolve_declared_composition(
        map_animation, payload.get("fallbacks"), len(pins),
        MAP_COMPOSITIONS, MULTI_PIN_SYSTEMS, MAP_EDITORIAL_SCENES, MULTI_PIN_SCENES)
    if map_animation in MAP_EDITORIAL_SCENES and label_animation != "none":
        raise ValueError("certified editorial map scenes require label_animation='none'")
    expected_sampler = validate_encoder_sampler(
        encoder_profile, expected_sampler, editorial=map_animation in MAP_EDITORIAL_SCENES)
    if sampler_requires_opencl(expected_sampler, encoder_profile["codec"],
                               map_animation in MAP_EDITORIAL_SCENES):
        import cv2  # noqa: PLC0415 - bound before first use: the lazy import
        # block below runs later in this function, and referencing cv2 before
        # it would raise UnboundLocalError.
        if not cv2.ocl.haveOpenCL():
            raise RuntimeError("declared dynamic-map profile requires an active OpenCL device")
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
    # Validate once the editorial catalog is loaded below, before any map
    # acceptance gate or frame production is attempted.
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
    # Keep nearby towns visible in Chronon's editorial place-and-region view.
    if basemap == "chronon_editorial":
        level_zoom["municipality"] = 9.7
        level_zoom["city"] = 9.7
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
    # authored final hold. Dedicated multi-pin compositions keep their pins;
    # every other short multi-stop beat fails closed below (no silent drop).
    minimum_tour_seconds = 3.0 + 4.5 * (len(stops) - 1)
    if (
        len(stops) > 1
        and total_frames / geo.FPS < minimum_tour_seconds
        and route_timing is None
        and pin_timing is None
        and map_animation not in MULTI_PIN_SYSTEMS
        and map_animation not in MULTI_PIN_SCENES
    ):
        # Never drop places silently: the planner must split or re-time the
        # sequence before rendering. Fail closed with the names that would be lost.
        dropped = [stop.display_name for stop in stops[1:]]
        raise ValueError(
            f"dynamic-map: beat of {total_frames / geo.FPS:.2f}s cannot show "
            f"{len(stops)} stops (needs {minimum_tour_seconds:.1f}s); "
            f"would drop {dropped!r}. Split the map group or extend the beat."
        )
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
        bounds = scene_camera_bounds.get(map_animation,
                    (6.0, 36.0, 40.0, 66.0))
        if map_animation == "ed_yemen_fill":
            width_fraction, height_fraction = 0.55, 0.86
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
            max_zoom=8.0)
        camera_place = Place(query="Editorial map bounds", display_name="Editorial map bounds",
                             lat=center_lat, lon=center_lon, ok=True)
        builder = geo._ShotBuilder(camera_place, "dive", total_frames)
        # Start at a wider (lower zoom) view than the fitted target. The old
        # hard floor of z=8 could put country scenes inside their target zoom,
        # clipping the authored bounds at frame zero.
        builder.start_zoom = max(5.0, fitted_zoom-1.1)
        builder.end_zoom = fitted_zoom
        builder.ANCHORS = tuple((s.lat,s.lon) for s in stops) + ((center_lat,center_lon),)
        builder.PREPARE_ZMIN, builder.PREPARE_ZMAX = 5, max(8,math.ceil(fitted_zoom)+1)
        builder.full_duration_zoom = True
        builder.terminal_hold_frames = round(total_frames*.52)
        # Hormuz is an overlay-authored route animation; the path itself
        # moves through time even when the optimal wide geography uses one
        # quantized tile zoom for the whole shot.
        builder.allow_zoom_hold = map_animation == "ed_hormuz_routes"
        builder._editorial_stops = stops
    elif len(stops) == 1:
        builder = geo._ShotBuilder(stops[0], "dive", total_frames)
        builder.end_zoom = stop_zooms[0]
        # Start city approaches at metro scale and finish at street scale;
        # regional and national views stay at their authored overview zoom.
        if map_level(pins[0]) == "city":
            builder.end_zoom = min(17.0, stop_zooms[0])
            # Open at metro scale, then make the only retained slow approach.
            builder.start_zoom = max(8.0, builder.end_zoom - 1.4)
        else:
            builder.end_zoom = max(5.8, stop_zooms[0] - 0.9)
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
        # Use 60% of the clip for the approach, then hold the target for
        # the remaining 40% so the map animation can read at its destination.
        builder.terminal_hold_frames = round(total_frames * 0.40)
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
            pin_reductions = ()
            if pin_timing is not None:
                # Per-pin spoken timing paces the camera: each stop is held
                # exactly while its place is spoken, and travel legs take the
                # spoken gaps. The renderer follows the voiceover, never the
                # reverse.
                stop_seconds, travel_seconds, pin_reductions = tour_timing_from_pin_timing(pin_timing, geo.FPS)
                tour_seconds = 0.0
            else:
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
            if pin_timing is None:
                travel_seconds = min(2.4, max(1.8, tour_seconds / (1.9 * (len(stops) - 1))))
                stop_seconds = max(0.15, (tour_seconds - travel_seconds * (len(stops) - 1)) / len(stops))
            builder = geo.TourBuilder(stops, seconds_per_stop=stop_seconds,
                                      travel_seconds=travel_seconds, end_zoom=max(stop_zooms))
            builder.stop_end_zooms = stop_zooms
            if pin_reductions:
                builder._stop_frame_reductions = pin_reductions
            # Start much closer to the first city: this avoids a steep opening
            # zoom step on short, multi-stop routes and matches the requested
            # city-first framing.
            builder.initial_zoom_fraction = 0.90
            # Use the full stop window for each city dive. The default short
            # 0.58 fraction quantized to fewer than two useful frames on dense
            # five-stop routes and tripped the strict velocity gate at frame 0.
            builder.stop_dive_fraction = 1.0
            builder.initial_zoom_fraction = 0.90
            builder.stop_dive_fraction = 1.0
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
    if basemap == "chronon_editorial":
        # The editorial map is a fully offline vector plate (paper +
        # Natural Earth/ISTAT boundaries): no Esri raster, no provider credit
        # burnt into the frame. Provenance rides the telemetry instead.
        from vector_plate_pyramid import VectorPlatePyramid, PROVENANCE
        pyramid = VectorPlatePyramid()
        basemap_provenance = PROVENANCE
    else:
        pyramid = dyn.DynamicTilePyramid(provider=basemap)
        basemap_provenance = "Esri raster tiles (attribution burnt into frame)"
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
    # Plate budget (operator decision 2026-10-24: "non mi serve 4k, mi basta
    # 1920*1080"): classic compositions prepare plates smaller than the
    # historical 3x-canvas (4K-class) margin — but not below the ~2x-canvas
    # floor the fractional-zoom blend crop requires (see below).
    # Certified editorial scenes keep their wide-pan margin. A declared value
    # always wins; it must be finite and positive (fail-closed).
    plate_margin_factor = payload.get("plate_margin_factor")
    if plate_margin_factor is None:
        # The fractional-zoom blend samples level z+1 with a crop up to TWO
        # canvases wide (resize_level scale 2**(t-1) >= 0.5 -> w = W/scale + 4),
        # so a plate must be at least ~2x canvas wide to contain ANY blend
        # crop: margin 1.0 is geometrically impossible (every fractional zoom
        # raised "no prepared plate at zoom N"). 2.5 is the smallest value with
        # comfortable rounding/interpolation slack that is still below the
        # historical 3x-canvas (4K-class) plates.
        plate_margin_factor = 3.0 if map_animation in MAP_EDITORIAL_SCENES else 2.5
    else:
        plate_margin_factor = float(plate_margin_factor)
        if not math.isfinite(plate_margin_factor) or plate_margin_factor <= 0.0:
            raise ValueError("plate_margin_factor must be finite and positive")
    sampler.plate_margin_factor = plate_margin_factor
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
        # Uncovered zooms are clamped to the prepared plates (with a warning)
        # instead of aborting; the frame renderer applies the same clamp.
        zoom = geo.covered_zoom(sampler, lat, lon, zoom, width, height)
        if map_animation in editorial_country_scenes:
            def project(y, x, _a=(lat, lon), _z=zoom):
                return geo_project(y,x,_a,_z,width,height)
            project.anchor=(lat,lon)
            project.zoom=zoom
            visible_geometries = {
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
        raise RuntimeError("fail-closed sampler telemetry expected zero engine fallbacks")
    print(f"[dynamic-map] prepared zooms {sampler.z_min}..{sampler.z_max} plate_margin={sampler.plate_margin_factor}", flush=True)
    if pyramid.telemetry["late_tile_fetches"] != 0:
        raise RuntimeError(f"plate composition performed {pyramid.telemetry['late_tile_fetches']} late tile fetches")
    if pyramid.telemetry["tile_fallbacks"] != 0:
        raise RuntimeError(f"tile prefetch produced {pyramid.telemetry['tile_fallbacks']} fallback tiles")
    gate_started = time.perf_counter()
    # Validate the prepared CPU sampler before uploading the immutable plates.
    # The final render uses the GPU sampler for every composition; classic
    # compositions still do their legacy drawing on the host after sampling.
    if map_animation in MAP_EDITORIAL_SCENES:
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            raise RuntimeError("OpenCL GPU map renderer failed to initialize")
        if sampler.opencl_plates is None:
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
        raise RuntimeError(f"map acceptance gate observed {sampler.fallback_count} engine fallback frames")
    # Use the OpenCL plate sampler for every map composition. The classic
    # marker/label compositor remains CPU based (and reads the sampled frame
    # back), but the costly per-frame geographic crop/resize/blend stays on
    # the GPU. DYNAMIC_MAP_GPU_SAMPLER=0 is the operational rollback switch.
    # Editorial compositions additionally keep their existing all-GPU layer
    # compositor and its stricter acceptance counters.
    gpu_frame_renderer = expected_sampler == "opencv_opencl"
    if map_animation in MAP_EDITORIAL_SCENES and not gpu_frame_renderer:
        raise RuntimeError("editorial map compositions require the OpenCL GPU sampler")
    if encoder_profile["codec"] == "h264_nvenc" and not gpu_frame_renderer:
        raise RuntimeError("NVENC map encode profile requires the OpenCL map sampler")
    opencl_device_name = ""
    if gpu_frame_renderer:
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
        opencl_device_name = device.name()
        print(f"[dynamic-map] GPU map sampler: OpenCL / {opencl_device_name}; "
              f"overlay compositor={'OpenCL' if map_animation in MAP_EDITORIAL_SCENES else 'CPU'}", flush=True)
        sampler.gpu_map_enabled = True
        if sampler.opencl_plates is None:
            gpu_plate_bytes = sampler.prepare_opencl()
        print(f"[dynamic-map] uploaded {gpu_plate_bytes} map plate bytes to GPU", flush=True)
    else:
        cv2.ocl.setUseOpenCL(False)
        sampler.gpu_map_enabled = False
        gpu_plate_bytes = 0
        print(f"[dynamic-map] classic frame renderer: CPU process pool, workers={frame_workers()}; encoder={encoder_profile['codec']}", flush=True)
    sampler.editorial_gpu_enabled = bool(map_animation in MAP_EDITORIAL_SCENES)
    sampler.editorial_scene = map_animation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    reset_gpu_counters()
    workers = frame_workers()
    stats = harness.encode_with_pool(builder, sampler, args.output,
                                     workers=workers, block=2,
                                     preset=encoder_profile["preset"],
                                     crf=int(encoder_profile["quality"]),
                                     gpu_required=bool(encoder_profile["gpu"]))
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
        # Map decision mirror: the group identity, the planner's declared
        # strategy, the composition family and any declared fallback decision
        # ride the telemetry so one report explains this render end to end.
        "map_group": payload.get("map_group"),
        "map_group_strategy": payload.get("map_group_strategy"),
        "composition_family": payload.get("composition_family"),
        "composition_fallback": payload.get("composition_fallback"),
        "composition_source": composition_source,
        "pin_timing": ([{"id": str(pin.get("id")), "start_s": start_s, "duration_s": duration_s}
                        for pin, (start_s, duration_s) in zip(pins, pin_timing)]
                       if pin_timing is not None else None),
        "frames": total_frames,
        "dimensions": {"width": width, "height": height},
        "fps": {"num": fps_num, "den": fps_den},
        "tile": dict(pyramid.telemetry),
        "basemap_provenance": basemap_provenance,
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
        # Telemetry v1 compatibility; fail-closed sampling cannot fall back.
        "engine_fallback_frames": 0,
        "lo_only_blend_frames": int(stats.get("lo_only_blend_frames", 0)),
        "output_bytes": stats["bytes"],
        "video_encoder": stats["encoder"],
        "gpu_encoder": stats["gpu_encoder"],
        "frame_renderer": "opencv_opencl" if gpu_frame_renderer else "cpu_process_pool",
        "gpu_frame_renderer": "opencv_opencl" if gpu_frame_renderer else "none",
        "frame_workers": 1 if gpu_frame_renderer else workers,
        "gpu_map_sampler": "opencv_opencl" if gpu_frame_renderer else "cpu",
        "encoder_preset": stats["preset"],
        "encoder_quality": stats["quality"],
        "gpu_overlay_compositor": "opencv_umat_opencl" if map_animation in MAP_EDITORIAL_SCENES else "cpu",
        "gpu_overlay_counts": overlay_counts,
        "opencl_device": opencl_device_name,
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
