#!/usr/bin/env python3
"""Contract tests for the additional ten-clip multi-image trio suite."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("render_multi_image_trio_v2.py")
SPEC = importlib.util.spec_from_file_location("multi_image_trio_v2", SCRIPT)
assert SPEC and SPEC.loader
TRIO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRIO)


class MultiImageTrioV2ContractTests(unittest.TestCase):
    def test_nine_unique_additional_animations_exclude_withdrawn_heartbeat(self) -> None:
        self.assertEqual(len(TRIO.ANIMATIONS), 9)
        self.assertEqual(len({name for name, _ in TRIO.ANIMATIONS}), 9)
        self.assertEqual(len({recipe for _, recipe in TRIO.ANIMATIONS}), 9)
        self.assertTrue(all(name.startswith("trio_v2_") for name, _ in TRIO.ANIMATIONS))
        self.assertNotIn("heartbeat", {recipe for _, recipe in TRIO.ANIMATIONS})
        self.assertNotIn("trio_v2_10_heartbeat", [name for name, _ in TRIO.ANIMATIONS])
        self.assertEqual(TRIO.SUITE.name, "multi_image_trio_v2")

    def test_every_plan_has_three_expected_simultaneous_animated_portraits(self) -> None:
        expected_ids = ["card_left", "card_mid", "card_right"]
        expected_positions = [list(position) for position in TRIO.POSITIONS]
        expected_assets = list(TRIO.ASSETS)
        for name, recipe in TRIO.ANIMATIONS:
            with self.subTest(animation=name):
                plan = TRIO._build(name, recipe).to_dict()
                images = [layer for layer in plan["layers"] if layer["type"] == "image"]
                self.assertEqual([layer["id"] for layer in images], expected_ids)
                self.assertEqual([layer["asset"] for layer in images], expected_assets)
                self.assertEqual([layer["position"] for layer in images], expected_positions)
                for layer in images:
                    self.assertEqual(layer["start_frame"], 0)
                    self.assertEqual(layer["duration_frames"], 150)
                    self.assertTrue(layer["animation"]["tracks"])
                    for animation_track in layer["animation"]["tracks"]:
                        frames = [key["frame"] for key in animation_track["keyframes"]]
                        self.assertEqual(frames, sorted(set(frames)), (name, layer["id"], animation_track))
                        self.assertTrue(all(0 <= frame < 150 for frame in frames))
                self.assertEqual(plan["canvas"], {
                    "width": 1920, "height": 1080, "fps_num": 30,
                    "fps_den": 1, "duration_frames": 150,
                })
                self.assertEqual(plan["output"]["path"], str(TRIO.OUT_DIR / f"{name}.mp4"))
                self.assertTrue(all((TRIO.OUT_DIR.parent.parent / asset).is_file() for asset in expected_assets))

    def test_suite_order_and_outputs_do_not_reuse_v1_names(self) -> None:
        self.assertEqual([item.name for item in TRIO.SUITE.items], [name for name, _ in TRIO.ANIMATIONS])
        self.assertNotEqual(TRIO.SUITE.out_dir, TRIO.OUT_DIR.parent / "multi_image_trio_v1")
        self.assertEqual(TRIO.SUITE.drive_folder, "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX")

    def test_focus_and_scale_stay_inside_declared_composition_bounds(self) -> None:
        for name, recipe in TRIO.ANIMATIONS:
            with self.subTest(animation=name):
                plan = TRIO._build(name, recipe).to_dict()
                for layer in (item for item in plan["layers"] if item["type"] == "image"):
                    for animation_track in layer["animation"]["tracks"]:
                        values = [key["value"] for key in animation_track["keyframes"]]
                        prop = animation_track["property"]
                        if prop == "scale":
                            self.assertGreaterEqual(min(values), 0.70)
                            self.assertLessEqual(max(values), 1.08)
                        if prop == "opacity":
                            self.assertGreaterEqual(min(values), 0.0)
                            self.assertLessEqual(max(values), 1.0)
                        if prop == "position_z":
                            self.assertLessEqual(max(abs(value) for value in values), 220.0)


if __name__ == "__main__":
    unittest.main()
