#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
CLI="${1:-$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli}"
OUT="${2:-$ROOT/out/social_recreator_v1}"
EMITTER="$ROOT/build/dev/chronontemplate_emit_social_recreator_v1"
[[ -x "$CLI" ]] || { echo "Chronon3D CLI missing: $CLI" >&2; exit 1; }
[[ -x "$EMITTER" ]] || { echo "C++ emitter missing; build chronontemplate_emit_social_recreator_v1 first" >&2; exit 1; }
mkdir -p "$OUT/plans" "$OUT/png" "$OUT/raw"
"$EMITTER" "$OUT/plans"
while IFS= read -r plan; do
  stem="$(basename "$plan" .plan.json)"
  "$CLI" render --plan "$plan" --assets-root "$ROOT" --backend software \
    --profile maximum --frame 0 --video-sink raw --pipe-pixfmt rgba \
    --log-level error -o "$OUT/raw/$stem.rgba"
  ffmpeg -hide_banner -loglevel error -y -f rawvideo -pixel_format rgba \
    -video_size 1920x1080 -i "$OUT/raw/$stem.rgba" -frames:v 1 \
    -pix_fmt rgba "$OUT/png/$stem.png"
  rm -f "$OUT/raw/$stem.rgba"
done < <(find "$OUT/plans" -maxdepth 1 -name '*.plan.json' -print | sort)
echo "Rendered 25 native C++/Chronon PNGs: $OUT/png"
