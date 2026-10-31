"""Web animation variants — 24 nuovi shot sulla grammatica di dual_marker_cross.

Stessa base (piastra editoriale + headline + highlight dietro il testo) ma con
assi variati:

  * highlight: bar, marker, double, underline, box, band, bracket, split,
    stripe, block  (10 stili)
  * camera v2: push, pull, drift_l, drift_r, tilt_up, tilt_down, settle, float
  * font: helv-bold, serif-bold-it, serif-black-it, oswald-bold, arial-bold,
    sans-black, impact, anton, abril, times-bold
  * corpo 58..112 px e altezza highlight 0.72..1.34 x corpo

Uso (il renderer sta in render_variants_v1.py):
  from shots_variants import VARIANTS, all_variant_shots
"""

from __future__ import annotations

import math

from web_shot_kit import Canvas, Shot

FPS = 30
SECONDS = 3.0


# --------------------------------------------------------------------------- #
# easing / timing
# --------------------------------------------------------------------------- #

def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _sweep(t: float, t0: float = 0.08, t1: float = 0.55) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _ease((t - t0) / (t1 - t0))


def _late(t: float, t0: float, t1: float) -> float:
    """Ritardo con partenza morbida (per i gesti secondari)."""
    return _sweep(t, max(t0, t0), t1) if t1 > t0 else 0.0


# --------------------------------------------------------------------------- #
# camera v2: movimenti propri, non il drift clampato del kit
# --------------------------------------------------------------------------- #

def _camera(mode: str, t: float):
    t = max(0.0, min(1.0, t))
    e = _ease(t)
    if mode == "push":
        return (1.0 + 0.075 * e, 0.5, 0.5)
    if mode == "pull":
        return (1.085 - 0.075 * e, 0.5, 0.5)
    if mode == "drift_l":
        return (1.045, 0.522 - 0.046 * e, 0.5)
    if mode == "drift_r":
        return (1.045, 0.478 + 0.046 * e, 0.5)
    if mode == "tilt_up":
        return (1.05, 0.5, 0.545 - 0.085 * e)
    if mode == "tilt_down":
        return (1.05, 0.5, 0.455 + 0.085 * e)
    if mode == "settle":
        return (1.11 - 0.09 * e, 0.5, 0.5)
    if mode == "float":
        return (1.035 + 0.018 * math.sin(2.0 * math.pi * 0.8 * t),
                0.5 + 0.009 * math.sin(2.0 * math.pi * 0.5 * t), 0.5)
    return (1.0 + 0.04 * e, 0.5, 0.5)


# --------------------------------------------------------------------------- #
# stili di highlight (disegnati DI DIETRO al testo)
# --------------------------------------------------------------------------- #

def _hl_bar(c: Canvas, x, y, w, h, color, s, alpha=0.94):
    """Banda piena netta, wipe orizzontale."""
    c.rect(x, y, w * s, h, color, alpha)


def _hl_marker(c: Canvas, x, y, w, h, color, s, alpha=0.95):
    """Pennarello grezzo (stesso gesto del dual marker)."""
    c.marker(x, y, w * s, h, color, alpha, sweep=1.0)


def _hl_double(c: Canvas, x, y, w, h, color, s, alpha=0.95):
    """Due passate sovrapposte, la seconda più bassa e più trasparente."""
    s2 = _sweep(s, 0.25, 1.0) if 0.0 < s < 1.0 else (1.0 if s >= 1.0 else 0.0)
    c.marker(x, y, w * s, h * 0.74, color, alpha * 0.9, sweep=1.0, seed=11)
    c.marker(x, y + h * 0.34, w * s2, h * 0.66, "#E4572E", 0.42, sweep=1.0, seed=23)


def _hl_underline(c: Canvas, x, y, w, h, color, s, alpha=0.95):
    """Sottolineatura spessa che si disegna da sinistra."""
    c.rect(x, y + h * 0.92, w * s, max(4.0, h * 0.13), color, alpha)


def _hl_box(c: Canvas, x, y, w, h, color, s, alpha=0.9):
    """Riquadro a quattro lati che si chiude (top, right, bottom, left)."""
    th = max(3.0, h * 0.055)
    parts = [(x, y, w, th), (x + w - th, y, th, h), (x, y + h - th, w, th),
             (x, y, th, h)]
    for i, (px, py, pw, ph) in enumerate(parts):
        local = max(0.0, min(1.0, s * 4.0 - i))
        if local <= 0.0:
            continue
        if i in (0, 2):
            c.rect(px, py, pw * local, ph, color, alpha)
        else:
            c.rect(px, py, pw, ph * local, color, alpha)


def _hl_band(c: Canvas, x, y, w, h, color, s, alpha=0.92):
    """Fascia a tutta larghezza che scende dall'alto."""
    c.rect(0, y, 1920, h * s, color, alpha)


def _hl_bracket(c: Canvas, x, y, w, h, color, s, alpha=0.95):
    """Due staffe [ ] che si avvicinano al testo."""
    th = max(3.0, h * 0.06)
    arm = w * 0.10
    for side, sign in ((0, -1), (1, 1)):
        if s <= side * 0.35:
            continue
        base_x = x if side == 0 else x + w
        dx = sign * arm * (1.0 - min(1.0, max(0.0, (s - side * 0.35) / 0.65)))
        c.rect(base_x + dx - (th if side == 0 else 0), y, th, h, color, alpha)
        c.rect(base_x + dx - (arm if side == 0 else 0), y, arm, th, color, alpha)
        c.rect(base_x + dx - (arm if side == 0 else 0), y + h - th, arm, th, color, alpha)


def _hl_split(c: Canvas, x, y, w, h, color, s, alpha=0.9):
    """Due bande: sopra il colore pieno, sotto lo stesso colore più chiaro."""
    c.rect(x, y, w * s, h * 0.52, color, alpha)
    c.rect(x, y + h * 0.52, w * s, h * 0.48, "#F2C500", alpha * 0.72)


def _hl_stripe(c: Canvas, x, y, w, h, color, s, alpha=0.9):
    """Tre strisce sfalsate, come tre passate veloci di penna."""
    for i, frac in enumerate((0.18, 0.5, 0.82)):
        local = max(0.0, min(1.0, s * 3.0 - i))
        if local <= 0.0:
            continue
        c.rect(x, y + h * frac - h * 0.12, w * local, h * 0.24, color,
               alpha * (0.95 - 0.12 * i))


def _hl_block(c: Canvas, x, y, w, h, color, s, alpha=0.93):
    """Blocchi che salgono dal basso a riempire la banda."""
    steps = 5
    for i in range(steps):
        local = max(0.0, min(1.0, s * steps - i))
        if local <= 0.0:
            continue
        bh = h / steps
        c.rect(x, y + h - bh * (i + 1), w * local, bh * 0.92, color,
               alpha * (0.98 - 0.04 * i))


HL_STYLES = {
    "bar": _hl_bar,
    "marker": _hl_marker,
    "double": _hl_double,
    "underline": _hl_underline,
    "box": _hl_box,
    "band": _hl_band,
    "bracket": _hl_bracket,
    "split": _hl_split,
    "stripe": _hl_stripe,
    "block": _hl_block,
}


# --------------------------------------------------------------------------- #
# specifiche: 24 shot
# --------------------------------------------------------------------------- #

# (nome, headline, highlight, font, corpo, stile, colore, ratio, camera, carta, inchiostro)
SPECS = [
    ("v01_marker_push", "Senate passes the chip export bill", "chip export bill",
     "helv-bold", 72, "marker", "#E6E300", 1.28, "push", "#EDECEA", "#141416"),
    ("v02_bar_drift_l", "Rainmaking Is Used As Weapon by U.S.", "As Weapon",
     "serif-black-it", 96, "bar", "#E6E300", 0.95, "drift_l", "#E9E8E6", "#10100F"),
    ("v03_double_pull", "The page snaps flat as the marker lands", "snaps flat",
     "arial-bold", 76, "double", "#E6E300", 1.18, "pull", "#F4F3F0", "#0E0E10"),
    ("v04_underline_tilt_up", "Simple Sabotage Field Manual revealed", "revealed",
     "serif-bold-it", 104, "underline", "#F2C500", 1.02, "tilt_up", "#0A0A0A", "#F5D24A"),
    ("v05_box_settle", "Why this 30-year-old founder gave it away", "gave it away",
     "helv-bold", 68, "box", "#E4572E", 1.34, "settle", "#F7F5F1", "#0E0E10"),
    ("v06_band_drift_r", "Missiles leave Seoul as region rattles", "leave Seoul",
     "oswald-bold", 92, "band", "#E4572E", 1.24, "drift_r", "#161616", "#F4F4F2"),
    ("v07_bracket_float", "When the sauce changed, it went downhill", "sauce changed",
     "sans-bold", 64, "bracket", "#E6E300", 1.10, "float", "#131110", "#F7F7F5"),
    ("v08_split_push", "The vault was opened after fifty years", "opened",
     "impact", 100, "split", "#C9DC28", 1.14, "push", "#EDECEA", "#141416"),
    ("v09_stripe_tilt_down", "Every warning sign was ignored for a decade", "ignored",
     "sans-black", 70, "stripe", "#E6E300", 1.22, "tilt_down", "#F2F0EC", "#101010"),
    ("v10_block_pull", "A single line changed the whole ruling", "whole ruling",
     "anton", 96, "block", "#F2C500", 1.06, "pull", "#101014", "#F3F3F0"),

    ("v11_marker_drift_r", "Golden State Warriors demanded a trade", "demanded a trade",
     "helv-med", 66, "marker", "#C9DC28", 1.15, "drift_r", "#F7F7F5", "#1A1A1A"),
    ("v12_bar_settle", "Fifty years of records vanished overnight", "vanished",
     "serif-bold", 98, "bar", "#C9DC28", 0.92, "settle", "#EDE9E1", "#12100E"),
    ("v13_underline_float", "Nobody read the footnote until now", "footnote",
     "oswald", 88, "underline", "#E6E300", 0.98, "float", "#0E0E12", "#EDEDEA"),
    ("v14_box_push", "The contract was signed in a single afternoon", "single afternoon",
     "times-bold", 74, "box", "#8A6A08", 1.20, "push", "#F5F1E8", "#141210"),
    ("v15_band_tilt_up", "Three warehouses held the same evidence", "same evidence",
     "abril", 92, "band", "#C9DC28", 1.30, "tilt_up", "#15120F", "#F4EFE6"),
    ("v16_bracket_drift_l", "The archive answered before the question", "answered",
     "serif-it", 102, "bracket", "#E4572E", 1.08, "drift_l", "#F3F1ED", "#131211"),
    ("v17_split_tilt_down", "One photograph undid the whole timeline", "undid",
     "sans-xbold", 84, "split", "#E6E300", 1.12, "tilt_down", "#101013", "#F6F4EF"),
    ("v18_stripe_pull", "The tape kept recording after the call ended", "kept recording",
     "helv-bold", 62, "stripe", "#F2C500", 1.18, "pull", "#EFEBE4", "#141310"),

    ("v19_block_drift_r", "Nobody expected the second shipment", "second shipment",
     "oswald-bold", 86, "block", "#C9DC28", 1.20, "drift_r", "#0F1114", "#EFEFEA"),
    ("v20_double_tilt_up", "The map was redrawn three times that year", "redrawn",
     "arial-bold", 80, "double", "#E6E300", 1.16, "tilt_up", "#F4F2EE", "#111111"),
    ("v21_marker_settle", "Every ledger entry pointed to the same name", "same name",
     "serif-bold-it", 90, "marker", "#E4572E", 1.20, "settle", "#120F0D", "#F3EDE4"),
    ("v22_bar_float", "The request was filed and then forgotten", "forgotten",
     "sans-med", 74, "bar", "#C9DC28", 1.00, "float", "#F6F4F0", "#171717"),
    ("v23_underline_push", "Two hours of silence decided the verdict", "silence",
     "anton", 104, "underline", "#E6E300", 1.00, "push", "#131316", "#F2F2EE"),
    ("v24_box_drift_l", "The last witness arrived after midnight", "last witness",
     "abril", 88, "box", "#E4572E", 1.26, "drift_l", "#F3EFE7", "#131110"),
]


def _build(spec) -> Shot:
    (name, head, hl, font, size, style, color, ratio, cam, paper, ink) = spec
    sub = "Editorial rebuild — variant pass"
    left = 160.0
    top = 400.0
    idx = head.find(hl)
    if idx < 0:
        raise ValueError(f"{name}: highlight {hl!r} non compare in headline")

    # Auto-fit: il corpo autore e' un'intenzione, ma la riga deve stare dentro
    # la cornice. Se a quella dimensione sfonda il margine destro, si scala il
    # corpo (e con esso il marker): la varieta' di grandezze resta, nessuna
    # headline viene tagliata.
    probe = Canvas()
    # Il crop della camera (zoom > 1) stringe il campo visivo: il margine va
    # diviso per lo zoom massimo della modalita', altrimenti il testo sta nel
    # plate ma esce dalla cornice renderizzata.
    _zoom_max = {"push": 1.075, "pull": 1.085, "drift_l": 1.045, "drift_r": 1.045,
                 "tilt_up": 1.05, "tilt_down": 1.05, "settle": 1.11, "float": 1.053}
    avail = (1920.0 - left - 80.0) / _zoom_max.get(cam, 1.05)
    natural = probe.measure(head, size, font)
    if natural > avail:
        size = round(size * avail / natural, 1)

    dark = sum(int(ink[i:i + 2], 16) for i in (1, 3, 5)) > 380

    def back(c: Canvas):
        c.rect(0, 0, 1920, 1080, paper)
        c.noise(0.009 if dark else 0.007, seed=900 + len(name))
        c.vignette(0.22 if dark else 0.14, 0.70)
        if dark:
            c.screen_grid(3, 0.018)

    def front(c: Canvas):
        # ombra minima: tiene il testo leggibile sopra il marker
        c.text(left, top, head, size, font, ink)
        c.text(left, top + size * 1.95, sub, max(22.0, size * 0.30), "oswald",
               "#8A8578" if dark else "#6E6A64")
        c.rect(left, top + size * 1.62, 240, 3,
               color if dark else "#2A2A2A", 0.55)

    def anim(c: Canvas, t: float):
        s = _sweep(t, 0.10, 0.52)
        if s <= 0.0:
            return
        # il marker parte dove inizia la parola evidenziata, non a inizio riga
        px = left + c.measure(head[:idx], size, font)
        w = c.measure(hl, size, font)
        hy = top + size * 0.12
        hh = size * ratio
        HL_STYLES[style](c, px, hy, w, hh, color, s, 0.95)

    shot = Shot(
        name=name,
        source=f"native variant ({style}, {font} {size}, cam v2 {cam})",
        seconds=SECONDS,
        description=f"{style} highlight on '{hl}' · {font} {size}px · camera {cam}",
        grain=0.012 if dark else 0.009,
        vig=0.24 if dark else 0.14,
        build_static=back,
        build_static_front=front,
        draw_anim=anim,
    )
    shot.camera = lambda t, m=cam: _camera(m, t)
    return shot


def all_variant_shots() -> list[Shot]:
    return [_build(spec) for spec in SPECS]


def variant_names() -> list[str]:
    return [spec[0] for spec in SPECS]


if __name__ == "__main__":
    for shot in all_variant_shots():
        print(shot.name, "|", shot.description)
    print(len(SPECS), "variants")
