"""viCal Soft Wall booking source-of-truth handoff."""

from __future__ import annotations

from typing import Any


def soft_wall_handoff_on_vical_confirmed(booking: Any) -> dict[str, Any]:
    """When a viCal booking is confirmed, update Soft Wall (+ CRM if present).

    Prefer viCal as SoT: Soft Wall booking rows are linked via metadata
    `vical_booking_id` rather than inventing a second calendar.
    Callers that need full CRM deal/inbox mesh should use
    ``keprix.crm.booking.on_vical_booking_confirmed_crm``.
    """
    meta = dict(getattr(booking, "metadata", None) or {})
    if isinstance(booking, dict):
        meta = dict(booking.get("metadata") or {})
        booking_id = str(booking.get("id") or "")
        guest_email = str(booking.get("guest_email") or "").strip().lower()
        starts_at = str(booking.get("starts_at") or "")
        ends_at = booking.get("ends_at")
        status = str(booking.get("status") or "")
    else:
        booking_id = str(booking.id)
        guest_email = str(booking.guest_email or "").strip().lower()
        starts_at = booking.starts_at.isoformat() if getattr(booking, "starts_at", None) else ""
        ends_at = booking.ends_at.isoformat() if getattr(booking, "ends_at", None) else None
        status = str(booking.status)

    if status != "confirmed":
        return {"ok": False, "reason": "not_confirmed"}

    workspace_id = str(meta.get("workspace_id") or meta.get("outreach_workspace_id") or "default")
    lead_id = meta.get("outreach_lead_id") or meta.get("lead_id")
    crm_lead_id = meta.get("crm_lead_id")

    result: dict[str, Any] = {
        "ok": True,
        "vical_booking_id": booking_id,
        "workspace_id": workspace_id,
        "outreach_lead_id": lead_id,
        "crm_lead_id": crm_lead_id,
        "mesh": {
            "vical": f"/vical?booking={booking_id}",
            "outreach_bookings": "/outreach/bookings",
            "outreach_lead": f"/outreach/leads/{lead_id}" if lead_id else None,
            "crm": f"/crm/leads/{crm_lead_id}" if crm_lead_id else "/crm",
            "calendar": "/calendar",
        },
    }

    try:
        from keprix.outreach.ops import get_outreach_ops_store
        from keprix.outreach.store import get_outreach_store

        ostore = get_outreach_store()
        ops = get_outreach_ops_store()

        if not lead_id and guest_email:
            # Best-effort match Soft Wall lead by email
            try:
                leads = ostore.list_leads(workspace_id, limit=500)
                match = next(
                    (l for l in leads if str(l.get("email") or "").strip().lower() == guest_email),
                    None,
                )
                if match:
                    lead_id = match["id"]
                    result["outreach_lead_id"] = lead_id
                    result["mesh"]["outreach_lead"] = f"/outreach/leads/{lead_id}"
            except Exception:
                pass

        if lead_id:
            try:
                ostore.update_lead_status(workspace_id, str(lead_id), "booked")
            except Exception:
                try:
                    with ostore._lock:  # noqa: SLF001
                        ostore._conn.execute(
                            "UPDATE outreach_leads SET status = ? WHERE id = ? AND workspace_id = ?",
                            ("booked", str(lead_id), workspace_id),
                        )
                        ostore._conn.commit()
                except Exception:
                    pass

            # Link Soft Wall booking row (idempotent by notes/metadata pattern)
            try:
                existing = [
                    b
                    for b in ops.list_bookings(workspace_id)
                    if str(b.get("notes") or "").find(f"vical:{booking_id}") >= 0
                    or str(b.get("id")) == str(meta.get("outreach_booking_id") or "")
                ]
                if existing:
                    ops.update_booking_status(workspace_id, existing[0]["id"], "confirmed")
                    result["outreach_booking_id"] = existing[0]["id"]
                else:
                    row = ops.create_booking(
                        workspace_id,
                        str(lead_id),
                        starts_at,
                        ends_at=ends_at,
                        status="confirmed",
                        notes=f"vical:{booking_id} Soft Wall linked (viCal SoT)",
                    )
                    result["outreach_booking_id"] = row.get("id")
            except Exception as exc:
                result["outreach_booking_error"] = str(exc)
    except Exception as exc:
        result["outreach_error"] = str(exc)

    # CRM stage booked when CRM store available
    try:
        from keprix.crm.store import get_crm_store

        cstore = get_crm_store()
        target = str(crm_lead_id or lead_id or "")
        if target:
            lead = cstore.get_lead(workspace_id, target)
            if lead:
                cstore.update_lead(workspace_id, target, stage="booked")
                cstore.create_activity(
                    workspace_id,
                    entity_type="lead",
                    entity_id=target,
                    activity_type="booking_confirmed",
                    channel="vical",
                    subject=f"viCal booking {booking_id} confirmed",
                    body=f"guest={guest_email}",
                )
                result["crm_updated"] = True
    except Exception as exc:
        result["crm_error"] = str(exc)

    return result
