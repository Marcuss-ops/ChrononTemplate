#!/usr/bin/env python3
"""map_editorial - reusable modern primitives + six certified Middle East scenes.

The six scenes (Saudi base, Iran red glow, Yemen fill, Yemen markers,
Hormuz routes, Mocha tactical overlay) are built
from ONE set of shared components, not 8 bespoke renderers:

  GeoMapBackground (tiles, owned by geo_runtime) + vignette + grid
  country_outline  - Natural Earth borders, trim-path reveal
  region_fill      - opacity fill with feathered edge
  glow_stroke      - 3-layer stroke (core + blurred halo + wide aura), additive
  label_capsule    - uppercase, letter-tracked, soft shadow, leader line
  marker_target    - filled dot + halo + ring, pop entrance
  hotspot          - dot + translucent disc + pulsing halo + ring
  route_path       - glowing line, trim write-on, flow dashes, arrowhead
  path_repeater    - oriented instances along a path (barrels)
  legend_panel     - dark panel with swatches, auto layout
  hatch_zone       - diagonal pattern clipped to a polygon
  dashed_ellipse   - dashed focus ellipse
  soft_arrow       - filled bezier band with round head

Geography honesty:
- Country borders are REAL: vendored Natural Earth 110m simplified rings
  (assets/ne_countries.json). No polygon dataset is fetched at render time.
- Conflict/tactical zones (Mocha areas, hatch zone, arrows) are SCHEMATIC
  overlays authored as lat/lon shapes, documented as such per scene.
- Routes are EDITORIAL curves through real chokepoints (Hormuz, Bab
  el-Mandeb), never presented as exact courses.
- Markers/labels for variable points come from caller pins (grounded data).

All drawing is deterministic (no random): the acceptance gate requires
byte-identical frames.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

MAP_EDITORIAL_SCENES = (
    "location_focus",
    "location_pulse",
    "ed_saudi_base",
    "ed_iran_glow",
    "ed_yemen_fill",
    "ed_yemen_markers",
    "ed_hormuz_routes",
    "ed_mocha_tactical",
)
MULTI_PIN_SCENES = ("ed_yemen_markers",)

# ---------------------------------------------------------------------------
# small math
# ---------------------------------------------------------------------------

def _stage(progress: float, start: float, dur: float) -> float:
    if dur <= 0:
        return 1.0 if progress >= start else 0.0
    return max(0.0, min(1.0, (progress - start) / dur))


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _back_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c = 1.70158
    u = t - 1.0
    return 1.0 + (c + 1.0) * u * u * u + c * u * u


# ---------------------------------------------------------------------------
# fonts (modern condensed bold for capsules, clean sans for body)
# ---------------------------------------------------------------------------

_ASSET_FONTS = Path(
    "/home/pierone/src/go-master/projects/Pyt/VeloxEditing/Chronon3d/assets/fonts")
_FONT_CACHE: dict[tuple[str, int], object] = {}


def _font(name: str, size: int):
    key = (name, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    from PIL import ImageFont
    candidates = {
        "cond": ["LiberationSansNarrow-Bold.ttf", "Arial-Bold.ttf",
                 "HelveticaNeue-Bold.otf"],
        "sans": ["Arial-Bold.ttf", "HelveticaNeue-Bold.otf",
                 "LiberationSans-Bold.ttf", "DMSans-Bold.ttf"],
        "sans_reg": ["LiberationSans-Regular.ttf", "Arial.ttf",
                     "DMSans-Regular.ttf", "DejaVuSans.ttf"],
    }.get(name, ["DejaVuSans.ttf"])
    search = ["/usr/share/fonts/truetype/liberation",
              "/usr/share/fonts/truetype/liberation2",
              "/usr/share/fonts/truetype/msttcorefonts",
              "/usr/share/fonts/truetype/dejavu", str(_ASSET_FONTS)]
    font = None
    for cand in candidates:
        for d in search:
            p = Path(d) / cand
            if p.is_file():
                try:
                    font = ImageFont.truetype(str(p), size)
                    break
                except Exception:
                    continue
        if font is not None:
            break
    if font is None:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


# ---------------------------------------------------------------------------
# borders dataset
# ---------------------------------------------------------------------------

_BORDERS: dict | None = None


def load_borders() -> dict:
    """Vendored Natural Earth 50m country rings: iso -> {name, polygons}."""
    global _BORDERS
    if _BORDERS is None:
        with open(HERE / "assets" / "ne_countries.json", encoding="utf-8") as f:
            _BORDERS = json.load(f)
    return _BORDERS


def country_polygons_screen(iso: str, project) -> list[list[tuple[int, int]]]:
    """Project a country's rings to screen; drop rings fully off-screen."""
    polys = []
    for ring in load_borders()[iso]["polygons"]:
        pts = [project(lat, lon) for lon, lat in ring]
        polys.append([(int(x), int(y)) for x, y in pts])
    return polys


# ---------------------------------------------------------------------------
# polyline helpers
# ---------------------------------------------------------------------------

def _arc_lengths(pts) -> list[float]:
    acc, out = 0.0, [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        acc += math.hypot(x1 - x0, y1 - y0)
        out.append(acc)
    return out


def trim_polyline(pts, frac: float):
    """Arc-length partial polyline (TrimPath equivalent), closed-safe."""
    frac = max(0.0, min(1.0, frac))
    if len(pts) < 2 or frac <= 0.0:
        return []
    if frac >= 1.0:
        return list(pts)
    lens = _arc_lengths(pts)
    total = lens[-1]
    if total <= 0:
        return list(pts)
    target, out = total * frac, [pts[0]]
    for i in range(1, len(pts)):
        if lens[i] <= target:
            out.append(pts[i])
        else:
            seg = lens[i] - lens[i - 1]
            t = 0.0 if seg <= 0 else (target - lens[i - 1]) / seg
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            break
    return out


def _on_screen(pts, W: int, H: int, margin: int = 100) -> bool:
    return any(-margin <= x <= W + margin and -margin <= y <= H + margin
               for x, y in pts)


def _clip_segment(pts, W: int, H: int):
    """Clamp polyline points to the frame for safe cv2 drawing."""
    return [(min(max(int(x), -2000), W + 2000),
             min(max(int(y), -2000), H + 2000)) for x, y in pts]


# ---------------------------------------------------------------------------
# cinematic base: vignette + grid
# ---------------------------------------------------------------------------

def vignette(frame, strength: float = 0.32) -> None:
    import cv2
    import numpy as np
    if strength <= 0.01:
        return
    H, W = frame.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    d = np.sqrt(dx * dx + dy * dy) / math.sqrt(2.0)
    mask = np.clip((d - 0.55) / 0.45, 0.0, 1.0) ** 1.6 * strength
    frame[:] = (frame.astype(np.float32)
                * (1.0 - mask[..., None])).astype(np.uint8)


def grid_overlay(frame, step: int = 160, alpha: float = 0.12) -> None:
    import cv2
    if alpha <= 0.01:
        return
    H, W = frame.shape[:2]
    ov = frame.copy()
    for x in range(0, W, step):
        cv2.line(ov, (x, 0), (x, H), (255, 255, 255), 1, cv2.LINE_AA)
    for y in range(0, H, step):
        cv2.line(ov, (0, y), (W, y), (255, 255, 255), 1, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, frame, 1.0 - alpha, 0, dst=frame)


# ---------------------------------------------------------------------------
# country outline + region fill + glow stroke
# ---------------------------------------------------------------------------

def draw_country_outline(frame, polys, reveal: float, W: int, H: int,
                         color=(255, 255, 255), width: int = 3) -> None:
    """White border with trim-path reveal; closed rings stay closed."""
    import cv2
    import numpy as np
    e = _ease(reveal)
    if e <= 0.01:
        return
    ov = frame.copy()
    for ring in polys:
        if not _on_screen(ring, W, H):
            continue
        seg = _clip_segment(trim_polyline(ring, e), W, H)
        if len(seg) < 2:
            continue
        cv2.polylines(ov, [np.array(seg, np.int32)], False, color, width,
                      cv2.LINE_AA)
    cv2.addWeighted(ov, e, frame, 1.0 - e, 0, dst=frame)


def draw_region_fill(frame, polys, W: int, H: int, color_bgr, alpha: float,
                     feather: int = 18) -> None:
    """Opacity fill with feathered edge so texture stays visible."""
    import cv2
    import numpy as np
    if alpha <= 0.01:
        return
    Hh, Ww = frame.shape[:2]
    mask = np.zeros((Hh, Ww), dtype=np.uint8)
    drew = False
    for ring in polys:
        if not _on_screen(ring, W, H):
            continue
        cv2.fillPoly(mask, [np.array(_clip_segment(ring, W, H), np.int32)],
                     255)
        drew = True
    if not drew:
        return
    if feather > 0:
        k = feather * 2 + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    a = (mask.astype(np.float32) / 255.0 * max(0.0, min(1.0, alpha)))
    solid = np.zeros_like(frame)
    solid[:] = color_bgr
    frame[:] = (frame.astype(np.float32) * (1 - a[..., None])
                + solid.astype(np.float32) * a[..., None]).astype(np.uint8)


def draw_glow_polyline(frame, pts, W: int, H: int, color_bgr,
                       intensity: float, core_w: int = 3, halo_w: int = 16,
                       aura_w: int = 34) -> None:
    """3-layer vector glow: sharp core + blurred halo + wide aura, additive."""
    import cv2
    import numpy as np
    e = max(0.0, min(1.0, intensity))
    if e <= 0.01 or len(pts) < 2 or not _on_screen(pts, W, H):
        return
    seg = np.array(_clip_segment(pts, W, H), np.int32)
    aura = np.zeros_like(frame)
    cv2.polylines(aura, [seg], False, color_bgr, aura_w, cv2.LINE_AA)
    aura = cv2.GaussianBlur(aura, (0, 0), 24)
    halo = np.zeros_like(frame)
    cv2.polylines(halo, [seg], False, color_bgr, halo_w, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), 10)
    cv2.addWeighted(frame, 1.0, aura, 0.30 * e, 0, dst=frame)
    cv2.addWeighted(frame, 1.0, halo, 0.55 * e, 0, dst=frame)
    core = frame.copy()
    cv2.polylines(core, [seg], False, color_bgr, core_w, cv2.LINE_AA)
    cv2.addWeighted(core, e, frame, 1.0 - e, 0, dst=frame)


# ---------------------------------------------------------------------------
# modern label capsule: uppercase + tracking + soft shadow + leader line
# ---------------------------------------------------------------------------

def tracked_width(draw, text: str, font, tracking: int) -> int:
    w = 0
    for ch in text:
        w += draw.textbbox((0, 0), ch, font=font)[2] + tracking
    return max(0, w - tracking)


def tracked_text(draw, xy, text: str, font, fill, tracking: int,
                 shadow: bool = True) -> None:
    """Letter-spaced text with a blurred soft shadow (no cheap hard offset)."""
    from PIL import Image, ImageDraw, ImageFilter
    x, y = xy
    if shadow:
        layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
        lay = ImageDraw.Draw(layer)
        cx = x
        for ch in text:
            lay.text((cx, y), ch, font=font, fill=(0, 0, 0, 200))
            cx += lay.textbbox((0, 0), ch, font=font)[2] + tracking
        layer = layer.filter(ImageFilter.GaussianBlur(5))
        draw._image.alpha_composite(layer, (3, 5))
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=font, fill=fill)
        cx += draw.textbbox((0, 0), ch, font=font)[2] + tracking


def label_capsule(draw, cx: int, cy: int, text: str, W: int, H: int,
                  entrance: float = 1.0, font_size: int = 34,
                  tracking: int = 6, accent_bgr=None,
                  leader_from=None, align: str = "center") -> None:
    """Dark rounded capsule, white tracked caps, optional accent underline
    and leader line. Entrance: fade + 10px rise."""
    from PIL import Image, ImageDraw
    e = _ease(entrance)
    if e <= 0.01 or not text:
        return
    text = text.upper()
    font = _font("cond", font_size)
    pad_x, pad_y = 30, 16
    tw = tracked_width(draw, text, font, tracking)
    bw, bh = tw + pad_x * 2, font_size + pad_y * 2
    rise = int(10 * (1.0 - e))
    if align == "center":
        x0 = int(min(max(cx - bw / 2, 24), W - bw - 24))
    elif align == "right":
        x0 = int(min(max(cx - bw - 12, 24), W - bw - 24))
    else:
        x0 = int(min(max(cx + 12, 24), W - bw - 24))
    y0 = int(min(max(cy - bh / 2 + rise, 24), H - bh - 24))
    if leader_from is not None:
        lleader = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
        llay = ImageDraw.Draw(lleader)
        lx = x0 + bw // 2
        llay.line([leader_from, (lx, y0 + bh)],
                  fill=(235, 235, 235, int(235 * e)), width=2)
        draw._image.alpha_composite(lleader)
    fill = (8, 13, 18, int(235 * e))
    layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
    lay = ImageDraw.Draw(layer)
    lay.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=10, fill=fill,
                          outline=(255, 255, 255, int(90 * e)), width=1)
    if accent_bgr is not None:
        b, g, r = accent_bgr
        lay.rounded_rectangle([x0 + 18, y0 + bh - 9, x0 + bw - 18, y0 + bh - 4],
                              radius=2, fill=(r, g, b, int(255 * e)))
    draw._image.alpha_composite(layer)
    tracked_text(draw, (x0 + pad_x, y0 + pad_y - 2), text, font,
                 (255, 255, 255, int(255 * e)), tracking)


# ---------------------------------------------------------------------------
# markers, hotspots
# ---------------------------------------------------------------------------

def marker_target(frame, x: int, y: int, color_bgr, entrance: float,
                  ring: bool = True) -> None:
    """Filled dot + soft halo + thin outer ring, overshoot pop entrance."""
    import cv2
    import numpy as np
    pop = _back_out(entrance)
    if pop <= 0.01:
        return
    r = max(1, int(9 * pop))
    halo = np.zeros_like(frame)
    cv2.circle(halo, (x, y), r + 14, color_bgr, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), 10)
    cv2.addWeighted(frame, 1.0, halo, 0.55, 0, dst=frame)
    cv2.circle(frame, (x, y), r, color_bgr, -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y), r, (255, 255, 255), 2, cv2.LINE_AA)
    if ring:
        cv2.circle(frame, (x, y), r + 12, (255, 255, 255), 2, cv2.LINE_AA)


def hotspot(frame, x: int, y: int, color_bgr, ignition: float,
            pulse_phase: float) -> None:
    """Hotspot recipe: red core + 40% disc + soft blur + 90-115 pulse."""
    import cv2
    import numpy as np
    e = _ease(ignition)
    if e <= 0.01:
        return
    pulse = 1.0 + 0.12 * math.sin(pulse_phase * math.tau)
    R = int(46 * pulse)
    disc = np.zeros_like(frame)
    cv2.circle(disc, (x, y), R, color_bgr, -1, cv2.LINE_AA)
    cv2.addWeighted(frame, 1.0, disc, 0.40 * e, 0, dst=frame)
    halo = np.zeros_like(frame)
    cv2.circle(halo, (x, y), R + 22, color_bgr, -1, cv2.LINE_AA)
    halo = cv2.GaussianBlur(halo, (0, 0), 20)
    cv2.addWeighted(frame, 1.0, halo, 0.50 * e, 0, dst=frame)
    cv2.circle(frame, (x, y), max(1, int(10 * e)), (255, 255, 255), -1,
               cv2.LINE_AA)
    cv2.circle(frame, (x, y), max(2, int(14 * e)), color_bgr, 3, cv2.LINE_AA)
    cv2.circle(frame, (x, y), R, (255, 255, 255), 2, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# routes: glowing write-on + flow + arrowhead + barrel repeater
# ---------------------------------------------------------------------------

def route_path(frame, pts, W: int, H: int, color_bgr, trim: float,
               flow_phase: float = 0.0, width: int = 5,
               arrow: bool = True, glow: bool = True) -> None:
    """Route component: glow stroke, arc-length write-on, travelling flow
    highlight and direction arrowhead at the head."""
    import cv2
    import numpy as np
    t = _ease(trim)
    if t <= 0.01 or len(pts) < 2 or not _on_screen(pts, W, H):
        return
    drawn = trim_polyline(pts, t)
    if len(drawn) < 2:
        return
    seg = np.array(_clip_segment(drawn, W, H), np.int32)
    if glow:
        halo = np.zeros_like(frame)
        cv2.polylines(halo, [seg], False, color_bgr, width + 10,
                      cv2.LINE_AA)
        halo = cv2.GaussianBlur(halo, (0, 0), 8)
        cv2.addWeighted(frame, 1.0, halo, 0.55, 0, dst=frame)
    cv2.polylines(frame, [seg], False, color_bgr, width, cv2.LINE_AA)
    cv2.polylines(frame, [seg], False, (255, 255, 255), max(1, width - 3),
                  cv2.LINE_AA)
    # flow: one bright dash travelling the drawn length
    if t > 0.05:
        lens = _arc_lengths(drawn)
        total = lens[-1] or 1.0
        head_d = ((flow_phase % 1.0) * total)
        for k, dd in enumerate(lens):
            if abs(dd - head_d) < total * 0.03:
                x, y = drawn[k]
                cv2.circle(frame, (int(x), int(y)), width + 3,
                           (255, 255, 255), -1, cv2.LINE_AA)
                break
    if arrow and t > 0.02:
        (x1, y1), (x0, y0) = drawn[-1], drawn[-2]
        ang = math.atan2(y1 - y0, x1 - x0)
        L, Sw = width * 4.2, width * 2.6
        tip = (x1, y1)
        b1 = (x1 - L * math.cos(ang) + Sw * math.sin(ang),
              y1 - L * math.sin(ang) - Sw * math.cos(ang))
        b2 = (x1 - L * math.cos(ang) - Sw * math.sin(ang),
              y1 - L * math.sin(ang) + Sw * math.cos(ang))
        cv2.fillPoly(frame, [np.array(
            [(int(tip[0]), int(tip[1])), (int(b1[0]), int(b1[1])),
             (int(b2[0]), int(b2[1]))], np.int32)], color_bgr, cv2.LINE_AA)


def path_repeater(frame, pts, W: int, H: int, entrance: float,
                  spacing_px: int = 90, color_bgr=(250, 200, 120)) -> None:
    """Oriented barrel instances every N px along the path."""
    import cv2
    import numpy as np
    e = _ease(entrance)
    if e <= 0.01 or len(pts) < 2:
        return
    lens = _arc_lengths(pts)
    total = lens[-1]
    if total <= 0:
        return
    d = spacing_px * 0.5
    while d < total:
        i = next((k for k, L in enumerate(lens) if L >= d), len(pts) - 1)
        x, y = pts[i]
        j = min(i + 1, len(pts) - 1)
        ang = math.atan2(pts[j][1] - y, pts[j][0] - x)
        if -40 <= x <= W + 40 and -40 <= y <= H + 40:
            w, h = 15, 10
            ca, sa = math.cos(ang), math.sin(ang)
            corners = []
            for sx, sy in ((-w / 2, -h / 2), (w / 2, -h / 2),
                           (w / 2, h / 2), (-w / 2, h / 2)):
                corners.append((int(x + sx * ca - sy * sa),
                                int(y + sx * sa + sy * ca)))
            ov = frame.copy()
            cv2.fillPoly(ov, [np.array(corners, np.int32)], (20, 22, 28),
                         cv2.LINE_AA)
            cv2.polylines(ov, [np.array(corners, np.int32)], True, color_bgr,
                          2, cv2.LINE_AA)
            cv2.addWeighted(ov, e, frame, 1.0 - e, 0, dst=frame)
        d += spacing_px


# ---------------------------------------------------------------------------
# legend, hatch, dashed ellipse, soft arrow, banner
# ---------------------------------------------------------------------------

def legend_panel(draw, x: int, y: int, items, entrance: float = 1.0) -> None:
    """Dark panel, swatch + aligned text rows, vertical auto layout."""
    from PIL import Image, ImageDraw
    e = _ease(entrance)
    if e <= 0.01 or not items:
        return
    font = _font("sans_reg", 24)
    rows = []
    maxw = 0
    for swatch, label in items:
        tw = draw.textbbox((0, 0), label.upper(), font=font)[2]
        maxw = max(maxw, tw)
        rows.append((swatch, label.upper()))
    bw = maxw + 130
    bh = 28 + 40 * len(rows)
    layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
    lay = ImageDraw.Draw(layer)
    lay.rounded_rectangle([x, y, x + bw, y + bh], radius=10,
                          fill=(8, 13, 18, int(225 * e)),
                          outline=(255, 255, 255, int(80 * e)), width=1)
    draw._image.alpha_composite(layer)
    for i, (swatch, label) in enumerate(rows):
        ry = y + 30 + i * 40
        if isinstance(swatch, str) and swatch == "hatch":
            for k in range(5):
                draw.line([(x + 26 + k * 7, ry + 12), (x + 32 + k * 7, ry - 4)
                           ], fill=(248, 113, 113, int(255 * e)), width=2)
        else:
            b, g, r = swatch
            draw.rounded_rectangle([x + 26, ry - 6, x + 58, ry + 18],
                                   radius=4, fill=(r, g, b, int(255 * e)))
        draw.text((x + 74, ry - 8), label, font=font,
                  fill=(235, 235, 235, int(255 * e)))


def hatch_zone(frame, polys, W: int, H: int, color_bgr, alpha: float,
               spacing: int = 14, width: int = 3) -> None:
    """Diagonal pattern clipped inside the polygon (contested zones)."""
    import cv2
    import numpy as np
    if alpha <= 0.01:
        return
    Hh, Ww = frame.shape[:2]
    mask = np.zeros((Hh, Ww), dtype=np.uint8)
    drew = False
    for ring in polys:
        if not _on_screen(ring, W, H):
            continue
        cv2.fillPoly(mask, [np.array(_clip_segment(ring, W, H), np.int32)],
                     255)
        drew = True
    if not drew:
        return
    pat = np.zeros((Hh, Ww), dtype=np.uint8)
    for k in range(-Hh, Ww, spacing):
        cv2.line(pat, (k, 0), (k + Hh, Hh), 255, width, cv2.LINE_AA)
    pat = cv2.bitwise_and(pat, mask)
    solid = np.zeros_like(frame)
    solid[:] = color_bgr
    a = pat.astype(np.float32) / 255.0 * max(0.0, min(1.0, alpha))
    frame[:] = (frame.astype(np.float32) * (1 - a[..., None])
                + solid.astype(np.float32) * a[..., None]).astype(np.uint8)


def dashed_ellipse(frame, cx: int, cy: int, rx: int, ry: int, color_bgr,
                   entrance: float, dashes: int = 26) -> None:
    import cv2
    e = _ease(entrance)
    if e <= 0.01:
        return
    ov = frame.copy()
    for k in range(dashes):
        if k % 2 == 0:
            a0 = 360.0 * k / dashes
            a1 = 360.0 * (k + 0.8) / dashes
            cv2.ellipse(ov, (cx, cy), (rx, ry), 0, a0, a1, color_bgr, 3,
                        cv2.LINE_AA)
    cv2.addWeighted(ov, e, frame, 1.0 - e, 0, dst=frame)


def soft_arrow(frame, pts, W: int, H: int, color_bgr, alpha: float,
               width: int = 26) -> None:
    """Filled organic band with round head (tactical push arrows)."""
    import cv2
    import numpy as np
    if alpha <= 0.01 or len(pts) < 2 or not _on_screen(pts, W, H):
        return
    seg = np.array(_clip_segment(pts, W, H), np.int32)
    band = np.zeros_like(frame)
    cv2.polylines(band, [seg], False, (255, 255, 255), width, cv2.LINE_AA)
    (x1, y1), (x0, y0) = pts[-1], pts[-2]
    ang = math.atan2(y1 - y0, x1 - x0)
    L = width * 1.9
    tip = (int(x1 + L * 0.4 * math.cos(ang)),
           int(y1 + L * 0.4 * math.sin(ang)))
    b1 = (int(x1 - L * math.cos(ang) + L * 0.8 * math.sin(ang)),
          int(y1 - L * math.sin(ang) - L * 0.8 * math.cos(ang)))
    b2 = (int(x1 - L * math.cos(ang) - L * 0.8 * math.sin(ang)),
          int(y1 - L * math.sin(ang) + L * 0.8 * math.cos(ang)))
    cv2.fillPoly(band, [np.array([tip, b1, b2], np.int32)], (255, 255, 255),
                 cv2.LINE_AA)
    band = cv2.GaussianBlur(band, (0, 0), 3)
    solid = np.zeros_like(frame)
    solid[:] = color_bgr
    a = (band[..., 0].astype(np.float32) / 255.0
         * max(0.0, min(1.0, alpha)))
    frame[:] = (frame.astype(np.float32) * (1 - a[..., None])
                + solid.astype(np.float32) * a[..., None]).astype(np.uint8)


def bottom_banner(draw, W: int, H: int, text: str, entrance: float,
                  color_bgr=(60, 40, 200)) -> None:
    """Red banner sliding from the left (spec scene 2)."""
    from PIL import Image, ImageDraw
    e = _ease(entrance)
    if e <= 0.01 or not text:
        return
    font = _font("cond", 36)
    tw = tracked_width(draw, text.upper(), font, 5)
    bw, bh = tw + 90, 76
    by = H - bh - 60
    bx = int(-bw + (60 + bw) * e)
    b, g, r = color_bgr
    layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
    lay = ImageDraw.Draw(layer)
    lay.rectangle([bx, by, bx + bw, by + bh], fill=(r, g, b, int(240 * e)))
    draw._image.alpha_composite(layer)
    tracked_text(draw, (bx + 45, by + 16), text.upper(), font,
                 (255, 255, 255, int(255 * e)), 5, shadow=False)


# ---------------------------------------------------------------------------
# fixed geography (real coords; schematic zones marked as such)
# ---------------------------------------------------------------------------

RIYADH = (24.7136, 46.6753)
TEHRAN = (35.6892, 51.3890)
SANAA = (15.3694, 44.1910)
HODEIDAH = (14.7979, 42.9545)
ABHA = (18.2164, 42.5053)
MOCHA = (13.3167, 43.2500)
HANISH = (13.72, 42.73)
HORMUZ = (26.55, 56.27)
BAB_EL_MANDEB = (12.58, 43.35)

# Editorial route corridors through real chokepoints (schematic courses).
ROUTE_BLUE = [(26.5, 56.3), (24.3, 58.8), (21.5, 62.0), (17.5, 66.0),
              (12.0, 68.5), (7.0, 72.5)]
ROUTE_RED_SEA = [(12.6, 43.4), (14.8, 41.8), (18.5, 39.0), (22.5, 37.0),
                 (27.7, 34.6)]
ROUTE_PIPELINE = [(26.6, 50.2), (24.8, 47.8), (23.2, 44.8), (22.2, 41.8),
                  (21.6, 39.4)]
ROUTE_PINK = [(26.5, 56.3), (24.8, 60.2), (20.0, 63.2), (14.0, 64.5),
              (8.5, 70.5)]

# SCHEMATIC tactical zones for the Mocha scene (illustrative, not surveyed).
ZONE_NORTH = [(16.6, 43.1), (16.6, 45.6), (14.2, 45.6), (13.4, 44.4),
              (14.2, 43.2)]
ZONE_HATCH = [(15.2, 43.3), (15.2, 44.6), (13.6, 44.6), (13.3, 43.6)]
ARROW_A = [(15.8, 44.8), (14.8, 44.2), (14.0, 43.7), (13.5, 43.35)]
ARROW_B = [(14.6, 45.2), (13.9, 44.4), (13.5, 43.8), (13.35, 43.3)]

RED_BGR = (60, 60, 220)
WIND_BLUE = (250, 165, 96)
PIPELINE_CYAN = (220, 200, 90)
ROUTE_PINK_C = (200, 120, 220)
SAND_GREEN = (110, 170, 100)


# ---------------------------------------------------------------------------
# scene context + dispatcher
# ---------------------------------------------------------------------------

def _pil_overlay(frame):
    import cv2
    from PIL import Image, ImageDraw
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert(
        "RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    return rgba, draw


def _flush(frame, rgba) -> None:
    import cv2
    import numpy as np
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")),
                            cv2.COLOR_RGB2BGR)


def _projected(project, geo_pts):
    return [project(lat, lon) for lat, lon in geo_pts]


def _visible_pins(pins, W: int, H: int, margin: int = 60):
    return [p for p in pins
            if -margin <= p["x"] <= W + margin
            and -margin <= p["y"] <= H + margin]


def _scene_saudi_base(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.3)))
    sau = country_polygons_screen("SAU", project)
    draw_country_outline(frame, sau, _stage(progress, 0.10, 0.45), W, H)
    rgba, draw = _pil_overlay(frame)
    rx, ry = project(*RIYADH)
    label_capsule(draw, rx, ry - 40, "SAUDI ARABIA", W, H,
                  _stage(progress, 0.45, 0.35), font_size=38)
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_iran_glow(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.3)))
    irn = country_polygons_screen("IRN", project)
    draw_country_outline(frame, irn, _stage(progress, 0.08, 0.40), W, H)
    # coastal/border red glow ramps up in 8-12 frames worth of progress
    for ring in irn:
        if _on_screen(ring, W, H):
            draw_glow_polyline(frame, trim_polyline(
                ring, _ease(_stage(progress, 0.15, 0.40))), W, H,
                RED_BGR, _stage(progress, 0.35, 0.25))
    rgba, draw = _pil_overlay(frame)
    tx, ty = project(*TEHRAN)
    label_capsule(draw, tx, ty - 40, "IRAN", W, H,
                  _stage(progress, 0.55, 0.25), font_size=38)
    bottom_banner(draw, W, H, "US NAVAL BLOCKADE OF IRAN",
                  _stage(progress, 0.65, 0.25))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_yemen_markers(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    pins = _visible_pins(ctx["pins"], W, H)
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.25)))
    sau = country_polygons_screen("SAU", project)
    yem = country_polygons_screen("YEM", project)
    draw_country_outline(frame, sau, _stage(progress, 0.05, 0.30), W, H,
                         width=2)
    draw_country_outline(frame, yem, _stage(progress, 0.10, 0.30), W, H)
    draw_region_fill(frame, yem, W, H, (70, 140, 70),
                     0.75 * _ease(_stage(progress, 0.30, 0.30)))
    # sequential marker pop-in from grounded pins (fallback: fixed towns)
    fixed = [("HODEIDAH", HODEIDAH), ("SANAA", SANAA),
             ("ABHA INTERNATIONAL AIRPORT", ABHA)]
    rgba, draw = _pil_overlay(frame)
    for i in range(3):
        e = _stage(progress, 0.45 + 0.10 * i, 0.15)
        if e <= 0.0:
            continue
        if i < len(pins):
            x, y, name = pins[i]["x"], pins[i]["y"], pins[i]["name"]
        else:
            (nm, g) = fixed[i]
            x, y = project(*g)
            name = nm
        _flush(frame, rgba)
        marker_target(frame, int(x), int(y), (60, 60, 220), e)
        rgba, draw = _pil_overlay(frame)
        label_capsule(draw, int(x), int(y) - 64, name, W, H, e,
                      font_size=28, accent_bgr=(60, 60, 220))
    mx, my = project(13.9, 45.8)
    label_capsule(draw, mx, my, "HOUTHI-CONTROLLED AREA", W, H,
                  _stage(progress, 0.72, 0.20), font_size=26,
                  accent_bgr=(60, 60, 220))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_oil_flows(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    pins = _visible_pins(ctx["pins"], W, H)
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.2)))
    for iso in ("SAU", "IRN", "YEM", "OMN", "ARE"):
        polys = country_polygons_screen(iso, project)
        draw_country_outline(frame, polys, _stage(progress, 0.03, 0.25), W,
                             H, width=2)
    blue = _projected(project, ROUTE_BLUE)
    pipe = _projected(project, ROUTE_PIPELINE)
    pink = _projected(project, ROUTE_PINK)
    redsea = _projected(project, ROUTE_RED_SEA)
    hx, hy = project(*HORMUZ)
    bx, by = project(*BAB_EL_MANDEB)
    hotspot(frame, int(hx), int(hy), (60, 60, 220),
             _stage(progress, 0.25, 0.15), progress * 1.5)
    route_path(frame, blue, W, H, WIND_BLUE, _stage(progress, 0.35, 0.25),
               flow_phase=progress * 2.0)
    route_path(frame, pipe, W, H, PIPELINE_CYAN,
               _stage(progress, 0.45, 0.25), flow_phase=progress * 2.0 + 0.4)
    route_path(frame, pink, W, H, ROUTE_PINK_C,
               _stage(progress, 0.55, 0.22), flow_phase=progress * 2.0 + 0.7)
    route_path(frame, redsea, W, H, WIND_BLUE,
               _stage(progress, 0.60, 0.20), flow_phase=progress * 2.0 + 0.2,
               width=4, arrow=False)
    path_repeater(frame, pipe, W, H, _stage(progress, 0.68, 0.15))
    marker_target(frame, int(bx), int(by), (60, 60, 220),
                  _stage(progress, 0.62, 0.12))
    rgba, draw = _pil_overlay(frame)
    for (g, txt) in ((RIYADH, "SAUDI ARABIA"), (TEHRAN, "IRAN"),
                     ((15.8, 47.5), "YEMEN")):
        gx, gy = project(*g)
        label_capsule(draw, gx, gy, txt, W, H,
                      _stage(progress, 0.12, 0.25), font_size=30)
    for p in pins[:4]:
        label_capsule(draw, p["x"], p["y"] - 58, p["name"], W, H,
                      _stage(progress, 0.66, 0.15), font_size=26,
                      accent_bgr=(60, 60, 220))
    label_capsule(draw, hx, hy - 70, "STRAIT OF HORMUZ", W, H,
                  _stage(progress, 0.70, 0.15), font_size=26,
                  accent_bgr=(60, 60, 220))
    legend_panel(draw, 60, H - 260, [
        (WIND_BLUE, "Crude route"), (PIPELINE_CYAN, "East-west pipeline"),
        (ROUTE_PINK_C, "Product route"), ((60, 60, 220), "Chokepoint"),
    ], _stage(progress, 0.78, 0.18))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_mocha_tactical(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    pins = _visible_pins(ctx["pins"], W, H)
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.2)))
    yem = country_polygons_screen("YEM", project)
    sau = country_polygons_screen("SAU", project)
    draw_country_outline(frame, yem, _stage(progress, 0.05, 0.25), W, H)
    draw_country_outline(frame, sau, _stage(progress, 0.05, 0.25), W, H,
                         width=2)
    zn = [_projected(project, ZONE_NORTH)]
    zh = [_projected(project, ZONE_HATCH)]
    draw_region_fill(frame, zn, W, H, (90, 150, 90),
                     0.65 * _ease(_stage(progress, 0.25, 0.25)))
    draw_region_fill(frame, zh, W, H, (60, 60, 190),
                     0.30 * _ease(_stage(progress, 0.30, 0.25)))
    hatch_zone(frame, zh, W, H, (60, 60, 220),
               0.85 * _ease(_stage(progress, 0.38, 0.25)))
    ex, ey = project(*HANISH)
    dashed_ellipse(frame, int(ex), int(ey), 90, 60, (255, 255, 255),
                   _stage(progress, 0.45, 0.20))
    aa = _projected(project, ARROW_A)
    ab = _projected(project, ARROW_B)
    soft_arrow(frame, trim_polyline(aa, _ease(_stage(progress, 0.50, 0.25))),
               W, H, (80, 140, 250), _stage(progress, 0.50, 0.25))
    soft_arrow(frame, trim_polyline(ab, _ease(_stage(progress, 0.56, 0.25))),
               W, H, (80, 140, 250), _stage(progress, 0.56, 0.25))
    mx, my = project(*MOCHA)
    marker_target(frame, int(mx), int(my), (60, 60, 220),
                  _stage(progress, 0.60, 0.15))
    rgba, draw = _pil_overlay(frame)
    label_capsule(draw, int(mx), int(my) - 66, "MOCHA", W, H,
                  _stage(progress, 0.66, 0.15), font_size=30,
                  accent_bgr=(60, 60, 220))
    if pins:
        p = pins[0]
        label_capsule(draw, p["x"], p["y"] - 58, p["name"], W, H,
                      _stage(progress, 0.66, 0.15), font_size=26)
    legend_panel(draw, 60, H - 220, [
        ((90, 150, 90), "Northern area"), ("hatch", "Contested zone"),
        ((80, 140, 250), "Advance"),
    ], _stage(progress, 0.76, 0.18))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_routes_clean(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.2)))
    for iso in ("SAU", "IRN", "YEM", "OMN"):
        polys = country_polygons_screen(iso, project)
        draw_country_outline(frame, polys, _stage(progress, 0.03, 0.25), W,
                             H, width=2)
    blue = _projected(project, ROUTE_BLUE)
    pipe = _projected(project, ROUTE_PIPELINE)
    pink = _projected(project, ROUTE_PINK)
    hx, hy = project(*HORMUZ)
    hotspot(frame, int(hx), int(hy), (60, 60, 220),
             _stage(progress, 0.15, 0.15), progress * 1.5)
    route_path(frame, blue, W, H, WIND_BLUE, _stage(progress, 0.30, 0.25),
               flow_phase=progress * 2.0)
    route_path(frame, pipe, W, H, PIPELINE_CYAN,
               _stage(progress, 0.42, 0.25), flow_phase=progress * 2.0 + 0.5)
    route_path(frame, pink, W, H, ROUTE_PINK_C,
               _stage(progress, 0.54, 0.22), flow_phase=progress * 2.0 + 0.8)
    rgba, draw = _pil_overlay(frame)
    for (g, txt) in ((RIYADH, "SAUDI ARABIA"), (TEHRAN, "IRAN")):
        gx, gy = project(*g)
        label_capsule(draw, gx, gy, txt, W, H,
                      _stage(progress, 0.10, 0.25), font_size=30)
    label_capsule(draw, hx, hy - 70, "STRAIT OF HORMUZ", W, H,
                  _stage(progress, 0.62, 0.15), font_size=26,
                  accent_bgr=(60, 60, 220))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_hormuz_focus(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.25)))
    for iso in ("SAU", "IRN", "OMN", "ARE"):
        polys = country_polygons_screen(iso, project)
        draw_country_outline(frame, polys, _stage(progress, 0.05, 0.30), W,
                             H, width=2)
    hx, hy = project(*HORMUZ)
    hotspot(frame, int(hx), int(hy), (60, 60, 220),
             _stage(progress, 0.30, 0.20), progress * 1.5)
    rgba, draw = _pil_overlay(frame)
    for (g, txt) in (((27.5, 45.0), "SAUDI ARABIA"),
                     ((31.0, 54.5), "IRAN")):
        gx, gy = project(*g)
        label_capsule(draw, gx, gy, txt, W, H,
                      _stage(progress, 0.15, 0.25), font_size=30)
    label_capsule(draw, hx, hy - 84, "STRAIT OF HORMUZ", W, H,
                  _stage(progress, 0.48, 0.22), font_size=30,
                  accent_bgr=(60, 60, 220),
                  leader_from=(int(hx), int(hy) - 18))
    _flush(frame, rgba)
    vignette(frame, 0.30)


def _scene_wide_minimal(frame, ctx, progress) -> None:
    W, H, project = ctx["W"], ctx["H"], ctx["project"]
    grid_overlay(frame, alpha=0.10 * _ease(_stage(progress, 0.0, 0.3)))
    for iso in ("SAU", "IRN"):
        polys = country_polygons_screen(iso, project)
        draw_country_outline(frame, polys, _stage(progress, 0.10, 0.45), W,
                             H)
    rgba, draw = _pil_overlay(frame)
    for (g, txt) in ((RIYADH, "SAUDI ARABIA"), (TEHRAN, "IRAN")):
        gx, gy = project(*g)
        label_capsule(draw, gx, gy, txt, W, H,
                      _stage(progress, 0.45, 0.35), font_size=34)
    _flush(frame, rgba)
    vignette(frame, 0.30)


_SCENE_DRAW = {
    "ed_saudi_base": _scene_saudi_base,
    "ed_iran_glow": _scene_iran_glow,
    "ed_yemen_fill": _scene_yemen_markers,
    "ed_yemen_markers": _scene_yemen_markers,
    "ed_hormuz_routes": _scene_routes_clean,
    "ed_mocha_tactical": _scene_mocha_tactical,
}

def draw_editorial_scene(frame, scene: str, ctx: dict,
                         progress: float) -> None:
    """Draw one of the six certified editorial map scenes in place."""
    try:
        fn = _SCENE_DRAW[scene]
    except KeyError:
        raise ValueError(f"unsupported map_animation: {scene}") from None
    for key in ("W", "H", "project", "pins"):
        if key not in ctx:
            raise ValueError(f"editorial scene {scene} missing ctx.{key}")
    fn(frame, ctx, max(0.0, min(1.0, progress)))
