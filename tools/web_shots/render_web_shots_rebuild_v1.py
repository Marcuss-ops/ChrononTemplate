"""Render the web screenshot rebuild v1: 28 stills + clips + manifest.

Runs every shot in tools/web_shots (groups A-E) and writes, per shot:
  shot_dir/still.png   — hero frame at `still_t`
  shot_dir/<name>.mp4  — short animated clip
plus contact_sheet.jpg and manifest.json at the output root.

Shots whose outputs already exist are skipped (resumable); pass --force to
re-render everything. Rendering is in-process; to parallelize, run several
invocations with disjoint --only lists concurrently, then one final run
without --only to assemble the manifest and contact sheet.

Usage (from anywhere):
  python tools/web_shots/render_web_shots_rebuild_v1.py [--out DIR]
      [--only NAME ...] [--stills-only] [--keep-frames] [--force]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image

from web_shot_kit import contact_sheet
from shots_group_a import GROUP_A
from shots_group_b import GROUP_B
from shots_group_c import GROUP_C
from shots_group_d import GROUP_D
from shots_group_e import GROUP_E

ALL_GROUPS = GROUP_A + GROUP_B + GROUP_C + GROUP_D + GROUP_E


def _entry_for(shot, stills_only: bool, skipped: bool = False) -> dict:
    n = max(2, int(round(shot.seconds * shot.fps)))
    return {
        "shot": shot.name,
        "source": shot.source,
        "description": shot.description,
        "seconds": shot.seconds,
        "fps": shot.fps,
        "frames": 0 if stills_only else n,
        "still": f"{shot.name}/still.png",
        "clip": None if stills_only else f"{shot.name}/{shot.name}.mp4",
        **({"skipped": True} if skipped else {}),
    }


def render_one(factory, out_root: Path, stills_only: bool, keep_frames: bool, force: bool) -> dict:
    shot = factory()
    shot_dir = out_root / shot.name
    still_path = shot_dir / "still.png"
    clip_path = shot_dir / f"{shot.name}.mp4"
    if not force and still_path.exists() and (stills_only or clip_path.exists()):
        return _entry_for(shot, stills_only, skipped=True)
    if stills_only:
        img = shot.render_still()
        shot_dir.mkdir(parents=True, exist_ok=True)
        img.save(still_path)
        return _entry_for(shot, stills_only)
    entry = shot.render_all(out_root, write_frames=True)
    if not keep_frames:
        shutil.rmtree(shot_dir / "frames", ignore_errors=True)
    entry["still"] = entry["still"].replace("\\", "/")
    entry["clip"] = entry["clip"].replace("\\", "/")
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE.parents[1] / "artifacts" / "web_shots_rebuild_v1"),
                    help="output root (default: artifacts/web_shots_rebuild_v1)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="render only these shot names")
    ap.add_argument("--stills-only", action="store_true",
                    help="render the hero stills without the mp4 clips")
    ap.add_argument("--keep-frames", action="store_true",
                    help="keep the per-frame PNG dumps next to the clips")
    ap.add_argument("--force", action="store_true",
                    help="re-render shots whose outputs already exist")
    args = ap.parse_args(argv)

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    entries = []
    for factory in ALL_GROUPS:
        shot = factory()
        if args.only and shot.name not in args.only:
            continue
        entry = render_one(factory, out_root, args.stills_only, args.keep_frames, args.force)
        entries.append(entry)
        tag = "skip" if entry.get("skipped") else "render"
        print(f"[{tag}] {entry['shot']} ({entry['source']})", flush=True)

    if not entries:
        print("[done] no shots matched --only", flush=True)
        return 1

    # Assembly only when the full set is in scope (avoids races between
    # concurrent --only workers; the final full run builds the artifacts).
    if not args.only:
        stills = [(e["shot"], Image.open(out_root / e["still"])) for e in entries]
        contact_sheet(stills, out_root / "contact_sheet.jpg")
        manifest = {
            "schema": "chronon.web-shots-rebuild.v1",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(entries),
            "shots": entries,
        }
        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[done] {len(entries)} shots -> {out_root}", flush=True)
    else:
        print(f"[done] {len(entries)} shots rendered (run without --only to assemble)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
