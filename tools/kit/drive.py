"""Google Drive upload: one implementation instead of fifteen copies.

The multipart upload, the refresh-token dance and the anyone-reader permission
grant previously lived (slightly different every time) inside each suite
script. Here they exist once; `upload_many` parallelises the small uploads.
"""

from __future__ import annotations

import concurrent.futures
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_UPLOAD_URL = (
    "https://www.googleapis.com/upload/drive/v3/files"
    "?uploadType=multipart&fields=id,name,webViewLink"
)


def refresh_token(token_path: Path, creds_path: Path) -> str:
    """Exchange the stored refresh token for a fresh access token (persisted)."""
    tok_data = json.loads(Path(token_path).read_text())
    creds = json.loads(Path(creds_path).read_text())
    client_info = creds.get("installed") or creds.get("web")

    params = {
        "client_id": client_info["client_id"],
        "client_secret": client_info["client_secret"],
        "refresh_token": tok_data.get("refresh_token"),
        "grant_type": "refresh_token",
    }
    req = urllib.request.Request(
        _TOKEN_URL, data=urllib.parse.urlencode(params).encode()
    )
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)
    tok_data["access_token"] = res["access_token"]
    Path(token_path).write_text(json.dumps(tok_data, indent=2))
    return res["access_token"]


def link_for(result: dict) -> str:
    return result.get("webViewLink") or (
        f"https://drive.google.com/file/d/{result.get('id')}/view"
    )


def upload_file(
    token: str, file_path: Path, folder_id: str, make_public: bool = True
) -> dict:
    """Multipart upload of one file into `folder_id`, optionally made readable."""
    file_path = Path(file_path)
    mime_type = "video/mp4" if file_path.suffix == ".mp4" else "image/png"
    boundary = "-------ChrononKitUpload"
    metadata = json.dumps({"name": file_path.name, "parents": [folder_id]})

    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode(
        "utf-8"
    )

    req = urllib.request.Request(
        _UPLOAD_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    with urllib.request.urlopen(req) as resp:
        res = json.load(resp)

    if make_public and res.get("id"):
        try:
            perm_req = urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files/{res['id']}/permissions",
                data=json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(perm_req):
                pass
        except Exception:
            pass  # the file is uploaded; a failed permission grant is not fatal
    return res


def upload_many(
    token: str,
    files: list[Path],
    folder_id: str,
    workers: int = 2,
) -> dict[Path, dict]:
    """Upload several files concurrently; returns {path: drive result}.

    Raises on the first failure after all futures settle, so one bad file does
    not silently drop the rest of the batch.
    """
    results: dict[Path, dict] = {}
    errors: list[tuple[Path, Exception]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(upload_file, token, path, folder_id): path for path in files
        }
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                results[path] = future.result()
            except Exception as exc:  # noqa: BLE001 - collected and re-raised
                errors.append((path, exc))
    if errors:
        path, exc = errors[0]
        raise RuntimeError(f"upload fallito per {path.name}: {exc}") from exc
    return results
