#!/usr/bin/env python3
"""Render ten new phrase-preset families on the native Chronon3D lane.

The current runs use a single look: Playfair Display static, near-black ink on
a white card.  This tool keeps that editorial paper language but opens ten
different families, each with its own typeface, layout and entrance:

    01 Swiss Grid          Inter, left-aligned grid, terracotta rule
    02 Didone Quote        DM Serif Display Italic, centred quotation
    03 Brutalist Poster    Oswald Bold, oversized poster, red second line
    04 Typewriter Memo     Ubuntu Mono, character-by-character memo
    05 Condensed Column    Oswald Medium, narrow column + standfirst
    06 Magazine Cover      Abril Fatface, framed cover with red rule
    07 Modern Luxe         Bodoni Moda, wide white space, slow settle
    08 Lower Third         Inter, black band with red end-stroke
    09 Grotesque Split     Space Grotesk + Inter, two-column split
    10 Noir Frame          DM Serif Display, ivory on charcoal, bronze frame

Every family is emitted as a chronon.render-plan.v2 at 1920x1080, 30 fps,
240 frames (8 seconds, below the 10-second review cap).  Plans are validated
with the CLI before anything is rendered, the encoded MP4s are probed for
geometry/duration, a frame is decoded and checked for visible content, and a
contact sheet is assembled for quick review.

Usage:
    tools/important_phrases/render_phrase_preset_families.py --emit
    tools/important_phrases/render_phrase_preset_families.py --render
    tools/important_phrases/render_phrase_preset_families.py --render --only 01
    tools/important_phrases/render_phrase_preset_families.py --upload
"""

from __future__ import annotations

import sys as _velox_sys
from pathlib import Path as _VeloxPath
_velox_sys.path.insert(0, str(_VeloxPath(__file__).resolve().parents[3] / "tools"))
from stack_config import overlay_root as _overlay_root  # noqa: E402

import os
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
ASSETS = REPO / "Chronon3d"
FONT_DIR = ASSETS / "assets" / "fonts"
OUT = ROOT / "out" / "phrase_preset_families_v1"
PLANS = OUT / "plans"
MP4 = OUT / "mp4"
PREVIEW = OUT / "preview"
LOGS = OUT / "logs"

CLI = ASSETS / "build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
UPLOADER = REPO / "RenderingGen/bin/drive-upload"
CREDENTIALS = REPO / "RenderingGen/UploadDrive/credentials.json"
TOKEN = REPO / "RenderingGen/UploadDrive/token.json"
DRIVE_FOLDER = _overlay_root()
DRIVE_SUBFOLDER = "Phrase Preset Families v1"

W, H, FPS, FRAMES = 1920, 1080, 30, 240
DURATION_S = FRAMES / FPS
INK = "#111111"
MUTED = "#6F6A61"
PAPER = "#F7F4EF"

FAMILY_META = [
    {
        "slug": "01_swiss_grid",
        "name": "Swiss Grid",
        "type": "Inter — left-aligned editorial grid",
        "motion": "terracotta rule draw + three-line rise",
        "note": "La base svizzera: gerarchia per peso, non per decorazione.",
    },
    {
        "slug": "02_didone_quote",
        "name": "Didone Quote",
        "type": "DM Serif Display Italic — centred quotation",
        "motion": "quotation-mark settle + soft scale fade",
        "note": "Citazione alta, tanto bianco, nessun ornamento oltre la virgoletta.",
    },
    {
        "slug": "03_brutalist_poster",
        "name": "Brutalist Poster",
        "type": "Oswald Bold — oversized uppercase poster",
        "motion": "top bar drop + snap scale + red line slide",
        "note": "Il contrario del minimal: tipo enorme, taglio duro, un solo rosso.",
    },
    {
        "slug": "04_typewriter_memo",
        "name": "Typewriter Memo",
        "type": "Ubuntu Mono — dossier / memo",
        "motion": "character reveal + blinking caret",
        "note": "Frase come documento: mono, caratteri uno a uno, caret finale.",
    },
    {
        "slug": "05_condensed_column",
        "name": "Condensed Column",
        "type": "Oswald Medium + Inter Light — narrow column",
        "motion": "line-by-line rise + vertical rule draw",
        "note": "Impaginazione da rivista: titolo stretto e standfirst a destra.",
    },
    {
        "slug": "06_magazine_cover",
        "name": "Magazine Cover",
        "type": "Abril Fatface — framed cover",
        "motion": "cover frame fade + line wipe + red rule draw",
        "note": "Copertina: cornice, kicker, titolo alto e una linea rossa.",
    },
    {
        "slug": "07_modern_luxe",
        "name": "Modern Luxe",
        "type": "Bodoni Moda — centred luxury",
        "motion": "90-frame scale settle + slow fades",
        "note": "Lusso tipografico: Bodoni, tracking ampio, regole sottilissime.",
    },
    {
        "slug": "08_lower_third",
        "name": "Lower Third",
        "type": "Inter — broadcast lower third",
        "motion": "band slide + red accent draw + two-line fade",
        "note": "Il preset più vicino all'overlay: banda nera e testo bianco.",
    },
    {
        "slug": "09_grotesque_split",
        "name": "Grotesque Split",
        "type": "Space Grotesk + Inter Light — two columns",
        "motion": "left rise + right staggered fade + rule draw",
        "note": "Split editoriale: statement a sinistra, contesto a destra.",
    },
    {
        "slug": "10_noir_frame",
        "name": "Noir Frame",
        "type": "DM Serif Display — ivory on charcoal",
        "motion": "bronze frame draw + slow breathing fade",
        "note": "L'unica famiglia scura: inchiostro chiaro, cornice bronzo.",
    },
]


# ---------------------------------------------------------------------------
# small authoring helpers
# ---------------------------------------------------------------------------

def rgba(value: str, alpha: float = 1.0) -> list[float]:
    v = value.lstrip("#")
    return [round(int(v[i : i + 2], 16) / 255.0, 4) for i in (0, 2, 4)] + [alpha]


def kf(pairs: list[tuple[int, float]]) -> list[dict[str, Any]]:
    return [{"frame": int(f), "value": float(v)} for f, v in pairs]


def ease_value(name: str, t: float) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if name == "linear":
        return t
    if name == "smoothstep":
        return t * t * (3.0 - 2.0 * t)
    if name == "in_quad":
        return t * t
    if name == "out_quad":
        return -(t * (t - 2.0))
    if name == "in_cubic":
        return t * t * t
    if name == "out_cubic":
        f = t - 1.0
        return f * f * f + 1.0
    if name == "in_out_cubic":
        if t < 0.5:
            return 4.0 * t * t * t
        f = 2.0 * t - 2.0
        return 0.5 * f * f * f + 1.0
    if name == "in_sine":
        return math.sin((t - 1.0) * math.pi / 2.0) + 1.0
    if name == "out_sine":
        return math.sin(t * math.pi / 2.0)
    if name == "in_out_sine":
        return 0.5 * (1.0 - math.cos(t * math.pi))
    if name == "in_out_quad":
        if t < 0.5:
            return 2.0 * t * t
        f = t - 1.0
        return -2.0 * f * f + 1.0
    if name == "in_expo":
        return 0.0 if t <= 0.0 else math.pow(2.0, 10.0 * (t - 1.0))
    if name == "out_expo":
        return 1.0 if t >= 1.0 else 1.0 - math.pow(2.0, -10.0 * t)
    if name == "in_out_expo":
        if t < 0.5:
            return 0.5 * math.pow(2.0, 20.0 * t - 10.0)
        return 1.0 - 0.5 * math.pow(2.0, -20.0 * t + 10.0)
    if name == "out_back":
        o = 1.70158
        n = t - 1.0
        return n * n * ((o + 1.0) * n + o) + 1.0
    raise SystemExit(f"unsupported easing: {name}")


def measure(text: str, font: str, size: float, tracking: float = 0.0) -> float:
    face = ImageFont.truetype(str(FONT_DIR / font), max(1, int(round(size))))
    width = float(face.getlength(text))
    if tracking and len(text) > 1:
        width += tracking * (len(text) - 1)
    return width


def fit_sizes(lines: list[dict[str, Any]], max_width: float) -> list[float]:
    sizes = [float(line.get("size", 64)) for line in lines]
    widths = [
        measure(line["text"], line["font"], size, float(line.get("tracking", 0.0)))
        for line, size in zip(lines, sizes)
    ]
    widest = max(widths) if widths else 0.0
    if widest > max_width and widest > 0:
        scale = max_width / widest
        sizes = [max(18.0, size * scale) for size in sizes]
    return sizes


def anchor_x(width: float, align: str, margin: float, x: float | None) -> float:
    if align == "left":
        return margin + width / 2.0
    if align == "right":
        return W - margin - width / 2.0
    return W / 2.0 if x is None else x


def rect(
    layer_id: str,
    cx: float,
    cy: float,
    width: float,
    height: float,
    color: str,
    *,
    anim: str = "none",
    delay: int = 0,
    opacity: float = 1.0,
) -> dict[str, Any]:
    return {
        "kind": "rect",
        "id": layer_id,
        "cx": cx,
        "cy": cy,
        "w": width,
        "h": height,
        "color": rgba(color, opacity),
        "anim": anim,
        "delay": delay,
    }


def text(
    layer_id: str,
    value: str,
    font: str,
    size: float,
    color: str,
    *,
    y: float,
    align: str = "left",
    margin: float = 140.0,
    x: float | None = None,
    tracking: float = 0.0,
    max_width: float = 1600.0,
    anim: str = "fade",
    delay: int = 0,
    text_anim: str | None = None,
    reveal: int = 42,
    shape: str = "smooth",
    order: str = "forward",
    pace: str = "out_cubic",
    extra: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    size = min(size, max_width / max(measure(value, font, size, tracking) / size, 1e-6))
    return {
        "kind": "text",
        "id": layer_id,
        "text": value,
        "font": font,
        "size": size,
        "color": rgba(color),
        "y": y,
        "align": align,
        "margin": margin,
        "x": x,
        "tracking": tracking,
        "anim": anim,
        "delay": delay,
        "text_anim": text_anim,
        "reveal": reveal,
        "shape": shape,
        "order": order,
        "pace": pace,
        "extra": extra or {},
    }


def block(
    lines: list[dict[str, Any]],
    *,
    y: float,
    align: str = "left",
    margin: float = 140.0,
    x: float | None = None,
    gap: float = 1.12,
    max_width: float = 1600.0,
    anim: str = "rise",
    delay: int = 8,
    stagger: int = 10,
    text_anim: str | None = None,
    reveal: int = 42,
    shape: str = "smooth",
    order: str = "forward",
    pace: str = "out_cubic",
    extra: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "block",
        "lines": lines,
        "y": y,
        "align": align,
        "margin": margin,
        "x": x,
        "gap": gap,
        "max_width": max_width,
        "anim": anim,
        "delay": delay,
        "stagger": stagger,
        "text_anim": text_anim,
        "reveal": reveal,
        "shape": shape,
        "order": order,
        "pace": pace,
        "extra": extra or {},
    }


# ---------------------------------------------------------------------------
# ten families
# ---------------------------------------------------------------------------

def families() -> list[dict[str, Any]]:
    return [
        {
            "meta": FAMILY_META[0],
            "bg": "#F7F4EF",
            "phrase": "Le parole giuste / arrivano al / momento giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#F7F4EF"),
                rect("rule", 192, 330, 64, 4, "#B3492F", anim="draw_x", delay=4),
                text("eyebrow", "PRESET 01 — SWISS GRID", "Inter-SemiBold.ttf", 17,
                     "#B3492F", y=292, margin=160, tracking=5, anim="fade", delay=2),
                block(
                    [
                        {"text": "Le parole giuste", "font": "Inter-SemiBold.ttf", "size": 138, "color": INK},
                        {"text": "arrivano al", "font": "Inter-SemiBold.ttf", "size": 138, "color": INK},
                        {"text": "momento giusto", "font": "Inter-Light.ttf", "size": 138, "color": MUTED},
                    ],
                    y=590, margin=160, gap=1.06, max_width=1600,
                    anim="rise", delay=8, stagger=10,
                ),
                text("footer", "1920 × 1080   /   30 FPS", "Inter-Light.ttf", 14,
                     MUTED, y=980, align="right", margin=160, tracking=3,
                     anim="fade", delay=46),
            ],
        },
        {
            "meta": FAMILY_META[1],
            "bg": "#FFFFFF",
            "phrase": "Le parole giuste / arrivano al momento / giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#FFFFFF"),
                text("quote", "“", "DM-Serif-Display.ttf", 240, "#D8C7B2",
                     y=300, x=960, align="center", anim="scale_settle", delay=0),
                block(
                    [
                        {"text": "Le parole giuste", "font": "DM-Serif-Display-Italic.ttf", "size": 128, "color": INK},
                        {"text": "arrivano al momento", "font": "DM-Serif-Display-Italic.ttf", "size": 128, "color": INK},
                        {"text": "giusto", "font": "DM-Serif-Display-Italic.ttf", "size": 128, "color": "#B3492F"},
                    ],
                    y=620, align="center", gap=1.12, max_width=1500,
                    anim="scale_settle", delay=10, stagger=12,
                ),
                text("signature", "— PRESET 02  /  DIDONE QUOTE", "Inter-Light.ttf", 15,
                     MUTED, y=930, align="center", tracking=5, anim="fade", delay=52),
            ],
        },
        {
            "meta": FAMILY_META[2],
            "bg": "#FFFFFF",
            "phrase": "LE PAROLE GIUSTE / ARRIVANO ORA",
            "layers": [
                rect("bg", 960, 540, W, H, "#FFFFFF"),
                rect("top_bar", 960, 90, W, 180, INK, anim="slide_y", delay=0),
                text("top_label", "PRESET 03  —  POSTER", "Inter-SemiBold.ttf", 20,
                     "#FFFFFF", y=90, margin=80, tracking=6, anim="fade", delay=12),
                text("line_one", "LE PAROLE", "Oswald-Bold.ttf", 300, INK,
                     y=410, margin=80, max_width=1760, anim="scale_settle", delay=4),
                text("line_two", "GIUSTE", "Oswald-Bold.ttf", 300, "#E12636",
                     y=700, margin=80, max_width=1760, anim="slide_left", delay=14),
                text("tagline", "ARRIVANO AL MOMENTO GIUSTO", "Oswald-Medium.ttf", 28,
                     MUTED, y=960, margin=80, tracking=2, anim="fade", delay=34),
                rect("bottom_rule", 960, 1020, W, 8, INK, anim="draw_x", delay=26),
            ],
        },
        {
            "meta": FAMILY_META[3],
            "bg": "#FAF7F2",
            "phrase": "Le parole giuste / arrivano al momento / giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#FAF7F2"),
                rect("top_rule", 960, 140, 1640, 2, INK, anim="draw_x", delay=0),
                text("eyebrow", "MEMO / 04 — ARCHIVIO", "UbuntuMono-R.ttf", 20,
                     INK, y=200, margin=140, tracking=2, anim="fade", delay=4),
                block(
                    [
                        {"text": "Le parole giuste", "font": "UbuntuMono-R.ttf", "size": 76, "color": INK},
                        {"text": "arrivano al momento", "font": "UbuntuMono-R.ttf", "size": 76, "color": INK},
                        {"text": "giusto", "font": "UbuntuMono-R.ttf", "size": 76, "color": INK},
                    ],
                    y=490, margin=140, gap=1.32, max_width=1500,
                    anim="none", delay=10, stagger=14,
                    text_anim="glyph", reveal=34, shape="square", pace="linear",
                ),
                rect("caret", 140 + measure("giusto", "UbuntuMono-R.ttf", 76) + 70, 490 + 1.32 * 76,
                     10, 68, INK, anim="blink", delay=0),
                rect("bottom_rule", 960, 760, 1640, 2, INK, anim="draw_x", delay=44),
                text("footer_left", "FONTE: PRESET FAMILIES V1", "UbuntuMono-R.ttf", 15,
                     MUTED, y=820, margin=140, tracking=1, anim="fade", delay=48),
                text("footer_right", "PAGINA 04", "UbuntuMono-R.ttf", 15,
                     MUTED, y=820, align="right", margin=140, tracking=1, anim="fade", delay=52),
            ],
        },
        {
            "meta": FAMILY_META[4],
            "bg": "#F2EEE6",
            "phrase": "LE PAROLE / GIUSTE ARRIVANO / AL MOMENTO / GIUSTO",
            "layers": [
                rect("bg", 960, 540, W, H, "#F2EEE6"),
                rect("column_rule", 930, 540, 2, 620, "#1F3A5F", anim="draw_y", delay=8),
                text("eyebrow", "05 — CRONACA", "Oswald-Medium.ttf", 22, "#1F3A5F",
                     y=250, margin=140, tracking=5, anim="slide_left", delay=2),
                block(
                    [
                        {"text": "LE PAROLE", "font": "Oswald-Medium.ttf", "size": 92, "color": INK},
                        {"text": "GIUSTE ARRIVANO", "font": "Oswald-Medium.ttf", "size": 92, "color": INK},
                        {"text": "AL MOMENTO", "font": "Oswald-Medium.ttf", "size": 92, "color": INK},
                        {"text": "GIUSTO", "font": "Oswald-Medium.ttf", "size": 92, "color": "#B3492F"},
                    ],
                    y=570, margin=140, gap=1.14, max_width=700,
                    anim="rise", delay=8, stagger=9,
                ),
                block(
                    [
                        {"text": "Un preset editoriale", "font": "Inter-Light.ttf", "size": 30, "color": "#4A463F"},
                        {"text": "per la frase che chiude", "font": "Inter-Light.ttf", "size": 30, "color": "#4A463F"},
                        {"text": "il capitolo.", "font": "Inter-Light.ttf", "size": 30, "color": "#4A463F"},
                    ],
                    y=560, align="left", margin=1010, gap=1.45, max_width=720,
                    anim="fade", delay=34, stagger=6,
                ),
                text("footer", "PRESET 05", "Oswald-Medium.ttf", 14, MUTED,
                     y=950, align="right", margin=140, tracking=4, anim="fade", delay=54),
            ],
        },
        {
            "meta": FAMILY_META[5],
            "bg": "#FFFFFF",
            "phrase": "Le parole / giuste / arrivano al momento giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#FFFFFF"),
                rect("frame_top", 960, 60, 1800, 4, INK, anim="fade", delay=0),
                rect("frame_bottom", 960, 1020, 1800, 4, INK, anim="fade", delay=0),
                rect("frame_left", 60, 540, 4, 960, INK, anim="fade", delay=0),
                rect("frame_right", 1860, 540, 4, 960, INK, anim="fade", delay=0),
                text("kicker", "PRESET 06", "Inter-SemiBold.ttf", 16, "#E12636",
                     y=150, margin=110, tracking=6, anim="slide_left", delay=6),
                text("line_one", "Le parole", "AbrilFatface-Regular.ttf", 180, INK,
                     y=430, margin=110, max_width=1600, anim="slide_left", delay=8),
                text("line_two", "giuste", "AbrilFatface-Regular.ttf", 180, INK,
                     y=620, margin=110, max_width=1600, anim="slide_left", delay=22),
                rect("red_rule", 170, 760, 120, 6, "#E12636", anim="draw_x", delay=44),
                block(
                    [{"text": "arrivano al momento giusto", "font": "Inter-Light.ttf", "size": 34,
                      "color": "#4A463F"}],
                    y=830, margin=110, max_width=1400, anim="fade", delay=52,
                ),
                text("footer", "1920 × 1080", "UbuntuMono-R.ttf", 14, MUTED,
                     y=970, align="right", margin=110, tracking=1, anim="fade", delay=58),
            ],
        },
        {
            "meta": FAMILY_META[6],
            "bg": "#FAF8F3",
            "phrase": "Le parole giuste / arrivano al momento / giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#FAF8F3"),
                text("eyebrow", "P R E S E T   0 7", "Inter-Light.ttf", 13, "#9A7B4F",
                     y=300, align="center", tracking=10, anim="fade", delay=8),
                block(
                    [
                        {"text": "Le parole giuste", "font": "BodoniModa-Regular.ttf", "size": 100, "color": "#141414"},
                        {"text": "arrivano al momento", "font": "BodoniModa-Regular.ttf", "size": 100, "color": "#141414"},
                        {"text": "giusto", "font": "BodoniModa-Regular.ttf", "size": 100, "color": "#141414"},
                    ],
                    y=560, align="center", gap=1.18, max_width=1500,
                    anim="scale_settle", delay=10, stagger=12,
                ),
                rect("rule_top", 960, 400, 480, 1, "#9A7B4F", anim="draw_x", delay=30),
                rect("rule_bottom", 960, 760, 480, 1, "#9A7B4F", anim="draw_x", delay=40),
                text("footer", "BODONI MODA  /  EDITORIAL LUXE", "Inter-Light.ttf", 13,
                     "#9A7B4F", y=880, align="center", tracking=6, anim="fade", delay=56),
            ],
        },
        {
            "meta": FAMILY_META[7],
            "bg": "#FFFFFF",
            "phrase": "Le parole giuste / arrivano al momento giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#FFFFFF"),
                text("kicker", "DOCUMENTARY  /  08", "Inter-SemiBold.ttf", 16, "#777777",
                     y=120, margin=80, tracking=4, anim="fade", delay=2),
                rect("band", 960, 850, W, 170, INK, anim="slide_left", delay=8),
                rect("accent", 80, 850, 8, 170, "#E12636", anim="draw_y", delay=24),
                text("line_one", "Le parole giuste", "Inter-SemiBold.ttf", 46, "#FFFFFF",
                     y=815, margin=120, max_width=1500, anim="slide_left", delay=30),
                text("line_two", "arrivano al momento giusto", "Inter-Light.ttf", 34, "#D8D8D8",
                     y=880, margin=120, max_width=1500, anim="fade", delay=40),
            ],
        },
        {
            "meta": FAMILY_META[8],
            "bg": "#F7F4EF",
            "phrase": "Le parole / giuste. / Un sistema tipografico che tiene insieme gerarchia, ritmo e silenzio.",
            "layers": [
                rect("bg", 960, 540, W, H, "#F7F4EF"),
                rect("column_rule", 930, 540, 2, 600, "#B9B3A8", anim="draw_y", delay=10),
                text("eyebrow", "09 / SPLIT", "UbuntuMono-R.ttf", 14, MUTED,
                     y=300, margin=140, tracking=4, anim="fade", delay=2),
                block(
                    [
                        {"text": "Le parole", "font": "Space-Grotesk.ttf", "size": 118, "color": INK},
                        {"text": "giuste.", "font": "Space-Grotesk.ttf", "size": 118, "color": "#E12636"},
                    ],
                    y=535, margin=140, gap=1.06, max_width=700,
                    anim="rise", delay=8, stagger=14,
                ),
                block(
                    [
                        {"text": "Un sistema tipografico", "font": "Inter-Light.ttf", "size": 27, "color": "#4A463F"},
                        {"text": "che tiene insieme", "font": "Inter-Light.ttf", "size": 27, "color": "#4A463F"},
                        {"text": "gerarchia, ritmo", "font": "Inter-Light.ttf", "size": 27, "color": "#4A463F"},
                        {"text": "e silenzio.", "font": "Inter-Light.ttf", "size": 27, "color": "#4A463F"},
                    ],
                    y=555, margin=1010, gap=1.55, max_width=720,
                    anim="fade", delay=26, stagger=7,
                ),
                text("footer", "PRESET FAMILIES — 2026", "UbuntuMono-R.ttf", 13, MUTED,
                     y=950, margin=140, tracking=2, anim="fade", delay=56),
            ],
        },
        {
            "meta": FAMILY_META[9],
            "bg": "#141414",
            "phrase": "Le parole giuste / arrivano al momento / giusto",
            "layers": [
                rect("bg", 960, 540, W, H, "#141414"),
                rect("frame_top", 960, 70, 1780, 2, "#9A7B4F", anim="fade", delay=0),
                rect("frame_bottom", 960, 1010, 1780, 2, "#9A7B4F", anim="fade", delay=0),
                rect("frame_left", 70, 540, 2, 940, "#9A7B4F", anim="fade", delay=0),
                rect("frame_right", 1850, 540, 2, 940, "#9A7B4F", anim="fade", delay=0),
                text("eyebrow", "PRESET 10 — NOIR", "Inter-Light.ttf", 13, "#9A7B4F",
                     y=300, align="center", tracking=8, anim="fade", delay=6),
                text("line_one", "Le parole giuste", "DM-Serif-Display.ttf", 112, "#F2EEE6",
                     y=500, align="center", max_width=1500, anim="fade", delay=10),
                text("line_two", "arrivano al momento", "DM-Serif-Display-Italic.ttf", 88, "#C9C0B2",
                     y=620, align="center", max_width=1500, anim="fade", delay=22),
                text("line_three", "giusto", "DM-Serif-Display-Italic.ttf", 88, "#C9C0B2",
                     y=720, align="center", max_width=1500, anim="fade", delay=32),
                text("footer", "LUCE RASENTE  /  INCHIOSTRO CHIARO", "Inter-Light.ttf", 12,
                     "#8A8378", y=880, align="center", tracking=6, anim="fade", delay=56),
            ],
        },
    ]


# ---------------------------------------------------------------------------
# plan lowering
# ---------------------------------------------------------------------------

def selector_start(delay: int, reveal: int, pace: str) -> list[dict[str, Any]]:
    end = max(delay + 1, delay + reveal)
    frames = [{"frame": 0, "value": 0}]
    for frame in range(1, end + 1):
        if frame <= delay:
            value = 0.0
        else:
            t = min(1.0, (frame - delay) / max(reveal, 1))
            value = round(100.0 * ease_value(pace, t), 4)
        frames.append({"frame": frame, "value": value})
    return frames


def bake(points: list[tuple[float, float]], easing: str) -> list[dict[str, Any]]:
    points = sorted(points)
    baked: list[dict[str, Any]] = []
    segment = 0
    for frame in range(FRAMES):
        while segment + 1 < len(points) and frame > points[segment + 1][0]:
            segment += 1
        if frame <= points[0][0]:
            value = points[0][1]
        elif segment + 1 >= len(points):
            value = points[-1][1]
        else:
            start, start_value = points[segment]
            end, end_value = points[segment + 1]
            if end <= start:
                value = end_value
            else:
                t = (frame - start) / (end - start)
                value = start_value + (end_value - start_value) * ease_value(easing, t)
        baked.append({"frame": frame, "value": round(float(value), 4)})
    return baked


def text_animator(
    layer_id: str,
    spec: dict[str, Any],
    delay: int,
    *,
    unit: str | None = None,
    reveal: int | None = None,
    shape: str | None = None,
    order: str | None = None,
    pace: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unit = unit or spec["text_anim"] or "word"
    reveal = reveal or spec["reveal"]
    shape = shape or spec["shape"]
    order = order or spec["order"]
    pace = pace or spec["pace"]
    selector = {
        "id": f"{layer_id}_selector",
        "unit": "glyph" if unit == "char" else unit,
        "shape": shape,
        "order": order,
        "combine": "replace",
        "exclude_spaces": True,
        "start": {"keyframes": selector_start(delay, reveal, pace), "easing": "linear"},
        "end": {"keyframes": [{"frame": 0, "value": 100}], "easing": "linear"},
    }
    properties = [
        {
            "property": "opacity",
            "keyframes": bake(
                [(0.0, 0.0), (delay, 0.0), (delay + max(12, reveal // 2), 1.0), (FRAMES - 1, 1.0)],
                "out_cubic",
            ),
            "easing": "linear",
        }
    ]
    for prop, (start_value, end_value) in (extra or {}).items():
        properties.append(
            {
                "property": prop,
                "keyframes": bake(
                    [
                        (0.0, start_value),
                        (delay, start_value),
                        (delay + reveal + 18, end_value),
                        (FRAMES - 1, end_value),
                    ],
                    "out_cubic",
                ),
                "easing": "linear",
            }
        )
    return {
        "id": f"{layer_id}_reveal",
        "selectors": [selector],
        "properties": properties,
    }


def layer_tracks(kind: str, delay: int) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    exit_fade = [{"frame": FRAMES - 12, "value": 1.0}, {"frame": FRAMES - 1, "value": 0.0}]
    if kind == "none":
        return [{"property": "opacity", "keyframes": [{"frame": 0, "value": 1.0}] + exit_fade,
                 "easing": "linear"}]
    if kind == "fade":
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 26, 1.0)]) + exit_fade,
            "easing": "out_cubic",
        })
    elif kind == "rise":
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 18, 1.0)]) + exit_fade,
            "easing": "linear",
        })
        tracks.append({
            "property": "position_y",
            "keyframes": kf([(0, 28.0), (delay, 28.0), (delay + 34, 0.0), (FRAMES - 1, 0.0)]),
            "easing": "out_cubic",
        })
    elif kind == "slide_left":
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 16, 1.0)]) + exit_fade,
            "easing": "linear",
        })
        tracks.append({
            "property": "position_x",
            "keyframes": kf([(0, -80.0), (delay, -80.0), (delay + 30, 0.0), (FRAMES - 1, 0.0)]),
            "easing": "out_expo",
        })
    elif kind == "scale_settle":
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 40, 1.0)]) + exit_fade,
            "easing": "in_out_sine",
        })
        tracks.append({
            "property": "scale",
            "keyframes": kf([(0, 1.045), (delay, 1.045), (delay + 70, 1.0), (FRAMES - 1, 1.0)]),
            "easing": "in_out_cubic",
        })
    return tracks


def rect_tracks(kind: str, delay: int, height: float) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    exit_fade = [{"frame": FRAMES - 12, "value": 1.0}, {"frame": FRAMES - 1, "value": 0.0}]
    if kind == "none":
        return [{"property": "opacity", "keyframes": [{"frame": 0, "value": 1.0}], "easing": "linear"}]
    if kind == "fade":
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 18, 1.0)]) + exit_fade,
            "easing": "linear",
        })
    elif kind == "draw_x":
        tracks.append({
            "property": "scale_x",
            "keyframes": kf([(0, 0.001), (delay, 0.001), (delay + 24, 1.0), (FRAMES - 1, 1.0)]),
            "easing": "out_cubic",
        })
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 8, 1.0)]) + exit_fade,
            "easing": "linear",
        })
    elif kind == "draw_y":
        tracks.append({
            "property": "scale_y",
            "keyframes": kf([(0, 0.001), (delay, 0.001), (delay + 28, 1.0), (FRAMES - 1, 1.0)]),
            "easing": "out_cubic",
        })
        tracks.append({
            "property": "opacity",
            "keyframes": kf([(0, 0.0), (delay, 0.0), (delay + 8, 1.0)]) + exit_fade,
            "easing": "linear",
        })
    elif kind == "slide_left":
        tracks.append({
            "property": "position_x",
            "keyframes": kf([(0, -W), (delay, -W), (delay + 28, 0.0), (FRAMES - 1, 0.0)]),
            "easing": "out_expo",
        })
    elif kind == "slide_y":
        tracks.append({
            "property": "position_y",
            "keyframes": kf([(0, -height), (delay, -height), (delay + 26, 0.0), (FRAMES - 1, 0.0)]),
            "easing": "out_expo",
        })
    elif kind == "blink":
        tracks.append({
            "property": "opacity",
            "keyframes": [
                {"frame": 0, "value": 1.0},
                {"frame": 18, "value": 1.0},
                {"frame": 19, "value": 0.0},
                {"frame": 34, "value": 0.0},
                {"frame": 35, "value": 1.0},
                {"frame": 52, "value": 1.0},
                {"frame": 53, "value": 0.0},
                {"frame": 68, "value": 0.0},
                {"frame": 69, "value": 1.0},
                {"frame": FRAMES - 12, "value": 1.0},
                {"frame": FRAMES - 1, "value": 0.0},
            ],
            "easing": "hold",
        })
    return tracks


def dedupe_track(track: dict[str, Any]) -> dict[str, Any]:
    """Collapse coincident keyframe frames, keeping the later value."""
    values: dict[int, float] = {}
    for key in track["keyframes"]:
        values[int(key["frame"])] = float(key["value"])
    track["keyframes"] = [
        {"frame": frame, "value": value} for frame, value in sorted(values.items())
    ]
    return track


def text_layer(spec: dict[str, Any], box_width: float, height: float) -> dict[str, Any]:
    layer: dict[str, Any] = {
        "id": spec["id"],
        "type": "text",
        "text": spec["text"],
        "size": [round(box_width, 2), round(height, 2)],
        "position": [round(spec["x"], 2), round(spec["y"], 2)],
        "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {
            "font": f"assets/fonts/{spec['font']}",
            "font_size": round(spec["size"], 2),
            "fill": "#%02X%02X%02X" % tuple(round(c * 255) for c in spec["color"][:3]),
        },
    }
    tracking = float(spec.get("tracking", 0.0))
    if tracking:
        encoded = spec["text"].encode("utf-8")
        layer["spans"] = [
            {"start": 0, "end": len(encoded), "style": {"tracking": tracking}}
        ]
    tracks = [dedupe_track(track) for track in layer_tracks(spec["anim"], spec["delay"])]
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if spec["text_anim"]:
        layer["text_animators"] = [
            text_animator(
                spec["id"],
                spec,
                spec["delay"],
                extra=spec.get("extra"),
            )
        ]
    return layer


def rect_layer(spec: dict[str, Any]) -> dict[str, Any]:
    layer: dict[str, Any] = {
        "id": spec["id"],
        "type": "color",
        "color": spec["color"],
        "size": [round(spec["w"], 2), round(spec["h"], 2)],
        "position": [round(spec["cx"] - W / 2.0, 2), round(spec["cy"] - H / 2.0, 2)],
        "start_frame": 0,
        "duration_frames": FRAMES,
    }
    tracks = [dedupe_track(track) for track in rect_tracks(spec["anim"], spec["delay"], spec["h"])]
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def resolve_layers(family: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    block_index = 0
    for spec in family["layers"]:
        if spec["kind"] == "rect":
            layers.append(rect_layer(spec))
            continue
        if spec["kind"] == "block":
            sizes = fit_sizes(spec["lines"], spec["max_width"])
            max_size = max(sizes)
            gap = spec["gap"] * max_size
            first_y = spec["y"] - (len(spec["lines"]) - 1) * gap / 2.0
            for index, line in enumerate(spec["lines"]):
                line_spec = dict(spec)
                line_spec.update(line)
                if isinstance(line.get("color"), str):
                    line_spec["color"] = rgba(line["color"])
                line_spec["id"] = f"{family['meta']['slug']}_block{block_index}_{index}"
                line_spec["size"] = sizes[index]
                line_spec["y"] = first_y + index * gap
                line_spec["delay"] = spec["delay"] + index * spec["stagger"]
                line_spec["tracking"] = float(line.get("tracking", 0.0))
                width = measure(line["text"], line["font"], line_spec["size"], float(line.get("tracking", 0.0)))
                box_w = width + 64.0
                line_spec["x"] = anchor_x(box_w, spec["align"], spec["margin"], spec["x"])
                layers.append(text_layer(line_spec, box_w, line_spec["size"] * 1.55))
            block_index += 1
            continue
        width = measure(spec["text"], spec["font"], spec["size"], spec["tracking"])
        spec = dict(spec)
        box_w = width + 64.0
        spec["x"] = anchor_x(box_w, spec["align"], spec["margin"], spec["x"])
        layers.append(text_layer(spec, box_w, spec["size"] * 1.55))
    return layers


def make_plan(family: dict[str, Any]) -> dict[str, Any]:
    meta = family["meta"]
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"chronontemplate_phrase_preset_{meta['slug']}",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": resolve_layers(family),
        "output": {"path": f"{meta['slug']}.mp4", "format": "mp4", "codec": "h264"},
    }


# ---------------------------------------------------------------------------
# verification / render / upload
# ---------------------------------------------------------------------------

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(plan: Path) -> None:
    subprocess.run(
        [str(CLI), "validate", "--plan", str(plan), "--assets-root", str(ASSETS)],
        check=True,
        cwd=REPO,
        stdout=subprocess.DEVNULL,
    )


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,nb_frames,r_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        check=True, text=True, capture_output=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "nb_frames": int(stream.get("nb_frames", 0)),
        "duration": float(data["format"]["duration"]),
    }


def decode_preview(video: Path, image: Path, at_seconds: float = 4.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{at_seconds}", "-i", str(video),
            "-frames:v", "1", "-update", "1", str(image),
        ],
        check=True,
        cwd=REPO,
    )
    with Image.open(image) as frame:
        if frame.size != (W, H):
            raise RuntimeError(f"{image.name}: expected 1920x1080, got {frame.size}")
        rgb = frame.convert("RGB")
        stat = ImageStat.Stat(rgb)
        if max(stat.stddev) < 2.0:
            raise RuntimeError(f"{image.name}: decoded frame has no visible variation")
        if len(rgb.getcolors(maxcolors=1_000_000) or []) < 8:
            raise RuntimeError(f"{image.name}: decoded frame is flat")


def render_one(slug: str, plan: Path, output: Path) -> dict[str, Any]:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{slug}.log"
    with log.open("w") as handle:
        subprocess.run(
            [
                str(CLI), "render",
                "--plan", str(plan),
                "--assets-root", str(ASSETS),
                "--backend", "vulkan",
                "--hardware", "nvenc",
                "--encoder-backend", "pipe",
                "--codec", "h264",
                "--fps", str(FPS),
                "--rate-control", "qp",
                "--qp", "18",
                "-o", str(output),
            ],
            check=True,
            cwd=REPO,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    info = probe(output)
    if (info["width"], info["height"]) != (W, H):
        raise RuntimeError(f"{output.name}: expected 1920x1080, got {info['width']}x{info['height']}")
    if abs(info["duration"] - DURATION_S) > 0.15:
        raise RuntimeError(f"{output.name}: expected {DURATION_S:.2f}s, got {info['duration']:.2f}s")
    if info["nb_frames"] != FRAMES:
        raise RuntimeError(f"{output.name}: expected {FRAMES} frames, got {info['nb_frames']}")
    preview = PREVIEW / f"{slug}.png"
    decode_preview(output, preview)
    info.update(sha256=sha256(output), bytes=output.stat().st_size, preview=preview.name)
    return info


def contact_sheet(rendered: list[dict[str, Any]]) -> Path:
    thumb_w, thumb_h, gutter, label_h = 640, 360, 26, 54
    cols = 2
    rows = math.ceil(len(rendered) / cols)
    sheet = Image.new(
        "RGB",
        (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter),
        (18, 18, 20),
    )
    draw = ImageDraw.Draw(sheet)
    try:
        label_font = ImageFont.truetype(str(FONT_DIR / "Inter-SemiBold.ttf"), 24)
        small_font = ImageFont.truetype(str(FONT_DIR / "Inter-Light.ttf"), 17)
    except OSError:
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    for index, item in enumerate(rendered):
        col, row = index % cols, index // cols
        x = gutter + col * (thumb_w + gutter)
        y = gutter + row * (thumb_h + label_h + gutter)
        with Image.open(PREVIEW / item["preview"]) as frame:
            thumb = frame.convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS)
            sheet.paste(thumb, (x, y + label_h))
        draw.text((x, y + 4), item["name"], font=label_font, fill=(242, 242, 245))
        draw.text((x, y + 30), item["type"], font=small_font, fill=(168, 168, 176))
    path = OUT / "PHRASE_PRESET_FAMILIES_contact_sheet.png"
    sheet.save(path, optimize=True)
    return path


def drive_upload(path: Path, name: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            str(UPLOADER),
            "-credentials", str(CREDENTIALS),
            "-token", str(TOKEN),
            "-folder", DRIVE_FOLDER,
            "-subfolder", DRIVE_SUBFOLDER,
            "-file", str(path),
            "-name", name,
            "-sha256", sha256(path),
        ],
        check=True, text=True, capture_output=True,
    )
    line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    if "DRIVE_UPLOAD_PASS" not in line:
        raise RuntimeError(f"Drive did not verify upload for {path.name}: {line}")
    fields = dict(part.split("=", 1) for part in line.split() if "=" in part)
    return {"result": line, "drive_id": fields.get("id", ""), "link": fields.get("link", "")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit", action="store_true", help="emit and validate the ten plans")
    parser.add_argument("--render", action="store_true", help="render the validated plans")
    parser.add_argument("--upload", action="store_true", help="upload verified MP4s to Drive")
    parser.add_argument("--only", default="", help="restrict to one family slug prefix, e.g. 01")
    parser.add_argument("--sheet", action="store_true", help="rebuild the contact sheet from rendered previews")
    args = parser.parse_args()
    if not (args.emit or args.render or args.upload or args.sheet):
        args.emit = args.render = True

    for required in (CLI, FONT_DIR):
        if not required.exists():
            raise SystemExit(f"missing renderer prerequisite: {required}")

    selected = families()
    if args.only:
        selected = [family for family in selected if family["meta"]["slug"].startswith(args.only)]
        if not selected:
            raise SystemExit(f"no family matches --only {args.only!r}")

    for directory in (PLANS, MP4, PREVIEW, LOGS):
        directory.mkdir(parents=True, exist_ok=True)

    manifest_path = OUT / "manifest.json"

    if args.upload and not (args.emit or args.render):
        if not manifest_path.exists():
            raise SystemExit(f"no manifest to upload from: {manifest_path}")
        existing = json.loads(manifest_path.read_text())
        entries = sorted(
            (entry for entry in existing.get("families", [])
             if (OUT / entry.get("mp4", "")).is_file()
             and (not args.only or entry["slug"].startswith(args.only))),
            key=lambda entry: entry["slug"],
        )
        if not entries:
            raise SystemExit("no rendered MP4s found for upload")
        for required in (UPLOADER, CREDENTIALS, TOKEN):
            if not required.is_file():
                raise SystemExit(f"missing Drive prerequisite: {required}")
        for entry in entries:
            if entry.get("uploaded"):
                print(f"DRIVE_SKIP {entry['slug']}: already uploaded")
                continue
            path = OUT / entry["mp4"]
            name = f"PHRASE_PRESET_{entry['slug'].upper()}_1920x1080.mp4"
            result = drive_upload(path, name)
            entry.update(uploaded=True, drive_id=result["drive_id"], link=result["link"],
                         drive_name=name)
            print(f"DRIVE_PASS {entry['slug']}: {result['link']}")
        sheet_path = OUT / existing.get("contact_sheet", {}).get("path", "")
        if sheet_path.is_file() and not existing.get("contact_sheet", {}).get("uploaded"):
            result = drive_upload(sheet_path, "PHRASE_PRESET_FAMILIES_contact_sheet.png")
            existing["contact_sheet"].update(
                uploaded=True, drive_id=result["drive_id"], link=result["link"])
            print(f"DRIVE_PASS contact_sheet: {result['link']}")
        existing["drive"] = {"folder_id": DRIVE_FOLDER, "subfolder": DRIVE_SUBFOLDER}
        manifest_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = [
            "# Phrase preset families — 10 new looks",
            "",
            f"Drive: https://drive.google.com/drive/folders/{DRIVE_FOLDER}",
            "",
            "Tutti i video sono 1920×1080, 30 fps, 240 frame (8,00 s).",
            "",
            "| # | Famiglia | Tipo | Movimento | Video |",
            "|---|---|---|---|---|",
        ]
        for index, entry in enumerate(entries, start=1):
            link = f"[apri]({entry['link']})" if entry.get("link") else "—"
            lines.append(
                f"| {index:02d} | {entry['name']} | {entry['type']} | "
                f"{entry['motion']} | {link} |"
            )
        if existing.get("contact_sheet", {}).get("link"):
            lines += ["", f"Contact sheet: {existing['contact_sheet']['link']}"]
        (OUT / "UPLOAD-MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"UPLOADED {len(entries)} families to Drive {DRIVE_FOLDER}/{DRIVE_SUBFOLDER}")
        return 0

    manifest: dict[str, Any] = {
        "schema": "chronontemplate.phrase-preset-families.v1",
        "engine": "Chronon3D Vulkan lane (native text + color layers)",
        "canvas": {"width": W, "height": H, "fps": FPS, "frames": FRAMES, "duration_s": DURATION_S},
        "style_system": "paper/white base, near-black ink, one accent per family",
        "families": [],
        "drive": {"folder_id": DRIVE_FOLDER, "subfolder": DRIVE_SUBFOLDER},
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        manifest["families"] = previous.get("families", [])

    if args.sheet:
        if not manifest_path.exists():
            raise SystemExit(f"no manifest to rebuild a contact sheet from: {manifest_path}")
        existing = json.loads(manifest_path.read_text())
        entries = sorted(
            (entry for entry in existing.get("families", [])
             if (PREVIEW / entry.get("preview", "")).is_file()),
            key=lambda entry: entry["slug"],
        )
        if not entries:
            raise SystemExit("no rendered previews found for the contact sheet")
        sheet = contact_sheet(entries)
        existing["contact_sheet"] = {
            "path": sheet.name, "bytes": sheet.stat().st_size, "sha256": sha256(sheet),
        }
        manifest_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"CONTACT_SHEET {sheet} ({len(entries)} families)")
        return 0

    emitted: list[tuple[dict[str, Any], Path]] = []
    for family in selected:
        meta = family["meta"]
        plan = make_plan(family)
        path = PLANS / f"{meta['slug']}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        validate(path)
        emitted.append((family, path))
        print(f"PLAN_VALID {meta['slug']}: {path.name}")

    if args.emit and not args.render:
        print(f"emitted {len(emitted)} plans in {PLANS}")
        return 0

    rendered: list[dict[str, Any]] = []
    for family, plan in emitted:
        meta = family["meta"]
        output = MP4 / f"{meta['slug']}.mp4"
        print(f"RENDER_START {meta['slug']}")
        info = render_one(meta["slug"], plan, output)
        entry = {
            **meta,
            "bg": family["bg"],
            "phrase": family["phrase"],
            "plan": f"plans/{plan.name}",
            "mp4": f"mp4/{output.name}",
            "preview": info["preview"],
            "width": info["width"],
            "height": info["height"],
            "frames": info["nb_frames"],
            "duration_s": round(info["duration"], 3),
            "sha256": info["sha256"],
            "bytes": info["bytes"],
            "uploaded": False,
        }
        rendered.append(entry)
        print(f"RENDER_PASS {meta['slug']}: {info['width']}x{info['height']} "
              f"{info['duration']:.2f}s {info['bytes']} bytes")

    sheet = contact_sheet(rendered) if rendered else None
    manifest["families"] = rendered + [
        item for item in manifest.get("families", [])
        if item.get("slug") not in {entry["slug"] for entry in rendered}
    ]
    if sheet:
        manifest["contact_sheet"] = {
            "path": sheet.name,
            "bytes": sheet.stat().st_size,
            "sha256": sha256(sheet),
        }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.upload:
        for required in (UPLOADER, CREDENTIALS, TOKEN):
            if not required.is_file():
                raise SystemExit(f"missing Drive prerequisite: {required}")
        for entry in rendered:
            path = MP4 / f"{entry['slug']}.mp4"
            name = f"PHRASE_PRESET_{entry['slug'].upper()}_1920x1080.mp4"
            result = drive_upload(path, name)
            entry.update(uploaded=True, drive_id=result["drive_id"], link=result["link"],
                         drive_name=name)
            print(f"DRIVE_PASS {entry['slug']}: {result['link']}")
        if sheet:
            result = drive_upload(sheet, "PHRASE_PRESET_FAMILIES_contact_sheet.png")
            manifest["contact_sheet"].update(
                uploaded=True, drive_id=result["drive_id"], link=result["link"])
            print(f"DRIVE_PASS contact_sheet: {result['link']}")
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"MANIFEST {manifest_path} ({len(rendered)} families)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"PHRASE_PRESET_FAMILIES_FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
