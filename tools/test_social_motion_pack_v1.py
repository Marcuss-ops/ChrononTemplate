#!/usr/bin/env python3
"""Contract tests for responsive Chronon social-motion plans."""
from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_social_motion_pack_v1.py")
SPEC = importlib.util.spec_from_file_location("social_motion_pack_v1", SCRIPT)
assert SPEC and SPEC.loader
PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK)


class SocialMotionPackTests(unittest.TestCase):
    def test_pack_has_eighteen_unique_deterministic_plans(self):
        first, second = PACK.all_plans(), PACK.all_plans()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 18)
        self.assertEqual(len({plan["job_id"] for plan in first}), 18)

    def test_every_plan_obeys_responsive_canvas_and_contract(self):
        for plan in PACK.all_plans():
            with self.subTest(plan=plan["job_id"]):
                PACK.validate_contract(plan)
                fmt = next(name for name in PACK.FORMATS if plan["job_id"].startswith(f"social_{name}_"))
                self.assertEqual((plan["canvas"]["width"], plan["canvas"]["height"]), PACK.FORMATS[fmt])
                for layer in plan["layers"]:
                    self.assertEqual(layer["duration_frames"], PACK.FRAMES)
                    for track in layer.get("animation", {}).get("tracks", []):
                        keys = track["keyframes"]
                        frames = [key["frame"] for key in keys]
                        self.assertEqual(frames, sorted(set(frames)))
                        self.assertTrue(all(0 <= frame < PACK.FRAMES for frame in frames))
                        self.assertTrue(all(math.isfinite(key["value"]) for key in keys))

    def test_each_image_count_uses_expected_assets_and_responsive_safe_slots(self):
        for fmt, (width, height) in PACK.FORMATS.items():
            for count in range(1, 6):
                plan = PACK.image_plan(fmt, count)
                images = [layer for layer in plan["layers"] if layer["type"] == "image"]
                self.assertEqual(len(images), count)
                self.assertEqual([layer["asset"] for layer in images], PACK.ASSETS[:count])
                self.assertTrue(all(layer["radius"] == 0 for layer in images))
                self.assertTrue(all(layer["enable_3d"] is False for layer in images))
                for layer in images:
                    x, y = layer["position"]
                    card_w, card_h = layer["size"]
                    self.assertLessEqual(abs(x) + card_w * 1.05 / 2, width / 2)
                    self.assertLessEqual(abs(y) + card_h * 1.05 / 2, height / 2)

    def test_image_assets_exist_when_the_content_bundle_is_present(self):
        missing = [asset for asset in PACK.ASSETS
                   if not (PACK.CHRONON / asset).is_file()]
        if missing:
            self.skipTest(f"optional Chronon3D content assets are unavailable: {missing[0]}")

    def test_contract_rejects_3d_depth_grading_on_flat_cards(self):
        plan = PACK.image_plan("landscape", 2)
        image = next(layer for layer in plan["layers"] if layer["type"] == "image")
        image["enable_3d"] = True
        with self.assertRaisesRegex(ValueError, "must not receive 3D depth grading"):
            PACK.validate_contract(plan)

    def test_contract_rejects_runtime_radius_that_causes_edge_halos(self):
        plan = PACK.image_plan("landscape", 2)
        image = next(layer for layer in plan["layers"] if layer["type"] == "image")
        image["radius"] = 18
        with self.assertRaisesRegex(ValueError, "runtime radius causes edge halos"):
            PACK.validate_contract(plan)

    def test_phrase_plans_have_three_distinct_animated_safe_fit_slogans(self):
        for fmt in PACK.FORMATS:
            plan = PACK.phrase_plan(fmt)
            phrases = [layer for layer in plan["layers"] if layer["type"] == "text"]
            self.assertEqual([layer["text"] for layer in phrases], PACK.SLOGANS[fmt])
            self.assertTrue(all(layer["style"]["fit_mode"] == "shrink_only" for layer in phrases))
            self.assertTrue(all({"opacity", "position_y", "scale"}.issubset(
                {track["property"] for track in layer["animation"]["tracks"]}) for layer in phrases))

    def test_cli_upload_is_explicit_and_targets_requested_drive_folder(self):
        args = PACK.cli_arguments(["--upload"])
        self.assertTrue(args.upload)
        self.assertEqual(args.drive_folder, "1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI")
        self.assertFalse(PACK.cli_arguments([]).upload)


if __name__ == "__main__":
    unittest.main()
