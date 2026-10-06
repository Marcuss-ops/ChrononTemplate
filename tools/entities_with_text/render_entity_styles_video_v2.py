#!/usr/bin/env python3
"""Render six review pages (22 styles) through Vulkan and NVENC."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[2]; WORKSPACE=ROOT.parent; OUT=ROOT/'out/entity_style_recreations_v1'
W,H,FPS,PAGE_FRAMES=1920,1080,30,120
FRAMES=6*PAGE_FRAMES
CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'
def main():
    layers=[]
    for i in range(6):
        layers.append({'id':f'review-page-{i+1:02d}','type':'image','asset':f'entity_style_recreations_v2_page_{i+1:02d}.png',
          'size':[W,H],'fit':'cover','position':[0,0],'start_frame':i*PAGE_FRAMES,'duration_frames':PAGE_FRAMES})
    plan={'schema':'chronon.render-plan.v3','version':3,'job_id':'entity_style_recreations_v2_gpu_review',
      'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},'layers':layers,
      'output':{'path':'entity_style_recreations_v2_gallery_gpu.mp4','format':'mp4','codec':'h264'}}
    pp=OUT/'entity_style_recreations_v2_gallery_gpu.plan.json'; pp.write_text(json.dumps(plan,indent=2)+'\n')
    raw=OUT/'entity_style_recreations_v2_gallery_gpu.nv12'; video=OUT/'entity_style_recreations_v2_gallery_gpu.mp4'
    subprocess.run([str(CLI),'render','--plan',str(pp),'--assets-root',str(OUT),'--backend','vulkan','--profile','preview',
      '--fps',str(FPS),'--video-sink','raw','--pipe-pixfmt','nv12','--chunks','1','--fb-pool-budget-mb','512',
      '--fb-pool-clear-policy','trim-after-job','--start-frame','0','--end-frame',str(FRAMES-1),'-o',str(raw)],cwd=WORKSPACE,check=True)
    if raw.stat().st_size!=FRAMES*W*H*3//2: raise RuntimeError('NV12 frame size check failed')
    subprocess.run(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','nv12','-video_size',f'{W}x{H}',
      '-framerate',str(FPS),'-i',str(raw),'-frames:v',str(FRAMES),'-vsync','cfr','-c:v','h264_nvenc','-preset','p4',
      '-cq','18','-b:v','0','-pix_fmt','yuv420p','-r',str(FPS),str(video)],cwd=WORKSPACE,check=True)
    raw.unlink(); print('VERIFIED_VULKAN_GPU_NVENC',video,FRAMES,FRAMES/FPS,'sec',flush=True)
if __name__=='__main__':main()
