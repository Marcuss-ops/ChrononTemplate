#!/usr/bin/env python3
"""Contract gates for the Kinetic Type Editorial V1 plan authoring tools."""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
BUILDER_PATH = TEMPLATE / "tools/important_phrases/build_kinetic_type_editorial_v1.py"
SPEC = importlib.util.spec_from_file_location("kinetic_type_editorial_builder", BUILDER_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class KineticTypeEditorialTests(unittest.TestCase):
    def test_exact_palette_typography_background_motion_and_recipe_families(self):
        self.assertEqual(BUILDER.EDITORIAL_COLOR_TOKENS["bg.base.black"], "#050308")
        self.assertEqual(BUILDER.EDITORIAL_COLOR_TOKENS["text.primary.white"], "#F5F3F7")
        self.assertEqual(BUILDER.EDITORIAL_COLOR_TOKENS["accent.yellow"], "#FFD83D")
        self.assertEqual(set(BUILDER.TYPOGRAPHY_TOKENS), {"display_xl", "display_l", "display_hero", "body_m", "label_xs"})
        self.assertGreaterEqual(BUILDER.TYPOGRAPHY_TOKENS["display_hero"]["font_size"], 400)
        self.assertEqual(len(BUILDER.BACKGROUND_PRESETS), 8)
        self.assertEqual(len(BUILDER.TEXT_MOTION_IDS), 10)
        self.assertEqual(len(BUILDER.SCENE_RECIPES), 5)
        self.assertEqual(len(BUILDER.GALLERY_SCENES), 13)
        self.assertTrue(all(preset["seed"] >= 0 for preset in BUILDER.BACKGROUND_PRESETS.values()))
        self.assertTrue(all(3 <= len(preset["blobs"]) <= 8 for preset in BUILDER.BACKGROUND_PRESETS.values()))

    def test_render_plans_are_deterministic_valid_bounded_and_safe(self):
        first = BUILDER.all_plans()
        second = BUILDER.all_plans()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 24)
        plan_ids = [plan["job_id"] for plan in first]
        self.assertEqual(len(plan_ids), len(set(plan_ids)))
        for plan in first:
            with self.subTest(plan=plan["job_id"]):
                BUILDER.validate_plan(plan)
                self.assertLessEqual(len(plan["layers"]), 32)
                self.assertTrue(all(math.isfinite(value) for value in _numeric_values(plan)))
                for layer in plan["layers"]:
                    if layer["type"] == "text":
                        self.assertEqual(layer["style"]["fit_mode"], "shrink_only")
                        self.assertIn(layer["style"]["font"], {BUILDER.FONT_BOLD, BUILDER.FONT_REGULAR})

    def test_all_backgrounds_use_deterministic_soft_textures_and_bounded_motion(self):
        for background_id in BUILDER.BACKGROUND_PRESETS:
            plan = BUILDER.build_background_plan(background_id)
            base = next(layer for layer in plan["layers"] if layer["id"] == "editorial-black-base")
            self.assertEqual(base["color"], BUILDER._rgba(BUILDER.EDITORIAL_COLOR_TOKENS["bg.base.black"]))
            blobs = [layer for layer in plan["layers"] if layer["id"].startswith("aurora-blob-")]
            self.assertEqual(len(blobs), 6)
            for blob in blobs:
                self.assertEqual(blob["type"], "image")
                self.assertTrue((BUILDER.ROOT.parent / blob["asset"]).is_file())
                for track in blob["animation"]["tracks"]:
                    keys = track["keyframes"]
                    self.assertEqual(keys[0]["frame"], 0)
                    self.assertEqual(keys[-1]["frame"], plan["canvas"]["duration_frames"] - 1)
                    values = [key["value"] for key in keys]
                    if background_id not in {"bg_aurora_crossfade", "bg_aurora_focus_swell"}:
                        self.assertAlmostEqual(float(values[0]), float(values[-1]))
                    else:
                        self.assertTrue(all(math.isfinite(float(value)) for value in values))
                    if track["property"] == "opacity":
                        self.assertTrue(all(0.0 <= float(value) <= 1.0 for value in values))

    def test_keyword_span_uses_utf8_byte_offsets_and_semantic_identity(self):
        text = "Élan design feels effortless"
        span = BUILDER._span(text, "effortless", "accent.coral", "word-focus")
        encoded = text.encode("utf-8")
        self.assertEqual(encoded[span["start"]:span["end"]].decode("utf-8"), "effortless")
        self.assertEqual(span["semantic_id"], "word-focus")
        self.assertEqual(span["style"]["color"], BUILDER.EDITORIAL_COLOR_TOKENS["text.primary.white"])
        with self.assertRaises(ValueError):
            BUILDER._span("word word", "word", "accent.coral")

    def test_hero_pop_and_accent_spans_have_measurable_kinetic_amplitude(self):
        hero = BUILDER.build_motion_plan("text_word_pop_focus")
        headline = next(layer for layer in hero["layers"] if layer["id"] == "headline")
        scale = next(track for track in headline["animation"]["tracks"]
                     if track["property"] == "scale")["keyframes"]
        values = [key["value"] for key in scale]
        self.assertGreaterEqual(max(values) / min(values), 10)
        self.assertEqual(values[0], 0.35)
        self.assertEqual(values[-1], 4.6)
        self.assertGreaterEqual(headline["style"]["font_size"], 400)
        self.assertTrue(any(track["property"] == "blur"
                            for animator in headline["text_animators"]
                            for track in animator["properties"]))

        emphasis = BUILDER.build_motion_plan("text_keyword_color_emphasis")
        target = next(layer for layer in emphasis["layers"] if layer.get("spans"))
        semantic = target["spans"][0]["semantic_id"]
        targeted = [animator for animator in target["text_animators"]
                    if animator["selectors"][0].get("semantic_id") == semantic]
        self.assertTrue(any({"scale", "blur", "tracking"}.issubset(
            {track["property"] for track in animator["properties"]}) for animator in targeted))

    def test_text_motion_presets_compile_to_existing_renderer_contract(self):
        expected = {
            "text_word_pop_focus": {"scale", "position_y", "opacity"},
            "text_phrase_soft_rise": {"position_y", "opacity"},
            "text_accent_word_swap": {"opacity"},
            "text_keyword_color_emphasis": {"fill_color"},
            "text_underline_draw": {"opacity", "position_y"},
            "text_word_replace_same_line": {"opacity"},
            "text_large_to_small_handoff": {"scale", "opacity"},
            "text_stagger_phrase_segments": {"position_y", "opacity"},
            "text_trailing_word_reveal": {"opacity"},
            "text_crossfade_phrase": {"opacity"},
        }
        for motion_id, expected_properties in expected.items():
            with self.subTest(motion=motion_id):
                plan = BUILDER.build_motion_plan(motion_id)
                properties = {track["property"]
                              for layer in plan["layers"]
                              for track in layer.get("animation", {}).get("tracks", [])}
                properties.update(track["property"]
                                  for layer in plan["layers"]
                                  for animator in layer.get("text_animators", [])
                                  for track in animator["properties"])
                self.assertTrue(expected_properties.issubset(properties))
                if motion_id in {"text_keyword_color_emphasis", "text_trailing_word_reveal"}:
                    target = next(layer for layer in plan["layers"] if layer.get("spans"))
                    self.assertEqual(len(target["spans"]), 1)
                    self.assertEqual(target["spans"][0]["semantic_id"],
                                     "accent-word" if motion_id == "text_keyword_color_emphasis" else "trailing-word")
                    self.assertEqual(target["text_animators"][0]["selectors"][0]["semantic_id"],
                                     target["spans"][0]["semantic_id"])

    def test_replacement_crossfade_and_gallery_encode_real_opacity_handoffs(self):
        replacement = BUILDER.build_motion_plan("text_word_replace_same_line")
        word_a = next(layer for layer in replacement["layers"] if layer["id"] == "word-a")
        word_b = next(layer for layer in replacement["layers"] if layer["id"] == "word-b")
        a_keys = word_a["animation"]["tracks"][0]["keyframes"]
        b_keys = word_b["animation"]["tracks"][0]["keyframes"]
        self.assertEqual([key["value"] for key in a_keys], [0, 1, 1, 0, 0])
        self.assertEqual([key["value"] for key in b_keys], [0, 0, 1, 1])
        self.assertEqual(a_keys[-2]["frame"], b_keys[-2]["frame"])
        self.assertEqual(a_keys[-2]["value"], 0)
        self.assertEqual(b_keys[-2]["value"], 1)
        self.assertEqual(word_a["position"], word_b["position"])
        b_position_x = next(track for track in word_b["animation"]["tracks"]
                            if track["property"] == "position_x")["keyframes"]
        self.assertGreater(b_position_x[0]["value"], 0)
        self.assertEqual(b_position_x[1]["value"], 0)
        self.assertLess(b_position_x[1]["frame"], b_position_x[2]["frame"])

        crossfade = BUILDER.build_motion_plan("text_crossfade_phrase")
        phrase_a = next(layer for layer in crossfade["layers"] if layer["id"] == "phrase-a")
        phrase_b = next(layer for layer in crossfade["layers"] if layer["id"] == "phrase-b")
        self.assertEqual(phrase_a["animation"]["tracks"][0]["keyframes"][-2]["value"], 0)
        self.assertEqual(phrase_b["animation"]["tracks"][0]["keyframes"][-2]["value"], 1)
        self.assertEqual(phrase_a["position"], phrase_b["position"])
        self.assertGreater(phrase_a["animation"]["tracks"][0]["keyframes"][-2]["frame"],
                           phrase_a["animation"]["tracks"][0]["keyframes"][-3]["frame"])

        gallery = BUILDER.build_gallery_plan()
        gallery_text = [layer for layer in gallery["layers"] if layer["id"].startswith("gallery-")]
        for previous, current in zip(gallery_text, gallery_text[1:]):
            previous_keys = previous["animation"]["tracks"][0]["keyframes"]
            current_keys = current["animation"]["tracks"][0]["keyframes"]
            self.assertEqual(previous_keys[-1]["value"], 0.0)
            self.assertEqual(current_keys[0]["value"], 0.0)
            self.assertLess(previous["start_frame"] + previous_keys[-1]["frame"],
                            current["start_frame"] + current_keys[1]["frame"])

    def test_animator_and_path_trim_keyframes_stay_within_each_layer_lifetime(self):
        for plan in BUILDER.all_plans():
            for layer in plan["layers"]:
                lifetime = layer.get("duration_frames", plan["canvas"]["duration_frames"])
                for animator in layer.get("text_animators", []):
                    for track in animator["properties"]:
                        self.assertTrue(all(0 <= key["frame"] < lifetime
                                            for key in track["keyframes"]))
                for operator in layer.get("shape", {}).get("operators", []):
                    animation = operator.get("params", {}).get("animation")
                    if animation:
                        self.assertTrue(all(0 <= key["frame"] < lifetime
                                            for key in animation["keyframes"]))

    def test_underline_draw_has_luminous_gpu_stroke_with_overshoot(self):
        plan = BUILDER.build_motion_plan("text_underline_draw")
        underline = next(layer for layer in plan["layers"] if layer["id"] == "keyword-underline")
        self.assertEqual(underline["shape"]["type"], "rounded_rect")
        scale = next(track for track in underline["animation"]["tracks"]
                     if track["property"] == "scale_x")["keyframes"]
        self.assertEqual(scale[0]["value"], 0.0)
        self.assertEqual(scale[1]["value"], 1.12)
        self.assertEqual(scale[2]["value"], 1.0)
        halo = next(layer for layer in plan["layers"]
                    if layer["id"] == "keyword-underline-afterglow")
        self.assertGreater(halo["size"][1], underline["size"][1])
        halo_opacity = next(track for track in halo["animation"]["tracks"]
                            if track["property"] == "opacity")["keyframes"]
        self.assertGreater(halo_opacity[1]["value"], halo_opacity[-1]["value"])

    def test_five_scene_recipes_have_single_background_owner_and_resolve_components(self):
        self.assertEqual(set(BUILDER.SCENE_RECIPES), {
            "recipe_editorial_hero_word", "recipe_editorial_statement",
            "recipe_editorial_underline", "recipe_editorial_progressive_concept",
            "recipe_editorial_large_to_secondary",
        })
        for recipe_id, recipe in BUILDER.SCENE_RECIPES.items():
            with self.subTest(recipe=recipe_id):
                plan = BUILDER.build_recipe_plan(recipe_id)
                base = next(layer for layer in plan["layers"] if layer["id"] == "editorial-black-base")
                self.assertEqual(base["color"], BUILDER._rgba(BUILDER.EDITORIAL_COLOR_TOKENS["bg.base.black"]))
                self.assertIn("editorial-black-base", {layer["id"] for layer in plan["layers"]})
                self.assertLessEqual(len(plan["layers"]), 32)
        underline = BUILDER.build_recipe_plan("recipe_editorial_underline")
        self.assertIn("keyword-underline", {layer["id"] for layer in underline["layers"]})
        large = BUILDER.build_recipe_plan("recipe_editorial_large_to_secondary")
        self.assertEqual({layer["id"] for layer in large["layers"]} & {"hero-word", "secondary-phrase"},
                         {"hero-word", "secondary-phrase"})

    def test_gallery_has_all_reference_phrases_with_safe_overlapped_scene_handoffs(self):
        plan = BUILDER.build_gallery_plan()
        self.assertEqual(plan["job_id"], "editorial_typography_gallery_v1")
        self.assertEqual(plan["canvas"]["duration_frames"], 12 * (54 - 12) + 54)
        text_layers = [layer for layer in plan["layers"] if layer.get("id", "").startswith("gallery-")]
        self.assertEqual(len(text_layers), 13)
        self.assertEqual([layer["text"] for layer in text_layers],
                         [scene[1] for scene in BUILDER.GALLERY_SCENES])
        for previous, current in zip(text_layers, text_layers[1:]):
            previous_start = previous["start_frame"]
            current_start = current["start_frame"]
            self.assertLess(current_start, previous_start + previous["duration_frames"])
            self.assertEqual(previous["position"], current["position"])
        design = next(layer for layer in text_layers if layer["id"] == "gallery-design_is_intelligence")
        gradient_parts = [span for span in design["spans"]
                          if span["semantic_id"].startswith("gradient-design-")]
        self.assertEqual(len(gradient_parts), 3)
        self.assertEqual([part["end"] - part["start"] for part in gradient_parts], [2, 2, 2])
        self.assertEqual(len([animator for animator in design["text_animators"]
                              if animator["id"].startswith("gradient-design-")]), 3)

    def test_catalog_family_ids_are_complete_and_plans_remain_renderer_native(self):
        plans = BUILDER.all_plans()
        motion_plans = [plan for plan in plans if plan["job_id"].startswith("canary_text_")]
        background_plans = [plan for plan in plans if plan["job_id"].startswith("canary_bg_")]
        recipe_plans = [plan for plan in plans if plan["job_id"].startswith("canary_recipe_")]
        self.assertEqual(len(motion_plans), 10)
        self.assertEqual(len(background_plans), 8)
        self.assertEqual(len(recipe_plans), 5)
        self.assertEqual(sum(plan["job_id"] == "editorial_typography_gallery_v1" for plan in plans), 1)
        self.assertTrue(all(plan["schema"] == "chronon.render-plan.v3" for plan in plans))
        self.assertFalse(any("glyph" in layer["id"] or "glyphs" in layer["id"]
                             for plan in plans for layer in plan["layers"]))


def _numeric_values(value):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _numeric_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _numeric_values(item)


if __name__ == "__main__":
    unittest.main()
