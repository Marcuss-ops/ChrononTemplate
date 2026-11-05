"""Claude-Code-flavoured web motion set — ten modern terminal/editorial shots.

The existing web variant set is a marker/highlight family. This set is a
separate grammar: warm charcoal terminals, coral accents, monospace chrome and
editorial headlines. Each shot uses a different font pair and a different
motion idea (typewriter, stream, diff, prompt/response, tool stack, plan,
editorial terminal, code review, agent trace, ship).

Everything is authored with the shared ``web_shot_kit`` primitives. No external
images or services are used.
"""
from __future__ import annotations

import math
from typing import Sequence

from web_shot_kit import Canvas, Shot

W, H = 1920, 1080
FPS = 30
SECONDS = 3.0

THEMES = {
    "dark": {
        "paper": "#141311", "ink": "#F5F0E8", "muted": "#938F86",
        "accent": "#D97757", "green": "#7BC47F", "red": "#E4572E",
        "yellow": "#F2C500", "blue": "#8AB4FF",
        "panel": "#1D1B18", "bar": "#24211D", "line": "#3A352E",
    },
    "light": {
        "paper": "#F2EDE3", "ink": "#1C1A17", "muted": "#756F65",
        "accent": "#C96444", "green": "#3E8B5B", "red": "#C44B2D",
        "yellow": "#B58B00", "blue": "#4C78C7",
        "panel": "#1D1B18", "bar": "#24211D", "line": "#D8CFC0",
    },
}

# Fonts are resolved by web_shot_kit. Keep the names short in the shot table.
FONTS = {
    "mono": "mono",
    "inter": "sans-med",
    "inter-bold": "sans-bold",
    "inter-black": "sans-black",
    "display": "interdisplay",
    "play": "serif-black",
    "play-bold": "serif-bold",
    "play-italic": "serif-black-it",
    "oswald": "oswald-bold",
    "anton": "anton",
    "abril": "abril",
    "helv": "helv-bold",
    "times": "times-bold",
}


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _reveal(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if t >= end else 0.0
    return _ease((t - start) / (end - start))


def _bg(c: Canvas, theme: dict, dark: bool, seed: int) -> None:
    c.rect(0, 0, W, H, theme["paper"])
    c.noise(0.010 if dark else 0.007, seed=seed)
    if dark:
        c.screen_grid(4, 0.012)
        c.vignette(0.25, 0.70)
    else:
        c.screen_grid(6, 0.006)
        c.vignette(0.15, 0.72)


def _kicker(c: Canvas, text: str, x: float, y: float, theme: dict) -> None:
    c.text(x, y, text, 16, "mono", theme["accent"], spacing=2.2)
    c.rect(x, y + 30, 86, 3, theme["accent"], 0.9)


def _panel(c: Canvas, x, y, w, h, title: str, theme: dict, radius=22) -> None:
    c.rect(x, y, w, h, theme["panel"], 1.0, radius=radius)
    c.rect(x, y, w, 54, theme["bar"], 1.0, radius=radius)
    c.rect(x, y + 32, w, 24, theme["bar"], 1.0)
    for i, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        c.ellipse(x + 22 + i * 22, y + 21, 10, 10, col)
    c.text(x + w / 2, y + 17, title, 15, "mono", theme["muted"], anchor="ma")
    c.line(x, y + 54, x + w, y + 54, theme["line"], 1, 0.9)


def _headline(c: Canvas, lines: Sequence[str], x, y, size, font, theme, t,
              ink: str | None = None, accent_last: bool = True) -> None:
    for i, line in enumerate(lines):
        a = _reveal(t, 0.04 + i * 0.09, 0.04 + i * 0.09 + 0.22)
        if a <= 0:
            continue
        dy = 20.0 * (1.0 - a)
        color = theme["accent"] if accent_last and i == len(lines) - 1 else (ink or theme["ink"])
        c.text(x, y + i * size * 1.05 + dy, line, size, font, color, alpha=a)


def _type_line(c: Canvas, x, y, text, size, font, color, t,
               start=0.08, end=0.36) -> float:
    n = int(round(len(text) * _reveal(t, start, end)))
    if n:
        c.text(x, y, text[:n], size, font, color)
    return x + c.measure(text[:n], size, font)


def _lines(c: Canvas, x, y, rows, size, line_h, theme, t,
           start=0.12, stagger=0.08, font="mono") -> None:
    for i, row in enumerate(rows):
        if isinstance(row, tuple):
            text, color = row
        else:
            text, color = row, theme["muted"]
        a = _reveal(t, start + i * stagger, start + i * stagger + 0.18)
        if a > 0:
            c.text(x, y + i * line_h, text, size, font, color, alpha=a)


def _cursor(c: Canvas, x, y, h, color, t, alpha=1.0) -> None:
    if t < 0.94 or int(t * 10) % 2 == 0:
        c.rect(x, y + 2, 11, h, color, alpha)


def _mini_card(c: Canvas, x, y, w, h, theme, accent, alpha=1.0, dy=0.0) -> None:
    c.rect(x, y + dy, w, h, theme["panel"], alpha, radius=16)
    c.line(x + 1, y + dy + 1, x + w - 1, y + dy + 1, accent, 1, alpha * 0.7)
    c.rect(x, y + dy + 18, 4, h - 36, accent, alpha * 0.9)


def _c01_typewriter() -> Shot:
    theme = THEMES["dark"]

    def static(c: Canvas):
        _bg(c, theme, True, 101)
        _kicker(c, "CLAUDE CODE  /  WEB 01", 130, 96, theme)
        _panel(c, 900, 150, 870, 780, "claude — ~/studio", theme)

    def anim(c: Canvas, t: float):
        _headline(c, ["Scrivi meno.", "Spedisci di più."], 130, 205, 78,
                  FONTS["display"], theme, t)
        sub = _reveal(t, 0.26, 0.42)
        c.text(132, 440, "Un agente. Tutto il contesto.", 26,
               FONTS["inter"], theme["muted"], alpha=sub)
        end = _type_line(c, 944, 260, '$ claude "refactor auth"', 24,
                         "mono", theme["ink"], t, 0.06, 0.40)
        _cursor(c, end + 9, 262, 26, theme["accent"], t)
        rows = [
            ("● reading src/auth/session.ts", theme["muted"]),
            ("● reading src/auth/tokens.ts", theme["muted"]),
            ("[ok] plan ready", theme["green"]),
            ("", theme["muted"]),
            ("3 files · 2 tests · 0 regressions", theme["ink"]),
        ]
        _lines(c, 944, 330, rows, 21, 40, theme, t, 0.38, 0.09)
        a = _reveal(t, 0.78, 0.90)
        c.rect(944, 552, 170, 36, theme["accent"], 0.16 * a, radius=18)
        c.text(1029, 559, "READY TO APPLY", 14, "mono", theme["accent"],
               alpha=a, anchor="ma")
        foot = _reveal(t, 0.86, 0.98)
        c.line(944, 630, 1726, 630, theme["line"], 1, 0.8 * foot)
        c.text(944, 655, "context 32k  ·  session 04  ·  2.1 s", 15,
               "mono", theme["muted"], alpha=foot)
        c.text(1726, 655, "sonnet", 15, "mono", theme["accent"], alpha=foot, anchor="ra")

    shot = Shot("c01_typewriter", "claude-code/typewriter",
                seconds=SECONDS, still_t=1.0,
                description="Typewriter prompt, tool trace, InterDisplay + mono",
                grain=0.010, vig=0.23,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.02 + 0.03 * _ease(t), 0.5, 0.5)
    return shot


def _c02_stream() -> Shot:
    theme = THEMES["light"]

    def static(c: Canvas):
        _bg(c, theme, False, 102)
        _kicker(c, "CLAUDE CODE  /  WEB 02", 130, 96, theme)
        c.text(90, 130, "“", 190, FONTS["play"], theme["accent"], alpha=0.16)
        _panel(c, 1010, 170, 760, 700, "stream · response", theme)

    def anim(c: Canvas, t: float):
        _headline(c, ["Il contesto", "giusto."], 130, 230, 94,
                  FONTS["play"], theme, t)
        rows = [
            ("La risposta arriva un token", theme["ink"]),
            ("alla volta, senza perdere", theme["ink"]),
            ("il filo del contesto.", theme["accent"]),
        ]
        _lines(c, 1052, 275, rows, 25, 54, theme, t, 0.14, 0.11)
        a = _reveal(t, 0.55, 0.72)
        c.text(1052, 500, "tokens  1,284", 17, "mono", theme["muted"], alpha=a)
        c.text(1052, 535, "streaming", 16, "mono", theme["green"], alpha=a)
        bar = _reveal(t, 0.16, 0.92)
        c.rect(1052, 585, 676, 3, theme["line"], 0.8)
        c.rect(1052, 585, 676 * bar, 3, theme["accent"], 0.95)
        end = _type_line(c, 1052, 630, "▌", 26, "mono", theme["accent"], t, 0.20, 0.30)
        _cursor(c, end, 632, 24, theme["accent"], t)
        c.text(1052, 690, "response  ·  1.8 s", 16, "mono", theme["muted"],
               alpha=_reveal(t, 0.72, 0.88))

    shot = Shot("c02_stream", "claude-code/stream",
                seconds=SECONDS, still_t=1.0,
                description="Token stream on warm paper, Playfair Black + mono",
                grain=0.008, vig=0.16,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.015 + 0.035 * _ease(t), 0.5, 0.5)
    return shot


def _c03_diff() -> Shot:
    theme = THEMES["dark"]

    def static(c: Canvas):
        _bg(c, theme, True, 103)
        _kicker(c, "CLAUDE CODE  /  WEB 03", 120, 88, theme)
        c.text(120, 135, "Una patch alla volta.", 66, FONTS["anton"], theme["ink"])
        _panel(c, 120, 260, 1680, 700, "diff -- src/auth/session.ts", theme)

    def anim(c: Canvas, t: float):
        _type_line(c, 164, 340, "$ claude review --diff", 22, "mono",
                   theme["ink"], t, 0.05, 0.30)
        rows = [
            ("12", "-  const session = createSession(user)", theme["red"]),
            ("13", "+  const session = await createSession(user)", theme["green"]),
            ("14", "+  if (!session) throw new AuthError()", theme["green"]),
            ("15", "   return session", theme["muted"]),
            ("16", "+  // refresh token is rotated", theme["green"]),
            ("17", "   }", theme["muted"]),
        ]
        for i, (num, text, color) in enumerate(rows):
            a = _reveal(t, 0.24 + i * 0.08, 0.24 + i * 0.08 + 0.16)
            if a <= 0:
                continue
            y = 410 + i * 48
            if color in (theme["green"], theme["red"]):
                c.rect(154, y - 5, 1080, 38, color, 0.12 * a, radius=6)
            c.text(164, y, num, 17, "mono", theme["muted"], alpha=a)
            c.text(220, y, text, 22, "mono", color, alpha=a)
        a = _reveal(t, 0.60, 0.82)
        c.text(1500, 400, "+128", 64, FONTS["anton"], theme["green"], alpha=a)
        c.text(1500, 470, "−42", 64, FONTS["anton"], theme["red"], alpha=a)
        c.text(1502, 550, "lines changed", 16, "mono", theme["muted"], alpha=a)
        c.text(164, 770, "[ok] 12 files reviewed  ·  [ok] 0 blockers", 19, "mono",
               theme["green"], alpha=_reveal(t, 0.74, 0.90))

    shot = Shot("c03_diff", "claude-code/diff",
                seconds=SECONDS, still_t=1.0,
                description="Animated diff and review metrics, Anton + mono",
                grain=0.011, vig=0.22,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.025 + 0.035 * _ease(t), 0.5, 0.5)
    return shot


def _c04_prompt_response() -> Shot:
    theme = THEMES["light"]

    def static(c: Canvas):
        _bg(c, theme, False, 104)
        _kicker(c, "CLAUDE CODE  /  WEB 04", 130, 92, theme)
        c.text(130, 105, "Prompt chiaro,", 70, FONTS["play"], theme["ink"])
        c.text(130, 178, "risposta netta.", 70, FONTS["play"], theme["accent"])
        _panel(c, 130, 345, 780, 560, "PROMPT", theme)
        c.rect(1010, 345, 780, 560, "#FBF7EF", 1.0, radius=22)
        c.line(1010, 399, 1790, 399, "#D8CFC0", 1, 1.0)
        c.text(1400, 362, "RESPONSE", 15, "mono", theme["muted"], anchor="ma")
        c.rect(130, 920, 1660, 1, theme["line"], 0.85)

    def anim(c: Canvas, t: float):
        dark = THEMES["dark"]
        left = [
            (">  refactor the auth flow", dark["ink"]),
            (">  keep the public API stable", dark["muted"]),
            (">  add the missing tests", dark["muted"]),
        ]
        _lines(c, 168, 450, left, 22, 48, dark, t, 0.16, 0.11)
        right = [
            ("Ho isolato la sessione,", theme["ink"]),
            ("aggiunto il refresh", theme["ink"]),
            ("e coperto i casi limite.", theme["ink"]),
        ]
        _lines(c, 1050, 450, right, 30, 50, theme, t, 0.38, 0.10, FONTS["play-bold"])
        a = _reveal(t, 0.75, 0.88)
        c.text(1050, 650, "[ok] 14 tests passed", 20, "mono", theme["green"], alpha=a)
        c.text(1050, 690, "no public API changes", 17, "mono", theme["muted"], alpha=a)
        arrow = _reveal(t, 0.28, 0.45)
        c.text(930, 600, "→", 44, FONTS["display"], theme["accent"], alpha=arrow)
        c.text(930, 645, "3.2 s", 14, "mono", theme["muted"], alpha=arrow)

    shot = Shot("c04_prompt_response", "claude-code/prompt-response",
                seconds=SECONDS, still_t=1.0,
                description="Split prompt/response card, Playfair + mono",
                grain=0.008, vig=0.16,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.018 + 0.028 * _ease(t), 0.5, 0.5)
    return shot


def _c05_tool_stack() -> Shot:
    theme = THEMES["dark"]

    def static(c: Canvas):
        _bg(c, theme, True, 105)
        _kicker(c, "CLAUDE CODE  /  WEB 05", 130, 96, theme)
        c.text(130, 205, "Gli strumenti", 80, FONTS["oswald"], theme["ink"])
        c.text(130, 285, "fanno il lavoro.", 80, FONTS["oswald"], theme["accent"])
        c.text(132, 410, "three calls, one clean diff", 22, FONTS["inter"], theme["muted"])

    def anim(c: Canvas, t: float):
        rows = [
            ("read_file", "src/auth/session.ts", "42 ms", theme["blue"]),
            ("run_tests", "vitest --run", "1.8 s", theme["accent"]),
            ("apply_patch", "+128  −42", "ready", theme["green"]),
        ]
        for i, (name, detail, status, accent) in enumerate(rows):
            a = _reveal(t, 0.16 + i * 0.16, 0.16 + i * 0.16 + 0.20)
            if a <= 0:
                continue
            dy = 32 * (1 - a)
            x, y, w, h = 980, 190 + i * 190, 780, 158
            _mini_card(c, x, y, w, h, theme, accent, a, dy)
            c.rect(x + 28, y + dy + 38, 54, 54, accent, 0.15 * a, radius=10)
            c.ellipse(x + 46, y + dy + 46, 18, 18, accent, 0.95 * a)
            c.text(x + 104, y + dy + 30, name, 25, "mono", theme["ink"], alpha=a)
            c.text(x + 104, y + dy + 74, detail, 18, "mono", theme["muted"], alpha=a)
            c.text(x + w - 30, y + dy + 38, status, 17, "mono", accent, alpha=a, anchor="ra")
            c.text(x + w - 30, y + dy + 100, "[ok] done", 14, "mono", theme["green"],
                   alpha=a, anchor="ra")
        rail = _reveal(t, 0.12, 0.80)
        c.line(950, 260, 950, 760, theme["line"], 2, 0.8 * rail)

    shot = Shot("c05_tool_stack", "claude-code/tool-stack",
                seconds=SECONDS, still_t=1.0,
                description="Stacked tool-call cards, Oswald + mono",
                grain=0.010, vig=0.22,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.02 + 0.03 * _ease(t), 0.5, 0.5)
    return shot


def _c06_plan_mode() -> Shot:
    theme = THEMES["light"]

    def static(c: Canvas):
        _bg(c, theme, False, 106)
        _kicker(c, "CLAUDE CODE  /  WEB 06", 130, 92, theme)
        c.text(130, 125, "Pianifica", 78, FONTS["play"], theme["ink"])
        c.text(130, 205, "prima di chiedere.", 78, FONTS["play"], theme["accent"])
        c.rect(130, 335, 1660, 560, "#FBF7EF", 1.0, radius=22)
        c.text(170, 365, "plan mode", 16, "mono", theme["muted"])
        c.line(130, 405, 1790, 405, "#D8CFC0", 1, 1.0)

    def anim(c: Canvas, t: float):
        rows = [
            ("Mappa il contesto", "2 file"),
            ("Isola il rischio", "1 test"),
            ("Applica la patch", "+128 / −42"),
            ("Verifica e chiudi", "0 regressioni"),
        ]
        for i, (label, meta) in enumerate(rows):
            a = _reveal(t, 0.18 + i * 0.13, 0.18 + i * 0.13 + 0.16)
            if a <= 0:
                continue
            y = 445 + i * 92
            c.rect(170, y, 28, 28, theme["line"], 0.9, radius=5)
            check = _reveal(t, 0.32 + i * 0.13, 0.32 + i * 0.13 + 0.16)
            if check > 0:
                c.line(177, y + 15, 183, y + 22, theme["green"], 3, check)
                c.line(183, y + 22, 194, y + 7, theme["green"], 3, check)
            c.text(222, y - 6, label, 30, FONTS["display"], theme["ink"], alpha=a)
            c.text(1620, y - 1, meta, 18, "mono", theme["muted"], alpha=a, anchor="ra")
        a = _reveal(t, 0.78, 0.92)
        c.text(170, 820, "4 steps  ·  2 files  ·  ~3 min", 20, "mono",
               theme["accent"], alpha=a)
        c.rect(170, 862, 1460 * _reveal(t, 0.20, 0.92), 3, theme["accent"], 0.9)

    shot = Shot("c06_plan_mode", "claude-code/plan-mode",
                seconds=SECONDS, still_t=1.0,
                description="Checklist plan mode, Playfair Black + InterDisplay + mono",
                grain=0.007, vig=0.15,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.018 + 0.028 * _ease(t), 0.5, 0.5)
    return shot


def _c07_editorial_terminal() -> Shot:
    theme = THEMES["light"]

    def static(c: Canvas):
        _bg(c, theme, False, 107)
        _kicker(c, "CLAUDE CODE  /  WEB 07", 120, 96, theme)
        c.rect(120, 128, 140, 3, theme["accent"], 0.9)
        _panel(c, 1000, 650, 780, 300, "claude — quick edit", THEMES["dark"])

    def anim(c: Canvas, t: float):
        _headline(c, ["Il codice", "è editoriale."], 120, 190, 118,
                  FONTS["play"], theme, t)
        a = _reveal(t, 0.26, 0.44)
        c.text(124, 500, "La forma è parte del risultato.", 26,
               FONTS["play-italic"], theme["muted"], alpha=a)
        end = _type_line(c, 1034, 735, '$ claude "make it editorial"', 22,
                         "mono", THEMES["dark"]["ink"], t, 0.34, 0.68)
        _cursor(c, end + 8, 737, 24, theme["accent"], t)
        c.text(1034, 805, "[ok] 1 file changed", 20, "mono", theme["green"],
               alpha=_reveal(t, 0.72, 0.86))
        c.text(1034, 845, "+ a little courage", 18, "mono", theme["muted"],
               alpha=_reveal(t, 0.80, 0.94))

    shot = Shot("c07_editorial_terminal", "claude-code/editorial-terminal",
                seconds=SECONDS, still_t=1.0,
                description="Oversized Playfair headline with a small terminal, mono",
                grain=0.007, vig=0.14,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.016 + 0.030 * _ease(t), 0.5, 0.5)
    return shot


def _c08_code_review() -> Shot:
    theme = THEMES["dark"]

    def static(c: Canvas):
        _bg(c, theme, True, 108)
        _kicker(c, "CLAUDE CODE  /  WEB 08", 120, 88, theme)
        c.text(120, 135, "Rivedi,", 72, FONTS["abril"], theme["ink"])
        c.text(120, 205, "non riscrivere.", 72, FONTS["abril"], theme["accent"])
        _panel(c, 120, 300, 1180, 680, "review — src/auth/session.ts", theme)

    def anim(c: Canvas, t: float):
        rows = [
            ("08", "// keep the public API stable", theme["muted"]),
            ("09", "const session = await createSession(user)", theme["ink"]),
            ("10", "if (!session) throw new AuthError()", theme["ink"]),
            ("11", "// refresh the token before returning", theme["green"]),
            ("12", "return { session, expiresAt }", theme["ink"]),
        ]
        for i, (num, text, color) in enumerate(rows):
            a = _reveal(t, 0.18 + i * 0.09, 0.18 + i * 0.09 + 0.16)
            if a <= 0:
                continue
            y = 370 + i * 54
            c.text(164, y, num, 17, "mono", theme["muted"], alpha=a)
            c.text(216, y, text, 22, "mono", color, alpha=a)
        reviews = [
            ("NIT", "Estrarre il refresh in un helper.", theme["yellow"]),
            ("RISK", "Il token scade durante il retry.", theme["red"]),
            ("SHIP", "Nessun blocker. Merge pulito.", theme["green"]),
        ]
        for i, (tag, text, color) in enumerate(reviews):
            a = _reveal(t, 0.40 + i * 0.14, 0.40 + i * 0.14 + 0.18)
            if a <= 0:
                continue
            y = 345 + i * 190
            _mini_card(c, 1340, y, 460, 150, theme, color, a, 20 * (1 - a))
            c.text(1370, y + 28, tag, 15, "mono", color, alpha=a)
            c.text(1370, y + 64, text, 20, FONTS["inter"], theme["ink"], alpha=a)
            c.text(1770, y + 28, "03", 15, "mono", theme["muted"], alpha=a, anchor="ra")
        c.text(1340, 920, "3 comments  ·  0 blockers", 18, "mono",
               theme["muted"], alpha=_reveal(t, 0.82, 0.94))

    shot = Shot("c08_code_review", "claude-code/code-review",
                seconds=SECONDS, still_t=1.0,
                description="Code review rail and verdict cards, Abril + mono",
                grain=0.011, vig=0.22,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.022 + 0.028 * _ease(t), 0.5, 0.5)
    return shot


def _c09_agent_trace() -> Shot:
    theme = THEMES["light"]

    def static(c: Canvas):
        _bg(c, theme, False, 109)
        _kicker(c, "CLAUDE CODE  /  WEB 09", 130, 96, theme)
        c.text(130, 130, "Ogni chiamata", 80, FONTS["helv"], theme["ink"])
        c.text(130, 210, "lascia una traccia.", 80, FONTS["helv"], theme["accent"])
        c.line(180, 650, 1740, 650, theme["line"], 2, 0.55)

    def anim(c: Canvas, t: float):
        nodes = [
            (180, "read", "0.2 s", theme["blue"]),
            (500, "grep", "0.4 s", theme["accent"]),
            (820, "plan", "0.8 s", theme["accent"]),
            (1140, "patch", "1.2 s", theme["green"]),
            (1460, "test", "2.0 s", theme["green"]),
            (1740, "ship", "2.4 s", theme["green"]),
        ]
        draw = _reveal(t, 0.08, 0.70)
        c.line(180, 650, 180 + (1740 - 180) * draw, 650, theme["accent"], 3, 0.95)
        for i, (x, label, time, color) in enumerate(nodes):
            a = _reveal(t, 0.16 + i * 0.12, 0.16 + i * 0.12 + 0.16)
            if a <= 0:
                continue
            c.ellipse(x - 13, 637, 26, 26, color, a)
            c.ellipse(x - 5, 645, 10, 10, theme["paper"], a)
            above = i % 2 == 0
            ty = 570 if above else 685
            c.text(x, ty, label, 25, "mono", theme["ink"], alpha=a, anchor="ma")
            c.text(x, ty + 36, time, 15, "mono", theme["muted"], alpha=a, anchor="ma")
        a = _reveal(t, 0.74, 0.90)
        c.text(130, 820, "6 tool calls  ·  2.4 s  ·  one continuous trace", 20,
               "mono", theme["muted"], alpha=a)
        c.rect(130, 866, 1460 * _reveal(t, 0.12, 0.92), 3, theme["accent"], 0.9)

    shot = Shot("c09_agent_trace", "claude-code/agent-trace",
                seconds=SECONDS, still_t=1.0,
                description="Horizontal agent trace, Helvetica Bold + mono",
                grain=0.007, vig=0.15,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.017 + 0.030 * _ease(t), 0.5, 0.5)
    return shot


def _c10_ship_it() -> Shot:
    theme = THEMES["dark"]

    def static(c: Canvas):
        _bg(c, theme, True, 110)
        _kicker(c, "CLAUDE CODE  /  WEB 10", 140, 90, theme)
        _panel(c, 140, 170, 1640, 740, "release — main", theme)
        c.text(140, 950, "claude code  ·  web motion", 15, "mono", theme["muted"])

    def anim(c: Canvas, t: float):
        rows = [
            ("$ claude ship", theme["ink"]),
            ("[ok] tests      142 passed", theme["green"]),
            ("[ok] typecheck  clean", theme["green"]),
            ("[ok] build      2.4 s", theme["green"]),
        ]
        _lines(c, 190, 235, rows, 22, 42, theme, t, 0.08, 0.10)
        a = _reveal(t, 0.38, 0.62)
        size = 120 + 52 * _ease(a)
        c.text(960, 545, "SHIP IT", size, FONTS["anton"], theme["ink"],
               alpha=a, anchor="mm")
        c.text(960, 625, "all checks passed  ·  ready to merge", 20, "mono",
               theme["green"], alpha=a, anchor="ma")
        bar = _reveal(t, 0.18, 0.94)
        c.rect(190, 790, 1540, 5, theme["line"], 0.9)
        c.rect(190, 790, 1540 * bar, 5, theme["green"], 0.95)
        c.text(190, 825, "main  →  production", 17, "mono", theme["muted"])
        c.text(1730, 825, f"{int(100 * bar):3d}%", 17, "mono", theme["green"], anchor="ra")

    shot = Shot("c10_ship_it", "claude-code/ship-it",
                seconds=SECONDS, still_t=1.0,
                description="Release terminal with a huge Anton SHIP IT, mono",
                grain=0.011, vig=0.23,
                build_static=static, draw_anim=anim)
    shot.camera = lambda t: (1.024 + 0.030 * _ease(t), 0.5, 0.5)
    return shot


BUILDERS = (
    _c01_typewriter, _c02_stream, _c03_diff, _c04_prompt_response,
    _c05_tool_stack, _c06_plan_mode, _c07_editorial_terminal,
    _c08_code_review, _c09_agent_trace, _c10_ship_it,
)


def all_claude_code_shots() -> list[Shot]:
    return [build() for build in BUILDERS]


def claude_code_names() -> list[str]:
    return [shot.name for shot in all_claude_code_shots()]


if __name__ == "__main__":
    for shot in all_claude_code_shots():
        print(shot.name, "|", shot.description)
    print(len(BUILDERS), "shots")
