import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

creds_file = os.path.expanduser("~/.config/velox/credentials.json")
tok_file = os.path.expanduser("~/.config/velox/token.json")

with open(creds_file) as f:
    creds = json.load(f)
with open(tok_file) as f:
    tok = json.load(f)

c_info = creds.get("installed") or creds.get("web")
params = {
    "client_id": c_info["client_id"],
    "client_secret": c_info["client_secret"],
    "refresh_token": tok.get("refresh_token"),
    "grant_type": "refresh_token"
}
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=urllib.parse.urlencode(params).encode())
with urllib.request.urlopen(req) as resp:
    new_tok = json.load(resp)["access_token"]

out_dir = Path("/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/out/modern_entities_ref")
out_dir.mkdir(parents=True, exist_ok=True)

files = [
    ("1XbW2CewH20NgTrDWtcdcavROd6MjXDbT", "ref_entity_01"),
    ("1JOquPOeHdSfLcBNPqEXCWPY2cbkETfSX", "ref_entity_02")
]

for fid, prefix in files:
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{fid}?fields=id,name,size,mimeType", headers={"Authorization": f"Bearer {new_tok}"})
    with urllib.request.urlopen(req) as resp:
        meta = json.load(resp)
        fname = meta.get("name", "file.mp4")
        mime = meta.get("mimeType", "")
        print(f"Meta: {fid} -> {fname} ({mime}, {meta.get('size')} bytes)")
    
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media", headers={"Authorization": f"Bearer {new_tok}"})
    target = out_dir / f"{prefix}_{fname}"
    with urllib.request.urlopen(req) as resp, open(target, "wb") as out_f:
        out_f.write(resp.read())
    print(f"Downloaded -> {target} ({target.stat().st_size} bytes)")
