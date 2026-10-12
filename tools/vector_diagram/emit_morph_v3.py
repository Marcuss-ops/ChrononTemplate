#!/usr/bin/env python3
"""Native v3 morph fixture: same-topology quad -> wide quad (frames 0-45/60)."""
import json, os

SRC = [[-100, -100], [100, -100], [100, 100], [-100, 100]]
DST = [[-150, -70], [150, -70], [150, 70], [-150, 70]]


def cmds(pts):
    out = [{"type": "move_to", "point": [float(pts[0][0]), float(pts[0][1])]}]
    out += [{"type": "line_to", "point": [float(x), float(y)]} for x, y in pts[1:]]
    out.append({"type": "close"})
    return out


plan = {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "vector_morph_test",
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
                   "duration_frames": 60},
        "layers": [
            {"id": "background", "type": "color",
             "color": [0.027, 0.035, 0.05, 1.0],
             "size": [1920, 1080], "position": [0, 0],
             "start_frame": 0, "duration_frames": 60},
            {"id": "morph_shape", "type": "shape", "size": [1920, 1080],
             "position": [0, 0], "start_frame": 0, "duration_frames": 60,
             "shape": {"type": "path", "path": cmds(SRC),
                       "stroke": {"color": "#FFFFFF", "width": 3},
                       "operators": [{"kind": "morph",
                                      "params": {"target": cmds(DST),
                                                 "progress": 0.0,
                                                 "animation": {
                                                     "easing": "linear",
                                                     "keyframes": [
                                                         {"frame": 0,
                                                          "value": 0.0},
                                                         {"frame": 45,
                                                          "value": 1.0}]}}}]}}
        ],
        "output": {"path": "vector_morph_test.mp4", "format": "mp4"}}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                   "vector_morph_test.native_v3.plan.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(plan, f, indent=1, sort_keys=True)
print(f"wrote {out}")
