"""Persistent per-workspace/channel pacing ledger.

This module records successful deliveries only. It never sends messages and
therefore cannot bypass the outreach Soft Wall.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _day_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def ensure_pacing_schema(store: Any) -> None:
    store._conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS crm_channel_send_ledger (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            lead_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            day_key TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            UNIQUE(workspace_id, channel, lead_id, kind, day_key)
        );
        CREATE INDEX IF NOT EXISTS ix_crm_channel_send_ledger_day
            ON crm_channel_send_ledger(workspace_id, channel, day_key);
        """
    )
    store._conn.commit()


def sent_today(store: Any, workspace_id: str, channel: str) -> int:
    ensure_pacing_schema(store)
    return int(store._conn.execute("SELECT COUNT(*) FROM crm_channel_send_ledger WHERE workspace_id = ? AND channel = ? AND day_key = ?", (workspace_id, channel, _day_key())).fetchone()[0])


def can_send(store: Any, workspace_id: str, channel: str, cap: int) -> bool:
    return sent_today(store, workspace_id, channel) < max(0, int(cap))


def record_send(store: Any, workspace_id: str, channel: str, lead_id: str, kind: str = "message", *, event_id: str | None = None) -> bool:
    ensure_pacing_schema(store)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    cursor = store._conn.execute(
        "INSERT OR IGNORE INTO crm_channel_send_ledger (id, workspace_id, channel, lead_id, kind, day_key, sent_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_id or f"send_{int(datetime.now(timezone.utc).timestamp() * 1000000)}", workspace_id, channel, lead_id, kind, _day_key(), now),
    )
    store._conn.commit()
    return cursor.rowcount == 1


def drain_batch(store: Any, workspace_id: str, channel: str, lead_ids: list[str], cap: int) -> list[str]:
    """Return the next eligible IDs; caller records each only after success."""
    remaining = max(0, int(cap) - sent_today(store, workspace_id, channel))
    if remaining <= 0:
        return []
    seen = {str(row[0]) for row in store._conn.execute("SELECT lead_id FROM crm_channel_send_ledger WHERE workspace_id = ? AND channel = ? AND day_key = ?", (workspace_id, channel, _day_key())).fetchall()}
    return [str(lead_id) for lead_id in lead_ids if str(lead_id) not in seen][:remaining]
