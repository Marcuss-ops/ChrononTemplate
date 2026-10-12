#!/usr/bin/env python3
"""Translate the conceptual recipe into strict chronon.render-plan.v3 native JSON.

Fixes applied for the native decoder/schema:
 - schema v3 / version 3 (v2 has no shape type)
 - no root 'deterministic', no camera.static/subtle_zoom (use null camera)
 - layers carry start_frame/duration_frames, 2-elem position
 - trajectory path is RELATIVE to its layer position (world = pos + rel);
   follow_path path_commands stay ABSOLUTE canvas coords (world = pt - half).
   Both describe the same world line -> dot_on_path holds.
 - operator animations carry NO 'property' key (schema additionalProperties:false)
 - morph animation values are scalars; trim values are [start,end,offset] arrays
 - ellipse uses fill RGBA array; glow uses {type:glow,radius,intensity,color RGBA}
 - opacity tracks use scalar values
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vector_diagram.geometry import norm_to_px, to_path_commands

W, H, FPS, DUR = 1920, 1080, 30, 90
NORM = [[0.10, 0.82], [0.30, 0.49], [0.40, 0.42], [0.52, 0.22], [0.68, 0.06], [0.88, 0.78]]
ABS = norm_to_px(NORM, W, H)
HX, HY = W / 2, H / 2
REL = [[x - HX, y - HY] for x, y in ABS]


def hex_rgba(h):
    h = h.lstrip("#")
    if len(h) == 6:
        return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4, 6)]


def op_track(keyframes, easing="linear"):
    return {"easing": easing,
            "keyframes": [{"frame": int(f), "value": v} for f, v in keyframes]}


traj_rel_cmds = to_path_commands(REL)
dot_abs_cmds = to_path_commands(ABS)

# COORDINATE CONVENTION (measured on software backend):
#  - color layers: position = top-left px (bg must be [0,0])
#  - shape layers: position = offset from canvas center (px = pos + half);
#    shape.path points are relative to the layer origin.
#    With trajectory pos=[0,0] and rel=ABS-half -> px=ABS. Follow driver
#    returns ABS-half in the same center-offset space -> px=ABS. Coincident.
layers = [
    {"id": "background", "type": "color", "color": hex_rgba("#07090D"),
     "size": [W, H], "position": [0, 0],
     "start_frame": 0, "duration_frames": DUR},
    {"id": "trajectory", "type": "shape", "size": [W, H],
     "position": [0, 0], "start_frame": 0, "duration_frames": DUR,
     "shape": {"type": "path", "path": traj_rel_cmds,
               "stroke": {"color": "#FFFFFF", "width": 2},
               "operators": [{"kind": "trim",
                              "params": {"start": 0.0, "end": 1.0, "offset": 0.0,
                                         "animation": op_track(
                                             [(8, [0.0, 0.0, 0.0]), (40, [0.0, 1.0, 0.0])])}}]}},
    {"id": "traveling_dot", "type": "shape", "size": [12, 12],
     "position": [0, 0], "start_frame": 0, "duration_frames": DUR,
     "shape": {"type": "ellipse", "fill": hex_rgba("#FFDD20")},
     "follow_path": {"path_commands": dot_abs_cmds,
                     "progress": op_track([(12, 0.0), (60, 1.0)]),
                     "auto_orient": False, "clamp_end": True},
     "effects": [{"type": "glow", "radius": 22, "intensity": 0.5,
                  "color": hex_rgba("#FFB800")}],
     "animation": {"tracks": [
         {"property": "opacity", "easing": "linear",
          "keyframes": [{"frame": 0, "value": 0}, {"frame": 12, "value": 1}]}]}},
]

# peak at 78% along absolute path
from vector_diagram.geometry import sample_normalized
peak_abs = sample_normalized(ABS, 0.78)["position"]
layers.append(
    {"id": "peak_marker", "type": "shape", "size": [10, 10],
     "position": [float(peak_abs[0] - HX), float(peak_abs[1] - HY)],
     "start_frame": 0, "duration_frames": DUR,
     "shape": {"type": "ellipse", "fill": hex_rgba("#FF384F")},
     "effects": [{"type": "glow", "radius": 18, "intensity": 0.45,
                  "color": hex_rgba("#FF384F")}],
     "animation": {"tracks": [
         {"property": "opacity", "easing": "linear",
          "keyframes": [{"frame": 48, "value": 0}, {"frame": 67, "value": 1}]}]}})

plan = {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "vector_documentary_diagram",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": DUR},
        "layers": layers,
        "output": {"path": "vector_documentary_diagram.mp4", "format": "mp4"}}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                   "vector_documentary_diagram.native_v3.plan.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(plan, f, indent=2, sort_keys=True)
print(f"wrote {out}")
