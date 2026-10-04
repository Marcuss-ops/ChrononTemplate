"""Suite pipeline: validate -> parallel render -> poster -> manifest -> upload.

One implementation of the three-phase main() that fifteen scripts wrote by
hand, with resume (`--from PLAN`), bounded parallelism and a timing manifest.
Rendering and validation are subprocess calls to `chronon3d_cli`, so the kit
never re-implements renderer semantics.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import drive
from .paths import Workspace, find_workspace


@dataclass
class SuiteItem:
    """One renderable unit of a suite: a name plus its plan builder."""

    name: str
    build: Callable[[], object]  # -> kit.plan.Plan or a hand-authored dict


@dataclass
class Suite:
    name: str
    out_dir: Path
    items: list[SuiteItem]
    drive_folder: str | None = None
    upload_assets: str = "videos"  # "videos" | "videos+posters" | "none"
    assets_root: Path | None = None
    workspace: Workspace | None = None
    verify: Callable[[Path], list[str]] | None = None  # -> list of problems
    items_meta: dict = field(default_factory=dict)  # per-item manifest extras


# ---------------------------------------------------------------- CLI glue ---

def add_pipeline_args(parser: argparse.ArgumentParser) -> None:
    """Standard flags every suite shares."""
    parser.add_argument("--out", type=Path, default=None,
                        help="output directory (default: the suite's own)")
    parser.add_argument("--validate-only", action="store_true",
                        help="write + validate the plans, no rendering")
    parser.add_argument("--render-only", action="store_true",
                        help="validate + render, no upload")
    parser.add_argument("--from", dest="resume_from", metavar="PLAN", default=None,
                        help="resume: render only the plans AFTER this one")
    parser.add_argument("--upload-only", action="store_true",
                        help="upload existing MP4s, no write/validate/render")
    parser.add_argument("--plans-only", action="store_true",
                        help="write plan JSONs only, no CLI involved")
    parser.add_argument("--jobs", type=int, default=1,
                        help="parallel renders (default 1)")
    parser.add_argument("--skip-upload", action="store_true",
                        help="never touch Google Drive")
    parser.add_argument("--no-posters", action="store_true")
    parser.add_argument("--cli", type=Path, default=None,
                        help="chronon3d_cli override")
    parser.add_argument("--drive-folder", type=str, default=None)
    parser.add_argument("--assets-root", type=Path, default=None)


def _plan_dict(built: object) -> dict:
    return built.to_dict() if hasattr(built, "to_dict") else built  # type: ignore


def run_suite(suite: Suite, argv: list[str] | None = None) -> int:
    """Standard suite entry point. Returns a process exit code."""
    ws = suite.workspace or find_workspace()
    suite.workspace = ws

    parser = argparse.ArgumentParser(prog=suite.name)
    add_pipeline_args(parser)
    args = parser.parse_args(argv)

    out_dir = Path(args.out) if args.out else suite.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_root = args.assets_root or suite.assets_root or ws.assets_root

    cli = ws.first_existing_cli(args.cli)
    need_cli = not (args.plans_only or args.upload_only)
    if need_cli and cli is None:
        raise SystemExit(
            "Chronon3D CLI non trovato (serve per validate/render): "
            "passa --cli o imposta CHRONON_CLI."
        )
    if args.plans_only:
        cli = None

    order = [item.name for item in suite.items]
    plans: dict[str, Path] = {}
    errors: list[str] = []

    # ---- write + validate ---------------------------------------------------
    if not args.upload_only:
        for item in suite.items:
            plan_dict = _plan_dict(item.build())
            # The builder bakes its default output path into the plan; redirect
            # it here so `--out` actually moves the rendered MP4 (and the
            # default dir keeps byte-identical plans).
            wanted_mp4 = str(out_dir / f"{item.name}.mp4")
            if plan_dict.get("output", {}).get("path") != wanted_mp4:
                plan_dict.setdefault("output", {})["path"] = wanted_mp4
            plan_path = out_dir / f"{item.name}.plan.json"
            # No trailing newline: byte-identical to the plans the handwritten
            # scripts produced with json.dump(..., indent=2).
            plan_path.write_text(json.dumps(plan_dict, indent=2))
            plans[item.name] = plan_path
            if args.plans_only:
                print(f"  [written] {item.name}")
                continue
            proc = subprocess.run(
                [str(cli), "validate", "--plan", str(plan_path),
                 "--assets-root", str(assets_root)],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                detail = (proc.stderr.strip() or proc.stdout.strip())[:2000]
                errors.append(f"VALIDATE {item.name}:\n{detail}")
                print(f"  [FAIL] validate {item.name}")
            else:
                print(f"  [OK] validate {item.name}")

        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        if args.plans_only or args.validate_only:
            print(f"{suite.name}: {len(plans)} piani scritti e validati.")
            return 0

    # ---- render (parallel, resumable) ---------------------------------------
    render_results: dict[str, tuple[bool, float]] = {}
    todo = order
    if args.resume_from:
        if args.resume_from not in order:
            raise SystemExit(f"--from {args.resume_from}: piano non presente nella suite")
        todo = order[order.index(args.resume_from) + 1:]

    if not args.upload_only and todo:
        jobs = max(1, min(args.jobs, len(todo)))
        print(f"--- render: {len(todo)} piani, {jobs} in parallelo ---")

        def _render(name: str) -> tuple[bool, float]:
            t0 = time.time()
            proc = subprocess.run(
                [str(cli), "render",
                 "--plan", str(plans[name]),
                 "--assets-root", str(assets_root)],
                capture_output=True, text=True,
            )
            dt = time.time() - t0
            if proc.returncode != 0:
                tail = (proc.stderr.strip() or proc.stdout.strip())[-2000:]
                print(f"RENDER {name} ({dt:.2f}s) FAILED:\n{tail}", file=sys.stderr)
            return proc.returncode == 0, dt

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_render, name): name for name in todo}
            for future in as_completed(futures):
                name = futures[future]
                ok, dt = future.result()
                render_results[name] = (ok, dt)
                print(f"  [{'OK' if ok else 'FAIL'}] render {name} ({dt:.2f}s)")

    def mp4_of(name: str) -> Path:
        return out_dir / f"{name}.mp4"

    rendered = [n for n in order if render_results.get(n, (False, 0.0))[0]]

    # ---- posters --------------------------------------------------------------
    if rendered and not args.no_posters and not args.upload_only:
        for name in rendered:
            poster = out_dir / f"{name}_poster.png"
            if poster.exists():
                continue
            subprocess.run(
                ["ffmpeg", "-y", "-ss", "00:00:02.5", "-i", str(mp4_of(name)),
                 "-vframes", "1", str(poster)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    # ---- manifest ---------------------------------------------------------------
    manifest = {
        "suite": suite.name,
        "workspace": str(ws.root),
        "cli": str(cli) if cli else None,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": {},
    }
    for name in order:
        entry: dict = {
            "plan": str(plans.get(name, out_dir / f"{name}.plan.json")),
            "mp4": str(mp4_of(name)) if mp4_of(name).exists() else None,
            "render_seconds": (
                round(render_results[name][1], 3) if name in render_results else None
            ),
        }
        if name in suite.items_meta:
            entry.update(suite.items_meta[name])
        manifest["items"][name] = entry
    manifest_path = out_dir / f"{suite.name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    if suite.verify is not None and not args.upload_only:
        problems = suite.verify(out_dir)
        manifest["verify"] = problems
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        for problem in problems:
            print(f"  [VERIFY-FAIL] {problem}", file=sys.stderr)

    # ---- upload -----------------------------------------------------------------
    folder = args.drive_folder or suite.drive_folder
    wants_upload = (
        not args.skip_upload
        and not args.render_only
        and folder
        and suite.upload_assets != "none"
        and (rendered or args.upload_only)
    )
    if wants_upload:
        token = drive.refresh_token(ws.token_path, ws.creds_path)
        files: list[Path] = []
        for name in rendered:
            files.append(mp4_of(name))
            if suite.upload_assets == "videos+posters":
                files.append(out_dir / f"{name}_poster.png")
        print(f"--- upload: {len(files)} file su Drive ---")
        uploads = drive.upload_many(token, files, folder)
        upload_meta = {
            str(path.name): drive.link_for(result)
            for path, result in uploads.items()
        }
        manifest["upload"] = upload_meta
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        for path in files:
            print(f"  [UP] {path.name} -> {upload_meta.get(path.name)}")

    ok_count = len(rendered)
    total = len(order)
    print(f"{suite.name}: {ok_count}/{total} render OK "
          f"(manifest: {manifest_path.name})")
    return 0 if ok_count == total and not errors else 1
