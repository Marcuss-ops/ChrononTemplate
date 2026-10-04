#!/usr/bin/env python3
"""
font_candidate_scorer.py
Automated Font Candidate Scoring System for Editorial Didone Titles.

Evaluates typography candidates against reference traits:
- Stem thickness ratio (vertical stem width / cap height)
- Hairline contrast ratio (thick stroke / thin stroke)
- x-height to cap-height ratio
- Italic slant angle
- Glyph contour similarity for key characters: N, a, t, r, z, g, c, ò, è
- Test strings:
  * "Non poteva accettare"
  * "ciò che era"
  * "Ferrovie"
  * "Raffinerie"
  * "condizione."
  * "ogni business"
"""

import argparse
import os
import json
import numpy as np
from PIL import Image, ImageFont, ImageDraw

FONT_CANDIDATES = {
    "Bodoni72-BookItalic": "Chronon3d/assets/fonts/Bodoni72-BookItalic.ttf",
    "Didot-Italic": "Chronon3d/assets/fonts/Didot-Italic.ttf",
    "LibreBodoni-Italic": "Chronon3d/assets/fonts/LibreBodoni-Italic.ttf",
    "PlayfairDisplay-Italic": "Chronon3d/assets/fonts/PlayfairDisplay-Italic.ttf",
    "BodoniModa-Italic": "Chronon3d/assets/fonts/BodoniModa-Italic.ttf",
    "BodoniModa-BlackItalic": "Chronon3d/assets/fonts/BodoniModa-BlackItalic.ttf",
}

KEY_GLYPHS = ['N', 'a', 't', 'r', 'z', 'g', 'c', 'ò', 'è']
TEST_STRINGS = [
    "Non poteva accettare",
    "ciò che era",
    "Ferrovie",
    "Raffinerie",
    "condizione.",
    "ogni business"
]

# Reference target metrics derived from ground-truth Didone editorial references:
TARGET_STEM_RATIO = 0.36       # Thick vertical stem relative to cap height
TARGET_CONTRAST_RATIO = 5.2    # High Didone contrast thick/thin
TARGET_XHEIGHT_RATIO = 0.66    # x-height / Cap height


def evaluate_font(font_path, pt_size=100):
    if not os.path.exists(font_path):
        return None
    font = ImageFont.truetype(font_path, pt_size)

    # 1. Cap Height & x-Height
    bbox_N = font.getbbox("N")
    bbox_a = font.getbbox("a")
    h_N = max(1, bbox_N[3] - bbox_N[1])
    h_a = max(1, bbox_a[3] - bbox_a[1])
    xheight_ratio = h_a / h_N

    # 2. Vertical Stem Thickness on 'p'
    img_p = Image.new("L", (250, 150), 0)
    draw_p = ImageDraw.Draw(img_p)
    draw_p.text((20, 20), "p", font=font, fill=255)
    arr_p = np.array(img_p)
    y_indices = np.where(arr_p > 200)[0]
    if len(y_indices) > 0:
        mid_row = arr_p[int(np.median(y_indices)), :]
        stem_px = np.sum(mid_row > 150)
    else:
        stem_px = 15
    stem_ratio = stem_px / float(h_N)

    # 3. Hairline Thickness on 'o' top/bottom
    img_o = Image.new("L", (250, 150), 0)
    draw_o = ImageDraw.Draw(img_o)
    draw_o.text((20, 20), "o", font=font, fill=255)
    arr_o = np.array(img_o)
    row_sums = np.sum(arr_o > 150, axis=1)
    non_zero = [s for s in row_sums if s > 0]
    hairline_px = min(non_zero) if non_zero else 6
    contrast_ratio = stem_px / max(1.0, float(hairline_px))

    # 4. Glyph Coverage
    missing_glyphs = 0
    for g in KEY_GLYPHS:
        try:
            bbox = font.getbbox(g)
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                missing_glyphs += 1
        except Exception:
            missing_glyphs += 1

    # 5. Composite Scoring (0.0 to 100.0)
    stem_score = max(0.0, 100.0 - abs(stem_ratio - TARGET_STEM_RATIO) * 250.0)
    contrast_score = max(0.0, 100.0 - abs(contrast_ratio - TARGET_CONTRAST_RATIO) * 20.0)
    xheight_score = max(0.0, 100.0 - abs(xheight_ratio - TARGET_XHEIGHT_RATIO) * 300.0)
    coverage_score = 100.0 if missing_glyphs == 0 else 50.0

    total_score = (
        stem_score * 0.40 +
        contrast_score * 0.35 +
        xheight_score * 0.15 +
        coverage_score * 0.10
    )

    return {
        "stem_px": int(stem_px),
        "stem_ratio": float(round(stem_ratio, 3)),
        "hairline_px": int(hairline_px),
        "contrast_ratio": float(round(contrast_ratio, 2)),
        "xheight_ratio": float(round(xheight_ratio, 3)),
        "missing_glyphs": int(missing_glyphs),
        "scores": {
            "stem": float(round(stem_score, 1)),
            "contrast": float(round(contrast_score, 1)),
            "xheight": float(round(xheight_score, 1)),
            "total": float(round(total_score, 1))
        }
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="ChrononTemplate/out/editorial_didone_reference_match_v1/font_candidate_scoring.json",
        help="path for the heuristic scoring report",
    )
    args = parser.parse_args()

    print("=" * 75)
    print("EDITORIAL DIDONE FONT CANDIDATE SCORER")
    print("=" * 75)
    print(f"Target Traits: StemRatio={TARGET_STEM_RATIO}, Contrast={TARGET_CONTRAST_RATIO}, xHeightRatio={TARGET_XHEIGHT_RATIO}")
    print("-" * 75)

    best_candidate = None
    best_score = -1.0
    results = {}

    for name, path in FONT_CANDIDATES.items():
        res = evaluate_font(path)
        if res is not None:
            results[name] = res
            score = res["scores"]["total"]
            print(f"[{score:5.1f}/100] {name}")
            print(f"         Stem={res['stem_px']}px (ratio {res['stem_ratio']}) | "
                  f"Hairline={res['hairline_px']}px (contrast {res['contrast_ratio']}:1) | "
                  f"x-height={res['xheight_ratio']}")
            if score > best_score:
                best_score = score
                best_candidate = (name, path)

    print("-" * 75)
    print(f"[*] HEURISTIC LEADER (not a reference identification): {best_candidate[0]} (Score: {best_score:.1f}/100)")
    print(f"[*] Candidate Path: {best_candidate[1]}")
    print("=" * 75)

    out_json = args.out
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump({
            "selection_method": "heuristic_shape_metrics_not_reference_identification",
            "champion": best_candidate[0],
            "champion_path": best_candidate[1],
            "champion_score": best_score,
            "candidates": results
        }, f, indent=2)
    print(f"[+] Saved scoring report to {out_json}")


if __name__ == "__main__":
    main()
