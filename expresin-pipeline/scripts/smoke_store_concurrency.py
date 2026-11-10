"""Concurrent SQLite access regression for the shared Store instance."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_TMP = ROOT / ".deepworks" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DATA = Path(tempfile.mkdtemp(prefix="store-concurrency-", dir=TEST_TMP))
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "server"))

from store import Store  # noqa: E402

store = Store(TEST_DATA / "concurrency.db")
user = store.create_user("usr_concurrency", "concurrency_user", "hash")
session = store.create_session("batch", user_id=user["id"])
token = "concurrency-token"
store.create_token(token, user["id"], "2999-01-01T00:00:00")
WORKERS = 8
ROUNDS = 40

assert store.get_token_user(token)["id"] == user["id"]


def worker(index: int) -> int:
    for round_no in range(ROUNDS):
        current = store.get_token_user(token)
        assert current and current["id"] == user["id"]
        assert store.list_sessions(user["id"], limit=6)
        assert store.get_drafts(session["id"]) is not None
        if round_no % 5 == 0:
            store.add_message(session["id"], "user", f"worker={index} round={round_no}")
        messages = store.get_messages(session["id"])
        assert isinstance(messages, list)
    return index


with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    results = list(pool.map(worker, range(WORKERS)))

message_count = len(store.get_messages(session["id"]))
expected = WORKERS * (ROUNDS // 5)
assert results == list(range(WORKERS))
assert message_count == expected, f"expected {expected} messages, got {message_count}"

# Bulk upsert atomicity: a failure in the second row must roll back the first row.
conn = store._conn
conn.execute(
    "CREATE TRIGGER force_bulk_failure BEFORE INSERT ON form_drafts"
    " WHEN NEW.field_path='force_fail'"
    " BEGIN SELECT RAISE(ABORT, 'forced failure'); END"
)
conn.commit()
try:
    try:
        store.upsert_drafts(
            session["id"],
            [
                {"field_path": "atomic.keep", "value": "must-roll-back", "status": "pending"},
                {"field_path": "force_fail", "value": "boom", "status": "pending"},
            ],
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("forced bulk failure did not raise")
    assert store.draft_value(session["id"], "atomic.keep") is None, "bulk upsert did not roll back"
finally:
    conn.execute("DROP TRIGGER force_bulk_failure")
    conn.commit()

print(
    f"STORE_CONCURRENCY_OK workers={WORKERS} rounds={ROUNDS} messages={message_count} rollback=ok"
)
print(f"TEST_DATA={TEST_DATA}")
