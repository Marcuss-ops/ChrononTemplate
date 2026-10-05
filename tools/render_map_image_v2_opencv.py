#!/usr/bin/env python3
"""Render the ten reference map motions from ChrononTemplate's live OpenCV map runtime.

The PNGs are used only for art direction. Every frame is rebuilt from the cached
satellite tile pyramid, an authoritative geographic boundary, and the named
OpenCV animation treatment. No provided reference image is used as a render layer.
"""
from __future__ import annotations
import argparse,json,math,os,sys,subprocess
os.environ["OMP_NUM_THREADS"]="1"
os.environ["OPENCV_NUM_THREADS"]="1"
from pathlib import Path
import cv2
cv2.setNumThreads(1)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent;TEMPLATE=HERE.parent;ROOT=TEMPLATE.parent
sys.path[:0]=[str(ROOT/'Chronon3d/tools/cartography'),str(HERE)]
import dynamic_tile_pyramid as dyn
import fast_plate_sampler as fast
import fast_geo_camera as harness
import geo_runtime as geo
W,H,FPS,N=1920,1080,30,150
GEO=json.loads((TEMPLATE/'catalog/ne_50m_admin_0_countries.geojson').read_text())
GEO1=json.loads((TEMPLATE/'catalog/ne_10m_admin_1_gujarat.geojson').read_text())
SCENES=[
 ('brazil','Brazil','Brazil','Brasilia',(-17.0,-54.5),(-47.9,-15.8),'#52E2D5','glow_reveal',5.0),
 ('usa','United States','United States of America','Washington D.C.',(38.5,-97.0),(-77.04,38.9),'#72D7FF','sweep_in',5.3),
 ('iran','Iran','Iran','Tehran',(32.0,53.7),(51.39,35.69),'#F4C264','gold_focus',6.0),
 ('india','India','India','New Delhi',(22.5,79.0),(77.21,28.61),'#5BE1D0','contour_draw',5.4),
 ('gujarat','Gujarat','Gujarat','Ahmedabad',(22.5,71.6),(72.57,23.02),'#F263D5','detail_push',7.0),
 ('italy','Italy','Italy','Rome',(42.4,12.7),(12.5,41.9),'#FF8276','beacon_arrival',6.8),
 ('nigeria','Nigeria','Nigeria','Lagos',(9.0,8.4),(3.38,6.52),'#5EE9AE','neon_bloom',6.1),
 ('china','China','China','Beijing',(35.8,103.5),(116.4,39.9),'#FF6755','slow_reveal',5.1),
 ('korea','South Korea','South Korea','Seoul',(36.3,127.8),(126.98,37.57),'#74CDFF','pin_focus',7.2),
 ('australia','Australia','Australia','Canberra',(-28.0,131.5),(149.13,-35.28),'#F6BF55','sunset_drift',5.0),
]
ACC=lambda s:tuple(int(s[i:i+2],16) for i in (5,3,1))
def ease(t):
 t=max(0.,min(1.,t));return t*t*(3.-2.*t)
def feature(slug):
 if slug=='gujarat':return GEO1['features'][0]['geometry']
 admin={'usa':'United States of America','korea':'South Korea'}.get(slug,dict((x[0],x[2]) for x in SCENES)[slug])
 return next(f['geometry'] for f in GEO['features'] if f.get('properties',{}).get('ADMIN')==admin)
def rings(g):
 if g['type']=='Polygon':return g['coordinates']
 if g['type']=='MultiPolygon':return [ring for poly in g['coordinates'] for ring in poly]
 raise ValueError(g['type'])
def country_polygons(geom):
 out=[]
 for ring in rings(geom):
  if len(ring)<3:continue
  pts=np.asarray([[p[0],p[1]] for p in ring],dtype=np.float64)
  # Lightweight geographic simplification; final edge is antialiased by OpenCV.
  # Preserve the feature's characteristic shape with at most ~700 points per ring.
  stride=max(1,math.ceil(len(pts)/1600));pts=pts[::stride]
  if len(pts)>=3:out.append(pts)
 return out
class Builder:
 def __init__(self,scene,polygons):
  self.slug,self.title,self.admin,self.capital,self.anchor,self.capital_xy,self.hex,self.motion,self.end_zoom=scene
  self.WIDTH,self.HEIGHT,self.FPS=W,H,FPS;self.TOTAL_FRAMES=N;self.FRAMES_TOTAL=N;self.ZOOM_INDEX=2
  self.ANCHORS=(self.anchor,);self.PREPARE_ZMIN=5;self.PREPARE_ZMAX=math.ceil(self.end_zoom)+1
  self.polygons=polygons;self.accent=ACC(self.hex);self.target_zoom=self.end_zoom
  self.place=geo.Place(query=self.title,display_name=self.title,lat=self.anchor[0],lon=self.anchor[1],ok=True)
  # Use ChrononTemplate's certified tile camera for motion; OpenCV owns map treatments.
  self.camera=geo._ShotBuilder(self.place,'dive',N)
  self.camera.end_zoom=max(5.15,self.end_zoom)
 def pose(self,f):
  # Reuse the named catalog's scale keyframes as the timing law for camera easing.
  motions={m['id']:m for m in json.loads((TEMPLATE/'catalog/motion_catalog.v1.json').read_text())['motions']}
  ident=f'map_image_{self.slug}_'+{'brazil':'glow_reveal','usa':'sweep_in','iran':'gold_focus','india':'contour_draw','gujarat':'detail_push','italy':'beacon_arrival','nigeria':'neon_bloom','china':'slow_reveal','korea':'pin_focus','australia':'sunset_drift'}[self.slug]
  track=next(t for t in motions[ident]['tracks'] if t['property']=='scale');keys=track['keyframes']
  k0,k1=keys[0],keys[-1];pos=min(1.,max(0.,(f-k0['frame'])/max(1,k1['frame']-k0['frame'])))
  # Per-motion keyframe profile determines how quickly the real map camera lands.
  val=k0['value']+(k1['value']-k0['value'])*ease(pos)
  p=1.-(val-k1['value'])/max(1e-6,k0['value']-k1['value'])
  lon=self.anchor[1]+(2.0*p if self.slug=='australia' else 0.0)
  return (self.anchor[0],lon,5.+(max(5.15,self.target_zoom)-5.)*p)
 def _screen(self,lon,lat,zoom):
  z=int(math.floor(zoom));factor=2.**(zoom-z)
  x,y=dyn.latlon_to_global_px(lat,lon,z);ax,ay=dyn.latlon_to_global_px(*getattr(self,'current_center',self.anchor),z)
  return int(round(W/2+(x-ax)*factor)),int(round(H/2+(y-ay)*factor))
 def _screen_polys(self,zoom):
  return [np.asarray([self._screen(float(lon),float(lat),zoom) for lon,lat in poly],dtype=np.int32) for poly in self.polygons]
 def _reveal(self,f):
  # Match the authored catalog's opacity curve on the map treatments.
  ident=f'map_image_{self.slug}_'+{'brazil':'glow_reveal','usa':'sweep_in','iran':'gold_focus','india':'contour_draw','gujarat':'detail_push','italy':'beacon_arrival','nigeria':'neon_bloom','china':'slow_reveal','korea':'pin_focus','australia':'sunset_drift'}[self.slug]
  motions={m['id']:m for m in json.loads((TEMPLATE/'catalog/motion_catalog.v1.json').read_text())['motions']}
  tr=next(t for t in motions[ident]['tracks'] if t['property']=='opacity');ks=tr['keyframes'];
  if f<=ks[0]['frame']:return 0.
  for a,b in zip(ks,ks[1:]):
   if f<=b['frame']:
    p=(f-a['frame'])/max(1,b['frame']-a['frame']);return a['value']+(b['value']-a['value'])*ease(p)
  return float(ks[-1]['value'])
 def _draw_country(self,frame,f,zoom,progress):
  pts=self._screen_polys(zoom);mask=np.zeros((H,W),np.uint8)
  if self.motion=='sweep_in':
   reveal=int(W*min(1.,progress*1.65));cv2.fillPoly(mask,[p for p in pts if len(p)>=3],255);mask[:,reveal:]=0
  else:cv2.fillPoly(mask,[p for p in pts if len(p)>=3],255)
  alpha=self._reveal(f)
  if self.motion=='contour_draw':alpha*=.34+.22*progress
  elif self.motion=='gold_focus':alpha*=.62
  elif self.motion=='detail_push':alpha*=.3
  else:alpha*=.46
  overlay=np.zeros_like(frame);overlay[:]=self.accent
  frame[mask>0]=cv2.addWeighted(frame,1.-alpha,overlay,alpha,0)[mask>0]
  # distinct animated border treatments, all based on authoritative geographic geometry
  edge=np.zeros((H,W),np.uint8)
  if self.motion=='contour_draw':
   for poly in pts:
    if len(poly)<2:continue
    seg=np.sqrt(np.sum(np.diff(poly.astype(np.float64),axis=0)**2,axis=1));total=float(seg.sum())
    budget=total*min(1.,progress*1.45);taken=[]
    for i,d in enumerate(seg):
     if budget<=0:break
     a,b=poly[i],poly[(i+1)%len(poly)];ratio=min(1.,budget/max(1e-6,d));end=(a+(b-a)*ratio).astype(int)
     cv2.line(edge,tuple(a),tuple(end),255,3,cv2.LINE_AA);budget-=d
  else:
   cv2.polylines(edge,[p for p in pts if len(p)>=3],True,255,3,cv2.LINE_AA)
  if self.motion=='sweep_in':edge[:,int(W*min(1.,progress*1.65)):]=0
  # Bright, layered neon rim: broad aura, tight glow, then a clean saturated edge.
  reveal=self._reveal(f);base=frame.astype(np.float32);color=np.asarray(self.accent,dtype=np.float32)[None,None,:]
  for sigma,strength in ((22,.50),(11,.62),(4,.52)):
   halo=cv2.GaussianBlur(edge,(0,0),sigma).astype(np.float32)/255.0
   a=(halo*(strength*reveal))[:,:,None]
   base=base*(1.-a)+color*a
  rim=(edge.astype(np.float32)/255.0*(.96*reveal))[:,:,None]
  bright=np.clip(color*.76+255*.24,0,255)
  base=base*(1.-rim)+bright*rim
  frame[:]=np.clip(base,0,255).astype(np.uint8)
  return pts
 def _draw_pin(self,frame,f,zoom,progress):
  label={'iran':'Tehran','italy':'Rome','nigeria':'Lagos'}.get(self.slug)
  if not label:return
  cx,cy=self._screen(*self.capital_xy,zoom);accent=self.accent
  arrive=ease((progress-.34)/.23)
  if self.motion=='beacon_arrival':arrive=ease((progress-.48)/.22)
  if self.motion=='pin_focus':arrive=ease((progress-.25)/.20)
  if arrive<=0:return
  pulse=.5+.5*math.sin(progress*math.tau*1.65);r=int(22+48*pulse)
  glow=np.zeros((H,W,3),np.uint8);cv2.circle(glow,(cx,cy),r,accent,-1,cv2.LINE_AA);glow=cv2.GaussianBlur(glow,(0,0),16);cv2.addWeighted(frame,1.,glow,.34*arrive,0,dst=frame)
  cv2.circle(frame,(cx,cy),r,(accent[0],accent[1],accent[2]),2,cv2.LINE_AA);cv2.circle(frame,(cx,cy),10,(accent[0],accent[1],accent[2]),-1,cv2.LINE_AA);cv2.circle(frame,(cx,cy),4,(255,255,255),-1,cv2.LINE_AA)
  # Reference pins are crisp white dots with small white geographic labels.
  radius=8 if self.slug=='iran' else 10
  cv2.circle(frame,(cx,cy),radius,(250,250,248),-1,cv2.LINE_AA)
  cv2.circle(frame,(cx,cy),radius+5,(250,250,248),2,cv2.LINE_AA)
  self._text(frame,label,(cx+22,cy+9),27,(250,250,248),bold=True,shadow=True)
 def _text(self,frame,text,xy,size,color,bold=False,shadow=False,center=False):
  canvas=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(canvas)
  path='/home/pierone/.local/share/fonts/Montserrat-Black.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
  font=ImageFont.truetype(path,size=size)
  x,y=xy;box=draw.textbbox((0,0),text,font=font,stroke_width=0);w=box[2]-box[0];h=box[3]-box[1]
  if center:x-=w//2;y-=h//2
  if shadow:draw.text((x,y),text,font=font,fill=color,stroke_width=2,stroke_fill=(8,16,22))
  draw.text((x,y),text,font=font,fill=color,stroke_width=0)
  frame[:]=cv2.cvtColor(np.asarray(canvas),cv2.COLOR_RGB2BGR)
 def _draw_context_labels(self,frame,zoom):
  if self.slug=='iran':
   labels=[('TÜRKİYE',39,35),('SYRIA',35.2,38),('IRAQ',33,44),('TURKMENISTAN',39,59),('AFGHANISTAN',34,66),('KUWAIT',29.5,47.5),('PAKISTAN',29,68),('SAUDI\nARABIA',24,45),('QATAR',25.3,51.2),('U.A.E.',24.4,54.4),('OMAN',21,57),('Caspian\nSea',40.5,51),('Persian\nGulf',26.5,51),('Gulf of\nOman',24.5,59)]
  elif self.slug=='gujarat':
   labels=[('PAKISTAN',26,68),('RAJASTHAN',27,74),('MADHYA\nPRADESH',23,79),('MAHARASHTRA',19,74),('ARABIAN SEA',19,68)]
  else:return
  for label,lat,lon in labels:
   x,y=self._screen(lon,lat,zoom)
   lines=label.split('\n');fs=27 if self.slug=='iran' else 24
   for i,line in enumerate(lines):self._text(frame,line,(x,y+i*(fs+5)),fs,(198,211,218),bold=True,shadow=True,center=True)
 def _draw_title(self,frame,f,progress,pts):
  alpha=ease((progress-.13)/.16)
  if alpha<=0:return
  title={'brazil':'BRASIL','usa':'UNITED STATES','iran':'IRAN','india':'INDIA','gujarat':'Gujarat','italy':'ITALY','nigeria':'NIGERIA','china':'CHINA','korea':'SOUTH KOREA','australia':'AUSTRALIA'}[self.slug]
  mask=np.zeros((H,W),np.uint8);cv2.fillPoly(mask,[p for p in pts if len(p)>=3],255)
  dist=cv2.distanceTransform(mask,cv2.DIST_L2,5);_,radius,_,(safe_x,safe_y)=cv2.minMaxLoc(dist)
  pose_zoom=self.pose(f)[2]
  title_lat,title_lon=(43.25,12.5) if self.slug=='italy' else self.anchor
  cx,cy=self._screen(title_lon,title_lat,pose_zoom)
  if not (0<=cx<W and 0<=cy<H and mask[cy,cx]):cx,cy=safe_x,safe_y
  if self.slug=='korea':
   # The reference places its title outside the peninsula with a fine leader.
   px,py=self._screen(126.98,37.57,self.pose(f)[2]);tx=min(W-400,px+110);ty=py-75
   cv2.circle(frame,(px,py),9,(250,250,248),-1,cv2.LINE_AA)
   cv2.line(frame,(px,py),(tx-14,ty+43),(250,250,248),2,cv2.LINE_AA)
   self._text(frame,title,(tx,ty),28,(250,250,248),bold=True)
   cv2.line(frame,(tx,ty+40),(tx+260,ty+40),(250,250,248),2,cv2.LINE_AA);return
  size=104 if self.slug in ('brazil','usa','iran','india','china','australia') else (88 if self.slug in ('italy','nigeria') else 60)
  row=np.flatnonzero(mask[cy]);segment=[]
  if row.size:
   cuts=np.where(np.diff(row)>1)[0]+1
   for group in np.split(row,cuts):
    if group.size and group[0]<=cx<=group[-1]:segment=group;break
  max_width=max(120,(int(segment[-1]-segment[0]+1)*.84) if len(segment) else radius*2.0)
  font_path='/home/pierone/.local/share/fonts/Montserrat-Black.ttf'
  while size>38 and ImageFont.truetype(font_path,size=size).getbbox(title)[2]>max_width:size-=2
  if self.slug=='gujarat':
   # The reference uses a single map tag instead of a centered country title.
   tag='Gujarat';font=ImageFont.truetype('/home/pierone/.local/share/fonts/Montserrat-Black.ttf',34)
   image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(image);b=draw.textbbox((0,0),tag,font=font);tw=b[2]-b[0]
   x=cx-tw//2-20;y=cy-30;draw.rectangle((x,y,x+tw+40,y+66),fill=(250,250,248));draw.text((x+20,y+8),tag,font=font,fill=(15,18,20));draw.polygon([(cx-15,y+66),(cx+15,y+66),(cx,y+91)],fill=(250,250,248));frame[:]=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR);return
  self._text(frame,title,(cx,cy),size,(250,248,244),bold=True,shadow=False,center=True)
 def render_frame_fast(self,sampler,f):
  lat,lon,zoom=self.pose(f);self.current_center=(lat,lon);frame=sampler.sample(lat,lon,zoom,W,H)
  prog=f/(N-1);pts=self._draw_country(frame,f,zoom,prog);self._draw_context_labels(frame,zoom);self._draw_pin(frame,f,zoom,prog);self._draw_title(frame,f,prog,pts)
  return frame

def render_one(scene,out,workers,block):
 builder=Builder(scene,country_polygons(feature(scene[0])))
 pyramid=dyn.DynamicTilePyramid(provider='esri_sat')
 sampler=fast.FastPlateSampler(pyramid,W,H)
 sampler.prepare(builder.ANCHORS,builder.PREPARE_ZMIN,builder.PREPARE_ZMAX)
 # Every frame must remain on the prepared tile pyramid. No fallback imagery.
 for f in range(N):
  lat,lon,z=builder.pose(f)
  if not sampler.can_sample(lat,lon,z,W,H):raise RuntimeError(f'{scene[0]} frame {f}: prepared imagery does not cover z={z:.2f}')
 geo.gate_builder(builder,sampler,'map-image/'+scene[0])
 return harness.encode_with_pool(builder,sampler,out,workers,block,preset='veryfast',crf=18)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',choices=[s[0] for s in SCENES],action='append');ap.add_argument('--workers',type=int,default=8);ap.add_argument('--block',type=int,default=3);a=ap.parse_args()
 outdir=TEMPLATE/'out/map_image_v1_opencv';(outdir/'renders').mkdir(parents=True,exist_ok=True);items=[]
 for scene in SCENES:
  if a.only and scene[0] not in a.only:continue
  out=outdir/'renders'/f'map_image_{scene[0]}_{scene[7]}.mp4'
  print(f'[map-image-opencv] {scene[1]} start, target zoom={scene[8]}',flush=True)
  stat=render_one(scene,out,a.workers,a.block)
  items.append({'id':f'map_image_{scene[0]}_{scene[7]}','name':scene[1],'video':str(out.relative_to(outdir)),'native_text':'OpenCV','map_source':'ChrononTemplate DynamicTilePyramid','frames':N,'dimensions':[W,H],'seconds':5,'stats':stat})
  print(f'[map-image-opencv] {scene[1]} pass {stat["bytes"]} bytes',flush=True)
 all_items=[]
 for scene in SCENES:
  f=outdir/'renders'/f'map_image_{scene[0]}_{scene[7]}.mp4'
  if f.is_file() and f.stat().st_size>0:all_items.append({'id':f'map_image_{scene[0]}_{scene[7]}','name':scene[1],'video':str(f.relative_to(outdir)),'map_source':'ChrononTemplate DynamicTilePyramid','renderer':'OpenCV','frames':N,'dimensions':[W,H],'fps':FPS,'seconds':5})
 (outdir/'manifest.json').write_text(json.dumps({'family':'map_image_v1','renderer':'ChrononTemplate OpenCV DynamicTilePyramid/FastPlateSampler','reference_images_used_as':'art direction only; excluded from video frames','canvas':[W,H,FPS],'duration_seconds':5,'animations':all_items},indent=2)+'\n')
 print('MAP_IMAGE_OPENCV_PASS',len(items),flush=True)
if __name__=='__main__':main()
