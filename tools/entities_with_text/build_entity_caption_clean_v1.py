#!/usr/bin/env python3
"""Clean, name-only Trump caption studies with archival family pair variants."""
from __future__ import annotations

import io, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/entity_caption_clean_v1"
CHRONON = ROOT.parent / "Chronon3d"
CLI = CHRONON / "build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
W, H, FPS, FRAMES = 1920, 1080, 30, 150
FONT_DIR = OUT / "assets/fonts"
FONTS = ["Bodoni72-BookItalic.ttf", "Space-Grotesk.ttf", "Montserrat-Bold.ttf", "Instrument-Sans.ttf"]
ARCHIVE = OUT / "assets/trump_fred_1986.jpg"
PORTRAIT_CUTOUT = ROOT / "out/entity_caption_reference_v3/assets/portraits/donald-trump-editorial.png"
PORTRAIT_2017 = OUT / "assets/trump_official_2017.jpg"


def kf(prop, pairs, easing="out_cubic"):
    return {"property": prop, "easing": easing, "keyframes": [{"frame": f, "value": v} for f, v in pairs]}


def crop_face(im, box, size):
    crop = im.crop(box)
    crop = ImageOps.fit(crop, size, method=Image.Resampling.LANCZOS, centering=(.5, .38))
    crop = ImageOps.grayscale(crop).convert("RGB")
    crop = ImageEnhance.Contrast(crop).enhance(1.16)
    return crop


def cover(im, size, center=(.5, .38), bg=(230,228,219)):
    if im.mode == "RGBA":
        bgim=Image.new("RGBA",im.size,(*bg,255)); bgim.alpha_composite(im); im=bgim.convert("RGB")
    return ImageOps.fit(im.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=center)


def make_art():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets/photos").mkdir(parents=True, exist_ok=True)
    im = Image.open(PORTRAIT_CUTOUT)
    official = Image.open(PORTRAIT_2017)
    fam = Image.open(ARCHIVE)
    # Distinct images for each of the two requested families.
    photos = {
        "trump_editorial": cover(im, (800, 1080), (.5, .30)),
        "trump_2017": cover(official, (800, 1080), (.5, .30)),
        "trump_1986": crop_face(fam, (2420, 430, 4890, 3290), (800, 1080)),
        "fred_1986": crop_face(fam, (260, 460, 2810, 3290), (800, 1080)),
    }
    for name, pic in photos.items():
        pic.save(OUT / f"assets/photos/{name}.jpg", quality=94, optimize=True)

    # Paper-wipe plates: spare, tactile, and intentionally free of extra copy.
    for i, key in enumerate(("trump_editorial", "trump_2017"), 1):
        base = Image.new("RGB", (W, H), (11, 12, 13)); d=ImageDraw.Draw(base, "RGBA")
        # restrained print texture and ruled edges
        for x in range(36, 930, 12): d.line((x, 100, x, 980), fill=(215,210,194,7), width=1)
        d.rectangle((78, 255, 1160, 810), fill=(235,232,221,255))
        d.rectangle((78, 255, 90, 810), fill=(170,48,54,255))
        d.rectangle((1160, 0, 1170, H), fill=(236,233,223,230))
        base.save(OUT/f"assets/plate_paper_{i}.jpg", quality=94)
    # Halftone card plates. Portraits are separate image layers; only a name is overlaid.
    for i in range(1, 3):
        base=Image.new("RGB",(W,H),(8,10,12)); d=ImageDraw.Draw(base,"RGBA")
        for x in range(12,W,12):
            for y in range(12,H,12): d.ellipse((x,y,x+2,y+2),fill=(225,225,220,17))
        d.rounded_rectangle((112,72,816,1008),radius=34,fill=(223,220,208,255))
        d.line((1010,540,1740,540),fill=(79,172,255,245),width=5)
        base.save(OUT/f"assets/plate_halftone_{i}.jpg",quality=94)
    # Three father/son editorial pair backgrounds: one shared historic photo source, three art directions.
    for i, colors in enumerate([((10,12,13),(228,225,216)),((11,23,22),(232,230,221)),((24,22,20),(239,235,224))],1):
        base=Image.new("RGB",(W,H),colors[0]); d=ImageDraw.Draw(base,"RGBA")
        d.rounded_rectangle((92,76,920,964),radius=18,fill=(231,229,220,255))
        d.rounded_rectangle((1000,76,1828,964),radius=18,fill=(231,229,220,255))
        if i == 1:
            d.line((960,80,960,1000),fill=(240,238,230,95),width=2)
        elif i == 2:
            d.line((960,75,960,995),fill=(90,174,245,210),width=5)
            d.rectangle((92,905,1828,910),fill=(90,174,245,100))
        else:
            d.rectangle((70,70,1850,880),outline=(201,53,59,190),width=3)
            d.line((960,60,960,990),fill=(201,53,59,120),width=2)
        base.save(OUT/f"assets/plate_pair_{i}.jpg",quality=94)


def compose_clean_art():
    """Bake reliable image placements into plates; keep only the entity labels as animated layers."""
    plates=OUT/"assets/plates"; titles=OUT/"assets/titles"
    plates.mkdir(parents=True,exist_ok=True); titles.mkdir(parents=True,exist_ok=True)
    ff={name:ImageFont.truetype(str(FONT_DIR/name),sz) for name,sz in [
        ("Bodoni72-BookItalic.ttf",108),("Montserrat-Bold.ttf",74),("Instrument-Sans.ttf",69) ]}
    def fit(path,size,center=(.5,.38)):
        im=Image.open(path).convert("RGB")
        return ImageOps.fit(im,size,method=Image.Resampling.LANCZOS,centering=center)
    def rounded_paste(dst,src,xy,r=18):
        mask=Image.new("L",src.size,0); ImageDraw.Draw(mask).rounded_rectangle((0,0,src.width-1,src.height-1),radius=r,fill=255)
        dst.paste(src,xy,mask)
    def title_png(name, entries):
        im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
        for text,xy,fontname,color in entries: d.text(xy,text,font=ff[fontname],fill=color,anchor="mm")
        im.save(titles/f"{name}.png",optimize=True)
    for idx,photo in enumerate(("trump_editorial","trump_2017"),1):
        bg=Image.new("RGB",(W,H),(11,12,13)); d=ImageDraw.Draw(bg,"RGBA")
        for x in range(36,930,12): d.line((x,100,x,980),fill=(215,210,194,7),width=1)
        d.rectangle((78,255,1160,810),fill=(235,232,221,255)); d.rectangle((78,255,90,810),fill=(170,48,54,255))
        d.rectangle((1160,0,1170,H),fill=(236,233,223,230))
        rounded_paste(bg,fit(OUT/f"assets/photos/{photo}.jpg",(800,1080),(.5,.3)),(1120,0),0)
        bg.save(plates/f"paper_{idx}.jpg",quality=95)
        title_png(f"paper_{idx}",[("DONALD TRUMP",(620,540),"Bodoni72-BookItalic.ttf",(23,24,26,255))])
    for idx,photo in enumerate(("trump_editorial","trump_2017"),1):
        bg=Image.new("RGB",(W,H),(8,10,12)); d=ImageDraw.Draw(bg,"RGBA")
        for x in range(12,W,12):
            for y in range(12,H,12): d.ellipse((x,y,x+2,y+2),fill=(225,225,220,17))
        d.rounded_rectangle((112,72,816,1008),radius=34,fill=(223,220,208,255))
        rounded_paste(bg,fit(OUT/f"assets/photos/{photo}.jpg",(672,912),(.5,.3)),(128,84),24)
        d.line((1010,540,1740,540),fill=(79,172,255,245),width=5)
        bg.save(plates/f"halftone_{idx}.jpg",quality=95)
        title_png(f"halftone_{idx}",[("DONALD TRUMP",(1375,540),"Montserrat-Bold.ttf",(246,246,241,255))])
    variants=[((10,12,13),(240,238,230),(218,55,60)),((11,23,22),(235,237,230),(83,171,244)),((24,22,20),(242,235,223),(216,173,90))]
    for idx,(bgcol,cardcol,accent) in enumerate(variants,1):
        bg=Image.new("RGB",(W,H),bgcol); d=ImageDraw.Draw(bg,"RGBA")
        d.rounded_rectangle((92,76,920,964),radius=18,fill=cardcol+(255,))
        d.rounded_rectangle((1000,76,1828,964),radius=18,fill=cardcol+(255,))
        if idx==1: d.line((960,80,960,1000),fill=(240,238,230,105),width=2)
        elif idx==2:
            d.line((960,75,960,995),fill=accent+(230,),width=5); d.rectangle((92,943,1828,949),fill=accent+(150,))
        else:
            d.rectangle((70,62,1850,978),outline=accent+(210,),width=3); d.line((960,60,960,990),fill=accent+(130,),width=2)
        rounded_paste(bg,fit(OUT/"assets/photos/fred_1986.jpg",(788,680),(.5,.38)),(108,94),10)
        rounded_paste(bg,fit(OUT/"assets/photos/trump_1986.jpg",(788,680),(.5,.38)),(1016,94),10)
        bg.save(plates/f"pair_{idx}.jpg",quality=95)
        title_png(f"pair_{idx}",[("FRED TRUMP",(506,850),"Instrument-Sans.ttf",(21,22,23,255)),
                                  ("DONALD TRUMP",(1414,850),"Instrument-Sans.ttf",(21,22,23,255))])


def image_layer(id, asset, pos, size, tracks):
    return {"id":id,"type":"image","asset":asset,"position":list(pos),"size":list(size),"fit":"cover",
            "start_frame":0,"duration_frames":FRAMES,"animation":{"tracks":tracks}}


def text_layer(id, text, fontname, size, pos, fill, tracks, glow=None, box=(1000,180)):
    st={"font":f"assets/fonts/{fontname}","font_size":size,"min_font_size":size,"max_font_size":size,
        "fit_mode":"shrink_only","fill":fill}
    if glow: st["glow"]={"radius":8,"intensity":.28,"color":glow}
    return {"id":id,"type":"text","text":text,"position":list(pos),"size":list(box),"start_frame":0,
            "duration_frames":FRAMES,"style":st,"enable_3d":True,"animation":{"tracks":tracks}}


def build_plans():
    specs=[]
    # The two requested styles, each with multiple distinct Trump photographs.
    for i,photo in enumerate(("trump_editorial","trump_2017"),1):
        specs.append((f"01_paper_name_{i:02d}", "paper", photo, i))
    for i,photo in enumerate(("trump_editorial","trump_2017"),1):
        specs.append((f"03_halftone_name_{i:02d}", "halftone", photo, i))
    for i in range(1,4): specs.append((f"05_father_son_{i:02d}", "pair", "pair", i))
    plans=[]
    for job, style, photo, idx in specs:
        layers=[]
        if style == "paper":
            layers.append(image_layer("plate",f"assets/plates/paper_{idx}.jpg",(0,0),(W,H),[kf("scale",[(0,1.04),(149,1.0)],"in_out_sine")]))
            layers.append(image_layer("animated-entity-name",f"assets/titles/paper_{idx}.png",(0,0),(W,H),[
                kf("scale",[(0,.94),(34,1.0)],"out_back"),kf("opacity",[(0,0),(14,1)])]))
        elif style == "halftone":
            layers.append(image_layer("plate",f"assets/plates/halftone_{idx}.jpg",(0,0),(W,H),[kf("scale",[(0,1.0),(149,1.025)],"in_out_sine")]))
            layers.append(image_layer("animated-entity-name",f"assets/titles/halftone_{idx}.png",(0,0),(W,H),[
                kf("scale",[(0,.9),(30,1.0)],"out_back"),kf("opacity",[(0,0),(17,1)])]))
        else:
            layers.append(image_layer("plate",f"assets/plates/pair_{idx}.jpg",(0,0),(W,H),[kf("scale",[(0,1.045),(149,1.0)],"in_out_sine")]))
            layers.append(image_layer("fred-name",f"assets/titles/pair_{idx}.png",(0,0),(W,H),[
                kf("scale",[(0,.97),(29,1.0)],"out_back"),kf("opacity",[(0,0),(13,1)])]))
        plans.append({"schema":"chronon.render-plan.v3","version":3,"job_id":job,
          "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":FRAMES},"layers":layers,
          "output":{"path":f"{job}.mp4","format":"mp4","codec":"h264"}})
    return plans


def render(plan_path, output):
    raw=output.with_suffix(".nv12")
    cmd=[str(CLI),"render","--plan",str(plan_path),"--assets-root",str(OUT),"--backend","vulkan","--profile","preview",
         "--fps",str(FPS),"--video-sink","raw","--pipe-pixfmt","nv12","--chunks","1","--fb-pool-budget-mb","512",
         "--fb-pool-clear-policy","trim-after-job","--start-frame","0","--end-frame",str(FRAMES-1),"-o",str(raw)]
    subprocess.run(cmd,cwd=ROOT.parent,check=True)
    assert raw.stat().st_size==FRAMES*W*H*3//2,raw.stat().st_size
    subprocess.run(["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","nv12","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i",str(raw),"-frames:v",str(FRAMES),"-vsync","cfr","-c:v","h264_nvenc","-preset","p4","-cq","17","-b:v","0","-pix_fmt","yuv420p","-r",str(FPS),"-video_track_timescale",str(FPS*1000),str(output)],cwd=ROOT.parent,check=True)
    raw.unlink()
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-select_streams","v:0","-show_entries","stream=width,height,r_frame_rate,nb_read_frames:format=duration","-of","json",str(output)]))
    s=meta["streams"][0]
    assert (s["width"],s["height"],s["r_frame_rate"],int(s["nb_read_frames"]))==(W,H,"30/1",FRAMES),meta
    assert abs(float(meta["format"]["duration"])-5)<.02,meta
    print("VERIFIED",output.name,flush=True)


def contact_sheet():
    items=sorted(OUT.glob("*.mp4"))
    w,h=960,540
    sheet=Image.new("RGB",(w*2,(h+34)*((len(items)+1)//2)),(12,13,14)); d=ImageDraw.Draw(sheet)
    ff=ImageFont.truetype(str(FONT_DIR/"Space-Grotesk.ttf"),23)
    for i,p in enumerate(items):
        raw=subprocess.check_output(["ffmpeg","-v","error","-ss","2","-i",str(p),"-frames:v","1","-f","image2pipe","-vcodec","png","-"])
        im=Image.open(io.BytesIO(raw)).convert("RGB").resize((w,h),Image.Resampling.LANCZOS)
        x=(i%2)*w; y=(i//2)*(h+34); sheet.paste(im,(x,y)); d.text((x+12,y+h+5),p.stem.upper(),font=ff,fill=(240,238,231))
    path=OUT/"entity_caption_clean_v1_contact_sheet.png"; sheet.save(path,optimize=True); return path


def main():
    import shutil
    FONT_DIR.mkdir(parents=True,exist_ok=True)
    for f in FONTS: shutil.copy2(CHRONON/"assets/fonts"/f,FONT_DIR/f)
    make_art()
    compose_clean_art()
    plans=build_plans()
    for plan in plans:
        p=OUT/(plan["job_id"]+".plan.json"); p.write_text(json.dumps(plan,indent=2)+"\n")
        output=OUT/(plan["job_id"]+".mp4")
        if output.exists() and output.stat().st_size:
            print("KEEP_VERIFIED_OUTPUT",output.name,flush=True)
            continue
        render(p,output)
    print("CONTACT_SHEET",contact_sheet())


if __name__=="__main__": main()
