#!/usr/bin/env python3
"""Build native Chronon render-plan previews for X Post and YouTube Community Post V1."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/social_post_v1"
W, H = 1920, 1080
REGULAR = "assets/fonts/Inter-Regular.ttf"
BOLD = "assets/fonts/Inter-Bold.ttf"
ICON = "assets/fonts/DejaVuSans.ttf"
AVATAR = "assets/images/people_sample_portrait_b.png"
MEDIA = "assets/images/investigative_journalist_hero.jpg"


def color(value: str) -> list[float]:
    raw = value.lstrip("#")
    return [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def shaped_width(text: str, font: str, size: float) -> float:
    if not text:
        return 0.0
    raw = subprocess.check_output([
        "hb-shape", f"--font-size={size}", "--output-format=json",
        str(ROOT / font), text,
    ])
    return sum(float(glyph["ax"]) for glyph in json.loads(raw))


def wrap(text: str, font: str, size: float, max_width: float) -> list[tuple[str, float]]:
    words = text.split()
    lines: list[tuple[str, float]] = []
    current = ""
    current_width = 0.0
    for word in words:
        candidate = f"{current} {word}".strip()
        width = shaped_width(candidate, font, size)
        if width > max_width and current:
            lines.append((current, current_width))
            current = word
            current_width = shaped_width(word, font, size)
            if current_width > max_width:
                raise ValueError(f"word exceeds text column: {word}")
        else:
            current = candidate
            current_width = width
    if current:
        lines.append((current, current_width))
    return lines


def shape_layer(layers: list[dict], name: str, x: float, y: float,
                width: float, height: float, fill: str, radius: float = 0) -> None:
    geometry = "rounded_rect" if radius else "rect"
    shape = {"type": geometry, "fill": color(fill)}
    if radius:
        shape["radius"] = radius
    layers.append({"id": name, "type": "shape", "shape": shape,
                   "size": [width, height], "position": [x, y],
                   "start_frame": 0, "duration_frames": 1})


def text_layer(layers: list[dict], name: str, text: str, x: float, y: float,
               font: str, size: float, fill: str, width: float | None = None) -> None:
    measured = shaped_width(text, font, size)
    box_width = max(width or 0, measured * 1.16 + 8)
    layers.append({"id": name, "type": "text", "text": text,
                   "size": [box_width, size * 1.4],
                   "position": [x, y],
                   "style": {"font": font, "font_size": size, "fill": fill},
                   "start_frame": 0, "duration_frames": 1})


def image_layer(layers: list[dict], name: str, asset: str,
                x: float, y: float, width: float, height: float, radius: float) -> None:
    layers.append({"id": name, "type": "image", "asset": asset,
                   "size": [width, height], "position": [x - W / 2, y - H / 2],
                   "fit": "cover", "radius": radius, "screen_space": True,
                   "start_frame": 0, "duration_frames": 1})


def build(platform: str, author: str, handle: str, timestamp: str,
          body: str, highlight: str, metrics: list[tuple[str, str]],
          dark: bool, media: str = MEDIA, media_ratio: float = 16 / 9,
          verified: bool = False) -> Path:
    is_x = platform == "x"
    canvas_color = "#000000" if dark else "#F2F2F2"
    card_color = "#000000" if is_x and dark else "#15202B" if is_x else "#212121" if dark else "#FFFFFF"
    ink = "#E7E9EA" if is_x and dark else "#FFFFFF" if is_x else "#F1F1F1" if dark else "#0F0F0F"
    muted = "#71767B" if is_x and dark else "#A6ADB3" if is_x else "#AAAAAA" if dark else "#606060"
    accent = "#1D9BF0" if is_x else "#065FD4" if not dark else "#3EA6FF"
    border = "#2F3336" if is_x and dark else "#38444D" if is_x else "#3F3F3F" if dark else "#E5E5E5"

    card_w, pad, avatar_size = 1080.0, 42.0, 78.0
    body_w = card_w - 2 * pad
    body_size, line_gap = 33.0, 45.0
    body_lines = wrap(body, REGULAR, body_size, body_w)
    body_top = pad + avatar_size + 32
    body_h = len(body_lines) * line_gap
    media_w = body_w if media else 0
    media_h = media_w / media_ratio if media else 0
    media_top = body_top + body_h + (22 if media else 0)
    footer_top = media_top + media_h + (26 if media else 22)
    card_h = footer_top + (82 if is_x else 70) + pad
    card_x, card_y = (W - card_w) / 2, (H - card_h) / 2
    layers: list[dict] = []

    # Backdrop and subtle outline are native shape layers, not a flattened UI plate.
    shape_layer(layers, "social_canvas", W / 2, H / 2, W, H, canvas_color)
    shape_layer(layers, "card_outline", W / 2, H / 2, card_w + 2, card_h + 2,
                border, 18)
    shape_layer(layers, "post_card", W / 2, H / 2, card_w, card_h, card_color, 18)

    avatar_x = card_x + pad + avatar_size / 2
    avatar_y = card_y + pad + avatar_size / 2
    image_layer(layers, "avatar_image", AVATAR, avatar_x, avatar_y,
                avatar_size, avatar_size, avatar_size / 2)
    identity_x = card_x + pad + avatar_size + 22
    author_size = 31.0
    author_width = shaped_width(author, BOLD, author_size)
    text_layer(layers, "author", author, identity_x + author_width / 2,
               card_y + pad + 21, BOLD, author_size, ink)
    if verified:
        badge_x = identity_x + author_width + 18
        shape_layer(layers, "verified_badge", badge_x, card_y + pad + 21,
                    22, 22, accent, 11)
        text_layer(layers, "verified_check", "✓", badge_x, card_y + pad + 21,
                   ICON, 16, "#FFFFFF")
    identity_meta = f"{handle}  ·  {timestamp}" if handle else timestamp
    text_layer(layers, "identity_meta", identity_meta,
               identity_x + shaped_width(identity_meta, REGULAR, 23) / 2,
               card_y + pad + 57, REGULAR, 23, muted)

    body_x = card_x + pad
    for line_index, (line, line_width) in enumerate(body_lines):
        line_top = card_y + body_top + line_index * line_gap
        # This preview uses a native HarfBuzz measurement for the same line
        # geometry that WebTextLayout resolves from FontEngine in the API.
        line_start = body.find(line)
        line_end = line_start + len(line)
        phrase_start = body.find(highlight)
        phrase_end = phrase_start + len(highlight)
        overlap_start, overlap_end = max(line_start, phrase_start), min(line_end, phrase_end)
        if overlap_start < overlap_end:
            local_start = overlap_start - line_start
            local_end = overlap_end - line_start
            prefix = line[:local_start]
            marked = line[local_start:local_end]
            left_width = shaped_width(prefix, REGULAR, body_size)
            mark_width = shaped_width(marked, REGULAR, body_size)
            shape_layer(layers, f"highlight_{line_index}",
                        body_x + left_width + mark_width / 2,
                        line_top + line_gap / 2, mark_width + 8, 36,
                        "#F7D85B", 4)
        text_layer(layers, f"body_line_{line_index}", line,
                   body_x + line_width / 2, line_top + line_gap / 2,
                   REGULAR, body_size, ink, line_width)

    if media:
        image_layer(layers, "attached_media", media, W / 2,
                    card_y + media_top + media_h / 2, media_w, media_h, 16)

    if is_x:
        views = next((value for label, value in metrics if label == "views"), "")
        metadata = timestamp + (f"  ·  {views} views" if views else "")
        text_layer(layers, "timestamp_views", metadata,
                   card_x + pad + shaped_width(metadata, REGULAR, 20) / 2,
                   card_y + footer_top + 18, REGULAR, 20, muted)
        counts = [f"{value} {label}" for label, value in metrics if label != "views" and value]
        action_string = "      ·      ".join(counts)
        if action_string:
            text_layer(layers, "engagement_metrics", action_string,
                       card_x + pad + shaped_width(action_string, REGULAR, 22) / 2,
                       card_y + footer_top + 54, REGULAR, 22, muted)
    else:
        action_string = "    ·    ".join(f"{value} {label}" for label, value in metrics if value)
        if action_string:
            text_layer(layers, "engagement_metrics", action_string,
                       card_x + pad + shaped_width(action_string, REGULAR, 24) / 2,
                       card_y + footer_top + 30, REGULAR, 24, muted)

    job = f"social_{platform}_post_v1"
    plan = {"schema": "chronon.render-plan.v3", "version": 3, "job_id": job,
            "canvas": {"width": W, "height": H, "fps_num": 30,
                       "fps_den": 1, "duration_frames": 1},
            "layers": layers,
            "output": {"path": f"{job}.mp4", "format": "mp4", "codec": "h264"}}
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / f"{job}.plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    return plan_path


def main() -> None:
    assets = (ROOT / AVATAR, ROOT / MEDIA)
    for asset in assets:
        if not asset.is_file():
            raise FileNotFoundError(asset)
    plans = [
        build("x", "Mara Lewis", "@maralewis", "2h",
              "New evidence changes the timeline: the first signal appears months earlier than the official report. We compared the logs, original footage and witness notes.",
              "the first signal appears months earlier",
              [("replies", "128"), ("reposts", "430"), ("likes", "2.7K"), ("views", "83K")],
              dark=True, verified=True),
        build("youtube", "Field Notes", "@fieldnotes", "5 hours ago",
              "We are sharing the full field notes from this week’s investigation. The new video walks through the sources, timeline and what still remains unverified.",
              "what still remains unverified",
              [("likes", "1.2K"), ("comments", "86")], dark=False),
    ]
    for path in plans:
        print(path)


if __name__ == "__main__":
    main()
