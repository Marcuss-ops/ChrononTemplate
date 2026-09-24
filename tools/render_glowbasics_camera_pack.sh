#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
PREVIEW_BUILD="$REPO/ChrononMotion3D-preview/build/strict-ownership"
PREVIEW="$PREVIEW_BUILD/chrononmotion_preview"
OUT="$ROOT/out/GlowBasics_camera_motion_cpp_v1"

cmake --build "$PREVIEW_BUILD" --target chrononmotion_preview -j 8
mkdir -p "$OUT/input_frames" "$OUT/videos"

fonts=(dmsans freeserif georgia inter poppins)
presets=(camera_push camera_pull camera_pan camera_orbit camera_shake camera_fov)
for font in "${fonts[@]}"; do
  source="$ROOT/out/GlowBasics/black_glow_${font}.mp4"
  still="$OUT/input_frames/${font}.png"
  ffmpeg -hide_banner -loglevel error -y -ss 1.8 -i "$source" -frames:v 1 "$still"
  for preset in "${presets[@]}"; do
    tmp="$OUT/tmp_${font}_${preset}"
    mkdir -p "$tmp"
    "$PREVIEW" --render "$tmp" --only "$preset" --image "$still" --clean
    mv "$tmp/${preset}.mp4" "$OUT/videos/black_glow_${font}_${preset}.mp4"
    rmdir "$tmp"
  done
done
