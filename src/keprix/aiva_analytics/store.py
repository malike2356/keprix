"""SQLite store for Aiva analytics events + daily rollups (K04)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _data_root() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "aiva_analytics"
    except Exception:
        root = Path.home() / ".keprix" / "aiva_analytics"
    root.mkdir(parents=True, exist_ok=True)
    return root


SCHEMA = """
CREATE TABLE IF NOT EXISTS aiva_analytics_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL DEFAULT 1,
    labels TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aiva_analytics_daily (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    day TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL DEFAULT 0,
    labels TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, day, metric_name, labels)
);

CREATE INDEX IF NOT EXISTS ix_aiva_analytics_events_ws
    ON aiva_analytics_events(workspace_id, metric_name, recorded_at);
CREATE INDEX IF NOT EXISTS ix_aiva_analytics_daily_ws
    ON aiva_analytics_daily(workspace_id, day);
"""


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if data.get("labels"):
        try:
            data["labels"] = json.loads(data["labels"])
        except json.JSONDecodeError:
            data["labels"] = {}
    else:
        data["labels"] = {}
    return data


class AnalyticsStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (_data_root() / "analytics.sqlite")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record(
        self,
        *,
        workspace_id: str,
        metric_name: str,
        metric_value: float = 1.0,
        labels: dict[str, Any] | None = None,
        recorded_at: str | None = None,
    ) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        at = recorded_at or _utcnow()
        labels_json = json.dumps(labels or {}, sort_keys=True)
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO aiva_analytics_events (
                    id, workspace_id, metric_name, metric_value, labels, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, workspace_id, metric_name, float(metric_value), labels_json, at),
            )
            self._conn.commit()
        return {
            "id": event_id,
            "workspace_id": workspace_id,
            "metric_name": metric_name,
            "metric_value": float(metric_value),
            "labels": labels or {},
            "recorded_at": at,
        }

    def query_events(
        self,
        workspace_id: str,
        *,
        metric_name: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM aiva_analytics_events WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if metric_name:
            sql += " AND metric_name = ?"
            params.append(metric_name)
        if since:
            sql += " AND recorded_at >= ?"
            params.append(since)
        if until:
            sql += " AND recorded_at <= ?"
            params.append(until)
        sql += " ORDER BY recorded_at ASC LIMIT ?"
        params.append(limit)
        return [d for r in self._conn.execute(sql, tuple(params)).fetchall() if (d := _row(r))]

    def sum_metric(
        self,
        workspace_id: str,
        metric_name: str,
        *,
        since: str | None = None,
        label_key: str | None = None,
        label_value: str | None = None,
    ) -> float:
        rows = self.query_events(workspace_id, metric_name=metric_name, since=since)
        total = 0.0
        for row in rows:
            labels = row.get("labels") or {}
            if label_key is not None and str(labels.get(label_key)) != str(label_value):
                continue
            total += float(row.get("metric_value") or 0)
        return total

    def upsert_daily(
        self,
        *,
        workspace_id: str,
        day: str,
        metric_name: str,
        metric_value: float,
        labels: dict[str, Any] | None = None,
    ) -> None:
        labels_json = json.dumps(labels or {}, sort_keys=True)
        now = _utcnow()
        with self._lock:
            existing = self._conn.execute(
                """
                SELECT id, metric_value FROM aiva_analytics_daily
                WHERE workspace_id = ? AND day = ? AND metric_name = ? AND labels = ?
                """,
                (workspace_id, day, metric_name, labels_json),
            ).fetchone()
            if existing:
                self._conn.execute(
                    """
                    UPDATE aiva_analytics_daily
                    SET metric_value = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (float(metric_value), now, existing["id"]),
                )
            else:
                self._conn.execute(
                    """
                    INSERT INTO aiva_analytics_daily (
                        id, workspace_id, day, metric_name, metric_value, labels, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), workspace_id, day, metric_name, float(metric_value), labels_json, now),
                )
            self._conn.commit()

    def list_daily(
        self,
        workspace_id: str,
        *,
        since_day: str | None = None,
        metric_name: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM aiva_analytics_daily WHERE workspace_id = ?"
        params: list[Any] = [workspace_id]
        if since_day:
            sql += " AND day >= ?"
            params.append(since_day)
        if metric_name:
            sql += " AND metric_name = ?"
            params.append(metric_name)
        sql += " ORDER BY day ASC"
        return [d for r in self._conn.execute(sql, tuple(params)).fetchall() if (d := _row(r))]

    def list_workspaces_with_events(self, since: str | None = None) -> list[str]:
        if since:
            rows = self._conn.execute(
                "SELECT DISTINCT workspace_id FROM aiva_analytics_events WHERE recorded_at >= ?",
                (since,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT DISTINCT workspace_id FROM aiva_analytics_events").fetchall()
        return [str(r["workspace_id"]) for r in rows]


_store: AnalyticsStore | None = None
_lock = threading.Lock()


def get_analytics_store(path: Path | None = None) -> AnalyticsStore:
    global _store
    if path is not None:
        return AnalyticsStore(path=path)
    with _lock:
        if _store is None:
            _store = AnalyticsStore()
        return _store


def reset_analytics_store_for_tests(path: Path | None = None) -> AnalyticsStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = AnalyticsStore(path=path) if path else AnalyticsStore()
        return _store
