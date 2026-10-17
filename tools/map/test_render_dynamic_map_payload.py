"""Offline checks for render_dynamic_map_overlay.py's payload contract.

These cover the renderer's editorial admission rules — per-pin spoken timing,
the fail-closed five-stop map-group budget, and DECLARED composition
fallbacks — without touching cv2, tiles or NVENC.
"""
from __future__ import annotations

import unittest

import render_dynamic_map_overlay as dm


def _pin(index: int, lat: float = 41.0, lon: float = 12.0) -> dict:
    return {"id": f"city:{index}", "label": f"City {index}",
            "latitude": lat + index * 0.01, "longitude": lon + index * 0.01}


class NormalizePinsTests(unittest.TestCase):
    def test_repeated_mentions_fold_into_one_stop(self) -> None:
        pins = dm.normalize_map_pins([_pin(0), _pin(0), _pin(1)])
        self.assertEqual([p["id"] for p in pins], ["city:0", "city:1"])

    def test_five_unique_stops_fit_the_budget(self) -> None:
        pins = dm.normalize_map_pins([_pin(i) for i in range(5)])
        self.assertEqual(len(pins), 5)

    def test_six_stops_fail_closed_and_name_the_lost_places(self) -> None:
        with self.assertRaises(ValueError) as caught:
            dm.normalize_map_pins([_pin(i) for i in range(6)])
        self.assertIn("City 5", str(caught.exception))
        self.assertIn("never drops a grounded place silently", str(caught.exception))


class PinTimingTests(unittest.TestCase):
    def test_absent_timing_is_none(self) -> None:
        self.assertIsNone(dm.parse_pin_timing([_pin(0)], None, 5_000_000))

    def test_schedule_aligns_with_pins(self) -> None:
        pins = [_pin(0), _pin(1)]
        timing = [
            {"id": "city:1", "start_s": 1.5, "duration_s": 1.0},
            {"id": "city:0", "start_s": 0.0, "duration_s": 1.25},
        ]
        got = dm.parse_pin_timing(pins, timing, 5_000_000)
        self.assertEqual(got, [(0.0, 1.25), (1.5, 1.0)])

    def test_missing_or_duplicate_or_overrunning_entries_fail_closed(self) -> None:
        pins = [_pin(0), _pin(1)]
        with self.assertRaises(ValueError):
            dm.parse_pin_timing(pins, [{"id": "city:0", "start_s": 0.0, "duration_s": 1.0}], 5_000_000)
        with self.assertRaises(ValueError):
            dm.parse_pin_timing(pins, [
                {"id": "city:0", "start_s": 0.0, "duration_s": 1.0},
                {"id": "city:0", "start_s": 1.0, "duration_s": 1.0},
                {"id": "city:1", "start_s": 2.0, "duration_s": 1.0},
            ], 5_000_000)
        with self.assertRaises(ValueError):
            dm.parse_pin_timing(pins, [
                {"id": "city:0", "start_s": 0.0, "duration_s": 6.0},
                {"id": "city:1", "start_s": 2.0, "duration_s": 1.0},
            ], 5_000_000)
        with self.assertRaises(ValueError):
            dm.parse_pin_timing(pins, [
                {"id": "city:0", "start_s": -1.0, "duration_s": 1.0},
                {"id": "city:1", "start_s": 2.0, "duration_s": 1.0},
            ], 5_000_000)


class TourTimingTests(unittest.TestCase):
    def test_each_stop_is_held_for_its_spoken_duration(self) -> None:
        schedule = [(0.0, 1.5), (2.0, 0.5)]
        sps, travel, reductions = dm.tour_timing_from_pin_timing(schedule, 24.0)
        self.assertEqual(sps, 1.5)
        self.assertAlmostEqual(travel, 0.5 if 0.5 >= 1.0 else 1.0)  # clamped into [1.0, 2.4]
        self.assertEqual(reductions[0], 0)
        self.assertEqual(reductions[1], int(round((1.5 - 0.5) * 24.0)))

    def test_gaps_average_into_travel_legs(self) -> None:
        schedule = [(0.0, 1.0), (3.0, 1.0), (6.0, 1.0)]
        _, travel, _ = dm.tour_timing_from_pin_timing(schedule, 24.0)
        self.assertAlmostEqual(travel, 2.0)


class DeclaredFallbackTests(unittest.TestCase):
    CERTIFIED = ("region_zoom", "pulse_marker", "spotlight")
    SCENES = ("ed_yemen_markers",)

    def test_explicit_compatible_composition_wins_verbatim(self) -> None:
        got, source = dm.resolve_declared_composition(
            "region_zoom", ["pulse_marker"], 1,
            self.CERTIFIED, (), self.SCENES, ())
        self.assertEqual((got, source), ("region_zoom", "explicit"))

    def test_incompatible_explicit_uses_declared_fallback_and_records_it(self) -> None:
        got, source = dm.resolve_declared_composition(
            "ed_yemen_markers", ["pulse_marker"], 2,
            self.CERTIFIED, (), self.SCENES, ())
        self.assertEqual((got, source), ("pulse_marker", "declared_fallback"))

    def test_incompatible_explicit_without_fallback_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            dm.resolve_declared_composition(
                "ed_yemen_markers", [], 2,
                self.CERTIFIED, (), self.SCENES, ())

    def test_unknown_composition_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            dm.resolve_declared_composition(
                "hyper_map", [], 2, self.CERTIFIED, (), self.SCENES, ())

    def test_empty_request_stays_empty(self) -> None:
        got, source = dm.resolve_declared_composition(
            "", ["pulse_marker"], 2, self.CERTIFIED, (), self.SCENES, ())
        self.assertEqual((got, source), ("", "none"))


if __name__ == "__main__":
    unittest.main()
