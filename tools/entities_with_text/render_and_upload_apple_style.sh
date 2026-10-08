#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/pierone/src/go-master/projects/Pyt/VeloxEditing"
CLI="$ROOT/Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli"
PLANS_DIR="$ROOT/ChrononTemplate/out/modern_entities_with_text/plans"
VIDEOS_DIR="$ROOT/ChrononTemplate/out/modern_entities_with_text/videos"
CREDS="$HOME/.config/velox/credentials.json"
TOKEN="$HOME/.config/velox/token.json"
PARENT="1Sc5gBaNCAsAkrfM-j9Ccm4kNwrKBBYuC"
SUBFOLDER="Modern Entities With Text"
BIN="$ROOT/RenderingGen/bin/drive-upload"

items=(
  "modern_entity_01_neon_glass_hoopin"
  "modern_entity_02_neon_card_portrait_cyan"
  "modern_entity_05_neon_card_gold"
)

echo "=== Rendering 3 Clean Apple / Figma Style Entities with Chronon GPU ==="
for id in "${items[@]}"; do
  plan_path="$PLANS_DIR/${id}.plan.json"
  echo "--- Rendering: $id ---"
  "$CLI" render \
    --plan "$plan_path" \
    --assets-root "$ROOT"
done

echo "=== Uploading to Drive Subfolder: '$SUBFOLDER' ==="
for id in "${items[@]}"; do
  video_file="$VIDEOS_DIR/${id}.mp4"
  echo "Uploading: ${id}.mp4 to $SUBFOLDER..."
  "$BIN" \
    -credentials "$CREDS" \
    -token "$TOKEN" \
    -folder "$PARENT" \
    -subfolder "$SUBFOLDER" \
    -file "$video_file" \
    -name "${id}.mp4"
done

echo "=== ALL 3 CLEAN APPLE-STYLE ENTITIES UPLOADED SUCCESSFULLY ==="
