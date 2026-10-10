#!/usr/bin/env python3
"""Render individually animated, five-second 1973 oil-crisis examples."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = ROOT / "ChrononTemplate/out/oil_crisis_1973_animation_samples"
ASSETS = OUT / "assets"
W, H, FPS, N = 1920, 1080, 30, 150
INK = (18, 21, 22); PAPER = (247, 247, 243); YELLOW = (242, 229, 0); CORAL = (241, 77, 54)
FONT = ROOT / "Chronon3d/assets/fonts/Inter-Bold.ttf"
REG = ROOT / "Chronon3d/assets/fonts/Inter-Regular.ttf"
DIDONE = ROOT / "Chronon3d/assets/fonts/Didot-Italic.ttf"

def font(sz, path=FONT): return ImageFont.truetype(str(path), sz)
def ease(t):
    t=max(0,min(1,t)); return t*t*(3-2*t)
def pop(t):
    t=max(0,min(1,t)); return 1-(1-t)**3
def text_center(d, xy, s, f, fill, anchor="mm", **kw): d.text(xy,s,font=f,fill=fill,anchor=anchor,**kw)
def base(color=PAPER): return Image.new("RGB",(W,H),color)
def draw_grain(im, seed=7):
    # Restrained, stable paper texture. Noise is deterministic per frame to avoid flicker.
    import numpy as np
    rng=np.random.default_rng(seed)
    a=np.asarray(im,dtype=np.int16); n=rng.integers(-2,3,(H,W,1),dtype=np.int16)
    return Image.fromarray(np.clip(a+n,0,255).astype("uint8"))
def encode(name, framefn):
    target=OUT/f"{name}.nvenc.mp4"
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","h264_nvenc","-preset","p5","-tune","hq","-rc","vbr","-cq","19","-b:v","0","-pix_fmt","yuv420p","-movflags","+faststart",str(target)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(N):
            im=framefn(i/(N-1),i)
            p.stdin.write(im.tobytes())
    finally:
        p.stdin.close()
    if p.wait(): raise RuntimeError(f"NVENC failed for {name}")
    # Keep final deliverable at the canonical filename, never reuse a stale render.
    target.replace(OUT/f"{name}.mp4")

def date_frame(t,i):
    im=base((14,16,17)); d=ImageDraw.Draw(im)
    # Stable archival grain and subtle projector gate; no luminance flashes.
    import random
    rng=random.Random(i//5)
    for _ in range(80):
        x=rng.randrange(W); y=rng.randrange(H); r=rng.choice([1,1,2])
        d.ellipse((x-r,y-r,x+r,y+r),fill=(32,34,34))
    d.rectangle((0,0,13,H),fill=(20,22,22)); d.rectangle((W-14,0,W,H),fill=(20,22,22))
    # Bracket draws in, then the date card wipes on from left to right.
    p=ease((t-.08)/.25); d.rectangle((448,760,448+int(995*p),766),fill=CORAL)
    q=ease((t-.22)/.16); d.rectangle((1438,620,1444,766),fill=CORAL if q>.01 else (14,16,17))
    reveal=pop((t-.30)/.42); x0,y0,x1,y1=450,395,1470,555
    d.rectangle((x0,y0,x0+int((x1-x0)*reveal),y1),fill=CORAL)
    if reveal>.03:
        layer=Image.new("RGBA",(W,H)); ld=ImageDraw.Draw(layer)
        ld.text((960,475),"6 ottobre 1973",font=font(102,DIDONE),fill=(255,249,238,255),anchor="mm")
        im.paste(layer,(0,0),layer)
    # Gentle, continuous camera drift across the five seconds.
    return im

DATE_STYLES=["fade_rise","year_count","calendar_flip","segment_stagger","timeline_tick",
             "range_draw","marker_drop","underline_focus","history_stack","chronology_focus"]
def date_style_frame(style,t,i):
    im=base((14,16,17)); d=ImageDraw.Draw(im)
    cream=(248,246,237); muted=(154,157,151)
    # Editorial date pack examples all use the same event data and visibly different motion.
    a=ease((t-.14)/.36); p=pop((t-.12)/.42)
    if style=="fade_rise":
        y=530+int((1-a)*105); d.rectangle((388,y+85,1532,y+89),fill=CORAL)
        text_center(d,(960,y),"6 ottobre 1973",font(94,DIDONE),cream)
        d.text((960,y+112),"GUERRA DEL KIPPUR",font=font(25,REG),fill=muted,anchor="mm")
    elif style=="year_count":
        year=1948+int(25*ease(t/.74)); text_center(d,(960,465),str(year),font(176),cream)
        w=int(740*a); d.rounded_rectangle((960-w//2,585,960+w//2,594),radius=5,fill=CORAL)
        if t>.62: text_center(d,(960,678),"6 OTTOBRE",font(34,REG),muted)
    elif style=="calendar_flip":
        # A page hinges into a settled card; the stable endpoint reads as a calendar.
        angle=math.cos(math.pi*p); card_w=max(64,int(650*abs(angle)))
        cx,cy=960,525
        d.rounded_rectangle((cx-card_w//2,cy-255,cx+card_w//2,cy+255),radius=24,fill=cream)
        if abs(angle)>.32:
            d.rounded_rectangle((cx-card_w//2,cy-255,cx+card_w//2,cy-132),radius=24,fill=CORAL)
            d.rectangle((cx-card_w//2,cy-157,cx+card_w//2,cy-132),fill=CORAL)
        if p>.42:
            text_center(d,(cx,cy-174),"OTTOBRE",font(31),cream)
            text_center(d,(cx,cy+16),"6",font(158),INK)
            text_center(d,(cx,cy+154),"1973",font(39),INK)
    elif style=="segment_stagger":
        for j,(s,x,y,f) in enumerate([("6",665,480,font(146,DIDONE)),("OTTOBRE",960,490,font(52)),("1973",1280,480,font(146,DIDONE))]):
            q=pop((t-(.12+j*.13))/.34); xx=int(x+(1-q)*(-150 if j%2==0 else 150))
            text_center(d,(xx,y),s,f,cream)
        d.rectangle((670,603,670+int(580*a),609),fill=CORAL)
    elif style in ("timeline_tick","chronology_focus"):
        x0,x1=230,1690; yy=615; years=list(range(1950,2001,5)); x1973=x0+(1973-1950)/(2000-1950)*(x1-x0)
        d.line((x0,yy,x0+int((x1-x0)*a),yy),fill=(95,98,95),width=4)
        for year in years:
            x=x0+(year-1950)/(2000-1950)*(x1-x0); active=year==1970 or year==1975
            hh=26 if active else 13
            d.line((int(x),yy-hh,int(x),yy+hh),fill=CORAL if active else muted,width=4)
            d.text((x,yy+50),str(year),font=font(19,REG),fill=muted,anchor="mm")
        q=ease((t-.38)/.27); r=int(17+10*q)
        d.ellipse((x1973-r,yy-r,x1973+r,yy+r),fill=CORAL)
        text_center(d,(x1973,405-int(35*q)),"6 OTTOBRE 1973",font(43),cream)
        if style=="chronology_focus":
            d.rounded_rectangle((x1973-260,721,x1973+260,787),radius=14,fill=(36,39,39))
            text_center(d,(x1973,754),"GUERRA DEL KIPPUR",font(22,REG),cream)
    elif style=="range_draw":
        d.text((310,340),"1973",font=font(39),fill=cream); d.text((1440,340),"1974",font=font(39),fill=cream)
        d.line((320,550,1600,550),fill=(64,68,68),width=8)
        q=ease((t-.15)/.60); d.line((320,550,320+int(1280*q),550),fill=CORAL,width=10)
        for x in (320,1600): d.ellipse((x-14,536,x+14,564),fill=cream)
        text_center(d,(320+int(1280*min(q,.61)),455),"6 OTTOBRE",font(33),cream)
        if t>.60: text_center(d,(960,700),"1973",font(96,DIDONE),cream)
    elif style=="marker_drop":
        yy=680; d.line((330,yy,1590,yy),fill=(91,94,92),width=4)
        x=960; fall=ease((t-.10)/.52); y=int(210+470*fall)
        d.line((x,yy-145,x,y),fill=CORAL,width=5)
        r=int(10+23*ease((t-.48)/.22)); d.ellipse((x-r,yy-r,x+r,yy+r),fill=CORAL)
        text_center(d,(x,yy-225),"6 ottobre 1973",font(76,DIDONE),cream)
    elif style=="underline_focus":
        text_center(d,(960,520),"6 ottobre 1973",font(105,DIDONE),cream)
        q=ease((t-.26)/.46); d.rounded_rectangle((470,622,470+int(980*q),630),radius=4,fill=CORAL)
        if t>.54: text_center(d,(960,700),"IL GIORNO IN CUI INIZIÒ LA GUERRA",font(25,REG),muted)
    elif style=="history_stack":
        entries=[("1948","Nascita di Israele"),("1956","Crisi di Suez"),("1967","Guerra dei Sei Giorni"),("1973","Guerra del Kippur")]
        for j,(year,label) in enumerate(entries):
            q=ease((t-(.05+j*.13))/.28); x=int(530+(1-q)*115); y=284+j*155
            active=j==3; col=CORAL if active else (67,70,69)
            d.text((x,y),year,font=font(47,DIDONE),fill=col)
            d.text((x+190,y+10),label,font=font(28,REG),fill=cream if active else muted)
            if active: d.rounded_rectangle((470,y-18,1450,y+75),radius=14,outline=CORAL,width=3)
    return im

def map_frame(t,i):
    bg=Image.open(ASSETS/"middle_east_oil_regions.png").convert("RGB")
    # Cropping and rescaling creates a steady camera move over the actual geographic artwork.
    z=1.07+.09*ease(t); cw=int(W/z); ch=int(H/z)
    cx=W//2+int(-22*math.sin(math.pi*t)); cy=H//2+int(-14*t)
    crop=bg.crop((cx-cw//2,cy-ch//2,cx+cw//2,cy+ch//2)).resize((W,H),Image.Resampling.LANCZOS)
    im=crop; d=ImageDraw.Draw(im)
    # Animate map focus: route stroke, then separate location pins and labels.
    d.rounded_rectangle((86,64,610,156),radius=10,fill=(248,247,242,220))
    d.text((112,84),"IL FRONTE DEL SINAI",font=font(37),fill=INK)
    route=[(925,500),(975,545),(1015,610),(1055,673),(1090,725)]
    k=ease((t-.25)/.48); upto=max(2,int(k*(len(route)-1))+1)
    if t>.25: d.line(route[:upto],fill=CORAL,width=8,joint="curve")
    for j,(x,y,label) in enumerate([(1090,725,"SINAI"),(1124,446,"ISRAELE"),(775,725,"EGITTO")]):
        a=ease((t-(.42+j*.12))/.17)
        if a:
            rr=int(8+9*a); d.ellipse((x-rr,y-rr,x+rr,y+rr),fill=CORAL,outline=(255,255,255),width=4)
            d.rounded_rectangle((x+18,y-25,x+18+len(label)*21,y+26),radius=16,fill=(255,255,255,230))
            d.text((x+31,y-17),label,font=font(22),fill=INK)
    return im

def phrase_frame(t,i):
    im=base(); d=ImageDraw.Draw(im)
    # Reference composition: real typeset phrase and two controlled highlighter sweeps.
    f=font(69); x=62; lines=[("Nell’ultimo anno,","la Germania ha perso"),("144mila posti di lavoro","nel settore"),("industriale.","")]
    # Center the three lines with measured typography.
    y0=176
    first="Nell’ultimo anno,"; phrase="la Germania ha perso"
    w1=d.textlength(first+" ",font=f); wp=d.textlength(phrase,font=f)
    full=w1+wp; xx=(W-full)/2
    y=y0
    d.text((xx,y),first,font=f,fill=INK)
    q=ease((t-.45)/.55); d.rectangle((xx+w1-8,y+9,xx+w1-8+int((wp+18)*q),y+80),fill=YELLOW)
    d.text((xx+w1,y),phrase,font=f,fill=INK)
    # Line two intentionally separates the highlighted evidence from its continuation.
    l2a="144mila posti di lavoro"; l2b="nel settore"
    w2=d.textlength(l2a+" "+l2b,font=f); xx2=(W-w2)/2; y2=276; w2a=d.textlength(l2a,font=f)
    q2=ease((t-.17)/.47); d.rectangle((xx2-7,y2+9,xx2-7+int((w2a+20)*q2),y2+80),fill=YELLOW)
    d.text((xx2,y2),l2a,font=f,fill=INK); d.text((xx2+w2a+18,y2),l2b,font=f,fill=INK)
    d.text((W/2,377),"industriale.",font=f,fill=INK,anchor="ma")
    # Small source line resolves in with a simple upward movement.
    a=ease((t-.68)/.22); d.text((65,950+int((1-a)*22)),"GERMANIA  /  INDUSTRIA",font=font(23,REG),fill=(105,108,105))
    return im

VALUES=[81,79,78,77,76,74,71,67]
def chart_frame(name,t,i):
    im=base(); d=ImageDraw.Draw(im)
    d.text((102,78),"L’OCCUPAZIONE INDUSTRIALE TEDESCA",font=font(32,REG),fill=(67,70,68))
    # Counter rolls up continuously instead of appearing as an unrelated static screenshot.
    count=int(144000*ease(t/.65)); d.text((98,122),f"−{count:,}".replace(",","."),font=font(126),fill=INK)
    d.text((104,270),"POSTI DI LAVORO IN UN ANNO",font=font(25,REG),fill=(100,103,100))
    d.line((104,345,465,345),fill=CORAL,width=7)
    left=205; gap=181; base_y=850; maxh=360
    # Each file gets a distinct visual grammar and a separately timed reveal.
    mode=name.removeprefix("data_")
    if mode=="line_trace" or mode=="area_fill_rise":
        pts=[(left+j*gap,base_y-(maxh*v/81)) for j,v in enumerate(VALUES)]
        n=min(len(pts),max(2,int(2+ease((t-.16)/.68)*(len(pts)-1))))
        if mode=="area_fill_rise" and t>.15:
            q=ease((t-.15)/.64)
            overlay=Image.new("RGBA",(W,H),(0,0,0,0)); od=ImageDraw.Draw(overlay)
            od.polygon([(left,base_y),*[(x,int(base_y+(y-base_y)*q)) for x,y in pts[:n]],(pts[n-1][0],base_y)],fill=(242,229,0,100))
            im=Image.alpha_composite(im.convert("RGBA"),overlay).convert("RGB"); d=ImageDraw.Draw(im)
        d.line((120,base_y,left+7*gap,base_y),fill=(190,191,186),width=2)
        d.line(pts[:n],fill=INK,width=8,joint="curve")
        for x,y in pts[:n]: d.ellipse((x-10,y-10,x+10,y+10),fill=CORAL)
    elif mode=="bar_compare_reveal":
        # Split panel for a direct before/after comparison.
        d.text((410,414),"2017",font=font(28,REG),fill=(91,94,91)); d.text((1250,414),"2024",font=font(28,REG),fill=(91,94,91))
        q=ease((t-.18)/.62)
        for x,val,col in [(440,81,YELLOW),(1270,67,CORAL)]:
            h=maxh*val/81*q; d.rounded_rectangle((x,base_y-h,x+210,base_y),radius=10,fill=col)
            d.text((x+105,base_y-h-55),f"{int(val*q)}",font=font(36),fill=INK,anchor="mm")
        d.text((960,640),"−17%",font=font(82),fill=CORAL,anchor="mm")
    elif mode=="grid_assemble":
        q=ease((t-.12)/.68)
        for j in range(6):
            yy=430+j*76; d.line((320,yy,1600,yy),fill=(218,220,216),width=2)
        for j,val in enumerate(VALUES):
            x=320+j*160; y=458+j*36
            a=ease((t-(.13+j*.055))/.22)
            d.rounded_rectangle((x,y,x+95,y+48),radius=8,fill=YELLOW if j!=7 else CORAL)
            d.text((x+47,y+24),str(val),font=font(23),fill=INK,anchor="mm")
    elif mode=="counter_roll":
        q=ease(t/.8); d.text((1040,146),"DAL 2017 AL 2024",font=font(27,REG),fill=CORAL)
        d.text((960,635),f"−{int(144*q):03d}.000",font=font(115),fill=INK,anchor="mm")
        d.text((960,730),"POSTI DI LAVORO",font=font(28,REG),fill=(94,98,95),anchor="mm")
        return im
    elif mode=="peak_callout":
        q=ease((t-.15)/.63)
        for j,val in enumerate(VALUES):
            x=left+j*gap; h=maxh*val/81*q
            d.rounded_rectangle((x-39,base_y-h,x+39,base_y),radius=8,fill=CORAL if j==3 else YELLOW)
        a=ease((t-.55)/.2); d.rounded_rectangle((1225,412,1560,476),radius=28,fill=CORAL)
        d.text((1392,444),"−3,1%",font=font(28),fill="white",anchor="mm")
    elif mode=="chart_focus_pulse":
        q=ease((t-.10)/.6)
        for j,val in enumerate(VALUES):
            x=left+j*gap; h=maxh*val/81*q
            pul=1+.08*math.sin(max(0,t-.6)*math.pi*2) if j==3 and t>.6 else 1
            h*=pul
            d.rounded_rectangle((x-37,base_y-h,x+37,base_y),radius=7,fill=CORAL if j==3 else YELLOW)
        d.ellipse((left+3*gap-91,base_y-maxh*VALUES[3]/81-83,left+3*gap+91,base_y-maxh*VALUES[3]/81+99),outline=CORAL,width=4)
    elif mode=="histogram_wave":
        for j,val in enumerate(VALUES):
            x=left+j*gap; q=ease((t-(.06+j*.045))/.22); h=maxh*val/81*q
            d.rounded_rectangle((x-42,base_y-h,x+42,base_y),radius=8,fill=YELLOW)
    elif mode=="histogram_center_out":
        for j,val in enumerate(VALUES):
            x=left+j*gap; q=ease((t-(.08+abs(j-3.5)*.08))/.24); h=maxh*val/81*q
            d.rounded_rectangle((x-42,base_y-h,x+42,base_y),radius=8,fill=CORAL if j in (3,4) else YELLOW)
    elif mode=="histogram_stagger_up":
        for j,val in enumerate(VALUES):
            x=left+j*gap; q=ease((t-(.08+j*.07))/.24); h=maxh*val/81*q
            d.rounded_rectangle((x-42,base_y-h,x+42,base_y),radius=8,fill=YELLOW)
    else: # data_area_fill_rise or a future recipe
        for j,val in enumerate(VALUES):
            x=left+j*gap; q=ease((t-.12)/.6); h=maxh*val/81*q
            d.rectangle((x-36,base_y-h,x+36,base_y),fill=YELLOW)
    if mode not in ("line_trace","area_fill_rise","bar_compare_reveal","grid_assemble","counter_roll"):
        for j in range(8):
            x=left+j*gap; d.text((x,880),str(2017+j),font=font(18,REG),fill=(105,108,105),anchor="mm")
        for yy in (500,590,680,770,850): d.line((160,yy,1690,yy),fill=(226,227,223),width=1)
    return im

def image_frame(t,i):
    im=base((14,16,17)); photo=Image.open(ASSETS/"refinery_rounded.png").convert("RGBA")
    x0,y0=310,178; cw,ch=1300,730
    # One-sided rounded coral edge follows a real image-card reveal, then a slow Ken Burns move.
    q=ease((t-.10)/.55); width=int(cw*q)
    d=ImageDraw.Draw(im)
    if width>0:
        d.rounded_rectangle((x0+18,y0,x0+cw+18,y0+ch),radius=18,fill=CORAL)
        zoom=1+.035*ease(t); pw=int(cw*zoom); ph=int(ch*zoom)
        moved=photo.resize((pw,ph),Image.Resampling.LANCZOS)
        ox=(pw-cw)//2; oy=(ph-ch)//2
        crop=moved.crop((ox,oy,ox+cw,oy+ch))
        # Clip to the reveal boundary: source photograph, not an animated screenshot.
        crop=crop.crop((0,0,width,ch)); im.paste(crop,(x0,y0),crop)
        # Hide the three non-accent sides with a fine warm keyline.
        ImageDraw.Draw(im).rounded_rectangle((x0,y0,x0+width,y0+ch),radius=17,outline=(234,230,217),width=2)
    return im

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if len(sys.argv)>1 and sys.argv[1]=="--dates-only":
        for ix,style in enumerate(DATE_STYLES,1):
            name="date_"+style
            print(f"[{ix}/{len(DATE_STYLES)}] Date motion: {name}",flush=True)
            encode(name,lambda t,i,s=style:date_style_frame(s,t,i))
        return
    plans=[("date_oil_crisis_stamp",date_frame),("map_middle_east_oil_focus",map_frame),
      ("phrase_yellow_highlighter_sweep",phrase_frame)]
    data_names=["data_histogram_stagger_up","data_histogram_wave","data_histogram_center_out","data_bar_compare_reveal","data_line_trace","data_peak_callout","data_counter_roll","data_grid_assemble","data_area_fill_rise","data_chart_focus_pulse"]
    plans.extend((name,lambda t,i,n=name:chart_frame(n,t,i)) for name in data_names)
    plans.append(("image_one_sided_rounded_accent",image_frame))
    for ix,(name,fn) in enumerate(plans,1):
        print(f"[{ix}/{len(plans)}] Rendering distinct animation with Vulkan-free drawing + NVENC: {name}",flush=True)
        encode(name,fn)
    print(f"Rendered {len(plans)} independent H.264 NVENC clips to {OUT}")
if __name__=="__main__": main()
