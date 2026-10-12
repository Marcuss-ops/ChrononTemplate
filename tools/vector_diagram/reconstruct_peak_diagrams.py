#!/usr/bin/env python3
"""Build faithful documentary peak-diagram native RenderPlans (no alternate renderer).

Phase A/B static plans are the visual gate before animated plans are emitted.
The path remains one native Chronon3D shape.path with one StrokeStyle; marker
positions are authored independently on the ascending segment / at the peak.
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out" / "peak_reconstruction"
W, H, FPS = 1920, 1080, 30

# User-authored normalized reference reconstruction. Compact ~40% width.
B_NORM = [(0.29, .73), (.40, .52), (.44, .45), (.47, .45),
          (.53, .34), (.55, .28), (.59, .21), (.69, .62)]
A_NORM = [(.34, .72), (.45, .43), (.51, .27), (.65, .71)]


def rgba(hexstr):
    s = hexstr.lstrip("#")
    return [int(s[i:i+2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def screen_xy(p):
    """RenderPlan's screen-space coordinates relative to the canvas center."""
    return [round(p[0] * W - W / 2, 3), round(p[1] * H - H / 2, 3)]


def commands(points):
    xy = [screen_xy(p) for p in points]
    return ([{"type": "move_to", "point": xy[0]}] +
            [{"type": "line_to", "point": p} for p in xy[1:]])


def glow_layer(id_, pos, diameter, core, halo, radius, intensity, start=0, duration=150,
               opacity=1.0, blend="normal"):
    return {
        "id": id_, "type": "shape", "size": [diameter, diameter],
        "position": screen_xy(pos), "start_frame": start, "duration_frames": duration,
        "opacity": opacity, "blend_mode": blend,
        "shape": {"type": "ellipse", "fill": rgba(core)},
        "effects": [{"type": "glow", "radius": radius, "intensity": intensity,
                     "color": rgba(halo)}],
    }


def background(texture=False, duration=150):
    layers = [{"id": "black_background", "type": "color", "color": rgba("#030304"),
              "size": [W, H], "position": [0, 0],
              "start_frame": 0, "duration_frames": duration}]
    if texture:
        # sparse, low-contrast marks only; these remain below the diagram.
        for i, (x, y, size, alpha) in enumerate([
            (.16,.22,1.5,.16),(.23,.78,1.2,.12),(.74,.17,1.4,.14),
            (.82,.69,1.3,.13),(.72,.84,1.1,.10),(.19,.44,1.0,.10),
            (.88,.35,1.2,.10),(.11,.61,1.1,.08)]):
            layers.append({"id":f"grain_dot_{i}","type":"shape","size":[size*2,size*2],
                "position":screen_xy((x,y)),"start_frame":0,"duration_frames":150,
                "opacity":alpha,"shape":{"type":"ellipse","fill":[.62,.66,.72,1]}})
        for i, y in enumerate((.28,.50,.76)):
            layers.append({"id":f"ambient_scanline_{i}","type":"shape",
                "size":[W*.78,1],"position":[0,round((y-.5)*H,3)],
                "start_frame":0,"duration_frames":150,"opacity":.045,
                "shape":{"type":"rect","fill":[.52,.57,.64,1]}})
    return layers


def base_plan(job, duration=150):
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":job,
        "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,
                  "duration_frames":duration},
        "layers":[],"output":{"path":f"{job}.mp4","format":"mp4"}}


def path_layer(points, id_="diagram_path", width=2.5, start=0, duration=150,
               trim=None):
    shape={"type":"path","path":commands(points),
           # Opaque fill matching the canvas keeps path stroke alpha enabled
           # without exposing the renderer's implicit close-fill on this open line.
           "fill":rgba("#030304"),
           "stroke":{"color":"#E8EBF0","width":width,"cap":"round","join":"round"}}
    if trim is not None:
        f0,f1=trim
        shape["operators"]=[{"kind":"trim","params":{"start":0,"end":1,"offset":0,
            "animation":{"easing":"linear","keyframes":[
                {"frame":f0,"value":[0,0,0]},{"frame":f1,"value":[0,1,0]}]}}}]
    # For Path, layer.color is the stroke modulation passed as node.color by
    # render_plan_compiler_shape; omit/transparent layer.color suppresses it.
    # Use an opaque layer color as the stroke-alpha multiplier; omit shape.fill
    # so the open path is never rasterized as a filled polygon.
    return {"id":id_,"type":"shape","size":[W,H],"position":[0,0],
            "color":[1,1,1,1],"screen_space":True,
            "start_frame":start,"duration_frames":duration,"shape":shape}


def static_b():
    plan=base_plan("annotated_peak_static_b",1)
    plan["layers"]=background(False,1)
    plan["layers"].append(path_layer(B_NORM,duration=1))
    # yellow core and broad orange halo. Glow is attached ONLY to this marker.
    plan["layers"].append(glow_layer("yellow_marker",(.40,.43),48,"#FFE52B",
        "#FF9A18",72,.85,duration=1))
    # Separate visible red indicators, both static in Phase B.
    plan["layers"].append(glow_layer("red_rising_marker",(.44,.45),28,"#E52335",
        "#F32035",34,.28,duration=1,opacity=.66))
    plan["layers"].append(glow_layer("red_peak_marker",(.59,.21),34,"#F02B3C",
        "#FF2838",42,.38,duration=1,opacity=.78))
    return plan


def minimal_a(duration=150, animated=False, texture=False):
    plan=base_plan("minimal_peak_diagram_a",duration)
    plan["layers"]=background(texture,duration)
    plan["layers"].append(path_layer(A_NORM,duration=duration,
        trim=(10,45) if animated else None))
    # Marker stays near lower rising branch, no full-path FollowPath.
    marker=glow_layer("yellow_marker",(.405,.565),48,"#FFE52B","#FF9A18",
        72,.82,start=0 if not animated else 0,duration=duration)
    if animated:
        marker["start_frame"]=0; marker["duration_frames"]=duration
        # opacity animation is known broken in this software backend, so use
        # an explicit visibility window instead of a discarded track.
        marker["start_frame"]=0; marker["duration_frames"]=duration
    plan["layers"].append(marker)
    return plan


def annotated_b(duration=150, animated=False, texture=False):
    plan=base_plan("annotated_peak_diagram_b",duration)
    plan["layers"]=background(texture,duration)
    plan["layers"].append(path_layer(B_NORM,duration=duration,
        trim=(10,45) if animated else None))
    # The yellow sphere is anchored around 40%,43%; it does not traverse the path.
    plan["layers"].append(glow_layer("yellow_marker",(.40,.43),48,"#FFE52B",
        "#FF9A18",72,.85,duration=duration))
    rise=glow_layer("red_rising_marker",(.44,.45),28,"#E52335","#F32035",
        34,.28,start=0 if not animated else 40,
        duration=duration if not animated else max(1,duration-40),opacity=.66)
    peak=glow_layer("red_peak_marker",(.59,.21),34,"#F02B3C","#FF2838",
        42,.38,start=0 if not animated else 60,
        duration=duration if not animated else max(1,duration-60),opacity=.78)
    plan["layers"] += [rise,peak]
    return plan


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plans={
        "phase_a_static_a.plan.json":minimal_a(1,False,False),
        "phase_a_static_b.plan.json":static_b(),
        "minimal_a_150f.plan.json":minimal_a(150,True,False),
        "annotated_b_150f.plan.json":annotated_b(150,True,False),
        "annotated_b_atmosphere_150f.plan.json":annotated_b(150,True,True),
        "minimal_a_static_150f.plan.json":minimal_a(150,False,False),
        "annotated_b_static_150f.plan.json":annotated_b(150,False,False),
    }
    for name,plan in plans.items():
        (OUT/name).write_text(json.dumps(plan,indent=2)+"\n")
        print(OUT/name)

if __name__=="__main__": main()
