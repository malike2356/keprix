"""Token security monitor: velocity, auth failures, UA/network shifts, scope violations."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.security.client_approval.fingerprint import token_security_enabled
from keprix.security.token_security.alerting import get_alert_manager

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS token_security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    token_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    fingerprint TEXT,
    ip_hash TEXT,
    ua_summary TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_token_sec_token_created
    ON token_security_events(token_id, created_at);
CREATE TABLE IF NOT EXISTS token_suspensions (
    token_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    created_at REAL NOT NULL,
    created_by TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS token_baselines (
    token_id TEXT PRIMARY KEY,
    last_ip_hash TEXT,
    last_ua_summary TEXT,
    updated_at REAL NOT NULL
);
"""


def _velocity_limit() -> int:
    try:
        return max(1, int(os.environ.get("KEPRIX_TOKEN_VELOCITY_LIMIT") or "120"))
    except ValueError:
        return 120


def _velocity_window() -> int:
    try:
        return max(5, int(os.environ.get("KEPRIX_TOKEN_VELOCITY_WINDOW_SEC") or "60"))
    except ValueError:
        return 60


def _failed_auth_limit() -> int:
    try:
        return max(1, int(os.environ.get("KEPRIX_TOKEN_FAILED_AUTH_LIMIT") or "10"))
    except ValueError:
        return 10


@dataclass
class MonitorResult:
    allowed: bool
    suspended: bool = False
    reason: str | None = None
    alerts: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "suspended": self.suspended,
            "reason": self.reason,
            "alerts": list(self.alerts or []),
        }


class TokenSecurityMonitor:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._path = sqlite_path or Path(data_dir()) / "token_security.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        if not self._ready:
            conn.executescript(_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def is_suspended(self, token_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT active FROM token_suspensions WHERE token_id = ? AND active = 1",
                (token_id,),
            ).fetchone()
        return bool(row)

    def suspend(self, token_id: str, *, reason: str, created_by: str | None = "monitor") -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO token_suspensions (token_id, reason, created_at, created_by, active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(token_id) DO UPDATE SET
                    reason = excluded.reason,
                    created_at = excluded.created_at,
                    created_by = excluded.created_by,
                    active = 1
                """,
                (token_id, reason, time.time(), created_by),
            )
            conn.commit()
        get_alert_manager().emit(
            f"token_suspended:{token_id}",
            title=f"API token suspended: {reason}",
            severity="critical",
            detail={"token_id": token_id, "reason": reason},
        )

    def unsuspend(self, token_id: str, *, created_by: str | None = "owner") -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE token_suspensions SET active = 0 WHERE token_id = ? AND active = 1",
                (token_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_suspensions(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT token_id, reason, created_at, created_by, active FROM token_suspensions ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "token_id": row[0],
                "reason": row[1],
                "created_at": row[2],
                "created_by": row[3],
                "active": bool(row[4]),
            }
            for row in rows
        ]

    def _record_event(
        self,
        token_id: str,
        event_type: str,
        *,
        fingerprint: str | None = None,
        ip_hash: str | None = None,
        ua_summary: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO token_security_events (
                    created_at, token_id, event_type, fingerprint, ip_hash, ua_summary, detail_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    token_id,
                    event_type,
                    fingerprint,
                    ip_hash,
                    ua_summary,
                    json.dumps(detail or {}),
                ),
            )
            conn.commit()

    def _count_events(self, token_id: str, event_type: str, window_sec: int) -> int:
        cutoff = time.time() - window_sec
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM token_security_events
                WHERE token_id = ? AND event_type = ? AND created_at >= ?
                """,
                (token_id, event_type, cutoff),
            ).fetchone()
        return int(row[0] if row else 0)

    def record_failed_auth(self, token_prefix_or_id: str, *, ip_hash: str | None = None) -> MonitorResult:
        if not token_security_enabled():
            return MonitorResult(allowed=True)
        key = token_prefix_or_id or "unknown"
        self._record_event(key, "failed_auth", ip_hash=ip_hash)
        count = self._count_events(key, "failed_auth", 900)
        alerts: list[str] = []
        if count >= _failed_auth_limit():
            alert_key = f"failed_auth_spike:{key}"
            if get_alert_manager().emit(
                alert_key,
                title="Failed API auth spike",
                detail={"token_id": key, "count": count, "window_sec": 900},
            ):
                alerts.append(alert_key)
            # Only suspend real token ids (not unknown prefixes) when configured.
            if os.environ.get("KEPRIX_TOKEN_SUSPEND_ON_FAILED_AUTH", "").lower() in {"1", "true", "yes"}:
                if key not in {"unknown", "invalid"}:
                    self.suspend(key, reason="failed_auth_spike")
                    return MonitorResult(allowed=False, suspended=True, reason="failed_auth_spike", alerts=alerts)
        return MonitorResult(allowed=True, alerts=alerts)

    def observe_request(
        self,
        token_id: str,
        *,
        fingerprint: str | None = None,
        ip_hash: str | None = None,
        ua_summary: str | None = None,
        auto_suspend_velocity: bool | None = None,
    ) -> MonitorResult:
        if not token_security_enabled():
            return MonitorResult(allowed=True)
        if self.is_suspended(token_id):
            return MonitorResult(allowed=False, suspended=True, reason="token_suspended")

        self._record_event(
            token_id,
            "request",
            fingerprint=fingerprint,
            ip_hash=ip_hash,
            ua_summary=ua_summary,
        )
        alerts: list[str] = []

        # Velocity
        window = _velocity_window()
        count = self._count_events(token_id, "request", window)
        if count > _velocity_limit():
            alert_key = f"velocity:{token_id}"
            if get_alert_manager().emit(
                alert_key,
                title="API token velocity anomaly",
                severity="critical",
                detail={"token_id": token_id, "count": count, "window_sec": window},
            ):
                alerts.append(alert_key)
            suspend = (
                auto_suspend_velocity
                if auto_suspend_velocity is not None
                else (os.environ.get("KEPRIX_TOKEN_SUSPEND_ON_VELOCITY", "true").lower() in {"1", "true", "yes"})
            )
            if suspend:
                self.suspend(token_id, reason="velocity_anomaly")
                return MonitorResult(allowed=False, suspended=True, reason="velocity_anomaly", alerts=alerts)

        # UA / network pattern change
        with self._conn() as conn:
            baseline = conn.execute(
                "SELECT last_ip_hash, last_ua_summary FROM token_baselines WHERE token_id = ?",
                (token_id,),
            ).fetchone()
            if baseline:
                last_ip, last_ua = baseline[0], baseline[1]
                if ip_hash and last_ip and ip_hash != last_ip:
                    alert_key = f"network_shift:{token_id}"
                    if get_alert_manager().emit(
                        alert_key,
                        title="API token network pattern change",
                        detail={"token_id": token_id, "ip_hash": ip_hash},
                    ):
                        alerts.append(alert_key)
                if ua_summary and last_ua and ua_summary != last_ua:
                    alert_key = f"ua_change:{token_id}"
                    if get_alert_manager().emit(
                        alert_key,
                        title="API token user-agent change",
                        detail={"token_id": token_id, "ua_summary": ua_summary},
                    ):
                        alerts.append(alert_key)
            conn.execute(
                """
                INSERT INTO token_baselines (token_id, last_ip_hash, last_ua_summary, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(token_id) DO UPDATE SET
                    last_ip_hash = COALESCE(excluded.last_ip_hash, token_baselines.last_ip_hash),
                    last_ua_summary = COALESCE(excluded.last_ua_summary, token_baselines.last_ua_summary),
                    updated_at = excluded.updated_at
                """,
                (token_id, ip_hash, ua_summary, time.time()),
            )
            conn.commit()

        return MonitorResult(allowed=True, alerts=alerts)

    def record_scope_violation(self, token_id: str, *, scope: str, detail: dict[str, Any] | None = None) -> None:
        if not token_security_enabled():
            return
        self._record_event(token_id, "scope_violation", detail={"scope": scope, **(detail or {})})
        get_alert_manager().emit(
            f"scope_violation:{token_id}:{scope}",
            title=f"API scope violation: {scope}",
            detail={"token_id": token_id, "scope": scope},
        )

    def record_suspicious_tool(self, token_id: str, *, tool_name: str) -> None:
        if not token_security_enabled():
            return
        self._record_event(token_id, "suspicious_tool", detail={"tool_name": tool_name})
        get_alert_manager().emit(
            f"suspicious_tool:{token_id}:{tool_name}",
            title=f"Suspicious generated-tool execution: {tool_name}",
            severity="warning",
            detail={"token_id": token_id, "tool_name": tool_name},
        )


_monitor: TokenSecurityMonitor | None = None


def get_token_security_monitor() -> TokenSecurityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = TokenSecurityMonitor()
    return _monitor


def reset_token_security_monitor_for_tests(monitor: TokenSecurityMonitor | None = None) -> TokenSecurityMonitor:
    global _monitor
    _monitor = monitor if monitor is not None else TokenSecurityMonitor()
    return _monitor
