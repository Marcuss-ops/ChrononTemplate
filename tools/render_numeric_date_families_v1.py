#!/usr/bin/env python3
"""Render the Metrics, Money, and Dates v1 motion family galleries."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
CATALOG = Path(__file__).resolve().parents[1] / "catalog/entity_motion_families.v1.json"
ASSETS = ROOT / "RenderingGen/renderinggen/out/editorial_v1"
OUT = ROOT / "out/editorial_v1"

DATA = {
    "metric": {
        "entity": "METRIC", "value": "72%", "label": "CUSTOMER RETENTION", "eyebrow": "KEY METRIC",
        "background": [0.018, 0.032, 0.043, 1], "ink": "#F3F7F7",
        "values": ["0%", "24%", "51%", "72%"],
        "accents": ["#6ED6C3", "#71C9F8", "#8B9CFF", "#F4C76B", "#70D6AE", "#8EB7F7", "#77D3C8", "#80C7F0", "#F1C879", "#8BC7A8"],
    },
    "money": {
        "entity": "MONEY", "value": "$12.4M", "label": "ANNUAL REVENUE", "eyebrow": "FINANCIAL SNAPSHOT",
        "background": [0.035, 0.034, 0.028, 1], "ink": "#F6F0E3",
        "values": ["$0", "$4.1M", "$8.6M", "$12.4M"],
        "accents": ["#79D7B0", "#D6C38E", "#77CBA5", "#D9CEB0", "#72CBA6", "#F0CC82", "#78D5AC", "#D8C496", "#A5D6B9", "#79C9A6"],
    },
    "date": {
        "entity": "DATE", "value": "MARCH 2024", "label": "PRODUCT LAUNCH", "eyebrow": "TIMELINE",
        "background": [0.04, 0.036, 0.031, 1], "ink": "#F3EFE7",
        "values": ["1998", "2007", "2016", "2024"],
        "accents": ["#82C9E8", "#A3B9ED", "#7BCABF", "#E1C27D", "#93B9E5", "#84CDBB", "#D2B98D", "#8BC6D5", "#C4B5E8", "#82CDB8"],
    },
}


def tr(prop, keys, easing="out_cubic"):
    normalized = dict(keys)
    return {"property": prop, "keyframes": [{"frame": f, "value": normalized[f]} for f in sorted(normalized)], "easing": easing}


def rgba(hex_color):
    raw = hex_color.lstrip("#")
    return [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1]


def text_layer(id_, text, size, position, start, duration, style, tracks, enable_3d=False):
    # Text positions are canvas coordinates; author the family in center-relative coordinates.
    canvas_position = [640 + position[0], 360 + position[1]]
    return {"id": id_, "type": "text", "text": text, "size": size, "position": canvas_position,
            "start_frame": start, "duration_frames": duration, "style": style,
            "animation": {"tracks": tracks}, **({"enable_3d": True} if enable_3d else {})}


def rect_layer(id_, size, position, start, duration, color, tracks=None):
    layer = {"id": id_, "type": "color", "color": color, "size": size, "position": position,
             "start_frame": start, "duration_frames": duration}
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def draw_stroke(id_, length, thickness, position, start, duration, color, rotation=0):
    tracks = [tr("scale", [(0, .015), (22, 1), (39, 1), (47, .015)])]
    if rotation:
        tracks.append(tr("rotation_z", [(0, rotation), (22, 0), (39, 0), (47, rotation)]))
    return rect_layer(id_, [length, thickness], position, start, duration, color, tracks)


def build_plan(family):
    cfg = DATA[family]
    catalog = json.loads(CATALOG.read_text())
    spec = next(f for f in catalog["families"] if f["entity_type"] == cfg["entity"])
    presets = spec["presets"]
    fps, segment = 24, 48
    total = len(presets) * segment
    layers = [rect_layer("background", [1280, 720], [0, 0], 0, total, cfg["background"])]
    for i, preset in enumerate(presets):
        start, accent = i * segment, cfg["accents"][i]
        # Three separate visual grammars, all set directly on the canvas without a card backdrop.
        value_x = 0 if family == "metric" else (-116 if family == "money" else -88)
        title_x = value_x
        label_x = value_x
        title_style = {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 13,
                       "fill": "#91A5AD" if family == "metric" else ("#B5A77F" if family == "money" else "#B4A99B")}
        label_style = {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 16,
                       "fill": "#A8BAC0" if family == "metric" else ("#BFB7A5" if family == "money" else "#BEB4A6")}
        value_style = {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 68 if family != "date" else 62,
                       "fill": cfg["ink"], "fit_mode": "shrink_only", "min_font_size": 44, "max_font_size": 68}
        title_tracks = [tr("opacity", [(0, 0), (17, 1), (39, 1), (47, 0)])]
        label_tracks = [tr("opacity", [(0, 0), (22, 1), (39, 1), (47, 0)])]
        value_tracks = [tr("opacity", [(0, 0), (15, 1), (39, 1), (47, 0)])]
        if preset in ("metric_counter_punch", "money_odometer_lux"):
            value_tracks += [tr("scale", [(0, .93), (19, 1.025), (27, 1), (39, 1), (47, .98)])]
        elif preset in ("metric_vertical_flip_count", "date_flip_calendar"):
            value_tracks += [tr("rotation_x", [(0, -76), (18, 0), (39, 0), (47, -76)])]
        elif preset in ("metric_split_digits", "date_stagger_segments"):
            value_tracks += [tr("position_y", [(0, 28), (20, 0), (39, 0), (47, 14)])]
        elif preset in ("metric_stat_card_reveal", "money_card_depth", "date_card_slide"):
            value_tracks += [tr("position_z", [(0, 110), (22, 0), (39, 0), (47, 70)])]
        elif preset in ("metric_delta_highlight", "money_delta_badge"):
            value_tracks += [tr("position_x", [(0, -48), (21, 0), (39, 0), (47, -24)])]
        elif preset in ("money_compare_before_after",):
            value_tracks += [tr("position_x", [(0, -32), (17, 0), (39, 0), (47, 22)])]
        elif preset in ("date_timeline_pop", "date_marker_drop"):
            value_tracks += [tr("position_y", [(0, -36 if preset.endswith("drop") else 16), (21, 0), (39, 0), (47, 20)])]
        elif preset in ("date_range_draw", "date_underline_focus", "metric_bar_support", "money_growth_bar", "money_ledger_reveal"):
            value_tracks += [tr("position_y", [(0, 12), (20, 0), (39, 0), (47, 8)])]
        elif preset in ("money_spotlight_focus",):
            value_tracks += [tr("scale", [(0, .97), (24, 1), (39, 1), (47, .98)])]
        elif preset in ("metric_focus_swap", "metric_ring_support", "metric_card_stack_sequence", "money_stat_grid",
                        "money_compact_ticker", "date_year_counter", "date_chronology_stack", "date_tick_reveal"):
            value_tracks += [tr("position_y", [(0, 18), (20, 0), (39, 0), (47, 10)])]
        title_y = -105 if family == "metric" else -126
        layers.append(text_layer(f"eyebrow-{i}", cfg["eyebrow"], [500, 32], [title_x, title_y], start, segment, title_style, title_tracks))

        # Count-up/countdown appears as a short, deterministic sequence of intermediate values.
        # The dedicated compare preset intentionally replaces the old amount with the new amount.
        if family == "date" and preset == "date_stagger_segments":
            for j, part in enumerate(("12", "JAN", "2026")):
                pos_x = (-186, 0, 186)[j]
                part_style = dict(value_style)
                part_style["font_size"] = 50 if j == 1 else 60
                part_style["min_font_size"] = part_style["max_font_size"]
                layers.append(text_layer(f"date-part-{i}-{j}", part, [180, 112], [pos_x, -6], start, segment, part_style,
                                         [tr("opacity", [(0, 0), (12 + j * 4, 0), (18 + j * 4, 1), (39, 1), (47, 0)]),
                                          tr("position_y", [(0, 18), (19 + j * 4, 0), (39, 0), (47, 12)])]))
        elif preset != "date_stagger_segments" and preset in ("metric_counter_rise", "metric_counter_punch", "metric_split_digits", "metric_vertical_flip_count",
                      "money_currency_counter", "money_odometer_lux", "money_compare_before_after", "date_year_counter"):
            values = cfg["values"] if family != "date" else ["1998", "2007", "2016", "2024"]
            for j, shown in enumerate(values):
                lo, hi = j * 6, (j + 1) * 6
                # Each intermediate value yields to the next; the final value owns the hold pose.
                opacity = [(0, 0), (lo, 0), (lo + 2, 1), (hi, 0), (47, 0)]
                if j == len(values) - 1:
                    opacity = [(0, 0), (lo, 0), (lo + 2, 1), (39, 1), (47, 0)]
                motion_tracks = [track for track in value_tracks if track["property"] != "opacity"]
                layers.append(text_layer(f"value-{i}-{j}", shown, [700, 112], [value_x, -6], start, segment, value_style,
                                         [tr("opacity", opacity)] + motion_tracks,
                                         enable_3d=preset in ("metric_vertical_flip_count", "date_flip_calendar", "metric_stat_card_reveal", "money_card_depth", "date_card_slide")))
        elif preset != "date_stagger_segments":
            displayed = "2010 — 2024" if family == "date" and preset == "date_range_draw" else cfg["value"]
            layers.append(text_layer(f"value-{i}", displayed, [700, 112], [value_x, -6], start, segment, value_style, value_tracks,
                                     enable_3d=preset in ("metric_vertical_flip_count", "date_flip_calendar", "metric_stat_card_reveal", "money_card_depth", "date_card_slide")))
        layers.append(text_layer(f"label-{i}", cfg["label"], [620, 38], [label_x, 82], start, segment, label_style, label_tracks))

        # Category-specific ink: data ticks, financial ledger marks, and date chronology.
        accent_rgba = rgba(accent)
        muted_rule = [0.30, 0.35, 0.37, 1] if family == "metric" else ([0.38, 0.34, 0.25, 1] if family == "money" else [0.38, 0.34, 0.29, 1])
        if family == "metric":
            if preset in ("metric_counter_rise", "metric_counter_punch", "metric_split_digits"):
                layers.append(draw_stroke(f"metric-underline-{i}", 190 if preset != "metric_split_digits" else 250, 2,
                                          [0, 63], start, segment, accent_rgba))
            elif preset == "metric_vertical_flip_count":
                layers.append(draw_stroke(f"metric-ruler-{i}", 2, 86, [-188, -3], start, segment, accent_rgba))
                for j in range(4):
                    layers.append(rect_layer(f"metric-tick-{i}-{j}", [12 if j == 3 else 7, 2], [-178, -42 + j * 26],
                                             start, segment, muted_rule))
            elif preset == "metric_stat_card_reveal":
                for dx, dy, sx, sy in ((-232, -58, 42, 2), (-232, -58, 2, 28), (232, 58, 42, 2), (232, 58, 2, 28)):
                    layers.append(draw_stroke(f"metric-open-frame-{i}-{len(layers)}", sx, sy, [dx, dy], start, segment, accent_rgba))
            elif preset == "metric_delta_highlight":
                layers.append(draw_stroke(f"metric-delta-leader-{i}", 72, 2, [168, -8], start, segment, accent_rgba, -18))
                layers.append(text_layer(f"metric-delta-{i}", "+8.2%", [120, 34], [244, -28], start + 8, segment - 8,
                                         {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 19, "fill": accent},
                                         [tr("opacity", [(0, 0), (12, 1), (31, 1), (39, 0)])]))
            elif preset == "metric_bar_support":
                layers.append(draw_stroke(f"metric-progress-{i}", 300, 3, [0, 75], start, segment, muted_rule))
                layers.append(rect_layer(f"metric-progress-fill-{i}", [216, 3], [-42, 75], start, segment, accent_rgba,
                                         [tr("scale", [(0, .01), (29, 1), (39, 1), (47, .01)])]))
            elif preset == "metric_ring_support":
                layers.append(text_layer(f"metric-ring-{i}", "◌", [72, 72], [244, -5], start + 6, segment - 6,
                                         {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 48, "fill": accent},
                                         [tr("rotation_z", [(0, -26), (24, 0), (39, 0), (41, -26)]),
                                          tr("opacity", [(0, 0), (13, 1), (33, 1), (39, 0)])]))
            elif preset == "metric_focus_swap":
                for j, (stat, pos_x) in enumerate((("42%", -186), ("72%", 0), ("18%", 186))):
                    layers.append(text_layer(f"metric-focus-{i}-{j}", stat, [120, 32], [pos_x, 152], start + 7, segment - 7,
                                             {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 17,
                                              "fill": accent if j == 1 else "#788A8F"},
                                             [tr("opacity", [(0, 0), (9 + j * 3, 1), (31, 1), (39, 0)])]))
                    if j == 1:
                        layers.append(draw_stroke(f"metric-focus-rule-{i}", 72, 2, [0, 171], start, segment, accent_rgba))
            elif preset == "metric_card_stack_sequence":
                for j, (val, name) in enumerate((("4.8M", "ACTIVE USERS"), ("72%", "RETENTION"), ("+8.2%", "GROWTH"))):
                    y = 139 + j * 34
                    layers.append(text_layer(f"metric-stack-{i}-{j}", f"{val}   {name}", [360, 28], [0, y], start + 3, segment - 3,
                                             {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 14,
                                              "fill": accent if j == 0 else "#91A5AD"},
                                             [tr("opacity", [(0, 0), (7 + j * 4, 1), (31, 1), (39, 0)])]))
                    if j < 2:
                        layers.append(draw_stroke(f"metric-stack-rule-{i}-{j}", 340, 1, [0, y + 16], start, segment, muted_rule))
        elif family == "money":
            if preset in ("money_currency_counter", "money_odometer_lux"):
                layers.append(text_layer(f"money-currency-{i}", "USD  /  FY24", [230, 26], [value_x - 4, -63], start + 4, segment - 4,
                                         title_style, [tr("opacity", [(0, 0), (13, 1), (35, 1), (42, 0)])]))
                layers.append(draw_stroke(f"money-rule-{i}", 270, 2, [value_x, 63], start, segment, accent_rgba))
            elif preset == "money_delta_badge":
                layers.append(text_layer(f"money-delta-{i}", "+8.2%  ↗", [160, 34], [value_x + 210, -2], start + 7, segment - 7,
                                         {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 16, "fill": accent},
                                         [tr("opacity", [(0, 0), (12, 1), (31, 1), (39, 0)])]))
                layers.append(draw_stroke(f"money-delta-rule-{i}", 100, 2, [value_x + 210, 21], start, segment, accent_rgba))
            elif preset == "money_ledger_reveal":
                for j, width in enumerate((390, 250, 390)):
                    layers.append(draw_stroke(f"money-ledger-{i}-{j}", width, 1 if j != 1 else 2,
                                              [value_x, -88 + j * 166], start, segment, muted_rule if j != 1 else accent_rgba))
                layers.append(text_layer(f"money-ledger-date-{i}", "REVENUE     ·     FY2024", [390, 24], [value_x, 104], start + 10, segment - 10,
                                         title_style, [tr("opacity", [(0, 0), (15, 1), (33, 1), (39, 0)])]))
            elif preset == "money_card_depth":
                for j, (dx, dy, w, h) in enumerate(((-225, -55, 48, 2), (-225, -55, 2, 30), (225, 55, 48, 2), (225, 55, 2, 30))):
                    layers.append(draw_stroke(f"money-corner-{i}-{j}", w, h, [value_x + dx, dy], start, segment, accent_rgba))
            elif preset == "money_compare_before_after":
                small = {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 15, "fill": "#A89F8A"}
                layers.append(text_layer(f"money-before-{i}", "$9.8M  ·  BEFORE", [250, 32], [value_x - 145, 92], start + 4, segment - 4,
                                         small, [tr("opacity", [(0, 0), (8, 1), (15, 1), (22, 0)])]))
                layers.append(text_layer(f"money-after-{i}", "$12.4M  ·  AFTER", [250, 32], [value_x + 150, 92], start + 15, segment - 15,
                                         {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 15, "fill": accent},
                                         [tr("opacity", [(0, 0), (8, 1), (30, 1), (38, 0)])]))
                layers.append(draw_stroke(f"money-compare-arrow-{i}", 100, 2, [value_x, 92], start + 8, segment - 8, accent_rgba))
            elif preset == "money_growth_bar":
                layers.append(draw_stroke(f"money-growth-baseline-{i}", 300, 2, [value_x, 77], start, segment, muted_rule))
                layers.append(rect_layer(f"money-growth-fill-{i}", [228, 3], [value_x - 36, 77], start, segment, accent_rgba,
                                         [tr("scale", [(0, .01), (27, 1), (39, 1), (47, .01)])]))
            elif preset == "money_compact_ticker":
                layers.append(text_layer(f"money-ticker-{i}", "USD     •     +8.2%     ↑     MARKET CLOSE", [520, 30], [value_x, 88], start + 4, segment - 4,
                                         {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 13, "fill": accent},
                                         [tr("position_x", [(0, 46), (18, 0), (39, 0), (47, 20)])]))
                layers.append(draw_stroke(f"money-ticker-rule-{i}", 540, 1, [value_x, 112], start, segment, muted_rule))
            elif preset == "money_spotlight_focus":
                layers.append(draw_stroke(f"money-brush-{i}", 310, 7, [value_x, 56], start, segment, accent_rgba, -1.5))
                layers.append(text_layer(f"money-hero-label-{i}", "REVENUE  ·  +8.2%", [260, 26], [value_x, 105], start + 8, segment - 8,
                                         title_style, [tr("opacity", [(0, 0), (12, 1), (31, 1), (39, 0)])]))
            elif preset == "money_stat_grid":
                items = (("4.8M", "ARR", -210), ("$12.4M", "REVENUE", 0), ("+8.2%", "GROWTH", 210))
                for j, (val, name, pos_x) in enumerate(items):
                    layers.append(text_layer(f"money-grid-value-{i}-{j}", val, [180, 34], [value_x + pos_x, 133], start + 5, segment - 5,
                                             {"font": "assets/fonts/Poppins-Bold.ttf", "font_size": 19,
                                              "fill": accent if j == 1 else cfg["ink"]},
                                             [tr("opacity", [(0, 0), (8 + j * 4, 1), (31, 1), (39, 0)])]))
                    layers.append(text_layer(f"money-grid-label-{i}-{j}", name, [180, 22], [value_x + pos_x, 160], start + 5, segment - 5,
                                             {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 10, "fill": title_style["fill"]},
                                             [tr("opacity", [(0, 0), (11 + j * 4, 1), (31, 1), (39, 0)])]))
                    if j < 2:
                        layers.append(draw_stroke(f"money-grid-divider-{i}-{j}", 38, 1, [value_x + pos_x + 105, 147], start, segment, muted_rule, 90))
        else:
            if preset in ("date_tick_reveal", "date_flip_calendar", "date_card_slide"):
                layers.append(draw_stroke(f"date-index-tick-{i}", 2, 46 if preset != "date_card_slide" else 74,
                                          [-235, -6], start, segment, accent_rgba))
            if preset in ("date_timeline_pop", "date_range_draw", "date_marker_drop", "date_chronology_stack"):
                layers.append(draw_stroke(f"date-timeline-{i}", 500, 2, [0, 133], start, segment, muted_rule))
                mark_x = -220 if preset == "date_marker_drop" else (0 if preset != "date_range_draw" else 220)
                layers.append(rect_layer(f"date-marker-{i}", [8, 8], [mark_x, 133], start, segment, accent_rgba,
                                         [tr("scale", [(0, .1), (18, 1), (39, 1), (47, .1)])]))
                if preset == "date_range_draw":
                    layers.append(text_layer(f"date-range-start-{i}", "2010", [120, 28], [-220, 160], start + 3, segment - 3,
                                             {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 15, "fill": "#BEB4A6"},
                                             [tr("opacity", [(0, 0), (10, 1), (31, 1), (39, 0)])]))
                    layers.append(text_layer(f"date-range-end-{i}", "2024", [120, 28], [220, 160], start + 13, segment - 13,
                                             {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 15, "fill": accent},
                                             [tr("opacity", [(0, 0), (10, 1), (31, 1), (39, 0)])]))
                if preset == "date_chronology_stack":
                    for j, (year, event) in enumerate((("2018", "FOUNDATION"), ("2021", "EXPANSION"), ("2024", "LAUNCH"))):
                        y = 153 + j * 31
                        layers.append(text_layer(f"chronology-{i}-{j}", f"{year}     {event}", [300, 26], [0, y], start + 4, segment - 4,
                                                 {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 13,
                                                  "fill": accent if j == 2 else "#BEB4A6"},
                                                 [tr("opacity", [(0, 0), (7 + j * 4, 1), (30, 1), (38, 0)])]))
                        if j < 2:
                            layers.append(draw_stroke(f"chronology-rule-{i}-{j}", 250, 1, [0, y + 14], start, segment, muted_rule))
            if preset == "date_range_draw":
                layers.append(draw_stroke(f"date-range-draw-{i}", 420, 2, [0, 133], start, segment, accent_rgba))
            elif preset == "date_year_counter":
                for j in range(7):
                    layers.append(rect_layer(f"date-year-tick-{i}-{j}", [2, 14 if j in (0, 6) else 7], [-150 + j * 50, 68],
                                             start, segment, accent_rgba if j in (0, 6) else muted_rule))
            elif preset == "date_stagger_segments":
                for j, part in enumerate(("DAY", "MONTH", "YEAR")):
                    layers.append(text_layer(f"date-part-label-{i}-{j}", part, [150, 22], [(-186, 0, 186)[j], 55], start + 2, segment - 2,
                                             {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 10, "fill": accent},
                                             [tr("opacity", [(0, 0), (8 + j * 4, 1), (31, 1), (39, 0)])]))
                    if j < 2:
                        layers.append(draw_stroke(f"date-part-divider-{i}-{j}", 24, 1, [(-93, 93)[j], -5], start, segment, muted_rule, 90))
            elif preset == "date_underline_focus":
                layers.append(draw_stroke(f"date-brush-{i}", 290, 7, [-88, 53], start, segment, accent_rgba, -1.2))
            elif preset == "date_marker_drop":
                layers.append(draw_stroke(f"date-marker-tail-{i}", 44, 2, [-220, 99], start, segment, accent_rgba, 90))
        layers.append(text_layer(f"preset-{i}", preset, [800, 28], [0, 255], start + 10, segment - 10,
                                 {"font": "assets/fonts/DejaVuSans.ttf", "font_size": 13, "fill": "#8494A6"},
                                 [tr("opacity", [(0, 0), (8, 1), (28, 1), (37, 0)])]))

    job_id = f"{family}_family_v1_gallery"
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job_id,
            "canvas": {"width": 1280, "height": 720, "fps_num": fps, "fps_den": 1, "duration_frames": total},
            "layers": layers, "output": {"path": f"{job_id}.mp4", "format": "mp4", "codec": "h264"}}
    plan_dir, render_dir = OUT / "plans", OUT / "renders"
    plan_dir.mkdir(parents=True, exist_ok=True); render_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"{job_id}.plan.json"
    output = render_dir / f"{job_id}.mp4"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    subprocess.run([str(CLI), "render-plan", "--input", str(plan_path), "--assets-root", str(ASSETS),
                    "--output", str(output), "--backend", "software", "--encode-preset", "veryfast",
                    "--trace", str(render_dir / f"{job_id}.pftrace")], check=True, cwd=ROOT)
    print(output)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in DATA:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} metric|money|date")
    build_plan(sys.argv[1])
