#!/usr/bin/env python3
"""Generate soft alpha radial blob textures for the Vulkan editorial pack."""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

import build_kinetic_type_editorial_v1 as editorial


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "assets" / "kinetic_type_editorial_v1"
SIZE = 512


def _chunk(name: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + name + payload
            + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF))


def _png_rgba(path: Path, rgb: tuple[int, int, int]) -> None:
    rows = bytearray()
    center = (SIZE - 1) * 0.5
    radius = center
    for y in range(SIZE):
        rows.append(0)  # PNG filter: None
        for x in range(SIZE):
            nx, ny = (x - center) / radius, (y - center) / radius
            angle = math.atan2(ny, nx)
            distance = math.hypot(nx, ny)
            # A stable low-frequency warp breaks the ellipse silhouette into
            # broad aurora folds while preserving a soft, banding-free falloff.
            edge = (1.0 + 0.075 * math.sin(3 * angle + 0.8)
                    + 0.045 * math.sin(5 * angle - 1.4)
                    + 0.025 * math.sin(9 * angle + 2.1))
            warped = distance / edge
            alpha = min(255, round(242 * math.exp(-4.1 * warped * warped)
                                   + 30 * math.exp(-13.0 * warped * warped))) if warped < 1.15 else 0
            rows.extend((*rgb, alpha))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header)
                     + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
                     + _chunk(b"IEND", b""))


def main() -> int:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    names = sorted({blob["color"].split(".", 2)[-1]
                    for preset in editorial.BACKGROUND_PRESETS.values()
                    for blob in preset["blobs"]})
    color_tokens = {name: f"bg.blob.{name}" for name in names}
    color_tokens.update({token.replace(".", "_"): token
                         for token in ("accent.coral", "accent.yellow", "accent.lavender")})
    for name, token in sorted(color_tokens.items()):
        color = editorial.EDITORIAL_COLOR_TOKENS[token].lstrip("#")
        rgb = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        path = DESTINATION / f"{name}.png"
        _png_rgba(path, rgb)
        print(f"PASS {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
