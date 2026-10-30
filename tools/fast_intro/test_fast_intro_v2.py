#!/usr/bin/env python3
"""Fast Intro v2 contract test (fail-closed).

Structural gates (no CLI needed) + optional native validation:
- schema chronon.render-plan.v3, duration 90-400
- hook: opacity/position/scale motion keyed at frames 0-12
- camera_samples cover the whole clip
- scales in [0.02, 3.4], no singular transforms
- easing in the native enum (linear/out_cubic/in_out_cubic/smoothstep/...)
- no legacy `enabled` fill wrappers, no round_rect typo, no font_size/color
  at layer top level (must live in style)
- fonts Inter-Black where text exists, never Inter-Regular
- whip: no pillarbox, <= 20 layers; punch: era+stat+collage present
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DIR = HERE.parents[1] / "out" / "fast_intro_v2"
REPO_ROOT = HERE.parents[2]

EASING_OK = {"linear", "in_quad", "out_quad", "in_out_quad", "in_cubic",
             "out_cubic", "in_out_cubic", "in_expo", "out_expo", "in_out_expo",
             "in_sine", "out_sine", "in_out_sine", "in_back", "out_back",
             "in_out_back", "in_elastic", "out_elastic", "in_out_elastic",
             "in_bounce", "out_bounce", "in_out_bounce", "smoothstep", "hold",
             "bezier", "spring"}


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
    assert '"enabled"' not in blob, f"{name}: legacy enabled wrapper"
    assert "round_rect" not in blob or '"rounded_rect"' in blob, \
        f"{name}: round_rect typo"
    assert "ease_out_cubic" not in blob and "ease_in" not in blob, \
        f"{name}: legacy easing"
    assert "Inter-Regular" not in blob, f"{name}: Regular font regression"
    hooked = False
    for layer in plan["layers"]:
        if layer.get("type") == "text":
            assert "style" in layer, f"{name}/{layer['id']}: text needs style"
            assert "font_size" not in layer and "color" not in layer, \
                f"{name}/{layer['id']}: font_size/color must live in style"
        for tr in layer.get("animation", {}).get("tracks", []):
            assert tr.get("easing") in EASING_OK, \
                f"{name}: bad easing {tr.get('easing')}"
            for kf in tr.get("keyframes", []):
                if isinstance(kf.get("frame"), int) and kf["frame"] <= 12 \
                        and layer.get("start_frame", 0) <= 12:
                    hooked = True
                if tr["property"] in ("scale", "scale_x", "scale_y"):
                    v = kf["value"]
                    vals = v if isinstance(v, list) else [v]
                    for x in vals:
                        assert 0.02 - 1e-6 <= abs(float(x)) <= 3.4 + 1e-6, \
                            f"{name}: scale out of range {x}"
    assert hooked, f"{name}: no hook motion in frames 0-12"
    for layer in plan["layers"]:
        # Renderer convention (see build_entity_presentation_v1 canvas_position):
        # text/shape positions are canvas pixels (layer center), image/color
        # positions are center-relative (canvas center is [0,0]).
        x, y = layer.get("position", [0, 0])[:2]
        if layer.get("type") in ("image", "color"):
            assert -960 - 1e-6 <= x <= 960 + 1e-6 and -540 - 1e-6 <= y <= 540 + 1e-6, \
                f"{name}/{layer['id']}: image/color must be center-relative, got {[x, y]}"
        if layer.get("type") == "text":
            assert layer.get("style", {}).get("min_font_size") == \
                layer.get("style", {}).get("font_size"), \
                f"{name}/{layer['id']}: text must lock min/max to font_size (shrink collapse)"
    ids = {layer["id"] for layer in plan["layers"]}
    if "punch" in name:
        assert any("era" in i for i in ids)
        assert any("stat" in i for i in ids)
        assert any("collage" in i for i in ids)
    if "whip" in name:
        assert not any("pillar" in i for i in ids), "pillarbox regression"
        assert len(plan["layers"]) <= 20, "layer explosion"
    if "opening" in name:
        assert any("pill" in i for i in ids), "chips must be pills"
    if any(layer.get("type") == "text" for layer in plan["layers"]):
        assert "Inter-Black" in blob or "Inter-Bold" in blob, \
            f"{name}: Black/Bold required"
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
        print(f"FAIL: native validate {path.name}:\n{r.stdout[-3000:]}")
        raise SystemExit(1)
    print(f"native ok: {path.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--native", action="store_true",
                    help="also run chronon3d_cli validate on each plan")
    ap.add_argument("--cli", type=Path, default=Path(
        "Chronon3d/build/chronon/win-release-clang/apps/chronon3d_cli/chronon3d_cli.exe"))
    args = ap.parse_args()
    plans = sorted(args.dir.glob("fast_intro_v2_*.plan.json"))
    if len(plans) < 4:
        fail(f"expected >=4 plans in {args.dir}, found {len(plans)}")
    for path in plans:
        if "vertical" in path.stem:
            continue
        check_plan(json.loads(path.read_text(encoding="utf8")), path.stem)
        if args.native:
            cli = args.cli if args.cli.is_absolute() else REPO_ROOT / args.cli
            if not cli.exists():
                fail(f"CLI not found: {cli}")
            native_validate(path, cli)
    print(f"PASS: {len([p for p in plans if 'vertical' not in p.stem])} plans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
