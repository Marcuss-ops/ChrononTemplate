#!/usr/bin/env python3
"""Build native, animated RenderPlan recreations of two supplied references."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "ChrononTemplate"
OUT = TEMPLATE / "out/reference_recreations"
ASSET_OUT = OUT / "assets"
FPS = 30
FRAMES = 150
FONT_BOLD = "ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"
FONT_REGULAR = "ChrononTemplate/assets/fonts/Inter-Medium.ttf"
FONT_ITALIC = "ChrononTemplate/assets/fonts/PlayfairDisplay-Italic.ttf"


def rgba(color: str, alpha: float = 1.0) -> list[float]:
    color = color.removeprefix("#")
    return [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def gradient(stops: list[tuple[float, str, float]], *, start=(0, 0), end=(1, 1)) -> dict:
    return {
        "type": "linear", "start": list(start), "end": list(end), "spread": "pad",
        "color_stops": [
            {"position": offset, "color": rgba(color, alpha)}
            for offset, color, alpha in stops
        ],
    }


def radial(stops: list[tuple[float, str, float]]) -> dict:
    return {
        "type": "radial", "center": [0.5, 0.5], "radius": 0.5, "spread": "pad",
        "color_stops": [
            {"position": offset, "color": rgba(color, alpha)}
            for offset, color, alpha in stops
        ],
    }


def track(prop: str, keys: list[tuple[int, float | list[float]]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def shape(id_: str, kind: str, size: tuple[float, float], position: tuple[float, float], *,
          fill=None, stroke=None, opacity=1.0, tracks=None, effects=None, blend="normal", radius=None) -> dict:
    if kind == "ellipse":
        kind, radius = "rounded_rect", min(size) / 2
    payload = {"type": kind}
    if fill is not None:
        payload["fill"] = fill
    if stroke is not None:
        payload["stroke"] = stroke
    if radius is not None:
        payload["radius"] = radius
    return {
        "id": id_, "type": "shape", "size": list(size), "position": list(position),
        "start_frame": 0, "duration_frames": FRAMES, "shape": payload,
        "opacity": opacity, "blend_mode": blend,
        **({"animation": {"tracks": tracks}} if tracks else {}),
        **({"effects": effects} if effects else {}),
    }


def path(id_: str, commands: list[dict], size: tuple[float, float], position: tuple[float, float], *,
         fill=None, stroke=None, opacity=1.0, tracks=None, effects=None, blend="normal") -> dict:
    return shape(id_, "path", size, position,
                 fill=fill, stroke=stroke, opacity=opacity, tracks=tracks,
                 effects=effects, blend=blend) | {"shape": {
                     "type": "path", "path": commands,
                     **({"fill": fill} if fill is not None else {}),
                     **({"stroke": stroke} if stroke is not None else {}),
                 }}


def text(id_: str, value: str, size: tuple[int, int], position: tuple[float, float], *,
         font=FONT_BOLD, font_size=60, color="#FFFFFF", opacity=1.0, tracks=None,
         align="center") -> dict:
    return {
        "id": id_, "type": "text", "text": value, "size": list(size),
        "position": list(position), "start_frame": 0, "duration_frames": FRAMES,
        "style": {"font": font, "font_size": font_size, "min_font_size": max(14, font_size * .82),
                  "max_font_size": font_size, "fill": color,
                  "fit_mode": "shrink_only", "text_align": align},
        "opacity": opacity,
        "animation": {"tracks": tracks or [track("opacity", [(0, 1), (FRAMES - 1, 1)], "linear")]},
    }


def bg(id_: str, color: str, width: int, height: int) -> dict:
    return {"id": id_, "type": "color", "color": rgba(color), "size": [width, height],
            "position": [0, 0], "start_frame": 0, "duration_frames": FRAMES}


def grid(width: int, height: int, *, step: int, color: str, opacity: float, id_: str) -> dict:
    commands = []
    for x in range(step, width, step):
        commands.extend([{"type": "move_to", "point": [x - width / 2, -height / 2]},
                         {"type": "line_to", "point": [x - width / 2, height / 2]}])
    for y in range(step, height, step):
        commands.extend([{"type": "move_to", "point": [-width / 2, y - height / 2]},
                         {"type": "line_to", "point": [width / 2, y - height / 2]}])
    return path(id_, commands, (width, height), (width / 2, height / 2),
                stroke={"color": color, "width": 1.2}, opacity=opacity, blend="screen")


def closed_round_rect(width: float, height: float, radius: float) -> list[dict]:
    left, right, top, bottom = -width / 2, width / 2, -height / 2, height / 2
    c = radius * 0.55228475
    return [
        {"type": "move_to", "point": [left + radius, top]},
        {"type": "line_to", "point": [right - radius, top]},
        {"type": "cubic_to", "control1": [right - radius + c, top], "control2": [right, top + radius - c], "point": [right, top + radius]},
        {"type": "line_to", "point": [right, bottom - radius]},
        {"type": "cubic_to", "control1": [right, bottom - radius + c], "control2": [right - radius + c, bottom], "point": [right - radius, bottom]},
        {"type": "line_to", "point": [left + radius, bottom]},
        {"type": "cubic_to", "control1": [left + radius - c, bottom], "control2": [left, bottom - radius + c], "point": [left, bottom - radius]},
        {"type": "line_to", "point": [left, top + radius]},
        {"type": "cubic_to", "control1": [left, top + radius - c], "control2": [left + radius - c, top], "point": [left + radius, top]},
        {"type": "close"},
    ]


def brain_plan() -> dict:
    w, h = 1920, 1080
    layers = [bg("blue-canvas", "#2145F5", w, h)]
    layers.append(shape("blue-aura", "ellipse", (950, 640), (1000, 700),
                        fill=rgba("#6971FF"), blend="screen", opacity=.11,
                        tracks=[track("scale", [(0, .96), (75, 1.02), (149, .97)], "in_out_sine")]))
    layers.append(grid(w, h, step=112, color="#90A5FF", opacity=.19, id_="blue-grid"))
    layers.append(text("title-claude", "Claude come un", (920, 155), (565, 160),
                       font=FONT_BOLD, font_size=112,
                       tracks=[track("opacity", [(0, 0), (25, 1), (149, 1)]),
                               track("position_y", [(0, 195), (42, 160), (149, 160)])]))
    layers.append(text("title-brain", "cervello", (730, 175), (1395, 156),
                       font=FONT_ITALIC, font_size=128,
                       tracks=[track("opacity", [(0, 0), (35, 1), (149, 1)]),
                               track("position_x", [(0, 1450), (50, 1395), (149, 1395)])]))

    # Layered pink sculptural silhouette; all lobes and grooves remain native paths.
    brain_pulse = [track("opacity", [(0, 0), (31, 1), (149, 1)]),
                   track("scale", [(0, .76), (56, 1.04), (82, 1), (149, 1)], "out_back"),
                   track("rotation_z", [(0, -4), (63, 1), (105, 0), (149, 0)], "in_out_sine")]
    layers.append(shape("brain-sculpture", "ellipse", (490, 350), (960, 680),
                        fill=rgba("#F36CB6"), stroke={"color": "#FFB9E4", "width": 3}, tracks=brain_pulse))
    for index, (size, position, color) in enumerate([
        ((230, 205), (829, 650), "#FF96CF"), ((240, 215), (966, 590), "#FF9BD3"),
        ((235, 207), (1098, 650), "#F975BD"),
    ]):
        layers.append(shape(f"brain-lobe-{index + 1}", "ellipse", size, position,
                            fill=rgba(color), opacity=.82, tracks=brain_pulse))
    # Pink raised folds and fissures across the brain lobes.
    folds = [
        ([{"type": "move_to", "point": [-205, 43]}, {"type": "cubic_to", "control1": [-148, -5], "control2": [-172, -81], "point": [-116, -151]}], 17),
        ([{"type": "move_to", "point": [-102, 119]}, {"type": "cubic_to", "control1": [-61, 43], "control2": [-107, -12], "point": [-47, -78]}, {"type": "cubic_to", "control1": [-9, -120], "control2": [-28, -155], "point": [2, -198]}], 18),
        ([{"type": "move_to", "point": [44, 151]}, {"type": "cubic_to", "control1": [111, 99], "control2": [54, 32], "point": [113, -7]}, {"type": "cubic_to", "control1": [162, -37], "control2": [129, -99], "point": [185, -148]}], 19),
        ([{"type": "move_to", "point": [-257, 30]}, {"type": "cubic_to", "control1": [-233, 82], "control2": [-202, 89], "point": [-166, 84]}], 10),
        ([{"type": "move_to", "point": [68, -190]}, {"type": "cubic_to", "control1": [98, -132], "control2": [61, -102], "point": [77, -67]}], 11),
    ]
    fold_commands = [command for commands, _ in folds for command in commands]
    layers.append(path("brain-folds", fold_commands, (660, 520), (960, 672),
                       stroke={"color": "#D92F9B", "width": 15}, opacity=.58,
                       tracks=[track("opacity", [(0, 0), (47, .58), (149, .58)])]))
    fold_highlights = [command for commands, _ in folds[:3] for command in commands]
    layers.append(path("brain-fold-highlights", fold_highlights, (660, 520), (955, 665),
                       stroke={"color": "#FFC5E8", "width": 5}, opacity=.72,
                       tracks=[track("opacity", [(0, 0), (55, .72), (149, .72)])]))

    # The white radial mark echoes the logo-like spark at the center of the reference.
    spark_commands = []
    for index in range(12):
        angle = index * 30
        import math
        a = math.radians(angle)
        inner, outer = (24, 130 if index % 2 == 0 else 104)
        p0 = [math.cos(a) * inner, math.sin(a) * inner]
        p1 = [math.cos(a) * outer, math.sin(a) * outer]
        spark_commands.extend([{"type": "move_to", "point": p0}, {"type": "line_to", "point": p1}])
    layers.append(path("brain-spark-rays", spark_commands, (310, 310), (960, 672),
                       stroke={"color": "#FFF4FF", "width": 15}, opacity=.95,
                       tracks=[track("opacity", [(0, 0), (45, .95), (149, .95)]),
                               track("rotation_z", [(0, -8), (78, 4), (149, 0)], "in_out_sine")]))
    layers.append(shape("brain-spark-center", "ellipse", (28, 28), (960, 672), fill=rgba("#FFF4FF"),
                        tracks=[track("scale", [(0, .2), (48, 1.35), (70, 1), (149, 1.1)], "out_back")]))
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "reference_claude_brain",
        "canvas": {"width": w, "height": h, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": layers, "output": {"path": "reference_claude_brain.mp4", "format": "mp4", "codec": "h264"},
    }


def rock_shape(id_: str, center: tuple[float, float], scale: float, seed: int) -> list[dict]:
    w, h = 260 * scale, 160 * scale
    points = [
        {"type": "move_to", "point": [-w * .48, h * .20]},
        {"type": "line_to", "point": [-w * .33, -h * .27]},
        {"type": "line_to", "point": [-w * .12, -h * .48]},
        {"type": "line_to", "point": [w * .15, -h * .38]},
        {"type": "line_to", "point": [w * .40, -h * .19]},
        {"type": "line_to", "point": [w * .48, h * .14]},
        {"type": "line_to", "point": [w * .19, h * .40]},
        {"type": "line_to", "point": [-w * .23, h * .37]},
        {"type": "close"},
    ]
    return [path(f"{id_}-body", points, (w, h), center, fill=rgba("#737C70"),
                 stroke={"color": "#BBC3B2", "width": 2},
                 tracks=[track("opacity", [(0, 0), (40 + seed * 8, 1), (149, 1)]),
                         track("scale", [(0, .72), (60 + seed * 8, 1.04), (82 + seed * 8, 1), (149, 1)], "out_back")])]


def curve_plan() -> dict:
    w, h = 1080, 1920
    layers = [bg("charcoal-board", "#25282D", w, h),
              grid(w, h, step=94, color="#596069", opacity=.25, id_="outer-grid")]
    card_w, card_h = 1010, 1846
    layers.append(shape("black-portrait-card", "rounded_rect", (card_w, card_h), (w / 2, h / 2),
                        fill=rgba("#030405"), stroke={"color": "#111318", "width": 2}, radius=52))

    layers.append(text("phrase-work", "The work of art", (850, 90), (540, 250),
                       font=FONT_REGULAR, font_size=59,
                       tracks=[track("opacity", [(0, 0), (20, 1), (149, 1)]),
                               track("position_y", [(0, 290), (38, 250), (149, 250)])]))
    layers.append(text("phrase-exists", "already exists", (880, 92), (540, 333),
                       font=FONT_ITALIC, font_size=70,
                       tracks=[track("opacity", [(0, 0), (32, 1), (149, 1)]),
                               track("scale", [(0, .94), (48, 1), (149, 1)])]))

    curve = [
        {"type": "move_to", "point": [35, -610]},
        {"type": "cubic_to", "control1": [180, -490], "control2": [226, -382], "point": [102, -272]},
        {"type": "cubic_to", "control1": [-39, -147], "control2": [-270, -90], "point": [-245, 34]},
        {"type": "cubic_to", "control1": [-222, 178], "control2": [8, 126], "point": [199, 247]},
        {"type": "cubic_to", "control1": [315, 328], "control2": [241, 438], "point": [73, 505]},
        {"type": "cubic_to", "control1": [-68, 560], "control2": [-251, 575], "point": [-226, 703]},
        {"type": "cubic_to", "control1": [-201, 820], "control2": [-41, 861], "point": [98, 927]},
    ]
    linepos = (540, 1024)
    # Broad neon bloom, electric blue body, and a fine light-catching core.
    for id_, color, width, opacity in [
        ("s-curve-glow", "#0757FF", 48, .30),
        ("s-curve-body", "#3C8BFF", 13, .98),
    ]:
        layers.append(path(id_, curve, (650, 1640), linepos,
                           stroke={"color": color, "width": width}, opacity=opacity,
                           tracks=[track("opacity", [(0, 0), (29, opacity), (149, opacity)]),
                                   track("scale", [(0, .96), (85, 1.02), (149, 1)], "in_out_sine")], blend="screen"))
    # Four blue anchor nodes connect the phrase to each stone.
    nodes = [(300, 735), (770, 1010), (330, 1335), (754, 1608)]
    for index, (x, y) in enumerate(nodes):
        layers.append(shape(f"curve-node-{index + 1}", "ellipse", (32, 32), (x, y),
                            fill=rgba("#071329"), stroke={"color": "#2783FF", "width": 6},
                            tracks=[track("opacity", [(0, 0), (42 + index * 8, 1), (149, 1)]),
                                    track("scale", [(0, .3), (42 + index * 8, 1), (149, 1)], "out_back")]))

    # Small editorial phrases sit alternately beside the illuminated path.
    layers.append(text("phrase-and-i-have-to", "and I have to", (390, 60), (288, 708),
                       font=FONT_REGULAR, font_size=49, align="left",
                       tracks=[track("opacity", [(0, 0), (54, 1), (149, 1)]),
                               track("position_x", [(0, 240), (74, 288), (149, 288)])]))
    layers.append(text("phrase-take-away", "take away", (360, 60), (790, 1035),
                       font=FONT_REGULAR, font_size=51,
                       tracks=[track("opacity", [(0, 0), (76, 1), (149, 1)]),
                               track("position_x", [(0, 840), (97, 790), (149, 790)])]))
    layers.append(text("phrase-the-rock", "the rock", (370, 76), (295, 1393),
                       font=FONT_ITALIC, font_size=65, align="left",
                       tracks=[track("opacity", [(0, 0), (105, 1), (149, 1)]),
                               track("position_y", [(0, 1430), (124, 1393), (149, 1393)])]))

    placements = [(300, 560, .86), (770, 915, .92), (300, 1245, .84), (760, 1525, .9)]
    for index, (x, y, scale) in enumerate(placements):
        layers.extend(rock_shape(f"moon-rock-{index + 1}", (x, y), scale, index))
    return {
        "schema": "chronon.render-plan.v3", "version": 3, "job_id": "reference_art_rock_curve",
        "canvas": {"width": w, "height": h, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
        "layers": layers, "output": {"path": "reference_art_rock_curve.mp4", "format": "mp4", "codec": "h264"},
    }


def svg_png(filename: str, source: str, width: int, height: int) -> str:
    ASSET_OUT.mkdir(parents=True, exist_ok=True)
    svg_path = ASSET_OUT / filename.replace(".png", ".svg")
    png_path = ASSET_OUT / filename
    svg_path.write_text(source, encoding="utf-8")
    subprocess.run(["magick", str(svg_path), "-resize", f"{width}x{height}!", str(png_path)], check=True)
    return f"ChrononTemplate/out/reference_recreations/assets/{filename}"


def artwork_brain_png() -> str:
    w, h = 1920, 1080
    grid_lines = []
    for x in range(0, w + 1, 112):
        grid_lines.append(f'<path d="M{x} 0V{h}" stroke="#A9B7FF" stroke-opacity=".17" stroke-width="2"/>')
    for y in range(0, h + 1, 112):
        grid_lines.append(f'<path d="M0 {y}H{w}" stroke="#A9B7FF" stroke-opacity=".17" stroke-width="2"/>')
    rays = []
    for i in range(12):
        angle = math.radians(i * 30)
        radius = 125 if i % 2 == 0 else 104
        x1, y1 = 960 + math.cos(angle) * 22, 665 + math.sin(angle) * 22
        x2, y2 = 960 + math.cos(angle) * radius, 665 + math.sin(angle) * radius
        rays.append(f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
      <defs>
        <radialGradient id="halo"><stop stop-color="#8F83FF" stop-opacity=".26"/><stop offset="1" stop-color="#2145F5" stop-opacity="0"/></radialGradient>
        <linearGradient id="brain" x1=".08" y1=".05" x2=".92" y2=".95"><stop stop-color="#FFB5DC"/><stop offset=".48" stop-color="#FF79C4"/><stop offset="1" stop-color="#E949A9"/></linearGradient>
        <linearGradient id="lobe" x1="0" y1="0" x2=".9" y2="1"><stop stop-color="#FFD1EB" stop-opacity=".9"/><stop offset="1" stop-color="#F64BAE" stop-opacity=".2"/></linearGradient>
        <filter id="soft" x="-.35" y="-.35" width="1.7" height="1.7"><feGaussianBlur stdDeviation="38"/></filter>
        <filter id="shadow" x="-.25" y="-.25" width="1.5" height="1.5"><feDropShadow dx="0" dy="22" stdDeviation="18" flood-color="#9D196E" flood-opacity=".38"/></filter>
      </defs>
      <rect width="100%" height="100%" fill="#2145F5"/>
      <ellipse cx="980" cy="650" rx="650" ry="410" fill="url(#halo)"/>
      {''.join(grid_lines)}
      <ellipse cx="960" cy="685" rx="330" ry="205" fill="#FF4BB8" fill-opacity=".34" filter="url(#soft)"/>
      <g filter="url(#shadow)">
        <path d="M675 703 C636 647 660 568 719 539 C706 456 779 396 862 424 C910 359 1002 375 1039 435 C1110 388 1201 432 1205 502 C1292 507 1336 588 1304 657 C1332 725 1283 800 1207 807 C1172 873 1085 891 1024 852 C948 892 866 868 838 820 C759 836 687 784 675 703Z" fill="url(#brain)" stroke="#FFC1E7" stroke-width="5"/>
        <path d="M717 628 C768 591 742 516 807 477 C851 451 883 464 906 491 M867 813 C822 754 858 698 827 651 C804 618 785 588 798 552 M1018 838 C1057 786 1011 739 1057 692 C1093 655 1111 609 1084 567 M1191 770 C1145 742 1166 686 1217 658 C1251 640 1261 598 1241 565 M969 451 C938 507 979 541 940 594 C909 635 917 688 952 711" fill="none" stroke="#DA379E" stroke-opacity=".68" stroke-width="18" stroke-linecap="round"/>
        <path d="M720 615 C766 578 745 520 809 482 M872 805 C836 756 867 702 838 657 M1028 829 C1061 780 1023 741 1065 698 M1188 760 C1151 736 1175 691 1218 665" fill="none" stroke="#FFD7EF" stroke-opacity=".88" stroke-width="6" stroke-linecap="round"/>
        <path d="M919 473 C953 450 980 463 996 488 C1024 464 1054 474 1065 501 C1094 496 1114 521 1101 546 C1125 567 1114 599 1086 606 C1080 637 1046 649 1023 633 C998 656 965 642 963 615 C932 609 921 578 940 557 C919 536 929 502 951 495Z" fill="url(#lobe)" opacity=".48"/>
      </g>
      <g fill="none" stroke="#FFF5FF" stroke-width="15" stroke-linecap="round">{''.join(rays)}</g>
      <circle cx="960" cy="665" r="13" fill="#FFF5FF"/>
    </svg>'''
    return svg_png("claude_brain_art.png", svg, w, h)


def artwork_curve_png() -> str:
    w, h = 1080, 1920
    grid_lines = []
    for x in range(22, w, 94):
        grid_lines.append(f'<path d="M{x} 0V{h}" stroke="#626872" stroke-opacity=".25"/>')
    for y in range(22, h, 94):
        grid_lines.append(f'<path d="M0 {y}H{w}" stroke="#626872" stroke-opacity=".25"/>')
    rock_groups = []
    placements = [(292, 574, .88), (784, 954, .94), (302, 1283, .84), (778, 1570, .91)]
    for i, (x, y, s) in enumerate(placements):
        rock_groups.append(f'''<g transform="translate({x} {y}) scale({s})" filter="url(#rockshadow)">
          <path d="M-122 34 L-97 -15 L-62 -49 L-24 -72 L22 -63 L67 -47 L105 -15 L121 22 L83 52 L30 64 L-31 58 L-89 62Z" fill="url(#stone{i})" stroke="#B7C0AF" stroke-opacity=".65" stroke-width="3"/>
          <path d="M-87 12 L-61 -32 L-24 -55 L-2 -37 L-31 7 L-68 36Z" fill="#D5D7C8" fill-opacity=".36"/>
          <path d="M15 -52 L55 -37 L90 -10 L64 4 L38 -11Z" fill="#EBE8D7" fill-opacity=".28"/>
          <path d="M-80 40 L-34 23 L5 35 L35 58 L-33 58Z" fill="#353C39" fill-opacity=".52"/>
        </g>''')
    stone_defs = ''.join(
        f'<linearGradient id="stone{i}" x1="0" y1="0" x2=".75" y2="1"><stop stop-color="#D8DAC9"/><stop offset=".45" stop-color="#9AA18F"/><stop offset="1" stop-color="#535B53"/></linearGradient>'
        for i in range(4))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
      <defs><filter id="blueglow" x="-.3" y="-.1" width="1.6" height="1.2"><feGaussianBlur stdDeviation="17"/></filter>
      <filter id="rockshadow" x="-.3" y="-.3" width="1.6" height="1.8"><feDropShadow dx="0" dy="12" stdDeviation="11" flood-color="#000" flood-opacity=".9"/></filter>
      {stone_defs}</defs>
      <rect width="100%" height="100%" fill="#25282D"/>{''.join(grid_lines)}
      <rect x="31" y="31" width="1018" height="1858" rx="55" fill="#030405" stroke="#111419" stroke-width="4"/>
      <path d="M574 381 C728 492 756 578 657 674 C522 804 310 827 329 954 C350 1090 601 1052 790 1193 C907 1280 841 1393 650 1454 C488 1505 308 1537 330 1645 C348 1744 519 1795 670 1858" fill="none" stroke="#0757FF" stroke-width="54" stroke-linecap="round" stroke-linejoin="round" opacity=".8" filter="url(#blueglow)"/>
      <path d="M574 381 C728 492 756 578 657 674 C522 804 310 827 329 954 C350 1090 601 1052 790 1193 C907 1280 841 1393 650 1454 C488 1505 308 1537 330 1645 C348 1744 519 1795 670 1858" fill="none" stroke="#126BFF" stroke-width="21" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M574 381 C728 492 756 578 657 674 C522 804 310 827 329 954 C350 1090 601 1052 790 1193 C907 1280 841 1393 650 1454 C488 1505 308 1537 330 1645 C348 1744 519 1795 670 1858" fill="none" stroke="#82B7FF" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
      <g fill="#071329" stroke="#2783FF" stroke-width="9"><circle cx="477" cy="759" r="24"/><circle cx="773" cy="1081" r="24"/><circle cx="462" cy="1457" r="24"/><circle cx="754" cy="1720" r="24"/></g>
      {''.join(rock_groups)}
    </svg>'''
    return svg_png("art_rock_curve_art.png", svg, w, h)


def image_layer(id_: str, asset: str, width: int, height: int, *, fade_end=25) -> dict:
    return {"id": id_, "type": "image", "asset": asset, "size": [width, height],
            "fit": "cover", "position": [0, 0], "start_frame": 0, "duration_frames": FRAMES,
            "animation": {"tracks": [track("opacity", [(0, 0), (fade_end, 1), (149, 1)]),
                                     track("scale", [(0, 1.015), (80, 1), (149, 1.01)], "in_out_sine")]}}


def brain_plan() -> dict:
    w, h = 1920, 1080
    layers = [image_layer("brain-artwork", artwork_brain_png(), w, h),
              text("title-claude", "Claude come un", (920, 155), (565, 160), font=FONT_BOLD,
                   font_size=112, tracks=[track("opacity", [(0, 0), (25, 1), (149, 1)]),
                                         track("position_y", [(0, 35), (42, 0), (149, 0)])]),
              text("title-brain", "cervello", (730, 175), (1395, 156), font=FONT_ITALIC,
                   font_size=128, tracks=[track("opacity", [(0, 0), (35, 1), (149, 1)]),
                                         track("position_x", [(0, 55), (50, 0), (149, 0)])])]
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": "reference_claude_brain",
            "canvas": {"width": w, "height": h, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers, "output": {"path": "reference_claude_brain.mp4", "format": "mp4", "codec": "h264"}}


def curve_plan() -> dict:
    w, h = 1080, 1920
    layers = [image_layer("rock-curve-artwork", artwork_curve_png(), w, h, fade_end=22),
              text("phrase-work", "The work of art", (850, 90), (540, 250), font=FONT_REGULAR,
                   font_size=59, tracks=[track("opacity", [(0, 0), (20, 1), (149, 1)]),
                                        track("position_y", [(0, 40), (38, 0), (149, 0)])]),
              text("phrase-exists", "already exists", (880, 92), (540, 333), font=FONT_ITALIC,
                   font_size=70, tracks=[track("opacity", [(0, 0), (32, 1), (149, 1)]),
                                         track("scale", [(0, .94), (48, 1), (149, 1)])]),
              text("phrase-and-i-have-to", "and I have to", (390, 60), (288, 708), font=FONT_REGULAR,
                   font_size=49, align="left", tracks=[track("opacity", [(0, 0), (54, 1), (149, 1)]),
                                                       track("position_x", [(0, 48), (74, 0), (149, 0)])]),
              text("phrase-take-away", "take away", (360, 60), (790, 1035), font=FONT_REGULAR,
                   font_size=51, tracks=[track("opacity", [(0, 0), (76, 1), (149, 1)]),
                                         track("position_x", [(0, -50), (97, 0), (149, 0)])]),
              text("phrase-the-rock", "the rock", (370, 76), (295, 1393), font=FONT_ITALIC,
                   font_size=65, align="left", tracks=[track("opacity", [(0, 0), (105, 1), (149, 1)]),
                                                        track("position_y", [(0, 37), (124, 0), (149, 0)])])]
    return {"schema": "chronon.render-plan.v3", "version": 3, "job_id": "reference_art_rock_curve",
            "canvas": {"width": w, "height": h, "fps_num": FPS, "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers, "output": {"path": "reference_art_rock_curve.mp4", "format": "mp4", "codec": "h264"}}


def build_all() -> list[dict]:
    plans = [brain_plan(), curve_plan()]
    for plan in plans:
        ids = [layer["id"] for layer in plan["layers"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate layer id in {plan['job_id']}")
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "chronontemplate.reference-recreations.v1", "animations": []}
    for plan in build_all():
        output = args.out / f"{plan['job_id']}.plan.json"
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["animations"].append({"id": plan["job_id"], "plan": output.name,
                                       "width": plan["canvas"]["width"], "height": plan["canvas"]["height"],
                                       "duration_frames": FRAMES, "fps": FPS})
        print(output)
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
