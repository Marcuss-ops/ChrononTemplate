import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("rgb_motion", ROOT / "tools/backgrounds/render_rgb_motion_v1.py")
rgb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rgb)


class RgbMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.family = json.loads((ROOT / "catalog/rgb_motion_v1.json").read_text())

    def test_catalog_has_ten_unique_recipes(self):
        ids = [recipe["id"] for recipe in self.family["recipes"]]
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(set(ids)), 10)

    def test_rgb_transform_expands_three_independent_branches_and_neutral_core(self):
        layers = rgb.resolve_rgb_channel_transform(12, 60, {
            "r": {"offset": (-10, 0), "rotation": -4},
            "g": {"offset": (0, 0)},
            "b": {"offset": (10, 0), "rotation": 4},
        })
        self.assertEqual(len(layers), 4)
        self.assertEqual([layer["style"]["fill"] for layer in layers[:3]],
                         [rgb.RGB["r"], rgb.RGB["g"], rgb.RGB["b"]])
        self.assertEqual([layer["animation"]["tracks"][-1]["keyframes"][0]["value"]
                          for layer in layers[:3]], [-4, 0, 4])
        self.assertEqual(layers[-1]["style"]["fill"], "#F8FAFF")

    def test_wave_warp_is_applied_independently_per_channel(self):
        layers = rgb.resolve_rgb_channel_transform(0, 60, {
            "r": {"warp": True, "phase": .1},
            "g": {"warp": True, "phase": 2.2},
            "b": {"warp": True, "phase": 4.3},
        })
        self.assertEqual([layer["effects"][0]["phase"] for layer in layers[:3]], [.1, 2.2, 4.3])

    def test_slice_identity_and_seeded_layout(self):
        a = rgb.resolve_slice_transform(0, 60, count=12, amplitude=0, seed=90)
        b = rgb.resolve_slice_transform(0, 60, count=12, amplitude=0, seed=90)
        self.assertEqual(a, b)
        self.assertEqual(len([x for x in a if x["id"].startswith("slice-horizontal-")]), 12)
        offsets_a = [x["animation"]["tracks"][1]["keyframes"][1]["value"] - rgb.WIDTH/2
                     for x in rgb.resolve_slice_transform(0, 60, count=12, amplitude=50, seed=90)[:-1]]
        offsets_b = [x["animation"]["tracks"][1]["keyframes"][1]["value"] - rgb.WIDTH/2
                     for x in rgb.resolve_slice_transform(0, 60, count=12, amplitude=50, seed=90)[:-1]]
        self.assertEqual(offsets_a, offsets_b)
        self.assertTrue(all(x["masks"][0]["type"] == "rect" for x in a[:-1]))

    def test_posterized_slices_snap_offsets_to_hold_grid(self):
        strips = rgb.resolve_slice_transform(0, 60, count=16, amplitude=80, seed=3, posterized=True)[:-1]
        for strip in strips:
            value = strip["animation"]["tracks"][1]["keyframes"][1]["value"] - rgb.WIDTH/2
            self.assertAlmostEqual(value / 18.0, round(value / 18.0))

    def test_multitap_spacing_decay_and_palette_endpoints(self):
        taps = rgb.resolve_multi_tap_trail(0, 60, taps=7, step=(0, 10), decay=.5,
                                           palette=["#FF0000", "#0000FF"])
        taps = [x for x in taps if x["id"].startswith("trail-tap-")]
        taps.reverse()
        ys = [next(track for track in layer["animation"]["tracks"] if track["property"] == "position_y")["keyframes"][0]["value"] for layer in taps]
        alphas = [layer["animation"]["tracks"][0]["keyframes"][0]["value"] for layer in taps]
        self.assertEqual(ys, [270 + 10*i for i in range(7)])
        self.assertEqual(alphas, [.5**i for i in range(7)])
        self.assertEqual(taps[0]["style"]["fill"], "#FF0000")
        self.assertEqual(taps[-1]["style"]["fill"], "#0000FF")

    def test_analytic_temporal_sampling_is_pure_and_clamped(self):
        trajectory = [(0, -100, 0), (20, 100, 20), (59, 0, 0)]
        a = rgb.resolve_analytic_temporal_channels(0, 60, trajectory, (-3, 0, 3))
        b = rgb.resolve_analytic_temporal_channels(0, 60, trajectory, (-3, 0, 3))
        self.assertEqual(a, b)
        # The red branch is 3 frames behind the green branch during linear travel.
        red_x = next(t for t in a[0]["animation"]["tracks"] if t["property"] == "position_x")["keyframes"][8]["value"]
        green_x = next(t for t in a[1]["animation"]["tracks"] if t["property"] == "position_x")["keyframes"][8]["value"]
        self.assertLess(red_x, green_x)
        self.assertTrue(all(math.isfinite(k["value"]) for layer in a for tr in layer["animation"]["tracks"]
                            for k in tr["keyframes"]))

    def test_velocity_field_separation_tracks_motion_then_settles_to_zero(self):
        layers = rgb.resolve_velocity_rgb_channels(0, 30, [(0, -100, 0), (15, 0, 20), (29, 0, 20)])
        def x_value(layer, frame):
            track = next(t for t in layer["animation"]["tracks"] if t["property"] == "position_x")
            return track["keyframes"][frame]["value"]
        self.assertNotEqual(x_value(layers[0], 8), x_value(layers[1], 8))
        self.assertNotEqual(x_value(layers[2], 8), x_value(layers[1], 8))
        self.assertEqual(x_value(layers[0], 29), x_value(layers[1], 29))
        self.assertEqual(x_value(layers[2], 29), x_value(layers[1], 29))

    def test_rapid_transition_catalog_contract_matches_recipe_definitions(self):
        expected = {
            "rgb_split_whip": (5, 8, 7, "normal"), "rgb_snap": (4, 6, 5, "micro"),
            "rgb_zoom_punch": (6, 10, 8, "normal"), "rgb_horizontal_tear": (6, 10, 8, "normal"),
            "rgb_glitch_cut": (4, 8, 6, "micro"), "rgb_lens_snap": (6, 9, 8, "normal"),
            "rgb_spin_blur": (6, 10, 8, "normal"), "prismatic_flash": (6, 10, 8, "normal"),
            "lightleak_rgb_combo": (8, 12, 10, "normal"), "film_burn_rgb": (8, 12, 10, "normal"),
        }
        catalog = json.loads((ROOT / "catalog/motion_catalog.v1.json").read_text())
        rows = catalog["rgb_motion"]["rapid_transitions"]
        self.assertEqual(len(rows), len(expected))
        self.assertEqual(len({row["id"] for row in rows}), len(expected))
        for row in rows:
            self.assertEqual((row["minimum_frames"], row["maximum_frames"],
                              row["recommended_frames"], row["timing_class"]), expected[row["id"]])
        emitted = json.loads((ROOT / "catalog/chronontemplate_catalog.v1.json").read_text())
        self.assertEqual(emitted["rgb_motion"]["rapid_transitions"], rows)

    def test_rapid_transition_plans_cover_the_proposal_and_frame_budgets(self):
        expected = {
            "rgb_split_whip": (5, 8), "rgb_snap": (4, 6),
            "rgb_zoom_punch": (6, 10), "rgb_horizontal_tear": (6, 10),
            "rgb_glitch_cut": (4, 8), "rgb_lens_snap": (6, 9),
            "rgb_spin_blur": (6, 10), "prismatic_flash": (6, 10),
            "lightleak_rgb_combo": (8, 12), "film_burn_rgb": (8, 12),
        }
        self.assertEqual(set(rgb.RAPID_TRANSITIONS), set(expected))
        plans = rgb.build_transition_plans()
        self.assertEqual(set(plans), set(expected))
        self.assertEqual(plans, rgb.build_transition_plans())
        for ident, bounds in expected.items():
            plan = plans[ident]
            frames = plan["canvas"]["duration_frames"]
            self.assertGreaterEqual(frames, bounds[0])
            self.assertLessEqual(frames, bounds[1])
            self.assertEqual(plan["schema"], "chronon.render-plan.v3")
            self.assertTrue(plan["layers"])
            for layer in plan["layers"]:
                for anim_track in layer.get("animation", {}).get("tracks", []):
                    keys = anim_track["keyframes"]
                    frame_ids = [key["frame"] for key in keys]
                    self.assertEqual(frame_ids, sorted(set(frame_ids)))
                    self.assertTrue(all(0 <= frame < frames for frame in frame_ids))

    def test_rgb_snap_uses_native_component_channel_transform(self):
        plan = rgb.build_transition_plans()["rgb_snap"]
        core = next(layer for layer in plan["layers"]
                    if any(effect.get("type") == "rgb_channel_transform"
                           for effect in layer.get("effects", [])))
        effect = next(effect for effect in core["effects"] if effect["type"] == "rgb_channel_transform")
        self.assertEqual(effect["red_transform"]["translation"], [-18.0, 0.0])
        self.assertEqual(effect["green_transform"]["translation"], [0.0, 0.0])
        self.assertEqual(effect["blue_transform"]["translation"], [18.0, 0.0])

    def test_rapid_rgb_presets_exercise_expected_primitive_combinations(self):
        plans = rgb.build_transition_plans()
        snap = plans["rgb_snap"]["layers"]
        self.assertEqual([layer["style"]["fill"] for layer in snap[2:5]],
                         [rgb.RGB["r"], rgb.RGB["g"], rgb.RGB["b"]])
        tear = plans["rgb_horizontal_tear"]["layers"]
        self.assertTrue(any(layer.get("masks") for layer in tear))
        self.assertGreaterEqual(sum(layer.get("style", {}).get("fill") == rgb.RGB["r"] for layer in tear), 1)
        zoom = [layer for layer in plans["rgb_zoom_punch"]["layers"] if "animation" in layer]
        self.assertTrue(any(any(track["property"] == "scale" and len(track["keyframes"]) == 3
                                for track in layer["animation"]["tracks"])
                            for layer in zoom))
        spin = [layer for layer in plans["rgb_spin_blur"]["layers"] if "animation" in layer]
        self.assertTrue(any(any(track["property"] == "rotation_z" and len(track["keyframes"]) == 3
                                for track in layer["animation"]["tracks"])
                            for layer in spin))
        for ident in ("rgb_snap", "rgb_zoom_punch", "rgb_horizontal_tear", "rgb_glitch_cut",
                      "rgb_lens_snap", "rgb_spin_blur"):
            effect_types = {effect["type"] for layer in plans[ident]["layers"]
                            for effect in layer.get("effects", [])}
            self.assertIn("rgb_channel_transform", effect_types, ident)
        for ident in ("rgb_zoom_punch", "rgb_lens_snap", "rgb_spin_blur"):
            effect_types = {effect["type"] for layer in plans[ident]["layers"]
                            for effect in layer.get("effects", [])}
            self.assertIn("radial_blur", effect_types, ident)

    def test_gallery_and_torture_are_deterministic_and_complete(self):
        first = rgb.build_plans(self.family)
        self.assertEqual(first, rgb.build_plans(self.family))
        self.assertEqual(first["canary_rgb_motion_v1"]["canvas"]["duration_frames"], 600)
        self.assertEqual(first["rgb_motion_torture_v1"]["canvas"]["duration_frames"], 300)
        self.assertTrue(any(layer.get("effects", [{}])[0].get("type") == "wave_warp"
                            for layer in first["rgb_motion_torture_v1"]["layers"]))

    def test_five_second_1080p_scene_transition_demos_are_deterministic(self):
        first = rgb.build_transition_demo_plans()
        second = rgb.build_transition_demo_plans()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 14)
        self.assertEqual(set(first), set(rgb.RAPID_TRANSITIONS) | set(rgb.CUSTOM_TRANSITIONS))
        for ident, plan in first.items():
            self.assertEqual(plan["canvas"], {
                "width": 1920, "height": 1080, "fps_num": 30,
                "fps_den": 1, "duration_frames": 150,
            })
            self.assertEqual(plan["output"]["format"], "mp4")
            self.assertEqual(plan["output"]["codec"], "h264")
            transition_layers = [layer for layer in plan["layers"]
                                 if layer["id"].startswith(("rgb-", "slice-", "trail-",
                                                            "velocity-", "temporal-",
                                                            "custom-prismatic-"))]
            self.assertTrue(transition_layers, ident)
            self.assertTrue(any(layer.get("type") == "color" and layer["id"].startswith("scene-b-")
                                for layer in plan["layers"]), ident)
            for layer in plan["layers"]:
                self.assertTrue(all(key["frame"] < 150
                                    for track_ in layer.get("animation", {}).get("tracks", [])
                                    for key in track_["keyframes"]), ident)

    def test_five_second_demo_contract_rejects_short_or_wrong_size_outputs(self):
        with self.assertRaises(ValueError):
            rgb.build_transition_demo_plans(total_frames=149)
        with self.assertRaises(ValueError):
            rgb.build_transition_demo_plans(width=1280)

    def test_custom_transition_combinations_use_deterministic_bounded_primitives(self):
        for ident, duration in rgb.CUSTOM_TRANSITIONS.items():
            first = rgb._custom_transition_layers(ident, duration, 72)
            second = rgb._custom_transition_layers(ident, duration, 72)
            self.assertEqual(first, second, ident)
            self.assertLessEqual(sum(layer["id"].startswith("slice-") for layer in first), 32, ident)
            self.assertTrue(first, ident)

    def test_invalid_limits_fail_closed(self):
        with self.assertRaises(ValueError):
            rgb.resolve_slice_transform(0, 60, count=33)
        with self.assertRaises(ValueError):
            rgb.resolve_multi_tap_trail(0, 60, taps=25)
        with self.assertRaises(ValueError):
            rgb.resolve_rgb_channel_transform(0, 1, {})


if __name__ == "__main__":
    unittest.main()
