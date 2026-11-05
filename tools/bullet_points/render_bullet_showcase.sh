#!/bin/bash
# Render the ten bullet-point variants on the GPU (Vulkan) lane.
# Usage: tools/bullet_points/render_bullet_showcase.sh [slug ...]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="${CHRONON_BIN:-$ROOT/../Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli}"
JOB="${BULLET_JOB:-$ROOT/out/bullet_points_showcase_v1}"
PLANS="$JOB/plans"
ART="$JOB/mp4"
LOGS="$JOB/logs"
ASSETS="$ROOT"

mkdir -p "$ART" "$LOGS"
if [ ! -x "$CLI" ]; then
  echo "chronon3d_cli not found at $CLI (set CHRONON_BIN)" >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  SLUGS="$*"
else
  SLUGS=$(cd "$PLANS" && ls *.plan.json | sed 's/\.plan\.json$//' | sort)
fi

render_one() {
  local slug="$1"
  echo "$(date +%H:%M:%S) START $slug" >> "$LOGS/progress.txt"
  "$CLI" render-plan \
    --input "$PLANS/$slug.plan.json" \
    --output "$ART/$slug.mp4" \
    --assets-root "$ASSETS" \
    --backend vulkan > "$LOGS/$slug.log" 2>&1
  local rc=$?
  echo "$rc" > "$LOGS/$slug.status"
  echo "$(date +%H:%M:%S) END $slug rc=$rc" >> "$LOGS/progress.txt"
  return $rc
}

# Render one at a time. Two or three concurrent 1080p Vulkan jobs exhaust
# the VMA pool (vmaCreateImage VkResult=-2) around frame 50-60.
fail=0
for slug in $SLUGS; do
  render_one "$slug" || fail=1
done

echo "$(date +%H:%M:%S) ALL_DONE fail=$fail" >> "$LOGS/progress.txt"
exit $fail
