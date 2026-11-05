#!/usr/bin/env python3
"""A real extruded-text experiment for the text_3d_v1 bullet family.

The shipping four-family clip uses a 2.5D scale push because the Vulkan text
lane culls `enable_3d` + `rotation_y` text layers. This experiment takes the
other route: it converts Inter-Black glyph outlines to polygons, extrudes them
into one closed mesh (front caps, back caps and side walls), and renders that
mesh with a perspective camera.

`TEXT` is deliberate: T, E, X and T are single-contour glyphs in Inter-Black,
so the profile is a simple polygon and no hole triangulation is needed. The
plan is a standalone study, `05_text_3d_mesh`, and does not touch the four
uploaded family clips.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "bullet_points_text3d_mesh_v1" / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
BG = [0.043, 0.051, 0.063, 1.0]
INK = "#F6F2E9"
BODY = "#DAD5CA"
MUTED = "#8C8880"
FOOTER = "#5F5C57"
ACCENT = "#B9A7FF"
FONT_FILE = "assets/fonts/Inter-Black.ttf"
WORD = "TEXT"
FONT_SIZE = 300.0
TRACKING = 18.0
DEPTH = 36.0
STEPS_PER_CURVE = 10

KICKER = "M E S H   S T U D Y"
POINTS = [
    "I contorni dei glifi diventano geometria",
    "L'estrusione aggiunge profondità reale",
    "La camera misura il volume, non un'illusione",
]


def hex_rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def fade(start, end):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, 1.0), (FRAMES - 1, 1.0)])}


def text_layer(lid, text, x, y, w, h, font, size, fill, start=0, tracks=None,
               screen_space=True):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
        "style": {
            "font": f"assets/fonts/{font}",
            "font_size": size,
            "min_font_size": size,
            "max_font_size": size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if screen_space:
        layer["screen_space"] = True
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, color, w, h, x, y, start=0, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [w, h],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
        "screen_space": True,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


# ── glyph outlines ───────────────────────────────────────────────────────────

def _quad(p0, c, p1, steps=STEPS_PER_CURVE):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1.0 - t
        out.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
    return out


def _cubic(p0, c1, c2, p1, steps=STEPS_PER_CURVE):
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1.0 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                    u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))
    return out


def glyph_contours(font, char):
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    glyph_name = cmap[ord(char)]
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[glyph_name].draw(pen)

    contours, current = [], []
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
                    current.extend(_quad(current[-1], control, mid))
                else:
                    current.extend(_quad(current[-1], control, end))
        elif op == "curveTo":
            c1, c2, end = args
            current.extend(_cubic(current[-1], c1, c2, end))
        elif op == "closePath":
            if len(current) >= 3:
                if current[-1] == current[0]:
                    current.pop()
                contours.append(current)
            current = []
    if len(current) >= 3:
        contours.append(current)

    cleaned = []
    for contour in contours:
        pts = []
        for p in contour:
            p = (float(p[0]), float(p[1]))
            if not pts or math.dist(p, pts[-1]) > 1e-7:
                pts.append(p)
        if len(pts) >= 3 and math.dist(pts[0], pts[-1]) <= 1e-7:
            pts.pop()
        if len(pts) >= 3:
            cleaned.append(pts)
    return glyph_name, cleaned


def signed_area(points):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1]
                     for a, b in zip(points, points[1:] + points[:1]))


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def point_in_triangle(p, a, b, c, eps=1e-6):
    d1, d2, d3 = cross(a, b, p), cross(b, c, p), cross(c, a, p)
    return (d1 >= -eps and d2 >= -eps and d3 >= -eps) or \
           (d1 <= eps and d2 <= eps and d3 <= eps)


def ear_clip(points):
    points = list(points)
    if signed_area(points) < 0:
        points.reverse()
    indices = list(range(len(points)))
    triangles = []
    while len(indices) > 3:
        clipped = False
        for i in range(len(indices)):
            ia = indices[i - 1]
            ib = indices[i]
            ic = indices[(i + 1) % len(indices)]
            a, b, c = points[ia], points[ib], points[ic]
            if cross(a, b, c) <= 1e-7:
                continue
            if any(point_in_triangle(points[j], a, b, c)
                   for j in indices if j not in (ia, ib, ic)):
                continue
            triangles.append((ia, ib, ic))
            del indices[i]
            clipped = True
            break
        if not clipped:
            raise ValueError("glyph contour could not be ear-clipped")
    triangles.append(tuple(indices))
    return points, triangles


# ── extruded mesh ────────────────────────────────────────────────────────────

def build_word_mesh(font_path: Path, word: str):
    font = TTFont(str(font_path))
    upm = font["head"].unitsPerEm
    scale = FONT_SIZE / upm
    hmtx = font["hmtx"]
    cmap = font.getBestCmap()

    glyphs = []
    cursor = 0.0
    for char in word:
        name, contours = glyph_contours(font, char)
        if len(contours) != 1:
            raise ValueError(f"{char!r} has {len(contours)} contours; this experiment needs single-contour glyphs")
        points = [(x * scale, y * scale) for x, y in contours[0]]
        points, triangles = ear_clip(points)
        advance = hmtx[name][0] * scale
        glyphs.append({"char": char, "points": points, "triangles": triangles,
                       "advance": advance})
        cursor += advance + TRACKING

    total_width = cursor - TRACKING
    xs = [x + sum(g["advance"] + TRACKING for g in glyphs[:i]) for i, g in enumerate(glyphs)
          for x, _ in g["points"]]
    ys = [y for g in glyphs for _, y in g["points"]]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    shift_x = -(minx + maxx) * 0.5
    shift_y = -(miny + maxy) * 0.5

    vertices = []
    indices = []
    z_front, z_back = -DEPTH * 0.5, DEPTH * 0.5

    def vertex(x, y, z, nx, ny, nz):
        vertices.append({
            "position": [round(x, 4), round(y, 4), round(z, 4)],
            "normal": [round(nx, 4), round(ny, 4), round(nz, 4)],
            "uv": [0.0, 0.0],
        })
        return len(vertices) - 1

    def tri(a, b, c):
        indices.extend([a, b, c])

    for i, glyph in enumerate(glyphs):
        offset = sum(g["advance"] + TRACKING for g in glyphs[:i])
        points = [(x + offset + shift_x, y + shift_y) for x, y in glyph["points"]]
        for ia, ib, ic in glyph["triangles"]:
            a, b, c = points[ia], points[ib], points[ic]
            # Back cap, +Z: CCW when seen from +Z.
            ba = vertex(a[0], a[1], z_back, 0, 0, 1)
            bb = vertex(b[0], b[1], z_back, 0, 0, 1)
            bc = vertex(c[0], c[1], z_back, 0, 0, 1)
            tri(ba, bb, bc)
            # Front cap, -Z: reverse winding so the visible face points at the camera.
            fa = vertex(a[0], a[1], z_front, 0, 0, -1)
            fb = vertex(b[0], b[1], z_front, 0, 0, -1)
            fc = vertex(c[0], c[1], z_front, 0, 0, -1)
            tri(fc, fb, fa)
        for a, b in zip(points, points[1:] + points[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length <= 1e-8:
                continue
            nx, ny = dy / length, -dx / length
            fa = vertex(a[0], a[1], z_front, nx, ny, 0)
            fb = vertex(b[0], b[1], z_front, nx, ny, 0)
            bb = vertex(b[0], b[1], z_back, nx, ny, 0)
            ba = vertex(a[0], a[1], z_back, nx, ny, 0)
            tri(fa, fb, bb)
            tri(fa, bb, ba)

    if len(vertices) > 250_000 or len(indices) > 750_000:
        raise ValueError("mesh exceeds inline-mesh budget")
    return {
        "vertices": vertices,
        "indices": indices,
        "material": {
            "diffuse": 0.65,
            "specular": 1.0,
            "shininess": 80.0,
            "metallic": 0.35,
            "roughness": 0.25,
            "base_color": hex_rgba(ACCENT),
        },
    }, total_width, maxy - miny, len(glyphs)


def camera():
    fov = 2.0 * math.degrees(math.atan((H / 2.0) / 1000.0))
    return {"type": "perspective", "position": [0, 0, -1000],
            "rotation_deg": [0, 0, 0], "fov_deg": round(fov, 4),
            "near": 1, "far": 10000, "zoom": 1}


def build_plan(mesh, word_width, word_height):
    accent_rgba = hex_rgba(ACCENT)
    layers = [
        color_layer("top_rule", accent_rgba, 1200, 1, 0, -380, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(0, 0.001), (42, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (8, 0.65), (FRAMES - 1, 0.65)])},
        ]),
        text_layer("kicker", KICKER, 960, 195, 900, 30,
                   "Inter-SemiBold.ttf", 20, ACCENT, 0, [fade(0, 20)]),
        {
            "id": "title_mesh",
            "type": "mesh",
            "size": [word_width + 160, word_height + 100],
            "position": [0, 160, 0],
            "scale": [1, 1, 1],
            "enable_3d": True,
            "screen_space": False,
            "loop": False,
            "opacity": 1.0,
            "start_frame": 0,
            "duration_frames": FRAMES,
            "color": [1.0, 1.0, 1.0, 1.0],
            "inline_mesh": mesh,
            "animation": {"tracks": [
                {"property": "position_z", "easing": "out_cubic",
                 "keyframes": kf([(0, -120.0), (50, 0.0), (FRAMES - 1, 0.0)])},
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(0, -24.0), (50, 0.0), (FRAMES - 1, 0.0)])},
                {"property": "rotation_x", "easing": "out_cubic",
                 "keyframes": kf([(0, 6.0), (50, 0.0), (FRAMES - 1, 2.0)])},
                {"property": "rotation_y", "easing": "out_cubic",
                 "keyframes": kf([(0, -26.0), (50, 0.0), (FRAMES - 1, 12.0)])},
                {"property": "scale", "easing": "out_cubic",
                 "keyframes": kf([(0, 0.96), (50, 1.0), (FRAMES - 1, 1.0)])},
                {"property": "opacity", "easing": "out_cubic",
                 "keyframes": kf([(0, 0.0), (20, 1.0), (FRAMES - 1, 1.0)])},
            ]},
        },
        color_layer("title_rule", accent_rgba, 220, 3, 0, -38, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(8, 0.001), (40, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (8, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        text_layer("caption", "EXTRUDED GLYPHS  ·  3D MESH", 960, 520, 800, 20,
                   "Inter-Medium.ttf", 12, MUTED, 14, [fade(14, 32)]),
        color_layer("progress", accent_rgba, 1600, 3, 0, 445, 0, [
            {"property": "scale_x", "easing": "linear",
             "keyframes": kf([(0, 0.001), (170, 1.0), (FRAMES - 1, 1.0)])},
        ]),
        text_layer("badge", "05 / 05   ·   TEXT 3D MESH", 1625, 195, 520, 24,
                   "Inter-Medium.ttf", 13, MUTED, 6, [fade(6, 24)]),
        text_layer("footer", "CHRONON TEMPLATE  ·  REAL EXTRUDED GLYPHS",
                   250, 1010, 620, 20, "Inter-Regular.ttf", 12, FOOTER),
    ]

    for i, point in enumerate(POINTS):
        start = 32 + i * 22
        layers.append(text_layer(
            f"bullet_{i}", f"—  {point}", 960, 580 + i * 120, 1400, 60,
            "Inter-Medium.ttf", 38, BODY, 0, [
                fade(start, start + 26),
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(start, 20.0), (start + 26, 0.0), (FRAMES - 1, 0.0)])},
            ]))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": "bullet_text3d_mesh_v1",
        "camera": camera(),
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "lighting_rig": {
            "key_direction": [0.35, -0.55, 0.75],
            "key_intensity": 1.55,
            "key_color": [1.0, 0.97, 0.92, 1.0],
            "ambient_intensity": 0.35,
            "ambient_color": [0.52, 0.60, 0.88, 1.0],
            "rim_enabled": True,
            "rim_intensity": 0.85,
            "rim_power": 3.0,
            "rim_color": [0.60, 0.78, 1.0, 1.0],
        },
        "layers": layers,
        "output": {"path": "05_text_3d_mesh.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    font_path = ROOT / FONT_FILE
    mesh, word_width, word_height, glyph_count = build_word_mesh(font_path, WORD)
    plan = build_plan(mesh, word_width, word_height)
    plan_path = OUT / "05_text_3d_mesh.plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    catalog = {
        "schema": "chronontemplate.bullet-families.v1",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "content": {"kicker": KICKER, "title": WORD, "points": POINTS},
        "mesh": {"font": FONT_FILE, "word": WORD, "glyphs": glyph_count,
                 "depth": DEPTH, "vertices": len(mesh["vertices"]),
                 "indices": len(mesh["indices"]),
                 "note": "single-contour glyphs; extruded caps and side walls"},
        "variants": [{
            "index": 5,
            "slug": "05_text_3d_mesh",
            "label": "TEXT 3D MESH",
            "family": "text_3d_v1",
            "motion_id": "text_3d_camera_push",
            "description": "Glifi Inter-Black estrusi, push di camera e yaw finale a 8°",
            "reveal": "mesh_extrusion",
            "title_font": "Inter-Black.ttf",
            "body_font": "Inter-Medium.ttf",
            "accent": ACCENT,
            "glow": {"shadow_color": ACCENT, "enabled": False,
                     "opacity": 0.0, "blur": 0},
            "plan": "plans/05_text_3d_mesh.plan.json",
            "mp4": "05_text_3d_mesh.mp4",
        }],
    }
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"{WORD}: {len(mesh['vertices'])} vertices, {len(mesh['indices']) // 3} triangles, "
          f"width={word_width:.1f}px height={word_height:.1f}px")
    print(f"wrote {plan_path}")
    print(f"wrote {OUT / 'showcase.json'}")


if __name__ == "__main__":
    main()
