#!/usr/bin/env bash
# Render the four Linux-native newspaper scenes through Chronon3D.
#
# The old tools/youtuber_style scenes required Blend2D and Windows paths. This
# family composes the four pages in C++ (make_newspaper_pages.cpp, stb only),
# emits pure RenderPlan V3 documents (image layer + live marker/redaction
# overlays), rasterizes with the canonical CLI, encodes with ffmpeg/libx264
# and verifies every stream. The Python composer is kept only as a fallback.
#
# Usage:
#   tools/newspaper/render_newspaper_pages.sh [out-dir]
#
# Environment:
#   CHRONON3D_CLI    explicit chronon3d_cli path
#   CHRONON_BACKEND  default: software (use vulkan only if the host supports it)
#   CHRONON_PROFILE  default: preview (draft is faster, production is slower)
#   SCENE            optional single scene name, e.g. newspaper_dossier
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
OUT="${1:-$ROOT/out/newspaper_pages}"
PLANS="$OUT/plans"
RENDERS="$OUT/renders"
mkdir -p "$PLANS" "$RENDERS"

# Part 1 in C++: build the composer (CMake target if a build tree exists,
# otherwise a direct g++ build against the Chronon3d vcpkg stb headers).
CPP_BIN="$ROOT/build/newspaper/chronontemplate_make_newspaper_pages"
mkdir -p "$(dirname "$CPP_BIN")"
built=0
for candidate in "$ROOT"/build/*/chronontemplate_make_newspaper_pages "$ROOT"/build/chronontemplate_make_newspaper_pages; do
    if [ -x "$candidate" ]; then CPP_BIN="$candidate"; built=1; break; fi
done
if [ "$built" -eq 0 ] && command -v g++ >/dev/null; then
    STB_INC=""
    for d in "$REPO"/Chronon3d/vcpkg_installed/*/x64-linux/include /usr/include; do
        if [ -f "$d/stb_image.h" ] && [ -f "$d/stb_truetype.h" ]; then STB_INC="$d"; break; fi
    done
    if [ -n "$STB_INC" ]; then
        g++ -std=c++20 -O2 -Wno-missing-field-initializers -I"$STB_INC" \
            "$ROOT/tools/newspaper/make_newspaper_pages.cpp" -o "$CPP_BIN" && built=1
    fi
fi
if [ "$built" -eq 1 ]; then
    "$CPP_BIN" "$ROOT"
else
    echo "C++ composer unavailable; falling back to Python/Pillow composer" >&2
    python3 "$ROOT/tools/newspaper/make_newspaper_pages.py"
fi
python3 "$ROOT/tools/newspaper/emit_newspaper_plans.py" "$PLANS"

for page in front_page dossier highlighter memo; do
    [[ -f "$ROOT/assets/newspaper/pages/$page.png" ]] || {
        echo "missing page asset: $ROOT/assets/newspaper/pages/$page.png" >&2
        exit 1
    }
done

CLI="${CHRONON3D_CLI:-}"
if [ -z "$CLI" ]; then
    for candidate in \
        "$REPO/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli" \
        "$REPO/Chronon3d/build/chronon/linux-video-release.root-bin/apps/chronon3d_cli/chronon3d_cli" \
        "$REPO/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"; do
        if [ -x "$candidate" ]; then CLI="$candidate"; break; fi
    done
fi
[[ -x "$CLI" ]] || { echo "chronon3d_cli not found; set CHRONON3D_CLI" >&2; exit 1; }
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || {
    echo "ffmpeg and ffprobe are required" >&2; exit 1
}

BACKEND="${CHRONON_BACKEND:-software}"
PROFILE="${CHRONON_PROFILE:-preview}"
status_file="$OUT/verification.tsv"
: > "$status_file"
failures=0

for plan in "$PLANS"/newspaper_*.plan.json; do
    name="$(basename "$plan" .plan.json)"
    if [[ -n "${SCENE:-}" && "$name" != "$SCENE" ]]; then
        continue
    fi
    frames="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["canvas"]["duration_frames"])' "$plan")"
    raw="$RENDERS/$name.nv12"
    mp4="$OUT/$name.mp4"
    echo "== $name ($frames frames, $BACKEND/$PROFILE)"
    "$CLI" validate --plan "$plan" --assets-root "$ROOT" >/dev/null
    "$CLI" render --plan "$plan" --assets-root "$ROOT" \
        --backend "$BACKEND" --profile "$PROFILE" --fps 30 \
        --video-sink raw --pipe-pixfmt nv12 --chunks 1 \
        --fb-pool-budget-mb 512 --fb-pool-clear-policy trim-after-job \
        --start-frame 0 --end-frame "$((frames - 1))" -v warn -o "$raw"
    expected=$((1920 * 1080 * 3 / 2 * frames))
    actual="$(stat -c%s "$raw" 2>/dev/null || echo 0)"
    if [ "$actual" -ne "$expected" ]; then
        echo "$name: raw size mismatch ($actual, expected $expected)" >&2
        rm -f "$raw"; failures=$((failures + 1)); continue
    fi
    ffmpeg -v error -y -f rawvideo -pixel_format nv12 -video_size 1920x1080 \
        -framerate 30 -i "$raw" -frames:v "$frames" -an \
        -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -r 30 \
        -video_track_timescale 30000 "$mp4"
    rm -f "$raw"
    codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$mp4")"
    width="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$mp4")"
    height="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$mp4")"
    rate="$(ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate -of csv=p=0 "$mp4")"
    actual_frames="$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 "$mp4")"
    if [[ "$codec" == h264 && "$width" == 1920 && "$height" == 1080 && \
          "$rate" == 30/1 && "$actual_frames" == "$frames" ]]; then
        bytes="$(stat -c%s "$mp4")"
        printf '%s\t%s\t%s\t%s\t%s\t%s\tOK\n' "$name" "$codec" "$width" "$height" \
            "$actual_frames" "$bytes" >> "$status_file"
        echo "verified $name: H.264 ${width}x${height} 30 fps ${actual_frames} frames"
    else
        echo "$name: verification failed ($codec ${width}x${height} $rate $actual_frames frames)" >&2
        failures=$((failures + 1))
    fi
done

if [ "$failures" -gt 0 ]; then
    echo "$failures clip(s) failed verification" >&2
    exit 1
fi
echo "all newspaper clips verified; manifest: $status_file"
