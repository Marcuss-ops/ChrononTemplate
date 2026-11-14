#!/bin/bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
JOB="$ROOT/ChrononTemplate/renders/date_odometer_4dates"
VIDEO="$JOB/odometer_4dates.mp4"
DRIVE="$ROOT/RenderingGen/renderinggen/drive-upload"
CREDS="$ROOT/RenderingGen/UploadDrive/credentials.json"
TOKEN="$ROOT/RenderingGen/UploadDrive/token.json"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/ops/lib/common.sh"
FOLDER="$VELOX_DRIVE_OVERLAY_ROOT"
NAME="FOCUS_4dates_ODOMETER_CLEAN_1920x1080.mp4"
LOG="$JOB/logs/upload_odometer.log"
mkdir -p "$JOB/logs"
if [ ! -s "$VIDEO" ]; then
  echo "odometer video missing: $VIDEO" >&2
  exit 1
fi
"$DRIVE" -credentials "$CREDS" -token "$TOKEN" -folder "$FOLDER" \
  -file "$VIDEO" -name "$NAME" >"$LOG" 2>&1
rc=$?
cat "$LOG"
if [ $rc -ne 0 ]; then exit $rc; fi
python3 - "$VIDEO" "$LOG" "$FOLDER" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
video, log, folder = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
text = log.read_text(errors="replace")
m = re.search(r"DRIVE_UPLOAD_PASS id=(\S+) link=(\S+) parent=(\S+) sha256=(\S+) bytes=(\d+)", text)
if not m:
    raise SystemExit("no DRIVE_UPLOAD_PASS line")
sha = hashlib.sha256(video.read_bytes()).hexdigest()
if sha.lower() != m.group(4).lower():
    raise SystemExit(f"sha mismatch: local {sha}, upload {m.group(4)}")
out_dir = video.parent
manifest = {
    "folder_id": folder,
    "folder_url": f"https://drive.google.com/drive/u/1/folders/{folder}",
    "file": video.name,
    "drive_name": "FOCUS_4dates_ODOMETER_CLEAN_1920x1080.mp4",
    "drive_id": m.group(1),
    "link": m.group(2),
    "sha256": sha,
    "bytes": int(m.group(5)),
    "canvas": "1920x1080",
    "fps": 30,
    "duration_seconds": 10.667,
    "frames": 320,
    "dates": ["1948", "1969", "1998", "2026"],
    "labels": [],
    "font_dates": "PlayfairDisplay.ttf",
    "font_labels": None,
    "style": "light editorial: cream, Playfair only, static rail, terracotta underline; no reticle, pin, count or footer",
    "motion": "century 19/20 static, last two digits roll vertically in a cream slot, underline moves to active date",
}
(out_dir / "UPLOAD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
(out_dir / "UPLOAD-MANIFEST.md").write_text(
    "# Focus 4 dates — ODOMETER upload\n\n"
    f"Folder: {manifest['folder_url']}\n\n"
    f"- File: [{manifest['drive_name']}]({manifest['link']})\n"
    f"- SHA-256: `{manifest['sha256']}`\n"
    f"- Size: {manifest['bytes']} bytes\n"
    f"- Canvas: {manifest['canvas']} · {manifest['fps']} fps · {manifest['frames']} frames\n"
    f"- Dates: {' · '.join(manifest['dates'])}\n"
    f"- Style: {manifest['style']}\n"
)
print("manifest:", out_dir / "UPLOAD-MANIFEST.json")
PY
