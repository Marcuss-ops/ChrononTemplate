#!/usr/bin/env python3
"""Chronon Multi-Image Trio V1 — kit edition.

Same five presets and same plan bytes as the original suite, authored through
the shared kit: workspace/CLI discovery, Plan builder, and the standard
validate -> render -> poster -> manifest -> upload pipeline with resume and
parallel rendering come from tools/kit instead of this file.

Presets (1920x1080, 5.0s @ 30fps, 500x680 cards @ X = -540 / 0 / +540):
  1. trio_fan_reveal
  2. trio_center_priority
  3. trio_ladder_stagger
  4. trio_arc_focus
  5. trio_depth_peel

Target Google Drive Folder: 1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import Canvas, Plan, Suite, SuiteItem, fade, track

CANVAS = Canvas(width=1920, height=1080, fps=30, duration_frames=150)
OUT_DIR = Path(__file__).resolve().parents[1] / "out" / "multi_image_trio_v1"
DRIVE_FOLDER_ID = "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX"

CARD_SIZE = (500, 680)
LEFT_X, MID_X, RIGHT_X = -540, 0, 540  # ints: the originals' plan bytes encode positions as ints

IMG_1 = "assets/famous_people_trio_v1/neil_armstrong.png"
IMG_2 = "assets/famous_people_trio_v1/sally_ride.png"
IMG_3 = "assets/famous_people_trio_v1/john_glenn.png"

END = CANVAS.duration_frames - 1  # 149


def bg() -> dict:
    return {
        "id": "studio_dark_bg",
        "type": "color",
        "color": [0.03, 0.04, 0.07, 1.0],
        "start_frame": 0,
        "duration_frames": CANVAS.duration_frames,
    }


def card(layer_id: str, asset: str, position: list[float],
         tracks: list[dict]) -> dict:
    # One-off shape kept literal so the plans stay byte-identical to the
    # originals authored before the kit existed.
    return {
        "id": layer_id,
        "type": "image",
        "asset": asset,
        "size": list(CARD_SIZE),
        "position": position,
        "radius": 0.0,
        "fit": "cover",
        "enable_3d": True,
        "start_frame": 0,
        "duration_frames": CANVAS.duration_frames,
        "animation": {"tracks": tracks},
    }


def new_plan(job_id: str) -> Plan:
    plan = Plan(job_id=job_id, canvas=CANVAS,
                output_path=OUT_DIR / f"{job_id}.mp4")
    plan.layer(bg())
    return plan


# =============================================================================
# 1. trio_fan_reveal — cards fan out from center, focus Left->Mid->Right
# =============================================================================
def build_01_trio_fan_reveal() -> Plan:
    plan = new_plan("trio_fan_reveal")
    plan.layer(card("card_left", IMG_1, [LEFT_X, 0], [
        track("position_x", "out_cubic", (0, 540.0), (24, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.90), (24, 1.0), (36, 1.05), (60, 1.05), (72, 0.96),
              (120, 0.96), (134, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 1.0), (60, 1.0), (72, 0.75), (120, 0.75),
             (134, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_mid", IMG_2, [MID_X, 0], [
        track("scale", "in_out_cubic",
              (0, 0.92), (24, 1.0), (60, 0.96), (72, 1.05), (96, 1.05),
              (108, 0.96), (120, 0.96), (134, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 1.0), (60, 0.75), (72, 1.0), (96, 1.0),
             (108, 0.75), (120, 0.75), (134, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_right", IMG_3, [RIGHT_X, 0], [
        track("position_x", "out_cubic", (0, -540.0), (24, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.90), (24, 1.0), (96, 0.96), (108, 1.05), (124, 1.05),
              (134, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 1.0), (96, 0.75), (108, 1.0), (124, 1.0),
             (134, 1.0), (END, 1.0)),
    ]))
    return plan


# =============================================================================
# 2. trio_center_priority — hero center, secondary flanks, firm hero lock
# =============================================================================
def build_02_trio_center_priority() -> Plan:
    plan = new_plan("trio_center_priority")
    plan.layer(card("card_left", IMG_1, [LEFT_X, 0], [
        track("position_x", "out_cubic", (0, -160.0), (24, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.88), (24, 0.94), (36, 1.02), (56, 1.02), (70, 0.92),
              (END, 0.92)),
        fade("in_out_cubic",
             (0, 0.0), (18, 0.80), (36, 1.0), (56, 1.0), (70, 0.72),
             (END, 0.72)),
    ]))
    plan.layer(card("card_right", IMG_3, [RIGHT_X, 0], [
        track("position_x", "out_cubic", (0, 160.0), (24, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.88), (24, 0.92), (60, 0.92), (74, 1.02), (94, 1.02),
              (108, 0.92), (END, 0.92)),
        fade("in_out_cubic",
             (0, 0.0), (18, 0.72), (60, 0.72), (74, 1.0), (94, 1.0),
             (108, 0.72), (END, 0.72)),
    ]))
    plan.layer(card("card_mid", IMG_2, [MID_X, 0], [
        track("scale", "in_out_cubic",
              (0, 0.92), (24, 1.02), (100, 1.02), (116, 1.08), (END, 1.08)),
        fade("in_out_cubic", (0, 0.0), (20, 1.0), (END, 1.0)),
    ]))
    return plan


# =============================================================================
# 3. trio_ladder_stagger — ladder entrance Left(F0) -> Mid(F18) -> Right(F36)
# =============================================================================
def build_03_trio_ladder_stagger() -> Plan:
    plan = new_plan("trio_ladder_stagger")
    plan.layer(card("card_left", IMG_1, [LEFT_X, 0], [
        track("position_x", "out_cubic", (0, -320.0), (22, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.92), (22, 1.04), (46, 1.04), (60, 0.96), (120, 0.96),
              (134, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 1.0), (46, 1.0), (60, 0.75), (120, 0.75),
             (134, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_mid", IMG_2, [MID_X, 0], [
        track("position_x", "out_cubic", (18, -320.0), (40, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.92), (18, 0.92), (40, 1.04), (74, 1.04), (88, 0.96),
              (120, 0.96), (134, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 0.0), (34, 1.0), (74, 1.0), (88, 0.75),
             (120, 0.75), (134, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_right", IMG_3, [RIGHT_X, 0], [
        track("position_x", "out_cubic", (36, -320.0), (58, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic",
              (0, 0.92), (36, 0.92), (58, 1.04), (110, 1.04), (124, 1.0),
              (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (36, 0.0), (52, 1.0), (110, 1.0), (124, 1.0),
             (END, 1.0)),
    ]))
    return plan


# =============================================================================
# 4. trio_arc_focus — parabolic arc: center elevated, flanks lowered
# =============================================================================
def build_04_trio_arc_focus() -> Plan:
    plan = new_plan("trio_arc_focus")
    plan.layer(card("card_left", IMG_1, [LEFT_X, 28], [
        track("scale", "in_out_cubic",
              (0, 0.92), (24, 1.04), (52, 1.04), (66, 0.96), (124, 0.96),
              (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (20, 1.0), (52, 1.0), (66, 0.74), (124, 0.74),
             (136, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_mid", IMG_2, [MID_X, -28], [
        track("scale", "in_out_cubic",
              (0, 0.92), (24, 0.96), (52, 0.96), (66, 1.05), (92, 1.05),
              (106, 0.96), (124, 0.96), (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (20, 0.74), (52, 0.74), (66, 1.0), (92, 1.0),
             (106, 0.74), (124, 0.74), (136, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_right", IMG_3, [RIGHT_X, 28], [
        track("scale", "in_out_cubic",
              (0, 0.92), (24, 0.96), (92, 0.96), (106, 1.04), (124, 1.04),
              (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (20, 0.74), (92, 0.74), (106, 1.0), (124, 1.0),
             (136, 1.0), (END, 1.0)),
    ]))
    return plan


# =============================================================================
# 5. trio_depth_peel — three depth tiers peel forward in succession
# =============================================================================
def build_05_trio_depth_peel() -> Plan:
    plan = new_plan("trio_depth_peel")
    plan.layer(card("card_left", IMG_1, [LEFT_X, 0], [
        track("scale", "in_out_cubic",
              (0, 0.90), (24, 1.06), (48, 1.06), (64, 0.95), (124, 0.95),
              (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 1.0), (48, 1.0), (64, 0.75), (124, 0.75),
             (136, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_mid", IMG_2, [MID_X, 0], [
        track("scale", "in_out_cubic",
              (0, 0.90), (24, 0.95), (52, 0.95), (68, 1.06), (92, 1.06),
              (106, 0.95), (124, 0.95), (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 0.75), (52, 0.75), (68, 1.0), (92, 1.0),
             (106, 0.75), (124, 0.75), (136, 1.0), (END, 1.0)),
    ]))
    plan.layer(card("card_right", IMG_3, [RIGHT_X, 0], [
        track("scale", "in_out_cubic",
              (0, 0.90), (24, 0.95), (92, 0.95), (108, 1.06), (124, 1.06),
              (136, 1.0), (END, 1.0)),
        fade("in_out_cubic",
             (0, 0.0), (18, 0.75), (92, 0.75), (108, 1.0), (124, 1.0),
             (136, 1.0), (END, 1.0)),
    ]))
    return plan


SUITE = Suite(
    name="multi_image_trio_v1",
    out_dir=OUT_DIR,
    drive_folder=DRIVE_FOLDER_ID,
    assets_root=Path(__file__).resolve().parents[1],
    items=[
        SuiteItem("trio_fan_reveal", build_01_trio_fan_reveal),
        SuiteItem("trio_center_priority", build_02_trio_center_priority),
        SuiteItem("trio_ladder_stagger", build_03_trio_ladder_stagger),
        SuiteItem("trio_arc_focus", build_04_trio_arc_focus),
        SuiteItem("trio_depth_peel", build_05_trio_depth_peel),
    ],
)

if __name__ == "__main__":
    from kit import run_suite
    raise SystemExit(run_suite(SUITE))
