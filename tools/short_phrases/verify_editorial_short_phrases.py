#!/usr/bin/env python3
"""Verify the Claude-inspired short-phrase MP4s through decoded video frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np


def frame(path: Path, index: int) -> np.ndarray:
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{index})",
        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ], capture_output=True, check=True)
    if len(result.stdout) != 1920 * 1080 * 3:
        raise ValueError(f"{path.name}: missing decoded frame {index}")
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(1080, 1920, 3)


def verify(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    animations = manifest["animations"]
    if len(animations) != 3 or any(not a["id"].startswith("short_phrase_editorial_claude_") for a in animations):
        raise ValueError("expected exactly the three Claude-inspired recipes")
    expected = {a["render"] for a in animations}
    if {p.name for p in directory.glob("*.mp4")} != expected:
        raise ValueError("MP4 set differs from the three-recipe manifest")
    evidence = []
    for animation in animations:
        path = directory / animation["render"]
        probe = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
            "-of", "json", str(path),
        ], capture_output=True, text=True, check=True).stdout)
        stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        if (stream["width"], stream["height"]) != (1920, 1080):
            raise ValueError(f"{path.name}: wrong resolution")
        expected_frames = int(manifest["canvas"]["duration_frames"])
        expected_fps = int(manifest["canvas"]["fps"])
        expected_seconds = expected_frames / expected_fps
        if Fraction(stream["avg_frame_rate"]) != expected_fps or int(stream["nb_read_frames"]) != expected_frames:
            raise ValueError(f"{path.name}: expected {expected_frames} frames at {expected_fps} fps")
        if stream["codec_name"] != "h264" or abs(float(probe["format"]["duration"]) - expected_seconds) > 0.05:
            raise ValueError(f"{path.name}: expected a {expected_seconds:g}-second H.264 preview")
        decoded = subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=480:270",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ], capture_output=True, check=True)
        frames = np.frombuffer(decoded.stdout, dtype=np.uint8).reshape(-1, 270, 480, 3)
        if len(frames) != expected_frames:
            raise ValueError(f"{path.name}: incomplete full-video decode")
        hold_frame = min(150, expected_frames - 20)
        samples = {index: frames[index] for index in
                   sorted({0, 10, 30, 60, 90, 120, hold_frame, hold_frame + 30, expected_frames - 15, expected_frames - 1})}
        hold = samples[hold_frame].astype(np.int16)
        background = np.median(hold[:20, :20], axis=(0, 1))
        visible = np.max(np.abs(hold - background), axis=2) > 40
        yy, xx = np.where(visible)
        if len(xx) < 125:
            raise ValueError(f"{path.name}: no readable foreground in decoded hold")
        bounds = [int(xx.min()) * 4, int(yy.min()) * 4, int(xx.max()) * 4, int(yy.max()) * 4]
        for index, image in enumerate(frames):
            mask = np.max(np.abs(image.astype(np.int16) - background), axis=2) > 40
            y, x = np.where(mask)
            if len(x) and (x.min() < 24 or x.max() >= 456 or y.min() < 21 or y.max() >= 249):
                raise ValueError(f"{path.name}: foreground outside safe area at frame {index}")
        if bounds[0] < 96 or bounds[2] >= 1824 or bounds[1] < 86 or bounds[3] >= 994:
            raise ValueError(f"{path.name}: foreground outside safe area: {bounds}")
        hold_delta = float(np.abs(samples[hold_frame].astype(np.int16) -
                                  samples[hold_frame + 30].astype(np.int16)).mean())
        middle_delta = float(np.abs(samples[60].astype(np.int16) - samples[120].astype(np.int16)).mean())
        entrance_delta = float(np.abs(hold - samples[10].astype(np.int16)).mean())
        if middle_delta < 0.05:
            raise ValueError(f"{path.name}: no measurable motion after entrance: {middle_delta}")
        if hold_delta > 0.8 or entrance_delta < 0.05:
            raise ValueError(f"{path.name}: missing entrance or unstable hold: {entrance_delta}, {hold_delta}")
        for index in (0, expected_frames - 1):
            if float(np.abs(samples[index].astype(np.int16) - background).mean()) > 0.8:
                raise ValueError(f"{path.name}: phrase does not fully disappear at frame {index}")
        if animation["id"] == "short_phrase_editorial_claude_diff_patch":
            orange = (hold[:, :, 0] > 210) & (hold[:, :, 1] > 55) & (hold[:, :, 1] < 190) & (hold[:, :, 2] < 100)
            if int(orange.sum()) < 20:
                raise ValueError(f"{path.name}: orange emphasized word is not visible in the hold")
        if animation.get("white_background"):
            corner = frames[60, :20, :20].astype(np.int16)
            paper = np.median(corner, axis=(0, 1))
            if float(np.min(paper)) < 210:
                raise ValueError(f"{path.name}: expected bright white editorial background")
        evidence.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "bytes": path.stat().st_size, "width": 1920, "height": 1080,
                         "fps": expected_fps, "frames": expected_frames, "seconds": expected_seconds,
                         "foreground_bounds": bounds, "entrance_pixel_delta": entrance_delta,
                         "hold_pixel_delta": hold_delta,
                         "middle_pixel_delta": middle_delta})
        print(f"VIDEO_PASS {path.name} frames={expected_frames} bounds={bounds} motion_delta={middle_delta:.4f} hold_delta={hold_delta:.4f}", flush=True)
    result = {"schema": "chronontemplate.editorial-short-phrase-verification.v1", "videos": evidence}
    (directory / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    verify(parser.parse_args().directory.resolve())
