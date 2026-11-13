#!/usr/bin/env python3
"""Generate the PNG assets used by the three YouTube FX RenderPlan bumpers.

The renderer's text route is intentionally not used here: each title is baked
into a transparent 1600x700 card with the same Anton/Inter typography, and the
light source/beam are soft PNGs. This keeps the plans GPU-friendly and makes the
typography editable by rerunning this script.

Usage: python3 tools/particle_lab/make_youtube_fx_assets.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets/fonts"
OUT = ROOT / "assets" / "youtube_fx"

CARD_W, CARD_H = 1600, 700
GLOW_SIZE = 1024
BEAM_W, BEAM_H = 620, 2400

RECIPES = [
    {
        "slug": "07_youtube_light_intro",
        "title": "CREA LA TUA STORIA",
        "kicker": "EP. 01  /  LIGHT + PARTICLES",
        "label": "CAMERA / LIGHT / PARTICLES",
        "accent": (89, 216, 255),
        "fill": (244, 251, 255),
        "title_size": 124,
    },
    {
        "slug": "08_youtube_particle_reveal",
        "title": "OGNI DETTAGLIO CONTA",
        "kicker": "PARTICLE REVEAL  /  EP. 02",
        "label": "CAMERA / BOKEH / FOCUS",
        "accent": (255, 140, 198),
        "fill": (255, 246, 250),
        "title_size": 112,
    },
    {
        "slug": "09_youtube_light_outro",
        "title": "ISCRIVITI ORA",
        "kicker": "NUOVA SERIE  /  OGNI SETTIMANA",
        "label": "LIGHT / PARTICLES / CAMERA",
        "accent": (255, 179, 71),
        "fill": (255, 244, 230),
        "title_size": 164,
    },
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / path), size)


def fit_font(path: str, text: str, size: int, max_width: int) -> ImageFont.FreeTypeFont:
    while size > 24:
        candidate = font(path, size)
        if candidate.getlength(text) <= max_width:
            return candidate
        size -= 2
    return font(path, size)


def centered(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
             face: ImageFont.FreeTypeFont, fill: tuple[int, ...]) -> None:
    draw.text(xy, text, font=face, fill=fill, anchor="mm")


def make_title_card(recipe: dict) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    title_face = fit_font("Anton-Regular.ttf", recipe["title"], recipe["title_size"], 1420)
    kicker_face = font("Inter-SemiBold.ttf", 31)
    label_face = font("Inter-Medium.ttf", 24)

    title_pos = (CARD_W / 2, 370)
    kicker_pos = (CARD_W / 2, 205)
    label_pos = (CARD_W / 2, 535)

    # A soft coloured halo is baked behind the sharp type. It replaces the
    # renderer-side text glow without adding a text-layer or blur pass.
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    centered(gd, title_pos, recipe["title"], title_face, (*recipe["accent"], 150))
    centered(gd, kicker_pos, recipe["kicker"], kicker_face, (*recipe["accent"], 90))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    card.alpha_composite(glow)
    card.alpha_composite(glow)

    draw = ImageDraw.Draw(card)
    centered(draw, kicker_pos, recipe["kicker"], kicker_face, (*recipe["accent"], 235))
    centered(draw, title_pos, recipe["title"], title_face, (*recipe["fill"], 255))
    centered(draw, label_pos, recipe["label"], label_face, (210, 224, 236, 185))
    draw.rounded_rectangle([CARD_W / 2 - 130, 270, CARD_W / 2 + 130, 274],
                           radius=2, fill=(*recipe["accent"], 190))
    return card


def make_glow(recipe: dict) -> Image.Image:
    glow = Image.new("RGBA", (GLOW_SIZE, GLOW_SIZE), (0, 0, 0, 0))
    pixels = glow.load()
    center = (GLOW_SIZE - 1) / 2.0
    radius = GLOW_SIZE / 2.0
    for y in range(GLOW_SIZE):
        dy = y - center
        for x in range(GLOW_SIZE):
            dx = x - center
            distance = math.hypot(dx, dy) / radius
            if distance >= 1.0:
                continue
            falloff = (1.0 - distance) ** 2.7
            core = max(0.0, 1.0 - distance * 5.2)
            alpha = int(255 * falloff)
            color = tuple(
                int(component + (255 - component) * core * 0.85)
                for component in recipe["accent"][:3]
            )
            pixels[x, y] = (*color, alpha)
    return glow


def make_beam(recipe: dict) -> Image.Image:
    strip = Image.new("RGBA", (BEAM_W, BEAM_H), (0, 0, 0, 0))
    pixels = strip.load()
    for y in range(BEAM_H):
        vertical = math.sin(math.pi * y / (BEAM_H - 1)) ** 0.8
        for x in range(BEAM_W):
            dx = (x - (BEAM_W - 1) / 2.0) / (BEAM_W / 2.0)
            profile = math.exp(-(dx * 3.4) ** 2)
            alpha = int(150 * profile * vertical)
            if alpha <= 0:
                continue
            core = max(0.0, 1.0 - abs(dx) * 2.2) * vertical
            color = tuple(
                int(component + (255 - component) * core * 0.90)
                for component in recipe["accent"][:3]
            )
            pixels[x, y] = (*color, alpha)
    rotated = strip.rotate(18, resample=Image.Resampling.BICUBIC, expand=True)
    return rotated


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for recipe in RECIPES:
        slug = recipe["slug"]
        make_title_card(recipe).save(OUT / f"{slug}_title.png", optimize=True)
        make_glow(recipe).save(OUT / f"{slug}_glow.png", optimize=True)
        make_beam(recipe).save(OUT / f"{slug}_beam.png", optimize=True)
        print(f"{slug}: title/glow/beam")


if __name__ == "__main__":
    main()
