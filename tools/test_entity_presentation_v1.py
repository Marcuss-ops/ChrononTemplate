#!/usr/bin/env python3
"""Contract gates for the catalog-driven editorial presentation V1 families."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import unittest
from pathlib import Path

def _numeric_values(value):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        yield float(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _numeric_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _numeric_values(item)


TEMPLATE = Path(__file__).resolve().parents[1]
CATALOG_PATH = TEMPLATE / "catalog/entity_presentation.v1.json"
BUILDER_PATH = TEMPLATE / "tools/build_entity_presentation_v1.py"
SPEC = importlib.util.spec_from_file_location("entity_presentation_builder", BUILDER_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "metric_v1": {"metric_counter_rise", "metric_counter_scale_settle", "metric_odometer_vertical", "metric_digits_stagger", "metric_bar_grow", "metric_ring_draw", "metric_delta_reveal", "metric_focus_punch", "metric_before_after", "metric_multi_stat_focus", "metric_count_flip", "metric_slide_left", "metric_ribbon_unfold", "metric_split_odometer", "metric_bounce_settle", "metric_arc_sweep", "metric_digit_cascade", "metric_compare_wipe", "metric_pulse_hold", "metric_debt_flip"},
    "date_v1": {"date_fade_rise", "date_year_count", "date_calendar_flip", "date_segment_stagger", "date_timeline_tick", "date_range_draw", "date_marker_drop", "date_underline_focus", "date_history_stack", "date_chronology_focus", "date_page_turn", "date_calendar_drop", "date_month_wipe", "date_timeline_sweep", "date_marker_pop", "date_split_year", "date_bracket_draw", "date_stamp_reveal", "date_era_zoom", "date_digit_flip"},
    "entity_card_v1": {"entity_caption_rise", "entity_depth_caption", "entity_yaw_caption", "entity_split_side", "entity_border_then_caption", "entity_glow_focus", "entity_name_underline", "entity_name_pill", "entity_parallax_caption", "entity_focus_frame"},
}


class EntityPresentationCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.families = {family["id"]: family for family in cls.catalog["families"]}

    def test_exact_three_families_with_unique_presets_and_known_templates(self):
        self.assertEqual(set(self.families), set(EXPECTED))
        seen = set()
        for family_id, family in self.families.items():
            ids = [preset["id"] for preset in family["presets"]]
            self.assertEqual(set(ids), EXPECTED[family_id])
            self.assertEqual(len(ids), 10 if family_id == "entity_card_v1" else 20)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertFalse(seen.intersection(ids))
            seen.update(ids)
            self.assertTrue(family["supported_template"])
            self.assertTrue(family["supported_content"])
            self.assertTrue(family["render_safe"])
            self.assertEqual(family["duration_bounds"], {"minimum_frames": 24, "maximum_frames": 240})

    def test_metric_and_date_presets_have_distinct_motion_signatures(self):
        for family_id in ("metric_v1", "date_v1"):
            signatures = []
            for preset in self.families[family_id]["presets"]:
                signature = tuple(
                    (track["property"], track["easing"],
                     tuple((key["frame"], key["value"]) for key in track["keyframes"]))
                    for track in preset["tracks"]
                )
                signatures.append(signature)
            self.assertEqual(len(signatures), 20)
            self.assertEqual(len(set(signatures)), 20, f"{family_id} contains duplicate animation definitions")

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
        self.assertIn("1.25M", BUILDER.METRIC_SAMPLES)
        self.assertIn("9.8x", BUILDER.METRIC_SAMPLES)
        self.assertIn("120 km", BUILDER.METRIC_SAMPLES)
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
        self.assertEqual(set(first), {"metric_v1_gallery_20", "metric_v1_canary_five_values", "metric_v1_gallery_4x5", "date_v1_gallery_20", "date_v1_gallery_4x5", "entity_card_v1_gallery_10x6", "entity_card_v1_two_entities_one_scene"})
        for plan in first.values():
            ids = [layer["id"] for layer in plan["layers"]]
            self.assertEqual(len(ids), len(set(ids)), f"{plan['job_id']} contains duplicate layer ids")
        five_value_canary = first["metric_v1_canary_five_values"]
        five_values = [layer for layer in five_value_canary["layers"] if layer.get("text_counter")]
        self.assertEqual(len(five_values), 5)
        self.assertEqual({layer["start_frame"] for layer in five_values}, {0})
        self.assertEqual({layer["duration_frames"] for layer in five_values}, {150})
        self.assertEqual(five_value_canary["canvas"]["duration_frames"], 150)
        counter_values = {layer["id"]: layer["text_counter"]["counter"]["to"] for layer in five_values}
        self.assertEqual(counter_values, {
            "metric_counter_rise-value": 0.42,
            "metric_counter_scale_settle-value": 3.4e9,
            "metric_bar_grow-value": 0.186,
            "metric_delta_reveal-value": 1.2e6,
            "metric_ring_draw-value": 0.72,
        })
        metric_grid = first["metric_v1_gallery_4x5"]
        self.assertEqual(metric_grid["canvas"]["duration_frames"], 150)
        date_grid = first["date_v1_gallery_4x5"]
        self.assertEqual(date_grid["canvas"]["duration_frames"], 150)
        date_tiles = [layer for layer in date_grid["layers"] if layer["id"].endswith("-tile")]
        self.assertEqual(len(date_tiles), 20)
        for preset_id in EXPECTED["date_v1"]:
            self.assertTrue(any(layer["id"].startswith(preset_id + "-") for layer in date_grid["layers"]))
        self.assertEqual({layer["start_frame"] for layer in date_tiles}, {0})
        self.assertEqual({layer["duration_frames"] for layer in date_tiles}, {150})
        for preset_id in EXPECTED["metric_v1"]:
            self.assertTrue(any(layer["id"].startswith(preset_id + "-") for layer in metric_grid["layers"]))
        metric_tiles = [layer for layer in metric_grid["layers"] if layer["id"].endswith("-tile")]
        self.assertEqual(len(metric_tiles), 20)
        grid_counters = {layer["id"].removesuffix("-value"): layer["text_counter"]["counter"]
                         for layer in metric_grid["layers"] if layer.get("text_counter")}
        self.assertEqual(set(grid_counters), set(BUILDER.METRIC_COUNTERS))
        self.assertEqual(grid_counters["metric_delta_reveal"]["to"], 1.2e6)
        self.assertEqual(metric_grid["canvas"]["fps_num"], 30)
        self.assertEqual(metric_grid["canvas"]["duration_frames"] / metric_grid["canvas"]["fps_num"], 5)
        self.assertEqual({layer["start_frame"] for layer in metric_tiles}, {0})
        self.assertEqual({layer["duration_frames"] for layer in metric_tiles}, {150})
        self.assertEqual(first["metric_v1_gallery_20"]["canvas"]["duration_frames"], 3000)
        self.assertEqual(first["date_v1_gallery_20"]["canvas"]["duration_frames"], 3000)
        self.assertEqual(first["entity_card_v1_two_entities_one_scene"]["canvas"]["duration_frames"], 150)
        grid_counters = {layer["id"]: layer["text_counter"]["counter"]
                         for layer in metric_grid["layers"] if layer.get("text_counter")}
        self.assertEqual(set(grid_counters), set(BUILDER.METRIC_COUNTERS[preset_id] and f"{preset_id}-value"
                                                for preset_id in BUILDER.METRIC_COUNTERS))
        self.assertEqual(grid_counters["metric_delta_reveal-value"]["to"], 1.2e6)
        date_text = json.dumps(first["date_v1_gallery_20"], ensure_ascii=False)
        for sample in ("MARCH 2024", "2026", "30 SEPTEMBER 2026", "12 JAN 2026", "Q4 2025", "2010–2020"):
            self.assertIn(sample, date_text)
        five_text = json.dumps(five_value_canary, ensure_ascii=False)
        for sample in ("GROWTH", "REVENUE", "YEAR OVER YEAR", "AUDIENCE", "COMPLETION", "+12.8%"):
            self.assertIn(sample, five_text)
        for plan in first.values():
            for layer in plan["layers"]:
                if "size" in layer and "position" in layer:
                    x, y = BUILDER.canvas_position(layer)
                    width, height = layer["size"]
                    self.assertGreaterEqual(x - width / 2, 0, layer["id"])
                    self.assertLessEqual(x + width / 2, 1920, layer["id"])
                    self.assertGreaterEqual(y - height / 2, 0, layer["id"])
                    self.assertLessEqual(y + height / 2, 1080, layer["id"])
        self.assertTrue(all(math.isfinite(value)
                            for plan in first.values()
                            for value in _numeric_values(plan)))
        entity_gallery = first["entity_card_v1_gallery_10x6"]
        self.assertEqual(entity_gallery["canvas"]["duration_frames"], 1500)
        self.assertEqual(sum(layer["id"].endswith("-preset") for layer in entity_gallery["layers"]), 10)
        duo = first["entity_card_v1_two_entities_one_scene"]
        self.assertEqual(duo["canvas"]["duration_frames"], 150)
        self.assertEqual(len([layer for layer in duo["layers"] if layer["type"] == "image"]), 2)
        self.assertEqual(len([layer for layer in duo["layers"] if layer["type"] == "text" and "caption" in layer["id"]]), 2)
        for family_id, gallery_id in (("metric_v1", "metric_v1_gallery_20"), ("date_v1", "date_v1_gallery_20"), ("entity_card_v1", "entity_card_v1_gallery_10x6")):
            plan = first[gallery_id]
            self.assertEqual(plan["canvas"]["width"], 1920)
            self.assertEqual(plan["canvas"]["height"], 1080)
            self.assertEqual(plan["canvas"]["fps_num"], 30)
            ids = EXPECTED[family_id]
            joined = json.dumps(plan, ensure_ascii=False)
            for preset_id in ids:
                self.assertIn(preset_id, joined)
            if family_id == "metric_v1":
                counters = {layer["id"].removesuffix("-value"): layer["text_counter"]["counter"]
                            for layer in plan["layers"] if layer.get("text_counter")}
                self.assertEqual(set(counters), set(BUILDER.METRIC_COUNTERS))
                for preset_id, counter in counters.items():
                    self.assertEqual(counter["from"], 0, preset_id)
                    self.assertGreater(counter["duration_frames"], 0, preset_id)
                    self.assertTrue(counter["to"] > 0, preset_id)
                self.assertEqual(counters["metric_counter_rise"]["to"], 0.42)
                self.assertEqual(counters["metric_counter_rise"]["format"], "percent")
                for expected in ("$3.4B", "1.25M", "+18.6%", "72%", "1.2M", "9.8x", "120 km"):
                    self.assertIn(expected, json.dumps(plan, ensure_ascii=False))
                self.assertTrue(any(layer["id"] == "metric_bar_grow-secondary"
                                    and layer["text"] == "+18.6%" for layer in plan["layers"]))
                before_after = json.dumps(plan, ensure_ascii=False)
                self.assertIn("$2.1B", before_after)
                self.assertIn("$3.4B", before_after)
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
        for gallery_id in ("metric_v1_gallery_20", "metric_v1_canary_five_values", "metric_v1_gallery_4x5", "date_v1_gallery_20", "date_v1_gallery_4x5", "entity_card_v1_gallery_10x6", "entity_card_v1_two_entities_one_scene"):
            gallery = first[gallery_id]
            background_id = "background" if gallery_id == "entity_card_v1_two_entities_one_scene" or gallery_id in {"metric_v1_canary_five_values", "metric_v1_gallery_4x5", "date_v1_gallery_4x5"} else "gallery-background"
            background = next(layer for layer in gallery["layers"] if layer["id"] == background_id)
            self.assertEqual(BUILDER.canvas_position(background), [960.0, 540.0])
            self.assertEqual(background["position"], [0.0, 0.0])
        entity_plan = first["entity_card_v1_gallery_10x6"]
        portraits = [layer for layer in entity_plan["layers"] if layer["type"] == "image"]
        self.assertTrue(portraits)
        self.assertTrue(all(BUILDER.canvas_position(layer)[0] > 0 for layer in portraits))
        captions = [layer for layer in entity_plan["layers"] if layer["type"] == "text" and "-name-" in layer["id"]]
        self.assertEqual(len(captions), 60)
        caption_values = {layer["text"] for layer in captions}
        self.assertTrue(set(BUILDER.ENTITY_SAMPLES).issubset(caption_values))
        for layer in captions:
            width, height = layer["size"]
            x, y = BUILDER.canvas_position(layer)
            self.assertGreaterEqual(x - width / 2, 0)
            self.assertLessEqual(x + width / 2, 1920)
            self.assertGreaterEqual(y - height / 2, 0)
            self.assertLessEqual(y + height / 2, 1080)

    def test_generated_animation_frames_and_counters_stay_within_global_layer_lifetimes(self):
        for plan in BUILDER.build_plans().values():
            for layer in plan["layers"]:
                start = layer["start_frame"]
                end = start + layer["duration_frames"] - 1
                tracks = layer.get("animation", {}).get("tracks", [])
                for animation_track in tracks:
                    frames = [key["frame"] for key in animation_track["keyframes"]]
                    self.assertEqual(frames, sorted(set(frames)), f"{plan['job_id']}:{layer['id']}")
                    self.assertGreaterEqual(frames[0], start, f"{plan['job_id']}:{layer['id']}")
                    self.assertLessEqual(frames[-1], end, f"{plan['job_id']}:{layer['id']}")
                if layer.get("text_counter"):
                    counter = layer["text_counter"]["counter"]
                    self.assertEqual(counter["start_frame"], start, f"{plan['job_id']}:{layer['id']}")
                    self.assertGreater(counter["duration_frames"], 0)
                    self.assertEqual(counter["duration_frames"], layer["duration_frames"])
                    self.assertLessEqual(counter["start_frame"] + counter["duration_frames"] - 1, end)
                for operator in layer.get("shape", {}).get("operators", []):
                    for key in operator.get("params", {}).get("animation", {}).get("keyframes", []):
                        self.assertGreaterEqual(key["frame"], start, f"{plan['job_id']}:{layer['id']}")
                        self.assertLessEqual(key["frame"], end, f"{plan['job_id']}:{layer['id']}")

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
        self.assertEqual(plan["canvas"]["duration_frames"], 150)
        self.assertEqual({layer["duration_frames"] for layer in images + captions}, {150})
        self.assertEqual(plan["canvas"]["fps_num"], 30)
        self.assertEqual(plan["canvas"]["duration_frames"] / plan["canvas"]["fps_num"], 5)
        self.assertEqual({layer["text"] for layer in captions}, {"PERSON A", "PERSON B"})
        image_centers = [BUILDER.canvas_position(image)[0] for image in images]
        self.assertLess(image_centers[0], image_centers[1])
        self.assertLess(image_centers[0] + images[0]["size"][0] / 2,
                        image_centers[1] - images[1]["size"][0] / 2)

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
            ix, iy = BUILDER.canvas_position(image)
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
        self.assertEqual(cjk, BUILDER.CJK_FONT)
        self.assertEqual(arabic, BUILDER.ARABIC_FONT)
        self.assertNotEqual(cjk, arabic)
        self.assertEqual(BUILDER.caption_font("李小龍"), cjk)
        self.assertEqual(BUILDER.caption_font("محمد علي"), arabic)

    def test_script_faces_exist_in_the_renderer_asset_bundle(self):
        configured_root = os.environ.get("CHRONON_TEMPLATE_RENDERER_ASSETS")
        candidates = [Path(configured_root)] if configured_root else []
        candidates.append(TEMPLATE.parent / "RenderingGen/renderinggen/out/editorial_v1")
        assets_root = next((path for path in candidates if path.is_dir()), None)
        if assets_root is None:
            self.skipTest(
                "optional RenderingGen sibling asset bundle is unavailable; "
                "set CHRONON_TEMPLATE_RENDERER_ASSETS to verify bundled fonts"
            )
        for name in BUILDER.ENTITY_SAMPLES:
            font = assets_root / BUILDER.caption_font(name)
            self.assertTrue(font.is_file(), f"missing bundled font for {name}: {font}")
        self.assertEqual(BUILDER.caption_font("محمد علي"), BUILDER.ARABIC_FONT)
        self.assertEqual(BUILDER.caption_font("李小龍"), BUILDER.CJK_FONT)

    def test_preset_visuals_use_native_renderer_primitives(self):
        plans = BUILDER.build_plans()
        metrics = plans["metric_v1_gallery_20"]["layers"]
        dates = plans["date_v1_gallery_20"]["layers"]
        entities = plans["entity_card_v1_gallery_10x6"]["layers"]
        self.assertTrue(any(layer["id"] == "metric-ring-draw-arc" for layer in metrics))
        self.assertTrue(any(layer["id"] == "date_range_draw-trim" for layer in dates))
        self.assertTrue(any(layer["id"].startswith("date_underline_focus-trim") for layer in dates))
        self.assertEqual(sum(layer["id"].startswith("date_history_stack-event-") for layer in dates), 4)
        self.assertEqual(sum(layer["id"].startswith("date_history_stack-label-") for layer in dates), 4)
        self.assertTrue(any(layer["id"] == "date_marker_drop-dot" for layer in dates))
        self.assertTrue(any(layer.get("effects") for layer in entities if layer["id"] == "entity_glow_focus-portrait-0"))
        self.assertTrue(any(layer["id"].startswith("entity_name_underline-underline-") for layer in entities))
        self.assertTrue(any(layer["id"].startswith("entity_border_then_caption-frame-draw-") for layer in entities))
        self.assertTrue(any(layer.get("style", {}).get("background") for layer in entities
                            if layer["id"] == "entity_name_pill-name-0"))

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
