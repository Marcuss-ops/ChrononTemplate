#!/usr/bin/env python3
"""Acceptance tests for certified GPU map scenes and their geographic framing."""
from __future__ import annotations

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
    _text_plate, draw_editorial_scene_gpu, fit_geo_bounds, geo_project,
    gpu_counters, reset_gpu_counters,
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
            projected = np.array(geo_project(*target, anchor, zoom, width, height))
            self.assertLess(float(np.linalg.norm(measured - projected)), 2.0)

    def test_bounds_fit_targets_for_three_scene_cameras(self):
        cases = [
            ((16.0,34.0,33.0,56.0), .74, .90, .70),
            ((12.0,41.5,19.5,47.0), .78, .72, .80),
            ((5.0,37.0,29.0,75.0), .78, .72, .80),
        ]
        for bounds,wf,hf,max_target in cases:
            with self.subTest(bounds=bounds):
                lat,lon,zoom,meta=fit_geo_bounds(bounds,1920,1080,
                    width_fraction=wf,height_fraction=hf,min_zoom=5,max_zoom=8)
                self.assertGreater(zoom,5)
                fw,fh=meta["canvas_fraction"]
                self.assertLessEqual(fw,wf+1e-6)
                self.assertLessEqual(fh,hf+1e-6)
                self.assertGreater(fw,.25)
                self.assertLessEqual(fw,max_target)
                project=lambda y,x: geo_project(y,x,(lat,lon),zoom,1920,1080)
                south,west,north,east=bounds
                xy=[project(y,x) for y in (south,north) for x in (west,east)]
                self.assertTrue(all(0<=x<=1920 and 0<=y<=1080 for x,y in xy))

    def test_capsule_rows_and_marker_labels_have_no_overlaps(self):
        W,H=960,540
        entries=[
            {"text":"SAUDI ARABIA","subtitle":"KINGDOM OF SAUDI ARABIA",
             "center":(480,270),"role":"country","reveal":1.0},
            {"text":"HODEIDAH","center":(380,320),"role":"place","reveal":1.0,
             "leader":(380,320),"candidate_distance":105},
            {"text":"SANAA","center":(410,290),"role":"place","reveal":1.0,
             "leader":(410,290),"candidate_distance":105,
             "candidate_offsets":((1,0),(0,-1),(0,1),(-1,0))},
            {"text":"YEMEN","center":(430,315),"role":"country","reveal":1.0,
             "candidate_distance":80},
        ]
        _rgba, boxes=_text_plate(W,H,entries,1.0,return_layout=True)
        self.assertEqual(len(boxes),4)
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                self.assertFalse(a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3])

    def test_three_scene_temporal_reveals_are_staggered(self):
        from map_editorial_gpu import _stage
        saudi=[_stage(p,0.0,.36) for p in (0,.18,.36,.8)]
        markers=[_stage(p,.28+i*.14,.12) for i in range(3) for p in (.30,.46,.60,.86)]
        route_stages=((.20,.27),(.47,.24),(.72,.22))
        reveals=[_stage(s+.10,s,d) for s,d in route_stages]
        self.assertEqual(saudi[0],0.0);self.assertAlmostEqual(saudi[-1],1.0)
        self.assertEqual([_stage(.34+i*.14,.28+i*.14,.12)>0 for i in range(3)], [True,True,True])
        self.assertEqual([_stage(.34,.28+i*.14,.12)>0 for i in range(3)], [True,False,False])
        self.assertLess(reveals[0],reveals[1]);self.assertLess(reveals[1],reveals[2])
        self.assertGreater(markers[0],0.0)

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
        width, height = 960, 540
        anchor = (15.5, 44.0)
        project = lambda lat, lon: geo_project(lat, lon, anchor, 7.2,
                                                width, height)
        pins = [
            {"id":"hodeidah","latitude": 14.7979, "longitude": 42.9545, "label": "HODEIDAH"},
            {"id":"sanaa","latitude": 15.3694, "longitude": 44.1910, "label": "SANAA"},
            {"id":"abha","latitude": 18.2164, "longitude": 42.5053, "label": "ABHA AIRPORT"},
        ]
        for scene in MAP_EDITORIAL_SCENES:
            with self.subTest(scene=scene):
                reset_gpu_counters()
                frame = cv2.UMat(np.full((height, width, 3),
                                         (80, 90, 100), np.uint8))
                scene_project = project
                if scene == "ed_yemen_markers":
                    scene_project = lambda lat, lon: geo_project(
                        lat, lon, (15.5, 44.0), 6.4, width, height)
                ctx = {"W": width, "H": height, "project": scene_project,
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

    def test_six_clip_render_contract_and_semantic_disclosures(self):
        import render_map_editorial_pack_v1 as pack
        import render_dynamic_map_overlay as renderer
        ids=[entry[0] for entry in pack.CLIPS]
        self.assertEqual(ids,["01_ed_saudi_base","02_ed_iran_glow","03_ed_yemen_fill",
                             "04_ed_yemen_markers","06_ed_mocha_tactical","05_ed_hormuz_routes"])
        self.assertTrue(all((entry[4] if len(entry)>4 else pack.STD_US)==5_000_000
                            for entry in pack.CLIPS))
        source=Path(renderer.__file__).read_text()
        self.assertIn('"ed_iran_glow": (23.5, 46.0, 32.5, 57.0)',source)
        self.assertIn('"ed_mocha_tactical": (12.4, 42.0, 15.8, 45.2)',source)
        gpu_source=(HERE/"map_editorial_gpu.py").read_text()
        self.assertIn("NOT VERIFIED CONTROL DATA",gpu_source)
        self.assertIn("US NAVAL BLOCKADE OF IRAN",gpu_source)
        self.assertIn("EAST-WEST PIPELINE",gpu_source)

    def test_scene_registry_contains_only_six_approved_ids(self):
        self.assertEqual(set(MAP_EDITORIAL_SCENES), {
            "ed_saudi_base", "ed_iran_glow", "ed_yemen_fill",
            "ed_yemen_markers", "ed_hormuz_routes", "ed_mocha_tactical",
        })


if __name__ == "__main__":
    unittest.main()
