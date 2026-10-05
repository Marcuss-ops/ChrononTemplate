#!/usr/bin/env python3
"""Render the 13-style contact sheet as a slow Vulkan GPU pan for review."""
from pathlib import Path
import json, subprocess

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parent
OUT=ROOT/'out/entity_style_recreations_v1'
SRC='entity_style_recreations_v1_contact_sheet.png'
W,H,FPS,FRAMES=1920,1080,30,1380
CLI=WORKSPACE/'Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli'

def main():
    # 46 seconds: start at the first row, pan through all 13 stills, end on the last row.
    plan={'schema':'chronon.render-plan.v3','version':3,'job_id':'entity_style_recreations_gallery_gpu',
      'canvas':{'width':W,'height':H,'fps_num':FPS,'fps_den':1,'duration_frames':FRAMES},
      'layers':[{'id':'style-contact-sheet','type':'image','asset':SRC,'size':[W,2910],
        'fit':'cover','position':[0,900],'start_frame':0,'duration_frames':FRAMES,
        'animation':{'tracks':[{'property':'position_y','easing':'linear','keyframes':[
          {'frame':0,'value':900},{'frame':690,'value':0},{'frame':FRAMES-1,'value':-900}]}]}}],
      'output':{'path':'entity_style_recreations_v1_gallery_gpu.mp4','format':'mp4','codec':'h264'}}
    pp=OUT/'entity_style_recreations_v1_gallery_gpu.plan.json'; pp.write_text(json.dumps(plan,indent=2)+'\n')
    raw=OUT/'entity_style_recreations_v1_gallery_gpu.nv12'; video=OUT/'entity_style_recreations_v1_gallery_gpu.mp4'
    subprocess.run([str(CLI),'render','--plan',str(pp),'--assets-root',str(OUT),'--backend','vulkan','--profile','preview',
      '--fps',str(FPS),'--video-sink','raw','--pipe-pixfmt','nv12','--chunks','1','--fb-pool-budget-mb','512',
      '--fb-pool-clear-policy','trim-after-job','--start-frame','0','--end-frame',str(FRAMES-1),'-o',str(raw)],cwd=WORKSPACE,check=True)
    if raw.stat().st_size!=FRAMES*W*H*3//2: raise RuntimeError('NV12 frame size check failed')
    subprocess.run(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','nv12','-video_size',f'{W}x{H}',
      '-framerate',str(FPS),'-i',str(raw),'-frames:v',str(FRAMES),'-vsync','cfr','-c:v','h264_nvenc','-preset','p4',
      '-cq','18','-b:v','0','-pix_fmt','yuv420p','-r',str(FPS),str(video)],cwd=WORKSPACE,check=True)
    raw.unlink(); print('VERIFIED_VULKAN_GPU_NVENC',video,FRAMES,FRAMES/FPS,'sec')

if __name__=='__main__': main()
