import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "abstract_backgrounds", ROOT / "tools/render_abstract_cinematic_backgrounds_v1.py")
backgrounds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backgrounds)


class AbstractCinematicBackgroundTests(unittest.TestCase):
    def test_recipe_generation_is_deterministic_and_covers_film_burn(self):
        first = backgrounds.recipes()
        self.assertEqual(first, backgrounds.recipes())
        ids = [name for name, _ in first]
        self.assertIn("cinematic_leak_film_burn", ids)
        self.assertIn("cinematic_leak_warped_ring", ids)
        self.assertIn("abstract_topographic_contours", ids)

    def test_animation_keys_are_finite_and_random_access_ready(self):
        for name, layers in backgrounds.recipes():
            for layer in layers:
                for track in layer.get("animation", {}).get("tracks", []):
                    keys = track["keyframes"]
                    frames = [key["frame"] for key in keys]
                    self.assertEqual(frames, sorted(set(frames)), (name, layer["id"]))
                    for key in keys:
                        values = key["value"] if isinstance(key["value"], list) else [key["value"]]
                        self.assertTrue(all(math.isfinite(value) for value in values), layer["id"])

    def test_offscreen_emitters_remain_valid_authored_sources(self):
        names = {name: layers for name, layers in backgrounds.recipes()}
        edge_layers = names["cinematic_leak_edge_burn"]
        emitter = next(layer for layer in edge_layers if layer["id"] == "edge-burn")
        self.assertGreater(emitter["position"][0] + emitter["size"][0] / 2,
                           backgrounds.W)
        self.assertEqual(emitter["start_frame"], 0)
        self.assertEqual(emitter["duration_frames"], backgrounds.FRAMES)


if __name__ == "__main__":
    unittest.main()
