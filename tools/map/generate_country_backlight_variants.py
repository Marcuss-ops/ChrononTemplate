#!/usr/bin/env python3
"""Generate colored map/backlight/smoke plates for documentary country variants."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "catalog" / "ne_50m_admin_0_countries.geojson"
W, H = 1920, 1080

# slug, Natural Earth ADMIN, title, accent color, backlight color
VARIANTS = [
    ("italy", "Italy", "ITALIA", "#28B878", (18, 139, 83)),
    ("brazil", "Brazil", "BRASILE", "#28C3C8", (14, 136, 151)),
    ("japan", "Japan", "GIAPPONE", "#F05B55", (172, 34, 43)),
]
BOUNDS = {
    "Italy": (6.2, 19.0, 35.0, 48.8),
    "Brazil": (-74.5, -34.0, -34.0, 5.5),
    "Japan": (128.0, 146.5, 30.0, 46.5),
}


def rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))


def build(slug, country, label, accent_hex, glow_rgb):
    out = ROOT / "assets" / f"{slug}_atmospheric_backlight_v1"
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(GEO.read_text())
    feature = next(f for f in data["features"] if f["properties"].get("ADMIN") == country)
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    west, east, south, north = BOUNDS[country]

    # Account for the latitude convergence enough to keep country proportions believable.
    xscale = np.cos(np.deg2rad((south + north) * .5))
    x_span = (east - west) * xscale
    y_span = north - south
    fit = min(1190 / x_span, 545 / y_span)
    drawn_w, drawn_h = x_span * fit, y_span * fit
    left, top = (W - drawn_w) / 2, (H - drawn_h) / 2
    def project(lon, lat):
        return left + (lon - west) * xscale * fit, top + (north - lat) * fit

    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    for poly in polys:
        ring = poly[0]
        inside = [(lon, lat) for lon, lat in ring
                  if west - 2 <= lon <= east + 2 and south - 2 <= lat <= north + 2]
        if len(inside) >= 3:
            # Keep only plausible country parts; ignore distant overseas fragments.
            lon_mid = sum(p[0] for p in inside) / len(inside)
            lat_mid = sum(p[1] for p in inside) / len(inside)
            if west - 1 <= lon_mid <= east + 1 and south - 1 <= lat_mid <= north + 1:
                draw.polygon([project(lon, lat) for lon, lat in ring], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(.8))
    mask.save(out / "country_mask.png")

    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.sqrt(((xx - W*.5)/(W*.76))**2 + ((yy - H*.49)/(H*.8))**2)
    rng = np.random.default_rng(sum(map(ord, slug)))
    grain = rng.normal(0, 1.0, (H, W))
    base = np.clip(10 - radial[..., None] * 6 + grain[..., None], 2, 15).astype(np.uint8)
    bg = np.dstack([base * .86, base * .84, base * .84]).astype(np.uint8)
    Image.fromarray(bg, "RGB").save(out / "dark_field.png")

    for sigma, strength, name, scale in [
        (180, 72, "wide_red_backlight.png", .72),
        (76, 66, "tight_red_diffusion.png", 1.0),
    ]:
        blurred = np.asarray(mask.filter(ImageFilter.GaussianBlur(sigma)), dtype=np.float32) / 255
        alpha = (blurred * strength).clip(0, 255).astype(np.uint8)
        rgba = np.zeros((H, W, 4), dtype=np.uint8)
        rgba[..., :3] = tuple(round(c * scale) for c in glow_rgb)
        rgba[..., 3] = alpha
        Image.fromarray(rgba, "RGBA").save(out / name)

    m = np.asarray(mask, dtype=np.float32) / 255
    accent = rgb(accent_hex)
    grad = np.clip(.72 + .2 * (1 - yy/H) + .045 * np.sin(xx/135), .43, .97)
    surf = np.zeros((H, W, 4), dtype=np.uint8)
    for ch, c in enumerate(accent):
        # A very dark surface tint preserves the same cinematic contrast.
        surf[..., ch] = (c * grad * .29).astype(np.uint8)
    surf[..., 3] = (m * 255).astype(np.uint8)
    Image.fromarray(surf, "RGBA").save(out / "burgundy_country.png")

    noise = np.zeros((H, W), dtype=np.float32)
    rng = np.random.default_rng(202 + sum(map(ord, slug)))
    for scale, weight in [(24, .50), (48, .30), (96, .20)]:
        small = Image.fromarray((rng.random((max(2, H//scale), max(2, W//scale))) * 255).astype(np.uint8))
        noise += np.asarray(small.resize((W, H), Image.BICUBIC), dtype=np.float32) / 255 * weight
    clouds = np.clip((noise - .49) * 2.7, 0, 1)
    band = np.exp(-((yy - (560 + 90*np.sin(xx/260))) / 270)**2)
    alpha = (clouds * band * 54).clip(0, 70).astype(np.uint8)
    smoke = np.zeros((H, W, 4), dtype=np.uint8)
    smoke[..., :3] = (119, 116, 116)
    smoke[..., 3] = alpha
    Image.fromarray(smoke, "RGBA").filter(ImageFilter.GaussianBlur(8)).save(out / "smoke_veil.png")
    print(f"generated {label}: {out}")


if __name__ == "__main__":
    for args in VARIANTS:
        build(*args)
