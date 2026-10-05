#!/usr/bin/env python3
"""Rebuild the Drive reference styles with separate Chronon text/image layers."""
from __future__ import annotations
import argparse, io, json, shutil, subprocess, sys, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; WORKSPACE=ROOT.parent
sys.path.insert(0,str(ROOT/'tools'))
import build_entity_caption_reference_v3 as base
SRC=ROOT/'out/trump_drive_references'; OUT=ROOT/'out/drive_reference_chronon_v1'; AS=OUT/'assets'; W,H,FPS,N=1920,1080,30,150
FONT_DIR=AS/'fonts'; PLATES=AS/'plates'; PORTRAITS=AS/'portraits'; DETAILS=AS/'details'
INK='#131416'; IVORY='#F2EFE6'; WHITE='#F2F0E9'; RED='#D62620'; GOLD='#B69A62'

def kf(p,pts,e='out_cubic'): return {'property':p,'easing':e,'keyframes':[{'frame':a,'value':b} for a,b in pts]}
def pos(x,y,w,h): return [x+w/2-W/2,H/2-(y+h/2)]
def img_layer(i,asset,x,y,w,h,anim=None,fit='contain',z=True):
    d={'id':f'image-{i}-{len(LAYERS)}','type':'image','asset':str(asset.relative_to(OUT)),'size':[w,h],'fit':fit,'position':pos(x,y,w,h),'start_frame':0,'duration_frames':N,'enable_3d':z}
    if anim:d['animation']={'tracks':anim}
    LAYERS.append(d); return d
def text_layer(i,text,font,size,fill,x,y,w,h,anim=None,tracked=0):
    layer=base.text_layer(f'text-{i}-{len(LAYERS)}',text,(x+w//2,H-(y+h//2)),(w,h),font,size,fill,anim or [],start=0)
    # Keep character animation on the native layer's regular position/opacity
    # tracks; avoiding per-glyph selectors keeps the plan compatible with the
    # current Chronon runtime's selector schema.
    LAYERS.append(layer); return layer

def gradient_plate(idx,top,bottom,accent=None,cream=False):
    im=Image.new('RGB',(W,H)); px=im.load()
    for y in range(H):
        t=y/(H-1); t=t*t*(3-2*t); c=tuple(round(top[k]*(1-t)+bottom[k]*t) for k in range(3))
        for x in range(W): px[x,y]=c
    d=ImageDraw.Draw(im,'RGBA')
    if accent:
        x,y,r=accent; glow=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        gd.ellipse((x-r,y-r,x+r,y+r),fill=(*accent[3],75)); glow=glow.filter(ImageFilter.GaussianBlur(r*.55)); im=Image.alpha_composite(im.convert('RGBA'),glow)
        d=ImageDraw.Draw(im,'RGBA')
    if not cream:
        rng=np.random.default_rng(idx+193); noise=Image.fromarray(rng.integers(0,10,(H,W),dtype=np.uint8),'L').filter(ImageFilter.GaussianBlur(.7))
        overlay=Image.new('RGBA',(W,H),(200,200,200,0)); overlay.putalpha(noise); im=Image.alpha_composite(im.convert('RGBA'),overlay)
    return im.convert('RGBA')

def make_portraits():
    PORTRAITS.mkdir(parents=True,exist_ok=True)
    p=base.grayscale_photo(); p.save(PORTRAITS/'donald_trump_cutout.png',optimize=True)
    # A soft, larger ghost portrait is a separate layer for the two archival blur layouts.
    a=p.getchannel('A'); box=a.getbbox(); cut=p.crop(box)
    cut.thumbnail((950,1050),Image.Resampling.LANCZOS)
    cut=cut.filter(ImageFilter.GaussianBlur(22)); cut.putalpha(cut.getchannel('A').point(lambda v:int(v*.20)))
    cut.save(PORTRAITS/'donald_trump_ghost.png',optimize=True)

def make_scene_photo(idx,refnum):
    src=Image.open(sorted(SRC.glob('*.png'))[refnum-1]).convert('RGB')
    # Crop only the cinematic still inside the card. The headline is authored as Chronon text.
    if refnum==6: crop=src.crop((0,82,1240,780))
    else: crop=src.crop((34,95,1638,708))
    photo=ImageOps.fit(crop,(1760,640),Image.Resampling.LANCZOS,centering=(.5,.5)).convert('RGBA')
    mask=Image.new('L',photo.size,0); ImageDraw.Draw(mask).rounded_rectangle((0,0,photo.width-1,photo.height-1),radius=28,fill=255); photo.putalpha(mask)
    path=AS/'scene_photos'/f'scene_{refnum:02d}.png'; path.parent.mkdir(parents=True,exist_ok=True); photo.save(path,optimize=True); return path

def make_early_plate(num):
    colors={1:((237,233,222),(230,226,216)),3:((238,234,223),(227,223,214)),5:((239,235,224),(228,225,215)),6:((239,235,224),(228,225,215))}
    top,bottom=colors[num]; im=gradient_plate(num,top,bottom,cream=True); d=ImageDraw.Draw(im,'RGBA')
    if num==6: d.line((63,824,63,1008),fill=(25,25,24,95),width=3)
    else: d.line((45,804,45,1006),fill=(25,25,24,95),width=3)
    return save_plate(num,im)

def save_plate(i,im):
    PLATES.mkdir(parents=True,exist_ok=True); p=PLATES/f'background_{i:02d}.png'; im.save(p,optimize=True); return p

# Trump group: 22 reference-specific compositions. Positions are screen-pixel boxes.
TRUMP=[
# bg top/bottom, portrait box, text lines, font, size, color, portrait card, special
((8,9,12),(20,21,23),(1290,155,520,770),('DONALD TRUMP',), 'Instrument-Sans.ttf',58,WHITE,1,'rule'),
((16,12,9),(8,9,11),(250,170,470,750),('DONALD TRUMP',),'PlayfairDisplay-Italic.ttf',76,WHITE,1,'amber'),
((247,245,239),(239,236,228),(1130,125,620,830),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',120,INK,1,'goldline'),
((8,9,11),(11,12,14),(180,225,390,650),('DONALD TRUMP',),'Instrument-Sans.ttf',61,WHITE,1,'ghost_right'),
((249,247,240),(244,241,233),(1220,115,600,820),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',122,INK,0,'cream_gold'),
((7,8,10),(17,18,20),(700,220,520,600),('DONALD TRUMP',),'Instrument-Sans.ttf',54,WHITE,1,'center_top'),
((7,18,34),(10,23,42),(1280,150,520,790),('DONALD TRUMP',),'Instrument-Sans.ttf',57,WHITE,1,'navy'),
((10,10,11),(18,18,18),(170,190,450,700),('DONALD TRUMP',),'Instrument-Sans.ttf',60,WHITE,1,'ghost_right'),
((248,246,239),(238,235,227),(160,130,600,830),('DONALD','TRUMP'),'PlayfairDisplay-Italic.ttf',105,INK,1,'goldline'),
((248,246,239),(240,237,230),(135,120,570,850),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',110,INK,1,'softgold'),
((9,8,10),(15,9,14),(150,150,520,800),('DONALD','TRUMP'),'DMSans-Bold.ttf',108,'#F0ECE7',1,'redglow'),
((250,249,246),(238,236,230),(130,120,640,850),('DONALD TRUMP',),'DMSans-Bold.ttf',68,INK,1,'thinrule'),
((8,10,13),(14,15,17),(175,105,900,970),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',132,WHITE,0,'toprule'),
((5,7,8),(9,10,12),(720,270,490,570),('DONALD','TRUMP'),'PlayfairDisplay-Italic.ttf',89,WHITE,1,'vertical'),
((7,9,12),(13,14,16),(120,155,630,790),('DONALD TRUMP',),'Instrument-Sans.ttf',59,WHITE,1,'ghost_right'),
((247,246,241),(236,234,227),(120,125,590,840),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',109,INK,1,'goldline'),
((8,9,11),(13,14,16),(120,105,635,870),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',125,WHITE,1,'reflection'),
((6,12,13),(10,17,18),(1250,125,560,830),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',126,WHITE,1,'metadata'),
((7,9,11),(12,13,15),(1290,140,520,800),('DONALD TRUMP',),'Instrument-Sans.ttf',58,WHITE,1,'quiet'),
((7,9,11),(13,15,18),(110,135,630,830),('DONALD','TRUMP'),'DMSans-Bold.ttf',120,WHITE,0,'bright_type'),
((6,7,9),(12,13,16),(710,205,500,610),('DONALD','TRUMP'),'Bodoni72-BookItalic.ttf',106,WHITE,1,'centered'),
((7,8,10),(13,15,18),(115,130,710,850),('DONALD TRUMP',),'Instrument-Sans.ttf',55,WHITE,1,'leftclose'),
]

# These modes animate photo, headline and finish separately in every five-second clip.
def photo_tracks(i):
    mods=[[("position_x",[(0,72),(30,0)]),("scale",[(0,.94),(40,1),(149,1.025)]),("opacity",[(0,0),(13,1)])],
          [("position_y",[(0,45),(32,0)]),("scale",[(0,.91),(35,1),(149,1.02)]),("opacity",[(0,0),(12,1)])],
          [("scale",[(0,.82),(34,1.02),(46,1),(149,1.018)]),("opacity",[(0,0),(14,1)])],
          [("position_x",[(0,-66),(27,0)]),("rotation_z",[(0,-2),(29,0)]),("opacity",[(0,0),(13,1)])],
          [("position_y",[(0,-56),(28,0)]),("scale",[(0,1.06),(32,1),(149,1.018)]),("opacity",[(0,0),(13,1)])]]
    return [kf(p,pts) for p,pts in mods[i%len(mods)]]
def title_tracks(i):
    mods=[[("position_x",[(0,55),(32,0)]),("opacity",[(0,0),(16,1)])],
          [("position_y",[(0,34),(31,0)]),("opacity",[(0,0),(14,1)])],
          [("scale",[(0,.86),(32,1)]),("opacity",[(0,0),(13,1)])],
          [("position_x",[(0,-52),(30,0)]),("opacity",[(0,0),(14,1)])],
          [("position_y",[(0,-28),(29,0)]),("opacity",[(0,0),(12,1)])]]
    return [kf(p,pts) for p,pts in mods[i%len(mods)]]

def build_trump_style(index, spec):
    top,bottom,box,lines,font,size,color,card,special=spec; i=index+8
    im=gradient_plate(i,top,bottom); d=ImageDraw.Draw(im,'RGBA')
    # Ambient editorial lights and thin rules, with one visual cue per reference.
    if special in ('amber','redglow'):
        glow=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        gc=(229,153,76) if special=='amber' else (213,24,38)
        gd.ellipse((-220,-180,700,760),fill=(*gc,88)); glow=glow.filter(ImageFilter.GaussianBlur(145)); im=Image.alpha_composite(im,glow); d=ImageDraw.Draw(im,'RGBA')
    if special in ('rule','toprule','thinrule','goldline','goldline','navy','quiet','metadata'):
        col=(194,164,105,120) if special in ('goldline','metadata') else (230,229,222,75)
        d.line((90,83,1830,83),fill=col,width=2)
    x,y,pw,ph=box
    if card:
        rad=26 if special in ('softgold','vertical','centered') else 8
        # soft inset plus hairline frame under the separate portrait layer
        d.rounded_rectangle((x-18,y-18,x+pw+18,y+ph+18),radius=rad,fill=(240,238,231,18),outline=(242,238,226,95),width=2)
        d.rounded_rectangle((x-10,y-10,x+pw+10,y+ph+10),radius=max(4,rad-5),outline=(255,255,255,24),width=1)
    if special in ('goldline','softgold'):
        # Place the brass accent beneath the full two-line title and keep it
        # inside the same negative-space column as the headline.
        if x+pw/2 < W/2: accent_box=(x+pw+72,700,W-80,704)
        else: accent_box=(80,700,x-72,704)
        d.rectangle(accent_box,fill=(188,151,72,190))
    if special=='redglow':
        d.rounded_rectangle((x-22,y-20,x+pw+22,y+ph+20),radius=10,outline=(207,32,39,230),width=3)
        d.line((960,760,1740,760),fill=(228,31,39,220),width=5)
    if special=='reflection':
        d.line((100,748,1820,748),fill=(230,226,217,85),width=2)
        for k in range(8): d.line((210+k*215,758,140+k*215,1055),fill=(210,206,196,14),width=1)
    if special=='metadata':
        d.text((102,98),'ARCHIVE STUDY  •  47',fill=(206,194,164,150))
        d.line((95,990,1825,990),fill=(222,221,211,65),width=1)
    if special=='toprule': d.line((98,150,1822,150),fill=(228,226,219,100),width=2)
    if special=='vertical': d.line((960,120,960,965),fill=(238,235,228,55),width=2)
    plate=save_plate(i,im)
    LAYERS.clear(); LAYERS.append({'id':f'background-{i:02d}','type':'image','asset':str(plate.relative_to(OUT)),'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':N})
    if special=='ghost_right':
        g=PORTRAITS/'donald_trump_ghost.png'; img_layer(i,g,930,10,960,1080,[kf('scale',[(0,1.0),(149,1.035)]),kf('opacity',[(0,.2),(30,.34)])],fit='contain',z=False)
    portrait=PORTRAITS/'donald_trump_cutout.png'; img_layer(i,portrait,*box,photo_tracks(index),fit='contain')
    # A small typographic detail is authored as separate text, never baked into the plate.
    if special=='metadata': text_layer(i,'ARCHIVE  /  47','Instrument-Sans.ttf',20,'#C9C0AA',98,100,360,40,[kf('opacity',[(0,0),(20,.8)])])
    if special in ('center_top','centered'):
        text_layer(i,'DONALD','Instrument-Sans.ttf',48,WHITE,690,94,540,82,title_tracks(index),tracked=17)
        text_layer(i,'TRUMP',font,size,WHITE,710,820,500,130,title_tracks(index+1),tracked=6)
    elif len(lines)==2:
        text='\n'.join(lines)
        # Target text sits opposite the portrait, or centered under it for cover compositions.
        if special in ('reflection','toprule','centered'):
            tx,ty,tw,th=960,520,900,380
        elif special=='vertical': tx,ty,tw,th=(960 if x<960 else 470),540,820,350
        elif special=='goldline': tx,ty,tw,th=560,480,830,350
        elif special=='softgold': tx,ty,tw,th=650,520,820,350
        elif special=='metadata': tx,ty,tw,th=510,520,780,360
        elif special=='redglow': tx,ty,tw,th=1390,535,900,340
        elif special=='bright_type': tx,ty,tw,th=570,530,900,360
        else: tx,ty,tw,th=(1390 if x<960 else 530),535,900,350
        # Keep the headline in the clear negative space beside the portrait.
        # Several art directions intentionally start with centered coordinates,
        # but those collide with left or right portraits at the final frame.
        if special not in ('vertical','centered') and tx-tw/2 < x+pw and tx+tw/2 > x:
            gap,margin=72,80
            if x+pw/2 < W/2:
                left=x+pw+gap; right=W-margin
            else:
                left=margin; right=x-gap
            tw=max(1,min(tw,right-left)); tx=(left+right)/2
        text_layer(i,text,font,size,color,tx-tw//2,ty-th//2,tw,th,title_tracks(index),tracked=9 if special in ('toprule','quiet') else 0)
    else:
        # One-line titles occupy the negative-space side of the composition.
        tx=510 if x>960 else 1370; ty=520
        if special=='vertical': tx=960
        if special=='quiet': tx=520
        if special=='leftclose': tx=1360
        tw=900 if tx>960 else 880
        text_layer(i,lines[0],font,size,color,tx-tw//2,ty-105,tw,210,title_tracks(index),tracked=18 if special in ('rule','navy','quiet','leftclose') else 0)
    plan={'schema':'chronon.render-plan.v3','version':3,'job_id':f'drive_reference_{i:02d}_native',
      'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':N},'layers':list(LAYERS),
      'output':{'path':f'{i:02d}_trump_style.mp4','format':'mp4','codec':'h264'}}
    return plan

LAYERS=[]
def build_early(index,refnum,title):
    LAYERS.clear(); bg=make_early_plate(index); LAYERS.append({'id':f'editorial-board-{index}','type':'image','asset':str(bg.relative_to(OUT)),'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':N})
    photo=make_scene_photo(index,refnum)
    if index==6: px,py,pw,ph=320,76,1280,720
    else: px,py,pw,ph=40,100,1840,700
    LAYERS.append({'id':f'photo-{index}','type':'image','asset':str(photo.relative_to(OUT)),'size':[pw,ph],'fit':'cover','position':pos(px,py,pw,ph),'start_frame':0,'duration_frames':N,'enable_3d':True,'animation':{'tracks':photo_tracks(index)}})
    anim=title_tracks(index)
    text_layer(index,title,'DMSans-Bold.ttf',138,INK,0,840,850,190,anim)
    plan={'schema':'chronon.render-plan.v3','version':3,'job_id':f'drive_reference_{index:02d}_native',
      'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':N},'layers':list(LAYERS),
      'output':{'path':f'{index:02d}_{title.lower()}_native.mp4','format':'mp4','codec':'h264'}}
    return plan

def make_phrase_bg(refnum,index):
    if refnum==7:
        # The source is a narrow screenshot of text only, so it cannot serve
        # as a clean photographic plate. Build a restrained cinematic backdrop.
        im=gradient_plate(index,(20,21,25),(5,7,10))
        glow=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
        gd.ellipse((880,220,1900,1040),fill=(92,68,45,46))
        im=Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(170)))
        p=save_plate(index,im); return p
    src=Image.open(sorted(SRC.glob('*.png'))[refnum-1]).convert('RGB')
    if refnum in (2,4):
        import cv2
        rgb=np.asarray(src); bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR); gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
        mask=np.zeros(gray.shape,dtype=np.uint8); band=gray[330:560,:]
        bright=(band>176).astype(np.uint8)*255
        red=((rgb[330:560,:,0]>125)&(rgb[330:560,:,1]<90)).astype(np.uint8)*255
        m=np.maximum(bright,red); m=cv2.dilate(m,np.ones((9,9),np.uint8),iterations=1); mask[330:560,:]=m
        bgr=cv2.inpaint(bgr,mask,19,cv2.INPAINT_TELEA); src=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
    bg=ImageOps.fit(src,(W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(27))
    bg=ImageEnhance.Brightness(bg).enhance(.48)
    d=ImageDraw.Draw(bg,'RGBA'); d.rectangle((0,0,W,H),fill=(5,6,8,60))
    p=save_plate(index,bg.convert('RGBA')); return p

def build_phrase(index,refnum,text,small=False):
    LAYERS.clear(); bg=make_phrase_bg(refnum,index); LAYERS.append({'id':f'cinema-background-{index}','type':'image','asset':str(bg.relative_to(OUT)),'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':N,'animation':{'tracks':[kf('scale',[(0,1.03),(149,1.0)],'in_out_sine')]}})
    font='PlayfairDisplay-Italic.ttf'; fs=52 if small else 68
    # A full-frame text box gives Chronon's native text layout a stable visual
    # center for these long italic lines (a narrow box clips the glyphs at the
    # top edge in the current runtime).
    tx,ty,tw,th=(960,540,W,H)
    # Transform tracks are offsets from the layer's authored position.
    anim=[kf('position_y',[(0,24),(34,0)]),kf('opacity',[(0,0),(16,1)])]
    layer=base.text_layer(f'text-{index}-{len(LAYERS)}',text,(tx,ty),(tw,th),font,fs,'#F7F2E8',anim,start=0)
    LAYERS.append(layer)
    # Animated red underline, centered under the rendered phrase. Keep it a
    # crisp editorial rule rather than a rounded brush stroke.
    line=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(line)
    if index==2: box=(430,600,1490,604)
    elif index==4: box=(645,600,1274,604)
    else: box=(1110,592,1730,596)
    d.rectangle(box,fill=(211,33,31,235))
    lp=DETAILS/f'accent_{index:02d}.png'; DETAILS.mkdir(parents=True,exist_ok=True); line.save(lp,optimize=True)
    LAYERS.append({'id':f'accent-{index}','type':'image','asset':str(lp.relative_to(OUT)),'size':[W,H],'fit':'contain','position':[0,0],'start_frame':0,'duration_frames':N,'animation':{'tracks':[kf('scale_x',[(0,.05),(38,1)]),kf('opacity',[(0,0),(20,1)])]}})
    plan={'schema':'chronon.render-plan.v3','version':3,'job_id':f'drive_reference_{index:02d}_native',
      'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':N},'layers':list(LAYERS),
      'output':{'path':f'{index:02d}_phrase_native.mp4','format':'mp4','codec':'h264'}}
    return plan

def render_clip(plan,index,skip=True):
    slug=plan['output']['path']; out=OUT/'individual_mp4'/slug; out.parent.mkdir(parents=True,exist_ok=True)
    if skip and out.exists(): return out
    pp=OUT/'plans'/f'{index:02d}.plan.json'; pp.parent.mkdir(parents=True,exist_ok=True); pp.write_text(json.dumps(plan,indent=2)+'\n')
    raw=OUT/f'{index:02d}.nv12'; log=OUT/'logs'/f'{index:02d}.log'; log.parent.mkdir(parents=True,exist_ok=True)
    cmd=[str(base.CLI),'render','--plan',str(pp),'--assets-root',str(OUT),'--backend','vulkan','--profile','preview','--fps',str(FPS),
      '--video-sink','raw','--pipe-pixfmt','nv12','--chunks','1','--fb-pool-budget-mb','512','--fb-pool-clear-policy','trim-after-job',
      '--start-frame','0','--end-frame',str(N-1),'-o',str(raw)]
    with log.open('w') as f: subprocess.run(cmd,cwd=WORKSPACE,stdout=f,stderr=subprocess.STDOUT,check=True)
    expected=N*W*H*3//2
    if raw.stat().st_size!=expected: raise RuntimeError(f'{index:02d}: NV12 size {raw.stat().st_size}, expected {expected}')
    subprocess.run(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','nv12','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i',str(raw),'-frames:v',str(N),'-an','-c:v','h264_nvenc','-preset','p4','-cq','18','-b:v','0','-pix_fmt','yuv420p','-r',str(FPS),'-video_track_timescale','30000',str(out)],cwd=WORKSPACE,check=True)
    raw.unlink()
    meta=subprocess.run(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate:format=duration','-of','json',str(out)],capture_output=True,text=True,check=True)
    d=json.loads(meta.stdout); s=d['streams'][0]; duration=float(d['format']['duration'])
    if (s['width'],s['height'],s['r_frame_rate'])!=(W,H,'30/1') or abs(duration-5)>.04: raise RuntimeError(f'{out.name} spec mismatch: {d}')
    print(f'VERIFIED {out.name} 1920x1080 30fps {duration:.3f}s',flush=True); return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--only',type=int,nargs='+'); ap.add_argument('--no-render',action='store_true'); ap.add_argument('--force',action='store_true'); a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True); make_portraits()
    for x in ('Bodoni72-BookItalic.ttf','Bricolage-Grotesque.ttf','DMSans-Bold.ttf','Instrument-Sans.ttf','PlayfairDisplay-Italic.ttf','Manrope.ttf','Montserrat-Bold.ttf'):
        (FONT_DIR).mkdir(parents=True,exist_ok=True); shutil.copy2(base.ASSETS if hasattr(base,'ASSETS') else base.ASSET_ROOT/'assets/fonts'/x,FONT_DIR/x)
    refs=sorted(SRC.glob('*.png'))
    manifest=[]
    for i in range(1,30):
        if a.only and i not in a.only: continue
        if i in (1,3,5,6):
            title={1:'SVOLTA',3:'DISCIPLINA',5:'VISIONE',6:'VISIONE'}[i]; plan=build_early(i,i,title)
        elif i==2: plan=build_phrase(i,i,'anche 3.000€ al mese non bastavano')
        elif i==4: plan=build_phrase(i,i,'continuava a crederci')
        elif i==7: plan=build_phrase(i,i,'nonostante guadagni 3.000€ al mese',small=True)
        else: plan=build_trump_style(i-8,TRUMP[i-8])
        pp=OUT/'plans'/f'{i:02d}.plan.json'; pp.parent.mkdir(parents=True,exist_ok=True); pp.write_text(json.dumps(plan,indent=2)+'\n')
        manifest.append({'index':i,'reference':refs[i-1].name,'plan':str(pp.relative_to(OUT)),'mp4':plan['output']['path'],'layers':len(plan['layers']),'duration_seconds':5,'width':W,'height':H,'fps':FPS})
        if not a.no_render: render_clip(plan,i,skip=not a.force)
    if not a.only:
        (OUT/'manifest.json').write_text(json.dumps({'schema':'chronontemplate.drive-reference-native.v1','count':29,'note':'Type, portrait and animation are separate Chronon layers; supplied images are style references, not rendered video plates.','clips':manifest},indent=2)+'\n')
if __name__=='__main__': main()
