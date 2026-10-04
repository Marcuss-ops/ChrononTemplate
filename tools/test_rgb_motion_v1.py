import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rgb_motion", ROOT / "tools/render_rgb_motion_v1.py")
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

    def test_gallery_and_torture_are_deterministic_and_complete(self):
        first = rgb.build_plans(self.family)
        self.assertEqual(first, rgb.build_plans(self.family))
        self.assertEqual(first["canary_rgb_motion_v1"]["canvas"]["duration_frames"], 600)
        self.assertEqual(first["rgb_motion_torture_v1"]["canvas"]["duration_frames"], 300)
        self.assertTrue(any(layer.get("effects", [{}])[0].get("type") == "wave_warp"
                            for layer in first["rgb_motion_torture_v1"]["layers"]))

    def test_invalid_limits_fail_closed(self):
        with self.assertRaises(ValueError):
            rgb.resolve_slice_transform(0, 60, count=33)
        with self.assertRaises(ValueError):
            rgb.resolve_multi_tap_trail(0, 60, taps=25)
        with self.assertRaises(ValueError):
            rgb.resolve_rgb_channel_transform(0, 1, {})


if __name__ == "__main__":
    unittest.main()
