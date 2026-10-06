from __future__ import annotations

import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "background_recreation", ROOT / "tools/backgrounds/render_background_recreation_v1.py")
backgrounds = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(backgrounds)


class BackgroundRecreationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes = backgrounds.recipes()
        cls.by_id = dict(cls.recipes)

    def test_exact_family_counts_and_stable_unique_ids(self):
        ids = [ident for ident, _ in self.recipes]
        self.assertEqual(len(ids), 43)
        self.assertEqual(len(set(ids)), 43)
        self.assertEqual(sum(ident.startswith("wave_") for ident in ids), 16)
        self.assertEqual(sum(ident.startswith("neon_") for ident in ids), 8)
        self.assertEqual(sum(ident.startswith("cinematic_") for ident in ids), 19)
        self.assertEqual(ids, [ident for ident, _ in backgrounds.recipes()])

    def test_every_recipe_is_a_five_second_background_only_renderplan(self):
        expected_canvas = {"width": 1920, "height": 1080, "fps_num": 30,
                           "fps_den": 1, "duration_frames": 150}
        for ident, layers in self.recipes:
            with self.subTest(ident=ident):
                plan = backgrounds.make_plan(ident, layers, Path(f"{ident}.mp4"))
                self.assertEqual(plan["canvas"], expected_canvas)
                self.assertEqual(plan["schema"], "chronon.render-plan.v3")
                self.assertGreaterEqual(len(layers), 4)
                self.assertEqual(len({layer["id"] for layer in layers}), len(layers))
                self.assertTrue(all(layer.get("type") != "text" for layer in layers))
                self.assertEqual(layers[0]["type"], "color")
                self.assertEqual(layers[0]["start_frame"], 0)
                self.assertEqual(layers[0]["duration_frames"], 150)

    def test_generated_values_and_tracks_are_finite_and_in_range(self):
        def visit(value, path):
            if isinstance(value, float):
                self.assertTrue(math.isfinite(value), path)
            elif isinstance(value, dict):
                for key, child in value.items():
                    visit(child, f"{path}.{key}")
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]")

        for ident, layers in self.recipes:
            with self.subTest(ident=ident):
                visit(layers, ident)
                for layer in layers:
                    for track in layer.get("animation", {}).get("tracks", []):
                        frames = [key["frame"] for key in track["keyframes"]]
                        self.assertEqual(frames, sorted(set(frames)), layer["id"])
                        self.assertEqual(frames[0], 0, layer["id"])
                        self.assertEqual(frames[-1], 149, layer["id"])

    def test_family_specific_compositions_are_distinct_and_use_expected_shapes(self):
        waves = [layers for ident, layers in self.recipes if ident.startswith("wave_")]
        neon = [layers for ident, layers in self.recipes if ident.startswith("neon_")]
        cinematic = [layers for ident, layers in self.recipes if ident.startswith("cinematic_")]
        self.assertEqual(len({repr(layers) for layers in waves}), 16)
        self.assertEqual(len({repr(layers) for layers in neon}), 8)
        self.assertEqual(len({repr(layers) for layers in cinematic}), 19)
        self.assertTrue(all(any(layer.get("shape", {}).get("type") == "ellipse" for layer in layers)
                            for layers in waves))
        self.assertTrue(all(not any(layer.get("shape", {}).get("type") == "path" for layer in layers)
                            for _, layers in self.recipes))
        for ident, layers in self.recipes:
            with self.subTest(ident=ident):
                moving = [layer for layer in layers
                          if backgrounds._layer_motion_span(layer) >= 80 and
                          {"position", "scale", "opacity"}.issubset(
                              {track["property"] for track in layer.get("animation", {}).get("tracks", [])})]
                self.assertGreaterEqual(len(moving), 2)
                backgrounds._validate_recipe_visual_contracts([(ident, layers)])
        self.assertTrue(all(any(layer.get("shape", {}).get("type") in {"ellipse", "rect"}
                                for layer in layers) for layers in neon))
        self.assertTrue(all(any(layer.get("shape", {}).get("type") in {"ellipse", "path"}
                                for layer in layers) for layers in cinematic))

    def test_video_verifier_rejects_missing_artifacts(self):
        with self.assertRaises(RuntimeError):
            backgrounds.validate_video(ROOT / "out" / "nonexistent-background.mp4", "missing")

    def test_decoded_motion_gate_rejects_static_video_and_accepts_visible_drift(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            static = Path(temp) / "static.mp4"
            moving = Path(temp) / "moving.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30:d=5",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(static)],
                check=True)
            with self.assertRaisesRegex(RuntimeError, "too subtle"):
                backgrounds.validate_motion(static, "static")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=5",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(moving)],
                check=True)
            self.assertGreater(backgrounds.validate_motion(moving, "moving"), .35)

    def test_contact_sheet_is_emitted_for_verified_posters(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            entries = []
            for ident in ("wave_01", "neon_01", "cinematic_01"):
                Image.new("RGB", (1920, 1080), (20, 60, 90)).save(out / f"{ident}.jpg")
                entries.append({"id": ident})
            sheet = backgrounds.write_contact_sheet(entries, out)
            self.assertTrue(sheet.is_file())
            with Image.open(sheet) as image:
                self.assertEqual(image.size, (2 * 18 + 6 * 320 + 5 * 12,
                                              2 * 18 + 180 + 28))


if __name__ == "__main__":
    unittest.main()
