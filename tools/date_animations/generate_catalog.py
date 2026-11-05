#!/usr/bin/env python3
"""Parametric date-animation catalog for Chronon3d render plans.

Thirteen presets share the same four dates, cream background, Playfair type
and minimal geometry. Only the date transition changes. The rolling-year
preset (12) is the clean odometer; the other twelve are generated here at
24 fps / 240 frames. Dates carry no editorial labels: the years are the
whole content.

The generated catalog is intentionally data-light: a preset changes dates,
typography and tracks, not the renderer. Every plan is a normal
`chronon.render-plan.v3` document and can be rendered with:

    chronon3d_cli render-plan --input <plan> --output <mp4> --assets-root ChrononTemplate

Catalog: golden_plans/date_animation_catalog/catalog.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ChrononTemplate
OUT = ROOT / "golden_plans" / "date_animation_catalog"
RENDERS = ROOT / "renders" / "date_animation_catalog"

TOTAL = 240
FPS = 24
PF = "assets/fonts/PlayfairDisplay.ttf"

INK = "#262521"
MUTED = "#66625B"
ACCENT = "#C8553D"
BG = [0.96, 0.95, 0.93, 1.0]
RAIL = [0.72, 0.70, 0.66, 1.0]
ACCENT_RGBA = [0.784, 0.333, 0.239, 1.0]

DATES = [
    ("1948", "BIRTH"),
    ("1969", "CHANGE"),
    ("1998", "LAUNCH"),
    ("2026", "NOW"),
]
RAIL_X = [540.0, 820.0, 1100.0, 1380.0]
DATE_Y = 470.0
RAIL_Y = 820.0
AXIS_Y = 886.0


def kf(pairs):
    return [{"frame": f, "value": float(v)} for f, v in pairs]


def text_layer(lid, text, x, y, w, h, font, size, fill, tracks=None):
    layer = {
        "id": lid,
        "type": "text",
        "text": text,
        "size": [w, h],
        "position": [x, y],
        "start_frame": 0,
        "duration_frames": TOTAL,
        "style": {
            "font": font,
            "font_size": size,
            "min_font_size": size,
            "max_font_size": size,
            "fit_mode": "shrink_only",
            "fill": fill,
        },
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def color_layer(lid, color, w, h, ox, oy, tracks=None):
    layer = {
        "id": lid,
        "type": "color",
        "color": color,
        "size": [w, h],
        "position": [ox, oy],
        "start_frame": 0,
        "duration_frames": TOTAL,
    }
    if tracks:
        layer["animation"] = {"tracks": tracks}
    return layer


def opacity(pairs, easing="out_cubic"):
    return {"property": "opacity", "keyframes": kf(pairs), "easing": easing}


def position_x(pairs, easing="out_cubic"):
    return {"property": "position_x", "keyframes": kf(pairs), "easing": easing}


def position_y(pairs, easing="out_cubic"):
    return {"property": "position_y", "keyframes": kf(pairs), "easing": easing}


def scale(pairs, easing="out_cubic"):
    return {"property": "scale", "keyframes": kf(pairs), "easing": easing}


def scale_x(pairs, easing="out_cubic"):
    return {"property": "scale_x", "keyframes": kf(pairs), "easing": easing}


def scale_y(pairs, easing="out_cubic"):
    return {"property": "scale_y", "keyframes": kf(pairs), "easing": easing}


def active_fades():
    """A 12-frame crossfade at each transition; holds are 48/60/60/36 frames."""
    return [
        [(0, 1), (48, 1), (60, 0), (TOTAL - 1, 0)],
        [(0, 0), (48, 0), (60, 1), (120, 1), (132, 0), (TOTAL - 1, 0)],
        [(0, 0), (120, 0), (132, 1), (192, 1), (204, 0), (TOTAL - 1, 0)],
        [(0, 0), (192, 0), (204, 1), (TOTAL - 1, 1)],
    ]


def add_bg(layers):
    layers.append(color_layer("bg", BG, 1920, 1080, 0, 0))


def add_date(layers, i, x=960, y=DATE_Y, size=230, w=1200, h=300,
             opacity_pairs=None, extra_tracks=None):
    tracks = [opacity(opacity_pairs or active_fades()[i], "in_out_cubic")]
    tracks.extend(extra_tracks or [])
    layers.append(text_layer(
        f"date_{i}", DATES[i][0], x, y, w, h, PF, size, INK, tracks
    ))




def add_rail(layers, line_w=1000, y=RAIL_Y):
    layers.append(color_layer("rail", RAIL, line_w, 2, 0, y - 540))
    for i, (date_text, _) in enumerate(DATES):
        layers.append(text_layer(
            f"axis_{i}", date_text, RAIL_X[i], y + 66, 240, 40, PF, 26, MUTED
        ))


# ---------------------------------------------------------------------------
# 01 — Timeline progressiva
# ---------------------------------------------------------------------------
def timeline_progress():
    layers = []
    add_bg(layers)
    for i in range(4):
        add_date(layers, i)
    add_rail(layers)

    # The accent line grows from the first node to the active node. Its left
    # edge stays at x=540, so scale and position move together.
    grows = [(0, .02), (48, .02), (60, .333), (120, .333),
             (132, .667), (192, .667), (204, 1), (TOTAL - 1, 1)]
    px = [(f, -420 + 420 * s) for f, s in grows]
    layers.append(color_layer(
        "progress_line", ACCENT_RGBA, 840, 2, 0, RAIL_Y - 540,
        [scale_x(grows, "in_out_cubic"), position_x(px, "in_out_cubic")],
    ))
    return layers


# ---------------------------------------------------------------------------
# 02 — Year Morph (only digits that change)
# ---------------------------------------------------------------------------
def year_morph():
    layers = []
    add_bg(layers)
    xs = [780, 900, 1020, 1140]

    def digit(lid, text, x, op):
        layers.append(text_layer(
            lid, text, x, DATE_Y, 180, 300, PF, 230, INK,
            [opacity(op, "in_out_cubic")],
        ))

    # 1 and 9 hold through the first three dates; only 19 -> 20 changes them.
    digit("d1_1", "1", xs[0], [(0, 1), (192, 1), (204, 0), (TOTAL - 1, 0)])
    digit("d1_2", "2", xs[0], [(0, 0), (192, 0), (204, 1), (TOTAL - 1, 1)])
    digit("d2_9", "9", xs[1], [(0, 1), (192, 1), (204, 0), (TOTAL - 1, 0)])
    digit("d2_0", "0", xs[1], [(0, 0), (192, 0), (204, 1), (TOTAL - 1, 1)])

    d3 = [
        ("4", [(0, 1), (48, 1), (60, 0), (TOTAL - 1, 0)]),
        ("6", [(0, 0), (48, 0), (60, 1), (120, 1), (132, 0), (TOTAL - 1, 0)]),
        ("9", [(0, 0), (120, 0), (132, 1), (192, 1), (204, 0), (TOTAL - 1, 0)]),
        ("2", [(0, 0), (192, 0), (204, 1), (TOTAL - 1, 1)]),
    ]
    d4 = [
        ("8", [(0, 1), (48, 1), (60, 0), (TOTAL - 1, 0)]),
        ("9", [(0, 0), (48, 0), (60, 1), (120, 1), (132, 0), (TOTAL - 1, 0)]),
        ("8", [(0, 0), (120, 0), (132, 1), (192, 1), (204, 0), (TOTAL - 1, 0)]),
        ("6", [(0, 0), (192, 0), (204, 1), (TOTAL - 1, 1)]),
    ]
    for j, (text, op) in enumerate(d3):
        digit(f"d3_{j}", text, xs[2], op)
    for j, (text, op) in enumerate(d4):
        digit(f"d4_{j}", text, xs[3], op)
    return layers


# ---------------------------------------------------------------------------
# 03 — Timeline verticale
# ---------------------------------------------------------------------------
def vertical_timeline():
    layers = []
    add_bg(layers)
    layers.append(color_layer("vertical_rail", RAIL, 2, 620, 700 - 960, 0))
    for i, (date_text, _) in enumerate(DATES):
        layers.append(text_layer(
            f"v_axis_{i}", date_text, 640, 300 + i * 180, 240, 40, PF, 26, MUTED
        ))

    for i in range(4):
        # 1948 exits upward; each new date enters from below and exits upward.
        if i == 0:
            ys = [(0, 0), (48, 0), (60, -40), (TOTAL - 1, -40)]
        elif i == 3:
            ys = [(0, 40), (192, 40), (204, 0), (TOTAL - 1, 0)]
        else:
            ys = [(0, 40), (60, 0), (120, 0), (132, -40), (TOTAL - 1, -40)]
        add_date(layers, i, x=1050, y=DATE_Y, size=230, w=1000, h=300,
                 extra_tracks=[position_y(ys, "in_out_cubic")])
    return layers


# ---------------------------------------------------------------------------
# 04 — Sottolineatura animata
# ---------------------------------------------------------------------------
def animated_underline():
    layers = []
    add_bg(layers)
    for i in range(4):
        add_date(layers, i, y=450)

    # Draw left-to-right under each date, then redraw for the next one.
    s_keys = [(0, 0), (16, 1), (48, 1), (50, 0), (68, 0), (72, 1),
              (120, 1), (122, 0), (140, 0), (144, 1),
              (192, 1), (194, 0), (212, 0), (216, 1), (TOTAL - 1, 1)]
    px = [(f, -180 + 180 * s) for f, s in s_keys]
    layers.append(color_layer(
        "draw_line", ACCENT_RGBA, 360, 2, 0, 660 - 540,
        [scale_x(s_keys, "in_out_cubic"), position_x(px, "in_out_cubic")],
    ))
    return layers


# ---------------------------------------------------------------------------
# 05 — Calendario essenziale / split-flap
# ---------------------------------------------------------------------------
def calendar_flip():
    layers = []
    add_bg(layers)
    xs = [780, 900, 1020, 1140]
    fades = active_fades()

    for i, (date_text, _) in enumerate(DATES):
        start, end = (0, 48) if i == 0 else (60 + (i - 1) * 72, 120 + (i - 1) * 72)
        if i == 0:
            squash = [(0, .62), (6, 1), (48, 1), (56, .62), (TOTAL - 1, .62)]
        elif i == 3:
            start, end = 204, TOTAL - 1
            squash = [(0, .62), (204, .62), (210, 1), (TOTAL - 1, 1)]
        else:
            squash = [(0, .62), (start - 12, .62), (start, .62),
                      (start + 6, 1), (end, 1), (end + 8, .62),
                      (TOTAL - 1, .62)]
        for j, ch in enumerate(date_text):
            layers.append(text_layer(
                f"cal_{i}_{j}", ch, xs[j], DATE_Y, 180, 300, PF, 230, INK,
                [opacity(fades[i], "in_out_cubic"), scale_y(squash, "out_cubic")],
            ))
    return layers


# ---------------------------------------------------------------------------
# 06 — Date Stack
# ---------------------------------------------------------------------------
def date_stack():
    layers = []
    add_bg(layers)
    for i in range(4):
        add_date(layers, i, x=1280, y=450, size=190, w=700, h=300)

    for i, (date_text, _) in enumerate(DATES):
        row_y = 330 + i * 120
        entry = [(0, 12), (16 + i * 4, 0), (TOTAL - 1, 0)]
        layers.append(text_layer(
            f"stack_row_{i}", date_text, 630, row_y,
            560, 50, PF, 30, MUTED,
            [position_y(entry, "out_cubic"), opacity([(0, 0), (12 + i * 4, .62), (TOTAL - 1, .62)], "out_cubic")],
        ))
        layers.append(text_layer(
            f"stack_active_{i}", date_text, 630, row_y,
            560, 50, PF, 30, ACCENT,
            [opacity(active_fades()[i], "in_out_cubic")],
        ))
    layers.append(color_layer(
        "stack_marker", ACCENT_RGBA, 2, 40, 350 - 960, 330 - 540,
        [position_y([(0, 0), (60, 0), (132, 120), (192, 240), (204, 360), (TOTAL - 1, 360)], "in_out_cubic")],
    ))
    return layers


# ---------------------------------------------------------------------------
# 07 — Split Date
# ---------------------------------------------------------------------------
def split_date():
    layers = []
    add_bg(layers)
    # Century and suffix meet with a deliberate gap. On a transition the old
    # halves part outward and the new ones arrive from outside, then close.
    for i, (date_text, _) in enumerate(DATES):
        prefix, suffix = date_text[:2], date_text[2:]
        op = active_fades()[i]
        # position_x tracks are offsets from the layer's base position.
        if i == 0:
            p_x = [(0, 0), (48, 0), (60, -30), (TOTAL - 1, -30)]
            s_x = [(0, 0), (48, 0), (60, 30), (TOTAL - 1, 30)]
        elif i == 3:
            p_x = [(0, 30), (192, 30), (204, 0), (TOTAL - 1, 0)]
            s_x = [(0, -30), (192, -30), (204, 0), (TOTAL - 1, 0)]
        else:
            p_x = [(0, 30), (48, 30), (60, 0), (120, 0),
                   (132, -30), (TOTAL - 1, -30)]
            s_x = [(0, -30), (48, -30), (60, 0), (120, 0),
                   (132, 30), (TOTAL - 1, 30)]
        layers.append(text_layer(
            f"split_p_{i}", prefix, 800, DATE_Y, 400, 300, PF, 230, INK,
            [position_x(p_x, "in_out_cubic"), opacity(op, "in_out_cubic")],
        ))
        layers.append(text_layer(
            f"split_s_{i}", suffix, 1120, DATE_Y, 400, 300, PF, 230, INK,
            [position_x(s_x, "in_out_cubic"), opacity(op, "in_out_cubic")],
        ))
    return layers


# ---------------------------------------------------------------------------
# 08 — Crossfade cronologico
# ---------------------------------------------------------------------------
def crossfade():
    layers = []
    add_bg(layers)
    for i in range(4):
        add_date(layers, i)
    return layers


# ---------------------------------------------------------------------------
# 09 — Punto che avanza
# ---------------------------------------------------------------------------
def moving_point():
    layers = []
    add_bg(layers)
    for i in range(4):
        add_date(layers, i)
    add_rail(layers)
    layers.append(color_layer(
        "point_tick", ACCENT_RGBA, 2, 18, RAIL_X[0] - 960, RAIL_Y - 540,
        [position_x([(0, 0), (48, 0), (60, 280), (120, 280),
                     (132, 560), (192, 560), (204, 840), (TOTAL - 1, 840)],
                    "in_out_cubic")],
    ))
    return layers


# ---------------------------------------------------------------------------
# 10 — Documentary Fade
# ---------------------------------------------------------------------------
def documentary_fade():
    layers = []
    add_bg(layers)
    for i in range(4):
        if i == 0:
            ys = [(0, 18), (14, 0), (TOTAL - 1, 0)]
        elif i == 3:
            ys = [(0, 18), (204, 18), (216, 0), (TOTAL - 1, 0)]
        else:
            ys = [(0, 18), (48 + (i - 1) * 72, 18), (60 + (i - 1) * 72, 0),
                  (TOTAL - 1, 0)]
        add_date(layers, i, extra_tracks=[position_y(ys, "out_cubic")])
    return layers


# ---------------------------------------------------------------------------
# 11 — Date Bridge
# ---------------------------------------------------------------------------
def date_bridge():
    layers = []
    add_bg(layers)
    layers.append(color_layer("bridge_line", RAIL, 840, 2, 0, 600 - 540))
    for i in range(4):
        add_date(layers, i, x=960, y=450, size=200, w=800, h=300)
        if i > 0:
            layers.append(text_layer(
                f"prev_{i}", DATES[i - 1][0], 560, 450, 500, 120,
                PF, 50, MUTED, [opacity(active_fades()[i], "in_out_cubic")],
            ))
        if i < 3:
            layers.append(text_layer(
                f"next_{i}", DATES[i + 1][0], 1360, 450, 500, 120,
                PF, 50, MUTED, [opacity(active_fades()[i], "in_out_cubic")],
            ))
    return layers


# ---------------------------------------------------------------------------
# 13 — Focus Shift
# ---------------------------------------------------------------------------
def focus_shift():
    layers = []
    add_bg(layers)
    for i in range(4):
        # All four dates stay visible; only the active one gains contrast and
        # scale. There is no giant date, no rail and no extra marker.
        op = [(0, .22), (48, .22), (60, .22), (132, .22), (204, .22),
              (TOTAL - 1, .22)]
        if i == 0:
            op = [(0, 1), (48, 1), (60, .22), (TOTAL - 1, .22)]
        elif i == 1:
            op = [(0, .22), (48, .22), (60, 1), (120, 1), (132, .22), (TOTAL - 1, .22)]
        elif i == 2:
            op = [(0, .22), (120, .22), (132, 1), (192, 1), (204, .22), (TOTAL - 1, .22)]
        else:
            op = [(0, .22), (192, .22), (204, 1), (TOTAL - 1, 1)]
        sc = [(0, .85), (48, .85), (60, .85), (TOTAL - 1, .85)]
        if i == 0:
            sc = [(0, 1.25), (48, 1.25), (60, .85), (TOTAL - 1, .85)]
        elif i == 1:
            sc = [(0, .85), (48, .85), (60, 1.25), (120, 1.25), (132, .85), (TOTAL - 1, .85)]
        elif i == 2:
            sc = [(0, .85), (120, .85), (132, 1.25), (192, 1.25), (204, .85), (TOTAL - 1, .85)]
        else:
            sc = [(0, .85), (192, .85), (204, 1.25), (TOTAL - 1, 1.25)]
        layers.append(text_layer(
            f"focus_date_{i}", DATES[i][0], RAIL_X[i], 470, 500, 160,
            PF, 72, INK, [opacity(op, "in_out_cubic"), scale(sc, "in_out_cubic")],
        ))
    return layers



# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
PRESETS = [
    ("01_timeline_progress", "Timeline progressiva",
     "Linea sottile che si estende e accende le date una alla volta.",
     timeline_progress, True),
    ("02_year_morph", "Year Morph",
     "Cambiano solo le cifre necessarie; 19 resta fermo fino al 2026.",
     year_morph, True),
    ("03_vertical_timeline", "Timeline verticale",
     "Asse verticale a sinistra, data grande a destra, scorrimento verso l'alto.",
     vertical_timeline, True),
    ("04_animated_underline", "Sottolineatura animata",
     "Data fissa e linea tracciata da sinistra a destra.",
     animated_underline, True),
    ("05_calendar_flip", "Calendario essenziale",
     "Quattro ruote a scomparsa: le cifre cambiano come un calendario a palette.",
     calendar_flip, True),
    ("06_date_stack", "Date Stack",
     "Le quattro date restano in colonna; quella attiva passa in grande a destra.",
     date_stack, True),
    ("07_split_date", "Split Date",
     "Secolo e anno separati che si aprono e si richiudono a ogni data.",
     split_date, True),
    ("08_crossfade", "Crossfade cronologico",
     "Dissolvenza pura, stessa posizione e stesso allineamento.",
     crossfade, True),
    ("09_moving_point", "Punto che avanza",
     "Un segno sottile percorre il rail e fa comparire la data.",
     moving_point, True),
    ("10_documentary_fade", "Documentary Fade",
     "Ingresso in dissolvenza con un micro-movimento verso l'alto.",
     documentary_fade, True),
    ("11_date_bridge", "Date Bridge",
     "Data attiva al centro, date adiacenti ai lati e una linea che le collega.",
     date_bridge, True),
    ("12_rolling_year", "Rolling Year",
     "Contatore meccanico pulito: le ultime due cifre scorrono nel loro slot.",
     None, False),
    ("13_focus_shift", "Focus Shift",
     "Tutte le date visibili; solo quella attiva è luminosa e leggermente più grande.",
     focus_shift, True),
]

EXISTING = {
    "slug": "12_rolling_year",
    "title": "Rolling Year",
    "description": "Contatore meccanico pulito: le ultime due cifre scorrono nel loro slot.",
    "plan": "golden_plans/date_odometer_4dates/odometer_4dates.plan.json",
    "video": "renders/date_odometer_4dates/odometer_4dates.mp4",
    "fps": 30,
    "frames": 320,
    "duration_ms": 10667,
    "status": "planned",
}


def build_plan(slug, layers):
    return {
        "schema": "chronon.render-plan.v3",
        "version": 3,
        "job_id": f"date_animation_{slug}",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "fps_num": FPS,
            "fps_den": 1,
            "duration_frames": TOTAL,
        },
        "layers": layers,
        "output": {
            "path": f"{slug}.mp4",
            "format": "mp4",
            "codec": "h264",
            "crf": 14,
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    catalog = []
    for slug, title, description, builder, generated in PRESETS:
        if not generated:
            entry = dict(EXISTING)
            entry["title"] = title
            entry["description"] = description
            catalog.append(entry)
            continue
        plan = build_plan(slug, builder())
        plan_path = OUT / slug / f"{slug}.plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        entry = {
            "slug": slug,
            "title": title,
            "description": description,
            "plan": str(plan_path.relative_to(ROOT)),
            "video": f"renders/date_animation_catalog/{slug}.mp4",
            "fps": FPS,
            "frames": TOTAL,
            "duration_ms": round(TOTAL / FPS * 1000),
            "layers": len(plan["layers"]),
            "status": "planned",
        }
        catalog.append(entry)
        print(f"{slug:24s} layers={len(plan['layers']):3d}  {plan_path}")

    catalog.sort(key=lambda x: x["slug"])
    (OUT / "catalog.json").write_text(
        json.dumps({"dates": [d for d, _ in DATES], "fps": FPS,
                    "duration_ms": round(TOTAL / FPS * 1000),
                    "presets": catalog}, indent=2, ensure_ascii=False) + "\n"
    )
    rows = ["# Date animation catalog", "",
            "Thirteen presets, same four dates and light Playfair editorial system.",
            "Generated plans are 1920×1080, 24 fps, 240 frames (10 s).",
            "Rolling Year is the 30 fps clean odometer; no preset shows text labels.", "",
            "| # | Preset | Motion | Plan |", "|---|---|---|---|"]
    for entry in catalog:
        rows.append(f"| {entry['slug'][:2]} | {entry['title']} | "
                    f"{entry['description']} | `{entry.get('plan', '—')}` |")
    (OUT / "CATALOG.md").write_text("\n".join(rows) + "\n")
    print(f"catalog: {OUT / 'catalog.json'}  presets={len(catalog)}")


if __name__ == "__main__":
    main()
