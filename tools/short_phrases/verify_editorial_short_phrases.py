#!/usr/bin/env python3
"""Verify the ten editorial short-phrase MP4s through decoded video frames."""
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
    if len(animations) != 10 or any(not a["id"].startswith("short_phrase_editorial_") for a in animations):
        raise ValueError("expected exactly ten editorial recipes")
    expected = {a["render"] for a in animations}
    if {p.name for p in directory.glob("*.mp4")} != expected:
        raise ValueError("MP4 set differs from the ten-recipe manifest")
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
        if Fraction(stream["avg_frame_rate"]) != 30 or int(stream["nb_read_frames"]) != 150:
            raise ValueError(f"{path.name}: expected 150 frames at 30 fps")
        if stream["codec_name"] != "h264" or abs(float(probe["format"]["duration"]) - 5) > 0.05:
            raise ValueError(f"{path.name}: expected a five-second H.264 preview")
        decoded = subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=480:270",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ], capture_output=True, check=True)
        frames = np.frombuffer(decoded.stdout, dtype=np.uint8).reshape(-1, 270, 480, 3)
        if len(frames) != 150:
            raise ValueError(f"{path.name}: incomplete full-video decode")
        samples = {index: frames[index] for index in (0, 10, 32, 40, 60, 90, 120, 149)}
        hold = samples[60].astype(np.int16)
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
        hold_delta = float(np.abs(samples[32].astype(np.int16) - samples[40].astype(np.int16)).mean())
        middle_delta = float(np.abs(samples[60].astype(np.int16) - samples[90].astype(np.int16)).mean())
        late_delta = float(np.abs(samples[120].astype(np.int16) - samples[90].astype(np.int16)).mean())
        if middle_delta < 0.5 or late_delta < 0.3:
            raise ValueError(f"{path.name}: sequence becomes static after entrance: middle={middle_delta}, late={late_delta}")
        entrance_delta = float(np.abs(hold - samples[10].astype(np.int16)).mean())
        if hold_delta > 0.8 or entrance_delta < 0.05:
            raise ValueError(f"{path.name}: missing entrance or unstable hold: {entrance_delta}, {hold_delta}")
        for index in (0, 149):
            if float(np.abs(samples[index].astype(np.int16) - background).mean()) > 0.8:
                raise ValueError(f"{path.name}: phrase does not fully disappear at frame {index}")
        evidence.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "bytes": path.stat().st_size, "width": 1920, "height": 1080,
                         "fps": 30, "frames": 150, "seconds": 5,
                         "foreground_bounds": bounds, "entrance_pixel_delta": entrance_delta,
                         "hold_pixel_delta": hold_delta,
                         "middle_pixel_delta": middle_delta, "late_pixel_delta": late_delta})
        print(f"VIDEO_PASS {path.name} bounds={bounds} middle_delta={middle_delta:.4f} late_delta={late_delta:.4f}", flush=True)
    result = {"schema": "chronontemplate.editorial-short-phrase-verification.v1", "videos": evidence}
    (directory / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    verify(parser.parse_args().directory.resolve())
