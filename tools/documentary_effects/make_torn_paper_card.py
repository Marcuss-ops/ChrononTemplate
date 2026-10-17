#!/usr/bin/env python3
"""Bake the torn paper clipping card from the paper texture plate.

The torn alpha edge is baked into real pixels (seeded, deterministic), so the
C++ pack consumes a plain image layer: no RoughenEdges effect crosses the
render-plan emitter, which cannot write it.
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1]
PLATE = (TEMPLATE / "catalog/minimal_documentary_backgrounds/assets"
         / "11_newspaper_paper_plate.png")
OUT = TEMPLATE / "assets/archival_timeline_reveal_v1/paper_card.png"
W, H, SEED = 790, 444, 1971


def main() -> None:
    plate = Image.open(PLATE).convert("RGB")
    crop = plate.crop(((1920 - W) // 2, (1080 - H) // 2 - 80,
                       (1920 + W) // 2, (1080 + H) // 2 - 80))
    rnd = random.Random(SEED)
    step = 14

    def edge(n: int) -> list[int]:
        return [max(0, min(20, int(rnd.gauss(10, 4)))) for _ in range(n + 1)]

    nx, ny = W // step, H // step
    top, bottom, left, right = edge(nx), edge(nx), edge(ny), edge(ny)
    poly = [(i * step, top[i]) for i in range(nx + 1)]
    poly += [(W - right[i], i * step) for i in range(ny + 1)]
    poly += [(W - i * step, H - bottom[nx - i]) for i in range(nx + 1)]
    poly += [(left[ny - i], H - i * step) for i in range(ny + 1)]

    alpha = Image.new("L", (W, H), 0)
    ImageDraw.Draw(alpha).polygon(poly, fill=255)
    card = crop.copy()
    card.putalpha(alpha)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    card.save(OUT)
    print(f"wrote {OUT} {card.size}")


if __name__ == "__main__":
    main()
