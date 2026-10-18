#!/usr/bin/env python3
"""Render a short Chronon native film-emulsion / archival signal showcase."""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[2]
ROOT = TEMPLATE.parent
CLI = ROOT / "Chronon3dGPU/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
OUT = TEMPLATE / "out/emulsion_grain_lab"
DEST = Path("/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4/MP4")
VIDEO = DEST / "memoria_emulsion_grain_1920x1080.mp4"
W, H, FPS, FRAMES = 1280, 720, 24, 120
OUTPUT_W, OUTPUT_H = 1920, 1080
SCALE = OUTPUT_W / W
FONT = "assets/fonts/Inter-Bold.ttf"


def layer(id_, kind, size, pos, *, start=0, duration=FRAMES, fill=None,
          stroke=None, opacity=1.0, blend=None, effects=None, text=None,
          font_size=20, color="#FFFFFF", tracks=None):
    item = {"id": id_, "type": kind, "size": list(size), "position": list(pos),
            "start_frame": start, "duration_frames": duration}
    if kind == "shape":
        circle = id_.startswith(("orb", "dust-")) or id_ in {"core-glow", "signal", "signal-core"}
        fill_value = fill or "#FFFFFF"
        if isinstance(fill_value, str) and fill_value.startswith("#"):
            fill_value = [int(fill_value[i:i+2], 16) / 255 for i in (1, 3, 5)] + [1.0]
        item["shape"] = {"type": "ellipse" if circle else "rect", "fill": fill_value}
        if stroke:
            item["shape"]["stroke"] = stroke
    if kind == "text":
        item["text"] = text
        item["style"] = {"font": str(FONT), "font_size": font_size,
                         "min_font_size": font_size, "max_font_size": font_size,
                         "fit_mode": "shrink_only", "fill": color}
    if opacity != 1.0: item["opacity"] = opacity
    if blend: item["blend_mode"] = blend
    if effects: item["effects"] = effects
    if tracks: item["animation"] = {"tracks": tracks}
    return item


def make_plan():
    layers = [layer("night", "shape", (W,H), (W/2,H/2), fill="#071018")]
    # Subtle multiscale clouding, followed by seeded, animated fine emulsion.
    layers += [
        layer("atmosphere", "shape", (W,H), (W/2,H/2), fill="#17232A",
              opacity=.28, effects=[{"type":"noise", "amount":.022, "size":3.0,
                                     "seed":31, "animated":False, "color_mode":"monochrome"}]),
        layer("emulsion", "shape", (W,H), (W/2,H/2), fill="#A58A5B",
              opacity=.10, blend="screen", effects=[{"type":"noise", "amount":.07,
                  "size":1.0, "seed":907, "animated":False, "color_mode":"monochrome",
                  "shadow_response":.65, "midtone_response":1.0, "highlight_response":.35}]),
    ]
    # Concentric archival aperture with restrained amber edge light.
    for i, (d, col, alpha) in enumerate(((490,"#1D3032",.68),(430,"#52706A",.48),
                                          (344,"#C09550",.56),(318,"#101A1C",.95))):
        layers.append(layer(f"orb-{i}", "shape", (d,d), (862,354), fill="#0A1215",
                            stroke={"color":col,"width":3 if i<3 else 1}, opacity=alpha))
    layers += [
        layer("core-glow", "shape", (246,246), (862,354), fill="#7B5430", opacity=.30,
              blend="screen"),
        layer("signal", "shape", (176,176), (862,354), fill="#D4AA63", opacity=.82,
              effects=[{"type":"noise","amount":.045,"size":2.2,"seed":1976,
                        "animated":False,"color_mode":"monochrome"}]),
        layer("signal-core", "shape", (128,128), (862,354), fill="#182326",
              stroke={"color":"#E8C989","width":2}, opacity=.95),
    ]
    # Fine radial scan marks and drifting dust points.
    for angle in range(0,360,15):
        rad=math.radians(angle)
        x,y=862+244*math.cos(rad),354+244*math.sin(rad)
        layers.append(layer(f"tick-{angle}","shape",(2,12 if angle%45 else 21),(x,y),
                            fill="#C39A59",opacity=.48))
    rng=random.Random(7721)
    for i in range(70):
        x=rng.uniform(130,1190); y=rng.uniform(90,635); d=rng.choice((1.5,2,3,4))
        a=rng.uniform(.18,.72)
        dx, dy = rng.uniform(-17, 17), rng.uniform(-10, 10)
        layers.append(layer(f"dust-{i:02}","shape",(d,d),(x,y),fill="#E4C68A",
                            opacity=a,blend="screen",tracks=[
                                {"property":"position_x","easing":"linear","keyframes":[
                                    {"frame":0,"value":0},{"frame":60,"value":dx},
                                    {"frame":119,"value":dx*.55}]},
                                {"property":"position_y","easing":"linear","keyframes":[
                                    {"frame":0,"value":0},{"frame":60,"value":dy},
                                    {"frame":119,"value":dy*.55}]}
                            ]))
    # Typography and registration marks.
    layers += [
        layer("kicker","text",(510,28),(285,118),text="CHRONON   /   EMULSION STUDY 01",
              font_size=15,color="#C4A46B"),
        layer("headline","text",(620,92),(405,256),text="MEMORIA",
              font_size=66,color="#E7D8B8",effects=[{"type":"noise","amount":.028,
              "size":1.2,"seed":86,"animated":False,"color_mode":"monochrome"}]),
        layer("subhead","text",(500,34),(385,310),text="ARCHIVE SIGNAL  /  1976",
              font_size=19,color="#C6AA75"),
        layer("caption","text",(550,42),(440,590),text="MULTISCALE GRAIN  •  TONAL RESPONSE  •  SEEDED DUST",
              font_size=13,color="#9CA89F"),
        layer("frame-top","shape",(960,1),(640,70),fill="#C4A46B",opacity=.45),
        layer("frame-bottom","shape",(960,1),(640,650),fill="#C4A46B",opacity=.45),
        layer("left-mark","shape",(26,2),(166,354),fill="#D9B876",opacity=.8),
        layer("right-mark","shape",(26,2),(1114,354),fill="#D9B876",opacity=.8),
    ]
    for item in layers:
        item["size"] = [value * SCALE for value in item["size"]]
        item["position"] = [value * SCALE for value in item["position"]]
        style = item.get("style")
        if style:
            for key in ("font_size", "min_font_size", "max_font_size"):
                if key in style: style[key] *= SCALE
        shape = item.get("shape", {})
        if isinstance(shape.get("stroke"), dict) and "width" in shape["stroke"]:
            shape["stroke"]["width"] *= SCALE
        for effect in item.get("effects", []):
            if "size" in effect: effect["size"] *= SCALE
        for track in item.get("animation", {}).get("tracks", []):
            if track.get("property") in {"position_x", "position_y"}:
                for keyframe in track["keyframes"]: keyframe["value"] *= SCALE
    return {"schema":"chronon.render-plan.v3", "version":3, "job_id":"emulsion_grain_lab",
            "canvas":{"width":OUTPUT_W,"height":OUTPUT_H,"fps_num":FPS,"fps_den":1,"duration_frames":FRAMES},
            "output":{"path":str(VIDEO),"format":"mp4","codec":"h264"},
            "layers":layers}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    plan=OUT/"emulsion_grain_lab.plan.json"
    plan.write_text(json.dumps(make_plan(),indent=2)+"\n")
    if not CLI.is_file(): raise SystemExit(f"Chronon CLI not found: {CLI}")
    subprocess.run([str(CLI),"validate","--plan",str(plan),"--assets-root",str(ROOT/"Chronon3dGPU")],check=True)
    raw = OUT / "emulsion_grain_lab.rgba"
    subprocess.run([str(CLI),"render","--backend","software","--plan",str(plan),
                    "--assets-root",str(ROOT/"Chronon3dGPU"),"--video-sink","raw",
                    "--pipe-pixfmt","rgba","--frames",f"0-{FRAMES-1}x1","-o",str(raw),
                    "--profile","preview"],check=True)
    video = VIDEO
    subprocess.run(["ffmpeg","-y","-f","rawvideo","-pixel_format","rgba",
                    "-video_size",f"{OUTPUT_W}x{OUTPUT_H}","-framerate",str(FPS),"-i",str(raw),
                    "-an","-c:v","libx264","-preset","medium","-crf","18",
                    "-pix_fmt","yuv420p",str(video)],check=True)
    subprocess.run(["ffmpeg","-y","-i",str(video),"-vf",
                    "select='eq(n,0)+eq(n,60)+eq(n,119)',scale=640:-1,tile=3x1",
                    "-frames:v","1",str(DEST/"memoria_emulsion_grain_contact_sheet.png"),"-loglevel","error"],check=True)
    raw.unlink(missing_ok=True)
    raw.with_suffix(raw.suffix + ".timing.json").unlink(missing_ok=True)


if __name__ == "__main__": main()
