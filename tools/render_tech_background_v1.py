#!/usr/bin/env python3
"""Author six deterministic keynote/AI background recipes and their canaries."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

TEMPLATE = Path(__file__).resolve().parents[1]
WORKSPACE = TEMPLATE.parent
CHRONON = WORKSPACE / "Chronon3d"
FAMILY_FILE = TEMPLATE / "catalog/tech_background_v1.json"
OUT = TEMPLATE / "out/tech_background_v1"
CLI_CANDIDATES = (
    CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    CHRONON / "build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)
W, H, FPS, SEGMENT = 960, 540, 30, 90


def track(prop: str, values: list[tuple[int, Any]], easing="in_out_sine") -> dict:
    unique = {int(frame): value for frame, value in values}
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": unique[f]} for f in sorted(unique)]}


def layer(id_: str, kind: str, start: int, duration: int, **fields) -> dict:
    return {"id":id_,"type":kind,"start_frame":start,"duration_frames":duration,**fields}


def rgba(color: list[float], alpha=1.0) -> list[float]:
    return [*color[:3], alpha]


def base(duration: int, job_id: str, title=True) -> list[dict]:
    layers = [layer("tech-dark-backplate", "color", 0, duration,
                    color=[.004,.008,.025,1], size=[W,H], position=[W/2,H/2], screen_space=True)]
    if title:
        layers += [
            layer("tech-title-line-1","text",0,duration,text="THE FUTURE",size=[660,88],position=[W/2,H/2-36],
                  style={"font":"Chronon3d/assets/fonts/Inter-Bold.ttf","font_size":58,"fill":"#F2F7FF",
                         "min_font_size":48,"max_font_size":58,"fit_mode":"shrink_only"},
                  animation={"tracks":[track("opacity",[(0,0),(15,1),(duration-15,1),(duration-1,0)])]}),
            layer("tech-title-line-2","text",0,duration,text="IS ALREADY HERE",size=[680,55],position=[W/2,H/2+34],
                  style={"font":"Chronon3d/assets/fonts/Inter-Regular.ttf","font_size":27,"fill":"#AFC8DE",
                         "min_font_size":22,"max_font_size":27,"fit_mode":"shrink_only"},
                  animation={"tracks":[track("opacity",[(0,0),(22,1),(duration-15,1),(duration-1,0)])]}),
        ]
    return layers


def _fade(duration: int) -> list[dict]:
    return [track("opacity",[(0,0),(10,1),(duration-10,1),(duration-1,0)])]


def field_layer(id_: str, start: int, duration: int, seed: int, generator: str,
                ramp: list[dict], *, frequency=1.0, operators=None,
                scale=2, opacity=.7, drift=(0.0,0.0)) -> dict:
    shape={"type":"rect","fill":[.01,.02,.06,1],
           "field":{"generator":generator,"seed":seed,"frequency":frequency,"octaves":5,
                    "operators":operators or []},
           "field_render_scale":scale,
           "field_drift":[float(drift[0]),float(drift[1])],
           "field_ramp":{"type":"linear","start":[0,.5],"end":[1,.5],"color_stops":ramp}}
    return layer(id_,"shape",start,duration,size=[W,H],position=[W/2,H/2],shape=shape,
                 blend_mode="screen",opacity=opacity,animation={"tracks":_fade(duration)})


def stroke_path(id_: str, start: int, duration: int, commands: list[dict], color: str,
                width: float, *, blur=0.0, bloom=0.0, opacity=.85,
                position=(W/2,H/2), rotation=(0.0,0.0), offset=(0.0,0.0)) -> dict:
    effects=[]
    if blur>0: effects.append({"type":"gaussian_blur","radius":blur})
    if bloom>0: effects.append({"type":"bloom","threshold":.18,"radius":min(256,blur or width),"intensity":bloom})
    return layer(id_,"shape",start,duration,size=[W,H],position=list(position),
                 shape={"type":"path","path":commands,"stroke":{"color":color,"width":width}},
                 blend_mode="screen",opacity=opacity,effects=effects,
                 animation={"tracks":[*_fade(duration),
                     track("rotation_z",[(0,rotation[0]),(duration-1,rotation[1])]),
                     track("position_y",[(0,offset[0]),(duration-1,offset[1])])]})


def line_commands(y: float, x0=-W*.7, x1=W*.7) -> list[dict]:
    return [{"type":"move_to","point":[x0,y]},
            {"type":"cubic_to","control1":[-W*.24,y-22],"control2":[W*.22,y+24],"point":[x1,y+4]}]


def arc_layer(id_: str, start: int, duration: int, color: str,
              *, size=(1360,1120), position=(W*.53,H*1.06), width=42,
              start_deg=202, sweep=132, blur=48, opacity=.9) -> dict:
    return layer(id_,"shape",start,duration,size=list(size),position=list(position),
                 shape={"type":"arc","start_degrees":start_deg,"sweep_degrees":sweep,
                        "segments":96,"stroke":{"color":color,"width":width}},
                 blend_mode="screen",opacity=opacity,
                 effects=[{"type":"gaussian_blur","radius":blur},
                          {"type":"bloom","threshold":.12,"radius":min(220,blur*2),"intensity":.5}],
                 animation={"tracks":[*_fade(duration),
                     track("position_x",[(0,0),(duration-1,-45)]),
                     track("position_y",[(0,0),(duration-1,-20)]),
                     track("rotation_z",[(0,-8),(duration-1,4)]),
                     track("scale",[(0,.98),(duration-1,1.08)])]})


def scene_layers(recipe: dict, start: int, duration: int, index: int) -> list[dict]:
    ident=recipe["id"]
    seed=int(recipe["seed"])
    palette=json.loads(FAMILY_FILE.read_text())["style_tokens"]
    cyan="#28D9F5"; aqua="#24E9C0"; magenta="#F625A8"; green="#39F59A"; red="#FF344E"
    result=[]
    if ident=="tech_blue_horizon":
        ramp=[{"position":0,"color":[.008,.012,.055,1]},
              {"position":.42,"color":[.025,.12,.35,1]},
              {"position":.68,"color":[.025,.35,.55,1]},
              {"position":1,"color":[.14,.76,.92,1]}]
        result.append(field_layer(f"{ident}-gradient",start,duration,seed,"linear",ramp,
                                  frequency=1,scale=2,opacity=.78,drift=(0,.008)))
        result.append(stroke_path(f"{ident}-outer-beam",start,duration,line_commands(22),cyan,142,
                                  blur=72,bloom=.56,opacity=.68,rotation=(-3,2),offset=(0,18)))
        result.append(stroke_path(f"{ident}-beam-core",start,duration,line_commands(22),"#82F6FF",8,
                                  blur=8,bloom=.35,opacity=.95,rotation=(-3,2),offset=(0,18)))
    elif ident=="tech_aqua_horizon":
        ramp=[{"position":0,"color":[.004,.018,.018,1]},
              {"position":.45,"color":[.008,.09,.1,1]},
              {"position":1,"color":[.015,.36,.32,1]}]
        result.append(field_layer(f"{ident}-field",start,duration,seed,"linear",ramp,
                                  frequency=1,scale=2,opacity=.76,drift=(0,-.004)))
        result.append(stroke_path(f"{ident}-wide-band",start,duration,line_commands(0),aqua,112,
                                  blur=64,bloom=.6,opacity=.76,offset=(-8,12)))
        result.append(stroke_path(f"{ident}-glow-core",start,duration,line_commands(0),"#B6FFE9",7,
                                  blur=5,bloom=.25,opacity=.92,offset=(-8,12)))
    elif ident=="tech_magenta_cone":
        cone=[{"type":"move_to","point":[-510,-450]},
              {"type":"line_to","point":[510,-450]},
              {"type":"line_to","point":[65,280]},
              {"type":"cubic_to","control1":[35,320],"control2":[-35,320],"point":[-65,280]},
              {"type":"close"}]
        result.append(layer(f"{ident}-cone", "shape",start,duration,size=[W,H],position=[W/2,H/2],
                            shape={"type":"path","path":cone,"fill":[.58,.025,.39,.29]},
                            blend_mode="screen",opacity=.9,effects=[{"type":"gaussian_blur","radius":82},
                                  {"type":"bloom","threshold":.08,"radius":154,"intensity":.58}],
                            animation={"tracks":[*_fade(duration),
                                track("scale",[(0,.92),(duration-1,1.08)]),
                                track("rotation_z",[(0,-2),(duration-1,3)])]}))
        result.append(layer(f"{ident}-source", "shape",start,duration,size=[220,150],position=[W/2,H*.93],
                            shape={"type":"ellipse","fill":[.96,.14,.68,.72]},blend_mode="screen",opacity=.82,
                            effects=[{"type":"gaussian_blur","radius":64},
                                     {"type":"light_rays","origin":[.5,.99],"length":880,
                                      "density":.5,"color":palette["magenta"],"decay":.9}]))
        result.append(stroke_path(f"{ident}-axis",start,duration,line_commands(8,-90,90),"#FF6EC9",5,
                                  blur=10,bloom=.35,opacity=.62,position=(W/2,H*.83)))
    elif ident in {"tech_arc_green","tech_arc_red"}:
        color=green if ident.endswith("green") else red
        result.append(arc_layer(f"{ident}-halo",start,duration,color,width=92,blur=76,opacity=.52,
                                position=(W*.52,H*1.08),size=(1480,1240)))
        result.append(arc_layer(f"{ident}-core",start,duration,"#C2FFE4" if ident.endswith("green") else "#FFB2C0",
                                width=13,blur=7,opacity=.98,position=(W*.52,H*1.08),size=(1480,1240)))
    elif ident=="tech_duotone_blob":
        blobs=(("blue",(W*.34,H*.52),(660,640),[.04,.24,.98,.68]),
               ("violet",(W*.57,H*.47),(700,690),[.43,.11,.92,.60]),
               ("pink",(W*.73,H*.53),(620,650),[.96,.06,.48,.58]))
        for name,position,size,color in blobs:
            result.append(layer(f"{ident}-{name}","shape",start,duration,size=list(size),position=list(position),
                                shape={"type":"ellipse","fill":color},blend_mode="screen",opacity=.82,
                                effects=[{"type":"gaussian_blur","radius":190},
                                         {"type":"bloom","threshold":.1,"radius":170,"intensity":.42}],
                                animation={"tracks":[*_fade(duration),
                                    track("position_x",[(0,0),(duration-1,16 if name!="pink" else -14)]),
                                    track("position_y",[(0,0),(duration-1,-8 if name=="violet" else 8)])]}))
    else:
        raise ValueError(f"unknown tech background recipe: {ident}")
    return result


def build_gallery(family=None) -> dict:
    family=family or json.loads(FAMILY_FILE.read_text())
    recipes=family["recipes"]
    total=SEGMENT*len(recipes)
    layers=base(total,"canary_tech_background_v1")
    for index,recipe in enumerate(recipes):
        start=index*SEGMENT
        layers.extend(scene_layers(recipe,start,SEGMENT,index))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"canary_tech_background_v1",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":total},
            "layers":layers,"output":{"path":"canary_tech_background_v1.mp4","format":"mp4","codec":"h264"}}


def build_torture(family=None) -> dict:
    family=family or json.loads(FAMILY_FILE.read_text())
    recipes=family["recipes"]
    total=15*FPS
    layers=base(total,"canary_tech_background_torture_v1")
    for index,recipe in enumerate(recipes):
        start=index*69
        duration=total-start
        # Each later scene overlaps the previous one; opacity fades cross-dissolve
        # independent universal layers while the shared headline stays fixed.
        duration=min(duration,105)
        layers.extend(scene_layers(recipe,start,duration,index))
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"canary_tech_background_torture_v1",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":total},
            "layers":layers,"output":{"path":"canary_tech_background_torture_v1.mp4","format":"mp4","codec":"h264"}}


def build_plans(family=None) -> dict[str,dict]:
    family=family or json.loads(FAMILY_FILE.read_text())
    return {"canary_tech_background_v1":build_gallery(family),
            "canary_tech_background_torture_v1":build_torture(family)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--plans",action="store_true",help="write gallery and torture plans")
    group.add_argument("--validate",action="store_true",help="write and validate plans")
    group.add_argument("--render",action="store_true",help="write, validate and render plans")
    parser.add_argument("--cli",type=Path,help="chronon3d_cli path")
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    plans=build_plans()
    for job_id,plan in plans.items():
        path=OUT/f"{job_id}.plan.json"
        path.write_text(json.dumps(plan,indent=2)+"\n")
        print(f"wrote {path}")
    if args.validate or args.render:
        cli=args.cli or next((p for p in CLI_CANDIDATES if p.is_file()),None)
        if cli is None: parser.error("chronon3d_cli not found; pass --cli")
        for job_id in plans:
            path=OUT/f"{job_id}.plan.json"
            subprocess.run([str(cli),"validate","--plan",str(path),"--assets-root",str(WORKSPACE)],check=True)
            print(f"validated {job_id}",flush=True)
            if args.render:
                subprocess.run([str(cli),"render","--plan",str(path),"--assets-root",str(WORKSPACE),
                                "--output",str(OUT/f"{job_id}.mp4"),"--backend","software"],check=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
