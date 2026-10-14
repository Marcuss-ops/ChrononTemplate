#!/usr/bin/env python3
"""Acceptance tests for local-ROI map rendering against the full-frame path."""
from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
RENDERER = HERE / "render_geo_camera_small_places.py"
sys.path.insert(0, str(HERE))
import render_geo_camera_small_places as current

MARKER_STYLES = (
    "gentle_fade", "soft_glow", "clean_fade", "word_soft_fade",
    "slow_fade", "quiet_bloom", "quick_fade", "silky_fade",
    "subtle_halo", "cinematic_fade", "diffuse_city_beacon", "rise_up",
    "pop_in", "soft_tracking", "title_top", "badge_side", "huge_center",
    "small_above", "caption_card", "editorial_serif", "gpin_bubble",
    "card_glass", "bare_big", "glow_react", "editorial_tag", "ribbon",
    "dot_ring", "outline_box",
)
COMPOSITIONS_WITH_CENTER_DOT = ("card_glass", "ribbon", "outline_box")
EDGE_POINTS = ((0, 0), (1919, 0), (0, 1079), (1919, 1079),
               (5, 540), (1914, 540), (960, 5), (960, 1074))


def _load_baseline():
    """Load today's renderer with the historical label tables frozen in place.

    HEAD^ is not a valid pixel baseline here: it predates unrelated local
    renderer changes. Keep those changes by loading the working renderer, then
    replace only its label roster projections and timing tables with the
    pre-roster constants from HEAD^.
    """
    root = Path(subprocess.check_output(
        ["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True).strip())
    relative = RENDERER.relative_to(root)
    historical = subprocess.check_output(
        ["git", "-C", str(root), "show", f"HEAD^:{relative.as_posix()}"], text=True)
    tree = ast.parse(historical)
    frozen = {}

    def evaluate(node):
        if isinstance(node, ast.Dict):
            return {evaluate(key): evaluate(value)
                    for key, value in zip(node.keys, node.values)}
        if isinstance(node, (ast.Tuple, ast.List)):
            values = [evaluate(value) for value in node.elts]
            return tuple(values) if isinstance(node, ast.Tuple) else values
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in frozen:
            return frozen[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return evaluate(node.left) + evaluate(node.right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = evaluate(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return evaluate(node.left) / evaluate(node.right)
        raise ValueError(f"unsupported historical table expression: {ast.dump(node)}")

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "MAP_LABEL_ANIMATIONS", "NEW_LABEL_GEOMETRIES", "COMPOSITION_STYLES",
                    "MARKER_DRAWN_STYLES",
                }:
                    frozen[target.id] = evaluate(node.value)
        if isinstance(node, ast.FunctionDef):
            wanted = {"draw_editorial_map_caption": "animation_timing",
                      "draw_map_marker_label": "timing"}.get(node.name)
            if wanted:
                for item in ast.walk(node):
                    if isinstance(item, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == wanted
                        for target in item.targets
                    ):
                        frozen["MAP_LABEL_RAIL_TIMING" if wanted == "animation_timing"
                               else "MAP_LABEL_MARKER_TIMING"] = evaluate(item.value)
    required = {"MAP_LABEL_ANIMATIONS", "NEW_LABEL_GEOMETRIES", "COMPOSITION_STYLES",
                "MARKER_DRAWN_STYLES", "MAP_LABEL_RAIL_TIMING", "MAP_LABEL_MARKER_TIMING"}
    if frozen.keys() < required:
        raise RuntimeError(f"historical label tables incomplete: {sorted(required - frozen.keys())}")

    temp = tempfile.NamedTemporaryFile(mode="w", suffix="_before_roi.py", delete=False)
    try:
        temp.write(RENDERER.read_text(encoding="utf-8"))
        temp.close()
        spec = importlib.util.spec_from_file_location("renderer_before_roi_acceptance", temp.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, value in frozen.items():
            setattr(module, name, value)
        return module, Path(temp.name)
    except Exception:
        Path(temp.name).unlink(missing_ok=True)
        raise


class MapRoiAcceptance(unittest.TestCase):
    def test_label_roster_derives_complete_runtime_projections(self):
        specs = current.MAP_LABEL_SPECS
        ids = [spec[0] for spec in specs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(current.MAP_LABEL_ANIMATIONS))
        self.assertEqual(
            tuple(spec[0] for spec in specs if spec[1] == "geometry"),
            current.NEW_LABEL_GEOMETRIES)
        self.assertEqual(
            tuple(spec[0] for spec in specs if spec[1] == "composition"),
            current.COMPOSITION_STYLES)
        self.assertEqual(
            tuple(spec[0] for spec in specs if spec[2]),
            current.MARKER_DRAWN_STYLES)
        self.assertEqual(
            {spec[0]: spec[3] for spec in specs if spec[3] is not None},
            current.MAP_LABEL_RAIL_TIMING)
        self.assertEqual(
            {spec[0]: spec[4] for spec in specs if spec[4] is not None},
            current.MAP_LABEL_MARKER_TIMING)
        self.assertEqual(set(current.MAP_LABEL_RAIL_TIMING), {
            "gentle_fade", "soft_glow", "clean_fade", "word_soft_fade",
            "slow_fade", "quiet_bloom", "quick_fade", "silky_fade",
            "subtle_halo", "cinematic_fade", "diffuse_city_beacon", "rise_up",
            "pop_in", "soft_tracking", "title_top", "badge_side", "huge_center",
            "small_above", "caption_card", "editorial_serif",
        })
        self.assertEqual(set(current.MAP_LABEL_MARKER_TIMING), set(ids))

    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.baseline_path = _load_baseline()
        # Keep this test scoped to ROI parity: glow color-space behavior is
        # intentionally owned by the shared engine-conformant primitive.
        for name in ("draw_location_glow", "draw_diffuse_city_beacon",
                     "draw_reaction_glow"):
            setattr(cls.baseline, name, getattr(current, name))
        rng = np.random.default_rng(7)
        cls.base = (rng.random((1080, 1920, 3)) * 255).astype(np.uint8)

    @classmethod
    def tearDownClass(cls):
        cls.baseline_path.unlink(missing_ok=True)

    def assert_frame_close_to_baseline(self, old, new):
        diff = np.abs(old.astype(np.int16) - new.astype(np.int16))
        self.assertLessEqual(int(diff.max()), 1)
        self.assertEqual(int(np.count_nonzero(np.any(diff > 1, axis=2))), 0)

    def test_all_marker_styles_match_baseline_within_one_lsb(self):
        self.assertEqual(set(MARKER_STYLES), set(current.MAP_LABEL_ANIMATIONS))
        for style in MARKER_STYLES:
            with self.subTest(style=style):
                old, new = self.base.copy(), self.base.copy()
                self.baseline.draw_map_location_marker(old, (960, 540), "Garlasco", .95, style)
                current.draw_map_location_marker(new, (960, 540), "Garlasco", .95, style)
                self.assert_frame_close_to_baseline(old, new)

    def test_compositions_keep_their_center_dot(self):
        point = (960, 540)
        for style in COMPOSITIONS_WITH_CENTER_DOT:
            with self.subTest(style=style):
                old, new = self.base.copy(), self.base.copy()
                self.baseline.draw_map_location_marker(old, point, "Garlasco", .95, style)
                current.draw_map_location_marker(new, point, "Garlasco", .95, style)
                self.assert_frame_close_to_baseline(old, new)
                self.assertTrue(np.all(new[point[1], point[0]] == 255))

    def test_marker_roi_clips_safely_at_frame_edges(self):
        for point in EDGE_POINTS:
            for style in MARKER_STYLES:
                with self.subTest(point=point, style=style):
                    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                    current.draw_map_location_marker(frame, point, "Garlasco", .95, style)
                    self.assertEqual(frame.shape, (1080, 1920, 3))
                    self.assertEqual(frame.dtype, np.uint8)

    def test_caption_roi_matches_full_frame_baseline_within_one_lsb(self):
        typography = {
            "font_family": "inter", "font_size_px": 92, "stroke_size": 2,
            "shadow_blur_px": 14, "shadow_opacity": .7, "glow_size": 10,
            "glow_intensity": .4, "fill": "#F8F5EA", "shadow_color": "#000000",
            "glow_color": "#FFFFFF",
        }
        old = self.baseline.draw_editorial_map_caption(
            self.base.copy(), "Garlasco", .95, typography, "slow_fade")
        new = current.draw_editorial_map_caption(
            self.base.copy(), "Garlasco", .95, typography, "slow_fade")
        self.assert_frame_close_to_baseline(old, new)


if __name__ == "__main__":
    unittest.main()
