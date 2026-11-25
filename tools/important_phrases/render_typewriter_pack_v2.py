#!/usr/bin/env python3
"""render_typewriter_pack_v2.py — 14 animazioni Typewriter 2D + 14 Typewriter 3D.

Il pack v1 (emit_typewriter_pack_v1.cpp) copriva 8 ricette; qui la stessa
grammatica di typing viene portata a 28 ricette: quattordici **2D** (testo
frontale, caret e reveal per-glyph/word) e quattordici **3D** (layer `enable_3d` con
ingresso su rotation/position_z/scale e camera prospettica con samples per
frame). La regola d'accento sotto la frase non fa parte del pack 2D.

Ogni ricetta copre frasi lunghe o brevi: il corpo scende e la frase va a capo
finche' ogni riga entra nella safe area, quindi la stessa ricetta funziona per
due parole o per tre righe di copy. Canvas 1920x1080, 24 fps, 192 frame (8 s),
quindi sotto il limite di 10 secondi richiesto.

Il contratto e' quello verificato dal pack v1 e da render_typewriter_modern_v2:

- reveal = text animator con selector percentuale (unit glyph|word, shape
  square|smooth, order forward|reverse); la coda non ancora battuta resta
  nascosta da una property `opacity: 0`;
- caret = shape layer le cui track `position_x`/`position_y` inseguono il
  frontier frame per frame; le track di posizione delle shape sono additive
  rispetto alla position del layer, quindi vengono authorate come delta;
- 3D = layer testo con `enable_3d: true`, position world centre-relative e
  plan-level `camera` + `camera_samples` (il contratto V3 non accetta piu'
  `camera_animation`).

Uso:
  python3 tools/important_phrases/render_typewriter_pack_v2.py
  python3 tools/important_phrases/render_typewriter_pack_v2.py --render
  ... --only tw2d_04_impact_short --only tw3d_04_depth_push_long
  ... --out RenderingGen/Upload/typewriter_pack_2d3d_20261125

CHRONON_CLI (o --cli) punta al chronon3d_cli; senza --render il tool emette
solo i plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
DEFAULT_OUT = WORKSPACE / "RenderingGen/Upload/typewriter_pack_2d3d_20261125"

W, H = 1920, 1080
FPS = 24
DUR = 192            # 8 s: dentro il limite di 10 s
MAX_BLOCK_H = 800.0
FONT_DIR = "assets/fonts"
FONT_ROOT = WORKSPACE / "Chronon3d" / FONT_DIR

BG_CENTER = (W / 2.0, H / 2.0)


# ── modello ricetta ─────────────────────────────────────────────────────────

@dataclass
class Recipe:
    id: str
    family: str               # "2d" | "3d"
    fit: str                  # short | long
    phrase: str
    font: str                 # file dentro Chronon3d/assets/fonts
    size_hint: int
    max_width: float
    max_lines: int
    line_height: float
    ink: str = "#F2F5F8"
    glow: tuple[str, float, float] = ("#FFFFFF", 8.0, 0.18)   # color, radius, intensity
    bg: str = "#05070D"
    bar: str = ""             # legacy: la regola 2D non viene piu' disegnata
    caret: str = ""           # "" = nessun caret
    caret_w_em: float = 0.12
    caret_h_em: float = 0.88
    caret_y_em: float = 0.02
    unit: str = "glyph"       # glyph | word
    shape: str = "square"     # square | smooth | ramp_up
    order: str = "forward"    # forward | reverse
    frames_per_char: float = 1.4
    start_sec: float = 0.42
    type_budget: float = 0.58
    stagger: bool = False     # start keys a gradini (staccato)
    erase: bool = False
    enter: bool = False       # push d'ingresso del layer (2D)
    blink: bool = True
    soft_band: float = 0.0    # percentuale di coda sfumata (2D)
    # ── 3D ──
    enter3d: dict = field(default_factory=dict)   # property -> [(frame, value), ...]
    camera: str = "static"
    z_offsets: list[float] = field(default_factory=list)  # parallax per riga


# ── ricette 2D ──────────────────────────────────────────────────────────────

RECIPES_2D = [
    Recipe("tw2d_01_mono_caret_short", "2d", "short", "OGNI DETTAGLIO CONTA",
           "DejaVuSansMono-Bold.ttf", 132, 1500, 1, 1.16,
           bg="#05070D", bar="#FFB454", caret="#FFB454",
           caret_w_em=0.62, caret_h_em=0.10, caret_y_em=0.50,
           frames_per_char=1.6, start_sec=0.42, type_budget=0.55),
    Recipe("tw2d_02_mono_long_wrap", "2d", "long",
           "NON È IL COLPO A DECIDERE LA PARTITA, MA IL MODO IN CUI SCEGLI DI RACCONTARLO.",
           "DejaVuSansMono-Bold.ttf", 88, 1560, 3, 1.24,
           ink="#E8EEF4", glow=("#AFC8FF", 6.0, 0.16), bg="#05070D",
           bar="#FFB454", caret="#FFB454",
           caret_w_em=0.10, caret_h_em=0.92, caret_y_em=0.02,
           frames_per_char=1.35, start_sec=0.42, type_budget=0.60),
    Recipe("tw2d_03_soft_frontier_long", "2d", "long",
           "Il silenzio, prima della verità, è la parte più difficile da montare.",
           "Inter-Medium.ttf", 96, 1520, 3, 1.28,
           ink="#F4F6FA", glow=("#8FB6FF", 10.0, 0.22), bg="#06080F",
           bar="#8FB6FF", unit="glyph", shape="square", soft_band=14.0,
           frames_per_char=1.5, start_sec=0.40, type_budget=0.62, blink=False),
    Recipe("tw2d_04_impact_short", "2d", "short", "TUTTO CAMBIA IN UN FRAME",
           "Inter-Black.ttf", 196, 1640, 1, 1.10,
           ink="#FFFFFF", glow=("#FF7A3D", 22.0, 0.55), bg="#08060A",
           bar="#FF7A3D", caret="#FF7A3D",
           caret_w_em=0.14, caret_h_em=0.86, caret_y_em=0.02,
           frames_per_char=1.9, start_sec=0.30, type_budget=0.50, enter=True),
    Recipe("tw2d_05_type_erase_short", "2d", "short", "ORA LO VEDI.",
           "Space-Grotesk.ttf", 168, 1360, 1, 1.12,
           ink="#F7F8FA", glow=("#9BE7FF", 16.0, 0.40), bg="#05070C",
           bar="#9BE7FF", caret="#9BE7FF",
           caret_w_em=0.12, caret_h_em=0.88, caret_y_em=0.02,
           frames_per_char=3.4, start_sec=0.14, type_budget=0.34,
           erase=True, blink=False),
    Recipe("tw2d_06_terminal_long", "2d", "long",
           "SIGNAL LOCKED // ARCHIVIO 1987 // LA TRASMISSIONE È IN CORSO",
           "DejaVuSansMono-Bold.ttf", 84, 1560, 3, 1.26,
           ink="#7CF0C9", glow=("#7CF0C9", 14.0, 0.35), bg="#03070A",
           bar="#7CF0C9", caret="#7CF0C9",
           caret_w_em=0.52, caret_h_em=0.92, caret_y_em=0.02,
           frames_per_char=1.25, start_sec=0.46, type_budget=0.58),
    Recipe("tw2d_07_editorial_caret_long", "2d", "long",
           "La verità è un dettaglio che nessuno aveva notato.",
           "PlayfairDisplay-Bold.ttf", 104, 1500, 3, 1.22,
           ink="#F5EFE3", glow=("#FFD9A0", 8.0, 0.20), bg="#0A0807",
           bar="#C9A227", caret="#FFB454",
           caret_w_em=0.60, caret_h_em=0.08, caret_y_em=0.50,
           frames_per_char=1.3, start_sec=0.42, type_budget=0.58),
    Recipe("tw2d_08_word_burst_short", "2d", "short", "NESSUN DETTAGLIO È CASUALE",
           "Inter-ExtraBold.ttf", 150, 1580, 1, 1.14,
           ink="#FFFFFF", glow=("#FFB454", 18.0, 0.48), bg="#07070B",
           bar="#FFB454", caret="#FFB454",
           caret_w_em=0.18, caret_h_em=0.80, caret_y_em=0.02,
           unit="word", frames_per_char=0.85, start_sec=0.36, type_budget=0.52),
    Recipe("tw2d_09_geo_block_short", "2d", "short", "IL CONFINE SI SPOSTA",
           "Geist-Bold.ttf", 150, 1520, 1, 1.14,
           ink="#EAF3E6", glow=("#B8F135", 16.0, 0.34), bg="#040806",
           bar="#B8F135", caret="#B8F135",
           caret_w_em=0.58, caret_h_em=0.12, caret_y_em=0.52,
           shape="ramp_up", frames_per_char=1.7, start_sec=0.38, type_budget=0.52),
    Recipe("tw2d_10_serif_rule_long", "2d", "long",
           "La memoria è una stanza che non smette di allargarsi.",
           "DM-Serif-Display.ttf", 98, 1500, 2, 1.24,
           ink="#F7F1E6", glow=("#E8C58A", 8.0, 0.18), bg="#0B0908",
           bar="#E8C58A", blink=False,
           frames_per_char=1.45, start_sec=0.44, type_budget=0.56),
    Recipe("tw2d_11_reverse_wipe_short", "2d", "short", "TORNA INDIETRO",
           "DejaVuSansMono-Bold.ttf", 154, 1440, 1, 1.14,
           ink="#DDEBFF", glow=("#6EA8FF", 14.0, 0.30), bg="#04060C",
           bar="#6EA8FF", caret="#6EA8FF",
           caret_w_em=0.46, caret_h_em=0.90, caret_y_em=0.02,
           order="reverse", frames_per_char=2.1, start_sec=0.34, type_budget=0.50),
    Recipe("tw2d_12_breath_long", "2d", "long",
           "Ogni parola arriva da sola, poi resta.",
           "Inter-Light.ttf", 112, 1480, 2, 1.26,
           ink="#F1F5F9", glow=("#93C5FD", 12.0, 0.26), bg="#060A11",
           shape="smooth", soft_band=10.0,
           frames_per_char=1.6, start_sec=0.40, type_budget=0.58, blink=False),
    Recipe("tw2d_13_underscore_short", "2d", "short", "PIÙ VICINO DI COSÌ",
           "Figtree-ExtraBold.ttf", 158, 1540, 1, 1.12,
           ink="#FFFFFF", glow=("#FF6E9E", 18.0, 0.40), bg="#08060A",
           bar="#FF6E9E", caret="#FF6E9E",
           caret_w_em=0.80, caret_h_em=0.09, caret_y_em=0.50,
           frames_per_char=1.5, start_sec=0.36, type_budget=0.54),
    Recipe("tw2d_14_slow_hold_long", "2d", "long",
           "Il dettaglio che nessuno vede è quello che cambia la storia.",
           "PlayfairDisplay-Italic.ttf", 100, 1500, 2, 1.24,
           ink="#F6EFE6", glow=("#FFD9A0", 9.0, 0.20), bg="#0A0807",
           caret="#FFB454", caret_w_em=0.10, caret_h_em=0.90, caret_y_em=0.02,
           frames_per_char=2.4, start_sec=0.28, type_budget=0.52),
]

# ── ricette 3D ──────────────────────────────────────────────────────────────

RECIPES_3D = [
    Recipe("tw3d_01_yaw_flip_short", "3d", "short", "TURN INTO THE LIGHT",
           "Inter-ExtraBold.ttf", 150, 1200, 1, 1.14,
           ink="#F3F7FF", glow=("#7DB4FF", 16.0, 0.34), bg="#05070D",
           caret="#FFB454", caret_w_em=0.12, caret_h_em=0.88,
           frames_per_char=1.5, start_sec=0.36, type_budget=0.52,
           enter3d={"rotation_y": [(0, -36.0), (52, 0.0)],
                    "position_z": [(0, 110.0), (52, 0.0)]},
           camera="static"),
    Recipe("tw3d_02_pitch_lift_short", "3d", "short", "LIFT WITH A TILT UP",
           "Montserrat-ExtraBold.ttf", 146, 1320, 1, 1.14,
           ink="#FFFFFF", glow=("#FFB454", 18.0, 0.40), bg="#08070C",
           caret="#FFB454", caret_w_em=0.12, caret_h_em=0.86,
           frames_per_char=1.6, start_sec=0.34, type_budget=0.52,
           enter3d={"rotation_x": [(0, 24.0), (50, 0.0)],
                    "position_y": [(0, -46.0), (50, 0.0)]},
           camera="static"),
    Recipe("tw3d_03_roll_settle_short", "3d", "short", "ROLL IN AND SETTLE",
           "DM-Sans.ttf", 148, 1320, 1, 1.12,
           ink="#F7F8FA", glow=("#9BE7FF", 14.0, 0.32), bg="#05080C",
           caret="#9BE7FF", caret_w_em=0.12, caret_h_em=0.86,
           frames_per_char=1.5, start_sec=0.32, type_budget=0.50,
           enter3d={"rotation_z": [(0, -10.0), (48, 0.0)],
                    "scale": [(0, 0.90), (48, 1.0)]},
           camera="static"),
    Recipe("tw3d_04_depth_push_long", "3d", "long",
           "Il futuro arriva prima di quanto siamo pronti a nominarlo.",
           "Inter-Bold.ttf", 90, 1320, 2, 1.24,
           ink="#EDF4FF", glow=("#6EA8FF", 12.0, 0.28), bg="#04060C",
           caret="#6EA8FF", caret_w_em=0.11, caret_h_em=0.90,
           frames_per_char=1.5, start_sec=0.38, type_budget=0.58,
           enter3d={"position_z": [(0, 200.0), (56, 0.0)],
                    "rotation_x": [(0, 7.0), (56, 0.0)]},
           camera="slow_push"),
    Recipe("tw3d_05_z_bounce_short", "3d", "short", "ORA O MAI PIÙ",
           "Inter-Black.ttf", 190, 1300, 1, 1.10,
           ink="#FFFFFF", glow=("#FF3158", 22.0, 0.52), bg="#0A0508",
           caret="#FF3158", caret_w_em=0.14, caret_h_em=0.84,
           frames_per_char=1.9, start_sec=0.28, type_budget=0.46,
           enter3d={"position_z": [(0, 330.0), (30, -26.0), (48, 0.0)],
                    "scale": [(0, 0.94), (30, 1.04), (48, 1.0)]},
           camera="static"),
    Recipe("tw3d_06_card_swing_long", "3d", "long",
           "La verità non ha fretta: aspetta il suo primo piano.",
           "PlayfairDisplay-Bold.ttf", 64, 1200, 2, 1.24,
           ink="#F5EFE3", glow=("#E8C58A", 10.0, 0.22), bg="#0A0806",
           caret="#C9A227", caret_w_em=0.11, caret_h_em=0.88,
           frames_per_char=0.5, start_sec=0.42, type_budget=0.30,
           enter3d={},
           camera="orbit_soft"),
    Recipe("tw3d_07_dolly_settle_long", "3d", "long",
           "Ogni storia comincia da un dettaglio che nessuno aveva notato.",
           "Inter-Medium.ttf", 96, 1320, 3, 1.26,
           ink="#F4F6FA", glow=("#8FB6FF", 10.0, 0.24), bg="#06080F",
           caret="#8FB6FF", caret_w_em=0.11, caret_h_em=0.88,
           frames_per_char=1.4, start_sec=0.40, type_budget=0.60,
           enter3d={"position_z": [(0, 240.0), (54, 0.0)],
                    "position_y": [(0, -34.0), (54, 0.0)]},
           camera="dolly_in"),
    Recipe("tw3d_08_orbit_short", "3d", "short", "ORBIT FINDS THE ANGLE",
           "Space-Grotesk.ttf", 132, 1040, 1, 1.12,
           ink="#EAF6FF", glow=("#4DE3FF", 18.0, 0.38), bg="#04080C",
           caret="#4DE3FF", caret_w_em=0.12, caret_h_em=0.86,
           frames_per_char=1.5, start_sec=0.34, type_budget=0.50,
           enter3d={"rotation_y": [(0, -16.0), (24, 5.0), (52, 0.0)]},
           camera="orbit_soft"),
    Recipe("tw3d_10_hero_pull_short", "3d", "short", "HERO PULL",
           "Oswald-Bold.ttf", 220, 1300, 1, 1.10,
           ink="#FFFFFF", glow=("#FFC65C", 20.0, 0.44), bg="#0A0705",
           caret="#FFC65C", caret_w_em=0.14, caret_h_em=0.82,
           frames_per_char=2.6, start_sec=0.30, type_budget=0.44,
           enter3d={"scale": [(0, 1.18), (46, 1.0)],
                    "position_z": [(0, -130.0), (46, 0.0)]},
           camera="pull_back"),
    Recipe("tw3d_11_spin_in_long", "3d", "long",
           "CENTO FRAME PER CAMBIARE IDEA AL MONDO.",
           "DejaVuSansMono-Bold.ttf", 90, 1320, 2, 1.24,
           ink="#D7FFE9", glow=("#7CF0C9", 12.0, 0.30), bg="#03070A",
           caret="#7CF0C9", caret_w_em=0.50, caret_h_em=0.90,
           frames_per_char=1.5, start_sec=0.34, type_budget=0.54,
           enter3d={"rotation_y": [(0, -14.0), (54, 0.0)],
                    "position_z": [(0, 60.0), (54, 0.0)]},
           camera="static"),
    Recipe("tw3d_12_parallax_split_short", "3d", "short", "DUE PIANI, UNA STORIA",
           "Figtree-ExtraBold.ttf", 128, 900, 2, 1.18,
           ink="#FFFFFF", glow=("#FF6E9E", 14.0, 0.32), bg="#08060A",
           caret="", frames_per_char=1.2, start_sec=0.32, type_budget=0.52,
           enter3d={"rotation_y": [(0, -18.0), (48, 0.0)]},
           camera="drift_up", z_offsets=[-60.0, 60.0]),
    Recipe("tw3d_13_camera_rise_long", "3d", "long",
           "La città si sveglia mentre la voce finisce la frase.",
           "PlayfairDisplay.ttf", 100, 1320, 2, 1.24,
           ink="#F6EFE6", glow=("#FFD9A0", 9.0, 0.20), bg="#0B0908",
           caret="#E8C58A", caret_w_em=0.11, caret_h_em=0.88,
           frames_per_char=1.45, start_sec=0.40, type_budget=0.58,
           enter3d={"rotation_x": [(0, 9.0), (52, 0.0)],
                    "position_y": [(0, 26.0), (52, 0.0)]},
           camera="rise_tilt"),
    Recipe("tw3d_14_camera_whip_short", "3d", "short", "SEGUE IL MOVIMENTO",
           "Montserrat-Bold.ttf", 140, 1040, 1, 1.12,
           ink="#FFFFFF", glow=("#FF7A3D", 18.0, 0.40), bg="#08060A",
           caret="#FF7A3D", caret_w_em=0.13, caret_h_em=0.86,
           frames_per_char=1.7, start_sec=0.30, type_budget=0.50,
           enter3d={"rotation_y": [(0, -14.0), (44, 0.0)]},
           camera="whip_pan"),
    Recipe("tw3d_15_iso_slide_long", "3d", "long",
           "Tutto si sposta di lato, anche ciò che sembra fermo.",
           "Inter-SemiBold.ttf", 100, 1320, 2, 1.24,
           ink="#F3F7FF", glow=("#7DB4FF", 11.0, 0.26), bg="#05070D",
           caret="#7DB4FF", caret_w_em=0.11, caret_h_em=0.88,
           frames_per_char=1.5, start_sec=0.38, type_budget=0.58,
           enter3d={"rotation_y": [(0, 26.0), (50, 0.0)],
                    "rotation_x": [(0, 11.0), (50, 0.0)],
                    "position_x": [(0, 64.0), (50, 0.0)]},
           camera="iso_settle"),
]

RECIPES = RECIPES_2D + RECIPES_3D


# ── colori / keyframe ───────────────────────────────────────────────────────

def hex_rgba(value: str) -> list[float]:
    raw = value.lstrip("#")
    return [int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def keys(pairs) -> list[dict]:
    """Keyframes ordinate, clampate al clip, con un solo valore per frame."""
    merged: dict[int, float] = {}
    for frame, value in pairs:
        merged[max(0, min(DUR, int(round(frame))))] = float(value)
    return [{"frame": f, "value": merged[f]} for f in sorted(merged)]


def track(prop: str, pairs, easing: str = "linear") -> dict:
    return {"property": prop, "easing": easing, "keyframes": keys(pairs)}


# ── misura e impaginazione ──────────────────────────────────────────────────

def font_path(name: str) -> Path:
    path = FONT_ROOT / name
    if not path.is_file():
        raise SystemExit(f"font mancante: {path}")
    return path


def measure(text: str, font: str, size: int) -> tuple[float, list[float]]:
    from PIL import ImageFont
    f = ImageFont.truetype(str(font_path(font)), int(size))
    starts, x = [], 0.0
    for ch in text:
        starts.append(x)
        x += f.getlength(ch)
    starts.append(x)
    return x, starts


def wrap(text: str, font: str, size: int, max_width: float):
    from PIL import ImageFont
    f = ImageFont.truetype(str(font_path(font)), int(size))
    space = f.getlength(" ")
    words = text.split(" ")
    lines: list[list[tuple[str, int]]] = [[]]   # (word, codepoint offset)
    widths = [0.0]
    cursor = 0
    offsets = []
    for word in words:
        offsets.append(cursor)
        cursor += len(word) + 1
    for word, off in zip(words, offsets):
        w = f.getlength(word)
        if not lines[-1]:
            lines[-1].append((word, off))
            widths[-1] = w
        elif widths[-1] + space + w <= max_width:
            lines[-1].append((word, off))
            widths[-1] += space + w
        else:
            lines.append([(word, off)])
            widths.append(w)
    out = []
    for line in lines:
        text_line = " ".join(w for w, _ in line)
        start = line[0][1]
        out.append((text_line, start, start + len(text_line)))
    return out


def fit_size(r: Recipe) -> int:
    for size in range(r.size_hint, 39, -2):
        lines = wrap(r.phrase, r.font, size, r.max_width)
        if len(lines) <= r.max_lines and len(lines) * size * r.line_height <= MAX_BLOCK_H:
            return size
    return 40


def laid_out(r: Recipe):
    size = fit_size(r)
    lines = wrap(r.phrase, r.font, size, r.max_width)
    line_height = size * r.line_height
    block_h = len(lines) * line_height
    top = (H - block_h) / 2.0 + line_height / 2.0
    laid = []
    for i, (text, start, end) in enumerate(lines):
        width, starts = measure(text, r.font, size)
        laid.append({
            "text": text,
            "start": start,
            "end": end,
            "width": width,
            "starts": starts,
            "left": (W - width) / 2.0,
            "y": top + i * line_height,
        })
    return size, laid


def typing_window(r: Recipe, chars: int) -> tuple[int, int]:
    start = int(round(r.start_sec * FPS))
    budget = int(round(r.type_budget * DUR))
    natural = int(round(chars * r.frames_per_char))
    span = max(8, min(natural, budget))
    return start, min(DUR - 6, start + span)


# ── plan 2D ─────────────────────────────────────────────────────────────────

def bg_layer(r: Recipe) -> dict:
    return {"id": "bg", "type": "shape", "size": [W, H],
            "position": list(BG_CENTER), "start_frame": 0, "duration_frames": DUR,
            "shape": {"type": "rect", "fill": hex_rgba(r.bg)}}


def shape_color(value: str, alpha: float = 1.0) -> list[float]:
    rgba = hex_rgba(value)
    rgba[3] = alpha
    return rgba


def caret_output(r: Recipe, laid, size: int, ts: int, te: int) -> list[dict]:
    """Caret: un campione per frame sul frontier della riga in battitura.

    Le track position_* delle shape sono additive rispetto alla position del
    layer, quindi i campioni diventano delta rispetto al primo punto.
    """
    caret_w = size * r.caret_w_em
    caret_h = size * r.caret_h_em
    total = max(1, len(r.phrase))
    erase_start = min(DUR - 24, te + 22)
    erase_end = DUR - 10
    xs, ys, ops = [], [], []
    for frame in range(0, DUR + 1):
        frac = (min(max(frame, ts), te) - ts) / max(1, te - ts)
        if r.erase and frame > erase_start:
            frac = 1.0 - (min(frame, erase_end) - erase_start) / max(1, erase_end - erase_start)
        target = frac * total
        line = laid[-1]
        for lm in laid:
            if target <= lm["end"] or lm is laid[-1]:
                line = lm
                span = max(1, lm["end"] - lm["start"])
                in_line = (target - lm["start"]) / span
                break
        else:  # pragma: no cover - il for copre sempre l'ultima riga
            in_line = 1.0
        in_line = min(1.0, max(0.0, in_line))
        length = len(line["text"])
        edge = length - int(round(in_line * length)) if r.order == "reverse" \
            else int(math.floor(in_line * length))
        edge = min(length, max(0, edge))
        x = line["left"] + line["starts"][edge] + caret_w * 0.5
        y = line["y"] + size * r.caret_y_em
        xs.append((frame, x - W / 2.0))
        ys.append((frame, y - H / 2.0))
        ops.append((frame, 1.0))

    still_from = erase_end if r.erase else te
    if r.blink:
        on = True
        for frame in range(still_from, DUR + 1, 8):
            for i, (f, _) in enumerate(ops):
                if f >= frame:
                    ops[i] = (f, 1.0 if on else 0.0)
            on = not on

    x0 = xs[0][1]
    y0 = ys[0][1]
    xs = [(f, v - x0) for f, v in xs]
    ys = [(f, v - y0) for f, v in ys]

    caret = {"id": "caret", "type": "shape", "size": [caret_w, caret_h],
             "position": [W / 2.0 + x0, H / 2.0 + y0],
             "start_frame": 0, "duration_frames": DUR,
             "shape": {"type": "rect", "fill": shape_color(r.caret)},
             "animation": {"tracks": [track("position_x", xs),
                                      track("position_y", ys),
                                      track("opacity", ops)]}}
    if not r.erase and not r.blink:
        caret["animation"]["tracks"][-1] = track(
            "opacity", [(0, 0.0), (ts, 0.0), (ts + 10, 1.0), (DUR, 1.0)])
    return [caret]


def build_2d(r: Recipe) -> dict:
    size, laid = laid_out(r)
    ts, te = typing_window(r, len(r.phrase))
    layers = [bg_layer(r)]

    total = max(1, len(r.phrase))
    for i, lm in enumerate(laid):
        share_before = lm["start"] / total
        share_after = lm["end"] / total
        line_ts = ts + int(round((te - ts) * share_before))
        line_te = max(line_ts + 2, ts + int(round((te - ts) * share_after)))

        if r.stagger:
            # Staccato: la battitura avanza a gradini invece che a velocita'
            # costante. Il frontier resta nascosto fra un gradino e l'altro.
            steps, cursor, key = 4, 0.0, [(0, 0.0), (line_ts, 0.0)]
            while cursor < 1.0:
                cursor = min(1.0, cursor + 0.18)
                key.append((line_ts + int((line_te - line_ts) * cursor), 100.0 * cursor))
                cursor = min(1.0, cursor + 0.06)
            start_keys = key[:2] + [(f, v) for f, v in key[2:]]
        else:
            start_keys = [(0, 0.0), (line_ts, 0.0), (line_te, 100.0), (DUR, 100.0)]

        if r.erase and lm is laid[-1]:
            start_keys = [(0, 0.0), (line_ts, 0.0), (line_te, 100.0),
                          (min(DUR - 24, te + 22), 100.0), (DUR - 10, 0.0), (DUR, 0.0)]

        animators = [{
            "id": "typewriter_window",
            "selectors": [{
                "unit": r.unit, "shape": r.shape, "order": r.order,
                "combine": "replace", "exclude_spaces": False,
                "start": {"easing": "linear", "keyframes": keys(start_keys)},
                "end": {"easing": "linear",
                        "keyframes": keys([(0, 100.0), (DUR, 100.0)])},
            }],
            "properties": [track("opacity", [(0, 0.0), (DUR, 0.0)])],
        }]
        if r.soft_band > 0.0 and not r.erase:
            low = max(0.0, 100.0 - r.soft_band)
            animators.append({
                "id": "frontier_blur",
                "selectors": [{
                    "unit": r.unit, "shape": "smooth", "order": r.order,
                    "combine": "replace", "exclude_spaces": False,
                    "start": {"easing": "linear",
                              "keyframes": keys([(0, 0.0), (line_ts, 0.0), (line_te, low), (DUR, low)])},
                    "end": {"easing": "linear",
                            "keyframes": keys([(0, 0.0), (line_ts, 0.0), (line_te, 100.0), (DUR, 100.0)])},
                }],
                "properties": [track("blur", [(0, 12.0), (DUR, 12.0)])],
            })

        layer = {
            "id": f"line{i}", "type": "text", "text": lm["text"],
            "size": [r.max_width, size * 1.45],
            "position": [W / 2.0, lm["y"]],
            "start_frame": 0, "duration_frames": DUR,
            "style": {"font": f"{FONT_DIR}/{r.font}", "font_size": size,
                      "fill": r.ink,
                      "glow": {"radius": r.glow[1], "intensity": r.glow[2],
                               "color": r.glow[0]}},
            "text_animators": animators,
        }
        if r.enter and i == 0:
            layer["animation"] = {"tracks": [
                track("position_y", [(0, 26.0), (10, 0.0)], "out_cubic"),
                track("opacity", [(0, 0.0), (8, 1.0)]),
                track("scale", [(0, 0.94), (12, 1.0)], "out_cubic"),
            ]}
        layers.append(layer)

    if r.caret:
        layers.extend(caret_output(r, laid, size, ts, te))

    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": r.id,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": DUR},
            "layers": layers,
            "output": {"path": f"{r.id}.mp4", "format": "mp4", "codec": "h264"}}


# ── plan 3D ─────────────────────────────────────────────────────────────────

def smooth(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)


def camera_move(name: str) -> Callable[[int], tuple]:
    """Restituisce (px, py, pz, rx, ry) per frame. z negativo = davanti.

    Tutte le curve partono e finiscono in posa neutra (0,0,-1000,0,0) tranne
    quelle che spingono davanti: la fine non e' mai un taglio.
    """
    t = lambda f: smooth(f / (DUR - 1))
    e = lambda f: smooth(f / 72.0)   # uscita entro il primo terzo

    moves = {
        "static": lambda f: (0.0, 0.0, -1000.0, 0.0, 0.0),
        "slow_push": lambda f: (0.0, 0.0, -1000.0 + 70.0 * t(f), 0.0, 0.0),
        "dolly_in": lambda f: (0.0, 0.0, -1080.0 + 110.0 * t(f), 0.0, 0.0),
        "pull_back": lambda f: (0.0, 0.0, -920.0 - 80.0 * t(f), 0.0, 0.0),
        "orbit": lambda f: (-60.0 * (1.0 - t(f)), 0.0, -1000.0, 0.0, -7.0 * (1.0 - t(f))),
        "orbit_left": lambda f: (70.0 * (1.0 - t(f)), 0.0, -1000.0,
                                 0.0, 6.0 * (1.0 - t(f))),
        # Stessa orbita con escursione ridotta: su una riga larga il pan
        # iniziale spingeva il bordo destro oltre la safe area.
        "orbit_soft": lambda f: (-34.0 * (1.0 - t(f)), 0.0, -1000.0,
                                 0.0, -4.0 * (1.0 - t(f))),
        "rise_tilt": lambda f: (0.0, -50.0 * (1.0 - t(f)), -1000.0,
                                5.0 * (1.0 - t(f)), 0.0),
        "tilt_down": lambda f: (0.0, 0.0, -1000.0, -6.0 * (1.0 - t(f)), 0.0),
        "whip_pan": lambda f: (-50.0 * (1.0 - e(f)), 0.0, -1000.0,
                              0.0, -6.0 * (1.0 - e(f))),
        "drift_up": lambda f: (0.0, 60.0 * (1.0 - t(f)), -1000.0, 0.0, 0.0),
        "iso_settle": lambda f: (40.0 * (1.0 - e(f)), -24.0 * (1.0 - e(f)),
                                 -1000.0 + 40.0 * t(f),
                                 3.0 * (1.0 - e(f)), 5.0 * (1.0 - e(f))),
    }
    if name not in moves:
        raise SystemExit(f"camera move sconosciuta: {name}")
    return moves[name]


def camera_for(name: str) -> tuple[dict, list[dict]]:
    move = camera_move(name)
    samples = []
    base = None
    for frame in range(DUR):
        px, py, pz, rx, ry = move(frame)
        cam = {"type": "perspective", "position": [px, py, pz],
               "rotation_deg": [rx, ry, 0.0], "fov_deg": 45, "near": 1,
               "far": 10000, "zoom": 1, "sensor_width_mm": 36,
               "lens_shift": [0, 0]}
        samples.append({"frame": frame, "camera": cam})
        if base is None:
            base = cam
    return base, samples


def build_3d(r: Recipe) -> dict:
    size, laid = laid_out(r)
    ts, te = typing_window(r, len(r.phrase))
    total = max(1, len(r.phrase))
    layers = [bg_layer(r)]

    enter_tracks = []
    for prop, pairs in r.enter3d.items():
        enter_tracks.append(track(prop, pairs, "in_out_cubic"))
    enter_tracks.append(track("opacity", [(0, 0.0), (16, 1.0), (DUR, 1.0)]))

    for i, lm in enumerate(laid):
        share_before = lm["start"] / total
        share_after = lm["end"] / total
        line_ts = ts + int(round((te - ts) * share_before))
        line_te = max(line_ts + 2, ts + int(round((te - ts) * share_after)))
        z = r.z_offsets[i] if i < len(r.z_offsets) else 0.0
        world_y = H / 2.0 - lm["y"]

        animators = [{
            "id": "typewriter_window",
            "selectors": [{
                "unit": r.unit, "shape": r.shape, "order": r.order,
                "combine": "replace", "exclude_spaces": False,
                "start": {"easing": "linear",
                          "keyframes": keys([(0, 0.0), (line_ts, 0.0), (line_te, 100.0), (DUR, 100.0)])},
                "end": {"easing": "linear",
                        "keyframes": keys([(0, 100.0), (DUR, 100.0)])},
            }],
            "properties": [track("opacity", [(0, 0.0), (DUR, 0.0)])],
        }]

        tracks = [dict(t) for t in enter_tracks]
        if z:
            # parallax: la riga entra da una profondita' diversa, quindi la
            # position_z dell'ingresso parte dal proprio offset e ci torna.
            for t in tracks:
                if t["property"] == "position_z":
                    t["keyframes"] = keys([(k["frame"], k["value"] + z) for k in t["keyframes"]])

        layer = {
            "id": f"line{i}", "type": "text", "text": lm["text"],
            "size": [r.max_width, size * 1.55],
            "position": [0.0, world_y, z],
            "start_frame": 0, "duration_frames": DUR,
            "enable_3d": True,
            "style": {"font": f"{FONT_DIR}/{r.font}", "font_size": size,
                      "fill": r.ink,
                      "glow": {"radius": r.glow[1], "intensity": r.glow[2],
                               "color": r.glow[0]}},
            "text_animators": animators,
            "animation": {"tracks": tracks},
        }
        layers.append(layer)

    camera, samples = camera_for(r.camera)
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": r.id,
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                       "duration_frames": DUR},
            "layers": layers,
            "camera": camera,
            "camera_samples": samples,
            "output": {"path": f"{r.id}.mp4", "format": "mp4", "codec": "h264"}}


def build_plan(r: Recipe) -> dict:
    return build_3d(r) if r.family == "3d" else build_2d(r)


# ── rendering e verifica ────────────────────────────────────────────────────

def resolve_cli(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("CHRONON_CLI"):
        candidates.append(Path(os.environ["CHRONON_CLI"]))
    candidates += [Path("/usr/local/bin/chronon3d_cli"),
                   Path("/opt/chronon3d/bin/chronon3d_cli")]
    for base in (WORKSPACE / "Chronon3d/build/chronon", ROOT / "../Chronon3d/build/chronon"):
        if base.is_dir():
            candidates += sorted(base.glob("*/apps/chronon3d_cli/chronon3d_cli"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise SystemExit("chronon3d_cli non trovato: passa --cli o CHRONON_CLI")


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=codec_name,width,height,nb_read_frames",
         "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    stream = json.loads(out)["streams"][0]
    return {"codec": stream["codec_name"], "width": int(stream["width"]),
            "height": int(stream["height"]), "frames": int(stream["nb_read_frames"])}


def plan_digest(plan: Path) -> str:
    return hashlib.sha256(plan.read_bytes()).hexdigest()


def verify_video(video: Path) -> dict:
    info = probe(video)
    if info["codec"] != "h264":
        raise SystemExit(f"{video.name}: codec {info['codec']}, atteso h264")
    if (info["width"], info["height"]) != (W, H):
        raise SystemExit(f"{video.name}: {info['width']}x{info['height']}, atteso {W}x{H}")
    if info["frames"] != DUR:
        raise SystemExit(f"{video.name}: {info['frames']} frame, attesi {DUR}")

    # 6 fps (un frame ogni 4) a 480x270: i difetti di safe area dei 3D durano
    # pochi frame e i campioni radi (0, 20, 46, ...) non li vedevano. Il fondo
    # e' scuro e il testo chiaro, quindi la soglia isola il soggetto. `fps`
    # evita l'errore di escaping di `select=not(mod(n,4))`, che restituiva
    # tutti i frame e faceva sembrare il frame 19 un frame 76.
    from PIL import Image
    fw, fh, step = 480, 270, 4
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-an", "-sn",
         "-vf", "fps=6,scale=480:270",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True, capture_output=True).stdout
    count = len(raw) // (fw * fh)
    boxes = []
    for i in range(count):
        im = Image.frombytes("L", (fw, fh), raw[i * fw * fh:(i + 1) * fw * fh])
        px = im.load()
        xs, ys = [], []
        for y in range(0, fh, 2):
            for x in range(0, fw, 2):
                if px[x, y] > 92:
                    xs.append(x); ys.append(y)
        if xs:
            boxes.append((i * step, min(xs) * 4, min(ys) * 4,
                          max(xs) * 4 + 3, max(ys) * 4 + 3))
    if not boxes:
        raise SystemExit(f"{video.name}: nessun frame con testo visibile")
    for frame, x0, y0, x1, y1 in boxes:
        if x0 < 40 or y0 < 40 or x1 > W - 40 or y1 > H - 40:
            raise SystemExit(f"{video.name}: testo fuori safe area al frame {frame} (bbox {x0, y0, x1, y1})")
    if not any(x1 - x0 > 240 for _, x0, _, x1, _ in boxes):
        raise SystemExit(f"{video.name}: il testo non compare (bbox troppo stretta)")
    return {"frames": info["frames"], "visible_frames": len(boxes),
            "first_visible": boxes[0][0], "bbox": list(boxes[-1][1:])}


def render_one(cli: Path, plan: Path, video: Path) -> dict:
    log = video.with_suffix(".log")
    video.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as handle:
        subprocess.run(
            [str(cli), "validate", "--plan", str(plan),
             "--assets-root", str(WORKSPACE / "Chronon3d")],
            check=True, stdout=handle, stderr=subprocess.STDOUT)
        started = time.time()
        subprocess.run(
            [str(cli), "render", "--plan", str(plan),
             "--assets-root", str(WORKSPACE / "Chronon3d"),
             "--backend", "vulkan", "--profile", "production",
             "--codec", "h264", "--fps", str(FPS),
             "--start-frame", "0", "--end-frame", str(DUR - 1),
             "-o", str(video)],
            check=True, stdout=handle, stderr=subprocess.STDOUT)
    # Il video e' valido solo per il plan che lo ha prodotto: senza questa
    # impronta un plan modificato veniva saltato e il clip restava vecchio.
    video.with_suffix(".plan.sha256").write_text(plan_digest(plan) + "\n")
    return {"seconds": round(time.time() - started, 1), **verify_video(video)}


def contact_sheet(video: Path, out: Path) -> None:
    frames = [8, 24, 48, 72, 120, 168]
    sel = "+".join(f"eq(n\\,{f})" for f in frames)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf",
         f"select={sel},scale=640:360,tile=3x2", "-frames:v", "1", str(out)],
        check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ── bundle ──────────────────────────────────────────────────────────────────

def write_bundle(out: Path, results: dict[str, dict]) -> None:
    clips = []
    for recipe in RECIPES:
        video = out / "videos" / f"{recipe.id}.mp4"
        plan = out / "plans" / f"{recipe.id}.plan.json"
        preview = out / "previews" / f"{recipe.id}.png"
        size, laid = laid_out(recipe)
        clips.append({
            "id": recipe.id,
            "family": recipe.family,
            "fit": recipe.fit,
            "phrase": recipe.phrase,
            "font": recipe.font,
            "font_size": size,
            "lines": len(laid),
            "unit": recipe.unit,
            "reveal_shape": recipe.shape,
            "order": recipe.order,
            "caret": recipe.caret or None,
            "erase": recipe.erase,
            "entrance_3d": bool(recipe.enter3d),
            "camera": recipe.camera if recipe.family == "3d" else None,
            "video": f"videos/{video.name}",
            "video_bytes": video.stat().st_size,
            "video_sha256": sha256(video),
            "plan": f"plans/{plan.name}",
            "plan_sha256": plan_digest(plan),
            "preview": f"previews/{preview.name}",
            "verify": results.get(recipe.id, {}),
        })
    manifest = {
        "schema": "chronontemplate.typewriter-pack.v2",
        "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                   "duration_frames": DUR, "duration_sec": DUR / FPS},
        "families": {"2d": len(RECIPES_2D), "3d": len(RECIPES_3D)},
        "clip_count": len(clips),
        "clips": clips,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    rows = "\n".join(
        f"| `{c['id']}` | {c['family']} | {c['fit']} | {c['font']} {c['font_size']}px / "
        f"{c['lines']} riga/he | {c['unit']} | {c['reveal_shape']} | "
        f"{c['caret'] or '—'} | {c['camera'] or '—'} | `{c['phrase']}` |"
        for c in clips)
    readme = f"""# Typewriter motion pack v2 — 14 animazioni 2D + 14 animazioni 3D

Ventotto ricette typewriter renderizzate con il backend Vulkan di Chronon3d e
codifica H.264, **1920x1080 a 24 fps, 192 frame (8 s)** — dentro il limite di
10 secondi. Quattordici ricette **2D** (testo frontale, caret, reveal per
glyph/word) e quattordici **3D** (layer `enable_3d`, ingresso su rotation /
position_z / scale e camera prospettica con samples per frame). Il pack 2D non
disegna la linea d'accento sotto la frase.

Le frasi sono sia **long** (fino a tre righe, corpo ridotto automaticamente)
sia **short** (una riga): la stessa ricetta si adatta alla lunghezza del copy.

## Clip

| id | famiglia | fit | font / righe | unit | reveal | caret | camera | frase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{rows}

## Contenuto del bundle

- `videos/<id>.mp4` — clip finale 1920x1080 24fps, H.264.
- `plans/<id>.plan.json` — `chronon.render-plan.v3` riproducibile.
- `previews/<id>.png` — contact sheet 6 frame su griglia 3x2.
- `MANIFEST.json` — SHA-256, byte, bbox verificata per ogni clip.

## Riprodurre

```bash
python3 ChrononTemplate/tools/important_phrases/render_typewriter_pack_v2.py \\
  --render --out RenderingGen/Upload/typewriter_pack_2d3d_20261125
```

Senza `--render` emette solo i plan. `CHRONON_CLI` (o `--cli`) indica il
`chronon3d_cli`; `--jobs 2` tiene due render Vulkan in parallelo.

## Verifica

Ogni clip viene ricontrollata con `ffprobe` (codec, risoluzione, 192 frame) e
con il bbox del testo su frame campionati: il soggetto deve essere dentro la
safe area di 40 px e sufficientemente largo, altrimenti il render fallisce.
"""
    (out / "README.md").write_text(readme)


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--only", action="append", default=None)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--cli", type=str, default=None)
    args = parser.parse_args()

    wanted = args.only or [r.id for r in RECIPES]
    unknown = set(wanted) - {r.id for r in RECIPES}
    if unknown:
        raise SystemExit(f"ricette sconosciute: {', '.join(sorted(unknown))}")

    out: Path = args.out
    for sub in ("plans", "videos", "previews", "logs"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    selected = [r for r in RECIPES if r.id in wanted]
    plans = {}
    for recipe in selected:
        plan = build_plan(recipe)
        path = out / "plans" / f"{recipe.id}.plan.json"
        path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        plans[recipe.id] = path
        size, laid = laid_out(recipe)
        print(f"plan {recipe.id}: {size}px, {len(laid)} riga/he", flush=True)

    if not args.render:
        return 0

    cli = resolve_cli(args.cli)
    print(f"engine: {cli}", flush=True)
    results: dict[str, dict] = {}
    todo = []
    for recipe in selected:
        video = out / "videos" / f"{recipe.id}.mp4"
        sidecar = video.with_suffix(".plan.sha256")
        fresh = (sidecar.is_file()
                 and sidecar.read_text().strip() == plan_digest(plans[recipe.id]))
        if video.is_file() and fresh and not args.force:
            try:
                results[recipe.id] = verify_video(video)
                contact_sheet(video, out / "previews" / f"{recipe.id}.png")
                print(f"skip {recipe.id}: gia' valido", flush=True)
                continue
            except SystemExit:
                pass
        todo.append(recipe)

    def run(recipe: Recipe) -> tuple[str, dict]:
        started = time.time()
        info = render_one(cli, plans[recipe.id], out / "videos" / f"{recipe.id}.mp4")
        contact_sheet(out / "videos" / f"{recipe.id}.mp4",
                      out / "previews" / f"{recipe.id}.png")
        print(f"rendered {recipe.id} in {info['seconds']}s "
              f"(bbox {info['bbox']}, totale {time.time() - started:.0f}s)", flush=True)
        return recipe.id, info

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(run, r): r for r in todo}
        for future in as_completed(futures):
            recipe = futures[future]
            try:
                mid, info = future.result()
            except Exception as exc:  # noqa: BLE001 - fail fast con il clip
                raise SystemExit(f"{recipe.id} fallito: {exc}") from exc
            results[mid] = info

    if len(results) == len(RECIPES):
        write_bundle(out, results)
        print(f"BUNDLE OK -> {out} ({len(results)} clip)", flush=True)
    else:
        print(f"parziale: {len(results)}/{len(RECIPES)} clip in {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
