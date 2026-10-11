#!/usr/bin/env python3
"""Fix Vulkan shape+position-track bug: moving shapes vanish mid-ramp.

Probe results (fast-dev CLI, NVENC pipe):
- shape + sloped position_x/position_y track -> layer ABSENT during ramp
- text  + sloped position_x track          -> tracks perfectly (probe D)
- shape + scale-only tracks                -> fine (oil showcase pattern)

Fix:
- cursor plans: convert moving shapes to text glyph layers (same id/pos/tracks)
- dataviz plans: strip position tracks from shapes (center-growth, oil pattern)
"""
from __future__ import annotations

import copy
import glob
import json
import sys

FONT = "assets/fonts/Inter-Bold.ttf"

# glyph, measured w/h @100px in Inter-Bold (pixel-probed)
G_CARET = ("\u258c", 48, 87)    # left half block, thin verticals
G_DOT = ("\u25cf", 75, 75)      # black circle, dots/squares
G_RING = ("\u25ef", 137, 137)   # large circle, rings
G_RING_S = ("\u25cb", 75, 75)   # white circle outline-ish, mid rings/auras
G_PILL = ("\u25ac", 84, 30)     # black rectangle, pills/badges/bars


def rgba_to_hex(fill) -> str:
    if isinstance(fill, str):
        return fill
    r, g, b = [max(0, min(255, int(round(c * 255)))) for c in fill[:3]]
    return f"#{r:02X}{g:02X}{b:02X}"


def pos_range(layer) -> float:
    mx = 0.0
    for t in layer.get("animation", {}).get("tracks", []):
        p = t["property"]
        if p in ("position_x", "position_y"):
            v = [k["value"] for k in t["keyframes"]]
            mx = max(mx, max(v) - min(v))
        elif p == "position":
            cols = list(zip(*[k["value"][:2] for k in t["keyframes"]]))
            for col in cols:
                mx = max(mx, max(col) - min(col))
        elif p in ("position.x", "position.y"):
            v = [k["value"] for k in t["keyframes"]]
            mx = max(mx, max(v) - min(v))
    return mx


def split_track(t: dict) -> list[dict]:
    """Split combined/axis-suffixed position tracks into position_x/y."""
    p = t["property"]
    if p == "position":
        out = []
        for ax, nm in enumerate(("position_x", "position_y")):
            c = copy.deepcopy(t)
            c["property"] = nm
            for k in c["keyframes"]:
                k["value"] = k["value"][ax]
            out.append(c)
        return out
    if p in ("position.x", "position.y"):
        c = copy.deepcopy(t)
        c["property"] = "position_x" if p.endswith(".x") else "position_y"
        return [c]
    return [copy.deepcopy(t)]


def pick_glyph(lid: str, w: float, h: float):
    l = lid.lower()
    if "shadow" in l or "ghost" in l or "glow" in l:
        return G_DOT
    if "aura" in l or "ring" in l or "loupe" in l:
        return G_RING if max(w, h) > 80 else G_RING_S
    if "wedge" in l or "pointer" in l or "head" in l or "plane" in l:
        return G_CARET if h >= w else G_DOT
    if w <= 16 and h >= 40:
        return G_CARET
    if h > w * 1.2:
        return G_CARET
    if w > h * 1.5:
        return G_PILL
    if abs(w - h) <= max(w, h) * 0.25:
        return G_DOT if max(w, h) <= 40 else (G_RING_S if max(w, h) <= 80 else G_RING)
    return G_CARET if h >= w else G_PILL


def shape_to_text(layer: dict) -> dict:
    w, h = layer.get("size", [20, 20])[:2]
    fill = layer.get("shape", {}).get("fill", [1, 1, 1, 1])
    glyph, gw, gh = pick_glyph(layer["id"], w, h)
    fs = max(8.0, h / gh * 100.0)
    pos = layer.get("position", [960, 540])
    tracks = []
    for t in layer.get("animation", {}).get("tracks", []):
        tracks.extend(split_track(t))
    nl = {
        "id": layer["id"],
        "type": "text",
        "text": glyph,
        "size": [max(200.0, w * 3.0), max(150.0, h + 70.0)],
        "position": [pos[0], pos[1]] if len(pos) == 2 else list(pos[:2]),
        "style": {
            "font": FONT,
            "font_size": round(fs, 2),
            "fill": rgba_to_hex(fill),
            "stroke": {"color": "#000000", "width": 0},
            "glow": {"radius": 0, "intensity": 0, "color": "#000000"},
        },
        "start_frame": layer.get("start_frame", 0),
        "duration_frames": layer.get("duration_frames", 90),
    }
    if tracks:
        nl["animation"] = {"tracks": tracks}
    for k in ("opacity", "enable_3d", "screen_space", "loop"):
        if k in layer:
            nl[k] = layer[k]
    return nl


def convert_layer_list(layers: list) -> int:
    """Convert moving shapes to text glyphs in a plan layer list. Returns count."""
    n = 0
    for i, l in enumerate(layers):
        if l.get("type") == "shape" and pos_range(l) > 1.0:
            layers[i] = shape_to_text(l)
            n += 1
    return n


def rebase_layer_list(layers: list) -> int:
    """Renderer adds track values to base position (probes: rendered=base+key).
    Generators wrote ABSOLUTE coords into keys, double-shifting every layer.
    If a position track's first key ~= base coord, subtract base from all keys.
    Returns number of rebased tracks. Idempotent (second run: first key ~= 0)."""
    n = 0
    for l in layers:
        base = l.get("position", [960.0, 540.0])
        for t in l.get("animation", {}).get("tracks", []):
            p = t["property"]
            axis = None
            if p == "position_x" or p == "position.x":
                axis = 0
            elif p == "position_y" or p == "position.y":
                axis = 1
            if axis is None or not t["keyframes"]:
                continue
            first = t["keyframes"][0]["value"]
            if abs(first - base[axis]) < 5.0 and abs(base[axis]) > 5.0:
                for k in t["keyframes"]:
                    k["value"] = round(k["value"] - base[axis], 4)
                n += 1
    return n


def fix_cursor_plan(path: str) -> int:
    d = json.load(open(path))
    n = 0
    for i, l in enumerate(d["layers"]):
        if l.get("type") == "shape" and pos_range(l) > 1.0:
            d["layers"][i] = shape_to_text(l)
            n += 1
    if n:
        json.dump(d, open(path, "w"), indent=2)
    return n


def fix_dataviz_plan(path: str) -> int:
    """Strip position tracks from shapes (center-growth, oil-showcase pattern)."""
    d = json.load(open(path))
    n = 0
    for l in d["layers"]:
        if l.get("type") != "shape":
            continue
        tr = l.get("animation", {}).get("tracks", [])
        keep = [t for t in tr if t["property"] not in (
            "position_x", "position_y", "position", "position.x", "position.y")]
        if len(keep) != len(tr):
            l["animation"]["tracks"] = keep
            n += 1
    if n:
        json.dump(d, open(path, "w"), indent=2)
    return n


if __name__ == "__main__":
    total_c = total_d = 0
    for p in sorted(glob.glob("out/cursor_animations/*.plan.json") +
                    glob.glob("out/cursor_catalog_16/*.plan.json")):
        c = fix_cursor_plan(p)
        total_c += c
        d = json.load(open(p))
        r = rebase_layer_list(d["layers"])
        if r:
            json.dump(d, open(p, "w"), indent=2)
        print(f"{p.split('out/')[-1]}: {c} shapes->text, {r} tracks rebased")
    for p in sorted(glob.glob("out/dataviz_modern/*.plan.json")):
        c = fix_dataviz_plan(p)
        total_d += c
        print(f"{p.split('out/')[-1]}: {c} shapes stripped")
    print(f"TOTAL converted={total_c} stripped={total_d}")
