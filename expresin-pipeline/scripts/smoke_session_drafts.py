from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TEST_TMP = ROOT / ".deepworks" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DATA = Path(tempfile.mkdtemp(prefix="session-drafts-test-", dir=TEST_TMP))
os.environ["EXPRESIN_DATA_DIR"] = str(TEST_DATA)
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
        json={"username": username, "password": "draft-test-password"},
    )
    check(response.status_code == 201, f"register {username}: {response.text}")
    return {"Authorization": f"Bearer {response.json()['token']}"}


alice = register("alice_drafts")
bob = register("bob_drafts")

response = client.get("/portal/assistant/sessions")
check(response.status_code == 401, "draft list must require auth")

response = client.post("/portal/assistant/sessions", headers=alice, json={})
check(response.status_code == 200, f"create alice session: {response.text}")
alice_sid = response.json()["id"]
response = client.post("/portal/assistant/sessions", headers=bob, json={})
bob_sid = response.json()["id"]

class FakeChatClient:
    def chat_json(self, _messages, **kwargs):
        check(kwargs.get("timeout") == 25, "chat extraction must use a bounded timeout")
        check(kwargs.get("max_retries") == 1, "chat extraction must not retry for minutes")
        return {"fields": []}, SimpleNamespace(usage={})

class FakeChatContext:
    def __enter__(self):
        return FakeChatClient()

    def __exit__(self, *_args):
        return None

original_llm_client = backend.llm_client
backend.llm_client = FakeChatContext
try:
    response = client.post(
        f"/portal/assistant/sessions/{bob_sid}/messages",
        headers=bob,
        json={"text": "今天天气怎么样"},
    )
finally:
    backend.llm_client = original_llm_client
check(response.status_code == 200, f"irrelevant message should still reply: {response.text}")
check("没有从这段话里识别出明确的实验字段" in response.json()["reply"], "empty extraction reply missing")

class UnexpectedLLMContext:
    def __enter__(self):
        raise AssertionError("common conversation must not call the LLM")

backend.llm_client = UnexpectedLLMContext
try:
    for message, expected in (
        ("你好", "你好，我是 Jarvis"),
        ("你能做什么", "三件事"),
        ("我需要做什么", "当前还缺少"),
        ("接下来要填什么", "当前还缺少"),
        ("你是谁", "实验记录助手"),
        ("谢谢", "不客气"),
    ):
        response = client.post(
            f"/portal/assistant/sessions/{bob_sid}/messages",
            headers=bob,
            json={"text": message},
        )
        check(
            response.status_code == 200 and expected in response.json().get("reply", ""),
            f"conversation reply mismatch for {message}: {response.text}",
        )
finally:
    backend.llm_client = original_llm_client

fields = [
    {"field_path": "01_Metadata.title", "value": "A600 动态吸附草稿", "status": "pending"},
    {"field_path": "01_Metadata.experiment_type", "value": "column", "status": "pending"},
    {"field_path": "01_Metadata.date_start", "value": "2026-11-03", "status": "pending"},
]
# 连接改为每线程独立后，主线程上的 trace_callback 看不到 TestClient 工作线程；
# 这里改为确认端点只调用一次批量保存，事务原子性由 smoke_store_concurrency 的
# 触发器回滚测试覆盖。
calls = []
original_upsert_drafts = backend.store.upsert_drafts


def counting_upsert_drafts(*args, **kwargs):
    calls.append(1)
    return original_upsert_drafts(*args, **kwargs)


backend.store.upsert_drafts = counting_upsert_drafts
try:
    response = client.patch(
        f"/portal/assistant/sessions/{alice_sid}/drafts",
        headers=alice,
        json={"fields": fields},
    )
finally:
    backend.store.upsert_drafts = original_upsert_drafts
check(response.status_code == 200, f"bulk draft save: {response.text}")
check(response.json()["updated"] == 3, "bulk save count mismatch")
check(len(calls) == 1, "bulk save must use one batch operation")

response = client.get(f"/portal/assistant/sessions/{alice_sid}/form-state", headers=alice)
values = {item["field_path"]: item["value"] for item in response.json()["fields"]}
check(values["01_Metadata.title"] == "A600 动态吸附草稿", "saved title missing")
check(values["01_Metadata.experiment_type"] == "column", "saved type missing")

response = client.get("/portal/assistant/sessions?limit=6", headers=alice)
check(response.status_code == 200, f"alice draft list: {response.text}")
alice_list = response.json()["sessions"]
check(len(alice_list) == 1 and alice_list[0]["id"] == alice_sid, "alice draft list mismatch")
check(alice_list[0]["title"] == "A600 动态吸附草稿", "draft title summary missing")
check(alice_list[0]["experiment_type"] == "column", "draft type summary missing")
check(alice_list[0]["field_count"] == 3, "draft field count mismatch")

response = client.get("/portal/assistant/sessions", headers=bob)
bob_list = response.json()["sessions"]
check(len(bob_list) == 1 and bob_list[0]["id"] == bob_sid, "bob draft list mismatch")
check(all(item["id"] != alice_sid for item in bob_list), "cross-user draft leaked")

response = client.patch(
    f"/portal/assistant/sessions/{alice_sid}/drafts",
    headers=bob,
    json={"fields": fields},
)
check(response.status_code == 404, "cross-user draft write must be hidden")

response = client.patch(
    f"/portal/assistant/sessions/{alice_sid}/drafts",
    headers=alice,
    json={"fields": [{"field_path": "not.in.schema", "value": "ignored"}]},
)
check(response.status_code == 200 and response.json()["updated"] == 0, "unknown field must be ignored")

backend.store.set_session_experiment(alice_sid, "RES-DRAFT-TEST-001")
response = client.get("/portal/assistant/sessions", headers=alice)
check(response.json()["sessions"] == [], "confirmed session must leave draft list")
response = client.patch(
    f"/portal/assistant/sessions/{alice_sid}/drafts",
    headers=alice,
    json={"fields": fields},
)
check(response.status_code == 409, "confirmed session must reject draft writes")

index_names = {
    row[1] for row in backend.store._conn.execute("PRAGMA index_list(sessions)").fetchall()
}
check("idx_sessions_user_status_updated" in index_names, "session list index missing")

legacy_path = TEST_DATA / "legacy-without-owner.db"
legacy_conn = sqlite3.connect(legacy_path)
legacy_conn.execute("CREATE TABLE experiments (id TEXT PRIMARY KEY, created_at TEXT)")
legacy_conn.close()
legacy_store = backend.Store(legacy_path)
legacy_columns = {
    row[1] for row in legacy_store._conn.execute("PRAGMA table_info(experiments)").fetchall()
}
legacy_indexes = {
    row[1] for row in legacy_store._conn.execute("PRAGMA index_list(experiments)").fetchall()
}
check("owner_user_id" in legacy_columns, "legacy owner migration missing")
check("idx_experiments_owner_created" in legacy_indexes, "post-migration experiment index missing")
legacy_store._conn.close()

print(f"session draft smoke checks passed: {checks}")
