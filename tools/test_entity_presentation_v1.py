#!/usr/bin/env python3
"""Contract gates for the catalog-driven editorial presentation V1 families."""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1]
CATALOG_PATH = TEMPLATE / "catalog/entity_presentation.v1.json"
BUILDER_PATH = TEMPLATE / "tools/build_entity_presentation_v1.py"
SPEC = importlib.util.spec_from_file_location("entity_presentation_builder", BUILDER_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "metric_v1": {"metric_counter_rise", "metric_counter_scale_settle", "metric_odometer_vertical", "metric_digits_stagger", "metric_bar_grow", "metric_ring_draw", "metric_delta_reveal", "metric_focus_punch", "metric_before_after", "metric_multi_stat_focus"},
    "date_v1": {"date_fade_rise", "date_year_count", "date_calendar_flip", "date_segment_stagger", "date_timeline_tick", "date_range_draw", "date_marker_drop", "date_underline_focus", "date_history_stack", "date_chronology_focus"},
    "entity_card_v1": {"entity_caption_rise", "entity_depth_caption", "entity_yaw_caption", "entity_split_side", "entity_border_then_caption", "entity_glow_focus", "entity_name_underline", "entity_name_pill", "entity_parallax_caption", "entity_focus_frame"},
}


class EntityPresentationCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.families = {family["id"]: family for family in cls.catalog["families"]}

    def test_exact_three_families_ten_unique_presets_and_known_templates(self):
        self.assertEqual(set(self.families), set(EXPECTED))
        seen = set()
        for family_id, family in self.families.items():
            ids = [preset["id"] for preset in family["presets"]]
            self.assertEqual(set(ids), EXPECTED[family_id])
            self.assertEqual(len(ids), 10)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertFalse(seen.intersection(ids))
            seen.update(ids)
            self.assertTrue(family["supported_template"])
            self.assertTrue(family["supported_content"])
            self.assertTrue(family["render_safe"])
            self.assertEqual(family["duration_bounds"], {"minimum_frames": 24, "maximum_frames": 240})

    def test_all_track_keyframes_are_finite_monotonic_and_end_at_rest(self):
        for family in self.families.values():
            for preset in family["presets"]:
                for track in preset["tracks"]:
                    with self.subTest(preset=preset["id"], property=track["property"]):
                        frames = [key["frame"] for key in track["keyframes"]]
                        values = [key["value"] for key in track["keyframes"]]
                        self.assertEqual(frames[0], 0)
                        self.assertEqual(frames, sorted(set(frames)))
                        self.assertGreaterEqual(frames[-1], 48)
                        self.assertTrue(all(isinstance(value, (int, float)) and math.isfinite(value) for value in values))
                        if track["property"] in {"opacity", "scale", "scale_x", "scale_y"}:
                            self.assertEqual(values[-1], 1)
                        if track["property"] in {"position_x", "position_y", "position_z", "rotation_x", "rotation_y"}:
                            self.assertEqual(values[-1], 0)
                        if preset["id"] in {"entity_depth_caption", "entity_yaw_caption", "entity_parallax_caption"} and track["property"] == "position_z":
                            self.assertEqual(values[-1], 0)

    def test_catalog_is_deterministic_and_all_motion_track_sample_frames_exist(self):
        self.assertEqual(json.loads(CATALOG_PATH.read_text()), self.catalog)
        for family in self.families.values():
            for preset in family["presets"]:
                for track in preset["tracks"]:
                    keyframes = track["keyframes"]
                    self.assertEqual(keyframes[0]["frame"], 0)
                    self.assertLessEqual(keyframes[-1]["frame"], 72)
                    midpoint = keyframes[len(keyframes) // 2]
                    self.assertTrue(math.isfinite(float(midpoint["value"])))

    def test_required_metric_and_date_examples_normalize(self):
        for raw in BUILDER.METRIC_SAMPLES:
            value = raw.strip()
            self.assertTrue(value)
            self.assertFalse(any(character in value for character in "\n\r"))
        for raw in BUILDER.DATE_SAMPLES:
            self.assertTrue(raw)
        self.assertIn("$3.4B", BUILDER.METRIC_SAMPLES)
        self.assertIn("1,250,000", BUILDER.METRIC_SAMPLES)
        self.assertIn("Q4 2026", BUILDER.DATE_SAMPLES)
        self.assertIn("42%", BUILDER.METRIC_SAMPLES)
        self.assertIn("42.5", BUILDER.METRIC_SAMPLES)
        self.assertIn("-12", BUILDER.METRIC_SAMPLES)
        self.assertIn("+18.7", BUILDER.METRIC_SAMPLES)
        self.assertIn("€12.5M", BUILDER.METRIC_SAMPLES)
        self.assertIn("30 September 2026", BUILDER.DATE_SAMPLES)
        self.assertIn("2010–2020", BUILDER.DATE_SAMPLES)
        self.assertIn("1999/2000", BUILDER.DATE_SAMPLES)

    def test_golden_plans_are_deterministic_and_cover_all_presets(self):
        first = BUILDER.build_plans()
        second = BUILDER.build_plans()
        self.assertEqual(first, second)
        self.assertEqual(set(first), {"metric_v1_gallery_10", "date_v1_gallery_10", "entity_card_v1_gallery_10x6", "entity_card_v1_two_entities_one_scene"})
        for family_id, gallery_id in (("metric_v1", "metric_v1_gallery_10"), ("date_v1", "date_v1_gallery_10"), ("entity_card_v1", "entity_card_v1_gallery_10x6")):
            plan = first[gallery_id]
            self.assertEqual(plan["canvas"]["width"], 1920)
            self.assertEqual(plan["canvas"]["height"], 1080)
            self.assertEqual(plan["canvas"]["fps_num"], 30)
            ids = EXPECTED[family_id]
            joined = json.dumps(plan, ensure_ascii=False)
            for preset_id in ids:
                self.assertIn(preset_id, joined)
            if family_id == "metric_v1":
                counter = next(layer for layer in plan["layers"] if layer["id"] == "metric_counter_rise-value")
                self.assertEqual(counter["text_counter"]["counter"]["from"], 0)
                self.assertEqual(counter["text_counter"]["counter"]["to"], 0.42)
                self.assertEqual(counter["text_counter"]["counter"]["format"], "percent")
            if family_id == "date_v1":
                range_date = next(layer for layer in plan["layers"] if layer["id"] == "date_range_draw-date")
                self.assertEqual(range_date["text_counter"]["counter"]["from"], 2010)
                self.assertEqual(range_date["text_counter"]["counter"]["to"], 2020)
                range_path = next(layer for layer in plan["layers"] if layer["id"] == "date_range_draw-trim")
                trim = range_path["shape"]["operators"][0]["params"]
                self.assertEqual(trim["start"], 0)
                self.assertEqual(trim["end"], 1)
                self.assertEqual(trim["animation"]["keyframes"][0]["value"], [0, 0, 0])
                self.assertEqual(trim["animation"]["keyframes"][-1]["value"], [0, 1, 0])
        entity_plan = first["entity_card_v1_gallery_10x6"]
        captions = [layer for layer in entity_plan["layers"] if layer["type"] == "text" and "-name-" in layer["id"]]
        self.assertEqual(len(captions), 60)
        caption_values = {layer["text"] for layer in captions}
        self.assertTrue(set(BUILDER.ENTITY_SAMPLES).issubset(caption_values))
        for layer in captions:
            width, height = layer["size"]
            x, y = layer["position"]
            self.assertGreaterEqual(x - width / 2, 0)
            self.assertLessEqual(x + width / 2, 1920)
            self.assertGreaterEqual(y - height / 2, 0)
            self.assertLessEqual(y + height / 2, 1080)

    def test_entity_family_presets_keep_shared_image_caption_lifetimes(self):
        plan = BUILDER.build_entity_gallery(self.families["entity_card_v1"])
        images = {layer["id"].replace("-portrait-", "-name-"): layer for layer in plan["layers"] if layer["type"] == "image"}
        captions = [layer for layer in plan["layers"] if layer["type"] == "text" and "-name-" in layer["id"]]
        self.assertEqual(len(captions), 60)
        for caption in captions:
            image = images[caption["id"]]
            self.assertEqual(image["start_frame"], caption["start_frame"])
            self.assertEqual(image["duration_frames"], caption["duration_frames"])

    def test_two_entities_share_one_scene_and_captions_remain(self):
        plan = BUILDER.build_two_entity_canary()
        images = [layer for layer in plan["layers"] if layer["type"] == "image"]
        captions = [layer for layer in plan["layers"] if layer["type"] == "text" and "caption" in layer["id"]]
        self.assertEqual(len(images), 2)
        self.assertEqual(len(captions), 2)
        self.assertEqual({layer["start_frame"] for layer in images + captions}, {0})
        self.assertEqual({layer["duration_frames"] for layer in images + captions}, {plan["canvas"]["duration_frames"]})
        self.assertEqual({layer["text"] for layer in captions}, {"PERSON A", "PERSON B"})
        self.assertLess(images[0]["position"][0], images[1]["position"][0])
        self.assertLess(images[0]["position"][0] + images[0]["size"][0] / 2,
                        images[1]["position"][0] - images[1]["size"][0] / 2)

    def test_entity_identity_and_image_path_are_preserved_in_gallery(self):
        plan = BUILDER.build_entity_gallery(self.families["entity_card_v1"])
        texts = [layer["text"] for layer in plan["layers"] if layer["type"] == "text"]
        images = [layer["asset"] for layer in plan["layers"] if layer["type"] == "image"]
        for name in BUILDER.ENTITY_SAMPLES:
            self.assertIn(name, texts)
        self.assertTrue(images)
        self.assertEqual(set(images), {BUILDER.CANARY_IMAGE})
        for layer in (layer for layer in plan["layers"] if layer["type"] == "image"):
            image_w, image_h = layer["size"]
            self.assertEqual(layer["radius"], 24)
            frame = layer["style"]["background"]
            self.assertEqual(frame["padding"], [4, 4])
            self.assertEqual(frame["radius"], layer["radius"] + 4)
            self.assertLessEqual(frame["radius"], min(image_w + 8, image_h + 8) / 2)

    def test_entity_captions_lay_out_below_and_beside_images(self):
        plan = BUILDER.build_entity_gallery(self.families["entity_card_v1"])
        images = {layer["id"]: layer for layer in plan["layers"] if layer["type"] == "image"}
        captions = [layer for layer in plan["layers"] if layer["type"] == "text" and "-name-" in layer["id"]]
        self.assertEqual(len(captions), 60)
        for caption in captions:
            preset_id, card_index = caption["id"].split("-name-")
            image = images[f"{preset_id}-portrait-{card_index}"]
            cx, cy = caption["position"]
            cw, ch = caption["size"]
            ix, iy = image["position"]
            iw, ih = image["size"]
            caption_box = (cx - cw / 2, cx + cw / 2, cy - ch / 2, cy + ch / 2)
            image_box = (ix - iw / 2, ix + iw / 2, iy - ih / 2, iy + ih / 2)
            overlaps = caption_box[0] < image_box[1] and caption_box[1] > image_box[0] \
                and caption_box[2] < image_box[3] and caption_box[3] > image_box[2]
            self.assertFalse(overlaps, f"{caption['id']} overlaps its image")
            if card_index in {"0", "1", "2", "3"}:
                # Bottom layout: caption.top >= image.bottom + margin, and the
                # caption is centred on the image within an epsilon.
                self.assertGreaterEqual(caption_box[2], image_box[3] + 8, caption["id"])
                self.assertLess(abs((caption_box[0] + caption_box[1]) / 2 - (image_box[0] + image_box[1]) / 2), 1.0, caption["id"])
            else:
                # Side layout: the caption is strictly beside its image.
                beside = caption_box[0] >= image_box[1] or caption_box[1] <= image_box[0]
                self.assertTrue(beside, f"{caption['id']} is not beside its image")

    def test_caption_font_mapping_is_script_aware_and_stable(self):
        plan = BUILDER.build_entity_gallery(self.families["entity_card_v1"])
        fonts = {}
        for layer in plan["layers"]:
            if layer["type"] == "text" and "-name-" in layer["id"]:
                fonts.setdefault(layer["text"], set()).add(layer["style"]["font"])
        for name, used in fonts.items():
            self.assertEqual(len(used), 1, f"{name} maps to {sorted(used)}")
        cjk = fonts["李小龍"].pop()
        arabic = fonts["محمد علي"].pop()
        self.assertIn("CJK", cjk)
        self.assertEqual(arabic, BUILDER.ARABIC_FONT)
        self.assertNotEqual(cjk, arabic)
        self.assertEqual(BUILDER.caption_font("李小龍"), cjk)
        self.assertEqual(BUILDER.caption_font("محمد علي"), arabic)

    def test_arabic_caption_uses_the_bundled_shaping_face(self):
        self.assertEqual(BUILDER.caption_font("محمد علي"), BUILDER.ARABIC_FONT)
        self.assertEqual(BUILDER.caption_font("李小龍"), "assets/fonts/NotoSansCJK-Regular.ttc")

    def test_long_names_shrink_instead_of_overflowing(self):
        plan = BUILDER.build_entity_gallery(self.families["entity_card_v1"])
        long_names = [layer for layer in plan["layers"]
                      if layer["type"] == "text" and layer["text"] == "Alexander Jonathan Montgomery Williams"]
        self.assertTrue(long_names)
        for layer in long_names:
            style = layer["style"]
            self.assertEqual(style["fit_mode"], "shrink_only")
            self.assertLess(style["min_font_size"], style["font_size"])
            self.assertGreaterEqual(layer["size"][0], 240)


if __name__ == "__main__":
    unittest.main()
