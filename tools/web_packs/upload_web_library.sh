#!/usr/bin/env bash
# Publish the unified web library to Drive.
#
# The uploader creates a child folder only when it does not exist, so each
# family is created once and the remaining clips go straight into its id.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/../../.." && pwd)
OUT="$ROOT/ChrononTemplate/out/web_v1"
UPLOADER="$ROOT/RenderingGen/bin/drive-upload"
CREDS="$ROOT/refactored/credentials.json"
TOKEN="$ROOT/refactored/token.json"
DRIVE_PARENT="1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"
TOP_NAME="${TOP_NAME:-WEB_20261125}"
EXPECTED_VIDEOS=33

for path in "$UPLOADER" "$CREDS" "$TOKEN" "$OUT/README.md" "$OUT/manifest.json" "$OUT/verification.json"; do
    [ -e "$path" ] || { echo "missing: $path" >&2; exit 1; }
done

python3 - "$OUT/verification.json" "$EXPECTED_VIDEOS" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1], encoding="utf-8"))
expected = int(sys.argv[2])
bad = [row for row in rows if not row.get("ok")]
if len(rows) != expected or bad:
    print(f"verification is not clean: {len(rows)} checked, {len(bad)} failed (expected {expected})", file=sys.stderr)
    for row in bad[:10]:
        print(f"  {row.get('family')}/{row.get('name')}", file=sys.stderr)
    raise SystemExit(1)
PY

mapfile -t videos < <(find "$OUT/videos" -mindepth 2 -maxdepth 2 -type f -name '*.mp4' ! -name '*.partial.mp4' -size +0c | sort)
[ "${#videos[@]}" -eq "$EXPECTED_VIDEOS" ] || { echo "expected $EXPECTED_VIDEOS videos, found ${#videos[@]}" >&2; exit 1; }

LAST_PARENT=""
upload_file() {
    local parent="$1" sub="$2" file="$3" name="$4"
    local args=(
        -credentials "$CREDS"
        -token "$TOKEN"
        -folder "$parent"
        -file "$file"
        -name "$name"
    )
    [ -n "$sub" ] && args+=(-subfolder "$sub")
    local out
    out=$("$UPLOADER" "${args[@]}")
    printf '%s\n' "$out"
    LAST_PARENT=$(printf '%s\n' "$out" | sed -n 's/.* parent=\([^ ]*\).*/\1/p' | tail -n 1)
    [ -n "$LAST_PARENT" ] || { echo "uploader returned no parent for $file" >&2; exit 1; }
}

# The README creates (or reuses) the top folder and gives us its id.
upload_file "$DRIVE_PARENT" "$TOP_NAME" "$OUT/README.md" README.md
TOP_ID="$LAST_PARENT"
echo "TOP_FOLDER_ID=$TOP_ID"

for file in "$OUT/manifest.json" "$OUT/verification.json"; do
    upload_file "$TOP_ID" "" "$file" "$(basename "$file")"
done

shopt -s nullglob
for file in "$OUT"/contact_sheets/*.jpg; do
    upload_file "$TOP_ID" "" "$file" "$(basename "$file")"
done
shopt -u nullglob

for family_dir in "$OUT"/videos/*/; do
    family=$(basename "$family_dir")
    mapfile -t family_videos < <(find "$family_dir" -maxdepth 1 -type f -name '*.mp4' ! -name '*.partial.mp4' -size +0c | sort)
    [ "${#family_videos[@]}" -gt 0 ] || { echo "no videos in $family" >&2; exit 1; }

    upload_file "$TOP_ID" "$family" "${family_videos[0]}" "$(basename "${family_videos[0]}")"
    family_id="$LAST_PARENT"
    echo "FAMILY_ID=$family $family_id"

    for file in "${family_videos[@]:1}"; do
        upload_file "$family_id" "" "$file" "$(basename "$file")"
    done
done

echo "DRIVE_FOLDER_ID=$TOP_ID"
echo "DRIVE_FOLDER_LINK=https://drive.google.com/drive/folders/$TOP_ID"
