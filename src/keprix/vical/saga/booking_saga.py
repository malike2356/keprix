"""Canonical provider-neutral booking saga (Prompt 632)."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
from keprix.vical.conferencing.redact import to_public_booking_view
from keprix.vical.conferencing.static_url_adapter import StaticUrlConferencingAdapter
from keprix.vical.conferencing.types import ConferenceCreateInput, ConferenceDeleteInput
from keprix.vical.conferencing.zoom_adapter import ZoomConferencingAdapter
from keprix.vical.saga.ledger import SagaLedger, get_saga_ledger
from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import BookingSource, VcalBooking


@dataclass
class SagaDeps:
    zoom_adapter: ZoomConferencingAdapter | None = None
    static_adapter: StaticUrlConferencingAdapter | None = None
    ledger: SagaLedger | None = None
    store: VicalStore | None = None
    lifecycle: BookingLifecycle | None = None
    calendar_deps: Any | None = None
    skip_calendar: bool = False


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def default_idempotency_key(
    *,
    workspace_id: str,
    event_type_id: str,
    guest_email: str,
    starts_at: datetime,
) -> str:
    material = "|".join(
        [
            workspace_id,
            event_type_id,
            guest_email.strip().lower(),
            _aware(starts_at).isoformat(),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"vical:{digest}"


def book_with_saga(
    user_id: str,
    *,
    guest_name: str,
    guest_email: str,
    starts_at: datetime,
    event_type_id: str | None = None,
    slug: str | None = None,
    ends_at: datetime | None = None,
    source: BookingSource = "api",
    notes: str | None = None,
    meeting_url: str | None = None,
    intake_answers: dict[str, Any] | None = None,
    contact_id: str | None = None,
    holder_token: str | None = None,
    lock_id: str | None = None,
    skip_slot_check: bool = False,
    metadata: dict[str, Any] | None = None,
    workspace_id: str | None = None,
    persona_id: str | None = None,
    idempotency_key: str | None = None,
    prefer_managed_zoom: bool = True,
    static_room_url: str | None = None,
    deps: SagaDeps | None = None,
) -> dict[str, Any]:
    deps = deps or SagaDeps()
    store = deps.store or vical_store
    life = deps.lifecycle or BookingLifecycle(store=store)
    ledger = deps.ledger or get_saga_ledger()
    zoom = deps.zoom_adapter or ZoomConferencingAdapter()
    static = deps.static_adapter or StaticUrlConferencingAdapter(
        default_url=static_room_url or meeting_url
    )

    et = life.slots.resolve_event_type(user_id, event_type_id=event_type_id, slug=slug)
    starts_at = _aware(starts_at)
    ends_at = _aware(ends_at or (starts_at + timedelta(minutes=et.duration_minutes)))
    ws = (workspace_id or getattr(et, "workspace_id", None) or user_id).strip() or user_id
    key = (idempotency_key or "").strip() or default_idempotency_key(
        workspace_id=ws,
        event_type_id=et.id,
        guest_email=guest_email,
        starts_at=starts_at,
    )

    existing_intent = ledger.find_booking_by_idempotency(ws, key)
    if existing_intent and existing_intent.get("bookingId"):
        booking = store.get_booking(user_id, str(existing_intent["bookingId"]))
        if booking:
            ops = ledger.list_provider_operations(ws, booking.id)
            return {
                "booking": booking,
                "publicBooking": to_public_booking_view(booking.to_dict()),
                "duplicate": True,
                "conferenceManaged": bool(
                    (booking.metadata or {}).get("conferenceManaged")
                ),
                "providerOperations": ops,
                "actionRequired": booking.status == "pending_review"
                or bool((booking.metadata or {}).get("action_required")),
            }

    hold_token = holder_token or secrets.token_urlsafe(12)
    hold = ledger.create_hold(
        workspace_id=ws,
        user_id=user_id,
        event_type_id=et.id,
        starts_at=starts_at.isoformat(),
        ends_at=ends_at.isoformat(),
        holder_token=hold_token,
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )
    ledger.upsert_intent(
        workspace_id=ws,
        user_id=user_id,
        idempotency_key=key,
        guest_email=guest_email,
        starts_at=starts_at.isoformat(),
        payload={"guestName": guest_name, "eventTypeId": et.id},
        status="open",
    )

    meta = dict(metadata or {})
    meta["idempotencyKey"] = key
    meta["saga"] = True

    try:
        booking = life.create(
            user_id,
            event_type_id=et.id,
            guest_name=guest_name,
            guest_email=guest_email,
            starts_at=starts_at,
            ends_at=ends_at,
            source=source,
            notes=notes,
            meeting_url=meeting_url,
            intake_answers=intake_answers,
            contact_id=contact_id,
            holder_token=holder_token,
            lock_id=lock_id,
            skip_slot_check=skip_slot_check,
            metadata=meta,
        )
    except BookingLifecycleError:
        ledger.release_hold(ws, hold["id"])
        raise

    ledger.commit_intent(ws, key, booking.id)
    ledger.add_participants(
        workspace_id=ws,
        booking_id=booking.id,
        participants=[
            {"role": "guest", "email": guest_email, "displayName": guest_name},
            {"role": "host", "email": None, "displayName": et.host_user_id},
        ],
    )

    conference_managed = False
    action_required = False
    location_wants_zoom = prefer_managed_zoom and (
        str(getattr(et, "location_mode", "") or "") in {"video", "zoom"}
        or bool(meta.get("preferManagedZoom", True))
    )

    if booking.status == "confirmed" and location_wants_zoom:
        conf_key = f"zoom:create:{key}"
        create_input = ConferenceCreateInput(
            workspace_id=ws,
            user_id=user_id,
            persona_id=persona_id,
            topic=f"{et.name}: {guest_name}"[:200],
            starts_at=starts_at.isoformat().replace("+00:00", "Z"),
            duration_minutes=max(
                15, int((ends_at - starts_at).total_seconds() // 60) or et.duration_minutes
            ),
            timezone="UTC",
            idempotency_key=conf_key,
        )
        zoom_result = zoom.create_meeting(create_input)
        ledger.record_provider_operation(
            workspace_id=ws,
            booking_id=booking.id,
            provider="zoom",
            operation="create_meeting",
            idempotency_key=conf_key,
            status="ok" if zoom_result.ok else "error",
            request={"topic": create_input.topic, "startsAt": create_input.starts_at},
            response=zoom_result.to_public_dict(),
            error_code=zoom_result.error_code,
        )

        if zoom_result.ok and zoom_result.join_url:
            conference_managed = True
            ledger.upsert_conference_artifact(
                workspace_id=ws,
                booking_id=booking.id,
                provider="zoom",
                status=zoom_result.status,
                meeting_id=zoom_result.meeting_id,
                join_url=zoom_result.join_url,
                host_start_url=zoom_result.host_start_url,
                passcode=zoom_result.passcode,
                managed=True,
            )
            booking = store.update_booking(
                user_id,
                booking.id,
                meeting_url=zoom_result.join_url,
                metadata={
                    **(booking.metadata or {}),
                    "conferenceManaged": True,
                    "conferenceProvider": "zoom",
                    "zoomMeetingId": zoom_result.meeting_id,
                    # never persist host start URL on booking metadata
                },
            )
        else:
            # Compensation / labelled fallback; do not fake managed Zoom
            static_result = static.create_meeting(create_input)
            ledger.record_provider_operation(
                workspace_id=ws,
                booking_id=booking.id,
                provider="static_url",
                operation="create_meeting",
                idempotency_key=f"static:create:{key}",
                status="ok" if static_result.ok else "error",
                response=static_result.to_public_dict(),
                error_code=zoom_result.error_code,
            )
            if static_result.join_url:
                ledger.upsert_conference_artifact(
                    workspace_id=ws,
                    booking_id=booking.id,
                    provider="static_url",
                    status=static_result.status,
                    meeting_id=static_result.meeting_id,
                    join_url=static_result.join_url,
                    managed=False,
                    detail=static_result.detail,
                )
                booking = store.update_booking(
                    user_id,
                    booking.id,
                    meeting_url=static_result.join_url,
                    metadata={
                        **(booking.metadata or {}),
                        "conferenceManaged": False,
                        "conferenceProvider": "static_url",
                        "staticRoomUrlFallback": True,
                        "zoomError": zoom_result.error_code,
                    },
                )
            elif zoom_result.error_code in {"rate_limited", "expired_token", "api_error"}:
                action_required = True
                booking = store.update_booking(
                    user_id,
                    booking.id,
                    metadata={
                        **(booking.metadata or {}),
                        "action_required": True,
                        "actionRequiredReason": zoom_result.error_code,
                        "conferenceManaged": False,
                    },
                )
    elif booking.status == "confirmed" and meeting_url:
        # Explicit URL: labelled unmanaged
        ledger.upsert_conference_artifact(
            workspace_id=ws,
            booking_id=booking.id,
            provider="static_url",
            status="created",
            join_url=meeting_url,
            managed=False,
            detail="explicit_meeting_url",
        )

    calendar_projection: dict[str, Any] | None = None
    if booking.status == "confirmed" and not deps.skip_calendar:
        from keprix.vical.calendar.sync_booking import CalendarSyncDeps, project_booking_calendar

        cal_deps = deps.calendar_deps
        if cal_deps is None:
            cal_deps = CalendarSyncDeps(ledger=ledger)
        elif getattr(cal_deps, "ledger", None) is None:
            cal_deps.ledger = ledger
        calendar_projection = project_booking_calendar(
            booking,
            workspace_id=ws,
            event_type_name=et.name,
            deps=cal_deps,
        )
        if calendar_projection.get("actionRequired"):
            action_required = True
            booking = store.update_booking(
                user_id,
                booking.id,
                metadata={
                    **(booking.metadata or {}),
                    "action_required": True,
                    "actionRequiredReason": (
                        (calendar_projection.get("result") or {}).get("errorCode")
                        or "calendar_projection"
                    ),
                    "calendarProvider": calendar_projection.get("provider"),
                },
            )
        else:
            booking = store.update_booking(
                user_id,
                booking.id,
                metadata={
                    **(booking.metadata or {}),
                    "calendarProvider": calendar_projection.get("provider"),
                    "calendarProjectionId": (calendar_projection.get("projection") or {}).get("id"),
                },
            )

    ledger.release_hold(ws, hold["id"])
    booking = store.get_booking(user_id, booking.id) or booking
    ops = ledger.list_provider_operations(ws, booking.id)
    return {
        "booking": booking,
        "publicBooking": to_public_booking_view(booking.to_dict()),
        "duplicate": False,
        "conferenceManaged": conference_managed
        or bool((booking.metadata or {}).get("conferenceManaged")),
        "providerOperations": ops,
        "actionRequired": action_required
        or bool((booking.metadata or {}).get("action_required")),
        "calendar": calendar_projection,
        "invitation": (calendar_projection or {}).get("invitation"),
    }


def cancel_with_saga(
    user_id: str,
    booking_id: str,
    *,
    workspace_id: str | None = None,
    reason: str | None = None,
    deps: SagaDeps | None = None,
) -> dict[str, Any]:
    deps = deps or SagaDeps()
    store = deps.store or vical_store
    life = deps.lifecycle or BookingLifecycle(store=store)
    ledger = deps.ledger or get_saga_ledger()
    zoom = deps.zoom_adapter or ZoomConferencingAdapter()
    booking = store.get_booking(user_id, booking_id)
    if not booking:
        raise BookingLifecycleError("booking not found")
    ws = workspace_id or user_id
    artifact = ledger.get_conference_artifact(ws, booking_id, provider="zoom")
    if artifact and artifact.get("meetingId") and artifact.get("managed"):
        del_key = f"zoom:delete:{booking_id}"
        result = zoom.delete_meeting(
            ConferenceDeleteInput(
                workspace_id=ws,
                user_id=user_id,
                meeting_id=str(artifact["meetingId"]),
                idempotency_key=del_key,
            )
        )
        ledger.record_provider_operation(
            workspace_id=ws,
            booking_id=booking_id,
            provider="zoom",
            operation="delete_meeting",
            idempotency_key=del_key,
            status="ok" if result.ok else "error",
            response=result.to_public_dict(),
            error_code=result.error_code,
        )
    calendar_cancel: dict[str, Any] | None = None
    if not deps.skip_calendar:
        from keprix.vical.calendar.reconcile import compensate_calendar_delete

        google = None
        if deps.calendar_deps is not None:
            google = getattr(deps.calendar_deps, "google", None)
        calendar_cancel = compensate_calendar_delete(
            workspace_id=ws,
            user_id=user_id,
            booking_id=booking_id,
            google=google,
        )
    cancelled = life.cancel(user_id, booking_id)
    nurture = None
    try:
        from keprix.customer_concierge.nurture_orchestration import apply_cancellation_policy

        nurture = apply_cancellation_policy(cancelled)
    except Exception:
        nurture = None
    return {
        "booking": cancelled,
        "publicBooking": to_public_booking_view(cancelled.to_dict()),
        "reason": reason,
        "calendar": calendar_cancel,
        "nurture": nurture,
    }


def reschedule_with_saga(
    user_id: str,
    booking_id: str,
    *,
    starts_at: datetime,
    ends_at: datetime | None = None,
    workspace_id: str | None = None,
    deps: SagaDeps | None = None,
) -> dict[str, Any]:
    deps = deps or SagaDeps()
    store = deps.store or vical_store
    life = deps.lifecycle or BookingLifecycle(store=store)
    ledger = deps.ledger or get_saga_ledger()
    zoom = deps.zoom_adapter or ZoomConferencingAdapter()
    booking = life.reschedule(user_id, booking_id, starts_at=starts_at, ends_at=ends_at)
    ws = workspace_id or user_id
    artifact = ledger.get_conference_artifact(ws, booking_id, provider="zoom")
    if artifact and artifact.get("meetingId") and artifact.get("managed"):
        from keprix.vical.conferencing.types import ConferenceUpdateInput

        duration = max(
            15,
            int((_aware(booking.ends_at) - _aware(booking.starts_at)).total_seconds() // 60),
        )
        upd_key = f"zoom:update:{booking_id}:{_aware(starts_at).isoformat()}"
        result = zoom.update_meeting(
            ConferenceUpdateInput(
                workspace_id=ws,
                user_id=user_id,
                meeting_id=str(artifact["meetingId"]),
                starts_at=_aware(starts_at).isoformat().replace("+00:00", "Z"),
                duration_minutes=duration,
                idempotency_key=upd_key,
            )
        )
        ledger.record_provider_operation(
            workspace_id=ws,
            booking_id=booking_id,
            provider="zoom",
            operation="update_meeting",
            idempotency_key=upd_key,
            status="ok" if result.ok else "error",
            response=result.to_public_dict(),
            error_code=result.error_code,
        )
    calendar_projection: dict[str, Any] | None = None
    if not deps.skip_calendar:
        from keprix.vical.calendar.sync_booking import CalendarSyncDeps, project_booking_calendar

        cal_deps = deps.calendar_deps or CalendarSyncDeps(ledger=ledger)
        if getattr(cal_deps, "ledger", None) is None:
            cal_deps.ledger = ledger
        # Re-project (update path via create_event idempotency / ICS rewrite)
        calendar_projection = project_booking_calendar(
            booking,
            workspace_id=ws,
            deps=cal_deps,
        )
    return {
        "booking": booking,
        "publicBooking": to_public_booking_view(booking.to_dict()),
        "calendar": calendar_projection,
        "invitation": (calendar_projection or {}).get("invitation"),
    }


__all__ = [
    "SagaDeps",
    "book_with_saga",
    "cancel_with_saga",
    "default_idempotency_key",
    "reschedule_with_saga",
]
