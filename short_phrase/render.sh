#!/usr/bin/env bash
# render.sh [out_dir] [recipe_id ...] : compile plans then render with Chronon3D (Vulkan).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="${1:-$HERE/out}"; shift || true
REPO="$(cd "$HERE/../.." && pwd)"
CLI=""
for c in "$REPO"/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli \
         "$REPO"/Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli \
         "$REPO"/Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli; do
  [[ -x "$c" ]] && CLI="$c" && break; done
python3 "$HERE/compile.py" "$OUT" "$@"
for plan in "$OUT"/*.plan.json; do
  n="$(basename "$plan" .plan.json)"
  if [[ $# -gt 0 ]] && ! printf '%s\n' "$@" | grep -qx "$n"; then continue; fi
  "$CLI" render --plan "$plan" --assets-root "$REPO/Chronon3d" --backend vulkan --hardware nvenc \
    --encoder-backend native --gpu-hot-path-mode require_gpu_native --codec h264 --fps 30 \
    --rate-control qp --qp 18 -o "$OUT/$n.mp4" >"$OUT/$n.log" 2>&1 && echo "rendered $n" || { echo "FAILED $n"; tail -5 "$OUT/$n.log"; }
done
