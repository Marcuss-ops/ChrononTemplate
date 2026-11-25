#!/usr/bin/env bash
# Upload the 14+14 typewriter pack (2D + 3D) to the shared Google Drive folder.
#
# Stessa meccanica di tools/short_phrases/upload_short_phrases_drive.sh: ogni
# MP4 sale content-addressed attraverso RenderingGen/bin/drive-upload, nella
# cartella Drive richiesta, con SHA-256 calcolato qui e verificato dal tool.
#
# Usage:
#   tools/important_phrases/upload_typewriter_pack_2d3d_drive.sh [pack-dir]
#
# Overrides: DRIVE_FOLDER_ID, DRIVE_CREDENTIALS, DRIVE_TOKEN, DRIVE_SUBFOLDER.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO="$(cd -- "$ROOT/.." && pwd)"
PACK="${1:-$REPO/RenderingGen/Upload/typewriter_pack_2d3d_20261125}"
UPLOADER="$REPO/RenderingGen/bin/drive-upload"
CREDENTIALS="${DRIVE_CREDENTIALS:-$REPO/refactored/credentials.json}"
TOKEN="${DRIVE_TOKEN:-$REPO/refactored/token.json}"
DRIVE_FOLDER="${DRIVE_FOLDER_ID:-1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS}"
DRIVE_SUBFOLDER="${DRIVE_SUBFOLDER-}"

for required in "$UPLOADER" "$CREDENTIALS" "$TOKEN"; do
  if [[ ! -r "$required" ]]; then
    printf 'Missing or unreadable upload requirement: %s\n' "$required" >&2
    exit 1
  fi
done

shopt -s nullglob
files=("$PACK"/videos/*.mp4)
if [[ ${#files[@]} -eq 0 ]]; then
  printf 'No typewriter MP4 files in %s — render first (tools/important_phrases/render_typewriter_pack_v2.py --render)\n' "$PACK" >&2
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
  printf 'Uploaded %d typewriter MP4 files to Drive folder %s/%s\n' \
    "${#files[@]}" "$DRIVE_FOLDER" "$DRIVE_SUBFOLDER"
else
  printf 'Uploaded %d typewriter MP4 files directly to Drive folder %s\n' \
    "${#files[@]}" "$DRIVE_FOLDER"
fi
