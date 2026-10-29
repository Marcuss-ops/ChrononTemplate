#!/usr/bin/env python3
"""Build a vintage crime-dossier portrait animation and render selected PNG frames."""
from __future__ import annotations
import argparse, importlib.util, json, os, subprocess
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
WORKSPACE = TEMPLATE.parent
OUT_DEFAULT = TEMPLATE / "out/carmine_galante_archive_v1"
FRAMES = 150
ASSET = "ChrononTemplate/assets/carmine_galante_v1/carmine_galante_1947_print.png"
BOARD = "ChrononTemplate/assets/carmine_galante_v1/galante_caseboard.png"
FONT = "ChrononTemplate/assets/fonts/"
_spec = importlib.util.spec_from_file_location(
    "entity_presentation_v1", TEMPLATE / "tools/entities_with_text/build_entity_presentation_v1.py")
assert _spec and _spec.loader
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)


def build_plan() -> dict:
    layers = [
        {"id":"caseboard","type":"image","asset":BOARD,"size":[1920,1080],
         "position":[0,0],"fit":"cover","start_frame":0,"duration_frames":FRAMES},
        BASE.color_layer("left-rule",[5,850],[97,555],0,FRAMES,[0.64,0.15,0.16,1]),
    ]
    mat={"id":"photo-mat","type":"color","color":[0.76,0.69,0.55,1],"size":[604,834],
         "position":BASE.renderer_center_position([525,560]),"start_frame":0,"duration_frames":FRAMES,
         "animation":{"tracks":[BASE.track("opacity",[(0,0),(16,1),(149,1)]),
                                  BASE.track("position_x",[(0,-35),(50,0),(149,0)])]}}
    layers.append(mat)
    portrait={"id":"galante-1947-mugshot","type":"image","asset":ASSET,"size":[574,804],"fit":"cover",
              "position":BASE.renderer_center_position([525,560]),"start_frame":0,"duration_frames":FRAMES,
              "animation":{"tracks":[BASE.track("opacity",[(0,0),(20,1),(149,1)]),
                                       BASE.track("scale",[(0,.90),(61,1.045),(89,1),(149,1)]),
                                       BASE.track("position_x",[(0,-52),(57,0),(149,0)])]},
              "effects":[{"type":"catalog","effect_id":"color.contrast","params":[{"param":"value","value":1.14}]},
                         {"type":"vignette","radius":0.76,"softness":0.48,"amount":0.16},
                         {"type":"noise","amount":0.022,"seed":1947,"animated":False,"size":1.0,"color_mode":"monochrome"}]}
    layers.append(portrait)
    layers += [
        BASE.layer_text("file-header","NYPD  /  IDENTIFICATION PHOTOGRAPH",[840,30],[1390,215],0,FRAMES,
                        font=FONT+"Inter-Bold.ttf",font_size=18,fill="#CDBB94",
                        tracks=[BASE.track("opacity",[(0,0),(20,1),(149,1)])]),
        BASE.layer_text("name-first","CARMINE",[900,152],[1378,380],0,FRAMES,
                        font=FONT+"Anton-Regular.ttf",font_size=118,min_font_size=118,fill="#E9E1D1",
                        tracks=[BASE.track("opacity",[(0,0),(36,1),(149,1)]),
                                BASE.track("position_x",[(0,55),(54,0),(149,0)])]),
        BASE.layer_text("name-last","GALANTE",[900,152],[1378,520],12,FRAMES-12,
                        font=FONT+"Anton-Regular.ttf",font_size=118,min_font_size=118,fill="#E9E1D1",
                        tracks=[BASE.track("opacity",[(0,0),(42,1),(137,1)]),
                                BASE.track("position_x",[(0,64),(55,0),(137,0)])]),
        BASE.color_layer("red-stamp",[384,5],[1195,646],34,FRAMES-34,[0.72,0.16,0.17,1],
                         [BASE.track("scale",[(0,0),(35,1),(115,1)])]),
        BASE.color_layer("cigar-tag-plate",[286,58],[1120,735],54,FRAMES-54,[0.63,0.11,0.13,1]),
        BASE.layer_text("cigar-tag","THE CIGAR",[265,42],[1120,735],54,FRAMES-54,
                        font=FONT+"Inter-ExtraBold.ttf",font_size=24,min_font_size=24,fill="#F2E9D7",
                        tracks=[BASE.track("opacity",[(0,0),(18,1),(95,1)])]),
        BASE.layer_text("family","BONANNO FAMILY  /  NEW YORK",[700,36],[1300,835],72,FRAMES-72,
                        font=FONT+"Inter-SemiBold.ttf",font_size=22,min_font_size=22,fill="#C8B999",
                        tracks=[BASE.track("opacity",[(0,0),(28,1),(77,1)])]),
        BASE.layer_text("date","1947  ·  NYPD MUGSHOT",[700,34],[1300,900],87,FRAMES-87,
                        font=FONT+"Inter-Bold.ttf",font_size=19,min_font_size=19,fill="#D7D0C2",
                        tracks=[BASE.track("opacity",[(0,0),(24,1),(62,1)])]),
        BASE.layer_text("credit","PHOTO: NEW YORK POLICE DEPARTMENT  /  PUBLIC DOMAIN",[720,28],[1290,1012],0,FRAMES,
                        font=FONT+"Inter-Regular.ttf",font_size=14,fill="#8F887A"),
        BASE.layer_text("case-id","CASE FILE  ·  47—09",[260,28],[1755,105],0,FRAMES,
                        font=FONT+"Inter-Bold.ttf",font_size=15,fill="#B7A98D"),
    ]
    plan=BASE.scene_plan("carmine_galante_archive_v1",layers,FRAMES)
    plan["output"]={"path":"carmine_galante_archive_v1.mp4","format":"mp4","codec":"h264"}
    return plan


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli",type=Path,default=Path(os.environ.get("CHRONON_CLI",WORKSPACE/"Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")))
    parser.add_argument("--assets-root",type=Path,default=WORKSPACE)
    parser.add_argument("--out",type=Path,default=OUT_DEFAULT)
    parser.add_argument("--frames",type=int,nargs="+",default=[18,40,64,92,120,149])
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    plan_path=args.out/"carmine_galante_archive_v1.plan.json"
    plan_path.write_text(json.dumps(build_plan(),indent=2)+"\n",encoding="utf-8")
    cli=args.cli.resolve();assets=args.assets_root.resolve()
    subprocess.run([str(cli),"validate","--plan",str(plan_path),"--assets-root",str(assets),"--profile","preview"],check=True,cwd=WORKSPACE)
    for frame in args.frames:
        if not 0<=frame<FRAMES: raise SystemExit(f"invalid frame {frame}")
        raw=args.out/f"galante_{frame:03d}.rgba";png=args.out/f"carmine_galante_{frame:03d}.png"
        subprocess.run([str(cli),"render","--backend","software","--plan",str(plan_path),"--assets-root",str(assets),"--video-sink","raw","--pipe-pixfmt","rgba","--start-frame",str(frame),"--end-frame",str(frame),"-o",str(raw)],check=True,cwd=WORKSPACE)
        subprocess.run(["ffmpeg","-y","-v","error","-f","rawvideo","-pixel_format","rgba","-video_size","1920x1080","-i",str(raw),"-frames:v","1",str(png)],check=True,cwd=WORKSPACE)
        raw.unlink();print(png)
    return 0

if __name__=="__main__":raise SystemExit(main())
