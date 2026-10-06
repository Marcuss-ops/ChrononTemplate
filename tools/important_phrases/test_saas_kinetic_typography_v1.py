#!/usr/bin/env python3
"""Contract tests for the SaaS Kinetic Typography V1 plan pack."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_saas_kinetic_typography_v1.py")
SPEC = importlib.util.spec_from_file_location("saas_kinetic", SCRIPT)
assert SPEC and SPEC.loader
saas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(saas)


class SaaSKineticTypographyContract(unittest.TestCase):
    def test_all_plans_are_deterministic_and_valid(self) -> None:
        first = saas.all_plans()
        second = saas.all_plans()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 7)
        for plan in first:
            saas.validate_plan(plan)
            self.assertEqual(plan["canvas"]["width"], 1920)
            self.assertEqual(plan["canvas"]["height"], 1080)
            self.assertEqual(plan["canvas"]["fps_num"], 30)

    def test_velocity_drop_uses_grapheme_fall_blur_and_bezier(self) -> None:
        plan = saas.build_scene("saas_velocity_drop")
        hero = next(layer for layer in plan["layers"] if layer["id"] == "drop-hero")
        ids = {animator["id"] for animator in hero["text_animators"]}
        self.assertIn("drop-fall", ids)
        self.assertIn("drop-blur-band", ids)
        fall = next(a for a in hero["text_animators"] if a["id"] == "drop-fall")
        self.assertEqual(fall["selectors"][0]["unit"], "grapheme")
        prop = fall["properties"][0]
        self.assertEqual(prop["easing"], "linear")
        self.assertEqual(prop["keyframes"][0]["value"], -300)
        self.assertEqual(prop["keyframes"][-1]["value"], 0)

    def test_word_stagger_is_per_word_and_tracking_stretches(self) -> None:
        plan = saas.build_scene("saas_word_stagger_stretch")
        words = [layer for layer in plan["layers"] if layer["type"] == "text"]
        self.assertEqual([layer["text"] for layer in words], ["Busy", "isn't", "productive"])
        self.assertEqual([layer["start_frame"] for layer in words], [0, 6, 12])
        tracking = words[-1]["text_animators"][0]["properties"][0]
        self.assertEqual(tracking["property"], "tracking")

    def test_split_uses_two_feathered_rect_masks(self) -> None:
        plan = saas.build_scene("saas_split_decapitation")
        top = next(layer for layer in plan["layers"] if layer["id"] == "split-top")
        bottom = next(layer for layer in plan["layers"] if layer["id"] == "split-bottom")
        self.assertEqual(top["masks"][0]["type"], "rect")
        self.assertEqual(bottom["masks"][0]["type"], "rect")
        self.assertLess(top["masks"][0]["position"][1],
                        bottom["masks"][0]["position"][1])

    def test_underline_is_a_spring_animated_shape(self) -> None:
        plan = saas.build_scene("saas_underline_spring")
        underline = next(layer for layer in plan["layers"] if layer["id"] == "underline-core")
        scale = next(t for t in underline["animation"]["tracks"] if t["property"] == "scale_x")
        self.assertEqual(scale["easing"], "spring")

    def test_gloss_uses_text_mask_gradient_and_sweep(self) -> None:
        plan = saas.build_scene("saas_glossy_shimmer")
        gradient = next(layer for layer in plan["layers"] if layer["id"] == "glossy-gradient")
        shimmer = next(layer for layer in plan["layers"] if layer["id"] == "glossy-shimmer")
        self.assertEqual(gradient["masks"][0]["source"], "glossy-base")
        self.assertEqual(gradient["shape"]["fill"]["type"], "linear")
        self.assertEqual(len(gradient["shape"]["fill"]["color_stops"]), 3)
        self.assertEqual(len(shimmer["fill_gradient_animation"]["keyframes"]), 4)

    def test_rotation_snap_uses_spring_rotation(self) -> None:
        plan = saas.build_scene("saas_rotation_snap")
        hero = next(layer for layer in plan["layers"] if layer["id"] == "snap-hero")
        rotation = next(t for t in hero["animation"]["tracks"]
                        if t["property"] == "rotation_z")
        self.assertEqual(rotation["easing"], "spring")
        self.assertEqual(rotation["keyframes"][0]["value"], 26.0)
        self.assertEqual(rotation["keyframes"][1]["value"], 0.0)

    def test_gallery_has_unique_ids_and_all_beats(self) -> None:
        plan = saas.build_gallery()
        ids = [layer["id"] for layer in plan["layers"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(plan["canvas"]["duration_frames"], 540)
        text = [layer["text"] for layer in plan["layers"] if layer["type"] == "text"]
        for phrase in ("Busy", "productive", "Stop", "Clarity", "Start today"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
