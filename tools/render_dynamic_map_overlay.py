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
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "Chronon3d/tools/cartography"))
sys.path.insert(0, str(HERE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    width, height = int(payload["width"]), int(payload["height"])
    fps_num, fps_den = int(payload["fps_num"]), int(payload["fps_den"])
    duration_us = int(payload["duration_us"])
    pins = payload.get("pins", [])
    area_glow_radius_km = float(payload.get("area_glow_radius_km", 0.0))
    camera_animations = {"signature_dive", "tilt_reveal", "orbit_arrival",
                         "slow_approach", "wide_context"}
    from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS
    camera_animation = str(payload.get("camera_animation", "signature_dive"))
    label_animation = str(payload.get("label_animation", "gentle_fade"))
    if camera_animation not in camera_animations:
        raise ValueError(f"unsupported camera_animation: {camera_animation}")
    if label_animation not in MAP_LABEL_ANIMATIONS:
        raise ValueError(f"unsupported label_animation: {label_animation}")
    if width < 16 or height < 16 or fps_num <= 0 or fps_den <= 0 or duration_us <= 0 or not pins:
        raise ValueError("dynamic map requires valid canvas, frame rate, duration and at least one pin")
    if not math.isfinite(area_glow_radius_km) or not 0.0 <= area_glow_radius_km <= 1000.0:
        raise ValueError("area_glow_radius_km must be finite and in [0, 1000]")
    if any(not math.isfinite(float(p[k])) for p in pins for k in ("latitude", "longitude")):
        raise ValueError("map coordinates must be finite")

    import cv2
    import geo_runtime as geo
    import fast_geo_camera as harness
    import dynamic_tile_pyramid as dyn
    import fast_plate_sampler as fast
    cv2.setNumThreads(1)
    geo.WIDTH, geo.HEIGHT, geo.FPS = width, height, fps_num / fps_den
    total_frames = max(2, round(duration_us * fps_num / (1_000_000 * fps_den)))
    stops = [geo.Place(
        query=str(pin.get("label") or pin["id"]),
        display_name=str(pin.get("label") or pin["id"]),
        lat=float(pin["latitude"]), lon=float(pin["longitude"]), ok=True,
    ) for pin in pins]

    def map_level(pin):
        scope = str(pin.get("scope") or "").strip().lower()
        if scope in {"continent", "country", "region", "city"}:
            return scope
        return "city"

    level_zoom = {"continent": 2.5, "country": 5.0, "region": 8.0, "city": 13.7}
    stop_zooms = [level_zoom[map_level(pin)] for pin in pins]

    if len(stops) == 1:
        preset = {"tilt_reveal": "tilt", "orbit_arrival": "orbit"}.get(camera_animation, "dive")
        builder = geo._ShotBuilder(stops[0], preset, total_frames)
        builder.end_zoom = stop_zooms[0]
        if camera_animation == "wide_context":
            builder.end_zoom = max(5.8, stop_zooms[0] - 2.0)
        elif camera_animation == "slow_approach":
            builder.end_zoom = max(5.8, stop_zooms[0] - 0.9)
    else:
        travel_seconds = min(1.0, duration_us / 1_000_000 / (2 * (len(stops) - 1)))
        stop_seconds = max(0.15, (duration_us / 1_000_000 - travel_seconds * (len(stops) - 1)) / len(stops))
        builder = geo.TourBuilder(stops, seconds_per_stop=stop_seconds,
                                  travel_seconds=travel_seconds, end_zoom=max(stop_zooms))
        builder.stop_end_zooms = stop_zooms
        builder.initial_zoom_fraction = 0.5
        builder.stop_dive_fraction = 0.58
        if camera_animation == "tilt_reveal":
            builder.initial_zoom_fraction = 0.54
            builder.stop_dive_fraction = 0.62
        elif camera_animation == "orbit_arrival":
            builder.initial_zoom_fraction = 0.58
            builder.stop_dive_fraction = 0.60
        elif camera_animation == "slow_approach":
            builder.initial_zoom_fraction = 0.62
            builder.stop_dive_fraction = 0.72
        elif camera_animation == "wide_context":
            builder.stop_end_zooms = [max(5.8, zoom - 1.7) for zoom in stop_zooms]
        builder.end_zoom = max(builder.stop_end_zooms)
        # Honor the frozen overlay duration exactly; the tour builder computes
        # its own frame count from stop/travel phases.
        builder.TOTAL_FRAMES = total_frames
        builder.FRAMES_TOTAL = total_frames

    # Production map overlays are clean satellite imagery: show only the
    # current place name, with no altitude HUD, diagnostic headings, route
    # graphics, attribution stamp, descent caption or progress bar.
    builder.minimal_map = True
    builder.map_area_glow_radius_km = area_glow_radius_km
    builder.map_label_animation = label_animation

    if builder.WIDTH != width or builder.HEIGHT != height:
        raise ValueError("Chronon geo camera output dimensions do not match the overlay canvas")
    pyramid = dyn.DynamicTilePyramid(provider="esri_sat")
    anchors = list(builder.ANCHORS)
    # Warm one coarse bridge plate per leg before worker processes fork. Tour
    # movement pulls out to this scale before crossing the map.
    for index in range(len(stops) - 1):
        a, b = stops[index], stops[index + 1]
        anchors.append(((a.lat + b.lat) / 2, (a.lon + b.lon) / 2))
    # Only prepare levels the animation can sample. Fractional zoom blends
    # z and z+1, so include the next integer above the deepest stop.
    prepare_zmax = min(builder.PREPARE_ZMAX,
                       max(6, math.ceil(max(stop_zooms)) + 1))
    for index, (lat, lon) in enumerate(anchors):
        zmax = prepare_zmax
        if index >= len(stops):
            leg = index - len(stops)
            a, b = stops[leg], stops[leg + 1]
            ax, ay = dyn.latlon_to_global_px(a.lat, a.lon, 5)
            bx, by = dyn.latlon_to_global_px(b.lat, b.lon, 5)
            leg_zoom = 5.0 + math.log2((0.72 * width) / max(math.hypot(bx - ax, by - ay), 1.0))
            zmax = min(zmax, max(6, math.ceil(leg_zoom) + 1))
        print(f"[dynamic-map] prefetch anchor {index + 1}/{len(anchors)} z=5..{zmax}", flush=True)
        radius = 6 if index >= len(stops) else 4
        pyramid.prefetch_pyramid(lat, lon, min_zoom=5, max_zoom=zmax,
                                 tile_radius_x=radius, tile_radius_y=max(4, radius - 1))

    # Compose each zoom plate once, then render frames as crops/resizes. The
    # previous sampler rebuilt the same tile mosaic for every frame.
    sampler = fast.FastPlateSampler(pyramid, width, height)
    sampler.prepare(builder.ANCHORS, builder.PREPARE_ZMIN, prepare_zmax)
    print(f"[dynamic-map] prepared zooms {sampler.z_min}..{sampler.z_max}", flush=True)
    geo.gate_builder(builder, sampler, "production-map-overlay")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = harness.encode_with_pool(builder, sampler, args.output,
                                     workers=min(8, max(1, (os.cpu_count() or 2) // 2)),
                                     block=2, preset="veryfast", crf=18)
    if stats.get("engine_fallback_frames", 0):
        raise RuntimeError(f"map sampler used fallback imagery in {stats['engine_fallback_frames']} frames")
    print(f"DYNAMIC_MAP_PASS frames={total_frames} provider=esri_sat output={args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
