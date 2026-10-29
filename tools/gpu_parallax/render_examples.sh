#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"
CLI="${CHRONON3D_CLI:-$WORKSPACE/Chronon3d-mainfix/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli}"
AUTHOR="$ROOT/tools/gpu_parallax/author_food_parallax.py"
PLAN_DIR="$ROOT/examples/gpu_food_parallax_v1/plans"
OUT="${1:-$ROOT/out/gpu_food_parallax_v1}"
EMITTER="${CHRONONTEMPLATE_GPU_PARALLAX_EMITTER:-$ROOT/build/release-fast/chronontemplate_emit_gpu_food_parallax_examples}"

[[ -x "$CLI" ]] || { echo "Chronon3D CLI not found: $CLI" >&2; exit 1; }
python3 -c 'from PIL import Image' >/dev/null 2>&1 || {
  echo "Python Pillow is required to author and wrap the parallax assets" >&2; exit 1;
}
python3 -c 'from PIL import Image' >/dev/null 2>&1 || {
  echo "Python Pillow is required to wrap raw GPU frames as PNG" >&2; exit 1;
}

[[ -x "$EMITTER" ]] || { echo "Plan emitter not found: $EMITTER" >&2; exit 1; }
mkdir -p "$PLAN_DIR" "$OUT/png" "$OUT/raw"
"$EMITTER" "$PLAN_DIR"
python3 "$AUTHOR"

for plan in "$PLAN_DIR"/*.plan.json; do
  stem="$(basename "$plan" .plan.json)"
  for frame in 0 90 179; do
    raw="$OUT/raw/${stem}_f${frame}.rgba"
    png="$OUT/png/${stem}_f${frame}.png"
    echo "== $stem frame $frame (strict Vulkan)"
    "$CLI" render --plan "$plan" --assets-root "$WORKSPACE" \
      --backend vulkan --profile maximum --start-frame "$frame" --end-frame "$frame" \
      --video-sink raw --pipe-pixfmt rgba -v error -o "$raw"
    python3 - "$raw.timing.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    report = json.load(stream)
gpu = report["job"]["gpu"]
if gpu["effective_backend"] != "vulkan":
    raise SystemExit(f"expected Vulkan, got {gpu['effective_backend']}")
if gpu["gpu_nodes"] <= 0 or gpu["software_fallback_nodes"] != 0:
    raise SystemExit("GPU render used no Vulkan nodes or fell back to software")
print(f"Vulkan nodes={gpu['gpu_nodes']}; software fallback=0")
PY
    python3 - "$raw" "$png" <<'PY'
from PIL import Image
import sys
Image.frombytes("RGBA", (1920, 1080), open(sys.argv[1], "rb").read()).save(sys.argv[2])
PY
    rm -f "$raw"
  done
done

echo "GPU previews saved under $OUT/png"
