#!/usr/bin/env python3
"""Acceptance tests for the six GPU-certified Middle East map scenes."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Chronon3d" / "tools" / "cartography"))
sys.path.insert(0, str(HERE))

from dynamic_tile_pyramid import latlon_to_global_px
from fast_plate_sampler import FastPlateSampler
from map_editorial import MAP_EDITORIAL_SCENES, load_borders
from map_editorial_gpu import (
    draw_editorial_scene_gpu, geo_project, gpu_counters, reset_gpu_counters,
)


class EditorialProjectionTests(unittest.TestCase):
    def test_screen_projection_matches_opencl_sampler_at_real_zooms(self):
        width, height = 960, 540
        anchor = (22.0, 53.0)
        target = (24.7136, 46.6753)
        sampler = FastPlateSampler(None, width, height)
        sampler.z_min, sampler.z_max = 5, 6
        sampler.opencl_plates = {}
        for z in (5, 6):
            ax, ay = latlon_to_global_px(*anchor, z)
            tx, ty = latlon_to_global_px(*target, z)
            left, top = ax - 2 * width - 10, ay - 2 * height - 10
            pw, ph = 4 * width + 20, 4 * height + 20
            plate = np.zeros((ph, pw, 3), np.uint8)
            cv2.circle(plate, (round(tx - left), round(ty - top)), 5,
                       (255, 255, 255), -1)
            sampler.opencl_plates[z] = [(left, top, cv2.UMat(plate), pw, ph)]
        for zoom in (5.0, 5.4, 6.0):
            actual = sampler.sample_opencl(*anchor, zoom, width, height).get()
            ys, xs = np.where(actual[:, :, 0] > 245)
            self.assertGreater(len(xs), 0)
            measured = np.array([xs.mean(), ys.mean()])
            projected = np.array(geo_project(*target, anchor, zoom,
                                             width, height))
            self.assertLess(float(np.linalg.norm(measured - projected)), 2.0)

    def test_country_geometries_are_available_and_nontrivial(self):
        data = load_borders()
        for iso in ("SAU", "IRN", "YEM", "OMN", "ARE"):
            with self.subTest(iso=iso):
                self.assertIn(iso, data)
                self.assertTrue(any(len(ring) >= 20 for ring in data[iso]["polygons"]))

    def test_six_scenes_use_opencl_compositing_and_reject_cpu_frame(self):
        if not cv2.ocl.haveOpenCL():
            self.skipTest("OpenCL runtime unavailable")
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            self.skipTest("OpenCL device could not be activated")
        width, height = 640, 360
        anchor = (22.0, 53.0)
        project = lambda lat, lon: geo_project(lat, lon, anchor, 5.2,
                                                width, height)
        pins = [
            {"latitude": 14.7979, "longitude": 42.9545, "label": "HODEIDAH"},
            {"latitude": 15.3694, "longitude": 44.1910, "label": "SANAA"},
            {"latitude": 18.2164, "longitude": 42.5053, "label": "ABHA AIRPORT"},
        ]
        for scene in MAP_EDITORIAL_SCENES:
            with self.subTest(scene=scene):
                reset_gpu_counters()
                frame = cv2.UMat(np.full((height, width, 3),
                                         (80, 90, 100), np.uint8))
                ctx = {"W": width, "H": height, "project": project,
                       "pins": pins if scene == "ed_yemen_markers" else []}
                result = draw_editorial_scene_gpu(frame, scene, ctx, 0.9)
                self.assertIsInstance(result, cv2.UMat)
                image = result.get()
                self.assertEqual(image.shape, (height, width, 3))
                self.assertGreater(float(np.std(image)), 1.0)
                counts = gpu_counters()
                self.assertGreater(counts["opencl"], 0)
                self.assertGreater(counts["composites"], 0)
                with self.assertRaises(TypeError):
                    draw_editorial_scene_gpu(np.zeros_like(image), scene, ctx, 0.9)

    def test_scene_registry_contains_only_six_approved_ids(self):
        self.assertEqual(set(MAP_EDITORIAL_SCENES), {
            "ed_saudi_base", "ed_iran_glow", "ed_yemen_fill",
            "ed_yemen_markers", "ed_hormuz_routes", "ed_mocha_tactical",
        })


if __name__ == "__main__":
    unittest.main()
