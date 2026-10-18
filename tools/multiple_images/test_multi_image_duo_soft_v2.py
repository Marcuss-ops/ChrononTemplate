#!/usr/bin/env python3
"""Contract tests for the multi_image_duo_soft_v2 render-plan authoring tool."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parents[2]
CATALOG = TEMPLATE_DIR / "catalog/multi_entity_layout.v1.json"

SCRIPT = Path(__file__).with_name("render_multi_image_duo_soft_v2.py")
SPEC = importlib.util.spec_from_file_location("multi_image_duo_soft_v2", SCRIPT)
assert SPEC and SPEC.loader
DUO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DUO)

EXPECTED_IDS = {
    "duo_soft_bloom_rise",
    "duo_soft_drift_settle",
    "duo_soft_cross_bloom",
    "duo_soft_breathe_hold",
    "duo_soft_stagger_glow",
}


class MultiImageDuoSoftContractTests(unittest.TestCase):
    def test_all_five_presets_are_defined_and_match_catalog_ids(self) -> None:
        self.assertEqual(set(DUO.PRESET_BUILDERS), EXPECTED_IDS)
        self.assertEqual(len(DUO.PRESET_SUITE), 5)

    def test_preset_ids_match_the_canonical_catalog(self) -> None:
        catalog = json.loads(CATALOG.read_text())
        catalog_ids = {
            preset["id"]
            for preset in catalog["motion_presets"]["multi_image_duo_soft_v2"]
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

    def test_soft_bounds_hold_for_every_preset(self) -> None:
        """Soft grammar: small drifts, gentle scales, opacity-led reveals."""
        for preset_id, builder in DUO.PRESET_SUITE:
            with self.subTest(preset=preset_id):
                plan = builder()
                image_layers = [layer for layer in plan["layers"] if layer["type"] == "image"]
                for layer in image_layers:
                    tracks = {track["property"]: track for track in layer["animation"]["tracks"]}
                    for prop in ("position_x", "position_y"):
                        if prop in tracks:
                            values = [abs(key["value"]) for key in tracks[prop]["keyframes"]]
                            self.assertLessEqual(max(values), 64.0, f"{prop} drift exceeds the soft bound")
                    scales = [key["value"] for key in tracks["scale"]["keyframes"]]
                    self.assertGreaterEqual(min(scales), 0.85)
                    self.assertLessEqual(max(scales), 1.05)
                    resting = {key["frame"]: key["value"] for key in tracks["scale"]["keyframes"]}
                    self.assertEqual(resting[149], 1.0)
                    opacities = [key["value"] for key in tracks["opacity"]["keyframes"]]
                    self.assertTrue(all(0.0 <= v <= 1.0 for v in opacities))

    def test_duo_slots_are_separated_and_inside_safe_area_even_at_focus_scale(self) -> None:
        plan = DUO.build_01_duo_soft_bloom_rise()
        left, right = [layer for layer in plan["layers"] if layer["type"] == "image"]
        scale = 1.05
        left_edge = DUO.WIDTH / 2 + left["position"][0] + left["size"][0] * scale / 2
        right_edge = DUO.WIDTH / 2 + right["position"][0] - right["size"][0] * scale / 2
        self.assertLess(left_edge, right_edge)
        self.assertGreater(DUO.WIDTH / 2 + left["position"][0] - left["size"][0] * scale / 2, 0)
        self.assertLess(DUO.WIDTH / 2 + right["position"][0] + right["size"][0] * scale / 2, DUO.WIDTH)
        self.assertLess(DUO.HEIGHT / 2 - DUO.CARD_H * scale / 2, DUO.HEIGHT)
        self.assertGreater(DUO.HEIGHT / 2 + DUO.CARD_H * scale / 2, 0)

    def test_upload_requires_the_complete_exact_mp4_set_before_touching_drive(self) -> None:
        args = DUO.cli_arguments(["--upload"])
        expected = {f"{preset_id}.mp4" for preset_id in DUO.PRESET_BUILDERS}
        from types import SimpleNamespace
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            for preset_id in DUO.PRESET_BUILDERS:
                (tmpdir / f"{preset_id}.mp4").write_bytes(b"fake")
            with self.assertRaises(RuntimeError):
                DUO.upload_deliverables([tmpdir / "duo_soft_bloom_rise.mp4"], SimpleNamespace(
                    drive_uploader=args.drive_uploader, drive_credentials=args.drive_credentials,
                    drive_token=args.drive_token, drive_folder=args.drive_folder))
        self.assertEqual(expected, {f"{preset_id}.mp4" for preset_id in EXPECTED_IDS})


if __name__ == "__main__":
    raise SystemExit(unittest.main())
