import os
import json
import io
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

CREDS_PATH = os.path.expanduser("~/.config/velox/credentials.json")
TOKEN_PATH = os.path.expanduser("~/.config/velox/token.json")

with open(CREDS_PATH) as f:
    c_data = json.load(f)["installed"]
with open(TOKEN_PATH) as f:
    t_data = json.load(f)

t_data["client_id"] = c_data["client_id"]
t_data["client_secret"] = c_data["client_secret"]

creds = Credentials.from_authorized_user_info(t_data)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build("drive", "v3", credentials=creds)

folder_id = "1m0yo6FsidSzI7QIuNVxWIEz8ZEAO6QfR"
query = f"'{folder_id}' in parents and trashed = false"

results = service.files().list(q=query, fields="files(id, name, mimeType, size)").execute()
files = results.get("files", [])
print(f"Found {len(files)} files in Drive folder:")

OUT_DIR = "/home/pierone/src/go-master/projects/Pyt/VeloxEditing/ChrononTemplate/out/web_preset_pack/downloaded"
os.makedirs(OUT_DIR, exist_ok=True)

for f in files:
    name = f.get("name")
    fid = f.get("id")
    size = f.get("size", "?")
    print(f" - {name} (id: {fid}, size: {size} bytes)")
    
    # Download file
    dest_path = os.path.join(OUT_DIR, name)
    req = service.files().get_media(fileId=fid)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"   Downloading {int(status.progress() * 100)}%...")
    print(f"   Saved to {dest_path}")

print("\nDone downloading all files!")
