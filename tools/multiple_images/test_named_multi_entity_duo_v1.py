#!/usr/bin/env python3
"""Contracts for x2 image-and-entity-name compositions."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("render_named_multi_entity_duo_v1.py")
SPEC = importlib.util.spec_from_file_location("named_multi_entity_duo_v1", SCRIPT)
assert SPEC and SPEC.loader
NAMED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NAMED)


class NamedMultiEntityDuoTests(unittest.TestCase):
    def test_five_named_motion_presets_keep_original_duo_motions(self) -> None:
        self.assertEqual(len(NAMED.ANIMATIONS), 5)
        self.assertEqual([name for name, _ in NAMED.ANIMATIONS], [
            f"named_{preset_id}" for preset_id, _ in NAMED.DUO.PRESET_SUITE
        ])
        self.assertEqual(NAMED.SUITE.drive_folder, "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX")

    def test_each_plan_has_two_named_images_and_two_synchronized_text_layers(self) -> None:
        expected_names = [person["name"] for person in NAMED.PEOPLE]
        expected_assets = [person["asset"] for person in NAMED.PEOPLE]
        for name, build in NAMED.ANIMATIONS:
            with self.subTest(preset=name):
                plan = build()
                images = [layer for layer in plan["layers"] if layer.get("type") == "image"]
                captions = [layer for layer in plan["layers"] if layer.get("id", "").startswith("entity_name_")]
                self.assertEqual([image["asset"] for image in images], expected_assets)
                self.assertEqual([caption["text"] for caption in captions], expected_names)
                self.assertEqual(len(images), 2)
                self.assertEqual(len(captions), 2)
                for image, caption in zip(images, captions, strict=True):
                    self.assertEqual(caption["start_frame"], image["start_frame"])
                    self.assertEqual(caption["duration_frames"], image["duration_frames"])
                    image_tracks = image["animation"]["tracks"]
                    caption_tracks = caption["animation"]["tracks"]
                    self.assertEqual(caption_tracks, [
                        next(track for track in image_tracks if track["property"] == "opacity"),
                        next(track for track in image_tracks if track["property"] == "scale"),
                    ])
                    self.assertEqual(caption["style"]["font"], NAMED.FONT)
                    self.assertEqual(caption["style"]["fit_mode"], "shrink_only")
                    self.assertEqual(caption["position"][1], 966)
                    self.assertTrue((NAMED.ROOT / image["asset"]).is_file())
                self.assertEqual(plan["canvas"]["duration_frames"], 150)
                self.assertEqual(plan["canvas"]["fps_num"], 30)

    def test_caption_boxes_are_below_images_and_inside_canvas(self) -> None:
        for name, build in NAMED.ANIMATIONS:
            with self.subTest(preset=name):
                plan = build()
                images = [layer for layer in plan["layers"] if layer.get("type") == "image"]
                captions = [layer for layer in plan["layers"] if layer.get("id", "").startswith("entity_name_")]
                for image, caption in zip(images, captions, strict=True):
                    x, y = image["position"]
                    w, h = image["size"]
                    image_bottom = DUO_CANVAS_CENTER_Y + y + h / 2 * 1.05
                    cx, cy = caption["position"]
                    cw, ch = caption["size"]
                    self.assertGreaterEqual(cy - ch / 2, image_bottom + 6)
                    self.assertGreaterEqual(cx - cw / 2, 0)
                    self.assertLessEqual(cx + cw / 2, 1920)
                    self.assertLessEqual(cy + ch / 2, 1080)

DUO_CANVAS_CENTER_Y = NAMED.DUO.HEIGHT / 2

if __name__ == "__main__":
    unittest.main()
