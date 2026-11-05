#!/bin/bash
# Upload verified chapter cards to Drive and write UPLOAD-MANIFEST.{json,md}.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
JOB="${CHAPTER_CARDS_JOB:-$ROOT/out/chapter_cards_showcase_v1}"
PREFIX="${CHAPTER_CARDS_PREFIX:-CHAPTER_CARD}"
ART="$JOB/mp4"
LOGS="$JOB/logs"
DRIVE="$REPO/RenderingGen/renderinggen/drive-upload"
CREDS="$REPO/RenderingGen/UploadDrive/credentials.json"
TOKEN="$REPO/RenderingGen/UploadDrive/token.json"
FOLDER="1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS"

mkdir -p "$LOGS"
: > "$LOGS/upload_progress.txt"

for f in "$ART"/*.mp4; do
  [ -e "$f" ] || continue
  slug=$(basename "$f" .mp4)
  log="$LOGS/upload_${slug}.log"
  if grep -q "DRIVE_UPLOAD_PASS" "$log" 2>/dev/null; then
    echo "$(date +%H:%M:%S) SKIP $slug (already uploaded)" >> "$LOGS/upload_progress.txt"
    continue
  fi
  echo "$(date +%H:%M:%S) UPLOAD $slug" >> "$LOGS/upload_progress.txt"
  "$DRIVE" -credentials "$CREDS" -token "$TOKEN" -folder "$FOLDER" \
    -file "$f" -name "${PREFIX}_${slug}_1920x1080.mp4" > "$log" 2>&1
  echo "$(date +%H:%M:%S) END $slug rc=$?" >> "$LOGS/upload_progress.txt"
done

python3 - "$JOB" "$FOLDER" <<'PY'
import json, re, sys
from pathlib import Path
job, folder = Path(sys.argv[1]), sys.argv[2]
catalog = json.loads((job / "plans" / "showcase.json").read_text())
pat = re.compile(r"DRIVE_UPLOAD_PASS id=(\S+) link=(\S+) parent=(\S+) sha256=(\S+) bytes=(\d+)")
files = []
for variant in catalog["variants"]:
    slug = variant["slug"]
    log = job / "logs" / f"upload_{slug}.log"
    text = log.read_text(errors="replace") if log.exists() else ""
    m = pat.search(text)
    entry = {k: variant[k] for k in
             ("slug", "chapter", "title", "display_font", "align", "reveal", "accent", "glow")}
    entry["local_file"] = f"mp4/{slug}.mp4"
    if m:
        entry.update(uploaded=True, drive_id=m.group(1), link=m.group(2),
                     parent=m.group(3), sha256=m.group(4), bytes=int(m.group(5)))
    else:
        entry.update(uploaded=False)
    files.append(entry)

manifest = {
    "folder_id": folder,
    "folder_url": f"https://drive.google.com/drive/u/1/folders/{folder}",
    "engine": catalog.get("engine", "Chronon3D (Vulkan) + ChrononTemplate chapter-card language"),
    "canvas": catalog["canvas"],
    "glow_note": catalog.get("glow_note", "blurred accent duplicate behind the warm-white title; native text style.glow is not used on the Vulkan lane"),
    "files": files,
}
(job / "UPLOAD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
lines = ["# Chapter cards — upload manifest", "",
         f"Folder: {manifest['folder_url']}", "",
         "| # | Chapter | Title | Display font | Align | Reveal | Accent | Drive | SHA-256 | Bytes |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for f in files:
    drive = f"[open]({f['link']})" if f["uploaded"] else "NOT UPLOADED"
    sha = f"`{f['sha256']}`" if f["uploaded"] else "—"
    size = f["bytes"] if f["uploaded"] else "—"
    lines.append(f"| {f['chapter']} | CAPITOLO {f['chapter']} | {f['title']} | "
                 f"{f['display_font']} | {f['align']} | {f['reveal']} | {f['accent']} | "
                 f"{drive} | {sha} | {size} |")
(job / "UPLOAD-MANIFEST.md").write_text("\n".join(lines) + "\n")
print("Wrote", job / "UPLOAD-MANIFEST.json")
print("Uploaded", sum(1 for f in files if f["uploaded"]), "of", len(files))
PY
