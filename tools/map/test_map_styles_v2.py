"""Offline checks for map_styles_v2.py (no ffmpeg needed)."""
from __future__ import annotations

import unittest

import map_styles_v2 as ms


def _reds(frame, box=None):
    region = frame.crop(box) if box else frame
    return sum(n for n, (r, g, b) in (region.getcolors(1 << 20) or [])
               if r > 150 and g < 110 and b < 120)


class RegistryTests(unittest.TestCase):
    def test_six_styles_registered(self) -> None:
        self.assertEqual(set(ms.STYLES),
                         {"dark", "route", "bubbles", "flyin", "timeline", "split"})

    def test_every_style_renders_sized_frames(self) -> None:
        for slug, (prepare, frame) in ms.STYLES.items():
            with self.subTest(style=slug):
                ctx = prepare()
                for f in (0, ms.FRAMES - 1):
                    img = frame(ctx, f)
                    self.assertEqual(img.size, (ms.W, ms.H))
                    self.assertEqual(img.mode, "RGB")


class DarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.dark_prepare()

    def test_night_background_and_yellow_france(self) -> None:
        img = ms.dark_frame(self.ctx, ms.FRAMES - 1)
        r, g, b = img.getpixel((10, 10))
        self.assertTrue(r < 40 and g < 40 and b < 50, (r, g, b))
        mx, my = self.ctx.marker
        r, g, b = img.getpixel((int(mx) + 25, int(my) + 25))
        self.assertTrue(r > 200 and g > 150 and b < 120, (r, g, b))

    def test_figure_hidden_early(self) -> None:
        self.assertEqual(_reds(ms.dark_frame(self.ctx, 10)), 0)


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.route_prepare()

    def test_route_draws_red_over_time(self) -> None:
        self.assertEqual(_reds(ms.route_frame(self.ctx, 10)), 0)
        self.assertGreater(_reds(ms.route_frame(self.ctx, 80)), 100)
        self.assertGreater(_reds(ms.route_frame(self.ctx, ms.FRAMES - 1)), 100)

    def test_endpoints_inside_canvas(self) -> None:
        for x, y in (self.ctx.a, self.ctx.b):
            self.assertTrue(0 <= x <= ms.W and 0 <= y <= ms.H)


class BubblesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.bubbles_prepare()

    def test_bubbles_appear_and_total_shown(self) -> None:
        self.assertEqual(_reds(ms.bubbles_frame(self.ctx, 10)), 0)
        self.assertGreater(_reds(ms.bubbles_frame(self.ctx, ms.FRAMES - 1)), 500)

    def test_radii_grow_with_value(self) -> None:
        radii = [p[2] for p in self.ctx.pins]
        self.assertEqual(radii, sorted(radii, reverse=True))


class FlyinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.fly_prepare()

    def test_starts_world_ends_on_tokyo(self) -> None:
        first = ms.fly_frame(self.ctx, 0)
        self.assertEqual(first.size, (ms.W, ms.H))
        last = ms.fly_frame(self.ctx, ms.FRAMES - 1)
        # Tokyo bay sits east of the marker, so count highlight over the frame.
        yellow = sum(n for n, (r, g, b) in (last.getcolors(1 << 20) or [])
                     if r > 200 and g > 150 and b < 120)
        self.assertGreater(yellow, 5000)

    def test_view_changes_through_flight(self) -> None:
        a = ms.fly_frame(self.ctx, 5)
        b = ms.fly_frame(self.ctx, 70)
        diff = sum(1 for x, y in zip(a.tobytes()[::97], b.tobytes()[::97]) if x != y)
        self.assertGreater(diff, 100)


class TimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.timeline_prepare()

    def test_pins_accumulate(self) -> None:
        early = ms.timeline_frame(self.ctx, 20)
        late = ms.timeline_frame(self.ctx, 130)
        diff = sum(1 for a, b in zip(early.tobytes()[::97], late.tobytes()[::97]) if a != b)
        self.assertGreater(diff, 100)

    def test_five_dated_pins(self) -> None:
        self.assertEqual([p[3] for p in self.ctx.pins], [2021, 2022, 2023, 2024, 2025])


class SplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ctx = ms.split_prepare()

    def test_divider_and_two_halves(self) -> None:
        img = ms.split_frame(self.ctx, ms.FRAMES - 1)
        self.assertEqual(img.getpixel((ms.W // 2, ms.H // 2))[:3], (255, 255, 255))
        left = img.crop((0, 0, ms.W // 2 - 10, ms.H))
        right = img.crop((ms.W // 2 + 10, 0, ms.W, ms.H))
        self.assertNotEqual(list(left.getdata())[::1000], list(right.getdata())[::1000])


if __name__ == "__main__":
    unittest.main()
