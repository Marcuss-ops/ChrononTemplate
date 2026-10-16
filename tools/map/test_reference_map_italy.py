"""Offline checks for reference_map_italy.py (no ffmpeg needed)."""
from __future__ import annotations

import unittest

import reference_map_italy as rm


class SceneTableTests(unittest.TestCase):
    def test_at_least_fifteen_unique_scenes(self) -> None:
        slugs = [s["slug"] for s in rm.SCENES]
        self.assertGreaterEqual(len(slugs), 15)
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_every_scene_resolves_area_and_city(self) -> None:
        for scene in rm.SCENES:
            with self.subTest(scene=scene["slug"]):
                features = rm.highlight_features(scene)
                self.assertTrue(features)
                lon, lat = rm.city_point(scene["city"])
                self.assertTrue(6.0 < lon < 19.0 and 36.0 < lat < 47.5)

    def test_scene_text_is_varied(self) -> None:
        figures = {s["figure"] for s in rm.SCENES}
        self.assertGreater(len(figures), 10)
        self.assertTrue(any(s["figure"] != "1 milione" for s in rm.SCENES))


class ProjectionTests(unittest.TestCase):
    def test_north_is_up(self) -> None:
        cam = rm.fit_camera(6.6, 18.5, 36.6, 47.1)
        _, y_north = cam.project(12.5, 46.0)
        _, y_south = cam.project(12.5, 38.0)
        self.assertLess(y_north, y_south)

    def test_bbox_is_centred_on_canvas(self) -> None:
        # Centring happens in Mercator space, so compare the two bbox corners.
        cam = rm.fit_camera(8.0, 10.0, 44.0, 46.0)
        x0, y0 = cam.project(8.0, 44.0)
        x1, y1 = cam.project(10.0, 46.0)
        self.assertAlmostEqual((x0 + x1) / 2, rm.W / 2, delta=0.5)
        self.assertAlmostEqual((y0 + y1) / 2, rm.H / 2, delta=0.5)


class TimelineTests(unittest.TestCase):
    def test_ramp_is_clamped_and_monotonic(self) -> None:
        values = [rm._ramp(f, 30, 50) for f in range(0, 80)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values[-1], 1.0)
        self.assertEqual(values, sorted(values))


class FrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scene = rm.scene_by_slug("lombardia")
        cls.layout, cls.base, cls.fill, cls.line = rm.prepare(cls.scene)

    def _frame(self, frame: int):
        return rm.compose_frame(frame, self.scene, self.layout, self.base, self.fill, self.line)

    def test_final_frame_has_yellow_area_at_marker(self) -> None:
        frame = self._frame(rm.FRAMES - 1)
        self.assertEqual(frame.size, (rm.W, rm.H))
        # The marker sits inside the highlighted area, so the pixel next to it is yellow.
        mx, my = self.layout.marker
        r, g, b = frame.getpixel((int(mx) + 20, int(my) + 20))
        self.assertTrue(r > 200 and g > 150 and b < 120, (r, g, b))

    def test_red_figure_appears_in_fixed_band(self) -> None:
        frame = self._frame(rm.FRAMES - 1)
        band = frame.crop((int(rm.FIG_X), int(rm.FIG_Y) - 90, int(rm.FIG_X) + 500, int(rm.FIG_Y) + 25))
        reds = sum(n for n, (r, g, b) in (band.getcolors(1 << 20) or [])
                   if r > 180 and g < 90 and b < 100)
        self.assertGreater(reds, 500)

    def test_figure_hidden_before_reveal(self) -> None:
        frame = self._frame(50)
        band = frame.crop((int(rm.FIG_X), int(rm.FIG_Y) - 90, int(rm.FIG_X) + 500, int(rm.FIG_Y) + 25))
        reds = sum(n for n, (r, g, b) in (band.getcolors(1 << 20) or [])
                   if r > 180 and g < 90 and b < 100)
        self.assertEqual(reds, 0)


if __name__ == "__main__":
    unittest.main()
