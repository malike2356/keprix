"""JSON-backed viCal store (calendar_store pattern)."""

from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.vical.types import (
    ACTIVE_BOOKING_STATUSES,
    BookingSource,
    BookingStatus,
    LocationMode,
    SessionOutcome,
    VcalAvailabilityRule,
    VcalBlackoutDate,
    VcalBooking,
    VcalEventType,
    VcalSlotLock,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _data_root() -> Path:
    try:
        from keprix.auth.config import data_dir

        return Path(data_dir())
    except Exception:
        return Path(os.environ.get("KEPRIX_DATA_DIR") or Path.home() / ".keprix")


def vical_store_path() -> Path:
    path = _data_root() / "workspace" / "vical_store.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Not serializable: {type(value)}")


class IsolationError(LookupError):
    """Raised when a row is missing or owned by another user."""


class VicalStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._lock = threading.RLock()
        self.event_types: dict[str, VcalEventType] = {}
        self.availability_rules: dict[str, VcalAvailabilityRule] = {}
        self.blackout_dates: dict[str, VcalBlackoutDate] = {}
        self.bookings: dict[str, VcalBooking] = {}
        self.slot_locks: dict[str, VcalSlotLock] = {}
        self.host_profiles: dict[str, dict] = {}
        self.intake_pools: dict[str, dict] = {}
        self._guest_token_index: dict[str, str] = {}
        self._public_slug_index: dict[str, str] = {}
        self._load()

    def _store_path(self) -> Path:
        return self._path or vical_store_path()

    def clear(self) -> None:
        with self._lock:
            self.event_types.clear()
            self.availability_rules.clear()
            self.blackout_dates.clear()
            self.bookings.clear()
            self.slot_locks.clear()
            self.host_profiles.clear()
            self.intake_pools.clear()
            self._guest_token_index.clear()
            self._public_slug_index.clear()
            self._persist()

    def _load(self) -> None:
        path = self._store_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        for row in (payload.get("event_types") or {}).values():
            et = self._event_type_from_dict(row)
            self.event_types[et.id] = et
        for row in (payload.get("availability_rules") or {}).values():
            rule = self._rule_from_dict(row)
            self.availability_rules[rule.id] = rule
        for row in (payload.get("blackout_dates") or {}).values():
            bo = self._blackout_from_dict(row)
            self.blackout_dates[bo.id] = bo
        for row in (payload.get("bookings") or {}).values():
            booking = self._booking_from_dict(row)
            self.bookings[booking.id] = booking
            self._guest_token_index[booking.guest_token] = booking.id
        for row in (payload.get("slot_locks") or {}).values():
            lock = self._lock_from_dict(row)
            self.slot_locks[lock.id] = lock
        for user_id, profile in (payload.get("host_profiles") or {}).items():
            row = dict(profile)
            row["user_id"] = str(user_id)
            self.host_profiles[str(user_id)] = row
            slug = str(row.get("public_slug") or "").strip().lower()
            if slug:
                self._public_slug_index[slug] = str(user_id)
        for pool_id, pool in (payload.get("intake_pools") or {}).items():
            self.intake_pools[str(pool_id)] = dict(pool)

    def _persist(self) -> None:
        path = self._store_path()
        payload = {
            "event_types": {k: v.to_dict() for k, v in self.event_types.items()},
            "availability_rules": {k: v.to_dict() for k, v in self.availability_rules.items()},
            "blackout_dates": {k: v.to_dict() for k, v in self.blackout_dates.items()},
            "bookings": {k: v.to_dict() for k, v in self.bookings.items()},
            "slot_locks": {k: v.to_dict() for k, v in self.slot_locks.items()},
            "host_profiles": self.host_profiles,
            "intake_pools": self.intake_pools,
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
        tmp.replace(path)

    def _event_type_from_dict(self, row: dict[str, Any]) -> VcalEventType:
        return VcalEventType(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            host_user_id=str(row.get("host_user_id") or row["user_id"]),
            slug=str(row["slug"]),
            name=str(row["name"]),
            duration_minutes=int(row.get("duration_minutes") or 30),
            buffer_before_minutes=int(row.get("buffer_before_minutes") or 0),
            buffer_after_minutes=int(row.get("buffer_after_minutes") or 0),
            min_notice_minutes=int(row.get("min_notice_minutes") or 120),
            horizon_days=int(row.get("horizon_days") or 30),
            location_mode=str(row.get("location_mode") or "unspecified"),  # type: ignore[arg-type]
            requires_approval=bool(row.get("requires_approval")),
            requires_deposit=bool(row.get("requires_deposit")),
            deposit_minor=row.get("deposit_minor"),
            deposit_currency=row.get("deposit_currency"),
            intake_pool_id=row.get("intake_pool_id"),
            active=bool(row.get("active", True)),
            metadata=dict(row.get("metadata") or {}),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
            workspace_id=row.get("workspace_id"),
            tenant_id=row.get("tenant_id"),
        )

    def _rule_from_dict(self, row: dict[str, Any]) -> VcalAvailabilityRule:
        return VcalAvailabilityRule(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            host_user_id=str(row.get("host_user_id") or row["user_id"]),
            day_of_week=int(row["day_of_week"]),
            start_time=str(row["start_time"]),
            end_time=str(row["end_time"]),
            timezone=str(row.get("timezone") or "UTC"),
            event_type_id=row.get("event_type_id"),
            active=bool(row.get("active", True)),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
            workspace_id=row.get("workspace_id"),
        )

    def _blackout_from_dict(self, row: dict[str, Any]) -> VcalBlackoutDate:
        starts = _parse_date(row.get("starts_on"))
        ends = _parse_date(row.get("ends_on"))
        if starts is None or ends is None:
            raise ValueError("blackout requires starts_on and ends_on")
        return VcalBlackoutDate(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            starts_on=starts,
            ends_on=ends,
            host_user_id=row.get("host_user_id"),
            reason=row.get("reason"),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
            workspace_id=row.get("workspace_id"),
        )

    def _booking_from_dict(self, row: dict[str, Any]) -> VcalBooking:
        starts = _parse_dt(row.get("starts_at"))
        ends = _parse_dt(row.get("ends_at"))
        if starts is None or ends is None:
            raise ValueError("booking requires starts_at and ends_at")
        return VcalBooking(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            event_type_id=str(row["event_type_id"]),
            host_user_id=str(row["host_user_id"]),
            guest_name=str(row["guest_name"]),
            guest_email=str(row["guest_email"]),
            starts_at=starts,
            ends_at=ends,
            status=str(row.get("status") or "confirmed"),  # type: ignore[arg-type]
            guest_token=str(row["guest_token"]),
            source=str(row.get("source") or "api"),  # type: ignore[arg-type]
            meeting_url=row.get("meeting_url"),
            workspace_event_id=row.get("workspace_event_id"),
            intake_answers=dict(row.get("intake_answers") or {}),
            notes=row.get("notes"),
            session_outcome=row.get("session_outcome"),
            cancel_reschedule=dict(row.get("cancel_reschedule") or {}),
            contact_id=row.get("contact_id"),
            metadata=dict(row.get("metadata") or {}),
            created_at=_parse_dt(row.get("created_at")),
            updated_at=_parse_dt(row.get("updated_at")),
            workspace_id=row.get("workspace_id"),
            tenant_id=row.get("tenant_id"),
        )

    def _lock_from_dict(self, row: dict[str, Any]) -> VcalSlotLock:
        starts = _parse_dt(row.get("starts_at"))
        ends = _parse_dt(row.get("ends_at"))
        expires = _parse_dt(row.get("expires_at"))
        if starts is None or ends is None or expires is None:
            raise ValueError("lock requires starts_at, ends_at, expires_at")
        return VcalSlotLock(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            host_user_id=str(row["host_user_id"]),
            starts_at=starts,
            ends_at=ends,
            holder_token=str(row["holder_token"]),
            expires_at=expires,
            event_type_id=row.get("event_type_id"),
            workspace_id=row.get("workspace_id"),
            created_at=_parse_dt(row.get("created_at")),
        )

    def _assert_tenant(self, resource: Any) -> None:
        from keprix.tenancy.isolation import TenantIsolationError, assert_tenant_owns

        try:
            assert_tenant_owns(resource)
        except TenantIsolationError as exc:
            raise IsolationError(str(exc)) from exc

    def _current_tenant(self) -> str | None:
        try:
            from keprix.tenancy.isolation import current_tenant_id

            return current_tenant_id()
        except Exception:
            return None

    def _owned_event_type(self, user_id: str, event_type_id: str) -> VcalEventType:
        et = self.event_types.get(event_type_id)
        if et is None or et.user_id != user_id:
            raise IsolationError(f"event type not found: {event_type_id}")
        self._assert_tenant(et)
        return et

    def _owned_booking(self, user_id: str, booking_id: str) -> VcalBooking:
        booking = self.bookings.get(booking_id)
        if booking is None or booking.user_id != user_id:
            raise IsolationError(f"booking not found: {booking_id}")
        self._assert_tenant(booking)
        return booking

    def create_event_type(
        self,
        *,
        user_id: str,
        slug: str,
        name: str,
        host_user_id: str | None = None,
        duration_minutes: int = 30,
        buffer_before_minutes: int = 0,
        buffer_after_minutes: int = 0,
        min_notice_minutes: int = 120,
        horizon_days: int = 30,
        location_mode: LocationMode = "unspecified",
        requires_approval: bool = False,
        requires_deposit: bool = False,
        deposit_minor: int | None = None,
        deposit_currency: str | None = None,
        intake_pool_id: str | None = None,
        active: bool = True,
        metadata: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        tenant_id: str | None = None,
    ) -> VcalEventType:
        with self._lock:
            slug_norm = slug.strip().lower().replace(" ", "-")
            for existing in self.event_types.values():
                if existing.user_id == user_id and existing.slug == slug_norm:
                    raise ValueError(f"event type slug already exists: {slug_norm}")
            now = _now()
            et = VcalEventType(
                id=str(uuid4()),
                user_id=user_id,
                host_user_id=host_user_id or user_id,
                slug=slug_norm,
                name=name.strip() or slug_norm,
                duration_minutes=max(5, int(duration_minutes)),
                buffer_before_minutes=max(0, int(buffer_before_minutes)),
                buffer_after_minutes=max(0, int(buffer_after_minutes)),
                min_notice_minutes=max(0, int(min_notice_minutes)),
                horizon_days=max(1, int(horizon_days)),
                location_mode=location_mode,
                requires_approval=requires_approval,
                requires_deposit=requires_deposit,
                deposit_minor=deposit_minor,
                deposit_currency=deposit_currency,
                intake_pool_id=intake_pool_id,
                active=active,
                metadata=dict(metadata or {}),
                created_at=now,
                updated_at=now,
                workspace_id=workspace_id,
                tenant_id=tenant_id or self._current_tenant(),
            )
            self.event_types[et.id] = et
            self._persist()
            return et

    def update_event_type(self, user_id: str, event_type_id: str, **fields) -> "VcalEventType":
        with self._lock:
            et = self._owned_event_type(user_id, event_type_id)
            allowed = {
                "name",
                "duration_minutes",
                "buffer_before_minutes",
                "buffer_after_minutes",
                "min_notice_minutes",
                "horizon_days",
                "location_mode",
                "requires_approval",
                "requires_deposit",
                "deposit_minor",
                "deposit_currency",
                "intake_pool_id",
                "active",
                "metadata",
            }
            for key, value in fields.items():
                if key not in allowed:
                    raise ValueError(f"cannot update field: {key}")
                if key in {
                    "duration_minutes",
                    "buffer_before_minutes",
                    "buffer_after_minutes",
                    "min_notice_minutes",
                    "horizon_days",
                    "deposit_minor",
                } and value is not None:
                    value = int(value)
                setattr(et, key, value)
            et.updated_at = _now()
            self._persist()
            return et

    def list_event_types(self, user_id: str, *, active_only: bool = False) -> list[VcalEventType]:
        rows = [et for et in self.event_types.values() if et.user_id == user_id]
        if active_only:
            rows = [et for et in rows if et.active]
        return sorted(rows, key=lambda et: et.name.lower())

    def get_event_type(self, user_id: str, event_type_id: str) -> VcalEventType:
        return self._owned_event_type(user_id, event_type_id)

    def get_event_type_by_slug(self, user_id: str, slug: str) -> VcalEventType | None:
        slug_norm = slug.strip().lower()
        for et in self.event_types.values():
            if et.user_id == user_id and et.slug == slug_norm:
                return et
        return None

    def create_availability_rule(
        self,
        *,
        user_id: str,
        day_of_week: int,
        start_time: str,
        end_time: str,
        timezone: str = "UTC",
        host_user_id: str | None = None,
        event_type_id: str | None = None,
        workspace_id: str | None = None,
    ) -> VcalAvailabilityRule:
        with self._lock:
            if event_type_id:
                self._owned_event_type(user_id, event_type_id)
            if not (0 <= int(day_of_week) <= 6):
                raise ValueError("day_of_week must be 0-6 (Monday-Sunday)")
            now = _now()
            rule = VcalAvailabilityRule(
                id=str(uuid4()),
                user_id=user_id,
                host_user_id=host_user_id or user_id,
                day_of_week=int(day_of_week),
                start_time=start_time,
                end_time=end_time,
                timezone=timezone or "UTC",
                event_type_id=event_type_id,
                active=True,
                created_at=now,
                updated_at=now,
                workspace_id=workspace_id,
            )
            self.availability_rules[rule.id] = rule
            self._persist()
            return rule

    def list_availability_rules(
        self,
        user_id: str,
        *,
        host_user_id: str | None = None,
        event_type_id: str | None = None,
    ) -> list[VcalAvailabilityRule]:
        rows = [r for r in self.availability_rules.values() if r.user_id == user_id and r.active]
        if host_user_id:
            rows = [r for r in rows if r.host_user_id == host_user_id]
        if event_type_id:
            rows = [r for r in rows if r.event_type_id is None or r.event_type_id == event_type_id]
        return sorted(rows, key=lambda r: (r.day_of_week, r.start_time))

    def create_blackout(
        self,
        *,
        user_id: str,
        starts_on: date,
        ends_on: date,
        host_user_id: str | None = None,
        reason: str | None = None,
        workspace_id: str | None = None,
    ) -> VcalBlackoutDate:
        with self._lock:
            if ends_on < starts_on:
                raise ValueError("ends_on must be on or after starts_on")
            now = _now()
            bo = VcalBlackoutDate(
                id=str(uuid4()),
                user_id=user_id,
                starts_on=starts_on,
                ends_on=ends_on,
                host_user_id=host_user_id,
                reason=reason,
                created_at=now,
                updated_at=now,
                workspace_id=workspace_id,
            )
            self.blackout_dates[bo.id] = bo
            self._persist()
            return bo

    def list_blackouts(self, user_id: str, *, host_user_id: str | None = None) -> list[VcalBlackoutDate]:
        rows = [b for b in self.blackout_dates.values() if b.user_id == user_id]
        if host_user_id:
            rows = [b for b in rows if b.host_user_id in (None, host_user_id)]
        return sorted(rows, key=lambda b: b.starts_on)

    def create_booking(
        self,
        *,
        user_id: str,
        event_type_id: str,
        guest_name: str,
        guest_email: str,
        starts_at: datetime,
        ends_at: datetime,
        status: BookingStatus = "confirmed",
        source: BookingSource = "api",
        host_user_id: str | None = None,
        meeting_url: str | None = None,
        workspace_event_id: str | None = None,
        intake_answers: dict[str, Any] | None = None,
        notes: str | None = None,
        contact_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        guest_token: str | None = None,
        tenant_id: str | None = None,
    ) -> VcalBooking:
        with self._lock:
            et = self._owned_event_type(user_id, event_type_id)
            if ends_at <= starts_at:
                raise ValueError("ends_at must be after starts_at")
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=timezone.utc)
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            token = guest_token or secrets.token_urlsafe(24)
            while token in self._guest_token_index:
                token = secrets.token_urlsafe(24)
            now = _now()
            booking = VcalBooking(
                id=str(uuid4()),
                user_id=user_id,
                event_type_id=et.id,
                host_user_id=host_user_id or et.host_user_id,
                guest_name=guest_name.strip(),
                guest_email=guest_email.strip().lower(),
                starts_at=starts_at,
                ends_at=ends_at,
                status=status,
                guest_token=token,
                source=source,
                meeting_url=meeting_url,
                workspace_event_id=workspace_event_id,
                intake_answers=dict(intake_answers or {}),
                notes=notes,
                contact_id=contact_id,
                metadata=dict(metadata or {}),
                created_at=now,
                updated_at=now,
                workspace_id=workspace_id,
                tenant_id=tenant_id or et.tenant_id or self._current_tenant(),
            )
            self.bookings[booking.id] = booking
            self._guest_token_index[token] = booking.id
            self._persist()
            return booking

    def get_booking(self, user_id: str, booking_id: str) -> VcalBooking:
        return self._owned_booking(user_id, booking_id)

    def get_booking_by_guest_token(self, guest_token: str) -> VcalBooking | None:
        booking_id = self._guest_token_index.get(guest_token)
        if not booking_id:
            return None
        return self.bookings.get(booking_id)

    def list_bookings(
        self,
        user_id: str,
        *,
        host_user_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        statuses: set[str] | None = None,
    ) -> list[VcalBooking]:
        rows = [b for b in self.bookings.values() if b.user_id == user_id]
        if host_user_id:
            rows = [b for b in rows if b.host_user_id == host_user_id]
        if statuses is not None:
            rows = [b for b in rows if b.status in statuses]
        if start is not None:
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            rows = [b for b in rows if b.ends_at > start]
        if end is not None:
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            rows = [b for b in rows if b.starts_at < end]
        return sorted(rows, key=lambda b: b.starts_at)

    def list_active_bookings_for_host(
        self,
        user_id: str,
        host_user_id: str,
        *,
        start: datetime,
        end: datetime,
    ) -> list[VcalBooking]:
        return self.list_bookings(
            user_id,
            host_user_id=host_user_id,
            start=start,
            end=end,
            statuses=set(ACTIVE_BOOKING_STATUSES),
        )

    def update_booking(
        self,
        user_id: str,
        booking_id: str,
        **fields: Any,
    ) -> VcalBooking:
        with self._lock:
            booking = self._owned_booking(user_id, booking_id)
            allowed = {
                "status",
                "meeting_url",
                "workspace_event_id",
                "notes",
                "session_outcome",
                "intake_answers",
                "cancel_reschedule",
                "starts_at",
                "ends_at",
                "metadata",
                "contact_id",
            }
            for key, value in fields.items():
                if key not in allowed:
                    raise ValueError(f"cannot update field: {key}")
                if key in {"starts_at", "ends_at"} and isinstance(value, str):
                    value = _parse_dt(value)
                if key == "session_outcome" and value is not None:
                    if value not in ("attended", "no_show"):
                        raise ValueError("invalid session_outcome")
                setattr(booking, key, value)
            booking.updated_at = _now()
            self._persist()
            return booking

    def create_slot_lock(
        self,
        *,
        user_id: str,
        host_user_id: str,
        starts_at: datetime,
        ends_at: datetime,
        holder_token: str,
        expires_at: datetime,
        event_type_id: str | None = None,
        workspace_id: str | None = None,
    ) -> VcalSlotLock:
        with self._lock:
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=timezone.utc)
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = _now()
            for existing in list(self.slot_locks.values()):
                if existing.user_id != user_id or existing.host_user_id != host_user_id:
                    continue
                if existing.expires_at <= now:
                    continue
                if starts_at < existing.ends_at and ends_at > existing.starts_at:
                    raise ValueError("slot already locked")
            lock = VcalSlotLock(
                id=str(uuid4()),
                user_id=user_id,
                host_user_id=host_user_id,
                starts_at=starts_at,
                ends_at=ends_at,
                holder_token=holder_token,
                expires_at=expires_at,
                event_type_id=event_type_id,
                workspace_id=workspace_id,
                created_at=now,
            )
            self.slot_locks[lock.id] = lock
            self._persist()
            return lock

    def release_slot_lock(self, user_id: str, lock_id: str, *, holder_token: str | None = None) -> bool:
        with self._lock:
            lock = self.slot_locks.get(lock_id)
            if lock is None or lock.user_id != user_id:
                return False
            if holder_token is not None and lock.holder_token != holder_token:
                return False
            del self.slot_locks[lock_id]
            self._persist()
            return True

    def prune_expired_locks(self, *, now: datetime | None = None) -> int:
        with self._lock:
            cursor = now or _now()
            if cursor.tzinfo is None:
                cursor = cursor.replace(tzinfo=timezone.utc)
            doomed = [lid for lid, lock in self.slot_locks.items() if lock.expires_at <= cursor]
            for lid in doomed:
                del self.slot_locks[lid]
            if doomed:
                self._persist()
            return len(doomed)

    def list_active_locks(
        self,
        user_id: str,
        host_user_id: str,
        *,
        start: datetime,
        end: datetime,
        now: datetime | None = None,
    ) -> list[VcalSlotLock]:
        cursor = now or _now()
        if cursor.tzinfo is None:
            cursor = cursor.replace(tzinfo=timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        rows: list[VcalSlotLock] = []
        for lock in self.slot_locks.values():
            if lock.user_id != user_id or lock.host_user_id != host_user_id:
                continue
            if lock.expires_at <= cursor:
                continue
            if lock.starts_at < end and lock.ends_at > start:
                rows.append(lock)
        return rows


    def upsert_host_profile(
        self,
        user_id: str,
        *,
        public_slug: str | None = None,
        display_name: str | None = None,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
        meeting_url_template: str | None = None,
    ) -> dict:
        with self._lock:
            row = dict(self.host_profiles.get(user_id) or {"user_id": user_id})
            old_slug = str(row.get("public_slug") or "").strip().lower()
            if public_slug is not None:
                slug = public_slug.strip().lower().replace(" ", "-")
                if not slug:
                    raise ValueError("public_slug required")
                other = self._public_slug_index.get(slug)
                if other and other != user_id:
                    raise ValueError("public_slug already taken")
                if old_slug and old_slug in self._public_slug_index:
                    del self._public_slug_index[old_slug]
                row["public_slug"] = slug
                self._public_slug_index[slug] = user_id
            if display_name is not None:
                row["display_name"] = display_name.strip() or user_id
            if webhook_url is not None:
                row["webhook_url"] = webhook_url.strip() or None
            if webhook_secret is not None:
                row["webhook_secret"] = webhook_secret
            if meeting_url_template is not None:
                row["meeting_url_template"] = meeting_url_template
            row.setdefault("display_name", user_id)
            row.setdefault("public_slug", user_id.lower().replace(" ", "-"))
            slug = str(row["public_slug"]).lower()
            self._public_slug_index[slug] = user_id
            self.host_profiles[user_id] = row
            self._persist()
            return dict(row)

    def get_host_profile(self, user_id: str) -> dict | None:
        row = self.host_profiles.get(user_id)
        return dict(row) if row else None

    def resolve_host_by_slug(self, public_slug: str) -> dict | None:
        user_id = self._public_slug_index.get(public_slug.strip().lower())
        if not user_id:
            return None
        return self.get_host_profile(user_id)

    def create_intake_pool(
        self,
        *,
        user_id: str,
        name: str,
        questions: list[dict] | None = None,
    ) -> dict:
        with self._lock:
            pool_id = str(uuid4())
            pool = {
                "id": pool_id,
                "user_id": user_id,
                "name": name.strip() or "Intake",
                "questions": list(questions or []),
                "created_at": _now().isoformat(),
                "updated_at": _now().isoformat(),
            }
            self.intake_pools[pool_id] = pool
            self._persist()
            return dict(pool)

    def list_intake_pools(self, user_id: str) -> list[dict]:
        return [dict(p) for p in self.intake_pools.values() if p.get("user_id") == user_id]

    def get_intake_pool(self, user_id: str, pool_id: str) -> dict:
        pool = self.intake_pools.get(pool_id)
        if pool is None or pool.get("user_id") != user_id:
            raise IsolationError(f"intake pool not found: {pool_id}")
        return dict(pool)


vical_store = VicalStore()
