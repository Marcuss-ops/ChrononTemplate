#!/usr/bin/env python3
"""Build map preview clips from native Chronon paths, shapes, and text."""
from __future__ import annotations
import argparse, json, math, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORKSPACE=ROOT.parent
GEO=ROOT/'catalog/ne_50m_admin_0_countries.geojson'
CAT=ROOT/'catalog/motion_catalog.v1.json'
OUT=ROOT/'out/map_image_v1'
CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
W,H,FPS,FRAMES=1920,1080,30,150
MAP_CX,MAP_CY=960,548
MAP_W,MAP_H=1500,690
FONT='Chronon3d/assets/fonts/Poppins-Bold.ttf'
BODY='Chronon3d/assets/fonts/Poppins-Regular.ttf'
SCENES=[
 ('brazil','Brazil','Brazil','Brasília',(-75,-32,-35,7),(-47.9,-15.8),'#48E0D1','glow_reveal'),
 ('usa','United States','United States of America','Washington, D.C.',(-129,-65,23,51),(-77.04,38.9),'#64C9FF','sweep_in'),
 ('iran','Iran','Iran','Tehran',(43,64,24,41),(51.39,35.69),'#F4BD54','gold_focus'),
 ('india','India','India','New Delhi',(67,98,5,38),(77.21,28.61),'#51D9C7','contour_draw'),
 ('gujarat','Gujarat','India','Ahmedabad',(66,76,18,27),(72.57,23.02),'#F14ECD','detail_push'),
 ('italy','Italy','Italy','Rome',(5,20,35,48),(12.5,41.9),'#FF7469','beacon_arrival'),
 ('nigeria','Nigeria','Nigeria','Abuja',(2,15,3,15),(7.49,9.06),'#54E3A5','neon_bloom'),
 ('china','China','China','Beijing',(73,135,17,54),(116.4,39.9),'#FF604F','slow_reveal'),
 ('korea','South Korea','South Korea','Seoul',(124,132,33,39),(126.98,37.57),'#62C5FF','pin_focus'),
 ('australia','Australia','Australia','Canberra',(111,156,-45,-9),(149.13,-35.28),'#F5B542','sunset_drift'),
]

def rgba(hex_color,alpha=1):
 h=hex_color.lstrip('#');return [int(h[i:i+2],16)/255 for i in (0,2,4)]+[alpha]

def track(prop,keys,easing='out_cubic'):
 return {'property':prop,'easing':easing,'keyframes':[{'frame':f,'value':v} for f,v in keys]}

def geom_rings(g):
 if not g:return []
 if g['type']=='Polygon': polys=[g['coordinates']]
 elif g['type']=='MultiPolygon': polys=g['coordinates']
 else:return []
 return [poly[0] for poly in polys if poly]

def clip_ring(ring,bbox):
 west,east,south,north=bbox
 pts=[(float(p[0]),float(p[1])) for p in ring]
 edges=[(0,west,True),(0,east,False),(1,south,True),(1,north,False)]
 for axis,bound,keep_greater in edges:
  if not pts:break
  result=[];prev=pts[-1];prev_in=(prev[axis]>=bound if keep_greater else prev[axis]<=bound)
  for cur in pts:
   cur_in=(cur[axis]>=bound if keep_greater else cur[axis]<=bound)
   if cur_in!=prev_in:
    den=cur[axis]-prev[axis]
    if abs(den)>1e-12:
     t=(bound-prev[axis])/den; cross=(prev[0]+t*(cur[0]-prev[0]),prev[1]+t*(cur[1]-prev[1]))
     result.append(cross)
   if cur_in:result.append(cur)
   prev,prev_in=cur,cur_in
  pts=result
 return pts if len(pts)>=3 else []

def scene_project(lon,lat,bbox):
 west,east,south,north=bbox; midlat=(south+north)/2
 coslat=max(.22,math.cos(math.radians(midlat)))
 x=(lon-(west+east)/2)*coslat; y=-(lat-(south+north)/2)
 raww=max(1,(east-west)*coslat); rawh=max(1,north-south)
 scale=min(MAP_W/raww,MAP_H/rawh)
 return x*scale,y*scale

def path_commands(rings,bbox):
 commands=[]
 for ring in rings:
  clipped=clip_ring(ring,bbox)
  if not clipped:continue
  # Bounded decimation keeps plans small while retaining recognizable coastlines.
  stride=max(1,math.ceil(len(clipped)/320));clipped=clipped[::stride]
  if len(clipped)<3:continue
  points=[scene_project(x,y,bbox) for x,y in clipped]
  commands.append({'type':'move_to','point':list(points[0])})
  commands.extend({'type':'line_to','point':list(p)} for p in points[1:])
  commands.append({'type':'close'})
 return commands

def shape(id_,commands,fill,stroke,width=1,tracks=None):
 d={'id':id_,'type':'shape','size':[W,H],'position':[MAP_CX,MAP_CY],
    'start_frame':0,'duration_frames':FRAMES,
    'shape':{'type':'path','path':commands,'fill':rgba(fill) if fill else [0,0,0,0],
             'stroke':{'color':stroke,'width':width}}}
 if tracks:d['animation']={'tracks':tracks}
 return d

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',choices=[s[0] for s in SCENES]);ap.add_argument('--render',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
 geo=json.loads(GEO.read_text());cat=json.loads(CAT.read_text())
 motions={m['id']:m for m in cat['motions'] if m.get('category')=='map_image_v1'}
 features=geo['features'];OUT.mkdir(parents=True,exist_ok=True)
 chosen=[s for s in SCENES if not a.only or s[0]==a.only]
 manifest=[]
 for idx,(slug,title,admin,capital,bbox,capital_xy,accent,suffix) in enumerate(chosen):
  motion_id=f'map_image_{slug}_{suffix}';motion=motions[motion_id]
  map_tracks=[]
  for t in motion['tracks']:
   # Keep the authored catalog camera move, retargeted from a raster to every native land path.
   prop=t['property'];keys=t['keyframes']
   if prop=='opacity':
    map_tracks.append(track('opacity',[(k['frame'],k['value']) for k in keys],'linear'))
   elif prop=='scale':
    map_tracks.append(track('scale',[(k['frame'],k['value']) for k in keys],'in_out_sine'))
  layers=[{'id':'night-atlas','type':'color','color':[.012,.025,.039,1],
           'size':[W,H],'screen_space':True,'start_frame':0,'duration_frames':FRAMES}]
  # Native cartographic graticule, horizon marks, and technical frame.
  for n in range(1,5):
   x=-MAP_W/2+n*MAP_W/5
   layers.append({'id':f'grid-meridian-{n}','type':'shape','size':[W,H],'position':[MAP_CX,MAP_CY],
    'start_frame':0,'duration_frames':FRAMES,'shape':{'type':'path','path':[{'type':'move_to','point':[x,-MAP_H/2]},{'type':'line_to','point':[x,MAP_H/2]}],
    'fill':[0,0,0,0],'stroke':{'color':'#294253','width':1}}})
  for n in range(1,4):
   y=-MAP_H/2+n*MAP_H/4
   layers.append({'id':f'grid-parallel-{n}','type':'shape','size':[W,H],'position':[MAP_CX,MAP_CY],
    'start_frame':0,'duration_frames':FRAMES,'shape':{'type':'path','path':[{'type':'move_to','point':[-MAP_W/2,y]},{'type':'line_to','point':[MAP_W/2,y]}],
    'fill':[0,0,0,0],'stroke':{'color':'#294253','width':1}}})
  west,east,south,north=bbox
  focus=next((f for f in features if f.get('properties',{}).get('ADMIN')==admin),None)
  if not focus:raise ValueError(f'No Natural Earth feature: {admin}')
  for f in features:
   props=f.get('properties',{});name=props.get('ADMIN','')
   bounds=props
   rings=geom_rings(f.get('geometry'))
   if not rings:continue
   cmd=path_commands(rings,bbox)
   if not cmd:continue
   is_focus=(name==admin)
   fill=accent if is_focus else '#183247'
   stroke=accent if is_focus else '#527083'
   fillalpha=.39 if is_focus else .8
   d=shape(f'land-{slug}-{props.get("ADM0_A3","x")}',cmd,None,stroke,3.0 if is_focus else 1.15,map_tracks)
   d['shape']['fill']=rgba(fill,fillalpha)
   if is_focus:
    # A second native path traces the real selected-country coastline.
    trace=shape(f'coastline-trace-{slug}',cmd,None,accent,5.5,
      [track('opacity',[(0,0),(10,1),(FRAMES-1,1)])])
    trace['shape']['operators']=[{'kind':'trim','params':{'start':0,'end':1,'animation':{'easing':'out_cubic','keyframes':[{'frame':0,'value':[0,0,0]},{'frame':58,'value':[0,1,0]}]}}}]
    layers.append(d);layers.append(trace)
    # Disciplined interior glow, target pin, and marker pulse use only native shapes.
    px,py=scene_project(*capital_xy,bbox)
    pulse={'id':f'capital-pulse-{slug}','type':'shape','size':[76,76],'position':[MAP_CX+px,MAP_CY+py],
      'start_frame':34,'duration_frames':FRAMES-34,'shape':{'type':'ellipse','fill':[0,0,0,0],
      'stroke':{'color':accent,'width':2.2}},'animation':{'tracks':[track('scale',[(0,.35),(26,1.5),(70,1.9)],'out_cubic'),track('opacity',[(0,.85),(28,.18),(70,0)])]}}
    pin={'id':f'capital-pin-{slug}','type':'shape','size':[20,20],'position':[MAP_CX+px,MAP_CY+py],
      'start_frame':36,'duration_frames':FRAMES-36,'shape':{'type':'ellipse','fill':rgba(accent),
      'stroke':{'color':'#F7F4EA','width':2}},'animation':{'tracks':[track('scale',[(0,.2),(13,1.2),(22,1)],'out_back'),track('opacity',[(0,0),(7,1)])]}}
    layers.extend([pulse,pin])
    label_x=max(300,min(1620,MAP_CX+px+120));label_y=max(260,min(785,MAP_CY+py-34))
    layers.append({'id':f'capital-label-{slug}','type':'text','text':capital.upper(),
      'size':[340,42],'position':[label_x,label_y],'start_frame':42,'duration_frames':FRAMES-42,
      'style':{'font':FONT,'font_size':19,'fill':'#F5F1E5','stroke':{'color':'#102432','width':2}},
      'animation':{'tracks':[track('position_x',[(0,28),(17,0)]),track('opacity',[(0,0),(12,1)])]}})
   else:layers.append(d)
  if slug=='gujarat':
   # The admin-1 state is absent from Natural Earth admin-0; draw an approximate
   # native vector inset over western India and call it out as Gujarat.
   gx=[(68.2,23.8),(68.8,22.5),(69.1,21.3),(70.1,20.7),(70.7,21.5),(71.8,21.8),(72.3,22.5),(73.3,22.1),(74.2,22.3),(74.5,23.1),(73.7,24.1),(72.8,24.5),(72.0,24.7),(71.4,24.2),(70.5,24.6),(69.5,24.3),(68.6,24.5)]
   gpoints=[scene_project(x,y,bbox) for x,y in gx]
   gpath=[{'type':'move_to','point':list(gpoints[0])}]+[{'type':'line_to','point':list(p)} for p in gpoints[1:]]+[{'type':'close'}]
   layers.append(shape('gujarat-native-outline',gpath,accent,accent,3.2,[track('opacity',[(0,0),(34,1)])]))
  # Native type layers: eyebrow, animated country headline, place detail, and footer.
  anims=[([('position_y',[(0,36),(34,0)]),('opacity',[(0,0),(16,1)])]),
         ([('position_x',[(0,74),(31,0)]),('opacity',[(0,0),(14,1)])]),
         ([('scale',[(0,.82),(30,1.03),(42,1)]),('opacity',[(0,0),(15,1)])]),
         ([('position_y',[(0,-30),(32,0)]),('opacity',[(0,0),(14,1)])]),
         ([('scale',[(0,.9),(26,1.04),(39,1)]),('opacity',[(0,0),(18,1)])])]
  variants={'brazil':0,'usa':1,'iran':2,'india':3,'gujarat':4,'italy':0,'nigeria':1,'china':2,'korea':3,'australia':4}
  title_tracks=[track(p,k,'out_cubic' if p!='opacity' else 'linear') for p,k in anims[variants[slug]]]
  layers.extend([
   {'id':f'atlas-kicker-{slug}','type':'text','text':'CHRONON  /  FIELD ATLAS','size':[560,30],'position':[MAP_CX,96],
    'start_frame':0,'duration_frames':FRAMES,'style':{'font':BODY,'font_size':16,'fill':accent},
    'animation':{'tracks':[track('opacity',[(0,0),(16,1)])]}},
   {'id':f'country-title-{slug}','type':'text','text':title.upper(),'size':[1050,132],'position':[MAP_CX,MAP_CY+65],
    'start_frame':0,'duration_frames':FRAMES,'style':{'font':FONT,'font_size':104 if len(title)<13 else 82,'min_font_size':66,'max_font_size':104,
      'fit_mode':'shrink_only','fill':'#F7F4EA','stroke':{'color':'#112638','width':2},
      'glow':{'radius':18,'intensity':.24,'threshold':0,'falloff':1,'core_strength':.28,'aura_strength':.14,'bloom_strength':.05}},
    'animation':{'tracks':title_tracks}},
   {'id':f'country-coordinate-{slug}','type':'text','text':f'{title.upper()}  /  {north:.0f}°N — {south:.0f}°S' if north*south<0 else f'{title.upper()}  /  {west:.0f}° — {east:.0f}°',
    'size':[680,30],'position':[MAP_CX,980],'start_frame':27,'duration_frames':FRAMES-27,
    'style':{'font':BODY,'font_size':15,'fill':'#9FB5C4'},'animation':{'tracks':[track('opacity',[(0,0),(18,.9)])]}}
  ])
  plan={'schema':'chronon.render-plan.v3','version':3,'job_id':motion_id,
    'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},
    'layers':layers,'output':{'path':f'{motion_id}.mp4','format':'mp4','codec':'h264'}}
  plans=OUT/'plans';plans.mkdir(parents=True,exist_ok=True);pp=plans/f'{motion_id}.plan.json';pp.write_text(json.dumps(plan,indent=2)+'\n')
  if a.validate or a.render:subprocess.run([str(CLI),'validate','--plan',str(pp),'--assets-root',str(WORKSPACE)],check=True,stdout=subprocess.DEVNULL)
  if a.render:
   renders=OUT/'renders';renders.mkdir(parents=True,exist_ok=True);dest=renders/f'{motion_id}.mp4'
   subprocess.run([str(CLI),'render','--plan',str(pp),'--assets-root',str(WORKSPACE),'--output',str(dest),
     '--backend','vulkan','--gpu-hot-path-mode','require_gpu_native','--hardware','nvenc','--encoder-backend','native',
     '--fps',str(FPS),'--rate-control','qp','--qp','20','--encode-preset','p5','--log-level','error'],check=True,stdout=subprocess.DEVNULL)
  manifest.append({'id':motion_id,'name':title,'plan':str(pp.relative_to(OUT)),'video':f'renders/{motion_id}.mp4','native_layers':len(layers)})
 (OUT/'native_manifest.json').write_text(json.dumps({'family':'map_image_v1_native','canvas':{'width':W,'height':H,'fps':FPS,'duration_seconds':5},'animations':manifest},indent=2)+'\n')
 print(f'NATIVE_MAP_PASS scenes={len(manifest)} layers_each=vector+type 1920x1080 5s')

if __name__=='__main__':main()
