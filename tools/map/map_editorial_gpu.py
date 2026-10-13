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
    "country_px": 54,
    "place_px": 35,
    "route_px": 30,
    "secondary_px": 21,
    "legend_px": 22,
    "capsule_pad_x": 20,
    "capsule_pad_y": 9,
    "safe_margin": 54,
    "grid_alpha": 0.045,
    "vignette_strength": 0.10,
    "map_exposure": 0.92,
    "map_contrast": 1.03,
    "saturation": 0.72,
}

WHITE = (242, 244, 238)
DARK = (10, 16, 22)
RED = (38, 48, 242)       # BGR, saturated red
RED_HI = (130, 150, 255)  # warm white/red highlight
CYAN = (240, 205, 64)     # BGR, cyan / teal for Bab el-Mandeb
BLUE = (255, 166, 74)     # BGR, marine blue for global routes
TEAL = (214, 202, 65)     # BGR, teal
PINK = (205, 50, 220)     # BGR, magenta / fuchsia for pipeline
MAGENTA = (205, 50, 220)  # BGR, pipeline magenta
GREEN = (70, 155, 60)     # BGR, rich editorial green
YELLOW = (64, 210, 255)   # BGR, warm gold

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
_COUNTRY_MASK_CACHE = {}


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
    """Exact Web-Mercator projection used by FastPlateSampler.sample_opencl."""
    from dynamic_tile_pyramid import latlon_to_global_px
    z = math.floor(zoom)
    scale = 2.0 ** (zoom - z)
    gx, gy = latlon_to_global_px(lat, lon, z)
    ax, ay = latlon_to_global_px(anchor[0], anchor[1], z)
    return (width * 0.5 + (gx - ax) * scale,
            height * 0.5 + (gy - ay) * scale)


def fit_geo_bounds(bounds, width, height, *, width_fraction=0.78,
                   height_fraction=0.76, min_zoom=5.0, max_zoom=8.0):
    """Return a camera center/zoom fitting WGS84 (south, west, north, east).

    The calculation uses the same global Web-Mercator pixel authority as the
    sampler. Binary search maximizes the zoom while keeping the padded bounds
    inside both safe-area dimensions.
    """
    from dynamic_tile_pyramid import latlon_to_global_px, global_px_to_latlon
    south, west, north, east = map(float, bounds)
    if not (-85 < south < north < 85 and -180 <= west < east <= 180):
        raise ValueError(f"invalid geographic bounds: {bounds}")
    if not (0 < width_fraction <= 1 and 0 < height_fraction <= 1):
        raise ValueError("bounds fit fractions must be in (0, 1]")
    zref = 8
    corners = [latlon_to_global_px(lat, lon, zref)
               for lat in (south, north) for lon in (west, east)]
    xs, ys = [p[0] for p in corners], [p[1] for p in corners]
    center = global_px_to_latlon((min(xs)+max(xs))/2,
                                 (min(ys)+max(ys))/2, zref)
    span_w, span_h = max(xs)-min(xs), max(ys)-min(ys)
    limit_w, limit_h = width*width_fraction, height*height_fraction
    if span_w <= 0 or span_h <= 0:
        raise ValueError("geographic bounds have no area")
    scale = min(limit_w/span_w, limit_h/span_h)
    zoom = zref + math.log2(scale)
    zoom = min(max_zoom, max(min_zoom, zoom))
    fitted_w, fitted_h = span_w*2**(zoom-zref), span_h*2**(zoom-zref)
    return (center[0], center[1], zoom,
            {"bounds": [south, west, north, east],
             "projected_span_px_at_z8": [span_w, span_h],
             "fitted_size_px": [fitted_w, fitted_h],
             "canvas_fraction": [fitted_w/width, fitted_h/height]})


def _rects_intersect(a, b, gap=0):
    return not (a[2]+gap <= b[0] or a[0] >= b[2]+gap or
                a[3]+gap <= b[1] or a[1] >= b[3]+gap)


def _place_labels(entries, W, H, draw):
    """Measure capsules first; place without overlap and fail closed on collision."""
    from PIL import Image, ImageDraw
    safe = STYLE["safe_margin"]
    occupied, layout = [], []
    for entry in entries:
        title = " ".join(str(entry["text"]).upper().split())
        subtitle = " ".join(str(entry.get("subtitle") or "").upper().split())
        role = entry.get("role", "place")
        title_size = STYLE["country_px"] if role == "country" else STYLE["route_px"] if role == "route" else STYLE["place_px"]
        sub_font = _font(STYLE["secondary_px"], False)
        sb = draw.textbbox((0,0), subtitle, font=sub_font) if subtitle else (0,0,0,0)
        pad_x, pad_y = STYLE["capsule_pad_x"], STYLE["capsule_pad_y"]
        max_text_width=W-2*STYLE["safe_margin"]-2*pad_x-16
        while True:
            title_font = _font(title_size, True)
            tb = draw.textbbox((0,0), title, font=title_font, stroke_width=1)
            tracked_w = sum(draw.textbbox((0,0),c,font=title_font)[2]+2 for c in title)-2
            title_w=max(tracked_w,tb[2]-tb[0])
            if max(title_w,sb[2]-sb[0] if subtitle else 0)<=max_text_width or title_size<=20:
                break
            title_size-=1
        sub_w=sb[2]-sb[0] if subtitle else 0
        box_w=max(title_w,sub_w)+2*pad_x+8
        gap=7 if subtitle else 0
        box_h=(tb[3]-tb[1])+(sb[3]-sb[1] if subtitle else 0)+2*pad_y+gap
        if box_w > W-2*safe or box_h > H-2*safe:
            raise ValueError(f"label too large for canvas: {title}")
        cx,cy=entry.get("center",(W/2,H/2))
        explicit=entry.get("box")
        if explicit:
            candidates=[(explicit[0],explicit[1])]
        else:
            offsets=entry.get("candidate_offsets",((0,-1),(0,1),(1,0),(-1,0)))
            distance=entry.get("candidate_distance",78)
            candidates=[]
            for dx,dy in offsets:
                if (dx,dy)==(0,-1): x,y=cx-box_w/2,cy-distance-box_h
                elif (dx,dy)==(0,1): x,y=cx-box_w/2,cy+distance
                elif (dx,dy)==(1,0): x,y=cx+distance,cy-box_h/2
                elif (dx,dy)==(-1,0): x,y=cx-distance-box_w,cy-box_h/2
                else: x,y=cx-box_w/2+dx*distance,cy-box_h/2+dy*distance
                candidates.append((x,y))
            # Deterministic safe-area grid fallback is ordered by distance to
            # the geographic point, preserving local association when possible.
            step_y=box_h+14; step_x=box_w+14
            ys=list(range(safe,max(safe+1,H-safe-box_h),step_y))
            xs=list(range(safe,max(safe+1,W-safe-box_w),step_x))
            ys.append(max(safe,H-safe-box_h)); xs.append(max(safe,W-safe-box_w))
            grid=[(x,y) for y in sorted(set(ys)) for x in sorted(set(xs))]
            candidates.extend(sorted(grid,key=lambda q:(q[0]+box_w/2-cx)**2+
                                                       (q[1]+box_h/2-cy)**2))
        chosen=None
        for x,y in candidates:
            x0=max(safe,min(W-safe-box_w,int(round(x))))
            y0=max(safe,min(H-safe-box_h,int(round(y))))
            box=(x0,y0,x0+box_w,y0+box_h)
            if not any(_rects_intersect(box,old,12) for old in occupied):
                chosen=box;break
        if chosen is None:
            raise ValueError(f"label collision cannot be resolved: {title}")
        occupied.append(chosen)
        title_row=(chosen[0]+pad_x,chosen[1]+pad_y,
                   chosen[0]+pad_x+title_w,chosen[1]+pad_y+(tb[3]-tb[1]))
        subtitle_row=None
        if subtitle:
            subtitle_row=(chosen[0]+pad_x, title_row[3]+gap,
                          chosen[0]+pad_x+sub_w, title_row[3]+gap+(sb[3]-sb[1]))
        layout.append({"entry":entry,"box":chosen,"title_font":title_font,
                       "sub_font":sub_font,"title_bbox":tb,"subtitle_bbox":sb,
                       "title_width":title_w,"rows":[title_row,subtitle_row]})
    return layout


def _text_plate(W, H, entries, progress, *, return_layout=False):
    """Measured capsules: title/subtitle rows have distinct baselines and boxes."""
    from PIL import Image, ImageDraw, ImageFilter
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    # Lay out the complete scene at every frame, including not-yet-revealed
    # entries. Reserving their boxes prevents already-visible labels jumping
    # when later callouts enter.
    layout=_place_labels(entries,W,H,draw)
    occupied=[]
    for item in layout:
        entry=item["entry"]; x0,y0,x1,y1=item["box"]
        reveal=max(0.0,min(1.0,entry.get("reveal",1.0)))
        if reveal <= 0.005:
            continue
        y_lift = int(round((1.0 - _ease(reveal)) * 8))
        y0_eff = y0 + y_lift
        y1_eff = y1 + y_lift
        title=str(entry["text"]).upper(); subtitle=str(entry.get("subtitle") or "").upper()
        font=item["title_font"]; subfont=item["sub_font"]
        pad_x,pad_y=STYLE["capsule_pad_x"],STYLE["capsule_pad_y"]
        color=entry.get("accent"); alpha=int(242*reveal)
        shadow=Image.new("RGBA",(W,H),(0,0,0,0));sd=ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x0,y0_eff+4,x1,y1_eff+4),radius=5,fill=(0,0,0,int(130*reveal)))
        plate.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
        draw=ImageDraw.Draw(plate)
        draw.rounded_rectangle((x0,y0_eff,x1,y1_eff),radius=4,fill=(*DARK,alpha),
                               outline=(221,230,232,int(100*reveal)),width=1)
        if color:
            draw.rectangle((x0,y0_eff+4,x0+4,y1_eff-4),fill=(*color[::-1],alpha))
        ink=(*WHITE,int(255*reveal)); tx=x0+pad_x+(5 if color else 0)
        ty=y0_eff+pad_y-item["title_bbox"][1]
        for ch in title:
            draw.text((tx,ty),ch,font=font,fill=ink,stroke_width=1,
                      stroke_fill=(3,8,12,int(210*reveal)))
            tx+=draw.textbbox((0,0),ch,font=font)[2]+2
        if subtitle:
            sy=ty+(item["title_bbox"][3]-item["title_bbox"][1])+7
            draw.text((x0+pad_x+(5 if color else 0),sy-item["subtitle_bbox"][1]),
                      subtitle,font=subfont,fill=(183,203,210,int(255*reveal)))
        anchor=entry.get("leader")
        if anchor:
            ax,ay=anchor
            bx=max(x0,min(x1,ax));by=max(y0_eff,min(y1_eff,ay))
            if x0<=ax<=x1 and y0_eff<=ay<=y1_eff:
                distances=((abs(ay-y0_eff), (ax,y0_eff)),(abs(ay-y1_eff),(ax,y1_eff)),
                           (abs(ax-x0),(x0,ay)),(abs(ax-x1),(x1,ay)))
                bx,by=min(distances,key=lambda q:q[0])[1]
            draw.line((ax,ay,bx,by),fill=(225,235,238,int(210*reveal)),width=2)
    all_rects=[]
    for item in layout:
        name=item["entry"]["text"]
        for row in item["rows"]:
            if row is None: continue
            if any(_rects_intersect(row,old,2) for old in all_rects):
                raise ValueError(f"text row bounding boxes overlap at {name}")
            all_rects.append(row)
    for a,b in zip(layout,layout[1:]):
        if _rects_intersect(a["box"],b["box"],4):
            raise ValueError(f"label capsule bounding boxes overlap: {a['entry']['text']} / {b['entry']['text']}")
    plate_arr=np.asarray(plate)
    boxes=[item["box"] for item in layout]
    return (plate_arr,boxes) if return_layout else plate_arr


def _simple_legend_plate(W, H, progress):
    """Compact Mocha legend that labels illustrative areas without asserting control."""
    from PIL import Image, ImageDraw
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    reveal = _stage(progress, 0.58, 0.12)
    if reveal <= 0.01:
        return np.asarray(plate)
    font = _font(15, False)
    title_font = _font(16, True)
    x, y = 54, H - 116
    width = 360
    height = 92
    alpha = int(225 * reveal)
    y_lift = int((1.0 - _ease(reveal)) * 8)
    y += y_lift
    draw.rounded_rectangle((x, y, x + width, y + height), radius=5,
                           fill=(*DARK, alpha), outline=(225, 232, 235, int(90 * reveal)), width=1)
    rows = ((GREEN, "GOVERNMENT / ALLIED AREA"), (RED, "HOUTHI CONTROL ZONE"))
    for i, (color, label) in enumerate(rows):
        yy = y + 12 + i * 26
        draw.rectangle((x + 14, yy + 2, x + 28, yy + 16), fill=(*color[::-1], int(255 * reveal)))
        draw.text((x + 36, yy), label, font=title_font, fill=(*WHITE, int(255 * reveal)))
    draw.text((x + 14, y + 68), "SCHEMATIC — NOT VERIFIED CONTROL DATA",
              font=font, fill=(185, 200, 206, int(240 * reveal)))
    return np.asarray(plate)


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


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return t * t * (3.0 - 2.0 * t)


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


def _text_plate_legacy(W, H, entries, progress):
    """Legacy layout kept for diagnostics; production uses measured _text_plate above."""
    from PIL import Image, ImageDraw, ImageFilter
    plate=Image.new("RGBA",(W,H),(0,0,0,0))
    draw=ImageDraw.Draw(plate)
    visible=[e for e in entries if _stage(progress,0,1) >= 0 and
             max(0.0,min(1.0,e.get("reveal",1.0)))>0.01]
    layout=_place_labels(visible,W,H,draw)
    for item in layout:
        entry=item["entry"]; x0,y0,x1,y1=item["box"]
        reveal=max(0.0,min(1.0,entry.get("reveal",1.0)))
        title=" ".join(str(entry["text"]).upper().split())
        subtitle=" ".join(str(entry.get("subtitle") or "").upper().split())
        color=entry.get("accent"); pad_x=STYLE["capsule_pad_x"]; pad_y=STYLE["capsule_pad_y"]
        shadow=Image.new("RGBA",(W,H),(0,0,0,0));sd=ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x0,y0+4,x1,y1+4),radius=5,fill=(0,0,0,int(115*reveal)))
        plate.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
        draw=ImageDraw.Draw(plate)
        draw.rounded_rectangle(item["box"],radius=4,fill=(*DARK,int(242*reveal)),
                               outline=(221,230,232,int(100*reveal)),width=1)
        if color: draw.rectangle((x0+1,y0+5,x0+4,y1-5),fill=(*color[::-1],int(242*reveal)))
        ink=(*WHITE,int(255*reveal)); xtext=x0+pad_x+(5 if color else 0)
        title_y=y0+pad_y-item["title_bbox"][1]
        for ch in title:
            draw.text((xtext,title_y),ch,font=item["title_font"],fill=ink,stroke_width=1,
                      stroke_fill=(3,8,12,int(210*reveal)))
            xtext+=draw.textbbox((0,0),ch,font=item["title_font"])[2]+2
        if subtitle:
            sub_y=title_y+(item["title_bbox"][3]-item["title_bbox"][1])+7
            draw.text((x0+pad_x+(5 if color else 0),sub_y-item["subtitle_bbox"][1]),
                      subtitle,font=item["sub_font"],fill=(183,203,210,int(255*reveal)))
        if entry.get("leader"):
            ax,ay=entry["leader"]; bx=max(x0,min(x1,ax)); by=max(y0,min(y1,ay))
            if x0<=ax<=x1 and y0<=ay<=y1:
                edge=((abs(ay-y0),(ax,y0)),(abs(ay-y1),(ax,y1)),
                      (abs(ax-x0),(x0,ay)),(abs(ax-x1),(x1,ay)))
                bx,by=min(edge,key=lambda v:v[0])[1]
            draw.line((ax,ay,bx,by),fill=(225,235,238,int(210*reveal)),width=2)
    plate_arr=np.asarray(plate)
    boxes=[item["box"] for item in layout]
    return (plate_arr,boxes) if return_layout else plate_arr


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


def _country(frame, iso, project, progress, W, H, *, fill=None, glow=None,
             stroke_px=2, reveal_start=0.12, reveal_duration=0.32,
             fill_start=0.34, fill_duration=0.24):
    data = load_borders().get(iso)
    if not data:
        raise ValueError(f"Natural Earth geometry missing: {iso}")
    rings = []
    fill_mask = _blank_mask(W, H)
    cache_key=None
    if fill:
        try:
            cache_key=(iso,W,H,tuple(round(v,7) for v in project.anchor),round(project.zoom,7))
        except AttributeError:
            cache_key=None
    cached=_COUNTRY_MASK_CACHE.get(cache_key) if cache_key is not None else None
    if cached is not None:
        rings,fill_mask=cached
        rings=[ring.copy() for ring in rings]
        fill_mask=fill_mask.copy()
    else:
        for ring in data["polygons"]:
            pts = np.asarray([project(lat, lon) for lon, lat in ring], np.int32)
            if pts.shape[0] < 4 or pts[:,0].max() < -20 or pts[:,0].min() > W+20 or pts[:,1].max() < -20 or pts[:,1].min() > H+20:
                continue
            rings.append(pts.reshape(-1,2))
            cv2.fillPoly(fill_mask, [pts.reshape(-1,1,2)], 255, lineType=cv2.LINE_AA)
        if cache_key is not None:
            _COUNTRY_MASK_CACHE[cache_key]=(rings,fill_mask)
    reveal = _stage(progress, reveal_start, reveal_duration)
    stroke_mask = _mask_rings(rings, W, H, reveal, stroke_px)
    if fill:
        frame = composite_mask(frame, fill_mask, fill[0], fill[1] * _stage(progress, fill_start, fill_duration))
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
           duration=0.24, width=5, arrow=True, dashed=False, glow_strength=0.55):
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
    frame=glow_mask(frame,mask,color,glow_strength)
    if arrow and len(cut)>=2:
        a,b=cut[-2],cut[-1]; ang=math.atan2(b[1]-a[1],b[0]-a[0]); L=width*5; S=width*3
        tri=np.array([b,(int(b[0]-L*math.cos(ang)+S*math.sin(ang)),int(b[1]-L*math.sin(ang)-S*math.cos(ang))),
                      (int(b[0]-L*math.cos(ang)-S*math.sin(ang)),int(b[1]-L*math.sin(ang)+S*math.cos(ang)))],np.int32)
        am=_blank_mask(W,H); cv2.fillPoly(am,[tri.reshape(-1,1,2)],255,cv2.LINE_AA)
        frame=composite_mask(frame,am,color,1.0)
    return frame


def _marker(frame, point, progress, W, H, color=RED, radius=7):
    """Refined editorial marker: dark center, crisp red ring, subtle outer pulse halo."""
    x, y = int(round(point[0])), int(round(point[1]))
    p = max(0.0, min(1.0, progress))
    pulse = 1.0 + 0.18 * math.sin(p * math.pi) if p < 1.0 else 1.0
    r = max(2, int(round(radius * pulse)))

    if p > 0.05:
        halo_r = int(round(r + 5 + (1.0 - p) * 5))
        halo_mask = _blank_mask(W, H)
        cv2.circle(halo_mask, (x, y), halo_r, 255, 1, cv2.LINE_AA)
        frame = composite_mask(frame, halo_mask, color, 0.38 * (1.0 - 0.4 * p))

    ring_mask = _blank_mask(W, H)
    cv2.circle(ring_mask, (x, y), r, 255, 2, cv2.LINE_AA)
    frame = glow_mask(frame, ring_mask, color, 0.40)

    core_mask = _blank_mask(W, H)
    cv2.circle(core_mask, (x, y), max(1, r - 2), 255, -1, cv2.LINE_AA)
    frame = composite_mask(frame, core_mask, DARK, 0.85)

    dot_mask = _blank_mask(W, H)
    cv2.circle(dot_mask, (x, y), 2, 255, -1, cv2.LINE_AA)
    return composite_mask(frame, dot_mask, WHITE, 0.95)


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
    if scene in ("location_focus", "location_pulse"):
        # A short title lead establishes the place before the map comes up.
        # The text/panel is rasterized as a mask on the host; the title blend,
        # map reveal, marker glow and all full-frame effects stay OpenCL/UMat.
        from PIL import Image, ImageDraw
        pulse_variant = scene == "location_pulse"
        map_reveal = _ease(_stage(progress, .07 if pulse_variant else .10,
                                   .15 if pulse_variant else .12))
        if map_reveal < 1.0:
            frame = cv2.addWeighted(frame, map_reveal, _solid(W,H,DARK),
                                    1.0-map_reveal, 0)
            _GPU_OPS["opencl"] += 1
        pin = pin_entries[0][0] if pin_entries else {"label":"Località"}
        point = pin_entries[0][1] if pin_entries else (W//2,H//2)
        title_plate = Image.new("RGBA", (W,H), (0,0,0,0))
        title_draw = ImageDraw.Draw(title_plate)
        title_e = 1.0 - _ease(_stage(progress, .08, .10))
        if title_e > .01:
            f_title = _font(max(44, round(102*W/1920)), True)
            title = str(pin.get("label") or "LOCALITÀ").upper()
            bbox=title_draw.textbbox((0,0),title,font=f_title)
            title_h=bbox[3]-bbox[1]
            title_w=bbox[2]-bbox[0]
            x = int(W*.085) if not pulse_variant else max(42,(W-title_w)//2)
            y = int(H*.43) if not pulse_variant else int(H*.18)
            title_draw.rounded_rectangle((x-28,y-28,min(W-50,x+title_w+56),y+title_h+64),
                                         radius=8,fill=(10,16,22,int(225*title_e)),
                                         outline=(221,230,232,int(90*title_e)),width=1)
            title_draw.text((x,y), title, font=f_title,
                            fill=(248,245,234,int(255*title_e)))
        if np.any(np.asarray(title_plate)[:,:,3]):
            frame = composite_rgba(frame, np.asarray(title_plate))
        reveal = _ease(_stage(progress,.22 if pulse_variant else .25,.13))
        if reveal > .01:
            x,y=map(int,point)
            frame=_marker(frame,(x,y),reveal,W,H,YELLOW,8)
        # The basemap already labels the town. A second floating callout on
        # the same marker duplicates the name and covers nearby roads.
        credits = {
            "esri_street": "Sources: Esri, DeLorme, HERE, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), MapmyIndia, TomTom",
            "esri_topo": "Sources: Esri, DeLorme, HERE, TomTom, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, swisstopo, MapmyIndia, GIS User Community",
            "esri_sat": "Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        }
        credit = credits.get(ctx.get("basemap", "esri_street"), "Sources: Esri and the GIS User Community")
        credit_plate=Image.new("RGBA",(W,H),(0,0,0,0))
        credit_draw=ImageDraw.Draw(credit_plate)
        credit_draw.text((18,H-25),credit,font=_font(max(10,round(13*W/1920)),False),
                         fill=(248,246,236,220),stroke_width=1,stroke_fill=(0,0,0,220))
        frame=composite_rgba(frame,np.asarray(credit_plate))
        return frame
    if scene == "ed_yemen_markers" and len(pin_entries) < 3:
        raise ValueError("ed_yemen_markers requires three grounded pins")
    labels=[]
    if scene=="ed_saudi_base":
        frame,_,_=_country(frame,"SAU",project,progress,W,H,stroke_px=2,
                            reveal_start=0.04,reveal_duration=0.30)
        x,y=project(24.7136,46.6753)
        labels=[{"text":"SAUDI ARABIA","center":(x,y),"role":"country",
                 "reveal":_stage(progress,.26,.16),"candidate_distance":56}]

    elif scene=="ed_iran_glow":
        frame,_,_=_country(frame,"IRN",project,progress,W,H,glow=(RED,.55),
                            stroke_px=2,reveal_start=.08,reveal_duration=.32)
        tx,ty=project(29.8,52.0)
        labels=[
            {"text":"IRAN","center":(tx,ty),"role":"country",
             "reveal":_stage(progress,.32,.14)},
            {"text":"US NAVAL BLOCKADE OF IRAN","center":(W*.50,H*.82),
             "role":"route","reveal":_stage(progress,.44,.14),
             "accent":RED,"candidate_distance":24}
        ]

    elif scene in ("ed_yemen_markers","ed_yemen_fill"):
        frame,_,_=_country(frame,"SAU",project,progress,W,H,
                            reveal_start=0.0,reveal_duration=.20,stroke_px=2)
        if scene == "ed_yemen_markers":
            frame,_,_=_country(frame,"YEM",project,progress,W,H,
                                fill=(GREEN,.40),fill_start=0.0,fill_duration=.18,
                                reveal_start=0.0,reveal_duration=.20,stroke_px=2)
            labels.extend([
                {"text":"SAUDI ARABIA","center":project(19.2,44.5),"role":"country",
                 "reveal":_stage(progress,.08,.10)},
                {"text":"YEMEN","center":project(14.8,46.0),"role":"country",
                 "reveal":_stage(progress,.08,.10)},
            ])
            # Strict sequential reveal: Sanaa -> Hodeidah -> Abha
            sanaa_pt = project(15.3694, 44.1910)
            e_sanaa = _stage(progress, .18, .12)
            if e_sanaa > 0:
                frame = _marker(frame, sanaa_pt, e_sanaa, W, H, RED, 7)
            labels.append({"text":"SANAA","center":sanaa_pt,"role":"place",
                           "reveal":e_sanaa,"accent":RED,"leader":sanaa_pt,
                           "candidate_distance":68,
                           "candidate_offsets":((1,0),(0,-1),(0,1),(-1,0))})

            hodeidah_pt = project(14.7979, 42.9545)
            e_hod = _stage(progress, .32, .12)
            if e_hod > 0:
                frame = _marker(frame, hodeidah_pt, e_hod, W, H, RED, 7)
            labels.append({"text":"HODEIDAH","center":hodeidah_pt,"role":"place",
                           "reveal":e_hod,"accent":RED,"leader":hodeidah_pt,
                           "candidate_distance":68,
                           "candidate_offsets":((-1,0),(0,1),(0,-1),(1,0))})

            abha_pt = project(18.2164, 42.5053)
            e_abha = _stage(progress, .46, .12)
            if e_abha > 0:
                frame = _marker(frame, abha_pt, e_abha, W, H, RED, 7)
            labels.append({"text":"ABHA INTL AIRPORT","center":abha_pt,"role":"place",
                           "reveal":e_abha,"accent":RED,"leader":abha_pt,
                           "candidate_distance":68,
                           "candidate_offsets":((1,0),(0,-1),(-1,0),(0,1))})

        else:
            frame,_,_=_country(frame,"YEM",project,progress,W,H,
                                fill=(GREEN,.40),fill_start=.08,fill_duration=.24,
                                reveal_start=.08,reveal_duration=.24,stroke_px=2)
            labels.extend([
                {"text":"SAUDI ARABIA","center":project(19.3,46.5),"role":"country",
                 "reveal":_stage(progress,.28,.12)},
                {"text":"YEMEN","center":project(14.6,45.55),"role":"country",
                 "reveal":_stage(progress,.28,.12)},
                {"text":"HOUTHI-CONTROLLED AREA","center":(W*.50,H*.84),
                 "role":"route","reveal":_stage(progress,.44,.14),"accent":GREEN},
            ])

    elif scene in ("ed_hormuz_routes","ed_hormuz_focus"):
        for iso in ("SAU","IRN","YEM","OMN","ARE"):
            frame,_,_=_country(frame,iso,project,progress,W,H,stroke_px=2)
        if scene=="ed_hormuz_focus":
            hp=project(26.55,56.27); frame=_marker(frame,hp,_stage(progress,.20,.16),W,H,RED,10)
            labels=[{"text":"STRAIT OF HORMUZ","center":hp,"role":"route","reveal":_stage(progress,.36,.16),"accent":RED}]
        else:
            # 1. Chokepoint Hormuz hotspot + label
            hp=project(26.55,56.27)
            e_hp=_stage(progress,.10,.12)
            if e_hp>0:
                frame=_marker(frame,hp,e_hp,W,H,RED,8)
            labels.append({"text":"HORMUZ","center":hp,"role":"route",
                           "reveal":e_hp,"accent":RED,
                           "leader":hp,"candidate_distance":64,
                           "candidate_offsets":((0,-1),(1,0),(-1,0),(0,1))})

            # 2. Blue maritime route: TO ASIA
            frame=_route(frame,[(26.5,56.3),(24.3,58.8),(21.5,62.0),(17.5,66.0),(12.0,68.5),(7.0,72.5)],
                         project,W,H,progress,BLUE,.22,duration=.18,width=6,arrow=True,glow_strength=.45)
            labels.append({"text":"TO ASIA","center":project(15.0,68.0),"role":"route",
                           "reveal":_stage(progress,.32,.12),"accent":BLUE,"candidate_distance":58})

            # 3. Magenta pipeline: EAST-WEST PIPELINE
            frame=_route(frame,[(26.6,50.2),(24.8,47.8),(23.2,44.8),(22.2,41.8),(21.6,39.4)],
                         project,W,H,progress,MAGENTA,.38,duration=.16,width=6,arrow=True,glow_strength=.45)
            labels.append({"text":"EAST-WEST PIPELINE","center":project(23.1,44.0),"role":"route",
                           "reveal":_stage(progress,.46,.12),"accent":MAGENTA,"candidate_distance":54})

            # 4. Red Sea corridor / Bab el-Mandeb: TO EUROPE
            frame=_route(frame,[(12.58,43.35),(14.8,41.8),(18.5,39.0),(22.5,37.0),(27.7,34.6)],
                         project,W,H,progress,CYAN,.52,duration=.16,width=5,arrow=True,dashed=True,glow_strength=.40)
            bmp=project(12.58,43.35)
            e_bm=_stage(progress,.58,.10)
            if e_bm>0:
                frame=_marker(frame,bmp,e_bm,W,H,RED,7)
            labels.extend([
                {"text":"BAB EL-MANDEB","center":bmp,"role":"route",
                 "reveal":e_bm,"accent":RED,"leader":bmp,"candidate_distance":62},
                {"text":"TO EUROPE","center":project(25.5,35.5),"role":"route",
                 "reveal":_stage(progress,.62,.10),"accent":CYAN,"candidate_distance":58},
            ])

    elif scene=="ed_mocha_tactical":
        frame,_,_=_country(frame,"YEM",project,progress,W,H,stroke_px=2,
                            reveal_start=0.0,reveal_duration=.20)
        # Tactical partitions
        green_zone=[(15.6,42.9),(15.6,44.0),(14.0,44.2),(13.7,43.3),(14.7,42.8)]
        red_zone=[(15.6,44.0),(15.4,45.2),(14.0,45.3),(13.4,44.2),(14.0,44.2)]
        for points,color,alpha,start in ((green_zone,GREEN,.38,.10),(red_zone,RED,.35,.20)):
            mask=_blank_mask(W,H)
            pts=np.array([project(lat,lon) for lat,lon in points],np.int32).reshape(-1,1,2)
            cv2.fillPoly(mask,[pts],255,cv2.LINE_AA)
            frame=composite_mask(frame,mask,color,alpha*_stage(progress,start,.14))

        # Soft contact hatch
        hatchpoly=[project(lat,lon) for lat,lon in ((15.2,43.4),(15.2,44.5),(13.6,44.5),(13.3,43.7))]
        hm=_blank_mask(W,H);cv2.fillPoly(hm,[np.array(hatchpoly,np.int32).reshape(-1,1,2)],255,cv2.LINE_AA)
        hatch=_blank_mask(W,H)
        for x in range(-H,W,32):cv2.line(hatch,(x,0),(x+H,H),255,1,cv2.LINE_AA)
        hatch=cv2.bitwise_and(hatch,hm)
        frame=composite_mask(frame,hatch,RED,.28*_stage(progress,.32,.14))

        # Smooth tactical directional arrows (entering sequentially)
        for i,route in enumerate(([(15.6,44.8),(14.7,44.2),(14.1,43.75),(13.65,43.45)],
                                  [(15.2,45.0),(14.4,44.2),(13.9,43.70),(13.55,43.50)])):
            frame=_route(frame,route,project,W,H,progress,BLUE,.44+i*.08,
                         duration=.14,width=4,arrow=True,glow_strength=.32)

        # Mocha marker + label
        mx,my=project(13.3167,43.25)
        e_mocha=_stage(progress,.58,.10)
        if e_mocha>0:
            frame=_marker(frame,(mx,my),e_mocha,W,H,RED,8)

        # Hanish Islands circle + label
        hx,hy=project(13.72,42.73)
        e_hanish=_stage(progress,.64,.10)
        hanish=_blank_mask(W,H);cv2.ellipse(hanish,(int(hx),int(hy)),(22,13),0,0,360,255,1,cv2.LINE_AA)
        frame=composite_mask(frame,hanish,WHITE,.85*e_hanish)

        labels=[
            {"text":"MOCHA","center":(mx,my),"role":"place","reveal":e_mocha,
             "accent":RED,"leader":(mx,my),"candidate_distance":64,
             "candidate_offsets":((1,0),(0,1),(1,-1))},
            {"text":"HANISH ISLANDS","center":(hx,hy),"role":"place","reveal":e_hanish,
             "leader":(hx,hy),"candidate_distance":64,
             "candidate_offsets":((-1,0),(0,-1),(-1,-1))}
        ]
    else:
        raise ValueError(f"unsupported GPU editorial scene: {scene}")
    if labels:
        frame=composite_rgba(frame,_text_plate(W,H,labels,progress))
    if scene=="ed_mocha_tactical":
        frame=composite_rgba(frame,_simple_legend_plate(W,H,progress))
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
