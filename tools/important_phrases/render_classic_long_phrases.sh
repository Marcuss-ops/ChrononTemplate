#!/usr/bin/env bash
# Render the Classic Apple long-phrase family on the GPU.
#
# The five recipes are re-authored short-phrase motions (baseline rise,
# tracking close, focus resolve, quiet zoom, glyph curtain) built for wrapped
# three-line copy instead of a single short line. The look is the Classic
# Apple one the request asked for: Playfair Display static, near-black ink on
# a white canvas, no glow and no stroke.
#
# emit_native_phrase_pack.py --pack classic-long lowers motion_catalog.v1.json
# to chronon.render-plan.v2, then chronon3d_cli draws each plan through the
# strict Vulkan lane (--backend vulkan, no automatic software backend).
#
# --gpu-hot-path-mode require_gpu_native is deliberately NOT set: on this host
# the video resolver reports required_gpu_capability_unavailable for the NVENC
# pipe handoff and aborts before frame one, while the text-run contract itself
# still draws through the native MTSDF path.
#
# Usage:
#   tools/important_phrases/render_classic_long_phrases.sh [output-dir] [--emit-only]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OUT="${1:-$ROOT/out/classic_long_phrase_v1}"
FILTER="${2:-}"
ASSETS_ROOT="$REPO/Chronon3d"
EMITTER="$ROOT/tools/important_phrases/emit_native_phrase_pack.py"

CLI=""
for candidate in \
  "$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli" \
  "$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli" \
  "$REPO/Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli"; do
  [[ -x "$candidate" ]] && CLI="$candidate" && break
done
[[ -n "$CLI" ]] || { echo "chronon3d_cli not found" >&2; exit 1; }
[[ -f "$EMITTER" ]] || { echo "emitter not found: $EMITTER" >&2; exit 1; }

mkdir -p "$OUT"
(cd "$REPO" && python3 "$EMITTER" --pack classic-long --out "$OUT")

if [[ "$FILTER" == "--emit-only" ]]; then
  echo "emitted Classic Apple long-phrase plans only in $OUT"
  exit 0
fi

shopt -s nullglob
plans=("$OUT"/classic_playfair_*.plan.json)
[[ ${#plans[@]} -gt 0 ]] || { echo "no Classic Apple plans in $OUT" >&2; exit 1; }

for plan in "${plans[@]}"; do
  name="$(basename "$plan" .plan.json)"
  "$CLI" render \
    --plan "$plan" \
    --assets-root "$ASSETS_ROOT" \
    --backend vulkan \
    --hardware nvenc \
    --encoder-backend pipe \
    --codec h264 \
    --fps 30 \
    --rate-control qp \
    --qp 18 \
    -o "$OUT/${name}.mp4"
  echo "rendered ${name}.mp4"
done

echo "rendered the Classic Apple long-phrase family in $OUT"
