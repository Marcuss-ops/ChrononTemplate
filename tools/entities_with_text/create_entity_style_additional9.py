#!/usr/bin/env python3
"""Recreate the nine newly added Drive references in the agreed clean style."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import json,zipfile

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'out/entity_style_recreations_v1'
PORTRAIT=ROOT/'out/entity_caption_reference_v3/assets/portraits/donald-trump-apple.png'
FONT=ROOT/'out/entity_caption_reference_v3/assets/fonts/Bricolage-Grotesque.ttf'; W,H=1920,1080
NAMES=['Soft Card Portrait','Archive Blur Simplified','Mirrored Name Lock','Centered Signature','Classic Split','Editorial Glow Removed','Portrait and Baseline','White Editorial Stack','Quiet Frame']

def main():
    portrait=Image.open(PORTRAIT).convert('RGBA'); portrait=portrait.crop(portrait.getchannel('A').getbbox())
    made=[]
    for j,name in enumerate(NAMES):
        i=j+14; im=Image.new('RGBA',(W,H),'white'); d=ImageDraw.Draw(im,'RGBA')
        if j in (0,6): px,py,pw,ph=120,100,620,880; tx,ty,tw,th=760,540,1050,220
        elif j==1: px,py,pw,ph=135,180,600,720; tx,ty,tw,th=770,540,1010,200
        elif j==2: px,py,pw,ph=1305,100,500,880; tx,ty,tw,th=95,540,1050,220
        elif j==3: px,py,pw,ph=680,105,560,740; tx,ty,tw,th=960,890,1020,150
        elif j==4: px,py,pw,ph=1330,100,500,880; tx,ty,tw,th=590,540,1100,300
        elif j==5: px,py,pw,ph=125,150,560,800; tx,ty,tw,th=760,540,1000,220
        elif j==7: px,py,pw,ph=115,100,520,880; tx,ty,tw,th=760,540,1050,300
        else: px,py,pw,ph=1320,90,500,900; tx,ty,tw,th=95,540,1050,220
        box=(px-20,py-18,px+pw+20,py+ph+18)
        if j in (0,3,5,7): d.rounded_rectangle(box,radius=26 if j in (0,7) else 8,outline=(24,25,27,38),width=2)
        if j in (2,6):
            rx=1090 if px>W//2 else 815
            d.line((rx,160,rx,920),fill=(24,25,27,36),width=2)
        if j==4: d.line((tx+90,ty+220,tx+tw-90,ty+220),fill=(24,25,27,60),width=2)
        shot=ImageOps.contain(portrait,(pw,ph),Image.Resampling.LANCZOS)
        im.alpha_composite(shot,(px+(pw-shot.width)//2,py+ph-shot.height))
        stacked=j in (4,7); fs=88 if j in (0,1,2,5,6,8) else 104
        f=ImageFont.truetype(str(FONT),fs); txt='DONALD\nTRUMP' if stacked else 'DONALD TRUMP'
        d.multiline_text((tx+tw//2,ty+th//2),txt,font=f,fill=(23,24,25,255),anchor='mm',align='center',spacing=0)
        fn=f'entity_style_{i:02d}_{name.lower().replace(" ","_")}.png'; im.convert('RGB').save(OUT/fn,optimize=True)
        made.append({'index':i,'name':name,'caption':'DONALD TRUMP','font':'Bricolage Grotesque','text_color':'#171819','background':'#FFFFFF','image_side':'left' if px<W//2 else 'right','asset':fn})
    # Read and extend the original manifest.
    mp=OUT/'entity_style_recreations_v1_manifest.json'; data=json.loads(mp.read_text()); data['styles']=data['styles'][:13]+made; data['count']=22; mp.write_text(json.dumps(data,indent=2)+'\n')
    fp=ImageFont.truetype(str(FONT),22)
    # High-resolution master contact sheet for browsing all individual PNGs.
    sheet=Image.new('RGB',(1940,11*570+90),(250,250,249)); d=ImageDraw.Draw(sheet); d.text((24,16),'DONALD TRUMP · 22 CLEAN STYLE RECREATIONS',font=fp,fill=(25,26,28))
    all_styles=data['styles']
    for k,m in enumerate(all_styles):
        tile=Image.open(OUT/m['asset']).convert('RGB').resize((940,528),Image.Resampling.LANCZOS)
        x=20+(k%2)*960; y=58+(k//2)*570; sheet.paste(tile,(x,y)); d.text((x+8,y+534),f"{k+1:02d}  {m['name'].upper()}",font=fp,fill=(35,36,38))
    sheet.save(OUT/'entity_style_recreations_v2_contact_sheet.png',optimize=True)
    # Six landscape pages keep each 16:9 still large and undistorted in the GPU review video.
    for pg in range(6):
        page=Image.new('RGB',(1920,1080),(250,250,249)); pd=ImageDraw.Draw(page)
        pd.text((32,18),f'DONALD TRUMP · CLEAN STYLE STUDIES · {pg+1}/6',font=fp,fill=(25,26,28))
        subset=all_styles[pg*4:(pg+1)*4]
        for n,m in enumerate(subset):
            src=Image.open(OUT/m['asset']).convert('RGB')
            tile=ImageOps.contain(src,(890,486),Image.Resampling.LANCZOS)
            x=30+(n%2)*960+(890-tile.width)//2; y=54+(n//2)*515+(486-tile.height)//2
            page.paste(tile,(x,y)); pd.text((30+(n%2)*960+12, y+tile.height+3),f"{m['index']:02d}  {m['name'].upper()}",font=ImageFont.truetype(str(FONT),16),fill=(38,39,41))
        page.save(OUT/f'entity_style_recreations_v2_page_{pg+1:02d}.png',optimize=True)
    zp=OUT/'entity_style_recreations_v2_assets.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
        for m in all_styles: z.write(OUT/m['asset'],m['asset'])
        z.write(mp,mp.name); z.write(OUT/'entity_style_recreations_v2_contact_sheet.png','entity_style_recreations_v2_contact_sheet.png')
    print('CREATED_TOTAL',len(all_styles),'STILLS_AND_6_PAGES')

if __name__=='__main__':main()
