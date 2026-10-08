#!/usr/bin/env python3
"""Render Brazil map animations from the supplied reference cards."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_destructive_dark_maps as maps  # noqa: E402

OUT = HERE.parents[1] / "out" / "brazil_reference_styles_v3"
OUT.mkdir(parents=True, exist_ok=True)
FPS, FRAMES = 30, 150
OCEAN = (157, 94, 37)  # BGR, blue teal
PALE_LAND = (191, 220, 242)
BRAZIL_ORANGE = (45, 91, 222)
YELLOW = (0, 224, 255)
WHITE = (246, 247, 243)
BRAZIL = maps.GEO.get_country_rings("Brazil")
BAHIA_FILE = HERE.parents[1] / "catalog" / "ne_10m_admin_1_bahia.geojson"
with BAHIA_FILE.open(encoding="utf-8") as f:
    _bahia_feature = json.load(f)["features"][0]
BAHIA = [np.asarray(poly[0], dtype=np.float32)
         for poly in _bahia_feature["geometry"]["coordinates"]]

SCENES = [
    ("Ilha de Vera Cruz", "ilha_vera_cruz", (-45, -13, 13), (-39.0646, -16.4435, 3200)),
    ("Fortaleza Recife Salvador", "northeast_cities", (-40, -8, 16), (-39, -9, 48)),
    ("Venezuela Guyana Suriname", "north_labels", (-59, 4, 13), (-58, 4, 24)),
    ("Porto Seguro", "porto_seguro", (-40.5, -15, 20), (-39.0646, -16.4435, 3200)),
]


def lerp(a, b, t):
    return a + (b - a) * t


def mask_for_polys(polys):
    mask = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
    if polys:
        cv2.fillPoly(mask, polys, 255, shift=maps.SUBPIXEL_SHIFT)
    return mask


def make_pin_mask(x, y, radius=25):
    mask = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
    cv2.circle(mask, (x, y - radius), radius, 255, -1, cv2.LINE_AA)
    cv2.fillConvexPoly(mask, np.array([[x-radius+3,y-radius//2],[x+radius-3,y-radius//2],[x,y+radius+15]],np.int32), 255, cv2.LINE_AA)
    return mask


def pin(gpu, x, y, color, t=1.0, white_center=False, size=25):
    if t <= 0:
        return
    pin_mask = make_pin_mask(x, y, size)
    glow = gpu.gaussian(pin_mask, 18)
    gpu.blend_mask(glow, color, .48 * t)
    gpu.blend_mask(pin_mask, color, .98 * t)
    center = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
    cv2.circle(center, (x, y-size), max(7, size//2), 255, -1, cv2.LINE_AA)
    gpu.blend_mask(center, WHITE if white_center else (10, 140, 237), .98 * t)


def label_box(frame, text, x, y, color=YELLOW, font=cv2.FONT_HERSHEY_TRIPLEX,
              scale=.82, pad_x=14, pad_y=8, background=(5, 8, 11)):
    (tw, th), base = cv2.getTextSize(text, font, scale, 2)
    cv2.rectangle(frame, (x, y), (x+tw+2*pad_x, y+th+2*pad_y+base), background, -1)
    cv2.putText(frame, text, (x+pad_x, y+th+pad_y), font, scale, color, 2, cv2.LINE_AA)


def grid(frame, color=(140, 186, 196), alpha=.30, gap=80):
    lines = np.zeros_like(frame)
    for x in range(0, maps.WIDTH, gap):
        cv2.line(lines, (x,0),(x,maps.HEIGHT),color,1,cv2.LINE_AA)
    for y in range(0, maps.HEIGHT, gap):
        cv2.line(lines, (0,y),(maps.WIDTH,y),color,1,cv2.LINE_AA)
    return cv2.addWeighted(frame, 1, lines, alpha, 0)


def base_grade(frame, style):
    if style in ("ilha_vera_cruz", "porto_seguro"):
        # Keep the topo plate crisp and natural; avoid the old washed parchment treatment.
        return cv2.convertScaleAbs(frame, alpha=1.04, beta=-3)
    if style == "northeast_cities":
        return cv2.addWeighted(frame,.28,np.full_like(frame,(48,94,207)),.72,0)
    return cv2.addWeighted(frame,.26,np.full_like(frame,(191,226,226)),.74,0)


def add_title_mask(gpu, text, origin, color, size=1.0, italic=True, shadow=True):
    face = cv2.FONT_HERSHEY_TRIPLEX | (cv2.FONT_ITALIC if italic else 0)
    mask = np.zeros((maps.HEIGHT,maps.WIDTH),dtype=np.uint8)
    cv2.putText(mask,text,(origin[0]+(2 if shadow else 0),origin[1]+(3 if shadow else 0)),face,size,255,5,cv2.LINE_AA)
    if shadow:
        gpu.blend_mask(gpu.gaussian(mask,3), (12,22,28),.62)
    cv2.putText(mask,text,origin,face,size,255,4,cv2.LINE_AA)
    gpu.blend_mask(mask,color,.99)


def location_marker(gpu, x, y, progress):
    """A restrained local locator instead of a country-sized highlight."""
    if progress <= 0:
        return
    glow = np.zeros((maps.HEIGHT, maps.WIDTH), dtype=np.uint8)
    ring = np.zeros_like(glow)
    dot = np.zeros_like(glow)
    cv2.circle(glow, (x, y), 30, 255, -1, cv2.LINE_AA)
    cv2.circle(ring, (x, y), 17, 255, 2, cv2.LINE_AA)
    cv2.circle(dot, (x, y), 6, 255, -1, cv2.LINE_AA)
    gpu.blend_mask(gpu.gaussian(glow, 18), (18, 140, 255), .30 * progress)
    gpu.blend_mask(ring, (248, 248, 244), .92 * progress)
    gpu.blend_mask(dot, (18, 140, 255), .98 * progress)


def modern_location_title(frame, title, eyebrow, progress):
    if progress <= 0:
        return
    x, y, w, h = 84, 834, 690, 164
    roi = frame[y:y+h, x:x+w]
    panel = np.full_like(roi, (26, 29, 31))
    cv2.addWeighted(panel, .80 * progress, roi, 1 - .80 * progress, 0, roi)
    accent = (34, 154, 255)
    cv2.line(frame, (x+3, y+24), (x+3, y+h-24), accent, 4, cv2.LINE_AA)
    cv2.putText(frame, eyebrow.upper(), (x+31, y+57), cv2.FONT_HERSHEY_SIMPLEX,
                .62, (191, 202, 207), 1, cv2.LINE_AA)
    cv2.putText(frame, title.upper(), (x+30, y+119), cv2.FONT_HERSHEY_SIMPLEX,
                1.36, (249, 249, 245), 2, cv2.LINE_AA)


def reference_ilha_title(frame, progress):
    if progress <= 0:
        return
    face = cv2.FONT_HERSHEY_DUPLEX
    for text, y, color in [("ILHA DE", 510, WHITE), ("VERA CRUZ", 595, YELLOW)]:
        scale, thickness = 1.72, 4
        (tw, th), base = cv2.getTextSize(text, face, scale, thickness)
        x = 1110
        pad_x, pad_y = 22, 9
        x1, y1 = x, y-th-pad_y
        x2, y2 = x+tw+2*pad_x, y+pad_y+base
        roi = frame[y1:y2, x1:x2]
        dark = np.full_like(roi, (8, 7, 7))
        cv2.addWeighted(dark, .94*progress, roi, 1-.94*progress, 0, roi)
        text_layer = np.zeros_like(frame)
        cv2.putText(text_layer, text, (x+pad_x, y), face, scale, color,
                    thickness, cv2.LINE_AA)
        frame[:] = cv2.addWeighted(frame, 1.0, text_layer, progress, 0)


def reference_ilha_title_open_cv(frame, progress):
    """Same timing and typography, rendered directly over the natural map."""
    if progress <= 0:
        return
    face = cv2.FONT_HERSHEY_DUPLEX
    for text, y, color in [("ILHA DE", 510, WHITE), ("VERA CRUZ", 595, YELLOW)]:
        origin = (1132, y)
        cv2.putText(frame, text, origin, face, 1.72, (8, 7, 7), 10, cv2.LINE_AA)
        layer = np.zeros_like(frame)
        cv2.putText(layer, text, origin, face, 1.72, color, 4, cv2.LINE_AA)
        frame[:] = cv2.addWeighted(frame, 1.0, layer, progress, 0)


def teal_reference_grade(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    # Deep teal relief, with enough luminance to keep topography visible.
    out = np.empty_like(frame)
    out[:, :, 0] = np.clip(70 + 70*gray, 0, 255)
    out[:, :, 1] = np.clip(54 + 82*gray, 0, 255)
    out[:, :, 2] = np.clip(12 + 35*gray, 0, 255)
    return out


def draw_reference_graticule(frame, alpha=.052, gap=112):
    lines = np.zeros_like(frame)
    color = (146, 131, 79)
    for x in range(0, maps.WIDTH, gap):
        cv2.line(lines, (x, 0), (x, maps.HEIGHT), color, 1, cv2.LINE_AA)
    for y in range(0, maps.HEIGHT, gap):
        cv2.line(lines, (0, y), (maps.WIDTH, y), color, 1, cv2.LINE_AA)
    cv2.addWeighted(frame, 1.0, lines, alpha, 0, frame)


def draw_reference_pin(gpu, x, y, t):
    if t <= 0:
        return
    glow = np.zeros((maps.HEIGHT, maps.WIDTH), np.uint8)
    dot = np.zeros_like(glow)
    cv2.circle(glow, (x, y), 14, 255, -1, cv2.LINE_AA)
    cv2.circle(dot, (x, y), 4, 255, -1, cv2.LINE_AA)
    gpu.blend_mask(gpu.gaussian(glow, 14), (164, 236, 255), .68*t)
    gpu.blend_mask(dot, (246, 248, 244), .96*t)


def draw_reference_watermark(frame):
    # Small serif monogram matching the supplied north-east corner mark.
    face = cv2.FONT_HERSHEY_TRIPLEX | cv2.FONT_ITALIC
    cv2.putText(frame, "N", (1670, 133), face, 3.0, (170, 196, 135), 2, cv2.LINE_AA)
    cv2.putText(frame, "L", (1723, 145), face, 2.8, (170, 196, 135), 2, cv2.LINE_AA)


def apply_basemap_variant(frame, variant):
    """Change only the basemap treatment; all animated overlays stay identical."""
    if variant == "negative":
        return cv2.bitwise_not(frame)
    return frame


def render_ilha_reference(scene, variant="normal_open"):
    title, slug, start, _ = scene
    maps.RENDERER_MODE = "opencv"
    end = (-39.2, -13.4, 70)
    camera_frames = 102
    provider = "esri_topo" if variant == "normal_opencv" else "esri_hillshade"
    cam = maps.DynamicCamera(start, end, camera_frames, provider=provider)
    out_dir = OUT / ("Normal OpenCV" if variant == "normal_opencv" else variant.title())
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"ilha_vera_cruz_{variant}_5s.mp4"
    writer = maps.H264NVENCStream(out)
    settled_land_mask = None
    yy, xx = np.mgrid[0:maps.HEIGHT, 0:maps.WIDTH]
    radius = ((xx-maps.WIDTH/2)/(maps.WIDTH*.72))**2 + ((yy-maps.HEIGHT/2)/(maps.HEIGHT*.78))**2
    vignette = np.clip(1.12 - .38*radius, .60, 1.0).astype(np.float32)
    for f in range(FRAMES):
        cx, cy, scale = cam.get_pose(f)
        raw_frame = cam.render_base(cx, cy, scale)
        base = (raw_frame if variant in ("white", "negative", "normal_opencv")
                else teal_reference_grade(raw_frame))
        frame = apply_basemap_variant(base, variant)
        if f >= camera_frames and settled_land_mask is None:
            half_lon = maps.WIDTH / (2.0*scale)
            half_lat = maps.HEIGHT / (2.0*scale*180.0/math.pi)
            visible_rings = [ring for ring, min_lon, max_lon, min_lat, max_lat
                             in maps.GEO.all_land_rings
                             if max_lon >= cx-half_lon and min_lon <= cx+half_lon
                             and max_lat >= cy-half_lat and min_lat <= cy+half_lat]
            settled_land_mask = mask_for_polys(cam.project_rings(visible_rings, cx, cy, scale))
        if settled_land_mask is not None:
            ocean_mask = cv2.bitwise_not(settled_land_mask)
            grade_gpu = maps.GPUMapFrame(frame)
            if variant == "white":
                # White land against black water; the selected state is the
                # inverse so it remains readable instead of disappearing.
                grade_gpu.blend_mask(settled_land_mask, (246, 246, 242), .96)
                grade_gpu.blend_mask(ocean_mask, (5, 6, 8), .97)
            elif variant == "negative":
                # Exact polarity inverse of White.
                grade_gpu.blend_mask(settled_land_mask, (7, 8, 10), .96)
                grade_gpu.blend_mask(ocean_mask, (245, 245, 241), .97)
            elif variant == "blue":
                grade_gpu.blend_mask(settled_land_mask, (75, 80, 24), .42)
                grade_gpu.blend_mask(ocean_mask, (137, 103, 18), .34)
            frame = grade_gpu.to_numpy()
        gpu = maps.GPUMapFrame(frame)
        region_mask = mask_for_polys(cam.project_rings(BAHIA, cx, cy, scale))
        area_t = maps.smooth_swoop((f-camera_frames)/12)
        if variant == "white":
            region_color = (7, 8, 10)
        elif variant == "negative":
            region_color = (246, 246, 242)
        else:
            region_color = (178, 211, 244)
        gpu.blend_mask(region_mask, region_color, .98*area_t)
        frame = gpu.to_numpy()
        # Preserve relief texture in the reference blue; keep the monochrome
        # variants crisp so their opposite polarities remain unambiguous.
        if variant == "blue":
            source_relief = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            shade = (source_relief - 128.0) * .34
            relief_tint = np.empty_like(frame, dtype=np.float32)
            relief_tint[:, :, 0] = 178 + shade
            relief_tint[:, :, 1] = 211 + shade
            relief_tint[:, :, 2] = 244 + shade
            alpha = (region_mask.astype(np.float32) / 255.0 * .27 * area_t)[..., None]
            frame = np.clip(frame.astype(np.float32)*(1-alpha) + relief_tint*alpha, 0, 255).astype(np.uint8)
        gpu = maps.GPUMapFrame(frame)
        x, y = cam.project_point(-39.0646, -16.4435, cx, cy, scale)
        draw_reference_pin(gpu, x, y, maps.smooth_swoop((f-camera_frames-3)/8))
        frame = gpu.to_numpy()
        draw_reference_graticule(frame)
        # Soft cinematic falloff around the outer edge, like the supplied card.
        frame = np.clip(frame.astype(np.float32)*vignette[..., None], 0, 255).astype(np.uint8)
        text_t = maps.smooth_swoop((f-camera_frames-20)/10)
        if variant == "normal_opencv":
            reference_ilha_title_open_cv(frame, text_t)
        else:
            reference_ilha_title(frame, text_t)
        draw_reference_watermark(frame)
        # One small atmospheric glow in the open water, matching the reference sparkle.
        if f > camera_frames:
            cv2.circle(frame, (1688, 814), 3, (206, 233, 247), -1, cv2.LINE_AA)
        writer.write(frame)
    writer.close()
    print(f"Rendered {title} in reference style: {out}", flush=True)


def render(scene):
    title, slug, start, end = scene
    if slug == "ilha_vera_cruz":
        return render_ilha_reference(scene, getattr(render, "variant", "normal_open"))
    maps.RENDERER_MODE="opencv"
    # Let the camera finish its move before any marker or typography appears.
    closeup = slug in ("ilha_vera_cruz", "porto_seguro")
    camera_frames = 102 if closeup else 84
    cam=maps.DynamicCamera(start,end,camera_frames,provider="esri_topo")
    frames=[]
    for f in range(FRAMES):
        shape_progress=maps.smooth_swoop((f-camera_frames)/14)
        point_start = camera_frames + 2 if closeup else 88
        text_start = camera_frames + 18 if closeup else 104
        point_progress=maps.smooth_swoop((f-point_start)/10)
        text_progress=maps.smooth_swoop((f-text_start)/10)
        cx,cy,scale=cam.get_pose(f)
        frame=base_grade(cam.render_base(cx,cy,scale),slug)
        if not closeup:
            frame=grid(frame,(150,188,194),.25,82)
        gpu=maps.GPUMapFrame(frame)
        brazil_polys=cam.project_rings(BRAZIL,cx,cy,scale)
        brazil_mask=mask_for_polys(brazil_polys)

        if slug=="ilha_vera_cruz":
            x,y=cam.project_point(-39.0646,-16.4435,cx,cy,scale)
            location_marker(gpu,x,y,point_progress)
            frame=gpu.to_numpy()
            modern_location_title(frame,"Ilha de Vera Cruz","Bahia | Brasil",text_progress)
            gpu=maps.GPUMapFrame(frame)
        elif slug=="northeast_cities":
            gpu.blend_mask(brazil_mask,BRAZIL_ORANGE,.88*shape_progress)
            cities=[("Fortaleza",-38.5267,-3.7319,(-185,-120)),("Recife",-34.8770,-8.0476,(-95,-132)),("Salvador",-38.5014,-12.9777,(-150,-125))]
            for city,lon,lat,offset in cities:
                x,y=cam.project_point(lon,lat,cx,cy,scale)
                # white locator with subtle white ring
                ring=np.zeros((maps.HEIGHT,maps.WIDTH),dtype=np.uint8)
                cv2.circle(ring,(x,y-25),77,255,4,cv2.LINE_AA)
                if f >= 88:
                    gpu.blend_mask(gpu.gaussian(ring,14),WHITE,.58*point_progress)
                    pin(gpu,x,y,WHITE,point_progress,white_center=False,size=28)
                if f >= 104:
                    add_title_mask(gpu,city,(x+offset[0],y+offset[1]),YELLOW,1.35*text_progress,True,True)
        elif slug=="north_labels":
            gpu.blend_mask(brazil_mask,(40,157,16),.92*shape_progress)
            if f >= 88:
                x,y=cam.project_point(-60,2,cx,cy,scale)
                pin(gpu,x,y,BRAZIL_ORANGE,point_progress,white_center=True,size=26)
            if f >= 104:
                other=[("COLOMBIA",180,315), ("VENEZUELA",520,150), ("GUYANA",850,235),
                       ("SURINAME",970,350), ("GUIANA FRANCESE",1220,245)]
                for text,x,y in other:
                    label_box(frame,text,x,y,(8,54,87),cv2.FONT_HERSHEY_TRIPLEX,.98,16,9,YELLOW)
                gpu=maps.GPUMapFrame(frame)
                gpu.blend_mask(brazil_mask,(40,157,16),.92*shape_progress)
        else:
            x,y=cam.project_point(-39.0646,-16.4435,cx,cy,scale)
            location_marker(gpu,x,y,point_progress)
            frame=gpu.to_numpy()
            modern_location_title(frame,"Porto Seguro","Bahia | Brasil",text_progress)
            gpu=maps.GPUMapFrame(frame)

        # Keep the fine reference grid visible above every animated shape.
        if not closeup:
            grid_mask=np.zeros((maps.HEIGHT,maps.WIDTH),dtype=np.uint8)
            for gx in range(0,maps.WIDTH,82): cv2.line(grid_mask,(gx,0),(gx,maps.HEIGHT),255,1,cv2.LINE_AA)
            for gy in range(0,maps.HEIGHT,82): cv2.line(grid_mask,(0,gy),(maps.WIDTH,gy),255,1,cv2.LINE_AA)
            gpu.blend_mask(grid_mask,(133,183,195),.10)
        frames.append(gpu.to_numpy())
    out=OUT/f"{slug}_5s.mp4"
    maps.write_video_h264(frames,out)
    print(f"Rendered {title}: {out}",flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scene",choices=[s[1] for s in SCENES])
    p.add_argument("--variant", choices=["white", "blue", "negative", "normal_opencv"], default="blue")
    args=p.parse_args()
    if not torch.cuda.is_available(): raise RuntimeError("CUDA required; CPU fallback disabled")
    enc=subprocess.run(["ffmpeg","-hide_banner","-encoders"],capture_output=True,text=True,check=True).stdout
    if "h264_nvenc" not in enc: raise RuntimeError("h264_nvenc required; software encoding disabled")
    print(f"GPU renderer active: {torch.cuda.get_device_name(0)}; encoder=h264_nvenc",flush=True)
    render.variant = args.variant
    for s in SCENES:
        if not args.scene or s[1]==args.scene: render(s)


if __name__=="__main__": main()
