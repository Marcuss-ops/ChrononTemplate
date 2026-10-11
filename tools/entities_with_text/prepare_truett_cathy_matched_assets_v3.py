#!/usr/bin/env python3
"""Prepare dark, matched documentary plates for the Truett Cathy scene."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "assets" / "images"
BG_SRC = IMAGES / "true_legacy_restaurant_background_v2.png"
FG_SRC = IMAGES / "truett_cathy_portrait_cutout_v2.png"
BG_OUT = IMAGES / "true_legacy_restaurant_background_v3_graded.png"
FG_OUT = IMAGES / "truett_cathy_portrait_v3_matched.png"
W, H = 1920, 1080


def prepare_background():
    src = Image.open(BG_SRC).convert("RGB")
    ratio = max(W / src.width, H / src.height)
    src = src.resize((round(src.width * ratio), round(src.height * ratio)), Image.LANCZOS)
    x0, y0 = (src.width - W) // 2, (src.height - H) // 2
    src = src.crop((x0, y0, x0 + W, y0 + H))
    src = ImageEnhance.Color(src).enhance(.65)
    src = ImageEnhance.Brightness(src).enhance(.47)
    src = src.filter(ImageFilter.GaussianBlur(3.5))
    yy, xx = np.mgrid[0:H, 0:W]
    radius = np.sqrt(((xx - W*.5)/(W*.73))**2 + ((yy - H*.48)/(H*.76))**2)
    vignette = np.clip(1.0 - .42 * np.maximum(0, radius - .30), .48, 1.0)
    pixels = np.asarray(src, dtype=np.float32) * vignette[..., None]
    pixels[..., 0] *= 1.03
    pixels[..., 1] *= .97
    graded = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    # Add a small practical sign to the blank red facade panel in this crop.
    # Keep the lettering dim and let the glow blend into the existing wall light.
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 24)
    sign = Image.new("RGBA", graded.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sign)
    d.text((1070, 355), "Chick-fil-A", font=font, fill=(231, 43, 46, 175), stroke_width=0)
    glow = sign.filter(ImageFilter.GaussianBlur(14))
    graded = Image.alpha_composite(graded, glow)
    graded = Image.alpha_composite(graded, sign)
    graded.convert("RGB").save(BG_OUT)


def prepare_portrait():
    src = Image.open(FG_SRC).convert("RGBA")
    rgb = ImageEnhance.Color(src.convert("RGB")).enhance(.88)
    rgb = ImageEnhance.Brightness(rgb).enhance(.82)
    rgb = ImageEnhance.Contrast(rgb).enhance(.96)
    alpha_img = src.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.28))
    alpha = np.asarray(alpha_img, dtype=np.float32) / 255
    rgb_px = np.asarray(rgb, dtype=np.float32)
    edge = (alpha > .01) & (alpha < .92)
    neutral = rgb_px.mean(axis=2, keepdims=True)
    rgb_px[edge] = rgb_px[edge] * .78 + neutral[edge] * .22

    # Soft, low-opacity wrap samples the graded background behind the cutout.
    plate = Image.open(BG_OUT).convert("RGB")
    sample = plate.crop((520, 0, 1400, 780)).resize(src.size, Image.BILINEAR)
    sample_px = np.asarray(sample, dtype=np.float32)
    mask_img = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    inner = np.asarray(mask_img, dtype=np.float32) - np.asarray(mask_img.filter(ImageFilter.MinFilter(7)), dtype=np.float32)
    wrap = np.clip(inner / 255, 0, 1) * .16
    wrap *= np.clip((sample_px[..., 0] - 24) / 120, 0, 1)
    warm = np.stack([np.maximum(sample_px[..., 0], 68), sample_px[..., 1] * .62,
                     sample_px[..., 2] * .50], axis=2)
    rgb_px = rgb_px * (1 - wrap[..., None]) + warm * wrap[..., None]
    out = np.dstack([np.clip(rgb_px, 0, 255).astype(np.uint8), np.asarray(alpha_img)])
    Image.fromarray(out, "RGBA").save(FG_OUT)


if __name__ == "__main__":
    prepare_background()
    prepare_portrait()
    print(f"Wrote {BG_OUT} and {FG_OUT}")
