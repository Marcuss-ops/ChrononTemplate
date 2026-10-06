#!/usr/bin/env python3
"""Compile and render the ten map-image animation references through Chronon."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORKSPACE=ROOT.parent
OUT=ROOT/'out/map_image_v1'
CAT=ROOT/'catalog/motion_catalog.v1.json'
CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
FPS=30; W=1920; H=1080; FRAMES=150
ITEMS=[('brazil','Brazil'),('usa','United States'),('iran','Iran'),('india','India'),('gujarat','Gujarat'),('italy','Italy'),('nigeria','Nigeria'),('china','China'),('korea','South Korea'),('australia','Australia')]
SUFFIX={'brazil':'glow_reveal','usa':'sweep_in','iran':'gold_focus','india':'contour_draw','gujarat':'detail_push','italy':'beacon_arrival','nigeria':'neon_bloom','china':'slow_reveal','korea':'pin_focus','australia':'sunset_drift'}
ACCENTS=['#7CE9E4','#8BD8FF','#F7C75D','#79EBDD','#FF55CF','#FF766B','#54F2AE','#FF624F','#79CCFF','#F1B64B']

def main():
    p=argparse.ArgumentParser();p.add_argument('--validate',action='store_true');p.add_argument('--render',action='store_true');p.add_argument('--cli',type=Path,default=CLI);a=p.parse_args()
    cat=json.loads(CAT.read_text()); motions={m['id']:m for m in cat['motions'] if m.get('category')=='map_image_v1'}
    if len(motions)!=10: raise SystemExit(f'expected 10 map_image_v1 motions, got {len(motions)}')
    for i,(slug,name) in enumerate(ITEMS,1):
        motion_id=f'map_image_{slug}_{SUFFIX[slug]}'
        definition=motions[motion_id]
        tracks=[]
        for track in definition['tracks']:
            keys=track['keyframes']; duration=min(FRAMES-1, keys[-1]['frame'])
            tracks.append({'property':track['property'],'easing':track.get('easing','out_cubic'),
                           'keyframes':[{'frame':k['frame'],'value':k['value']} for k in keys if k['frame']<=duration]})
        src=ROOT/'assets/map_animation_refs'/f'ref_{i:02d}.png'
        image={'id':f'{slug}-map','type':'image','asset':str(src.relative_to(WORKSPACE)),
               'size':[W,H],'fit':'cover','position':[0,0],'start_frame':0,'duration_frames':FRAMES,
               'animation':{'tracks':tracks}}
        plan={'schema':'chronon.render-plan.v3','version':3,'job_id':motion_id,
              'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},
              'layers':[image],'output':{'path':f'{motion_id}.mp4','format':'mp4','codec':'h264'}}
        plans=OUT/'plans';plans.mkdir(parents=True,exist_ok=True); dest=plans/f'{motion_id}.plan.json';dest.write_text(json.dumps(plan,indent=2)+'\n')
        if a.validate or a.render:
            subprocess.run([str(a.cli),'validate','--plan',str(dest),'--assets-root',str(WORKSPACE)],check=True)
        if a.render:
            renders=OUT/'renders';renders.mkdir(parents=True,exist_ok=True)
            subprocess.run([str(a.cli),'render','--plan',str(dest),'--assets-root',str(WORKSPACE),
                            '--output',str(renders/f'{motion_id}.mp4'),'--backend','vulkan',
                            '--gpu-hot-path-mode','require_gpu_native','--hardware','nvenc',
                            '--encoder-backend','native','--fps',str(FPS),'--rate-control','qp',
                            '--qp','20','--encode-preset','p1','--log-level','error'],check=True)
    manifest={'family':'map_image_v1','canvas':{'width':W,'height':H,'fps':FPS,'duration_seconds':FRAMES/FPS},
              'animations':[{'id':f'map_image_{slug}_{SUFFIX[slug]}','name':name,'plan':f'plans/map_image_{slug}_{SUFFIX[slug]}.plan.json',
                             'video':f'renders/map_image_{slug}_{SUFFIX[slug]}.mp4','reference':f'assets/map_animation_refs/ref_{i:02d}.png'}
                            for i,(slug,name) in enumerate(ITEMS,1)]}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'MAP_IMAGE_V1_PASS motions={len(ITEMS)} size={W}x{H} duration=5s output={OUT}')
if __name__=='__main__': main()
