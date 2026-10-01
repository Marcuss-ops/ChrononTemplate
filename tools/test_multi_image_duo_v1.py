#!/usr/bin/env python3
"""Contract tests for the multi_image_duo_v1 render-plan authoring tool."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[1]
CATALOG = TEMPLATE_DIR / "catalog/multi_entity_layout.v1.json"

SCRIPT = Path(__file__).with_name("render_multi_entity_layout_v1.py")
SPEC = importlib.util.spec_from_file_location("multi_image_duo_v1", SCRIPT)
assert SPEC and SPEC.loader
DUO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DUO)


class MultiImageDuoContractTests(unittest.TestCase):
    def test_all_five_presets_are_defined_and_match_catalog_ids(self) -> None:
        self.assertEqual(
            set(DUO.PRESET_BUILDERS),
            {
                "duo_split_reveal",
                "duo_depth_stagger",
                "duo_cross_focus",
                "duo_parallax_balance",
                "duo_compare_hold",
            },
        )
        self.assertEqual(len(DUO.PRESET_SUITE), 5)

    def test_preset_ids_match_the_canonical_catalog(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        catalog_ids = {
            preset["id"]
            for preset in catalog["motion_presets"]["multi_image_duo_v1"]
        }
        self.assertEqual(catalog_ids, set(DUO.PRESET_BUILDERS))

    def test_each_preset_is_deterministic_and_a_single_two_image_scene(self) -> None:
        for preset_id, builder in DUO.PRESET_SUITE:
            with self.subTest(preset=preset_id):
                plan = builder()
                self.assertEqual(plan, builder())
                self.assertEqual(plan["output"]["path"], f"{preset_id}.mp4")
                self.assertFalse(Path(plan["output"]["path"]).is_absolute())
                self.assertEqual(plan["job_id"], preset_id)
                self.assertTrue(DUO.validate_plan_contract(preset_id, plan))
                image_layers = [layer for layer in plan["layers"] if layer["type"] == "image"]
                self.assertEqual([layer["id"] for layer in image_layers], ["card_left", "card_right"])
                self.assertEqual({layer["asset"] for layer in image_layers}, {DUO.IMAGE_LEFT, DUO.IMAGE_RIGHT})
                self.assertTrue(all(layer["duration_frames"] == 150 for layer in image_layers))
                self.assertTrue(all(layer["start_frame"] == 0 for layer in image_layers))
                self.assertTrue(all(layer["fit"] == "cover" for layer in image_layers))
                self.assertTrue(all(layer.get("animation", {}).get("tracks") for layer in image_layers))
                left_scale = next(track for track in image_layers[0]["animation"]["tracks"] if track["property"] == "scale")
                right_scale = next(track for track in image_layers[1]["animation"]["tracks"] if track["property"] == "scale")
                left_focus = {key["frame"]: key["value"] for key in left_scale["keyframes"]}
                right_focus = {key["frame"]: key["value"] for key in right_scale["keyframes"]}
                shared_frames = set(left_focus) & set(right_focus)
                self.assertTrue(
                    any(left_focus[frame] > right_focus[frame] for frame in shared_frames),
                    "the left image must receive primary focus",
                )
                self.assertTrue(
                    any(right_focus[frame] > left_focus[frame] for frame in shared_frames),
                    "focus must later move to the right image",
                )

    def test_duo_slots_are_separated_and_inside_safe_area_even_at_focus_scale(self) -> None:
        plan = DUO.build_05_duo_compare_hold()
        left, right = [layer for layer in plan["layers"] if layer["type"] == "image"]
        scale = 1.05
        left_edge = DUO.WIDTH / 2 + left["position"][0] + left["size"][0] * scale / 2
        right_edge = DUO.WIDTH / 2 + right["position"][0] - right["size"][0] * scale / 2
        self.assertLess(left_edge, right_edge)
        self.assertGreater(DUO.WIDTH / 2 + left["position"][0] - left["size"][0] * scale / 2, 0)
        self.assertLess(DUO.WIDTH / 2 + right["position"][0] + right["size"][0] * scale / 2, DUO.WIDTH)
        self.assertLess(DUO.HEIGHT / 2 - DUO.CARD_H * scale / 2, DUO.HEIGHT)
        self.assertGreater(DUO.HEIGHT / 2 + DUO.CARD_H * scale / 2, 0)

    def test_catalog_declares_a_six_pixel_gap_at_maximum_focus_scale(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        layout = catalog["primitives"]["layout_resolver"]["layouts"]["count_2"]
        left, right = layout["slots"]
        focus = layout["maximum_focus_scale"]
        left_right_edge = DUO.WIDTH / 2 + left["center"][0] + left["size"][0] * focus / 2
        right_left_edge = DUO.WIDTH / 2 + right["center"][0] - right["size"][0] * focus / 2
        self.assertGreaterEqual(right_left_edge - left_right_edge, 6)
        self.assertEqual(layout["simultaneous_images"], 2)
        self.assertEqual(layout["reveal_deadline_ratio"], 0.45)
        expected_left_bounds = [
            DUO.WIDTH / 2 + left["center"][0] - left["size"][0] * focus / 2,
            DUO.HEIGHT / 2 + left["center"][1] - left["size"][1] * focus / 2,
            DUO.WIDTH / 2 + left["center"][0] + left["size"][0] * focus / 2,
            DUO.HEIGHT / 2 + left["center"][1] + left["size"][1] * focus / 2,
        ]
        self.assertEqual(left["safe_bounds"], [round(value) for value in expected_left_bounds])

    def test_canaries_cover_people_brand_and_generic_asset_pairs(self) -> None:
        self.assertEqual(set(DUO.CANARY_VARIANTS), {"people", "brand", "generic"})
        for variant, assets in DUO.CANARY_VARIANTS.items():
            with self.subTest(variant=variant):
                plan = DUO.make_canary_plan(variant, assets)
                self.assertEqual(plan["job_id"], f"canary_{variant}_duo_compare_hold")
                self.assertTrue(DUO.validate_plan_contract(plan["job_id"], plan))
                self.assertEqual(
                    [layer["asset"] for layer in plan["layers"] if layer["type"] == "image"],
                    list(assets),
                )

    def test_upload_requires_the_complete_exact_mp4_set_before_touching_drive(self) -> None:
        args = DUO.cli_arguments(["--upload"])
        expected = {
            *(f"{preset_id}.mp4" for preset_id in DUO.PRESET_BUILDERS),
            *(f"canary_{variant}_{DUO.CANARY_PRESET}.mp4" for variant in DUO.CANARY_VARIANTS),
        }
        from types import SimpleNamespace

        original = DUO.subprocess.run
        original_uploader = args.drive_uploader
        original_credentials = args.drive_credentials
        original_token = args.drive_token
        captured = []

        def fake_run(command, **kwargs):
            captured.append((command, kwargs))
            return SimpleNamespace(stdout="DRIVE_UPLOAD_PASS id=fake parent=fake sha256=fake bytes=0", stderr="")

        temporary_mp4 = TEMPLATE_DIR / "out/multi_image_duo_v1/test-upload.mp4"
        args.drive_uploader = Path("/bin/true")
        args.drive_credentials = Path("/etc/hosts")
        args.drive_token = Path("/etc/hosts")
        try:
            DUO.subprocess.run = fake_run
            with self.assertRaisesRegex(RuntimeError, "incomplete/unexpected"):
                DUO.upload_deliverables([temporary_mp4], args)
            self.assertEqual(captured, [], "an incomplete deliverable set must not invoke the uploader")
            self.assertEqual(expected.__len__(), 8)
        finally:
            DUO.subprocess.run = original
            args.drive_uploader = original_uploader
            args.drive_credentials = original_credentials
            args.drive_token = original_token

    def test_contract_rejects_a_sequential_single_image_fallback(self) -> None:
        plan = DUO.build_01_duo_split_reveal()
        plan["layers"] = [layer for layer in plan["layers"] if layer.get("id") != "card_right"]
        with self.assertRaisesRegex(ValueError, "exactly two simultaneous"):
            DUO.validate_plan_contract("invalid", plan)

    def test_contract_rejects_focus_scale_that_breaks_safe_gap(self) -> None:
        plan = DUO.build_05_duo_compare_hold()
        left = next(layer for layer in plan["layers"] if layer.get("id") == "card_left")
        scale = next(track for track in left["animation"]["tracks"] if track["property"] == "scale")
        scale["keyframes"][2]["value"] = 1.08
        with self.assertRaisesRegex(ValueError, "focus scale must remain"):
            DUO.validate_plan_contract("oversized_focus", plan)

    def test_contract_rejects_non_reciprocal_focus(self) -> None:
        plan = DUO.build_05_duo_compare_hold()
        left = next(layer for layer in plan["layers"] if layer.get("id") == "card_left")
        right = next(layer for layer in plan["layers"] if layer.get("id") == "card_right")
        left_scale = next(track for track in left["animation"]["tracks"] if track["property"] == "scale")
        right_scale = next(track for track in right["animation"]["tracks"] if track["property"] == "scale")
        right_scale["keyframes"] = [dict(key) for key in left_scale["keyframes"]]
        with self.assertRaisesRegex(ValueError, "transfer primary focus"):
            DUO.validate_plan_contract("no_focus_transfer", plan)

    def test_contract_rejects_late_or_missing_reveal(self) -> None:
        plan = DUO.build_01_duo_split_reveal()
        left = next(layer for layer in plan["layers"] if layer.get("id") == "card_left")
        opacity = next(track for track in left["animation"]["tracks"] if track["property"] == "opacity")
        opacity["keyframes"] = [{"frame": 0, "value": 0.0}, {"frame": 80, "value": 1.0}]
        with self.assertRaisesRegex(ValueError, "visible by 45%"):
            DUO.validate_plan_contract("late_reveal", plan)


if __name__ == "__main__":
    unittest.main()
