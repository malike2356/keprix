"""Idempotent calendar reconciliation and repair (Prompt 633)."""

from __future__ import annotations

from typing import Any

from keprix.vical.calendar.delivery_state import booking_invitation_view, map_google_response
from keprix.vical.calendar.google_adapter import GoogleCalendarAdapter
from keprix.vical.calendar.projection_store import ProjectionStore, get_projection_store
from keprix.vical.calendar.types import CalendarAttendeeSnapshot


def apply_attendee_responses(
    *,
    workspace_id: str,
    booking_id: str,
    provider: str,
    attendees: list[dict[str, Any]],
    store: ProjectionStore | None = None,
) -> dict[str, Any]:
    """Update projection guest response; out-of-order safe (last write wins on response)."""
    proj = store or get_projection_store()
    mapped: list[dict[str, Any]] = []
    for a in attendees:
        email = str(a.get("email") or "").strip()
        if not email:
            continue
        if provider == "google":
            resp_s, del_s = map_google_response(a.get("responseStatus") or a.get("response"))
        else:
            from keprix.vical.calendar.delivery_state import map_microsoft_response

            resp_s, del_s = map_microsoft_response(a.get("responseStatus") or a.get("response"))
        snap = CalendarAttendeeSnapshot(email=email, response_status=resp_s, delivery_state=del_s)
        mapped.append(snap.to_dict())

    existing = proj.get_projection(workspace_id, booking_id, provider=provider)
    if not existing:
        return {"ok": False, "errorCode": "projection_missing", "invitation": booking_invitation_view(None)}

    invite_state = existing.get("invitationDeliveryState") or "unknown"
    if mapped:
        invite_state = mapped[0].get("deliveryState") or invite_state

    updated = proj.upsert_projection(
        workspace_id=workspace_id,
        user_id=str(existing.get("userId") or ""),
        booking_id=booking_id,
        provider=provider,
        provider_event_id=existing.get("providerEventId"),
        etag=existing.get("etag"),
        html_link=existing.get("htmlLink"),
        host_event_created=bool(existing.get("hostEventCreated")),
        invitation_send_requested=bool(existing.get("invitationSendRequested")),
        invitation_delivery_state=str(invite_state),
        attendees=mapped or existing.get("attendees"),
        workspace_event_id=existing.get("workspaceEventId"),
        ics_uid=existing.get("icsUid"),
        status=existing.get("status") or "succeeded",
    )
    proj.record_delivery_attempt(
        workspace_id=workspace_id,
        booking_id=booking_id,
        channel="guest_response_reconcile",
        provider=provider,
        status="reconciled",
        evidence=f"attendees:{len(mapped)}",
        detail={"attendees": mapped},
    )
    return {"ok": True, "projection": updated, "invitation": booking_invitation_view(updated)}


def repair_projection_from_provider(
    *,
    workspace_id: str,
    user_id: str,
    booking_id: str,
    provider: str = "google",
    google: GoogleCalendarAdapter | None = None,
    store: ProjectionStore | None = None,
) -> dict[str, Any]:
    """Incremental repair: re-fetch provider event and apply attendees."""
    proj = store or get_projection_store()
    existing = proj.get_projection(workspace_id, booking_id, provider=provider)
    if not existing or not existing.get("providerEventId"):
        return {"ok": False, "errorCode": "projection_missing"}
    if provider != "google":
        return {"ok": False, "errorCode": "repair_provider_unsupported"}
    adapter = google or GoogleCalendarAdapter()
    result = adapter.get_event(
        workspace_id=workspace_id,
        user_id=user_id,
        provider_event_id=str(existing["providerEventId"]),
    )
    if not result.ok:
        return {"ok": False, "errorCode": result.error_code, "result": result.to_public_dict()}
    return apply_attendee_responses(
        workspace_id=workspace_id,
        booking_id=booking_id,
        provider=provider,
        attendees=[a.to_dict() for a in result.attendees],
        store=proj,
    )


def compensate_calendar_delete(
    *,
    workspace_id: str,
    user_id: str,
    booking_id: str,
    google: GoogleCalendarAdapter | None = None,
    store: ProjectionStore | None = None,
) -> dict[str, Any]:
    """Best-effort cancel of host calendar event (idempotent)."""
    proj = store or get_projection_store()
    existing = proj.get_projection(workspace_id, booking_id)
    if not existing or not existing.get("providerEventId"):
        return {"ok": True, "skipped": True, "reason": "no_projection"}
    provider = existing.get("provider") or "ics"
    if provider == "ics":
        return {"ok": True, "skipped": True, "reason": "ics_local_only"}
    if provider == "google":
        adapter = google or GoogleCalendarAdapter()
        result = adapter.delete_event(
            workspace_id=workspace_id,
            user_id=user_id,
            booking_id=booking_id,
            provider_event_id=str(existing["providerEventId"]),
            idempotency_key=f"cal:delete:{booking_id}",
        )
        proj.record_delivery_attempt(
            workspace_id=workspace_id,
            booking_id=booking_id,
            channel="host_calendar_cancel",
            provider="google",
            status="succeeded" if result.ok else "failed",
            evidence=result.provider_event_id,
            detail=result.to_public_dict(),
        )
        return {"ok": result.ok, "result": result.to_public_dict()}
    return {"ok": True, "skipped": True, "reason": f"provider_{provider}"}
