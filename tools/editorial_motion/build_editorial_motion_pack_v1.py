#!/usr/bin/env python3
"""Generate editorial_motion_pack_v1: five families, five animations each.

Families
  image_backdrop_grid  one image, the same image blurred behind it, a light
                       grid over the whole canvas
  date_motion          four-date editorial sequences
  glow_connections     glowing lines joining the newest short phrases
  camera_phrases       short phrases moved by camera-like 2D transforms
  image_lists          lists with an image beside the list or beside each row

Every preset is an ordinary chronon.render-plan.v3 document. The pack owns
composition and timing only; Chronon3d owns fonts, rasterization and effects.
Generated plans are 1920x1080, 30 fps, 180 frames (6 s).

    python3 ChrononTemplate/tools/editorial_motion/build_editorial_motion_pack_v1.py
    chronon3d_cli validate --plan <plan> --assets-root ChrononTemplate
"""
from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]  # ChrononTemplate
OUT = TEMPLATE / "golden_plans" / "editorial_motion_pack_v1"

W, H, FPS, TOTAL = 1920, 1080, 30, 180

PF = "assets/fonts/PlayfairDisplay.ttf"
PFI = "assets/fonts/PlayfairDisplay-Italic.ttf"
IB = "assets/fonts/Inter-Bold.ttf"
IR = "assets/fonts/Inter-Regular.ttf"

BG = [0.031, 0.041, 0.055, 1.0]
INK = "#F3EFE4"
MUTED = "#8A98AA"
DIM = "#526074"
ACCENT = "#6FE3FF"
WARM = "#FFB27A"
VIOLET = "#B9A2FF"
GRID = "#7FA8C8"

HEROES = (
    "assets/images/card_penta_1.png",
    "assets/images/card_penta_2.png",
    "assets/images/card_penta_3.png",
    "assets/images/card_penta_4.png",
    "assets/images/card_penta_5.png",
)
THUMBS = (
    "assets/images/card_trio_1.png",
    "assets/images/card_trio_2.png",
    "assets/images/card_trio_3.png",
)
LIST_HERO = "assets/images/investigative_journalist_hero.jpg"
PORTRAIT = "assets/images/premium_sample_portrait.png"

DATES = ("1948", "1969", "1998", "2026")
DATE_WINDOWS = ((0, 38, 46), (44, 82, 90), (88, 126, 134), (134, TOTAL - 1, TOTAL - 1))


def kf(pairs):
    unique = {}
    for frame, value in pairs:
        unique[int(round(frame))] = float(value)
    return [{"frame": frame, "value": unique[frame]} for frame in sorted(unique)]


def track(prop, pairs, easing="out_cubic"):
    return {"property": prop, "keyframes": kf(pairs), "easing": easing}


def has_3d(tracks):
    return any(t["property"] in {"position_z", "rotation_x", "rotation_y"} for t in tracks)


def text_layer(lid, text, x, y, w, h, font, size, fill, *, tracks=None,
               min_size=None, glow=None, stroke=None, shadow=True, italic=False):
    style = {
        "font": font,
        "font_size": size,
        "min_font_size": min_size if min_size is not None else max(14, int(size * 0.62)),
        "max_font_size": size,
        "fit_mode": "shrink_only",
        "fill": fill,
    }
    if glow:
        style["glow"] = {"radius": glow[0], "intensity": glow[1], "color": glow[2]}
    if stroke:
        style["stroke"] = {"color": stroke[0], "width": stroke[1]}
    if shadow:
        style["shadow"] = {"color": "#000000", "opacity": 0.55, "blur": 18, "offset": [0, 6]}
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [int(w), int(h)],
        "position": [float(x), float(y)],
        "start_frame": 0,
        "duration_frames": TOTAL,
        "style": style,
    }
    motion = tracks or [track("opacity", [(0, 1), (TOTAL - 1, 1)], "linear")]
    layer["animation"] = {"tracks": motion}
    if has_3d(motion):
        layer["enable_3d"] = True
    return layer


def image_layer(lid, asset, x, y, w, h, *, tracks=None, radius=0,
                effects=None, fit="cover", start=0, duration=TOTAL):
    layer = {
        "id": lid,
        "type": "image",
        "asset": asset,
        "size": [int(w), int(h)],
        "position": [float(x) - W / 2, float(y) - H / 2],
        "fit": fit,
        "radius": radius,
        "start_frame": start,
        "duration_frames": duration,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
        if has_3d(tracks):
            layer["enable_3d"] = True
    if effects:
        layer["effects"] = effects
    return layer


def color_layer(lid, color, *, tracks=None, effects=None, x=W / 2, y=H / 2,
                w=W, h=H):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [int(w), int(h)],
        "position": [float(x) - W / 2, float(y) - H / 2],
        "start_frame": 0,
        "duration_frames": TOTAL,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    if effects:
        layer["effects"] = effects
    return layer


def path_layer(lid, path, *, stroke_color=ACCENT, width=4, tracks=None,
               effects=None, opacity=1.0, trim=None, start=0, duration=TOTAL,
               cap="round", alpha=1.0):
    shape = {
        "type": "path",
        "path": path,
        "stroke": {
            "color": stroke_color,
            "width": width,
            "cap": cap,
            "join": "round",
        },
    }
    if trim:
        shape["operators"] = [{
            "kind": "trim",
            "params": {
                "start": 0.0,
                "end": 1.0,
                "offset": 0.0,
                "animation": {
                    "easing": trim.get("easing", "in_out_cubic"),
                    "keyframes": [
                        {"frame": key["frame"], "value": [0.0, key["value"], 0.0]}
                        for key in kf(trim["keys"])
                    ],
                },
            },
        }]
    layer = {
        "id": lid,
        "type": "shape",
        "size": [W, H],
        "position": [0, 0],
        "start_frame": start,
        "duration_frames": duration,
        "opacity": opacity,
        "shape": shape,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
        if has_3d(tracks):
            layer["enable_3d"] = True
    if effects:
        layer["effects"] = effects
    return layer


def rect_layer(lid, x, y, w, h, radius, *, fill=None, stroke=None,
               tracks=None, effects=None, opacity=1.0):
    shape = {"type": "rounded_rect", "radius": radius}
    if fill:
        shape["fill"] = fill
    if stroke:
        shape["stroke"] = {"color": stroke[0], "width": stroke[1]}
    layer = {
        "id": lid,
        "type": "shape",
        "size": [int(w), int(h)],
        "position": [float(x) - W / 2, float(y) - H / 2],
        "start_frame": 0,
        "duration_frames": TOTAL,
        "opacity": opacity,
        "shape": shape,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
        if has_3d(tracks):
            layer["enable_3d"] = True
    if effects:
        layer["effects"] = effects
    return layer


def line_path(x1, y1, x2, y2):
    return [{"type": "move_to", "point": [x1, y1]},
            {"type": "line_to", "point": [x2, y2]}]


def grid_path(spacing=120, extent_x=W / 2, extent_y=H / 2):
    points = []
    x = -extent_x
    while x <= extent_x + 0.1:
        points += [{"type": "move_to", "point": [x, -extent_y]},
                   {"type": "line_to", "point": [x, extent_y]}]
        x += spacing
    y = -extent_y
    while y <= extent_y + 0.1:
        points += [{"type": "move_to", "point": [-extent_x, y]},
                   {"type": "line_to", "point": [extent_x, y]}]
        y += spacing
    return points


def dot_grid_path(spacing=120):
    points = []
    y = -480
    while y <= 480:
        x = -840
        while x <= 840:
            points += [{"type": "move_to", "point": [x - 2, y]},
                       {"type": "line_to", "point": [x + 2, y]}]
            x += spacing
        y += spacing
    return points


def vignette(amount=0.5):
    return [{"type": "vignette", "radius": 0.82, "softness": 0.55, "amount": amount}]


def blur(radius=22):
    return [{"type": "gaussian_blur", "radius": radius}]


def glow(radius=24, intensity=0.55, color=ACCENT, alpha=1.0):
    rgb = [int(color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    return [{"type": "glow", "radius": radius, "intensity": intensity,
             "color": rgb + [alpha]}]


def base_canvas(amount=0.55):
    return [
        color_layer("bg", BG, effects=vignette(amount)),
        color_layer("bg_wash", [0.06, 0.11, 0.16, 0.22]),
    ]


def date_opacity(index):
    if index == 0:
        return [(0, 1), (38, 1), (46, 0), (TOTAL - 1, 0)]
    if index == len(DATES) - 1:
        return [(0, 0), (134, 0), (142, 1), (TOTAL - 1, 1)]
    start, hold, end = DATE_WINDOWS[index]
    return [(0, 0), (start - 8, 0), (start, 1), (hold, 1), (end, 0), (TOTAL - 1, 0)]


def date_pop(index):
    start, hold, end = DATE_WINDOWS[index]
    if index == 0:
        return [(0, 0.96), (16, 1.02), (34, 1), (46, 1), (TOTAL - 1, 1)]
    if index == len(DATES) - 1:
        return [(0, 0.96), (134, 0.96), (150, 1.02), (168, 1), (TOTAL - 1, 1)]
    return [(0, 0.96), (start, 0.96), (start + 12, 1.02), (start + 26, 1),
            (end, 1), (TOTAL - 1, 1)]


# ---------------------------------------------------------------------------
# Family 1 - image + same image backdrop + light grid over the whole canvas
# ---------------------------------------------------------------------------
def _image_backdrop_base(asset, *, card=(980, 620), backdrop_blur=22,
                         backdrop_zoom=(1.06, 1.14), grid_opacity=0.11):
    layers = base_canvas(0.5)
    layers.append(image_layer(
        "image_backdrop", asset, W / 2, H / 2, W, H, radius=0,
        effects=blur(backdrop_blur),
        tracks=[track("scale", [(0, backdrop_zoom[0]), (TOTAL - 1, backdrop_zoom[1])],
                      "in_out_sine")],
    ))
    layers.append(color_layer("backdrop_tint", [0.01, 0.02, 0.035, 0.48]))
    return layers


def _image_card(layers, asset, card, *, frame=True, effects=None):
    cw, ch = card
    layers.append(image_layer(
        "hero_image", asset, W / 2, H / 2, cw, ch, radius=18,
        effects=effects or glow(28, 0.28, ACCENT, 0.55),
        tracks=[track("opacity", [(0, 0), (22, 1), (TOTAL - 1, 1)]),
                track("scale", [(0, 0.93), (38, 1.015), (52, 1), (TOTAL - 1, 1)])],
    ))
    if frame:
        layers.append(rect_layer(
            "hero_frame", W / 2, H / 2, cw + 18, ch + 18, 26,
            stroke=("#BFEFFF", 2.0),
            tracks=[track("opacity", [(0, 0), (34, 0.62), (TOTAL - 1, 0.62)])],
        ))
    return layers


def _grid_layers(layers, *, opacity=0.11, drift=12, dot=False, scan=False):
    path = dot_grid_path(120) if dot else grid_path(120)
    layers.append(path_layer(
        "grid_minor", path, stroke_color=GRID, width=1.0,
        tracks=[track("opacity", [(0, 0), (30, opacity), (TOTAL - 1, opacity * 0.85)]),
                track("position_y", [(0, -drift), (TOTAL - 1, drift)], "in_out_sine")],
    ))
    major = grid_path(480)
    layers.append(path_layer(
        "grid_major", major, stroke_color=GRID, width=1.5,
        tracks=[track("opacity", [(0, 0), (40, opacity * 1.35), (TOTAL - 1, opacity * 1.15)]),
                track("position_x", [(0, drift), (TOTAL - 1, -drift)], "in_out_sine")],
    ))
    if scan:
        layers.append(path_layer(
            "scan_line", line_path(-960, 0, 960, 0),
            stroke_color=ACCENT, width=3, effects=glow(26, 0.85),
            tracks=[track("position_y", [(0, -540), (96, 540)], "in_out_sine"),
                    track("opacity", [(0, 0), (10, 0.9), (86, 0.9), (98, 0)]),
                    track("scale_x", [(0, 1), (TOTAL - 1, 1)], "linear")],
        ))


def image_backdrop_grid_reveal():
    asset = HEROES[0]
    layers = _image_backdrop_base(asset)
    _image_card(layers, asset, (1000, 640))
    _grid_layers(layers, opacity=0.12, drift=14)
    layers.append(rect_layer(
        "corner_mark", 260, 180, 64, 2, 1, fill=[0.43, 0.89, 1, 0.8],
        tracks=[track("scale_x", [(0, 0.01), (40, 1), (TOTAL - 1, 1)]),
                track("opacity", [(0, 0), (28, 1), (TOTAL - 1, 0.8)])],
    ))
    return layers


def image_backdrop_grid_scan():
    asset = HEROES[1]
    layers = _image_backdrop_base(asset, card=(920, 700), backdrop_zoom=(1.1, 1.2))
    _image_card(layers, asset, (920, 700), effects=glow(34, 0.34, WARM, 0.5))
    _grid_layers(layers, opacity=0.09, drift=0, scan=True)
    return layers


def image_backdrop_grid_parallax():
    asset = HEROES[2]
    layers = _image_backdrop_base(asset, card=(1040, 600), backdrop_zoom=(1.12, 1.24))
    layers.append(image_layer(
        "hero_image", asset, W / 2, H / 2, 1040, 600, radius=16,
        effects=glow(30, 0.3, VIOLET, 0.45),
        tracks=[track("opacity", [(0, 0), (20, 1), (TOTAL - 1, 1)]),
                track("position_x", [(0, 28), (TOTAL - 1, -22)], "in_out_sine"),
                track("position_y", [(0, 10), (TOTAL - 1, -8)], "in_out_sine"),
                track("rotation_y", [(0, -4.5), (TOTAL - 1, 3.5)], "in_out_sine")],
    ))
    layers.append(rect_layer(
        "hero_frame", W / 2, H / 2, 1058, 618, 24, stroke=("#D9CCFF", 1.8),
        tracks=[track("opacity", [(0, 0), (36, 0.5), (TOTAL - 1, 0.5)])],
    ))
    _grid_layers(layers, opacity=0.1, drift=20)
    return layers


def image_backdrop_grid_focus():
    asset = HEROES[3]
    layers = _image_backdrop_base(asset, card=(860, 680), backdrop_blur=28)
    layers.append(image_layer(
        "hero_image", asset, W / 2, H / 2, 860, 680, radius=20,
        effects=glow(40, 0.32, ACCENT, 0.5),
        tracks=[track("opacity", [(0, 0), (26, 1), (TOTAL - 1, 1)]),
                track("scale", [(0, 1.06), (TOTAL - 1, 1.0)], "in_out_sine")],
    ))
    for index, (x, y, sx, sy) in enumerate(((400, 190, 1, 1), (1520, 190, -1, 1),
                                            (400, 890, 1, -1), (1520, 890, -1, -1))):
        rx, ry = x - W / 2, y - H / 2
        layers.append(path_layer(
            f"focus_bracket_{index}",
            [{"type": "move_to", "point": [rx + sx * 54, ry]},
             {"type": "line_to", "point": [rx, ry]},
             {"type": "line_to", "point": [rx, ry + sy * 54]}],
            stroke_color="#D9F6FF", width=2.5,
            trim={"keys": [(15 + index * 4, 0), (48 + index * 4, 1)]},
            effects=glow(16, 0.5),
        ))
    _grid_layers(layers, opacity=0.08, drift=6)
    return layers


def image_backdrop_grid_dots():
    asset = HEROES[4]
    layers = _image_backdrop_base(asset, card=(980, 620), backdrop_zoom=(1.08, 1.18))
    _image_card(layers, asset, (980, 620), effects=glow(26, 0.3, WARM, 0.45))
    _grid_layers(layers, opacity=0.1, drift=8, dot=True)
    layers.append(path_layer(
        "diagonal_sheen",
        [{"type": "move_to", "point": [-1060, 560]},
         {"type": "line_to", "point": [1060, -560]}],
        stroke_color="#FFFFFF", width=90, opacity=0.035,
        tracks=[track("position_x", [(0, -180), (TOTAL - 1, 220)], "in_out_sine")],
    ))
    return layers


# ---------------------------------------------------------------------------
# Family 2 - date animations
# ---------------------------------------------------------------------------
def _date_layers(layers, *, x=W / 2, y=470, size=220, box=(1100, 330),
                 glow_intensity=0.22):
    for index, date in enumerate(DATES):
        layers.append(text_layer(
            f"date_{index}", date, x, y, box[0], box[1], PF, size, INK,
            tracks=[track("opacity", date_opacity(index), "in_out_cubic"),
                    track("scale", date_pop(index), "out_cubic")],
            glow=(38, glow_intensity, ACCENT if index == len(DATES) - 1 else "#FFFFFF"),
        ))
    return layers


def date_glow_rail():
    layers = base_canvas(0.62)
    layers.append(text_layer(
        "kicker", "CRONOLOGIA", W / 2, 190, 460, 60, IB, 22, ACCENT,
        tracks=[track("opacity", [(0, 0), (18, 0.9), (TOTAL - 1, 0.9)])],
        glow=(14, 0.5, ACCENT), shadow=False,
    ))
    _date_layers(layers, y=460)
    layers.append(path_layer(
        "rail", line_path(-560, 150, 560, 150), stroke_color="#5A6B80", width=2,
        trim={"keys": [(0, 0), (120, 1)]},
    ))
    xs = (-480, -160, 160, 480)
    for index, x in enumerate(xs):
        layers.append(path_layer(
            f"node_{index}", line_path(x, 136, x, 164), stroke_color=ACCENT, width=3,
            trim={"keys": [(index * 20, 0), (index * 20 + 16, 1)]},
            effects=glow(14, 0.6), opacity=0.85,
        ))
        layers.append(text_layer(
            f"rail_date_{index}", DATES[index], W / 2 + x, 760, 250, 60, PF, 28, DIM,
            tracks=[track("opacity", [(0, 0), (30 + index * 18, 0.85), (TOTAL - 1, 0.85)])],
            shadow=False,
        ))
        layers.append(text_layer(
            f"rail_active_{index}", DATES[index], W / 2 + x, 760, 250, 60, PF, 28, ACCENT,
            tracks=[track("opacity", date_opacity(index), "in_out_cubic")],
            glow=(16, 0.55, ACCENT), shadow=False,
        ))
    layers.append(rect_layer(
        "rail_tick", W / 2 - 480, 690, 10, 10, 5, fill=[0.43, 0.89, 1, 1],
        effects=glow(22, 0.8),
        tracks=[track("position_x", [(0, 0), (44, 0), (58, 320), (88, 320),
                                     (102, 640), (132, 640), (146, 960),
                                     (TOTAL - 1, 960)], "in_out_cubic"),
                track("opacity", [(0, 0), (16, 1), (TOTAL - 1, 1)])],
    ))
    return layers


def date_digit_drift():
    layers = base_canvas(0.6)
    xs = (790, 905, 1020, 1135)
    for index, date in enumerate(DATES):
        for digit_index, char in enumerate(date):
            start = DATE_WINDOWS[index][0]
            layers.append(text_layer(
                f"digit_{index}_{digit_index}", char, xs[digit_index], 480, 180, 320,
                PF, 220, INK,
                tracks=[track("opacity", date_opacity(index), "in_out_cubic"),
                        track("position_y", [(0, 34 + digit_index * 8),
                                             (start + 10 + digit_index * 4, 0),
                                             (TOTAL - 1, 0)], "out_cubic")],
                glow=(32, 0.16, ACCENT),
            ))
    layers.append(path_layer(
        "digit_rule", line_path(-420, 160, 420, 160), stroke_color=ACCENT, width=3,
        trim={"keys": [(8, 0), (70, 0.92), (TOTAL - 1, 0.92)]},
        effects=glow(18, 0.5),
    ))
    layers.append(text_layer(
        "digit_kicker", "QUATTRO SOGLIE", W / 2, 800, 520, 60, IB, 20, MUTED,
        tracks=[track("opacity", [(0, 0), (36, 0.85), (TOTAL - 1, 0.85)])],
        shadow=False,
    ))
    return layers


def date_vertical_ledger():
    layers = base_canvas(0.58)
    for index, date in enumerate(DATES):
        layers.append(text_layer(
            f"ledger_row_{index}", date, 460, 350 + index * 120, 560, 80,
            PF, 44, MUTED,
            tracks=[track("opacity", [(0, 0), (20 + index * 10, 0.72), (TOTAL - 1, 0.72)])],
            shadow=False,
        ))
        layers.append(text_layer(
            f"ledger_active_{index}", date, 460, 350 + index * 120, 560, 80,
            PF, 44, ACCENT,
            tracks=[track("opacity", date_opacity(index), "in_out_cubic")],
            glow=(20, 0.5, ACCENT), shadow=False,
        ))
    for index, date in enumerate(DATES):
        layers.append(text_layer(
            f"ledger_big_{index}", date, 1210, 520, 760, 330, PF, 190, INK,
            tracks=[track("opacity", date_opacity(index), "in_out_cubic"),
                    track("position_x", [(0, 26), (DATE_WINDOWS[index][0] + 18, 0),
                                         (TOTAL - 1, 0)], "out_cubic")],
            glow=(36, 0.2, ACCENT),
        ))
    layers.append(rect_layer(
        "ledger_rule", 780, 470, 2, 420, 1, fill=[0.43, 0.89, 1, 0.55],
        tracks=[track("opacity", [(0, 0), (24, 0.8), (TOTAL - 1, 0.8)])],
    ))
    layers.append(rect_layer(
        "ledger_marker", 780, 350, 54, 3, 1, fill=[0.43, 0.89, 1, 1],
        effects=glow(18, 0.7),
        tracks=[track("position_y", [(0, 0), (44, 0), (60, 120), (88, 120),
                                     (104, 240), (132, 240), (148, 360),
                                     (TOTAL - 1, 360)], "in_out_cubic"),
                track("opacity", [(0, 0), (18, 1), (TOTAL - 1, 1)])],
    ))
    return layers


def date_arc():
    layers = base_canvas(0.64)
    arc = [
        {"type": "move_to", "point": [-560, 300]},
        {"type": "cubic_to", "control1": [-300, 220], "control2": [300, 220],
         "point": [560, 300]},
    ]
    layers.append(path_layer(
        "arc", arc, stroke_color="#6F8298", width=2,
        trim={"keys": [(0, 0), (110, 1)]},
    ))
    arc_points = ((-520, 300), (-180, 245), (180, 245), (520, 300))
    for index, (x, y) in enumerate(arc_points):
        layers.append(rect_layer(
            f"arc_node_{index}", W / 2 + x, 540 + y, 12, 12, 6,
            fill=[0.43, 0.89, 1, 1], effects=glow(16, 0.55),
            tracks=[track("opacity", date_opacity(index), "in_out_cubic"),
                    track("scale", [(0, 0.4), (DATE_WINDOWS[index][0] + 8, 1.25),
                                    (DATE_WINDOWS[index][0] + 24, 1), (TOTAL - 1, 1)],
                          "out_cubic")],
        ))
        layers.append(text_layer(
            f"arc_date_{index}", DATES[index], W / 2 + x, 540 + y + 52, 260, 46,
            PF, 24, MUTED,
            tracks=[track("opacity", date_opacity(index), "in_out_cubic")],
            shadow=False,
        ))
    _date_layers(layers, y=490, size=210)
    layers.append(text_layer(
        "arc_kicker", "LINEA DEL TEMPO", W / 2, 960, 520, 56, IB, 18, MUTED,
        tracks=[track("opacity", [(0, 0), (44, 0.8), (TOTAL - 1, 0.8)])],
        shadow=False,
    ))
    return layers


def date_odometer():
    layers = base_canvas(0.6)
    layers.append(rect_layer(
        "odometer_window", W / 2, 490, 760, 300, 12,
        fill=[0.03, 0.05, 0.075, 0.72], stroke=("#7C93AA", 1.4),
        tracks=[track("opacity", [(0, 0), (20, 1), (TOTAL - 1, 1)])],
    ))
    for index, date in enumerate(DATES):
        start, hold, end = DATE_WINDOWS[index]
        if index == 0:
            ys = [(0, 0), (44, 0), (60, -260), (TOTAL - 1, -260)]
        elif index == len(DATES) - 1:
            ys = [(0, 780), (132, 780), (150, 0), (TOTAL - 1, 0)]
        else:
            ys = [(0, index * 260), (start - 10, index * 260),
                  (start + 18, (index - 1) * 260), (TOTAL - 1, (index - 1) * 260)]
        layers.append(text_layer(
            f"odometer_{index}", date, W / 2, 490, 700, 280, PF, 190, INK,
            tracks=[track("position_y", ys, "in_out_cubic"),
                    track("opacity", [(0, 0), (start + 2, 1), (end, 1), (TOTAL - 1, 1)])
                    if index not in (0, len(DATES) - 1) else
                    track("opacity", [(0, 1), (TOTAL - 1, 1)], "linear")],
            glow=(30, 0.18, ACCENT),
        ))
    layers.append(path_layer(
        "odometer_rule", line_path(-360, 250, 360, 250), stroke_color=ACCENT, width=3,
        trim={"keys": [(0, 0), (80, 1)]}, effects=glow(18, 0.55),
    ))
    layers.append(text_layer(
        "odometer_kicker", "SCORRE IL TEMPO", W / 2, 870, 520, 54, IB, 20, MUTED,
        tracks=[track("opacity", [(0, 0), (30, 0.85), (TOTAL - 1, 0.85)])],
        shadow=False,
    ))
    return layers


# ---------------------------------------------------------------------------
# Family 3 - glowing lines between phrases
# ---------------------------------------------------------------------------
def _phrase(layers, lid, text, x, y, *, size=54, color=INK, box=(560, 180),
            start=0, glow_color=ACCENT, intensity=0.3):
    return layers.append(text_layer(
        lid, text, x, y, box[0], box[1], IB, size, color,
        tracks=[track("opacity", [(0, 0), (start + 16, 1), (TOTAL - 1, 1)]),
                track("position_y", [(0, 18), (start + 22, 0), (TOTAL - 1, 0)], "out_cubic")],
        glow=(24, intensity, glow_color),
    ))


def _travel_dot(layers, lid, keys, *, color=ACCENT, size=16):
    layers.append(rect_layer(
        lid, W / 2, H / 2, size, size, size / 2,
        fill=[0.55, 0.94, 1, 1], effects=glow(26, 0.9),
        tracks=[track("position_x", keys, "in_out_cubic"),
                track("opacity", [(0, 0), (16, 1), (TOTAL - 1, 0.85)])],
    ))


def glow_line_direct():
    layers = base_canvas(0.68)
    _phrase(layers, "phrase_left", "NUOVE PROVE", 500, 540, size=58)
    _phrase(layers, "phrase_right", "LA SVOLTA", 1420, 540, size=58, color=ACCENT,
            glow_color=ACCENT, intensity=0.45, start=16)
    layers.append(path_layer(
        "connector", line_path(-210, 0, 210, 0), stroke_color=ACCENT, width=4,
        trim={"keys": [(26, 0), (86, 1)]}, effects=glow(22, 0.8),
    ))
    _travel_dot(layers, "connector_dot",
                [(30, -210), (86, 210), (TOTAL - 1, 210)])
    layers.append(text_layer(
        "connector_label", "COLLEGAMENTO  /  01", W / 2, 620, 420, 44, IB, 15, MUTED,
        tracks=[track("opacity", [(0, 0), (80, 0.75), (TOTAL - 1, 0.75)])],
        shadow=False,
    ))
    return layers


def glow_line_elbow():
    layers = base_canvas(0.66)
    _phrase(layers, "elbow_top", "IL CONTESTO", 500, 400, size=52)
    _phrase(layers, "elbow_bottom", "LA DECISIONE", 1420, 690, size=52, color=ACCENT,
            start=20, intensity=0.42)
    elbow = [
        {"type": "move_to", "point": [-300, -140]},
        {"type": "line_to", "point": [0, -140]},
        {"type": "line_to", "point": [0, 150]},
        {"type": "line_to", "point": [300, 150]},
    ]
    layers.append(path_layer(
        "elbow_connector", elbow, stroke_color=ACCENT, width=4,
        trim={"keys": [(24, 0), (108, 1)]}, effects=glow(24, 0.75),
    ))
    for index, (x, y) in enumerate(((-300, -140), (0, -140), (0, 150), (300, 150))):
        layers.append(rect_layer(
            f"elbow_node_{index}", W / 2 + x, H / 2 + y, 10, 10, 5,
            fill=[0.55, 0.94, 1, 1], effects=glow(16, 0.7),
            tracks=[track("opacity", [(0, 0), (34 + index * 18, 1), (TOTAL - 1, 0.9)])],
        ))
    return layers


def glow_line_pulses():
    layers = base_canvas(0.7)
    _phrase(layers, "pulse_left", "PRIMA", 470, 540, size=62, color=MUTED,
            intensity=0.15)
    _phrase(layers, "pulse_right", "ADESSO", 1450, 540, size=62, color=ACCENT,
            start=12, intensity=0.5)
    for index in range(5):
        x = -240 + index * 120
        layers.append(path_layer(
            f"pulse_dash_{index}", line_path(x - 30, 0, x + 30, 0),
            stroke_color=ACCENT if index >= 3 else "#8FB8CC",
            width=6 if index >= 3 else 3,
            trim={"keys": [(30 + index * 12, 0), (54 + index * 12, 1)]},
            effects=glow(20 if index >= 3 else 12, 0.65),
            opacity=0.95,
        ))
    _travel_dot(layers, "pulse_dot", [(34, -300), (120, 300), (TOTAL - 1, 300)],
                size=12)
    layers.append(text_layer(
        "pulse_label", "SEGNALE  /  ATTIVO", W / 2, 640, 460, 42, IB, 15, MUTED,
        tracks=[track("opacity", [(0, 0), (110, 0.8), (TOTAL - 1, 0.8)])],
        shadow=False,
    ))
    return layers


def glow_line_arc():
    layers = base_canvas(0.64)
    _phrase(layers, "arc_left", "LA STORIA", 500, 650, size=56)
    _phrase(layers, "arc_right", "CONTINUA", 1430, 650, size=56, color=ACCENT,
            start=14, intensity=0.46)
    arc = [
        {"type": "move_to", "point": [-300, 80]},
        {"type": "cubic_to", "control1": [-170, -240], "control2": [170, -240],
         "point": [300, 80]},
    ]
    layers.append(path_layer(
        "arc_connector", arc, stroke_color=ACCENT, width=4,
        trim={"keys": [(26, 0), (104, 1)]}, effects=glow(26, 0.8),
    ))
    layers.append(rect_layer(
        "arc_apex", W / 2, 393, 18, 18, 9, fill=[0.55, 0.94, 1, 1],
        effects=glow(26, 0.9),
        tracks=[track("scale", [(0, 0.2), (76, 1.5), (94, 1), (TOTAL - 1, 1)]),
                track("opacity", [(0, 0), (70, 1), (TOTAL - 1, 0.9)])],
    ))
    return layers


def glow_line_chain():
    layers = base_canvas(0.66)
    phrases = (("CONTESTO", 340), ("PROVE", 540), ("SENTENZA", 740))
    spine = [{"type": "move_to", "point": [-250, -230]},
             {"type": "line_to", "point": [-250, 230]}]
    layers.append(path_layer(
        "chain_spine", spine, stroke_color="#7E96AB", width=2,
        trim={"keys": [(0, 0), (96, 1)]},
    ))
    for index, (label, y) in enumerate(phrases):
        _phrase(layers, f"chain_phrase_{index}", label, 1140, y, size=46,
                box=(480, 100), color=ACCENT if index == 2 else INK,
                start=index * 20, intensity=0.42 if index == 2 else 0.22)
        branch = [{"type": "move_to", "point": [-250, y - 540]},
                  {"type": "line_to", "point": [-40, y - 540]}]
        layers.append(path_layer(
            f"chain_branch_{index}", branch, stroke_color=ACCENT, width=3,
            trim={"keys": [(20 + index * 24, 0), (52 + index * 24, 1)]},
            effects=glow(18, 0.6),
        ))
        layers.append(rect_layer(
            f"chain_node_{index}", 710, y, 12, 12, 6,
            fill=[0.55, 0.94, 1, 1], effects=glow(18, 0.7),
            tracks=[track("opacity", [(0, 0), (30 + index * 24, 1), (TOTAL - 1, 0.9)])],
        ))
    return layers


# ---------------------------------------------------------------------------
# Family 4 - short phrases with camera-like motion
# ---------------------------------------------------------------------------
def _camera_phrase(layers, text, *, y=520, size=104, box=(1500, 340), font=IB,
                   color=INK, tracks=None, glow_color=ACCENT, intensity=0.3):
    layers.append(text_layer(
        "phrase", text, W / 2, y, box[0], box[1], font, size, color,
        tracks=tracks, glow=(46, intensity, glow_color),
        stroke=("#05090D", 2.0),
    ))


def _camera_rule(layers, y=650, width=360, *, color=ACCENT, start=20):
    layers.append(path_layer(
        "camera_rule", line_path(-width / 2, y - 540, width / 2, y - 540),
        stroke_color=color, width=3,
        trim={"keys": [(start, 0), (start + 46, 1)]}, effects=glow(20, 0.65),
    ))


def camera_phrase_push():
    layers = base_canvas(0.72)
    _camera_phrase(layers, "L'ULTIMA PAROLA", size=100,
                   tracks=[track("opacity", [(0, 0), (24, 1), (TOTAL - 1, 1)]),
                           track("scale", [(0, 0.86), (52, 1.0), (TOTAL - 1, 1.02)],
                                 "in_out_cubic"),
                           track("position_y", [(0, 26), (52, 0), (TOTAL - 1, -2)],
                                 "in_out_cubic")])
    _camera_rule(layers, 660, 440)
    layers.append(text_layer(
        "camera_kicker", "PUSH IN  /  01", W / 2, 820, 440, 50, IB, 18, MUTED,
        tracks=[track("opacity", [(0, 0), (40, 0.8), (TOTAL - 1, 0.8)])],
        shadow=False,
    ))
    return layers


def camera_phrase_pull():
    layers = base_canvas(0.7)
    _camera_phrase(layers, "TUTTO CAMBIA", size=112, color=ACCENT,
                   glow_color=ACCENT, intensity=0.42,
                   tracks=[track("opacity", [(0, 0.2), (26, 1), (TOTAL - 1, 1)]),
                           track("scale", [(0, 1.28), (54, 1.0), (TOTAL - 1, 0.985)],
                                 "in_out_cubic"),
                           track("position_y", [(0, -18), (54, 0), (TOTAL - 1, 4)],
                                 "in_out_cubic")])
    _camera_rule(layers, 660, 500, start=28)
    return layers


def camera_phrase_orbit():
    layers = base_canvas(0.7)
    _camera_phrase(layers, "NUOVI ORIZZONTI", size=96, font=PF,
                   tracks=[track("opacity", [(0, 0), (22, 1), (TOTAL - 1, 1)]),
                           track("position_x", [(0, -120), (66, 0), (TOTAL - 1, 8)],
                                 "in_out_cubic"),
                           track("position_y", [(0, -10), (66, 0), (TOTAL - 1, 0)],
                                 "in_out_cubic"),
                           track("scale", [(0, 0.94), (34, 1.0), (66, 1.0), (TOTAL - 1, 1.02)],
                                 "in_out_cubic")])
    _camera_rule(layers, 670, 480, color=WARM, start=24)
    layers.append(rect_layer(
        "orbit_marker", 400, 300, 12, 12, 6, fill=[1, 0.7, 0.48, 1],
        effects=glow(20, 0.7),
        tracks=[track("position_x", [(0, -120), (70, 120), (TOTAL - 1, 120)],
                      "in_out_sine"),
                track("opacity", [(0, 0), (38, 1), (TOTAL - 1, 0.75)])],
    ))
    return layers


def camera_phrase_tilt():
    layers = base_canvas(0.68)
    _camera_phrase(layers, "CAMBIA IL\nPUNTO DI VISTA", size=86, box=(1320, 460),
                   tracks=[track("opacity", [(0, 0), (24, 1), (TOTAL - 1, 1)]),
                           track("position_y", [(0, 100), (60, 0), (TOTAL - 1, -4)],
                                 "in_out_cubic"),
                           track("scale", [(0, 1.08), (60, 1.0), (TOTAL - 1, 1.02)],
                                 "in_out_cubic")])
    _camera_rule(layers, 770, 520, start=34)
    return layers


def camera_phrase_parallax():
    layers = base_canvas(0.72)
    layers.append(text_layer(
        "phrase_back", "LA STORIA", W / 2 - 120, 440, 1200, 240, IB, 92, "#D6DEE8",
        tracks=[track("opacity", [(0, 0), (22, 1), (TOTAL - 1, 1)]),
                track("position_x", [(0, 90), (TOTAL - 1, -40)], "in_out_sine"),
                track("scale", [(0, 0.97), (TOTAL - 1, 1.03)], "in_out_sine")],
        glow=(30, 0.18, "#FFFFFF"),
    ))
    layers.append(text_layer(
        "phrase_front", "CONTINUA", W / 2 + 160, 650, 900, 240, IB, 92, ACCENT,
        tracks=[track("opacity", [(0, 0), (30, 1), (TOTAL - 1, 1)]),
                track("position_x", [(0, -60), (TOTAL - 1, 80)], "in_out_sine"),
                track("scale", [(0, 1.06), (TOTAL - 1, 1.0)], "in_out_sine")],
        glow=(40, 0.4, ACCENT),
    ))
    _camera_rule(layers, 790, 620, start=40)
    return layers


# ---------------------------------------------------------------------------
# Family 5 - lists with an image beside the list
# ---------------------------------------------------------------------------
LIST_ITEMS = ("Il contesto", "La decisione", "Le conseguenze")


def _list_heading(layers, text="PUNTI CHIAVE", x=1260, y=330):
    layers.append(text_layer(
        "list_heading", text, x, y, 760, 110, PF, 58, INK,
        tracks=[track("opacity", [(0, 0), (24, 1), (TOTAL - 1, 1)]),
                track("position_y", [(0, 18), (34, 0), (TOTAL - 1, 0)])],
        glow=(22, 0.16, ACCENT),
    ))


def _row(layers, index, x, y, text, *, box=(680, 70), size=34,
         color=INK, start=None, marker=True):
    start = index * 14 if start is None else start
    layers.append(text_layer(
        f"row_{index}", text, x, y, box[0], box[1], IR, size, color,
        tracks=[track("opacity", [(0, 0), (start + 18, 1), (TOTAL - 1, 1)]),
                track("position_x", [(0, 26), (start + 28, 0), (TOTAL - 1, 0)])],
    ))
    if marker:
        layers.append(rect_layer(
            f"row_dot_{index}", x - box[0] / 2 + 4, y, 8, 8, 4,
            fill=[0.43, 0.89, 1, 0.9], effects=glow(10, 0.5),
            tracks=[track("opacity", [(0, 0), (start + 16, 1), (TOTAL - 1, 0.9)])],
        ))


def image_list_split():
    layers = base_canvas(0.58)
    layers.append(image_layer(
        "list_hero", LIST_HERO, 480, 540, 620, 780, radius=22,
        effects=glow(24, 0.24, ACCENT, 0.45),
        tracks=[track("opacity", [(0, 0), (24, 1), (TOTAL - 1, 1)]),
                track("scale", [(0, 1.04), (TOTAL - 1, 1.0)], "in_out_sine")],
    ))
    _list_heading(layers, x=1280, y=350)
    for index, item in enumerate(LIST_ITEMS):
        _row(layers, index, 1280, 500 + index * 120, item, box=(720, 80))
        layers.append(path_layer(
            f"row_rule_{index}",
            line_path(-340, (500 + index * 120 - 540) + 46, 340, (500 + index * 120 - 540) + 46),
            stroke_color="#60758C", width=1,
            trim={"keys": [(index * 14 + 12, 0), (index * 14 + 58, 1)]},
            opacity=0.6,
        ))
    return layers


def image_list_thumb_rows():
    layers = base_canvas(0.62)
    _list_heading(layers, "IN SINTESI", x=W / 2, y=250)
    for index, (item, asset) in enumerate(zip(LIST_ITEMS, THUMBS)):
        y = 400 + index * 200
        layers.append(image_layer(
            f"thumb_{index}", asset, 610, y, 220, 140, radius=12,
            effects=glow(14, 0.22, ACCENT, 0.4),
            tracks=[track("opacity", [(0, 0), (20 + index * 14, 1), (TOTAL - 1, 1)]),
                    track("position_x", [(0, -30), (30 + index * 14, 0), (TOTAL - 1, 0)])],
        ))
        layers.append(text_layer(
            f"thumb_number_{index}", f"0{index + 1}", 810, y, 110, 90, IB, 30, ACCENT,
            tracks=[track("opacity", [(0, 0), (26 + index * 14, 1), (TOTAL - 1, 1)])],
            glow=(12, 0.45, ACCENT), shadow=False,
        ))
        _row(layers, index, 1160, y, item, box=(620, 80), start=index * 14 + 10,
             marker=False)
        layers.append(path_layer(
            f"thumb_rule_{index}",
            line_path(-200, y - 540 + 72, 480, y - 540 + 72),
            stroke_color="#5E748A", width=1.2,
            trim={"keys": [(index * 14 + 18, 0), (index * 14 + 70, 1)]},
            opacity=0.65,
        ))
    return layers


def image_list_numbered():
    layers = base_canvas(0.6)
    layers.append(image_layer(
        "list_hero", LIST_HERO, 1470, 550, 560, 720, radius=18,
        effects=glow(26, 0.24, WARM, 0.4),
        tracks=[track("opacity", [(0, 0), (28, 1), (TOTAL - 1, 1)]),
                track("position_x", [(0, 36), (TOTAL - 1, 0)], "out_cubic")],
    ))
    for index, item in enumerate(LIST_ITEMS):
        y = 380 + index * 160
        layers.append(text_layer(
            f"number_{index}", f"0{index + 1}", 360, y, 160, 120, PF, 64, ACCENT,
            tracks=[track("opacity", [(0, 0), (18 + index * 14, 1), (TOTAL - 1, 1)])],
            glow=(16, 0.4, ACCENT),
        ))
        _row(layers, index, 800, y + 10, item, box=(680, 90), size=38, start=index * 14)
        layers.append(path_layer(
            f"number_rule_{index}",
            line_path(-330, y - 540 + 72, 330, y - 540 + 72),
            stroke_color="#6B8096", width=1.4,
            trim={"keys": [(index * 14 + 20, 0), (index * 14 + 74, 1)]},
            opacity=0.7,
        ))
    return layers


def image_list_circle():
    layers = base_canvas(0.62)
    layers.append(image_layer(
        "list_circle", PORTRAIT, 1450, 520, 560, 560, radius=280,
        effects=glow(34, 0.28, ACCENT, 0.45),
        tracks=[track("opacity", [(0, 0), (30, 1), (TOTAL - 1, 1)]),
                track("scale", [(0, 0.9), (52, 1.02), (70, 1), (TOTAL - 1, 1)])],
    ))
    layers.append(rect_layer(
        "circle_ring", 1450, 520, 596, 596, 298, stroke=("#B9EFFF", 1.6),
        tracks=[track("opacity", [(0, 0), (48, 0.55), (TOTAL - 1, 0.55)]),
                track("scale", [(0, 1.08), (70, 1), (TOTAL - 1, 1)])],
    ))
    _list_heading(layers, "IL QUADRO", x=700, y=300)
    for index, item in enumerate(LIST_ITEMS):
        _row(layers, index, 700, 470 + index * 140, item, box=(700, 90), size=36)
        layers.append(rect_layer(
            f"circle_dot_{index}", 260, 470 + index * 140, 10, 10, 5,
            fill=[0.43, 0.89, 1, 0.9], effects=glow(12, 0.5),
            tracks=[track("opacity", [(0, 0), (index * 14 + 18, 1), (TOTAL - 1, 0.9)])],
        ))
    return layers


def image_list_filmstrip():
    layers = base_canvas(0.6)
    for index, asset in enumerate(THUMBS):
        x = 560 + index * 400
        layers.append(image_layer(
            f"strip_image_{index}", asset, x, 330, 340, 220, radius=10,
            effects=glow(14, 0.2, ACCENT, 0.35),
            tracks=[track("opacity", [(0, 0), (22 + index * 14, 1), (TOTAL - 1, 1)]),
                    track("position_y", [(0, 24), (42 + index * 14, 0), (TOTAL - 1, 0)])],
        ))
        layers.append(rect_layer(
            f"strip_frame_{index}", x, 330, 350, 230, 15, stroke=("#8FB8CC", 1.2),
            tracks=[track("opacity", [(0, 0), (36 + index * 14, 0.6), (TOTAL - 1, 0.6)])],
        ))
    for index, item in enumerate(LIST_ITEMS):
        _row(layers, index, W / 2, 620 + index * 110, item, box=(800, 80), size=36,
             start=index * 16 + 20, marker=True)
        layers.append(path_layer(
            f"strip_rule_{index}",
            line_path(-400, (620 + index * 110 - 540) + 42,
                      400, (620 + index * 110 - 540) + 42),
            stroke_color="#5C7188", width=1.2,
            trim={"keys": [(index * 16 + 25, 0), (index * 16 + 82, 1)]},
            opacity=0.6,
        ))
    return layers


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
FAMILIES = (
    {
        "id": "image_backdrop_grid",
        "title": "Immagini con backdrop e griglia",
        "description": "La stessa immagine sfocata dietro, la card nitida davanti e una griglia leggera su tutta l'inquadratura.",
        "presets": (
            ("image_backdrop_grid_reveal", "Backdrop grid reveal",
             "Card che emerge dalla copia sfocata mentre la griglia sale e si accende.", image_backdrop_grid_reveal),
            ("image_backdrop_grid_scan", "Backdrop grid scan",
             "Linea di scansione luminosa che attraversa la griglia e la card.", image_backdrop_grid_scan),
            ("image_backdrop_grid_parallax", "Backdrop grid parallax",
             "Backdrop e griglia in contro-movimento, card con micro-rotazione 3D.", image_backdrop_grid_parallax),
            ("image_backdrop_grid_focus", "Backdrop grid focus",
             "Fuoco che si chiude sulla card e quattro angoli che si disegnano.", image_backdrop_grid_focus),
            ("image_backdrop_grid_dots", "Backdrop dot grid",
             "Matrice di punti al posto delle linee e riflesso diagonale.", image_backdrop_grid_dots),
        ),
    },
    {
        "id": "date_motion",
        "title": "Animazioni data",
        "description": "Quattro date in sequenza, tipografia Playfair e accenti glow su fondo editoriale scuro.",
        "presets": (
            ("date_glow_rail", "Date glow rail",
             "Rail luminoso con nodi e tick che avanza al cambio data.", date_glow_rail),
            ("date_digit_drift", "Date digit drift",
             "Ogni cifra entra dal basso con uno scarto progressivo.", date_digit_drift),
            ("date_vertical_ledger", "Date vertical ledger",
             "Elenco verticale delle date e data attiva grande a destra.", date_vertical_ledger),
            ("date_arc", "Date arc",
             "Arco che collega quattro nodi e data attiva al centro.", date_arc),
            ("date_odometer", "Date odometer",
             "Nastro verticale che scorre una data intera per volta.", date_odometer),
        ),
    },
    {
        "id": "glow_connections",
        "title": "Linee glow tra frasi",
        "description": "Collegamenti luminosi che uniscono le frasi più recenti: dritti, a gomito, a impulsi, ad arco e a catena.",
        "presets": (
            ("glow_line_direct", "Glow line direct",
             "Due frasi e una linea luminosa che si disegna tra loro.", glow_line_direct),
            ("glow_line_elbow", "Glow line elbow",
             "Connettore a gomito con nodi luminosi tra due frasi sfalsate.", glow_line_elbow),
            ("glow_line_pulses", "Glow line pulses",
             "Cinque impulsi si accendono in sequenza lungo il collegamento.", glow_line_pulses),
            ("glow_line_arc", "Glow line arc",
             "Arco luminoso con nodo centrale pulsante.", glow_line_arc),
            ("glow_line_chain", "Glow line chain",
             "Spina verticale con rami verso tre frasi in sequenza.", glow_line_chain),
        ),
    },
    {
        "id": "camera_phrases",
        "title": "Frasi con camera",
        "description": "Frasi brevi mosse da pan, scale e parallasse 2D che simulano push, pull, orbita e tilt di camera.",
        "presets": (
            ("camera_phrase_push", "Camera phrase push",
             "Push in frontale con leggero tilt che si raddrizza.", camera_phrase_push),
            ("camera_phrase_pull", "Camera phrase pull",
             "Il titolo parte grande e si assesta indietro.", camera_phrase_pull),
            ("camera_phrase_orbit", "Camera phrase orbit",
             "Orbita laterale con pan e variazione di scala.", camera_phrase_orbit),
            ("camera_phrase_tilt", "Camera phrase tilt",
             "Tilt dall'alto con discesa e messa a fuoco della frase.", camera_phrase_tilt),
            ("camera_phrase_parallax", "Camera phrase parallax",
             "Due righe con pan opposto e scala diversa in parallasse.", camera_phrase_parallax),
        ),
    },
    {
        "id": "image_lists",
        "title": "Elenchi con immagine",
        "description": "Liste editoriali con un'immagine accanto al blocco o una miniatura accanto a ogni voce.",
        "presets": (
            ("image_list_split", "Image list split",
             "Immagine grande a sinistra e tre voci con regole a destra.", image_list_split),
            ("image_list_thumb_rows", "Image list thumb rows",
             "Una miniatura accanto a ogni voce, in righe sfalsate.", image_list_thumb_rows),
            ("image_list_numbered", "Image list numbered",
             "Numeri grandi, voci e immagine verticale a destra.", image_list_numbered),
            ("image_list_circle", "Image list circle",
             "Ritratto circolare a destra e lista con punti luminosi a sinistra.", image_list_circle),
            ("image_list_filmstrip", "Image list filmstrip",
             "Filmstrip di tre immagini sopra e lista con sottolineature.", image_list_filmstrip),
        ),
    },
)


def build_plan(slug, layers):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"editorial_motion_{slug}",
        "canvas": {
            "width": W,
            "height": H,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": TOTAL,
        },
        "layers": layers,
        "output": {
            "path": f"{slug}.mp4",
            "format": "mp4",
            "codec": "h264",
            "crf": 16,
        },
    }


def used_assets(layers):
    return sorted({layer["asset"] for layer in layers if layer["type"] == "image"})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog_families = []
    total = 0
    for family in FAMILIES:
        family_dir = OUT / family["id"]
        family_dir.mkdir(parents=True, exist_ok=True)
        presets = []
        for slug, title, description, builder in family["presets"]:
            layers = builder()
            plan = build_plan(slug, layers)
            plan_path = family_dir / f"{slug}.plan.json"
            plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
            entry = {
                "id": slug,
                "title": title,
                "description": description,
                "plan": str(plan_path.relative_to(TEMPLATE)),
                "fps": FPS,
                "frames": TOTAL,
                "duration_ms": round(TOTAL / FPS * 1000),
                "layers": len(layers),
                "assets": used_assets(layers),
            }
            presets.append(entry)
            total += 1
            print(f"{family['id']:20s} {slug:28s} layers={len(layers):3d}")
        catalog_families.append({
            "id": family["id"],
            "title": family["title"],
            "description": family["description"],
            "presets": presets,
        })

    catalog = {
        "schema": "chronontemplate.editorial-motion-pack.v1",
        "version": 1,
        "family_id": "editorial_motion_pack_v1",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1},
        "duration_frames": TOTAL,
        "duration_ms": round(TOTAL / FPS * 1000),
        "families": catalog_families,
    }
    (OUT / "catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    )

    rows = [
        "# Editorial motion pack v1",
        "",
        "Cinque famiglie, cinque animazioni ciascuna. Piani RenderPlan V3 a",
        "1920x1080, 30 fps, 180 frame (6 secondi), generati da",
        "`tools/editorial_motion/build_editorial_motion_pack_v1.py`.",
        "",
        "| Famiglia | # | Animazione | Movimento | Piano |",
        "|---|---|---|---|---|",
    ]
    for family in catalog_families:
        for index, entry in enumerate(family["presets"], start=1):
            rows.append(
                f"| {family['title']} | {index:02d} | {entry['title']} | "
                f"{entry['description']} | `{entry['plan']}` |"
            )
    (OUT / "CATALOG.md").write_text("\n".join(rows) + "\n")
    print(f"\n{catalog['family_id']}: {total} plans -> {OUT}")
    print(f"catalog: {OUT / 'catalog.json'}")


if __name__ == "__main__":
    main()
