#!/usr/bin/env python3
"""Build ten original portrait motion-graphic studies based on the supplied video."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "ChrononTemplate/out/youtube_g9xoKm5DEeU"
OUT = BASE / "animations"
ASSETS = OUT / "assets"
OUT_WIDE = BASE / "animations_16x9"
ASSETS_WIDE = OUT_WIDE / "assets"
W, H, FPS, FRAMES = 1080, 1920, 30, 150
FONT = "ChrononTemplate/assets/fonts/Inter-Medium.ttf"
BOLD = "ChrononTemplate/assets/fonts/Inter-ExtraBold.ttf"
ITALIC = "ChrononTemplate/assets/fonts/PlayfairDisplay-Italic.ttf"


def text_layer(scene_id: str, idx: int, txt: str, x: int, y: int, bw: int, bh: int,
               size: int, color: str = "#F7F6F2", *, font: str = BOLD,
               align: str = "center", italic: bool = False) -> dict:
    begin = min(84, 12 + idx * 25)
    fy = -34 if idx % 2 == 0 else 28
    return {
        "id": f"{scene_id}-text-{idx+1}", "type": "text", "text": txt,
        "size": [bw, bh], "position": [x, y], "start_frame": 0,
        "duration_frames": FRAMES,
        "style": {"font": ITALIC if italic else font, "font_size": size,
                  "min_font_size": max(18, size * .78), "max_font_size": size,
                  "fill": color, "fit_mode": "shrink_only", "text_align": align},
        "opacity": 1.0,
        "animation": {"tracks": [
            {"property": "opacity", "easing": "out_cubic", "keyframes": [
                {"frame": 0, "value": 0}, {"frame": begin, "value": 0},
                {"frame": begin + 17, "value": 1}, {"frame": FRAMES - 1, "value": 1}]},
            {"property": "position_y", "easing": "out_cubic", "keyframes": [
                {"frame": begin, "value": fy}, {"frame": begin + 26, "value": 0},
                {"frame": FRAMES - 1, "value": 0}]},
        ]},
    }


def svg_scene(background: str, content: str, accent: str = "#377BFF") -> str:
    # A quiet fine paper grain and a framed field echo the video's restrained design language.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
    <defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".68" numOctaves="2" seed="17"/><feColorMatrix values=".25 0 0 0 .55 .25 0 0 0 .55 .25 0 0 0 .55 0 0 0 .08 0"/></filter>
    <filter id="glow" x="-.7" y="-.5" width="2.4" height="2"><feGaussianBlur stdDeviation="20"/></filter>
    <linearGradient id="paper" x2="0" y2="1"><stop stop-color="#f5f2ea"/><stop offset="1" stop-color="#ddd9d0"/></linearGradient>
    <linearGradient id="blue" x2="0" y2="1"><stop stop-color="#40a5ff"/><stop offset="1" stop-color="#1749ed"/></linearGradient></defs>
    <rect width="1080" height="1920" fill="{background}"/>
    <rect width="1080" height="1920" filter="url(#grain)" opacity=".42"/>
    {content}
    </svg>'''


SCENES = [
    ("01_caption_emphasis", "Highlighted captions", "#11141a",
     '''<rect x="68" y="100" width="944" height="1720" rx="48" fill="#141821" stroke="#353c48" stroke-width="3"/>
     <path d="M130 1220 Q390 1000 570 1200 T950 1130 V1790 H130Z" fill="#203957" opacity=".65"/>
     <ellipse cx="570" cy="930" rx="225" ry="305" fill="#263344"/><path d="M300 1510 Q328 1220 570 1200 Q810 1230 840 1510V1730H300Z" fill="#192431"/>
     <rect x="120" y="1100" width="840" height="270" rx="20" fill="#030508" opacity=".68"/>''',
     [("Choose what matters", 540, 1115, 850, 100, 57, "#f6f5f1", BOLD),
      ("in a world full of noise.", 540, 1230, 880, 110, 66, "#72a7ff", ITALIC)]),
    ("02_broll_text", "Text over cinematic B-roll", "#1d211f",
     '''<rect width="1080" height="1920" fill="url(#paper)"/>
     <path d="M0 930L150 740 250 900 420 580 600 930 760 690 1080 960V1920H0Z" fill="#55594d"/>
     <path d="M0 1110Q250 1000 460 1160T1080 1100V1920H0Z" fill="#242923"/>
     <circle cx="790" cy="470" r="105" fill="#e2bd7c" opacity=".85"/>
     <rect x="60" y="140" width="960" height="1640" rx="18" fill="none" stroke="#e8e1d4" stroke-width="5" opacity=".55"/>''',
     [("Make room", 540, 270, 820, 150, 92, "#252821", BOLD),
      ("for what matters.", 540, 390, 900, 120, 70, "#285fbd", ITALIC)]),
    ("03_kinetic_type", "Kinetic typography", "#07090d",
     '''<rect x="70" y="130" width="940" height="1660" rx="44" fill="#080a10" stroke="#222a38" stroke-width="3"/>
     <path d="M130 980H950M130 1010H760" stroke="#245bdb" stroke-width="3" opacity=".45"/>
     <circle cx="865" cy="1000" r="155" fill="#103177" opacity=".12" filter="url(#glow)"/>''',
     [("A new", 540, 750, 860, 150, 112, "#f7f7f5", BOLD),
      ("direction", 540, 940, 950, 170, 128, "#5c91ff", ITALIC),
      ("starts with one choice.", 540, 1115, 900, 110, 56, "#e7e8ec", FONT)]),
    ("04_line_text", "Line-led text reveal", "#06080c",
     '''<rect x="56" y="90" width="968" height="1740" rx="46" fill="#05070b" stroke="#222832" stroke-width="3"/>
     <path d="M540 300 C760 440 750 600 525 750 C310 900 335 1045 570 1180 C790 1310 785 1450 540 1615" fill="none" stroke="#0865ff" stroke-width="54" opacity=".5" filter="url(#glow)"/>
     <path d="M540 300 C760 440 750 600 525 750 C310 900 335 1045 570 1180 C790 1310 785 1450 540 1615" fill="none" stroke="url(#blue)" stroke-width="13" stroke-linecap="round"/>
     <circle cx="540" cy="300" r="18" fill="#ecf4ff"/><circle cx="570" cy="1180" r="21" fill="#a4ceff"/>''',
     [("The work of art", 540, 380, 820, 100, 61, "#f5f4f2", FONT),
      ("already exists", 540, 490, 900, 112, 76, "#ffffff", ITALIC),
      ("follow the line", 540, 1440, 720, 90, 54, "#8eb9ff", BOLD)]),
    ("05_line_illustration", "Line and illustration", "#070a10",
     '''<rect x="55" y="88" width="970" height="1744" rx="45" fill="#06090f" stroke="#27303c" stroke-width="3"/>
     <path d="M540 300V530" stroke="#3483ff" stroke-width="9"/><path d="M540 1200V1560" stroke="#3483ff" stroke-width="9"/>
     <circle cx="540" cy="840" r="250" fill="#081d49" stroke="#4d93ff" stroke-width="7"/>
     <path d="M540 650C480 590 390 625 382 720C310 725 292 805 340 865C278 930 315 1010 400 1020C410 1112 493 1135 540 1080C598 1137 682 1107 690 1020C777 1014 810 925 750 865C792 800 760 725 700 715C684 620 598 590 540 650Z" fill="#285fbd" stroke="#90c0ff" stroke-width="6"/>
     <path d="M452 708C405 752 448 795 470 824M610 690C650 733 602 784 588 815M380 885C438 900 428 958 405 982M700 870C647 900 655 953 682 980M525 675C505 740 550 773 535 810M520 862C480 915 514 965 490 1010M585 858C620 908 575 959 610 1005" fill="none" stroke="#8fbaff" stroke-width="13" stroke-linecap="round" opacity=".72"/>
     <circle cx="540" cy="840" r="285" fill="none" stroke="#2c69d7" stroke-width="2" stroke-dasharray="4 22"/>''',
     [("What shapes", 540, 260, 850, 110, 70, "#f7f7f4", FONT),
      ("your life?", 540, 375, 800, 120, 86, "#89baff", ITALIC),
      ("small choices, repeated", 540, 1470, 900, 90, 49, "#e7edf7", FONT)]),
    ("06_quote_card", "Cinematic quote card", "#e7e2d8",
     '''<rect width="1080" height="1920" fill="url(#paper)"/>
     <rect x="82" y="128" width="916" height="1664" rx="20" fill="#f1eee7" stroke="#c9c3b9" stroke-width="2"/>
     <path d="M210 510H870M210 1420H870" stroke="#b9c4d7" stroke-width="3"/>
     <text x="170" y="715" font-family="Georgia" font-size="280" fill="#285ed0">“</text>
     <text x="910" y="1450" font-family="Georgia" font-size="280" fill="#285ed0">”</text>
     <circle cx="540" cy="960" r="360" fill="#ffffff" opacity=".24"/>''',
     [("A meaningful life", 540, 820, 870, 140, 86, "#20242a", BOLD),
      ("begins with attention.", 540, 945, 900, 140, 72, "#285ed0", ITALIC),
      ("A small reminder", 540, 1510, 760, 80, 41, "#666970", FONT)]),
    ("07_center_illustration", "Centered illustration with orbiting ideas", "#f3f0e8",
     '''<rect width="1080" height="1920" fill="url(#paper)"/>
     <circle cx="540" cy="1000" r="310" fill="#e2e9f2" stroke="#d0d9e5" stroke-width="4"/>
     <ellipse cx="540" cy="970" rx="94" ry="126" fill="#2b5fba"/><path d="M360 1330Q390 1125 540 1115Q690 1125 720 1330Z" fill="#2453a6"/>
     <circle cx="540" cy="1000" r="440" fill="none" stroke="#3778d9" stroke-width="4" stroke-dasharray="7 18"/>
     <circle cx="540" cy="560" r="30" fill="#397de1"/><circle cx="160" cy="1220" r="26" fill="#397de1"/><circle cx="920" cy="1220" r="26" fill="#397de1"/>
     <path d="M540 560L360 800M160 1220L300 1130M920 1220L780 1130" stroke="#9aaec9" stroke-width="3"/>''',
     [("One idea.", 540, 275, 840, 120, 88, "#20242a", BOLD),
      ("Many directions.", 540, 390, 900, 130, 74, "#2864c8", ITALIC)]),
    ("08_side_illustration", "Side illustration and copy", "#f1eee6",
     '''<rect width="1080" height="1920" fill="url(#paper)"/>
     <path d="M0 460Q170 340 360 500V1730Q170 1570 0 1710Z" fill="#dce5ef"/>
     <circle cx="225" cy="900" r="104" fill="#3168bd"/><path d="M80 1390Q95 1055 225 1050Q355 1055 370 1390Z" fill="#2856a2"/>
     <path d="M450 700H900M450 740H760" stroke="#9daaba" stroke-width="3"/>
     <rect x="118" y="650" width="214" height="500" rx="105" fill="none" stroke="#fff" stroke-width="10" opacity=".4"/>''',
     [("A different", 690, 700, 640, 120, 74, "#252930", FONT),
      ("point of view", 700, 830, 650, 135, 78, "#285fbd", ITALIC),
      ("can change the story.", 700, 1000, 650, 170, 54, "#30343a", FONT)]),
    ("09_object_text", "Object and text", "#080a10",
     '''<rect x="56" y="90" width="968" height="1740" rx="45" fill="#06080c" stroke="#242a33" stroke-width="3"/>
     <circle cx="540" cy="1010" r="330" fill="#0f1b2c" stroke="#2a3a50" stroke-width="5"/>
     <path d="M540 1010C700 790 850 1060 620 1170C400 1280 330 960 540 880C700 815 730 1000 590 1060C470 1110 440 970 530 955" fill="none" stroke="#4b8fff" stroke-width="11" stroke-linecap="round"/>
     <circle cx="540" cy="1010" r="14" fill="#d9ebff"/>
     <path d="M180 1010H300M780 1010H900" stroke="#315688" stroke-width="3"/>''',
     [("Slow", 540, 490, 760, 120, 88, "#f7f7f3", BOLD),
      ("and steady.", 540, 610, 860, 130, 82, "#81b0ff", ITALIC),
      ("Keep moving forward", 540, 1450, 800, 90, 50, "#d8dee8", FONT)]),
    ("10_graph_explainer", "Minimal graph and label", "#05070b",
     '''<rect x="62" y="95" width="956" height="1730" rx="42" fill="#070a0f" stroke="#222c38" stroke-width="3"/>
     <g stroke="#29323d" stroke-width="2" opacity=".8"><path d="M180 770H900M180 950H900M180 1130H900M180 1310H900M180 1490H900"/><path d="M300 700V1530M480 700V1530M660 700V1530M840 700V1530"/></g>
     <path d="M190 1440L335 1390L415 1390L490 1220L590 1220L665 1030L750 1030L825 820L900 820" fill="none" stroke="#0c57ef" stroke-width="34" opacity=".55" filter="url(#glow)"/>
     <path d="M190 1440L335 1390L415 1390L490 1220L590 1220L665 1030L750 1030L825 820L900 820" fill="none" stroke="#79adff" stroke-width="8" stroke-linejoin="round"/>
     <circle cx="900" cy="820" r="20" fill="#d9e9ff" stroke="#4389ff" stroke-width="8"/>''',
     [("Small steps", 540, 350, 850, 120, 86, "#f6f5f1", BOLD),
      ("build momentum.", 540, 480, 900, 130, 72, "#87b5ff", ITALIC),
      ("A simple visual explanation", 540, 1600, 850, 90, 43, "#b9c0cb", FONT)]),
]

MOTION_DOTS = {
    "04_line_text": (540, 1615, [
        (0, 0, -1315), (18, 140, -1185), (35, 160, -1055), (53, -15, -865),
        (72, -190, -695), (89, -205, -575), (105, 30, -435), (123, 220, -305),
        (137, 245, -165), (149, 0, 0)]),
    "05_line_illustration": (540, 840, [
        (0, 0, -500), (18, 0, -360), (36, 0, -200), (56, 0, 0),
        (78, 0, 0), (100, 0, -15), (125, 0, 0), (149, 0, 0)]),
    "07_center_illustration": (540, 1000, [
        (0, 0, -440), (25, 310, -310), (50, 440, 0), (75, 310, 310),
        (100, 0, 440), (125, -310, 310), (149, -440, 0)]),
    "09_object_text": (540, 1010, [
        (0, 0, -120), (20, 190, -170), (40, 310, -50), (60, 220, 160),
        (80, 0, 230), (100, -205, 160), (120, -280, -20), (140, -150, -135),
        (149, 0, -55)]),
    "10_graph_explainer": (900, 820, [
        (0, -710, 620), (18, -565, 570), (34, -485, 570), (52, -410, 400),
        (70, -310, 400), (88, -235, 210), (106, -150, 210), (126, -75, 0),
        (149, 0, 0)]),
}


def track(prop: str, keys: list[tuple[int, float]], easing: str = "in_out_sine") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    jobs = []
    wide_jobs = []
    for scene_id, title, background, art, lines in SCENES:
        svg = svg_scene(background, art)
        svg_path = ASSETS / f"{scene_id}.svg"
        png_path = ASSETS / f"{scene_id}.png"
        svg_path.write_text(svg, encoding="utf-8")
        subprocess.run(["magick", str(svg_path), "-strip", str(png_path)], check=True)
        layers = [{"id": f"{scene_id}-art", "type": "image",
                   "asset": str(png_path.relative_to(ROOT)).replace("\\", "/"),
                   "size": [W, H], "fit": "cover", "position": [0, 0],
                   "start_frame": 0, "duration_frames": FRAMES,
                   "animation": {"tracks": [track("scale", [(0, 1.02), (72, 1), (149, 1.01)])]}}]
        for idx, (txt, x, y, bw, bh, size, color, font) in enumerate(lines):
            layers.append(text_layer(scene_id, idx, txt, x, y, bw, bh, size, color,
                                     font=font, italic=(font == ITALIC)))
        if scene_id in MOTION_DOTS:
            dot_x, dot_y, path = MOTION_DOTS[scene_id]
            layers.append({"id": f"{scene_id}-moving-blue-marker", "type": "text",
                           "text": "●", "size": [78, 78], "position": [dot_x, dot_y],
                           "start_frame": 0, "duration_frames": FRAMES,
                           "style": {"font": BOLD, "font_size": 48, "min_font_size": 48,
                                      "max_font_size": 48, "fill": "#8dc0ff",
                                      "fit_mode": "shrink_only", "text_align": "center"},
                           "animation": {"tracks": [
                               {"property": "opacity", "easing": "out_cubic", "keyframes": [
                                   {"frame": 0, "value": 0}, {"frame": 8, "value": 1},
                                   {"frame": FRAMES - 1, "value": 1}]},
                               {"property": "position_x", "easing": "in_out_sine",
                                "keyframes": [{"frame": f, "value": x} for f, x, _ in path]},
                               {"property": "position_y", "easing": "in_out_sine",
                                "keyframes": [{"frame": f, "value": y} for f, _, y in path]},
                           ]}})
        plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": scene_id,
                "canvas": {"width": W, "height": H, "fps_num": FPS, "fps_den": 1,
                           "duration_frames": FRAMES}, "layers": layers,
                "output": {"path": f"{scene_id}.mp4", "format": "mp4", "codec": "h264"}}
        plan_path = OUT / f"{scene_id}.plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        jobs.append({"id": scene_id, "style": title, "plan": plan_path.name,
                     "asset": f"assets/{scene_id}.png", "duration_seconds": 5,
                     "canvas": "1080x1920", "fps": FPS})
        ASSETS_WIDE.mkdir(parents=True, exist_ok=True)
        wide_id = f"{scene_id}_16x9"
        bg_svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">',
                  '<defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".72" numOctaves="2" seed="31"/><feColorMatrix values=".25 0 0 0 .5 .25 0 0 0 .5 .25 0 0 0 .5 0 0 0 .1 0"/></filter></defs>',
                  '<rect width="1920" height="1080" fill="#25282d"/>']
        bg_svg += [f'<path d="M{x} 0V1080" stroke="#747a82" stroke-width="1" opacity=".11"/>'
                   for x in range(64, 1920, 64)]
        bg_svg += [f'<path d="M0 {y}H1920" stroke="#747a82" stroke-width="1" opacity=".11"/>'
                   for y in range(56, 1080, 56)]
        bg_svg += ['<rect width="1920" height="1080" filter="url(#grain)" opacity=".18"/>', '</svg>']
        bg_svg_path = ASSETS_WIDE / "charcoal_grid.svg"
        bg_png_path = ASSETS_WIDE / "charcoal_grid.png"
        if not bg_png_path.exists():
            bg_svg_path.write_text("".join(bg_svg), encoding="utf-8")
            subprocess.run(["magick", str(bg_svg_path), "-strip", str(bg_png_path)], check=True)
        portrait_png = ASSETS / f"{scene_id}.png"
        wide_layers = [
            {"id": f"{wide_id}-background", "type": "image",
             "asset": str(bg_png_path.relative_to(ROOT)).replace("\\", "/"),
             "size": [1920, 1080], "fit": "cover", "position": [0, 0],
             "start_frame": 0, "duration_frames": FRAMES},
            {"id": f"{wide_id}-portrait-card", "type": "image",
             "asset": str(portrait_png.relative_to(ROOT)).replace("\\", "/"),
             "size": [608, 1080], "fit": "cover", "position": [0, 0],
             "start_frame": 0, "duration_frames": FRAMES,
             "animation": {"tracks": [track("scale", [(0, 1.035), (72, 1), (149, 1.005)])]}},
        ]
        for text_item in layers[1:]:
            wide_item = json.loads(json.dumps(text_item))
            wide_item["id"] += "-wide"
            wide_item["position"] = [round(656 + text_item["position"][0] * (608 / 1080), 2),
                                     round(text_item["position"][1] * (1080 / 1920), 2)]
            wide_item["size"] = [round(v * (608 / 1080), 2) for v in text_item["size"]]
            for key in ("font_size", "min_font_size", "max_font_size"):
                wide_item["style"][key] = round(wide_item["style"][key] * (608 / 1080), 2)
            for tr in wide_item.get("animation", {}).get("tracks", []):
                if tr["property"] == "position_x":
                    scale = 608 / 1080
                    for kf in tr["keyframes"]:
                        kf["value"] = round(kf["value"] * scale, 2)
                elif tr["property"] == "position_y":
                    scale = 1080 / 1920
                    for kf in tr["keyframes"]:
                        kf["value"] = round(kf["value"] * scale, 2)
            wide_layers.append(wide_item)
        wide_plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": wide_id,
                     "canvas": {"width": 1920, "height": 1080, "fps_num": FPS, "fps_den": 1,
                                "duration_frames": FRAMES}, "layers": wide_layers,
                     "output": {"path": f"{wide_id}.mp4", "format": "mp4", "codec": "h264"}}
        wide_path = OUT_WIDE / f"{wide_id}.plan.json"
        wide_path.write_text(json.dumps(wide_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        wide_jobs.append({"id": wide_id, "style": title, "plan": wide_path.name,
                          "asset": f"assets/{scene_id}.png", "canvas": "1920x1080",
                          "card": "608x1080 centered", "duration_seconds": 5, "fps": FPS})
    (OUT / "manifest.json").write_text(json.dumps({"source": "YouTube g9xoKm5DEeU; style references studied locally",
                                                    "render_backend": "Chronon3d C++ CLI + Vulkan strict + NVENC",
                                                    "animations": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_WIDE / "manifest.json").write_text(json.dumps({"source": "YouTube g9xoKm5DEeU; 16:9 stage for portrait animation designs",
                                                         "render_backend": "Chronon3d C++ CLI + Vulkan strict + NVENC",
                                                         "animations": wide_jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(jobs)} portrait and {len(wide_jobs)} 16:9 Chronon plans")


if __name__ == "__main__":
    main()
