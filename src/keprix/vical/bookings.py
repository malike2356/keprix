"""Booking lifecycle with workspace calendar bridge."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from keprix.vical.slots import SlotEngine
from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import ACTIVE_BOOKING_STATUSES, BookingSource, BookingStatus, VcalBooking


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class BookingLifecycleError(ValueError):
    pass


class BookingLifecycle:
    def __init__(
        self,
        *,
        store: VicalStore | None = None,
        slot_engine: SlotEngine | None = None,
        create_calendar_event: Callable[..., dict[str, Any]] | None = None,
        update_calendar_event: Callable[..., dict[str, Any]] | None = None,
        delete_calendar_event: Callable[..., None] | None = None,
    ) -> None:
        self.store = store or vical_store
        self.slots = slot_engine or SlotEngine(store=self.store)
        self._create_calendar_event = create_calendar_event
        self._update_calendar_event = update_calendar_event
        self._delete_calendar_event = delete_calendar_event

    def _cal_create(self, user_id: str, **fields: Any) -> dict[str, Any] | None:
        if self._create_calendar_event is not None:
            return self._create_calendar_event(user_id, **fields)
        try:
            from keprix.workspace.repository import workspace_repo

            return workspace_repo.create_event({"id": user_id, "username": user_id}, **fields)
        except Exception:
            return None

    def _cal_update(self, user_id: str, event_id: str, **fields: Any) -> None:
        if self._update_calendar_event is not None:
            self._update_calendar_event(user_id, event_id, **fields)
            return
        try:
            from keprix.workspace.repository import workspace_repo

            workspace_repo.update_event({"id": user_id, "username": user_id}, event_id, **fields)
        except Exception:
            return

    def _cal_delete(self, user_id: str, event_id: str) -> None:
        if self._delete_calendar_event is not None:
            self._delete_calendar_event(user_id, event_id)
            return
        try:
            from keprix.workspace.repository import workspace_repo

            workspace_repo.delete_event({"id": user_id, "username": user_id}, event_id)
        except Exception:
            return

    def _initial_status(self, *, requires_deposit: bool, requires_approval: bool) -> BookingStatus:
        if requires_deposit:
            return "pending_payment"
        if requires_approval:
            return "pending_review"
        return "confirmed"

    def create(
        self,
        user_id: str,
        *,
        event_type_id: str | None = None,
        slug: str | None = None,
        guest_name: str,
        guest_email: str,
        starts_at: datetime,
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
    ) -> VcalBooking:
        et = self.slots.resolve_event_type(user_id, event_type_id=event_type_id, slug=slug)
        starts_at = _aware(starts_at)
        ends_at = _aware(ends_at or (starts_at + timedelta(minutes=et.duration_minutes)))
        if ends_at <= starts_at:
            raise BookingLifecycleError("ends_at must be after starts_at")

        if not skip_slot_check:
            offered = self.slots.offer_slots(
                user_id,
                event_type_id=et.id,
                start=starts_at - timedelta(minutes=1),
                count=50,
            )
            if not any(s.start_at == starts_at and s.end_at == ends_at for s in offered):
                # also accept if start matches (duration from type)
                if not any(s.start_at == starts_at for s in offered):
                    raise BookingLifecycleError("requested slot is not available")

        if holder_token and lock_id:
            lock = self.store.slot_locks.get(lock_id)
            if (
                lock is None
                or lock.user_id != user_id
                or lock.holder_token != holder_token
                or lock.expires_at <= _now()
            ):
                raise BookingLifecycleError("slot lock missing or expired")
        elif not skip_slot_check:
            # best-effort lock for race
            try:
                lock = self.slots.acquire_lock(
                    user_id,
                    host_user_id=et.host_user_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    event_type_id=et.id,
                    holder_token=holder_token or secrets.token_urlsafe(12),
                )
                lock_id = lock.id
                holder_token = lock.holder_token
            except ValueError as exc:
                raise BookingLifecycleError(str(exc)) from exc

        status = self._initial_status(
            requires_deposit=et.requires_deposit,
            requires_approval=et.requires_approval,
        )
        booking = self.store.create_booking(
            user_id=user_id,
            event_type_id=et.id,
            host_user_id=et.host_user_id,
            guest_name=guest_name,
            guest_email=guest_email,
            starts_at=starts_at,
            ends_at=ends_at,
            status=status,
            source=source,
            meeting_url=meeting_url,
            intake_answers=intake_answers,
            notes=notes,
            contact_id=contact_id,
            metadata=metadata,
        )

        if status == "confirmed":
            from keprix.vical.conferencing import apply_meeting_url_on_confirm

            booking = apply_meeting_url_on_confirm(user_id, booking, store=self.store, explicit=meeting_url)
            self._bridge_create_calendar(user_id, booking, et.name)

        if lock_id and holder_token:
            self.store.release_slot_lock(user_id, lock_id, holder_token=holder_token)

        booking = self.store.get_booking(user_id, booking.id)
        self._emit_side_effects(booking, event=f"vical.booking.{booking.status}")
        return booking

    def _emit_side_effects(self, booking: VcalBooking, *, event: str, is_reschedule: bool = False) -> None:
        try:
            from keprix.vical.notifications import kind_for_status, notify_booking

            kind = kind_for_status(booking.status, is_reschedule=is_reschedule)
            if kind:
                notify_booking(kind, booking)
        except Exception:
            pass
        try:
            from keprix.vical.webhooks import dispatch_booking_webhook

            dispatch_booking_webhook(booking, event, store=self.store)
        except Exception:
            pass
        if event.endswith(".confirmed") or (
            event.startswith("vical.booking.") and booking.status == "confirmed" and not is_reschedule
        ):
            try:
                from keprix.workflows.conditions import execute_booking_confirmed_workflow

                execute_booking_confirmed_workflow(booking.to_dict())
            except Exception:
                pass
            try:
                from keprix.crm.booking import on_vical_booking_confirmed_crm

                on_vical_booking_confirmed_crm(booking)
            except Exception:
                try:
                    from keprix.outreach.vical_handoff import soft_wall_handoff_on_vical_confirmed

                    soft_wall_handoff_on_vical_confirmed(booking)
                except Exception:
                    pass

    def _bridge_create_calendar(self, user_id: str, booking: VcalBooking, title_prefix: str) -> None:
        from keprix.capability_mesh.ids import calendar_event_metadata_for_booking

        event = self._cal_create(
            booking.host_user_id,
            title=f"{title_prefix}: {booking.guest_name}",
            description=f"viCal booking {booking.id}\nGuest: {booking.guest_email}",
            start_at=booking.starts_at,
            end_at=booking.ends_at,
            location=booking.meeting_url or "",
            metadata=calendar_event_metadata_for_booking(booking),
        )
        if event and event.get("id"):
            self.store.update_booking(user_id, booking.id, workspace_event_id=str(event["id"]))

    def approve(self, user_id: str, booking_id: str) -> VcalBooking:
        booking = self.store.get_booking(user_id, booking_id)
        if booking.status not in {"pending_review", "pending_payment"}:
            raise BookingLifecycleError(f"cannot approve from status {booking.status}")
        if booking.status == "pending_payment":
            raise BookingLifecycleError("booking still pending payment")
        from keprix.vical.conferencing import apply_meeting_url_on_confirm

        updated = self.store.update_booking(user_id, booking_id, status="confirmed")
        updated = apply_meeting_url_on_confirm(user_id, updated, store=self.store)
        if not updated.workspace_event_id:
            et = self.store.get_event_type(user_id, updated.event_type_id)
            self._bridge_create_calendar(user_id, updated, et.name)
            updated = self.store.get_booking(user_id, booking_id)
        self._emit_side_effects(updated, event="vical.booking.confirmed")
        return updated

    def reject(self, user_id: str, booking_id: str, *, reason: str | None = None) -> VcalBooking:
        booking = self.store.get_booking(user_id, booking_id)
        if booking.status not in {"pending_review", "pending_payment", "confirmed"}:
            raise BookingLifecycleError(f"cannot reject from status {booking.status}")
        meta = dict(booking.cancel_reschedule)
        if reason:
            meta["reject_reason"] = reason
        if booking.workspace_event_id:
            self._cal_delete(booking.host_user_id, booking.workspace_event_id)
        updated = self.store.update_booking(
            user_id,
            booking_id,
            status="rejected",
            workspace_event_id=None,
            cancel_reschedule=meta,
        )
        self._emit_side_effects(updated, event="vical.booking.rejected")
        return updated

    def cancel(self, user_id: str, booking_id: str, *, reason: str | None = None) -> VcalBooking:
        booking = self.store.get_booking(user_id, booking_id)
        if booking.status in {"cancelled", "rejected"}:
            return booking
        if booking.status not in ACTIVE_BOOKING_STATUSES:
            raise BookingLifecycleError(f"cannot cancel from status {booking.status}")
        meta = dict(booking.cancel_reschedule)
        if reason:
            meta["cancel_reason"] = reason
        meta["cancelled_at"] = _now().isoformat()
        if booking.workspace_event_id:
            self._cal_delete(booking.host_user_id, booking.workspace_event_id)
        updated = self.store.update_booking(
            user_id,
            booking_id,
            status="cancelled",
            workspace_event_id=None,
            cancel_reschedule=meta,
        )
        self._emit_side_effects(updated, event="vical.booking.cancelled")
        return updated

    def cancel_by_guest_token(self, guest_token: str, *, reason: str | None = None) -> VcalBooking:
        booking = self.store.get_booking_by_guest_token(guest_token)
        if booking is None:
            raise BookingLifecycleError("booking not found")
        return self.cancel(booking.user_id, booking.id, reason=reason)

    def reschedule(
        self,
        user_id: str,
        booking_id: str,
        *,
        starts_at: datetime,
        ends_at: datetime | None = None,
    ) -> VcalBooking:
        booking = self.store.get_booking(user_id, booking_id)
        if booking.status not in ACTIVE_BOOKING_STATUSES:
            raise BookingLifecycleError(f"cannot reschedule from status {booking.status}")
        et = self.store.get_event_type(user_id, booking.event_type_id)
        starts_at = _aware(starts_at)
        ends_at = _aware(ends_at or (starts_at + timedelta(minutes=et.duration_minutes)))

        # Conflict check: other active bookings (exclude self) + other calendar events
        overlapping = [
            b
            for b in self.store.list_active_bookings_for_host(
                user_id,
                booking.host_user_id,
                start=starts_at,
                end=ends_at,
            )
            if b.id != booking.id and starts_at < b.ends_at and ends_at > b.starts_at
        ]
        if overlapping:
            raise BookingLifecycleError("requested slot is not available")

        try:
            from keprix.workspace.repository import workspace_repo

            for event in workspace_repo.list_events(
                {"id": booking.host_user_id},
                start=starts_at,
                end=ends_at,
            ):
                if str(event.get("id")) == str(booking.workspace_event_id or ""):
                    continue
                ev_start = event["start_at"]
                ev_end = event["end_at"]
                if isinstance(ev_start, str):
                    ev_start = datetime.fromisoformat(ev_start.replace("Z", "+00:00"))
                if isinstance(ev_end, str):
                    ev_end = datetime.fromisoformat(ev_end.replace("Z", "+00:00"))
                if starts_at < _aware(ev_end) and ends_at > _aware(ev_start):
                    raise BookingLifecycleError("requested slot is not available")
        except BookingLifecycleError:
            raise
        except Exception:
            pass

        meta = dict(booking.cancel_reschedule)
        meta["previous_starts_at"] = booking.starts_at.isoformat()
        meta["previous_ends_at"] = booking.ends_at.isoformat()
        updated = self.store.update_booking(
            user_id,
            booking_id,
            starts_at=starts_at,
            ends_at=ends_at,
            cancel_reschedule=meta,
        )
        if updated.workspace_event_id:
            self._cal_update(
                updated.host_user_id,
                updated.workspace_event_id,
                start_at=starts_at,
                end_at=ends_at,
                title=f"{et.name}: {updated.guest_name}",
            )
        elif updated.status == "confirmed":
            self._bridge_create_calendar(user_id, updated, et.name)
            updated = self.store.get_booking(user_id, booking_id)
        self._emit_side_effects(updated, event="vical.booking.rescheduled", is_reschedule=True)
        return updated

    def mark_outcome(self, user_id: str, booking_id: str, outcome: str) -> VcalBooking:
        if outcome not in {"attended", "no_show"}:
            raise BookingLifecycleError("outcome must be attended or no_show")
        booking = self.store.get_booking(user_id, booking_id)
        if booking.status != "confirmed":
            raise BookingLifecycleError("only confirmed bookings can set outcome")
        return self.store.update_booking(user_id, booking_id, session_outcome=outcome)
