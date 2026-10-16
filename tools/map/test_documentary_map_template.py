#!/usr/bin/env python3
"""Offline contract tests for the data-driven documentary map template."""
import copy
import json
import unittest
from pathlib import Path

import documentary_map_template as tpl

SPEC_PATH = Path(__file__).resolve().parent / "specs" / "italy_rome_1_milione.json"


class DocumentaryMapTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC_PATH.read_text())
        cls.plan = tpl.build_plan(cls.spec)
        cls.ids = [layer["id"] for layer in cls.plan["layers"]]

    def test_sample_spec_is_valid(self):
        self.assertEqual(tpl.validate_spec(copy.deepcopy(self.spec))["highlight_country"], "Italy")

    def test_plan_has_required_scene_layers(self):
        for layer_id in ("city-marker", "city-connector", "label-box", "label-text", "editorial-text"):
            self.assertIn(layer_id, self.ids)
        self.assertEqual(self.plan["schema"], "chronon.render-plan.v3")
        self.assertEqual(self.plan["job_id"], self.spec["job_id"])

    def test_country_outline_is_drawn_for_italy(self):
        borders = [i for i in self.ids if i.startswith("country-border-edge-")]
        self.assertGreater(len(borders), 20)

    def test_editorial_and_label_text_come_from_spec(self):
        layers = {layer["id"]: layer for layer in self.plan["layers"]}
        self.assertEqual(layers["editorial-text"]["text"], "1 milione")
        self.assertEqual(layers["label-text"]["text"], "ROMA")

    def test_plan_is_deterministic(self):
        self.assertEqual(json.dumps(self.plan, sort_keys=True),
                         json.dumps(tpl.build_plan(copy.deepcopy(self.spec)), sort_keys=True))

    def test_invalid_specs_fail_closed(self):
        cases = {
            "missing field": lambda s: s.pop("editorial_text"),
            "bad job_id": lambda s: s.__setitem__("job_id", "Bad Id!"),
            "bbox outside extent": lambda s: s.__setitem__("bbox", [-200, 0, 0, 10]),
            "zoom out of range": lambda s: s["camera"].__setitem__("zoom", 99),
            "city outside extent": lambda s: s["city"].__setitem__("lat", 95),
            "empty label": lambda s: s.__setitem__("label", "  "),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                spec = copy.deepcopy(self.spec)
                mutate(spec)
                with self.assertRaises(tpl.SpecError):
                    tpl.validate_spec(spec)

    def test_unknown_country_fails_closed(self):
        spec = copy.deepcopy(self.spec)
        spec["highlight_country"] = "Atlantis"
        with self.assertRaises(tpl.SpecError):
            tpl.build_plan(spec)


if __name__ == "__main__":
    unittest.main()
