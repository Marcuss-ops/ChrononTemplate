import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("photo_motion", ROOT / "tools/single_images/render_photo_motion_v1.py")
photo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(photo)


class PhotoMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.family = json.loads((ROOT / "catalog/photo_motion_v1.json").read_text())

    def test_catalog_has_all_18_unique_recipes(self):
        ids = photo.recipe_ids(self.family)
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)
        self.assertEqual(sum(map(len, (g["recipes"] for g in self.family["recipe_groups"]))), 18)

    def test_plan_generation_is_deterministic(self):
        self.assertEqual(photo.build_plans(self.family), photo.build_plans(self.family))

    def test_stack_slots_resolve_expected_card_handoff(self):
        self.assertEqual([x["slot"] for x in photo.resolve_stack_slots(3, 0)], ["hero", "back1", "back2"])
        self.assertEqual([x["slot"] for x in photo.resolve_stack_slots(3, 1)], ["exit", "hero", "back1"])
        self.assertEqual([x["slot"] for x in photo.resolve_stack_slots(4, 0, browser=True)],
                         ["hero", "back1", "back2", "off"])

    def test_pile_slots_are_seeded_separated_and_monotonic_in_z(self):
        first = photo.deterministic_pile_slots(8, 420)
        self.assertEqual(first, photo.deterministic_pile_slots(8, 420))
        self.assertNotEqual(first, photo.deterministic_pile_slots(8, 421))
        self.assertTrue(all(a["z"] < b["z"] for a, b in zip(first, first[1:])))

    def test_card_parts_share_parent_rotation_and_scale_tracks(self):
        poses = [photo.pose(0, 100, 200, rotation=-8, scale=.9), photo.pose(20, 300, 400, rotation=2, scale=1.1)]
        parts = photo.card_parts("rigid-0", photo.PHOTO_ASSETS[0], (100, 200), 0, 30, poses,
                                 self.family["style_tokens"]["archive"], kind="polaroid")
        self.assertGreaterEqual(len(parts), 3)
        for part in parts:
            tracks = {t["property"]: t["keyframes"] for t in part["animation"]["tracks"]}
            self.assertEqual(tracks["rotation_z"], [{"frame": 0, "value": -8}, {"frame": 20, "value": 2}])
            self.assertEqual(tracks["scale"], [{"frame": 0, "value": .9}, {"frame": 20, "value": 1.1}])

    def test_reveal_recipes_use_expected_masks_and_effects(self):
        family = self.family
        recipes = family["recipe_groups"][-1]["recipes"]
        shapes = {"photo_capsule_zoom_reveal": "rounded_rect", "photo_slit_reveal": "rounded_rect",
                  "photo_circle_focus": "ellipse", "photo_diagonal_wipe": "path",
                  "photo_radial_burst": "ellipse", "photo_mask_expand": "rounded_rect"}
        for recipe in recipes:
            image = photo._mask_recipe(recipe, 0, 0, 60, family["style_tokens"]["darkroom"], photo.PHOTO_ASSETS[0])[0]
            self.assertEqual(image["masks"][0]["type"], shapes[recipe])
            self.assertEqual(image["masks"][0]["mode"], "intersect")
            self.assertTrue(all(m.get("radius", 0) <= min(m["size"])/2 for m in image["masks"] if m["type"] == "rounded_rect"))
            if recipe in {"photo_radial_burst", "photo_capsule_zoom_reveal"}:
                self.assertEqual(image["effects"][0]["type"], "radial_blur")

    def test_canary_durations_cover_catalog_and_torture(self):
        plans = photo.build_plans(self.family)
        gallery, torture = plans.values()
        self.assertEqual(gallery["canvas"]["duration_frames"], 18 * 60)
        self.assertEqual(torture["canvas"]["duration_frames"], 15 * 30)
        self.assertEqual(gallery["canvas"]["width"], 1920)
        self.assertEqual(gallery["canvas"]["height"], 1080)


if __name__ == "__main__":
    unittest.main()
