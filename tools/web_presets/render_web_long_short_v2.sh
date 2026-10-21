#!/usr/bin/env bash
# Render a focused Web + long/short phrase showcase using the native Chronon
# plans. The short-phrase modern recipes currently request Bricolage Grotesque,
# which is absent from this checkout, so emitted showcase plans use the bundled
# Inter Bold face. The C++ emitter carries the same compatibility default.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
CLI="${1:-$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli}"
OUT="${2:-$ROOT/out/web_long_short_v2}"
BACKEND="${CHRONON_BACKEND:-software}"
WEB_EMITTER="$ROOT/build/dev-fast/chronontemplate_emit_web_page_highlight"
SHORT_EMITTER="$ROOT/build/dev-fast/chronontemplate_emit_short_phrase_plans"

[[ -x "$CLI" ]] || { echo "chronon3d_cli not found: $CLI" >&2; exit 1; }
[[ -x "$WEB_EMITTER" ]] || { echo "web emitter not found: $WEB_EMITTER" >&2; exit 1; }
[[ -x "$SHORT_EMITTER" ]] || { echo "short-phrase emitter not found: $SHORT_EMITTER" >&2; exit 1; }
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || {
  echo "ffmpeg and ffprobe are required" >&2; exit 1;
}

mkdir -p "$OUT/plans/web" "$OUT/plans/short" "$OUT/renders"
"$WEB_EMITTER" "$OUT/plans/web"
"$SHORT_EMITTER" "$OUT/plans/short"

# The source change handles future builds. This output-side rewrite also keeps
# this script usable with a previously built emitter while the workspace build
# dependencies are being reconciled.
python3 - "$OUT/plans/short" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for path in root.glob("*.plan.json"):
    data = json.loads(path.read_text())
    changed = False
    for layer in data.get("layers", []):
        style = layer.get("style")
        if style and style.get("font") == "assets/fonts/Bricolage-Grotesque.ttf":
            style["font"] = "assets/fonts/Inter-Bold.ttf"
            changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n")
PY

render_clip() {
  local stem="$1" frames="$2" plan="$3"
  local raw="$OUT/renders/${stem}.nv12"
  local mp4="$OUT/${stem}.mp4"
  echo "== $stem"
  "$CLI" render --plan "$plan" --assets-root "$ROOT" --backend "$BACKEND" \
    --profile preview --fps 30 --video-sink raw --pipe-pixfmt nv12 \
    --chunks 1 --fb-pool-budget-mb 512 --fb-pool-clear-policy trim-after-job \
    --start-frame 0 --end-frame "$((frames - 1))" -v error -o "$raw"
  ffmpeg -v error -y -f rawvideo -pixel_format nv12 -video_size 1920x1080 \
    -framerate 30 -i "$raw" -frames:v "$frames" -an -c:v libx264 \
    -preset veryfast -crf 18 -pix_fmt yuv420p -r 30 \
    -video_track_timescale 30000 "$mp4"
  rm -f "$raw"
  local codec width height rate actual_frames
  codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$mp4")"
  width="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$mp4")"
  height="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$mp4")"
  rate="$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of csv=p=0 "$mp4")"
  actual_frames="$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 "$mp4")"
  [[ "$codec" == h264 && "$width" == 1920 && "$height" == 1080 && "$rate" == 30/1 && "$actual_frames" == "$frames" ]] || {
    echo "verification failed: $stem ($codec ${width}x${height} $rate $actual_frames frames)" >&2
    return 1
  }
  echo "verified $stem: H.264 1920x1080 30 fps $frames frames"
}

render_clip web_page_complete_light_v1 240 "$OUT/plans/web/web_page_complete_light_v1.plan.json"
render_clip web_page_highlight3d_dark_v1 240 "$OUT/plans/web/web_page_highlight3d_dark_v1.plan.json"
render_clip web_page_longphraseblurred_light_v1 240 "$OUT/plans/web/web_page_longphraseblurred_light_v1.plan.json"
render_clip short_phrase_editorial_baseline_rise 210 "$OUT/plans/short/short_phrase_editorial_baseline_rise.plan.json"
render_clip short_phrase_editorial_contrast_sweep 210 "$OUT/plans/short/short_phrase_editorial_contrast_sweep.plan.json"
render_clip short_phrase_product_kinetic_center_build 210 "$OUT/plans/short/short_phrase_product_kinetic_center_build.plan.json"

echo "six clips rendered and verified in $OUT"
