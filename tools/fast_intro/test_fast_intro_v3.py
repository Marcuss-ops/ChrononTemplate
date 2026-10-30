#!/usr/bin/env python3
"""Fast Intro v3 contract test (fail-closed).

Modern-language gates on top of the v2 structural gates:
- Anton display + Inter-Black labels; no Inter-Regular anywhere
- no legacy orange-gradient palette (#FFD24A, #EE7A10, #0E0202 ...)
- every recipe carries the film-grain overlay above its imagery
- letterbox bars only in cutline; no pills, no marker dots, no rings
- hook motion at frames 0-12, camera covering the whole clip
- image/color positions center-relative, text min/max locked
- keyframes strictly sorted per track, easing in the native enum
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DIR = HERE.parents[1] / "out" / "fast_intro_v3"
REPO_ROOT = HERE.parents[2]

EASING_OK = {"linear", "in_quad", "out_quad", "in_out_quad", "in_cubic",
             "out_cubic", "in_out_cubic", "in_expo", "out_expo", "in_out_expo",
             "in_sine", "out_sine", "in_out_sine", "in_back", "out_back",
             "in_out_back", "in_elastic", "out_elastic", "in_out_elastic",
             "in_bounce", "out_bounce", "in_out_bounce", "smoothstep", "hold",
             "bezier", "spring"}

LEGACY_ORANGE = ["#FFD24A", "#FFC12E", "#F79A16", "#EE7A10", "#F08A14",
                 "#D95E0B", "#C24A08", "#B23A08", "#8E2206", "#5E0D04",
                 "#0E0202", "#5D5A54", "#77746E", "#363530", "#F5F3EE"]


def fail(msg: str):
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def check_plan(plan: dict, name: str):
    assert plan.get("schema") == "chronon.render-plan.v3", f"{name}: schema"
    dur = plan["canvas"]["duration_frames"]
    assert 90 <= dur <= 400, f"{name}: duration {dur}"
    samples = plan.get("camera_samples", [])
    assert len(samples) >= dur - 1, f"{name}: camera must cover clip"
    blob = json.dumps(plan)
    assert "Inter-Regular" not in blob, f"{name}: Regular font regression"
    assert "Anton-Regular" in blob, f"{name}: Anton display required"
    for banned in LEGACY_ORANGE:
        assert banned not in blob, f"{name}: legacy orange {banned}"
    assert '"enabled"' not in blob, f"{name}: legacy enabled wrapper"
    assert "round_rect" not in blob or '"rounded_rect"' in blob
    ids = [l["id"] for l in plan["layers"]]
    assert any("pill" in i for i in ids) is False, f"{name}: pills are dead"
    assert any("marker" in i for i in ids) is False, f"{name}: marker dots dead"
    assert any("ring_" in i for i in ids) is False, f"{name}: rings are dead"
    grain = [l for l in plan["layers"] if l["id"] == "grain"]
    assert len(grain) == 1, f"{name}: grain overlay required"
    if "cutline" not in name:
        assert not any(i.startswith("bar_") for i in ids), \
            f"{name}: letterbox belongs to cutline only"
    hooked = False
    for layer in plan["layers"]:
        if layer.get("type") == "text":
            assert "style" in layer, f"{name}/{layer['id']}: text needs style"
            st = layer["style"]
            assert st.get("min_font_size") == st.get("font_size"), \
                f"{name}/{layer['id']}: lock min/max"
        x, y = layer.get("position", [0, 0])[:2]
        if layer.get("type") in ("image", "color") and layer["id"] != "grain":
            assert -960 - 1e-6 <= x <= 960 + 1e-6 and -540 - 1e-6 <= y <= 540 + 1e-6, \
                f"{name}/{layer['id']}: center-relative position required"
        for tr in layer.get("animation", {}).get("tracks", []):
            assert tr.get("easing") in EASING_OK, f"{name}: bad easing"
            frames = [kf["frame"] for kf in tr.get("keyframes", [])]
            assert frames == sorted(frames) and len(set(frames)) == len(frames), \
                f"{name}/{layer['id']}: keyframes must be strictly sorted"
            for kf in tr.get("keyframes", []):
                if isinstance(kf.get("frame"), int) and kf["frame"] <= 12 \
                        and layer.get("start_frame", 0) <= 12:
                    hooked = True
    assert hooked, f"{name}: no hook motion in frames 0-12"
    print(f"ok: {name} ({len(plan['layers'])} layers, {dur}f)")


def native_validate(path: Path, cli: Path):
    r = subprocess.run([str(cli), "validate", "--plan", str(path),
                        "--assets-root", str(REPO_ROOT)],
                       capture_output=True, text=True, timeout=120)
    out = r.stdout or ""
    start, end = out.find("{"), out.rfind("}")
    try:
        verdict = json.loads(out[start:end + 1]) if start >= 0 else {}
    except json.JSONDecodeError:
        verdict = {}
    if not verdict.get("valid", False):
        print(f"FAIL: native validate {path.name}:\n{out[-3000:]}")
        raise SystemExit(1)
    print(f"native ok: {path.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--native", action="store_true")
    ap.add_argument("--cli", type=Path, default=Path(
        "Chronon3d/build/chronon/win-release-clang/apps/chronon3d_cli/chronon3d_cli.exe"))
    args = ap.parse_args()
    plans = sorted(args.dir.glob("fast_intro_v3_*.plan.json"))
    if len(plans) < 4:
        fail(f"expected >=4 plans in {args.dir}, found {len(plans)}")
    for path in plans:
        check_plan(json.loads(path.read_text(encoding="utf8")), path.stem)
        if args.native:
            cli = args.cli if args.cli.is_absolute() else REPO_ROOT / args.cli
            if not cli.exists():
                fail(f"CLI not found: {cli}")
            native_validate(path, cli)
    print(f"PASS: {len(plans)} plans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
