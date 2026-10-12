#!/usr/bin/env python3
"""map_compositions - the 15 cartographic motion-graphic systems.

Each system is a full composition (marker + connector + label + effects +
screen-space titles), selected at runtime with the ``map_animation`` payload
field. ``""`` (or missing) keeps the classic camera+label behaviour; the 15
ids below replace the standard bottom rail with their own text, so the rail
stays suppressed for them in geo_runtime.

The fundamental split from the spec: geography lives in map space (pins are
projected every frame with the live camera pose, so connectors follow their
marker during zoom/pan), readable labels live in screen space.

Honest limitations (documented, not hidden):
- Region systems (region_zoom, region_fill) have no polygon dataset in the
  renderer, so the region is a circular highlight around the pin centroid.
- photo_callout / info_card need a real photo asset: pin field ``photo`` with
  an absolute path that must exist. Without it the card renders compact
  (title + category + counter) and never a generated image.
- info_card's counter needs pin field ``value`` (a number). Without it the
  counter row is omitted, never fabricated.
- global_context's inset is a stylized schematic (graticule + viewport rect +
  title), not a second real map: no simplified-borders dataset exists.
- multi_locations / route_line need at least 2 pins; the renderer fails
  closed otherwise.

All drawing is deterministic (no random): the acceptance gate requires
byte-identical frames.
"""

from __future__ import annotations

import math
from pathlib import Path

# Canonical order: 01..15 from the spec.
MAP_COMPOSITIONS = (
    "simple_label",      # 01: pop point + trim line + dark panel, screen-space
    "region_zoom",       # 02: zoom + circular region highlight + name
    "bracket_label",     # 03: corner brackets, text straight on the map
    "photo_callout",     # 04: point + connector + photo card
    "pulse_marker",      # 05: loop concentric rings + label
    "multi_locations",   # 06: staggered multi pins, category colours
    "focus_title",       # 07: region wash + giant screen-space title
    "route_line",        # 08: dashed curve between two pins + traveller
    "spotlight",         # 09: darkened exterior, focus circle + label
    "region_fill",       # 10: outline draw + progressive fill + label
    "info_card",         # 11: stacked card with photo, counter, location
    "vertical_callout",  # 12: vertical line + black panel above
    "icon_label",        # 13: coloured circle + vector glyph + label
    "label_reveal",      # 14: colour bar opens the dark panel
    "global_context",    # 15: main map + stylized inset viewport map
)

# Systems that require at least two pins (fail closed with fewer).
MULTI_PIN_SYSTEMS = ("multi_locations", "route_line")

# Category -> accent colour (BGR for cv2, RGB for PIL handled at use site).
CATEGORY_ACCENT = {
    "wind": (250, 165, 96),     # blue  #60A5FA
    "solar": (21, 204, 250),    # yellow #FACC15
    "focus": (113, 113, 248),   # red   #F87171
    "hydro": (255, 220, 100),   # cyan-ish
}
DEFAULT_ACCENT = (255, 255, 255)

_FONT_DIR = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/Chronon3d/assets/fonts")
_FONT_CACHE: dict[tuple[str, int], object] = {}


def _font(name: str, size: int):
    """Best-effort typeface loader: condensed bold first for the modern
    editorial look (Liberation Sans Narrow), then Inter/Helvetica."""
    key = (name, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    from PIL import ImageFont
    candidates = {
        "sans": ["Inter-Bold.ttf", "HelveticaNeue-Bold.otf", "DMSans-Bold.ttf",
                 "Arial-Bold.ttf", "LiberationSans-Bold.ttf",
                 "DejaVuSans-Bold.ttf"],
        "sans_reg": ["Inter-Regular.ttf", "DMSans-Regular.ttf", "DM-Sans.ttf",
                     "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
        "cond": ["LiberationSansNarrow-Bold.ttf", "Bricolage-Grotesque.ttf",
                 "Changa-One.ttf", "Inter-Bold.ttf",
                 "HelveticaNeue-Bold.otf"],
        "serif": ["DM-Serif-Display.ttf", "BodoniModa-BoldItalic.ttf",
                  "Georgia_Bold.ttf", "FreeSerif.ttf"],
    }.get(name, ["DejaVuSans.ttf"])
    search_dirs = ["/usr/share/fonts/truetype/liberation",
                   "/usr/share/fonts/truetype/liberation2",
                   "/usr/share/fonts/truetype/msttcorefonts",
                   "/usr/share/fonts/truetype/dejavu", str(_FONT_DIR)]
    font = None
    for cand in candidates:
        for d in search_dirs:
            path = Path(d) / cand
            if path.is_file():
                try:
                    font = ImageFont.truetype(str(path), size)
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


def _stage(progress: float, start: float, dur: float) -> float:
    """Sub-progress of a stage in [start, start+dur] mapped to [0, 1]."""
    if dur <= 0:
        return 1.0 if progress >= start else 0.0
    return max(0.0, min(1.0, (progress - start) / dur))


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _back_out(t: float) -> float:
    """Overshoot pop for marker entrances (spec: 0% -> 115% -> 100%)."""
    t = max(0.0, min(1.0, t))
    c = 1.70158
    u = t - 1.0
    return 1.0 + (c + 1.0) * u * u * u + c * u * u


def geo_to_screen_px(lat: float, lon: float, anchor: tuple[float, float],
                     zoom: float, width: int, height: int) -> tuple[int, int]:
    """Project a geographic point onto the current nadir frame."""
    from dynamic_tile_pyramid import latlon_to_global_px
    zf = math.floor(zoom)
    scale = 2.0 ** (zoom - zf)
    gx, gy = latlon_to_global_px(lat, lon, int(zf))
    ax, ay = latlon_to_global_px(anchor[0], anchor[1], int(zf))
    return (int(round(width / 2 + (gx - ax) * scale)),
            int(round(height / 2 + (gy - ay) * scale)))


def _accent_bgr(pin: dict) -> tuple[int, int, int]:
    color = str(pin.get("color") or "").strip()
    if color.startswith("#") and len(color) == 7:
        try:
            r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
            return (b, g, r)
        except ValueError:
            pass
    return CATEGORY_ACCENT.get(str(pin.get("category") or "").lower(), DEFAULT_ACCENT)


def _accent_rgb(pin: dict) -> tuple[int, int, int]:
    b, g, r = _accent_bgr(pin)
    return (r, g, b)


def _panel(draw, box: tuple[int, int, int, int], radius: int,
           alpha: float, outline=None, outline_w: int = 0) -> None:
    """Dark label background #080D12 with a soft drop shadow and a hairline
    light border by default: the modern capsule look, no flat SVG box."""
    if alpha <= 0.01:
        return
    from PIL import Image, ImageDraw, ImageFilter
    x0, y0, x1, y1 = box
    e = max(0.0, min(1.0, alpha))
    if outline is None:
        outline = (255, 255, 255, int(80 * e))
        outline_w = max(outline_w, 1)
    shadow = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
    sh = ImageDraw.Draw(shadow)
    sh.rounded_rectangle([x0, y0 + 7, x1, y1 + 7], radius=radius,
                         fill=(0, 0, 0, int(140 * e)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    draw._image.alpha_composite(shadow)
    fill = (8, 13, 18, int(255 * e * 0.94))
    layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
    lay = ImageDraw.Draw(layer)
    lay.rounded_rectangle(box, radius=radius, fill=fill,
                          outline=outline, width=outline_w or 1)
    draw._image.alpha_composite(layer)


def _text(draw, xy: tuple[int, int], s: str, font, fill=(255, 255, 255),
          anchor: str = "la", shadow: bool = True,
          tracking: int = 0) -> tuple[int, int]:
    """Text with a blurred soft shadow (never the hard 2px offset) and
    optional letter-spacing for the tracked editorial look."""
    from PIL import Image, ImageDraw, ImageFilter
    ink = fill + (255,) if len(fill) == 3 else fill
    if tracking:
        cx = xy[0]
        if shadow:
            layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
            lay = ImageDraw.Draw(layer)
            tx = cx
            for ch in s:
                lay.text((tx, xy[1]), ch, font=font, fill=(0, 0, 0, 200))
                tx += lay.textbbox((0, 0), ch, font=font)[2] + tracking
            layer = layer.filter(ImageFilter.GaussianBlur(5))
            draw._image.alpha_composite(layer, (3, 5))
        tx = cx
        for ch in s:
            draw.text((tx, xy[1]), ch, font=font, fill=ink)
            tx += draw.textbbox((0, 0), ch, font=font)[2] + tracking
        return (tx - tracking - cx, draw.textbbox(xy, s, font=font)[3])
    if shadow:
        layer = Image.new("RGBA", draw._image.size, (0, 0, 0, 0))
        lay = ImageDraw.Draw(layer)
        lay.text(xy, s, font=font, fill=(0, 0, 0, 200), anchor=anchor)
        layer = layer.filter(ImageFilter.GaussianBlur(5))
        draw._image.alpha_composite(layer, (3, 5))
    draw.text(xy, s, font=font, fill=ink, anchor=anchor)
    left, top, right, bottom = draw.textbbox(xy, s, font=font, anchor=anchor)
    return (right - left, bottom - top)


def _pin_name(pin: dict) -> str:
    return str(pin.get("name") or pin.get("label") or "LOCATION").strip()[:48]


def _pin_sub(pin: dict) -> str:
    return str(pin.get("subtitle") or pin.get("category") or "").strip().upper()[:40]


# ---------------------------------------------------------------------------
# 01. Simple Location Label: pop point -> trim line -> dark panel + text
# ---------------------------------------------------------------------------
def _comp_simple_label(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    # Frame 0-10/45: point pops 0% -> 115% -> 100%.
    pop = _back_out(_stage(progress, 0.0, 0.22))
    if pop > 0.01:
        r = max(1, int(9 * pop))
        cv2.circle(frame, (cx, cy), r + 6, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), r, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), r, (140, 200, 255), 2, cv2.LINE_AA)
    # Frame 8-20/45: thin white line draws toward the label area.
    line_e = _ease(_stage(progress, 0.17, 0.28))
    px, py = min(cx + 260, W - 420), cy - 120
    if line_e > 0.01:
        ex = int(cx + (px - cx) * line_e)
        ey = int(cy + (py - cy) * line_e)
        cv2.line(frame, (cx, cy), (ex, ey), (255, 255, 255), 2, cv2.LINE_AA)
    # Frame 16-30/45: dark panel fades + slides 16px; text 3 frames later.
    panel_e = _ease(_stage(progress, 0.35, 0.32))
    if panel_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name, sub = _pin_name(pin), _pin_sub(pin)
        f_title, f_sub = _font("sans", 38), _font("sans_reg", 24)
        tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
                 draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
        bw, bh = tw + 72, (150 if sub else 104)
        slide = int(16 * (1.0 - panel_e))
        _panel(draw, (px + slide, py, px + slide + bw, py + bh), 10, panel_e)
        text_e = _ease(_stage(progress, 0.42, 0.25))
        if text_e > 0.01:
            _text(draw, (px + slide + 36, py + 22), name, f_title)
            if sub:
                _text(draw, (px + slide + 36, py + 78), sub, f_sub,
                      fill=(170, 200, 220))
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)
    # Frames 30-45: hold (camera push-in belongs to the camera system).


# ---------------------------------------------------------------------------
# 02. Region Zoom Highlight: circular region highlight + outline + name
# ---------------------------------------------------------------------------
def _region_centroid(pins) -> tuple[int, int]:
    xs = [p["x"] for p in pins]
    ys = [p["y"] for p in pins]
    return (sum(xs) // len(xs), sum(ys) // len(ys))


def _comp_region_zoom(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    cx, cy = _region_centroid(pins)
    R = 300
    # Frames 30-58/90: outline draws progressively (TrimPath approximated
    # with an arc sweep; no polygon dataset exists in the renderer).
    trim = _ease(_stage(progress, 0.33, 0.31))
    if trim > 0.01:
        overlay = frame.copy()
        cv2.ellipse(overlay, (cx, cy), (R, R), 0, -90, -90 + 360 * trim,
                    (255, 220, 150), 3, cv2.LINE_AA)
        cv2.addWeighted(overlay, trim, frame, 1.0 - trim, 0, dst=frame)
    # Frames 48-70/90: transparent blue/cyan fill + very light outer glow.
    fill_e = _ease(_stage(progress, 0.53, 0.25))
    if fill_e > 0.01:
        wash = np.zeros_like(frame)
        cv2.circle(wash, (cx, cy), R, (200, 150, 60), -1, cv2.LINE_AA)
        cv2.addWeighted(frame, 1.0, wash, 0.28 * fill_e, 0, dst=frame)
        glow = np.zeros_like(frame)
        cv2.circle(glow, (cx, cy), R + 26, (255, 220, 150), 10, cv2.LINE_AA)
        glow = cv2.GaussianBlur(glow, (0, 0), 18)
        cv2.addWeighted(frame, 1.0, glow, 0.30 * fill_e, 0, dst=frame)
    # Frames 60-80/90: region name + subtitle.
    name_e = _ease(_stage(progress, 0.66, 0.22))
    if name_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name, sub = _pin_name(pins[0]), _pin_sub(pins[0])
        f_title, f_sub = _font("sans", 42), _font("sans_reg", 24)
        tw = draw.textbbox((0, 0), name, font=f_title)[2]
        bx = min(max(cx - tw // 2 - 36, 40), W - tw - 80)
        by = min(cy + R + 24, H - 170)
        _panel(draw, (bx, by, bx + tw + 72, by + (140 if sub else 96)), 10, name_e)
        _text(draw, (bx + 36, by + 20), name, f_title)
        if sub:
            _text(draw, (bx + 36, by + 76), sub, f_sub, fill=(150, 210, 235))
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 03. Bracket Label: dot + diagonal line + corner brackets, map-native text
# ---------------------------------------------------------------------------
def _comp_bracket_label(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    dot_e = _ease(_stage(progress, 0.0, 0.22))
    if dot_e > 0.01:
        r = max(1, int(7 * dot_e))
        cv2.circle(frame, (cx, cy), r, (255, 255, 255), -1, cv2.LINE_AA)
    line_e = _ease(_stage(progress, 0.17, 0.30))
    tx, ty = min(cx + 300, W - 480), cy - 150
    if line_e > 0.01:
        cv2.line(frame, (cx, cy),
                 (int(cx + (tx - cx) * line_e), int(cy + (ty - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    # Four L corners draw around the text zone (no full panel).
    br_e = _ease(_stage(progress, 0.33, 0.33))
    name, sub = _pin_name(pin), _pin_sub(pin)
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    f_title, f_sub = _font("sans", 40), _font("sans_reg", 24)
    tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
             draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
    th = 150 if sub else 100
    m = 18
    x0, y0, x1, y1 = tx - m, ty - m, tx + tw + m, ty + th
    if br_e > 0.01:
        L = int(34 * br_e)
        col = (255, 255, 255, int(255 * br_e))
        seg = [((x0, y0 + L), (x0, y0), (x0 + L, y0)),
               ((x1 - L, y0), (x1, y0), (x1, y0 + L)),
               ((x0, y1 - L), (x0, y1), (x0 + L, y1)),
               ((x1 - L, y1), (x1, y1), (x1, y1 - L))]
        for (ax_, ay_), (bx_, by_), (cx_, cy_) in seg:
            draw.line([(ax_, ay_), (bx_, by_), (cx_, cy_)], fill=col, width=3)
    name_e = _ease(_stage(progress, 0.55, 0.28))
    if name_e > 0.01:
        lift = int(8 * (1.0 - name_e))
        _text(draw, (tx, ty - lift), name, f_title)
        if sub and name_e > 0.4:
            _text(draw, (tx, ty + 56 - lift), sub, f_sub, fill=(200, 215, 225))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 04. Photo Callout: point -> connector -> card with real photo asset
# ---------------------------------------------------------------------------
def _draw_photo_into(draw, photo_path: str, box: tuple[int, int, int, int],
                     radius: int) -> bool:
    """Paste a real photo asset clipped to a rounded mask. Never generate."""
    from PIL import Image, ImageDraw, ImageOps
    p = Path(photo_path)
    if not p.is_file():
        return False
    try:
        img = Image.open(p).convert("RGB")
    except Exception:
        return False
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return False
    fitted = ImageOps.fit(img, (w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    draw._image.paste(fitted, (x0, y0), mask)
    return True


def _comp_photo_callout(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    dot_e = _ease(_stage(progress, 0.0, 0.22))
    if dot_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(6 * dot_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    card_w, card_h = 400, 330
    bx = min(max(cx + 120, 40), W - card_w - 40)
    by = min(max(cy - card_h - 60, 60), H - card_h - 40)
    line_e = _ease(_stage(progress, 0.16, 0.19))
    if line_e > 0.01:
        cv2.line(frame, (cx, cy),
                 (int(cx + (bx - cx) * line_e), int(cy + (by + card_h // 2 - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    card_e = _ease(_stage(progress, 0.28, 0.22))
    if card_e <= 0.01:
        return
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    grow = 0.94 + 0.06 * card_e
    cw, ch = int(card_w * grow), int(card_h * grow)
    _panel(draw, (bx, by, bx + cw, by + ch), 14, card_e,
           outline=(255, 255, 255, int(255 * card_e)), outline_w=2)
    photo = str(pin.get("photo") or "")
    photo_ok = False
    if photo and card_e > 0.5:
        photo_ok = _draw_photo_into(draw, photo, (bx + 16, by + 16, bx + cw - 16, by + 150), 10)
    name, sub = _pin_name(pin), _pin_sub(pin)
    base_y = by + 166 if photo_ok else by + 28
    _text(draw, (bx + 28, base_y), name, _font("sans", 38))
    if sub:
        _text(draw, (bx + 28, base_y + 56), sub, _font("sans_reg", 24),
              fill=(170, 200, 220))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 05. Animated Pulse: looping concentric rings + label
# ---------------------------------------------------------------------------
def _comp_pulse_marker(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    accent = _accent_bgr(pin)
    cv2.circle(frame, (cx, cy), 8, (255, 255, 255), -1, cv2.LINE_AA)
    # Three rings, staggered by 12/45 of the 45-frame loop; loop phase runs
    # over the whole clip so the pulse never freezes on the hold.
    loop = (progress * 2.7) % 1.0
    for offset in (0.0, 0.27, 0.53):
        ph = (loop - offset) % 1.0
        r = int(10 + 45 * ph)
        a = max(0.0, 0.65 * (1.0 - ph))
        if a <= 0.01:
            continue
        ring = np.zeros_like(frame)
        col = tuple(int(c * a) for c in accent)
        cv2.circle(ring, (cx, cy), r, col, 2, cv2.LINE_AA)
        ring = cv2.GaussianBlur(ring, (0, 0), 3)
        cv2.addWeighted(frame, 1.0, ring, 1.0, 0, dst=frame)
    if progress > 0.42:
        label_e = _ease(_stage(progress, 0.42, 0.20))
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name = _pin_name(pin)
        f = _font("sans", 36)
        tw = draw.textbbox((0, 0), name, font=f)[2]
        bx = min(cx + 60, W - tw - 100)
        _panel(draw, (bx, cy - 44, bx + tw + 64, cy + 44), 10, label_e)
        _text(draw, (bx + 32, cy - 24), name, f)
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 06. Multi-Locations: staggered entrances, category colours, screen labels
# ---------------------------------------------------------------------------
def _comp_multi_locations(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    f_title = _font("sans", 32)
    for i, pin in enumerate(pins):
        # Stagger ~12 frames at 30fps across the clip's first two thirds.
        e = _ease(_stage(progress, 0.12 + 0.075 * i, 0.16))
        if e <= 0.01:
            continue
        cx, cy = pin["x"], pin["y"]
        if not (-50 <= cx <= W + 50 and -50 <= cy <= H + 50):
            continue
        accent = _accent_bgr(pin)
        # Point + connector (labels only move; markers never leave geography).
        cv2.circle(frame, (cx, cy), 7, accent, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 7, (255, 255, 255), 1, cv2.LINE_AA)
        name = _pin_name(pin)
        tw = draw.textbbox((0, 0), name, font=f_title)[2]
        above = (i % 2 == 0)
        side = 1 if (i % 4) < 2 else -1
        lx = int(min(max(cx + side * 90 - tw / 2, 30), W - tw - 90))
        ly = int(cy - 110 if above else cy + 70)
        ly = min(max(ly, 60), H - 120)
        cv2.line(frame, (cx, cy), (int(lx + tw / 2), ly + (44 if above else 0)),
                 (240, 240, 240), 2, cv2.LINE_AA)
        _panel(draw, (lx - 24, ly - 12, lx + tw + 24, ly + 56), 8, e,
               outline=tuple(list(_accent_rgb(pin)) + [int(255 * e)]), outline_w=2)
        _text(draw, (lx, ly), name, f_title)
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 07. Focus Zoom + Title: region wash + giant screen-space title
# ---------------------------------------------------------------------------
def _comp_focus_title(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    cx, cy = _region_centroid(pins)
    wash_e = _ease(_stage(progress, 0.22, 0.35))
    if wash_e > 0.01:
        wash = np.zeros_like(frame)
        cv2.circle(wash, (cx, cy), 260, (200, 150, 60), -1, cv2.LINE_AA)
        cv2.addWeighted(frame, 1.0, wash, 0.22 * wash_e, 0, dst=frame)
        cv2.ellipse(frame, (cx, cy), (260, 260), 0, 0, 360,
                    (220, 240, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 8, (255, 255, 255), -1, cv2.LINE_AA)
    # Giant condensed title, screen-space: rises 35px, blur approximated by
    # drawing soft before sharp while entering.
    title_e = _ease(_stage(progress, 0.39, 0.28))
    if title_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name = _pin_name(pins[0])
        sub = _pin_sub(pins[0])
        f_big = _font("cond", 150)
        rise = int(35 * (1.0 - title_e))
        base = H - 260 + rise
        _text(draw, (90, base), name, f_big)
        sub_e = _ease(_stage(progress, 0.50, 0.25))
        if sub_e > 0.01 and sub:
            _text(draw, (96, base + 168), sub, _font("sans", 34),
                  fill=(150, 210, 235))
        line_e = _ease(_stage(progress, 0.55, 0.25))
        if line_e > 0.01:
            y = base + (226 if sub else 190)
            draw.line([(90, y), (90 + int(520 * line_e), y)],
                      fill=(250, 204, 21, 255), width=6)
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 08. Route Line: dashed curve between two pins + traveller + labels
# ---------------------------------------------------------------------------
def _bezier(p0, p1, p2, t):
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def _comp_route_line(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    a, b = pins[0], pins[1]
    ax_, ay_, bx_, by_ = a["x"], a["y"], b["x"], b["y"]
    mx, my = (ax_ + bx_) / 2, (ay_ + by_) / 2
    dx, dy = bx_ - ax_, by_ - ay_
    dist = math.hypot(dx, dy) or 1.0
    # Editorial curve only: a perpendicular-lifted quadratic, never presented
    # as an exact road or geographic path.
    ctrl = (mx - dy / dist * 0.18 * dist, my + dx / dist * 0.18 * dist)
    start_e = _ease(_stage(progress, 0.0, 0.13))
    if start_e > 0.01:
        cv2.circle(frame, (ax_, ay_), 7, (255, 255, 255), -1, cv2.LINE_AA)
    trim = _ease(_stage(progress, 0.13, 0.47))
    N = 72
    pts = [_bezier((ax_, ay_), ctrl, (bx_, by_), t / N) for t in range(N + 1)]
    head = int(N * trim)
    for i in range(max(0, head - 1)):
        if (i // 4) % 2 == 0:  # dashed stroke along the curve length
            cv2.line(frame, (int(pts[i][0]), int(pts[i][1])),
                     (int(pts[i + 1][0]), int(pts[i + 1][1])),
                     (255, 240, 180), 3, cv2.LINE_AA)
    if 0 < head <= N:
        hx, hy = int(pts[head][0]), int(pts[head][1])
        cv2.circle(frame, (hx, hy), 9, (255, 240, 180), -1, cv2.LINE_AA)
        cv2.circle(frame, (hx, hy), 9, (120, 80, 20), 2, cv2.LINE_AA)
    dest_e = _back_out(_stage(progress, 0.55, 0.19))
    if dest_e > 0.01:
        cv2.circle(frame, (bx_, by_), max(1, int(8 * dest_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    label_e = _ease(_stage(progress, 0.66, 0.22))
    if label_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        f = _font("sans", 32)
        for pin, px_, py_ in ((a, ax_, ay_), (b, bx_, by_)):
            name = _pin_name(pin)
            tw = draw.textbbox((0, 0), name, font=f)[2]
            lx = int(min(max(px_ + 24, 30), W - tw - 70))
            ly = int(min(max(py_ - 90, 50), H - 110))
            _panel(draw, (lx - 22, ly - 10, lx + tw + 22, ly + 52), 8, label_e)
            _text(draw, (lx, ly), name, f)
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 09. Spotlight Circle: darken exterior, focus circle + label
# ---------------------------------------------------------------------------
def _comp_spotlight(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    grow = _ease(_stage(progress, 0.16, 0.38))
    R = int(120 + 130 * grow)
    if grow > 0.01:
        # Slightly darken the exterior through a blurred subtractive mask;
        # the interior keeps its natural brightness.
        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.circle(mask, (cx, cy), R, 255, -1, cv2.LINE_AA)
        mask = cv2.GaussianBlur(mask, (0, 0), 28)
        dark = (mask.astype(np.float32) / 255.0 * 110.0).astype(np.uint8)
        dark3 = cv2.merge([dark, dark, dark])
        frame[:] = cv2.subtract(frame, dark3)
        cv2.ellipse(frame, (cx, cy), (R, R), 0, 0, 360,
                    (255, 255, 255), 2, cv2.LINE_AA)
    pt_e = _ease(_stage(progress, 0.39, 0.17))
    if pt_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(8 * pt_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    label_e = _ease(_stage(progress, 0.50, 0.22))
    if label_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name, sub = _pin_name(pin), _pin_sub(pin)
        f_title, f_sub = _font("sans", 38), _font("sans_reg", 24)
        tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
                 draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
        bx = int(min(max(cx - tw / 2, 40), W - tw - 110))
        by = min(cy + R // 2 + 20, H - 180)
        _panel(draw, (bx - 30, by, bx + tw + 30, by + (140 if sub else 92)), 10, label_e)
        _text(draw, (bx, by + 20), name, f_title)
        if sub:
            _text(draw, (bx, by + 76), sub, f_sub, fill=(170, 200, 220))
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 10. Region Fill: outline draw -> progressive fill -> marker + label
# ---------------------------------------------------------------------------
def _comp_region_fill(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    cx, cy = _region_centroid(pins)
    R = 250
    trim = _ease(_stage(progress, 0.20, 0.33))
    if trim > 0.01:
        overlay = frame.copy()
        cv2.ellipse(overlay, (cx, cy), (R, R), 0, -90, -90 + 360 * trim,
                    (255, 255, 255), 3, cv2.LINE_AA)
        cv2.addWeighted(overlay, trim, frame, 1.0 - trim, 0, dst=frame)
    # Progressive masked fill, dark red at 20-35% so texture stays visible.
    fill_e = _ease(_stage(progress, 0.40, 0.33))
    if fill_e > 0.01:
        mask = np.zeros((H, W), dtype=np.uint8)
        cv2.ellipse(mask, (cx, cy), (R, R), 0, -90, -90 + 360 * fill_e, 255, -1,
                    cv2.LINE_AA)
        red = np.zeros_like(frame)
        red[:] = (40, 30, 180)
        alpha = (mask.astype(np.float32) / 255.0 * 0.30 * fill_e)
        frame[:] = (frame.astype(np.float32) * (1 - alpha[..., None])
                    + red.astype(np.float32) * alpha[..., None]).astype(np.uint8)
    mark_e = _ease(_stage(progress, 0.60, 0.13))
    if mark_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(8 * mark_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    label_e = _ease(_stage(progress, 0.73, 0.27))
    if label_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name = _pin_name(pins[0])
        f = _font("sans", 38)
        tw = draw.textbbox((0, 0), name, font=f)[2]
        bx = int(min(max(cx - tw / 2, 40), W - tw - 110))
        by = min(cy + R + 20, H - 150)
        _panel(draw, (bx - 30, by, bx + tw + 30, by + 92), 10, label_e)
        _text(draw, (bx, by + 20), name, f)
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 11. Stacked Info Card: marker -> connector -> card + photo + counter
# ---------------------------------------------------------------------------
def _comp_info_card(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    mark_e = _ease(_stage(progress, 0.0, 0.15))
    if mark_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(8 * mark_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    card_w, card_h = 460, 300
    bx = min(max(cx + 110, 40), W - card_w - 40)
    by = min(max(cy - card_h // 2, 60), H - card_h - 40)
    line_e = _ease(_stage(progress, 0.12, 0.16))
    if line_e > 0.01:
        cv2.line(frame, (cx, cy),
                 (int(cx + (bx - cx) * line_e), int(cy + (by + 60 - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    card_e = _ease(_stage(progress, 0.25, 0.20))
    if card_e <= 0.01:
        return
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    rise = int(25 * (1.0 - card_e))
    _panel(draw, (bx, by + rise, bx + card_w, by + rise + card_h), 12, card_e)
    y = by + rise + 20
    photo = str(pin.get("photo") or "")
    if photo and card_e > 0.6:
        if _draw_photo_into(draw, photo, (bx + 20, y, bx + card_w - 20, y + 110), 8):
            y += 126
    if _ease(_stage(progress, 0.44, 0.18)) > 0.01:
        _text(draw, (bx + 28, y), _pin_name(pin), _font("sans", 40))
        y += 58
    sub = _pin_sub(pin)
    if sub and _ease(_stage(progress, 0.50, 0.15)) > 0.01:
        _text(draw, (bx + 28, y), sub, _font("sans_reg", 24), fill=(170, 200, 220))
        y += 40
    # Counter: counts from zero to the caller-provided value only. No value
    # in the payload -> no counter row, never a fabricated number.
    try:
        target = float(pin.get("value")) if pin.get("value") is not None else None
    except (TypeError, ValueError):
        target = None
    if target is not None and math.isfinite(target):
        count_e = _ease(_stage(progress, 0.58, 0.17))
        if count_e > 0.01:
            unit = str(pin.get("unit") or "").strip()[:12]
            val = target * count_e
            shown = f"{val:,.0f}".replace(",", ".") + (f" {unit}" if unit else "")
            _text(draw, (bx + 28, y), shown, _font("sans", 44), fill=(150, 210, 235))
            y += 56
    loc = str(pin.get("location") or "").strip().upper()[:40]
    if loc and _ease(_stage(progress, 0.70, 0.15)) > 0.01:
        draw.ellipse([bx + 28, y + 6, bx + 44, y + 22], outline=(150, 210, 235), width=2)
        draw.ellipse([bx + 33, y + 11, bx + 39, y + 17], fill=(150, 210, 235, 255))
        _text(draw, (bx + 54, y), loc, _font("sans_reg", 22), fill=(200, 215, 225))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 12. Vertical Callout: dot -> vertical line -> black panel above
# ---------------------------------------------------------------------------
def _comp_vertical_callout(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    dot_e = _ease(_stage(progress, 0.0, 0.22))
    if dot_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(7 * dot_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    line_e = _ease(_stage(progress, 0.17, 0.28))
    top = max(cy - 190, 170)
    if line_e > 0.01:
        cv2.line(frame, (cx, cy), (cx, int(cy + (top - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    panel_e = _ease(_stage(progress, 0.33, 0.29))
    if panel_e > 0.01:
        rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(rgba)
        draw._image = rgba
        name, sub = _pin_name(pin), _pin_sub(pin)
        f_title, f_sub = _font("sans", 36), _font("sans_reg", 23)
        tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
                 draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
        bw, bh = tw + 64, (132 if sub else 88)
        bx = int(min(max(cx - bw / 2, 30), W - bw - 30))
        lift = int(10 * (1.0 - panel_e))
        _panel(draw, (bx, top - bh - 12 + lift, bx + bw, top - 12 + lift), 5, panel_e)
        _text(draw, (bx + 32, top - bh + 8 + lift), name, f_title)
        if sub:
            _text(draw, (bx + 32, top - bh + 60 + lift), sub, f_sub,
                  fill=(170, 200, 220))
        frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 13. Icon Label: coloured circle + vector glyph + connector + panel
# ---------------------------------------------------------------------------
def _draw_glyph(draw, kind: str, cx: int, cy: int, r: int) -> None:
    """Minimal vector glyphs from one coherent set (white, 3px strokes)."""
    kind = (kind or "").lower()
    if kind == "wind":
        for k in range(3):
            ang = -math.pi / 2 + k * 2 * math.pi / 3
            draw.line([(cx, cy), (cx + int(r * 0.8 * math.cos(ang)),
                                  cy + int(r * 0.8 * math.sin(ang)))],
                      fill=(255, 255, 255, 255), width=4)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 255))
    elif kind == "solar":
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7],
                     outline=(255, 255, 255, 255), width=3)
        for k in range(8):
            ang = k * math.pi / 4
            draw.line([(cx + int(10 * math.cos(ang)), cy + int(10 * math.sin(ang))),
                       (cx + int(r * 0.85 * math.cos(ang)),
                        cy + int(r * 0.85 * math.sin(ang)))],
                      fill=(255, 255, 255, 255), width=3)
    elif kind in ("power", "bolt"):
        draw.polygon([(cx + 4, cy - r // 2), (cx - 8, cy + 4), (cx - 1, cy + 4),
                      (cx - 4, cy + r // 2), (cx + 8, cy - 4), (cx + 1, cy - 4)],
                     fill=(255, 255, 255, 255))
    else:  # factory / generic site marker
        draw.rectangle([cx - 10, cy - 2, cx + 10, cy + 10],
                       outline=(255, 255, 255, 255), width=3)
        draw.polygon([(cx - 10, cy - 2), (cx - 4, cy - 10), (cx + 2, cy - 2)],
                     outline=(255, 255, 255, 255))
        draw.line([(cx - 10, cy + 10), (cx + 10, cy + 10)],
                  fill=(255, 255, 255, 255), width=3)


def _comp_icon_label(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    accent = _accent_rgb(pin)
    pop = _back_out(_stage(progress, 0.0, 0.20))
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    if pop > 0.01:
        r = max(1, int(26 * pop))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=accent + (255,))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(255, 255, 255, 255), width=3)
        if pop > 0.9:
            kind = str(pin.get("category") or "").lower()
            kind = {"wind": "wind", "solar": "solar"}.get(kind, "power"
                    if kind in ("power", "plant", "energy") else "factory")
            _draw_glyph(draw, kind, cx, cy, r)
    line_e = _ease(_stage(progress, 0.30, 0.23))
    lx, ly = min(cx + 220, W - 420), cy - 60
    if line_e > 0.01:
        cv2.line(frame, (cx + 26, cy),
                 (int(cx + 26 + (lx - cx - 26) * line_e),
                  int(cy + (ly - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    label_e = _ease(_stage(progress, 0.42, 0.28))
    if label_e > 0.01:
        name, sub = _pin_name(pin), _pin_sub(pin)
        f_title, f_sub = _font("sans", 36), _font("sans_reg", 23)
        tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
                 draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
        _panel(draw, (lx, ly - 14, lx + tw + 64, ly + (118 if sub else 74)), 8,
               label_e, outline=accent + (int(255 * label_e),), outline_w=2)
        _text(draw, (lx + 32, ly + 4), name, f_title)
        if sub:
            _text(draw, (lx + 32, ly + 56), sub, f_sub, fill=(170, 200, 220))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 14. Animated Label Reveal: colour bar grows down, opens the panel right
# ---------------------------------------------------------------------------
def _comp_label_reveal(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    pin = pins[0]
    cx, cy = pin["x"], pin["y"]
    mark_e = _ease(_stage(progress, 0.0, 0.15))
    if mark_e > 0.01:
        cv2.circle(frame, (cx, cy), max(1, int(7 * mark_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
    lx, top = min(cx + 60, W - 460), max(cy - 170, 60)
    line_e = _ease(_stage(progress, 0.15, 0.27))
    if line_e > 0.01:
        cv2.line(frame, (cx, cy),
                 (int(cx + (lx - cx) * line_e), int(cy + (top + 130 - cy) * line_e)),
                 (255, 255, 255), 2, cv2.LINE_AA)
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    accent = _accent_rgb(pin) if pin.get("color") or pin.get("category") else (250, 204, 21)
    # The colour bar grows top -> bottom, then opens the panel rightward.
    bar_e = _ease(_stage(progress, 0.33, 0.22))
    bar_h = 110
    if bar_e > 0.01:
        draw.rectangle([lx, top, lx + 6, top + int(bar_h * bar_e)],
                       fill=accent + (255,))
    name, sub = _pin_name(pin), _pin_sub(pin)
    f_title, f_sub = _font("sans", 38), _font("sans_reg", 24)
    tw = max(draw.textbbox((0, 0), name, font=f_title)[2],
             draw.textbbox((0, 0), sub, font=f_sub)[2] if sub else 0)
    wipe = _ease(_stage(progress, 0.42, 0.29))
    if wipe > 0.01:
        bw = int((tw + 80) * wipe)
        _panel(draw, (lx + 6, top, lx + 6 + bw, top + bar_h), 4, wipe)
    text_e = _ease(_stage(progress, 0.55, 0.27))
    if text_e > 0.01:
        slide = int(12 * (1.0 - text_e))
        draw.rectangle([lx + 6, top, lx + 6 + int((tw + 80) * wipe), top + bar_h],
                       fill=None, outline=None)
        # Clip text to the wiped width: draw on a mask layer first.
        from PIL import Image as _I
        layer = _I.new("RGBA", rgba.size, (0, 0, 0, 0))
        lay = ImageDraw.Draw(layer)
        _text(lay, (lx + 38 + slide, top + 16), name, f_title, shadow=False)
        if sub:
            _text(lay, (lx + 38 + slide, top + 66), sub, f_sub,
                  fill=(170, 200, 220), shadow=False)
        mask = _I.new("L", rgba.size, 0)
        ImageDraw.Draw(mask).rectangle(
            [lx + 6, top, lx + 6 + int((tw + 80) * wipe), top + bar_h], fill=255)
        rgba.alpha_composite(Image.composite(layer, _I.new("RGBA", rgba.size, (0, 0, 0, 0)), mask))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 15. Global Context: main map + stylized inset viewport map
# ---------------------------------------------------------------------------
def _comp_global_context(frame, pins, progress, W, H) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    # Main-map marker for orientation.
    pin = pins[0]
    mark_e = _ease(_stage(progress, 0.0, 0.20))
    if mark_e > 0.01:
        cv2.circle(frame, (pin["x"], pin["y"]), max(1, int(8 * mark_e)),
                   (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (pin["x"], pin["y"]), max(2, int(16 * mark_e)),
                   (150, 210, 235), 2, cv2.LINE_AA)
    inset_e = _ease(_stage(progress, 0.16, 0.22))
    if inset_e <= 0.01:
        return
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    draw = ImageDraw.Draw(rgba)
    draw._image = rgba
    iw, ih = 400, 300
    ix, iy = W - iw - 48, 48
    _panel(draw, (ix, iy, ix + iw, iy + ih + 64), 12, inset_e,
           outline=(255, 255, 255, int(200 * inset_e)), outline_w=2)
    # Stylized schematic: graticule only (no simplified-borders dataset).
    for gx in range(ix + 40, ix + iw, 40):
        draw.line([(gx, iy + 16), (gx, iy + ih - 16)], fill=(90, 110, 130, 255), width=1)
    for gy in range(iy + 40, iy + ih, 40):
        draw.line([(ix + 16, gy), (ix + iw - 16, gy)], fill=(90, 110, 130, 255), width=1)
    # Viewport rectangle: the area the main camera shows (draws itself in).
    rect_e = _ease(_stage(progress, 0.28, 0.20))
    if rect_e > 0.01:
        rw, rh = int(150 * rect_e), int(110 * rect_e)
        rx, ry = ix + (iw - rw) // 2, iy + (ih - rh) // 2
        draw.rectangle([rx, ry, rx + rw, ry + rh],
                       outline=(250, 204, 21, 255), width=3)
        draw.ellipse([rx + rw // 2 - 5, ry + rh // 2 - 5,
                      rx + rw // 2 + 5, ry + rh // 2 + 5],
                     fill=(248, 113, 113, 255))
    title_e = _ease(_stage(progress, 0.39, 0.22))
    if title_e > 0.01:
        _text(draw, (ix + 20, iy + ih + 10), _pin_name(pin), _font("sans", 32))
    frame[:] = cv2.cvtColor(np.array(rgba.convert("RGB")), cv2.COLOR_RGB2BGR)


_COMPOSITION_DRAW = {
    "simple_label": _comp_simple_label,
    "region_zoom": _comp_region_zoom,
    "bracket_label": _comp_bracket_label,
    "photo_callout": _comp_photo_callout,
    "pulse_marker": _comp_pulse_marker,
    "multi_locations": _comp_multi_locations,
    "focus_title": _comp_focus_title,
    "route_line": _comp_route_line,
    "spotlight": _comp_spotlight,
    "region_fill": _comp_region_fill,
    "info_card": _comp_info_card,
    "vertical_callout": _comp_vertical_callout,
    "icon_label": _comp_icon_label,
    "label_reveal": _comp_label_reveal,
    "global_context": _comp_global_context,
}


def draw_composition(frame, composition: str, pins: list[dict],
                     progress: float, width: int, height: int) -> None:
    """Draw one of the 15 map systems in place. Raises on unknown id."""
    try:
        fn = _COMPOSITION_DRAW[composition]
    except KeyError:
        raise ValueError(f"unsupported map_animation: {composition}") from None
    if not pins:
        raise ValueError(f"map_animation {composition} requires at least one pin")
    if composition in MULTI_PIN_SYSTEMS and len(pins) < 2:
        raise ValueError(f"map_animation {composition} requires at least two pins")
    fn(frame, pins, max(0.0, min(1.0, progress)), width, height)
