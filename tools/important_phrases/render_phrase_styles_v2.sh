#!/usr/bin/env bash
# Build the C++ emitter, emit the 10 plans, render them with Chronon3D (Vulkan + NVENC).
# usage: render_phrase_styles_v2.sh [out_dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../../.." && pwd)"
OUT="${1:-$REPO/RenderingGen/Upload/style_presets_20261117/chronon_cpp}"; mkdir -p "$OUT"
BIN="$OUT/emit_phrase_styles_v2"
g++ -std=c++17 -O2 "$HERE/emit_phrase_styles_v2.cpp" -I/usr/include/freetype2 -lfreetype -o "$BIN"
"$BIN" "$REPO" "$OUT"
CLI="$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
for plan in "$OUT"/*.plan.json; do n="$(basename "$plan" .plan.json)"
  "$CLI" render --plan "$plan" --assets-root "$REPO/Chronon3d" --backend vulkan --hardware nvenc \
    --encoder-backend native --gpu-hot-path-mode require_gpu_native --codec h264 --fps 30 \
    --rate-control qp --qp 18 -o "$OUT/$n.mp4" >"$OUT/$n.log" 2>&1 && echo "rendered $n" || { echo "FAILED $n"; tail -5 "$OUT/$n.log"; }
done
