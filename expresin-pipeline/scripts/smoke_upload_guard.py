"""Upload guard regression: path traversal, size limit, empty file, no overwrite."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_TMP = ROOT / ".deepworks" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DATA = Path(tempfile.mkdtemp(prefix="upload-guard-test-", dir=TEST_TMP))
os.environ["EXPRESIN_DATA_DIR"] = str(TEST_DATA)
os.environ["EXPRESIN_MAX_UPLOAD_MB"] = "1"
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "server"))

import app as backend  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(backend.app)
checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def register(username):
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "upload-guard-password"},
    )
    check(response.status_code == 201, f"register {username}: {response.text}")
    return {"Authorization": f"Bearer {response.json()['token']}"}


headers = register("upload_guard_user")
response = client.post("/portal/assistant/sessions", headers=headers, json={})
check(response.status_code == 200, f"create session: {response.text}")
sid = response.json()["id"]


def upload(filename, content, analyze=False):
    return client.post(
        f"/portal/assistant/sessions/{sid}/upload",
        headers=headers,
        files={"file": (filename, content, "application/octet-stream")},
        data={"analyze": str(analyze).lower()},
    )


# 1) Directory components must never escape RAW_DIR.
response = upload(r"..\..\escape.xlsx", b"not-an-excel-file")
check(response.status_code == 200, f"traversal upload should be stored safely: {response.text}")
raw_uri = Path(response.json()["raw"]["uri"]).resolve()
check(raw_uri.parent == backend.RAW_DIR.resolve(), f"raw file escaped RAW_DIR: {raw_uri}")
check(raw_uri.name.endswith("escape.xlsx"), f"display suffix lost: {raw_uri.name}")
check(".." not in raw_uri.name, f"path segment leaked into stored name: {raw_uri.name}")

# 2) Same original name with different bytes must keep two raw versions.
latest_paths = []
for content in (b"version-one", b"version-two"):
    response = upload("same-name.xlsx", content)
    check(response.status_code == 200, f"same-name upload failed: {response.text}")
    latest_paths.append(Path(response.json()["raw"]["uri"]).resolve())
check(latest_paths[0] != latest_paths[1], "same-name upload overwrote the previous raw file")
check(all(path.is_file() for path in latest_paths), "raw versions were not persisted")
check(backend._raw_file_path(sid, "same-name.xlsx") == latest_paths[1], "latest raw lookup mismatch")

# 3) Empty files and oversize files are rejected before analysis.
response = upload("empty.xlsx", b"")
check(response.status_code == 400, f"empty upload should be 400: {response.text}")

response = upload("too-large.xlsx", b"x" * (backend.MAX_UPLOAD_BYTES + 1))
check(response.status_code == 413, f"oversize upload should be 413: {response.text}")
detail = response.json().get("detail") or {}
check(detail.get("retryable") is False, "oversize rejection must not be marked retryable")

print(f"UPLOAD_GUARD_OK checks={checks}")
print(f"TEST_DATA={TEST_DATA}")
