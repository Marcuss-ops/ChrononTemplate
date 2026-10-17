#!/usr/bin/env python3
"""map_compositions - the 3 cartographic motion-graphic systems.

Each system is a complete map composition selected at runtime with the
``map_animation`` payload field. The three retained systems draw their own
grounded marker, glow, and text.

The fundamental split from the spec: geography lives in map space (pins are
projected every frame with the live camera pose, so connectors follow their
marker during zoom/pan), readable labels live in screen space.

Honest limitation: ``region_zoom`` uses a circular highlight around the pin
centroid because this renderer has no fine-grained region polygon dataset.

All drawing is deterministic (no random): the acceptance gate requires
byte-identical frames.
"""

from __future__ import annotations

import math
from pathlib import Path

# Canonical order: the retained systems from the map-motion catalog.
MAP_COMPOSITIONS = (
    "region_zoom",       # 02: zoom + circular region highlight + name
    "pulse_marker",      # 05: loop concentric rings + label
    "spotlight",         # 09: darkened exterior, focus circle + label
)

# Systems that require at least two pins (fail closed with fewer).
MULTI_PIN_SYSTEMS = ()

# Category -> accent colour (BGR for cv2, RGB for PIL handled at use site).
CATEGORY_ACCENT = {
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
# ---------------------------------------------------------------------------
# Region Zoom Highlight: circular region highlight + outline + name
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


# ---------------------------------------------------------------------------
# 07. Focus Zoom + Title: region wash + giant screen-space title
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 08. Route Line: dashed curve between two pins + traveller + labels
# ---------------------------------------------------------------------------
def _bezier(p0, p1, p2, t):
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])




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


# ---------------------------------------------------------------------------
# 11. Stacked Info Card: marker -> connector -> card + photo + counter
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 12. Vertical Callout: dot -> vertical line -> black panel above
# ---------------------------------------------------------------------------


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




# ---------------------------------------------------------------------------
# 14. Animated Label Reveal: colour bar grows down, opens the panel right
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Runtime dispatch for the six retained map compositions
# ---------------------------------------------------------------------------


_COMPOSITION_DRAW = {
    "region_zoom": _comp_region_zoom,
    "pulse_marker": _comp_pulse_marker,
    "spotlight": _comp_spotlight,
}


def draw_composition(frame, composition: str, pins: list[dict],
                     progress: float, width: int, height: int) -> None:
    """Draw one of the 3 retained map systems in place. Raises on unknown id."""
    try:
        fn = _COMPOSITION_DRAW[composition]
    except KeyError:
        raise ValueError(f"unsupported map_animation: {composition}") from None
    if not pins:
        raise ValueError(f"map_animation {composition} requires at least one pin")
    if composition in MULTI_PIN_SYSTEMS and len(pins) < 2:
        raise ValueError(f"map_animation {composition} requires at least two pins")
    fn(frame, pins, max(0.0, min(1.0, progress)), width, height)
