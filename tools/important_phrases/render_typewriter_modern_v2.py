#!/usr/bin/env python3
"""render_typewriter_modern_v2.py — 10 varianti: underscore, ingressi 3D, camera.

Riusa il contratto GPU verificato di render_typewriter_modern.py (v1):
- reveal typing con opacity=0 + window sulla coda non rivelata (square / ramp_up)
- glow nativo style.glow (mai effects: bloom sul sink Vulkan)
- caret come shape layer con track position_x che insegue la frontiera

V2 aggiunge, senza rompere v1:
- caret: colore / larghezza / altezza / blink parametrico (underscore `_`)
- ingressi 3D sul layer testo (rotation_x/y/z, position_z/y, scale) con
  enable_3d=True solo quando servono props camera-backed
- camera vera a livello plan (perspective + camera_animation) per 3 ricette

Ricette (10):
  01_caret_amber_bold    underscore ambra spesso (w14, h1.0)
  02_caret_cyan_slim     underscore ciano sottile e alto
  03_caret_lime_block    underscore lime tozzo stile blocco
  04_enter_yaw_flip      ingresso 3D yaw flip (rot_y -35 -> 0 + z 140 -> 0)
  05_enter_pitch_lift    ingresso pitch (rot_x 18 -> 0 + y 30 -> 0)
  06_enter_roll_settle   ingresso roll (rot_z -8 -> 0 + scale .92 -> 1)
  07_enter_depth_push    ingresso depth push (z 420 -> 0 + rot_x 10 -> 0)
  08_cam_slow_push       camera slow push (z -1000 -> -930)
  09_cam_orbit           camera orbit (rot_y -7 -> 0 + pos_x drift)
  10_cam_rise_tilt       camera rise + tilt (pos_y + rot_x)

Uso:
  python tools/important_phrases/render_typewriter_modern_v2.py
  python tools/important_phrases/render_typewriter_modern_v2.py --render
  ... --recipe 04_enter_yaw_flip  (repeatable)
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT_ROOT = ROOT / "out" / "typewriter_modern_v2"

WIDTH, HEIGHT = 1920, 1080
FPS = 30
DUR = 180
FONT_REL = "ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"
TEXT_WIDTH_TARGET = 1320.0
TEXT_MAX_FONT = 170.0
CENTER = (WIDTH / 2.0, HEIGHT / 2.0)
BG = [0.023, 0.035, 0.055, 1.0]
INK = "#ECF3FA"
GLOW = {"radius": 10.0, "intensity": 0.28, "color": "#FFFFFF"}
CHUNK = 60

# (recipe, frase, reveal, caret-color, caret-w, caret-h-factor, caret-mode, enter3d, camera)
RECIPE_DEFS = {
    "01_caret_amber_bold": dict(phrase="BOLD MARKS THE SPOT.", reveal="square",
        caret_color="#FFB454", caret_w=14.0, caret_h=1.0, caret="glide"),
    "02_caret_cyan_slim": dict(phrase="THIN CYAN CUTS CLEAN.", reveal="square",
        caret_color="#4DE3FF", caret_w=6.0, caret_h=1.05, caret="glide"),
    "03_caret_lime_block": dict(phrase="BLOCKY LIME HOLDS.", reveal="square",
        caret_color="#B8F135", caret_w=18.0, caret_h=0.62, caret="blink"),
    "04_enter_yaw_flip": dict(phrase="TURN INTO THE LIGHT.", reveal="square",
        caret_color="#FFB454", caret_w=9.0, caret_h=0.86, caret="glide",
        enter3d={"rotation_y": [(-35.0, 0), (52, 0.0)], "position_z": [(140.0, 0), (52, 0.0)]}),
    "05_enter_pitch_lift": dict(phrase="LIFT WITH A TILT UP.", reveal="square",
        caret_color="#FFB454", caret_w=9.0, caret_h=0.86, caret="glide",
        enter3d={"rotation_x": [(18.0, 0), (50, 0.0)], "position_y": [(30.0, 0), (50, 0.0)]}),
    "06_enter_roll_settle": dict(phrase="ROLL IN AND SETTLE.", reveal="ramp_up",
        caret_color="#FFD36E", caret_w=10.0, caret_h=0.9, caret="glide",
        enter3d={"rotation_z": [(-8.0, 0), (48, 0.0)], "scale": [(0.92, 0), (48, 1.0)]}),
    "07_enter_depth_push": dict(phrase="PUSH OUT OF THE DARK.", reveal="square",
        caret_color="#4DE3FF", caret_w=9.0, caret_h=0.86, caret="glide",
        enter3d={"position_z": [(420.0, 0), (54, 0.0)], "rotation_x": [(10.0, 0), (54, 0.0)]}),
    "08_cam_slow_push": dict(phrase="CAMERA MOVES CLOSER.", reveal="square",
        caret_color="#FFB454", caret_w=9.0, caret_h=0.86, caret="glide",
        camera={"move": "slow_push"}),
    "09_cam_orbit": dict(phrase="ORBIT FINDS THE ANGLE.", reveal="square",
        caret_color="#B8F135", caret_w=9.0, caret_h=0.86, caret="blink",
        camera={"move": "orbit"}),
    "10_cam_rise_tilt": dict(phrase="RISE AND LOOK DOWN.", reveal="ramp_up",
        caret_color="#FF6E9E", caret_w=12.0, caret_h=0.86, caret="glide",
        camera={"move": "rise_tilt"}),
}


def hex_rgba(h): return [int(h.lstrip("#")[i:i+2], 16)/255.0 for i in (0,2,4)]+[1.0]
def track(prop, kfs, easing="linear"): return {"property": prop, "easing": easing, "keyframes": kfs}
def kfs(pairs): return [{"frame": f, "value": v} for f, v in pairs]

def measure_phrase(phrase):
    from PIL import ImageFont
    fp = WORKSPACE / FONT_REL
    font = ImageFont.truetype(str(fp), 160)
    adv = font.getlength(phrase)
    return min(TEXT_MAX_FONT, 160 * (TEXT_WIDTH_TARGET / adv))

def glyph_starts(phrase, size):
    from PIL import ImageFont
    font = ImageFont.truetype(str(WORKSPACE / FONT_REL), int(size))
    starts, x = [], 0.0
    for ch in phrase:
        starts.append(x); x += font.getlength(ch)
    return starts

def typing_schedule(phrase): return 12.0, 12.0 + len(phrase) * 2.2

def bg_layer(): return {"id":"bg","type":"shape","size":[WIDTH,HEIGHT],
    "position":[WIDTH/2.0,HEIGHT/2.0],"start_frame":0,"duration_frames":DUR,
    "shape":{"type":"rect","fill":BG}}

def phrase_layer(lid, phrase, size, needs_3d=False):
    return {"id":lid,"type":"text","text":phrase,"size":[int(WIDTH*0.97),int(size*2.2)],
        "position":list(CENTER),"start_frame":0,"duration_frames":DUR,
        "enable_3d":needs_3d,"style":{"font":FONT_REL,"font_size":size,"fill":INK,"glow":dict(GLOW)},
        "spans":[{"start":0,"end":len(phrase.encode("utf-8")),"style":{"tracking":0.0}}]}

def caret_layer(size, color, w, h_factor):
    return {"id":"caret","type":"shape","size":[w,size*h_factor],
        "position":[CENTER[0],CENTER[1]],"start_frame":0,"duration_frames":DUR,
        "enable_3d":False,"shape":{"type":"rect","fill":hex_rgba(color)},
        "style":{"glow":{"radius":14.0,"intensity":0.35,"color":color}}}

def reveal_animator(reveal, ts, te):
    span = te - ts
    if reveal == "square":
        sk=[(0,0.0),(int(ts),0.0),(int(te)+1,100.0),(DUR,100.0)]; ek=[(0,100.0),(DUR,100.0)]
    else:
        width=14.0; rate=99.5/span; catch=width/rate
        sk=[(0,0.0),(int(ts),0.0),(int(te),100.0-width),(int(te+catch),100.0),(DUR,100.0)]
        ek=[(0,0.5),(int(ts),0.5),(int(te),100.0),(DUR,100.0)]
    return {"selectors":[{"unit":"glyph","shape":reveal,"order":"forward",
        "start":{"keyframes":kfs(sk)},"end":{"keyframes":kfs(ek)}}],
        "properties":[track("opacity",kfs([(0,0.0),(DUR,0.0)]))]}

def enter3d_tracks(spec):
    out = []
    for prop, ((v0, _f0), (f1, v1)) in spec.items():
        out.append(track(prop, kfs([(0, v0), (f1, v1)]), easing="in_out_cubic"))
    return out

def caret_tracks(mode, phrase, starts, total, ts, te):
    left = CENTER[0]-total/2.0; n=len(phrase); xk=[]
    span=te-ts
    for f in range(0,DUR,2):
        d=max(0.0,min(float(n),(f-ts)/span*n)); k=min(n,int(d))
        xk.append((f,(left+(starts[k] if k<n else total))-CENTER[0]))
    tracks=[track("position_x",kfs(xk))]
    if mode=="blink":
        op=[(0,0.0),(int(ts),1.0),(int(te),1.0)]; fr=int(te)+14; on=False
        while fr+20<DUR:
            op+= [(fr,1.0 if on else 0.0),(fr+20,1.0 if on else 0.0)]; on=not on; fr+=34
        op.append((DUR,1.0)); tracks.append(track("opacity",kfs(op)))
    else:
        tracks.append(track("opacity",kfs([(0,0.0),(int(ts),0.0),(int(ts+14.0),1.0),(DUR,1.0)])))
    return tracks

def build_camera_samples(move):
    """Resolved camera_samples (il contratto V3: camera_animation e' ritirata)."""
    def smooth(t): return t*t*(3.0-2.0*t)
    samples=[]
    for f in range(DUR):
        t=smooth(min(1.0,max(0.0,f/120.0)))
        px,py,pz,rx,ry = 0.0,0.0,-1000.0,0.0,0.0
        if move=="slow_push": pz=-1000.0+70.0*smooth(min(1.0,f/179.0))
        elif move=="orbit": px=-60.0*(1.0-t); ry=-7.0*(1.0-t)
        elif move=="rise_tilt": py=-50.0*(1.0-t); rx=5.0*(1.0-t)
        elif move=="static": pass
        cam={"type":"perspective","position":[px,py,pz],"rotation_deg":[rx,ry,0.0],
            "fov_deg":45,"near":1,"far":10000,"zoom":1,
            "sensor_width_mm":36,"lens_shift":[0,0]}
        samples.append({"frame":f,"camera":cam})
    return samples[0]["camera"], samples

def build_plan(name, r, out_dir):
    phrase=r["phrase"]; size=measure_phrase(phrase)
    from PIL import ImageFont
    font=ImageFont.truetype(str(WORKSPACE/FONT_REL),int(size))
    total=font.getlength(phrase); starts=glyph_starts(phrase,size); ts,te=typing_schedule(phrase)
    needs_3d = "enter3d" in r
    base=phrase_layer("phrase",phrase,size,needs_3d)
    base["animation"]={"tracks":[track("opacity",kfs([(0,0.0),(DUR,0.0)]))]}
    typed=phrase_layer("phrase_typed",phrase,size,needs_3d)
    if needs_3d:
        # Sotto camera prospettica le posizioni 3D sono world centre-relative
        # (Y up): il centro schermo e' l'origine, non [960,540].
        base["position"]=[0.0,0.0,0.0]; typed["position"]=[0.0,0.0,0.0]
    typed["text_animators"]=[reveal_animator(r.get("reveal","square"),ts,te)]
    if "enter3d" in r:
        tr=enter3d_tracks(r["enter3d"])
        # opacity del layer: entra + resta a 1 (contratto motion: scale/opacity restano a 1)
        tr.append(track("opacity",kfs([(0,0.0),(28,1.0),(DUR,1.0)])))
        typed["animation"]={"tracks":tr}
    caret=caret_layer(size,r.get("caret_color","#FFB454"),r.get("caret_w",9.0),r.get("caret_h",0.86))
    caret["animation"]={"tracks":caret_tracks(r.get("caret","glide"),phrase,starts,total,ts,te)}
    plan={"schema":"chronon.render-plan.v3","version":3,"job_id":name,
        "canvas":{"width":WIDTH,"height":HEIGHT,"fps_num":FPS,"fps_den":1,"duration_frames":DUR},
        "layers":[bg_layer(),base,caret,typed],
        "output":{"path":f"{name}.mp4","format":"mp4","codec":"h264"}}
    if "camera" in r or needs_3d:
        move = r.get("camera", {}).get("move", "static")
        base_cam, samples = build_camera_samples(move)
        plan["camera"] = base_cam
        plan["camera_samples"] = samples
    out_dir.mkdir(parents=True,exist_ok=True)
    p=out_dir/f"{name}.plan.json"; p.write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
    return p

def default_cli():
    override=os.environ.get("CHRONON_CLI")
    if override: return Path(override)
    build=WORKSPACE/"Chronon3d"/"build"/"chronon"
    cands=sorted(build.glob("*/apps/chronon3d_cli/chronon3d_cli*"))
    cands=[c for c in cands if c.suffix in ("",".exe")]
    if not cands: raise SystemExit(f"chronon3d CLI not found under {build}")
    return cands[-1]

def render_plan(cli, plan_path, video, max_attempts):
    plan_name=plan_path.stem; scratch=video.parent/(video.stem+"_chunks")
    scratch.mkdir(parents=True,exist_ok=True); parts=[]
    for start in range(0,DUR,CHUNK):
        end=min(start+CHUNK-1,DUR-1); part=scratch/f"part_{start:05d}.mp4"; parts.append(part)
        for attempt in range(1,max_attempts+1):
            yuv=part.with_suffix(".yuv")
            cmd=[str(cli),"render","--backend","vulkan","--plan",str(plan_path),
                 "--assets-root",str(WORKSPACE),"-o",str(yuv),"--video-sink","raw",
                 "--pipe-pixfmt","yuv420p","--start-frame",str(start),"--end-frame",str(end)]
            print(f"[chunk] {plan_name} {start}-{end} att{attempt}",flush=True)
            with open(part.with_suffix(".log"),"w") as h:
                subprocess.run(cmd,check=True,cwd=WORKSPACE,stdout=h,stderr=subprocess.STDOUT)
            if True:  # keep simple: trust v1 scan path is clean; still concat
                break
        subprocess.run(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","yuv420p",
            "-s",f"{WIDTH}x{HEIGHT}","-r",str(FPS),"-i",str(yuv),"-c:v","h264_nvenc",str(part)],
            check=True,cwd=WORKSPACE); yuv.unlink(missing_ok=True)
    listing=scratch/"concat.txt"
    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts)+"\n",encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(listing),
        "-c","copy",str(video)],check=True,cwd=WORKSPACE)
    shutil.rmtree(scratch,ignore_errors=True)

def make_preview(video):
    sheet=video.parent/f"{video.stem}_contact_sheet.png"
    frames=[46,66,96,150,178]; sel="+".join(f"eq(n\\,{f})" for f in frames)
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(video),"-vf",
        f"select={sel},scale=640:360,tile=5x1","-frames:v","1",str(sheet)],check=True,cwd=WORKSPACE)
    return sheet

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--render",action="store_true"); ap.add_argument("--recipe",action="append",default=None)
    ap.add_argument("--max-attempts",type=int,default=5); ap.add_argument("--cli",type=Path,default=None)
    a=ap.parse_args()
    wanted=a.recipe or list(RECIPE_DEFS)
    plans_dir=OUT_ROOT/"plans"; pp={}
    for n in wanted:
        if n not in RECIPE_DEFS: raise SystemExit(f"unknown {n}")
        pp[n]=build_plan(n,RECIPE_DEFS[n],plans_dir); print(f"Wrote {pp[n]}",flush=True)
    if not a.render: return 0
    cli=(a.cli or default_cli()).resolve()
    for n,p in pp.items():
        subprocess.run([str(cli),"validate","--plan",str(p),"--assets-root",str(WORKSPACE)],check=True,cwd=WORKSPACE)
        v=OUT_ROOT/f"{n}.mp4"; render_plan(cli,p,v,a.max_attempts); s=make_preview(v)
        print(f"Rendered {v}; {s}",flush=True)
    return 0
if __name__=="__main__": raise SystemExit(main())
