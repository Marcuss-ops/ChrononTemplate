#!/usr/bin/env python3
"""Baked sprite-chain variant (renders on backends without path-stroke/follow).

Faithful to ChrononMotion's own map vocabulary (CHRONONMOTION.md):
'a route is authored as a chain of soft glow sprites walked at even arc
length ... lit in sequence so the shape draws itself.'
Positions come from the SAME arc-length sampler (geometry.sample_normalized)
that mirrors Chronon3D PathSampler, so dot_on_path holds by construction.
All layers are static ellipses + native glow -> software-backend safe.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vector_diagram.geometry import norm_to_px, sample_normalized

W, H, FPS, DUR = 1920, 1080, 30, 90
NORM = [[0.10, 0.82], [0.30, 0.49], [0.40, 0.42],
        [0.52, 0.22], [0.68, 0.06], [0.88, 0.78]]
ABS = norm_to_px(NORM, W, H)
HX, HY = W / 2, H / 2


def hex_rgba(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def dot_layer(lid, abs_pos, size, fill, glow_r, glow_i, glow_c, start, dur):
    return {"id": lid, "type": "shape", "size": [size, size],
            "position": [float(abs_pos[0] - HX), float(abs_pos[1] - HY)],
            "start_frame": int(start), "duration_frames": int(dur),
            "shape": {"type": "ellipse", "fill": hex_rgba(fill)},
            "effects": [{"type": "glow", "radius": float(glow_r),
                         "intensity": float(glow_i), "color": hex_rgba(glow_c)}]}


layers = [{"id": "background", "type": "color", "color": hex_rgba("#07090D"),
           "size": [W, H], "position": [0, 0],
           "start_frame": 0, "duration_frames": DUR}]

# trajectory chain: 48 sprites, staggered reveal 8->40 (draw-on without trim)
N_CHAIN = 48
for i in range(N_CHAIN):
    t = i / (N_CHAIN - 1)
    p = sample_normalized(ABS, t)["position"]
    start = 8 + int(round(t * (40 - 8)))
    layers.append(dot_layer(f"traj_{i:02d}", p, 7, "#FFFFFF", 8, 0.25,
                            "#FFFFFF", start, DUR - start))

# traveling head: 16 sequential windows 12->60 (moving dot without follow)
N_HEAD = 16
span = 60 - 12
for i in range(N_HEAD):
    t = i / (N_HEAD - 1)
    p = sample_normalized(ABS, t)["position"]
    start = 12 + int(round(t * span))
    dur = max(2, (span // N_HEAD) + 2)
    if i == N_HEAD - 1:
        dur = DUR - start  # head persists in the final held frame (spec 67-90)
    layers.append(dot_layer(f"head_{i:02d}", p, 12, "#FFDD20", 22, 0.5,
                            "#FFB800", start, min(dur, DUR - start)))

# peak marker from frame 48
peak = sample_normalized(ABS, 0.78)["position"]
layers.append(dot_layer("peak_marker", peak, 10, "#FF384F", 18, 0.45,
                        "#FF384F", 48, DUR - 48))

plan = {"schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "vector_documentary_diagram_baked",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": DUR},
        "layers": layers,
        "output": {"path": "vector_documentary_diagram_baked.mp4",
                   "format": "mp4"}}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out",
                   "vector_documentary_diagram.baked_v3.plan.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(plan, f, indent=1, sort_keys=True)
print(f"wrote {out} with {len(layers)} layers")
