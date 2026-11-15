#!/usr/bin/env python3
"""Generate the P1 macro-LCD full-frame optical plate.

The native lens path resamples tight layer surfaces to transparent; a
full-frame opaque plate keeps the card edge measurable for curvature and
chromatic aberration. The surrounding fill matches p1_ground (#D7DADD).
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "ChrononTemplate/assets/documentary_parity/p1_panel_opaque.png"

W, H = 1920, 1080
LEFT, TOP, CARD_W, CARD_H = 96, 70, 1728, 940
GROUND = (215, 218, 221)
CARD = (255, 255, 255)

image = Image.new("RGB", (W, H), GROUND)
draw = ImageDraw.Draw(image)
draw.rounded_rectangle(
    [LEFT, TOP, LEFT + CARD_W - 1, TOP + CARD_H - 1],
    radius=24,
    fill=CARD,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUT)
print(OUT)
