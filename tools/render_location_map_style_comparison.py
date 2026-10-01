#!/usr/bin/env python3
"""Compare selectable, georeferenced location map bases in one short canary."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import render_location_family_v1 as geo  # shared projection and renderer helpers

CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
SOURCE_DIR = Path(__file__).resolve().parents[1] / "catalog/maps"
ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
OUT = ROOT / "out/editorial_v1"
FPS, SEGMENT = 24, 48
STYLES = [
    ("natural_earth_hypso_relief_water.jpg", "CROSS BLENDED HYPOSOMETRIC", "Elevation tint and shaded relief", (1.24, 1.20, .88)),
    ("natural_earth_landcover_relief_water.jpg", "NATURAL EARTH LAND COVER", "Land cover with shaded relief", (1.20, 1.15, .88)),
    ("nasa_blue_marble_august.jpg", "NASA BLUE MARBLE", "Cloud-free satellite composite", (1.12, 1.02, 1.00)),
]

def build():
    geo.prepare_atlas()  # emits accurately projected Natural Earth country borders
    layers = [{"id": "comparison-bg", "type": "color", "color": [0.025, 0.035, 0.05, 1],
               "size": [1280, 720], "start_frame": 0, "duration_frames": len(STYLES)*SEGMENT}]
    font = "assets/fonts/Poppins-Bold.ttf"
    body = "assets/fonts/DejaVuSans.ttf"
    lon, lat = 2.3522, 48.8566
    point = geo.geo_xy(lon, lat)
    for i, (filename, title, subtitle, grade) in enumerate(STYLES):
        start = i * SEGMENT
        source = Image.open(SOURCE_DIR / filename).convert("RGB")
        source = ImageEnhance.Color(source).enhance(grade[0])
        source = ImageEnhance.Contrast(source).enhance(grade[1])
        source = ImageEnhance.Brightness(source).enhance(grade[2])
        styled_name = f"assets/canary/map-style-{i+1:02d}.jpg"
        source.save(ASSETS / styled_name, quality=94, optimize=True, subsampling=0)
        fade = [geo.tr("opacity", [(0, 0), (8, 1), (39, 1), (47, 0)])]
        layers.append({"id": f"map-style-{i}", "type": "image", "asset": styled_name,
                       "size": geo.MAP_SIZE, "position": [0, 0], "fit": "contain",
                       "start_frame": start, "duration_frames": SEGMENT, "animation": {"tracks": fade}})
        layers.append({"id": f"map-boundaries-{i}", "type": "image",
                       "asset": "assets/canary/natural-earth-boundaries.png", "size": geo.MAP_SIZE,
                       "position": [0, 0], "fit": "contain", "start_frame": start,
                       "duration_frames": SEGMENT, "animation": {"tracks": fade}})
        title_keys = [geo.tr("opacity", [(0, 0), (9, 1), (39, 1), (46, 0)]),
                      geo.tr("position_y", [(0, 7), (17, 0), (39, 0), (46, -4)])]
        layers.append({"id": f"style-title-{i}", "type": "text", "text": title,
                       "size": [740, 46], "position": [640, 98], "start_frame": start+2,
                       "duration_frames": SEGMENT-2,
                       "style": {"font": font, "font_size": 25, "fill": "#F6F5EE",
                                 "fit_mode": "shrink_only", "min_font_size": 19, "max_font_size": 25},
                       "animation": {"tracks": title_keys}})
        layers.append({"id": f"style-subtitle-{i}", "type": "text", "text": subtitle,
                       "size": [600, 25], "position": [640, 139], "start_frame": start+5,
                       "duration_frames": SEGMENT-5,
                       "style": {"font": body, "font_size": 13, "fill": "#EEF0E8"},
                       "animation": {"tracks": [geo.tr("opacity", [(0, 0), (10, .9), (38, .9), (43, 0)])]}})
        layers.append(geo.marker(f"paris-pin-{i}", point, "#FFCB72", start+9,
                                 SEGMENT-9, radius=10,
                                 tracks=[geo.tr("scale", [(0, .3), (12, 1), (38, 1), (46, .2)]),
                                         geo.tr("opacity", [(0, 0), (8, 1), (38, 1), (46, 0)])]))
        layers.append({"id": f"paris-label-{i}", "type": "text", "text": "PARIS",
                       "size": [130, 23], "position": [640+point[0]+74, 360+point[1]-13],
                       "start_frame": start+13, "duration_frames": SEGMENT-13,
                       "style": {"font": font, "font_size": 14, "fill": "#FFF3D6"},
                       "animation": {"tracks": [geo.tr("opacity", [(0, 0), (6, 1), (29, 1), (34, 0)])]}})
        layers.append({"id": f"map-label-{i}", "type": "text",
                       "text": f"BASE {i+1}  /  SAME GEOGRAPHIC EXTENT", "size": [450, 22],
                       "position": [640, 687], "start_frame": start+5,
                       "duration_frames": SEGMENT-5,
                       "style": {"font": body, "font_size": 11, "fill": "#F4F1E9"},
                       "animation": {"tracks": [geo.tr("opacity", [(0, 0), (7, .8), (39, .8), (43, 0)])]}})

    for layer in layers:
        span = layer.get("duration_frames", SEGMENT)
        for track in layer.get("animation", {}).get("tracks", []):
            frames = {}
            for key in track["keyframes"]:
                frames[min(key["frame"], span-1)] = key["value"]
            track["keyframes"] = [{"frame": f, "value": frames[f]} for f in sorted(frames)]
    job = "location_map_style_comparison_v1"
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job,
            "canvas": {"width": 1280, "height": 720, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": len(STYLES)*SEGMENT}, "layers": layers,
            "output": {"path": f"{job}.mp4", "format": "mp4", "codec": "h264"}}
    plans, renders = OUT/"plans", OUT/"renders"
    plans.mkdir(parents=True, exist_ok=True); renders.mkdir(parents=True, exist_ok=True)
    plan_file, output = plans/f"{job}.plan.json", renders/f"{job}.mp4"
    plan_file.write_text(json.dumps(plan, indent=2)+"\n")
    subprocess.run([str(CLI), "render-plan", "--input", str(plan_file), "--assets-root", str(ASSETS),
                    "--output", str(output), "--backend", "software", "--encode-preset", "veryfast",
                    "--trace", str(renders/f"{job}.pftrace")], cwd=ROOT, check=True)
    print(output)

if __name__ == "__main__":
    build()
