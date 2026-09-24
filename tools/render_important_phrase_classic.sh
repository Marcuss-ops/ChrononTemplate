#!/usr/bin/env bash
# Render the Classic important-phrase pack on the GPU.
#
# The animation families live in C++ (ClassicPhrasePack.hpp, TypewriterPhrasePack.hpp
# on the shared look in ImportantPhrasePack.hpp);
# chronontemplate_emit_important_phrase_plans lowers them to render plans and
# chronon3d_cli draws them with the Vulkan backend (--gpu-hot-path-mode
# require_gpu_native fails closed if the GPU lane cannot run).
#
# All families are emitted; one family is rendered at a time (the pipelines
# ask for Typewriter today, Classic stays ready for the day it is wanted).
#
# Usage:
#   tools/render_important_phrase_classic.sh [output-dir] [--emit-only]
#   FAMILY=classic|typewriter|apple|all tools/render_important_phrase_classic.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OUT="${1:-$ROOT/out/important_phrase_classic_v1}"
ASSETS_ROOT="$ROOT"
CLI="$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"
EMITTER="$ROOT/build/release-fast/chronontemplate_emit_important_phrase_plans"
[[ -x "$EMITTER" ]] || EMITTER="$ROOT/build/dev-fast/chronontemplate_emit_important_phrase_plans"

EMIT_ONLY=0
[[ "${2:-}" == "--emit-only" ]] && EMIT_ONLY=1

mkdir -p "$OUT"
"$EMITTER" "$OUT"

if [[ "$EMIT_ONLY" -eq 1 ]]; then
  echo "emitted plans only in $OUT"
  exit 0
fi

FAMILY="${FAMILY:-typewriter}"
shopt -s nullglob
if [[ "$FAMILY" == "all" ]]; then
  plans=("$OUT"/*.plan.json)
else
  plans=("$OUT"/"${FAMILY}"_*.plan.json)
fi
if [[ ${#plans[@]} -eq 0 ]]; then
  echo "no ${FAMILY} plans in $OUT" >&2
  exit 1
fi

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

echo "rendered the classic important-phrase pack in $OUT"
