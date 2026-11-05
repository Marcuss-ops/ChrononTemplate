#!/usr/bin/env python3
"""Build the extruded 3D title mesh for the Caesar apotheosis scene.

Playfair Display outlines are flattened with fontTools and triangulated with
holes by mapbox_earcut. The resulting caps and side walls are written as an
InlineMeshPlan payload for Chronon3D. This is asset preparation only: the
render, camera, light rig, depth of field and video are Chronon3D's.

Usage:
    python3 tools/showcases/build_giulio_cesare_title_mesh.py
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mapbox_earcut
import numpy as np
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = TEMPLATE_ROOT.parent
FONT = PROJECT_ROOT / "Chronon3d" / "assets" / "fonts" / "PlayfairDisplay-Bold.ttf"
OUT = TEMPLATE_ROOT / "assets" / "giulio_cesare_apoteosi_v1" / "giulio_cesare_title_mesh.json"

TEXT = "GIULIO CESARE"
FONT_SIZE = 200.0
TRACKING = 8.0
CURVE_STEPS = 12
DEPTH_RATIO = 0.07
MATERIAL = {
    "diffuse": 0.78,
    "specular": 0.55,
    "shininess": 44.0,
    "rim_intensity": 0.25,
    "base_color": [0.86, 0.73, 0.46, 1.0],
    "metallic": 0.30,
    "roughness": 0.34,
    "emissive": [0.10, 0.065, 0.022],
    "double_sided": True,
}


def quad(p0, control, p1):
    out = []
    for i in range(1, CURVE_STEPS + 1):
        t = i / CURVE_STEPS
        u = 1.0 - t
        out.append((u * u * p0[0] + 2 * u * t * control[0] + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * control[1] + t * t * p1[1]))
    return out


def cubic(p0, c1, c2, p1):
    out = []
    for i in range(1, CURVE_STEPS + 1):
        t = i / CURVE_STEPS
        u = 1.0 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                    u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))
    return out


def glyph_contours(font: TTFont, char: str) -> tuple[str, list[list[tuple[float, float]]]]:
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    glyph_name = cmap[ord(char)]
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(pen)

    contours: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    start = None
    for op, args in pen.value:
        if op == "moveTo":
            if len(current) >= 3:
                contours.append(current)
            current = [args[0]]
            start = args[0]
        elif op == "lineTo":
            current.append(args[0])
        elif op == "qCurveTo":
            points = list(args)
            if points[-1] is None:
                points = points[:-1] + [start]
            offs, end = points[:-1], points[-1]
            for i, control in enumerate(offs):
                if i + 1 < len(offs):
                    nxt = offs[i + 1]
                    mid = ((control[0] + nxt[0]) * 0.5, (control[1] + nxt[1]) * 0.5)
                    current.extend(quad(current[-1], control, mid))
                else:
                    current.extend(quad(current[-1], control, end))
        elif op == "curveTo":
            current.extend(cubic(current[-1], args[0], args[1], args[2]))
        elif op == "closePath":
            if len(current) >= 3:
                if current[-1] == current[0]:
                    current.pop()
                contours.append(current)
            current = []
    if len(current) >= 3:
        contours.append(current)

    cleaned: list[list[tuple[float, float]]] = []
    for contour in contours:
        points: list[tuple[float, float]] = []
        for point in contour:
            point = (float(point[0]), float(point[1]))
            if not points or math.dist(point, points[-1]) > 1e-7:
                points.append(point)
        if len(points) >= 3 and math.dist(points[0], points[-1]) < 1e-7:
            points.pop()
        if len(points) >= 3:
            cleaned.append(points)
    return glyph_name, cleaned


def signed_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))


def point_in_polygon(point, polygon) -> bool:
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            x_cross = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < x_cross:
                inside = not inside
    return inside


def glyph_mesh(font: TTFont, char: str) -> tuple[list[list[tuple[float, float]]], float]:
    glyph_name, contours = glyph_contours(font, char)
    scale = FONT_SIZE / font["head"].unitsPerEm
    advance = font["hmtx"][glyph_name][0] * scale
    if not contours:
        return [], advance

    areas = [signed_area(contour) for contour in contours]
    depth = []
    for i, contour in enumerate(contours):
        depth.append(sum(1 for j, other in enumerate(contours) if i != j and point_in_polygon(contour[0], other)))
    outers = [i for i, d in enumerate(depth) if d % 2 == 0]
    holes = [i for i, d in enumerate(depth) if d % 2 == 1]
    groups: list[list[list[tuple[float, float]]]] = []

    for outer in outers:
        ring = list(contours[outer])
        if signed_area(ring) < 0:
            ring.reverse()
        group = [ring]
        containing = []
        for hole in holes:
            if point_in_polygon(contours[hole][0], contours[outer]):
                containing.append((abs(areas[outer]), hole))
        for _, hole in sorted(containing):
            hole_ring = list(contours[hole])
            if signed_area(hole_ring) > 0:
                hole_ring.reverse()
            group.append(hole_ring)
        groups.append(group)
    scaled = [[[(x * scale, y * scale) for x, y in ring] for ring in group] for group in groups]
    return scaled, advance


def build_mesh() -> dict:
    font = TTFont(str(FONT))
    cursor = 0.0
    placed: list[list[list[tuple[float, float]]]] = []
    for char in TEXT:
        groups, advance = glyph_mesh(font, char)
        for group in groups:
            placed.append([[(x + cursor, y) for x, y in ring] for ring in group])
        cursor += advance + TRACKING

    all_points = [point for group in placed for ring in group for point in ring]
    if not all_points:
        raise ValueError("title produced no contours")
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    height = max_y - min_y
    if height <= 0:
        raise ValueError("title has no height")
    center_x = 0.5 * (min_x + max_x)
    center_y = 0.5 * (min_y + max_y)

    vertices: list[dict] = []
    indices: list[int] = []

    def add_vertex(x, y, z, nx, ny, nz):
        vertices.append({
            "position": [round(float(x), 5), round(float(y), 5), round(float(z), 5)],
            "normal": [round(float(nx), 5), round(float(ny), 5), round(float(nz), 5)],
            "uv": [0.0, 0.0],
        })
        return len(vertices) - 1

    def tri(a, b, c):
        indices.extend((a, b, c))

    for group in placed:
        flat = []
        ends = []
        for ring in group:
            for x, y in ring:
                flat.append(((x - center_x) / height, (y - center_y) / height))
            ends.append(len(flat))
        triangles = mapbox_earcut.triangulate_float64(
            np.asarray(flat, dtype=np.float64),
            np.asarray(ends, dtype=np.uint32),
        )
        if triangles.size == 0:
            raise ValueError("mapbox_earcut returned no triangles for a glyph")
        for raw in triangles.reshape(-1, 3):
            a, b, c = (flat[int(i)] for i in raw)
            # Back cap faces +Z.
            ba = add_vertex(a[0], a[1], DEPTH_RATIO * 0.5, 0, 0, 1)
            bb = add_vertex(b[0], b[1], DEPTH_RATIO * 0.5, 0, 0, 1)
            bc = add_vertex(c[0], c[1], DEPTH_RATIO * 0.5, 0, 0, 1)
            tri(ba, bb, bc)
            # Front cap faces the camera at -Z.
            fa = add_vertex(a[0], a[1], -DEPTH_RATIO * 0.5, 0, 0, -1)
            fb = add_vertex(b[0], b[1], -DEPTH_RATIO * 0.5, 0, 0, -1)
            fc = add_vertex(c[0], c[1], -DEPTH_RATIO * 0.5, 0, 0, -1)
            tri(fc, fb, fa)
        for ring in group:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                ax, ay = (a[0] - center_x) / height, (a[1] - center_y) / height
                bx, by = (b[0] - center_x) / height, (b[1] - center_y) / height
                dx, dy = bx - ax, by - ay
                length = math.hypot(dx, dy)
                if length <= 1e-8:
                    continue
                nx, ny = dy / length, -dx / length
                fa = add_vertex(ax, ay, -DEPTH_RATIO * 0.5, nx, ny, 0)
                fb = add_vertex(bx, by, -DEPTH_RATIO * 0.5, nx, ny, 0)
                bb = add_vertex(bx, by, DEPTH_RATIO * 0.5, nx, ny, 0)
                ba = add_vertex(ax, ay, DEPTH_RATIO * 0.5, nx, ny, 0)
                tri(fa, fb, bb)
                tri(fa, bb, ba)

    if len(vertices) > 250_000 or len(indices) > 750_000:
        raise ValueError("title mesh exceeds InlineMeshPlan limits")
    return {
        "source": {
            "font": str(FONT.relative_to(PROJECT_ROOT)),
            "text": TEXT,
            "generator": "tools/showcases/build_giulio_cesare_title_mesh.py",
        },
        "metrics": {
            "width": round((max_x - min_x) / height, 5),
            "height": 1.0,
            "depth": DEPTH_RATIO,
            "vertices": len(vertices),
            "triangles": len(indices) // 3,
        },
        "material": MATERIAL,
        "vertices": vertices,
        "indices": indices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if OUT.exists() and not args.force:
        print(f"exists: {OUT}")
        return
    mesh = build_mesh()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(mesh, separators=(",", ":"), allow_nan=False) + "\n")
    m = mesh["metrics"]
    print(f"title: {m['vertices']} vertices, {m['triangles']} triangles, "
          f"width={m['width']:.3f} height={m['height']:.3f} -> {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
