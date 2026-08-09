"""Nurture orchestration around booking and support cases (Prompt 634)."""

from __future__ import annotations

import os
from typing import Any


def _meta(booking: Any) -> dict[str, Any]:
    if isinstance(booking, dict):
        return dict(booking.get("metadata") or {})
    return dict(getattr(booking, "metadata", None) or {})


def stop_sales_cadence_on_booking(booking: Any) -> dict[str, Any]:
    """Confirmed booking stops sales cadence (Soft Wall + CRM)."""
    from keprix.crm.booking import on_vical_booking_confirmed_crm

    result = on_vical_booking_confirmed_crm(booking)
    return {
        "ok": True,
        "action": "stop_sales_cadence",
        "reason": "booking_confirmed",
        "handoff": result,
    }


def pause_outreach_for_support_case(
    *,
    workspace_id: str,
    guest_email: str | None = None,
    outreach_lead_id: str | None = None,
    support_case_id: str | None = None,
) -> dict[str, Any]:
    """Active support cases pause inappropriate outreach messages."""
    lead_id = outreach_lead_id
    out: dict[str, Any] = {
        "ok": True,
        "action": "pause_outreach_support_case",
        "supportCaseId": support_case_id,
        "paused": False,
    }
    try:
        from keprix.outreach.store import get_outreach_store

        store = get_outreach_store()
        if not lead_id and guest_email:
            email = guest_email.strip().lower()
            for lead in store.list_leads(workspace_id, limit=500):
                if str(lead.get("email") or "").strip().lower() == email:
                    lead_id = lead["id"]
                    break
        if not lead_id:
            out["ok"] = False
            out["reason"] = "lead_not_found"
            return out
        # Prefer explicit pause status when present; else tag metadata via status note
        try:
            store.update_lead_status(workspace_id, str(lead_id), "paused_support")
        except Exception:
            with store._lock:  # noqa: SLF001
                store._conn.execute(
                    "UPDATE outreach_leads SET status = ? WHERE id = ? AND workspace_id = ?",
                    ("paused_support", str(lead_id), workspace_id),
                )
                store._conn.commit()
        out["paused"] = True
        out["outreachLeadId"] = lead_id
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)[:200]
    return out


def apply_cancellation_policy(
    booking: Any,
    *,
    policy: str | None = None,
) -> dict[str, Any]:
    """Cancellation follows operator policy (default: do not auto-restart cadence)."""
    resolved = (policy or os.environ.get("KEPRIX_CONCIERGE_CANCEL_NURTURE_POLICY") or "hold").strip().lower()
    # hold = leave lead booked/cancelled without re-enrolling
    # resume = optional operator-approved re-open (not automatic sales restart)
    return {
        "ok": True,
        "action": "cancellation_policy",
        "policy": resolved if resolved in {"hold", "resume"} else "hold",
        "autoRestartCadence": False,
        "bookingId": _meta(booking).get("id")
        or (booking.get("id") if isinstance(booking, dict) else getattr(booking, "id", None)),
        "note": "Cadence does not auto-restart after cancel; operator must approve resume.",
    }


def no_show_recovery_gate(*, approved_automation: bool | None = None) -> dict[str, Any]:
    """No-show recovery requires approved automation."""
    env_ok = os.environ.get("KEPRIX_CONCIERGE_NOSHOW_RECOVERY_APPROVED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    allowed = bool(approved_automation) if approved_automation is not None else env_ok
    return {
        "ok": allowed,
        "action": "no_show_recovery",
        "allowed": allowed,
        "requiresApprovedAutomation": True,
        "error_code": None if allowed else "no_show_recovery_not_approved",
    }


def update_funnel_outcome(
    *,
    workspace_id: str,
    booking_id: str,
    outcome: str,
    conversion: bool | None = None,
) -> dict[str, Any]:
    """Persist outcome/conversion onto booking metadata for funnel reporting."""
    from keprix.vical.store import vical_store

    booking = vical_store.get_booking(workspace_id, booking_id)
    if not booking:
        return {"ok": False, "error_code": "booking_not_found"}
    meta = dict(booking.metadata or {})
    meta["outcome"] = outcome
    if conversion is not None:
        meta["conversion"] = conversion
    updated = vical_store.update_booking(workspace_id, booking_id, metadata=meta)
    return {
        "ok": True,
        "bookingId": booking_id,
        "outcome": outcome,
        "conversion": conversion,
        "status": updated.status,
    }


def orchestrate_after_booking_confirmed(
    booking: Any,
    *,
    audience_session_id: str | None = None,
) -> dict[str, Any]:
    stop = stop_sales_cadence_on_booking(booking)
    from keprix.customer_concierge.capability_mesh import build_booking_mesh

    mesh = build_booking_mesh(booking, audience_session_id=audience_session_id)
    return {"ok": True, "nurture": stop, "mesh": mesh}


def orchestrate_after_support_case(
    *,
    workspace_id: str,
    guest_email: str | None,
    support_case_id: str,
    outreach_lead_id: str | None = None,
) -> dict[str, Any]:
    return pause_outreach_for_support_case(
        workspace_id=workspace_id,
        guest_email=guest_email,
        outreach_lead_id=outreach_lead_id,
        support_case_id=support_case_id,
    )


__all__ = [
    "apply_cancellation_policy",
    "no_show_recovery_gate",
    "orchestrate_after_booking_confirmed",
    "orchestrate_after_support_case",
    "pause_outreach_for_support_case",
    "stop_sales_cadence_on_booking",
    "update_funnel_outcome",
]
