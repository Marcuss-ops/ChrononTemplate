#!/usr/bin/env python3
"""Ten minimal chapter cards: warm paper, ink, one terracotta accent.

No glow, no gradients, no progress bars, no ghost numerals. The card is only
an eyebrow (CAPITOLO NN), a single title line and a short hairline. Helvetica
Neue carries the type; the ten variants change weight, size, alignment and
entrance within that one system.

Renderer dialect:
- text/shape positions are canvas pixels (layer centre)
- color positions are centre-relative (0,0 = canvas centre)
- `tracking` goes through text spans
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
JOB = ROOT / "out" / "chapter_cards_minimal_v1"
OUT = JOB / "plans"

W, H, FPS, FRAMES = 1920, 1080, 30, 180
PAPER = [0.949, 0.933, 0.902, 1.0]      # #F2EEE6
INK = "#161616"
GRAY = "#6F6A61"
ACCENT = "#B3492F"

LABEL_Y, TITLE_Y, RULE_Y = 380, 500, 640
MARGIN = 160
CENTER_X, RIGHT_X = 960, W - MARGIN

VARIANTS = [
    dict(slug="01_luogo_e_data", chapter="01", title="Il luogo e la data",
         font="HelveticaNeue-Regular.otf", size=132, align="left",
         reveal="rise", label=ACCENT, rule=56, rule_color=ACCENT),
    dict(slug="02_prove_tecniche", chapter="02", title="Le prove tecniche",
         font="HelveticaNeue-Medium.otf", size=120, align="left",
         reveal="fade", label=GRAY, rule=40, rule_color=INK),
    dict(slug="03_testimonianze", chapter="03", title="Le testimonianze",
         font="HelveticaNeue-Regular.otf", size=128, align="center",
         reveal="soft_rise", label=GRAY, rule=0, rule_color=INK),
    dict(slug="04_cronologia", chapter="04", title="La cronologia",
         font="HelveticaNeue-Bold.otf", size=144, align="right",
         reveal="rise", label=ACCENT, rule=56, rule_color=ACCENT),
    dict(slug="05_fonti", chapter="05", title="Le fonti",
         font="HelveticaNeue-Medium.otf", size=150, align="left",
         reveal="fade", label=GRAY, rule=40, rule_color=INK),
    dict(slug="06_ipotesi", chapter="06", title="L'ipotesi",
         font="HelveticaNeue-Regular.otf", size=140, align="center",
         reveal="rise", label=ACCENT, rule=56, rule_color=ACCENT),
    dict(slug="07_contraddizioni", chapter="07", title="Le contraddizioni",
         font="HelveticaNeue-Medium.otf", size=116, align="left",
         reveal="slide", label=GRAY, rule=0, rule_color=INK),
    dict(slug="08_movente", chapter="08", title="Il movente",
         font="HelveticaNeue-Bold.otf", size=140, align="right",
         reveal="fade", label=ACCENT, rule=56, rule_color=ACCENT),
    dict(slug="09_verifica", chapter="09", title="La verifica",
         font="HelveticaNeue-Regular.otf", size=136, align="left",
         reveal="rise", label=GRAY, rule=40, rule_color=INK),
    dict(slug="10_resta_agli_atti", chapter="10", title="Cosa resta agli atti",
         font="HelveticaNeue-Medium.otf", size=112, align="center",
         reveal="soft_rise", label=ACCENT, rule=56, rule_color=ACCENT),
]


def kf(pairs):
    return [{"frame": int(f), "value": v} for f, v in pairs]


def rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def measure(text: str, font: str, size: int) -> float:
    face = ImageFont.truetype(str(ROOT / "assets" / "fonts" / font), size)
    return float(face.getlength(text))


def fit_size(text: str, font: str, requested: int, max_width: float) -> tuple[int, float]:
    size = requested
    while size > 64 and measure(text, font, size) > max_width:
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
        "size": [w, h],
        "position": [dx, dy],   # centre-relative
        "start_frame": start,
        "duration_frames": FRAMES - start,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def fade(start, end):
    return {"property": "opacity", "easing": "out_cubic",
            "keyframes": kf([(start, 0.0), (end, 1.0), (FRAMES - 1, 1.0)])}


def title_tracks(kind: str):
    if kind == "rise":
        return [fade(12, 38),
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(12, 24.0), (44, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "soft_rise":
        return [fade(16, 54),
                {"property": "position_y", "easing": "out_cubic",
                 "keyframes": kf([(16, 14.0), (58, 0.0), (FRAMES - 1, 0.0)])}]
    if kind == "slide":
        return [fade(12, 38),
                {"property": "position_x", "easing": "out_cubic",
                 "keyframes": kf([(12, -28.0), (42, 0.0), (FRAMES - 1, 0.0)])}]
    return [fade(12, 46)]


def build(variant):
    align = variant["align"]
    max_width = 1560 if align != "center" else 1600
    size, width = fit_size(variant["title"], variant["font"], variant["size"], max_width)
    box = width + 100
    if align == "left":
        title_x = MARGIN + box / 2
    elif align == "right":
        title_x = RIGHT_X - box / 2
    else:
        title_x = CENTER_X
    tracks = title_tracks(variant["reveal"])

    label = f"CAPITOLO {variant['chapter']}"
    label_tracking = 7.0
    label_width = measure(label, "HelveticaNeue-Medium.otf", 12) + label_tracking * (len(label) - 1)
    if align == "left":
        label_center = MARGIN + (label_width + 40) / 2
    elif align == "right":
        label_center = RIGHT_X - (label_width + 40) / 2
    else:
        label_center = CENTER_X

    layers = [
        color_layer("paper", PAPER, W, H, 0, 0),
        text_layer("label", label, label_center, LABEL_Y, label_width + 40,
                   "HelveticaNeue-Medium.otf", 12, variant["label"], 4,
                   [fade(4, 20),
                    {"property": "position_y", "easing": "out_cubic",
                     "keyframes": kf([(4, 6.0), (22, 0.0), (FRAMES - 1, 0.0)])}],
                   tracking=label_tracking),
        text_layer("title", variant["title"], title_x, TITLE_Y, box,
                   variant["font"], size, INK, 0, tracks, tracking=-2.0),
    ]

    if variant["rule"]:
        rule_w = variant["rule"]
        if align == "left":
            rule_x = MARGIN + rule_w / 2
        elif align == "right":
            rule_x = RIGHT_X - rule_w / 2
        else:
            rule_x = CENTER_X
        layers.append(color_layer(
            "rule", rgba(variant["rule_color"], 0.85), rule_w, 2,
            rule_x - W / 2, RULE_Y - H / 2, 30, [
                {"property": "scale_x", "easing": "in_out_cubic",
                 "keyframes": kf([(30, 0.001), (54, 1.0), (FRAMES - 1, 1.0)])},
                {"property": "opacity", "easing": "linear",
                 "keyframes": kf([(30, 0.0), (38, 1.0), (FRAMES - 1, 1.0)])}]))

    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"chapter_card_minimal_{variant['slug']}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": FRAMES},
        "layers": layers,
        "output": {"path": f"{variant['slug']}.mp4", "format": "mp4", "codec": "h264"},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "schema": "chronontemplate.chapter-cards-minimal.v1",
        "engine": "Chronon3D (Vulkan) + ChrononTemplate minimal chapter-card language",
        "glow_note": "no glow: flat warm paper, ink type, one terracotta accent",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES},
        "variants": [],
    }
    for index, variant in enumerate(VARIANTS, start=1):
        plan = build(variant)
        path = OUT / f"{variant['slug']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        size, width = fit_size(variant["title"], variant["font"], variant["size"],
                               1560 if variant["align"] != "center" else 1600)
        catalog["variants"].append({
            "index": index,
            "slug": variant["slug"],
            "chapter": variant["chapter"],
            "title": variant["title"],
            "display_font": variant["font"],
            "font_px": size,
            "title_width_px": round(width, 1),
            "align": variant["align"],
            "reveal": variant["reveal"],
            "accent": variant["label"],
            "rule": variant["rule"],
            "glow": {"opacity": 0.0, "blur": 0},
            "plan": f"plans/{variant['slug']}.plan.json",
            "mp4": f"{variant['slug']}.mp4",
        })
        print(f"{path.name}: {variant['title']!r} {size}px {width:.0f}w "
              f"align={variant['align']} reveal={variant['reveal']}")
    (OUT / "showcase.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print("wrote", OUT / "showcase.json")


if __name__ == "__main__":
    main()
