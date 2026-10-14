#!/usr/bin/env python3
"""Regression tests for the Documentary Graphics 2.0 reference suite."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
from PIL import Image

HERE = Path(__file__).resolve()
MODULE_PATH = HERE.with_name("documentary_quality_v2.py")
spec = importlib.util.spec_from_file_location("documentary_quality_v2", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
DOC = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = DOC
spec.loader.exec_module(DOC)


class DocumentaryQualityV2Tests(unittest.TestCase):
    def test_five_complete_eight_second_plans_are_deterministic(self) -> None:
        first = [builder() for builder in DOC.BUILDERS]
        second = [builder() for builder in DOC.BUILDERS]
        self.assertEqual(len(first), 5)
        self.assertEqual(first, second)
        self.assertEqual(len({plan["job_id"] for plan in first}), 5)
        for plan in first:
            with self.subTest(plan=plan["job_id"]):
                self.assertEqual(plan["schema"], "chronon.render-plan.v3")
                self.assertEqual(plan["canvas"], {
                    "width": 1920, "height": 1080, "fps_num": 30,
                    "fps_den": 1, "duration_frames": 240})
                self.assertEqual(plan["output"]["codec"], "h264")
                self.assertGreaterEqual(len(plan["layers"]), 10)

    def test_documentary_scenes_have_real_image_context_and_native_spans(self) -> None:
        plans = [builder() for builder in DOC.BUILDERS]
        for plan in plans[:3] + plans[4:]:
            with self.subTest(plan=plan["job_id"]):
                self.assertTrue(any(layer.get("type") == "image" for layer in plan["layers"]))
                self.assertTrue(all(layer.get("asset") == DOC.PHOTO for layer in plan["layers"]
                                    if layer.get("type") == "image"))
                self.assertTrue(any(layer.get("spans") for layer in plan["layers"]))
        multiline = plans[2]
        span_layers = [layer for layer in multiline["layers"] if layer.get("spans")]
        self.assertEqual(len(span_layers), 3)
        for layer in span_layers:
            value = layer["text"].encode("utf-8")
            for text_span in layer["spans"]:
                self.assertLessEqual(text_span["end"], len(value))
                self.assertLess(text_span["start"], text_span["end"])
                self.assertEqual(value[text_span["start"]:text_span["end"]].decode("utf-8"),
                                 {"line-1": "overlooked", "line-2": "three days",
                                  "line-3": "changes the sequence"}[layer["id"]])

    def test_data_scene_is_honestly_labeled_as_illustrative(self) -> None:
        plan = DOC.data_visualization()
        text = " ".join(layer.get("text", "") for layer in plan["layers"])
        self.assertIn("illustrative dataset", text)
        self.assertIn("not historical financial data", text)
        self.assertEqual(sum(bool(re.fullmatch(r"bar-\d+", layer["id"]))
                             for layer in plan["layers"]), 6)

    def test_documentary_glow_uses_shared_fine_warm_stroke_without_neon(self) -> None:
        plan = DOC.evidence_connection()
        path_layers = [layer for layer in plan["layers"]
                       if layer.get("id", "").startswith("date_connection")]
        self.assertEqual([layer["id"] for layer in path_layers],
                         ["date_connection_soft", "date_connection_core"])
        self.assertEqual([layer["shape"]["stroke"]["width"] for layer in path_layers], [5.0, 1.8])
        self.assertTrue(all(layer["shape"]["stroke"]["color"] == DOC.AMBER
                            for layer in path_layers))
        self.assertFalse(any(layer.get("effects") for layer in path_layers))
        self.assertFalse(any(layer.get("id", "").startswith(("premium_", "wp_ripple"))
                             for layer in plan["layers"]))

    def test_source_photo_is_optimized_below_one_megabyte(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="doc-photo-v2-test-") as tmp:
            path = DOC.prepare_photo_asset(Path(tmp))
            self.assertLess(path.stat().st_size, 1_000_000)
            with Image.open(path) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(max(image.size), 1440)

    def test_emit_only_writes_five_plans_and_no_png_or_video(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="doc-quality-v2-test-") as tmp:
            out = Path(tmp)
            paths = DOC.emit(out)
            self.assertEqual(len(paths), 5)
            self.assertEqual({path.suffix for path in paths}, {".json"})
            self.assertEqual(len(list(out.glob("*.plan.json"))), 5)
            self.assertFalse(list(out.glob("*.png")))
            self.assertFalse(list(out.glob("*.mp4")))
            self.assertLess((out / "assets/industrial_port_dawn.jpg").stat().st_size, 1_000_000)
            for path in paths:
                plan = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(Path(plan["output"]["path"]).parent, out.resolve())


if __name__ == "__main__":
    unittest.main()
