#!/usr/bin/env python3
"""Short-phrase motion compiler (v3).

recipes/*.json  ->  chronon.render-plan.v2

One layer per animated unit (word / glyph / phrase). Every property is sampled
per frame with an explicit easing, so timing is fully authored here and the
renderer only plays keyframes. No drift, no procedural noise.

usage: compile.py [out_dir] [recipe_id ...]
"""
import json, math, sys
from pathlib import Path
from PIL import ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent.parent / "Chronon3d"
W, H, FPS = 1920, 1080, 30

PALETTE = {
    "dark":  {"bg": "assets/images/short_phrase_dark.png", "text": (1, 1, 1),
              "blue": (0.36, 0.60, 1.0), "gray": (0.42, 0.42, 0.45)},
    "light": {"bg": "assets/images/short_phrase_light.png", "text": (0.03, 0.03, 0.03),
              "blue": (0.30, 0.50, 1.0), "gray": (0.62, 0.62, 0.62)},
}


# ── easing ────────────────────────────────────────────────────────────────
def ease(name, t):
    t = min(max(t, 0.0), 1.0)
    if name == "linear": return t
    if name == "expo_out": return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)
    if name == "out_cubic": return 1 - (1 - t) ** 3
    if name == "in_cubic": return t ** 3
    if name == "in_out_cubic": return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
    if name == "in_out_sine": return .5 * (1 - math.cos(math.pi * t))
    if name == "out_back":
        c1 = 1.5; c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    raise ValueError(name)


def lerp(a, b, t): return a + (b - a) * t


# ── layout ────────────────────────────────────────────────────────────────
def font_for(recipe):
    return ImageFont.truetype(str(ASSETS / recipe["font"]), recipe["size"])


def layout(recipe):
    """Final centred position of every unit: [{text,line,cx,cy,w,h,word}]."""
    f = font_for(recipe)
    size = recipe["size"]
    line_h = int(size * 1.22)
    lines = recipe["text"].split("\n")
    track = recipe.get("tracking_px", 0)
    units, word_i = [], 0
    for li, line in enumerate(lines):
        cy = H / 2 + (li - (len(lines) - 1) / 2) * line_h + recipe.get("y_offset", 0)
        total = f.getlength(line) + track * max(len(line) - 1, 0)
        x0 = W / 2 - total / 2
        pos = 0
        for wi, word in enumerate(line.split(" ")):
            start = f.getlength(line[:pos]) + track * pos
            if recipe["unit"] in ("word", "phrase", "slot"):
                w = f.getlength(word)
                units.append(dict(text=word, word=word_i, line=li, w=w, h=line_h,
                                  cx=x0 + start + w / 2, cy=cy, x0=x0 + start))
            else:  # glyph
                for ci, ch in enumerate(word):
                    s = f.getlength(line[:pos + ci]) + track * (pos + ci)
                    w = f.getlength(ch)
                    units.append(dict(text=ch, word=word_i, line=li, w=w, h=line_h,
                                      cx=x0 + s + w / 2, cy=cy, x0=x0 + s))
            word_i += 1
            pos += len(word) + 1
    if recipe["unit"] == "phrase":
        # a single layer: merge into the full block
        allw = [u for u in units]
        left = min(u["x0"] for u in allw); right = max(u["x0"] + u["w"] for u in allw)
        return [dict(text=recipe["text"], word=0, line=0, w=right - left, h=line_h * len(lines),
                     cx=(left + right) / 2, cy=H / 2 + recipe.get("y_offset", 0), x0=left)]
    return units


# ── timeline ──────────────────────────────────────────────────────────────
def unit_curve(recipe, i, n, u, frame):
    """Properties of unit i at `frame`."""
    st = recipe["stagger"]
    ent = recipe["enter"]
    fr, to = recipe["from"], recipe["to"]
    ex = recipe["exit"]
    eas = recipe.get("easing", "out_cubic")
    unit_idx = u["word"] if recipe.get("stagger_by") == "word" else i

    if recipe["unit"] == "slot":
        slot = recipe["slot"]
        t0 = u["word"] * slot
        p_in = ease(eas, (frame - t0) / ent)
        p_out = ease("in_cubic", (frame - (t0 + ent + recipe["hold_each"])) / ex["frames"])
    else:
        t0 = recipe.get("delay", 0) + unit_idx * st
        p_in = ease(eas, (frame - t0) / ent)
        order = unit_idx if ex["mode"] in ("forward", "wipe", "arc") else (n - 1 - unit_idx)
        if ex["mode"] == "reverse": order = unit_idx
        t1 = recipe["out_start"] + order * ex.get("stagger", 0)
        p_out = ease(ex.get("easing", "in_cubic"), (frame - t1) / ex["frames"])

    props = {}
    keys = set(fr) | set(to)
    for k in keys:
        props[k] = lerp(fr.get(k, to.get(k, 0)), to.get(k, fr.get(k, 0)), p_in)
    # exit
    ext = ex.get("to", {"opacity": 0})
    for k, v in ext.items():
        base = props.get(k, 1.0 if k in ("opacity", "scale") else 0.0)
        props[k] = lerp(base, v, p_out)
    if ex["mode"] == "arc":
        nn = max(n - 1, 1)
        nrm = unit_idx / nn
        props["y"] = props.get("y", 0) + math.sin(nrm * math.pi) * ex.get("amplitude", 40) * p_out
        props["rotation"] = props.get("rotation", 0) + lerp(-8, 8, nrm) * p_out
        props["x"] = props.get("x", 0) + ex.get("drift_x", 120) * p_out
    return props, p_in


def color_mix(recipe, i, n, u, frame):
    """Amount (0..1) of the accent colour at `frame` for the unit."""
    c = recipe.get("color")
    if not c: return 0.0, None
    if recipe["unit"] == "slot":
        t0 = u["word"] * recipe["slot"]
    else:
        unit_idx = u["word"] if recipe.get("stagger_by") == "word" else i
        t0 = recipe.get("delay", 0) + unit_idx * recipe["stagger"]
    which = c["tint"]
    if "only" in c and u["word"] not in c["only"]:
        return 0.0, None
    settle = c["settle"]
    hold = c.get("hold", 0)
    tt = frame - t0 - recipe["enter"] * c.get("lead", 0.0)
    amt = 1.0 if tt < hold else 1 - ease("out_cubic", (tt - hold) / settle)
    if c.get("fade_in"):  # accent that appears mid-slot (single_word_swap)
        pass
    return amt, which


# ── plan emission ─────────────────────────────────────────────────────────
def build(recipe):
    pal = PALETTE[recipe["theme"]]
    units = layout(recipe)
    n = len(units)
    dur = recipe["duration"]
    layers = [{"id": "background", "type": "image", "asset": pal["bg"], "size": [W, H],
               "fit": "cover", "position": [0, 0], "start_frame": 0, "duration_frames": dur}]
    base = pal["text"]
    pad = 40
    for i, u in enumerate(units):
        tracks = {k: [] for k in ("position_x", "position_y", "scale", "opacity", "blur", "rotation")}
        fill = []
        for f in range(dur):
            p, _ = unit_curve(recipe, i, n, u, f)
            tracks["position_x"].append({"frame": f, "value": u["cx"] + p.get("x", 0)})
            tracks["position_y"].append({"frame": f, "value": u["cy"] + p.get("y", 0)})
            tracks["scale"].append({"frame": f, "value": p.get("scale", 1.0)})
            tracks["opacity"].append({"frame": f, "value": min(max(p.get("opacity", 1.0), 0), 1)})
            tracks["blur"].append({"frame": f, "value": max(p.get("blur", 0.0), 0)})
            tracks["rotation"].append({"frame": f, "value": [0.0, 0.0, p.get("rotation", 0.0)]})
            amt, which = color_mix(recipe, i, n, u, f)
            gray = p.get("gray", 0.0)
            col = list(base)
            if which and amt > 0:
                col = [lerp(base[k], pal[which][k], amt) for k in range(3)]
            if gray > 0:
                col = [lerp(col[k], pal["gray"][k], min(gray, 1)) for k in range(3)]
            fill.append({"frame": f, "value": [*[min(max(c, 0), 1) for c in col], 1.0]})
        layer = {
            "id": f"u{i:02d}", "type": "text", "text": u["text"],
            "size": [u["w"] + pad * 2, u["h"]],
            "position": [u["cx"], u["cy"]],
            "style": {"font": recipe["font"], "font_size": recipe["size"], "fill": "#FFFFFF",
                      "stroke": {"color": "#000000", "width": 0},
                      "glow": {"radius": 0, "intensity": 0, "color": "#000000"}},
            "start_frame": 0, "duration_frames": dur,
            "animation": {"tracks": [{"property": k, "keyframes": v, "easing": "linear"}
                                      for k, v in tracks.items()
                                      if k != "rotation" or recipe["exit"]["mode"] == "arc"]},
            "text_animators": [{
                "id": f"u{i:02d}_color",
                "selectors": [{"id": f"u{i:02d}_sel", "unit": "word", "shape": "square",
                               "order": "forward", "combine": "replace", "exclude_spaces": True,
                               "start": {"keyframes": [{"frame": 0, "value": 0}], "easing": "linear"},
                               "end": {"keyframes": [{"frame": 0, "value": 100}], "easing": "linear"}}],
                "properties": [{"property": "fill_color", "keyframes": fill, "easing": "linear"}]}],
        }
        layers.append(layer)
    return {"schema": "chronon.render-plan.v2", "version": 2,
            "job_id": f"short_phrase_{recipe['id']}",
            "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1, "duration_frames": dur},
            "layers": layers,
            "output": {"path": f"{recipe['id']}.mp4", "format": "mp4", "codec": "h264"}}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "out")
    only = set(sys.argv[2:])
    out.mkdir(parents=True, exist_ok=True)
    for path in sorted((HERE / "recipes").glob("*.json")):
        recipe = json.loads(path.read_text())
        if only and recipe["id"] not in only: continue
        (out / f"{recipe['id']}.plan.json").write_text(json.dumps(build(recipe)))
        print("plan", recipe["id"])


if __name__ == "__main__":
    main()
