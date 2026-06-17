"""SQLite-backed task store (stdlib sqlite3, single file).

`tags` and `run` are stored as JSON text. A `meta` row holds the schema version;
the store refuses to open a database written by a newer schema (no silent
downgrade). Upgrades, when SCHEMA_VERSION grows, are additive-only.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from ..models import SCHEMA_VERSION
from .base import Store

_COLUMNS = (
    "id", "title", "body", "status", "project", "due_date",
    "tags", "run_status", "run", "created_at", "updated_at", "schema_version",
)


def _row_to_task(row: sqlite3.Row) -> Dict[str, Any]:
    task = {key: row[key] for key in _COLUMNS}
    task["tags"] = json.loads(row["tags"] or "[]")
    task["run"] = json.loads(row["run"]) if row["run"] else None
    return task


def _encode(task: Dict[str, Any]) -> List[Any]:
    """Flatten a task dict into a row tuple aligned with _COLUMNS."""
    return [
        task["id"], task["title"], task.get("body", ""), task["status"],
        task.get("project"), task.get("due_date"),
        json.dumps(task.get("tags") or []),
        task.get("run_status", "none"),
        json.dumps(task["run"]) if task.get("run") else None,
        task.get("created_at"), task.get("updated_at"),
        task.get("schema_version", SCHEMA_VERSION),
    ]


class SqliteStore(Store):
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS meta "
                "(key TEXT PRIMARY KEY, value TEXT)"
            )
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS tasks ("
                "id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT, "
                "status TEXT NOT NULL, project TEXT, due_date TEXT, "
                "tags TEXT, run_status TEXT, run TEXT, "
                "created_at TEXT, updated_at TEXT, schema_version INTEGER)"
            )
            self._guard_version()

    def _guard_version(self) -> None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            return
        existing = int(row["value"])
        if existing > SCHEMA_VERSION:
            raise RuntimeError(
                "database schema_version %d is newer than supported %d; "
                "refusing to downgrade" % (existing, SCHEMA_VERSION)
            )

    def list_tasks(self, *, date=None, project=None, status=None):
        sql = "SELECT * FROM tasks"
        clauses, params = [], []
        if date:
            clauses.append("due_date = ?")
            params.append(date)
        if project:
            clauses.append("project = ?")
            params.append(project)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC"
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_task(r) for r in rows]

    def get_task(self, task_id):
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return _row_to_task(row) if row else None

    def create_task(self, task):
        placeholders = ", ".join("?" * len(_COLUMNS))
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO tasks (%s) VALUES (%s)"
                % (", ".join(_COLUMNS), placeholders),
                _encode(task),
            )
        return task

    def update_task(self, task):
        cols = [c for c in _COLUMNS if c != "id"]
        assignments = ", ".join("%s = ?" % c for c in cols)
        params = _encode(task)[1:] + [task["id"]]
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE tasks SET %s WHERE id = ?" % assignments, params
            )
        return task

    def delete_task(self, task_id):
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM tasks WHERE id = ?", (task_id,)
            )
        return cur.rowcount > 0

    def close(self):
        self._conn.close()
