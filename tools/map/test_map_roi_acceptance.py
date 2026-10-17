#!/usr/bin/env python3
"""Contract checks for the retired standalone map-label animation catalog."""
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_geo_camera_small_places as renderer


class RetiredMapLabelContract(unittest.TestCase):
    def test_standalone_label_animation_catalog_is_empty(self):
        self.assertEqual(renderer.MAP_LABEL_ANIMATIONS, ())
        self.assertEqual(renderer.MARKER_DRAWN_STYLES, ())

    def test_retired_animation_ids_fail_closed(self):
        import numpy as np
        frame = np.zeros((24, 24, 3), dtype=np.uint8)
        for animation in ("simple_label", "bracket_label", "diffuse_city_beacon",
                          "glow_react", "editorial_serif", "ribbon"):
            with self.subTest(animation=animation):
                with self.assertRaises(ValueError):
                    renderer.draw_map_location_marker(frame, (12, 12), "Garlasco", 0.5,
                                                      animation)
                with self.assertRaises(ValueError):
                    renderer.draw_editorial_map_caption(frame, "Garlasco", 0.5,
                                                        animation=animation)


if __name__ == "__main__":
    unittest.main()
