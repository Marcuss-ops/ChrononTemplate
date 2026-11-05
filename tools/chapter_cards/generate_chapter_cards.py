#!/usr/bin/env python3
"""Ten chapter-card openers authored inside ChrononTemplate.

One chapter per clip: a small `CAPITOLO NN` marker and a single title line.
No bullet lists, no paragraphs. Only the treatment changes: display face,
accent, glow strength and entrance, so the ten cards can be compared as
directions for a documentary chapter system.

Renderer dialect (certified against chronon3d_cli):
- text/shape positions are canvas pixels (layer centre)
- color positions are centre-relative (0,0 = canvas centre)
- text box width comes from a PIL measurement, so left/right aligned cards
  really start/end at the intended margin
- `tracking` is applied through text spans

The glow is a blurred accent copy of the title drawn behind the warm-white
title. `style.glow` on a text layer is dropped by the Vulkan lane and a shadow
on the top layer is composited over the fill, tinting the glyphs.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "chapter_cards_showcase_v1" / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
BG = [0.035, 0.043, 0.055, 1.0]
INK = "#F7F2E8"

LABEL, TITLE_Y, RULE_Y, PROGRESS_Y = 400, 545, 675, 1000
CENTER_X, LEFT_X, RIGHT_X = 960, 200, 1720

VARIANTS = [
    dict(slug="01_luogo_e_data", chapter="01", title="Il luogo e la data",
         display="PlayfairDisplay-Bold.ttf", align="center", reveal="rise",
         accent="#67E8F9", glow=0.45, blur=18),
    dict(slug="02_prove_tecniche", chapter="02", title="Le prove tecniche",
         display="Oswald-Bold.ttf", align="left", reveal="slide_left",
         accent="#F6B26B", glow=0.55, blur=18),
    dict(slug="03_testimonianze", chapter="03", title="Le testimonianze",
         display="PlayfairDisplay-Italic.ttf", align="center", reveal="soft_rise",
         accent="#E7D7BE", glow=0.30, blur=12),
    dict(slug="04_cronologia", chapter="04", title="La cronologia",
         display="Anton-Regular.ttf", align="right", reveal="drop",
         accent="#FF6FB5", glow=0.65, blur=26),
    dict(slug="05_fonti", chapter="05", title="Le fonti",
         display="AbrilFatface-Regular.ttf", align="left", reveal="scale_pop",
         accent="#C8F26B", glow=0.60, blur=20),
    dict(slug="06_ipotesi", chapter="06", title="L'ipotesi",
         display="PlayfairDisplay-Black.ttf", align="center", reveal="depth",
         accent="#5EEAD4", glow=0.50, blur=20),
    dict(slug="07_contraddizioni", chapter="07", title="Le contraddizioni",
         display="PlayfairDisplay-Italic.ttf", align="left", reveal="fade",
         accent="#B9A7FF", glow=0.25, blur=10),
    dict(slug="08_movente", chapter="08", title="Il movente",
         display="PlayfairDisplay-BoldItalic.ttf", align="center", reveal="rise",
         accent="#FFD98A", glow=0.72, blur=30),
    dict(slug="09_verifica", chapter="09", title="La verifica",
         display="Inter-Black.ttf", align="left", reveal="slide_left",
         accent="#8AB4FF", glow=0.45, blur=14),
    dict(slug="10_resta_agli_atti", chapter="10", title="Cosa resta agli atti",
         display="PlayfairDisplay-ExtraBold.ttf", align="center", reveal="scale_settle",
         accent="#FF8F6B", glow=0.62, blur=24),
]


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def measure(text: str, font: str, size: int) -> float:
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    return float(face.getlength(text))


def fit_title(text: str, font: str, max_width: float, cap: int = 150) -> tuple[int, float]:
    size = cap
    while size > 72:
        width = measure(text, font, size)
        if width <= max_width:
            return size, width
        size -= 2
    return 72, measure(text, font, 72)


def text_layer(lid, text, x, y, box_w, font, size, fill, shadow=None,
               start=0, tracks=None, tracking=None):
    style = {
        "font": f"assets/fonts/{font}",
        "font_size": size,
        "min_font_size": size,
        "max_font_size": size,
        "fit_mode": "shrink_only",
        "fill": fill,
    }
    if shadow:
        style["shadow"] = shadow
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [int(box_w), int(size * 1.9)],
        "position": [x, y],
        "start_frame": start,
        "duration_frames": FRAMES - start,
        "style": style,
    }
    if tracking is not None:
        layer["spans"] = [{"start": 0, "end": len(text.encode()), "style": {"tracking": tracking}}]
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, fill, w, h, dx, dy, start=0, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": fill,
        "size": [w, h],
        "position": [dx, dy],   # centre-relative
        "start_frame": start,
        "duration_frames": FRAMES - start,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def fade(start, end, peak=1.0):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, peak), (FRAMES - 1, peak)])}


def title_tracks(kind: str, start: int = 14):
    if kind == "rise":
        return [fade(start, start + 20),
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(start, 62.0), (start + 28, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "soft_rise":
        return [fade(start, start + 34),
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(start, 26.0), (start + 40, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "slide_left":
        return [fade(start, start + 18),
                {"property": "position_x", "easing": "out_cubic",
                 "keyframes": kf([(start, -120.0), (start + 32, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "drop":
        return [{"property": "opacity", "easing": "out_cubic",
                 "keyframes": kf([(start, 0.0), (start + 10, 1.0), (FRAMES - 1, 1.0)])},
                {"property": "position_y", "easing": "linear",
                 "keyframes": kf([(start, -84.0), (start + 22, 0.0), (start + 28, 14.0),
                                  (start + 36, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "scale_pop":
        return [fade(start, start + 14),
                {"property": "scale", "easing": "out_cubic",
                 "keyframes": kf([(start, 0.72), (start + 18, 1.04),
                                  (start + 28, 1.0), (FRAMES - 1, 1.0)])}]
    if kind == "depth":
        return [fade(start, start + 26),
                {"property": "scale", "easing": "out_cubic",
                 "keyframes": kf([(start, 1.28), (start + 34, 1.0), (FRAMES - 1, 1.0)])}]
    if kind == "fade":
        return [fade(start, start + 36)]
    if kind == "scale_settle":
        return [fade(start, start + 28),
                {"property": "scale", "easing": "out_cubic",
                 "keyframes": kf([(start, 1.12), (start + 36, 1.0), (FRAMES - 1, 1.0)])}]
    return [fade(start, start + 22)]


def build(variant):
    accent = variant["accent"]
    reveal = variant["reveal"]
    align = variant["align"]
    title_tracks_ = title_tracks(reveal)

    max_width = 1480 if align == "center" else 1320
    title_size, title_width = fit_title(variant["title"], variant["display"], max_width)
    title_box = title_width + 140

    if align == "center":
        title_x = CENTER_X
        label_x = CENTER_X
        rule_x = CENTER_X
    elif align == "left":
        title_x = LEFT_X + title_box / 2
        label_x = LEFT_X
        rule_x = LEFT_X + 90
    else:
        title_x = RIGHT_X - title_box / 2
        label_x = RIGHT_X
        rule_x = RIGHT_X - 90

    label = f"CAPITOLO {variant['chapter']}"
    label_tracking = 9.0
    label_width = measure(label, "Inter-SemiBold.ttf", 22) + label_tracking * (len(label) - 1)
    if align == "center":
        label_center = CENTER_X
    elif align == "left":
        label_center = LEFT_X + (label_width + 60) / 2
    else:
        label_center = RIGHT_X - (label_width + 60) / 2

    glow = {"color": accent, "opacity": variant["glow"],
            "blur": variant["blur"], "offset": [0, 0]}

    layers = [color_layer("bg", BG, W, H, 0, 0)]

    layers += [
        text_layer("title_glow", variant["title"], title_x, TITLE_Y, title_box,
                   variant["display"], title_size, accent, glow, 0, title_tracks_),
        text_layer("title", variant["title"], title_x, TITLE_Y, title_box,
                   variant["display"], title_size, INK, None, 0, title_tracks_),
        text_layer("label", label, label_center, LABEL, label_width + 60,
                   "Inter-SemiBold.ttf", 22, accent, None, 4,
                   [fade(4, 22),
                    {"property": "position_y", "easing": "out_cubic",
                     "keyframes": kf([(4, 12.0), (22, 0.0), (FRAMES - 1, 0.0)])}],
                   tracking=label_tracking),
        color_layer("rule", rgba(accent, 0.9), 180, 2,
                    rule_x - W / 2, RULE_Y - H / 2, 30, [
            {"property": "scale_x", "easing": "out_cubic",
             "keyframes": kf([(34, 0.001), (64, 1.0), (FRAMES - 1, 1.0)])},
            {"property": "opacity", "easing": "linear",
             "keyframes": kf([(30, 0.0), (40, 1.0), (FRAMES - 1, 1.0)])}],
        ),
        color_layer("progress", rgba(accent, 0.55), 1200, 2, 0, PROGRESS_Y - 540, 0, [
            {"property": "scale_x", "easing": "linear",
             "keyframes": kf([(0, 0.001), (170, 1.0), (FRAMES - 1, 1.0)])}],
        ),
    ]

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"chapter_card_{variant['slug']}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{variant['slug']}.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schema": "chronontemplate.chapter-cards-showcase.v1",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "variants": [],
    }
    for index, variant in enumerate(VARIANTS, start=1):
        plan = build(variant)
        path = OUT / f"{variant['slug']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        title_size, title_width = fit_title(
            variant["title"], variant["display"],
            1480 if variant["align"] == "center" else 1320)
        catalog["variants"].append({
            "index": index,
            "slug": variant["slug"],
            "chapter": variant["chapter"],
            "title": variant["title"],
            "display_font": variant["display"],
            "align": variant["align"],
            "reveal": variant["reveal"],
            "accent": variant["accent"],
            "glow": {"opacity": variant["glow"], "blur": variant["blur"]},
            "title_px": title_size,
            "title_width_px": round(title_width, 1),
            "plan": f"plans/{variant['slug']}.plan.json",
            "mp4": f"{variant['slug']}.mp4",
        })
        print(f"{path.name}: {variant['title']!r} {title_size}px "
              f"{title_width:.0f}w align={variant['align']} reveal={variant['reveal']}")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print("wrote", OUT / "showcase.json")


if __name__ == "__main__":
    main()
