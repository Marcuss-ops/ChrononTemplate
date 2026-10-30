"""Build centered, full-page highlight recreations from three reference frames.

All three clips share one editorial layout, typeface, size, and camera. The
complete text appears together first; a marker sweep begins after a short hold.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image

from web_shot_kit import Canvas, Shot, contact_sheet


W, H = 1920, 1080
FONT = "serif"
SIZE = 48
LEADING = 82
LEFT = 210
TEXT = "#77736F"
INK = "#171614"
PAPER = "#EAE9E6"
MARKER = "#E6E32E"


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def centered_shot(name: str, source: str, description: str,
                  lines: list[str], highlight_line: int, phrase: str,
                  prefix: str = "") -> Shot:
    block_h = SIZE + max(0, len(lines) - 1) * LEADING
    y0 = (H - block_h) / 2

    def background(c: Canvas):
        c.rect(0, 0, W, H, PAPER)

    def text_layer(c: Canvas):
        for i, line in enumerate(lines):
            color = INK if i == highlight_line else TEXT
            c.text(LEFT, y0 + i * LEADING, line, SIZE, FONT, color)

    def marker(c: Canvas, t: float):
        # Keep the entire page in frame. The marker starts after every line is
        # already visible, then the same full-frame composition holds.
        sweep = ease((t - 0.38) / 0.30)
        if sweep > 0.0:
            x = LEFT + c.measure(prefix, SIZE, FONT) - 8
            width = c.measure(phrase, SIZE, FONT) + 16
            seed = sum((i + 1) * ord(ch) for i, ch in enumerate(name)) & 0xFFFF
            c.marker(x, y0 + highlight_line * LEADING + 5, width, 58,
                     MARKER, alpha=0.96, sweep=sweep,
                     seed=seed, rough=True)

    return Shot(
        name=name,
        source=source,
        seconds=3.0,
        fps=30,
        still_t=1.0,
        description=description,
        cam_from=(1.0, 0.5, 0.5),
        cam_to=(1.0, 0.5, 0.5),
        grain=0.0,
        vig=0.0,
        build_static=background,
        build_static_front=text_layer,
        draw_anim=marker,
    )


SHOTS = [
    centered_shot(
        "10_tax_exempt_nyt",
        "Screenshot 2026-10-25 at 12-28-56 Unsettling Conspiracies That Turned Out True - YouTube.png",
        "Centered NYT excerpt; the full passage appears before the tax-status highlight.",
        [
            "Federal authorities ruled that the church's activities were",
            "and it lost its tax-exempt status.",
            "ordered to pay those taxes. Years of",
            "appeals followed and lawsuits flooded the IRS.",
            "From 1973–1977, something was",
        ],
        1,
        "and it lost its tax-exempt status.",
    ),
    centered_shot(
        "13_foia_finkel_zoom",
        "Screenshot 2026-10-25 at 12-47-03 Unsettling Conspiracies That Turned Out True - YouTube.png",
        "Centered, complete FOIA excerpt; marker starts after all words are on screen.",
        [
            "filed a Freedom of Information Act request",
            "Washington Post reporter David Finkel in his book",
        ],
        0,
        "Freedom of Information Act request",
        prefix="filed a ",
    ),
    centered_shot(
        "14_vw_40_times",
        "Screenshot 2026-10-25 at 12-51-15 Unsettling Conspiracies That Turned Out True - YouTube.png",
        "Centered VW emissions excerpt; the full text holds before the yellow phrase sweep.",
        [
            "A May 2014 test led researchers to investigate Volkswagen emissions.",
            "Researchers at West Virginia University tested two VW diesel models.",
            "The cars emitted far more nitrogen oxides than permitted,",
            "up to 40 times the permitted levels.",
        ],
        3,
        "40 times the permitted levels.",
        prefix="up to ",
    ),
]


def main() -> int:
    out_root = HERE.parents[1] / "artifacts" / "web_shots_centered_highlights_v1"
    out_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for shot in SHOTS:
        entries.append(shot.render_all(out_root, write_frames=True))
        print(f"[render] {shot.name}", flush=True)

    contact_sheet([(s.name, Image.open(out_root / e["still"]))
                   for s, e in zip(SHOTS, entries)], out_root / "contact_sheet.jpg")
    manifest = {
        "schema": "chronon.web-shots-centered-highlights.v1",
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "layout": {
            "canvas": [W, H],
            "fps": 30,
            "duration_seconds": 3,
            "font": FONT,
            "font_size": SIZE,
            "camera": "fixed center; no zoom",
            "sequence": "all text fades in together, holds, then highlight sweeps",
        },
        "shots": entries,
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[done] {len(entries)} centered clips -> {out_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
