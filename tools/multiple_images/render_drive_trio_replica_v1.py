#!/usr/bin/env python3
"""Drive trio replica V1 — ricrea le 2 reference Drive in Chronon.

Reference 1 (dark_fan): 3 polaroid bianche su fondo scuro, ventaglio
  sinistra -12deg / centro 0deg davanti / destra +12deg.
Reference 2 (light_archive): 3 foto archivio arrotondate su fondo
  grigio chiaro + caption Bednyaks/Serednyaks/Kulaks + label "Archive image".

Suite: 1920x1080 30fps 150f, 4 clip:
  1. dark_fan_reveal — ventaglio dal centro, focus L->Mid->R
  2. dark_fan_settle — ladder stagger + micro push
  3. light_archive_grid — rise stagger su fondo chiaro
  4. light_archive_captions — come 3 + caption + label archivio

Target Drive: stessa cartella trio esistente 1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kit import Canvas, Plan, Suite, SuiteItem, fade, track

CANVAS = Canvas(width=1920, height=1080, fps=30, duration_frames=150)
OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "drive_trio_replica_v1"
DRIVE_FOLDER_ID = "1SXQQaEwJ2mk9_u0T2Fl15DQ1C6_A8kcX"
END = CANVAS.duration_frames - 1

ASSETS = "assets/drive_trio_replica_v1"
DARK = (f"{ASSETS}/dark_pol_1.png", f"{ASSETS}/dark_pol_2.png", f"{ASSETS}/dark_pol_3.png")
LIGHT = (f"{ASSETS}/light_1.png", f"{ASSETS}/light_2.png", f"{ASSETS}/light_3.png")

DARK_POS = [(-380, 0), (0, -20), (380, 0)]
DARK_TILT = [-12.0, 0.0, 12.0]
DARK_SIZE = (440, 638)
LIGHT_POS = [(-600, -60), (0, -60), (600, -60)]


def bg_layer(plan: Plan, rgb: tuple[float, float, float]) -> None:
    plan.color_layer("bg", (rgb[0], rgb[1], rgb[2], 1.0))


def white_backing(plan: Plan, lid: str, pos, w: int, h: int, tilt: float, tracks) -> None:
    # backing polaroid bianco: color rect con stessa animazione della foto
    layer = {
        "id": lid,
        "type": "color",
        "color": [0.96, 0.96, 0.95, 1.0],
        "size": [w, h],
        "position": list(pos),
        "start_frame": 0,
        "duration_frames": CANVAS.duration_frames,
        "animation": {"tracks": tracks},
    }
    plan.layer(layer)


def dark_tracks(i: int, mode: str) -> list[dict]:
    tilt = DARK_TILT[i]
    d = i * 8
    if mode == "reveal":
        return [
            track("position_x", "out_cubic", (0, DARK_POS[i][0] * 1.6), (26 + d, DARK_POS[i][0]), (END, DARK_POS[i][0])),
            track("scale", "in_out_cubic", (0, 0.85), (26 + d, 1.04), (48 + d, 1.0), (END, 1.0)),
            track("rotation_z", "out_cubic", (0, tilt * 2.2), (26 + d, tilt), (END, tilt)),
            fade("out_cubic", (0, 0.0), (14 + d, 1.0), (END, 1.0)),
        ]
    # settle: ladder + focus pulse
    return [
        track("position_y", "out_cubic", (0, 120.0), (28 + d, 0.0), (END, 0.0)),
        track("scale", "in_out_cubic", (0, 0.88), (28 + d, 1.05), (52 + d, 1.0), (END, 1.02)),
        track("rotation_z", "out_cubic", (0, tilt * 2.0), (28 + d, tilt), (END, tilt)),
        fade("out_cubic", (0, 0.0), (16 + d, 1.0), (END, 1.0)),
    ]


def build_dark(job_id: str, mode: str) -> Plan:
    plan = Plan(job_id=job_id, canvas=CANVAS, output_path=OUT_DIR / f"{job_id}.mp4")
    bg_layer(plan, (0.045, 0.045, 0.055))
    # ordine: laterali prima, centro ultimo = davanti (come reference).
    # Bordo polaroid cotto nell'asset: un solo layer per card, rotazione pulita.
    order = [0, 2, 1]
    for i in order:
        x, y = DARK_POS[i]
        tr = dark_tracks(i, mode)
        plan.image_card(f"card_{i}", DARK[i], DARK_SIZE, [x, y], tr,
                        radius=0.0, fit="cover", enable_3d=True,
                        start_frame=0, duration_frames=CANVAS.duration_frames)
    return plan


def light_tracks(i: int) -> list[dict]:
    d = i * 10
    return [
        track("position_y", "out_cubic", (0, 90.0), (26 + d, 0.0), (END, 0.0)),
        track("scale", "out_cubic", (0, 0.88), (26 + d, 1.03), (46 + d, 1.0), (END, 1.0)),
        fade("out_cubic", (0, 0.0), (16 + d, 1.0), (END, 1.0)),
    ]


def build_light(job_id: str, with_captions: bool) -> Plan:
    plan = Plan(job_id=job_id, canvas=CANVAS, output_path=OUT_DIR / f"{job_id}.mp4")
    bg_layer(plan, (0.905, 0.905, 0.90))
    for i, (asset, (x, y)) in enumerate(zip(LIGHT, LIGHT_POS)):
        tr = light_tracks(i)
        plan.image_card(f"card_{i}", asset, (560, 385), [x, y], tr,
                        radius=60.0, fit="cover", enable_3d=True,
                        start_frame=0, duration_frames=CANVAS.duration_frames)
    if with_captions:
        caps = ["Bednyaks", "Serednyaks", "Kulaks"]
        for i, (cap, (x, _)) in enumerate(zip(caps, LIGHT_POS)):
            d = i * 10
            # testo = coordinate schermo assolute (0,0 in alto-sx):
            # card center screen x = 960+x, caption sotto le card y~830
            plan.text_card(f"cap_{i}", cap, size=(560, 60), position=[960 + x, 830],
                           font="assets/fonts/Inter-Bold.ttf", font_size=38.0,
                           fill="#FFFFFF",
                           tracks=[fade("out_cubic", (0, 0.0), (40 + d, 1.0), (END, 1.0))])
        plan.text_card("archive_kicker", "Archive image", size=(500, 40), position=[200, 70],
                       font="assets/fonts/Inter-Regular.ttf", font_size=28.0, fill="#3A3A3A",
                       tracks=[fade("out_cubic", (0, 0.0), (10, 1.0), (END, 1.0))])
        plan.text_card("archive_sub", "Bednyaks, Serednyaks, and Kulaks", size=(700, 40), position=[300, 110],
                       font="assets/fonts/Inter-Regular.ttf", font_size=26.0, fill="#3A3A3A",
                       tracks=[fade("out_cubic", (0, 0.0), (16, 1.0), (END, 1.0))])
    return plan


SUITE = Suite(
    name="drive_trio_replica_v1",
    out_dir=OUT_DIR,
    drive_folder=DRIVE_FOLDER_ID,
    assets_root=Path(__file__).resolve().parents[2],
    items=[
        SuiteItem("dark_fan_reveal", lambda: build_dark("dark_fan_reveal", "reveal")),
        SuiteItem("dark_fan_settle", lambda: build_dark("dark_fan_settle", "settle")),
        SuiteItem("light_archive_grid", lambda: build_light("light_archive_grid", False)),
        SuiteItem("light_archive_captions", lambda: build_light("light_archive_captions", True)),
    ],
)

if __name__ == "__main__":
    from kit import run_suite
    raise SystemExit(run_suite(SUITE))
