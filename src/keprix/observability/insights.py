"""API-facing insights built on the session insights engine."""

from __future__ import annotations

from typing import Any


def usage_summary(days: int = 30, user_id: str | None = None) -> dict[str, Any]:
    """Return usage summary from session DB when available, else metrics fallback."""
    try:
        from keprix_state import SessionDB

        db = SessionDB()
        from agent.insights import InsightsEngine

        engine = InsightsEngine(db)
        report = engine.generate(days=days)
        if user_id:
            report["user_id"] = user_id
        return report
    except Exception:
        return {
            "days": days,
            "sessions": 0,
            "messages": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "note": "Session database unavailable; metrics API still active.",
        }


async def timeline_from_metrics(days: int = 30, user_id: str | None = None) -> dict[str, Any]:
    from keprix.observability.metrics import get_metrics_store

    store = get_metrics_store()
    messages = await store.sum_by_day(metric_type="message", days=days, user_id=user_id)
    tokens = await store.sum_by_day(metric_type="token", days=days, user_id=user_id)
    return {"days": days, "messages": messages, "tokens": tokens}
