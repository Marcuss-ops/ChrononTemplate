#!/usr/bin/env bash
# End-to-end acceptance for the six vector editorial map styles:
# DTO -> RenderPlan -> validated MP4 -> extracted still.
#
# Required tools: chronontemplate_emit_editorial_map, chronon3d_cli, ffmpeg,
# ffprobe, python3 with Pillow.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT_ROOT="$(cd "$ROOT/.." && pwd)"

STYLES="${STYLES:-editorial_vox paper_cutout dark_radar blueprint connection_arc floating_island}"
SCENES_DIR="${SCENES_DIR:-$PROJECT_ROOT/.tmp/editorial-scenes}"
PLANS_DIR="${PLANS_DIR:-$PROJECT_ROOT/.tmp/editorial-plans}"
CLIPS_DIR="${CLIPS_DIR:-$PROJECT_ROOT/.tmp/editorial-clips}"
FRAMES_DIR="${FRAMES_DIR:-$PROJECT_ROOT/.tmp/editorial-frames}"
FRAME="${FRAME:-210}"
BACKEND="${BACKEND:-vulkan}"

EMITTER="${EMITTER_BIN:-$ROOT/build/dev-fast/chronontemplate_emit_editorial_map}"
if [[ ! -x "$EMITTER" ]]; then
    echo "missing emitter: $EMITTER" >&2
    exit 2
fi

CLI="${CHRONON_BIN:-$PROJECT_ROOT/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli}"
if [[ ! -x "$CLI" ]]; then
    CLI="$PROJECT_ROOT/Chronon3d/build/chronon/linux-video-test/apps/chronon3d_cli/chronon3d_cli"
fi
if [[ ! -x "$CLI" ]]; then
    echo "missing chronon3d_cli; set CHRONON_BIN" >&2
    exit 2
fi

mkdir -p "$PLANS_DIR" "$CLIPS_DIR" "$FRAMES_DIR"

for style in $STYLES; do
    scene="$SCENES_DIR/$style.scene.json"
    plan="$PLANS_DIR/$style.plan.json"
    clip="$CLIPS_DIR/$style.mp4"
    if [[ ! -f "$scene" ]]; then
        echo "missing DTO: $scene" >&2
        exit 2
    fi
    echo "== $style: DTO -> plan"
    "$EMITTER" "$scene" "$plan"
    echo "== $style: validate"
    validation="$("$CLI" validate --plan "$plan" --assets-root "$ROOT")"
    if ! grep -q '"valid": true' <<<"$validation"; then
        echo "$validation" >&2
        echo "validation failed for $style" >&2
        exit 1
    fi
    echo "== $style: render $clip"
    "$CLI" render \
        --plan "$plan" \
        --assets-root "$ROOT" \
        --backend "$BACKEND" \
        --output "$clip"
done

python3 - "$CLIPS_DIR" "$FRAMES_DIR" "$FRAME" $STYLES <<'PY'
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageStat

clips_dir = Path(sys.argv[1])
frames_dir = Path(sys.argv[2])
frame_number = int(sys.argv[3])
styles = sys.argv[4:]

failures = []
for style in styles:
    clip = clips_dir / f"{style}.mp4"
    if not clip.is_file() or clip.stat().st_size == 0:
        failures.append(f"{style}: missing or empty clip")
        continue
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate,duration",
         "-of", "json", str(clip)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    width = int(stream["width"])
    height = int(stream["height"])
    frames = int(stream.get("nb_read_frames") or 0)
    duration = float(stream.get("duration") or 0)
    if (width, height) != (1920, 1080):
        failures.append(f"{style}: {width}x{height}, want 1920x1080")
    if frames != 240:
        failures.append(f"{style}: {frames} frames, want 240")
    if abs(duration - 8.0) > 0.05:
        failures.append(f"{style}: {duration:.3f}s, want 8.0s")
    still = frames_dir / f"{style}_frame{frame_number:04d}.png"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{frame_number / 30.0:.6f}",
         "-i", str(clip), "-frames:v", "1", str(still)],
        check=True,
    )
    image = Image.open(still).convert("RGB")
    stat = ImageStat.Stat(image)
    if image.size != (1920, 1080):
        failures.append(f"{style}: still {image.size}, want 1920x1080")
    if sum(stat.stddev) < 3.0:
        failures.append(f"{style}: still looks blank (stddev {sum(stat.stddev):.2f})")
    colors = image.getcolors(maxcolors=1_000_000)
    distinct = len(colors) if colors is not None else 1_000_000
    print(f"{style}: {width}x{height} {frames}f {duration:.3f}s "
          f"still={still.name} stddev={sum(stat.stddev):.2f} colors={distinct}")

if failures:
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    raise SystemExit(1)
print(f"PASS: {len(styles)} editorial map clips")
PY
