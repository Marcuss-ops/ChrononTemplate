#!/usr/bin/env python3
"""Offline contract tests for the dependency-light place pipeline."""
import json
import os
import subprocess
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

    def test_catalog_resolves_localized_city_and_never_calls_network(self):
        with mock.patch.object(geo_places.urllib.request, "urlopen",
                               side_effect=AssertionError("offline catalog should resolve Roma")):
            place = geo_places.geocode(geo_places.Place("Roma"), offline_only=True)
        self.assertTrue(place.ok)
        self.assertEqual(place.display_name, "Rome, Lazio, IT")
        self.assertEqual((place.lat, place.lon), (41.89193, 12.51133))

    def test_catalog_resolves_adm1_region_and_country_capital(self):
        with mock.patch.object(geo_places.urllib.request, "urlopen",
                               side_effect=AssertionError("offline catalog must not call network")):
            region = geo_places.geocode(geo_places.Place("California"), offline_only=True)
            country = geo_places.geocode(geo_places.Place("Italy"), offline_only=True)
        self.assertTrue(region.ok)
        self.assertEqual(region.display_name, "California, US")
        self.assertGreater(region.lat, 32.0)
        self.assertLess(region.lat, 43.0)
        self.assertGreater(region.lon, -125.0)
        self.assertLess(region.lon, -113.0)
        self.assertTrue(country.ok)
        self.assertEqual(country.display_name, "Italy (Rome)")
        self.assertEqual((country.lat, country.lon), (41.89193, 12.51133))

    def test_catalog_ambiguous_region_requires_remote_or_offline_failure(self):
        with mock.patch.object(geo_places.urllib.request, "urlopen",
                               side_effect=AssertionError("offline ambiguity must not call network")):
            unresolved = geo_places.geocode(geo_places.Place("Georgia"), offline_only=True)
        self.assertFalse(unresolved.ok)

    def test_ambiguous_country_region_never_calls_online_geocoder(self):
        with mock.patch.object(geo_places.urllib.request, "urlopen",
                               side_effect=AssertionError("ambiguous geography must never call network")) as urlopen:
            unresolved = geo_places.geocode(geo_places.Place("Georgia"))
        self.assertFalse(unresolved.ok)
        urlopen.assert_not_called()

    def test_unique_city_name_collision_is_not_resolved_offline(self):
        with mock.patch.object(geo_places.urllib.request, "urlopen",
                               side_effect=AssertionError("ambiguous city must not call network")):
            unresolved = geo_places.geocode(geo_places.Place("Rome"), offline_only=True)
        self.assertFalse(unresolved.ok)

    def test_geocode_cache_is_persistent_and_language_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "nested" / "cache.json"
            with mock.patch.dict(os.environ, {"CHRONON_GEOCODE_CACHE": str(cache)}):
                with mock.patch.object(geo_places, "GeographicCatalog", side_effect=FileNotFoundError), \
                     mock.patch.object(geo_places.urllib.request, "urlopen") as urlopen:
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

    def test_geocode_cache_is_language_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache.json"
            with mock.patch.dict(os.environ, {"CHRONON_GEOCODE_CACHE": str(cache)}), \
                 mock.patch.object(geo_places, "GeographicCatalog", side_effect=FileNotFoundError), \
                 mock.patch.object(geo_places.urllib.request, "urlopen") as urlopen, \
                 mock.patch.object(geo_places.time, "sleep") as sleep, \
                 mock.patch.object(geo_places.time, "monotonic", return_value=10.0), \
                 mock.patch.object(geo_places.json, "load", side_effect=[
                     [{"display_name": "Rome, Lazio, Italy", "lat": "41.9", "lon": "12.5"}],
                     [{"display_name": "Roma, Lazio, Italia", "lat": "41.9", "lon": "12.5"}],
                 ]):
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.__exit__.return_value = False
                urlopen.return_value = response
                geo_places._LAST_GEOCODE_REQUEST = 0.0
                with mock.patch.object(geo_places, "GeographicCatalog",
                                       side_effect=FileNotFoundError):
                    english = geo_places.geocode(geo_places.Place("Roma"), "en")
                    italian = geo_places.geocode(geo_places.Place("Roma"), "it")
                self.assertEqual(english.display_name, "Rome, Lazio, Italy")
                self.assertEqual(italian.display_name, "Roma, Lazio, Italia")
                self.assertEqual(urlopen.call_count, 2)
                self.assertEqual(
                    [call.args[0].full_url.rsplit("accept-language=", 1)[1]
                     for call in urlopen.call_args_list], ["en", "it"])
                sleep.assert_called_once_with(1.0)

    def test_not_found_result_is_persisted_and_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache.json"
            with mock.patch.dict(os.environ, {"CHRONON_GEOCODE_CACHE": str(cache)}), \
                 mock.patch.object(geo_places, "GeographicCatalog", side_effect=FileNotFoundError), \
                 mock.patch.object(geo_places.urllib.request, "urlopen") as urlopen, \
                 mock.patch.object(geo_places.time, "sleep") as sleep, \
                 mock.patch.object(geo_places.time, "monotonic", return_value=10.0), \
                 mock.patch.object(geo_places.json, "load", return_value=[]):
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.__exit__.return_value = False
                urlopen.return_value = response
                geo_places._LAST_GEOCODE_REQUEST = 0.0
                first = geo_places.geocode(geo_places.Place("Atlantis"))
                second = geo_places.geocode(geo_places.Place(" atlantis "))
                self.assertFalse(first.ok)
                self.assertFalse(second.ok)
                self.assertEqual(urlopen.call_count, 1)
                payload = json.loads(cache.read_text(encoding="utf-8"))
                self.assertIsNone(next(iter(payload["entries"].values())))
                sleep.assert_not_called()

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
                    with mock.patch.object(geo_places.json, "load", return_value=[]), \
                         mock.patch.object(geo_places, "GeographicCatalog",
                                           side_effect=FileNotFoundError):
                        geo_places._LAST_GEOCODE_REQUEST = 9.5
                        geo_places.geocode(geo_places.Place("Roma"))
                    sleep.assert_called_once()
                    self.assertAlmostEqual(sleep.call_args.args[0], 0.5, places=6)
                    urlopen.assert_called_once()

    def test_module_does_not_import_image_or_tile_runtime(self):
        code = (
            "import sys; import geo_places; "
            "forbidden = {'cv2', 'numpy', 'dynamic_tile_pyramid', 'fast_geo_camera'}; "
            "assert not (forbidden & sys.modules.keys())"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=Path(__file__).resolve().parent,
            text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
