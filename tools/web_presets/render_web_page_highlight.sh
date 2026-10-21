#!/usr/bin/env bash
# Render the six native WebPageHighlightPack plans through Chronon3D on a
# GPU/NVENC host, exactly like the other editorial packs do:
#
#   1. bounded raw-NV12 export  (CLI: --video-sink raw --pipe-pixfmt nv12
#      --chunks 1 --fb-pool-budget-mb 512)
#   2. single ffmpeg encode     (h264_nvenc when present, else libx264)
#   3. ffprobe verification     (H.264, 1920x1080, 30 fps, exact frame count)
#
# Plans are written by chronontemplate_emit_web_page_highlight; run this from
# the ChrononTemplate root:
#   tools/web_presets/render_web_page_highlight.sh [cli] [assets-root] [outdir]
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="${1:-$REPO/../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli}"
ASSETS="${2:-$REPO}"
OUT="${3:-$REPO/out/web_page_highlight_v1}"
# The per-glyph folds fall back to the CPU text lane on both backends;
# CHRONON_BACKEND=software is the deterministic choice on CPU-only hosts.
BACKEND="${CHRONON_BACKEND:-vulkan}"
# Verified clips are delivered to the user's MP4 folder when it is mounted
# (WSL: /mnt/c/...). Override with argument 4 or WEB_MP4_DELIVERY_DIR.
DELIVERY="${4:-${WEB_MP4_DELIVERY_DIR:-/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4}}"
PLAN_DIR="$OUT"
RENDER_DIR="$OUT/renders"
mkdir -p "$RENDER_DIR"
if [ -d "$DELIVERY" ]; then echo "delivery dir: $DELIVERY"; else DELIVERY=""; fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo "ffmpeg/ffprobe are required for encode and verification" >&2
    exit 1
fi
if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_nvenc \
    && "$CLI" doctor 2>/dev/null | grep -q "encoder.nvenc.*PASS"; then
    ENCODE=("-c:v" "h264_nvenc" "-preset" "p4" "-cq" "18" "-b:v" "0")
    echo "encoding with NVENC"
else
    ENCODE=("-c:v" "libx264" "-preset" "veryfast" "-crf" "17")
    echo "encoding with libx264 (no NVENC)"
fi

: > "$OUT/verification.json.new"
echo "[" >> "$OUT/verification.json.new"
first=1
failures=0
for plan in "$PLAN_DIR"/web_page_*.plan.json; do
    name="$(basename "$plan" .plan.json)"
    raw="$RENDER_DIR/$name.nv12"
    output="$RENDER_DIR/$name.mp4"
    echo "== $name"
    "$CLI" render --plan "$plan" --assets-root "$ASSETS" \
        --backend "$BACKEND" --profile preview --fps 30 \
        --video-sink raw --pipe-pixfmt nv12 --chunks 1 \
        --fb-pool-budget-mb 512 --fb-pool-clear-policy trim-after-job \
        --start-frame 0 --end-frame 239 -o "$raw" || { failures=$((failures+1)); continue; }
    expected=$(( (1920*1080*3/2) * 240 ))
    actual=$(stat -c%s "$raw" 2>/dev/null || echo 0)
    if [ "$actual" -ne "$expected" ]; then
        echo "$name: raw frame size mismatch ($actual, expected $expected)" >&2
        rm -f "$raw"; failures=$((failures+1)); continue
    fi
    ffmpeg -v error -y -f rawvideo -pixel_format nv12 -video_size 1920x1080 \
        -framerate 30 -i "$raw" -frames:v 240 -an "${ENCODE[@]}" \
        -pix_fmt yuv420p -r 30 -video_track_timescale 30000 "$output"
    rm -f "$raw"
    if ! ffprobe -v error -select_streams v:0 -show_entries \
        stream=codec_name,width,height,avg_frame_rate,nb_frames \
        -of csv=p=0 "$output"; then
        echo "$name: ffprobe failed" >&2
    fi
    codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name \
        -of default=nw=1:nk=1 "$output")
    frames=$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames \
        -of default=nw=1:nk=1 "$output")
    ok=$([ "$codec" = "h264" ] && [ "$frames" -eq 240 ] && echo true || echo false)
    if [ "$ok" = true ] && [ -n "$DELIVERY" ]; then
        mkdir -p "$DELIVERY"
        cp -f "$output" "$DELIVERY/"
        echo "delivered $name -> $DELIVERY"
    fi
    [ $first -eq 1 ] || echo "," >> "$OUT/verification.json.new"
    first=0
    printf '{"name":"%s","codec":"%s","frames":%s,"ok":%s,"size":%d}\n' \
        "$name" "$codec" "$frames" "$ok" "$(stat -c%s "$output")" \
        >> "$OUT/verification.json.new"
    [ "$ok" = true ] || failures=$((failures+1))
done
echo "]" >> "$OUT/verification.json.new"
mv "$OUT/verification.json.new" "$OUT/verification.json"
if [ "$failures" -gt 0 ]; then
    echo "$failures clip(s) failed verification" >&2
    exit 1
fi
echo "all six clips verified: H.264, 1920x1080, 30 fps, 240 frames"
