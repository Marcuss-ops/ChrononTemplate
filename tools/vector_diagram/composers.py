"""High-level vector composers — thin wrappers over native Chronon primitives.

Each composer emits ONLY existing RenderPlan vocabulary:
  VectorDrawOn       -> shape.path + operators[trim + trim_animation]
  FollowPath         -> layer.follow_path {path_commands, progress} (same geometry object)
  GlowMarker         -> shape.ellipse + effects[glow] + opacity animation
  ShapeMorphAnimation-> shape.path + operators[morph + morph_animation] (matching topology)
  AnimatedDiagram    -> timeline composition of the above (RenderPlan v2 dict)

No new renderer is introduced. This mirrors the Lottie/SVG lowering rule:
Bodymovin/SVG stay compile-time inputs; lowered tracks use LayerPlan +
AnimationTrackPlan + existing sampler/compiler.
"""
from __future__ import annotations
import copy

from .geometry import to_path_commands, norm_to_px


def track(prop, keys, easing="linear"):
    """keys: list of (frame, value_list)."""
    return {
        "property": prop,
        "easing": easing,
        "keyframes": [{"frame": int(f), "value": list(v)} for f, v in keys],
    }


def vector_draw_on(layer_id, pts_px, stroke="#FFFFFF", stroke_width=2,
                   draw_frames=(8, 40), size=(1920, 1080)):
    """Line that draws itself via native Trim operator (shape.operators)."""
    f0, f1 = draw_frames
    assert 0 <= f0 < f1, "draw_frames must be ordered"
    path = to_path_commands(pts_px)
    return {
        "id": layer_id,
        "type": "shape",
        "size": [float(size[0]), float(size[1])],
        "position": [float(size[0]) / 2, float(size[1]) / 2, 0],
        "shape": {
            "type": "path",
            "path": path,
            "stroke": {"color": stroke, "width": float(stroke_width)},
            "operators": [
                {
                    "kind": "trim",
                    "params": {
                        "start": 0.0, "end": 1.0, "offset": 0.0,
                        "animation": track("trim", [(f0, [0.0, 0.0, 0.0]), (f1, [0.0, 1.0, 0.0])]),
                    },
                }
            ],
        },
    }


def follow_path(layer_id, pts_px, progress_frames=(12, 60), radius=6,
                color="#FFDD20", auto_orient=False):
    """Dot/icon that follows the SAME path_commands object (dot_on_path)."""
    f0, f1 = progress_frames
    assert 0 <= f0 < f1
    path = to_path_commands(pts_px)
    return {
        "id": layer_id,
        "type": "shape",
        "size": [float(radius * 2), float(radius * 2)],
        "position": [float(pts_px[0][0]), float(pts_px[0][1]), 0],
        "shape": {"type": "ellipse",
                  "fill": _hex_to_rgba(color)},
        "follow_path": {
            "path_commands": path,
            "progress": track("follow_path_progress", [(f0, [0.0]), (f1, [1.0])]),
            "auto_orient": bool(auto_orient),
            "clamp_end": True,
        },
    }


def glow_marker(layer_dict, radius_px=22, intensity=0.5, color="#FFB800",
                pulse_frames=None):
    """Attach native Glow effect; optionally pulse intensity via effect track."""
    out = copy.deepcopy(layer_dict)
    r, g, b, a = _hex_to_rgba(color)
    out.setdefault("effects", []).append(
        {"type": "glow", "radius": float(radius_px),
         "intensity": float(intensity), "color": [r, g, b, a]})
    if pulse_frames:
        f0, f1, f2 = pulse_frames
        out.setdefault("effect_tracks", []).append(
            track("glow_intensity",
                  [(f0, [float(intensity) * 0.7]), (f1, [float(intensity)]),
                   (f2, [float(intensity) * 0.7])]))
    return out


def appear_opacity(layer_dict, appear_frames=(0, 12)):
    f0, f1 = appear_frames
    out = copy.deepcopy(layer_dict)
    out.setdefault("animation", {"tracks": []})
    if isinstance(out["animation"], dict) and "tracks" in out["animation"]:
        out["animation"]["tracks"].append(
            track("opacity", [(f0, [0.0]), (f1, [1.0])]))
    return out


def shape_morph_animation(layer_id, src_pts_px, dst_pts_px,
                          morph_frames=(0, 30), stroke="#FFFFFF", stroke_width=2,
                          size=(1920, 1080)):
    """Morph between two SAME-TOPOLOGY polylines via native Morph operator."""
    src = to_path_commands(src_pts_px)
    dst = to_path_commands(dst_pts_px)
    if len(src) != len(dst):
        raise ValueError(f"morph topology mismatch: {len(src)} vs {len(dst)} cmds "
                         "(matching vertex/tangent/closure required, fail closed)")
    for s, d in zip(src, dst):
        if s["type"] != d["type"]:
            raise ValueError(f"morph topology mismatch: {s['type']} vs {d['type']}")
    f0, f1 = morph_frames
    return {
        "id": layer_id,
        "type": "shape",
        "size": [float(size[0]), float(size[1])],
        "position": [float(size[0]) / 2, float(size[1]) / 2, 0],
        "shape": {
            "type": "path",
            "path": src,
            "stroke": {"color": stroke, "width": float(stroke_width)},
            "operators": [
                {
                    "kind": "morph",
                    "params": {
                        "target": dst,
                        "progress": 0.0,
                        "animation": track("morph_progress", [(f0, [0.0]), (f1, [1.0])]),
                    },
                }
            ],
        },
    }


def animated_diagram(layers, width=1920, height=1080, fps=30,
                     duration_frames=90, job_id="vector_documentary_diagram",
                     background="#07090D"):
    """Compose layers into a deterministic RenderPlan v2 dict."""
    bg = _hex_to_rgba(background)
    plan_layers = [{
        "id": "background",
        "type": "color",
        "color": list(bg),
        "size": [float(width), float(height)],
        "position": [float(width) / 2, float(height) / 2, 0],
    }]
    plan_layers.extend(copy.deepcopy(layers))
    return {
        "schema": "chronon.render-plan.v2",
        "version": 2,
        "job_id": job_id,
        "deterministic": True,
        "canvas": {"width": width, "height": height,
                   "fps_num": fps, "fps_den": 1,
                   "duration_frames": duration_frames},
        "camera": {"type": "perspective", "static": True, "subtle_zoom": 1.02},
        "layers": plan_layers,
        "output": {"path": f"{job_id}.mp4", "format": "mp4"},
    }


def build_vector_documentary_diagram(width=1920, height=1080):
    """Concrete 90f recipe from the spec (trajectory + traveling_dot + peak_marker)."""
    norm = [[0.10, 0.82], [0.30, 0.49], [0.40, 0.42],
            [0.52, 0.22], [0.68, 0.06], [0.88, 0.78]]
    pts = norm_to_px(norm, width, height)
    traj = vector_draw_on("trajectory", pts, stroke="#FFFFFF",
                          stroke_width=2, draw_frames=(8, 40),
                          size=(width, height))
    dot = follow_path("traveling_dot", pts, progress_frames=(12, 60),
                      radius=6, color="#FFDD20")
    dot = glow_marker(dot, radius_px=22, intensity=0.5, color="#FFB800",
                      pulse_frames=(67, 78, 90))
    dot = appear_opacity(dot, appear_frames=(0, 12))
    # peak marker sits at 78% of the same path
    from .geometry import sample_normalized
    peak = sample_normalized(pts, 0.78)["position"]
    peak_layer = {
        "id": "peak_marker",
        "type": "shape",
        "size": [10.0, 10.0],
        "position": [float(peak[0]), float(peak[1]), 0],
        "shape": {"type": "ellipse",
                  "fill": _hex_to_rgba("#FF384F")},
    }
    peak_layer = glow_marker(peak_layer, radius_px=18, intensity=0.45,
                             color="#FF384F")
    peak_layer = appear_opacity(peak_layer, appear_frames=(48, 67))
    plan = animated_diagram([traj, dot, peak_layer], width=width,
                            height=height, fps=30, duration_frames=90,
                            job_id="vector_documentary_diagram")
    # shared-geometry proof artefact
    plan["_shared_geometry"] = {
        "note": "trajectory.shape.path == traveling_dot.follow_path.path_commands (same arc-length source)",
        "trajectory_path": traj["shape"]["path"],
        "dot_path": dot["follow_path"]["path_commands"],
    }
    return plan


def _hex_to_rgba(h):
    h = h.lstrip("#")
    if len(h) == 6:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        return [r, g, b, 1.0]
    if len(h) == 8:
        return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4, 6)]
    raise ValueError(f"bad hex color {h}")
