#!/usr/bin/env python3
"""Render one standalone MP4 for every registered map animation variant."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
OUT = TEMPLATE / "out" / "map_animation_review_curated10_20261017"
RENDERER = HERE / "render_dynamic_map_overlay.py"
sys.path[:0] = [str(HERE), str(TEMPLATE.parent / "Chronon3d/tools/cartography")]
from render_geo_camera_small_places import MAP_LABEL_ANIMATIONS
from map_compositions import MAP_COMPOSITIONS
from map_editorial import MAP_EDITORIAL_SCENES

GARLASCO = {"id":"garlasco", "label":"Garlasco", "latitude":45.1972,
            "longitude":8.9237, "location":"Garlasco, Italy", "category":"focus",
            "subtitle":"Pavia, Italy"}
NEARBY = [
    GARLASCO,
    {"id":"pavia", "label":"Pavia", "latitude":45.1845, "longitude":9.1582,
     "location":"Pavia, Italy", "category":"wind", "subtitle":"Lombardy"},
    {"id":"vigevano", "label":"Vigevano", "latitude":45.3150, "longitude":8.8560,
     "location":"Vigevano, Italy", "category":"solar", "subtitle":"Lombardy"},
    {"id":"mortara", "label":"Mortara", "latitude":45.2500, "longitude":8.7350,
     "location":"Mortara, Italy", "category":"hydro", "subtitle":"Lombardy"},
    {"id":"lomello", "label":"Lomello", "latitude":45.1230, "longitude":8.7970,
     "location":"Lomello, Italy", "category":"focus", "subtitle":"Lombardy"},
]
EDITORIAL = {
 "ed_saudi_base": [{"id":"saudi","label":"Saudi Arabia","latitude":24.7136,"longitude":46.6753,"scope":"country"}],
 "ed_iran_glow": [{"id":"iran","label":"Iran","latitude":32.0,"longitude":53.0,"scope":"country"}],
 "ed_yemen_fill": [{"id":"yemen","label":"Yemen","latitude":15.3,"longitude":47.0,"scope":"country"}],
 "ed_yemen_markers": [
   {"id":"sanaa","label":"Sanaa","latitude":15.3694,"longitude":44.1910,"scope":"country"},
   {"id":"hodeidah","label":"Hodeidah","latitude":14.7979,"longitude":42.9545,"scope":"country"},
   {"id":"abha","label":"Abha Intl Airport","latitude":18.2164,"longitude":42.5053,"scope":"country"}],
 "ed_hormuz_routes": [{"id":"hormuz","label":"Strait of Hormuz","latitude":26.55,"longitude":56.27,"scope":"country"}],
 "ed_mocha_tactical": [{"id":"mocha","label":"Mocha","latitude":13.3167,"longitude":43.25,"scope":"region"}],
}

def catalog():
    items=[]
    for i, name in enumerate(("slow_approach",),1):
        items.append((f"01-camera/{i:02d}-camera-{name}", "camera", name, [GARLASCO], 5.0))
    for i, name in enumerate(MAP_LABEL_ANIMATIONS,1):
        items.append((f"02-label/{i:02d}-label-{name}", "label", name, [GARLASCO], 5.0))
    for i, name in enumerate(MAP_COMPOSITIONS,1):
        pins=[GARLASCO]
        items.append((f"03-composition/{i:02d}-map-{name}", "composition", name, pins, 6.5 if len(pins)>1 else 5.0))
    for i, name in enumerate(MAP_EDITORIAL_SCENES,1):
        items.append((f"04-editorial/{i:02d}-scene-{name}", "editorial", name, EDITORIAL[name], 5.0))
    return items

def render(item):
    slug, kind, name, pins, seconds = item
    rel=Path(slug + ".mp4")
    target=OUT/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    payload={"width":1280,"height":720,"fps_num":24,"fps_den":1,
             "duration_us":round(seconds*1_000_000),"pins":pins,
             "area_glow_radius_km":0.0,"camera_animation":"slow_approach",
             "label_animation":"none","map_animation":"","basemap":"esri_sat"}
    if kind=="camera":
        payload["camera_animation"]=name
    elif kind=="label":
        payload["label_animation"]=name
    else:
        payload["map_animation"]=name
        if kind=="composition" and len(pins)>1:
            payload["camera_animation"]="slow_approach"
    src=target.with_suffix(".json")
    src.write_text(json.dumps(payload,separators=(",",":")),encoding="utf-8")
    print(f"[map-review] {len(list(OUT.rglob('*.mp4')))+1}/{len(catalog())} {rel}",flush=True)
    subprocess.run([sys.executable,str(RENDERER),"--input",str(src),"--output",str(target)],check=True)
    return {"file":str(rel),"category":kind,"animation":name,"duration_seconds":seconds,
            "pins":[p["label"] for p in pins]}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    items=catalog()
    only=set(sys.argv[1:])
    if only:
        items=[item for item in items if item[0] in only or item[1] in only or item[2] in only]
    done=[]
    for item in items:
        target=OUT/(item[0]+".mp4")
        if target.is_file() and target.stat().st_size>0:
            done.append({"file":str(Path(item[0]+".mp4")),"category":item[1],"animation":item[2],"duration_seconds":item[4],"pins":[p["label"] for p in item[3]]})
            continue
        done.append(render(item))
    (OUT/"index.json").write_text(json.dumps({"title":"PipelineGen Map Animation Review Pack","rendered_separately":True,"canvas":"1280x720, 24 fps; one MP4 per retained animation","counts":{"camera":1,"label":len(MAP_LABEL_ANIMATIONS),"composition":len(MAP_COMPOSITIONS),"editorial":len(MAP_EDITORIAL_SCENES)},"clips":done},indent=2),encoding="utf-8")
    print(f"[map-review] complete: {len(done)} clips at {OUT}",flush=True)
if __name__=="__main__": main()
