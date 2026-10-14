#!/usr/bin/env python3
"""Contract and validation tests for the 15 Minimalist Documentary Backgrounds."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/minimal_documentary_backgrounds"
PLANS_DIR = CATALOG / "plans"
ASSETS_DIR = CATALOG / "assets"

EXPECTED_PRESETS = [
    "01_dark_film_grain",
    "02_dark_paper",
    "03_archival_film",
    "04_deep_navy_gradient",
    "05_warm_documentary",
    "06_editorial_ivory",
    "07_soft_vignette",
    "08_matte_charcoal",
    "09_subtle_film_scratches",
    "10_blurred_backdrop",
    "11_newspaper_paper",
    "12_faint_horizontal_lines",
    "13_floating_dust",
    "14_muted_olive",
    "15_soft_light_sweep",
]


class MinimalDocumentaryBackgroundTests(unittest.TestCase):
    def test_all_15_presets_exist_and_conform_to_renderplan_v3(self):
        for pid in EXPECTED_PRESETS:
            plan_file = PLANS_DIR / f"{pid}.plan.json"
            self.assertTrue(plan_file.exists(), f"Plan missing for {pid}")
            with open(plan_file, "r", encoding="utf-8") as f:
                plan = json.load(f)
            self.assertEqual(plan["schema"], "chronon.render-plan.v3")
            self.assertEqual(plan["version"], 3)
            self.assertEqual(plan["job_id"], pid)
            canvas = plan["canvas"]
            self.assertEqual(canvas["width"], 1920)
            self.assertEqual(canvas["height"], 1080)
            self.assertEqual(canvas["fps_num"], 30)
            self.assertEqual(canvas["fps_den"], 1)
            self.assertEqual(canvas["duration_frames"], 240)  # 8.0s @ 30fps

    def test_asset_plates_exist_and_have_content(self):
        for pid in EXPECTED_PRESETS:
            plate_file = ASSETS_DIR / f"{pid}_plate.png"
            self.assertTrue(plate_file.exists(), f"Asset plate missing for {pid}")
            self.assertGreater(plate_file.stat().st_size, 1024, f"Plate {pid} too small")

    def test_camera_drift_is_restrained_and_subtle(self):
        """Enforces the documentary rule: near-static, restrained motion envelope."""
        for pid in EXPECTED_PRESETS:
            plan_file = PLANS_DIR / f"{pid}.plan.json"
            with open(plan_file, "r", encoding="utf-8") as f:
                plan = json.load(f)
            layers = plan["layers"]
            self.assertGreaterEqual(len(layers), 1)
            main_layer = layers[0]
            self.assertTrue(main_layer.get("enable_3d", False))
            tracks = main_layer["animation"]["tracks"]
            for track in tracks:
                prop = track["property"]
                keys = track["keyframes"]
                frames = [k["frame"] for k in keys]
                self.assertEqual(frames, sorted(set(frames)), f"Unordered frames in {pid} track {prop}")
                for k in keys:
                    val = k["value"]
                    self.assertTrue(math.isfinite(val), f"Non-finite value in {pid} track {prop}")
                    if prop == "scale":
                        self.assertGreaterEqual(val, 1.000, f"Scale below 1.0 in {pid}")
                        self.assertLessEqual(val, 1.030, f"Scale exceeds restrained threshold in {pid}")
                    elif prop in ("position_x", "position_y"):
                        self.assertGreaterEqual(val, -60.0, f"Position out of subtle envelope in {pid}")
                        self.assertLessEqual(val, 60.0, f"Position out of subtle envelope in {pid}")


if __name__ == "__main__":
    unittest.main()
