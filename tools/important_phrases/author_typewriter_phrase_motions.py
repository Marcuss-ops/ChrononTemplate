#!/usr/bin/env python3
"""Author the typewriter motions into the phrase pool.

The eight recipes are the ones rendered into the Typewriter Pack v1 clips, but
expressed as *animation only*: no font, no size, no colour, no caret. Those
belong to the runtime, which picks them per job (overlay_style), so a pool entry
that carried them would override the user's typography. What is left here is the
gesture: which unit steps forward, how fast, with which reveal edge, and whether
the line pushes in as it starts.

Two things the clips do stay out, because the pool contract cannot express them
and a motion that fakes them would render wrong: the caret (decoration, and the
runtime owns it) and the erase pass. Erasing needs a selector window that
closes — `end` sweeping 100 -> 0 — while every lowerer anchors the window at
100 and sweeps `start`, so a reverse-order animator hides the whole line from
frame one instead of removing it at the end.

They land in `catalog/motion_catalog.v1.json`, which `emit_catalog` projects into
`chronontemplate_catalog.v1.json` — the document RenderingGen embeds and draws
from. The split the user asked for is carried by `targets`, because that is what
the renderer's inventory reads:

    targets ["text","phrase","short_phrase"]  -> the short-phrase pool
    targets ["text","phrase"]                 -> the long/important-phrase pool

A motion tagged `short_phrase` appears only in the short pool (the inventory
groups it there), and an untagged phrase motion appears only in the long one, so
the two families never mix.

Timing is derived with the pack emitter's own schedule (start_sec, frames per
char, type budget over 192 frames at 24 fps), so the pool entry and the rendered
clip step forward at the same moments.

Idempotent: rows are replaced in place, so re-running after a catalog refresh
restores the family.

Usage:
    tools/important_phrases/author_typewriter_phrase_motions.py
    tools/important_phrases/author_typewriter_phrase_motions.py --check
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog/motion_catalog.v1.json"

CATEGORY = "typewriter_phrase_v1"

# The clip envelope the pack renders: 8 s at 24 fps.
DURATION_FRAMES = 192
FPS = 24


def track(prop, keys, easing="linear"):
    return {
        "property": prop,
        "keyframes": [{"frame": f, "value": v} for f, v in keys],
        "easing": easing,
    }


def schedule(phrase, frames_per_char, start_sec, type_budget):
    """The pack emitter's typing schedule: start frame and the frame the sweep ends.

    The emitter sizes the typing by the phrase's codepoint count regardless of
    the selector unit (a word selector still sweeps over the same characters),
    so the pool entry steps forward on the frames the rendered clips do.
    """

    units = len(phrase)
    start = int(round(start_sec * FPS))
    budget = int(round(type_budget * DURATION_FRAMES))
    natural = int(round(units * frames_per_char))
    span = max(8, min(natural, budget))
    return start, min(DURATION_FRAMES - 6, start + span)


def reveal(unit, shape, pace, delay, enter):
    """The typing sweep: every unit ahead of the leading edge stays hidden.

    `opacity` pins the animator's hidden value at 0 and the selector walks the
    edge forward, so a unit joins the phrase the frame the edge passes it and
    keeps the layer's own style from then on. Nothing here describes what the
    text looks like.
    """

    return {
        "id": "typing",
        "selector": {
            "kind": unit,
            "shape": shape,
            "order": "forward",
            "stagger": 1,
            "pace": pace,
            "delay": delay,
            "enter": enter,
        },
        "properties": [track("opacity", [(0, 0.0), (1, 0.0)], "linear")],
    }


def motion(mid, title, fit, unit, phrase, frames_per_char, start_sec, type_budget,
           shape="square", pace="linear", tracks=(), extra_animators=(), timing=None):
    # `timing` carries the (start, sweep end) measured on the rendered pack plan
    # for this recipe. Wrapping drops trailing spaces, so the emitter's char
    # count is one or two short of len(phrase) on the wrapped lines; the pool
    # entry uses the frames the clip actually steps on.
    start, sweep_end = timing or schedule(phrase, frames_per_char, start_sec, type_budget)
    targets = ["text", "phrase"]
    if fit == "short":
        targets.append("short_phrase")
    animators = [reveal(unit, shape, pace, start, sweep_end), *extra_animators]
    enter = max(sweep_end, *(a["selector"]["enter"] for a in animators))
    return {
        "id": mid,
        "title": title,
        "category": CATEGORY,
        "targets": targets,
        "unit": unit,
        "enter": enter,
        "exit": 14,
        "tracks": list(tracks),
        "text_animators": animators,
        "render_safe": True,
    }


RECIPES = [
    motion(
        "typewriter_glyph_square_short",
        "Typewriter Glyph Square (short)",
        "short",
        "glyph",
        "OGNI DETTAGLIO CONTA",
        1.6, 0.42, 0.55,
        timing=(10, 42),
    ),
    motion(
        "typewriter_glyph_wrap_long",
        "Typewriter Glyph Wrap (long)",
        "long",
        "glyph",
        "NON È IL COLPO A DECIDERE LA PARTITA, MA IL MODO IN CUI SCEGLI DI RACCONTARLO.",
        1.35, 0.42, 0.60,
        timing=(10, 113),
    ),
    motion(
        "typewriter_soft_edge_long",
        "Typewriter Soft Edge (long)",
        "long",
        "glyph",
        "Il silenzio, prima della verità, è la parte più difficile da montare.",
        1.5, 0.40, 0.62,
        shape="smooth",
        timing=(10, 112),
    ),
    motion(
        "typewriter_impact_push_short",
        "Typewriter Impact Push (short)",
        "short",
        "glyph",
        "TUTTO CAMBIA IN UN FRAME",
        1.9, 0.30, 0.50,
        pace="out_cubic",
        timing=(7, 53),
        tracks=[
            track("scale", [(0, 1.06), (26, 1.0)]),
            track("opacity", [(0, 0.0), (18, 1.0)], "linear"),
        ],
    ),
    motion(
        "typewriter_slow_type_short",
        "Typewriter Slow Type (short)",
        "short",
        "glyph",
        "ORA LO VEDI.",
        3.4, 0.14, 0.34,
        timing=(3, 44),
    ),
    motion(
        "typewriter_terminal_block_long",
        "Typewriter Terminal Block (long)",
        "long",
        "glyph",
        "SIGNAL LOCKED // ARCHIVIO 1987 // LA TRASMISSIONE È IN CORSO",
        1.25, 0.46, 0.58,
        timing=(11, 85),
    ),
    motion(
        "typewriter_editorial_line_long",
        "Typewriter Editorial Line (long)",
        "long",
        "glyph",
        "La verità è un dettaglio che nessuno aveva notato.",
        1.3, 0.42, 0.58,
        timing=(10, 74),
    ),
    motion(
        "typewriter_word_burst_short",
        "Typewriter Word Burst (short)",
        "short",
        "word",
        "NESSUN DETTAGLIO È CASUALE",
        0.85, 0.36, 0.52,
        pace="out_cubic",
        timing=(9, 31),
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
        seen = max(seen, frames[-1])
    for animator in recipe["text_animators"]:
        selector = animator["selector"]
        if selector["kind"] not in ("glyph", "word", "line"):
            raise SystemExit(f"{recipe['id']}: unsupported selector unit {selector['kind']}")
        if selector["shape"] not in ("square", "smooth"):
            raise SystemExit(f"{recipe['id']}: unsupported selector shape {selector['shape']}")
        if selector["order"] not in ("forward", "reverse"):
            raise SystemExit(f"{recipe['id']}: unsupported selector order {selector['order']}")
        if selector["delay"] + 1 >= selector["enter"]:
            raise SystemExit(f"{recipe['id']}: {animator['id']} window is empty")
        if selector["enter"] > recipe["enter"]:
            raise SystemExit(f"{recipe['id']}: {animator['id']} outlives the motion window")
        for t in animator["properties"]:
            if t["property"] not in ("opacity", "position_x", "position_y", "scale", "tracking"):
                raise SystemExit(f"{recipe['id']}: unsupported animator property {t['property']}")
            frames = [k["frame"] for k in t["keyframes"]]
            if frames[0] != 0 or any(b <= a for a, b in zip(frames, frames[1:])):
                raise SystemExit(
                    f"{recipe['id']}: animator {t['property']} keyframes must start at 0 and increase"
                )
            seen = max(seen, frames[-1])
    if seen > recipe["enter"]:
        raise SystemExit(f"{recipe['id']}: a track outlives the entrance ({seen} > {recipe['enter']})")
    if not recipe["tracks"] and recipe["unit"] not in ("glyph", "word"):
        raise SystemExit(f"{recipe['id']}: unsupported unit {recipe['unit']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 unless every recipe is present")
    args = parser.parse_args()

    for recipe in RECIPES:
        validate(recipe)
        if not 0 <= recipe["enter"] < DURATION_FRAMES:
            raise SystemExit(f"{recipe['id']}: entrance {recipe['enter']} leaves the clip")

    catalog = json.loads(CATALOG.read_text())
    rows = catalog["motions"]
    by_id = {row["id"]: index for index, row in enumerate(rows)}
    missing = [r["id"] for r in RECIPES if r["id"] not in by_id]
    if args.check:
        if missing:
            raise SystemExit(f"missing typewriter motions: {', '.join(missing)}")
        stale = [r["id"] for r in RECIPES if rows[by_id[r["id"]]] != r]
        if stale:
            raise SystemExit(f"stale typewriter motions: {', '.join(stale)}")
        print(f"{len(RECIPES)} typewriter motions are authored")
        return

    for recipe in RECIPES:
        if recipe["id"] in by_id:
            rows[by_id[recipe["id"]]] = recipe
        else:
            rows.append(recipe)

    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"authored {len(RECIPES)} typewriter motions in {CATALOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
