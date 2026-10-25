#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
CLI="${1:-$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli}"
OUT="${2:-$ROOT/out/web_documentary_reference_stills_v1}"
EMITTER="$ROOT/build/release-fast/chronontemplate_emit_web_documentary_reference_stills"
BACKEND="${CHRONON_BACKEND:-software}"

[[ -x "$CLI" ]] || { echo "chronon3d_cli not found: $CLI" >&2; exit 1; }
[[ -x "$EMITTER" ]] || { echo "web emitter not found: $EMITTER" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg is required to wrap the renderer's raw still frame as PNG" >&2; exit 1; }

mkdir -p "$OUT/plans" "$OUT/png" "$OUT/raw"
"$EMITTER" "$OUT/plans"
cd "$ROOT"

while IFS= read -r plan; do
  stem="$(basename "$plan" .plan.json)"
  plan_arg="$(realpath --relative-to="$ROOT" "$OUT/plans/${stem}.plan.json")"
  png="$OUT/png/${stem}.png"
  raw="$OUT/raw/${stem}.rgba"
  echo "== $stem"
  "$CLI" render --plan "$plan_arg" --assets-root "$ROOT" --backend "$BACKEND" \
    --profile maximum --frame 0 --video-sink raw --pipe-pixfmt rgba -v error -o "$raw"
  ffmpeg -v error -y -f rawvideo -pixel_format rgba -video_size 1920x1080 \
    -i "$raw" -frames:v 1 -pix_fmt rgba "$png"
  rm -f "$raw"
  dimensions="$(file -b "$png")"
  [[ "$dimensions" == *"1920 x 1080"* ]] || {
    echo "expected 1920x1080 PNG, got: $dimensions" >&2
    exit 1
  }
  echo "rendered $png ($dimensions)"
done < <(find "$OUT/plans" -maxdepth 1 -name '*.plan.json' -print | sort)

echo "four static 1920x1080 documentary web stills are in $OUT/png"
