#!/usr/bin/env python3
"""Author map reference animations as Chronon compositions with native type and paths."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WORKSPACE=ROOT.parent
CAT=ROOT/'catalog/motion_catalog.v1.json';OUT=ROOT/'out/map_image_v1'
CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
W,H,FPS,N=1920,1080,30,150;CX,CY=960,540
FONT='Chronon3d/assets/fonts/Poppins-Bold.ttf';BODY='Chronon3d/assets/fonts/Poppins-Regular.ttf'
SCENES=[('brazil','Brazil','Brasília','#52E2D5','glow_reveal'),('usa','United States','Washington, D.C.','#72D7FF','sweep_in'),
 ('iran','Iran','Tehran','#F4C264','gold_focus'),('india','India','New Delhi','#5BE1D0','contour_draw'),
 ('gujarat','Gujarat','Ahmedabad','#F263D5','detail_push'),('italy','Italy','Rome','#FF8276','beacon_arrival'),
 ('nigeria','Nigeria','Abuja','#5EE9AE','neon_bloom'),('china','China','Beijing','#FF6755','slow_reveal'),
 ('korea','South Korea','Seoul','#74CDFF','pin_focus'),('australia','Australia','Canberra','#F6BF55','sunset_drift')]
def tr(p,keys,e='out_cubic'):return {'property':p,'easing':e,'keyframes':[{'frame':f,'value':v} for f,v in keys]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',choices=[s[0] for s in SCENES]);ap.add_argument('--validate',action='store_true');ap.add_argument('--render',action='store_true');a=ap.parse_args()
 motions={m['id']:m for m in json.loads(CAT.read_text())['motions'] if m.get('category')=='map_image_v1'};items=[]
 for order,(slug,title,capital,accent,suffix) in enumerate((s for s in SCENES if not a.only or s[0]==a.only),1):
  index=next(i for i,s in enumerate(SCENES,1) if s[0]==slug);mid=f'map_image_{slug}_{suffix}'
  motion=motions[mid];cam=[]
  for track in motion['tracks']:
   cam.append(tr(track['property'],[(k['frame'],k['value']) for k in track['keyframes']],
                 'in_out_sine' if track['property']=='scale' else 'linear'))
  source=ROOT/'assets/map_animation_refs'/f'ref_{index:02d}.png'
  layers=[{'id':f'{slug}-map-plate','type':'image','asset':str(source.relative_to(WORKSPACE)),
    'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':N,'animation':{'tracks':cam}}]
  variants={
   'brazil':[tr('position_x',[(0,-78),(36,0)]),tr('opacity',[(0,0),(22,1)])],
   'usa':[tr('position_y',[(0,36),(33,0)]),tr('opacity',[(0,0),(18,1)])],
   'iran':[tr('position_y',[(0,20),(27,0)]),tr('opacity',[(0,0),(17,1)])],
   'india':[tr('position_x',[(0,90),(38,0)]),tr('opacity',[(0,0),(19,1)])],
   'gujarat':[tr('position_y',[(0,22),(24,0)]),tr('opacity',[(0,0),(20,1)])],
   'italy':[tr('position_y',[(0,-34),(31,0)]),tr('opacity',[(0,0),(17,1)])],
   'nigeria':[tr('position_x',[(0,66),(30,0)]),tr('opacity',[(0,0),(16,1)])],
   'china':[tr('position_y',[(0,20),(26,0)]),tr('opacity',[(0,0),(15,1)])],
   'korea':[tr('position_y',[(0,42),(31,0)]),tr('opacity',[(0,0),(18,1)])],
   'australia':[tr('position_y',[(0,24),(35,0)]),tr('opacity',[(0,0),(17,1)])]}
  layers.extend([
   {'id':f'{slug}-series-label','type':'text','text':f'FIELD ATLAS  /  REGIONAL STUDY  {index:02d}',
    'size':[860,30],'position':[530,865],'start_frame':0,'duration_frames':N,
    'style':{'font':BODY,'font_size':16,'fill':accent},'animation':{'tracks':[tr('position_x',[(0,-28),(23,0)]),tr('opacity',[(0,0),(18,1)])]}},
   {'id':f'{slug}-native-title','type':'text','text':title.upper(),'size':[1000,98],'position':[610,947],
    'start_frame':0,'duration_frames':N,'style':{'font':FONT,'font_size':78 if len(title)<14 else 66,
      'min_font_size':56,'max_font_size':78,'fit_mode':'shrink_only','fill':'#F7F4EA'},
    'animation':{'tracks':variants[slug]}},
   {'id':f'{slug}-native-callout','type':'text','text':f'CAPITAL  /  {capital.upper()}','size':[650,40],
    'position':[1500,946],'start_frame':0,'duration_frames':N,
    'style':{'font':BODY,'font_size':19,'fill':'#B8C7CF'},
    'animation':{'tracks':[tr('position_x',[(0,56),(63,0)]),tr('opacity',[(0,0),(57,1)])]}}
  ])
  plan={'schema':'chronon.render-plan.v3','version':3,'job_id':mid,
   'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':N},'layers':layers,
   'output':{'path':f'{mid}.mp4','format':'mp4','codec':'h264'}}
  plans=OUT/'plans';plans.mkdir(parents=True,exist_ok=True);pp=plans/f'{mid}.plan.json';pp.write_text(json.dumps(plan,indent=2)+'\n')
  if a.validate or a.render:subprocess.run([str(CLI),'validate','--plan',str(pp),'--assets-root',str(WORKSPACE)],check=True,stdout=subprocess.DEVNULL)
  if a.render:
   dest=OUT/'renders'/f'{mid}.mp4';dest.parent.mkdir(parents=True,exist_ok=True)
   subprocess.run([str(CLI),'render','--plan',str(pp),'--assets-root',str(WORKSPACE),'--output',str(dest),
    '--backend','vulkan','--gpu-hot-path-mode','require_gpu_native','--hardware','nvenc','--encoder-backend','native',
    '--fps',str(FPS),'--rate-control','qp','--qp','20','--encode-preset','p5','--log-level','error'],check=True,stdout=subprocess.DEVNULL)
  items.append({'id':mid,'name':title,'plan':str(pp.relative_to(OUT)),'video':f'renders/{mid}.mp4','native_layers':3})
 (OUT/'native_manifest.json').write_text(json.dumps({'family':'map_image_v1','format':'Chronon render-plan with native animated text','canvas':{'width':W,'height':H,'fps':FPS,'duration_seconds':5},'animations':items},indent=2)+'\n')
 print(f'NATIVE_MAP_PASS scenes={len(items)} native_text_layers=3 vector_paths=0 1920x1080 5s')
if __name__=='__main__':main()
