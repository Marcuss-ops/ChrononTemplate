#!/usr/bin/env python3
"""Offline contract tests for the dependency-light place pipeline."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import geo_places


class GeoPlacesTests(unittest.TestCase):
    def test_place_extraction_and_presets(self):
        cases = {
            "Roma poi il Colosseo e infine Venezia": [
                ("Roma", "dive"), ("Colosseo", "dive"), ("Venezia", "dive")],
            "Lughetto, Campagna Lupia con tilt, Piazza San Marco": [
                ("Lughetto", "dive"), ("Campagna Lupia", "tilt"),
                ("Piazza San Marco", "dive")],
            "Machu Picchu con orbita e poi Giza": [
                ("Machu Picchu", "orbit"), ("Giza", "dive")],
            '"Piazza dei Miracoli" con metric': [
                ("Piazza dei Miracoli", "metric")],
            "Stazione di Santa Lucia con orbita": [
                ("Stazione di Santa Lucia", "orbit")],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                actual = [(place.query, place.preset)
                          for place in geo_places.extract_places(text)]
                self.assertEqual(actual, expected)

    def test_models_keep_expected_defaults_and_labels(self):
        place = geo_places.Place("Roma")
        self.assertEqual(place.short_name, "ROMA")
        self.assertEqual(place.subtitle, "ROMA")
        self.assertFalse(place.ok)
        tour = geo_places.Tour("Roma")
        self.assertEqual(tour.stops, [])
        self.assertIsNone(tour.mp4)

    def test_geocode_cache_is_persistent_and_language_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "nested" / "cache.json"
            with mock.patch.dict(os.environ, {"CHRONON_GEOCODE_CACHE": str(cache)}):
                with mock.patch.object(geo_places.urllib.request, "urlopen") as urlopen:
                    response = mock.MagicMock()
                    response.__enter__.return_value = response
                    response.__exit__.return_value = False
                    geo_places._LAST_GEOCODE_REQUEST = 0.0
                    urlopen.return_value = response
                    with mock.patch.object(geo_places.json, "load", return_value=[{
                        "display_name": "Roma, Lazio, Italia", "lat": "41.9", "lon": "12.5"}]), \
                         mock.patch.object(geo_places.time, "sleep") as sleep:
                        first = geo_places.geocode(geo_places.Place(" Roma  "))
                        second = geo_places.geocode(geo_places.Place("roma"))
                        self.assertTrue(first.ok)
                        self.assertTrue(second.ok)
                        self.assertEqual((second.lat, second.lon), (41.9, 12.5))
                        self.assertEqual(urlopen.call_count, 1)
                        sleep.assert_not_called()
                payload = json.loads(cache.read_text(encoding="utf-8"))
                self.assertEqual(payload["version"], geo_places._GEOCODE_CACHE_VERSION)
                self.assertEqual(len(payload["entries"]), 1)
                self.assertFalse(list(cache.parent.glob("*.tmp")))

    def test_geocode_rate_limits_uncached_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CHRONON_GEOCODE_CACHE": str(Path(tmp) / "cache.json")}):
                with mock.patch.object(geo_places.urllib.request, "urlopen") as urlopen, \
                     mock.patch.object(geo_places.time, "sleep") as sleep, \
                     mock.patch.object(geo_places.time, "monotonic", side_effect=[10.0, 10.1, 10.1, 11.0]):
                    response = mock.MagicMock()
                    response.__enter__.return_value = response
                    response.__exit__.return_value = False
                    urlopen.return_value = response
                    with mock.patch.object(geo_places.json, "load", return_value=[]):
                        geo_places._LAST_GEOCODE_REQUEST = 9.5
                        geo_places.geocode(geo_places.Place("Roma"))
                    sleep.assert_called_once()
                    self.assertAlmostEqual(sleep.call_args.args[0], 0.5, places=6)
                    urlopen.assert_called_once()

    def test_module_does_not_import_image_or_tile_runtime(self):
        forbidden = ("cv2", "numpy", "dynamic_tile_pyramid", "fast_geo_camera")
        self.assertFalse(set(forbidden) & sys.modules.keys())


if __name__ == "__main__":
    unittest.main()
