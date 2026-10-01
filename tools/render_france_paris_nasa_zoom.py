#!/usr/bin/env python3
"""Cinematic NASA Blue Marble zoom from the North Atlantic to France/Paris."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
CATALOG = Path(__file__).resolve().parents[1] / "catalog"
ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
OUT = ROOT / "out/editorial_v1"
W, H, FPS, DURATION = 1280, 720, 24, 240
MAP_SIZE = (1480, 630)
BOUNDS = (-100.0, 50.0, 8.0, 72.0)
PARIS = (2.3522, 48.8566)
ACCENT = (255, 196, 103)
ATLAS_POS = ((W-MAP_SIZE[0])/2, (H-MAP_SIZE[1])/2)
# Pixel registration between the cropped NASA plate and the Natural Earth vector atlas.
PARIS_REGISTRATION = (-96.0, 37.0)


def tr(prop, keys, easing="in_out_cubic"):
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}


def px(lon, lat, scale=1):
    lo, hi, bottom, top = BOUNDS
    return ((lon-lo)/(hi-lo)*MAP_SIZE[0]*scale,
            (top-lat)/(top-bottom)*MAP_SIZE[1]*scale)


def create_france_glow():
    data = json.loads((CATALOG / "ne_50m_admin_0_countries.geojson").read_text())
    feature = next(f for f in data["features"] if f["properties"].get("ADMIN") == "France")
    geom = feature["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    # Mainland France and Corsica; omit Guiana and overseas territories from this view.
    polygons = [p for p in polygons if p[0] and -6 <= sum(pt[0] for pt in p[0])/len(p[0]) <= 10
                and 41 <= sum(pt[1] for pt in p[0])/len(p[0]) <= 52]
    s = 3
    crisp = Image.new("RGBA", (MAP_SIZE[0]*s, MAP_SIZE[1]*s), (0, 0, 0, 0))
    mask = Image.new("L", (MAP_SIZE[0]*s, MAP_SIZE[1]*s), 0)
    d = ImageDraw.Draw(crisp)
    md = ImageDraw.Draw(mask)
    for poly in polygons:
        ring = [px(lon, lat, s) for lon, lat in poly[0] if
                BOUNDS[0] <= lon <= BOUNDS[1] and BOUNDS[2] <= lat <= BOUNDS[3]]
        if len(ring) >= 3:
            md.polygon(ring, fill=255)
            d.line(ring + [ring[0]], fill=(*ACCENT, 255), width=2*s, joint="curve")
    mask = mask.resize(MAP_SIZE, Image.Resampling.LANCZOS)
    # A restrained amber wash fills the whole territory while preserving the satellite texture.
    yy, xx = np.mgrid[0:MAP_SIZE[1], 0:MAP_SIZE[0]]
    paris_x, paris_y = px(*PARIS)
    distance = np.sqrt((xx-paris_x)**2 + (yy-paris_y)**2)
    alpha = np.asarray(mask, dtype=np.float32) * (0.20 + 0.12*np.exp(-distance/175.0))
    fill = Image.new("RGBA", MAP_SIZE, (*ACCENT, 0))
    fill.putalpha(Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), "L"))
    fill = fill.filter(ImageFilter.GaussianBlur(1.2))
    fill.save(ASSETS / "assets/canary/france-fill-glow.png")
    # Separate geographic rings let the country fill travel outward from Paris instead of
    # simply fading on as a complete, static overlay.
    dparis = np.sqrt((xx-paris_x)**2 + (yy-paris_y)**2)
    for i, radius in enumerate((25, 48, 72, 96, 125, 170)):
        inner = 0 if i == 0 else (25, 48, 72, 96, 125)[i-1]
        ring_alpha = np.asarray(mask, dtype=np.float32) * np.clip((radius-dparis)/5.0, 0, 1)
        if i:
            ring_alpha *= np.clip((dparis-inner+5.0)/5.0, 0, 1)
        ring = Image.new("RGBA", MAP_SIZE, (*ACCENT, 0))
        ring.putalpha(Image.fromarray(np.clip(ring_alpha*0.27, 0, 255).astype(np.uint8), "L"))
        ring = ring.filter(ImageFilter.GaussianBlur(1.0))
        ring.save(ASSETS / f"assets/canary/france-fill-wave-{i+1}.png")
    crisp = crisp.resize(MAP_SIZE, Image.Resampling.LANCZOS)
    crisp.save(ASSETS / "assets/canary/france-border-crisp.png")
    blurred = crisp.filter(ImageFilter.GaussianBlur(10))
    # Restrained amber bloom; two soft radii keep the country edge legible.
    alpha = blurred.getchannel("A").point(lambda x: int(x * 0.42))
    blurred.putalpha(alpha)
    blurred.save(ASSETS / "assets/canary/france-border-glow.png")
    soft = crisp.filter(ImageFilter.GaussianBlur(3))
    alpha = soft.getchannel("A").point(lambda x: int(x * 0.50))
    soft.putalpha(alpha)
    soft.save(ASSETS / "assets/canary/france-border-soft.png")


def create_geo_labels():
    labels = Image.new("RGBA", MAP_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(labels)
    font = ImageFont.truetype(str(ASSETS / "assets/fonts/Poppins-Bold.ttf"), 13)
    places = [("UNITED KINGDOM",-2.8,54.5),("GERMANY",10.2,51.2),
              ("SPAIN",-3.6,40.3),("ITALY",12.4,42.5),("FRANCE",2.0,46.0)]
    for label, lon, lat in places:
        x, y = px(lon, lat)
        box = draw.textbbox((0, 0), label, font=font)
        tw, th = box[2]-box[0], box[3]-box[1]
        draw.text((x-tw/2, y-th/2), label, font=font, fill=(239,239,233,220),
                  stroke_width=2, stroke_fill=(12,18,22,145))
    labels.save(ASSETS / "assets/canary/natural-earth-geo-labels.png")


def create_relief_lighting():
    """Build soft, direction-dependent hillshade accents from the matching relief plate.

    The Natural Earth raster has the same crop and registration as the NASA plate.
    Its shaded relief supplies terrain normals; four low-contrast light directions
    are then crossfaded in the plan so ridges catch a moving, restrained key light.
    """
    relief = np.asarray(Image.open(CATALOG / "maps/natural_earth_hypso_relief_water.jpg")
                        .convert("RGB"), dtype=np.float32) / 255.0
    # Blue-dominant pixels are water. Keep the lighting on the land surface only.
    land = np.clip((relief[..., 0] - relief[..., 2] + 0.12) / 0.32, 0.0, 1.0)
    luma_raw = 0.2126 * relief[..., 0] + 0.7152 * relief[..., 1] + 0.0722 * relief[..., 2]
    luma = np.asarray(Image.fromarray(np.uint8(luma_raw * 255)).filter(
        ImageFilter.GaussianBlur(7.0)), dtype=np.float32) / 255.0
    gy, gx = np.gradient(luma)
    gx = Image.fromarray(np.uint8(np.clip(gx * 255 / 0.09 + 128, 0, 255))).filter(ImageFilter.GaussianBlur(2.0))
    gy = Image.fromarray(np.uint8(np.clip(gy * 255 / 0.09 + 128, 0, 255))).filter(ImageFilter.GaussianBlur(2.0))
    gx = (np.asarray(gx, dtype=np.float32) - 128.0) * 0.09 / 255.0
    gy = (np.asarray(gy, dtype=np.float32) - 128.0) * 0.09 / 255.0
    for index, azimuth in enumerate((315, 45, 135, 225)):
        angle = np.deg2rad(azimuth)
        # Directional derivative approximates a moving grazing light. The alpha
        # stays low so the NASA surface remains the dominant visual texture.
        facing = gx * np.cos(angle) - gy * np.sin(angle)
        alpha = np.clip((np.abs(facing) - 0.0002) * 70.0, 0.0, 0.24) * land
        warm = facing >= 0
        rgb = np.empty((*alpha.shape, 3), dtype=np.uint8)
        rgb[warm] = (255, 226, 177)
        rgb[~warm] = (69, 92, 120)
        rgba = np.dstack((rgb, np.uint8(np.clip(alpha * 255, 0, 255))))
        Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(0.65)).save(
            ASSETS / f"assets/canary/relief-grazing-light-{index+1}.png")


def build():
    (ASSETS / "assets/canary").mkdir(parents=True, exist_ok=True)
    create_france_glow()
    create_geo_labels()
    create_relief_lighting()
    nasa = Image.open(CATALOG / "maps/nasa_blue_marble_august.jpg").convert("RGB")
    # This NASA asset is already a regional Atlantic/Europe crop matching BOUNDS.
    nasa = nasa.resize(MAP_SIZE, Image.Resampling.LANCZOS)
    nasa.save(ASSETS / "assets/canary/nasa-paris-zoom-map.jpg", quality=95, subsampling=0)

    # A two-stage camera move: a broad Atlantic-to-Europe push, then a tighter
    # geographic approach to Paris. Dense samples preserve one continuous easing curve.
    lon, lat = PARIS
    dpx, dpy = px(lon, lat)
    dx, dy = dpx-MAP_SIZE[0]/2, dpy-MAP_SIZE[1]/2
    paris_x_keys, paris_y_keys = [], []
    zoom_keys, x_keys, y_keys = [], [], []
    for frame in range(0, 145, 2):
        u = frame / 144
        progress = u*u*(3-2*u)
        # Short initial glide, broad approach, then a slower final landing.
        zoom = 1.0 + 0.58*min(1.0, progress*1.45) + 1.18*max(0.0, (progress-0.28)/0.72)
        zoom = min(zoom, 2.76)
        zoom_keys.append((frame, zoom))
        x_keys.append((frame, -zoom*progress*dx))
        y_keys.append((frame, -zoom*progress*dy))
    for frame in (170, 198, 239):
        zoom_keys.append((frame, 2.76)); x_keys.append((frame, -2.76*dx)); y_keys.append((frame, -2.76*dy))
    map_motion = [tr("scale", zoom_keys, "linear"), tr("position_x", x_keys, "linear"),
                  tr("position_y", y_keys, "linear")]
    map_in = tr("opacity", [(0, 1), (239, 1)], "linear")
    layers = [
        {"id": "bg", "type": "color", "color": [0.008, 0.014, 0.025, 1], "size": [W,H],
         "start_frame": 0, "duration_frames": DURATION},
        {"id": "nasa-blue-marble", "type": "image", "asset": "assets/canary/nasa-paris-zoom-map.jpg",
         "size": list(MAP_SIZE), "position": list(ATLAS_POS), "fit": "contain", "start_frame": 0,
         "duration_frames": DURATION, "animation": {"tracks": map_motion + [map_in]}},
    ]
    # Subtle country context lines first; geo labels are attached to the same map transform.
    layers.append({"id":"country-context","type":"image","asset":"assets/canary/natural-earth-boundaries.png",
        "size":list(MAP_SIZE),"position":list(ATLAS_POS),"fit":"contain","start_frame":0,"duration_frames":DURATION,
        "animation":{"tracks":map_motion + [tr("opacity",[(0,.48),(239,.48)],"linear")]}})
    layers.append({"id":"geo-labels","type":"image","asset":"assets/canary/natural-earth-geo-labels.png",
        "size":list(MAP_SIZE),"position":list(ATLAS_POS),"fit":"contain","start_frame":0,"duration_frames":DURATION,
        "animation":{"tracks":map_motion + [tr("opacity",[(0,.85),(60,.85),(94,0),(239,0)],"in_out_cubic")]}})
    # Give the terrain its own moving light response. Each grazing-light plate is
    # derived from the registered Natural Earth shaded-relief raster and stays
    # locked to the NASA geography while the illumination travels across ridges.
    light_phases = [
        [(0,.76),(45,.52),(90,.18),(135,0),(180,.18),(239,.52)],
        [(0,.18),(45,.52),(90,.76),(135,.52),(180,.18),(239,0)],
        [(0,0),(45,.18),(90,.52),(135,.76),(180,.52),(239,.18)],
        [(0,.52),(45,.18),(90,0),(135,.18),(180,.52),(239,.76)],
    ]
    for i, opacity_keys in enumerate(light_phases):
        layers.append({"id":f"terrain-grazing-light-{i+1}","type":"image",
            "asset":f"assets/canary/relief-grazing-light-{i+1}.png","size":list(MAP_SIZE),
            "position":list(ATLAS_POS),"fit":"contain","start_frame":0,"duration_frames":DURATION,
            "animation":{"tracks":map_motion + [tr("opacity",opacity_keys,"in_out_cubic")]}})
    # Reveal a soft fill in concentric geographic bands, expanding out from Paris.
    for i, start in enumerate((66, 71, 76, 81, 86, 91)):
        layers.append({"id":f"france-fill-wave-{i+1}","type":"image",
            "asset":f"assets/canary/france-fill-wave-{i+1}.png","size":list(MAP_SIZE),
            "position":list(ATLAS_POS),"fit":"contain","start_frame":0,"duration_frames":DURATION,
            "animation":{"tracks":map_motion + [tr("opacity",[(0,0),(start,0),(start+7,.96),(239,.96)],"out_cubic")]}})
    for name, opacity in [("france-border-glow.png", .70),
                          ("france-border-soft.png", .85),
                          ("france-border-crisp.png", 1.0)]:
        layers.append({"id":name,"type":"image","asset":f"assets/canary/{name}","size":list(MAP_SIZE),
            "position":list(ATLAS_POS),"fit":"contain","start_frame":0,"duration_frames":DURATION,
            "animation":{"tracks":map_motion + [tr("opacity",[(0,0),(65,0),(92,opacity),(125,opacity),
                                                                        (150,opacity*.82),(170,opacity)],"out_cubic")]}})

    # The Paris marker uses the same camera transform as the map, with inverse scale,
    # so it stays attached to the real coordinate throughout the move.
    # position tracks are offsets from the layer's base position. Follow the same
    # projected map point every frame, while inverse scaling keeps the marker crisp.
    marker_x, marker_y, inv_scale = [], [], []
    for idx, (f, z) in enumerate(zoom_keys[:73]):
        p = min(1.0, (f/144)**2*(3-2*f/144))
        marker_x.append((f, (z-1-z*p)*dx + PARIS_REGISTRATION[0]*p))
        marker_y.append((f, (z-1-z*p)*dy + PARIS_REGISTRATION[1]*p))
        inv_scale.append((f, 1.0/z))
    for f in (170,198,239):
        marker_x.append((f,-dx+PARIS_REGISTRATION[0])); marker_y.append((f,-dy+PARIS_REGISTRATION[1]))
        inv_scale.append((f,1/2.76))
    layers.append({"id":"paris-dot","type":"shape","shape":{"type":"ellipse","fill":[1,.77,.40,1],
        "stroke":{"color":"#FFF0D2","width":2}},"size":[18,18],"position":[W/2+dx,H/2+dy],
        "start_frame":0,"duration_frames":DURATION,"animation":{"tracks":[
            tr("position_x",marker_x,"linear"),tr("position_y",marker_y,"linear"),
            tr("scale",inv_scale,"linear"),tr("opacity",[(0,0),(58,0),(76,1),(239,1)],"out_cubic")]}})
    body = "assets/fonts/DejaVuSans.ttf"
    bold = "assets/fonts/Poppins-Bold.ttf"
    layers.extend([
        {"id":"france-title","type":"text","text":"FRANCE","size":[360,54],"position":[640,565],
         "start_frame":116,"duration_frames":124,"style":{"font":bold,"font_size":30,"fill":"#F7F4ED",
            "fit_mode":"shrink_only","min_font_size":26,"max_font_size":30},
         "animation":{"tracks":[tr("opacity",[(0,0),(18,1),(100,1),(124,.92)],"out_cubic"),
                                   tr("position_y",[(0,16),(20,0),(124,0)],"out_cubic")]}},
        {"id":"paris-label","type":"text","text":"PARIS  ·  48.8566° N  2.3522° E","size":[400,26],
         "position":[640,604],"start_frame":134,"duration_frames":106,
         "style":{"font":body,"font_size":15,"fill":"#F8D69D"},
         "animation":{"tracks":[tr("opacity",[(0,0),(16,.96),(106,.96)],"out_cubic"),
                                   tr("position_y",[(0,10),(18,0),(106,0)],"out_cubic")]}},
        {"id":"paris-leader","type":"shape","shape":{"type":"rect","fill":[1,.76,.40,.72]},
         "size":[1,44],"position":[640,529],"start_frame":124,"duration_frames":116,
         "animation":{"tracks":[tr("scale_x",[(0,.01),(17,1),(116,1)],"out_cubic"),
                                   tr("opacity",[(0,0),(14,.72),(116,.72)],"out_cubic")]}},
    ])

    job = "france_paris_nasa_zoom_v1"
    plan = {"schema":"chronon.render-plan.v3","version":3,"job_id":job,
        "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,"duration_frames":DURATION},
        "layers":layers,"output":{"path":f"{job}.mp4","format":"mp4","codec":"h264"}}
    plans, renders = OUT/"plans", OUT/"renders"
    plans.mkdir(parents=True, exist_ok=True); renders.mkdir(parents=True, exist_ok=True)
    pp, out = plans/f"{job}.plan.json", renders/f"{job}.mp4"
    pp.write_text(json.dumps(plan, indent=2)+"\n")
    subprocess.run([str(CLI),"render-plan","--input",str(pp),"--assets-root",str(ASSETS),"--output",str(out),
        "--backend","software","--encode-preset","veryfast","--trace",str(renders/f"{job}.pftrace")],
        cwd=ROOT, check=True)
    print(out)


if __name__ == "__main__":
    build()
