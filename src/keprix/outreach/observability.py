"""Unified standalone outreach observability (Prompt 628).

Aggregates scheduler, delivery, mailbox, Soft Wall backlog, suppressions,
funnel conversion, and a lightweight database latency probe into one snapshot
operators can poll from API/CLI without inventing parallel metrics stores.
"""

from __future__ import annotations

import time
from typing import Any


REQUIRED_METRIC_KEYS: tuple[str, ...] = (
    "scheduler_heartbeat",
    "oldest_due_age_seconds",
    "queue_depth",
    "dead_letters",
    "approval_backlog",
    "send_failures",
    "provider_event_lag_seconds",
    "mailbox_cursor_age_seconds",
    "unmatched_replies",
    "reconciliation_drift",
    "suppressions",
    "funnel_conversion",
    "database_latency_ms",
)


def _db_latency_ms(store: Any) -> float | None:
    started = time.perf_counter()
    try:
        store._fetchone("SELECT 1 AS ok")
    except Exception:
        return None
    return round((time.perf_counter() - started) * 1000.0, 3)


def _provider_event_lag_seconds(store: Any, workspace_id: str | None) -> float | None:
    """Age of oldest sent message still missing a terminal delivery event."""
    from datetime import datetime, timezone

    ws_clause = " AND workspace_id = ?" if workspace_id else ""
    params: tuple[Any, ...] = (workspace_id,) if workspace_id else ()
    row = store._fetchone(
        f"""
        SELECT sent_at FROM outreach_messages
        WHERE sent_at IS NOT NULL
          AND COALESCE(delivery_state, '') IN ('sent', 'queued', '')
          AND COALESCE(bounced, 0) = 0
          {ws_clause}
        ORDER BY sent_at ASC LIMIT 1
        """,
        params,
    )
    if not row or not row.get("sent_at"):
        return 0.0
    try:
        sent = store._parse_iso_dt(str(row["sent_at"]))
        now = datetime.now(timezone.utc)
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        return max(0.0, (now - sent).total_seconds())
    except Exception:
        return None


def _mailbox_cursor_age_seconds(store: Any, workspace_id: str | None) -> float | None:
    from datetime import datetime, timezone

    ws_clause = " WHERE workspace_id = ?" if workspace_id else ""
    params: tuple[Any, ...] = (workspace_id,) if workspace_id else ()
    try:
        row = store._fetchone(
            f"""
            SELECT updated_at FROM outreach_inbound_cursors
            {ws_clause}
            ORDER BY updated_at DESC LIMIT 1
            """,
            params,
        )
    except Exception:
        return None
    if not row or not row.get("updated_at"):
        return None
    try:
        seen = store._parse_iso_dt(str(row["updated_at"]))
        now = datetime.now(timezone.utc)
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        return max(0.0, (now - seen).total_seconds())
    except Exception:
        return None


def _unmatched_replies(store: Any, workspace_id: str | None) -> int:
    ws_clause = " AND workspace_id = ?" if workspace_id else ""
    params: tuple[Any, ...] = (workspace_id,) if workspace_id else ()
    try:
        row = store._fetchone(
            f"""
            SELECT COUNT(*) AS c FROM outreach_replies
            WHERE COALESCE(match_status, '') IN ('unmatched', 'ambiguous')
              AND COALESCE(resolved, 0) = 0
              {ws_clause}
            """,
            params,
        )
        return int((row or {}).get("c") or 0)
    except Exception:
        return 0


def _send_failures(store: Any, workspace_id: str | None) -> int:
    ws_clause = " AND workspace_id = ?" if workspace_id else ""
    params: tuple[Any, ...] = (workspace_id,) if workspace_id else ()
    try:
        row = store._fetchone(
            f"""
            SELECT COUNT(*) AS c FROM outreach_messages
            WHERE COALESCE(delivery_state, '') IN ('failed', 'error', 'soft_bounce')
              {ws_clause}
            """,
            params,
        )
        return int((row or {}).get("c") or 0)
    except Exception:
        return 0


def _suppression_count(workspace_id: str | None, crm_store: Any | None) -> int:
    if crm_store is None or not workspace_id:
        return 0
    try:
        rows = crm_store.list_suppressions(workspace_id)
        return len(rows or [])
    except Exception:
        return 0


def _funnel_conversion(workspace_id: str | None, crm_store: Any | None) -> dict[str, Any]:
    if crm_store is None or not workspace_id:
        return {"available": False}
    try:
        from keprix.crm.funnel_analytics import conversion_rates, funnel_snapshot

        return {
            "available": True,
            "snapshot": funnel_snapshot(workspace_id, crm_store=crm_store),
            "rates": conversion_rates(workspace_id, crm_store=crm_store),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def collect_outreach_observability(
    workspace_id: str | None = None,
    *,
    store: Any | None = None,
    ops: Any | None = None,
    crm_store: Any | None = None,
) -> dict[str, Any]:
    """Return a single operator-facing observability snapshot."""
    from keprix.outreach.ops import get_outreach_ops_store
    from keprix.outreach.reconcile import delivery_health
    from keprix.outreach.store import get_outreach_store

    store = store or get_outreach_store()
    ops = ops or get_outreach_ops_store()
    if crm_store is None:
        try:
            from keprix.crm.store import get_crm_store

            crm_store = get_crm_store()
        except Exception:
            crm_store = None

    health = delivery_health(workspace_id=workspace_id, store=store, ops=ops)
    sched = store.get_scheduler_health(workspace_id)
    pending = 0
    try:
        if workspace_id:
            pending = len(ops.list_approvals(workspace_id, status="pending"))
        else:
            pending = len(ops.list_approvals(status="pending") or [])
    except TypeError:
        try:
            pending = len(ops.list_approvals(workspace_id or "", status="pending"))
        except Exception:
            pending = int(sched.get("awaiting_approval_count") or 0)
    except Exception:
        pending = int(sched.get("awaiting_approval_count") or 0)

    snapshot = {
        "workspace_id": workspace_id,
        "scheduler_heartbeat": sched.get("heartbeat"),
        "oldest_due_age_seconds": sched.get("oldest_due_age_seconds"),
        "queue_depth": int(sched.get("queue_depth") or 0),
        "dead_letters": int(sched.get("dead_letter_count") or 0),
        "approval_backlog": pending,
        "send_failures": _send_failures(store, workspace_id),
        "provider_event_lag_seconds": _provider_event_lag_seconds(store, workspace_id),
        "mailbox_cursor_age_seconds": _mailbox_cursor_age_seconds(store, workspace_id),
        "unmatched_replies": _unmatched_replies(store, workspace_id),
        "reconciliation_drift": int((health.get("delivery") or {}).get("drift_count") or 0),
        "suppressions": _suppression_count(workspace_id, crm_store),
        "funnel_conversion": _funnel_conversion(workspace_id, crm_store),
        "database_latency_ms": _db_latency_ms(store),
        "delivery": health.get("delivery") or {},
        "scheduler": sched,
    }
    missing = [k for k in REQUIRED_METRIC_KEYS if k not in snapshot]
    snapshot["complete"] = not missing
    snapshot["missing_keys"] = missing
    return snapshot
