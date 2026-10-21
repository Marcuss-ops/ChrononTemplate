#!/usr/bin/env python3
"""Rebuild NBA long/short phrase clips in the approved article-to-title style."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/nba_web_long_short_redo"
W, H, FPS, FRAMES = 1920, 1080, 30, 240
PAGE_FADE_IN, PAGE_FADE_OUT = 99, 111
TITLE_FADE_IN, TITLE_FADE_OUT = 109, 124
FONT_PATH = ROOT / "assets/fonts/Inter-Bold.ttf"
KUMINGA_PATH = ROOT / "out/web_article_fold/static_page.png"
MARK_CUBAN_PATH = ROOT / "out/reference_article_styles/nba_article_preview.png"
KUMINGA_BASE = Image.open(KUMINGA_PATH).convert("RGB")
MARK_CUBAN_BASE = Image.open(MARK_CUBAN_PATH).convert("RGB")


def article_page(frame: int, subject: str) -> Image.Image:
    """Hold the source article, then dissolve it into the title card."""
    page = KUMINGA_BASE.copy() if subject == "kuminga" else MARK_CUBAN_BASE.copy()
    if subject == "kuminga":
        # The existing plate reserves this headline area; use the exact long
        # story headline from the approved article reference.
        draw = ImageDraw.Draw(page)
        font = ImageFont.truetype(str(FONT_PATH), 52)
        draw.text((453, 153), "Sources: Jonathan Kuminga", font=font, fill=(36, 55, 70))
        draw.text((453, 216), "demanding trade away from Warriors", font=font, fill=(36, 55, 70))
    if frame < PAGE_FADE_IN:
        return page
    alpha = min(1.0, (frame - PAGE_FADE_IN) / (PAGE_FADE_OUT - PAGE_FADE_IN))
    black = Image.new("RGB", (W, H), "black")
    return Image.blend(page, black, alpha)


def italic_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                y: int, alpha: int) -> None:
    # Slant the bold NBA-style sans face as in the approved centered title card.
    width = int(font.getlength(text)) + 90
    box = font.getbbox(text)
    height = box[3] - box[1] + 22
    tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((35, 8 - box[1]), text, font=font,
                             fill=(248, 248, 248, alpha))
    slant = 0.18
    out_w = width + int(height * slant)
    tile = tile.transform((out_w, height), Image.Transform.AFFINE,
                          (1, slant, -height * slant, 0, 1, 0),
                          resample=Image.Resampling.BICUBIC)
    draw.bitmap(((W - out_w) // 2, y), tile)


def title_card(frame: int, lines: tuple[str, ...]) -> Image.Image:
    card = Image.new("RGB", (W, H), "black")
    if frame <= TITLE_FADE_IN:
        return card
    alpha = min(255, int(255 * (frame - TITLE_FADE_IN) / (TITLE_FADE_OUT - TITLE_FADE_IN)))
    draw = ImageDraw.Draw(card, "RGBA")
    font_size = 84 if len(lines) == 1 else 68
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    while max(font.getlength(line) for line in lines) > 1560 and font_size > 48:
        font_size -= 2
        font = ImageFont.truetype(str(FONT_PATH), font_size)
    line_gap = int(font_size * 1.24)
    first_y = (H - len(lines) * line_gap) // 2 - 12
    for index, line in enumerate(lines):
        italic_text(draw, line, font, first_y + index * line_gap, alpha)
    # The reference uses a quiet hairline beneath its single centered title.
    line_width = 330
    line_y = first_y + len(lines) * line_gap + 2
    draw.line((W // 2 - line_width // 2, line_y,
               W // 2 + line_width // 2, line_y), fill=(166, 166, 166, alpha), width=2)
    return card


def make_frame(frame: int, subject: str, short: bool) -> Image.Image:
    lines = {
        ("kuminga", False): ("Sources: Jonathan Kuminga",
                              "demanding trade away from Warriors"),
        ("kuminga", True): ("Kuminga: Trade Request",),
        ("mark_cuban", False): ("Report: Mark Cuban Hired Former FBI Agent",
                                 "to Investigate NBA After 2006 Finals"),
        ("mark_cuban", True): ("NBA After 2006 Finals",),
    }[(subject, short)]
    page = article_page(frame, subject)
    card = title_card(frame, lines)
    if frame <= TITLE_FADE_IN:
        return page
    alpha = min(1.0, (frame - TITLE_FADE_IN) / (TITLE_FADE_OUT - TITLE_FADE_IN))
    # Page and title crossfade together, matching the existing NBA Web clips.
    return Image.blend(page, card, alpha)


def encode(name: str, subject: str, short: bool) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / f"{name}.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
               "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(output)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for frame in range(FRAMES):
            proc.stdin.write(make_frame(frame, subject, short).tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError(f"ffmpeg failed for {name}")
    except BaseException:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.terminate()
        proc.wait()
        raise
    return output


def main() -> None:
    for path in (FONT_PATH, KUMINGA_PATH, MARK_CUBAN_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)
    jobs = [
        ("nba_web_kuminga_long", "kuminga", False),
        ("nba_web_kuminga_short", "kuminga", True),
        ("nba_web_mark_cuban_long", "mark_cuban", False),
        ("nba_web_mark_cuban_short", "mark_cuban", True),
    ]
    for name, subject, short in jobs:
        result = encode(name, subject, short)
        print(f"wrote {result}", flush=True)


if __name__ == "__main__":
    main()
