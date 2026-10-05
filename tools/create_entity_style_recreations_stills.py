#!/usr/bin/env python3
"""Build 13 clean white/black still recreations from the downloaded references."""
from pathlib import Path
import json, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out/entity_style_recreations_v1'
REF=ROOT/'out/entity_caption_apple_v1/source_references'
PORTRAIT=ROOT/'out/entity_caption_reference_v3/assets/portraits/donald-trump-apple.png'
FONT=ROOT/'out/entity_caption_reference_v3/assets/fonts/Bricolage-Grotesque.ttf'
W,H=1920,1080
NAMES=['Editorial Pair','Mirrored Minimal','Big Type','Centered Portrait','Portrait Close Up','Name Bracket','Type First','Gallery Frame','Corner Portrait','Vertical Balance','Soft Card','Ink Outline','Editorial Rule']

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    portrait=Image.open(PORTRAIT).convert('RGBA'); bbox=portrait.getchannel('A').getbbox(); portrait=portrait.crop(bbox)
    made=[]
    for i,name in enumerate(NAMES):
        im=Image.new('RGBA',(W,H),(255,255,255,255)); d=ImageDraw.Draw(im,'RGBA')
        side='right' if i in (1,2,6,11) else 'left'
        if i in (3,5): side='center'
        # Match broad composition families while keeping the same monochrome system.
        if i in (3,5): box=(650,105,1270,830); px,py,pw,ph=(650,105,620,725); tx,ty,tw,th=(380,875,1160,150)
        elif i==2: box=(1270,118,1790,942); px,py,pw,ph=(1270,118,520,824); tx,ty,tw,th=(90,340,1040,310)
        elif i==6: box=(1320,130,1790,930); px,py,pw,ph=(1320,130,470,800); tx,ty,tw,th=(70,350,1150,340)
        elif i==8: box=(110,100,510,575); px,py,pw,ph=(110,100,400,475); tx,ty,tw,th=((1020 if side=='left' else 90),610,800,300)
        elif i==9: box=(110,82,820,998); px,py,pw,ph=(110,82,710,916); tx,ty,tw,th=(930,270,850,320)
        elif i==4: box=(95,75,935,1005); px,py,pw,ph=(95,75,840,930); tx,ty,tw,th=(1115,475,700,190)
        else:
            px,py,pw,ph=((115 if side=='left' else 1325),92,480,896)
            tx,ty,tw,th=((755 if side=='left' else 80),420,1050,240)
            box=(px-22,py-16,px+pw+22,py+ph+16)
        if i in (0,7,10): d.rounded_rectangle(box,radius=28 if i!=7 else 10,outline=(24,25,27,44),width=2)
        elif i in (1,11): d.line((1090,140,1090,940),fill=(24,25,27,35),width=2)
        elif i==5: d.line((575,860,1345,860),fill=(24,25,27,75),width=2)
        elif i==12: d.line((110,940,1810,940),fill=(24,25,27,70),width=2)
        if i==10: d.rounded_rectangle(box,radius=34,fill=(250,250,250,255),outline=(24,25,27,28),width=2)
        shot=ImageOps.contain(portrait,(pw,ph),Image.Resampling.LANCZOS)
        im.alpha_composite(shot,(px+(pw-shot.width)//2,py+(ph-shot.height)))
        # Keep the chosen Bricolage face throughout; hierarchy comes from size and line break.
        fs=112 if i in (2,6,8,9) else 84 if i in (0,1,4,7,10,11,12) else 90
        if i in (2,6,9): text='DONALD\nTRUMP'
        elif i==5: text='DONALD TRUMP'
        else: text='DONALD TRUMP'
        font=ImageFont.truetype(str(FONT),fs)
        anchor='mm'
        # A narrow spacing treatment on the minimal first two studies, still native image text only.
        if i in (0,1):
            chars=list(text); widths=[d.textlength(c,font=font) for c in chars]; x=tx+(tw-(sum(widths)+10*(len(chars)-1)))//2
            yy=ty+(th-font.size)//2
            for c,cw in zip(chars,widths): d.text((x,yy),c,font=font,fill=(23,24,25,255)); x+=cw+10
        else:
            d.multiline_text((tx+tw//2,ty+th//2),text,font=font,fill=(23,24,25,255),anchor=anchor,align='center',spacing=2,stroke_width=0)
        fn=f'entity_style_{i+1:02d}_{NAMES[i].lower().replace(" ","_")}.png'
        path=OUT/fn; im.convert('RGB').save(path,optimize=True)
        made.append({'index':i+1,'name':NAMES[i],'caption':'DONALD TRUMP','font':'Bricolage Grotesque','text_color':'#171819','background':'#FFFFFF','image_side':side,'asset':fn})
    manifest=OUT/'entity_style_recreations_v1_manifest.json'
    manifest.write_text(json.dumps({'count':len(made),'side_options':['left','right'],'styles':made},indent=2)+'\n')
    sheet=Image.new('RGB',(1940,5*570+90),(250,250,249)); d=ImageDraw.Draw(sheet); label=ImageFont.truetype(str(FONT),22)
    d.text((24,16),'DONALD TRUMP · 13 CLEAN STYLE RECREATIONS',font=label,fill=(25,26,28))
    for i,m in enumerate(made):
        im=Image.open(OUT/m['asset']).resize((940,528),Image.Resampling.LANCZOS)
        x=20+(i%2)*960; y=58+(i//2)*570; sheet.paste(im,(x,y)); d.text((x+8,y+534),f"{i+1:02d}  {m['name'].upper()}",font=label,fill=(35,36,38))
    sp=OUT/'entity_style_recreations_v1_contact_sheet.png'; sheet.save(sp,optimize=True)
    zp=OUT/'entity_style_recreations_v1_assets.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.glob('entity_style_*.png')): z.write(p,p.name)
        z.write(manifest,manifest.name)
    print('CREATED',len(made),'stills',sp,zp)

if __name__=='__main__': main()
