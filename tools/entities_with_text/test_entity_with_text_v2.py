#!/usr/bin/env python3
"""Contract checks for the renderer-native entity-with-text V2 showcase."""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("build_entity_with_text_v2.py")
SPEC = importlib.util.spec_from_file_location("entity_with_text_v2", SCRIPT)
assert SPEC and SPEC.loader
V2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V2)


class EntityWithTextV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = V2.build_all()

    def test_fifteen_unique_five_second_renderplan_v3_scenes(self):
        self.assertEqual(len(self.plans), 15)
        self.assertEqual(len({plan["job_id"] for plan in self.plans}), 15)
        for plan in self.plans:
            with self.subTest(scene=plan["job_id"]):
                self.assertEqual(plan["schema"], "chronon.render-plan.v3")
                self.assertEqual(plan["canvas"], {"width":1920,"height":1080,"fps_num":30,"fps_den":1,"duration_frames":150})
                layer_ids=[layer["id"] for layer in plan["layers"]]
                self.assertEqual(len(layer_ids),len(set(layer_ids)))

    def test_portrait_and_native_title_are_separate_and_animated(self):
        for plan in self.plans:
            with self.subTest(scene=plan["job_id"]):
                portrait=next(layer for layer in plan["layers"] if layer["id"]=="steve-jobs-portrait")
                title=next(layer for layer in plan["layers"] if layer["id"]=="steve-jobs-title")
                self.assertEqual(portrait["type"],"image")
                self.assertEqual(portrait["asset"],V2.ASSET)
                self.assertEqual(title["type"],"text")
                self.assertEqual(title["text"],"STEVE JOBS")
                self.assertEqual(title["style"]["font"],V2.FONT)
                self.assertEqual(portrait["duration_frames"],150)
                self.assertEqual(title["duration_frames"],150)
                self.assertTrue(portrait["animation"]["tracks"])
                self.assertTrue(title["animation"]["tracks"])
                self.assertFalse(any(layer.get("type")=="image" and "title" in layer.get("id","") for layer in plan["layers"]))

    def test_ten_existing_directions_are_refined_and_five_are_new(self):
        refined=[item for item in V2.RECIPES if not item["source"].startswith("new_")]
        new=[item for item in V2.RECIPES if item["source"].startswith("new_")]
        self.assertEqual(len(refined),10)
        self.assertEqual(len(new),5)
        for item in refined:
            self.assertIn(item["source"],{preset["id"] for preset in V2.BASE.load_families()["entity_card_v1"]["presets"]})
        self.assertEqual({item["id"] for item in new},{
            "entity_v2_monumental_push","entity_v2_archive_filmstrip","entity_v2_dual_depth_lockup",
            "entity_v2_quote_annotation","entity_v2_silhouette_reveal"})

    def test_all_animated_keys_are_finite_and_inside_their_layer_lifetime(self):
        for plan in self.plans:
            for layer in plan["layers"]:
                animation=layer.get("animation",{})
                for track in animation.get("tracks",[]):
                    keys=track["keyframes"]
                    frames=[key["frame"] for key in keys]
                    self.assertEqual(frames,sorted(set(frames)),f"{plan['job_id']}:{layer['id']}")
                    self.assertTrue(all(math.isfinite(float(value)) for key in keys for value in (key["value"] if isinstance(key["value"],list) else [key["value"]])))
                    start=layer["start_frame"]
                    end=start+layer["duration_frames"]
                    self.assertTrue(all(start<=frame<end for frame in frames),f"{plan['job_id']}:{layer['id']}")
                if layer["type"]=="text" and layer["id"]=="steve-jobs-title":
                    self.assertGreater(len({json.dumps(track["keyframes"],sort_keys=True) for track in animation["tracks"]}),0)

    def test_every_referenced_asset_and_font_exists(self):
        self.assertTrue((V2.ROOT/V2.ASSET).is_file())
        self.assertTrue((V2.ROOT/V2.FONT).is_file())
        preview=V2._preview_plan(self.plans[0],V2.ROOT,0.5)
        image=next(layer for layer in preview["layers"] if layer["type"]=="image")
        title=next(layer for layer in preview["layers"] if layer["id"]=="steve-jobs-title")
        self.assertTrue((V2.TEMPLATE/image["asset"]).is_file())
        self.assertTrue((V2.TEMPLATE/title["style"]["font"]).is_file())
        self.assertEqual(preview["canvas"]["width"],960)
        self.assertEqual(preview["canvas"]["height"],540)


if __name__=="__main__":
    unittest.main()
