#!/usr/bin/env python3
"""Fifteen minimal chapter-card motion studies, five per family.

Apple-like treatment: #F5F5F7 paper, #1D1D1F ink, one #0071E3 accent,
Playfair Display static, short travel, out-expo settles, no glow.

TYPEWRITER  01 caret type, 02 blink-then-type, 03 word rise,
            04 character cascade, 05 character pop.
HIGHLIGHTER 06 left sweep, 07 centre bloom, 08 word stagger,
            09 underline draw, 10 layered sweep.
BRUSH       11 three bars, 12 single stroke, 13 centre stroke,
            14 double pass, 15 dry segments.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
JOB = ROOT / "out" / "chapter_motion_demos_v2"
OUT = JOB / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
PAPER = [0.961, 0.961, 0.969, 1.0]  # #F5F5F7
INK = "#1D1D1F"
BLUE = "#0071E3"
GRAY = "#86868B"
MARGIN, TITLE_Y = 160, 500


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def measure(text: str, font: str, size: int) -> float:
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    return float(face.getlength(text))


def fit_size(text: str, font: str, requested: int, max_width: float):
    size = requested
    while size > 48 and measure(text, font, size) > max_width:
        size -= 2
    return size, measure(text, font, size)


def text_layer(lid, text, cx, y, box_w, font, size, fill,
               start=0, tracks=None, tracking=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [int(box_w), int(size * 1.9)],
        "position": [cx, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
        "style": {
            "font": f"assets/fonts/{font}",
            "font_size": size,
            "min_font_size": size,
            "max_font_size": size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if tracking is not None:
        layer["spans"] = [{"start": 0, "end": len(text.encode()),
                           "style": {"tracking": tracking}}]
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, fill, w, h, dx, dy, start=0, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": fill,
        "size": [int(w), int(h)],
        "position": [dx, dy],
        "start_frame": start,
        "duration_frames": FRAMES - start,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def shape_bar(lid, cx, cy, width, height, color, tracks, rotation=0.0):
    return {
        "id": lid,
        "type": "shape",
        "enable_3d": True,
        "shape": {"type": "rect", "fill": color},
        "size": [int(width), int(height)],
        "position": [cx - W / 2, cy - H / 2],
        "rotation": [0.0, 0.0, rotation],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "animation": {"tracks": tracks},
    }


def fade(start, end, peak=1.0, easing="out_expo"):
    return {"property": "opacity", "easing": easing,
            "keyframes": kf([(start, 0.0), (end, peak), (FRAMES - 1, peak)])}


def rise(start, end, distance=12.0, easing="out_expo"):
    return {"property": "position_y", "easing": easing,
            "keyframes": kf([(start, distance), (end, 0.0), (FRAMES - 1, 0.0)])}


def left_grow(start, end, width, alpha=1.0, easing="out_expo"):
    return [
        {"property": "scale_x", "easing": easing,
         "keyframes": kf([(start, 0.001), (end, 1.0), (FRAMES - 1, 1.0)])},
        {"property": "position_x", "easing": easing,
         "keyframes": kf([(start, -width / 2), (end, 0.0), (FRAMES - 1, 0.0)])},
        {"property": "opacity", "easing": "linear",
         "keyframes": kf([(start, 0.0), (start + 2, alpha), (FRAMES - 1, alpha)])},
    ]


def centre_grow(start, end, alpha=1.0, easing="out_expo"):
    return [
        {"property": "scale_x", "easing": easing,
         "keyframes": kf([(start, 0.001), (end, 1.0), (FRAMES - 1, 1.0)])},
        {"property": "opacity", "easing": "linear",
         "keyframes": kf([(start, 0.0), (start + 2, alpha), (FRAMES - 1, alpha)])},
    ]


def right_grow(start, end, width, alpha=1.0, easing="out_expo"):
    return [
        {"property": "scale_x", "easing": easing,
         "keyframes": kf([(start, 0.001), (end, 1.0), (FRAMES - 1, 1.0)])},
        {"property": "position_x", "easing": easing,
         "keyframes": kf([(start, width / 2), (end, 0.0), (FRAMES - 1, 0.0)])},
        {"property": "opacity", "easing": "linear",
         "keyframes": kf([(start, 0.0), (start + 2, alpha), (FRAMES - 1, alpha)])},
    ]


def label_layer(chapter: str):
    text = f"CAPITOLO {chapter}"
    tracking = 7.0
    width = measure(text, "HelveticaNeue-Medium.otf", 12) + tracking * (len(text) - 1)
    return text_layer("label", text, MARGIN + width / 2, 380, width + 40,
                      "HelveticaNeue-Medium.otf", 12, GRAY, 4,
                      [fade(4, 20, easing="out_cubic"),
                       rise(4, 22, 6.0, easing="out_cubic")],
                      tracking=tracking)


def base_layers(chapter: str):
    return [color_layer("paper", PAPER, W, H, 0, 0), label_layer(chapter)]


def full_title(text, font, size, width, tracks, box_extra=120):
    # Text is centred inside its box, so centring on the measured width
    # keeps the visible left edge exactly on MARGIN.
    return text_layer("title", text, MARGIN + width / 2, TITLE_Y,
                      width + box_extra, font, size, INK, 0, tracks)


def plan_for(slug, chapter, layers, title, font, size, width, reveal, motion):
    plan = {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"chapter_motion_v2_{slug}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{slug}.mp4", "format": "mp4", "codec": "h264"},
    }
    meta = {
        "slug": slug, "chapter": chapter, "title": title, "motion": motion,
        "display_font": font, "align": "left", "reveal": reveal,
        "accent": BLUE, "size": size, "width": round(width, 1),
    }
    return plan, meta


def char_layout(text, font, size, left):
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    x = float(left)
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            x += float(face.getlength(ch))
            continue
        adv = float(face.getlength(ch))
        out.append((i, ch, x, adv))
        x += adv
    return out


def word_layout(text, font, size, left):
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    x = float(left)
    out = []
    for word in text.split(" "):
        w = float(face.getlength(word))
        out.append((word, x, w))
        x += w + float(face.getlength(" "))
    return out


def caret_x_tracks(chars, left, type_start, step):
    # Only one key per typed glyph: with the fast 1.4-frame step, adding a
    # second key at s + 1 would collide with the next glyph's integer frame.
    keys = [(0, 0.0)]
    for k, (_i, _ch, x, _adv) in enumerate(chars):
        keys.append((round(type_start + k * step), x - left))
    last_end = round(type_start + (len(chars) - 1) * step) + 2
    keys.append((last_end, chars[-1][2] + chars[-1][3] - left))
    dedup = {frame: value for frame, value in keys}
    return sorted(dedup.items()), last_end


def caret_layer(x_keys, opacity_keys, size):
    return {
        "id": "caret",
        "type": "shape",
        "shape": {"type": "rect", "fill": rgba(BLUE)},
        "size": [3, int(size * 0.78)],
        "position": [MARGIN + 2 - W / 2, TITLE_Y - H / 2],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "animation": {"tracks": [
            {"property": "position_x", "easing": "linear",
             "keyframes": kf(x_keys)},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf(opacity_keys)},
        ]},
    }


# ── TYPEWRITER ───────────────────────────────────────────────────────────────
def build_t1(slug):
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    chars = char_layout(phrase, font, size, MARGIN)
    layers = base_layers("01")
    for k, (ch_i, ch, x, adv) in enumerate(chars):
        start = 18 + k * 2.2
        layers.append(text_layer(
            f"char_{ch_i:02d}", ch, x + adv / 2, TITLE_Y, adv + 28,
            font, size, INK, 0,
            [fade(start, start + 1.5, easing="linear")]))
    x_keys, type_end = caret_x_tracks(chars, MARGIN, 18, 2.2)
    opacity_keys = [(0, 0.0), (10, 1.0), (type_end + 2, 1.0),
                    (type_end + 10, 0.0), (FRAMES - 1, 0.0)]
    layers.append(caret_layer(x_keys, opacity_keys, size))
    return plan_for(slug, "01", layers, phrase, font, size, width,
                    "typewriter", "01 caret type")


def build_t2(slug):
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    chars = char_layout(phrase, font, size, MARGIN)
    layers = base_layers("01")
    type_start = 46
    for k, (ch_i, ch, x, adv) in enumerate(chars):
        start = type_start + k * 1.4
        layers.append(text_layer(
            f"char_{ch_i:02d}", ch, x + adv / 2, TITLE_Y, adv + 28,
            font, size, INK, 0,
            [fade(start, start + 1.0, easing="linear")]))
    x_keys, type_end = caret_x_tracks(chars, MARGIN, type_start, 1.4)
    blink = [(0, 0.0), (8, 1.0), (12, 1.0), (14, 0.0), (18, 0.0),
             (20, 1.0), (24, 1.0), (26, 0.0), (30, 0.0), (32, 1.0),
             (36, 1.0), (38, 0.0), (42, 0.0), (44, 1.0)]
    opacity_keys = blink + [(type_end + 2, 1.0), (type_end + 10, 0.0),
                            (FRAMES - 1, 0.0)]
    layers.append(caret_layer(x_keys, opacity_keys, size))
    return plan_for(slug, "01", layers, phrase, font, size, width,
                    "typewriter", "02 blink then type")


def build_t3(slug):
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    words = word_layout(phrase, font, size, MARGIN)
    layers = base_layers("01")
    for i, (word, x, w) in enumerate(words):
        start = 18 + i * 4
        layers.append(text_layer(
            f"word_{i:02d}", word, x + w / 2, TITLE_Y, w + 30,
            font, size, INK, 0,
            [fade(start, start + 12), rise(start, start + 16, 14.0)]))
    return plan_for(slug, "01", layers, phrase, font, size, width,
                    "typewriter", "03 word rise")


def build_t4(slug):
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    chars = char_layout(phrase, font, size, MARGIN)
    layers = base_layers("01")
    for k, (ch_i, ch, x, adv) in enumerate(chars):
        start = 18 + k * 0.9
        layers.append(text_layer(
            f"char_{ch_i:02d}", ch, x + adv / 2, TITLE_Y, adv + 28,
            font, size, INK, 0,
            [fade(start, start + 10), rise(start, start + 14, 12.0)]))
    return plan_for(slug, "01", layers, phrase, font, size, width,
                    "typewriter", "04 character cascade")


def build_t5(slug):
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    chars = char_layout(phrase, font, size, MARGIN)
    layers = base_layers("01")
    for k, (ch_i, ch, x, adv) in enumerate(chars):
        start = 20 + k * 1.2
        tracks = [
            {"property": "opacity", "easing": "out_expo",
             "keyframes": kf([(start, 0.0), (start + 1, 0.30),
                              (start + 4, 1.0), (FRAMES - 1, 1.0)])},
            rise(start, start + 8, 6.0),
        ]
        layers.append(text_layer(
            f"char_{ch_i:02d}", ch, x + adv / 2, TITLE_Y, adv + 28,
            font, size, INK, 0, tracks))
    return plan_for(slug, "01", layers, phrase, font, size, width,
                    "typewriter", "05 soft type")


# ── HIGHLIGHTER ──────────────────────────────────────────────────────────────
def highlighter_base():
    phrase = "Le prove tecniche cambiano la storia"
    key = "cambiano la storia"
    font = "PlayfairDisplay-Bold.ttf"
    size, width = fit_size(phrase, font, 92, 1560)
    prefix = phrase[:phrase.index(key)]
    prefix_w = measure(prefix, font, size)
    key_w = measure(key, font, size)
    return phrase, key, font, size, width, prefix_w, key_w


def build_h1(slug):
    phrase, key, font, size, width, prefix_w, key_w = highlighter_base()
    layers = base_layers("02")
    band_w = key_w + 16
    band_h = size * 0.62
    band_cx = MARGIN + prefix_w + key_w / 2
    band_cy = TITLE_Y + size * 0.16
    layers.append(color_layer("band", rgba(BLUE, 0.22), band_w, band_h,
                              band_cx - W / 2, band_cy - H / 2, 0,
                              left_grow(30, 58, band_w, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "02", layers, phrase, font, size, width,
                    "highlighter", "06 left sweep")


def build_h2(slug):
    phrase, key, font, size, width, prefix_w, key_w = highlighter_base()
    layers = base_layers("02")
    band_w = key_w + 16
    band_h = size * 0.62
    band_cx = MARGIN + prefix_w + key_w / 2
    band_cy = TITLE_Y + size * 0.16
    layers.append(color_layer("band", rgba(BLUE, 0.22), band_w, band_h,
                              band_cx - W / 2, band_cy - H / 2, 0,
                              centre_grow(30, 56, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "02", layers, phrase, font, size, width,
                    "highlighter", "07 centre bloom")


def build_h3(slug):
    phrase, key, font, size, width, prefix_w, key_w = highlighter_base()
    layers = base_layers("02")
    words = word_layout(key, font, size, MARGIN + prefix_w)
    band_h = size * 0.62
    band_cy = TITLE_Y + size * 0.16
    for i, (word, x, w) in enumerate(words):
        start = 30 + i * 4
        band_w = w + 12
        layers.append(color_layer(
            f"band_{i:02d}", rgba(BLUE, 0.22), band_w, band_h,
            x + w / 2 - W / 2, band_cy - H / 2, 0,
            left_grow(start, start + 16, band_w, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "02", layers, phrase, font, size, width,
                    "highlighter", "08 word stagger")


def build_h4(slug):
    phrase, key, font, size, width, prefix_w, key_w = highlighter_base()
    layers = base_layers("02")
    line_w = key_w + 12
    line_cy = TITLE_Y + size * 0.66
    layers.append(color_layer("underline", rgba(BLUE, 0.92), line_w, 3,
                              MARGIN + prefix_w + key_w / 2 - W / 2,
                              line_cy - H / 2, 0,
                              left_grow(30, 58, line_w, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "02", layers, phrase, font, size, width,
                    "highlighter", "09 underline draw")


def build_h5(slug):
    phrase, key, font, size, width, prefix_w, key_w = highlighter_base()
    layers = base_layers("02")
    band_w = key_w + 22
    band_h = size * 0.70
    band_cx = MARGIN + prefix_w + key_w / 2
    band_cy = TITLE_Y + size * 0.14
    layers.append(color_layer("band_soft", rgba(BLUE, 0.10), band_w, band_h,
                              band_cx - W / 2, band_cy - H / 2, 0,
                              left_grow(30, 54, band_w, 1.0)))
    line_w = key_w + 12
    line_cy = TITLE_Y + size * 0.66
    layers.append(color_layer("band_line", rgba(BLUE, 0.92), line_w, 3,
                              MARGIN + prefix_w + key_w / 2 - W / 2,
                              line_cy - H / 2, 0,
                              left_grow(42, 66, line_w, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "02", layers, phrase, font, size, width,
                    "highlighter", "10 layered sweep")


# ── BRUSH ────────────────────────────────────────────────────────────────────
def brush_base():
    phrase = "La verità emerge dalle contraddizioni"
    key = "contraddizioni"
    font = "PlayfairDisplay-Bold.ttf"
    size, width = fit_size(phrase, font, 90, 1560)
    prefix_w = measure(phrase[:phrase.index(key)], font, size)
    key_w = measure(key, font, size)
    x0 = MARGIN + prefix_w - 4
    x1 = x0 + key_w + 8
    base_y = TITLE_Y + size * 0.66
    return phrase, font, size, width, x0, x1, base_y


def build_b1(slug):
    phrase, font, size, width, x0, x1, base_y = brush_base()
    layers = base_layers("03")
    w = x1 - x0
    layers.append(shape_bar("bar_main", (x0 + x1) / 2, base_y, w, 10,
                            rgba(BLUE, 0.90), left_grow(32, 62, w, 1.0),
                            rotation=-0.35))
    layers.append(shape_bar("bar_mid", (x0 + x1) / 2, base_y + 5, w - 28, 4,
                            rgba(BLUE, 0.55), left_grow(38, 68, w - 28, 1.0),
                            rotation=0.25))
    layers.append(shape_bar("bar_thin", (x0 + x1) / 2 + 4, base_y + 8, w - 54, 2,
                            rgba(BLUE, 0.35), left_grow(42, 72, w - 54, 1.0),
                            rotation=-0.15))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "03", layers, phrase, font, size, width,
                    "brush", "11 three bars")


def build_b2(slug):
    phrase, font, size, width, x0, x1, base_y = brush_base()
    layers = base_layers("03")
    w = x1 - x0
    layers.append(shape_bar("bar_single", (x0 + x1) / 2, base_y, w, 9,
                            rgba(BLUE, 0.90), left_grow(28, 62, w, 1.0),
                            rotation=-0.20))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "03", layers, phrase, font, size, width,
                    "brush", "12 single stroke")


def build_b3(slug):
    phrase, font, size, width, x0, x1, base_y = brush_base()
    layers = base_layers("03")
    w = x1 - x0
    layers.append(shape_bar("bar_center", (x0 + x1) / 2, base_y, w, 9,
                            rgba(BLUE, 0.90), centre_grow(30, 58, 1.0)))
    layers.append(shape_bar("bar_center_thin", (x0 + x1) / 2, base_y + 7,
                            w - 40, 2, rgba(BLUE, 0.45),
                            centre_grow(36, 64, 1.0)))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "03", layers, phrase, font, size, width,
                    "brush", "13 centre stroke")


def build_b4(slug):
    phrase, font, size, width, x0, x1, base_y = brush_base()
    layers = base_layers("03")
    w = x1 - x0
    layers.append(shape_bar("bar_first", (x0 + x1) / 2, base_y, w, 8,
                            rgba(BLUE, 0.90), left_grow(28, 56, w, 1.0),
                            rotation=-0.20))
    layers.append(shape_bar("bar_return", (x0 + x1) / 2, base_y + 8, w - 24, 2,
                            rgba(BLUE, 0.50),
                            right_grow(44, 72, w - 24, 1.0), rotation=0.15))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "03", layers, phrase, font, size, width,
                    "brush", "14 double pass")


def build_b5(slug):
    phrase, font, size, width, x0, x1, base_y = brush_base()
    layers = base_layers("03")
    n = 7
    seg = (x1 - x0) / n
    offsets = [0, -2, 1, -1, 2, 0, -1]
    heights = [7, 5, 7, 4, 6, 5, 7]
    rotations = [-0.4, 0.3, -0.2, 0.5, -0.3, 0.2, -0.1]
    for i in range(n):
        w = seg + 14
        left = x0 + i * seg - 7
        start = 26 + i * 3
        layers.append(shape_bar(
            f"seg_{i:02d}", left + w / 2, base_y + offsets[i], w, heights[i],
            rgba(BLUE, 0.82), left_grow(start, start + 16, w, 1.0),
            rotation=rotations[i]))
    layers.append(full_title(phrase, font, size, width, [fade(8, 30)]))
    return plan_for(slug, "03", layers, phrase, font, size, width,
                    "brush", "15 dry segments")


BUILDERS = [
    ("01_t1_caret_type", build_t1),
    ("02_t2_blink_then_type", build_t2),
    ("03_t3_word_rise", build_t3),
    ("04_t4_char_cascade", build_t4),
    ("05_t5_soft_type", build_t5),
    ("06_h1_sweep", build_h1),
    ("07_h2_centre_bloom", build_h2),
    ("08_h3_word_stagger", build_h3),
    ("09_h4_underline_draw", build_h4),
    ("10_h5_layered_sweep", build_h5),
    ("11_b1_three_bars", build_b1),
    ("12_b2_single_stroke", build_b2),
    ("13_b3_centre_stroke", build_b3),
    ("14_b4_double_pass", build_b4),
    ("15_b5_dry_segments", build_b5),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schema": "chronontemplate.chapter-motion-demos.v2",
        "engine": "Chronon3D (Vulkan) + ChrononTemplate motion families",
        "glow_note": "no glow: #F5F5F7 paper, #1D1D1F ink, one #0071E3 accent",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "variants": [],
    }
    for slug, build in BUILDERS:
        plan, meta = build(slug)
        path = OUT / f"{slug}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        catalog["variants"].append({
            "index": len(catalog["variants"]) + 1,
            **meta,
            "glow": {"opacity": 0.0, "blur": 0},
            "plan": f"plans/{slug}.plan.json",
            "mp4": f"{slug}.mp4",
        })
        print(f"{path.name}: {meta['motion']} | {meta['title']!r} {meta['size']}px")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print("wrote", OUT / "showcase.json")


if __name__ == "__main__":
    main()
