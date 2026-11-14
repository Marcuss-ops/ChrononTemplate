#!/bin/bash
# Upload the verified bullet-point variants to the shared Drive folder and
# write UPLOAD-MANIFEST.{json,md} next to the renders.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
JOB="${BULLET_JOB:-$ROOT/out/bullet_points_showcase_v1}"
PREFIX="${BULLET_PREFIX:-BULLETPOINTS}"
ART="$JOB/mp4"
LOGS="$JOB/logs"
DRIVE="$REPO/RenderingGen/renderinggen/drive-upload"
CREDS="$REPO/RenderingGen/UploadDrive/credentials.json"
TOKEN="$REPO/RenderingGen/UploadDrive/token.json"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/ops/lib/common.sh"
FOLDER="$VELOX_DRIVE_OVERLAY_ROOT"

mkdir -p "$LOGS"
: > "$LOGS/upload_progress.txt"

SLUGS=$(cd "$ART" && ls *.mp4 | sed 's/\.mp4$//' | sort)
for slug in $SLUGS; do
  f="$ART/$slug.mp4"
  log="$LOGS/upload_${slug}.log"
  if grep -q "DRIVE_UPLOAD_PASS" "$log" 2>/dev/null; then
    echo "$(date +%H:%M:%S) SKIP $slug (already uploaded)" >> "$LOGS/upload_progress.txt"
    continue
  fi
  if [ ! -s "$f" ]; then
    echo "$(date +%H:%M:%S) MISSING $slug" >> "$LOGS/upload_progress.txt"
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
    entry = {"slug": slug, "label": variant["label"], "reveal": variant["reveal"],
             "family": variant.get("family"), "motion_id": variant.get("motion_id"),
             "title_font": variant["title_font"], "body_font": variant["body_font"],
             "accent": variant["accent"], "glow": variant["glow"],
             "local_file": f"mp4/{slug}.mp4"}
    if m:
        entry.update(uploaded=True, drive_id=m.group(1), link=m.group(2),
                     parent=m.group(3), sha256=m.group(4), bytes=int(m.group(5)))
    else:
        entry.update(uploaded=False)
    files.append(entry)

manifest = {
    "folder_id": folder,
    "folder_url": f"https://drive.google.com/drive/u/1/folders/{folder}",
    "engine": "Chronon3D (Vulkan backend) + ChrononTemplate BulletListPack vocabulary",
    "canvas": catalog["canvas"],
    "content": catalog["content"],
    "glow_note": "no coloured glow. The four-family 03 uses a 2.5D scale/rise fallback; the standalone 05 mesh study uses an extruded glyph mesh.",
    "files": files,
}
(job / "UPLOAD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

lines = ["# Bullet points showcase — upload manifest", "",
         f"Folder: {manifest['folder_url']}", "",
         "| # | Variant | Family | Motion | Fonts (title / body) | Accent | Drive | SHA-256 | Bytes |",
         "|---|---|---|---|---|---|---|---|---|"]
for i, f in enumerate(files, 1):
    drive = f"[open]({f['link']})" if f["uploaded"] else "NOT UPLOADED"
    fonts = f"{f['title_font']} / {f['body_font']}"
    sha = f"`{f['sha256']}`" if f["uploaded"] else "—"
    size = f["bytes"] if f["uploaded"] else "—"
    lines.append(f"| {i:02d} | {f['label']} | {f['family']} | `{f['motion_id']}` | {fonts} | {f['accent']} | {drive} | {sha} | {size} |")
(job / "UPLOAD-MANIFEST.md").write_text("\n".join(lines) + "\n")
print("Wrote", job / "UPLOAD-MANIFEST.json")
print("Uploaded", sum(1 for f in files if f["uploaded"]), "of", len(files))
PY
