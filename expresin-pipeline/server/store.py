"""PortalJarvis 数据存储层（SQLite）。

对应 PRD 第 11 章数据模型中的：
AssistantSession、FormDraft、FieldProvenance、MissingField、ConfirmationLog、Experiment。

设计要点：
- Raw 层只读：原始文件一旦写入 session_assets，不接受覆盖，仅追加新版本。
- Processed 可追溯：Experiment.processed_json 中每个值都携带 source_type / source_ref。
- 确认才入库：只有经过 /confirm 的字段才写入 experiments 表（PRD FR-20）。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL DEFAULT 'lab_default',
    user_id       TEXT NOT NULL DEFAULT 'default_user',
    project_id    TEXT NOT NULL DEFAULT 'DHT',
    template_id   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft',   -- draft | confirmed
    experiment_id TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS form_drafts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    field_path   TEXT NOT NULL,
    value        TEXT,
    unit         TEXT,
    confidence   REAL,
    status       TEXT NOT NULL DEFAULT 'pending',  -- pending | confirmed | low_confidence | unit_error | deferred
    source_type  TEXT,                             -- conversation | upload | template_default | manual
    source_ref   TEXT,
    raw_text     TEXT,
    model_version TEXT,
    updated_at   TEXT NOT NULL,
    UNIQUE (session_id, field_path)
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,                      -- user | assistant
    content    TEXT NOT NULL,
    meta_json  TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_assets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    kind         TEXT NOT NULL,                    -- raw_file | recognized_blocks
    name         TEXT,
    sha256       TEXT,
    payload_json TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id             TEXT PRIMARY KEY,
    session_id     TEXT,
    tenant_id      TEXT NOT NULL DEFAULT 'lab_default',
    project_id     TEXT NOT NULL DEFAULT 'DHT',
    title          TEXT,
    experiment_type TEXT,
    operator       TEXT,
    date_start     TEXT,
    status         TEXT NOT NULL DEFAULT 'archived',
    meta_json      TEXT,
    processed_json TEXT,
    raw_file       TEXT,
    raw_sha256     TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS confirmation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    field_path TEXT NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    confirmed_by TEXT,
    timestamp  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_drafts_session ON form_drafts (session_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id);
CREATE INDEX IF NOT EXISTS idx_assets_session ON session_assets (session_id);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------ 会话
    def create_session(
        self,
        template_id: str,
        project_id: str = "DHT",
        user_id: str = "default_user",
        tenant_id: str = "lab_default",
    ) -> dict[str, Any]:
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        now = _now()
        self._conn.execute(
            "INSERT INTO sessions (id, tenant_id, user_id, project_id, template_id, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (session_id, tenant_id, user_id, project_id, template_id, "draft", now, now),
        )
        self._conn.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None

    def touch_session(self, session_id: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE id=?", (_now(), session_id)
        )
        self._conn.commit()

    def set_session_experiment(self, session_id: str, experiment_id: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET experiment_id=?, status='confirmed', updated_at=? WHERE id=?",
            (experiment_id, _now(), session_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ 草稿
    def upsert_draft(
        self,
        session_id: str,
        field_path: str,
        value: Any,
        unit: str | None = None,
        confidence: float | None = None,
        status: str = "pending",
        source_type: str | None = None,
        source_ref: str | None = None,
        raw_text: str | None = None,
        model_version: str | None = None,
    ) -> None:
        now = _now()
        text = "" if value is None else str(value)
        self._conn.execute(
            """
            INSERT INTO form_drafts
                (session_id, field_path, value, unit, confidence, status,
                 source_type, source_ref, raw_text, model_version, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (session_id, field_path) DO UPDATE SET
                value=excluded.value,
                unit=COALESCE(excluded.unit, form_drafts.unit),
                confidence=COALESCE(excluded.confidence, form_drafts.confidence),
                status=excluded.status,
                source_type=COALESCE(excluded.source_type, form_drafts.source_type),
                source_ref=COALESCE(excluded.source_ref, form_drafts.source_ref),
                raw_text=COALESCE(excluded.raw_text, form_drafts.raw_text),
                model_version=COALESCE(excluded.model_version, form_drafts.model_version),
                updated_at=excluded.updated_at
            """,
            (
                session_id, field_path, text, unit, confidence, status,
                source_type, source_ref, raw_text, model_version, now,
            ),
        )
        self._conn.commit()

    def get_drafts(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM form_drafts WHERE session_id=? ORDER BY field_path", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_draft_map(self, session_id: str) -> dict[str, dict[str, Any]]:
        return {d["field_path"]: d for d in self.get_drafts(session_id)}

    def draft_value(self, session_id: str, field_path: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM form_drafts WHERE session_id=? AND field_path=?",
            (session_id, field_path),
        ).fetchone()
        return row["value"] if row else None

    # ------------------------------------------------------------------ 消息
    def add_message(
        self, session_id: str, role: str, content: str, meta: dict | None = None
    ) -> dict[str, Any]:
        cur = self._conn.execute(
            "INSERT INTO messages (session_id, role, content, meta_json, created_at) VALUES (?,?,?,?,?)",
            (session_id, role, content, json.dumps(meta or {}, ensure_ascii=False), _now()),
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "role": role, "content": content, "meta": meta or {}}

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id", (session_id,)
        ).fetchall()
        out = []
        for r in rows:
            item = dict(r)
            item["meta"] = json.loads(item.pop("meta_json") or "{}")
            out.append(item)
        return out

    # ------------------------------------------------------------------ 资产
    def add_asset(
        self,
        session_id: str,
        kind: str,
        name: str | None = None,
        sha256: str | None = None,
        payload: dict | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO session_assets (session_id, kind, name, sha256, payload_json, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (session_id, kind, name, sha256, json.dumps(payload or {}, ensure_ascii=False), _now()),
        )
        self._conn.commit()

    def latest_asset(self, session_id: str, kind: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM session_assets WHERE session_id=? AND kind=? ORDER BY id DESC LIMIT 1",
            (session_id, kind),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        return item

    # ------------------------------------------------------------------ 确认
    def log_confirmation(
        self, session_id: str, field_path: str, old_value: Any, new_value: Any, by: str = "user"
    ) -> None:
        self._conn.execute(
            "INSERT INTO confirmation_log (session_id, field_path, old_value, new_value, confirmed_by, timestamp)"
            " VALUES (?,?,?,?,?,?)",
            (session_id, field_path, "" if old_value is None else str(old_value),
             "" if new_value is None else str(new_value), by, _now()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ 实验编号
    def next_experiment_id(self, date: datetime | None = None) -> str:
        """按当天已有编号的最大序号 +1 生成。

        原先用 COUNT(*) 计数，一旦历史记录有空洞（删除或跳号）就会重号；
        改用最大序号可以避免这类碰撞。
        """
        day = (date or datetime.now()).strftime("%Y%m%d")
        prefix = f"RES-{day}-"
        row = self._conn.execute(
            "SELECT MAX(id) AS m FROM experiments WHERE id LIKE ?", (prefix + "%",)
        ).fetchone()
        last = (row["m"] if row and row["m"] else "") or ""
        tail = last[len(prefix):]
        n = int(tail) + 1 if tail.isdigit() else 1
        return f"{prefix}{n:03d}"

    # ------------------------------------------------------------------ 实验
    def create_experiment(
        self,
        experiment_id: str,
        session_id: str,
        project_id: str,
        title: str,
        experiment_type: str,
        operator: str,
        date_start: str,
        meta: dict,
        processed: dict,
        raw_file: str | None,
        raw_sha256: str | None,
        tenant_id: str = "lab_default",
    ) -> dict[str, Any]:
        now = _now()
        # 幂等归档：同一编号重复归档时更新既有记录，而不是抛主键冲突。
        # created_at 保持不变，只刷新 updated_at，保证创建时间可追溯。
        self._conn.execute(
            """
            INSERT INTO experiments
                (id, session_id, tenant_id, project_id, title, experiment_type, operator,
                 date_start, status, meta_json, processed_json, raw_file, raw_sha256,
                 created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                session_id=excluded.session_id,
                project_id=excluded.project_id,
                title=excluded.title,
                experiment_type=excluded.experiment_type,
                operator=excluded.operator,
                date_start=excluded.date_start,
                status=excluded.status,
                meta_json=excluded.meta_json,
                processed_json=excluded.processed_json,
                raw_file=excluded.raw_file,
                raw_sha256=excluded.raw_sha256,
                updated_at=excluded.updated_at
            """,
            (
                experiment_id, session_id, tenant_id, project_id, title, experiment_type,
                operator, date_start, "archived",
                json.dumps(meta, ensure_ascii=False),
                json.dumps(processed, ensure_ascii=False),
                raw_file, raw_sha256, now, now,
            ),
        )
        self._conn.commit()
        return self.get_experiment(experiment_id)

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM experiments WHERE id=?", (experiment_id,)
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["meta"] = json.loads(item.pop("meta_json") or "{}")
        item["processed"] = json.loads(item.pop("processed_json") or "{}")
        return item

    def list_experiments(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, project_id, title, experiment_type, operator, date_start, status,"
            " raw_file, session_id, created_at FROM experiments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]