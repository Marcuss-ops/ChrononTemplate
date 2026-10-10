#!/usr/bin/env bash
# Upload the title-camera v2 renders to the shared Google Drive folder.
#
# Uses RenderingGen's content-addressed uploader (RenderingGen/bin/drive-upload):
# every MP4 is uploaded with its SHA-256 directly into the requested Drive
# folder unless an optional DRIVE_SUBFOLDER is set.
#
# Usage:
#   tools/camera_roll/upload_title_camera_v2_drive.sh [renders-dir]
#
# Overrides: DRIVE_FOLDER_ID, DRIVE_CREDENTIALS, DRIVE_TOKEN, DRIVE_SUBFOLDER.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd -- "$ROOT/.." && pwd)"
PACK="${1:-$ROOT/out/camera_title_documentary_v2}"
UPLOADER="$REPO/RenderingGen/bin/drive-upload"
CREDENTIALS="${DRIVE_CREDENTIALS:-$REPO/RenderingGen/UploadDrive/credentials.json}"
TOKEN="${DRIVE_TOKEN:-$REPO/RenderingGen/UploadDrive/token.json}"
DRIVE_FOLDER="${DRIVE_FOLDER_ID:-1G6zct81UYjMhVzj5gfRYvdWUNZ15JFSH}"
DRIVE_SUBFOLDER="${DRIVE_SUBFOLDER:-}"

for required in "$UPLOADER" "$CREDENTIALS" "$TOKEN"; do
  if [[ ! -r "$required" ]]; then
    printf 'Missing or unreadable upload requirement: %s\n' "$required" >&2
    exit 1
  fi
done

shopt -s nullglob
files=("$PACK"/simplicity/*.mp4 "$PACK"/rome/*.mp4)
if [[ ${#files[@]} -eq 0 ]]; then
  printf 'No MP4 files in %s — render first (chronontemplate_emit_title_camera_v2 + chronon3d_cli render)\n' "$PACK" >&2
  exit 1
fi

for file in "${files[@]}"; do
  digest="$(sha256sum "$file" | cut -d ' ' -f 1)"
  "$UPLOADER" \
    -credentials "$CREDENTIALS" \
    -token "$TOKEN" \
    -folder "$DRIVE_FOLDER" \
    ${DRIVE_SUBFOLDER:+-subfolder "$DRIVE_SUBFOLDER"} \
    -file "$file" \
    -name "$(basename -- "$(dirname -- "$file")")_$(basename -- "$file")" \
    -sha256 "$digest"
done

if [[ -n "$DRIVE_SUBFOLDER" ]]; then
  printf 'Uploaded %d title-camera v2 MP4 files to Drive folder %s/%s\n' \
    "${#files[@]}" "$DRIVE_FOLDER" "$DRIVE_SUBFOLDER"
else
  printf 'Uploaded %d title-camera v2 MP4 files directly to Drive folder %s\n' \
    "${#files[@]}" "$DRIVE_FOLDER"
fi
