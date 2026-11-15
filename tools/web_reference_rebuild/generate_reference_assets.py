#!/usr/bin/env python3
"""Generate the static artwork for the five supplied web references.

The animation remains native RenderPlan V3; only the paper pages, the torn
strip and the archive photograph are raster assets, exactly like the existing
newspaper-page family.  Run from the ChrononTemplate root:

    python3 tools/web_reference_rebuild/generate_reference_assets.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "web_reference_rebuild_20261114"
FONT_DIRS = [ROOT / "assets" / "fonts", ROOT.parent / "Chronon3d" / "assets" / "fonts"]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        path = directory / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    raise FileNotFoundError(f"font not found: {name}")


def paper(width: int, height: int, rgb: tuple[int, int, int], seed: int,
          fibers: int = 220) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.full((height, width, 3), rgb, dtype=np.float32)
    arr += rng.normal(0.0, 2.8, (height, width, 1))
    # Low-frequency foxing, kept subtle so the type stays crisp.
    low = rng.normal(0.0, 1.0, (max(2, height // 48), max(2, width // 48)))
    low = np.array(Image.fromarray(low.astype(np.float32), "F").resize(
        (width, height), Image.Resampling.BICUBIC))
    arr += low[..., None] * 2.2
    image = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    for _ in range(fibers):
        x = int(rng.integers(0, width))
        y = int(rng.integers(0, height))
        length = int(rng.integers(6, 34))
        draw.line((x, y, x + length, y + int(rng.integers(-1, 2))),
                  fill=(120, 110, 92, int(rng.integers(5, 14))), width=1)
    return image


def vignette(image: Image.Image, amount: float, power: float = 1.5) -> Image.Image:
    width, height = image.size
    yy, xx = np.mgrid[0:height, 0:width]
    nx = (xx - width / 2.0) / (width / 2.0)
    ny = (yy - height / 2.0) / (height / 2.0)
    radius = np.sqrt(nx * nx + ny * ny) / np.sqrt(2.0)
    shade = 1.0 - amount * np.clip((radius - 0.12) / 0.88, 0.0, 1.0) ** power
    arr = np.asarray(image, dtype=np.float32) * shade[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont,
         width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_book_page() -> None:
    width, height = 1920, 1080
    image = paper(width, height, (243, 241, 236), 71, fibers=360)
    image = vignette(image, 0.30, 1.5)
    draw = ImageDraw.Draw(image)
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(text_layer)

    head = font("FreeSerif.ttf", 44)
    head_italic = font("PlayfairDisplay-Italic.ttf", 44)
    draw.text((170, 92), "XXIII", font=head, fill=(169, 166, 160))
    draw.text((282, 92), "Frivolity", font=head_italic, fill=(169, 166, 160))

    body = font("FreeSerif.ttf", 48)
    grey = (188, 185, 179)
    ink = (23, 22, 20)
    x = 175
    y = 178
    step = 70
    black_lines = [
        "As the nation declines in power and",
        "wealth, a universal pessimism gradually",
        "pervades the people, and itself hastens the",
        "decline.",
    ]
    for line in black_lines:
        tdraw.text((x, y), line, font=body, fill=ink)
        y += step

    # The continuation is already grey on the paper; it stays in the base so
    # the highlighter never touches it.
    left = "decline."
    after = "  There is nothing succeeds like"
    draw.text((x + draw.textlength(left, font=body), 388), after, font=body, fill=grey)
    for index, line in enumerate(["success, and, in the Ages of Conquest and",
                                  "Commerce, the nation was carried"]):
        draw.text((x, 458 + index * step), line, font=body, fill=grey)

    # Clipped letters from the adjoining column at the extreme left.
    # Clipped letters from the adjoining column, just inside the macro crop.
    sliver = font("FreeSerif.ttf", 44)
    for index, letter in enumerate("ey slrtav"):
        draw.text((74 + (index % 3) * 7, 96 + index * 66), letter,
                  font=sliver, fill=(183, 180, 174))

    image.save(OUT / "book_page_base.png")
    text_layer.save(OUT / "book_text.png")
    composite = image.convert("RGBA")
    composite.alpha_composite(text_layer)
    composite.convert("RGB").save(OUT / "book_page.png")


def make_la_times_page() -> None:
    width, height = 2200, 1240
    image = paper(width, height, (217, 216, 212), 92, fibers=420)
    draw = ImageDraw.Draw(image, "RGBA")

    headline = font("PlayfairDisplay-Bold.ttf", 96)
    lines = [
        "Giants Finally Get Their Bonds :",
        "He is guaranteed a record $43.75 million",
        "for six years",
    ]
    for index, line in enumerate(lines):
        draw.text((width / 2, 64 + index * 108), line, font=headline,
                  fill=(27, 27, 27), anchor="ma")

    draw.line((150, 388, 2050, 388), fill=(92, 90, 86), width=3)

    draw.rectangle((150, 414, 380, 476), fill=(28, 28, 28))
    badge = font("PlayfairDisplay-Bold.ttf", 32)
    draw.text((265, 445), "LA Times", font=badge, fill=(245, 244, 240), anchor="mm")
    date = font("FreeSerif.ttf", 28)
    draw.text((2050, 432), "December 9, 1992", font=date, fill=(52, 51, 48), anchor="ra")

    body = font("FreeSerif.ttf", 16)
    article = (
        "The new owners of the San Francisco Giants will take the uniform No. 24 "
        "out of retirement so that it can be worn by Willie Mays, who shed tears "
        "of joy Tuesday at the long delayed official announcement. Bonds otherwise "
        "will be laughing his way to the bank because he is guaranteed a record "
        "$43.75 million for six years, with the possibility that it will top out at "
        "more than $50 million through deferred salary. An arrangement unprecedented "
        "in baseball history, it is the kind of contract that lawyers for the Giants "
        "had been working on since they announced on Tuesday that they had agreed to "
        "a deal with the free agent. I needed and received the guarantee that I "
        "wouldn't have any responsibility. No matter what happened, said Bonds. The "
        "$100-million sale of the Giants from Lurie to the Magowan group is expected "
        "to be approved by the end of the week. The only hold-up is a minor language "
        "issue in the agreement between the two groups. Bonds contract calls for a "
        "$2.5-million signing bonus and yearly guarantees of $4.75 million, with the "
        "deferred money bringing the total value above $50 million. The team also "
        "retired the number of Willie Mays, the godfather of Bonds, in a ceremony "
        "that mixed applause with the raw emotion of a franchise changing hands. "
        "Magowan conceded that baseball has obvious financial problems but said the "
        "signing gives the Giants the best player in the game to build around. It is "
        "expensive and risky, he said, but we are not starting from behind. We have "
        "sold one ticket. The Giants believe the new ballpark and the new ownership "
        "will restore a proud franchise. "
    )
    paragraphs = (article + " ") * 4
    all_lines = wrap(draw, paragraphs, body, 430)
    line_height = 21
    columns_x = [150, 650, 1150, 1650]
    per_column = 30
    cursor = 0
    for column, x in enumerate(columns_x):
        for row in range(per_column):
            if cursor >= len(all_lines):
                cursor = 0
            line = all_lines[cursor]
            cursor += 1
            draw.text((x, 510 + row * line_height), line, font=body,
                      fill=(48, 47, 44))
    for x in (620, 1120, 1620):
        draw.line((x, 500, x, 1178), fill=(128, 126, 120), width=2)

    # A washed-out archive watermark, as in the supplied video frame.
    mark = font("Inter-Bold.ttf", 46)
    draw.rectangle((2060, 28, 2142, 108), fill=(236, 235, 231, 170))
    draw.text((2101, 68), "S", font=mark, fill=(152, 152, 148, 210), anchor="mm")

    image.save(OUT / "la_times_page.png")


def make_tilted_newspaper() -> None:
    """Bake the 2.5D page pose; image-layer rotation is ignored by the executor."""
    source = Image.open(OUT / "la_times_page.png").convert("RGBA")
    width, height = 1920, 1080
    # Full-bleed quad: every edge sits outside the 1920x1080 frame, so no
    # black corners are visible even at scale 1.0 and the headline survives.
    destination = [(-60, -40), (2000, -140), (1950, 1140), (-20, 1150)]
    source_quad = [(0, 0), (source.width, 0), (source.width, source.height),
                   (0, source.height)]

    def coefficients(output_quad, input_quad):
        matrix = []
        for (x, y), (u, v) in zip(output_quad, input_quad):
            matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
            matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        return np.linalg.solve(np.array(matrix, dtype=float),
                               np.array(input_quad, dtype=float).reshape(8)).reshape(8)

    page_coeffs = coefficients(destination, source_quad)
    shadow_src = Image.new("RGBA", source.size, (0, 0, 0, 190))
    shadow = shadow_src.transform(
        (width, height), Image.PERSPECTIVE,
        coefficients([(x + 20, y + 28) for x, y in destination], source_quad),
        Image.Resampling.BICUBIC)
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(shadow)
    page = source.transform((width, height), Image.PERSPECTIVE, page_coeffs,
                            Image.Resampling.BICUBIC)
    canvas.alpha_composite(page)
    canvas.save(OUT / "la_times_page_tilted.png")


def make_torn_background() -> None:
    """A soft charcoal desk with a faint, uneven pool of light."""
    width, height = 1920, 1080
    rng = np.random.default_rng(35)
    yy, xx = np.mgrid[0:height, 0:width]
    nx = (xx - width / 2.0) / (width / 2.0)
    ny = (yy - height / 2.0) / (height / 2.0)
    glow = np.exp(-((nx * 1.05) ** 2 + (ny * 0.85) ** 2) * 1.8)
    arr = np.full((height, width, 3), 16.0, dtype=np.float32)
    arr += glow[..., None] * 9.0
    low = rng.normal(0.0, 1.0, (height // 32, width // 32)).astype(np.float32)
    low = np.array(Image.fromarray(low, "F").resize((width, height),
                                                       Image.Resampling.BICUBIC))
    arr += low[..., None] * 1.4
    arr += rng.normal(0.0, 0.6, (height, width, 1))
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(
        OUT / "torn_bg.png")


def make_torn_strip() -> None:
    width, height = 1800, 460
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rng = np.random.default_rng(33)

    def fray(t: float, amp: float = 9.0) -> float:
        coarse = 0.45 * math.sin(t * 0.018 + 1.2)
        medium = 0.35 * math.sin(t * 0.41 + 0.4)
        fine = 0.20 * math.sin(t * 1.7 + 2.1)
        return amp * (coarse + medium + fine) + float(rng.normal(0.0, 1.1))

    top: list[tuple[int, int]] = []
    for x in range(40, 1761, 7):
        top.append((x, 40 + int(fray(x))))
    right: list[tuple[int, int]] = []
    for y in range(48, 421, 6):
        right.append((1768 + int(fray(y)), y))
    bottom: list[tuple[int, int]] = []
    for x in range(1760, 39, -7):
        bottom.append((x, 420 + int(fray(x + 37.0))))
    left: list[tuple[int, int]] = []
    for y in range(414, 39, -6):
        left.append((32 + int(fray(y + 19.0)), y))
    polygon = top + right + bottom + left

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon(
        [(x, y + 18) for x, y in polygon], fill=(0, 0, 0, 155))
    shadow = shadow.filter(ImageFilter.GaussianBlur(17))
    canvas.alpha_composite(shadow)

    strip = paper(width, height, (234, 232, 226), 44, fibers=240).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    strip.putalpha(mask)
    canvas.alpha_composite(strip)

    canvas.save(OUT / "torn_strip_base.png")
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    text = font("FreeSerif.ttf", 62)
    draw.text((120, 112), "Books were just the start. Merchandising, virtually nonexistent at",
              font=text, fill=(52, 50, 47))
    draw.text((120, 190), "Scholastic, became a $60 million division. That included the TV-",
              font=text, fill=(52, 50, 47))
    text_layer.save(OUT / "torn_strip_text.png")
    composite = canvas.copy()
    composite.alpha_composite(text_layer)
    composite.save(OUT / "torn_strip.png")


def marker_texture(name: str, width: int, height: int, seed: int) -> None:
    """Organic highlighter stroke: undulating, feathered top/bottom edges."""
    rng = np.random.default_rng(seed)
    t = np.arange(width)
    amp = max(1.6, height * 0.045)
    top = height * 0.09 + amp * (0.8 * np.sin(t * 0.012 + 0.7) +
                                 0.5 * np.sin(t * 0.047 + 2.1))
    bottom = height * 0.91 - amp * (0.8 * np.sin(t * 0.013 + 1.9) +
                                    0.5 * np.sin(t * 0.041 + 0.2))
    top = top + rng.normal(0.0, 0.45, width)
    bottom = bottom + rng.normal(0.0, 0.45, width)
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    for x in range(width):
        y0 = max(0, int(round(top[x])))
        y1 = min(height, int(round(bottom[x])))
        if y1 > y0:
            arr[y0:y1, x] = (242, 197, 0, 255)
    band = Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(0.6))
    band.save(OUT / name)


def make_marker_bands() -> None:
    marker_texture("marker_strip.png", 1586, 78, 21)
    marker_texture("marker_evidence_3.png", 251, 68, 22)
    marker_texture("marker_evidence_4.png", 1400, 70, 23)
    marker_texture("marker_evidence_5.png", 1300, 72, 24)
    marker_texture("marker_evidence_6.png", 340, 72, 25)
    marker_texture("marker_book_1.png", 1508, 86, 26)
    marker_texture("marker_book_2.png", 322, 86, 27)


def make_evidence_text() -> None:
    width, height = 1920, 1080
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    face = font("PlayfairDisplay-Bold.ttf", 54)
    lines = [
        "… The question for the Serra High graduate, his mother",
        "and for his father, former Giants and major league star",
        "Bobby, on the comeback trail with the New York",
        "Yankees' Columbus, Ohio farm team, is whether a",
        "substantial bonus offer and an immediate pro career is a",
        "better path than a college scholarship opportunity at",
        "Arizona State … and then a pro career.",
    ]
    for index, line in enumerate(lines):
        draw.text((230, 210 + index * 80), line, font=face, fill=(17, 17, 17))
    canvas.save(OUT / "evidence_text.png")


def make_collage_left_text() -> None:
    """Defocused previous-shot text that continues into the collage frame."""
    page = Image.open(OUT / "la_times_page.png").convert("RGB")
    crop = ImageOps.fit(page.crop((0, 380, 560, 1080)), (620, 520),
                        Image.Resampling.LANCZOS)
    crop = crop.filter(ImageFilter.GaussianBlur(5))
    crop = ImageEnhance.Brightness(crop).enhance(0.85)
    rgba = crop.convert("RGBA")
    xx = np.linspace(0.0, 1.0, 620)[None, :]
    yy = np.linspace(0.0, 1.0, 520)[:, None]
    alpha = (np.clip(1.0 - xx * 1.25, 0.0, 1.0) *
             np.clip(1.0 - np.abs(yy - 0.5) * 1.3, 0.0, 1.0) * 0.85)
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8), "L"))
    rgba.save(OUT / "collage_left_text.png")


def make_bridge_photo() -> None:
    source = Image.open(OUT / "bridge_fortpoint.jpg").convert("L")
    source = ImageOps.autocontrast(source, cutoff=1)
    source = ImageOps.fit(source, (1000, 620), Image.Resampling.LANCZOS,
                          centering=(0.56, 0.52))
    arr = np.asarray(source, dtype=np.float32)
    arr = np.clip((arr - 128.0) * 1.16 + 128.0, 0, 255)
    Image.fromarray(arr.astype(np.uint8), "L").convert("RGB").save(OUT / "bridge_bw.png")


def make_blurred_backgrounds() -> None:
    """The supplied frames use a heavily defocused newspaper behind the subject."""
    page = Image.open(OUT / "la_times_page.png").convert("RGB")
    base = ImageOps.fit(page, (1920, 1080), Image.Resampling.LANCZOS,
                        centering=(0.5, 0.5))

    evidence = base.filter(ImageFilter.GaussianBlur(18))
    evidence = vignette(evidence, 0.12, 1.05)
    evidence.save(OUT / "evidence_bg.png")

    collage = base.filter(ImageFilter.GaussianBlur(30))
    collage = vignette(collage, 0.24, 1.2)
    # A soft pale band behind the archival title, like the reference frame.
    wash = Image.new("L", (1920, 1080), 0)
    wash_draw = ImageDraw.Draw(wash)
    for y in range(420):
        wash_draw.line((0, y, 1920, y), fill=int(118 * max(0.0, 1.0 - y / 420.0) ** 1.6))
    pale = Image.new("RGB", (1920, 1080), (220, 219, 214))
    collage = Image.composite(pale, collage, wash)
    collage.save(OUT / "collage_bg.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_book_page()
    make_la_times_page()
    make_tilted_newspaper()
    make_torn_background()
    make_torn_strip()
    make_marker_bands()
    make_evidence_text()
    make_collage_left_text()
    make_bridge_photo()
    make_blurred_backgrounds()
    print(f"assets written to {OUT}")


if __name__ == "__main__":
    main()
