#!/usr/bin/env python3
"""Documentary Phrase Highlighting 3.0: native text/path RenderPlans only.

The canonical Chronon3D renderer owns shaping, text metrics, compositing and
frame sampling. No external text engine or path rasterizer is used here.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'ChrononTemplate/out/documentary_phrase_highlighting_v3'
CLI = ROOT / 'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
W,H,FPS,FRAMES = 1920,1080,30,180
REGULAR='Chronon3d/assets/fonts/Inter-Regular.ttf'; BOLD='Chronon3d/assets/fonts/Inter-Bold.ttf'
INK='#202322'; PAPER='#F2EEE4'; AMBER='#C49A5A'; RED='#A64A3E'; MUTED='#92958F'
PRESETS=[
 ('01_single_phrase_highlight','The truth was never revealed.','truth|revealed','underline'),
 ('02_soft_marker_reveal','A hidden connection emerged.','hidden|connection','marker'),
 ('03_multi_phrase_connection','The missing files|The secret meeting','missing files|secret meeting','curved'),
 ('04_investigative_keyword_network','The records changed everything.','records|changed|everything','network'),
 ('05_word_by_word_focus','Nobody knew what happened.','Nobody|knew|what|happened','focus'),
 ('06_hand_drawn_underline','An unexpected discovery.','unexpected discovery','handline'),
 ('07_phrase_to_phrase_trace','A date in the ledger|A name in the record','date in the ledger|name in the record','trace'),
 ('08_precision_bracket_highlight','The witness changed the account.','witness changed','bracket'),
 ('09_sequential_statement_highlight','First, the documents disappeared.|Then, the witnesses changed.|Finally, the truth emerged.','truth emerged','sequence'),
 ('10_documentary_phrase_master','The overlooked date connected the records.|A second copy was filed three days later.|The original register named the harbor office.','overlooked date|three days|harbor office','master'),
]

def rgba(value):
 value=value.lstrip('#')
 return [int(value[i:i+2],16)/255 for i in (0,2,4)]+[1.0]
def tr(prop, keys, easing='in_out_sine'):
 return {'property':prop,'easing':easing,'keyframes':[{'frame':f,'value':v} for f,v in keys]}

def phrase_layer(id_,text,x,y,w,size,color,font=BOLD,start=0,fade=True,height=130):
 # Text placement is canvas-centered inside its own frame. Compensate the
 # compiler's canvas-center layer basis so [x,y] remains the frame top-left.
 return {'id':id_,'type':'text','text':text,'position':[x+w/2,y+height/2],'size':[w,height],'screen_space':True,'start_frame':start,'duration_frames':FRAMES-start,'style':{'font':font,'font_size':size,'min_font_size':size,'max_font_size':size,'fit_mode':'shrink_only','fill':color},'animation':{'tracks':[tr('opacity',[(start,0),(start+12,1)],'out_cubic')] if fade else []}}


def text_path_layer(id_,points,color,width,start,end,frames=FRAMES):
 # Shape paths are authored centre-relative and their world matrix is identity
 # under screen_layer(); unlike TextRun, they do not get a canvas-centre bake.
 return path_layer(id_,points,color,width,start,end,frames)


def build_master(bg='dark'):
 """The single acceptance-scene RenderPlan; all geometry is canvas-pixel authored."""
 dark=bg=='dark'; base='#171B1C' if dark else '#E9E3D6'
 fg='#F2EFE6' if dark else INK; accent=AMBER if dark else '#855B2B'
 bg_rgba=rgba(base)
 layers=[{'id':'background','type':'color','color':bg_rgba,'position':[0,0],'size':[W,H],'screen_space':True,'start_frame':0,'duration_frames':FRAMES}]
 title=phrase_layer('title','THE MISSING EVIDENCE',210,300,1500,96,fg,BOLD,0,True,150)
 title['animation']['tracks']=[tr('opacity',[(0,0),(24,1)],'out_cubic')]
 layers.append(title)
 # Underline only the word MISSING; coordinates use the checked Inter font metrics.
 from PIL import ImageFont
 font=ImageFont.truetype(str(ROOT/BOLD),96)
 pre=font.getlength('THE '); word=font.getlength('MISSING')
 title_left=210+(1500-font.getlength(title['text']))/2
 title_y=300+150/2
 missing_left=title_left+pre
 underline_y=title_y+61
 layers.append(text_path_layer('highlight-missing',[(missing_left,underline_y),(missing_left+word,underline_y)],accent,2.1,24,42))
 layers[-1]['shape']['fill']=[0.0,0.0,0.0,0.0]
 labels=[('witness','The witness',170,710,'witness'),('report','The report',710,710,'report'),('timeline','The timeline',1250,710,None)]
 label_width=500; label_y=710; label_h=110; label_size=54
 target_centres=[]
 for i,(identity,text,x,y,highlight) in enumerate(labels):
  start=75+i*10
  layer=phrase_layer(identity,text,x,y,label_width,label_size,fg,BOLD,start,True,label_h)
  layers.append(layer)
  center_x=x+label_width/2
  target_centres.append((center_x,y-5)) # stop just above the rendered glyph bounds.
  if highlight:
   f=ImageFont.truetype(str(ROOT/BOLD),label_size)
   prefix=f.getlength(text[:text.index(highlight)])
   word_width=f.getlength(highlight)
   ink_left=center_x-f.getlength(text)/2+prefix
   yy=y+label_h/2+34
   layers.append(text_path_layer('highlight-'+identity,[(ink_left,yy),(ink_left+word_width,yy)],accent,2.0,105,165))
   layers[-1]['shape']['fill']=[0.0,0.0,0.0,0.0]
 # Connect actual title/label frame anchors with three animated native paths.
 starts=[(420,title_y+72),(960,title_y+72),(1500,title_y+72)]
 for i,((sx,sy),(tx,ty)) in enumerate(zip(starts,target_centres)):
  ex,ey=tx,ty
  # Start just below the title and end just above each label, leaving a
  # clean route that does not overlap opaque glyphs.
  sy=title_y+72
  ey=label_y-30
  dx=ex-sx
  points=[]
  for j in range(25):
   t=j/24; u=1-t
   points.append((u**3*sx+3*u*u*t*(sx+dx*.15)+3*u*t*t*(ex-dx*.15)+t**3*ex,
                  u**3*sy+3*u*u*t*(sy+100)+3*u*t*t*(ey-95)+t**3*ey))
  layers.append(text_path_layer(f'connector-{i+1}',points,accent,2.0,42+i*2,75+i*2))
  layers[-1]['shape']['fill']=[0.0,0.0,0.0,0.0]
 return {'schema':'chronon.render-plan.v3','version':3,'job_id':'documentary_phrase_master_corrected_'+bg,
  'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},'layers':layers,
  'output':{'path':'documentary_phrase_master_corrected.mp4','format':'mp4','codec':'h264'}}


def verify_master(video,plan,bg,report_dir,ffmpeg='ffmpeg',ffprobe='ffprobe'):
 """Render-sample gate: codec/geometry, visible text, safe margins and timed changes."""
 from PIL import Image, ImageChops
 import numpy as np
 video=Path(video); report_dir=Path(report_dir); report_dir.mkdir(parents=True,exist_ok=True)
 stream=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,avg_frame_rate,nb_read_frames,duration','-of','json',str(video)],text=True))['streams'][0]
 expected=('h264',W,H,'30/1',FRAMES)
 actual=(stream['codec_name'],int(stream['width']),int(stream['height']),stream['avg_frame_rate'],int(stream['nb_read_frames']))
 if actual!=expected or abs(float(stream['duration'])-6)>0.001: raise RuntimeError(f'{bg}: invalid stream {stream}')
 samples={'title':0.5,'underline':1.2,'connectors_before':1.35,'connectors_after':2.35,'connector_final':3.8,'labels':3.3,'word_highlights':4.5,'final':5.8}
 frames={}
 for name,seconds in samples.items():
  path=report_dir/f'{bg}_{name}.png'
  subprocess.run([ffmpeg,'-y','-loglevel','error','-ss',str(seconds),'-i',str(video),'-frames:v','1',str(path)],check=True)
  frames[name]=Image.open(path).convert('RGB')
 background=np.asarray(frames['final'])[5,5].astype(int)
 def box(name,rect):
  image=np.asarray(frames[name]).astype(int); x0,y0,x1,y1=rect
  roi=image[y0:y1,x0:x1]; mask=np.max(np.abs(roi-background),axis=2)>4
  ys,xs=np.where(mask)
  if not len(xs): raise RuntimeError(f'{bg}: no rendered pixels in {name} region {rect}')
  return [int(xs.min()+x0),int(ys.min()+y0),int(xs.max()+x0),int(ys.max()+y0)],int(mask.sum())
 text_regions={'title':[210,300,1710,450],'witness':[170,710,670,820],'report':[710,710,1210,820],'timeline':[1250,710,1750,820]}
 boxes={}; ink={}
 for key,rect in text_regions.items(): boxes[key],ink[key]=box('final',rect)
 for key,value in boxes.items():
  if value[0]<120 or value[1]<120 or value[2]>W-120 or value[3]>H-120: raise RuntimeError(f'{bg}: {key} violates 120px safe margin: {value}')
 def difference(before,after):
  a=np.asarray(frames[before]).astype(int); b=np.asarray(frames[after]).astype(int)
  return int(np.count_nonzero(np.max(np.abs(a-b),axis=2)>18))
 def region_ink(frame_name,rect):
  image=np.asarray(frames[frame_name]).astype(int); x0,y0,x1,y1=rect
  roi=image[y0:y1,x0:x1]
  return int(np.count_nonzero(np.max(np.abs(roi-background),axis=2)>12))
 def color_ink(frame_name,rect,color,threshold=28):
  image=np.asarray(frames[frame_name]).astype(int); x0,y0,x1,y1=rect
  roi=image[y0:y1,x0:x1]
  target=np.asarray(color,dtype=int)
  return int(np.count_nonzero(np.max(np.abs(roi-target),axis=2)<threshold))
 def path_bounds(layer_id,padding=6):
  layer=next((item for item in plan['layers'] if item['id']==layer_id),None)
  if layer is None: raise RuntimeError(f'{bg}: missing path layer {layer_id}')
  commands=layer.get('shape',{}).get('path',[])
  points=[command['point'] for command in commands if command.get('type')!='close']
  if len(points)<2: raise RuntimeError(f'{bg}: path {layer_id} has no drawable segment')
  position=layer.get('position',[0.0,0.0])
  xs=[float(point[0])+float(position[0])+W*0.5 for point in points]
  ys=[float(point[1])+float(position[1])+H*0.5 for point in points]
  return [max(0,int(min(xs)-padding)),max(0,int(min(ys)-padding)),
          min(W,int(max(xs)+padding+1)),min(H,int(max(ys)+padding+1))]
 accent=tuple(int(channel*255) for channel in plan['layers'][2]['shape']['stroke']['color'][:3])
 title_bounds=[560,430,1380,525]
 # Screen-space path placement is validated against the drawn stroke pixels,
 # which include native path rasterization's cap/edge footprint.
 highlights={'title_underline':('underline','highlight-missing',title_bounds),
             'witness_underline':('word_highlights','highlight-witness',[350,770,600,820]),
             'report_underline':('word_highlights','highlight-report',[900,770,1120,820])}
 highlight_ink={key:region_ink(frame_name,rect)
                for key,(frame_name,_layer_id,rect) in highlights.items()}
 if min(highlight_ink.values())<12:
  raise RuntimeError(f'{bg}: authored accent highlight paths are not visible: {highlight_ink}')
 motion={'title_to_underline':difference('title','underline'),
         'connector_reveal':difference('connectors_before','connectors_after'),
         'secondary_reveal':difference('connectors_after','labels'),
         'selected_word_reveal':difference('labels','word_highlights')}
 if min(motion.values())<40: raise RuntimeError(f'{bg}: animation visibility below threshold: {motion}')
 before=np.asarray(frames['connectors_before']).astype(int)
 after=np.asarray(frames['connectors_after']).astype(int)
 route=(slice(430,700),slice(250,1670))
 route_diff=np.max(np.abs(after[route]-before[route]),axis=2)
 connector_changed=int(np.count_nonzero(route_diff>12))
 final=np.asarray(frames['final']).astype(int)
 route_ink=np.max(np.abs(final[route]-background),axis=2)
 connector_ink=int(np.count_nonzero(route_ink>12))
 connector_ids=('connector-1','connector-2','connector-3')
 connector_boxes=[path_bounds(layer_id,8) for layer_id in connector_ids]
 # Sample at 3.8s (frame 114), after each trim interval has completed.
 connector_check=np.asarray(frames['connector_final']).astype(int)
 connector_final_ink=0
 for rect in connector_boxes:
  x0,y0,x1,y1=rect; roi=connector_check[y0:y1,x0:x1]
  # Video output color conversion and 4:2:0 chroma subsampling shift the
  # authored amber noticeably; require warm, non-background pixels instead
  # of exact RGB proximity.
  warm=(roi[:,:,0]>80)&(roi[:,:,0]>roi[:,:,1]*1.12)&(roi[:,:,1]>roi[:,:,2]*1.1)
  connector_final_ink+=int(np.count_nonzero(warm))
 # The reveal sample checks spatial route activity while the completed
 # connector sample checks actual stroke-colored pixels in each path bound.
 if connector_changed<40 or connector_final_ink<12:
  raise RuntimeError(f'{bg}: connectors are not visibly drawn: changed={connector_changed}, accent_ink={connector_final_ink}')
 motion['connector_region_changed_pixels']=connector_changed
 motion['connector_region_ink_pixels']=connector_ink
 motion['connector_final_accent_pixels']=connector_final_ink
 if min(ink[key] for key in ('title','witness','report','timeline'))<250:
  raise RuntimeError(f'{bg}: rendered text coverage too small: {ink}')
 return {'background':bg,'stream':stream,'text_bounding_boxes_px':boxes,'text_ink_pixel_counts':ink,
         'highlight_ink_pixel_counts':highlight_ink,
         'animation_changed_pixels':motion,'sample_frames':{k:str(report_dir/f'{bg}_{k}.png') for k in samples},
         'safe_margin_px':120,'passed':True}
def render_corrected_master(out=OUT,cli=CLI):
 out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
 report_dir=out/'documentary_phrase_master_corrected_verification'
 records=[]
 for bg in ('dark','ivory'):
  plan=build_master(bg); plan_path=out/f'documentary_phrase_master_corrected_{bg}.plan.json'
  video=out/'documentary_phrase_master_corrected.mp4' if bg=='dark' else report_dir/'documentary_phrase_master_corrected_ivory_check.mp4'
  plan['output']['path']=str(video.resolve()); plan_path.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
  subprocess.run([str(cli),'render','--plan',str(plan_path),'--assets-root',str(ROOT),'--backend','vulkan','--profile','production','--fps','30','--ffmpeg-mode','pipe','--encoder-backend','pipe','--hardware','none','--rate-control','crf','--crf','20','--preset','medium','-o',str(video)],check=True,cwd=ROOT)
  records.append(verify_master(video,plan,bg,report_dir))
 report={'scene':'THE MISSING EVIDENCE','delivery_video':str((out/'documentary_phrase_master_corrected.mp4').resolve()),
         'resolution':[W,H],'fps':FPS,'duration_seconds':6,'verified_backgrounds':records,'passed':True}
 (report_dir/'acceptance_report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report


RENDER_CORRECTED_MASTER=render_corrected_master




def focus_word_animators(layer, words, dim, focus, first=30, step=18, hold=10):
 layer['spans']=[]; layer['text_animators']=[]
 raw=layer['text']
 for i,word in enumerate(words):
  at=raw.index(word); start=len(raw[:at].encode()); end=start+len(word.encode()); sid=f'{layer["id"]}-word-{i}'
  layer['spans'].append({'start':start,'end':end,'semantic_id':sid,'style':{'color':dim}})
  on=first+i*step; off=on+hold
  layer['text_animators'].append({'id':sid+'-focus','selectors':[{'id':sid+'-selector','semantic_id':sid,'unit':'word','shape':'square','order':'forward','combine':'replace','exclude_spaces':True}], 'properties':[{'property':'fill_color','easing':'linear','keyframes':[{'frame':0,'value':rgba(dim)},{'frame':on,'value':rgba(dim)},{'frame':on+1,'value':rgba(focus)},{'frame':off,'value':rgba(focus)},{'frame':off+1,'value':rgba(dim)},{'frame':FRAMES-1,'value':rgba(dim)}]}]})

def marker_animator(layer,sid,color,start=30,end=78):
 layer['text_animators']=[{'id':sid+'-marker-reveal','selectors':[{'id':sid+'-marker-selector','semantic_id':sid,'unit':'word','shape':'square','order':'forward','combine':'replace','exclude_spaces':True}], 'properties':[{'property':'background_color','easing':'linear','keyframes':[{'frame':0,'value':rgba(color)[:3]+[0]},{'frame':start,'value':rgba(color)[:3]+[0]},{'frame':start+1,'value':rgba(color)[:3]+[.34]},{'frame':end,'value':rgba(color)[:3]+[.34]}]}]}]
def spans(layer, targets, fg, bg, kind):
 text=layer['text']; out=[]
 for phrase in targets:
  at=text.index(phrase); a=len(text[:at].encode()); b=a+len(phrase.encode())
  if kind in ('marker','master','sequence','focus'):
   style={'highlight':{'background':bg+'55','padding_em':.09,'radius_em':.03}}
   if kind=='focus': style={'color':fg}
  else: style={'color':fg}
  out.append({'start':a,'end':b,'semantic_id':f'{layer["id"]}-{len(out)}','style':style})
 layer['spans']=out

def path_layer(id_, points, color, width, start=24, end=90, frames=FRAMES):
 cmds=[{'type':'move_to' if i==0 else 'line_to','point':[x-W/2,y-H/2]} for i,(x,y) in enumerate(points)]
 return {'id':id_,'type':'shape','shape':{'type':'path','path':cmds,'stroke':{'color':rgba(color),'width':width,'cap':'butt','join':'round'},'operators':[{'kind':'trim','params':{'start':0,'end':1,'animation':{'easing':'in_out_sine','keyframes':[{'frame':start,'value':[0,0,0]},{'frame':end,'value':[0,1,0]}]}}}]},'color':rgba(color),'position':[0,0],'size':[W,H],'start_frame':0,'duration_frames':frames,'screen_space':True}
def cubic(a,b,c,d,n=32):
 pts=[]
 for i in range(n+1):
  t=i/n; u=1-t
  pts.append(tuple(round(u**3*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t**3*d[k],2) for k in (0,1)))
 return pts

def build(preset,bg):
 name,copy,targets,kind=preset; dark=bg=='dark'; base='#171B1C' if dark else '#E9E3D6'; fg='#F2EFE6' if dark else INK; accent=AMBER if dark else '#9B6C34'; dim='#B8BBB4' if dark else MUTED
 layers=[{'id':'background','type':'color','color':rgba(base),'position':[0,0],'size':[W,H],'screen_space':True,'start_frame':0,'duration_frames':FRAMES},
 {'id':'eyebrow','type':'text','text':'DOCUMENTARY / EVIDENCE','position':[150,120],'size':[900,42],'screen_space':True,'start_frame':0,'duration_frames':FRAMES,'style':{'font':REGULAR,'font_size':22,'fill':accent}}]
 lines=copy.split('|'); target_groups=targets.split('|'); y0=400 if len(lines)==1 else 325
 text_layers=[]
 for i,line in enumerate(lines):
  y=y0+i*(155 if len(lines)>2 else 190); start=12+i*(14 if kind=='sequence' else 5)
  if kind=='sequence' and i==2: start=92
  layer=phrase_layer(f'phrase-{i+1}',line,190,y,1540,60 if len(lines)==1 else 48,fg,BOLD,start)
  keys=target_groups[i].split(',') if len(target_groups)==len(lines) else (target_groups if len(lines)==1 else (target_groups if kind=='sequence' and i==len(lines)-1 else []))
  if kind=='focus':
   focus_word_animators(layer,keys,dim,accent,first=30,step=20,hold=10)
  else:
   if keys: spans(layer,keys,accent,accent,kind)
   if kind=='marker' and keys: marker_animator(layer,layer['spans'][0]['semantic_id'],accent)
  layers.append(layer); text_layers.append(layer)
  if kind in ('underline','handline'):
   yy=y+79; points=[(235,yy),(1680,yy)] if kind=='underline' else [(240,yy),(590,yy-2),(980,yy+1),(1670,yy-1)]
   layers.append(path_layer('highlight-line',points,accent,1.7 if kind=='underline' else 1.35,30,78))
  if kind=='bracket':
   left=215; right=1665; top=y-10; bot=y+96
   for sgn,x in ((1,left),(-1,right)):
    pts=[(x+sgn*26,top),(x,top),(x,bot),(x+sgn*26,bot)]
    layers.append(path_layer('bracket-'+str(sgn),pts,accent,1.6,32,70))
  if kind=='focus':
   layer['animation']['tracks']=[tr('opacity',[(0,0),(12,.48),(22,1),(43,.48),(64,1)],'in_out_sine')]
  if kind=='sequence' and i==2:
   # Stagger the last statement, then reveal its semantic highlight only after entry.
   layer['animation']['tracks']=[tr('opacity',[(start,0),(start+12,1)],'out_cubic')]
   layer['animation']['tracks'].append(tr('scale',[(0,1),(100,1),(118,1.025),(132,1)],'out_cubic'))
   marker_animator(layer,layer['spans'][0]['semantic_id'],accent,start=start+28,end=start+55)
 if kind in ('curved','trace','master') and len(text_layers)>=2:
  for i in range(len(text_layers)-1):
   y1=y0+i*(155 if len(lines)>2 else 190)+83; y2=y0+(i+1)*(155 if len(lines)>2 else 190)+4
   pts=cubic((1615,y1),(1770,y1+24),(1740,y2-20),(1615,y2))
   layers.append(path_layer(f'connector-{i}',pts,accent,1.35,36+i*12,82+i*12))
 if kind=='network':
  center=(960,535)
  for i,(label,pos) in enumerate(zip(['date','ledger','source'],[(310,770),(960,800),(1610,770)])):
   word=phrase_layer('keyword-'+str(i),label,pos[0]-150,pos[1],300,30,dim,REGULAR,24+i*12)
   spans(word,[label],accent,accent,'marker'); layers.append(word)
   layers.append(path_layer('network-link-'+str(i),cubic(center,(center[0],center[1]+90),(pos[0],pos[1]-120),pos),accent,1.1,35+i*14,75+i*14))
 # Stable catalog IDs and complete render contract.
 return {'schema':'chronon.render-plan.v3','version':3,'job_id':name+'_'+bg,'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},'layers':layers,'output':{'path':name+'_'+bg+'.mp4','format':'mp4','codec':'h264'}}

def emit(out=OUT):
 out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True); paths=[]
 for preset in PRESETS:
  for bg in ('dark','ivory'):
   plan=build(preset,bg); path=out/(plan['job_id']+'.plan.json'); plan['output']['path']=str((out/(plan['job_id']+'.mp4')).resolve()); path.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n'); paths.append(path)
 return paths

def render(out=OUT,cli=CLI):
 plans=emit(out); records=[]
 for plan in plans:
  obj=json.loads(plan.read_text()); video=Path(obj['output']['path'])
  subprocess.run([str(cli),'render','--plan',str(plan),'--assets-root',str(ROOT),'--backend','vulkan','--profile','production','--fps','30','--ffmpeg-mode','pipe','--encoder-backend','pipe','--hardware','none','--rate-control','crf','--crf','20','--preset','medium','-o',str(video)],check=True,cwd=ROOT)
  info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,avg_frame_rate,nb_read_frames,duration','-of','json',str(video)],text=True))['streams'][0]
  if (info['codec_name'],info['width'],info['height'],info['avg_frame_rate'],int(info['nb_read_frames'])) != ('h264',W,H,'30/1',FRAMES) or abs(float(info['duration'])-6)>0.001: raise RuntimeError(f'bad stream {video}: {info}')
  records.append({'plan':plan.name,'video':video.name,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'probe':info})
 (Path(out)/'manifest.json').write_text(json.dumps({'resolution':[W,H],'fps':FPS,'duration_seconds':6,'variants':['dark','ivory'],'renderer_backend':'vulkan','encoder_backend':'ffmpeg_pipe_cpu','strict_gpu_native_nvenc':'unavailable_on_host','videos':records},indent=2)+'\n')

def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--out',type=Path,default=OUT); ap.add_argument('--cli',type=Path,default=CLI); ap.add_argument('--render',action='store_true'); ap.add_argument('--corrected-master',action='store_true'); a=ap.parse_args(); paths=emit(a.out) if not a.corrected_master else []; print(f'Emitted {len(paths)} plans to {a.out.resolve()}' if not a.corrected_master else f'Rendering corrected master to {a.out.resolve()}'); render(a.out.resolve(),a.cli.resolve()) if a.render else None; render_corrected_master(a.out.resolve(),a.cli.resolve()) if a.corrected_master else None
if __name__=='__main__': main()
