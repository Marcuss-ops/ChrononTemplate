#!/usr/bin/env bash
# Upload the Classic Apple long-phrase renders to the shared Google Drive folder.
#
# Same mechanism as tools/short_phrases/upload_short_phrases_drive.sh: every MP4
# goes up content-addressed through RenderingGen/bin/drive-upload, into the
# requested Drive folder, unless an optional DRIVE_SUBFOLDER is set.
#
# Usage:
#   tools/important_phrases/upload_classic_long_phrases_drive.sh [pack-dir]
#
# Overrides: DRIVE_FOLDER_ID, DRIVE_CREDENTIALS, DRIVE_TOKEN, DRIVE_SUBFOLDER.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd -- "$ROOT/.." && pwd)"
PACK="${1:-$ROOT/out/classic_long_phrase_v1}"
UPLOADER="$REPO/RenderingGen/bin/drive-upload"
CREDENTIALS="${DRIVE_CREDENTIALS:-$REPO/RenderingGen/UploadDrive/credentials.json}"
TOKEN="${DRIVE_TOKEN:-$REPO/RenderingGen/UploadDrive/token.json}"
DRIVE_FOLDER="${DRIVE_FOLDER_ID:-1cW_SrXc779dss5uwwDt0lgbQt8dN4Y8b}"
DRIVE_SUBFOLDER="${DRIVE_SUBFOLDER-Classic Apple Long Phrases}"

for required in "$UPLOADER" "$CREDENTIALS" "$TOKEN"; do
  if [[ ! -r "$required" ]]; then
    printf 'Missing or unreadable upload requirement: %s\n' "$required" >&2
    exit 1
  fi
done

shopt -s nullglob
files=("$PACK"/classic_playfair_*.mp4)
if [[ ${#files[@]} -eq 0 ]]; then
  printf 'No Classic Apple MP4 files in %s — render first (tools/important_phrases/render_classic_long_phrases.sh)\n' "$PACK" >&2
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
    -name "$(basename -- "$file")" \
    -sha256 "$digest"
done

if [[ -n "$DRIVE_SUBFOLDER" ]]; then
  printf 'Uploaded %d Classic Apple MP4 files to Drive folder %s/%s\n' \
    "${#files[@]}" "$DRIVE_FOLDER" "$DRIVE_SUBFOLDER"
else
  printf 'Uploaded %d Classic Apple MP4 files directly to Drive folder %s\n' \
    "${#files[@]}" "$DRIVE_FOLDER"
fi
