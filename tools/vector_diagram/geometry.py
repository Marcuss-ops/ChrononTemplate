"""Arc-length polyline sampler — Python mirror of Chronon3D PathSampler.

Contract mirrored from Chronon3d/include/chronon3d/text/path_sampler.hpp:
  sample_normalized(t) -> position, tangent, normal
Normal = 90deg clockwise of tangent: (tangent.y, -tangent.x).
"""
from __future__ import annotations
import math


def polyline_lengths(pts):
    segs = []
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append(L)
        total += L
    return segs, total


def sample_normalized(pts, t):
    """Sample polyline at normalized t in [0,1]. Returns dict with position/tangent/normal."""
    t = max(0.0, min(1.0, float(t)))
    segs, total = polyline_lengths(pts)
    if total <= 0:
        p = pts[0]
        return {"position": list(p), "tangent": [1.0, 0.0], "normal": [0.0, -1.0],
                "distance": 0.0, "normalized_t": 0.0}
    target = t * total
    acc = 0.0
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if acc + L >= target or L == 0:
            f = 0.0 if L == 0 else (target - acc) / L
            f = max(0.0, min(1.0, f))
            px = a[0] + (b[0] - a[0]) * f
            py = a[1] + (b[1] - a[1]) * f
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy) or 1.0
            tx, ty = dx / n, dy / n
            nx, ny = ty, -tx
            return {"position": [px, py], "tangent": [tx, ty], "normal": [nx, ny],
                    "distance": target, "normalized_t": t}
        acc += L
    # t == 1 exactly
    a, b = pts[-2], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    tx, ty = dx / n, dy / n
    return {"position": list(pts[-1]), "tangent": [tx, ty], "normal": [ty, -tx],
            "distance": total, "normalized_t": 1.0}


def to_path_commands(pts_px):
    """Polyline points (px) -> RenderPlan ShapePathCommandPlan list."""
    cmds = [{"type": "move_to", "point": [float(pts_px[0][0]), float(pts_px[0][1])]}]
    for p in pts_px[1:]:
        cmds.append({"type": "line_to", "point": [float(p[0]), float(p[1])]})
    return cmds


def norm_to_px(norm_pts, w, h):
    return [[x * w, y * h] for x, y in norm_pts]
