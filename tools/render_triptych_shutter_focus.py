"""Render three independent archival photo cards with per-card rack focus.

Usage: python render_triptych_shutter_focus.py <asset-directory> <output.mp4>
The photo cards are separate layers, with explicit spacing and no shared focus mask.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 1280, 720
OUTPUT_WIDTH, OUTPUT_HEIGHT = 1920, 1080
FPS, DURATION = 30, 5.0
FRAME_COUNT = int(FPS * DURATION)
SHUTTER_SAMPLES = 4
CARD_W, CARD_H = 320, 210
PHOTO_X, PHOTO_Y, PHOTO_W, PHOTO_H = 12, 12, 296, 166
CARD_POSITIONS = [(80, 146), (480, 132), (880, 146)]


def smoothstep(a: float, b: float, t: float) -> float:
    x = np.clip((t - a) / (b - a), 0.0, 1.0)
    return float(x * x * (3.0 - 2.0 * x))


def focus_weights(t: float) -> tuple[float, float, float]:
    # Left, middle and right prints each have their own focus interval.
    left = max(1.0 - smoothstep(0.65, 1.55, t), smoothstep(4.0, 4.8, t))
    middle = max(smoothstep(1.0, 1.7, t) * (1.0 - smoothstep(2.55, 3.25, t)),
                 smoothstep(4.0, 4.8, t))
    right = max(smoothstep(2.65, 3.4, t) * (1.0 - smoothstep(3.8, 4.55, t)),
                smoothstep(4.0, 4.8, t))
    return left, middle, right


def paper_background() -> np.ndarray:
    rng = np.random.default_rng(41)
    coarse = rng.normal(0, 2.6, (30, 54)).astype(np.float32)
    coarse = cv2.resize(coarse, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    fine = rng.normal(0, 2.0, (HEIGHT, WIDTH)).astype(np.float32)
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    nx, ny = (xx - WIDTH / 2) / (WIDTH / 2), (yy - HEIGHT / 2) / (HEIGHT / 2)
    vignette = np.clip(1.0 - 0.045 * (nx * nx + ny * ny), 0.89, 1.0)
    base = np.empty((HEIGHT, WIDTH, 3), dtype=np.float32)
    # Warm charcoal-gray paper, with restrained fibers and softly aged corners.
    for channel, value in enumerate((112, 119, 126)):
        base[:, :, channel] = (value + coarse + fine) * vignette
    return np.clip(base, 0, 255).astype(np.uint8)


def load_cards(asset_dir: Path) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    names = ("photo_01_island.png", "photo_02_radio.png", "photo_03_corridor.png")
    cards = []
    for name in names:
        photo = cv2.imread(str(asset_dir / name), cv2.IMREAD_COLOR)
        if photo is None:
            raise RuntimeError(f"cannot open photo asset: {asset_dir / name}")
        photo = cv2.resize(photo, (PHOTO_W, PHOTO_H), interpolation=cv2.INTER_AREA)
        soft_photo = cv2.GaussianBlur(photo, (0, 0), 4.5)
        card = np.full((CARD_H, CARD_W, 3), (218, 222, 226), dtype=np.uint8)
        card[PHOTO_Y:PHOTO_Y + PHOTO_H, PHOTO_X:PHOTO_X + PHOTO_W] = photo
        # A narrow aged mount keeps all four edges of each print distinct.
        cv2.rectangle(card, (4, 4), (CARD_W - 5, CARD_H - 5), (198, 204, 209), 1)
        cv2.line(card, (PHOTO_X, PHOTO_Y + PHOTO_H + 10),
                 (PHOTO_X + PHOTO_W, PHOTO_Y + PHOTO_H + 10), (208, 211, 214), 1)
        cards.append((card, photo, soft_photo))
    return cards


def add_shadow(canvas: np.ndarray, x: int, y: int) -> None:
    pad = 18
    sx, sy = max(0, x - pad), max(0, y - pad)
    ex, ey = min(WIDTH, x + CARD_W + pad), min(HEIGHT, y + CARD_H + pad)
    shadow = np.zeros((ey - sy, ex - sx), dtype=np.uint8)
    cv2.rectangle(shadow, (x - sx + 4, y - sy + 8),
                  (min(ex - sx - 1, x - sx + CARD_W + 3),
                   min(ey - sy - 1, y - sy + CARD_H + 7)), 36, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 8.0).astype(np.float32) / 255.0
    roi = canvas[sy:ey, sx:ex].astype(np.float32)
    roi *= 1.0 - shadow[:, :, None] * 0.28
    canvas[sy:ey, sx:ex] = np.clip(roi, 0, 255).astype(np.uint8)


def render(asset_dir: Path, output_path: Path) -> int:
    cards = load_cards(asset_dir)
    bg = paper_background()
    ffmpeg = [
        "C:/Ffmpeg/ffmpeg.exe", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-vf", f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:flags=lanczos",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(DURATION), str(output_path),
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoder = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    assert encoder.stdin is not None
    offsets = (np.arange(SHUTTER_SAMPLES, dtype=np.float32) + 0.5) / SHUTTER_SAMPLES - 0.5
    try:
        for frame_idx in range(FRAME_COUNT):
            exposure = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
            for offset in offsets:
                t = float(np.clip((frame_idx + float(offset) * 0.5) / FPS, 0.0, DURATION))
                weights = focus_weights(t)
                scene = bg.copy()
                # Each layer has its own crop, blur, timing and motion. The generous
                # gaps mean neither a neighboring photo nor its border enters a focus mask.
                for idx, ((card, sharp, soft), (base_x, base_y)) in enumerate(zip(cards, CARD_POSITIONS)):
                    focus = weights[idx]
                    focused_photo = cv2.addWeighted(soft, 1.0 - focus, sharp, focus, 0.0)
                    panel = card.copy()
                    panel[PHOTO_Y:PHOTO_Y + PHOTO_H, PHOTO_X:PHOTO_X + PHOTO_W] = focused_photo
                    phase = t / DURATION
                    dx = round((phase - 0.5) * (8, -5, 6)[idx])
                    dy = round(np.sin(phase * np.pi) * (4, -3, 3)[idx])
                    x, y = base_x + dx, base_y + dy
                    add_shadow(scene, x, y)
                    scene[y:y + CARD_H, x:x + CARD_W] = panel
                exposure += scene.astype(np.float32)
            frame = np.clip(exposure / SHUTTER_SAMPLES, 0, 255).astype(np.uint8)
            encoder.stdin.write(frame.tobytes())
            if frame_idx % 30 == 0:
                print(f"Rendered {frame_idx}/{FRAME_COUNT} frames", flush=True)
    finally:
        encoder.stdin.close()
    return encoder.wait()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: render_triptych_shutter_focus.py <asset-directory> <output.mp4>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(render(Path(sys.argv[1]), Path(sys.argv[2])))
