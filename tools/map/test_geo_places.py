#!/usr/bin/env python3
"""Offline contract tests for the dependency-light place pipeline."""
import sys
import unittest

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

    def test_module_does_not_import_image_or_tile_runtime(self):
        forbidden = ("cv2", "numpy", "dynamic_tile_pyramid", "fast_geo_camera")
        self.assertFalse(set(forbidden) & sys.modules.keys())


if __name__ == "__main__":
    unittest.main()
