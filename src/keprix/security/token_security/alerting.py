"""Alert helpers with suppression windows (no raw sensitive payloads)."""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir

logger = logging.getLogger(__name__)

DEFAULT_SUPPRESSION_SECONDS = 15 * 60

_SCHEMA = """
CREATE TABLE IF NOT EXISTS security_alert_suppressions (
    alert_key TEXT PRIMARY KEY,
    last_sent_at REAL NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS security_alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    alert_key TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
"""


class AlertManager:
    def __init__(self, sqlite_path: Path | None = None, suppression_seconds: int = DEFAULT_SUPPRESSION_SECONDS) -> None:
        self._path = sqlite_path or Path(data_dir()) / "token_security_alerts.db"
        self._suppression = max(60, int(suppression_seconds))
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def should_emit(self, alert_key: str) -> bool:
        now = time.time()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT last_sent_at, count FROM security_alert_suppressions WHERE alert_key = ?",
                (alert_key,),
            ).fetchone()
            if row and (now - float(row[0])) < self._suppression:
                conn.execute(
                    "UPDATE security_alert_suppressions SET count = count + 1 WHERE alert_key = ?",
                    (alert_key,),
                )
                conn.commit()
                return False
            conn.execute(
                """
                INSERT INTO security_alert_suppressions (alert_key, last_sent_at, count)
                VALUES (?, ?, 1)
                ON CONFLICT(alert_key) DO UPDATE SET last_sent_at = excluded.last_sent_at, count = 1
                """,
                (alert_key, now),
            )
            conn.commit()
            return True

    def emit(
        self,
        alert_key: str,
        *,
        title: str,
        severity: str = "warning",
        detail: dict[str, Any] | None = None,
        force: bool = False,
    ) -> bool:
        if not force and not self.should_emit(alert_key):
            logger.debug("alert suppressed: %s", alert_key)
            return False
        import json

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO security_alert_log (created_at, alert_key, severity, title, detail_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (time.time(), alert_key, severity, title, json.dumps(detail or {})),
            )
            conn.commit()
        logger.warning("security alert [%s] %s: %s", severity, alert_key, title)
        return True

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        import json

        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT created_at, alert_key, severity, title, detail_json
                FROM security_alert_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, min(int(limit), 200)),),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                detail = json.loads(row[4] or "{}")
            except Exception:
                detail = {}
            out.append(
                {
                    "created_at": row[0],
                    "alert_key": row[1],
                    "severity": row[2],
                    "title": row[3],
                    "detail": detail,
                }
            )
        return out


_alerts: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    global _alerts
    if _alerts is None:
        _alerts = AlertManager()
    return _alerts


def reset_alert_manager_for_tests(manager: AlertManager | None = None) -> AlertManager:
    global _alerts
    _alerts = manager if manager is not None else AlertManager()
    return _alerts
