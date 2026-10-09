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
    raw_pins = payload.get("pins", [])
    # Keep a route map focused: repeated mentions of the same place are one
    # stop, and no tour may contain more than five distinct stops.
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
                         "slow_approach", "wide_context"}
    from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS
    camera_animation = str(payload.get("camera_animation", "signature_dive"))
    label_animation = str(payload.get("label_animation", "gentle_fade"))
    basemap = str(payload.get("basemap", "esri_sat"))
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

    # Keep country and region maps at a broad reference scale. City maps land
    # near street level; 17.0 is within the certified local tile pyramid.
    level_zoom = {"continent": 2.5, "country": 5.0, "region": 8.0, "city": 17.0}
    stop_zooms = [level_zoom[map_level(pin)] for pin in pins]

    if len(stops) == 1:
        preset = {"tilt_reveal": "tilt", "orbit_arrival": "orbit"}.get(camera_animation, "dive")
        builder = geo._ShotBuilder(stops[0], preset, total_frames)
        builder.end_zoom = stop_zooms[0]
        # Start city approaches at metro scale and finish at street scale;
        # regional and national views stay at their authored overview zoom.
        builder.start_zoom = min(builder.end_zoom, max(10.0, builder.end_zoom - 4.5))
        # City maps spend the full 6.5-second camera window approaching the
        # destination, then remain still for the 1.5-second label read.
        builder.full_duration_zoom = True
        builder.terminal_hold_frames = round(1.5 * fps_num / fps_den)
        if camera_animation == "wide_context":
            builder.end_zoom = max(5.8, stop_zooms[0] - 2.0)
        elif camera_animation == "slow_approach":
            builder.end_zoom = max(5.8, stop_zooms[0] - 0.9)
    else:
        # Keep the previous five-second camera tour, then hold the final
        # destination for another 1.5 seconds. The builder's timeline ends
        # before TOTAL_FRAMES, so its final-pose fallback supplies that hold.
        tour_seconds = max(1.0, duration_us / 1_000_000 - 1.5)
        travel_seconds = min(1.5, tour_seconds / (2 * (len(stops) - 1)))
        stop_seconds = max(0.15, (tour_seconds - travel_seconds * (len(stops) - 1)) / len(stops))
        builder = geo.TourBuilder(stops, seconds_per_stop=stop_seconds,
                                  travel_seconds=travel_seconds, end_zoom=max(stop_zooms))
        builder.stop_end_zooms = stop_zooms
        builder.initial_zoom_fraction = 0.62
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
    pyramid = dyn.DynamicTilePyramid(provider=basemap)
    anchors = list(builder.ANCHORS)
    # The camera pans through each route midpoint. Include each midpoint in the
    # plate union so every camera center on a linearly interpolated route is
    # covered by the coarse leg plate.
    for index in range(len(stops) - 1):
        a, b = stops[index], stops[index + 1]
        anchors.append(((a.lat + b.lat) / 2, (a.lon + b.lon) / 2))
    # Only prepare levels the animation can sample. Fractional zoom blends
    # z and z+1, so include the next integer above the deepest stop.
    prepare_zmin = min(builder.PREPARE_ZMIN, max(0, math.floor(min(stop_zooms))))
    # The current frame sampler cannot consume zooms below its historic z=5
    # floor; clamp the authored flight to that certified floor instead of
    # allocating world-sized plates or falling back during a coarse shot.
    if prepare_zmin < 5:
        if len(stops) == 1:
            builder.end_zoom = max(5.0, builder.end_zoom)
        else:
            builder.stop_end_zooms = [max(5.0, zoom) for zoom in builder.stop_end_zooms]
            builder.end_zoom = max(builder.stop_end_zooms)
        stop_zooms = [max(5.0, zoom) for zoom in stop_zooms]
        prepare_zmin = 5
    # Regional routes use a lower zoom while crossing distance, but each stop
    # still needs its local high-zoom tiles for the city arrival. Do not cap
    # the prepared pyramid at the route builder's broad-span limit.
    prepare_zmax = min(18, max(builder.PREPARE_ZMAX,
                               6, math.ceil(max(stop_zooms)) + 1))
    if prepare_zmax < prepare_zmin:
        prepare_zmax = prepare_zmin

    # The camera may zoom out to show an entire route leg. Validate its actual
    # frame trajectory at the integer-sampling boundary before encoding; never
    # rely on the sampler's slow fallback to hide an undersized plate.
    for leg_index in range(len(stops) - 1):
        a, b = stops[leg_index], stops[leg_index + 1]
        ax, ay = dyn.latlon_to_global_px(a.lat, a.lon, 5)
        bx, by = dyn.latlon_to_global_px(b.lat, b.lon, 5)
        leg_zoom = max(5.2, min(max(stop_zooms), 5.0 + math.log2(
            (0.72 * width) / max(math.hypot(bx - ax, by - ay), 1.0))))
        prepare_zmax = max(prepare_zmax, math.ceil(leg_zoom) + 1)

    sampler = fast.FastPlateSampler(pyramid, width, height)
    sampler.gpu_map_enabled = False
    sampler.prepare(anchors, prepare_zmin, prepare_zmax)
    for frame_idx in range(total_frames):
        if len(stops) > 1:
            lat, lon, zoom = builder.pose(frame_idx)
        else:
            lat, lon = stops[0].lat, stops[0].lon
            zoom = builder.pose(frame_idx)[0]
        if not sampler.can_sample(lat, lon, zoom, width, height):
            raise RuntimeError(
                f"prepared map plates do not cover camera frame {frame_idx} "
                f"at zoom {zoom:.3f}; refusing slow fallback")
    if sampler.fallback_count != 0:
        raise RuntimeError("geometry-only sampler coverage check invoked the slow renderer")
    print(f"[dynamic-map] prepared zooms {sampler.z_min}..{sampler.z_max}", flush=True)
    if pyramid.telemetry["late_tile_fetches"] != 0:
        raise RuntimeError(f"plate composition performed {pyramid.telemetry['late_tile_fetches']} late tile fetches")
    if pyramid.telemetry["tile_fallbacks"] != 0:
        raise RuntimeError(f"tile prefetch produced {pyramid.telemetry['tile_fallbacks']} fallback tiles")
    gate_started = time.perf_counter()
    geo.gate_builder(builder, sampler, "production-map-overlay")
    gate_ms = (time.perf_counter() - gate_started) * 1000.0
    if sampler.fallback_count != 0:
        raise RuntimeError(f"map acceptance gate used {sampler.fallback_count} slow-engine fallback frames")
    # The acceptance gate is deliberately CPU-only and small. Actual video
    # frames use OpenCL on the NVIDIA device, then stream to NVENC.
    cv2.ocl.setUseOpenCL(True)
    if not cv2.ocl.useOpenCL():
        raise RuntimeError("OpenCL GPU map renderer failed to initialize")
    device = cv2.ocl.Device.getDefault()
    if "NVIDIA" not in device.vendorName().upper():
        raise RuntimeError(f"GPU map renderer selected unexpected device: {device.name()}")
    print(f"[dynamic-map] GPU frame renderer: OpenCL / {device.name()}", flush=True)
    gpu_plate_bytes = sampler.prepare_opencl()
    print(f"[dynamic-map] uploaded {gpu_plate_bytes} map plate bytes to GPU", flush=True)
    sampler.gpu_map_enabled = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = harness.encode_with_pool(builder, sampler, args.output,
                                     workers=min(2, max(1, (os.cpu_count() or 2) // 2)),
                                     block=2, preset="slow", crf=15,
                                     gpu_required=True)
    if stats.get("engine_fallback_frames", 0):
        raise RuntimeError(f"map sampler used fallback imagery in {stats['engine_fallback_frames']} frames")
    summary = {
        "schema": "chronon.dynamic-map-telemetry.v1",
        "basemap": basemap,
        "frames": total_frames,
        "dimensions": {"width": width, "height": height},
        "fps": {"num": fps_num, "den": fps_den},
        "tile": dict(pyramid.telemetry),
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
