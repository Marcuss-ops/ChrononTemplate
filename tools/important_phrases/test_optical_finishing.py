#!/usr/bin/env python3
"""Contract tests for the editorial Didone render-plan generator.

These checks inspect fresh plans generated in memory; stale MP4s and PNGs in
out/ cannot make a broken source plan pass. Pixel-level GPU verification still
requires rendering the plan through Chronon3D on a Vulkan host.
"""

import hashlib
import importlib.util
import os
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
TOOL_PATH = ROOT / "ChrononTemplate/tools/important_phrases/render_editorial_didone_canary.py"
FONT_PATH = ROOT / "Chronon3d/assets/fonts/Bodoni72-BookItalic.ttf"

spec = importlib.util.spec_from_file_location("didone_canary", TOOL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load canary generator: {TOOL_PATH}")
didone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(didone)


def test_selected_font_is_the_shipped_bodoni_72_book_italic():
    assert didone.FONT_BLACK_REL == "assets/fonts/Bodoni72-BookItalic.ttf"
    assert FONT_PATH.is_file(), f"Missing selected face: {FONT_PATH}"
    font = ImageFont.truetype(str(FONT_PATH), 100)
    family, style = font.getname()
    assert "Bodoni" in family, (family, style)
    assert "italic" in style.lower(), (family, style)
    print(f"Font face: {family} {style}")
    print(f"Bodoni72-BookItalic SHA-256: {hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()}")


def test_scene_one_line_order_and_left_to_right_bar_wipe():
    plan = didone.make_scene1_plan()
    layers = {layer["id"]: layer for layer in plan["layers"]}
    assert layers["line0"]["text"] == "Non poteva accettare"
    assert layers["line1"]["text"] == "ciò che era"
    assert layers["line0"]["position"][1] < layers["line1"]["position"][1]

    bar = layers["red_bar"]
    tracks = {track["property"]: track["keyframes"]
              for track in bar["animation"]["tracks"]}
    assert tracks["scale_x"][0]["value"] == 0.0
    assert tracks["scale_x"][-1]["value"] == 1.0
    assert tracks["position_x"][0]["value"] < 0.0
    assert tracks["position_x"][-1]["value"] == 0.0
    opacity_keys = tracks["opacity"]
    assert all(key["value"] == 1.0 for key in opacity_keys)
    assert not any(layer.get("enable_3d") for layer in layers.values())


def test_checklist_order_and_open_leading():
    layers = {layer["id"]: layer for layer in didone.make_scene2_plan()["layers"]}
    text_layers = [layers[f"text_{index}"] for index in range(3)]
    assert [layer["text"] for layer in text_layers] == [
        "Ferrovie", "Oleodotti", "Raffinerie"]
    y_positions = [layer["position"][1] for layer in text_layers]
    font_size = text_layers[0]["style"]["font_size"]
    assert y_positions == sorted(y_positions)
    assert min(b - a for a, b in zip(y_positions, y_positions[1:])) >= font_size * 2.0
    for index, text_layer in enumerate(text_layers):
        check = layers[f"check_{index}"]
        assert abs(check["position"][0] - (text_layer["position"][0] +
                   didone.ImageFont.truetype(str(FONT_PATH), font_size).getlength(text_layer["text"]) / 2.0 + 75.0)) < 1.0
        assert check["position"][1] == text_layer["position"][1] - 5.0


def test_conservative_bloom_and_native_background_treatment():
    plans = [didone.make_scene1_plan(), didone.make_scene2_plan(),
             didone.make_scene3_plan(), didone.make_scene4_plan()]
    for plan in plans:
        for layer in plan["layers"]:
            if layer["type"] == "text":
                assert not layer.get("enable_3d", False)
                assert "rotation" not in layer
                for effect in layer.get("effects", []):
                    assert effect["type"] == "bloom"
                    assert effect["threshold"] >= 0.90
                    assert effect["intensity"] <= 0.16
            # Background and checklist layers use only effects verified in the
            # Vulkan strict-native capability table; native noise/vignette are
            # currently not supported and must not silently force fallback.
            assert not any(effect["type"] in {"noise", "vignette"}
                           for effect in layer.get("effects", []))


def test_transition_uses_camera_motion_and_previous_phrase_crop():
    plan = didone.make_scene5_transition_plan()
    layers = {layer["id"]: layer for layer in plan["layers"]}
    assert layers["previous_phrase"]["text"] == "Non poteva accettare"
    assert layers["incoming_phrase"]["text"] == "ciò che era"
    assert layers["previous_phrase"]["position"][1] < 150
    assert layers["incoming_phrase"]["position"][1] > 540
    assert layers["previous_phrase"]["enable_3d"] and layers["incoming_phrase"]["enable_3d"]
    tracks = {track["property"]: track for track in plan["camera_animation"]["tracks"]}
    assert {"camera_position_y", "camera_position_z"}.issubset(tracks)
    for track in tracks.values():
        frames = [key["frame"] for key in track["keyframes"]]
        assert frames == sorted(set(frames))
        assert track["easing"] == "in_out_cubic"
    incoming_opacity = {key["frame"]: key["value"]
                        for key in next(track for track in layers["incoming_phrase"]["animation"]["tracks"]
                                        if track["property"] == "opacity")["keyframes"]}
    assert incoming_opacity[0] == 0.0 and incoming_opacity[149] == 1.0


def test_renderer_requires_vulkan_and_never_uploads_by_default():
    source = TOOL_PATH.read_text()
    render_body = source.split("def render_scene(", 1)[1].split("\ndef ", 1)[0]
    assert '"--backend", "vulkan"' in render_body
    assert '"--gpu-hot-path-mode", "require_gpu_native"' in render_body
    assert '"--hardware", "none"' in render_body
    assert '"--encoder-backend", "pipe"' in render_body
    assert "noise=alls=" not in source
    assert 'parser.add_argument("--upload", action="store_true"' in source
    assert "--upload" in source
    assert '--out-dir' in source


def test_compare_candidates_uses_one_fixed_size_and_gpu_path():
    source = (ROOT / "ChrononTemplate/tools/important_phrases/render_didone_font_comparison.py").read_text()
    assert "FONT_SIZE = 190" in source
    assert '"Bodoni 72 Bold (non-italic control)"' in source
    assert '"fill": color}' in source
    assert "_fit(font_path" not in source.split("def build_plan", 1)[1].split("def validate_with_cli", 1)[0]
    assert '"--backend", "vulkan"' in source
    assert '"--gpu-hot-path-mode", "require_gpu_native"' in source
    compare_body = source.split("def render_candidate(", 1)[1].split("\ndef ", 1)[0]
    assert '"--hardware", "none"' in compare_body
    assert '"--encoder-backend", "pipe"' in compare_body


def main():
    tests = [
        test_selected_font_is_the_shipped_bodoni_72_book_italic,
        test_scene_one_line_order_and_left_to_right_bar_wipe,
        test_checklist_order_and_open_leading,
        test_conservative_bloom_and_native_background_treatment,
        test_transition_uses_camera_motion_and_previous_phrase_crop,
        test_renderer_requires_vulkan_and_never_uploads_by_default,
        test_compare_candidates_uses_one_fixed_size_and_gpu_path,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} Didone plan contracts")


if __name__ == "__main__":
    main()
