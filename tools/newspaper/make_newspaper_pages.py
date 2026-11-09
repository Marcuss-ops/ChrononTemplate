#!/usr/bin/env python3
"""LEGACY FALLBACK — the C++ composer (make_newspaper_pages.cpp) is canonical.

Compose the four Linux-native newspaper pages as 1920x1080 PNGs.

The Chronon text layer path in this CLI build composites below the paper
shapes and uses a different position convention from shapes.  The newspaper
family therefore bakes the editorial layout (type, rules, photo, stamp) into
one image per scene, which Chronon animates as a screen-space image layer.
The only live overlays are the highlighter bands and the redaction bars; their
rectangles are measured here and written to meta.json so the plan emitter and
the page art cannot drift apart.

Outputs:
    assets/newspaper/pages/{front_page,dossier,highlighter,memo}.png
    assets/newspaper/pages/meta.json

No browser, no Blend2D, no Windows paths.  Pillow is the same dependency the
old setup used for its paper assets; Chronon still owns the animation and the
video encode.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts"
OUT_DIR = ROOT / "assets" / "newspaper" / "pages"
W, H = 1920, 1080

INK = "#1D1B18"
INK_SOFT = "#383530"
MUTED = "#6B665D"
MUTED_LIGHT = "#807A70"
PAPER = "#F6F1E4"
PAPER_COOL = "#F7F4EA"
DESK = "#C8C5BC"
RULE = "#A9A296"
RED = "#A23B32"
BLUE = "#2755A8"
YELLOW = "#FFE22A"


@lru_cache(maxsize=None)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def rgb(hex_color: str) -> tuple[int, int, int]:
    return ImageColor.getrgb(hex_color)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    face: ImageFont.FreeTypeFont,
    fill: str,
    tracking: float = 0.0,
    anchor: str = "lt",
) -> None:
    """Draw letter-spaced text, preserving the requested horizontal anchor."""
    widths = [draw.textlength(ch, font=face) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for ch, width in zip(text, widths):
        draw.text((x, y), ch, font=face, fill=fill, anchor="l" + anchor[1])
        x += width + tracking


def rule(draw: ImageDraw.ImageDraw, x0: float, y: float, x1: float,
         color: str = RULE, width: int = 1) -> None:
    draw.line((x0, y, x1, y), fill=color, width=width)


def desk_background(hex_color: str = DESK) -> Image.Image:
    """A quietly graded, slightly dusty desk surface."""
    base = np.array(rgb(hex_color), dtype=np.float32)
    top = np.clip(base + 14, 0, 255)
    bottom = np.clip(base - 12, 0, 255)
    grad = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    arr = top[None, None, :] * (1.0 - grad) + bottom[None, None, :] * grad
    arr = np.broadcast_to(arr, (H, W, 3)).copy()
    rng = np.random.default_rng(1979)
    arr += rng.normal(0.0, 2.6, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W]
    radius = ((xx - W / 2) ** 2) / (W / 2) ** 2 + ((yy - H / 2) ** 2) / (H / 2) ** 2
    vignette = 1.0 - 0.10 * np.clip(radius - 0.35, 0.0, 1.0)
    arr *= vignette[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def paper_sheet(im: Image.Image, box: tuple[int, int, int, int],
                fill: str = PAPER) -> None:
    x0, y0, x1, y1 = box
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((x0 + 15, y0 + 19, x1 + 15, y1 + 19), fill=(24, 21, 17, 110))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(17)))
    draw = ImageDraw.Draw(im)
    draw.rectangle(box, fill=fill, outline="#D9D2C2", width=1)
    draw.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill="#FFFDF7", width=1)
    # A faint foxing/fibre layer keeps the sheet from looking like flat vector.
    rng = np.random.default_rng(x0 * 31 + y0)
    fibers = Image.new("RGBA", im.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fibers)
    for _ in range(90):
        fx = int(rng.integers(x0 + 10, x1 - 10))
        fy = int(rng.integers(y0 + 10, y1 - 10))
        length = int(rng.integers(4, 22))
        alpha = int(rng.integers(4, 11))
        fd.line((fx, fy, fx + length, fy + int(rng.integers(-1, 2))),
                fill=(120, 108, 84, alpha), width=1)
    im.alpha_composite(fibers)


def paste_photo(im: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    tw, th = x1 - x0, y1 - y0
    source = Image.open(ROOT / "assets" / "newspaper" / "front_page_photo.jpg").convert("L")
    source = ImageOps.autocontrast(source, cutoff=1)
    scale = max(tw / source.width, th / source.height)
    source = source.resize((max(1, int(source.width * scale) + 1),
                            max(1, int(source.height * scale) + 1)),
                           Image.LANCZOS)
    left = (source.width - tw) // 2
    top = (source.height - th) // 2
    source = source.crop((left, top, left + tw, top + th)).convert("RGB")
    # Warm the greys slightly toward the paper, like a letterpress halftone.
    arr = np.asarray(source, dtype=np.float32)
    arr[..., 0] *= 1.03
    arr[..., 2] *= 0.96
    source = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    im.paste(source, (x0, y0))
    draw = ImageDraw.Draw(im)
    draw.rectangle(box, outline="#3B3833", width=2)


def stamp(im: Image.Image, box: tuple[int, int, int, int], text: str,
          angle: float = -5.0, color: str = RED) -> None:
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle(box, outline=color, width=4)
    draw.text(((x0 + x1) / 2, (y0 + y1) / 2), text,
              font=font("Inter-Bold.ttf", 17), fill=color, anchor="mm")
    layer = layer.rotate(angle, resample=Image.BICUBIC,
                         center=((x0 + x1) / 2, (y0 + y1) / 2))
    im.alpha_composite(layer)


def ink_rect(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
             face: ImageFont.FreeTypeFont, anchor: str = "lt",
             pad_x: int = 8, pad_y: int = 5) -> list[int]:
    x0, y0, x1, y1 = draw.textbbox(xy, text, font=face, anchor=anchor)
    return [int(round(x0 - pad_x)), int(round(y0 - pad_y)),
            int(round(x1 - x0 + 2 * pad_x)), int(round(y1 - y0 + 2 * pad_y))]


# ── 01. Front page ───────────────────────────────────────────────────────────
def front_page() -> tuple[Image.Image, dict]:
    im = desk_background(DESK)
    paper_sheet(im, (150, 86, 1770, 1000), PAPER)
    d = ImageDraw.Draw(im)

    draw_tracked(d, (210, 120), "THE CHRONON JOURNAL  ·  SECTION D  ·  SUNDAY EDITION",
                 font("Inter-Bold.ttf", 15), MUTED, 2.6)
    d.text((960, 146), "Science Times", font=font("PlayfairDisplay-Bold.ttf", 106),
           fill=INK, anchor="mt")
    rule(d, 210, 274, 1710, RULE, 2)
    d.text((960, 284), "TUESDAY, OCTOBER 19, 2026  ·  SCIENCE DESK  ·  WASHINGTON, D.C.",
           font=font("Inter-Medium.ttf", 15), fill="#4A4741", anchor="mt")
    rule(d, 210, 316, 1710, "#2A2824", 4)

    d.text((210, 350), "THE MEN WHO", font=font("PlayfairDisplay-Bold.ttf", 92),
           fill=INK, anchor="lt")
    d.text((210, 442), "STARED AT GOATS", font=font("PlayfairDisplay-Bold.ttf", 92),
           fill=INK, anchor="lt")
    d.text((210, 572),
           "Inside the Pentagon's psychic-spy program — and the",
           font=font("PlayfairDisplay-Italic.ttf", 31), fill=INK_SOFT, anchor="lt")
    d.text((210, 610),
           "paper trail that refused to disappear.",
           font=font("PlayfairDisplay-Italic.ttf", 31), fill=INK_SOFT, anchor="lt")
    d.text((210, 660), "BY ELENA MARSH  ·  WASHINGTON, D.C.",
           font=font("Inter-Bold.ttf", 14), fill="#5A554E", anchor="lt")
    rule(d, 210, 692, 1050, "#8E897F", 1)

    paste_photo(im, (1110, 350, 1710, 690))
    d.text((1110, 700), "A declassified training room, photographed for the archive in 1983.",
           font=font("PlayfairDisplay-Italic.ttf", 16), fill="#504C45", anchor="lt")
    d.text((1110, 724), "PHOTO: CHRONON VISUAL LAB / ARCHIVE",
           font=font("Inter-Medium.ttf", 11), fill="#7A746B", anchor="lt")

    columns = [
        [
            "For nearly two decades, a small group of",
            "intelligence officers argued that the human",
            "mind could be trained to see across oceans.",
            "The program began with a simple question:",
            "if attention can be focused, can it also be",
            "projected? Files released this month show",
            "that the answer was never settled. What",
            "survived was the paperwork.",
        ],
        [
            "Reviewers described a revolving door of",
            "contractors, retired officers and self-taught",
            "psychics. Each brought a different vocabulary",
            "for the same claim: that distance was a detail,",
            "not a limit. Funding continued through the",
            "1980s, even as internal reports warned that",
            "results could not be repeated outside the lab.",
            "The archive kept growing anyway.",
        ],
        [
            "Historians say the file is valuable less for",
            "what it proves than for what it records: the",
            "confidence of institutions, the fragility of",
            "evidence, and the long afterlife of a secret.",
            "The final memo is dated 1987. Its last line is",
            "a request for more time. The request was",
            "denied, but the pages were never destroyed.",
            "They were simply moved to another box.",
        ],
    ]
    for i, lines in enumerate(columns):
        x = 210 + i * 480
        for j, line in enumerate(lines):
            d.text((x, 760 + j * 23), line, font=font("PlayfairDisplay.ttf", 17),
                   fill=INK_SOFT, anchor="lt")
    for x in (675, 1155):
        d.line((x, 750, x, 940), fill="#B9B1A2", width=1)
    rule(d, 210, 958, 1710, "#8E897F", 1)
    d.text((210, 968), "D1  ·  CHRONON JOURNAL  ·  ALL RIGHTS RESERVED",
           font=font("Inter-Medium.ttf", 11), fill="#6B665D", anchor="lt")
    d.text((1710, 968), "PAGE 01", font=font("Inter-Bold.ttf", 11),
           fill="#6B665D", anchor="rt")
    return im, {"duration": 180, "markers": [], "redactions": []}


# ── 02. Dossier close-up ─────────────────────────────────────────────────────
def dossier() -> tuple[Image.Image, dict]:
    im = desk_background("#C6C3BA")
    paper_sheet(im, (250, 70, 1670, 1010), "#F3EFE3")
    d = ImageDraw.Draw(im)

    draw_tracked(d, (330, 122), "ARCHIVE  /  RESEARCH NOTE 1979",
                 font("Inter-Bold.ttf", 16), "#6B6862", 2.2)
    rule(d, 330, 158, 1450, "#8B877F", 2)

    d.text((330, 196), "... Project.", font=font("PlayfairDisplay.ttf", 58),
           fill="#5D5B57", anchor="lt")
    d.text((330, 280), "primarily involved", font=font("PlayfairDisplay.ttf", 58),
           fill="#5D5B57", anchor="lt")
    focus_face = font("PlayfairDisplay-Bold.ttf", 74)
    d.text((330, 378), "remote viewing", font=focus_face, fill=BLUE, anchor="lt")
    marker = ink_rect(d, (330, 378), "remote viewing", focus_face, pad_x=14, pad_y=9)

    d.text((330, 504), "Project was overseen until 1987",
           font=font("PlayfairDisplay.ttf", 46), fill="#5D5B57", anchor="lt")
    d.text((330, 588), "Albert Stubblebine",
           font=font("PlayfairDisplay-Bold.ttf", 56), fill="#6D6861", anchor="lt")
    d.text((330, 664), "former head of the Defense",
           font=font("PlayfairDisplay.ttf", 42), fill="#5D5B57", anchor="lt")
    d.text((330, 718), "Intelligence Agency",
           font=font("PlayfairDisplay.ttf", 42), fill="#5D5B57", anchor="lt")

    left_notes = [
        "Records released under the",
        "declassification review show",
        "a long-running program that",
        "trained viewers to describe",
        "distant locations from a",
        "controlled room. The file",
        "contains interviews, session",
        "notes and administrative",
        "memos spanning more than",
        "a decade of work.",
    ]
    right_notes = [
        "Funding was renewed each",
        "year despite mixed results.",
        "Reviewers noted that the",
        "program produced few",
        "reliable leads and that",
        "independent replication",
        "remained difficult. The",
        "archive copy is incomplete;",
        "several pages are marked",
        "as withheld.",
    ]
    for x, notes in ((330, left_notes), (940, right_notes)):
        for i, line in enumerate(notes):
            d.text((x, 790 + i * 18), line, font=font("PlayfairDisplay.ttf", 15),
                   fill="#77736C", anchor="lt")
    rule(d, 330, 972, 1450, "#8B877F", 1)
    d.text((330, 982), "DECLASSIFIED  /  ARCHIVE COPY  /  PAGE 12 OF 29",
           font=font("Inter-Medium.ttf", 11), fill="#6B6862", anchor="lt")
    d.text((1450, 982), "PAGE 12", font=font("Inter-Bold.ttf", 11),
           fill="#6B6862", anchor="rt")

    stamp(im, (1352, 116, 1592, 174), "DECLASSIFIED", angle=-4.5)
    return im, {
        "duration": 150,
        "markers": [{
            "id": "dossier_marker",
            "rect": marker,
            "delay": 34,
            "span": 40,
            "peak": 0.30,
        }],
        "redactions": [],
    }


# ── 03. Highlighter sweep clipping ───────────────────────────────────────────
def highlighter() -> tuple[Image.Image, dict]:
    im = desk_background("#C7C4BB")
    paper_sheet(im, (220, 200, 1700, 880), PAPER_COOL)
    d = ImageDraw.Draw(im)

    draw_tracked(d, (960, 250), "CONTEMPORARY PRESS  /  ARCHIVE CLIPPING",
                 font("Inter-Bold.ttf", 15), "#6B665D", 2.6, anchor="mt")
    rule(d, 310, 286, 1610, "#A7A199", 1)

    big = font("PlayfairDisplay.ttf", 54)
    d.text((960, 338), "Over the years more than 20", font=big,
           fill="#2C2A27", anchor="mt")
    d.text((960, 402), "psychics were employed.", font=big,
           fill="#2C2A27", anchor="mt")
    mid = font("PlayfairDisplay.ttf", 36)
    d.text((960, 492), "some ended up in psychiatric hospitals,",
           font=mid, fill="#5E5B56", anchor="mt")
    d.text((960, 540), "others lost the plot ...", font=mid,
           fill="#5E5B56", anchor="mt")
    d.text((960, 620), "obsessed with crop circles and aliens.",
           font=font("PlayfairDisplay-Italic.ttf", 36), fill="#5E5B56", anchor="mt")
    d.text((960, 700), "— filed by the science desk, undated",
           font=font("PlayfairDisplay-Italic.ttf", 18), fill="#77736C", anchor="mt")

    rule(d, 310, 790, 1610, "#A7A199", 1)
    d.text((310, 806), "FIG. 04  ·  PRESS CLIPPING, UNDATED",
           font=font("Inter-Medium.ttf", 11), fill="#6B665D", anchor="lt")
    d.text((1610, 806), "SOURCE: CHRONON ARCHIVE",
           font=font("Inter-Medium.ttf", 11), fill="#6B665D", anchor="rt")

    marker_1 = ink_rect(d, (960, 402), "psychics were employed.", big,
                        anchor="mt", pad_x=14, pad_y=8)
    marker_2 = ink_rect(d, (960, 620), "crop circles and aliens.",
                        font("PlayfairDisplay-Italic.ttf", 36),
                        anchor="mt", pad_x=12, pad_y=7)
    return im, {
        "duration": 150,
        "markers": [
            {"id": "sweep_marker_1", "rect": marker_1, "delay": 34,
             "span": 42, "peak": 0.62},
            {"id": "sweep_marker_2", "rect": marker_2, "delay": 82,
             "span": 34, "peak": 0.52},
        ],
        "redactions": [],
    }


# ── 04. Declassified memo ────────────────────────────────────────────────────
def memo() -> tuple[Image.Image, dict]:
    im = desk_background("#C4C1B8")
    paper_sheet(im, (230, 80, 1690, 1000), "#F5F1E5")
    d = ImageDraw.Draw(im)

    draw_tracked(d, (960, 126), "DEPARTMENT OF DEFENSE",
                 font("Inter-Bold.ttf", 26), "#2E2B27", 2.2, anchor="mt")
    d.text((960, 168), "DECLASSIFIED  ·  ARCHIVE COPY",
           font=font("Inter-Medium.ttf", 15), fill="#6B665D", anchor="mt")
    stamp(im, (1390, 126, 1640, 184), "DECLASSIFIED", angle=-4.0)
    rule(d, 330, 208, 1590, "#8B877F", 2)

    mono = font("LiberationMono-Bold.ttf", 34)
    body_lines = [
        "The program was reviewed in",
        "years 1983 and 1984 by the",
        "former head of the Defense",
        "Intelligence Agency.",
    ]
    for i, line in enumerate(body_lines):
        d.text((330, 258 + i * 52), line, font=mono, fill=INK_SOFT, anchor="lt")

    date_rect = ink_rect(d, (330, 310), "years 1983 and 1984", mono,
                         pad_x=8, pad_y=5)

    d.text((330, 560), "Selected phrases remain",
           font=font("PlayfairDisplay.ttf", 44), fill=INK_SOFT, anchor="lt")
    d.text((330, 614), "redacted in this copy.",
           font=font("PlayfairDisplay.ttf", 44), fill=INK_SOFT, anchor="lt")

    d.text((1120, 754), "REDACTED", font=font("Inter-Bold.ttf", 13),
           fill="#8B2F28", anchor="lt")
    # The bars are live Chronon shapes at these page coordinates.
    d.text((1120, 866), "SOURCE AND METHOD WITHHELD",
           font=font("Inter-Medium.ttf", 12), fill="#6B665D", anchor="lt")

    rule(d, 330, 954, 1590, "#8B877F", 1)
    d.text((330, 966), "ARCHIVE  /  BOX 14  /  FOLDER 03  /  PAGE 07",
           font=font("Inter-Medium.ttf", 11), fill="#6B665D", anchor="lt")
    d.text((1590, 966), "PAGE 07", font=font("Inter-Bold.ttf", 11),
           fill="#6B665D", anchor="rt")

    return im, {
        "duration": 150,
        "markers": [{
            "id": "memo_date_marker",
            "rect": date_rect,
            "delay": 38,
            "span": 40,
            "peak": 0.52,
        }],
        "redactions": [
            {"id": "memo_redaction_1", "rect": [1120, 788, 330, 26],
             "delay": 22, "span": 8},
            {"id": "memo_redaction_2", "rect": [1120, 824, 240, 26],
             "delay": 28, "span": 8},
        ],
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict[str, dict] = {}
    for name, builder in (
        ("front_page", front_page),
        ("dossier", dossier),
        ("highlighter", highlighter),
        ("memo", memo),
    ):
        image, scene_meta = builder()
        image = image.convert("RGB")
        path = OUT_DIR / f"{name}.png"
        image.save(path, optimize=True)
        scene_meta["asset"] = f"assets/newspaper/pages/{name}.png"
        meta[name] = scene_meta
        print(f"wrote {path} ({image.width}x{image.height})")
    meta_path = OUT_DIR / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {meta_path}")


if __name__ == "__main__":
    main()
