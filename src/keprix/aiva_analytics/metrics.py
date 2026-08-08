"""Aiva analytics metric helpers (K04)."""

from __future__ import annotations

import logging
import time
from typing import Any

from keprix.aiva_analytics.store import AnalyticsStore, get_analytics_store

logger = logging.getLogger(__name__)

# Metric name constants (OpenTelemetry-style)
AIVA_AGENT_CALLS = "aiva_agent_calls_total"
AIVA_AGENT_DURATION = "aiva_agent_duration_seconds"
AIVA_AGENT_TOKENS = "aiva_agent_tokens_total"
AIVA_AGENT_ERRORS = "aiva_agent_errors_total"
AIVA_TOOL_CALLS = "aiva_tool_calls_total"
AIVA_TOOL_DURATION = "aiva_tool_duration_seconds"
AIVA_OUTREACH_SENT = "aiva_outreach_emails_sent_total"
AIVA_OUTREACH_OPENED = "aiva_outreach_emails_opened_total"
AIVA_OUTREACH_CLICKED = "aiva_outreach_emails_clicked_total"
AIVA_OUTREACH_REPLIES = "aiva_outreach_replies_total"
AIVA_OUTREACH_BOOKINGS = "aiva_outreach_bookings_total"
AIVA_OUTREACH_LEADS = "aiva_outreach_leads_total"
AIVA_WORKER_ACTIVE = "aiva_worker_active_total"
AIVA_WORKER_MESSAGES = "aiva_worker_messages_total"
AIVA_WORKER_ESCALATIONS = "aiva_worker_escalations_total"
AIVA_AGENT_COST_USD = "aiva_agent_cost_usd_total"


def record_metric(
    workspace_id: str,
    metric_name: str,
    metric_value: float = 1.0,
    *,
    labels: dict[str, Any] | None = None,
    store: AnalyticsStore | None = None,
) -> dict[str, Any]:
    target = store or get_analytics_store()
    event = target.record(
        workspace_id=workspace_id,
        metric_name=metric_name,
        metric_value=metric_value,
        labels=labels,
    )
    try:
        from keprix.aiva_analytics.otel_export import export_metric_counter

        export_metric_counter(metric_name, metric_value, labels={"workspace_id": workspace_id, **(labels or {})})
    except Exception:
        logger.debug("otel export skipped", exc_info=True)
    return event


def record_agent_call(
    *,
    workspace_id: str,
    worker_id: str,
    model: str,
    duration_seconds: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float | None = None,
    error_type: str | None = None,
    store: AnalyticsStore | None = None,
) -> None:
    labels = {"workspace_id": workspace_id, "worker_id": worker_id, "model": model}
    record_metric(workspace_id, AIVA_AGENT_CALLS, 1, labels=labels, store=store)
    record_metric(
        workspace_id,
        AIVA_AGENT_DURATION,
        max(0.0, float(duration_seconds)),
        labels={"workspace_id": workspace_id, "worker_id": worker_id},
        store=store,
    )
    if prompt_tokens:
        record_metric(
            workspace_id,
            AIVA_AGENT_TOKENS,
            prompt_tokens,
            labels={"workspace_id": workspace_id, "worker_id": worker_id, "type": "prompt"},
            store=store,
        )
    if completion_tokens:
        record_metric(
            workspace_id,
            AIVA_AGENT_TOKENS,
            completion_tokens,
            labels={"workspace_id": workspace_id, "worker_id": worker_id, "type": "completion"},
            store=store,
        )
    if cost_usd is not None:
        record_metric(
            workspace_id,
            AIVA_AGENT_COST_USD,
            float(cost_usd),
            labels={"workspace_id": workspace_id, "worker_id": worker_id},
            store=store,
        )
    if error_type:
        record_metric(
            workspace_id,
            AIVA_AGENT_ERRORS,
            1,
            labels={"workspace_id": workspace_id, "worker_id": worker_id, "error_type": error_type},
            store=store,
        )


def record_tool_call(
    *,
    workspace_id: str,
    tool_name: str,
    duration_seconds: float = 0.0,
    store: AnalyticsStore | None = None,
) -> None:
    record_metric(
        workspace_id,
        AIVA_TOOL_CALLS,
        1,
        labels={"workspace_id": workspace_id, "tool_name": tool_name},
        store=store,
    )
    if duration_seconds:
        record_metric(
            workspace_id,
            AIVA_TOOL_DURATION,
            float(duration_seconds),
            labels={"workspace_id": workspace_id, "tool_name": tool_name},
            store=store,
        )


def record_outreach_email_sent(
    workspace_id: str,
    campaign_id: str | None = None,
    store: AnalyticsStore | None = None,
) -> None:
    record_metric(
        workspace_id,
        AIVA_OUTREACH_SENT,
        1,
        labels={"workspace_id": workspace_id, "campaign_id": campaign_id or ""},
        store=store,
    )


def record_outreach_reply(
    workspace_id: str,
    classification: str | None = None,
    store: AnalyticsStore | None = None,
) -> None:
    record_metric(
        workspace_id,
        AIVA_OUTREACH_REPLIES,
        1,
        labels={"workspace_id": workspace_id, "classification": classification or "unknown"},
        store=store,
    )
    if classification == "booking_intent":
        record_metric(workspace_id, AIVA_OUTREACH_BOOKINGS, 1, labels={"workspace_id": workspace_id}, store=store)


def record_worker_message(
    workspace_id: str,
    worker_id: str,
    channel: str = "web",
    store: AnalyticsStore | None = None,
) -> None:
    record_metric(
        workspace_id,
        AIVA_WORKER_MESSAGES,
        1,
        labels={"workspace_id": workspace_id, "worker_id": worker_id, "channel": channel},
        store=store,
    )


def record_worker_escalation(
    workspace_id: str,
    worker_id: str,
    store: AnalyticsStore | None = None,
) -> None:
    record_metric(
        workspace_id,
        AIVA_WORKER_ESCALATIONS,
        1,
        labels={"workspace_id": workspace_id, "worker_id": worker_id},
        store=store,
    )


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def seconds(self) -> float:
        return time.perf_counter() - self._start
