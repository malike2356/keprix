"""LLM usage analytics service (Prompt 146)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from keprix.usage.budget import get_llm_usage_budget_store
from keprix.usage.filters import UsageQueryFilters
from keprix.usage.store import get_llm_usage_store


class LlmUsageAnalytics:
    async def summary(self, filters: UsageQueryFilters) -> dict[str, Any]:
        return await get_llm_usage_store().aggregate_summary(filters)

    async def timeseries(
        self,
        filters: UsageQueryFilters,
        *,
        granularity: Literal["day", "hour"] = "day",
    ) -> list[dict[str, Any]]:
        return await get_llm_usage_store().aggregate_timeseries(filters, granularity=granularity)

    async def breakdown(
        self,
        filters: UsageQueryFilters,
        *,
        dimension: Literal["model", "provider", "channel", "user", "agent"],
    ) -> list[dict[str, Any]]:
        return await get_llm_usage_store().aggregate_breakdown(filters, dimension=dimension)

    async def list_events(
        self,
        filters: UsageQueryFilters,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await get_llm_usage_store().list_events(filters, limit=limit, offset=offset)

    async def budget_status(self, workspace_id: str = "default") -> dict[str, Any]:
        return await get_llm_usage_budget_store().budget_status(workspace_id)

    async def set_budget(
        self,
        workspace_id: str,
        *,
        monthly_budget_usd: Decimal | None,
        alert_threshold_percent: int = 80,
    ) -> dict[str, Any]:
        config = await get_llm_usage_budget_store().set_budget(
            workspace_id,
            monthly_budget_usd=monthly_budget_usd,
            alert_threshold_percent=alert_threshold_percent,
        )
        return {
            "workspace_id": config.workspace_id,
            "monthly_budget_usd": float(config.monthly_budget_usd)
            if config.monthly_budget_usd is not None
            else None,
            "alert_threshold_percent": config.alert_threshold_percent,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }


_analytics: LlmUsageAnalytics | None = None


def get_llm_usage_analytics() -> LlmUsageAnalytics:
    global _analytics
    if _analytics is None:
        _analytics = LlmUsageAnalytics()
    return _analytics
