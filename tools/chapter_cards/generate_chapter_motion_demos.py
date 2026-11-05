#!/usr/bin/env python3
"""Three minimal chapter cards, three motion families.

1. TYPEWRITER  — Playfair Display static, glyph-by-glyph typing + caret.
2. HIGHLIGHTER — long line, ochre marker band sweeping under the key phrase.
3. BRUSH       — long line, organic brush underline revealed with a trim operator.

Paper #F2EEE6, ink #161616, terracotta #B3492F. No glow, no progress bars.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
JOB = ROOT / "out" / "chapter_motion_demos_v1"
OUT = JOB / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
PAPER = [0.949, 0.933, 0.902, 1.0]
INK = "#161616"
TERRACOTTA = "#B3492F"
BRUSH_RGBA = [0.702, 0.286, 0.184, 1.0]
OCHRE = "#E8C56B"
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


def text_layer(lid, text, x, y, box_w, font, size, fill,
               start=0, tracks=None, tracking=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [int(box_w), int(size * 1.9)],
        "position": [x, y],
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


def fade(start, end):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, 1.0), (FRAMES - 1, 1.0)])}


def label_layer(chapter: str):
    text = f"CAPITOLO {chapter}"
    tracking = 7.0
    width = measure(text, "HelveticaNeue-Medium.otf", 12) + tracking * (len(text) - 1)
    return text_layer("label", text, MARGIN + (width + 40) / 2, 380, width + 40,
                      "HelveticaNeue-Medium.otf", 12, TERRACOTTA, 4,
                      [fade(4, 20),
                       {"property": "position_y", "easing": "out_cubic",
                        "keyframes": kf([(4, 6.0), (22, 0.0), (FRAMES - 1, 0.0)])}],
                      tracking=tracking)


def base_layers(chapter: str):
    return [color_layer("paper", PAPER, W, H, 0, 0), label_layer(chapter)]


# ── 1. TYPEWRITER ────────────────────────────────────────────────────────────
def build_typewriter():
    phrase = "Il luogo e la data"
    font = "PlayfairDisplay.ttf"
    size = 132
    width = measure(phrase, font, size)
    left = MARGIN
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    layers = base_layers("01")

    starts = []
    cursor = 0.0
    for ch in phrase:
        advance = float(face.getlength(ch))
        starts.append(cursor)
        cursor += advance

    typed = 0
    for i, ch in enumerate(phrase):
        if ch == " ":
            continue
        char_w = measure(ch, font, size)
        x = left + starts[i] + char_w / 2
        start = 18 + typed * 2.4
        layers.append(text_layer(
            f"char_{i:02d}", ch, x, TITLE_Y, char_w + 28, font, size, INK, 0,
            [{"property": "opacity", "easing": "out_cubic",
              "keyframes": kf([(start, 0.0), (start + 2, 1.0), (FRAMES - 1, 1.0)])}]))
        typed += 1

    type_start, type_end = 18, 18 + (typed - 1) * 2.4
    caret_keys = []
    for f in range(16, int(type_end) + 8, 2):
        p = max(0.0, min(1.0, (f - type_start) / max(1.0, type_end - type_start)))
        k = min(typed, int(p * typed))
        idx = 0
        seen = 0
        for i, ch in enumerate(phrase):
            if ch == " ":
                continue
            if seen == k:
                idx = i
                break
            seen += 1
        else:
            idx = len(phrase) - 1
        x = left + starts[idx] + 2
        caret_keys.append((f, x - (left + 2)))
    caret_keys += [(FRAMES - 1, caret_keys[-1][1])]

    layers.append({
        "id": "caret",
        "type": "shape",
        "shape": {"type": "rect", "fill": rgba(TERRACOTTA)},
        "size": [3, int(size * 0.78)],
        # shape positions are centre-relative (0,0 = canvas centre)
        "position": [left + 2 - W / 2, TITLE_Y - H / 2],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "animation": {"tracks": [
            {"property": "position_x", "easing": "linear",
             "keyframes": kf(caret_keys)},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(0, 0.0), (14, 1.0), (int(type_end) + 4, 1.0),
                              (int(type_end) + 12, 0.0), (FRAMES - 1, 0.0)])},
        ]},
    })

    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "chapter_motion_typewriter",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": "01_typewriter_luogo.mp4", "format": "mp4", "codec": "h264"},
    }, {"slug": "01_typewriter_luogo", "chapter": "01", "title": phrase,
        "display_font": font, "align": "left", "reveal": "typewriter",
        "accent": TERRACOTTA, "size": size, "width": round(width, 1)}


# ── 2. HIGHLIGHTER ───────────────────────────────────────────────────────────
def build_highlighter():
    phrase = "Le prove tecniche cambiano la storia"
    key = "cambiano la storia"
    font = "PlayfairDisplay-Bold.ttf"
    max_width = 1560
    size, width = fit_size(phrase, font, 104, max_width)
    left = MARGIN
    prefix = phrase[:phrase.index(key)]
    prefix_w = measure(prefix, font, size)
    key_w = measure(key, font, size)
    pad = 10
    band_left = left + prefix_w - pad
    band_w = key_w + pad * 2
    band_h = size * 0.64
    band_y = TITLE_Y + size * 0.16

    dx = (band_left + band_w / 2) - W / 2
    dy = band_y - H / 2
    sweep = [dict(frame=28, value=0.001), dict(frame=56, value=1.0)]
    layers = base_layers("02")
    layers.append(color_layer(
        "highlight_band", rgba(OCHRE, 0.58), band_w, band_h, dx, dy, 0, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(28, 0.001), (56, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "position_x", "easing": "out_cubic",
             "keyframes": kf([(28, -band_w / 2), (56, 0.0), (FRAMES - 1, 0.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(28, 0.0), (30, 1.0), (FRAMES - 1, 1.0)])},
        ]))
    layers.append(text_layer("title", phrase, left + (width + 100) / 2, TITLE_Y,
                             width + 100, font, size, INK, 0,
                             [fade(8, 30)], tracking=-1.0))
    layers.append(color_layer("rule", rgba(TERRACOTTA, 0.75), 56, 2,
                              MARGIN + 28 - W / 2, 650 - H / 2, 30, [
                                  {"property": "scale_x", "easing": "in_out_cubic",
                                   "keyframes": kf([(58, 0.001), (76, 1.0), (FRAMES - 1, 1.0)])},
                                  {"property": "opacity", "easing": "linear",
                                   "keyframes": kf([(58, 0.0), (64, 1.0), (FRAMES - 1, 1.0)])}]))

    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "chapter_motion_highlighter",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": "02_highlighter_prove.mp4", "format": "mp4", "codec": "h264"},
    }, {"slug": "02_highlighter_prove", "chapter": "02", "title": phrase,
        "display_font": font, "align": "left", "reveal": "highlighter",
        "accent": OCHRE, "size": size, "width": round(width, 1)}


# ── 3. BRUSH ─────────────────────────────────────────────────────────────────
def brush_bar(lid, cx, cy, width, height, color, start, end, rotation,
              opacity=1.0):
    """A filled rect grows from its left edge: scale_x and position_x share
    the easing, so the left end stays put. Position is canvas-centre relative."""
    layer = {
        "id": lid,
        "type": "shape",
        "enable_3d": True,
        "shape": {
            "type": "rect",
            "fill": color,
        },
        "size": [width, height],
        "position": [cx, cy],
        "rotation": [0.0, 0.0, rotation],
        "start_frame": 0,
        "duration_frames": FRAMES,
    }
    layer["animation"] = {"tracks": [
        {"property": "scale_x", "easing": "in_out_cubic",
         "keyframes": kf([(start, 0.001), (end, 1.0), (FRAMES - 1, 1.0)])},
        {"property": "position_x", "easing": "in_out_cubic",
         "keyframes": kf([(start, -width * 0.5 * 0.999), (end, 0.0),
                          (FRAMES - 1, 0.0)])},
        {"property": "opacity", "easing": "linear",
         "keyframes": kf([(start, 0.0), (start + 2, opacity), (FRAMES - 1, opacity)])},
    ]}
    return layer


def build_brush():
    phrase = "La verità emerge dalle contraddizioni"
    key = "contraddizioni"
    font = "PlayfairDisplay-Bold.ttf"
    size, width = fit_size(phrase, font, 92, 1560)
    left = MARGIN
    prefix_w = measure(phrase[:phrase.index(key)], font, size)
    key_w = measure(key, font, size)
    x0 = left + prefix_w - 4
    x1 = x0 + key_w + 8
    underline_y = TITLE_Y + size * 0.54

    layers = base_layers("03")
    layers.append(text_layer("title", phrase, left + (width + 100) / 2, TITLE_Y,
                             width + 100, font, size, INK, 0,
                             [fade(8, 30)], tracking=-1.0))
    cx = (x0 + x1) / 2 - W / 2
    cy = underline_y - H / 2
    layers.append(brush_bar("brush_main", cx, cy, x1 - x0, 11,
                            BRUSH_RGBA, 32, 62, -0.35))
    layers.append(brush_bar("brush_mid", cx - 8, cy + 4, x1 - x0 - 28, 5,
                            BRUSH_RGBA, 38, 68, 0.25, opacity=0.78))
    layers.append(brush_bar("brush_thin", cx + 4, cy + 7, x1 - x0 - 54, 2,
                            BRUSH_RGBA, 42, 72, -0.15, opacity=0.55))

    return {
        "schema": "chronon.render-plan.v3", "version": 3,
        "job_id": "chapter_motion_brush",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": "03_brush_contraddizioni.mp4", "format": "mp4", "codec": "h264"},
    }, {"slug": "03_brush_contraddizioni", "chapter": "03", "title": phrase,
        "display_font": font, "align": "left", "reveal": "brush",
        "accent": TERRACOTTA, "size": size, "width": round(width, 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schema": "chronontemplate.chapter-motion-demos.v1",
        "engine": "Chronon3D (Vulkan) + ChrononTemplate motion families",
        "glow_note": "no glow: paper, ink and one terracotta accent",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "variants": [],
    }
    for build in (build_typewriter, build_highlighter, build_brush):
        plan, meta = build()
        path = OUT / f"{meta['slug']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        catalog["variants"].append({
            "index": len(catalog["variants"]) + 1,
            **meta,
            "glow": {"opacity": 0.0, "blur": 0},
            "plan": f"plans/{meta['slug']}.plan.json",
            "mp4": f"{meta['slug']}.mp4",
        })
        print(f"{path.name}: {meta['title']!r} {meta['size']}px reveal={meta['reveal']}")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print("wrote", OUT / "showcase.json")


if __name__ == "__main__":
    main()
