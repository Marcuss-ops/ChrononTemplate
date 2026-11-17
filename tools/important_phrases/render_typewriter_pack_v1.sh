#!/usr/bin/env bash
# Typewriter motion pack v1 — emit plans with the C++ emitter, then render every
# clip on the GPU (Vulkan backend + native NVENC) and assemble the MP4.
#
# Each clip is ONE NVENC run. That used to be wrong: a single long run froze the
# per-glyph reveal after the first frame, so the pack was rendered in 16-frame
# chunks and concatenated. The engine has since been fixed at the root — the
# dirty tracker folded the sampled frame into an animating text run's
# fingerprint (SceneHasher::has_live_text_run_animation), so the native
# RGBA→NV12 conversion reconverts the glyph block on every animating frame.
# A single run now measures identical to the old chunked render (max 0.001 mean
# luma per frame over 192 frames, byte-identical across repeats), so the
# chunking workaround is gone: ffmpeg only builds the preview sheets.
#
# Regression lock: Chronon3d/tests/render_graph/pipeline/
# test_dirty_text_animator_bbox.cpp.
#
# usage: render_typewriter_pack_v1.sh [out_dir] [motion-id ...]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
OUT="${1:-$REPO/RenderingGen/Upload/typewriter_pack_20261116}"
shift || true

FPS=24
TOTAL=192
CLI="$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
ASSETS="$REPO/Chronon3d"

mkdir -p "$OUT/plans" "$OUT/videos" "$OUT/previews" "$OUT/logs"

BIN="$OUT/emit_typewriter_pack_v1"
g++ -std=c++17 -O2 "$HERE/emit_typewriter_pack_v1.cpp" -I/usr/include/freetype2 -lfreetype -o "$BIN"
"$BIN" "$REPO" "$OUT/plans" "$@"

render_clip() {
  local id="$1"
  local plan="$OUT/plans/$id.plan.json"
  local log="$OUT/logs/$id.log"

  "$CLI" validate --plan "$plan" --assets-root "$ASSETS" >"$log" 2>&1

  "$CLI" render --plan "$plan" --assets-root "$ASSETS" \
    --backend vulkan --hardware nvenc --encoder-backend native \
    --gpu-hot-path-mode require_gpu_native --codec h264 --fps "$FPS" \
    --rate-control qp --qp 18 --start-frame 0 --end-frame $((TOTAL - 1)) \
    -o "$OUT/videos/$id.mp4" >>"$log" 2>&1

  local frames
  frames="$(ffprobe -v error -select_streams v:0 -count_frames \
    -show_entries stream=nb_read_frames -of csv=p=0 "$OUT/videos/$id.mp4")"
  [ "$frames" = "$TOTAL" ] || {
    echo "FAIL $id: expected $TOTAL frames, got '$frames'" >&2
    exit 1
  }

  ffmpeg -y -v error -i "$OUT/videos/$id.mp4" -vf \
    "select='eq(n\,6)+eq(n\,24)+eq(n\,48)+eq(n\,96)+eq(n\,144)+eq(n\,190)',scale=640:360,tile=3x2" \
    -frames:v 1 "$OUT/previews/$id.png"
}

for plan in "$OUT"/plans/*.plan.json; do
  id="$(basename "$plan" .plan.json)"
  render_clip "$id"
  echo "rendered $id"
done

echo "TYPEWRITER_PACK_RENDER_OK -> $OUT/videos"
