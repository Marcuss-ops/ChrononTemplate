#!/usr/bin/env python3
"""Composite the per-character article fold reveal over a prepared plate and encode 1080p H.264."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
import subprocess
import sys

if len(sys.argv) not in (3, 4):
    raise SystemExit("usage: render_web_article_fold.py <static_page.png> <output.mp4> [<Inter-Bold.ttf>]")

plate_path, output_path = map(Path, sys.argv[1:3])
W, H, FPS, FRAMES = 1920, 1080, 30, 240
font_path = Path(sys.argv[3]) if len(sys.argv) == 4 else Path(__file__).resolve().parents[2] / "out/web_article_fold/fonts/Inter-Bold.ttf"
font = ImageFont.truetype(str(font_path), 52)
plate = Image.open(plate_path).convert("RGB")
if plate.size != (W, H):
    raise ValueError(f"expected 1920x1080 plate, got {plate.size}")

def glyphs_for_line(text, x, y, begin, stagger=2, duration=9):
    # Split a single correctly kerned raster line into glyph tiles. Each tile
    # grows upward from its baseline as its short fold finishes.
    box = font.getbbox(text)
    line = Image.new("RGBA", (math.ceil(font.getlength(text)) + 8, box[3] - box[1] + 8))
    ImageDraw.Draw(line).text((2, 4 - box[1]), text, font=font, fill=(36, 55, 70, 255))
    output = []
    cursor = 0.0
    for index, ch in enumerate(text):
        next_cursor = font.getlength(text[:index + 1])
        left = max(0, int(math.floor(cursor)) + 1)
        right = min(line.width, max(left + 1, int(math.ceil(next_cursor)) + 4))
        tile = line.crop((left, 0, right, line.height))
        if ch != " ":
            output.append((tile, x + int(cursor), y, begin + index * stagger, begin + index * stagger + duration))
        cursor = next_cursor
    return output

glyphs = glyphs_for_line("Sources: Jonathan Kuminga", 453, 153, 0)
glyphs += glyphs_for_line("demanding trade away from Warriors", 453, 216, 42)

command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
           "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(output_path)]
output_path.parent.mkdir(parents=True, exist_ok=True)
encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
try:
    for frame in range(FRAMES):
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for tile, x, y, start, end in glyphs:
            if frame < start:
                continue
            p = min(1.0, (frame - start) / max(1, end - start))
            eased = 1.0 - (1.0 - p) ** 3
            visible_h = max(1, int(tile.height * eased))
            folded = tile.resize((tile.width, visible_h), Image.Resampling.LANCZOS)
            if p < 0.55:
                alpha = folded.getchannel("A").point(lambda value: int(value * (0.55 + 0.45 * p / 0.55)))
                folded.putalpha(alpha)
            # The bottom edge stays planted; the top edge unfolds upward.
            overlay.alpha_composite(folded, (x, y + tile.height - visible_h))
        frame_image = Image.alpha_composite(plate.convert("RGBA"), overlay).convert("RGB")
            # A restrained push-in over the web article page.
        zoom = 1.0 + 0.035 * frame / max(1, FRAMES - 1)
        if zoom > 1.0:
            zw, zh = int(W * zoom), int(H * zoom)
            enlarged = frame_image.resize((zw, zh), Image.Resampling.LANCZOS)
            x0, y0 = (zw - W) // 2, (zh - H) // 2
            frame_image = enlarged.crop((x0, y0, x0 + W, y0 + H))
        encoder.stdin.write(frame_image.tobytes())
        if frame % 30 == 0:
            print(f"rendered {frame + 1}/{FRAMES} frames", flush=True)
    encoder.stdin.close()
    result = encoder.wait()
    if result:
        raise SystemExit(result)
except BaseException:
    if encoder.stdin and not encoder.stdin.closed:
        encoder.stdin.close()
    encoder.terminate()
    encoder.wait()
    raise
print(f"wrote {output_path}")
