#!/usr/bin/env python3
"""Author editable native plans for three documentary social-card styles."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/social_reference_styles_v1"
W, H = 1920, 1080
REG = "assets/fonts/Inter-Regular.ttf"
BOLD = "assets/fonts/Inter-Bold.ttf"


def width(text, font, size):
    if not text:
        return 0.0
    raw = subprocess.check_output(["hb-shape", f"--font-size={size}", "--output-format=json", str(ROOT / font), text])
    return sum(g["ax"] for g in json.loads(raw))


def col(hexcolor):
    h = hexcolor.lstrip("#")
    return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)] + [1.0]


def shape(ls, name, x, y, w, h, color, radius=0):
    shp = {"type": "rounded_rect" if radius else "rect", "fill": col(color)}
    if radius:
        shp["radius"] = radius
    ls.append({"id": name, "type": "shape", "shape": shp, "size": [w, h], "position": [x + W / 2, y + H / 2], "start_frame": 0, "duration_frames": 1})


def text(ls, name, value, x, y, size, color, font=REG):
    ls.append({"id": name, "type": "text", "text": value, "size": [max(20, width(value, font, size) + 12), size * 1.5], "position": [x + W / 2, y + H / 2], "style": {"font": font, "font_size": size, "fill": color}, "start_frame": 0, "duration_frames": 1})


def base(name, background="#050505"):
    ls=[]
    shape(ls, "background", 0, 0, W, H, background)
    return ls


def box(ls, name, x, y, w, h, color, radius=0):
    """Shape placed by top-left pixel coordinates on the 1920×1080 canvas."""
    shape(ls, name, x + w / 2 - W / 2, y + h / 2 - H / 2, w, h, color, radius)


def label(ls, name, value, x, y, size, color, font=REG):
    """Place text from a top-left design coordinate using Chronon's centered anchor."""
    box_width = max(20, width(value, font, size) + 16)
    ls.append({"id": name, "type": "text", "text": value,
               "size": [box_width, size * 1.55],
               "position": [x + box_width / 2, y],
               "style": {"font": font, "font_size": size, "fill": color},
               "start_frame": 0, "duration_frames": 1})


def x_post(name, accent=False):
    ls = base(name)
    if accent:
        # Reference 3: black X post, isolated red phrase band and generous margins.
        box(ls, "avatar", 210, 275, 104, 104, "#35302D", 52)
        label(ls, "avatar_initial", "C", 243, 295, 43, "#F4F4F4", BOLD)
        label(ls, "display_name", "Chloe Cole", 338, 275, 39, "#F5F5F5", BOLD)
        label(ls, "verified", "✓", 558, 272, 30, "#1D9BF0", BOLD)
        label(ls, "handle", "@ChloeCole", 338, 322, 33, "#777A7D")
        box(ls, "subscribe_button", 1320, 268, 270, 86, "#F1F3F4", 43)
        label(ls, "subscribe_label", "Subscribe", 1367, 288, 34, "#080808", BOLD)
        box(ls, "red_highlight", 180, 425, 1515, 68, "#F10D12")
        label(ls, "post_copy", "An extremely bad influence for Mr. Beast’s main demographic.", 200, 430, 43, "#FFFFFF")
        label(ls, "timestamp_views", "12:09 AM · Jul 22, 2023 · 95.3K Views", 205, 550, 34, "#71767B")
        divider_y, actions_y = 650, 705
    else:
        # Reference 1: wide, text-led X post with a dark defocused surround.
        box(ls, "avatar", 220, 205, 106, 106, "#383431", 53)
        label(ls, "avatar_initial", "G", 253, 225, 43, "#F4F4F4", BOLD)
        label(ls, "display_name", "Grant", 348, 206, 40, "#F5F5F5", BOLD)
        label(ls, "verified", "✓", 460, 202, 30, "#1D9BF0", BOLD)
        label(ls, "handle", "@grantsglimpse", 348, 253, 34, "#777A7D")
        box(ls, "follow_button", 1380, 205, 210, 82, "#F1F3F4", 41)
        label(ls, "follow_label", "Follow", 1430, 224, 35, "#080808", BOLD)
        label(ls, "post_copy_line_1", "The same woman who called people broke for not buying her $28", 215, 365, 46, "#F5F5F5")
        label(ls, "post_copy_line_2", 'cookies is mad when someone calls her a “moody socialist billionaire”', 215, 425, 46, "#F5F5F5")
        label(ls, "post_copy_followup", "You can't make this up.", 215, 550, 44, "#F5F5F5")
        label(ls, "timestamp_views", "11:20 PM · Jan 27, 2026 · 36.2K Views", 220, 665, 34, "#71767B")
        divider_y, actions_y = 750, 798
    box(ls, "action_divider", 210, divider_y, 1495, 2, "#292929")
    action_labels = ["◯   2", "↻   1", "♡   192", "▱   5", "↥"]
    for i, (x, value) in enumerate(zip([235, 590, 960, 1300, 1650], action_labels)):
        label(ls, f"action_{i}", value, x, actions_y, 33, "#777B80")
    return ls


def youtube_comment():
    ls = base("youtube_comment_highlight")
    # Restrained out-of-focus surround; comment remains the sharp focal plane.
    box(ls, "ambient_left", 0, 0, 240, H, "#161616", 72)
    box(ls, "ambient_right", 1680, 0, 240, H, "#141414", 72)
    box(ls, "comment_red_frame", 115, 380, 1690, 320, "#F10D12")
    box(ls, "comment_black_surface", 130, 395, 1660, 290, "#080808")
    box(ls, "avatar", 145, 430, 120, 120, "#7C18A8", 60)
    label(ls, "avatar_initial", "S", 185, 453, 55, "#FFFFFF")
    label(ls, "comment_author", "@TimelesslyModern", 315, 425, 42, "#F4F4F4", BOLD)
    label(ls, "comment_age", "2 months ago", 820, 428, 38, "#A5A5A5")
    label(ls, "comment_copy", "She wants clout, and thinks disrespecting her partner is the way to do it.", 315, 505, 43, "#F5F5F5")
    for i, (x, value) in enumerate(zip([320, 520, 715, 920], ["Like   22", "Dislike", "♥", "Reply"])):
        label(ls, f"comment_action_{i}", value, x, 600, 35, "#CECECE", BOLD if i == 3 else REG)
    return ls


def write(name, layers):
    plan={"schema":"chronon.render-plan.v3","version":3,"job_id":name,
          "canvas":{"width":W,"height":H,"fps_num":30,"fps_den":1,"duration_frames":1},
          "layers":layers,"output":{"path":name+".mp4","format":"mp4","codec":"h264"}}
    path=OUT/(name+".plan.json"); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n")
    return path


def main():
    plans=[write("x_post_dark",x_post("x_post_dark")),
           write("x_post_red_highlight",x_post("x_post_red_highlight",True)),
           write("youtube_comment_red_frame",youtube_comment())]
    for p in plans: print(p)


if __name__ == "__main__": main()
