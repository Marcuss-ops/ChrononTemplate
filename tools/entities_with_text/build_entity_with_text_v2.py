#!/usr/bin/env python3
"""Build a renderer-native Steve Jobs entity + title motion study, V2."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
OUT = TEMPLATE / "out/entity_with_text_v2"
ASSET = "ChrononTemplate/out/modern_entities_with_text/assets/nobox_steve_cutout_bw.png"
FONT = "ChrononTemplate/assets/fonts/Inter-Bold.ttf"
FPS = 30
FRAMES = 150

_builder_spec = importlib.util.spec_from_file_location(
    "entity_presentation_v1_builder", TEMPLATE / "tools/entities_with_text/build_entity_presentation_v1.py")
assert _builder_spec and _builder_spec.loader
BASE = importlib.util.module_from_spec(_builder_spec)
_builder_spec.loader.exec_module(BASE)

# The first ten names deliberately map V1 ideas into a more legible, coherent
# hero-card composition. The five appended recipes explore camera/depth,
# archival framing and split-layout options without rasterizing the name.
RECIPES = [
    {"id":"entity_v2_caption_rise","source":"entity_caption_rise","image":[("opacity",[(0,0),(28,1),(149,1)]),("scale",[(0,.92),(56,1),(149,1)])],"title":[("opacity",[(0,0),(42,1),(149,1)]),("position_y",[(0,42),(50,0),(149,0)])],"layout":"lower"},
    {"id":"entity_v2_depth_settle","source":"entity_depth_caption","image":[("opacity",[(0,0),(32,1),(149,1)]),("position_z",[(0,150),(62,0),(149,0)]),("scale",[(0,.91),(62,1),(149,1)])],"title":[("opacity",[(0,0),(48,1),(149,1)]),("position_z",[(0,82),(54,0),(149,0)])],"layout":"lower"},
    {"id":"entity_v2_yaw_reveal","source":"entity_yaw_caption","image":[("opacity",[(0,0),(34,1),(149,1)]),("rotation_y",[(0,-16),(58,2),(82,0),(149,0)]),("position_z",[(0,-90),(60,0),(149,0)])],"title":[("opacity",[(0,0),(50,1),(149,1)]),("position_x",[(0,36),(58,0),(149,0)])],"layout":"lower"},
    {"id":"entity_v2_split_name","source":"entity_split_side","image":[("opacity",[(0,0),(26,1),(149,1)]),("position_x",[(0,-190),(58,0),(149,0)]),("scale",[(0,.94),(58,1),(149,1)])],"title":[("opacity",[(0,0),(42,1),(149,1)]),("position_x",[(0,150),(68,0),(149,0)])],"layout":"split"},
    {"id":"entity_v2_frame_then_name","source":"entity_border_then_caption","image":[("opacity",[(0,0),(32,0),(50,1),(149,1)]),("scale",[(0,.96),(55,1),(149,1)])],"title":[("opacity",[(0,0),(44,0),(62,1),(149,1)]),("position_y",[(0,25),(65,0),(149,0)])],"layout":"lower"},
    {"id":"entity_v2_focus_frame","source":"entity_focus_frame","image":[("opacity",[(0,0),(32,1),(149,1)]),("scale",[(0,.96),(55,1.035),(78,1),(149,1)])],"title":[("opacity",[(0,0),(48,1),(149,1)]),("scale",[(0,.94),(60,1),(149,1)])],"layout":"lower"},
    {"id":"entity_v2_glow_focus","source":"entity_glow_focus","image":[("opacity",[(0,0),(36,1),(149,1)]),("scale",[(0,.9),(60,1.025),(82,1),(149,1)])],"title":[("opacity",[(0,0),(52,1),(149,1)]),("position_y",[(0,24),(62,0),(149,0)])],"layout":"lower","glow":True},
    {"id":"entity_v2_name_underline","source":"entity_name_underline","image":[("opacity",[(0,0),(30,1),(149,1)]),("position_y",[(0,32),(54,0),(149,0)])],"title":[("opacity",[(0,0),(44,1),(149,1)]),("position_y",[(0,18),(58,0),(149,0)])],"layout":"lower","underline":True},
    {"id":"entity_v2_name_pill","source":"entity_name_pill","image":[("opacity",[(0,0),(30,1),(149,1)]),("scale",[(0,.94),(55,1),(149,1)])],"title":[("opacity",[(0,0),(42,1),(149,1)]),("scale",[(0,.86),(54,1.04),(68,1),(149,1)])],"layout":"lower","pill":True},
    {"id":"entity_v2_parallax_caption","source":"entity_parallax_caption","image":[("opacity",[(0,0),(30,1),(149,1)]),("position_x",[(0,-30),(149,22)])],"title":[("opacity",[(0,0),(46,1),(149,1)]),("position_x",[(0,45),(149,-28)])],"layout":"lower"},
    {"id":"entity_v2_monumental_push","source":"new_monumental_camera_push","image":[("opacity",[(0,0),(36,1),(149,1)]),("position_z",[(0,190),(82,-30),(112,0),(149,0)]),("scale",[(0,.86),(86,1.04),(112,1),(149,1)])],"title":[("opacity",[(0,0),(62,1),(149,1)]),("scale",[(0,.9),(74,1),(149,1)]),("position_y",[(0,48),(76,0),(149,0)])],"layout":"monumental"},
    {"id":"entity_v2_archive_filmstrip","source":"new_archive_filmstrip_reveal","image":[("opacity",[(0,0),(42,1),(149,1)]),("position_x",[(0,220),(70,0),(149,-8)])],"title":[("opacity",[(0,0),(55,1),(149,1)]),("position_x",[(0,-170),(76,0),(149,0)])],"layout":"split","archive":True},
    {"id":"entity_v2_dual_depth_lockup","source":"new_dual_depth_lockup","image":[("opacity",[(0,0),(34,1),(149,1)]),("position_z",[(0,-120),(65,0),(149,0)]),("rotation_y",[(0,10),(58,0),(149,0)])],"title":[("opacity",[(0,0),(53,1),(149,1)]),("position_z",[(0,120),(72,0),(149,0)])],"layout":"lower"},
    {"id":"entity_v2_quote_annotation","source":"new_documentary_annotation","image":[("opacity",[(0,0),(36,1),(149,1)]),("scale",[(0,.94),(60,1),(149,1)])],"title":[("opacity",[(0,0),(54,1),(149,1)]),("position_y",[(0,30),(70,0),(149,0)])],"layout":"annotation","annotation":True},
    {"id":"entity_v2_silhouette_reveal","source":"new_silhouette_color_reveal","image":[("opacity",[(0,0),(18,0),(50,1),(149,1)]),("scale",[(0,1.08),(62,1),(149,1)])],"title":[("opacity",[(0,0),(57,1),(149,1)]),("position_x",[(0,42),(70,0),(149,0)])],"layout":"monumental"},
]


def _tracks(spec: list[tuple[str, list[tuple[int, float]]]]) -> list[dict]:
    return [BASE.track(prop, keys, "out_cubic") for prop, keys in spec]


def _rule(layer_id: str, center: tuple[int, int], width: int, color: str, start: int = 0) -> dict:
    x, y = center
    # Native color plate reveal: narrow at first, then extends from the center.
    duration = FRAMES - start
    final = duration - 1
    layer=BASE.color_layer(layer_id,[width,5],[x,y],start,duration,[1,1,1,1],
                           [BASE.track("scale_x",[(0,.015),(min(56,final),1),(final,1)],"out_cubic"),
                            BASE.track("opacity",[(0,0),(min(38,final),1),(final,1)],"out_cubic")])
    layer["type"]="shape"
    layer["shape"]={"type":"path","path":[{"type":"move_to","point":[-width/2,0]},{"type":"line_to","point":[width/2,0]}],"stroke":{"color":color,"width":5}}
    layer.pop("color",None)
    return layer


def build_plan(recipe: dict) -> dict:
    layout = recipe["layout"]
    bg = [0.022,0.031,0.043,1] if not recipe.get("archive") else [0.052,0.047,0.039,1]
    layers = [BASE.color_layer("background",[1920,1080],[960,540],0,FRAMES,bg)]
    if recipe.get("archive"):
        layers.append(BASE.color_layer("archive-band",[1920,220],[960,250],0,FRAMES,[0.09,0.075,0.057,1]))
        layers.append(BASE.layer_text("archive-kicker","ARCHIVE  /  PORTRAIT STUDY",[800,38],[960,140],0,FRAMES,font=FONT,font_size=24,fill="#D9C7A4",
                                      tracks=[BASE.track("opacity",[(0,0),(40,1),(149,1)])]))
    if recipe.get("annotation"):
        layers.append(BASE.layer_text("annotation-kicker","A DIFFERENT WAY OF THINKING",[700,38],[960,145],0,FRAMES,font=FONT,font_size=24,fill="#D8B977",
                                      tracks=[BASE.track("opacity",[(0,0),(38,1),(149,1)])]))
        layers.append(BASE.layer_text("annotation-quote","A DIFFERENT WAY OF THINKING",[860,65],[960,930],12,FRAMES-12,font=FONT,font_size=34,fill="#E5DED1",
                                      tracks=[BASE.track("opacity",[(0,0),(56,1),(137,1)]),BASE.track("position_y",[(0,20),(60,0),(137,0)])]))
    if layout == "split":
        image_xy, image_size, title_xy, title_size = [650,500],[620,660],[1310,500],[740,140]
    elif layout == "monumental":
        image_xy, image_size, title_xy, title_size = [960,435],[690,700],[960,850],[1400,145]
    else:
        image_xy, image_size, title_xy, title_size = [960,450],[680,690],[960,865],[1250,135]
    image = {"id":"steve-jobs-portrait","type":"image","asset":ASSET,"size":image_size,"fit":"contain",
             "position":BASE.renderer_center_position(image_xy),"start_frame":0,"duration_frames":FRAMES,
             "enable_3d":any(prop in {"position_z","rotation_x","rotation_y"} for prop,_ in recipe["image"]),
             "animation":{"tracks":_tracks(recipe["image"])},"effects":[]}
    if recipe.get("glow"):
        image["effects"]=[{"type":"glow","radius":20,"intensity":.16,"color":[.84,.68,.42,1]}]
    BASE.add_entity_image_frame(image,image_radius=10,stroke_width=0)
    layers.append(image)
    title_fill = "#E8D6AF" if recipe.get("archive") else "#F4F1E9"
    title = BASE.layer_text("steve-jobs-title","STEVE JOBS",title_size,title_xy,0,FRAMES,font=FONT,font_size=118 if layout!="split" else 88,
                            min_font_size=58,fill=title_fill,tracks=_tracks(recipe["title"]))
    if recipe.get("pill"):
        title["style"]["background"]={"color":"#252B30","radius":22,"padding":[24,12]}
    layers.append(title)
    if layout != "split":
        accent_color="#D8B977" if recipe.get("archive") else "#B7975B"
        layers.append(_rule("title-accent-rule",(960,940),430,accent_color))
        layers.append(BASE.layer_text("portrait-caption","INNOVATOR  ·  1955—2011",[620,36],[960,995],18,FRAMES-18,font=FONT,font_size=22,fill="#9C9A94",
                                      tracks=[BASE.track("opacity",[(0,0),(36,1),(131,1)])]))
    elif recipe.get("archive"):
        layers.append(_rule("archive-rule",(1310,610),440,"#D8B977"))
        layers.append(BASE.layer_text("archive-subtitle","CO-FOUNDER  ·  APPLE",[600,38],[1310,670],18,FRAMES-18,font=FONT,font_size=24,fill="#CFC2A9",
                                      tracks=[BASE.track("opacity",[(0,0),(42,1),(131,1)])]))
    if recipe.get("underline"):
        layers.append(_rule("native-title-underline",(960,945),540,"#D8B977",start=18))
    if recipe.get("archive"):
        for y in (180,875):
            layers.append(_rule(f"archive-hairline-{y}",(960,y),1580,"#776849"))
    return BASE.scene_plan(recipe["id"],layers,FRAMES)


def build_all() -> list[dict]:
    plans=[build_plan(recipe) for recipe in RECIPES]
    ids=[p["job_id"] for p in plans]
    if len(ids)!=len(set(ids)):
        raise ValueError("duplicate entity motion id")
    return plans


def _preview_plan(plan: dict, assets_root: Path, scale: float) -> dict:
    """Remap repository-rooted plan assets for Chronon3D's fast exhibit compositor."""
    result = json.loads(json.dumps(plan))
    for layer in result.get("layers", []):
        asset = layer.get("asset")
        if asset and asset.startswith("ChrononTemplate/"):
            layer["asset"] = asset.removeprefix("ChrononTemplate/")
        font = (layer.get("style") or {}).get("font")
        if font and font.startswith("ChrononTemplate/"):
            layer["style"]["font"] = font.removeprefix("ChrononTemplate/")
    result["canvas"]["width"] = round(result["canvas"]["width"] * scale)
    result["canvas"]["height"] = round(result["canvas"]["height"] * scale)
    preview_layers=[]
    for layer in result.get("layers", []):
        if layer.get("type") not in {"image","text"}:
            continue  # the review compositor is intentionally image/text-only
        if "size" in layer:
            layer["size"] = [round(value * scale) for value in layer["size"]]
        if "position" in layer:
            layer["position"] = [value * scale for value in layer["position"]]
        if "style" in layer and "font_size" in layer["style"]:
            layer["style"]["font_size"] = max(1, round(layer["style"]["font_size"] * scale))
        original_tracks=(layer.get("animation") or {}).get("tracks",[])
        for item in original_tracks:
            if item["property"] in {"opacity","scale","scale_x","scale_y"}:
                item["keyframes"]=[{**key,"value":[key["value"]] if isinstance(key["value"],(int,float)) else key["value"]} for key in item["keyframes"]]
        axis_tracks={item["property"]:{int(key["frame"]):key["value"] for key in item["keyframes"]} for item in original_tracks}
        if "position" in axis_tracks or any(key in axis_tracks for key in ("position_x","position_y")):
            frames=sorted({int(frame) for prop in ("position_x","position_y","position") for frame in axis_tracks.get(prop,{})})
            base=list(layer.get("position",[0,0]))
            if layer["type"]=="image":
                base=[base[0],base[1]]
            def axis_value(prop,frame,component):
                keys=axis_tracks.get(prop,{})
                applicable=[key_frame for key_frame in keys if key_frame<=frame]
                return float(keys[applicable[-1]][0] if isinstance(keys[applicable[-1]],list) else keys[applicable[-1]]) if applicable else 0.0
            def combined(frame):
                explicit=axis_tracks.get("position",{})
                pkeys=[key_frame for key_frame in explicit if key_frame<=frame]
                value=list(explicit[pkeys[-1]][:2]) if pkeys else list(base[:2])
                value[0]+=axis_value("position_x",frame,0)*scale
                value[1]+=axis_value("position_y",frame,1)*scale
                return value
            layer["animation"]={"tracks":[item for item in original_tracks if item["property"] not in {"position_x","position_y","position_z"}]}
            layer["animation"]["tracks"].append({"property":"position","keyframes":[{"frame":frame,"value":combined(frame)} for frame in frames]})
        preview_layers.append(layer)
    result["layers"]=preview_layers
    return result


def render_previews(output_dir: Path, assets_root: Path, scale: float) -> list[Path]:
    """Render small, faithful plan-driven H.264 previews via the bundled compositor."""
    preview_script = ROOT / "Chronon3d/tools/preview_render_plan.py"
    if not preview_script.is_file():
        raise FileNotFoundError(f"plan preview renderer not found: {preview_script}")
    videos = output_dir / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    destinations = []
    for recipe, plan in zip(RECIPES, build_all()):
        preview_path = output_dir / f".{plan['job_id']}.preview.plan.json"
        preview_path.write_text(json.dumps(_preview_plan(plan, TEMPLATE, scale), ensure_ascii=False), encoding="utf-8")
        destination = videos / f"{plan['job_id']}.mp4"
        subprocess.run(["python3", str(preview_script), "--plan", str(preview_path),
                        "--assets-root", str(TEMPLATE), "--out", str(destination),
                        "--scale", "1", "--supersample", "1"], check=True)
        preview_path.unlink()
        destinations.append(destination)
    return destinations


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=OUT)
    parser.add_argument("--cli",type=Path)
    parser.add_argument("--assets-root",type=Path,default=ROOT)
    parser.add_argument("--render-previews",action="store_true",help="render small H.264 review previews with Chronon3D's plan compositor")
    parser.add_argument("--preview-scale",type=float,default=0.5)
    args=parser.parse_args(argv)
    args.out.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"chronontemplate.entity-with-text.v2","version":2,"canvas":{"width":1920,"height":1080,"fps":FPS,"duration_frames":FRAMES},"animations":[]}
    for recipe,plan in zip(RECIPES,build_all()):
        path=args.out/f"{plan['job_id']}.plan.json"
        path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if args.cli:
            subprocess.run([str(args.cli),"validate","--plan",str(path),"--assets-root",str(args.assets_root)],check=True)
        manifest["animations"].append({"id":recipe["id"],"refines":recipe["source"],"plan":path.name,"portrait_and_title_are_separate_layers":True,"new":recipe["source"].startswith("new_")})
        print(path)
    manifest_path=args.out/"manifest.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MANIFEST {manifest_path}")
    if args.render_previews:
        videos=render_previews(args.out,args.assets_root,args.preview_scale)
        print(f"PREVIEWS_COMPLETE files={len(videos)} dir={args.out / 'videos'} scale={args.preview_scale}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
