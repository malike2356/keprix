"""Persistent managed AI credit ledger (SQLite + optional PostgreSQL)."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from keprix.auth.config import data_dir

logger = logging.getLogger(__name__)

LedgerEntryType = Literal[
    "grant",
    "debit",
    "purchase",
    "refund",
    "expiry",
    "admin_adjust",
    "included_reset",
]

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_credit_wallets (
    workspace_id TEXT PRIMARY KEY,
    user_id TEXT,
    balance_credits INTEGER NOT NULL DEFAULT 0,
    included_remaining INTEGER NOT NULL DEFAULT 0,
    included_period TEXT,
    trial_granted INTEGER NOT NULL DEFAULT 0,
    spend_limit_credits INTEGER,
    alert_percent INTEGER NOT NULL DEFAULT 80,
    last_alert_key TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_credit_ledger (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    user_id TEXT,
    entry_type TEXT NOT NULL,
    credits INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    model TEXT,
    channel TEXT,
    run_id TEXT,
    note TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ai_ledger_workspace_created
    ON ai_credit_ledger(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS ix_ai_ledger_type_created
    ON ai_credit_ledger(entry_type, created_at);
CREATE TABLE IF NOT EXISTS ai_credit_daily (
    workspace_id TEXT NOT NULL,
    day TEXT NOT NULL,
    credits_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (workspace_id, day)
);
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


@dataclass
class WalletState:
    workspace_id: str
    user_id: str | None = None
    balance_credits: int = 0
    included_remaining: int = 0
    included_period: str | None = None
    trial_granted: int = 0
    spend_limit_credits: int | None = None
    alert_percent: int = 80
    last_alert_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""

    @property
    def available(self) -> int:
        return max(0, int(self.included_remaining)) + max(0, int(self.balance_credits))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "balance_credits": self.balance_credits,
            "included_remaining": self.included_remaining,
            "included_period": self.included_period,
            "trial_granted": self.trial_granted,
            "spend_limit_credits": self.spend_limit_credits,
            "alert_percent": self.alert_percent,
            "available_credits": self.available,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata or {}),
        }


@dataclass
class LedgerEntry:
    id: str
    workspace_id: str
    user_id: str | None
    entry_type: LedgerEntryType
    credits: int
    balance_after: int
    model: str | None = None
    channel: str | None = None
    run_id: str | None = None
    note: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "entry_type": self.entry_type,
            "credits": self.credits,
            "balance_after": self.balance_after,
            "model": self.model,
            "channel": self.channel,
            "run_id": self.run_id,
            "note": self.note,
            "metadata": dict(self.metadata or {}),
            "created_at": self.created_at,
        }


class AiCreditStore:
    """File-backed SQLite ledger. Safe for CE/dev without Postgres."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "ai_credit_wallet.db"
        self._ready = False

    def _conn(self) -> sqlite3.Connection:
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._sqlite_path))
        conn.row_factory = sqlite3.Row
        if not self._ready:
            conn.executescript(_SQLITE_SCHEMA)
            conn.commit()
            self._ready = True
        return conn

    def get_wallet(self, workspace_id: str) -> WalletState:
        ws = (workspace_id or "default").strip() or "default"
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ai_credit_wallets WHERE workspace_id = ?",
                (ws,),
            ).fetchone()
        if row is None:
            return WalletState(workspace_id=ws, updated_at=_iso())
        meta_raw = row["metadata"] or "{}"
        try:
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else dict(meta_raw or {})
        except Exception:
            meta = {}
        return WalletState(
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            balance_credits=int(row["balance_credits"] or 0),
            included_remaining=int(row["included_remaining"] or 0),
            included_period=row["included_period"],
            trial_granted=int(row["trial_granted"] or 0),
            spend_limit_credits=row["spend_limit_credits"],
            alert_percent=int(row["alert_percent"] or 80),
            last_alert_key=row["last_alert_key"] or "",
            metadata=meta,
            updated_at=row["updated_at"] or "",
        )

    def _upsert_wallet(self, conn: sqlite3.Connection, wallet: WalletState) -> None:
        conn.execute(
            """
            INSERT INTO ai_credit_wallets (
                workspace_id, user_id, balance_credits, included_remaining,
                included_period, trial_granted, spend_limit_credits, alert_percent,
                last_alert_key, metadata, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                user_id = excluded.user_id,
                balance_credits = excluded.balance_credits,
                included_remaining = excluded.included_remaining,
                included_period = excluded.included_period,
                trial_granted = excluded.trial_granted,
                spend_limit_credits = excluded.spend_limit_credits,
                alert_percent = excluded.alert_percent,
                last_alert_key = excluded.last_alert_key,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at
            """,
            (
                wallet.workspace_id,
                wallet.user_id,
                int(wallet.balance_credits),
                int(wallet.included_remaining),
                wallet.included_period,
                int(wallet.trial_granted),
                wallet.spend_limit_credits,
                int(wallet.alert_percent),
                wallet.last_alert_key or "",
                json.dumps(wallet.metadata or {}),
                wallet.updated_at or _iso(),
            ),
        )

    def append_entry(
        self,
        *,
        workspace_id: str,
        entry_type: LedgerEntryType,
        credits: int,
        user_id: str | None = None,
        model: str | None = None,
        channel: str | None = None,
        run_id: str | None = None,
        note: str | None = None,
        metadata: dict[str, Any] | None = None,
        apply_to_balance: bool = True,
        apply_to_included: bool = False,
    ) -> tuple[WalletState, LedgerEntry]:
        """Append an immutable ledger row and update wallet balances."""
        ws = (workspace_id or "default").strip() or "default"
        delta = int(credits)
        with self._conn() as conn:
            wallet = self.get_wallet(ws)
            if user_id:
                wallet.user_id = user_id

            if apply_to_included and delta != 0:
                # Positive grant increases included; negative debit reduces it.
                wallet.included_remaining = max(0, int(wallet.included_remaining) + delta)

            if apply_to_balance and delta != 0 and not apply_to_included:
                wallet.balance_credits = int(wallet.balance_credits) + delta
                if wallet.balance_credits < 0 and entry_type == "debit":
                    # Allow momentary dip; next gate blocks. Clamp for grants/refunds.
                    pass
                elif entry_type in {"grant", "purchase", "refund", "admin_adjust"} and wallet.balance_credits < 0:
                    wallet.balance_credits = 0

            if entry_type == "debit" and apply_to_balance and not apply_to_included:
                # Debits are negative credits in the ledger.
                pass

            wallet.updated_at = _iso()
            self._upsert_wallet(conn, wallet)

            entry = LedgerEntry(
                id=str(uuid.uuid4()),
                workspace_id=ws,
                user_id=wallet.user_id,
                entry_type=entry_type,
                credits=delta,
                balance_after=wallet.available,
                model=model,
                channel=channel,
                run_id=run_id,
                note=note,
                metadata=dict(metadata or {}),
                created_at=_iso(),
            )
            conn.execute(
                """
                INSERT INTO ai_credit_ledger (
                    id, workspace_id, user_id, entry_type, credits, balance_after,
                    model, channel, run_id, note, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.workspace_id,
                    entry.user_id,
                    entry.entry_type,
                    entry.credits,
                    entry.balance_after,
                    entry.model,
                    entry.channel,
                    entry.run_id,
                    entry.note,
                    json.dumps(entry.metadata or {}),
                    entry.created_at,
                ),
            )
            conn.commit()
            return wallet, entry

    def save_wallet(self, wallet: WalletState) -> WalletState:
        wallet.updated_at = _iso()
        with self._conn() as conn:
            self._upsert_wallet(conn, wallet)
            conn.commit()
        return wallet

    def list_ledger(
        self,
        workspace_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        ws = (workspace_id or "default").strip() or "default"
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ai_credit_ledger
                WHERE workspace_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (ws, max(1, min(int(limit), 500)), max(0, int(offset))),
            ).fetchall()
        out: list[LedgerEntry] = []
        for row in rows:
            try:
                meta = json.loads(row["metadata"] or "{}")
            except Exception:
                meta = {}
            out.append(
                LedgerEntry(
                    id=row["id"],
                    workspace_id=row["workspace_id"],
                    user_id=row["user_id"],
                    entry_type=row["entry_type"],  # type: ignore[arg-type]
                    credits=int(row["credits"]),
                    balance_after=int(row["balance_after"]),
                    model=row["model"],
                    channel=row["channel"],
                    run_id=row["run_id"],
                    note=row["note"],
                    metadata=meta,
                    created_at=row["created_at"],
                )
            )
        return out

    def add_daily_usage(self, workspace_id: str, credits: int, *, day: str | None = None) -> int:
        ws = (workspace_id or "default").strip() or "default"
        day_key = day or _utcnow().strftime("%Y-%m-%d")
        used = max(0, int(credits))
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ai_credit_daily (workspace_id, day, credits_used)
                VALUES (?, ?, ?)
                ON CONFLICT(workspace_id, day) DO UPDATE SET
                    credits_used = credits_used + excluded.credits_used
                """,
                (ws, day_key, used),
            )
            row = conn.execute(
                "SELECT credits_used FROM ai_credit_daily WHERE workspace_id = ? AND day = ?",
                (ws, day_key),
            ).fetchone()
            conn.commit()
            return int(row["credits_used"] if row else used)

    def get_daily_usage(self, workspace_id: str, *, day: str | None = None) -> int:
        ws = (workspace_id or "default").strip() or "default"
        day_key = day or _utcnow().strftime("%Y-%m-%d")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT credits_used FROM ai_credit_daily WHERE workspace_id = ? AND day = ?",
                (ws, day_key),
            ).fetchone()
        return int(row["credits_used"] if row else 0)


_store: AiCreditStore | None = None


def get_ai_credit_store() -> AiCreditStore:
    global _store
    if _store is None:
        _store = AiCreditStore()
    return _store


def reset_ai_credit_store_for_tests(store: AiCreditStore | None = None) -> AiCreditStore:
    global _store
    _store = store if store is not None else AiCreditStore()
    return _store
