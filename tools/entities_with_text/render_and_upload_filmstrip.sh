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

id="modern_entity_06_editorial_filmstrip_jobs"
plan_path="$PLANS_DIR/${id}.plan.json"
video_file="$VIDEOS_DIR/${id}.mp4"

echo "=== Rendering Editorial Filmstrip Jobs with Chronon GPU ==="
"$CLI" render \
  --plan "$plan_path" \
  --assets-root "$ROOT"

echo "=== Uploading: ${id}.mp4 to $SUBFOLDER ==="
"$BIN" \
  -credentials "$CREDS" \
  -token "$TOKEN" \
  -folder "$PARENT" \
  -subfolder "$SUBFOLDER" \
  -file "$video_file" \
  -name "${id}.mp4"

echo "=== FILMSTRIP EDITORIAL RENDER AND UPLOAD DONE ==="
