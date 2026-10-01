#!/usr/bin/env python3
"""Build and render the fifteen-preset people entity motion gallery."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
FAMILY_CATALOG = Path(__file__).resolve().parents[1] / "catalog/entity_motion_families.v1.json"
ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
OUT = ROOT / "out/editorial_v1"

def track(prop, keys, easing="out_cubic"):
    return {"property": prop, "keyframes": [{"frame": f, "value": v} for f, v in keys], "easing": easing}

def main():
    family = json.loads(FAMILY_CATALOG.read_text())["families"][0]
    IDS = family["presets"]
    layouts = family["preset_layouts"]
    fps, segment = 24, 48
    layers = [{"id":"bg", "type":"color", "color":[0.035,0.047,0.067,1], "size":[1280,720], "start_frame":0, "duration_frames":len(IDS)*segment}]
    for n, preset in enumerate(IDS):
        start = n * segment
        layout = layouts[preset]
        portrait_position = [0,-20]
        caption_position = [640,590]
        caption_size = [500,54]
        image_tracks = [track("opacity", [(0,0),(16,1),(40,1),(47,0)])]
        caption_tracks = [track("opacity", [(0,0),(20,1),(40,1),(47,0)])]
        if preset in ("people_caption_rise", "people_stack_reveal"):
            image_tracks += [track("scale", [(0,.96),(22,1),(40,1),(47,.96)])]
            caption_tracks += [track("position_y", [(0,24),(24,0),(40,0),(47,24)])]
        elif preset == "people_depth_caption":
            image_tracks += [track("position_z", [(0,110),(24,0),(40,0),(47,110)])]
            caption_tracks += [track("position_y", [(0,12),(28,0),(40,0),(47,12)])]
        elif preset == "people_yaw_reveal":
            image_tracks += [track("rotation_y", [(0,-14),(24,0),(40,0),(47,-14)], "out_cubic")]
        elif preset == "people_split_side_reveal":
            image_tracks += [track("position_x", [(-0, -70),(24,0),(40,0),(47,-70)])]
            caption_tracks += [track("position_x", [(0,70),(28,0),(40,0),(47,70)])]
        elif preset == "people_card_float_settle":
            image_tracks += [track("position_y", [(0,18),(18,-3),(30,0),(40,0),(47,18)], "in_out_cubic")]
            caption_tracks += [track("position_y", [(0,12),(28,0),(40,0),(47,12)])]
        elif preset == "people_underline_identity":
            caption_tracks += [track("position_y", [(0,8),(24,0),(40,0),(47,8)])]
        elif preset == "people_focus_frame":
            image_tracks += [track("scale", [(0,1.025),(24,1),(40,1),(47,1.025)])]
        elif preset == "people_name_pill_pop":
            caption_tracks += [track("scale", [(0,.94),(26,1),(40,1),(47,.94)])]
        elif preset == "people_portrait_parallax":
            image_tracks += [track("rotation_x", [(0,5),(24,0),(40,0),(47,5)])]
        elif preset == "people_side_left_text_right":
            portrait_position = [-225,-20]
            caption_position = [900,330]
            caption_size = [450,64]
            caption_tracks += [track("position_x", [(0,64),(25,0),(40,0),(47,64)])]
        elif preset == "people_side_right_text_left":
            portrait_position = [225,-20]
            caption_position = [380,330]
            caption_size = [450,64]
            caption_tracks += [track("position_x", [(0,-64),(25,0),(40,0),(47,-64)])]
        elif preset == "people_split_left_to_right":
            portrait_position = [-225,-20]
            caption_position = [900,330]
            caption_size = [450,64]
            image_tracks += [track("position_x", [(-0,-72),(24,0),(40,0),(47,-72)])]
            caption_tracks += [track("position_x", [(0,78),(27,0),(40,0),(47,78)])]
        elif preset == "people_split_right_to_left":
            portrait_position = [225,-20]
            caption_position = [380,330]
            caption_size = [450,64]
            image_tracks += [track("position_x", [(0,72),(24,0),(40,0),(47,72)])]
            caption_tracks += [track("position_x", [(0,-78),(27,0),(40,0),(47,-78)])]
        elif preset == "people_caption_over_portrait_lower":
            portrait_position = [0,58]
            caption_position = [640,138]
            image_tracks += [track("position_y", [(0,30),(24,0),(40,0),(47,30)])]
            caption_tracks += [track("position_y", [(0,-24),(25,0),(40,0),(47,-24)])]
        name_style = {"font":"assets/fonts/Poppins-Bold.ttf","font_size":30,"fill":"#F5F7FA","fit_mode":"shrink_only","min_font_size":26,"max_font_size":30}
        if preset == "people_name_pill_pop":
            name_style["background"] = {"color":"#263342","opacity":0.96,"radius":16,"padding":[20,10]}
        layers += [
            {"id":f"portrait-{n}","type":"image","asset":"assets/canary/people-demo-portrait.png","size":[390,390],"fit":"cover","position":portrait_position,"start_frame":start,"duration_frames":segment,"animation":{"tracks":image_tracks},"enable_3d":preset in ("people_depth_caption","people_yaw_reveal","people_portrait_parallax")},
            {"id":f"name-{n}","type":"text","text":"Mira Chen","size":caption_size,"position":caption_position,"start_frame":start,"duration_frames":segment,"style":name_style,"animation":{"tracks":caption_tracks}},
            {"id":f"preset-{n}","type":"text","text":preset,"size":[700,28],"position":[640,665 if layout == "person_card_top_caption" else 645],"start_frame":start+12,"duration_frames":segment-12,"style":{"font":"assets/fonts/DejaVuSans.ttf","font_size":13,"fill":"#9FB0C2"},"animation":{"tracks":[track("opacity",[(0,0),(8,1),(32,1),(35,0)])]}},
        ]
    plan = {"schema":"chronon.render-plan.v3","version":3,"job_id":"people_family_v1_gallery_15","canvas":{"width":1280,"height":720,"fps_num":fps,"fps_den":1,"duration_frames":len(IDS)*segment},"layers":layers,"output":{"path":"people_family_v1_gallery_15.mp4","format":"mp4","codec":"h264"}}
    plan_dir = OUT / "plans"
    render_dir = OUT / "renders"
    plan_dir.mkdir(parents=True,exist_ok=True); render_dir.mkdir(parents=True,exist_ok=True)
    plan_path = plan_dir / "people_family_v1_gallery_15.plan.json"
    plan_path.write_text(json.dumps(plan,indent=2)+"\n")
    output = render_dir / "people_family_v1_gallery_15.mp4"
    subprocess.run([str(CLI),"render-plan","--input",str(plan_path),"--assets-root",str(ASSETS),"--output",str(output),"--backend","software","--encode-preset","veryfast","--trace",str(render_dir/"people_family_v1_gallery_15.pftrace")],check=True,cwd=ROOT)
    print(output)

if __name__ == "__main__":
    main()
