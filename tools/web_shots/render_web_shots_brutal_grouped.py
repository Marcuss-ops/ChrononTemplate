#!/usr/bin/env python3
"""Restore the original brutal web-shot pass and organise it by groups.

The MP4s in ``out/web_animations_pod_v1`` are the versions rendered on
2026-10-30.  The later "elegant" pass replaced their look, so this delivery
copies the surviving original files byte-for-byte into a new tree:

    <group>/<subgroup>/<shot>.mp4

It also writes a grouped contact sheet, one contact sheet per group, a
machine-readable manifest with the legacy A-E/next provenance, and a README.
Upload creates the same nested group/subgroup structure on Drive.

Usage:
  python tools/web_shots/render_web_shots_brutal_grouped.py --skip-upload
  python tools/web_shots/render_web_shots_brutal_grouped.py --upload-only
  python tools/web_shots/render_web_shots_brutal_grouped.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
TEMPLATE_ROOT = HERE.parents[1]
WORKSPACE = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TEMPLATE_ROOT / "tools"))

from web_shot_kit import contact_sheet, get_font  # noqa: E402
from render_web_shots_rebuild_v1 import ALL_GROUPS  # noqa: E402
from shots_next import NEXT_GROUP  # noqa: E402
from kit import drive  # noqa: E402

SOURCE = TEMPLATE_ROOT / "out" / "web_animations_pod_v1"
OUT = TEMPLATE_ROOT / "out" / "web_shots_brutal_grouped_v1"
DRIVE_PARENT = "1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
DRIVE_ROOT_NAME = "ChrononTemplate_WebShots_Brutal_Grouped_20261122_1080p"

WIDTH, HEIGHT, FPS, FRAMES = 1920, 1080, 30, 90

# Content taxonomy: one home per shot.  The original A-E/next grouping is kept
# as `legacy_group` in the manifest, but it is too arbitrary to use as folders.
GROUPS = [
    {
        "id": "01_editorial_pages",
        "label": "Editorial pages",
        "subgroups": [
            {"id": "03_culture", "label": "Culture", "shots": ["03_alexis_arquette_article"]},
            {
                "id": "04_archive_press",
                "label": "Archive press",
                "shots": [
                    "08_rainmaking_nyt",
                    "17_guardian_biggest_frauds",
                    "27_times_of_india_coxon",
                ],
            },
            {
                "id": "05_business_tech",
                "label": "Business & tech",
                "shots": [
                    "15_cnbcsbf_profile_tilt",
                    "16_nbc_swindled_8b",
                    "24_big_foot_pizza",
                    "26_pizza_hut_perception",
                ],
            },
        ],
    },
    {
        "id": "02_documents_archives",
        "label": "Documents & archives",
        "subgroups": [
            {
                "id": "01_investigation",
                "label": "Investigation",
                "shots": [
                    "04_corll_warehouse_excerpt",
                    "09_pinto_highlight",
                    "10_tax_exempt_nyt",
                    "20_indictment_summary",
                ],
            },
            {
                "id": "02_declassified",
                "label": "Declassified",
                "shots": ["11_acoustic_kitty_field_test", "12_sabotage_manual_glow"],
            },
            {"id": "03_foia", "label": "FOIA", "shots": ["13_foia_finkel_zoom"]},
        ],
    },
    {
        "id": "03_quotes_captions",
        "label": "Quotes & captions",
        "subgroups": [
            {
                "id": "01_quotes",
                "label": "Quotes",
                "shots": [
                    "05_they_were_the_economy",
                    "06_thug_teacher_quote",
                    "19_nyt_look_crazy_zoom",
                ],
            },
            {
                "id": "02_captions",
                "label": "Captions",
                "shots": ["25_pizza_sauce_caption", "next_caption_pop_card"],
            },
        ],
    },
    {
        "id": "04_social_cards",
        "label": "Social posts",
        "subgroups": [
            {
                "id": "01_posts",
                "label": "Posts",
                "shots": [
                    "18_ftx_tweet_card",
                    "22_ivie_facebook",
                    "28_amodei_pace_frontier",
                ],
            }
        ],
    },
    {
        "id": "05_data_timeline",
        "label": "Data & timeline",
        "subgroups": [
            {
                "id": "01_stats",
                "label": "Stats",
                "shots": ["14_vw_40_times", "23_black_vault_foia"],
            },
            {
                "id": "02_timelines",
                "label": "Timelines",
                "shots": ["21_guardian_seoul_missiles", "next_timeline_dash"],
            },
        ],
    },
    {
        "id": "06_crt_broadcast",
        "label": "CRT & broadcast",
        "subgroups": [
            {
                "id": "01_newspaper_crt",
                "label": "Newspaper CRT",
                "shots": ["07_crt_alcohol_headline"],
            },
        ],
    },
    {
        "id": "07_native_mechanics",
        "label": "Native mechanics",
        "subgroups": [
            {
                "id": "01_markers",
                "label": "Markers",
                "shots": ["next_dual_marker_cross"],
            },
            {
                "id": "02_glow",
                "label": "Glow",
                "shots": ["next_glow_line_pulse"],
            },
            {
                "id": "03_tilt",
                "label": "Tilt",
                "shots": ["next_tilt_snap_reveal"],
            },
        ],
    },
]

SHOT_LABELS = {
    "03_alexis_arquette_article": "Alexis Arquette — tell-all memoir",
    "04_corll_warehouse_excerpt": "Corll — warehouse excerpt",
    "05_they_were_the_economy": "They were the economy — quote",
    "06_thug_teacher_quote": "Thug — teacher quote",
    "07_crt_alcohol_headline": "CRT — alcohol headline",
    "08_rainmaking_nyt": "Rainmaking — NYT",
    "09_pinto_highlight": "Pinto — crash tests",
    "10_tax_exempt_nyt": "Tax-exempt church — NYT",
    "11_acoustic_kitty_field_test": "Acoustic Kitty — field test",
    "12_sabotage_manual_glow": "Simple Sabotage — manual",
    "13_foia_finkel_zoom": "FOIA — Finkel request",
    "14_vw_40_times": "VW — 40 times the limit",
    "15_cnbcsbf_profile_tilt": "SBF — CNBC profile",
    "16_nbc_swindled_8b": "NBC — $8 billion",
    "17_guardian_biggest_frauds": "Guardian — biggest frauds",
    "18_ftx_tweet_card": "FTX — post card",
    "19_nyt_look_crazy_zoom": "NYT — look crazy",
    "20_indictment_summary": "Indictment — summary",
    "21_guardian_seoul_missiles": "Guardian — Seoul missiles",
    "22_ivie_facebook": "Ivie — Facebook post",
    "23_black_vault_foia": "Black Vault — FOIA archive",
    "24_big_foot_pizza": "Pizza Hut — Big Foot",
    "25_pizza_sauce_caption": "Pizza sauce — caption",
    "26_pizza_hut_perception": "Pizza Hut — perception",
    "27_times_of_india_coxon": "Times of India — Coxon",
    "28_amodei_pace_frontier": "Amodei — pace the frontier",
    "next_caption_pop_card": "Caption pop — recipe",
    "next_dual_marker_cross": "Dual marker — recipe",
    "next_glow_line_pulse": "Glow line — recipe",
    "next_tilt_snap_reveal": "Tilt snap — recipe",
    "next_timeline_dash": "Timeline dash — recipe",
}

LEGACY_GROUP = {
    "07_crt_alcohol_headline": "A",
    "08_rainmaking_nyt": "A",
    "09_pinto_highlight": "A",
    "10_tax_exempt_nyt": "A",
    "03_alexis_arquette_article": "B",
    "04_corll_warehouse_excerpt": "B",
    "05_they_were_the_economy": "B",
    "06_thug_teacher_quote": "B",
    "11_acoustic_kitty_field_test": "B",
    "12_sabotage_manual_glow": "C",
    "13_foia_finkel_zoom": "C",
    "14_vw_40_times": "C",
    "15_cnbcsbf_profile_tilt": "C",
    "16_nbc_swindled_8b": "C",
    "17_guardian_biggest_frauds": "D",
    "18_ftx_tweet_card": "D",
    "19_nyt_look_crazy_zoom": "D",
    "20_indictment_summary": "D",
    "21_guardian_seoul_missiles": "D",
    "22_ivie_facebook": "E",
    "23_black_vault_foia": "E",
    "24_big_foot_pizza": "E",
    "25_pizza_sauce_caption": "E",
    "26_pizza_hut_perception": "E",
    "27_times_of_india_coxon": "E",
    "28_amodei_pace_frontier": "E",
    "next_caption_pop_card": "NEXT",
    "next_dual_marker_cross": "NEXT",
    "next_glow_line_pulse": "NEXT",
    "next_tilt_snap_reveal": "NEXT",
    "next_timeline_dash": "NEXT",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe not found (install ffmpeg)")
    data = json.loads(subprocess.check_output([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration",
        "-of", "json", str(path),
    ], text=True))
    stream = data["streams"][0]
    return {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": stream.get("r_frame_rate"),
        "frames": int(stream.get("nb_frames", 0)),
        "duration_s": round(float(data.get("format", {}).get("duration", 0.0)), 3),
    }


def _check_spec(path: Path) -> dict:
    spec = _probe(path)
    problems = []
    if spec["codec"] != "h264":
        problems.append(f"codec {spec['codec']} != h264")
    if (spec["width"], spec["height"]) != (WIDTH, HEIGHT):
        problems.append(f"{spec['width']}x{spec['height']} != {WIDTH}x{HEIGHT}")
    if spec["fps"] != "30/1":
        problems.append(f"fps {spec['fps']} != 30/1")
    if spec["frames"] != FRAMES:
        problems.append(f"frames {spec['frames']} != {FRAMES}")
    if abs(spec["duration_s"] - 3.0) > 0.12:
        problems.append(f"duration {spec['duration_s']}s != 3.0s")
    if problems:
        raise SystemExit(f"{path}: " + "; ".join(problems))
    return spec


def _assert_taxonomy() -> None:
    expected = {factory().name for factory in list(ALL_GROUPS) + list(NEXT_GROUP)}
    placed = [shot for group in GROUPS for sub in group["subgroups"] for shot in sub["shots"]]
    if len(placed) != len(set(placed)):
        raise SystemExit("taxonomy contains duplicate shot names")
    if set(placed) != expected:
        missing = sorted(expected - set(placed))
        extra = sorted(set(placed) - expected)
        raise SystemExit(f"taxonomy mismatch: missing={missing} extra={extra}")
    if set(SHOT_LABELS) != expected:
        raise SystemExit("SHOT_LABELS does not cover exactly the expected shots")
    if set(LEGACY_GROUP) != expected:
        raise SystemExit("LEGACY_GROUP does not cover exactly the expected shots")


def _shorten(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"


def _grouped_contact_sheet(path: Path) -> None:
    cols, tile_w, tile_h = 4, 360, 203
    gap, pad, label_h = 16, 24, 26
    group_header, sub_header, group_gap = 54, 30, 26
    width = pad * 2 + cols * tile_w + (cols - 1) * gap

    height = pad
    for group in GROUPS:
        height += group_header
        for sub in group["subgroups"]:
            rows = (len(sub["shots"]) + cols - 1) // cols
            height += sub_header + rows * (tile_h + label_h) + (rows - 1) * gap
        height += group_gap
    height += pad

    sheet = Image.new("RGB", (width, height), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    head_font = get_font("sans-bold", 25, 1.0)
    sub_font = get_font("sans-bold", 17, 1.0)
    tile_font = get_font("sans", 15, 1.0)
    meta_font = get_font("sans", 14, 1.0)
    accent = "#C9A15A"
    y = pad

    for group in GROUPS:
        count = sum(len(sub["shots"]) for sub in group["subgroups"])
        d.text((pad, y + 8), f"{group['id'][:2]}  {group['label'].upper()}",
               font=head_font, fill="#F1EEE6")
        d.text((width - pad, y + 14), f"{count} shots", font=meta_font,
               fill="#A7A39A", anchor="ra")
        d.rectangle((pad, y + group_header - 10, width - pad, y + group_header - 7),
                    fill=accent)
        y += group_header

        for sub in group["subgroups"]:
            d.text((pad, y + 3), f"{sub['id']} · {sub['label']}",
                   font=sub_font, fill=accent)
            y += sub_header
            rows = (len(sub["shots"]) + cols - 1) // cols
            for i, name in enumerate(sub["shots"]):
                col, row = i % cols, i // cols
                x = pad + col * (tile_w + gap)
                ty = y + row * (tile_h + label_h + gap)
                still = SOURCE / name / "still.png"
                if not still.exists():
                    raise SystemExit(f"missing still: {still}")
                img = Image.open(still).convert("RGB")
                img = ImageOps.fit(img, (tile_w, tile_h), Image.LANCZOS)
                sheet.paste(img, (x, ty))
                d.rectangle((x, ty, x + tile_w - 1, ty + tile_h - 1),
                            outline="#3A3833")
                label = f"{i + 1:02d} · {SHOT_LABELS[name]}"
                label = _shorten(d, label, tile_font, tile_w)
                d.text((x, ty + tile_h + 5), label, font=tile_font, fill="#D8D4CB")
            y += rows * (tile_h + label_h) + (rows - 1) * gap
        y += group_gap

    sheet.save(path, quality=88, optimize=True)


def _write_group_sheet(group: dict, path: Path) -> None:
    stills = []
    for sub in group["subgroups"]:
        for name in sub["shots"]:
            still = SOURCE / name / "still.png"
            stills.append((f"{sub['id']} · {SHOT_LABELS[name]}", Image.open(still)))
    contact_sheet(stills, path, cols=2, cell_w=640)


def _build(force: bool = False) -> dict:
    _assert_taxonomy()
    if not SOURCE.exists():
        raise SystemExit(f"missing source pod: {SOURCE}")
    if force and OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    shot_meta = {}
    for name in SHOT_LABELS:
        shot = next(factory() for factory in list(ALL_GROUPS) + list(NEXT_GROUP)
                    if factory().name == name)
        shot_meta[name] = {
            "source": shot.source,
            "description": shot.description,
        }

    records = []
    groups_out = []
    for group in GROUPS:
        group_dir = OUT / group["id"]
        group_dir.mkdir(parents=True, exist_ok=True)
        group_out = {
            "id": group["id"],
            "label": group["label"],
            "count": 0,
            "subgroups": [],
        }
        for sub in group["subgroups"]:
            sub_dir = group_dir / sub["id"]
            sub_dir.mkdir(parents=True, exist_ok=True)
            sub_out = {
                "id": sub["id"],
                "label": sub["label"],
                "count": len(sub["shots"]),
                "shots": [],
            }
            for name in sub["shots"]:
                src = SOURCE / name / f"{name}.mp4"
                if not src.exists():
                    raise SystemExit(f"missing source clip: {src}")
                dst = sub_dir / f"{name}.mp4"
                src_sha = _sha256(src)
                if not dst.exists() or _sha256(dst) != src_sha:
                    shutil.copy2(src, dst)
                spec = _check_spec(dst)
                rel = f"{group['id']}/{sub['id']}/{name}.mp4"
                record = {
                    "name": name,
                    "label": SHOT_LABELS[name],
                    "legacy_group": LEGACY_GROUP[name],
                    "group": group["id"],
                    "subgroup": sub["id"],
                    "source": shot_meta[name]["source"],
                    "description": shot_meta[name]["description"],
                    "clip": rel,
                    "sha256": src_sha,
                    "bytes": dst.stat().st_size,
                    "spec": spec,
                }
                records.append(record)
                sub_out["shots"].append(record)
                print(f"  [OK] {rel}", flush=True)
            group_out["subgroups"].append(sub_out)
            group_out["count"] += sub_out["count"]
        groups_out.append(group_out)

    # Root contact sheet: grouped view only.
    _grouped_contact_sheet(OUT / "contact_sheet_grouped.jpg")
    for group in GROUPS:
        _write_group_sheet(group, OUT / group["id"] / "contact_sheet.jpg")

    manifest = {
        "schema": "chronon.web-shots-brutal-groups.v1",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_root": str(SOURCE.relative_to(WORKSPACE)),
        "note": (
            "Original brutal web-shot pass restored byte-for-byte from "
            "out/web_animations_pod_v1. The elegant pass is separate and superseded."
        ),
        "canvas": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "frames": FRAMES,
            "duration_s": 3.0,
        },
        "count": len(records),
        "group_count": len(groups_out),
        "subgroup_count": sum(len(g["subgroups"]) for g in groups_out),
        "groups": groups_out,
        "files": records,
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = [
        "# Web shots — brutal pass, grouped",
        "",
        "**Data:** 2026-11-22  ",
        "**Fonte:** `ChrononTemplate/out/web_animations_pod_v1` (pass originale del 2026-10-30)  ",
        f"**Contenuto:** {len(records)} MP4 + manifest + contact sheet  ",
        "**Specifiche:** 1920×1080, 30 fps, H.264, 3 s (90 frame)  ",
        "**Drive:** `ChrononTemplate_WebShots_Brutal_Grouped_20261122_1080p`",
        "",
        "## Cosa è stato ripristinato",
        "",
        f"Sono tornati i {len(records)} MP4 originali, copiati byte-per-byte: testo denso,",
        "marker gialli, pagine storte, player chrome e grana da screenshot web.",
        "Nessun re-render e nessuna passata elegante.",
        "",
        "## Rimossi su richiesta",
        "",
        "- `01_kuminga_espn_article` (Sports)",
        "- `02_al_capone_title` (Title cards)",
        "- `next_crt_fringe_flash` (Fringe flash)",
        "",
        "Anche i rispettivi generatori Python sono stati eliminati.",
        "",
        "## Gruppi e sottogruppi",
        "",
    ]
    for group in groups_out:
        readme.append(f"### {group['id']} — {group['label']} ({group['count']})")
        readme.append("")
        for sub in group["subgroups"]:
            names = ", ".join(f"`{s['name']}`" for s in sub["shots"])
            readme.append(f"- **{sub['id']}** — {sub['label']}: {names}")
        readme.append("")
    readme += [
        "## Provenienza legacy",
        "",
        "| Gruppo legacy | Shot |",
        "|---|---|",
    ]
    for legacy in ["A", "B", "C", "D", "E", "NEXT"]:
        names = [r["name"] for r in records if r["legacy_group"] == legacy]
        readme.append(f"| {legacy} | " + ", ".join(f"`{n}`" for n in names) + " |")
    readme += [
        "",
        "## Verifica",
        "",
        f"- {len(records)}/{len(records)} clip H.264 1920×1080, 30 fps, 90 frame, 3.000 s.",
        f"- {len(records)} SHA-256 distinti.",
        "- `MANIFEST.json` contiene gruppo, sottogruppo, legacy group, hash e specs.",
        "- `contact_sheet_grouped.jpg` è la vista ordinata per gruppi.",
        "",
        "La vecchia consegna `ChrononTemplate_WebShots_Elegant_20261122_1080p`",
        "resta separata e non è più la versione di riferimento.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(readme), encoding="utf-8")

    print(f"[build] {len(records)} clips, {len(groups_out)} groups, "
          f"{manifest['subgroup_count']} subgroups -> {OUT}", flush=True)
    print(f"[build] manifest={OUT / 'MANIFEST.json'}", flush=True)
    return manifest


def _load_upload(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_upload(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _upload() -> dict:
    manifest_path = OUT / "MANIFEST.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing {manifest_path}; run the build first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    upload_path = OUT / "upload_manifest.json"
    existing = _load_upload(upload_path)

    folders = {f["path"]: f for f in existing.get("folders", [])}
    uploaded = {f["path"]: f for f in existing.get("files", [])}
    root_docs = ["contact_sheet_grouped.jpg", "MANIFEST.json", "README.md"]

    token = drive.refresh_token(
        WORKSPACE / "refactored" / "token.json",
        WORKSPACE / "refactored" / "credentials.json",
    )

    def save() -> None:
        _save_upload(upload_path, {
            "schema": "chronon.web-shots-brutal-groups.upload.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "root_folder": DRIVE_ROOT_NAME,
            "root_folder_id": root_id,
            "root_url": root_url,
            "parent_folder_id": DRIVE_PARENT,
            "folder_count": len(folders),
            "file_count": len(uploaded),
            "folders": sorted(folders.values(), key=lambda f: f["path"]),
            "files": sorted(uploaded.values(), key=lambda f: f["path"]),
        })

    root_id = existing.get("root_folder_id")
    root_url = existing.get("root_url", "")
    if not root_id:
        root = drive.create_folder(token, DRIVE_ROOT_NAME, DRIVE_PARENT)
        root_id = root["id"]
        root_url = root.get("webViewLink") or (
            f"https://drive.google.com/drive/folders/{root_id}")
        save()
        print(f"[drive] root {DRIVE_ROOT_NAME} -> {root_url}", flush=True)

    # Reconcile an existing delivery with the current manifest.  Removing a
    # shot from the taxonomy must also remove its clip, subgroup and stale docs.
    desired_folders = {group["id"] for group in manifest["groups"]}
    desired_folders |= {
        f"{group['id']}/{sub['id']}"
        for group in manifest["groups"] for sub in group["subgroups"]
    }
    desired_files = {
        shot["clip"]
        for group in manifest["groups"] for sub in group["subgroups"]
        for shot in sub["shots"]
    }
    desired_files |= {
        f"{group['id']}/contact_sheet.jpg" for group in manifest["groups"]
    }
    desired_files |= set(root_docs)

    for rel in sorted(set(uploaded) - desired_files):
        rec = uploaded.pop(rel)
        if rec.get("drive_file_id"):
            drive.trash_file(token, rec["drive_file_id"])
        save()
        print(f"  [DEL] {rel}", flush=True)

    for rel in sorted(set(folders) - desired_folders, reverse=True):
        rec = folders.pop(rel)
        if rec.get("id"):
            drive.trash_file(token, rec["id"])
        save()
        print(f"  [DEL] {rel}/", flush=True)

    def ensure_folder(path: str, name: str, parent_id: str) -> dict:
        if path in folders and folders[path].get("id"):
            return folders[path]
        res = drive.create_folder(token, name, parent_id)
        rec = {
            "path": path,
            "name": name,
            "id": res["id"],
            "url": res.get("webViewLink") or (
                f"https://drive.google.com/drive/folders/{res['id']}"),
            "parent_id": parent_id,
        }
        folders[path] = rec
        save()
        print(f"[drive] folder {path}", flush=True)
        return rec

    def upload_one(rel: str, parent_id: str) -> dict:
        src = OUT / rel
        sha = _sha256(src)
        old = uploaded.get(rel)
        if old and old.get("sha256") == sha and old.get("parent_id") == parent_id:
            return old
        if old:
            if old.get("drive_file_id"):
                drive.trash_file(token, old["drive_file_id"])
            uploaded.pop(rel, None)
            save()
            print(f"  [DEL] {rel} (old version)", flush=True)
        res = drive.upload_file(token, src, parent_id)
        rec = {
            "path": rel,
            "name": src.name,
            "drive_file_id": res["id"],
            "drive_url": drive.link_for(res),
            "parent_id": parent_id,
            "sha256": sha,
            "bytes": src.stat().st_size,
        }
        uploaded[rel] = rec
        save()
        print(f"  [UP] {rel}", flush=True)
        return rec

    for group in manifest["groups"]:
        gpath = group["id"]
        gfolder = ensure_folder(gpath, group["label"], root_id)
        upload_one(f"{gpath}/contact_sheet.jpg", gfolder["id"])
        for sub in group["subgroups"]:
            spath = f"{gpath}/{sub['id']}"
            sfolder = ensure_folder(spath, sub["label"], gfolder["id"])
            pending = []
            for shot in sub["shots"]:
                rel = shot["clip"]
                old = uploaded.get(rel)
                if not (old and old.get("sha256") == shot["sha256"]
                        and old.get("parent_id") == sfolder["id"]):
                    pending.append(rel)
            if pending:
                results = drive.upload_many(
                    token, [OUT / rel for rel in pending], sfolder["id"], workers=3)
                for rel, res in results.items():
                    rel_s = rel.relative_to(OUT).as_posix()
                    uploaded[rel_s] = {
                        "path": rel_s,
                        "name": rel.name,
                        "drive_file_id": res["id"],
                        "drive_url": drive.link_for(res),
                        "parent_id": sfolder["id"],
                        "sha256": _sha256(rel),
                        "bytes": rel.stat().st_size,
                    }
                    print(f"  [UP] {rel_s}", flush=True)
                save()

    for doc in root_docs:
        upload_one(doc, root_id)

    clips = [f for f in uploaded.values() if f["path"].endswith(".mp4")]
    expected_clips = [
        shot["clip"]
        for group in manifest["groups"] for sub in group["subgroups"]
        for shot in sub["shots"]
    ]
    if {f["path"] for f in clips} != set(expected_clips):
        raise SystemExit(
            f"upload incomplete: {len(clips)}/{len(expected_clips)} clips")
    save()
    print(f"DRIVE_GROUPS_PASS root={root_url} folders={len(folders)} "
          f"files={len(uploaded)} clips={len(clips)}", flush=True)
    return {
        "root_url": root_url,
        "root_id": root_id,
        "folders": len(folders),
        "files": len(uploaded),
        "clips": len(clips),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-upload", action="store_true", help="build only")
    ap.add_argument("--upload-only", action="store_true",
                    help="upload the local bundle without rebuilding")
    ap.add_argument("--force", action="store_true",
                    help="delete and rebuild the local grouped tree")
    args = ap.parse_args(argv)

    if args.upload_only:
        if not (OUT / "MANIFEST.json").exists():
            raise SystemExit(f"missing {OUT / 'MANIFEST.json'}")
    else:
        _build(force=args.force)
    if not args.skip_upload:
        _upload()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
