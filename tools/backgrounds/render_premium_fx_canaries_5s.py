#!/usr/bin/env python3
"""Build and render five deterministic, 5 second premium FX canaries."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
WORKSPACE = TEMPLATE.parent
CHRONON = WORKSPACE / "Chronon3d"
OUT = TEMPLATE / "out/premium_fx_canaries_5s"
VISUAL = TEMPLATE / "tests/visual"
GOLDEN_DIR = {"rgb_motion_canary_5s":"rgb", "bloom_canary_5s":"bloom",
              "procedural_background_canary_5s":"background", "light_leak_canary_5s":"light_leak",
              "premium_fx_torture_5s":"premium_torture"}
CLI = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
W, H, FPS, N = 1920, 1080, 30, 150
FONT = "Chronon3d/assets/fonts/Inter-Bold.ttf"
CHECKPOINTS = (0, 30, 60, 90, 120, 149)


def track(prop, values, easing="linear"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": int(f), "value": v} for f, v in values]}


def base(job, color="#050505"):
    c=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
    return {"schema":"chronon.render-plan.v3", "version":3, "job_id":job,
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":N},
            "output":{"path":str(OUT/f"{job}.mp4"),"format":"mp4","codec":"h264"},
    "layers":[{"id":"background","type":"color","color":[*c,1.0],
                        "size":[W,H],"position":[W/2,H/2],"screen_space":True,
                        "start_frame":0,"duration_frames":N}]}


def text(id_, start=0, duration=N, color="#FFFFFF", x=W/2, y=H/2, size=230, effects=None, blend="normal"):
    row={"id":id_,"type":"text","text":"CHRONON","size":[1560,320],"position":[x,y],
         "start_frame":start,"duration_frames":duration,
         "style":{"font":FONT,"font_size":size,"min_font_size":size,"max_font_size":size,
                  "fit_mode":"shrink_only","fill":color},"blend_mode":blend}
    if effects: row["effects"]=effects
    return row


def shape(id_, start=0, duration=N, *, kind="ellipse", size=(120,120), pos=(W/2,H/2), fill="#FFFFFF",
          stroke=None, effects=None, blend="screen", opacity=1.0, animation=None, field=None):
    spec={"type":kind}
    if field:
        spec.update(field)
    else:
        if isinstance(fill,str) and fill.startswith("#"):
            rgb=tuple(int(fill[i:i+2],16)/255 for i in (1,3,5))
            spec["fill"]=[*rgb,1.0]
        else: spec["fill"] = fill
    if stroke: spec["stroke"]=stroke
    row={"id":id_,"type":"shape","shape":spec,"size":list(size),"position":list(pos),
         "start_frame":start,"duration_frames":duration,"blend_mode":blend,"opacity":opacity}
    if effects: row["effects"]=effects
    if animation: row["animation"]={"tracks":animation}
    return row


def bloom(threshold=.4, radius=36, intensity=.6):
    return {"type":"bloom","threshold":threshold,"radius":radius,"intensity":intensity}


def rgb_plan():
    p=base("rgb_motion_canary_5s")
    # White identity source; later segments use separate color branches as a deterministic,
    # visually explicit channel test. Every timeline row is a pure frame function.
    p["layers"].append(text("identity",0,30))
    split_effect={"type":"chromatic_aberration","red_offset":-25,"blue_offset":25}
    p["layers"].append(text("rgb-split",30,30,effects=[split_effect]))
    for ch, color, dx, dy in (("r","#FF2638",-18,12),("g","#32FF92",0,0),("b","#3187FF",18,-12)):
        row=text("warp-"+ch,60,30,color=color,x=W/2+dx,y=H/2+dy,blend="add")
        row["animation"]={"tracks":[
            track("position_x",[(0,0),(14,-2*dx),(29,0)]),
            track("position_y",[(0,0),(14,-2*dy),(29,0)])]}
        p["layers"].append(row)
    p["layers"].append(text("warp-white-core",60,30,size=220))
    # Twelve masked horizontal strips with seeded offsets held in three-frame plateaus.
    import random
    rng=random.Random(42)
    for i in range(12):
        h=320/12
        dy=-160+h*(i+.5)
        dx=round(rng.uniform(-80,80))
        p["layers"].append({**text(f"slice-{i:02d}",90,30,color=("#FF4356" if i%3==0 else "#FFFFFF" if i%3==1 else "#548DFF"),x=W/2+dx),
                            "masks":[{"type":"rect","mode":"intersect","position":[0,dy],"size":[1560,h+.8]}]})
    palette=("#FF2638","#FF9D22","#FFE746","#41F477","#25DDF1","#426BFF","#B646FF")
    for i in reversed(range(8)):
        p["layers"].append(text(f"trail-{i}",120,16,color=palette[round(i*6/7)],x=W/2,y=H/2+i*12,size=210))
    p["layers"].append(text("settle",136,14,size=230))
    return p


def bloom_plan():
    p=base("bloom_canary_5s", "#050505")
    for start,dur,radius,strength,threshold in ((0,30,0,0,.7),(30,30,8,.25,.7),(60,30,48,.7,.7),(90,30,120,.9,.4),(120,30,80,1.2,.2)):
        p["layers"].append(text(f"bloom-title-{start}",start,dur,size=160,
                                effects=([bloom(threshold,radius,strength)] if radius else None)))
        for name,kind,size,pos,col in (("point","ellipse",(34,34),(350,300),"#FFFFFF"),
                                       ("red","ellipse",(54,54),(1570,300),"#FF2020"),
                                       ("hdr","rect",(260,110),(960,790),"#FFFFFF")):
            p["layers"].append(shape(f"bloom-{start}-{name}",start,dur,kind=kind,size=size,pos=pos,fill=col,
                                      effects=([bloom(threshold,radius,strength)] if radius else None)))
    return p


def background_plan():
    p=base("procedural_background_canary_5s", "#000000")
    radial=lambda c:[{"position":0,"color":[*c,.86]},
                     {"position":.55,"color":[*c,.38]},
                     {"position":1,"color":[0,0,0,0]}]
    for start,dur,amount,positions in ((0,30,0,[(0,W/2),(29,W/2)]),
                                        (30,30,0,[(0,W*.3),(29,W*.7)]),
                                        (60,30,.25,[(0,W/2),(29,W/2)]),
                                        (90,30,.18,[(0,W*.25),(29,W*.75)]),
                                        (120,30,.3,[(0,W/2),(19,W/2),(29,W/2)])):
        p["layers"].append(shape(f"radial-field-{start}",start,dur,kind="ellipse",size=(1260,1020),
            pos=(W/2,H/2),blend="normal",field={"fill":{"type":"radial","center":[.5,.5],
            "radius":.72,"spread":"pad","color_stops":radial((.56,.04,.82))}} ,
            effects=([{"type":"turbulent_displace","amount":amount,"size":.45,"evolution":.3,
                       "evolution_speed":0,"complexity":3}] if amount else None),
            animation=[track("position_x",[(f,x-W/2) for f,x in positions])]))
        if start==90:
            for tag,col,pos0,pos1 in (("cyan",(.02,.72,.9),W*.25,W*.7),("magenta",(.92,.025,.48),W*.75,W*.3)):
                p["layers"].append(shape(f"crossing-{tag}",start,dur,kind="ellipse",size=(700,650),
                    pos=(W/2,H*.5),blend="screen",field={"fill":{"type":"radial","center":[.5,.5],
                    "radius":.7,"spread":"pad","color_stops":radial(col)}},
                    animation=[track("position_x",[(0,pos0-W/2),(29,pos1-W/2)])]))
    return p


def leak_plan():
    p=base("light_leak_canary_5s", "#080808")
    p["layers"].append(text("leak-title",0,N,color="#CFCFCF",size=170))
    for start,dur,x0,x1,col in ((30,30,-220,120,"#FF542B"),(60,30,-250,2170,"#FF7A32"),
                                (90,30,0,0,"#FF572D"),(90,30,W,0,"#F1243E"),(120,30,820,820,"#FF642F")):
        if start==90: positions=[(0,x0),(dur-1,x0)]
        else: positions=[(0,x0),(dur-1,x1)]
        # Large blurred emitters deliberately extend beyond the surface to test bounds.
        base_x=0 if start!=90 else x0
        motion=([track("position_x",[(0,x0),(dur-1,x1)])] if start!=90 else None)
        p["layers"].append(shape(f"leak-{start}-{x0}",start,dur,size=(1000,850),pos=(base_x,H/2),fill=col,
            effects=[{"type":"gaussian_blur","radius":180},bloom(.03,160,.25)],
            animation=motion))
    return p


def premium_plan():
    p=base("premium_fx_torture_5s", "#070411")
    # Animated deterministic fractal field plus static dark base.
    p["layers"].append(shape("premium-field",0,N,kind="ellipse",size=(1500,1120),pos=(W/2,H/2),blend="screen",opacity=.75,
        field={"fill":{"type":"radial","center":[.5,.5],"radius":.78,"spread":"pad","color_stops":[
            {"position":0,"color":[.42,.035,.72,.78]},{"position":.58,"color":[.16,.012,.32,.4]},
            {"position":1,"color":[.01,.002,.03,0]}]}},
        effects=[{"type":"turbulent_displace","amount":.16,"size":.5,"evolution":.4,"evolution_speed":0,"complexity":4}]))
    p["layers"].append(shape("red-brush",0,N,kind="path",size=(720,70),pos=(W/2,720),
         field={"path":[{"type":"move_to","point":[-360,0]},{"type":"cubic_to","control1":[-100,-18],"control2":[100,18],"point":[360,0]}],
                "stroke":{"color":"#FF2638","width":16}},blend="screen"))
    p["layers"].append(text("premium-clean",0,N,size=220))
    # Section overlays: leak, RGB chromatic aberration, slices, and 8-tap trail. Clean text is restored at end.
    p["layers"].append(shape("premium-leak",30,120,size=(1250,900),pos=(-100,H/2),fill="#FF522A",
         effects=[{"type":"gaussian_blur","radius":190},bloom(.1,96,.35)],blend="screen",
         animation=[track("position_x",[(0,0),(59,1060),(119,2200)])]))
    p["layers"].append(text("premium-rgb",60,30,effects=[{"type":"chromatic_aberration","red_offset":-15,"blue_offset":15}]))
    import random
    rng=random.Random(42)
    for i in range(12):
        h=320/12; dy=-160+h*(i+.5); dx=rng.randint(-80,80)
        p["layers"].append({**text(f"premium-slice-{i}",90,30,color=("#FF3333" if i%2 else "#6699FF"),x=W/2+dx),
            "masks":[{"type":"rect","mode":"intersect","position":[0,dy],"size":[1560,h+.8]}]})
    for i in reversed(range(8)):
        p["layers"].append(text(f"premium-trail-{i}",100,36,color=("#FF463C","#FF9B32","#FFE44B","#48F57C","#34DDED","#5084FF","#B951FF")[round(i*6/7)],
                                 x=W/2+i*12,y=H/2+i*5,size=210))
    # Final clean settle overlay at f136..149; the procedural backdrop itself is static after f139.
    return p


BUILDERS={"rgb_motion_canary_5s":rgb_plan,"bloom_canary_5s":bloom_plan,
          "procedural_background_canary_5s":background_plan,"light_leak_canary_5s":leak_plan,
          "premium_fx_torture_5s":premium_plan}


def run(cmd):
    subprocess.run([str(x) for x in cmd],check=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render",action="store_true")
    ap.add_argument("--validate",action="store_true")
    ap.add_argument("--frames",action="store_true",help="write sequential and direct checkpoint PNGs and compare")
    ap.add_argument("--only",choices=tuple(BUILDERS),help="render/check only one canary")
    ap.add_argument("--cpu-vulkan",action="store_true",help="compare Bloom f75 raw output on software and Vulkan")
    ap.add_argument("--cli",type=Path,default=CLI)
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    selected={name:builder for name,builder in BUILDERS.items() if args.only is None or args.only==name}
    for name,builder in selected.items():
        plan=builder(); path=OUT/f"{name}.plan.json"
        path.write_text(json.dumps(plan,indent=2)+"\n")
        print(f"WROTE {path}")
        if args.validate or args.render:
            run([args.cli,"validate","--plan",path,"--assets-root",WORKSPACE])
        if args.render:
            run([args.cli,"render","--plan",path,"--assets-root",WORKSPACE,"--output",OUT/f"{name}.mp4","--backend","software"])
        if args.frames:
            d=OUT/"_verify"/name; d.mkdir(parents=True,exist_ok=True)
            golden=VISUAL/GOLDEN_DIR[name]; golden.mkdir(parents=True,exist_ok=True)
            frame_bytes=W*H*4
            sequence=d/"sequential.rgba"
            run([args.cli,"render","--plan",path,"--assets-root",WORKSPACE,"--start-frame","0",
                 "--end-frame",str(N-1),"--output",sequence,"--backend","software","--video-sink","raw"])
            if sequence.stat().st_size != frame_bytes*N:
                raise RuntimeError(f"{name}: raw sequence size does not match {N} RGBA frames")
            from PIL import Image, ImageChops
            report={}
            for frame in CHECKPOINTS:
                direct=d/f"direct_{frame:03d}.rgba"
                run([args.cli,"render","--plan",path,"--assets-root",WORKSPACE,"--start-frame",str(frame),
                     "--end-frame",str(frame),"--output",direct,"--backend","software","--video-sink","raw"])
                expected=sequence.open("rb")
                expected.seek(frame_bytes*frame)
                seq_bytes=expected.read(frame_bytes)
                expected.close()
                direct_bytes=direct.read_bytes()
                exact=direct_bytes==seq_bytes
                seq_image=Image.frombytes("RGBA",(W,H),seq_bytes)
                seq_image.save(golden/f"frame_{frame:03d}.png")
                entry={"exact":exact,"direct_bytes":len(direct_bytes),"sequence_bytes":len(seq_bytes)}
                if not exact:
                    direct_image=Image.frombytes("RGBA",(W,H),direct_bytes)
                    delta=ImageChops.difference(direct_image,seq_image)
                    entry["max_abs_delta"]=max(max(channel) for channel in delta.getextrema())
                    entry["diff_bbox"]=list(delta.getbbox()) if delta.getbbox() else None
                report[str(frame)]=entry
                direct.unlink()
                Path(str(direct)+".timing.json").unlink(missing_ok=True)
            (golden/"random_access_report.json").write_text(json.dumps(report,indent=2)+"\n")
            sequence.unlink()
            Path(str(sequence)+".timing.json").unlink(missing_ok=True)
            for candidate in d.glob("*.timing.json"): candidate.unlink()
            print(name,json.dumps(report))
    if args.cpu_vulkan:
        import numpy as np
        d=OUT/"_parity"; d.mkdir(parents=True,exist_ok=True)
        p=OUT/"bloom_canary_5s.plan.json"
        results={}
        outputs={"software":d/"software_f075.rgba","vulkan":d/"vulkan_f075.rgba"}
        for backend,out in outputs.items():
            proc=subprocess.run([str(args.cli),"render","--plan",str(p),"--assets-root",str(WORKSPACE),
                "--start-frame","75","--end-frame","75","--output",str(out),"--backend",backend,
                "--video-sink","raw"],capture_output=True,text=True)
            results[backend]={"returncode":proc.returncode}
            if proc.returncode:
                results[backend]["error"]=(proc.stderr or proc.stdout)[-4000:]
                break
            results[backend]["bytes"]=out.stat().st_size
        if all(x.get("returncode")==0 for x in results.values()):
            a=np.frombuffer(outputs["software"].read_bytes(),dtype=np.uint8).astype(np.int16)
            b=np.frombuffer(outputs["vulkan"].read_bytes(),dtype=np.uint8).astype(np.int16)
            delta=np.abs(a-b)
            results["comparison"]={"exact":bool(np.array_equal(a,b)),"max_abs":int(delta.max()),
                "mean_abs":float(delta.mean()),"changed_channels":int(np.count_nonzero(delta))}
        for out in outputs.values():
            out.unlink(missing_ok=True); Path(str(out)+".timing.json").unlink(missing_ok=True)
        target=VISUAL/"bloom"; target.mkdir(parents=True,exist_ok=True)
        (target/"cpu_vulkan_f075.json").write_text(json.dumps(results,indent=2)+"\n")
        print("cpu-vulkan",json.dumps(results))


if __name__=="__main__": main()
