#!/usr/bin/env python3
"""Build a Chronon preview showing four animated reveals of the Scene 03 still."""
from __future__ import annotations

import json
from pathlib import Path

W, H, FPS = 854, 480, 30
SEGMENT = 90
TOTAL = SEGMENT * 4
SOURCE = Path("/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Scene03_Seated_Desk/Composition_Preview.png")
OUT = SOURCE.parent / "Photo_Reveal_Variants"
FONT = Path(__file__).resolve().parents[3] / "Chronon3d/assets/fonts/Inter-Bold.ttf"


def track(prop: str, keys: list[tuple[int, float]]) -> dict:
    return {"property": prop, "easing": "in_out_cubic",
            "keyframes": [{"frame": f, "value": v} for f, v in keys]}


def path(points: list[tuple[float, float]]) -> list[dict]:
    return ([{"type": "move_to", "point": list(points[0])}]
            + [{"type": "line_to", "point": list(p)} for p in points[1:]]
            + [{"type": "close"}])


def mask_for(style: str) -> dict:
    if style == "PENNELLATA":
        # Irregular matte grows vertically; its rough silhouette evokes a dry brush.
        rough = [(-440,-250),(-340,-235),(-280,-249),(-205,-229),(-130,-246),(-55,-232),
                 (25,-249),(100,-230),(180,-245),(260,-229),(345,-246),(440,-232),
                 (440,232),(335,246),(250,230),(165,248),(80,232),(0,249),(-80,232),
                 (-165,247),(-255,229),(-345,245),(-440,230)]
        # Preserve path topology for Chronon's path morph decoder: top edge
        # points move to the top edge and bottom edge points to the bottom.
        full = [(-440 + n * 88, -260) for n in range(11)] + [
            (440 - n * (880 / 11), 260) for n in range(12)]
        return {"type":"path", "mode":"intersect", "path":path(rough),
                "target_path":path(full), "animation":{"keyframes":[
                    {"frame":0,"value":0.0},{"frame":52,"value":1.0}]}}
    if style == "DIAGONALE":
        start = [(-430,-250),(-370,-250),(-115,250),(-175,250)]
        end = [(-430,-250),(430,-250),(430,250),(-430,250)]
        return {"type":"path", "mode":"intersect", "path":path(start),
                "target_path":path(end), "animation":{"keyframes":[
                    {"frame":0,"value":0.0},{"frame":48,"value":1.0}]}}
    if style == "IRIDE":
        return {"type":"ellipse", "mode":"intersect", "position":[0,0],
                "size":[900,900], "expansion_track":{"keyframes":[
                    {"frame":0,"value":-700},{"frame":52,"value":0}]}}
    # Expanding horizontal band, followed by a quick full-frame settle.
    return {"type":"rounded_rect", "mode":"intersect", "position":[0,0],
            "size":[900,165], "radius":82, "expansion_track":{"keyframes":[
                {"frame":0,"value":-680},{"frame":42,"value":0},
                {"frame":58,"value":220}]}}


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    OUT.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(SOURCE, OUT/SOURCE.name)
    shutil.copy2(FONT, OUT/FONT.name)
    image_size = [W, H]
    layers = [{"id":"background", "type":"color", "start_frame":0,
               "duration_frames":TOTAL, "size":image_size,
               "position":[W/2,H/2], "screen_space":True, "color":[0,0,0,1]}]
    variants = ["PENNELLATA", "DIAGONALE", "IRIDE", "FASCIA"]
    for i, title in enumerate(variants):
        start = i * SEGMENT
        layers.append({"id":f"photo-{i}", "type":"image", "asset":SOURCE.name,
                       "start_frame":start, "duration_frames":SEGMENT,
                       "size":image_size, "position":[W/2,H/2], "fit":"contain",
                       "masks":[mask_for(title)]})
        layers.append({"id":f"caption-{i}", "type":"text", "text":title,
                       "start_frame":start+2, "duration_frames":SEGMENT-2,
                       "size":[280,36], "position":[W/2,30],
                       "style":{"font":FONT.name, "font_size":20, "min_font_size":18,
                                "max_font_size":20, "fit_mode":"shrink_only",
                                "fill":"#FFFFFF"},
                       "animation":{"tracks":[track("opacity",[(0,0.0),(6,1.0),
                                                                        (67,1.0),(83,0.0)])]}})
    plan = {"schema":"chronon.render-plan.v3", "version":3,
            "job_id":"scene03_photo_reveal_variants",
            "canvas":{"width":W,"height":H,"fps_num":FPS,"fps_den":1,
                      "duration_frames":TOTAL},
            "layers":layers,
            "output":{"path":str(OUT/"Scene03_Photo_Reveal_Variants_854x480.mp4"),
                      "format":"mp4","codec":"h264"}}
    (OUT/"Scene03_Photo_Reveal_Variants.plan.json").write_text(
        json.dumps(plan, indent=2)+"\n", encoding="utf-8")
    (OUT/"SCENE_CONTRACT.md").write_text(
        "# Scene contract — Scene 03 photo reveal variants\n\n"
        "- Subject: supplied Scene 03 composition preview (1920×1080 RGB still).\n"
        "- Composition: contain the complete still, centered on pure black; 854×480.\n"
        "- Motion: four 3-second reveals, in order: dry brush, watercolor bloom, circular iris, "
        "diagonal wipe. Each segment holds the revealed image briefly.\n"
        "- Layers: black background, source image, animated matte, effect name.\n"
        "- Render: deterministic Pillow matte generation piped through FFmpeg/libx264; 30 fps, 12 s.\n"
        "- Chronon plan: included as an editable mask-layout reference; the local PNG render lane\n"
        "  does not evaluate animated masks per frame, so it is not used to encode this preview.\n"
        "- Exclude: extra scene objects, color grading, lighting changes, particles, music.\n"
        "- Approval preview: the MP4 and contact sheet must show each effect clearly on black.\n",
        encoding="utf-8")
    print(OUT/"Scene03_Photo_Reveal_Variants.plan.json")


if __name__ == "__main__":
    main()
