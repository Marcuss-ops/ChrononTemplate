#!/usr/bin/env python3
"""Contract checks for the canonical Vintage Documentary title and variants."""
import argparse
import json
import subprocess
from pathlib import Path


VARIANTS = {
    "classic": ("vintage_documentary_title_01.plan.json", 6),
    "soft": ("vintage_documentary_title_01_soft.plan.json", 3),
    "aged": ("vintage_documentary_title_01_aged.plan.json", 12),
}
EXPECTED_TEXT = {
    "small_the": ("The", 92.0, [300.0, 380.0]),
    "main_title": ("DOCUMENTARY", 280.0, [960.0, 545.0]),
    "script_sub": ("editing-style", 104.0, [1330.0, 740.0]),
}


def validate_plan(path: Path, expected_scratches: int, assets_root: Path) -> None:
    plan = json.loads(path.read_text())
    assert plan["schema"] == "chronon.render-plan.v3", path
    assert plan["canvas"] == {
        "width": 1920, "height": 1080, "fps_num": 30,
        "fps_den": 1, "duration_frames": 150,
    }, path
    layers = {layer["id"]: layer for layer in plan["layers"]}
    assert {"background", "small_the", "main_title", "script_sub",
            "film_dust", "flicker_overlay"}.issubset(layers), path
    assert len([name for name in layers if name.startswith("film_scratch_")]) == expected_scratches, path
    assert layers["background"]["color"] in (
        [0.0353, 0.0353, 0.0353, 1.0],
        [0.0353, 0.033, 0.029, 1.0],
    ), path
    background_noise = [effect for effect in layers["background"]["effects"]
                        if effect["type"] == "noise"]
    assert background_noise and background_noise[0]["animated"] is True
    assert background_noise[0]["seed"] == 42
    emitter = layers["film_dust"]["particle_emitter"]
    assert emitter["seed"] == 1234

    for layer_id, (text, size, position) in EXPECTED_TEXT.items():
        layer = layers[layer_id]
        assert layer["type"] == "text" and layer["text"] == text
        assert layer["position"] == position
        assert layer["style"]["font_size"] == size
        font_path = assets_root / layer["style"]["font"]
        assert font_path.is_file(), str(font_path)
        assert any(effect["type"] == "noise" for effect in layer["effects"])
        assert any(track["property"] == "opacity" for track in layer["animation"]["tracks"])

    for name, layer in layers.items():
        if not name.startswith("film_scratch_"):
            continue
        assert layer["type"] == "shape" and layer["shape"]["type"] == "path"
        assert len(layer["shape"]["path"]) >= 2
        assert layer["shape"]["stroke"]["width"] > 0

    assert layers["flicker_overlay"]["animation"]["tracks"][0]["keyframes"]
    assert layers["main_title"]["animation"]["tracks"][-1]["keyframes"][-1]["value"] == 1.025


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--assets-root", type=Path, required=True)
    parser.add_argument("--cli", type=Path)
    args = parser.parse_args()
    for variant, (filename, scratches) in VARIANTS.items():
        path = args.catalog / filename
        validate_plan(path, scratches, args.assets_root)
        # The GPU dry-run is opportunistic: the plan contract above is the
        # assertion, and a worker without a built chronon3d_cli skips the
        # render instead of failing on a missing optional binary.
        if args.cli and args.cli.is_file():
            output = subprocess.run(
                [str(args.cli), "render", "--plan", str(path),
                 "--assets-root", str(args.assets_root), "--backend", "vulkan",
                 "--dry-run", "-o", f"/tmp/vdt-{variant}-contract.mp4"],
                check=True, capture_output=True, text=True)
            assert '"status": "PASS"' in output.stdout, output.stdout
        print(f"PASS {variant}: {path}")


if __name__ == "__main__":
    main()
