#!/usr/bin/env bash
# Emit and render the long central phrase/highlight templates on Chronon's GPU.
# Usage: tools/important_phrases/render_phrase_highlights.sh [output-directory]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OUT="${1:-$ROOT/out/phrase_highlight_v1}"
PLAN_DIR="$OUT/plans"
EMITTER="$ROOT/build/chronontemplate_emit_important_phrase_plans"
CLI="$REPO/Chronon3d/.tmp/chronon-builds/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
if [[ ! -x "$CLI" ]]; then
  CLI="$REPO/Chronon3d/build/chronon/linux-release-validation/apps/chronon3d_cli/chronon3d_cli"
fi

[[ -x "$EMITTER" ]] || { echo "missing plan emitter: $EMITTER" >&2; exit 1; }
[[ -x "$CLI" ]] || { echo "missing Chronon3D CLI: $CLI" >&2; exit 1; }
mkdir -p "$PLAN_DIR"
"$EMITTER" "$PLAN_DIR"

shopt -s nullglob
plans=("$PLAN_DIR"/phrase_*.plan.json)
[[ ${#plans[@]} -ge 15 ]] || { echo "expected at least 15 phrase highlight plans" >&2; exit 1; }

for plan in "${plans[@]}"; do
  name="$(basename "$plan" .plan.json)"
  "$CLI" render \
    --plan "$plan" \
    --assets-root "$REPO/Chronon3d" \
    --backend vulkan \
    --hardware none \
    --rate-control crf \
    --crf 21 \
    --preset medium \
    --encoder-backend pipe \
    --gpu-hot-path-mode auto \
    -o "$OUT/$name.mp4"
  echo "rendered $OUT/$name.mp4"
done
