#!/usr/bin/env python3
"""Bake the visual assets for the object_stage scene.

Everything that used to be a 3D text layer (card names, title, kicker) is
composited here into PNGs.  The renderer then only deals with images, which
keeps typography pixel-perfect and avoids the 3D text layout quirks.

Outputs (in ChrononTemplate/assets/object_stage_v1/):
  desk_bg_v2.png   3840x2160 dark desk with paper ghosts, dust and vignette
  card_ada.png     dossier card, Ada Lovelace
  card_curie.png   dossier card, Marie Curie
  card_tesla.png   dossier card, Nikola Tesla
  title_overlay.png  1920x1080 transparent title / frame / vignette
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets/object_stage_v1"
FONTS = ROOT / "assets/fonts"

SERIF = FONTS / "PlayfairDisplay-Bold.ttf"
SANS = FONTS / "Inter-SemiBold.ttf"
SANS_MED = FONTS / "Inter-Medium.ttf"
SANS_REG = FONTS / "Inter-Regular.ttf"

GOLD = (200, 162, 74)
IVORY = (244, 239, 227)
MUTED = (140, 130, 108)
INK_TOP = (18, 23, 33)
INK_BOTTOM = (7, 10, 15)

CARD_W, CARD_H = 1000, 1300
CARD_INSET = 30
CARD_RADIUS = 56

random.seed(7)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def tracked(draw: ImageDraw.ImageDraw, xy, text: str, fnt, fill,
            tracking: float = 0.0, anchor_center: bool = True) -> None:
    """Draw text with letter spacing; optionally centred on xy."""
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2.0
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="ls")
        x += w + tracking


def vertical_gradient(size, top, bottom) -> Image.Image:
    w, h = size
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        arr[:, :, c] = top[c] * (1 - t) + bottom[c] * t
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")


def add_grain(img: Image.Image, amount: float = 5.0) -> Image.Image:
    noise = np.random.default_rng(11).normal(0, amount, (img.height, img.width, 1))
    arr = np.asarray(img).astype(np.float32) + noise
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), img.mode)


def clean_alpha(img: Image.Image) -> Image.Image:
    """Drop tiny detached islands left by background removal."""
    try:
        from scipy import ndimage
    except Exception:
        return img
    alpha = np.asarray(img.split()[3])
    labels, count = ndimage.label(alpha > 12)
    if count <= 1:
        return img
    sizes = ndimage.sum(alpha > 12, labels, range(1, count + 1))
    largest = sizes.max()
    keep = np.zeros_like(alpha)
    for idx, size in enumerate(sizes, start=1):
        if size >= largest * 0.012:
            keep[labels == idx] = 255
    out = img.copy()
    out.putalpha(Image.fromarray(np.minimum(alpha, keep).astype(np.uint8)))
    return out


def load_portrait(name: str, target_h: int, max_w: int) -> Image.Image:
    src = Image.open(ASSETS / f"{name}.png").convert("RGBA")
    src = clean_alpha(src)
    if name == "ada_lovelace":
        # the archival plate is full-length; crop to a bust so the face reads
        src = src.crop((0, 0, src.width, int(src.height * 0.72)))
    w, h = src.size
    scale = min(target_h / h, max_w / w)
    src = src.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)

    # warm archival duotone, keep the alpha
    alpha = src.split()[3]
    grey = ImageOps.grayscale(src)
    grey = ImageOps.autocontrast(grey, cutoff=0.4)
    tinted = ImageOps.colorize(grey, black=(9, 11, 14), mid=(118, 110, 95), white=(247, 240, 226))
    tinted = tinted.convert("RGBA")
    tinted.putalpha(alpha)
    return tinted


def rounded_mask(size, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


# --------------------------------------------------------------------------
# card
# --------------------------------------------------------------------------

def build_card(subject: str, display: str, dates: str, index: str, role: str) -> Image.Image:
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    card_box = (CARD_INSET, CARD_INSET, CARD_W - CARD_INSET, CARD_H - CARD_INSET)
    card_size = (card_box[2] - card_box[0], card_box[3] - card_box[1])

    # card body: dark navy vertical gradient + warm pool of light at the top
    body = vertical_gradient(card_size, INK_TOP, INK_BOTTOM).convert("RGBA")
    warm = Image.new("RGBA", card_size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(warm)
    wd.ellipse((-card_size[0] * 0.25, -card_size[1] * 0.45,
                card_size[0] * 1.25, card_size[1] * 0.62),
               fill=(116, 87, 46, 54))
    warm = warm.filter(ImageFilter.GaussianBlur(90))
    body = Image.alpha_composite(body, warm)

    mask = rounded_mask(card_size, CARD_RADIUS)
    body.putalpha(mask)
    canvas.alpha_composite(body, (card_box[0], card_box[1]))

    # portrait, placed in the upper two thirds; crops are normalised by subject
    crop = {
        "ada_lovelace": (700, 660, 152),
        "marie_curie": (760, 620, 150),
        "nikola_tesla": (690, 560, 178),
    }.get(subject, (760, 700, 150))
    portrait = load_portrait(subject, target_h=crop[0], max_w=crop[1])
    px = card_box[0] + (card_size[0] - portrait.width) // 2
    py = card_box[1] + crop[2]
    alpha = portrait.split()[3]

    # soft warm bloom behind the silhouette
    glow = Image.new("RGBA", portrait.size, (0, 0, 0, 0))
    glow.putalpha(alpha.filter(ImageFilter.GaussianBlur(26)).point(lambda a: int(a * 0.42)))
    glow = Image.composite(Image.new("RGBA", portrait.size, (255, 196, 110, 255)),
                           Image.new("RGBA", portrait.size, (0, 0, 0, 0)),
                           glow.split()[3])
    canvas.alpha_composite(glow, (px - 14, py - 8))

    # contact shadow under the cut-out, kept inside the card
    shadow = Image.new("RGBA", portrait.size, (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(22)).point(lambda a: int(a * 0.60)))
    canvas.alpha_composite(shadow, (px + 6, py + 16))

    canvas.alpha_composite(portrait, (px, py))

    # lower scrim so the caption reads over the torso
    scrim = Image.new("L", (1, card_size[1]), 0)
    for y in range(card_size[1]):
        t = max(0.0, min(1.0, (y - 720) / 430.0))
        scrim.putpixel((0, y), int(215 * (t ** 1.5)))
    scrim = scrim.resize(card_size)
    scrim = Image.composite(scrim, Image.new("L", card_size, 0), mask)
    scrim_rgba = Image.new("RGBA", card_size, (3, 4, 6, 255))
    scrim_rgba.putalpha(scrim)
    canvas.alpha_composite(scrim_rgba, (card_box[0], card_box[1]))

    draw = ImageDraw.Draw(canvas)

    # gold frame + inner hairline
    draw.rounded_rectangle(card_box, CARD_RADIUS, outline=(*GOLD, 225), width=4)
    inner = (card_box[0] + 14, card_box[1] + 14, card_box[2] - 14, card_box[3] - 14)
    draw.rounded_rectangle(inner, CARD_RADIUS - 12, outline=(255, 226, 168, 30), width=1)

    # archive header
    tracked(draw, (card_box[0] + 46, card_box[1] + 62), "ARCHIVIO", font(SANS, 27),
            (*GOLD, 215), tracking=6, anchor_center=False)
    tracked(draw, (card_box[0] + 46, card_box[1] + 96), "RITRATTI / MMXXVI",
            font(SANS_REG, 21), (170, 158, 132, 190), tracking=3, anchor_center=False)

    # index at the top right
    idx_font = font(SERIF, 54)
    draw.text((card_box[2] - 50, card_box[1] + 58), index, font=idx_font,
              fill=(*GOLD, 120), anchor="ra")

    # caption block: hairline, name, role, years
    line_y = 900
    draw.line((card_box[0] + 56, line_y, card_box[2] - 56, line_y),
              fill=(*GOLD, 170), width=2)

    draw.text(((CARD_W) // 2, 932), display, font=font(SERIF, 64),
              fill=(*IVORY, 255), anchor="ma")

    tracked(draw, (CARD_W // 2, 1042), role, font(SANS_REG, 24),
            (*GOLD, 215), tracking=5)

    tracked(draw, (CARD_W // 2, 1104), dates, font(SANS_MED, 30),
            (184, 170, 142, 235), tracking=5)

    # a hair of film grain over the whole card
    grain = Image.effect_noise((CARD_W, CARD_H), 9).convert("L")
    grain_rgba = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, 255))
    grain_rgba.putalpha(grain.point(lambda a: int(abs(a - 128) * 0.16)))
    canvas = Image.alpha_composite(canvas, Image.composite(
        grain_rgba, Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0)),
        canvas.split()[3]))

    # bake the glow and the two-level shadow into the PNG: the per-frame blur
    # passes were the dominant cost of the software render.
    pad_x, pad_top, pad_bottom = 80, 100, 100
    out = Image.new("RGBA", (CARD_W + 2 * pad_x, CARD_H + pad_top + pad_bottom),
                    (0, 0, 0, 0))
    card_alpha = canvas.split()[3]
    alpha_layer = Image.new("L", out.size, 0)
    alpha_layer.paste(card_alpha, (pad_x, pad_top))

    def halo(color, blur, opacity, offset):
        a = alpha_layer.filter(ImageFilter.GaussianBlur(blur)).point(
            lambda v: int(v * opacity))
        layer = Image.new("RGBA", out.size, (*color, 255))
        layer.putalpha(a)
        return layer, offset

    for layer, offset in [
        halo((255, 198, 112), 28, 0.20, (0, 10)),
        halo((0, 0, 0), 46, 0.62, (0, 36)),
        halo((0, 0, 0), 12, 0.52, (0, 8)),
    ]:
        out.alpha_composite(layer, (offset[0], offset[1]))
    out.alpha_composite(canvas, (pad_x, pad_top))
    return out


# --------------------------------------------------------------------------
# desk
# --------------------------------------------------------------------------

def build_desk() -> Image.Image:
    W, H = 3840, 2160
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W * 0.5) / (W * 0.5)
    ny = (yy - H * 0.52) / (H * 0.52)
    r = np.sqrt(nx ** 2 + (ny * 0.82) ** 2)
    light = np.clip(1.0 - r, 0.0, 1.0) ** 1.7

    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:, :, 0] = 6 + 52 * light
    base[:, :, 1] = 7 + 43 * light
    base[:, :, 2] = 9 + 30 * light

    # a warm pool of light behind the three cards
    gx = (xx - W * 0.5) / (W * 0.30)
    gy = (yy - H * 0.36) / (H * 0.26)
    pool = np.exp(-(gx ** 2 + gy ** 2) * 1.3)
    base[:, :, 0] += 38 * pool
    base[:, :, 1] += 28 * pool
    base[:, :, 2] += 16 * pool

    img = Image.fromarray(base.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # ghost papers on the desk, heavily out of focus
    papers = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(papers)
    for cx, cy, w, h, ang, a in [
        (0.13, 0.22, 0.24, 0.30, 18, 26), (0.86, 0.18, 0.20, 0.28, -24, 22),
        (0.08, 0.80, 0.26, 0.30, -14, 30), (0.93, 0.78, 0.24, 0.32, 12, 24),
        (0.70, 0.88, 0.18, 0.20, 5, 18),
    ]:
        box = ((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H)
        tile = Image.new("RGBA", (int(box[2] - box[0]), int(box[3] - box[1])), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        d.rounded_rectangle((0, 0, tile.width - 1, tile.height - 1), 26,
                            fill=(36, 33, 28, a), outline=(120, 100, 66, a // 2), width=3)
        tile = tile.rotate(ang, expand=True, resample=Image.BICUBIC)
        papers.alpha_composite(tile, (int(box[0]), int(box[1])))
    papers = papers.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, papers)

    # a faint archive circle and centre line behind the cast
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, int(H * 0.40)
    for radius, a in [(420, 22), (520, 12)]:
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     outline=(200, 162, 74, a), width=2)
    draw.line((cx, cy - 980, cx, cy + 980), fill=(200, 162, 74, 10), width=2)

    # paper fibres and scratches
    for _ in range(90):
        y = random.uniform(0, H)
        x = random.uniform(-200, W)
        length = random.uniform(80, 900)
        a = random.randint(4, 13)
        draw.line((x, y, x + length, y + random.uniform(-6, 6)),
                  fill=(220, 205, 180, a), width=random.choice([1, 1, 2]))
    img = img.filter(ImageFilter.GaussianBlur(0.6))

    # dust motes, some in focus, some blooming
    for _ in range(240):
        x, y = random.uniform(0, W), random.uniform(0, H)
        rr = random.choice([1, 1, 2, 2, 3])
        a = random.randint(8, 38)
        dot = Image.new("RGBA", (rr * 12, rr * 12), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse((rr * 6 - rr, rr * 6 - rr, rr * 6 + rr, rr * 6 + rr),
                                    fill=(235, 215, 175, a))
        if rr >= 2:
            dot = dot.filter(ImageFilter.GaussianBlur(rr * 1.2))
        img.alpha_composite(dot, (int(x), int(y)))

    # vignette
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    vig = np.clip(1.15 - 0.55 * (r ** 2), 0.35, 1.0)[:, :, None]
    arr = arr * vig
    arr = arr + np.random.default_rng(5).normal(0, 2.2, (H, W, 1))
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------
# title overlay
# --------------------------------------------------------------------------

def build_title() -> Image.Image:
    W, H = 1920, 1080
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # static grade: top and bottom falloff + soft corner vignette
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    top = np.clip((420 - np.arange(H)) / 420, 0, 1) ** 1.6 * 150
    bottom = np.clip((np.arange(H) - 820) / 260, 0, 1) ** 1.4 * 150
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    vig = np.clip((np.sqrt(nx ** 2 + ny ** 2) - 0.55) / 0.75, 0, 1) ** 1.4 * 86
    alpha = np.clip(top[:, None] + bottom[:, None] + vig, 0, 255)
    arr[:, :, 0] = 4
    arr[:, :, 1] = 5
    arr[:, :, 2] = 7
    arr[:, :, 3] = alpha.astype(np.uint8)
    img = Image.alpha_composite(img, Image.fromarray(arr, "RGBA"))

    draw = ImageDraw.Draw(img)

    # thin frame with corner ticks
    inset = 34
    draw.rectangle((inset, inset, W - inset, H - inset), outline=(200, 162, 74, 34), width=1)
    tick = 44
    for x, y, dx, dy in [(inset, inset, 1, 1), (W - inset, inset, -1, 1),
                         (inset, H - inset, 1, -1), (W - inset, H - inset, -1, -1)]:
        draw.line((x, y, x + dx * tick, y), fill=(200, 162, 74, 110), width=2)
        draw.line((x, y, x, y + dy * tick), fill=(200, 162, 74, 110), width=2)

    # kicker
    tracked(draw, (W // 2, 56), "UN ARCHIVIO IN TRE RITRATTI", font(SANS, 20),
            (*GOLD, 235), tracking=8)

    # single-line title: it must end above the card tops (~210 px)
    title_font = font(SERIF, 72)
    draw.text((W // 2, 126), "LE MENTI CHE HANNO CAMBIATO IL MONDO", font=title_font,
              fill=(*IVORY, 255), anchor="mm")
    draw.line((W // 2 - 110, 178, W // 2 + 110, 178), fill=(*GOLD, 170), width=2)

    # footer
    footer_font = font(SANS_REG, 19)
    tracked(draw, (96, 1024), "CHRONON  ·  OBJECT STAGE  /  V1", footer_font,
            (*MUTED, 235), tracking=4, anchor_center=False)
    right_text = "1920 × 1080   ·   30 FPS"
    right_w = sum(draw.textlength(ch, font=footer_font) for ch in right_text) + 4 * (len(right_text) - 1)
    tracked(draw, (W - 96 - right_w, 1024), right_text, footer_font,
            (*MUTED, 210), tracking=4, anchor_center=False)
    return img


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    desk = build_desk()
    desk.save(ASSETS / "desk_bg_v2.png", optimize=True)
    print("desk", desk.size)

    cards = [
        ("ada_lovelace", "ADA LOVELACE", "1815 — 1852", "01", "MATEMATICA", "card_ada.png"),
        ("marie_curie", "MARIE CURIE", "1867 — 1934", "02", "FISICA  ·  CHIMICA", "card_curie.png"),
        ("nikola_tesla", "NIKOLA TESLA", "1856 — 1943", "03", "INGEGNERIA  ·  ELETTRICITÀ", "card_tesla.png"),
    ]
    for subject, display, dates, index, role, name in cards:
        card = build_card(subject, display, dates, index, role)
        card.save(ASSETS / name, optimize=True)
        print(name, card.size)

    title = build_title()
    title.save(ASSETS / "title_overlay.png", optimize=True)
    print("title", title.size)


if __name__ == "__main__":
    main()
