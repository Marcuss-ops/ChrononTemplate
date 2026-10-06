#!/usr/bin/env python3
"""Rebuild the nine Drive screenshot references as animated reading pages.

Every visible pixel is rendered from native Chronon text/color layers. Screenshots
supply text/layout reference only; no screenshot image is an MP4 source layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
DEFAULT_OUT = ROOT / "out/drive_reference_recreations_v1"
DRIVE_FOLDER = "1m0yo6FsidSzI7QIuNVxWIEz8ZEAO6QfR"
DRIVE_UPLOADER = WORKSPACE / "RenderingGen/bin/drive-upload"
DRIVE_OAUTH = WORKSPACE / "RenderingGen/UploadDrive"
WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 150
FONT_REGULAR = "Chronon3d/assets/fonts/Inter-Regular.ttf"
FONT_BOLD = "Chronon3d/assets/fonts/Inter-Bold.ttf"
FONT_SERIF_BOLD = "Chronon3d/assets/fonts/Bodoni72-Bold.ttf"
PIL_REGULAR = WORKSPACE / FONT_REGULAR
PIL_BOLD = WORKSPACE / FONT_BOLD
PIL_SERIF_BOLD = WORKSPACE / FONT_SERIF_BOLD

# The article/excerpt text is transcribed from the screenshots, rather than
# padded with unrelated marketing copy. Highlight phrases are exact substrings.
PAGES = [
    {"prefix": "01_nba_clippers_retire_number", "ref": "01_Screenshot 2026-10-06 at 09-03-24 New Jerseys Coming To The NBA - YouTube.png",
     "brand": "THE SPORTS DESK", "section": "NBA  /  UNIFORMS & LEGACY", "date": "ARTICLE EXCERPT",
     "title": "The Clippers Continue To Disrespect Chris Paul After Allowing Bradley Beal To Wear #3 Immediately After Promising Paul They Would Retire His Number",
     "paragraphs": ["The Clippers Continue To Disrespect Chris Paul After Allowing Bradley Beal To Wear #3 Immediately After Promising Paul They Would Retire His Number"],
     "highlights": [{"text": "Wear #3", "color": "yellow"}, {"text": "Retire His Number", "color": "red"}],
     "sidebar": ["CHRIS PAUL", "BRADLEY BEAL", "JERSEY NO. 3"], "url": "sportsdesk.local/stories/clippers-number-3"},
    {"prefix": "02_nba_specter_definition", "ref": "02_Screenshot 2026-10-06 at 09-02-48 New Jerseys Coming To The NBA - YouTube.png",
     "brand": "WORD NOTES", "section": "WORD OF THE STORY  /  SPECTER", "date": "DICTIONARY ENTRY",
     "title": "A specter", "paragraphs": [
         "A specter (or spectre in British English) means a ghost or a terrifying, lingering source of dread and worry about the future.",
         "Primary meanings",
         "A ghost: A visible, floating spirit or phantom of a dead person.",
         "A feared future event: A mental image or looming worry about something bad that might happen."],
     "highlights": [{"text": "terrifying, lingering source of dread", "color": "yellow"}, {"text": "A feared future event", "color": "red"}],
     "sidebar": ["PRONUNCIATION", "/ˈspek.tər/", "PRIMARY MEANINGS"], "url": "wordnotes.local/entry/specter"},
    {"prefix": "03_nba_specter_uniforms", "ref": "03_Screenshot 2026-10-06 at 09-02-33 New Jerseys Coming To The NBA - YouTube.png",
     "brand": "THE SPORTS DESK", "section": "NBA  /  NEW RELEASE", "date": "LEAGUE NEWS",
     "title": "NBA, Nike announces new Specter uniforms for league's oldest teams",
     "paragraphs": ["NBA, Nike announces new Specter uniforms for league's oldest teams"],
     "highlights": [{"text": "new Specter uniforms", "color": "yellow"}, {"text": "oldest teams", "color": "red"}],
     "sidebar": ["NBA", "NIKE", "UNIFORMS"], "url": "sportsdesk.local/nba/specter-uniforms"},
    {"prefix": "04_harvard_fbi_threat", "ref": "04_Screenshot 2026-10-05 at 12-02-39 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "CASE FILE  /  REPORTED EXCERPT", "date": "SOURCE TEXT",
     "title": "A prerecorded message gave the victims instructions",
     "paragraphs": ["The headphones were used to play a prerecorded message that provided instructions, indicated that the break-in was being performed by a professional group on-site to collect financial debts, and threatened that both victims would be hurt by electric shock or by cutting their faces if either of the two victims did not comply, according to the FBI."],
     "highlights": [{"text": "prerecorded message", "color": "yellow"}, {"text": "both victims would be hurt by electric shock", "color": "red"}],
     "sidebar": ["REPORTED BY", "THE FBI", "EXCERPT"], "url": "longform.local/case-file/reported-excerpt"},
    {"prefix": "05_harvard_stale_clue", "ref": "05_Screenshot 2026-10-05 at 12-02-29 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "CASE FILE  /  INVESTIGATION", "date": "SOURCE TEXT",
     "title": "A detail in the house was already out of date",
     "paragraphs": ["He had been shown a picture of Victim M's ex-fiancée. Certain features were the same as Ms. Victim F's, so we assumed it was the same person.",
                    "There had also been belongings and engagement cards in the house suggesting that Victim M's ex-fiancée was still living there and was Mr. Victim M's fiancée. However, we had previously entered the house some time before, and this information was stale."],
     "highlights": [{"text": "engagement cards", "color": "yellow"}, {"text": "this information was stale", "color": "red"}],
     "sidebar": ["CASE NOTES", "TIMELINE", "EARLIER VISIT"], "url": "longform.local/case-file/investigation-notes"},
    {"prefix": "06_harvard_breakup_turn", "ref": "06_Screenshot 2026-10-05 at 12-02-18 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "CASE FILE  /  WITNESS ACCOUNT", "date": "SOURCE TEXT",
     "title": "“After that, something clicked off in him”",
     "paragraphs": ["Night, dressed in black. Soon after, the couple broke up, and Muller took leave from his job.",
                    "“After that, something clicked off in him,” Zarback recalled. “He just gave in to whatever illness this was.”"],
     "highlights": [{"text": "the couple broke up", "color": "yellow"}, {"text": "something clicked off in him", "color": "red"}],
     "sidebar": ["WITNESS", "ZARBACK", "REPORTED QUOTE"], "url": "longform.local/case-file/witness-account"},
    {"prefix": "07_harvard_marine_trumpet", "ref": "07_Screenshot 2026-10-05 at 12-01-06 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "BACKGROUND  /  EARLY YEARS", "date": "SOURCE TEXT",
     "title": "Three years in the Marine Corps band",
     "paragraphs": ["Muller spent three years playing trumpet in the Marine Corps band at bases in California and Japan, where he also started a nonprofit to teach locals about the Internet."],
     "highlights": [{"text": "three years playing trumpet", "color": "yellow"}, {"text": "California and Japan", "color": "red"}],
     "sidebar": ["MARINE CORPS", "CALIFORNIA", "JAPAN"], "url": "longform.local/background/early-years"},
    {"prefix": "08_harvard_sacramento_family", "ref": "08_Screenshot 2026-10-05 at 12-00-55 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "BACKGROUND  /  FAMILY", "date": "SOURCE TEXT",
     "title": "Muller grew up in the suburbs of Sacramento",
     "paragraphs": ["Muller grew up in the suburbs of Sacramento. His mother Joyce was a middle school English teacher, and his father, Monty, was a school administrator who served as a wrestling coach.",
                    "He has one younger brother, Kent. His parents divorced during his senior year of high school after his father began an extramarital affair."],
     "highlights": [{"text": "suburbs of Sacramento", "color": "yellow"}, {"text": "His parents divorced", "color": "red"}],
     "sidebar": ["SACRAMENTO", "JOYCE  /  MOTHER", "MONTY  /  FATHER"], "url": "longform.local/background/family"},
    {"prefix": "09_harvard_repeat_frame", "ref": "09_Screenshot 2026-10-05 at 12-00-51 The Harvard Lawyer Who Kidnapped His Neighbor - YouTube.png",
     "brand": "LONGFORM READER", "section": "BACKGROUND  /  FAMILY", "date": "SOURCE TEXT  ·  CONTINUED",
     "title": "A family history, revisited",
     "paragraphs": ["Muller grew up in the suburbs of Sacramento. His mother Joyce was a middle school English teacher, and his father, Monty, was a school administrator who served as a wrestling coach.",
                    "He has one younger brother, Kent. His parents divorced during his senior year of high school after his father began an extramarital affair."],
     "highlights": [{"text": "middle school English teacher", "color": "yellow"}, {"text": "extramarital affair", "color": "red"}],
     "sidebar": ["SACRAMENTO", "FAMILY", "CONTINUED"], "url": "longform.local/background/family-contd"},
]

COLORS = {
    "browser": "#E9EBEF", "chrome_text": "#596171", "page": "#FCFBF8",
    "paper_edge": "#DADDE2", "nav": "#F6F6F4", "ink": "#242833",
    "muted": "#737985", "light_rule": "#E2E3E5", "yellow": "#FFE66D",
    "red": "#DF625D", "white": "#FFFFFF", "pill": "#F0F1F2",
}


def rgba(color: str, alpha: float = 1.0) -> list[float]:
    value = color.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]


def track(prop: str, keys: list[tuple[int, Any]], easing: str = "out_cubic") -> dict:
    return {"property": prop, "easing": easing,
            "keyframes": [{"frame": frame, "value": value} for frame, value in keys]}


def rect(layer_id: str, x: float, y: float, width: float, height: float,
         color: str, *, keys: list[dict] | None = None, alpha: float = 1.0) -> dict:
    return {"id": layer_id, "type": "color", "color": rgba(color, alpha),
            "size": [width, height], "position": [x - WIDTH / 2, y - HEIGHT / 2],
            "screen_space": True, "start_frame": 0, "duration_frames": FRAMES,
            **({"animation": {"tracks": keys}} if keys else {})}


def add_rect(layers: list[dict], layer_id: str, x: float, y: float,
             width: float, height: float, color: str, *, keys: list[dict] | None = None,
             alpha: float = 1.0) -> None:
    layers.append(rect(layer_id, x, y, width, height, color, keys=keys, alpha=alpha))


def add_text(layers: list[dict], layer_id: str, text: str, cx: float, cy: float,
             width: float, height: float, size: int, color: str, *, bold: bool = False,
             start: int = 0, delay: int = 0, keys: list[dict] | None = None,
             background: str | None = None, font_asset: str | None = None) -> None:
    layer = native_text(layer_id, text, cx, cy, width, height, size, color,
                        bold=bold, start=start, delay=delay, keys=keys,
                        font_asset=font_asset)
    if background:
        layer["style"]["background"] = {"color": background, "opacity": 0.78,
                                         "radius": 0, "padding": [5, 1]}
    layers.append(layer)


def native_text(layer_id: str, text: str, cx: float, cy: float,
                width: float, height: float, size: int, color: str, *, bold: bool = False,
                start: int = 0, delay: int = 0, keys: list[dict] | None = None,
                align: str = "left", font_asset: str | None = None) -> dict:
    # Text layers in RenderPlan are center-anchored. Positions are native
    # text geometry in canvas pixels; no DOM/browser screenshot is rasterized.
    if keys is None:
        visible = [(0, 0.0), (delay, 0.0), (delay + 8, 1.0), (FRAMES - 1, 1.0)]
        unique = []
        for frame, value in visible:
            if not unique or frame > unique[-1][0]:
                unique.append((frame, value))
            else:
                unique[-1] = (frame, value)
        keys = [track("opacity", unique),
                track("position_y", [(0, 12), (delay + 8, 0), (FRAMES - 1, 0)])]
    return {"id": layer_id, "type": "text", "text": text,
            "position": [cx, cy], "size": [max(36, width), max(30, height)],
            "start_frame": start, "duration_frames": FRAMES,
            "style": {"font": str(font_asset or (FONT_BOLD if bold else FONT_REGULAR)),
                      "font_size": size, "min_font_size": size,
                      "max_font_size": size, "fit_mode": "shrink_only", "fill": color},
            "animation": {"tracks": keys}}


def _font(size: int, bold: bool = False, serif: bool = False):
    path = PIL_SERIF_BOLD if serif else (PIL_BOLD if bold else PIL_REGULAR)
    return ImageFont.truetype(str(path), size)


def wrap_highlighted(text: str, highlight: str | list[dict] | None, font, max_width: float):
    """Wrap text while assigning each token to its exact red/yellow phrase."""
    entries = []
    if isinstance(highlight, str):
        entries = [{"text": highlight, "color": "yellow"}]
    elif highlight:
        entries = highlight
    spans: list[tuple[int, int, str]] = []
    for entry in entries:
        match = re.search(re.escape(entry["text"]), text, flags=re.IGNORECASE)
        if match:
            spans.append((match.start(), match.end(), entry["color"]))
    tokens: list[tuple[str, str | None]] = []
    for match in re.finditer(r"\S+", text):
        color = next((entry_color for start, end, entry_color in spans
                      if match.start() < end and match.end() > start), None)
        tokens.append((match.group(), color))
    lines: list[list[tuple[str, str | None]]] = []
    current: list[tuple[str, str | None]] = []
    for token, selected in tokens:
        candidate = current + [(token, selected)]
        content = " ".join(item[0] for item in candidate)
        if current and font.getlength(content) > max_width:
            lines.append(current)
            current = [(token, selected)]
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def add_line(layers: list[dict], parts: list[tuple[str, str | None]], x: float, y: float,
             font_size: int, paragraph_index: int, line_index: int, page: dict,
             *, heading: bool = False) -> tuple[int, int]:
    font = _font(font_size, bold=heading)
    total_width = font.getlength(" ".join(text for text, _ in parts))
    base_height = int(font_size * 1.65)
    delay = min(96, 16 + paragraph_index * 12 + line_index * 3)
    hi_frame = min(FRAMES - 24, 62 + paragraph_index * 8 + line_index * 2)
    grouped: list[tuple[str, str | None]] = []
    for word, selected_color in parts:
        if grouped and grouped[-1][1] == selected_color:
            grouped[-1] = (grouped[-1][0] + " " + word, selected_color)
        else:
            grouped.append((word, selected_color))
    cursor_x = x
    space = font.getlength(" ")
    for part_index, (phrase, selected) in enumerate(grouped):
        phrase_width = font.getlength(phrase)
        center_x = cursor_x + phrase_width / 2
        text_keys = [track("opacity", [(0, 0), (hi_frame - 2, 0),
                                         (hi_frame + 8, 1), (FRAMES - 1, 1)]),
                     track("scale_x", [(0, 0.96), (hi_frame, 0.96),
                                       (hi_frame + 8, 1.02), (hi_frame + 14, 1),
                                       (FRAMES - 1, 1)])] if selected else None
        if selected:
            plate_id = f"highlight-plate-{selected}-{paragraph_index}-{line_index}-{part_index}"
            plate_width = phrase_width + 18
            plate_height = base_height + 2
            add_rect(layers, plate_id, center_x, y, plate_width, plate_height,
                     COLORS[selected], keys=[track("opacity", [(0, 0), (hi_frame - 2, 0),
                         (hi_frame + 8, 1), (FRAMES - 1, 1)]),
                         track("scale_x", [(0, 0.96), (hi_frame, 0.96),
                             (hi_frame + 8, 1.02), (hi_frame + 14, 1),
                             (FRAMES - 1, 1)])])
        layer_id = (f"highlight-{selected}-{paragraph_index}-{line_index}-{part_index}"
                    if selected else f"copy-{paragraph_index}-{line_index}-{part_index}")
        add_text(layers, layer_id, phrase, center_x, y, phrase_width + 18,
                 base_height, font_size,
                 ("#FFFFFF" if selected == "red" else "#202329") if selected else "#202329",
                 bold=heading or bool(selected), delay=delay + (7 if selected else 0),
                 keys=text_keys)
        cursor_x += phrase_width + space
    return base_height, delay


def build_page(page: dict) -> dict:
    layers: list[dict] = []
    # Restrained browser frame and a centered editorial canvas replace the
    # overly elaborate rails/chrome of the first reading-page treatment.
    add_rect(layers, "browser-surround", WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT, "#E7E8E7")
    add_rect(layers, "browser-topbar", WIDTH / 2, 26, WIDTH, 52, "#F0F0EE")
    for index, color in enumerate(("#F17468", "#E8BD57", "#70BF82")):
        add_rect(layers, f"browser-window-dot-{index}", 128 + index * 22, 29, 10, 10, color)
    add_rect(layers, "browser-address", 960, 26, 1010, 30, "#FAFAF8", alpha=1)
    add_text(layers, "browser-address-text", page["url"], 960, 26, 920, 28, 14, "#777A79")

    paper_left, paper_right = 210, 1710
    paper_width = paper_right - paper_left
    add_rect(layers, "web-page", WIDTH / 2, 554, paper_width, 988, "#FFFEFC")
    add_rect(layers, "masthead-rule", WIDTH / 2, 96, paper_width, 1.5, "#D8D6D1")
    add_text(layers, "site-brand", page["brand"], WIDTH / 2, 72,
             650, 34, 21, "#242424", bold=True, delay=2)
    add_text(layers, "site-nav", "ARTICLES       ARCHIVE       ABOUT", 1400, 72,
             440, 28, 14, "#777570", delay=5)
    add_rect(layers, "article-top-rule", WIDTH / 2, 130, paper_width - 140, 1, "#E7E4DF")
    add_text(layers, "article-section", page["section"], WIDTH / 2, 161,
             1040, 26, 14, "#8A4A40" if "CASE FILE" in page["section"] else "#77736D",
             bold=True, delay=7)

    title_font_size = 38 if len(page["title"]) > 100 else 44 if len(page["title"]) > 60 else 48
    title_font = _font(title_font_size, bold=True, serif=True)
    title_lines = wrap_highlighted(page["title"], None, title_font, 1120)
    title_line_height = int(title_font_size * 1.18)
    title_y = 205
    for line_index, parts in enumerate(title_lines):
        line = " ".join(text for text, _ in parts)
        width = title_font.getlength(line)
        add_text(layers, f"article-title-{line_index}", line, WIDTH / 2,
                 title_y, 1160, title_line_height + 10, title_font_size, "#22211F",
                 bold=True, delay=12 + line_index * 5, font_asset=FONT_SERIF_BOLD)
        title_y += title_line_height
    section_y = 205 + len(title_lines) * title_line_height + 28
    add_text(layers, "article-date", page["date"], WIDTH / 2, section_y,
             640, 25, 13, "#85817A", delay=19)
    add_rect(layers, "article-divider", WIDTH / 2, section_y + 21, 1160, 1.5, "#DEDAD3")

    main_x, main_width = 390, 1140
    body_y = section_y + 53
    paragraph_index = 0
    line_index = 0
    for paragraph_index, paragraph in enumerate(page["paragraphs"]):
        is_heading = paragraph in {"Primary meanings"}
        font_size = 31 if is_heading else 24
        font = _font(font_size, bold=is_heading)
        highlight = [entry for entry in page["highlights"]
                     if entry["text"].casefold() in paragraph.casefold()]
        wrapped = wrap_highlighted(paragraph, highlight, font, main_width)
        for local_line, parts in enumerate(wrapped):
            line_height, _ = add_line(layers, parts, main_x, body_y, font_size,
                                      paragraph_index, local_line, page, heading=is_heading)
            body_y += line_height
            line_index += 1
        body_y += 22 if is_heading else 27

    if body_y > 990:
        raise ValueError(f"{page['prefix']}: article text exceeds the reading column")

    # Editorial folio footer, without sidebar widgets competing with the article.
    add_rect(layers, "page-bottom-rule", WIDTH / 2, 1013, paper_width - 140, 1.5, "#DEDAD3")
    add_text(layers, "page-footer", "SOURCE EXCERPT     ·     READING EDITION", WIDTH / 2, 1038,
             700, 24, 12, "#96918A", delay=66)

    plan = {"schema": "chronon.render-plan.v3", "version": 3,
            "job_id": f"drive_ref_{page['prefix']}",
            "canvas": {"width": WIDTH, "height": HEIGHT, "fps_num": FPS,
                       "fps_den": 1, "duration_frames": FRAMES},
            "layers": layers,
            "output": {"path": f"{page['prefix']}.mp4", "format": "mp4", "codec": "h264"}}
    validate_plan(plan, page)
    return plan


def validate_plan(plan: dict, page: dict) -> None:
    if plan["schema"] != "chronon.render-plan.v3" or plan["canvas"] != {
            "width": WIDTH, "height": HEIGHT, "fps_num": FPS, "fps_den": 1,
            "duration_frames": FRAMES}:
        raise ValueError(f"{page['prefix']}: bad RenderPlan header")
    layers = plan["layers"]
    ids = [layer["id"] for layer in layers]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{page['prefix']}: duplicate layer ids")
    if any(layer["type"] == "image" for layer in layers):
        raise ValueError(f"{page['prefix']}: screenshot image layer forbidden")
    texts = [layer.get("text", "") for layer in layers if layer["type"] == "text"]
    page_copy = re.sub(r"\\s+", " ", " ".join(texts)).casefold()
    title_copy = re.sub(r"\\s+", " ", page["title"]).casefold()
    if title_copy not in page_copy:
        raise ValueError(f"{page['prefix']}: webpage headline missing")
    for highlight in page["highlights"]:
        if not any(highlight["text"].casefold() in paragraph.casefold()
                   for paragraph in page["paragraphs"]):
            raise ValueError(f"{page['prefix']}: highlight is not an exact article substring: {highlight['text']}")
    for layer in layers:
        for motion_track in layer.get("animation", {}).get("tracks", []):
            frames = [key["frame"] for key in motion_track.get("keyframes", [])]
            if len(frames) < 2 or frames != sorted(set(frames)):
                raise ValueError(f"{page['prefix']}/{layer['id']}: malformed animation keyframes")
            if frames[0] != 0 or frames[-1] >= FRAMES:
                raise ValueError(f"{page['prefix']}/{layer['id']}: keyframes escape clip lifetime")
    for color in {entry["color"] for entry in page["highlights"]}:
        selected_runs = [layer.get("text", "") for layer in layers
                         if layer["type"] == "text"
                         and layer["id"].startswith(f"highlight-{color}-")]
        selected_copy = re.sub(r"\\s+", " ", " ".join(selected_runs)).casefold()
        for entry in (item for item in page["highlights"] if item["color"] == color):
            phrase = re.sub(r"\\s+", " ", entry["text"]).casefold()
            if phrase not in selected_copy:
                raise ValueError(f"{page['prefix']}: {color} highlight run missing exact phrase {entry['text']!r}")
        if not any(layer["id"].startswith(f"highlight-plate-{color}-")
                   and layer.get("color") == rgba(COLORS[color]) for layer in layers):
            raise ValueError(f"{page['prefix']}: missing native {color} highlight plate")
    if len(layers) > 48:
        raise ValueError(f"{page['prefix']}: native graph has too many draw layers ({len(layers)} > 48)")


def verify_videos(out: Path) -> list[dict]:
    ffprobe = subprocess.run(["which", "ffprobe"], capture_output=True, text=True, check=True).stdout.strip()
    if not ffprobe:
        raise RuntimeError("ffprobe is required to verify video exports")
    evidence = []
    expected = {f"{page['prefix']}.mp4" for page in PAGES}
    actual = {path.name for path in out.glob("*.mp4") if not path.name.endswith(".partial.mp4")
              and ".smoke." not in path.name}
    if actual != expected:
        raise ValueError(f"MP4 set mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    import numpy as np
    for page in PAGES:
        path = out / f"{page['prefix']}.mp4"
        probe_result = subprocess.run([ffprobe, "-v", "error", "-count_frames", "-show_streams",
            "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=True)
        probe = json.loads(probe_result.stdout)
        stream = next(row for row in probe["streams"] if row["codec_type"] == "video")
        if stream["codec_name"] != "h264" or (stream["width"], stream["height"]) != (WIDTH, HEIGHT):
            raise ValueError(f"{path.name}: expected 1920x1080 H.264")
        if Fraction(stream["avg_frame_rate"]) != FPS or int(stream["nb_read_frames"]) != FRAMES:
            raise ValueError(f"{path.name}: expected {FRAMES} frames at {FPS} fps")
        if abs(float(probe["format"]["duration"]) - 5.0) > 0.06:
            raise ValueError(f"{path.name}: expected five seconds")
        # Decode full-size key frames: color-key pixel thresholds at thumbnail
        # resolution lose saturated yellow/red through H.264 chroma subsampling.
        sample = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
            "select=eq(n\\,70)+eq(n\\,90)+eq(n\\,120),scale=960:540", "-vsync", "0",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, check=True)
        sample_width, sample_height = 960, 540
        frame_bytes = sample_width * sample_height * 3
        if len(sample.stdout) != frame_bytes * 3:
            raise ValueError(f"{path.name}: failed to decode half-resolution highlight frames")
        images = [np.frombuffer(sample.stdout[i * frame_bytes:(i + 1) * frame_bytes],
                               dtype=np.uint8).reshape(sample_height, sample_width, 3) for i in range(3)]
        highlight_frames = {}
        # Read the highlighter backdrop color at each plan-authored highlight
        # box; this avoids counting browser chrome/sidebar accents as article marks.
        plan_document = json.loads((out / f"{page['prefix']}.plan.json").read_text())
        for color in {entry["color"] for entry in page["highlights"]}:
            target = np.array([int(COLORS[color][i:i + 2], 16) for i in (1, 3, 5)])
            boxes = []
            for layer in plan_document["layers"]:
                if not layer["id"].startswith(f"highlight-plate-{color}-"):
                    continue
                # Color layers use center-relative positions, unlike text layers'
                # canvas coordinates. Recover the plate's canvas-space center.
                cx, cy = layer["position"]
                cx += WIDTH / 2
                cy += HEIGHT / 2
                box_width, box_height = layer["size"]
                boxes.append((max(0, int((cy - box_height / 2 - 4) * 0.5)),
                              min(sample_height, int((cy + box_height / 2 + 4) * 0.5)),
                              max(0, int((cx - box_width / 2 - 4) * 0.5)),
                              min(sample_width, int((cx + box_width / 2 + 4) * 0.5))))
            hits = 0
            for page_frame in images:
                frame_hits = 0
                for y0, y1, x0, x1 in boxes:
                    if x0 >= x1 or y0 >= y1:
                        continue
                    region = page_frame[y0:y1, x0:x1].astype(np.int16)
                    # H.264 4:2:0 changes saturated marker RGB values; a
                    # channel-wise tolerance retains color identity without
                    # counting the dark/white glyph foreground.
                    frame_hits += int((np.max(np.abs(region - target), axis=2) < 72).sum())
                hits = max(hits, frame_hits)
            highlight_frames[color] = hits
        highlight_color = "+".join(sorted(highlight_frames))
        highlight_pixels = [highlight_frames[color] for color in sorted(highlight_frames)]
        if any(count < 20 for count in highlight_pixels):
            raise ValueError(f"{path.name}: encoded highlight color missing: {highlight_frames}")
        # Opening-to-settled image delta confirms the article page animates.
        first_last = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
            "select=eq(n\\,8)+eq(n\\,120),scale=160:90", "-vsync", "0",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, check=True)
        small_bytes = 160 * 90 * 3
        if len(first_last.stdout) != small_bytes * 2:
            raise ValueError(f"{path.name}: failed to decode entrance frames")
        a = np.frombuffer(first_last.stdout[:small_bytes], dtype=np.uint8).astype(np.int16)
        b = np.frombuffer(first_last.stdout[small_bytes:], dtype=np.uint8).astype(np.int16)
        page_delta = float(np.abs(a - b).mean())
        if page_delta < 0.25:
            raise ValueError(f"{path.name}: article has no decoded entrance/highlighter motion")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        evidence.append({"file": path.name, "sha256": digest, "bytes": path.stat().st_size,
                         "codec": "h264", "width": WIDTH, "height": HEIGHT,
                         "fps": FPS, "frames": FRAMES, "seconds": 5.0,
                         "highlight_color": highlight_color, "highlight_pixels": highlight_pixels,
                         "page_delta": page_delta})
        print(f"VIDEO_PASS {path.name} 1920x1080/30fps/5s; {highlight_color} highlight_pixels={highlight_pixels}; page_delta={page_delta:.2f}", flush=True)
    (out / "verification.json").write_text(json.dumps({"schema": "chronontemplate.drive-reference-recreations.v2", "videos": evidence}, indent=2) + "\n")
    return evidence


def update_existing_drive_files(out: Path, evidence: list[dict], folder: str) -> None:
    """Replace prior bad exports in place and verify the remote bytes by SHA-256."""
    if folder != DRIVE_FOLDER:
        raise ValueError("replacement upload is restricted to the screenshot source folder")
    if not DRIVE_UPLOADER.is_file():
        raise FileNotFoundError(f"RenderingGen drive-upload not found: {DRIVE_UPLOADER}")
    sys.path.insert(0, str((ROOT / "tools").resolve()))
    from kit.drive import refresh_token
    access_token = refresh_token(DRIVE_OAUTH / "token.json", DRIVE_OAUTH / "credentials.json")
    auth = {"Authorization": f"Bearer {access_token}"}
    # Include trashed entries too: the prior erroneous exports may already be
    # in Drive trash, but replacement must preserve and revive their IDs.
    query = urllib.parse.urlencode({"q": f"'{folder}' in parents",
        "fields": "nextPageToken,files(id,name,mimeType,size,parents,trashed)", "pageSize": 1000,
        "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"})
    url = "https://www.googleapis.com/drive/v3/files?" + query
    existing = []
    while url:
        request = urllib.request.Request(url, headers=auth)
        with urllib.request.urlopen(request, timeout=60) as response:
            listing = json.load(response)
        existing.extend(listing.get("files", []))
        token_page = listing.get("nextPageToken")
        if token_page:
            url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({
                "q": f"'{folder}' in parents",
                "fields": "nextPageToken,files(id,name,mimeType,size,parents,trashed)", "pageSize": 1000,
                "supportsAllDrives": "true", "includeItemsFromAllDrives": "true",
                "pageToken": token_page})
        else:
            url = ""
    by_name: dict[str, list[dict]] = {}
    for row in existing:
        by_name.setdefault(row["name"], []).append(row)
    expected = {record["file"] for record in evidence}
    if expected != {f"{page['prefix']}.mp4" for page in PAGES}:
        raise ValueError("refusing to update Drive until the exact nine-video set is verified")
    replacements = []
    for record in evidence:
        matches = by_name.get(record["file"], [])
        if len(matches) != 1 or matches[0].get("mimeType") != "video/mp4" or folder not in matches[0].get("parents", []):
            raise ValueError(f"expected one previous MP4 in destination folder: {record['file']}")
        replacements.append((record, matches[0]))

    receipt = {"destination_folder": folder, "operation": "replace_existing_in_place", "videos": []}
    for record, previous in replacements:
        path = out / record["file"]
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != record["sha256"]:
            raise ValueError(f"{path.name}: changed after local verification")
        base = f"https://www.googleapis.com/drive/v3/files/{urllib.parse.quote(previous['id'], safe='')}"
        if previous.get("trashed"):
            restore = urllib.request.Request(
                f"{base}?supportsAllDrives=true",
                data=json.dumps({"trashed": False}).encode("utf-8"),
                headers={**auth, "Content-Type": "application/json"}, method="PATCH")
            with urllib.request.urlopen(restore, timeout=60) as response:
                restored = json.load(response)
            if restored.get("id") != previous["id"] or restored.get("trashed"):
                raise ValueError(f"{path.name}: failed to restore the existing Drive file")
        patch = urllib.request.Request(
            f"https://www.googleapis.com/upload/drive/v3/files/{previous['id']}?uploadType=media&supportsAllDrives=true",
            data=payload, headers={**auth, "Content-Type": "video/mp4"}, method="PATCH")
        with urllib.request.urlopen(patch, timeout=180) as response:
            updated = json.load(response)
        if updated.get("id") != previous["id"]:
            raise ValueError(f"{path.name}: Drive replaced the identity instead of updating it")
        with urllib.request.urlopen(urllib.request.Request(base + "?alt=media&supportsAllDrives=true", headers=auth), timeout=180) as response:
            remote = response.read()
        remote_hash = hashlib.sha256(remote).hexdigest()
        if len(remote) != len(payload) or remote_hash != digest:
            raise ValueError(f"{path.name}: remote download SHA-256 verification failed")
        metadata_request = urllib.request.Request(
            base + "?" + urllib.parse.urlencode({"fields": "id,name,mimeType,size,parents,trashed",
                                                 "supportsAllDrives": "true"}), headers=auth)
        with urllib.request.urlopen(metadata_request, timeout=60) as response:
            final_metadata = json.load(response)
        if (final_metadata.get("id") != previous["id"] or final_metadata.get("name") != path.name
                or final_metadata.get("mimeType") != "video/mp4"
                or folder not in final_metadata.get("parents", [])
                or final_metadata.get("trashed")):
            raise ValueError(f"{path.name}: Drive identity, name, parent, or visibility verification failed")
        row = {"file": path.name, "id": previous["id"], "parent": folder,
               "restored_from_trash": bool(previous.get("trashed")),
               "sha256": remote_hash, "bytes": len(remote), "remote_download_verified": True,
               "remote_parent_and_visibility_verified": True}
        receipt["videos"].append(row)
        (out / "upload_manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"DRIVE_REPLACE_PASS file={path.name} id={previous['id']} sha256={remote_hash} bytes={len(remote)}", flush=True)


def build(args: argparse.Namespace) -> None:
    out: Path = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cli: Path = args.cli.resolve()
    if not cli.is_file():
        raise FileNotFoundError(f"Chronon3D CLI not found: {cli}")
    written: list[tuple[dict, Path]] = []
    for page in PAGES:
        plan = build_page(page)
        path = out / f"{page['prefix']}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        result = subprocess.run([str(cli), "validate", "--plan", str(path),
                                 "--assets-root", str(WORKSPACE)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"Chronon validation failed: {path.name}\n{result.stdout}\n{result.stderr}")
        print(f"PLAN_PASS {path.name} native_text={sum(l['type']=='text' for l in plan['layers'])} highlights={sum(l['id'].startswith('highlight-') for l in plan['layers'])}", flush=True)
        written.append((page, path))
    manifest = {"schema": "chronontemplate.web-reading-page-recreations.v1",
        "source_folder": DRIVE_FOLDER, "renderer": "Chronon3D chronon.render-plan.v3",            "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS, "frames": FRAMES},
            "screenshot_images_embedded": False,
        "animations": [{"id": page["prefix"], "reference": page["ref"],
            "plan": path.name, "render": f"{page['prefix']}.mp4", "page_title": page["title"],
            "paragraphs": page["paragraphs"], "highlights": page["highlights"],
            "website_brand": page["brand"], "url": page["url"]} for page, path in written]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if args.validate_only:
        return
    if not args.render_only:
        for page, path in written:
            target = out / f"{page['prefix']}.mp4"
            # Resume only a genuinely complete export; cancelled partials from
            # an earlier interrupted run are always replaced by Chronon.
            if target.is_file():
                probe = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                    "stream=nb_read_frames,codec_name,width,height,avg_frame_rate", "-of", "json", str(target)],
                    capture_output=True, text=True, check=False)
                try:
                    stream = json.loads(probe.stdout)["streams"][0]
                    reusable = (probe.returncode == 0 and target.stat().st_mtime >= path.stat().st_mtime
                        and stream.get("codec_name") == "h264"
                        and stream.get("width") == WIDTH and stream.get("height") == HEIGHT
                        and stream.get("avg_frame_rate") == "30/1"
                        and int(stream.get("nb_read_frames", 0)) == FRAMES)
                except (KeyError, ValueError, IndexError, json.JSONDecodeError):
                    reusable = False
                if reusable:
                    print(f"RENDER_REUSE_COMPLETE {target.name}", flush=True)
                    continue
            print(f"RENDER_WEB_PAGE {target.name}", flush=True)
            # The software backend's RGBA pipe preserves saturated authored
            # article/highlighter colors; native NVENC currently tints those
            # layers green. Vulkan cannot render native text/color layers.
            subprocess.run([str(cli), "render", "--plan", str(path), "--assets-root", str(WORKSPACE),
                "--backend", "software", "--hardware", "none", "--encoder-backend", "pipe",
                "--codec", "h264", "--fps", "30", "--rate-control", "crf", "--crf", "15",
                "-o", str(target)], check=True)
    evidence = verify_videos(out)
    if args.upload:
        update_existing_drive_files(out, evidence, args.drive_folder)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cli", type=Path, default=WORKSPACE / "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--render-only", action="store_true", help="Verify an already rendered complete set")
    parser.add_argument("--upload", action="store_true", help="Replace the nine prior MP4s in-place in the source Drive folder")
    parser.add_argument("--drive-folder", default=DRIVE_FOLDER)
    args = parser.parse_args()
    if args.validate_only and args.upload:
        parser.error("--upload cannot be combined with --validate-only")
    if args.render_only and args.validate_only:
        parser.error("--render-only cannot be combined with --validate-only")
    if args.upload and args.drive_folder != DRIVE_FOLDER:
        parser.error("--upload is restricted to the screenshot source folder")
    try:
        build(args)
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())