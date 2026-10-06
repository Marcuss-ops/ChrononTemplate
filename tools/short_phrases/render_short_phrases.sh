#!/usr/bin/env bash
# Render the short-phrase family on the GPU.
#
# The twelve archetypes live in C++ (ShortPhrasePack.hpp);
# chronontemplate_emit_short_phrase_plans lowers them to chronon.render-plan.v2
# plans and chronon3d_cli draws them with the Vulkan backend
# (--gpu-hot-path-mode require_gpu_native fails closed if the GPU lane cannot
# run). 1920x1080, 30 fps, 5 s per clip.
#
# Usage:
#   tools/short_phrases/render_short_phrases.sh [output-dir] [--emit-only]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OUT="${1:-$ROOT/out/short_phrase_v1}"
ASSETS_ROOT="$REPO/Chronon3d"
EMITTER="$ROOT/build/release-fast/chronontemplate_emit_short_phrase_plans"
[[ -x "$EMITTER" ]] || EMITTER="$ROOT/build/dev/chronontemplate_emit_short_phrase_plans"

CLI=""
for candidate in \
  "$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli" \
  "$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli" \
  "$REPO/Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli"; do
  [[ -x "$candidate" ]] && CLI="$candidate" && break
done
[[ -n "$CLI" ]] || { echo "chronon3d_cli not found" >&2; exit 1; }
[[ -x "$EMITTER" ]] || { echo "emitter not built: $EMITTER" >&2; exit 1; }

mkdir -p "$OUT"
"$EMITTER" "$OUT"

if [[ "${2:-}" == "--emit-only" ]]; then
  echo "emitted short-phrase plans only in $OUT"
  exit 0
fi

shopt -s nullglob
plans=("$OUT"/short_phrase_*.plan.json)
[[ ${#plans[@]} -gt 0 ]] || { echo "no short-phrase plans in $OUT" >&2; exit 1; }

for plan in "${plans[@]}"; do
  name="$(basename "$plan" .plan.json)"
  "$CLI" render \
    --plan "$plan" \
    --assets-root "$ASSETS_ROOT" \
    --backend vulkan \
    --hardware nvenc \
    --encoder-backend native \
    --gpu-hot-path-mode require_gpu_native \
    --codec h264 \
    --fps 30 \
    --rate-control qp \
    --qp 18 \
    -o "$OUT/${name}.mp4"
  echo "rendered ${name}.mp4"
done

echo "rendered the short-phrase family in $OUT"
