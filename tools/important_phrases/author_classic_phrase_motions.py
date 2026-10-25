#!/usr/bin/env python3
"""Author the Classic Apple long-phrase motions.

The short-phrase family animates one short line; these five recipes re-author
its restrained vocabulary for wrapped copy of up to three lines, with the
Classic Apple look the pack renders: Playfair Display static, near-black ink
on a white canvas (catalog/classic_phrase_style.v1.json).

Each recipe is one text animator over a reveal window, exactly what
Chronon3D's canonical GPU text contract lowers (see
can_lower_gpu_text_animation), and the visible difference between them is:

    baseline_rise    the block rises while words snap in front-loaded
    tracking_close   lines gather as the tracking closes and the block settles
    focus_resolve    a glyph-fast burst settling out of a slight over-scale
    quiet_zoom       a delayed, very slow push-in with an even line-by-line fade
    glyph_curtain    lines drop in from above on a hard, square cut

`pace` and `delay` shape the selector sweep; the emitter bakes them per frame
because Chronon's plan tracks are linear-only.

It is idempotent: rows are replaced in place, so re-running after a catalog
refresh restores the family.

Usage:
    tools/important_phrases/author_classic_phrase_motions.py
    tools/important_phrases/author_classic_phrase_motions.py --check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog/motion_catalog.v1.json"
STYLE = ROOT / "catalog/classic_phrase_style.v1.json"

CATEGORY = "apple_v2"


def track(prop, keys, easing="out_cubic"):
    return {
        "property": prop,
        "keyframes": [{"frame": f, "value": v} for f, v in keys],
        "easing": easing,
    }


def reveal(unit, pace, delay, enter, shape="smooth", extra=()):
    """The hidden value + the window sweep that reveals the phrase.

    Extra properties ride the same selector, so they act on each unit exactly
    while it joins the phrase (the tracking close only exists during the
    fade-in, which is where the eye reads it).
    """
    return {
        "id": "reveal",
        "selector": {
            "kind": unit,
            "shape": shape,
            "order": "forward",
            "stagger": 1,
            "pace": pace,
            "delay": delay,
            "enter": enter,
        },
        "properties": [
            *extra,
            track("opacity", [(0, 0.0), (1, 0.0)], "linear"),
        ],
    }


def motion(mid, title, unit, enter, tracks, animator):
    return {
        "id": mid,
        "title": title,
        "category": CATEGORY,
        "targets": ["text", "phrase"],
        "unit": unit,
        "enter": enter,
        "exit": 14,
        "tracks": tracks,
        "text_animators": [animator],
        "render_safe": True,
    }


RECIPES = [
    motion(
        "classic_playfair_baseline_rise",
        "Classic Baseline Rise",
        "word",
        72,
        [
            track("position_y", [(0, 30.0), (26, 0.0)]),
            track("opacity", [(0, 0.0), (18, 1.0)], "linear"),
        ],
        reveal("word", "out_cubic", 8, 64),
    ),
    motion(
        "classic_playfair_tracking_close",
        "Classic Tracking Close",
        "line",
        72,
        [
            track("scale", [(0, 1.03), (46, 1.0)]),
            track("opacity", [(0, 0.0), (20, 1.0)], "linear"),
        ],
        reveal("line", "in_out_sine", 4, 66,
               extra=[track("tracking", [(0, 14.0), (52, 0.0)])]),
    ),
    motion(
        "classic_playfair_focus_resolve",
        "Classic Focus Resolve",
        "glyph",
        72,
        [
            track("scale", [(0, 1.04), (44, 1.0)]),
            track("opacity", [(0, 0.0), (14, 1.0)], "linear"),
        ],
        reveal("glyph", "out_expo", 2, 68),
    ),
    motion(
        "classic_playfair_quiet_zoom",
        "Classic Quiet Zoom",
        "word",
        72,
        [
            track("scale", [(0, 0.955), (54, 1.0)], "in_out_cubic"),
            track("opacity", [(0, 0.0), (30, 1.0)], "linear"),
        ],
        reveal("word", "in_out_cubic", 18, 72),
    ),
    motion(
        "classic_playfair_glyph_curtain",
        "Classic Glyph Curtain",
        "line",
        72,
        [
            track("position_y", [(0, -26.0), (24, 0.0)]),
            track("opacity", [(0, 0.0), (12, 1.0)], "linear"),
        ],
        reveal("line", "out_cubic", 0, 48, shape="square"),
    ),
    # ── The wider Apple-like set ─────────────────────────────────────────
    # Same family window, same renderer contract (one animator, one selector,
    # no per-unit blur, no layer tracking), different editorial gesture.
    motion(
        "classic_playfair_word_lift",
        "Classic Word Lift",
        "word",
        72,
        [track("opacity", [(0, 0.0), (10, 1.0)], "linear")],
        reveal("word", "out_cubic", 2, 66,
               extra=[track("position_y", [(0, 20.0), (64, 0.0)])]),
    ),
    motion(
        "classic_playfair_line_float",
        "Classic Line Float",
        "line",
        72,
        [
            track("position_y", [(0, -14.0), (36, 0.0)]),
            track("opacity", [(0, 0.0), (20, 1.0)], "linear"),
        ],
        reveal("line", "in_out_sine", 10, 72),
    ),
    motion(
        "classic_playfair_soft_push_in",
        "Classic Soft Push In",
        "word",
        72,
        [
            track("scale", [(0, 1.06), (46, 1.0)], "in_out_cubic"),
            track("opacity", [(0, 0.0), (18, 1.0)], "linear"),
        ],
        reveal("word", "out_cubic", 14, 72),
    ),
    motion(
        "classic_playfair_hero_settle",
        "Classic Hero Settle",
        "line",
        72,
        [
            track("scale", [(0, 0.94), (40, 1.0)]),
            track("opacity", [(0, 0.0), (16, 1.0)], "linear"),
        ],
        reveal("line", "out_cubic", 8, 72),
    ),
    motion(
        "classic_playfair_depth_push",
        "Classic Depth Push",
        "line",
        72,
        [
            track("scale", [(0, 1.12), (50, 1.0)]),
            track("opacity", [(0, 0.0), (22, 1.0)], "linear"),
        ],
        reveal("line", "out_quad", 6, 70),
    ),
    motion(
        "classic_playfair_tracking_open",
        "Classic Tracking Open",
        "word",
        72,
        [
            track("scale", [(0, 1.02), (40, 1.0)]),
            track("opacity", [(0, 0.0), (14, 1.0)], "linear"),
        ],
        reveal("word", "out_expo", 4, 68,
               extra=[track("tracking", [(0, 10.0), (60, 0.0)])]),
    ),
    motion(
        "classic_playfair_glyph_glide",
        "Classic Glyph Glide",
        "glyph",
        72,
        [track("opacity", [(0, 0.0), (12, 1.0)], "linear")],
        reveal("glyph", "in_out_sine", 0, 58,
               extra=[track("position_x", [(0, 20.0), (66, 0.0)])]),
    ),
    motion(
        "classic_playfair_letter_tick",
        "Classic Letter Tick",
        "glyph",
        72,
        [track("opacity", [(0, 0.0), (8, 1.0)], "linear")],
        reveal("glyph", "linear", 0, 54, shape="square"),
    ),
    motion(
        "classic_playfair_breath_in",
        "Classic Breath In",
        "glyph",
        72,
        [
            track("scale", [(0, 0.98), (56, 1.0)], "in_out_cubic"),
            track("opacity", [(0, 0.0), (34, 1.0)], "linear"),
        ],
        reveal("glyph", "in_out_expo", 20, 72),
    ),
    motion(
        "classic_playfair_quiet_dissolve",
        "Classic Quiet Dissolve",
        "word",
        72,
        [
            track("position_y", [(0, 8.0), (40, 0.0)], "in_out_cubic"),
            track("opacity", [(0, 0.0), (36, 1.0)], "linear"),
        ],
        reveal("word", "in_out_sine", 26, 72),
    ),
]


def validate(recipe: dict) -> None:
    """The emitter's fail-closed rules, restated so bad data fails here first."""
    seen = -1
    for t in recipe["tracks"]:
        frames = [k["frame"] for k in t["keyframes"]]
        if frames[0] != 0 or any(b <= a for a, b in zip(frames, frames[1:])):
            raise SystemExit(f"{recipe['id']}: {t['property']} keyframes must start at 0 and increase")
        if t["property"] in ("scale", "opacity") and t["keyframes"][-1]["value"] != 1:
            raise SystemExit(f"{recipe['id']}: {t['property']} must rest at 1")
        if t["property"] in ("position_x", "position_y") and t["keyframes"][-1]["value"] != 0:
            raise SystemExit(f"{recipe['id']}: {t['property']} must rest at 0")
        if t["property"] == "blur" and t["keyframes"][-1]["value"] != 0:
            raise SystemExit(f"{recipe['id']}: blur must rest at 0")
        if t["property"] == "tracking" and t["keyframes"][-1]["value"] != 0:
            raise SystemExit(f"{recipe['id']}: tracking must rest at 0")
        seen = max(seen, frames[-1])
    for animator in recipe["text_animators"]:
        for t in animator["properties"]:
            frames = [k["frame"] for k in t["keyframes"]]
            if frames[0] != 0 or any(b <= a for a, b in zip(frames, frames[1:])):
                raise SystemExit(
                    f"{recipe['id']}: animator {t['property']} keyframes must start at 0 and increase"
                )
            seen = max(seen, frames[-1])
    if seen > recipe["enter"]:
        raise SystemExit(f"{recipe['id']}: a track outlives the entrance ({seen} > {recipe['enter']})")
    selector = recipe["text_animators"][0]["selector"]
    if selector["delay"] + 1 >= selector["enter"]:
        raise SystemExit(f"{recipe['id']}: the reveal window is empty")
    if selector["enter"] > recipe["enter"]:
        raise SystemExit(f"{recipe['id']}: the reveal outlives the entrance")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 unless every recipe is present")
    args = parser.parse_args()

    style = json.loads(STYLE.read_text())
    if style["background"][:3] != [1.0, 1.0, 1.0]:
        raise SystemExit("the Classic style must rest on a white canvas")

    for recipe in RECIPES:
        validate(recipe)

    catalog = json.loads(CATALOG.read_text())
    rows = catalog["motions"]
    by_id = {row["id"]: index for index, row in enumerate(rows)}
    missing = [r["id"] for r in RECIPES if r["id"] not in by_id]
    if args.check:
        if missing:
            raise SystemExit(f"missing Classic Apple motions: {', '.join(missing)}")
        stale = [r["id"] for r in RECIPES if rows[by_id[r["id"]]] != r]
        if stale:
            raise SystemExit(f"stale Classic Apple motions: {', '.join(stale)}")
        print(f"{len(RECIPES)} Classic Apple motions are authored")
        return

    for recipe in RECIPES:
        if recipe["id"] in by_id:
            rows[by_id[recipe["id"]]] = recipe
        else:
            rows.append(recipe)

    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"authored {len(RECIPES)} Classic Apple motions in {CATALOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
