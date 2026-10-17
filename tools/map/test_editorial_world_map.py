"""Offline checks for editorial_world_map.py (no ffmpeg needed)."""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import editorial_world_map as wm


class MercatorParityTests(unittest.TestCase):
    # Certified vectors shared with RenderingGen internal/geo and
    # ChrononMotion3D motion_geospatial.cpp. X/Y must match to 1e-6.
    VECTORS = [
        (41.890210, 12.492231, 14, 2242697.0401450666, 1558716.8764844453),
        (29.86, -92.70, 8, 15892.48, 27067.93732941762),
        (33.9598, -83.3768, 16, 4502967.491697778, 6704228.367772281),
        (0.0, 0.0, 0, 128.0, 128.0),
    ]

    def test_matches_certified_reference_pixels(self) -> None:
        for lat, lon, zoom, want_x, want_y in self.VECTORS:
            x, y = wm.latlon_to_global(lat, lon, zoom)
            self.assertAlmostEqual(x, want_x, delta=1e-6)
            self.assertAlmostEqual(y, want_y, delta=1e-6)

    def test_round_trip(self) -> None:
        for lat, lon, zoom, _, _ in self.VECTORS:
            x, y = wm.latlon_to_global(lat, lon, zoom)
            rlat, rlon = wm.global_to_latlon(x, y, zoom)
            self.assertAlmostEqual(rlat, lat, delta=1e-9)
            self.assertAlmostEqual(rlon, lon, delta=1e-9)

    def test_certified_gulf_corridor_window(self) -> None:
        win = wm.Window.centered_on(29.86, -92.70, 8, 1920, 1080)
        cx, cy = win.to_raster(29.86, -92.70)
        self.assertAlmostEqual(cx, 960.0, delta=0.01)
        self.assertAlmostEqual(cy, 540.0, delta=0.01)
        self.assertEqual(
            (round(win.to_raster(29.7604, -95.3698)[0]),
             round(win.to_raster(29.7604, -95.3698)[1])), (474, 561))
        self.assertEqual(
            (round(win.to_raster(29.9654, -90.0321)[0]),
             round(win.to_raster(29.9654, -90.0321)[1])), (1446, 518))
        self.assertTrue(win.contains(29.7604, -95.3698))
        self.assertFalse(win.contains(48.8566, 2.3522))


class SceneTableTests(unittest.TestCase):
    def test_world_covers_four_continents(self) -> None:
        iso2s = {s.get("country_iso2") for s in wm.WORLD_SCENES}
        self.assertGreaterEqual(len(iso2s), 8)

    def test_slugs_unique(self) -> None:
        slugs = [s["slug"] for s in wm.SCENES]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_every_scene_resolves(self) -> None:
        for scene in wm.SCENES:
            with self.subTest(scene=scene["slug"]):
                features, _ = wm.highlight_features(scene)
                self.assertTrue(features)
                iso = (scene.get("city_country_iso2") or scene.get("country_iso2")
                       or ("IT" if scene["kind"] == "italy_admin" else None))
                lon, lat = wm.city_point(scene["city"], iso)
                self.assertTrue(-180 <= lon <= 180 and -90 <= lat <= 90)


class MainTerritoryTests(unittest.TestCase):
    def test_camera_ignores_overseas_departments(self) -> None:
        lon_min, lon_max, lat_min, lat_max = wm.main_territory_bounds(
            wm.country_features("FRA"))
        self.assertGreater(lon_min, -10.0)  # French Guiana sits at lon ~-52
        self.assertLess(lon_max, 15.0)
        lon_min, lon_max, lat_min, lat_max = wm.main_territory_bounds(
            wm.country_features("USA"))
        self.assertGreater(lon_min, -130.0)  # Alaska sits west of -130


class WindowTests(unittest.TestCase):
    def test_highlight_fits_and_city_inside(self) -> None:
        for scene in wm.SCENES:
            with self.subTest(scene=scene["slug"]):
                layout, _, _, _ = wm.prepare(scene)
                x0, y0 = layout.win.to_raster(layout.city_lat, layout.city_lon)
                # city raster position equals the marker drawn on canvas
                self.assertAlmostEqual(x0, layout.marker[0], delta=1.0)
                self.assertAlmostEqual(y0, layout.marker[1], delta=1.0)
                self.assertTrue(layout.win.contains(layout.city_lat, layout.city_lon))


class ExporterTests(unittest.TestCase):
    def test_export_plan_matches_basemap_and_contract(self) -> None:
        scene = wm.scene_by_slug("francia")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            png, plan_path = wm.export_renderinggen(scene, out_dir)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["schema_version"], "renderinggen.overlay-plan.v1")
            item = plan["items"][0]
            self.assertEqual((item["kind"], item["template_id"]), ("map", "MAP"))
            m = item["map"]
            self.assertEqual(m["provider"], "local")
            self.assertTrue(m["source_id"] and m["source_license"] and m["attribution"])
            self.assertEqual((m["width"], m["height"]), (wm.W, wm.H))
            self.assertEqual(len(item["asset_refs"]), 1)
            asset = item["asset_refs"][0]
            self.assertEqual(asset["media_type"], "image/png")
            self.assertTrue(asset["url"].startswith("assets/"))
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            self.assertEqual(asset["sha256"], digest)
            pin = m["pins"][0]
            win = wm.Window.centered_on(
                m["center"]["latitude"], m["center"]["longitude"],
                m["zoom"], m["width"], m["height"])
            self.assertTrue(win.contains(pin["latitude"], pin["longitude"]))
            # plate pixels agree with the contract window, not just the JSON
            x, y = win.to_raster(pin["latitude"], pin["longitude"])
            from PIL import Image
            plate = Image.open(png).convert("RGB")
            r, g, b = plate.getpixel((min(wm.W - 1, max(0, int(x))),
                                      min(wm.H - 1, max(0, int(y)))))
            self.assertTrue(math.dist((r, g, b), wm.rm.YELLOW) < 120, (r, g, b))


class FrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scene = wm.scene_by_slug("francia")
        cls.layout, cls.base, cls.fill, cls.line = wm.prepare(cls.scene)

    def test_final_frame_has_yellow_and_red_figure(self) -> None:
        frame = wm.compose_frame(wm.FRAMES - 1, self.scene, self.layout,
                                 self.base, self.fill, self.line)
        self.assertEqual(frame.size, (wm.W, wm.H))
        mx, my = self.layout.marker
        r, g, b = frame.getpixel((int(mx) + 20, int(my) + 20))
        self.assertTrue(r > 200 and g > 150 and b < 120, (r, g, b))
        band = frame.crop((int(wm.rm.FIG_X), int(wm.rm.FIG_Y) - 90,
                           int(wm.rm.FIG_X) + 500, int(wm.rm.FIG_Y) + 25))
        reds = sum(n for n, (r, g, b) in (band.getcolors(1 << 20) or [])
                   if r > 180 and g < 90 and b < 100)
        self.assertGreater(reds, 500)


if __name__ == "__main__":
    unittest.main()
