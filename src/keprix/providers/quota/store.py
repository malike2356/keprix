"""SQLite persistence for quota buckets."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from keprix.providers.quota.tracker import QuotaBucket


class SQLiteQuotaStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure()

    def _ensure(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_quota (
                    provider TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    limit_tokens INTEGER NOT NULL,
                    used_tokens INTEGER NOT NULL,
                    reserved_tokens INTEGER NOT NULL,
                    burn_rate REAL NOT NULL,
                    PRIMARY KEY(provider, account_id)
                )
                """
            )

    def save(self, bucket: QuotaBucket) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO provider_quota
                (provider, account_id, limit_tokens, used_tokens, reserved_tokens, burn_rate)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bucket.provider, bucket.account_id, bucket.limit, bucket.used, bucket.reserved, bucket.burn_rate),
            )

    def load(self, provider: str, account_id: str = "default") -> QuotaBucket | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT provider, account_id, limit_tokens, used_tokens, reserved_tokens, burn_rate FROM provider_quota WHERE provider = ? AND account_id = ?",
                (provider, account_id),
            ).fetchone()
        if row is None:
            return None
        return QuotaBucket(provider=row[0], account_id=row[1], limit=int(row[2]), used=int(row[3]), reserved=int(row[4]), burn_rate=float(row[5]))
