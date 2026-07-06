"""Monthly LLM usage budget configuration and status."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, Numeric, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.auth.config import data_dir
from keprix.database import Base, get_session_factory
from keprix.usage.config import get_llm_usage_config
from keprix.usage.filters import UsageQueryFilters
from keprix.usage.store import get_llm_usage_store

_BUDGET_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_usage_budget (
    workspace_id TEXT PRIMARY KEY,
    monthly_budget_usd REAL,
    alert_threshold_percent INTEGER NOT NULL DEFAULT 80,
    updated_at TEXT NOT NULL
);
"""


@dataclass
class BudgetConfig:
    workspace_id: str
    monthly_budget_usd: Decimal | None
    alert_threshold_percent: int = 80
    updated_at: datetime | None = None


class LlmUsageBudgetRow(Base):
    __tablename__ = "llm_usage_budget"

    workspace_id: Mapped[str] = mapped_column(Text, primary_key=True)
    monthly_budget_usd: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    alert_threshold_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LlmUsageBudgetStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self._sqlite_path = sqlite_path or Path(data_dir()) / "llm_usage.db"
        self._budget_table_ready = False

    def _use_sqlite(self) -> bool:
        if get_session_factory() is not None:
            return False
        return get_llm_usage_config().sqlite_fallback

    def _ensure_budget_table_sqlite(self, conn: sqlite3.Connection) -> None:
        if not self._budget_table_ready:
            conn.executescript(_BUDGET_SQLITE_SCHEMA)
            conn.commit()
            self._budget_table_ready = True

    def get_budget_sync(self, workspace_id: str = "default") -> BudgetConfig:
        if self._use_sqlite():
            with sqlite3.connect(self._sqlite_path) as conn:
                self._ensure_budget_table_sqlite(conn)
                row = conn.execute(
                    "SELECT monthly_budget_usd, alert_threshold_percent, updated_at FROM llm_usage_budget WHERE workspace_id = ?",
                    (workspace_id,),
                ).fetchone()
            if not row:
                return BudgetConfig(workspace_id=workspace_id, monthly_budget_usd=None)
            return BudgetConfig(
                workspace_id=workspace_id,
                monthly_budget_usd=Decimal(str(row[0])) if row[0] is not None else None,
                alert_threshold_percent=int(row[1] or 80),
                updated_at=datetime.fromisoformat(row[2]) if row[2] else None,
            )
        return BudgetConfig(workspace_id=workspace_id, monthly_budget_usd=None)

    async def get_budget(self, workspace_id: str = "default") -> BudgetConfig:
        if self._use_sqlite():
            return self.get_budget_sync(workspace_id)
        factory = get_session_factory()
        if factory is None:
            return BudgetConfig(workspace_id=workspace_id, monthly_budget_usd=None)
        async with factory() as session:
            row = await session.get(LlmUsageBudgetRow, workspace_id)
            if row is None:
                return BudgetConfig(workspace_id=workspace_id, monthly_budget_usd=None)
            return BudgetConfig(
                workspace_id=workspace_id,
                monthly_budget_usd=row.monthly_budget_usd,
                alert_threshold_percent=int(row.alert_threshold_percent or 80),
                updated_at=row.updated_at,
            )

    async def set_budget(
        self,
        workspace_id: str,
        *,
        monthly_budget_usd: Decimal | None,
        alert_threshold_percent: int = 80,
    ) -> BudgetConfig:
        now = datetime.now(timezone.utc)
        if self._use_sqlite():
            with sqlite3.connect(self._sqlite_path) as conn:
                self._ensure_budget_table_sqlite(conn)
                conn.execute(
                    """
                    INSERT INTO llm_usage_budget (workspace_id, monthly_budget_usd, alert_threshold_percent, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(workspace_id) DO UPDATE SET
                      monthly_budget_usd = excluded.monthly_budget_usd,
                      alert_threshold_percent = excluded.alert_threshold_percent,
                      updated_at = excluded.updated_at
                    """,
                    (
                        workspace_id,
                        float(monthly_budget_usd) if monthly_budget_usd is not None else None,
                        int(alert_threshold_percent),
                        now.isoformat(),
                    ),
                )
                conn.commit()
            return BudgetConfig(
                workspace_id=workspace_id,
                monthly_budget_usd=monthly_budget_usd,
                alert_threshold_percent=alert_threshold_percent,
                updated_at=now,
            )

        factory = get_session_factory()
        if factory is None:
            return BudgetConfig(workspace_id=workspace_id, monthly_budget_usd=monthly_budget_usd)
        async with factory() as session:
            row = await session.get(LlmUsageBudgetRow, workspace_id)
            if row is None:
                row = LlmUsageBudgetRow(
                    workspace_id=workspace_id,
                    monthly_budget_usd=monthly_budget_usd,
                    alert_threshold_percent=alert_threshold_percent,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.monthly_budget_usd = monthly_budget_usd
                row.alert_threshold_percent = alert_threshold_percent
                row.updated_at = now
            await session.commit()
        return BudgetConfig(
            workspace_id=workspace_id,
            monthly_budget_usd=monthly_budget_usd,
            alert_threshold_percent=alert_threshold_percent,
            updated_at=now,
        )

    def month_start_utc(self) -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async def month_to_date_spend(self, workspace_id: str = "default") -> Decimal:
        filters = UsageQueryFilters(
            workspace_id=workspace_id,
            since=self.month_start_utc(),
        )
        summary = await get_llm_usage_store().aggregate_summary(filters)
        return Decimal(str(summary.get("total_cost_usd") or 0))

    async def budget_status(self, workspace_id: str = "default") -> dict[str, Any]:
        config = await self.get_budget(workspace_id)
        spent = await self.month_to_date_spend(workspace_id)
        budget = config.monthly_budget_usd
        percent_used = None
        alert = False
        if budget is not None and budget > 0:
            percent_used = float(spent / budget * 100)
            alert = percent_used >= float(config.alert_threshold_percent)
        return {
            "workspace_id": workspace_id,
            "spent_usd": float(spent),
            "monthly_budget_usd": float(budget) if budget is not None else None,
            "alert_threshold_percent": config.alert_threshold_percent,
            "percent_used": round(percent_used, 2) if percent_used is not None else None,
            "alert": alert,
            "month_start_utc": self.month_start_utc().date().isoformat(),
        }


_budget_store: LlmUsageBudgetStore | None = None


def get_llm_usage_budget_store() -> LlmUsageBudgetStore:
    global _budget_store
    if _budget_store is None:
        _budget_store = LlmUsageBudgetStore()
    return _budget_store


async def ensure_budget_tables() -> None:
    from keprix.database import get_engine
    engine = get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: LlmUsageBudgetRow.__table__.create(sync_conn, checkfirst=True)
        )
