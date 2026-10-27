#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../../../" && pwd)
out=${1:-"$root/artifacts/rig_2d_anims_v1"}
cli=${CHRONON_CLI:-"$root/../Chronon3d/build/chronon/svg-rigging-dev/apps/chronon3d_cli/chronon3d_cli"}
mkdir -p "$out"
python3 "$root/tools/vector_diagram/rig_2d_anims/emit_rig_2d_anims.py" --output "$out"

kinds=(${CHRONON_ANIMS:-idle_breath wave walk_cycle jump_land})
for kind in "${kinds[@]}"; do
  plan="$out/rig_2d_${kind}_v1.plan.json"
  raw="$out/rig_2d_${kind}_v1.rgba"
  video="$out/rig_2d_${kind}_v1.mp4"
  "$cli" validate --plan "$plan" --assets-root "$root"
  "$cli" render --plan "$plan" --assets-root "$root" --backend software \
    --video-sink raw --pipe-pixfmt rgba --fps 30 --start-frame 0 \
    --end-frame 119 --log-level warn --output "$raw"
  expected=$((854 * 480 * 4 * 120))
  actual=$(stat -c '%s' "$raw")
  if [[ "$actual" != "$expected" ]]; then
    echo "$kind: expected $expected RGBA bytes, got $actual" >&2
    exit 1
  fi
  ffmpeg -hide_banner -loglevel error -y -f rawvideo -pixel_format rgba \
    -video_size 854x480 -framerate 30 -i "$raw" -an -c:v libx264 \
    -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart "$video"
  preview_frame=0
  case "$kind" in
    idle_breath) preview_frame=28 ;;
    wave) preview_frame=60 ;;
    walk_cycle) preview_frame=15 ;;
    jump_land) preview_frame=68 ;;
  esac
  ffmpeg -hide_banner -loglevel error -y -i "$video" \
    -vf "select=eq(n\\,${preview_frame})" -vsync 0 -frames:v 1 \
    "$out/rig_2d_${kind}_v1.png"
  unlink "$raw"
  rm -f "$raw.timing.json"
done

montage "$out"/rig_2d_*_v1.png -tile 2x2 -geometry 854x480+8+8 \
  "$out/rig_2d_anims_contact_sheet.png"
