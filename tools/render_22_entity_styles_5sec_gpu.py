#!/usr/bin/env python3
"""Render palette-varied five-second portrait/name animations on Vulkan GPU."""
from __future__ import annotations
import json,shutil,subprocess,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; WORKSPACE=ROOT.parent; OUT=ROOT/'out/entity_style_recreations_v1'
sys.path.insert(0,str(ROOT/'tools'))
import build_entity_caption_reference_v3 as base
W,H,FPS,FRAMES=1920,1080,30,150
ASSETS=OUT/'assets'; FONT='Bricolage-Grotesque.ttf'

# (slug, label, photo center x/y/width/height, caption center x/y/width/height, stacked)
STYLES=[
 ('editorial_pair','Editorial Pair',(450,540,600,850),(1380,540,930,190),0),
 ('mirrored_minimal','Mirrored Minimal',(1470,540,590,830),(540,540,960,190),0),
 ('big_type','Big Type',(1450,540,570,790),(500,540,970,300),1),
 ('centered_portrait','Centered Portrait',(565,520,580,820),(1390,535,940,220),0),
 ('portrait_close_up','Portrait Close Up',(415,540,740,930),(1370,540,980,190),0),
 ('name_bracket','Name Bracket',(960,445,500,650),(960,790,1120,170),0),
 ('type_first','Type First',(1460,540,600,820),(495,540,930,300),1),
 ('gallery_frame','Gallery Frame',(455,540,640,850),(1380,530,940,190),0),
 ('vertical_balance','Vertical Balance',(455,560,680,900),(1370,350,930,300),1),
 ('soft_card','Soft Card',(440,540,680,890),(1380,540,960,190),0),
 ('ink_outline','Ink Outline',(1470,540,610,850),(535,540,970,190),0),
 ('editorial_rule','Editorial Rule',(445,540,600,830),(1380,535,960,190),0),
 ('soft_card_portrait','Soft Card Portrait',(450,540,610,850),(1370,540,960,190),0),
 ('archive_blur_simplified','Archive Blur Simplified',(430,540,650,840),(1370,540,980,190),0),
 ('mirrored_name_lock','Mirrored Name Lock',(1470,540,590,830),(535,540,960,190),0),
 ('centered_signature','Centered Signature',(960,425,550,720),(960,790,1120,170),0),
 ('classic_split','Classic Split',(1470,540,600,850),(500,540,980,300),1),
 ('editorial_glow_removed','Editorial Glow Removed',(445,540,630,830),(1380,540,960,190),0),
 ('portrait_and_baseline','Portrait and Baseline',(430,540,640,870),(1380,560,960,180),0),
 ('white_editorial_stack','White Editorial Stack',(430,540,560,820),(1380,540,960,300),1),
 ('quiet_frame','Quiet Frame',(1470,540,590,840),(525,540,990,190),0),
]

PALETTES=[
 ((10,12,16),(32,37,46),(242,239,230),(212,169,91)),
 ((8,19,39),(19,43,77),(248,246,239),(111,167,221)),
 ((63,28,9),(177,77,18),(255,239,206),(255,187,86)),
 ((242,238,225),(255,252,243),(29,31,34),(177,129,62)),
 ((31,9,16),(111,20,33),(255,242,228),(231,64,62)),
 ((8,34,35),(18,91,86),(237,249,241),(101,209,183)),
 ((28,34,44),(83,94,111),(248,246,240),(189,198,210)),
 ((250,250,248),(255,255,255),(21,25,32),(190,40,40)),
]

def track(prop,points,easing='out_cubic'):
 return {'property':prop,'easing':easing,'keyframes':[{'frame':f,'value':v} for f,v in points]}

def photo_motion(i,side):
 d=-1 if side=='left' else 1
 modes=[
  [track('position_y',[(0,55),(28,0)]),track('scale',[(0,.93),(38,1)]),track('opacity',[(0,0),(14,1)])],
  [track('position_x',[(0,70*d),(30,0)]),track('opacity',[(0,0),(12,1)])],
  [track('scale',[(0,.82),(32,1.015),(46,1)],'out_back'),track('opacity',[(0,0),(14,1)])],
  [track('rotation_z',[(0,-4*d),(30,0)]),track('scale',[(0,.96),(32,1)]),track('opacity',[(0,0),(12,1)])],
  [track('position_y',[(0,80),(34,0)]),track('scale',[(0,1.05),(34,1)]),track('opacity',[(0,.15),(13,1)])],
  [track('position_x',[(0,-60*d),(26,0)]),track('scale',[(0,.96),(32,1)]),track('opacity',[(0,0),(12,1)])],
  [track('rotation_z',[(0,3*d),(28,0)]),track('position_y',[(0,42),(28,0)]),track('opacity',[(0,0),(12,1)])],
  [track('scale',[(0,1.10),(34,1)],'out_cubic'),track('opacity',[(0,.18),(11,1)])],
 ]
 # End with a barely visible continuous camera drift so each five-second file
 # remains a motion clip after the entrance settles.
 chosen=[dict(x) for x in modes[i%len(modes)]]
 scale_track=next((x for x in chosen if x['property']=='scale'),None)
 if scale_track:
  scale_track['keyframes'].append({'frame':149,'value':1.018})
 else:
  chosen.append(track('scale',[(40,1.0),(149,1.018)],'in_out_sine'))
 return chosen

def caption_motion(i,side):
 d=1 if side=='left' else -1
 patterns=[
  [track('position_x',[(0,48*d),(28,0)]),track('opacity',[(0,0),(15,1)])],
  [track('position_y',[(0,40),(28,0)]),track('opacity',[(0,0),(13,1)])],
  [track('scale',[(0,.9),(27,1)]),track('opacity',[(0,0),(13,1)])],
  [track('position_y',[(0,-30),(25,0)]),track('opacity',[(0,0),(12,1)])],
  [track('position_x',[(0,-38*d),(28,0)]),track('opacity',[(0,0),(14,1)])],
  [track('scale',[(0,1.07),(30,1)]),track('opacity',[(0,0),(13,1)])],
 ]
 variants=[
  [track('position_x',[(0,-260*d),(26,16),(39,0)]),track('opacity',[(0,0),(10,1)])],
  [track('position_y',[(0,190),(21,-12),(34,0)]),track('opacity',[(0,0),(9,1)])],
  [track('scale',[(0,.55),(25,1.08),(40,1)],'out_back'),track('opacity',[(0,0),(10,1)])],
  [track('position_x',[(0,360*d),(31,0)]),track('opacity',[(0,0),(8,1)])],
  [track('position_y',[(0,-155),(28,0)]),track('scale',[(0,1.16),(28,1)]),track('opacity',[(0,0),(10,1)])],
  [track('scale',[(0,.82),(20,1.04),(34,1)]),track('position_x',[(0,-90*d),(29,0)]),track('opacity',[(0,0),(8,1)])],
  [track('position_y',[(0,45),(18,-6),(30,0)]),track('opacity',[(0,0),(6,1)])]
 ]
 return variants[i%len(variants)]

def build_palette_assets():
 from PIL import ImageDraw, ImageFilter, ImageOps
 pd=ASSETS/'palettes'; qd=ASSETS/'portraits'; pd.mkdir(parents=True,exist_ok=True); qd.mkdir(parents=True,exist_ok=True)
 original=base.grayscale_photo()
 for j,(top,bottom,light,accent) in enumerate(PALETTES):
  plate=Image.new('RGB',(W,H)); pix=plate.load()
  for y in range(H):
   t=y/(H-1); t=t*t*(3-2*t); col=tuple(round(top[k]*(1-t)+bottom[k]*t) for k in range(3))
   for x in range(W): pix[x,y]=col
  d=ImageDraw.Draw(plate,'RGBA'); d.ellipse((W*.58,-H*.38,W*1.22,H*.78),fill=(*accent,42))
  d.line((86,82,W-86,82),fill=(*accent,130),width=2); d.line((86,H-84,W-86,H-84),fill=(*accent,110),width=2)
  for k in range(7): d.line((110+k*25,115,110+k*25,H-115),fill=(*accent,13),width=1)
  plate=plate.filter(ImageFilter.GaussianBlur(1.0)); plate.save(pd/f'palette-{j+1:02d}.png',optimize=True)
  lum=original.getchannel('R')
  if j==3: shadow,highlight=(77,60,39),(224,208,174)
  elif j==7: shadow,highlight=(67,26,29),(222,218,211)
  else: shadow,highlight=tuple(int(v*.42) for v in accent),light
  toned=ImageOps.colorize(lum,black=shadow,white=highlight).convert('RGBA')
  toned.putalpha(original.getchannel('A')); toned.save(qd/f'trump-palette-{j+1:02d}.png',optimize=True)

def main():
 (ASSETS/'portraits').mkdir(parents=True,exist_ok=True)
 (ASSETS/'fonts').mkdir(parents=True,exist_ok=True)
 build_palette_assets()
 shutil.copy2(base.CHRONON/'assets/fonts'/FONT,OUT/ASSETS/'fonts'/FONT)
 total=len(STYLES)*FRAMES
 layers=[]
 for i,(slug,label,photo,caption,stacked) in enumerate(STYLES):
  original_no=i+1 if i<8 else i+2
  start=i*FRAMES; px,py,pw,ph=photo; tx,ty,tw,th=caption
  palette=i%len(PALETTES); bg=f'assets/palettes/palette-{palette+1:02d}.png'; portrait=f'assets/portraits/trump-palette-{palette+1:02d}.png'
  fg_hex='#%02X%02X%02X'%PALETTES[palette][2]
  layers.append({'id':f'background-{original_no:02d}','type':'image','asset':bg,'size':[W,H],'fit':'cover','position':[0,0],
    'start_frame':start,'duration_frames':FRAMES})
  photo_side='left' if px<W/2 else 'right'
  layers.append({'id':f'photo-{original_no:02d}','type':'image','asset':portrait,'size':[pw,ph],'fit':'contain',
    'position':[px-W/2,H/2-py],'start_frame':start,'duration_frames':FRAMES,'enable_3d':True,
    'animation':{'tracks':photo_motion(i,photo_side)}})
  text='DONALD\nTRUMP' if stacked else 'DONALD TRUMP'
  fsize=112 if stacked else (76 if tw<950 else 90)
  tl=base.text_layer(f'name-{original_no:02d}',text,(tx,H-ty),(tw,th),FONT,fsize,fg_hex,caption_motion(i,photo_side))
  tl['start_frame']=start; tl['duration_frames']=FRAMES; layers.append(tl)
 plan={'schema':'chronon.render-plan.v3','version':3,'job_id':'trump_entity_21_varied_5sec_gpu',
   'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':total},'layers':layers,
   'output':{'path':'trump_entity_21_varied_5sec_gpu_master.mp4','format':'mp4','codec':'h264'}}
 pp=OUT/'trump_entity_21_varied_5sec_gpu.plan.json'; pp.write_text(json.dumps(plan,indent=2)+'\n')
 raw=OUT/'trump_entity_21_varied_5sec_gpu.nv12'; master=OUT/'trump_entity_21_varied_5sec_gpu_master.mp4'
 if not master.exists():
  cli=base.CLI
  subprocess.run([str(cli),'render','--plan',str(pp),'--assets-root',str(OUT),'--backend','vulkan','--profile','preview',
   '--fps',str(FPS),'--video-sink','raw','--pipe-pixfmt','nv12','--chunks','1','--fb-pool-budget-mb','768',
   '--fb-pool-clear-policy','trim-after-job','--start-frame','0','--end-frame',str(total-1),'-o',str(raw)],cwd=WORKSPACE,check=True)
  expected=total*W*H*3//2
  if raw.stat().st_size!=expected: raise RuntimeError(f'NV12 size mismatch: {raw.stat().st_size} != {expected}')
  subprocess.run(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','nv12','-video_size',f'{W}x{H}','-framerate',str(FPS),
   '-i',str(raw),'-frames:v',str(total),'-vsync','cfr','-c:v','h264_nvenc','-preset','p4','-cq','18','-b:v','0','-pix_fmt','yuv420p',
   '-r',str(FPS),'-g',str(FPS),str(master)],cwd=WORKSPACE,check=True)
  raw.unlink(); print('MASTER_GPU_RENDER_VERIFIED',total,'frames',total/FPS,'seconds',flush=True)
 clips=OUT/'individual_mp4'; clips.mkdir(exist_ok=True)
 for p in clips.glob('*.mp4'): p.unlink()
 names=[]
 for i,(slug,label,*_) in enumerate(STYLES):
  original_no=i+1 if i<8 else i+2
  final=clips/f'trump_entity_{original_no:02d}_{slug}.mp4'
  subprocess.run(['ffmpeg','-v','error','-y','-ss',str(i*5),'-i',str(master),'-frames:v',str(FRAMES),'-an','-c:v','h264_nvenc',
   '-preset','p4','-cq','18','-b:v','0','-pix_fmt','yuv420p','-r',str(FPS),'-vsync','cfr','-video_track_timescale','30000',str(final)],cwd=WORKSPACE,check=True)
  probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nk=1:nw=1',str(final)],capture_output=True,text=True,check=True)
  dur=float(probe.stdout.strip())
  if abs(dur-5)>0.04: raise RuntimeError(f'{final.name} is {dur:.3f}s, expected five seconds')
  names.append(final.name)
 print('INDIVIDUAL_NVENC_CLIPS_VERIFIED',len(names),json.dumps(names),flush=True)

if __name__=='__main__': main()
