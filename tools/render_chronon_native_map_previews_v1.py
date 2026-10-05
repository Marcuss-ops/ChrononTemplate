#!/usr/bin/env python3
"""Animate map references with Chronon-native titles, vector contours and markers."""
from __future__ import annotations
import argparse,json,math,subprocess
from pathlib import Path
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1];WORKSPACE=ROOT.parent
GEO=ROOT/'catalog/ne_50m_admin_0_countries.geojson';CAT=ROOT/'catalog/motion_catalog.v1.json'
OUT=ROOT/'out/map_image_v1';CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
W,H,FPS,N=1920,1080,30,150;CX,CY=960,540;MW,MH=900,700
MASKS=[((76,35,110),(106,255,255),(390,80,1260,900)),
 ((78,5,130),(112,180,255),(170,10,1610,850)),
 ((15,95,130),(40,255,255),(500,100,1280,790)),
 ((76,35,105),(106,255,255),(480,120,1330,930)),
 ((135,45,95),(179,255,255),(370,100,1240,820)),
 ((0,80,95),(16,255,255),(470,90,1180,830)),
 ((34,45,60),(90,255,255),(440,100,1230,820)),
 ((0,75,85),(17,255,255),(280,20,1320,790)),
 ((76,35,105),(106,255,255),(620,280,1020,700)),
 ((15,80,120),(42,255,255),(260,130,980,850))]
FONT='Chronon3d/assets/fonts/Poppins-Bold.ttf';BODY='Chronon3d/assets/fonts/Poppins-Regular.ttf'
SCENES=[
 ('brazil','Brazil','Brazil','Brasília',(-75,-32,-35,7),(-47.9,-15.8),'#52E2D5','glow_reveal'),
 ('usa','United States','United States of America','Washington, D.C.',(-129,-65,23,51),(-77.04,38.9),'#72D7FF','sweep_in'),
 ('iran','Iran','Iran','Tehran',(43,64,24,41),(51.39,35.69),'#F4C264','gold_focus'),
 ('india','India','India','New Delhi',(67,98,5,38),(77.21,28.61),'#5BE1D0','contour_draw'),
 ('gujarat','Gujarat','India','Ahmedabad',(66,76,18,27),(72.57,23.02),'#F263D5','detail_push'),
 ('italy','Italy','Italy','Rome',(5,20,35,48),(12.5,41.9),'#FF8276','beacon_arrival'),
 ('nigeria','Nigeria','Nigeria','Abuja',(2,15,3,15),(7.49,9.06),'#5EE9AE','neon_bloom'),
 ('china','China','China','Beijing',(73,135,17,54),(116.4,39.9),'#FF6755','slow_reveal'),
 ('korea','South Korea','South Korea','Seoul',(124,132,33,39),(126.98,37.57),'#74CDFF','pin_focus'),
 ('australia','Australia','Australia','Canberra',(111,156,-45,-9),(149.13,-35.28),'#F6BF55','sunset_drift')]

def rgba(h,a=1):
 h=h.lstrip('#');return [int(h[i:i+2],16)/255 for i in (0,2,4)]+[a]
def tr(p,keys,e='out_cubic'):return {'property':p,'easing':e,'keyframes':[{'frame':f,'value':v} for f,v in keys]}
def rings(g):
 if not g:return []
 ps=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
 return [p[0] for p in ps if p]
def clip(r,b):
 w,e,s,n=b;pts=[(float(a),float(c)) for a,c,*_ in r]
 for axis,bound,greater in ((0,w,1),(0,e,0),(1,s,1),(1,n,0)):
  if not pts:break
  out=[];prev=pts[-1];pin=prev[axis]>=bound if greater else prev[axis]<=bound
  for cur in pts:
   cin=cur[axis]>=bound if greater else cur[axis]<=bound
   if cin!=pin:
    den=cur[axis]-prev[axis]
    if den:
     t=(bound-prev[axis])/den;out.append((prev[0]+t*(cur[0]-prev[0]),prev[1]+t*(cur[1]-prev[1])))
   if cin:out.append(cur)
   prev,pin=cur,cin
  pts=out
 return pts if len(pts)>=3 else []
def project(lon,lat,b):
 w,e,s,n=b
 return ((lon-(w+e)/2)/(e-w)*MW,-(lat-(s+n)/2)/(n-s)*MH)
def path_for(feature,b):
 cmd=[];selected=[]
 for r in rings(feature['geometry']):
  pts=clip(r,b)
  if len(pts)>=3:selected.append(pts)
 selected.sort(key=lambda p:abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))),reverse=True)
 for pts in selected[:1]:
  stride=max(1,math.ceil(len(pts)/12));pts=pts[::stride]
  if len(pts)<3:continue
  q=[project(x,y,b) for x,y in pts]
  cmd.append({'type':'move_to','point':list(q[0])});cmd += [{'type':'line_to','point':list(p)} for p in q[1:]];cmd.append({'type':'close'})
 return cmd
def reference_contour(src,index):
 image=cv2.imread(str(src))
 if image is None:raise ValueError(f'cannot read map reference {src}')
 hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV);lo,hi,(x0,y0,x1,y1)=MASKS[index-1]
 mask=cv2.inRange(hsv[y0:y1,x0:x1],np.array(lo,dtype=np.uint8),np.array(hi,dtype=np.uint8))
 mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(11,11)))
 contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
 if not contours:raise ValueError(f'could not detect the highlighted country in {src.name}')
 contour=max(contours,key=cv2.contourArea)
 if cv2.contourArea(contour)<5000:raise ValueError(f'country mask too small for {src.name}')
 contour=contour+np.array([[[x0,y0]]],dtype=np.int32)
 contour=cv2.approxPolyDP(contour,epsilon=7.0,closed=True).reshape(-1,2)
 if len(contour)>12:contour=contour[np.linspace(0,len(contour)-1,12,dtype=int)]
 pts=[(float(x)*W/image.shape[1]-W/2,float(y)*H/image.shape[0]-H/2) for x,y in contour]
 return [{'type':'move_to','point':list(pts[0])}]+[{'type':'line_to','point':list(q)} for q in pts[1:]]+[{'type':'close'}]
def shape(id_,typ,size,pos,body,start=0,dur=N,animation=None):
 d={'id':id_,'type':'shape','size':size,'position':pos,'start_frame':start,'duration_frames':dur,'shape':body}
 if animation:d['animation']={'tracks':animation}
 return d
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',choices=[s[0] for s in SCENES]);ap.add_argument('--render',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
 geo=json.loads(GEO.read_text());features=geo['features'];motions={m['id']:m for m in json.loads(CAT.read_text())['motions'] if m.get('category')=='map_image_v1'}
 items=[]
 for i,(slug,title,admin,capital,bbox,capital_xy,accent,suffix) in enumerate((s for s in SCENES if not a.only or s[0]==a.only),1):
  reference_index=next(n for n,s in enumerate(SCENES,1) if s[0]==slug)
  mid=f'map_image_{slug}_{suffix}';motion=motions[mid]
  motion_tracks=[]
  for t in motion['tracks']:
   keys=[(k['frame'],k['value']) for k in t['keyframes']]
   motion_tracks.append(tr(t['property'],keys,'in_out_sine' if t['property']=='scale' else 'linear'))
  src=ROOT/'assets/map_animation_refs'/f'ref_{reference_index:02d}.png'
  layers=[{'id':f'{slug}-reference-map','type':'image','asset':str(src.relative_to(WORKSPACE)),
    'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':N,'animation':{'tracks':motion_tracks}}]
  outline=reference_contour(src,reference_index)
  # Native Chronon path with no fill: GPU trims the real country/state coastline on.
  path_shape=shape(f'{slug}-outline','shape',[W,H],[CX,CY],{'type':'path','path':outline,
    'fill':[0,0,0,0],'stroke':{'color':accent,'width':5}},animation=[tr('opacity',[(0,0),(8,1)])])
  path_shape['shape']['operators']=[{'kind':'trim','params':{'start':0,'end':1,'animation':{'easing':'out_cubic','keyframes':[{'frame':0,'value':[0,0,0]},{'frame':58,'value':[0,1,0]}]}}}]
  layers.append(path_shape)
  # Native filled ellipses build a soft pulse and a crisp capital pin; no raster text.
  px,py=project(*capital_xy,bbox)
  pinpos=[CX+px,CY+py]
  layers.extend([
   shape(f'{slug}-pulse-a','shape',[72,72],pinpos,{'type':'ellipse','fill':rgba(accent,.18)},0,N,
      [tr('scale',[(0,.28),(35,.28),(63,1.8),(105,2.2)]),tr('opacity',[(0,0),(35,0),(43,.85),(63,.25),(105,0)])]),
   shape(f'{slug}-pulse-b','shape',[48,48],pinpos,{'type':'ellipse','fill':rgba(accent,.25)},0,N,
      [tr('scale',[(0,.25),(48,.25),(70,1.7),(105,2)]),tr('opacity',[(0,0),(48,0),(55,.7),(78,.2),(105,0)])]),
   shape(f'{slug}-pin','shape',[20,20],pinpos,{'type':'ellipse','fill':rgba(accent)},0,N,
      [tr('scale',[(0,.2),(44,.2),(57,1.25),(66,1)]),tr('opacity',[(0,0),(48,0),(55,1)])]),
   {'id':f'{slug}-capital','type':'text','text':capital.upper(),'size':[370,44],
    'position':[max(250,min(1640,CX+px+120)),max(230,min(790,CY+py-36))],
    'start_frame':0,'duration_frames':N,'style':{'font':FONT,'font_size':20,'fill':'#F8F5EB',
      'stroke':{'color':'#102431','width':2}},'animation':{'tracks':[tr('position_x',[(0,34),(67,0)]),tr('opacity',[(0,0),(55,0),(67,1)])]}}
  ])
  # Native editorial title rail animates independently of the photographed map.
  layers.append(shape(f'{slug}-title-rail','shape',[W,192],[CX,940],
    {'type':'rect','fill':[.018,.035,.052,.92]},start=0,dur=N,
    animation=[tr('position_y',[(0,35),(36,0)]),tr('opacity',[(0,0),(18,.96)])]))
  layers.extend([
   {'id':f'{slug}-eyebrow','type':'text','text':'FIELD ATLAS   /   SELECTED REGION','size':[920,28],
    'position':[640,884],'start_frame':20,'duration_frames':130,'style':{'font':BODY,'font_size':16,'fill':accent},
    'animation':{'tracks':[tr('position_x',[(0,-30),(25,0)]),tr('opacity',[(0,0),(18,1)])]}},
   {'id':f'{slug}-title','type':'text','text':title.upper(),'size':[1040,100],'position':[680,960],
    'start_frame':0,'duration_frames':N,'style':{'font':FONT,'font_size':78 if len(title)<14 else 66,'min_font_size':56,'max_font_size':78,
      'fit_mode':'shrink_only','fill':'#F6F2E8'},
    'animation':{'tracks':[tr('position_x',[(0,-90),(39,0)]),tr('opacity',[(0,0),(23,1)])]}},
   {'id':f'{slug}-subline','type':'text','text':f'CAPITAL  /  {capital.upper()}','size':[660,34],
    'position':[1450,965],'start_frame':50,'duration_frames':100,'style':{'font':BODY,'font_size':20,'fill':'#AFC4D1'},
    'animation':{'tracks':[tr('position_x',[(0,45),(18,0)]),tr('opacity',[(0,0),(17,1)])]}}
  ])
  plan={'schema':'chronon.render-plan.v3','version':3,'job_id':mid,
    'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':N},'layers':layers,
    'output':{'path':f'{mid}.mp4','format':'mp4','codec':'h264'}}
  plans=OUT/'plans';plans.mkdir(parents=True,exist_ok=True);pp=plans/f'{mid}.plan.json';pp.write_text(json.dumps(plan,indent=2)+'\n')
  if a.validate or a.render:subprocess.run([str(CLI),'validate','--plan',str(pp),'--assets-root',str(WORKSPACE)],check=True,stdout=subprocess.DEVNULL)
  if a.render:
   renders=OUT/'renders';renders.mkdir(parents=True,exist_ok=True)
   subprocess.run([str(CLI),'render','--plan',str(pp),'--assets-root',str(WORKSPACE),'--output',str(renders/f'{mid}.mp4'),
    '--backend','vulkan','--gpu-hot-path-mode','require_gpu_native','--hardware','nvenc','--encoder-backend','native',
    '--fps',str(FPS),'--rate-control','qp','--qp','20','--encode-preset','p5','--log-level','error'],check=True,stdout=subprocess.DEVNULL)
  items.append({'id':mid,'name':title,'plan':str(pp.relative_to(OUT)),'video':f'renders/{mid}.mp4','native_layers':len(layers)})
 (OUT/'native_manifest.json').write_text(json.dumps({'family':'map_image_v1','canvas':{'width':W,'height':H,'fps':FPS,'duration_seconds':5},'animations':items},indent=2)+'\n')
 print(f'NATIVE_MAP_PASS animations={len(items)} native_chronon_layers=path+ellipses+type 1920x1080 5s')
if __name__=='__main__':main()
