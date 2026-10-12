#!/usr/bin/env python3
"""GPU-backed documentary map scene compositor.

Map pixels arrive as cv2.UMat from FastPlateSampler.sample_opencl. All full-frame
color finishing, mask feathering, glow blur, alpha compositing and contrast
operations remain UMat/OpenCL until the final readback for NVENC. Vector outlines
and text glyph masks are rasterized on the host (OpenCV/Pillow do not expose a
portable polygon/text OpenCL rasterizer); those masks are immediately uploaded,
then every image-space effect/composite is done on the GPU. No CPU fallback for
frame processing is permitted.

Geography uses Natural Earth 50m country geometry plus WGS84 points/routes;
zone polygons are labeled schematic unless caller supplies sourced geometry.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from map_editorial import load_borders

STYLE = {
    "country_px": 58,
    "place_px": 40,
    "route_px": 32,
    "secondary_px": 23,
    "legend_px": 22,
    "capsule_pad_x": 22,
    "capsule_pad_y": 10,
    "safe_margin": 54,
    "grid_alpha": 0.065,
    "vignette_strength": 0.14,
    "map_exposure": 0.89,
    "map_contrast": 0.97,
    "saturation": 0.76,
}

WHITE = (242, 244, 238)
DARK = (7, 14, 21)
RED = (38, 48, 242)       # BGR, saturated red
RED_HI = (130, 150, 255)  # warm white/red highlight
CYAN = (255, 205, 68)
BLUE = (255, 166, 74)
TEAL = (214, 202, 65)
PINK = (205, 105, 238)
GREEN = (96, 164, 91)

FONT_DIRS = [Path("/usr/share/fonts/truetype/msttcorefonts"),
             Path("/usr/share/fonts/truetype/liberation"),
             Path("/usr/share/fonts/truetype/liberation2"),
             Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/Chronon3d/assets/fonts")]
_FONT_CACHE = {}
_SOLID_CACHE = {}
_GPU_OPS = {"opencl": 0, "mask_uploads": 0, "composites": 0, "blur": 0}
_VIGNETTE_CACHE = {}
_GRID_CACHE = {}
_CURRENT_SIZE = (1920, 1080)


def reset_gpu_counters():
    for k in _GPU_OPS:
        _GPU_OPS[k] = 0


def gpu_counters():
    return dict(_GPU_OPS)


def _assert_gpu(frame):
    if not isinstance(frame, cv2.UMat):
        raise TypeError(f"editorial GPU compositor requires cv2.UMat, got {type(frame).__name__}")
    if not cv2.ocl.haveOpenCL():
        raise RuntimeError("OpenCL unavailable for editorial map compositor")
    cv2.ocl.setUseOpenCL(True)
    if not cv2.ocl.useOpenCL():
        raise RuntimeError("OpenCL did not activate for editorial map compositor")


def geo_project(lat, lon, anchor, zoom, width, height):
    """Exact Web-Mercator screen projection used by FastPlateSampler.sample_opencl.

    FastPlateSampler crops the requested camera center to output center. At
    integer tile zoom, each global Mercator pixel at that zoom maps to
    2**fractional_zoom pixels in the rendered canvas.
    """
    from dynamic_tile_pyramid import latlon_to_global_px
    z = math.floor(zoom)
    scale = 2.0 ** (zoom - z)
    gx, gy = latlon_to_global_px(lat, lon, z)
    ax, ay = latlon_to_global_px(anchor[0], anchor[1], z)
    return (width * 0.5 + (gx - ax) * scale,
            height * 0.5 + (gy - ay) * scale)


def _font(size: int, condensed: bool = True):
    key = (size, condensed)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    from PIL import ImageFont
    names = (["Oswald-Bold.ttf", "LiberationSansNarrow-Bold.ttf", "Arial-Bold.ttf"]
             if condensed else ["Inter-Medium.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"])
    for name in names:
        for directory in FONT_DIRS:
            p = directory / name
            if p.is_file():
                try:
                    _FONT_CACHE[key] = ImageFont.truetype(str(p), size)
                    return _FONT_CACHE[key]
                except OSError:
                    pass
    _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _stage(p, start, duration):
    if duration <= 0:
        return float(p >= start)
    t = max(0.0, min(1.0, (p - start) / duration))
    return t * t * (3.0 - 2.0 * t)


def _blank_mask(W, H):
    return np.zeros((H, W), dtype=np.uint8)


def _polygon_masks(iso, project, W, H, reveal=1.0, width=0):
    """Host rasterization only; closed real NE rings. Returns binary masks.

    Reveal uses the linearly sampled arc-length prefix; mask fill always uses
    the complete country geometry, never a circle/ellipse substitute.
    """
    data = load_borders().get(iso)
    if not data:
        raise ValueError(f"country geometry missing for ISO {iso}")
    fill = _blank_mask(W, H)
    stroke = _blank_mask(W, H)
    for ring in data["polygons"]:
        pts = np.asarray([project(lat, lon) for lon, lat in ring], np.int32)
        if pts.shape[0] < 4:
            continue
        # Restrict work for rings completely outside the canvas.
        if (pts[:, 0].max() < -20 or pts[:, 0].min() > W + 20 or
                pts[:, 1].max() < -20 or pts[:, 1].min() > H + 20):
            continue
        cv2.fillPoly(fill, [pts.reshape(-1, 1, 2)], 255, lineType=cv2.LINE_AA)
        if reveal > 0:
            # Approximate trim-path by edge-length prefix on the closed ring.
            closed = pts.reshape(-1, 2)
            lens = np.hypot(np.diff(closed[:, 0]), np.diff(closed[:, 1]))
            total = float(lens.sum())
            target = max(1.0, min(1.0, reveal)) * total
            acc = 0.0
            path = [tuple(closed[0])]
            for j, length in enumerate(lens):
                if acc + length <= target:
                    path.append(tuple(closed[j + 1])); acc += float(length)
                else:
                    if length > 0:
                        t = (target - acc) / float(length)
                        q = closed[j] + (closed[j + 1] - closed[j]) * t
                        path.append((int(q[0]), int(q[1])))
                    break
            if len(path) >= 2:
                cv2.polylines(stroke, [np.asarray(path, np.int32).reshape(-1, 1, 2)],
                              False, 255, max(1, width), cv2.LINE_AA)
    return fill, stroke


def _upload_mask(mask):
    _GPU_OPS["mask_uploads"] += 1
    return cv2.UMat(np.ascontiguousarray(mask))


def _solid(W, H, color):
    key = (W, H, tuple(color))
    out = _SOLID_CACHE.get(key)
    if out is None:
        host = np.empty((H, W, 3), dtype=np.uint8)
        host[:] = color
        out = cv2.UMat(host)
        _SOLID_CACHE[key] = out
    return out


def composite_mask(frame, mask, color_bgr, alpha=1.0):
    """OpenCL alpha composite a host or GPU mask over UMat frame.

    Host masks are only geometric rasterization; a UMat mask (e.g. blurred
    glow) never downloads to CPU between effects.
    """
    _assert_gpu(frame)
    if alpha <= 0.001:
        return frame
    W,H=_CURRENT_SIZE
    if not isinstance(mask,cv2.UMat) and mask.shape[:2] != (H,W):
        raise ValueError("GPU mask dimensions differ from current frame")
    m = mask if isinstance(mask, cv2.UMat) else _upload_mask(mask)
    m3 = cv2.merge([m, m, m])
    colored = cv2.multiply(_solid(W, H, color_bgr), m3,
                           scale=float(max(0.0, min(1.0, alpha))) / 255.0)
    frame = cv2.add(frame, colored)
    _GPU_OPS["opencl"] += 2
    _GPU_OPS["composites"] += 1
    return frame


def composite_rgba(frame, rgba):
    """Composite a CPU-rasterized RGBA text/panel plate using OpenCL."""
    _assert_gpu(frame)
    if rgba.dtype != np.uint8 or rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("text/panel plate must be uint8 RGBA")
    alpha = rgba[:, :, 3]
    if not np.any(alpha):
        return frame
    H,W=rgba.shape[:2]
    if (W,H) != _CURRENT_SIZE:
        raise ValueError(f"overlay plate {(H,W)} does not match GPU frame {_CURRENT_SIZE[::-1]}")
    # Convert RGB host glyph plate into the BGR premultiplied source. Only
    # glyph rasterization is CPU; blend and frame mutation stay on OpenCL.
    bgr = np.ascontiguousarray(rgba[:, :, 2::-1])
    bgr_u = cv2.UMat(bgr)
    a_u = _upload_mask(alpha)
    a3 = cv2.merge([a_u, a_u, a_u])
    fg = cv2.multiply(bgr_u, a3, scale=1.0 / 255.0)
    inv = cv2.subtract(cv2.UMat(np.full(alpha.shape, 255, np.uint8)), a_u)
    inv3 = cv2.merge([inv, inv, inv])
    bg = cv2.multiply(frame, inv3, scale=1.0 / 255.0)
    frame = cv2.add(fg, bg)
    _GPU_OPS["opencl"] += 4
    _GPU_OPS["composites"] += 1
    return frame


def glow_mask(frame, stroke_mask, color_bgr, strength=1.0):
    """GPU medium/wide glow + crisp core from one geographic path."""
    if strength <= 0.001:
        return frame
    _assert_gpu(frame)
    H, W = stroke_mask.shape
    mask = _upload_mask(stroke_mask)
    wide = cv2.GaussianBlur(mask, (0, 0), 22)
    mid = cv2.GaussianBlur(mask, (0, 0), 9)
    _GPU_OPS["blur"] += 2
    frame = composite_mask(frame, wide, color_bgr, 0.18 * strength)
    frame = composite_mask(frame, mid, color_bgr, 0.42 * strength)
    frame = composite_mask(frame, stroke_mask, color_bgr, 1.0)
    return frame


def _base_grade(frame):
    """Exposure/contrast/saturation treatment on OpenCL."""
    _assert_gpu(frame)
    frame = cv2.convertScaleAbs(frame, alpha=STYLE["map_exposure"] * STYLE["map_contrast"], beta=-2)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    frame = cv2.addWeighted(frame, STYLE["saturation"], gray3,
                            1.0 - STYLE["saturation"], 0.0)
    _GPU_OPS["opencl"] += 3
    return frame


def _draw_grid(frame, W, H, progress):
    if progress <= 0:
        return frame
    key=(W,H)
    mask=_GRID_CACHE.get(key)
    if mask is None:
        host=_blank_mask(W,H)
        step=190
        for x in range(step//2,W,step): cv2.line(host,(x,0),(x,H-1),255,1,cv2.LINE_AA)
        for y in range(step//2,H,step): cv2.line(host,(0,y),(W-1,y),255,1,cv2.LINE_AA)
        mask=cv2.UMat(host); _GRID_CACHE[key]=mask
    return composite_mask(frame,mask,WHITE,STYLE["grid_alpha"]*progress)


def _draw_vignette(frame, W, H):
    # Upload the static spatial mask once per resolution. Grade/composite stays
    # OpenCL; this is not regenerated or copied back per frame.
    key = (W, H)
    mask = _VIGNETTE_CACHE.get(key)
    if mask is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
        mask = np.ascontiguousarray((np.clip((d - 0.55) / 0.45, 0, 1) ** 1.6 * 255).astype(np.uint8))
        mask = cv2.UMat(mask)
        _VIGNETTE_CACHE[key] = mask
    return composite_mask(frame, mask, (0, 0, 0), STYLE["vignette_strength"])


def _text_plate(W, H, entries, progress):
    """Render measured documentary typography and capsules into transparent RGBA.

    entry fields: text, center, role, reveal, accent, subtitle, leader.
    Placement is screen-space; location pins remain geographic.
    """
    from PIL import Image, ImageDraw, ImageFilter
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    safe = STYLE["safe_margin"]
    occupied = []
    for entry in entries:
        reveal = max(0.0, min(1.0, entry.get("reveal", 1.0)))
        if reveal <= 0.01:
            continue
        text = " ".join(str(entry["text"]).upper().split())
        role = entry.get("role", "place")
        target = STYLE["country_px"] if role == "country" else STYLE["route_px"] if role == "route" else STYLE["place_px"]
        min_size = 25
        color = entry.get("accent")
        subtitle = entry.get("subtitle") or ""
        # Measure and reduce only to documented minimum; if no fit, use a
        # second row/alternate candidate rather than clipping outside canvas.
        size = target
        while size > min_size:
            font = _font(size, True)
            bb = draw.textbbox((0, 0), text, font=font, stroke_width=1)
            if bb[2] - bb[0] <= W - 2 * safe - 44:
                break
            size -= 1
        font = _font(size, True)
        secondary_font = _font(STYLE["secondary_px"], False)
        tw = draw.textbbox((0, 0), text, font=font, stroke_width=1)[2]
        sh = draw.textbbox((0, 0), subtitle, font=secondary_font)[3] if subtitle else 0
        pad_x, pad_y = STYLE["capsule_pad_x"], STYLE["capsule_pad_y"]
        bw = min(W - 2 * safe, tw + pad_x * 2)
        bh = size + 2 * pad_y + (sh + 5 if subtitle else 0)
        cx, cy = entry["center"]
        # Collision-aware candidate list: above, below, right, left.
        candidates = [(cx, cy - bh - 34), (cx, cy + 34),
                      (cx + 40, cy - bh / 2), (cx - 40, cy - bh / 2)]
        chosen = None
        for tx, ty in candidates:
            x0 = int(max(safe, min(W - safe - bw, tx - bw / 2)))
            y0 = int(max(safe, min(H - safe - bh, ty)))
            box = (x0, y0, x0 + bw, y0 + bh)
            if all(box[2] <= b[0] - 10 or box[0] >= b[2] + 10 or
                   box[3] <= b[1] - 8 or box[1] >= b[3] + 8 for b in occupied):
                chosen = box
                break
        if chosen is None:
            # fail-safe layout shrinks to minimum size while preserving safe area
            x0 = int(max(safe, min(W - safe - bw, cx - bw / 2)))
            y0 = int(max(safe, min(H - safe - bh, cy - bh / 2)))
            chosen = (x0, y0, x0 + bw, y0 + bh)
        x0, y0, x1, y1 = chosen
        occupied.append(chosen)
        alpha = int(242 * reveal)
        # soft shadow + very thin divider; no pill/big app-button aesthetic
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x0, y0 + 5, x1, y1 + 5), radius=5,
                             fill=(0, 0, 0, int(130 * reveal)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        plate.alpha_composite(shadow)
        draw = ImageDraw.Draw(plate)
        draw.rounded_rectangle(chosen, radius=4, fill=(*DARK, alpha),
                               outline=(221, 230, 232, int(100 * reveal)), width=1)
        if color:
            accent_rgb = color[::-1]
            draw.rectangle((x0, y0 + 5, x0 + 4, y1 - 5), fill=(*accent_rgb, alpha))
        # letter tracking 1.8px, condensed display font
        tx = x0 + pad_x + (4 if color else 0)
        ty = y0 + pad_y
        ink = (*WHITE, int(255 * reveal))
        for ch in text:
            draw.text((tx, ty), ch, font=font, fill=ink,
                      stroke_width=1, stroke_fill=(3, 8, 12, int(210 * reveal)))
            tx += draw.textbbox((0, 0), ch, font=font)[2] + 2
        if subtitle:
            draw.text((x0 + pad_x + (4 if color else 0), y0 + pad_y + size + 2),
                      subtitle.upper(), font=secondary_font,
                      fill=(183, 203, 210, int(255 * reveal)))
        leader = entry.get("leader")
        if leader:
            lx = (x0 + x1) // 2
            ly = y0 if leader[1] < y0 else y1
            draw.line((leader[0], leader[1], lx, ly),
                      fill=(225, 235, 238, int(210 * reveal)), width=2)
    return np.asarray(plate)


def _mask_rings(rings, W, H, reveal=1.0, stroke=3):
    mask = _blank_mask(W, H)
    for coords in rings:
        pts = np.asarray(coords, np.int32).reshape(-1, 1, 2)
        if len(pts) < 4:
            continue
        if reveal >= 0.999:
            cv2.polylines(mask, [pts], True, 255, stroke, cv2.LINE_AA)
        else:
            xy = pts.reshape(-1, 2)
            lens = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
            target = max(1, float(lens.sum()) * max(0, min(1, reveal)))
            acc = 0.0
            prefix = [tuple(xy[0])]
            for i, d in enumerate(lens):
                if acc + d < target:
                    prefix.append(tuple(xy[i + 1])); acc += float(d)
                else:
                    if d > 0:
                        t = (target - acc) / float(d)
                        q = xy[i] + (xy[i + 1] - xy[i]) * t
                        prefix.append(tuple(map(int, q)))
                    break
            if len(prefix) >= 2:
                cv2.polylines(mask, [np.asarray(prefix, np.int32).reshape(-1, 1, 2)],
                              False, 255, stroke, cv2.LINE_AA)
    return mask


def _country(frame, iso, project, progress, W, H, *, fill=None, glow=None):
    data = load_borders().get(iso)
    if not data:
        raise ValueError(f"Natural Earth geometry missing: {iso}")
    rings = []
    fill_mask = _blank_mask(W, H)
    for ring in data["polygons"]:
        pts = np.asarray([project(lat, lon) for lon, lat in ring], np.int32)
        if pts.shape[0] < 4 or pts[:,0].max() < -20 or pts[:,0].min() > W+20 or pts[:,1].max() < -20 or pts[:,1].min() > H+20:
            continue
        rings.append(pts.reshape(-1,2))
        cv2.fillPoly(fill_mask, [pts.reshape(-1,1,2)], 255, lineType=cv2.LINE_AA)
    reveal = _stage(progress, 0.12, 0.32)
    stroke_mask = _mask_rings(rings, W, H, reveal, 3)
    if fill:
        frame = composite_mask(frame, fill_mask, fill[0], fill[1] * _stage(progress, 0.34, 0.24))
    if glow:
        frame = glow_mask(frame, stroke_mask, glow[0], glow[1] * _stage(progress, 0.28, 0.24))
    else:
        frame = composite_mask(frame, stroke_mask, WHITE, 0.9)
    return frame, fill_mask, stroke_mask


def _line_mask(points, W, H, width=4, dashed=False):
    mask = _blank_mask(W, H)
    pts = np.asarray(points, np.int32).reshape(-1,1,2)
    if len(pts) < 2:
        return mask
    if not dashed:
        cv2.polylines(mask, [pts], False, 255, width, cv2.LINE_AA)
        return mask
    xy=pts.reshape(-1,2)
    for (x0,y0),(x1,y1) in zip(xy,xy[1:]):
        length=max(1,int(math.hypot(x1-x0,y1-y0)))
        for t0 in range(0,length,24):
            t1=min(length,t0+14)
            a=t0/length; b=t1/length
            cv2.line(mask,(int(x0+(x1-x0)*a),int(y0+(y1-y0)*a)),
                     (int(x0+(x1-x0)*b),int(y0+(y1-y0)*b)),255,width,cv2.LINE_AA)
    return mask


def _route(frame, geo_points, project, W, H, progress, color, start,
           duration=0.24, width=5, arrow=True, dashed=False):
    if progress <= start:
        return frame
    reveal=_stage(progress,start,duration)
    pts=[project(lat,lon) for lat,lon in geo_points]
    if len(pts)<2:return frame
    lengths=[0.0]
    for a,b in zip(pts,pts[1:]): lengths.append(lengths[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
    total=lengths[-1] or 1
    dist=total*reveal
    cut=[]
    for i in range(1,len(pts)):
        if lengths[i] <= dist: cut.append(pts[i])
        else:
            a,b=pts[i-1],pts[i]; t=(dist-lengths[i-1])/(lengths[i]-lengths[i-1] or 1)
            cut.append((int(a[0]+(b[0]-a[0])*t),int(a[1]+(b[1]-a[1])*t))); break
    if reveal>0.01:
        cut.insert(0,pts[0])
    mask=_line_mask(cut,W,H,width,dashed)
    frame=glow_mask(frame,mask,color,1.0)
    if arrow and len(cut)>=2:
        a,b=cut[-2],cut[-1]; ang=math.atan2(b[1]-a[1],b[0]-a[0]); L=width*5; S=width*3
        tri=np.array([b,(int(b[0]-L*math.cos(ang)+S*math.sin(ang)),int(b[1]-L*math.sin(ang)-S*math.cos(ang))),
                      (int(b[0]-L*math.cos(ang)-S*math.sin(ang)),int(b[1]-L*math.sin(ang)+S*math.cos(ang)))],np.int32)
        am=_blank_mask(W,H); cv2.fillPoly(am,[tri.reshape(-1,1,2)],255,cv2.LINE_AA)
        frame=composite_mask(frame,am,color,1.0)
    return frame


def _marker(frame, point, progress, W, H, color=RED, radius=9):
    x,y=map(int,point)
    disk=_blank_mask(W,H); ring=_blank_mask(W,H)
    r=max(1,int(radius*max(0.05,min(1.15,progress*1.15))))
    cv2.circle(disk,(x,y),r,255,-1,cv2.LINE_AA)
    cv2.circle(ring,(x,y),r+8,255,2,cv2.LINE_AA)
    frame=glow_mask(frame,ring,color,0.8)
    frame=composite_mask(frame,disk,color,1.0)
    core=_blank_mask(W,H); cv2.circle(core,(x,y),3,255,-1,cv2.LINE_AA)
    return composite_mask(frame,core,WHITE,1.0)


def _label(frame, W,H, entries):
    return composite_rgba(frame,_text_plate(W,H,entries,0.0))


def _pin_entries(ctx, project, progress, scene):
    W,H=int(ctx["W"]),int(ctx["H"])
    pins=ctx.get("pins",[])
    entries=[]
    for i,p in enumerate(pins):
        lat=p.get("latitude"); lon=p.get("longitude")
        if lat is None or lon is None:
            xy=(p.get("x",W/2),p.get("y",H/2))
        else:
            xy=project(lat,lon)
        entries.append((p,xy,i))
    return entries


def draw_editorial_scene_gpu(frame, scene, ctx, progress):
    """Render a scene into UMat. All image-space compositing/effects stay OpenCL."""
    _assert_gpu(frame)
    W=int(ctx["W"]); H=int(ctx["H"])
    global _CURRENT_SIZE
    _CURRENT_SIZE=(W,H)
    project=ctx["project"]
    frame=_base_grade(frame)
    frame=_draw_grid(frame,W,H,_stage(progress,0.0,0.18))
    pin_entries=_pin_entries(ctx,project,progress,scene)
    if scene == "ed_yemen_markers" and len(pin_entries) < 3:
        raise ValueError("ed_yemen_markers requires three grounded pins")
    labels=[]
    if scene=="ed_saudi_base":
        frame,_,_=_country(frame,"SAU",project,progress,W,H)
        x,y=project(*((24.7136,46.6753)))
        labels=[{"text":"SAUDI ARABIA","center":(x,y),"role":"country","reveal":_stage(progress,.38,.24),"subtitle":"KINGDOM OF SAUDI ARABIA","accent":CYAN}]
    elif scene=="ed_iran_glow":
        frame,_,_=_country(frame,"IRN",project,progress,W,H,glow=(RED,1.0))
        tx,ty=project(35.6892,51.3890)
        labels=[{"text":"IRAN","center":(tx,ty),"role":"country","reveal":_stage(progress,.45,.18),"subtitle":"PERSIAN GULF REGION","accent":RED_HI}]
        # Context note is evidence-neutral rather than making a current-events claim.
        labels.append({"text":"PERSIAN GULF REGION","center":(W*.5,H*.82),"role":"route","reveal":_stage(progress,.62,.22),"accent":RED})
    elif scene in ("ed_yemen_markers","ed_yemen_fill"):
        frame,_,_=_country(frame,"SAU",project,progress,W,H)
        frame,_,_=_country(frame,"YEM",project,progress,W,H,fill=(GREEN,.38))
        if scene == "ed_yemen_markers":
            for i,(pin,xy,_idx) in enumerate(pin_entries[:3]):
                e=_stage(progress,.42+i*.09,.13)
                if e>0:
                    frame=_marker(frame,xy,e,W,H,RED,10)
                    labels.append({"text":pin.get("label") or pin.get("name") or "LOCATION",
                                   "center":xy,"role":"place","reveal":e,"accent":RED_HI})
        area=project(14.6,45.55)
        labels.append({"text":"YEMEN","center":area,"role":"country","reveal":_stage(progress,.62,.17),"subtitle":"INTERNATIONAL BOUNDARY","accent":GREEN})
    elif scene in ("ed_hormuz_routes","ed_hormuz_focus"):
        for iso in ("SAU","IRN","YEM","OMN","ARE"):
            frame,_,_=_country(frame,iso,project,progress,W,H)
        if scene=="ed_hormuz_focus":
            hp=project(26.55,56.27); frame=_marker(frame,hp,_stage(progress,.32,.18),W,H,RED,18)
            labels=[{"text":"STRAIT OF HORMUZ","center":hp,"role":"route","reveal":_stage(progress,.48,.2),"accent":RED_HI}]
        else:
            frame=_route(frame,[(26.5,56.3),(24.3,58.8),(21.5,62.0),(17.5,66.0),(12,68.5),(7,72.5)],project,W,H,progress,BLUE,.27,arrow=True)
            frame=_route(frame,[(26.6,50.2),(24.8,47.8),(23.2,44.8),(22.2,41.8),(21.6,39.4)],project,W,H,progress,TEAL,.40,arrow=True)
            frame=_route(frame,[(26.5,56.3),(24.8,60.2),(20,63.2),(14,64.5),(8.5,70.5)],project,W,H,progress,PINK,.52,arrow=True,dashed=True)
            for name,lat,lon in (("STRAIT OF HORMUZ",26.55,56.27),("BAB EL-MANDEB",12.58,43.35)):
                hp=project(lat,lon); frame=_marker(frame,hp,_stage(progress,.22,.12),W,H,RED,13)
                labels.append({"text":name,"center":hp,"role":"route","reveal":_stage(progress,.65,.16),"accent":RED_HI})
    elif scene=="ed_mocha_tactical":
        frame,_,_=_country(frame,"YEM",project,progress,W,H)
        # Tactical zones and attack arrows remain explicitly schematic.
        zone=[(16.6,43.1),(16.6,45.6),(14.2,45.6),(13.4,44.4),(14.2,43.2)]
        zm=_blank_mask(W,H); cv2.fillPoly(zm,[np.array([project(lat,lon) for lat,lon in zone],np.int32).reshape(-1,1,2)],255,cv2.LINE_AA)
        frame=composite_mask(frame,zm,GREEN,.30*_stage(progress,.25,.2))
        hatch=_blank_mask(W,H)
        hatchpoly=[project(lat,lon) for lat,lon in ((15.2,43.3),(15.2,44.6),(13.6,44.6),(13.3,43.6))]
        hm=_blank_mask(W,H); cv2.fillPoly(hm,[np.array(hatchpoly,np.int32).reshape(-1,1,2)],255,cv2.LINE_AA)
        for x in range(-H,W,18):cv2.line(hatch,(x,0),(x+H,H),255,2,cv2.LINE_AA)
        hatch=cv2.bitwise_and(hatch,hm)
        frame=composite_mask(frame,hatch,RED,.42*_stage(progress,.36,.22))
        frame=_route(frame,[(15.8,44.8),(14.8,44.2),(14,43.7),(13.5,43.35)],project,W,H,progress,RED_HI,.48,arrow=True,width=13)
        mx,my=project(13.3167,43.25); frame=_marker(frame,(mx,my),_stage(progress,.6,.15),W,H,RED,12)
        labels=[{"text":"MOCHA","center":(mx,my),"role":"place","reveal":_stage(progress,.66,.15),"accent":RED_HI},
                {"text":"SCHEMATIC TACTICAL ZONE","center":project(15.3,45.3),"role":"route","reveal":_stage(progress,.74,.16),"accent":RED}]
    else:
        raise ValueError(f"unsupported GPU editorial scene: {scene}")
    if labels:
        frame=composite_rgba(frame,_text_plate(W,H,labels,progress))
    frame=_draw_vignette(frame,W,H)
    _GPU_OPS["opencl"] += 1
    return frame


def _point_in_ring(point, ring):
    """Ray cast in source coordinates; used for geographic validation/tests."""
    x,y=point; inside=False
    pts=ring if ring[0]==ring[-1] else ring+[ring[0]]
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1+1e-30)+x1:
            inside=not inside
    return inside
