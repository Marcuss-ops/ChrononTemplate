#!/usr/bin/env python3
"""Emit vector_documentary_diagram RenderPlan + morph + footage-composition fixtures."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vector_diagram.composers import (
    build_vector_documentary_diagram, shape_morph_animation, animated_diagram,
    vector_draw_on, follow_path, glow_marker, appear_opacity)
from vector_diagram.geometry import norm_to_px

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# 1) main 90f recipe
plan = build_vector_documentary_diagram()
shared = plan.pop("_shared_geometry")
with open(os.path.join(OUT, "vector_documentary_diagram.plan.json"), "w") as f:
    json.dump(plan, f, indent=2, sort_keys=True)
with open(os.path.join(OUT, "shared_geometry_proof.json"), "w") as f:
    json.dump(shared, f, indent=2, sort_keys=True)

# 2) morph fixture: circle-ish square -> oval (same topology: move+3 line_to+close)
W, H = 1920, 1080
src = [[860, 440], [1060, 440], [1060, 640], [860, 640]]
dst = [[810, 470], [1110, 470], [1110, 610], [810, 610]]
src_px = src
dst_px = dst
morph_layer = shape_morph_animation("morph_shape", src_px, dst_px, morph_frames=(0, 45))
morph_plan = animated_diagram([morph_layer], duration_frames=60, job_id="vector_morph_test")
with open(os.path.join(OUT, "vector_morph_test.plan.json"), "w") as f:
    json.dump(morph_plan, f, indent=2, sort_keys=True)

# 3) vector + footage composition: diagram layers + video source layer (compositing check)
footage = {
    "id": "footage_src", "type": "video", "source": "editorial_plate.mp4",
    "position": [960, 540, 0], "size": [1920, 1080],
    "start_frame": 60, "duration_frames": 30,
}
diagram_layers = plan["layers"]  # background + 3 vector layers
comp_layers = diagram_layers + [footage]
import copy
comp = {"schema": "chronon.render-plan.v2", "version": 2,
        "job_id": "vector_plus_footage", "deterministic": True,
        "canvas": {"width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
                   "duration_frames": 90},
        "camera": {"type": "perspective", "static": True},
        "layers": copy.deepcopy(comp_layers),
        "output": {"path": "vector_plus_footage.mp4", "format": "mp4"}}
with open(os.path.join(OUT, "vector_plus_footage.plan.json"), "w") as f:
    json.dump(comp, f, indent=2, sort_keys=True)

print(f"wrote 3 plans to {OUT}")
