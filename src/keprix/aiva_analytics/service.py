"""Aiva analytics aggregation service (K04)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.aiva_analytics import metrics as m
from keprix.aiva_analytics.store import AnalyticsStore, get_analytics_store

_service: "AnalyticsService | None" = None
_lock = threading.Lock()


def _since_days(days: int) -> str:
    day = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    return day.replace(microsecond=0).isoformat()


def _day_key(iso: str) -> str:
    return iso[:10]


class AnalyticsService:
    def __init__(self, store: AnalyticsStore | None = None) -> None:
        self.store = store or get_analytics_store()

    def overview(self, workspace_id: str, *, days: int = 30) -> dict[str, Any]:
        since = _since_days(days)
        agent_calls = self.store.sum_metric(workspace_id, m.AIVA_AGENT_CALLS, since=since)
        tokens = self.store.sum_metric(workspace_id, m.AIVA_AGENT_TOKENS, since=since)
        errors = self.store.sum_metric(workspace_id, m.AIVA_AGENT_ERRORS, since=since)
        duration = self.store.sum_metric(workspace_id, m.AIVA_AGENT_DURATION, since=since)
        cost = self.store.sum_metric(workspace_id, m.AIVA_AGENT_COST_USD, since=since)
        tool_calls = self.store.sum_metric(workspace_id, m.AIVA_TOOL_CALLS, since=since)
        emails_sent = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_SENT, since=since)
        replies = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_REPLIES, since=since)
        bookings = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_BOOKINGS, since=since)
        worker_msgs = self.store.sum_metric(workspace_id, m.AIVA_WORKER_MESSAGES, since=since)
        escalations = self.store.sum_metric(workspace_id, m.AIVA_WORKER_ESCALATIONS, since=since)

        avg_duration = (duration / agent_calls) if agent_calls else 0.0
        reply_rate = (replies / emails_sent) if emails_sent else 0.0
        booking_rate = (bookings / emails_sent) if emails_sent else 0.0

        return {
            "workspace_id": workspace_id,
            "days": days,
            "agent": {
                "calls": agent_calls,
                "tokens": tokens,
                "errors": errors,
                "avg_duration_seconds": round(avg_duration, 4),
                "estimated_cost_usd": round(cost, 6),
                "tool_calls": tool_calls,
            },
            "outreach": {
                "emails_sent": emails_sent,
                "replies": replies,
                "bookings": bookings,
                "reply_rate": round(reply_rate, 4),
                "booking_rate": round(booking_rate, 4),
            },
            "workers": {
                "messages": worker_msgs,
                "escalations": escalations,
            },
        }

    def outreach(self, workspace_id: str, *, campaign_id: str | None = None, days: int = 30) -> dict[str, Any]:
        since = _since_days(days)
        cid = campaign_id or ""

        def _sum(name: str) -> float:
            if campaign_id:
                return self.store.sum_metric(
                    workspace_id, name, since=since, label_key="campaign_id", label_value=cid
                )
            return self.store.sum_metric(workspace_id, name, since=since)

        sent = _sum(m.AIVA_OUTREACH_SENT)
        opened = _sum(m.AIVA_OUTREACH_OPENED)
        clicked = _sum(m.AIVA_OUTREACH_CLICKED)
        replies = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_REPLIES, since=since)
        bookings = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_BOOKINGS, since=since)
        leads = self.store.sum_metric(workspace_id, m.AIVA_OUTREACH_LEADS, since=since)

        # Enrich from outreach store when available
        campaign_stats = None
        try:
            from keprix.outreach.service import get_outreach_service

            svc = get_outreach_service()
            if campaign_id:
                campaign_stats = svc.store.campaign_stats(workspace_id, campaign_id)
            else:
                campaigns = svc.store.list_campaigns(workspace_id)
                campaign_stats = {"campaigns": len(campaigns), "items": campaigns[:20]}
        except Exception:
            campaign_stats = None

        return {
            "workspace_id": workspace_id,
            "campaign_id": campaign_id,
            "days": days,
            "funnel": {
                "emails_sent": sent,
                "emails_opened": opened,
                "emails_clicked": clicked,
                "replies": replies,
                "bookings": bookings,
                "leads": leads,
                "open_rate": round((opened / sent) if sent else 0.0, 4),
                "click_rate": round((clicked / sent) if sent else 0.0, 4),
                "reply_rate": round((replies / sent) if sent else 0.0, 4),
                "booking_rate": round((bookings / sent) if sent else 0.0, 4),
            },
            "campaign_stats": campaign_stats,
        }

    def worker(self, workspace_id: str, *, worker_id: str | None = None, days: int = 30) -> dict[str, Any]:
        since = _since_days(days)
        wid = worker_id or ""

        def _sum(name: str) -> float:
            if worker_id:
                return self.store.sum_metric(
                    workspace_id, name, since=since, label_key="worker_id", label_value=wid
                )
            return self.store.sum_metric(workspace_id, name, since=since)

        messages = _sum(m.AIVA_WORKER_MESSAGES)
        escalations = _sum(m.AIVA_WORKER_ESCALATIONS)
        agent_calls = _sum(m.AIVA_AGENT_CALLS)
        tokens = _sum(m.AIVA_AGENT_TOKENS)
        duration = _sum(m.AIVA_AGENT_DURATION)
        cost = _sum(m.AIVA_AGENT_COST_USD)

        return {
            "workspace_id": workspace_id,
            "worker_id": worker_id,
            "days": days,
            "messages": messages,
            "escalations": escalations,
            "agent_calls": agent_calls,
            "tokens": tokens,
            "avg_duration_seconds": round((duration / agent_calls) if agent_calls else 0.0, 4),
            "estimated_cost_usd": round(cost, 6),
        }

    def usage(self, workspace_id: str, *, days: int = 30) -> dict[str, Any]:
        since = _since_days(days)
        events = self.store.query_events(workspace_id, since=since, limit=20000)
        by_day: dict[str, dict[str, float]] = {}
        for ev in events:
            day = _day_key(str(ev.get("recorded_at") or ""))
            if not day:
                continue
            bucket = by_day.setdefault(
                day,
                {
                    "agent_calls": 0.0,
                    "tokens": 0.0,
                    "cost_usd": 0.0,
                    "emails_sent": 0.0,
                    "replies": 0.0,
                    "worker_messages": 0.0,
                },
            )
            name = ev.get("metric_name")
            val = float(ev.get("metric_value") or 0)
            if name == m.AIVA_AGENT_CALLS:
                bucket["agent_calls"] += val
            elif name == m.AIVA_AGENT_TOKENS:
                bucket["tokens"] += val
            elif name == m.AIVA_AGENT_COST_USD:
                bucket["cost_usd"] += val
            elif name == m.AIVA_OUTREACH_SENT:
                bucket["emails_sent"] += val
            elif name == m.AIVA_OUTREACH_REPLIES:
                bucket["replies"] += val
            elif name == m.AIVA_WORKER_MESSAGES:
                bucket["worker_messages"] += val

        series = [{"day": d, **by_day[d]} for d in sorted(by_day.keys())]
        totals = {
            "agent_calls": sum(x["agent_calls"] for x in series),
            "tokens": sum(x["tokens"] for x in series),
            "cost_usd": round(sum(x["cost_usd"] for x in series), 6),
            "emails_sent": sum(x["emails_sent"] for x in series),
            "replies": sum(x["replies"] for x in series),
            "worker_messages": sum(x["worker_messages"] for x in series),
        }

        daily = self.store.list_daily(
            workspace_id,
            since_day=(datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))).date().isoformat(),
        )

        return {
            "workspace_id": workspace_id,
            "days": days,
            "series": series,
            "totals": totals,
            "daily_summaries": daily,
        }

    def aggregate_daily(self, *, lookback_days: int = 2) -> dict[str, Any]:
        since = _since_days(lookback_days)
        workspaces = self.store.list_workspaces_with_events(since=since)
        rolled = 0
        for ws in workspaces:
            events = self.store.query_events(ws, since=since, limit=50000)
            buckets: dict[tuple[str, str], float] = {}
            for ev in events:
                day = _day_key(str(ev.get("recorded_at") or ""))
                name = str(ev.get("metric_name") or "")
                if not day or not name:
                    continue
                key = (day, name)
                buckets[key] = buckets.get(key, 0.0) + float(ev.get("metric_value") or 0)
            for (day, name), value in buckets.items():
                self.store.upsert_daily(
                    workspace_id=ws,
                    day=day,
                    metric_name=name,
                    metric_value=value,
                    labels={},
                )
                rolled += 1
        return {"workspaces": len(workspaces), "rows_upserted": rolled}


def get_analytics_service(store: AnalyticsStore | None = None) -> AnalyticsService:
    global _service
    if store is not None:
        return AnalyticsService(store=store)
    with _lock:
        if _service is None:
            _service = AnalyticsService()
        return _service


def reset_analytics_service_for_tests(store: AnalyticsStore | None = None) -> AnalyticsService:
    global _service
    with _lock:
        _service = AnalyticsService(store=store) if store else AnalyticsService()
        return _service
