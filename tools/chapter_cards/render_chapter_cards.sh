#!/bin/bash
# Render the ten chapter cards on the GPU (Vulkan), one at a time.
# Usage: tools/chapter_cards/render_chapter_cards.sh [slug ...]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="${CHRONON_BIN:-$ROOT/../Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli}"
JOB="${CHAPTER_CARDS_JOB:-$ROOT/out/chapter_cards_showcase_v1}"
PLANS="$JOB/plans"
ART="$JOB/mp4"
LOGS="$JOB/logs"

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

fail=0
for slug in $SLUGS; do
  echo "$(date +%H:%M:%S) START $slug" >> "$LOGS/progress.txt"
  "$CLI" render-plan \
    --input "$PLANS/$slug.plan.json" \
    --output "$ART/$slug.mp4" \
    --assets-root "$ROOT" \
    --backend vulkan > "$LOGS/$slug.log" 2>&1
  rc=$?
  echo "$rc" > "$LOGS/$slug.status"
  echo "$(date +%H:%M:%S) END $slug rc=$rc" >> "$LOGS/progress.txt"
  [ "$rc" -eq 0 ] || fail=1
done

echo "$(date +%H:%M:%S) ALL_DONE fail=$fail" >> "$LOGS/progress.txt"
exit $fail
