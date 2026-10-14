#!/usr/bin/env python3
"""Offline contracts for composable documentary-map runtime layers."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Chronon3d" / "tools" / "cartography"))
import geo_documentary as doc
import geo_runtime as geo
import dynamic_tile_pyramid as dyn
import render_geo_camera_small_places as small


class DocumentaryLayersTests(unittest.TestCase):
    def test_earthrise_schedule_pose_and_beat_sync_are_deterministic(self):
        self.assertEqual(doc.earthrise_zoom(5.0, 18.0, 0.0), (18.0, 0.0))
        self.assertEqual(doc.earthrise_zoom(5.0, 18.0, 1.0), (5.0, 1.0))
        events = doc.beat_schedule([{"id": "route", "time_s": 1.1}], [1.0, 2.0], 30)
        self.assertEqual(events, [{"id": "route", "time_s": 1.0, "frame": 30}])
        pose = (10.0, 20.0, 7.0, 25.0, 90.0)
        self.assertEqual(doc.pose_label_anchor(2, 3, pose,
                         lambda lat, lon, p: (lat+p[3], lon+p[4])), (27, 93))

    def test_geojson_draw_on_holes_and_choropleth(self):
        frame = np.zeros((120, 160, 3), np.uint8)
        geojson = {"type": "FeatureCollection", "features": [{
            "id": "north", "properties": {"name": "north"},
            "geometry": {"type": "Polygon", "coordinates": [
                [[0,0],[1,0],[1,1],[0,1],[0,0]],
                [[.4,.4],[.6,.4],[.6,.6],[.4,.6],[.4,.4]],
            ]}}]}
        project = lambda lon, lat: (round(10+lon*100), round(10+lat*90))
        doc.draw_geojson_regions(frame, geojson, project, 1,
                                values={"north": 5}, value_range=(0,10), fill_alpha=.5)
        self.assertGreater(int(frame[25, 25].max()), 0)
        self.assertTrue(np.array_equal(frame[55, 60], np.zeros(3, np.uint8)))
        self.assertTrue(np.any(frame[38:82, 38:82] != 0), "choropleth numeric label should be drawn inside region")
        with self.assertRaises(ValueError):
            doc.draw_geojson_regions(frame, {"type": "FeatureCollection", "features": []},
                                     project, 0, values={"x": float("nan")})

    def test_radar_and_diagonal_epoch_wipe(self):
        frame = np.zeros((100,100,3), np.uint8)
        doc.draw_radar_pulse(frame, (50,50), .3)
        self.assertGreater(int(frame.max()), 0)
        before = np.zeros((4,4,3), np.uint8)
        after = np.full_like(before, 255)
        out = doc.diagonal_wipe(before, after, .5)
        self.assertTrue(np.any(out == 255) and np.any(out == 0))
        with self.assertRaises(ValueError):
            doc.diagonal_wipe(before, after[:2], .5)

    def test_diagonal_wipe_umat_matches_cpu_and_stays_on_opencl(self):
        if not cv2.ocl.haveOpenCL():
            self.skipTest("OpenCL runtime unavailable")
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            self.skipTest("OpenCL device could not be activated")
        rng = np.random.default_rng(23)
        before = rng.integers(0, 256, (48, 64, 3), dtype=np.uint8)
        after = rng.integers(0, 256, (48, 64, 3), dtype=np.uint8)
        expected = doc.diagonal_wipe(before, after, .43)
        result = doc.diagonal_wipe(cv2.UMat(before), cv2.UMat(after), .43,
                                   frame_shape=before.shape[:2])
        self.assertIsInstance(result, cv2.UMat)
        self.assertTrue(np.array_equal(expected, result.get()))
        self.assertIsInstance(doc._WIPE_DIAGONAL_FIELDS[(48, 64)], cv2.UMat)

    def test_diagonal_wipe_rejects_inactive_opencl_for_umat(self):
        before = cv2.UMat(np.zeros((4, 4, 3), np.uint8))
        after = cv2.UMat(np.full((4, 4, 3), 255, np.uint8))
        with mock.patch.object(cv2.ocl, "useOpenCL", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "OpenCL must be active"):
                doc.diagonal_wipe(before, after, .5, frame_shape=(4, 4))

    def test_hillshade_and_space_to_street(self):
        base = np.full((12,16,3), 100, np.uint8)
        relief = np.full((12,16), 220, np.uint8)
        out = doc.apply_hillshade(base, relief, .5)
        self.assertEqual(int(out[0,0,0]), 160)
        self.assertEqual(doc.space_to_street_zoom(0), 5.0)
        self.assertEqual(doc.space_to_street_zoom(1), 18.0)

    def test_geojson_lines_and_epoch_pair_sampling(self):
        frame = np.zeros((32,32,3), np.uint8)
        lines = {"type":"FeatureCollection","features":[{"type":"Feature",
                 "geometry":{"type":"LineString","coordinates":[[0,0],[1,1]]},
                 "properties":{}}]}
        doc.draw_geojson_lines(frame, lines, lambda x,y:(round(x*20),round(y*20)), 1)
        self.assertGreater(int(frame.max()), 0)
        before = np.zeros_like(frame)
        after = np.full_like(frame, 180)
        class Sampler:
            def __init__(self, image): self.image = image
            def sample(self, *args): return self.image.copy()
        result = doc.sample_epoch_pair(Sampler(before), Sampler(after), 0,0,5,32,32,.5)
        self.assertTrue(np.any(result == 180) and np.any(result == 0))

    def test_feature_id_value_and_feature_collection_validation(self):
        frame = np.zeros((48,48,3), np.uint8)
        geometry = {"type":"FeatureCollection","features":[{
            "type":"Feature","id":"numeric-id","properties":{"name":"display-name"},
            "geometry":{"type":"Polygon","coordinates":[[
                [0,0],[1,0],[1,1],[0,1],[0,0]]]}}]}
        doc.draw_geojson_regions(frame, geometry, lambda x,y:(8+round(x*24),8+round(y*24)),
                                 1, values={"numeric-id":7}, value_range=(0,10))
        self.assertGreater(int(frame[24,24].max()), 0)
        with self.assertRaises(ValueError):
            doc.draw_geojson_regions(frame, {"type":"FeatureCollection","features":[{}]},
                                     lambda x,y:(x,y), 1)
        with self.assertRaises(ValueError):
            doc.draw_geojson_regions(frame, geometry, lambda x,y:(x,y), 1, fill_alpha=2)

    def test_route_beat_actions_are_separate_from_tour_phase_schedule(self):
        stops = [geo.Place("A", lat=1, lon=2, ok=True),
                 geo.Place("B", lat=1.1, lon=2.1, ok=True)]
        builder = geo.TourBuilder(stops, seconds_per_stop=1, travel_seconds=1,
                                  beat_events=[{"frame":5,"action":"route"}])
        schedule = builder._schedule()
        self.assertEqual(len(schedule), 3)
        self.assertTrue(all(isinstance(mark[2], int) for mark in schedule))
        self.assertEqual(builder.TOTAL_FRAMES, sum(mark[1]-mark[0] for mark in schedule))
        with self.assertRaises(ValueError):
            geo.TourBuilder(stops, seconds_per_stop=1, travel_seconds=1,
                            beat_events=[{"frame":builder.TOTAL_FRAMES,"action":"pin"}])

    def test_roi_route_buffer_preserves_reference_pixels(self):
        small.WIDTH, small.HEIGHT = 320, 180
        frame = np.full((180,320,3), 40, np.uint8)
        reference = frame.copy()
        start, end, anchor, zoom, reveal = (45.35,12.09),(45.38,12.13),(45.36,12.11),12.0,.8
        overlay = np.zeros_like(reference)
        front = reveal * 30
        for i in range(26):
            if i > front: break
            t=i/25
            lat=start[0]+(end[0]-start[0])*t
            lon=start[1]+(end[1]-start[1])*t
            sx,sy=small.geo_to_screen(lat,lon,anchor,zoom)
            if not (0<=sx<small.WIDTH and 0<=sy<small.HEIGHT): continue
            head=max(0.,1.-abs(front-i)*.35); strength=.55+.45*head
            for radius,alpha in ((18,.20*strength),(10,.45*strength),(4,.95*strength)):
                cv2.circle(overlay,(sx,sy),radius,(int(60*alpha),int(240*alpha),int(255*alpha)),-1,cv2.LINE_AA)
        cv2.addWeighted(overlay,1.,reference,1.,0,dst=reference)
        small.draw_route_glow(frame,start,end,anchor,zoom,reveal)
        self.assertTrue(np.array_equal(frame,reference))
        scratch=small._ROUTE_GLOW_SCRATCH.buffer
        small.draw_route_glow(frame,start,end,anchor,zoom,reveal)
        self.assertIs(scratch,small._ROUTE_GLOW_SCRATCH.buffer)

    def test_wayback_release_is_explicit_and_changes_url_path(self):
        with self.assertRaises(ValueError):
            dyn.DynamicTilePyramid("esri_wayback")
        with self.assertRaises(ValueError):
            dyn.DynamicTilePyramid("esri_sat", wayback_release=12)
        pyramid = dyn.DynamicTilePyramid("esri_wayback", wayback_release=56102)
        second_epoch = dyn.DynamicTilePyramid("esri_wayback", wayback_release=56103)
        self.assertNotEqual(pyramid.cache_namespace, second_epoch.cache_namespace)
        url = pyramid.url_template.format(release=pyramid.wayback_release,
                                          z=15, y=123, x=456)
        self.assertTrue(url.endswith("/tile/56102/15/123/456"))

    def test_wayback_release_uses_separate_persistent_cache_namespaces(self):
        first = dyn.DynamicTilePyramid("esri_wayback", wayback_release=1001)
        second = dyn.DynamicTilePyramid("esri_wayback", wayback_release=1002)
        self.assertNotEqual(first.cache_namespace, second.cache_namespace)
        self.assertEqual(first.cache_namespace, "esri_wayback_1001")
        self.assertEqual(second.cache_namespace, "esri_wayback_1002")

    def test_route_glow_reuses_scratch_buffer_without_changing_reference_pixels(self):
        frame = np.zeros((1080,1920,3), np.uint8)
        small.WIDTH, small.HEIGHT = 1920,1080
        small.draw_route_glow(frame, (45.35,12.09), (45.38,12.13),
                              (45.36,12.11), 16.0, .8)
        first = small._ROUTE_GLOW_SCRATCH.buffer
        self.assertGreater(int(frame.max()), 0)
        frame.fill(0)
        small.draw_route_glow(frame, (45.35,12.09), (45.38,12.13),
                              (45.36,12.11), 16.0, .8)
        self.assertIs(small._ROUTE_GLOW_SCRATCH.buffer, first)
        self.assertGreater(int(frame.max()), 0)


if __name__ == "__main__":
    unittest.main()
