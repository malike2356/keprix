"""Reconcile stuck outreach delivery states and expire stale Soft Wall approvals."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def reconcile_delivery(
    *,
    workspace_id: str | None = None,
    older_than_minutes: int = 30,
    expire_approvals_hours: int | None = None,
    store=None,
    ops=None,
) -> dict[str, Any]:
    """Flag sent/accepted messages lacking delivered/bounce; expire stale approvals.

    Does not auto-resend. Optional resend remains Soft Wall gated (operator action).
    """
    from keprix.outreach.ops import get_outreach_ops_store
    from keprix.outreach.store import get_outreach_store

    store = store or get_outreach_store()
    ops = ops or get_outreach_ops_store()
    now = _utcnow()
    cutoff = _iso(now - timedelta(minutes=max(1, int(older_than_minutes))))
    expire_h = expire_approvals_hours
    if expire_h is None:
        expire_h = int(os.environ.get("KEPRIX_OUTREACH_APPROVAL_EXPIRE_HOURS") or 72)

    stuck = store.list_stuck_delivery_messages(
        workspace_id=workspace_id,
        older_than_iso=cutoff,
    )
    for msg in stuck:
        try:
            err = str(msg.get("send_error") or "")
            note = "delivery_drift:stuck_without_terminal_event"
            if note not in err:
                store.update_message(
                    str(msg.get("workspace_id") or workspace_id or ""),
                    str(msg["id"]),
                    send_error=note if not err else f"{err};{note}",
                )
        except Exception:
            logger.exception("failed to flag drift message %s", msg.get("id"))

    expired = 0
    if expire_h and expire_h > 0:
        expire_before = _iso(now - timedelta(hours=int(expire_h)))
        try:
            expired = ops.expire_stale_approvals(
                workspace_id=workspace_id,
                older_than_iso=expire_before,
            )
        except Exception:
            logger.exception("expire_stale_approvals failed")

    dry_run = os.environ.get("KEPRIX_OUTREACH_DRY_RUN", "1") not in ("0", "false", "False")
    sender_mode = "dry_run" if dry_run else "live"
    not_configured = False
    if not dry_run and workspace_id:
        try:
            from keprix.outreach.delivery import resolve_sender

            control = ops.get_control(workspace_id)
            resolved = resolve_sender(workspace_id, None, control=control)
            not_configured = resolved.get("mode") == "not_configured"
            sender_mode = str(resolved.get("mode") or sender_mode)
        except Exception:
            pass

    return {
        "workspace_id": workspace_id,
        "at": _iso(now),
        "older_than_minutes": older_than_minutes,
        "drift_count": len(stuck),
        "drift_message_ids": [m.get("id") for m in stuck],
        "expired_approvals": expired,
        "dry_run": dry_run,
        "sender_mode": sender_mode,
        "not_configured": not_configured,
    }


def delivery_health(*, workspace_id: str | None = None, store=None, ops=None) -> dict[str, Any]:
    """Health chip payload: dry_run, not_configured, drift count."""
    from keprix.outreach.ops import get_outreach_ops_store
    from keprix.outreach.store import get_outreach_store

    store = store or get_outreach_store()
    ops = ops or get_outreach_ops_store()
    recon = reconcile_delivery(
        workspace_id=workspace_id,
        older_than_minutes=int(os.environ.get("KEPRIX_OUTREACH_DRIFT_MINUTES") or 30),
        store=store,
        ops=ops,
    )
    sched = store.get_scheduler_health(workspace_id)
    return {
        **sched,
        "delivery": {
            "dry_run": recon["dry_run"],
            "not_configured": recon["not_configured"],
            "sender_mode": recon["sender_mode"],
            "drift_count": recon["drift_count"],
            "expired_approvals": recon["expired_approvals"],
        },
    }
