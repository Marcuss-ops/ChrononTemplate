import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tech_background", ROOT / "tools/render_tech_background_v1.py")
tech = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tech)


class TechBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.family = json.loads((ROOT / "catalog/tech_background_v1.json").read_text())

    def test_catalog_has_six_unique_recipe_ids(self):
        ids = [r["id"] for r in self.family["recipes"]]
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(set(ids)), 6)
        self.assertEqual(ids, ["tech_blue_horizon", "tech_aqua_horizon", "tech_magenta_cone",
                               "tech_arc_green", "tech_arc_red", "tech_duotone_blob"])

    def test_gallery_and_torture_are_deterministic(self):
        first, second = tech.build_plans(self.family), tech.build_plans(self.family)
        self.assertEqual(first, second)
        self.assertEqual(first["canary_tech_background_v1"]["canvas"]["duration_frames"], 6 * 90)
        self.assertEqual(first["canary_tech_background_torture_v1"]["canvas"]["duration_frames"], 450)

    def test_common_title_is_identical_across_gallery(self):
        plan = tech.build_gallery(self.family)
        self.assertEqual(plan["canvas"]["width"], 960)
        self.assertEqual(plan["canvas"]["height"], 540)
        titles = [layer for layer in plan["layers"] if layer["id"] in {"tech-title-line-1", "tech-title-line-2"}]
        self.assertEqual([item["text"] for item in titles], ["THE FUTURE", "IS ALREADY HERE"])

    def test_primitives_match_each_recipe_language(self):
        recipes = {r["id"]: r for r in self.family["recipes"]}
        for index, ident in enumerate(recipes):
            layers = tech.scene_layers(recipes[ident], 0, tech.SEGMENT, index)
            if ident in {"tech_blue_horizon", "tech_aqua_horizon"}:
                self.assertTrue(any(layer["shape"].get("field") for layer in layers if "shape" in layer))
                self.assertTrue(any(layer["shape"].get("type") == "path" for layer in layers if "shape" in layer))
            elif ident == "tech_magenta_cone":
                self.assertTrue(any(any(effect["type"] == "light_rays" for effect in layer.get("effects", []))
                                    for layer in layers))
            elif ident in {"tech_arc_green", "tech_arc_red"}:
                arcs = [layer for layer in layers if layer.get("shape", {}).get("type") == "arc"]
                self.assertEqual(len(arcs), 2)
                self.assertTrue(all(layer["position"][1] > tech.H for layer in arcs))
            else:
                blobs = [layer for layer in layers if layer.get("shape", {}).get("type") == "ellipse"]
                self.assertEqual(len(blobs), 3)


if __name__ == "__main__":
    unittest.main()
