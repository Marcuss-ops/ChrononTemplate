#!/usr/bin/env python3
"""Determinism and renderer-contract tests for text_depth_focus_v1."""
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_text_depth_focus_v1.py")
SPEC = importlib.util.spec_from_file_location("text_depth_focus_v1", SCRIPT)
assert SPEC and SPEC.loader
FOCUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FOCUS)


class TextDepthFocusTests(unittest.TestCase):
    def test_eight_named_presets_are_deterministic_and_renderer_bounded(self):
        first, second = FOCUS.all_plans(), FOCUS.all_plans()
        self.assertEqual(first, second)
        self.assertEqual([plan["job_id"] for plan in first], list(FOCUS.PRESET_IDS))
        self.assertEqual(len(first), 8)
        for plan in first:
            with self.subTest(preset=plan["job_id"]):
                FOCUS.validate_plan(plan)
                self.assertEqual((plan["canvas"]["width"], plan["canvas"]["height"],
                                  plan["canvas"]["fps_num"], plan["canvas"]["duration_frames"]),
                                 (1920, 1080, 30, 150))
                self.assertTrue(all(math.isfinite(value) for value in _numbers(plan)))

    def test_static_word_focus_has_distance_weighted_blur_and_subtle_scale(self):
        plan = FOCUS.build_plan("text_focus_word_static")
        words = plan["layers"][1:5]
        expected = [5.2, 2.6, 0.0, 2.6]
        for layer, blur in zip(words, expected):
            properties = {prop["property"]: prop["keyframes"]
                          for prop in layer["text_animators"][0]["properties"]}
            self.assertEqual(properties["blur"][-1]["value"], blur)
            self.assertEqual(properties["blur"][-2]["frame"], 16)
            if layer["text"] == "VIDEOS":
                self.assertEqual(properties["blur"][0]["value"], 5.0)
            elif layer["text"] == "MAKE":
                self.assertEqual(properties["blur"][0]["value"], 5.2)
            scales = [key["value"][0] for key in properties["scale"]]
            self.assertLessEqual(max(scales), 1.0)
            self.assertGreaterEqual(min(scales), 0.94)

    def test_focus_travel_is_baked_continuous_and_random_access_deterministic(self):
        keys = FOCUS._focus_samples([0, 1, 2, 3])
        self.assertEqual(keys, FOCUS._focus_samples([0, 1, 2, 3]))
        self.assertEqual(len(keys), FOCUS.FRAMES)
        self.assertEqual([keys[i][0] for i in (0, 37, 75, 112, 149)], [0, 37, 75, 112, 149])
        values = [value for _, value in keys]
        self.assertAlmostEqual(values[0], 0)
        self.assertAlmostEqual(values[-1], 3)
        self.assertLess(max(abs(b - a) for a, b in zip(values, values[1:])), 0.08)
        for preset in ("text_focus_word_travel", "text_focus_near_to_far", "text_focus_far_to_near"):
            with self.subTest(preset=preset):
                plan = FOCUS.build_plan(preset)
                for layer in plan["layers"][1:5]:
                    blur = next(track for track in layer["text_animators"][0]["properties"]
                                if track["property"] == "blur")["keyframes"]
                    self.assertEqual(len(blur), FOCUS.FRAMES)
                    self.assertLess(max(abs(b["value"] - a["value"])
                                        for a, b in zip(blur, blur[1:])), 0.21)

    def test_true_depth_plans_use_world_z_and_camera_dof_contract(self):
        for preset in ("text_focus_near_to_far", "text_focus_far_to_near", "text_focus_depth_cascade"):
            with self.subTest(preset=preset):
                plan = FOCUS.build_plan(preset)
                self.assertEqual([layer["position"][2] for layer in plan["layers"][1:5]],
                                 [500.0, 560.0, 620.0, 680.0])
                self.assertEqual(plan["camera"]["dof"]["enabled"], preset == "text_focus_depth_cascade")
                self.assertEqual(plan["camera"]["dof"]["focus_distance"], 620.0)
                self.assertTrue(all(layer["enable_3d"] for layer in plan["layers"][1:5]))
                self.assertTrue(all("position_z" not in {
                    prop["property"] for prop in layer["text_animators"][0]["properties"]
                } for layer in plan["layers"][1:5]))
        cascade = FOCUS.build_plan("text_focus_depth_cascade")
        self.assertTrue(all(key["value"] == 0 for layer in cascade["layers"][1:5]
                            for track in layer["text_animators"][0]["properties"]
                            if track["property"] == "blur" for key in track["keyframes"]))
        z_tracks = [next(track for track in layer["animation"]["tracks"]
                         if track["property"] == "position_z") for layer in cascade["layers"][1:5]]
        self.assertTrue(all(track["keyframes"][-1]["value"] == 0 for track in z_tracks))

    def test_layout_and_semantic_spans_preserve_phrase_and_no_blur_pop(self):
        plan = FOCUS.build_plan("text_focus_rack_duo")
        words = plan["layers"][1:5]
        self.assertEqual(" ".join(layer["text"] for layer in words), FOCUS.PHRASE)
        for index, layer in enumerate(words):
            span = layer["spans"][0]
            self.assertEqual(span["semantic_id"], f"word-{index}")
            self.assertEqual((span["start"], span["end"]), (0, len(layer["text"].encode("utf-8"))))
            blur = next(prop for prop in layer["text_animators"][0]["properties"]
                        if prop["property"] == "blur")["keyframes"]
            self.assertEqual(blur[0]["frame"], 0)
            self.assertEqual(blur[-1]["frame"], FOCUS.FRAMES - 1)
            self.assertTrue(all(math.isfinite(key["value"]) and 0 <= key["value"] <= 7 for key in blur))


def _numbers(value):
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        return [number for child in value.values() for number in _numbers(child)]
    if isinstance(value, (list, tuple)):
        return [number for child in value for number in _numbers(child)]
    return []


if __name__ == "__main__":
    unittest.main()
