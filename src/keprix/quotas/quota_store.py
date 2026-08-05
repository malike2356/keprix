"""QuotaStore: atomic per-product usage tracking with period reset.

Persists to JSON under the data dir so usage survives process restart.
Postgres remains the preferred multi-instance path when wired separately.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .quota_config import (
    ProductQuota,
    QuotaUsage,
    ResourceType,
    get_quota_config,
)


def _period_bounds(period: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (period_start, period_end) for the given cadence relative to now."""
    if now is None:
        now = datetime.now(tz=timezone.utc)

    if period == "hourly":
        start = now.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
    elif period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif period == "weekly":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(weeks=1)
    else:  # monthly
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)

    return start, end


def _store_path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "quotas"
    except Exception:
        root = Path.home() / ".keprix" / "quotas"
    root.mkdir(parents=True, exist_ok=True)
    return root / "usage.json"


@dataclass
class _ProductState:
    usage: dict[ResourceType, int] = field(default_factory=dict)
    concurrent_sessions: int = 0
    period_start: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class QuotaStore:
    """JSON-backed quota usage store with atomic increment and period reset."""

    def __init__(self, quota_config=None, path: Path | None = None) -> None:
        self._config = quota_config or get_quota_config()
        self._states: dict[str, _ProductState] = {}
        self._lock = asyncio.Lock()
        self._path = path or _store_path()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        for product_id, row in (payload.get("products") or {}).items():
            usage_raw = row.get("usage") or {}
            usage: dict[ResourceType, int] = {}
            for key, value in usage_raw.items():
                try:
                    usage[ResourceType(key)] = int(value)
                except Exception:
                    continue
            state = _ProductState(
                usage=usage,
                concurrent_sessions=int(row.get("concurrent_sessions") or 0),
            )
            try:
                state.period_start = datetime.fromisoformat(str(row["period_start"]))
                state.period_end = datetime.fromisoformat(str(row["period_end"]))
            except Exception:
                pass
            self._states[str(product_id)] = state

    def _persist(self) -> None:
        products: dict[str, Any] = {}
        for product_id, state in self._states.items():
            products[product_id] = {
                "usage": {
                    (k.value if hasattr(k, "value") else str(k)): v for k, v in state.usage.items()
                },
                "concurrent_sessions": state.concurrent_sessions,
                "period_start": state.period_start.isoformat(),
                "period_end": state.period_end.isoformat(),
            }
        self._path.write_text(json.dumps({"products": products}, indent=2), encoding="utf-8")

    def _get_or_create_state(self, product_id: str) -> _ProductState:
        if product_id not in self._states:
            self._states[product_id] = _ProductState()
        return self._states[product_id]

    async def _ensure_period(self, product_id: str, quota: ProductQuota) -> _ProductState:
        state = self._get_or_create_state(product_id)
        now = datetime.now(tz=timezone.utc)
        if now >= state.period_end:
            start, end = _period_bounds(quota.period, now)
            state.usage = {}
            state.period_start = start
            state.period_end = end
            self._persist()
        elif state.period_end == state.period_start:
            start, end = _period_bounds(quota.period, now)
            state.period_start = start
            state.period_end = end
            self._persist()
        return state

    async def increment(
        self,
        product_id: str,
        resource: ResourceType,
        amount: int,
        session_id: str | None = None,
    ) -> QuotaUsage:
        async with self._lock:
            quota = await self._config.get_quota(product_id)
            state = await self._ensure_period(product_id, quota)
            state.usage[resource] = state.usage.get(resource, 0) + amount
            self._persist()
            return self._build_usage(product_id, state, quota)

    async def get_usage(self, product_id: str) -> QuotaUsage:
        async with self._lock:
            quota = await self._config.get_quota(product_id)
            state = await self._ensure_period(product_id, quota)
            return self._build_usage(product_id, state, quota)

    async def reset_period(self, product_id: str) -> None:
        async with self._lock:
            await self._config.get_quota(product_id)
            state = self._get_or_create_state(product_id)
            start, end = _period_bounds(
                (await self._config.get_quota(product_id)).period
            )
            state.usage = {}
            state.period_start = start
            state.period_end = end
            self._persist()

    async def set_concurrent_sessions(self, product_id: str, count: int) -> None:
        async with self._lock:
            state = self._get_or_create_state(product_id)
            state.concurrent_sessions = max(0, count)
            self._persist()

    async def increment_concurrent_sessions(self, product_id: str, delta: int = 1) -> int:
        async with self._lock:
            state = self._get_or_create_state(product_id)
            state.concurrent_sessions = max(0, state.concurrent_sessions + delta)
            self._persist()
            return state.concurrent_sessions

    def _build_usage(
        self, product_id: str, state: _ProductState, quota: ProductQuota
    ) -> QuotaUsage:
        usage = dict(state.usage)
        if state.concurrent_sessions > 0:
            usage[ResourceType.CONCURRENT_SESSIONS] = state.concurrent_sessions
        return QuotaUsage(
            product_id=product_id,
            period_start=state.period_start,
            period_end=state.period_end,
            usage=usage,
            limits=dict(quota.limits),
            burst_allowance=quota.burst_allowance,
        )
