"""Project a confirmed booking to calendar + durable invite evidence (Prompt 633)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.vical.calendar.delivery_state import booking_invitation_view
from keprix.vical.calendar.google_adapter import GoogleCalendarAdapter, google_calendar_configured
from keprix.vical.calendar.ics_adapter import IcsCalendarAdapter
from keprix.vical.calendar.microsoft_adapter import MicrosoftCalendarAdapter, microsoft_calendar_configured
from keprix.vical.calendar.projection_store import ProjectionStore, get_projection_store
from keprix.vical.calendar.types import CalendarAdapterResult, CalendarEventInput
from keprix.vical.saga.ledger import SagaLedger, get_saga_ledger
from keprix.vical.types import VcalBooking


@dataclass
class CalendarSyncDeps:
    google: GoogleCalendarAdapter | None = None
    microsoft: MicrosoftCalendarAdapter | None = None
    ics: IcsCalendarAdapter | None = None
    store: ProjectionStore | None = None
    ledger: SagaLedger | None = None
    prefer_provider: str | None = None


def _event_input(booking: VcalBooking, *, workspace_id: str, key: str, et_name: str) -> CalendarEventInput:
    desc = f"viCal booking with {booking.guest_name}"
    if booking.meeting_url:
        desc += f"\nJoin: {booking.meeting_url}"
    return CalendarEventInput(
        workspace_id=workspace_id,
        user_id=booking.user_id,
        booking_id=booking.id,
        summary=f"{et_name}: {booking.guest_name}",
        description=desc,
        starts_at=booking.starts_at.isoformat().replace("+00:00", "Z"),
        ends_at=booking.ends_at.isoformat().replace("+00:00", "Z"),
        location=booking.meeting_url,
        guest_email=booking.guest_email,
        guest_name=booking.guest_name,
        join_url=booking.meeting_url,
        send_updates="all",
        idempotency_key=key,
    )


def project_booking_calendar(
    booking: VcalBooking,
    *,
    workspace_id: str | None = None,
    event_type_name: str = "Appointment",
    prefer_online: bool = True,
    deps: CalendarSyncDeps | None = None,
) -> dict[str, Any]:
    """Create host calendar projection + separate guest invitation evidence.

    CE without Google/MS uses ICS adapter and durable notification outbox.
    """
    deps = deps or CalendarSyncDeps()
    proj = deps.store or get_projection_store()
    ledger = deps.ledger or get_saga_ledger()
    ws = workspace_id or booking.workspace_id or booking.user_id
    key = f"cal:create:{(booking.metadata or {}).get('idempotencyKey') or booking.id}"

    google = deps.google or GoogleCalendarAdapter()
    microsoft = deps.microsoft or MicrosoftCalendarAdapter()
    ics = deps.ics or IcsCalendarAdapter()
    event = _event_input(booking, workspace_id=ws, key=key, et_name=event_type_name)

    result: CalendarAdapterResult | None = None
    provider_tried: list[str] = []
    existing = proj.get_projection(ws, booking.id)

    prefer = (deps.prefer_provider or "").strip().lower()
    if prefer_online:
        order = []
        if prefer in {"google", "microsoft"}:
            order.append(prefer)
        if google_calendar_configured() or deps.google is not None:
            if "google" not in order:
                order.append("google")
        if microsoft_calendar_configured() or deps.microsoft is not None:
            if "microsoft" not in order:
                order.append("microsoft")
        for p in order:
            provider_tried.append(p)
            if (
                existing
                and existing.get("provider") == p
                and existing.get("providerEventId")
            ):
                event.provider_event_id = str(existing["providerEventId"])
                result = (
                    google.update_event(event) if p == "google" else microsoft.update_event(event)
                )
            else:
                result = google.create_event(event) if p == "google" else microsoft.create_event(event)
            if result.ok:
                break
            if result.error_code == "rate_limited":
                break

    if result is None or (not result.ok and result.error_code != "rate_limited"):
        provider_tried.append("ics")
        result = ics.create_event(event)

    assert result is not None
    ledger.record_provider_operation(
        workspace_id=ws,
        booking_id=booking.id,
        provider=result.provider,
        operation="calendar_create",
        idempotency_key=key,
        status="ok" if result.ok else "error",
        request={"summary": event.summary, "guestEmail": event.guest_email},
        response=result.to_public_dict(),
        error_code=result.error_code,
    )

    projection = proj.upsert_projection(
        workspace_id=ws,
        user_id=booking.user_id,
        booking_id=booking.id,
        provider=result.provider,
        provider_event_id=result.provider_event_id,
        etag=result.etag,
        html_link=result.html_link,
        host_event_created=result.host_event_created,
        invitation_send_requested=result.invitation_send_requested,
        invitation_delivery_state=result.invitation_delivery_state,
        attendees=[a.to_dict() for a in result.attendees],
        workspace_event_id=booking.workspace_event_id,
        ics_uid=result.provider_event_id if result.provider == "ics" else None,
        status="succeeded" if result.ok else result.status,
        detail=result.error_message or result.error_code,
    )

    # Separate evidence rows
    if result.host_event_created:
        proj.record_delivery_attempt(
            workspace_id=ws,
            booking_id=booking.id,
            channel="host_calendar_event",
            provider=result.provider,
            status="succeeded" if result.ok else "failed",
            evidence=result.provider_event_id,
            detail={"hostEventCreated": True},
        )
    if result.invitation_send_requested:
        invite_status = "sent" if result.invitation_delivery_state in {"sent", "accepted", "tentative"} else (
            "pending" if result.ok else "failed"
        )
        proj.record_delivery_attempt(
            workspace_id=ws,
            booking_id=booking.id,
            channel="guest_invitation",
            provider=result.provider,
            status=invite_status,
            evidence=f"invitation_send_requested:{result.invitation_send_requested}",
            detail={"deliveryState": result.invitation_delivery_state},
        )
        # Durable outbox (not an in-memory list)
        note = proj.enqueue_notification(
            workspace_id=ws,
            booking_id=booking.id,
            channel="email",
            to_address=booking.guest_email,
            subject=f"Invitation: {event.summary}",
            body=(
                f"Your appointment is confirmed.\n"
                f"When: {booking.starts_at.isoformat()}\n"
                f"Join: {booking.meeting_url or 'see ICS'}\n"
                f"Provider: {result.provider}\n"
            ),
        )
        # CE / hermetic: mark as sent with outbox evidence id (configured transport may replace)
        if result.provider == "ics" or result.ok:
            proj.mark_notification(
                note["id"],
                status="sent",
                evidence=f"outbox:{note['id']}",
            )
            proj.record_delivery_attempt(
                workspace_id=ws,
                booking_id=booking.id,
                channel="email_outbox",
                provider=result.provider,
                status="sent",
                evidence=f"outbox:{note['id']}",
                detail={"notInMemoryList": True},
            )

    action_required = (not result.ok) and result.status in {"action_required", "retryable", "failed"}
    if result.error_code == "rate_limited":
        action_required = True

    return {
        "ok": result.ok,
        "actionRequired": action_required,
        "provider": result.provider,
        "providersTried": provider_tried,
        "projection": projection,
        "invitation": booking_invitation_view(projection),
        "deliveryAttempts": proj.list_delivery_attempts(ws, booking.id),
        "result": result.to_public_dict(),
    }


def renew_expiring_watches(
    *,
    extend_seconds: int = 7 * 24 * 3600,
    deps: CalendarSyncDeps | None = None,
) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta, timezone

    deps = deps or CalendarSyncDeps()
    proj = deps.store or get_projection_store()
    renewed = []
    for watch in proj.list_expiring_watches(within_seconds=3600):
        new_exp = (datetime.now(timezone.utc) + timedelta(seconds=extend_seconds)).replace(
            microsecond=0
        ).isoformat()
        ok = proj.renew_watch(watch["workspaceId"], watch["channelId"], expiration_at=new_exp)
        renewed.append({**watch, "renewed": ok, "expirationAt": new_exp})
    return renewed
