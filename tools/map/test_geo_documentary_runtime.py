#!/usr/bin/env python3
"""Offline integration contracts for the documentary GeoRuntime API."""
from __future__ import annotations

import subprocess
import tempfile
import time
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
import geo_runtime as geo
import dynamic_tile_pyramid as dyn
import render_dynamic_map_3d_orbit_colosseum as drive_publisher
from fast_plate_sampler import FastPlateSampler
from geo_documentary import draw_geojson_regions


class RuntimeDocumentaryContracts(unittest.TestCase):
    def test_runtime_resolve_uses_offline_geography_catalog_before_remote(self):
        runtime = geo.GeoRuntime(
            out_root=Path(tempfile.mkdtemp()) / "out",
            offline_geocoding=True,
        )
        with mock.patch.object(geo, "geocode", wraps=geo.geocode) as resolve:
            tour = runtime.resolve("Roma")
        self.assertEqual(len(tour.stops), 1)
        self.assertTrue(tour.stops[0].ok)
        self.assertEqual(tour.stops[0].display_name, "Rome, Lazio, IT")
        self.assertIs(resolve.call_args.kwargs["catalog"], runtime._geographic_catalog)
        runtime.close()

    def test_documentary_shot_presets_have_c2_endpoint_poses(self):
        place = geo.Place("Test", lat=41.9, lon=12.5, ok=True)
        earthrise = geo._ShotBuilder(place, "earthrise", 120)
        earthrise.start_zoom, earthrise.end_zoom = 17.5, 5.5
        space = geo._ShotBuilder(place, "space_to_street", 120)
        space.start_zoom, space.end_zoom = 5.0, 18.0
        self.assertAlmostEqual(earthrise.pose(0)[0], 17.5)
        self.assertAlmostEqual(earthrise.pose(119)[0], 5.5)
        self.assertAlmostEqual(space.pose(0)[0], 5.0)
        self.assertAlmostEqual(space.pose(119)[0], 18.0)
        self.assertGreater(geo.check_velocity_strict(earthrise), 0)
        self.assertGreater(geo.check_velocity_strict(space), 0)

    def test_cli_surface_is_repeatable_and_explicit(self):
        result = subprocess.run([sys.executable, str(HERE / "geo_runtime.py"), "--help"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ("--place", "--shot-preset", "--strict-native",
                       "--offline-geocoding", "--online-geocoding", "--geographic-catalog",
                       "--wayback-release", "--documentary", "--beat-times"):
            self.assertIn(option, result.stdout)
        self.assertNotIn("--allow-fallback", result.stdout)

    def test_route_buffer_exact_pixels_and_repeat_allocation(self):
        small = __import__("render_geo_camera_small_places")
        small.WIDTH, small.HEIGHT = 960, 540
        frm, to, anchor, zoom, reveal = (45.3543, 12.0964), (45.3827, 12.1288), (45.37, 12.11), 13.0, .8
        def old_path(frame):
            overlay = np.zeros_like(frame)
            front = reveal * 30
            for i in range(26):
                if i > front: break
                t = i / 25
                lat = frm[0] + (to[0] - frm[0]) * t
                lon = frm[1] + (to[1] - frm[1]) * t
                sx, sy = small.geo_to_screen(lat, lon, anchor, zoom)
                if not (0 <= sx < small.WIDTH and 0 <= sy < small.HEIGHT): continue
                head = max(0., 1. - abs(front-i)*.35); strength=.55+.45*head
                for radius,alpha in ((18,.20*strength),(10,.45*strength),(4,.95*strength)):
                    cv2.circle(overlay,(sx,sy),radius,(int(60*alpha),int(240*alpha),int(255*alpha)),-1,cv2.LINE_AA)
            cv2.addWeighted(overlay,1.,frame,1.,0,dst=frame)
        a=np.random.default_rng(9).integers(0,256,(540,960,3),np.uint8); b=a.copy()
        old_path(a); small.draw_route_glow(b,frm,to,anchor,zoom,reveal)
        self.assertTrue(np.array_equal(a,b))
        scratch=small._ROUTE_GLOW_SCRATCH.buffer
        small.draw_route_glow(b,frm,to,anchor,zoom,reveal)
        self.assertIs(scratch,small._ROUTE_GLOW_SCRATCH.buffer)

    def test_shared_gaussian_halo_matches_premultiplied_linear_light_reference(self):
        mask = np.zeros((65, 65), np.uint8)
        mask[32, 32] = 255
        from glow_primitive import gaussian_halo
        actual = gaussian_halo(mask, (10, 80, 220), sigma=4.0, intensity=.7)
        # Independent 1-D discrete Gaussian matches the engine's radius=ceil(3*sigma)
        # kernel and its linear-premultiplied horizontal/vertical convolution.
        sigma, radius = 4.0, 12
        x = np.arange(-radius, radius + 1, dtype=np.float64)
        kernel = np.exp(-.5 * (x / sigma) ** 2)
        kernel /= kernel.sum()
        alpha = np.zeros((65,65), np.float64)
        alpha[32,32] = 1.0
        filtered = np.outer(kernel, kernel)
        srgb = np.asarray((10,80,220), np.float64) / 255.0
        linear = np.where(srgb <= .04045, srgb / 12.92,
                          ((srgb + .055) / 1.055) ** 2.4)
        # The engine unpremultiplies after the linear blur, encodes straight
        # sRGB, then premultiplies the encoded channels by filtered coverage.
        encoded = np.where(linear <= .0031308, linear * 12.92,
                           1.055 * np.power(linear, 1/2.4) - .055)
        expected_patch = np.clip(
            encoded[None, None, :] * filtered[:, :, None] * .7 * 255,
            0, 255).astype(np.uint8)
        self.assertTrue(np.array_equal(actual[20:45,20:45], expected_patch))

    def test_drive_wrapper_uses_verified_publisher_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            credentials = Path(tmp) / "credentials.json"
            token = Path(tmp) / "token.json"
            executable = Path(tmp) / "drive-upload"
            artifact = Path(tmp) / "render.mp4"
            for path in (credentials, token, executable, artifact):
                path.write_bytes(b"local-test")
            fields = ("DRIVE_UPLOAD_PASS id=file-1 link=https://drive.example/view "
                      "parent=folder-1 sha256=" + "a" * 64 + " bytes=10\n")
            completed = subprocess.CompletedProcess([], 0, fields, "")
            with mock.patch.dict("os.environ", {
                "CHRONON_DRIVE_CREDENTIALS": str(credentials),
                "CHRONON_DRIVE_TOKEN": str(token),
            }), mock.patch.object(drive_publisher, "DRIVE_UPLOAD", executable), \
                 mock.patch.object(drive_publisher.subprocess, "run", return_value=completed) as run:
                result = drive_publisher.upload_to_drive(artifact, "legacy-token-arg", "folder-1")
            self.assertEqual(result["id"], "file-1")
            self.assertEqual(result["parent"], "folder-1")
            self.assertEqual(result["sha256"], "a" * 64)
            self.assertEqual(result["bytes"], 10)
            self.assertIn("-file", run.call_args.args[0])
            self.assertIn("-credentials", run.call_args.args[0])
            self.assertIn("-token", run.call_args.args[0])
            bad = subprocess.CompletedProcess([], 0, "id=file-1 bytes=10", "")
            with mock.patch.dict("os.environ", {
                "CHRONON_DRIVE_CREDENTIALS": str(credentials),
                "CHRONON_DRIVE_TOKEN": str(token),
            }), mock.patch.object(drive_publisher, "DRIVE_UPLOAD", executable), \
                 mock.patch.object(drive_publisher.subprocess, "run", return_value=bad):
                with self.assertRaisesRegex(RuntimeError, "invalid telemetry"):
                    drive_publisher.upload_to_drive(artifact, "legacy-token-arg", "folder-1")

    def test_sampler_missing_prepared_coverage_fails_closed_without_engine_fallback(self):
        class Pyramid:
            def sample_continuous(self, *args):
                return np.zeros((4, 4, 3), np.uint8)
        plate = FastPlateSampler(Pyramid(), 4, 4)
        plate.z_min, plate.z_max = 2, 3
        plate.plates = {}
        with self.assertRaisesRegex(RuntimeError, "prepared plates"):
            plate.sample(0, 0, 4, 4, 4)
        self.assertEqual(plate.fallback_count, 0)
        self.assertFalse(hasattr(plate, "allow_fallback"))

    def test_strict_native_fails_closed_without_opencl(self):
        runtime = geo.GeoRuntime(out_root=Path("/tmp/geo-runtime-native-gate-test"),
                                 strict_native=True)
        with mock.patch.object(cv2.ocl, "haveOpenCL", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "requires OpenCL"):
                runtime._check_native_runtime()

    def test_wayback_is_selected_before_tile_prefetch(self):
        builder = geo._ShotBuilder(geo.Place("Test", lat=0, lon=0, ok=True), "earthrise", 20)
        builder.tile_provider = "esri_wayback"
        builder.wayback_release = 56102
        pyramid = dyn.DynamicTilePyramid(builder.tile_provider,
                                         wayback_release=builder.wayback_release)
        self.assertEqual(pyramid.provider, "esri_wayback")
        self.assertIn("/tile/56102/", pyramid.url_template.format(
            release=pyramid.wayback_release, z=5, y=10, x=10))

    def test_cpu_renderer_is_deterministic_and_opencl_copy_parity(self):
        geometry = {"type":"FeatureCollection","features":[{
            "id":"r","properties":{"name":"r"},"geometry":{"type":"Polygon",
            "coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}]}
        project = lambda lon,lat:(20+int(lon*30),20+int(lat*30))
        base = np.full((80,80,3),30,np.uint8)
        cpu = base.copy()
        draw_geojson_regions(cpu,geometry,project,1,values={"r":1},value_range=(0,2))
        again=base.copy()
        draw_geojson_regions(again,geometry,project,1,values={"r":1},value_range=(0,2))
        self.assertTrue(np.array_equal(cpu,again))
        umat = cv2.UMat(base)
        round_trip = umat.get()
        self.assertTrue(np.array_equal(base, round_trip))

    def test_cpu_opencl_sampler_frame_parity(self):
        if not cv2.ocl.haveOpenCL():
            self.skipTest("OpenCL runtime unavailable")
        cv2.ocl.setUseOpenCL(True)
        if not cv2.ocl.useOpenCL():
            self.skipTest("OpenCL device could not be activated")
        sampler = FastPlateSampler(dyn.DynamicTilePyramid(), 64, 48)
        sampler.z_min, sampler.z_max = 5, 6
        sampler.plates = {}
        for zoom in (5, 6):
            h, w = 1200, 1400
            yy, xx = np.mgrid[:h, :w]
            plate = np.empty((h, w, 3), np.uint8)
            plate[:, :, 0] = (xx * 13 + yy * 3 + zoom) % 256
            plate[:, :, 1] = (xx * 5 + yy * 11 + zoom * 7) % 256
            plate[:, :, 2] = (xx * 7 + yy * 17 + zoom * 19) % 256
            from dynamic_tile_pyramid import latlon_to_global_px
            anchor_px = latlon_to_global_px(0.25, 0.5, zoom)
            sampler.plates[zoom] = [(anchor_px[0] - w / 2,
                                     anchor_px[1] - h / 2, plate)]
        sampler.prepare_opencl()
        cpu = sampler.sample(0.25, 0.5, 5.35, 64, 48)
        gpu = sampler.sample_opencl(0.25, 0.5, 5.35, 64, 48).get()
        delta = np.abs(cpu.astype(np.int16) - gpu.astype(np.int16))
        self.assertLessEqual(int(delta.max()), 2)
        self.assertLessEqual(float(delta.mean()), 0.15)
        self.assertEqual(sampler.fallback_count, 0)


if __name__ == "__main__":
    unittest.main()
