#!/usr/bin/env python3
"""Contract tests for the map_motion_v1 catalog consumer."""
import json
import unittest

import render_map_motion_family_v1 as maps


class MapMotionFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(maps.CATALOG.read_text())
        cls.geo = json.loads(maps.GEOJSON.read_text())
        cls.plans = maps.build_plans(cls.catalog, cls.geo)

    def test_every_manifest_recipe_has_a_generated_family_scene(self):
        item_ids = [item["id"] for family in self.catalog["families"] for item in family["items"]]
        self.assertEqual(len(item_ids), 45)
        self.assertEqual(len(set(item_ids)), 45)
        all_layer_ids = {layer["id"] for plan in self.plans.values() for layer in plan["layers"]}
        for item_id in item_ids:
            self.assertIn(f"{item_id}-base", all_layer_ids)
            self.assertIn(f"{item_id}-title", all_layer_ids)

    def test_plans_are_deterministic(self):
        self.assertEqual(json.dumps(self.plans, sort_keys=True),
                         json.dumps(maps.build_plans(self.catalog, self.geo), sort_keys=True))

    def test_routes_use_trimmed_geo_paths_and_following_arrowheads(self):
        plan = self.plans["canary_map_routes_v1"]
        route_layers = [layer for layer in plan["layers"] if layer["id"].endswith("-route")]
        arrow_layers = [layer for layer in plan["layers"] if layer["id"].endswith("-route-head")]
        self.assertTrue(route_layers)
        self.assertTrue(arrow_layers)
        for route in route_layers:
            self.assertEqual(route["shape"]["path"][1]["type"], "cubic_to")
            trim = route["shape"]["operators"][0]
            self.assertEqual(trim["kind"], "trim")
            self.assertEqual([key["value"][1] for key in trim["params"]["animation"]["keyframes"]], [0, 1])
        for arrow in arrow_layers:
            tracks = {entry["property"]: entry for entry in arrow["animation"]["tracks"]}
            self.assertEqual(set(tracks), {"position_x", "position_y", "rotation_z"})
            self.assertEqual(len(tracks["position_x"]["keyframes"]), 5)
            self.assertEqual(len(tracks["position_y"]["keyframes"]), 5)
            self.assertEqual(len(tracks["rotation_z"]["keyframes"]), 5)

    def test_country_outline_is_runtime_path_not_boundary_bitmap(self):
        plan = self.plans["canary_map_basic_v1"]
        outline = next(layer for layer in plan["layers"] if layer["id"] == "map_country_outline_draw-france-outline")
        self.assertEqual(outline["shape"]["type"], "path")
        self.assertGreater(len(outline["shape"]["path"]), 3)
        self.assertEqual(outline["shape"]["operators"][0]["kind"], "trim")
        self.assertNotIn("asset", outline["shape"])

    def test_synthetic_map_data_is_labeled_illustrative(self):
        plan = self.plans["canary_map_data_v1"]
        notes = [layer.get("text", "") for layer in plan["layers"] if "disclaimer" in layer["id"]]
        self.assertTrue(notes)
        self.assertTrue(all("NOT EMPIRICAL" in note for note in notes))

    def test_projection_is_finite_and_deterministic(self):
        point = maps.projected(-0.128, 51.507)
        self.assertEqual(point, maps.projected(-0.128, 51.507))
        self.assertTrue(all(abs(value) < 1000 for value in point))

    def test_gallery_uses_distinct_text_roles_and_map_labels_use_professional_effects(self):
        plans = list(self.plans.values())
        title = next(layer for layer in plans[0]["layers"] if layer["id"].endswith("-title"))
        eyebrow = next(layer for layer in plans[0]["layers"] if layer["id"].endswith("-eyebrow"))
        self.assertGreater(title["style"]["font_size"], eyebrow["style"]["font_size"])
        self.assertNotEqual(title["style"]["fill"], eyebrow["style"]["fill"])
        labels = [layer for plan in plans for layer in plan["layers"]
                  if layer["type"] == "text" and "-label" in layer["id"]]
        self.assertTrue(labels)
        for label in labels:
            style = label["style"]
            self.assertEqual(style["stroke"]["color"], "#06131D")
            self.assertGreater(style["stroke"]["width"], 0)
            self.assertGreater(style["shadow"]["blur"], 0)
            self.assertIn("background", style)
        self.assertFalse((maps.ROOT / "include/chronontemplate/map/MapPack.hpp").exists())
        self.assertFalse((maps.ROOT / "src/chronontemplate/map/MapPack.cpp").exists())
        self.assertFalse((maps.ROOT / "tests/map_pack.cpp").exists())
        modern_header = (maps.ROOT / "include/chronontemplate/map/ModernMapPack.hpp").read_text()
        self.assertIn("composeModernMap", modern_header)


if __name__ == "__main__":
    unittest.main()
