#!/usr/bin/env python3
"""Composable documentary-map layers and shot schedules.

All geometry inputs are explicit GeoJSON/WGS84 or pixel layers: this module
never downloads data. Coordinate projection is injected by the active camera.
"""
from __future__ import annotations

import math
from typing import Callable


def earthrise_zoom(start_zoom: float, end_zoom: float, progress: float) -> tuple[float, float]:
    """Return zoom and eased route draw-on for an overview rise from a detailed pin."""
    p = max(0.0, min(1.0, float(progress)))
    eased = p * p * (3.0 - 2.0 * p)
    return end_zoom + (start_zoom - end_zoom) * eased, eased


def beat_schedule(events: list[dict], beat_times_s: list[float], fps: float) -> list[dict]:
    """Snap event seconds to nearest supplied beat and return stable frame events."""
    if fps <= 0 or any(not math.isfinite(float(t)) or t < 0 for t in beat_times_s):
        raise ValueError("fps must be positive and beat times finite/nonnegative")
    beats = sorted(float(t) for t in beat_times_s)
    result = []
    for event in events:
        seconds = float(event["time_s"])
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("event time_s must be finite and nonnegative")
        snapped = min(beats, key=lambda beat: (abs(beat-seconds), beat)) if beats else seconds
        result.append({**event, "time_s": snapped, "frame": round(snapped * fps)})
    return result


def pose_label_anchor(latitude: float, longitude: float, pose: tuple,
                      project: Callable[[float, float, tuple], tuple[float, float]]):
    """Project a label against this frame's full camera pose, not a static point."""
    return project(latitude, longitude, pose)


def _polygons(geometry: dict):
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        return [coordinates]
    if kind == "MultiPolygon":
        return coordinates
    if kind == "GeometryCollection":
        return [polygon for item in geometry.get("geometries", [])
                for polygon in _polygons(item)]
    raise ValueError(f"unsupported region geometry: {kind!r}")


def _trim(points, fraction: float):
    if len(points) < 2:
        return points
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    target = sum(lengths) * max(0.0, min(1.0, fraction))
    out = [points[0]]
    for a, b, length in zip(points, points[1:], lengths):
        if target <= 0:
            break
        if length <= target:
            out.append(b)
            target -= length
        else:
            t = target / length
            out.append((round(a[0] + (b[0]-a[0])*t), round(a[1] + (b[1]-a[1])*t)))
            break
    return out


def _feature_key(feature: dict) -> str:
    properties = feature.get("properties") or {}
    return str(feature.get("id", properties.get("name", "")))


def _project_geometry(project, ring):
    import numpy as np
    return np.asarray([project(float(lon), float(lat)) for lon, lat in ring], np.int32)


def _polygon_color(value: float, value_range: tuple[float, float]):
    lo, hi = value_range
    t = 0.5 if hi == lo else max(0.0, min(1.0, (value - lo) / (hi - lo)))
    return (int(255 * (1-t)), 40, int(255*t))


def _draw_value_label(frame, mask, value: float) -> None:
    import cv2
    import numpy as np
    h, w = frame.shape[:2]
    moments = cv2.moments(mask, binaryImage=True)
    if moments["m00"] <= 0:
        return
    cx = round(moments["m10"] / moments["m00"])
    cy = round(moments["m01"] / moments["m00"])
    text = f"{value:g}"
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    origin = (cx-tw//2, cy+(th-baseline)//2)
    text_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.putText(text_mask, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 3, cv2.LINE_AA)
    cv2.putText(text_mask, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1, cv2.LINE_AA)
    frame[(text_mask != 0) & (mask != 0)] = (20, 24, 32)


def _region_draw_order(geojson: dict, values: dict | None):
    features = geojson.get("features")
    if not isinstance(features, list):
        raise ValueError("GeoJSON features must be a list")
    numeric = []
    for key, raw_value in (values or {}).items():
        value = float(raw_value)
        if not math.isfinite(value):
            raise ValueError(f"non-finite choropleth value for {key}")
        numeric.append(value)
    prepared = []
    for feature in features:
        if feature.get("type", "Feature") != "Feature":
            raise ValueError("GeoJSON FeatureCollection entries must be Features")
        key = _feature_key(feature)
        raw = None if values is None else values.get(key)
        value = None if raw is None else float(raw)
        if value is not None:
            if not math.isfinite(value):
                raise ValueError(f"non-finite choropleth value for {key}")
            numeric.append(value)
        prepared.append((feature, key, value))
    return prepared, numeric


def _feature_polygons(feature: dict):
    geometry = feature.get("geometry") or {}
    polygons = _polygons(geometry)
    normalized = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon or len(polygon[0]) < 4:
            raise ValueError(f"invalid polygon ring for region {_feature_key(feature)!r}")
        normalized.append(polygon)
    return normalized


def _draw_feature_mask(frame, polygon, project):
    import cv2
    import numpy as np
    h, w = frame.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for ring_index, ring in enumerate(polygon):
        pixels = _project_geometry(project, ring)
        cv2.fillPoly(mask, [pixels], 255 if ring_index == 0 else 0)
    return mask


def _composite_choropleth(frame, mask, value: float, value_range, alpha: float) -> None:
    import numpy as np
    color = _polygon_color(value, value_range)
    selected = mask != 0
    if np.any(selected):
        src = frame[selected].astype(np.float32)
        frame[selected] = np.clip(src * (1-alpha) + np.asarray(color) * alpha + 0.5,
                                  0, 255).astype(np.uint8)


def _draw_feature_outline(frame, exterior, progress: float,
                          outline_bgr, outline_width: int) -> None:
    import cv2
    import numpy as np
    points = exterior.reshape(-1, 2).tolist()
    reveal = _trim(points, progress)
    if len(reveal) >= 2:
        cv2.polylines(frame, [np.asarray(reveal, np.int32)], False,
                      outline_bgr, outline_width, cv2.LINE_AA)


def _draw_all_regions(frame, prepared, project, progress, values_range,
                      fill_alpha, outline_bgr, outline_width):
    import cv2
    for feature, _key, value in prepared:
        for polygon in _feature_polygons(feature):
            mask = _draw_feature_mask(frame, polygon, project)
            if value is not None and values_range is not None:
                _composite_choropleth(frame, mask, value, values_range, fill_alpha)
                _draw_value_label(frame, mask, value)
            exterior = _project_geometry(project, polygon[0])
            _draw_feature_outline(frame, exterior, progress, outline_bgr, outline_width)


def _draw_line_features(frame, geojson, project, progress, outline_bgr, width):
    import cv2
    import numpy as np
    kind = geojson.get("type")
    if kind != "FeatureCollection" or not isinstance(geojson.get("features"), list):
        raise ValueError("lines must be a GeoJSON FeatureCollection")
    for feature in geojson["features"]:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates", [])
        if geometry.get("type") == "LineString":
            lines = [coordinates]
        elif geometry.get("type") == "MultiLineString":
            lines = coordinates
        else:
            raise ValueError(f"unsupported line geometry: {geometry.get('type')!r}")
        for line in lines:
            pixels = _project_geometry(project, line)
            reveal = _trim(pixels.tolist(), progress)
            if len(reveal) >= 2:
                cv2.polylines(frame, [np.asarray(reveal, np.int32)], False,
                              outline_bgr, width, cv2.LINE_AA)


def draw_geojson_lines(frame, geojson: dict, project, progress: float, *,
                       color_bgr=(80, 220, 255), width: int = 3) -> None:
    """Draw-on GeoJSON LineString/MultiLineString routes in WGS84."""
    if width < 1:
        raise ValueError("line width must be positive")
    _draw_line_features(frame, geojson, project, progress, color_bgr, width)


def build_epoch_sampler(provider: str, release: int | None, width: int, height: int,
                        anchors, z_min: int, z_max: int):
    """Prepare an isolated provider/release sampler for an epoch comparison."""
    import sys
    from pathlib import Path
    cartography = Path(__file__).resolve().parents[3] / "Chronon3d" / "tools" / "cartography"
    if str(cartography) not in sys.path:
        sys.path.insert(0, str(cartography))
    from dynamic_tile_pyramid import DynamicTilePyramid
    from fast_plate_sampler import FastPlateSampler
    pyramid = DynamicTilePyramid(provider=provider, wayback_release=release)
    sampler = FastPlateSampler(pyramid, width, height)
    sampler.prepare(anchors, z_min, z_max)
    return sampler


def sample_epoch_pair(before_sampler, after_sampler, latitude: float, longitude: float,
                      zoom: float, width: int, height: int, progress: float):
    """Sample two independently prepared providers and apply the diagonal wipe."""
    before = before_sampler.sample(latitude, longitude, zoom, width, height)
    after = after_sampler.sample(latitude, longitude, zoom, width, height)
    return diagonal_wipe(before, after, progress)


def draw_space_to_street(frame, project, progress: float, route_geojson: dict | None = None):
    """Standardized space-to-street overlay hook for the standalone camera preset."""
    if route_geojson is not None:
        draw_geojson_lines(frame, route_geojson, project, progress)


def draw_camera_aligned_label(frame, point, text: str, pose: tuple, project,
                              progress: float, *, color=(255,255,255)):
    """Place a compact label at a pose-projected anchor."""
    import cv2
    latitude, longitude = point
    x, y = pose_label_anchor(latitude, longitude, pose, project)
    cv2.putText(frame, text, (round(x), round(y)), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, color, 2, cv2.LINE_AA)



def draw_geojson_regions(frame, geojson: dict, project, progress: float, *,
                         values: dict | None = None, fill_alpha: float = 0.32,
                         outline_bgr=(255, 245, 220), outline_width: int = 2,
                         value_range: tuple[float, float] | None = None) -> None:
    """Draw Polygon/MultiPolygon FeatureCollections with holes and draw-on outlines.

    `project(lon, lat)` maps source coordinates into the frame. Numeric values
    are keyed by feature id/name, mapped blue-to-red and printed inside their
    feature. GeometryCollection polygon members are supported as well.
    """
    import cv2
    import numpy as np
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("regions must be a GeoJSON FeatureCollection")
    if not 0.0 <= fill_alpha <= 1.0:
        raise ValueError("fill_alpha must be in [0, 1]")
    prepared, numeric = _region_draw_order(geojson, values)
    if value_range is None and numeric:
        value_range = (min(numeric), max(numeric))
    if value_range is not None:
        lo, hi = map(float, value_range)
        if not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
            raise ValueError("value_range must be finite and ordered")
        value_range = (lo, hi)
    _draw_all_regions(frame, prepared, project, float(progress), value_range,
                      fill_alpha, outline_bgr, outline_width)


def draw_radar_pulse(frame, point: tuple[int, int], progress: float, *,
                     color_bgr=(40, 80, 255), rings: int = 3,
                     max_radius: int = 110) -> None:
    """Draw phase-offset expanding rings around a projected hotspot."""
    import cv2
    if rings < 1 or max_radius < 1:
        raise ValueError("rings and max_radius must be positive")
    p = float(progress) % 1.0
    for i in range(rings):
        phase = (p + i / rings) % 1.0
        radius = max(1, round(4 + (max_radius-4) * phase))
        alpha = 1.0 - phase
        color = tuple(round(c * alpha) for c in color_bgr)
        cv2.circle(frame, tuple(map(int, point)), radius, color, 2, cv2.LINE_AA)


_WIPE_DIAGONAL_FIELDS = {}


def diagonal_wipe(before, after, progress: float, frame_shape=None):
    """Composite a diagonal epoch wipe; UMat frames stay on OpenCL.

    NumPy inputs retain the offline CPU API and full shape/dtype validation.
    UMat inputs are expected to be matching uint8 BGR camera frames (as
    produced by FastPlateSampler); shape metadata is not downloaded from the
    device, and the full-resolution mask selection stays in OpenCV/OpenCL.
    """
    import cv2
    import numpy as np

    gpu = isinstance(before, cv2.UMat) or isinstance(after, cv2.UMat)
    p = max(0.0, min(1.0, float(progress)))
    if gpu:
        if not cv2.ocl.useOpenCL():
            raise RuntimeError("OpenCL must be active for UMat epoch compositing")
        before_gpu = before if isinstance(before, cv2.UMat) else cv2.UMat(before)
        after_gpu = after if isinstance(after, cv2.UMat) else cv2.UMat(after)
        # The camera output dimensions are stable throughout a render. Upload
        # the normalized diagonal ramp once per resolution; only the scalar
        # threshold and two GPU copies execute for each frame.
        # UMat dimensions are not exposed consistently by OpenCV's Python API;
        # pass the known sampler frame dimensions rather than downloading a
        # full frame merely to discover its shape.
        if frame_shape is None or len(frame_shape) < 2:
            raise ValueError("UMat epoch wipe requires frame_shape=(height, width)")
        h, w = map(int, frame_shape[:2])
        field = _WIPE_DIAGONAL_FIELDS.get((h, w))
        if field is None:
            yy, xx = np.mgrid[:h, :w]
            ramp = ((xx / max(1, w - 1) + yy / max(1, h - 1)) / 2.0).astype(np.float32)
            field = cv2.UMat(ramp)
            _WIPE_DIAGONAL_FIELDS[(h, w)] = field
        mask = cv2.compare(field, p, cv2.CMP_LE)
        result = cv2.UMat(h, w, cv2.CV_8UC3)
        cv2.copyTo(after_gpu, mask, result)
        inverse = cv2.bitwise_not(mask)
        cv2.copyTo(before_gpu, inverse, result)
        return result

    if before.shape != after.shape or before.dtype != after.dtype:
        raise ValueError("comparison epoch frames must have identical shape and dtype")
    h, w = before.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    mask = (xx / max(1, w-1) + yy / max(1, h-1)) / 2.0 <= p
    return np.where(mask[..., None], after, before)


def apply_hillshade(frame, hillshade, alpha: float = 0.25):
    """Blend an explicitly supplied, already aligned grayscale/RGB relief layer."""
    import cv2
    import numpy as np
    if hillshade.shape[:2] != frame.shape[:2]:
        raise ValueError("hillshade dimensions must match the camera frame")
    if not 0 <= alpha <= 1:
        raise ValueError("hillshade alpha must be in [0, 1]")
    relief = hillshade
    if relief.ndim == 2:
        relief = cv2.cvtColor(relief, cv2.COLOR_GRAY2BGR)
    if relief.shape != frame.shape:
        raise ValueError("hillshade must be grayscale or match frame channels")
    return cv2.addWeighted(frame, 1-alpha, relief.astype(np.uint8), alpha, 0)


def space_to_street_zoom(progress: float, start_zoom: float = 5.0,
                         end_zoom: float = 18.0) -> float:
    """C2 zoom schedule reusable by a GeoRuntime shot builder."""
    p = max(0.0, min(1.0, float(progress)))
    e = p*p*p*(p*(p*6-15)+10)
    return start_zoom + (end_zoom-start_zoom)*e
