#!/usr/bin/env python3
"""Recreate 13 portrait/name references as clean monochrome GPU studies."""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import build_entity_caption_reference_v3 as base  # noqa: E402

OUT = ROOT / "out/entity_style_recreations_v1"
ASSET_ROOT = OUT
W, H, FPS = 1920, 1080, 30
SCENE_FRAMES = 105
PORTRAIT = "assets/portraits/donald-trump-apple.png"
FONT = "Bricolage-Grotesque.ttf"
INK = "#171819"

# Name remains native editable text in every plan. Side can be switched in the
# layout records, and image position is computed from that value.
LAYOUTS = [
    ("01_editorial_pair", "Editorial Pair", "left", "right", "single"),
    ("02_mirrored_minimal", "Mirrored Minimal", "right", "left", "single"),
    ("03_big_type", "Big Type", "right", "left", "stack"),
    ("04_centered_portrait", "Centered Portrait", "center", "center", "below"),
    ("05_portrait_closeup", "Portrait Close Up", "left", "right", "single"),
    ("06_name_bracket", "Name Bracket", "center", "center", "bracket"),
    ("07_type_first", "Type First", "right", "left", "stack"),
    ("08_gallery_frame", "Gallery Frame", "left", "right", "single"),
    ("09_corner_portrait", "Corner Portrait", "left", "right", "stack"),
    ("10_vertical_balance", "Vertical Balance", "left", "right", "stack"),
    ("11_soft_card", "Soft Card", "left", "right", "single"),
    ("12_ink_outline", "Ink Outline", "right", "left", "single"),
    ("13_editorial_rule", "Editorial Rule", "left", "right", "single"),
]

def kf(prop: str, keys: list[tuple[int, float]], easing="out_cubic"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}

def make_plate(i: int) -> Path:
    p = ASSET_ROOT / "assets/plates" / f"clean-{i+1:02d}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGBA", (W,H), (255,255,255,255))
    d = ImageDraw.Draw(im, "RGBA")
    # Restrained structural accents only: fine rules, open frames and soft gray
    # surfaces. Reference copy, labels, dates and decorative slogans are removed.
    if i in (0, 4, 7, 10):
        d.rounded_rectangle((98,74,822,1006), radius=(28 if i in (0,10) else 8),
                            outline=(25,26,28,30 if i==10 else 58), width=2)
    elif i in (1, 2, 6, 11):
        d.line((1090,135,1090,945), fill=(20,22,24,28), width=2)
    elif i == 3:
        d.rounded_rectangle((542,54,1378,922), radius=28, fill=(249,249,249,255),
                            outline=(27,29,30,35), width=2)
    elif i == 5:
        d.line((570,904,1350,904), fill=(30,31,32,110), width=2)
    elif i == 8:
        d.line((1290,155,1810,155), fill=(20,22,24,38), width=2)
    elif i == 9:
        d.rounded_rectangle((112,74,808,1006), radius=14, fill=(248,248,248,255))
    elif i == 12:
        d.line((94,935,1826,935), fill=(28,29,31,70), width=2)
    im.save(p)
    return p

def build_plan() -> dict:
    layers = [{"id":"white-stage", "type":"image", "asset":"assets/plates/clean-01.png",
               "size":[W,H], "fit":"cover", "position":[0,0], "start_frame":0,
               "duration_frames":SCENE_FRAMES*len(LAYOUTS)}]
    photo_anim = [
        [kf("position_y",[(0,44),(26,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_x",[(0,70),(25,0)]), kf("opacity",[(0,0),(11,1)])],
        [kf("scale",[(0,.92),(27,1)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_y",[(0,58),(26,0)]), kf("scale",[(0,.96),(29,1)])],
        [kf("scale",[(0,1.08),(28,1)],"out_cubic"), kf("opacity",[(0,.18),(10,1)])],
        [kf("rotation_z",[(0,-2),(24,0)]), kf("opacity",[(0,0),(10,1)])],
        [kf("position_x",[(0,90),(28,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_y",[(0,34),(24,0)]), kf("scale",[(0,.97),(25,1)])],
        [kf("position_y",[(0,-58),(30,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("scale",[(0,.88),(28,1)],"out_cubic"), kf("opacity",[(0,0),(12,1)])],
        [kf("position_x",[(0,-55),(30,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("rotation_z",[(0,2.2),(26,0)]), kf("scale",[(0,.96),(28,1)])],
        [kf("position_y",[(0,45),(25,0)]), kf("opacity",[(0,0),(11,1)])],
    ]
    text_anim = [
        [kf("position_x",[(0,48),(28,0)]), kf("opacity",[(0,0),(14,1)])],
        [kf("position_x",[(0,-50),(28,0)]), kf("opacity",[(0,0),(14,1)])],
        [kf("position_y",[(0,36),(29,0)]), kf("opacity",[(0,0),(13,1)])],
        [kf("position_y",[(0,28),(24,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_x",[(0,34),(25,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_y",[(0,-26),(26,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_x",[(0,72),(30,0)]), kf("opacity",[(0,0),(13,1)])],
        [kf("position_x",[(0,42),(27,0)]), kf("opacity",[(0,0),(13,1)])],
        [kf("position_y",[(0,42),(28,0)]), kf("opacity",[(0,0),(13,1)])],
        [kf("position_x",[(0,-55),(30,0)]), kf("opacity",[(0,0),(13,1)])],
        [kf("position_y",[(0,26),(24,0)]), kf("opacity",[(0,0),(12,1)])],
        [kf("position_x",[(0,-60),(30,0)]), kf("opacity",[(0,0),(14,1)])],
        [kf("position_y",[(0,32),(26,0)]), kf("opacity",[(0,0),(13,1)])],
    ]
    for i,(slug,label,side,textside,typ) in enumerate(LAYOUTS):
        start=i*SCENE_FRAMES
        plate=make_plate(i)
        layers.append({"id":f"plate-{i+1:02d}","type":"image","asset":f"assets/plates/{plate.name}",
                       "size":[W,H],"fit":"cover","position":[0,0],"start_frame":start,
                       "duration_frames":SCENE_FRAMES,"animation":{"tracks":[kf("opacity",[(0,0),(8,1)])]}})
        if typ=="below":
            px,py,pw,ph=960,490,650,700; tx,ty,tw,th=960,944,1120,145; ts=82
        elif typ=="bracket":
            px,py,pw,ph=960,470,570,720; tx,ty,tw,th=960,958,1060,150; ts=92
        elif typ=="stack":
            if i==8: px,py,pw,ph=330,230,360,470; tx,ty,tw,th=(1370 if textside=="right" else 550),670,1120,300; ts=118
            elif i==9: px,py,pw,ph=445,540,680,820; tx,ty,tw,th=1420,350,900,300; ts=104
            else: px,py,pw,ph=(1420 if side=="right" else 500),540,640,840; tx,ty,tw,th=(505 if textside=="left" else 1420),540,1020,310; ts=118
        elif i==6:
            px,py,pw,ph=1450,540,590,810; tx,ty,tw,th=510,540,1120,300; ts=120
        else:
            if side=="center": px,py,pw,ph=960,490,650,700
            elif i==4: px,py,pw,ph=(425 if side=="left" else 1495),540,790,940
            elif i==8: px,py,pw,ph=330,225,360,470
            else: px,py,pw,ph=(470 if side=="left" else 1450),540,640,840
            tx,ty,tw,th=(1425 if textside=="right" else 495),540,1000,180; ts=84
        layers.append({"id":f"portrait-{i+1:02d}","type":"image","asset":PORTRAIT,"size":[pw,ph],
                       "fit":"contain","position":[px-W/2, H/2-py],"start_frame":start,
                       "duration_frames":SCENE_FRAMES,"enable_3d":True,"animation":{"tracks":photo_anim[i]}})
        value="DONALD\nTRUMP" if typ=="stack" else "DONALD TRUMP"
        tl=base.text_layer(f"name-{i+1:02d}",value,(tx,H-ty),(tw,th),FONT,ts,INK,text_anim[i])
        tl["start_frame"]=start; tl["duration_frames"]=SCENE_FRAMES
        layers.append(tl)
    return {"schema":"chronon.render-plan.v3","version":3,"job_id":"entity_style_recreations_v1",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":SCENE_FRAMES*len(LAYOUTS)},
            "layers":layers,"output":{"path":"entity_style_recreations_v1.mp4","format":"mp4","codec":"h264"}}

def render(plan_path: Path, out: Path, cli: Path):
    frames=SCENE_FRAMES*len(LAYOUTS); raw=out.with_suffix(".nv12")
    cmd=[str(cli),"render","--plan",str(plan_path),"--assets-root",str(ASSET_ROOT),"--backend","vulkan",
         "--profile","preview","--fps",str(FPS),"--video-sink","raw","--pipe-pixfmt","nv12","--chunks","1",
         "--fb-pool-budget-mb","512","--fb-pool-clear-policy","trim-after-job","--start-frame","0",
         "--end-frame",str(frames-1),"-o",str(raw)]
    subprocess.run(cmd,cwd=WORKSPACE,check=True)
    expected=frames*W*H*3//2
    if raw.stat().st_size!=expected: raise RuntimeError(f"NV12 size mismatch: {raw.stat().st_size} != {expected}")
    subprocess.run(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","nv12","-video_size",f"{W}x{H}",
                    "-framerate",str(FPS),"-i",str(raw),"-frames:v",str(frames),"-vsync","cfr","-c:v","h264_nvenc",
                    "-preset","p4","-cq","18","-b:v","0","-pix_fmt","yuv420p","-r",str(FPS),str(out)],cwd=WORKSPACE,check=True)
    raw.unlink()
    return frames

def contact_sheet(video: Path):
    sheet=Image.new("RGB",(1940,5*570+90),(250,250,249)); d=ImageDraw.Draw(sheet)
    fp=ImageFont.truetype(str(ASSET_ROOT/"assets/fonts"/FONT),22)
    d.text((24,16),"DONALD TRUMP · 13 CLEAN APPLE STUDIES",font=fp,fill=(25,26,28))
    for i,(slug,label,*_) in enumerate(LAYOUTS):
        frame=i*SCENE_FRAMES+78
        raw=subprocess.run(["ffmpeg","-v","error","-ss",f"{frame/FPS:.4f}","-i",str(video),"-frames:v","1","-f","image2pipe","-vcodec","png","-"],check=True,capture_output=True).stdout
        im=Image.open(io.BytesIO(raw)).convert("RGB").resize((940,528),Image.Resampling.LANCZOS)
        x=20+(i%2)*960; y=58+(i//2)*570; sheet.paste(im,(x,y)); d.text((x+8,y+534),f"{i+1:02d}  {label.upper()}",font=fp,fill=(35,36,38))
    p=OUT/"entity_style_recreations_v1_contact_sheet.png"; sheet.save(p,optimize=True); return p

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (ASSET_ROOT/"assets/fonts").mkdir(parents=True,exist_ok=True)
    (ASSET_ROOT/"assets/portraits").mkdir(parents=True,exist_ok=True)
    shutil.copy2(base.CHRONON/"assets/fonts"/FONT,ASSET_ROOT/"assets/fonts"/FONT)
    source=base.PORTRAIT_SOURCE
    shutil.copy2(source,ASSET_ROOT/PORTRAIT)
    # Ensure portrait retains a true transparent background for clean white staging.
    im=Image.open(ASSET_ROOT/PORTRAIT).convert("RGBA")
    from PIL import ImageOps,ImageEnhance
    gray=ImageOps.grayscale(im.convert("RGB")); gray=ImageEnhance.Contrast(gray).enhance(1.23)
    Image.merge("RGBA",(gray,gray.copy(),gray.copy(),im.getchannel("A"))).save(ASSET_ROOT/PORTRAIT)
    plan=build_plan(); pp=OUT/"entity_style_recreations_v1.plan.json"; pp.write_text(json.dumps(plan,indent=2)+"\n",encoding="utf8")
    video=OUT/"entity_style_recreations_v1.mp4"
    frames=render(pp,video,base.CLI); print("VERIFIED_GPU",frames,"frames",frames/FPS,"seconds",flush=True)
    print("CONTACT_SHEET",contact_sheet(video),flush=True)

if __name__=="__main__": main()
