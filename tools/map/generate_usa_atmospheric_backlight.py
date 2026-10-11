#!/usr/bin/env python3
"""Build procedural RGBA plates for the native Chronon USA backlight example."""
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "usa_atmospheric_backlight_v1"
GEO = ROOT / "catalog" / "ne_50m_admin_0_countries.geojson"
W, H = 1920, 1080


def country_polygons():
    data = json.loads(GEO.read_text())
    feature = next(f for f in data["features"]
                   if f["properties"].get("ADMIN") == "United States of America")
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [p[0] for p in polys]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Native continental US outline in a wide cinematic frame. Alaska and Hawaii
    # are intentionally represented as small, recognizable insets.
    bbox = (-125.0, -66.5, 24.0, 50.0)
    def project(lon, lat):
        x = 365 + (lon - bbox[0]) / (bbox[1] - bbox[0]) * 1190
        y = 815 - (lat - bbox[2]) / (bbox[3] - bbox[2]) * 545
        return (x, y)

    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    polygons = country_polygons()
    alaska, hawaii = [], []
    for poly in polygons:
        lon = sum(pt[0] for pt in poly[:-1]) / max(1, len(poly)-1)
        lat = sum(pt[1] for pt in poly[:-1]) / max(1, len(poly)-1)
        if lon < -130:
            alaska.append(poly)
            continue
        if -161 < lon < -154 and 18 < lat < 23:
            hawaii.append(poly)
            continue
        if -127 < lon < -65 and 23 < lat < 51:
            draw.polygon([project(lon, lat) for lon, lat in poly], fill=255)

    # Alaska/Hawaii inset geometry, styled as part of the same country silhouette.
    for poly in alaska:
        pts = [(270 + (lon + 180) / 52 * 180, 800 - (lat - 50) / 22 * 125)
               for lon, lat in poly if lon <= -128 and 50 <= lat <= 73]
        if len(pts) > 2:
            draw.polygon(pts, fill=255)
    for poly in hawaii:
        pts = [(475 + (lon + 160) * 29, 800 - (lat - 18) * 28)
               for lon, lat in poly]
        if len(pts) > 2:
            draw.polygon(pts, fill=255)

    # Edge anti-aliasing and modest smoothing retain geographic detail.
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    mask.save(OUT / "usa_mask.png")

    # Nearly black charcoal field with an understated vignette and fine texture.
    yy, xx = np.mgrid[0:H, 0:W]
    radial = np.sqrt(((xx - W*.51)/(W*.75))**2 + ((yy - H*.48)/(H*.78))**2)
    rng = np.random.default_rng(3200)
    grain = rng.normal(0, 1.15, (H, W))
    base = np.clip(10 - radial[..., None] * 6 + grain[..., None], 2, 16).astype(np.uint8)
    bg = np.dstack([base * .86, base * .84, base * .84]).astype(np.uint8)
    Image.fromarray(bg, "RGB").save(OUT / "dark_field.png")

    # Two true silhouette-derived light passes: a broad haze and a tighter core.
    wide = mask.filter(ImageFilter.GaussianBlur(175))
    tight = mask.filter(ImageFilter.GaussianBlur(74))
    def glow_plate(blurred, color, strength, filename):
        a = (np.asarray(blurred).astype(np.float32) / 255 * strength).clip(0, 255).astype(np.uint8)
        rgba = np.zeros((H, W, 4), dtype=np.uint8)
        rgba[..., :3] = color
        rgba[..., 3] = a
        Image.fromarray(rgba, "RGBA").save(OUT / filename)
    glow_plate(wide, (130, 10, 17), 82, "wide_red_backlight.png")
    glow_plate(tight, (184, 17, 27), 78, "tight_red_diffusion.png")

    # Burgundy map surface with a slow-looking spatial red variation and subdued edge.
    m = np.asarray(mask).astype(np.float32) / 255
    gradient = np.clip(.74 + .20 * (1 - yy / H) + .05 * np.sin(xx / 135), .45, .98)
    surface = np.zeros((H, W, 4), dtype=np.uint8)
    surface[..., 0] = (70 * gradient).astype(np.uint8)
    surface[..., 1] = (5 * gradient).astype(np.uint8)
    surface[..., 2] = (9 * gradient).astype(np.uint8)
    surface[..., 3] = (m * 255).astype(np.uint8)
    Image.fromarray(surface, "RGBA").save(OUT / "burgundy_usa.png")

    # Procedural smoke: layered low-frequency noise, softly blurred, partially
    # masked over the light so it occludes the backlight instead of outlining it.
    noise = np.zeros((H, W), dtype=np.float32)
    rng = np.random.default_rng(49)
    for scale, weight in [(24, .50), (48, .30), (96, .20)]:
        small = Image.fromarray((rng.random((max(2, H//scale), max(2, W//scale))) * 255).astype(np.uint8))
        noise += np.asarray(small.resize((W, H), Image.BICUBIC), dtype=np.float32) / 255 * weight
    clouds = np.clip((noise - .49) * 2.7, 0, 1)
    veil = np.clip(.25 + .75 * (1 - m), .18, 1.0)
    # Keep clouds concentrated behind/around the map with tendrils crossing it.
    band = np.exp(-((yy - (560 + 90*np.sin(xx/260))) / 260)**2)
    alpha = (clouds * veil * band * 58).clip(0, 75).astype(np.uint8)
    smoke = np.zeros((H, W, 4), dtype=np.uint8)
    smoke[..., :3] = (119, 116, 116)
    smoke[..., 3] = alpha
    Image.fromarray(smoke, "RGBA").filter(ImageFilter.GaussianBlur(8)).save(OUT / "smoke_veil.png")

    print(f"Wrote procedural backlight plates to {OUT}")


if __name__ == "__main__":
    main()
