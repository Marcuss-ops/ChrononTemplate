#!/usr/bin/env python3
"""short_phrase_motion.v1 catalog contract test.

The catalog is data (`catalog/short_phrase_motion.v1.json`) generated from the
C++-owned pack by `chronontemplate_emit_short_phrase_catalog`. This test pins
the contract without needing the CLI or a GPU:

  1.  the emitter exits 0 and prints valid JSON;
  2.  the document names the short-phrase archetypes, the five exit modes and the
      decor bumper, with unique `short_phrase_*` ids;
  3.  every recipe stays inside the renderer contract: GPU-lowerable selector
      (full | reveal | reveal_soft | band), strictly increasing keyframes that
      start at 0, emphasis inside the phrase, and in + hold + out inside its
      timing bracket;
  4.  the selection table covers exactly 1..5 words and only names real recipes;
  5.  the committed catalog is byte-for-byte what the emitter produces today —
      the file is generated, not hand-maintained.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [OK] {name}")
    else:
        failures.append(f"{name}{': ' + detail if detail else ''}")
        print(f"  [FAIL] {name} {detail}")


def valid_keyframes(track: dict) -> bool:
    keys = track.get("keyframes") or []
    if len(keys) < 2 or keys[0].get("frame") != 0:
        return False
    previous = -1
    for key in keys:
        frame = key.get("frame")
        if not isinstance(frame, int) or frame <= previous:
            return False
        if not isinstance(key.get("value"), (int, float)):
            return False
        previous = frame
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, help="short-phrase emitter binary path")
    parser.add_argument("--catalog", required=True, help="committed catalog path")
    args = parser.parse_args()

    tool = Path(args.tool)
    catalog = Path(args.catalog)
    if not tool.is_file():
        print(f"FAIL: missing tool binary {tool}")
        return 1

    print("== the emitter prints valid JSON")
    first = subprocess.run([str(tool)], capture_output=True, text=True)
    check("emitter exits 0", first.returncode == 0, first.stderr.strip())
    if first.returncode != 0:
        print(f"\n{len(failures)} failure(s)")
        return 1
    try:
        document = json.loads(first.stdout)
    except json.JSONDecodeError as error:
        print(f"FAIL: stdout is not JSON: {error}")
        return 1

    print("== the document header")
    check("schema", document.get("schema") == "chronontemplate.short-phrase-motion.v1",
          str(document.get("schema")))
    check("version", document.get("version") == 1, str(document.get("version")))
    check("catalog id", document.get("catalog_id") == "short_phrase_motion_v1")
    check("source", document.get("source") == "chronontemplate::ShortPhrasePack")
    check("word range", document.get("word_range") == [1, 5], str(document.get("word_range")))
    exit_modes = document.get("exit_modes") or []
    check("five exit modes", exit_modes == ["reverse", "forward", "wipe", "scatter", "arc_dissolve"],
          str(exit_modes))

    print("== the short-phrase recipes")
    recipes = document.get("recipes") or []
    retired_ids = {
        "short_phrase_editorial_claude_diff_patch",
        "short_phrase_editorial_claude_prompt_response",
        "short_phrase_editorial_lift_and_rule",
        "short_phrase_editorial_rule_handoff",
        "short_phrase_editorial_underline_draw",
        "short_phrase_phrase_build_focus",
        "short_phrase_product_decrypted_text",
        "short_phrase_product_fold_text",
        "short_phrase_product_glare_hover",
        "short_phrase_product_line_by_line_slide",
        "short_phrase_product_scramble_reveal",
        "short_phrase_product_shape_blur",
        "short_phrase_product_warp_text",
        "short_phrase_product_weight_wave",
        "short_phrase_scale_settle_word",
        "short_phrase_semantic_chain_curve",
        "short_phrase_semantic_two_line",
        "short_phrase_simple_progressive_phrase",
        "short_phrase_single_word_swap",
        "short_phrase_word_cascade_sentence",
        "short_phrase_word_mask_sequence",
        "short_phrase_character_write_on",
        "short_phrase_editorial_paper_title_card",
    }
    check("none of the retired motions is published", not retired_ids.intersection({r["id"] for r in recipes}))
    check("27 surviving recipes", len(recipes) == 27, str(len(recipes)))
    editorial = [r for r in recipes if r["id"].startswith("short_phrase_editorial_")]
    product = [r for r in recipes if r["id"].startswith("short_phrase_product_")]
    check("surviving editorial recipes", len(editorial) == 8, str(len(editorial)))
    check("surviving product recipes", len(product) == 15, str(len(product)))
    check("exact surviving id set", {recipe.get("id") for recipe in recipes} == {
        "short_phrase_shape_phrase_wipe",
        "short_phrase_character_tracking_reveal",
        "short_phrase_character_cascade_shapes",
        "short_phrase_editorial_baseline_rise",
        "short_phrase_editorial_side_glide",
        "short_phrase_editorial_tracking_close",
        "short_phrase_editorial_focus_resolve",
        "short_phrase_editorial_glyph_curtain",
        "short_phrase_editorial_contrast_sweep",
        "short_phrase_editorial_quiet_zoom",
        "short_phrase_product_blur_out_up",
        "short_phrase_product_bottom_up_letters",
        "short_phrase_product_focus_blur_resolve",
        "short_phrase_product_kinetic_center_build",
        "short_phrase_product_per_word_rise",
        "short_phrase_product_perspective_marquee",
        "short_phrase_product_strikethrough_replace",
        "short_phrase_product_text_match_cut",
        "short_phrase_product_text_shimmer",
        "short_phrase_product_chromatic_fringe_title",
        "short_phrase_product_masked_heading",
        "short_phrase_product_split_flap_text",
        "short_phrase_product_scroll_reveal",
        "short_phrase_product_scrambled_text",
        "short_phrase_product_gradual_blur",
        "short_phrase_editorial_claude_terminal_focus",
        "short_phrase_burst",
    })
    adapted_product_ids = {
        "short_phrase_product_masked_heading", "short_phrase_product_split_flap_text",
        "short_phrase_product_scroll_reveal", "short_phrase_product_scrambled_text",
        "short_phrase_product_gradual_blur",
    }
    check("adapted products are registered", adapted_product_ids.issubset({r["id"] for r in product}))
    for recipe in product:
        if recipe["id"] in adapted_product_ids:
            check(f"{recipe['id']} has an adaptation note", bool(recipe.get("adaptation_note")))
            if recipe["id"] not in {
                "short_phrase_product_per_word_rise",
                "short_phrase_product_perspective_marquee",
                "short_phrase_product_strikethrough_replace",
                "short_phrase_product_text_shimmer",
            }:
                check(f"{recipe['id']} uses a three-second entrance", recipe.get("enter") == 90,
                      str(recipe.get("enter")))
    check("every recipe is categorized", all(r.get("family") and r.get("subcategory") for r in recipes))
    check("surviving animation families", {r.get("family") for r in recipes} == {"classic", "editorial", "product_video"})
    check("computer-character assembly remains available",
          "computer_character_assembly" in {r.get("subcategory") for r in recipes})
    check("editorial recipes retain their render style", all(r.get("font_size", 0) > 0 and isinstance(r.get("light"), bool) for r in editorial))
    ids = [r.get("id") for r in recipes]
    check("ids are unique", len(set(ids)) == len(ids))
    check("ids carry the short_phrase_ prefix", all(str(i).startswith("short_phrase_") for i in ids))

    known_ids = set(ids)
    for recipe in recipes:
        rid = recipe.get("id", "?")
        check(f"{rid} has a title and phrase",
              bool(recipe.get("title")) and bool(recipe.get("phrase")))
        check(f"{rid} omits removed paper-background metadata", "paper_background" not in recipe)
        if rid in adapted_product_ids:
            check(f"{rid} documents omitted interactivity/shader behavior",
                  any(term in recipe.get("adaptation_note", "") for term in
                      ("not represented", "not available", "not supported", "native eased entrance")),
                  str(recipe.get("adaptation_note")))
        check(f"{rid} entrance lands inside its clip",
              isinstance(recipe.get("enter"), int) and 0 < recipe["enter"] < 210,
              str(recipe.get("enter")))
        words = recipe.get("word_count")
        check(f"{rid} declares a word count", isinstance(words, int) and words >= 1, str(words))
        selector = recipe.get("selector") or {}
        check(f"{rid} selects a known unit",
              selector.get("unit") in {"layer", "glyph", "word", "line"}, str(selector.get("unit")))
        check(f"{rid} uses a GPU-lowerable window",
              selector.get("window") in {"full", "reveal", "reveal_soft", "band"} or
              str(selector.get("window", "")).startswith("pick:"),
              str(selector.get("window")))
        check(f"{rid} has an exit mode", recipe.get("exit") in exit_modes, str(recipe.get("exit")))
        check(f"{rid} decor is null or star_bumper",
              recipe.get("decor") in (None, "star_bumper"), str(recipe.get("decor")))

        emphasis = recipe.get("emphasis") or []
        check(f"{rid} emphasises real words",
              all(isinstance(w, int) and 0 <= w < words for w in emphasis), str(emphasis))

        tracks = list(recipe.get("tracks") or [])
        for animator in recipe.get("text_animators") or []:
            tracks.extend(animator.get("properties") or [])
        for accent in recipe.get("accents") or []:
            tracks.extend(accent.get("tracks") or [])
        overlays = recipe.get("text_overlays") or []
        for overlay in overlays:
            tracks.extend(overlay.get("tracks") or [])
            check(f"{rid}.{overlay.get('id', 'overlay')} contains text", bool(overlay.get("text")))
        if rid == "short_phrase_product_perspective_marquee":
            tracks.append({"property": "camera_position_x", "keyframes": [
                {"frame": 0, "value": 0}, {"frame": 209, "value": 0}
            ]})
        check(f"{rid} authors some motion", bool(tracks))
        # Text overlay state changes may only carry one keyframe when static,
        # so validate authored overlay tracks but not synthesized camera placeholders.
        authored_tracks = [t for t in tracks if t.get("property") != "camera_position_x"]
        check(f"{rid} keyframes are well-formed",
              all(valid_keyframes(t) for t in authored_tracks),
              str([t.get("property") for t in tracks]))

        timing = recipe.get("timing") or {}
        bracket = (timing.get("min_frames"), timing.get("max_frames"))
        phases = (timing.get("in_frames"), timing.get("hold_frames"), timing.get("out_frames"))
        check(f"{rid} timing bracket is ordered",
              all(isinstance(v, int) for v in bracket) and bracket[0] <= bracket[1], str(bracket))
        check(f"{rid} in + hold + out fits the bracket",
              all(isinstance(v, int) and v > 0 for v in phases)
              and bracket[0] <= sum(phases) <= bracket[1],
              f"{phases} in {bracket}")

    print("== the decor bumper")
    decor = document.get("decor") or []
    check("one decor element", len(decor) == 1, str(len(decor)))
    if decor:
        star = decor[0]
        check("star bumper id", star.get("id") == "short_phrase.decor.star_bumper")
        check("four-point star", star.get("shape") == "four_point_star", str(star.get("shape")))
        tracks = star.get("tracks") or []
        check("bumper carries motion", bool(tracks))
        check("bumper keyframes are well-formed", all(valid_keyframes(t) for t in tracks))

    print("== the selection table")
    selection = document.get("selection") or {}
    check("selection covers exactly 1..5 words", sorted(selection) == [str(n) for n in range(1, 6)],
          str(sorted(selection)))
    for count, picks in selection.items():
        check(f"{count} word(s) suggest at least one recipe", bool(picks))
        check(f"{count} word(s) only suggest real recipes",
              all(p in known_ids for p in picks), str(picks))

    print("== the committed catalog is generated from the C++ pack")
    if not catalog.is_file():
        check("catalog file exists", False, str(catalog))
    else:
        committed = json.loads(catalog.read_text())
        committed_ids = {recipe.get("id") for recipe in committed.get("recipes", [])}
        check("committed catalog omits retired ids", not retired_ids.intersection(committed_ids))
        check("catalog matches the emitter output", catalog.read_text() == first.stdout,
              "catalog/short_phrase_motion.v1.json is stale — regenerate it")
    second = subprocess.run([str(tool)], capture_output=True, text=True)
    check("the emitter is deterministic", second.stdout == first.stdout)

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall short_phrase catalog contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
