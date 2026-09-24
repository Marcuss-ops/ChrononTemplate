#!/usr/bin/env python3
"""Single local delivery gate for render-plan 2.5D/3D text clips.

The gate is deliberately independent of the renderer. It checks the encoded
artifact, the plan contract, visible ink, frame variation, transparent layer
corners, and a geometry change across the authored 3D motion. It writes the
contact sheet and a machine-readable receipt; it never uploads anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


WIDTH = 1920
HEIGHT = 1080
SAMPLES = (4, 12, 24, 40, 58, 76, 96, 112)
VISIBLE = (12, 24, 40, 58, 76, 96)


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True)


def probe(video: Path) -> dict[str, Any]:
    data = json.loads(
        run(
            "ffprobe", "-v", "error",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate,nb_frames",
            "-select_streams", "v:0", "-of", "json", str(video),
        )
    )
    stream = data.get("streams", [{}])[0]
    return {
        "codec": stream.get("codec_name"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": stream.get("avg_frame_rate"),
        "frames": int(stream.get("nb_frames", 0)),
    }


def extract(video: Path, frame: int, destination: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
         "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1", str(destination)],
        check=True,
    )


def image_data(path: Path) -> tuple[bytes, int, int]:
    with Image.open(path).convert("RGB") as image:
        return image.tobytes(), image.width, image.height


def bbox(path: Path) -> list[int] | None:
    with Image.open(path).convert("RGB") as image:
        probe_image = image.resize((480, 270), Image.Resampling.BILINEAR)
        pixels = probe_image.load()
        background = pixels[0, 0]
        points: list[tuple[int, int]] = []
        for y in range(probe_image.height):
            for x in range(probe_image.width):
                if sum(abs(pixels[x, y][i] - background[i]) for i in range(3)) > 42:
                    points.append((x, y))
        if not points:
            return None
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return [
            round(min(xs) * WIDTH / 480), round(min(ys) * HEIGHT / 270),
            round((max(xs) + 1) * WIDTH / 480), round((max(ys) + 1) * HEIGHT / 270),
        ]


def roi_corner_means(path: Path, layers: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    with Image.open(path).convert("RGB") as image:
        for layer in layers:
            position = layer.get("position")
            size = layer.get("size")
            if not position or not size or len(position) < 2 or len(size) < 2:
                continue
            # Render-plan text positions are the centre of their authored box.
            x0 = max(0, min(WIDTH - 1, int(position[0] - size[0] * 0.5)))
            y0 = max(0, min(HEIGHT - 1, int(position[1] - size[1] * 0.5)))
            x1 = max(x0 + 1, min(WIDTH, int(position[0] + size[0] * 0.5)))
            y1 = max(y0 + 1, min(HEIGHT, int(position[1] + size[1] * 0.5)))
            for x, y in ((x0, y0), (x1 - 1, y0), (x0, y1 - 1), (x1 - 1, y1 - 1)):
                patch = image.crop((max(0, x - 5), max(0, y - 5),
                                    min(WIDTH, x + 6), min(HEIGHT, y + 6)))
                values.append(sum(sum(pixel) for pixel in patch.getdata()) /
                              (3 * patch.width * patch.height))
    return values


def layer_roi(layer: dict[str, Any]) -> tuple[int, int, int, int] | None:
    position = layer.get("position")
    size = layer.get("size")
    if not position or not size or len(position) < 2 or len(size) < 2:
        return None
    x0 = max(0, min(WIDTH, int(position[0] - size[0] * 0.5)))
    y0 = max(0, min(HEIGHT, int(position[1] - size[1] * 0.5)))
    x1 = max(x0 + 1, min(WIDTH, int(position[0] + size[0] * 0.5)))
    y1 = max(y0 + 1, min(HEIGHT, int(position[1] + size[1] * 0.5)))
    return x0, y0, x1, y1


def seam_metrics(path: Path, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find vertical discontinuities that survive across a layer's ink rows.

    Glyph edges are local: they occupy a small fraction of the ROI height.
    A surface seam is a column-wide discontinuity over the authored surface,
    so it is scored by both edge magnitude and vertical support. A low-
    frequency column profile is also recorded: it catches a soft rectangle
    edge even when compression makes its per-row gradient intermittent.
    """
    with Image.open(path).convert("RGB") as image:
        rgb = np.asarray(image, dtype=np.int16)
    background = rgb[0, 0]
    results: list[dict[str, Any]] = []
    for layer in layers:
        roi = layer_roi(layer)
        if roi is None or layer.get("type") != "text":
            continue
        x0, y0, x1, y1 = roi
        crop = rgb[y0:y1, x0:x1]
        if crop.shape[1] < 3:
            continue
        edge = np.abs(crop[:, 1:] - crop[:, :-1]).mean(axis=2)
        # Evaluate the complete authored surface, including its empty rows.
        # A glyph stem can be tall inside the ink band, but it cannot produce
        # a discontinuity through the blank rows above and below the glyphs.
        support = edge > 16.0
        coverage = support.mean(axis=0)
        score = np.divide(
            (edge * support).sum(axis=0),
            np.maximum(support.sum(axis=0), 1),
        ) * coverage
        centre = float(np.median(score))
        mad = float(np.median(np.abs(score - centre)))
        threshold = max(12.0, centre + 8.0 * max(mad, 0.5))
        candidates = np.flatnonzero((score > threshold) & (coverage > 0.75))
        peaks: list[dict[str, Any]] = []
        for column in candidates:
            left = score[column - 1] if column > 0 else -1.0
            right = score[column + 1] if column + 1 < len(score) else -1.0
            if score[column] < left or score[column] < right:
                continue
            peaks.append({
                "x": int(x0 + column + 1),
                "score": round(float(score[column]), 3),
                "coverage": round(float(coverage[column]), 3),
                "kind": "row_gradient",
            })

        # Collapse the ROI vertically before scanning. Normal glyph stems
        # move as the projection changes; a reused surface/rectangle edge is
        # anchored and recurs at the same canvas column. Keep these candidates
        # separate in the receipt so the negative-control diagnosis is clear.
        profile = crop.mean(axis=0)
        profile_edge = np.abs(profile[1:] - profile[:-1]).mean(axis=1)
        profile_centre = float(np.median(profile_edge))
        profile_mad = float(np.median(np.abs(profile_edge - profile_centre)))
        profile_threshold = max(8.0, profile_centre + 6.0 * max(profile_mad, 0.5))
        for column in np.flatnonzero(profile_edge > profile_threshold):
            peaks.append({
                "x": int(x0 + column + 1),
                "score": round(float(profile_edge[column]), 3),
                "coverage": 1.0,
                "kind": "low_frequency_profile",
            })
        results.append({"layer": layer.get("id", "text"), "peaks": peaks})
    return results


def glyph_signature(path: Path, layer: dict[str, Any]) -> np.ndarray | None:
    roi = layer_roi(layer)
    if roi is None:
        return None
    with Image.open(path).convert("RGB") as image:
        rgb = np.asarray(image, dtype=np.int16)
    x0, y0, x1, y1 = roi
    crop = rgb[y0:y1, x0:x1]
    background = rgb[0, 0]
    mask = np.abs(crop - background).sum(axis=2) > 24
    points = np.argwhere(mask)
    if points.size == 0:
        return None
    min_y, min_x = points.min(axis=0)
    max_y, max_x = points.max(axis=0) + 1
    ink = Image.fromarray((mask[min_y:max_y, min_x:max_x] * 255).astype(np.uint8))
    ink = ink.resize((128, 48), Image.Resampling.BILINEAR)
    return np.asarray(ink, dtype=np.float32) / 255.0


def glyph_consistency(paths: dict[int, Path], layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare normalized glyph shapes across motion samples.

    Normalizing the active ink bbox removes the authored dolly/zoom. A sudden
    raster/glyph family change remains as a large distance from the robust
    median signature (the frame-96 bubble case is the motivating regression).
    """
    results: list[dict[str, Any]] = []
    text_layers = [layer for layer in layers if layer.get("type") == "text"]
    for layer in text_layers:
        signatures = {
            frame: signature for frame, frame_path in paths.items()
            # Reveal/exit frames are intentionally partial glyph populations;
            # compare the stable authored text while it is fully present.
            if 40 <= frame <= 96
            and (signature := glyph_signature(frame_path, layer)) is not None
        }
        if len(signatures) < 3:
            continue
        stack = np.stack(list(signatures.values()))
        reference = np.median(stack, axis=0)
        distances = {
            str(frame): round(float(np.abs(signature - reference).mean()), 4)
            for frame, signature in signatures.items()
        }
        # Geometry under orbit changes the normalized mask, but not by the
        # abrupt amount produced by a different glyph rasterizer. Keep the
        # threshold explicit in the receipt for auditability.
        outliers = [frame for frame, distance in distances.items() if distance > 0.24]
        results.append({
            "layer": layer.get("id", "text"),
            "distances": distances,
            "threshold": 0.24,
            "outliers": outliers,
        })
    return results


def contact_sheet(frames: list[tuple[int, Path]], destination: Path) -> None:
    tile = (320, 180)
    label = 24
    sheet = Image.new("RGB", (tile[0] * len(frames), tile[1] + label), "#111827")
    draw = ImageDraw.Draw(sheet)
    for index, (frame, path) in enumerate(frames):
        with Image.open(path).convert("RGB") as image:
            image.thumbnail(tile)
            sheet.paste(image, (index * tile[0] + (tile[0] - image.width) // 2,
                                label + (tile[1] - image.height) // 2))
        draw.text((index * tile[0] + 8, 5), f"frame {frame}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--expected-frames", type=int, required=True)
    parser.add_argument("--expected-fps", default="24/1")
    parser.add_argument("--require-3d", action="store_true")
    args = parser.parse_args()

    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise SystemExit("verify_3d_delivery requires ffprobe and ffmpeg")

    plan = json.loads(args.plan.read_text())
    metadata = probe(args.video)
    failures: list[str] = []
    if (metadata["width"], metadata["height"], metadata["fps"], metadata["frames"]) != (
        WIDTH, HEIGHT, args.expected_fps, args.expected_frames
    ):
        failures.append(f"invalid video metadata: {metadata}")

    animated_layers = [layer for layer in plan.get("layers", [])
                       if layer.get("enable_3d") is True]
    for layer in animated_layers:
        if layer.get("type") != "text":
            continue
        size = layer.get("size") or []
        if len(size) >= 2 and (float(size[0]) >= WIDTH * 0.9 or
                               float(size[1]) >= HEIGHT * 0.9):
            failures.append(
                f"text layer {layer.get('id', '<unnamed>')} uses a full-canvas surface"
            )
    three_d_tracks: list[str] = []
    for layer in animated_layers:
        for track in layer.get("animation", {}).get("tracks", []):
            if track.get("property") in {"position_z", "rotation_x", "rotation_y",
                                          "rotation_z", "scale_z"}:
                three_d_tracks.append(track["property"])
    if args.require_3d and (not animated_layers or not three_d_tracks):
        failures.append("plan has no explicit enable_3d layer with a concrete 3D track")

    frame_dir = args.report.parent / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames: list[tuple[int, Path]] = []
    hashes: dict[str, str] = {}
    boxes: dict[str, list[int] | None] = {}
    corners: dict[str, list[float]] = {}
    seam_report: dict[str, list[dict[str, Any]]] = {}
    frame_paths: dict[int, Path] = {}
    for frame in SAMPLES:
        path = frame_dir / f"frame-{frame:03d}.png"
        extract(args.video, frame, path)
        raw, _, _ = image_data(path)
        frames.append((frame, path))
        frame_paths[frame] = path
        hashes[str(frame)] = hashlib.sha256(raw).hexdigest()
        boxes[str(frame)] = bbox(path)
        corners[str(frame)] = roi_corner_means(path, animated_layers)
        seam_report[str(frame)] = seam_metrics(path, animated_layers)

    if len(set(hashes.values())) < 4:
        failures.append("sampled encoded frames are effectively static")
    missing_visible = [frame for frame in VISIBLE if boxes[str(frame)] is None]
    if missing_visible:
        failures.append(f"no visible ink at frames {missing_visible}")

    visible_boxes = [boxes[str(frame)] for frame in VISIBLE if boxes[str(frame)]]
    if args.require_3d and len(visible_boxes) >= 2:
        widths = [box[2] - box[0] for box in visible_boxes]
        heights = [box[3] - box[1] for box in visible_boxes]
        if max(widths) - min(widths) < 24 and max(heights) - min(heights) < 24:
            failures.append("3D canary failed: projected ink geometry did not change")

    flat_gray = [value for values in corners.values() for value in values
                 if value > 42.0]
    if flat_gray:
        failures.append("layer ROI corner is not transparent/background-like; opaque box suspected")

    # A glyph edge moves with the projected text.  A reused-surface seam is
    # anchored in the canvas and therefore recurs at the same x in several
    # motion samples.  Require recurrence before failing the delivery gate;
    # the per-frame candidates remain in the receipt for diagnosis.
    seam_columns: dict[tuple[str, int], set[int]] = {}
    for frame, entries in seam_report.items():
        for entry in entries:
            layer_id = str(entry["layer"])
            for peak in entry["peaks"]:
                x = int(peak["x"])
                for canonical_x in range(x - 1, x + 2):
                    seam_columns.setdefault((layer_id, canonical_x), set()).add(int(frame))
    recurring_seams = [
        {"layer": layer_id, "x": x, "frames": sorted(frames)}
        for (layer_id, x), frames in seam_columns.items()
        if len(frames) >= 4
        and frames.intersection({4, 12, 24})
        and frames.intersection({96, 112})
    ]
    seam_hits = recurring_seams
    if seam_hits:
        failures.append(f"vertical surface seam detected: {seam_hits}")

    consistency = glyph_consistency(frame_paths, animated_layers)
    glyph_hits = [entry for entry in consistency if entry["outliers"]]
    if glyph_hits:
        failures.append(f"glyph shape consistency failed: {glyph_hits}")

    contact_sheet(frames, args.contact_sheet)
    report = {
        "gate": "chronon-3d-delivery-v2",
        "upload_allowed": not failures,
        "video": str(args.video),
        "plan": str(args.plan),
        "metadata": metadata,
        "three_d_tracks": sorted(set(three_d_tracks)),
        "frame_hashes": hashes,
        "ink_bboxes": boxes,
        "roi_corner_means": corners,
        "seam_detection": seam_report,
        "glyph_consistency": consistency,
        "contact_sheet": str(args.contact_sheet),
        "failures": failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"upload_allowed": not failures, "failures": failures,
                      "contact_sheet": str(args.contact_sheet)}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
