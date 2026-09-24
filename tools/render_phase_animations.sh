#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/ChrononTemplate/out/phase_animations_zayas_ennis_v1}"
ASSETS_ROOT="$ROOT/Chronon3d"
BIN="$ROOT/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli"

mkdir -p "$OUT"
python3 "$ROOT/ChrononTemplate/tools/generate_phase_animations.py" --out "$OUT"

"$BIN" render \
  --plan "$OUT/zayas_ennis_3d_orbit.plan.json" \
  --assets-root "$ASSETS_ROOT" \
  --backend software \
  --profile production \
  --codec h264 \
  --fps 30 \
  --crf 18 \
  -o "$OUT/zayas_ennis_3d_orbit.mp4"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

"$BIN" render \
  --plan "$OUT/zayas_ennis_typewriter.plan.json" \
  --assets-root "$ASSETS_ROOT" \
  --backend software \
  --profile production \
  --codec h264 \
  --fps 30 \
  --crf 18 \
  -o "$WORK/typewriter_base.mp4"

# ChrononTemplate supplies the canonical text/glow base.  The final wipe is
# applied in YUV space so the black canvas and white glow stay exact while the
# reveal advances from left to right over the first 3 seconds.
ffmpeg -hide_banner -loglevel error -y \
  -i "$WORK/typewriter_base.mp4" \
  -vf "geq=lum='if(gt(X,min(W,max(0,(N-9)/90*W))),0,lum(X,Y))':cb='if(gt(X,min(W,max(0,(N-9)/90*W))),128,cb(X,Y))':cr='if(gt(X,min(W,max(0,(N-9)/90*W))),128,cr(X,Y))'" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -crf 18 \
  -movflags +faststart \
  "$WORK/typewriter_final.mp4"

mv "$WORK/typewriter_final.mp4" "$OUT/zayas_ennis_typewriter.mp4"
rm -f "$OUT/zayas_ennis_typewriter.mp4.timing.json" \
      "$OUT/zayas_ennis_typewriter.mp4.telemetry-summary.json"
echo "rendered phase animations in $OUT"
