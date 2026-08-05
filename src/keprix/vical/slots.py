"""Slot engine + short-lived locks."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from keprix.vical.busy import BusyReader
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import VcalAvailabilityRule, VcalEventType


@dataclass(frozen=True)
class TimeSlot:
    start_at: datetime
    end_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {"start_at": self.start_at.isoformat(), "end_at": self.end_at.isoformat()}


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    return int(parts[0]), int(parts[1] if len(parts) > 1 else 0)


class SlotEngine:
    def __init__(
        self,
        *,
        store: VicalStore | None = None,
        busy_reader: BusyReader | None = None,
        lock_ttl_seconds: int = 180,
    ) -> None:
        self.store = store or vical_store
        self.busy = busy_reader or BusyReader(store=self.store)
        self.lock_ttl_seconds = max(30, int(lock_ttl_seconds))

    def resolve_event_type(
        self,
        user_id: str,
        *,
        event_type_id: str | None = None,
        slug: str | None = None,
        auto_seed: bool = True,
    ) -> VcalEventType:
        if event_type_id:
            return self.store.get_event_type(user_id, event_type_id)
        if slug:
            found = self.store.get_event_type_by_slug(user_id, slug)
            if found:
                return found
        if auto_seed:
            ensure_default_consultation(user_id, store=self.store)
            found = self.store.get_event_type_by_slug(user_id, slug or "consultation")
            if found:
                return found
        raise LookupError("event type not found")

    def _rules_for(self, user_id: str, et: VcalEventType) -> list[VcalAvailabilityRule]:
        typed = self.store.list_availability_rules(
            user_id,
            host_user_id=et.host_user_id,
            event_type_id=et.id,
        )
        if typed:
            return typed
        return [
            r
            for r in self.store.list_availability_rules(user_id, host_user_id=et.host_user_id)
            if r.event_type_id is None
        ]

    def _in_blackout(self, user_id: str, host_user_id: str, day: date) -> bool:
        for bo in self.store.list_blackouts(user_id, host_user_id=host_user_id):
            if bo.starts_on <= day <= bo.ends_on:
                return True
        return False

    def offer_slots(
        self,
        user_id: str,
        *,
        event_type_id: str | None = None,
        slug: str | None = None,
        start: datetime | None = None,
        count: int = 20,
        now: datetime | None = None,
    ) -> list[TimeSlot]:
        et = self.resolve_event_type(user_id, event_type_id=event_type_id, slug=slug)
        rules = self._rules_for(user_id, et)
        if not rules:
            return []

        cursor_now = _ensure_aware(now or datetime.now(timezone.utc))
        window_start = _ensure_aware(start or cursor_now)
        earliest = cursor_now + timedelta(minutes=int(et.min_notice_minutes))
        if window_start < earliest:
            window_start = earliest
        window_end = cursor_now + timedelta(days=int(et.horizon_days))

        # Use first rule timezone as reference (ECHO default UTC)
        tz_name = rules[0].timezone or "UTC"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001
            tz = timezone.utc

        busy = self.busy.collect(
            user_id=user_id,
            host_user_id=et.host_user_id,
            start=window_start,
            end=window_end,
            event_type=et,
            now=cursor_now,
        )

        duration = timedelta(minutes=int(et.duration_minutes))
        step = duration if et.duration_minutes >= 15 else timedelta(minutes=15)
        slots: list[TimeSlot] = []

        day_cursor = window_start.astimezone(tz).date()
        last_day = window_end.astimezone(tz).date()
        while day_cursor <= last_day and len(slots) < count:
            if self._in_blackout(user_id, et.host_user_id, day_cursor):
                day_cursor += timedelta(days=1)
                continue
            weekday = day_cursor.weekday()
            day_rules = [r for r in rules if r.day_of_week == weekday and r.active]
            for rule in day_rules:
                sh, sm = _parse_hhmm(rule.start_time)
                eh, em = _parse_hhmm(rule.end_time)
                slot_start = datetime(day_cursor.year, day_cursor.month, day_cursor.day, sh, sm, tzinfo=tz)
                day_end = datetime(day_cursor.year, day_cursor.month, day_cursor.day, eh, em, tzinfo=tz)
                while slot_start + duration <= day_end and len(slots) < count:
                    slot_end = slot_start + duration
                    utc_start = slot_start.astimezone(timezone.utc)
                    utc_end = slot_end.astimezone(timezone.utc)
                    if utc_start >= window_start and utc_end <= window_end:
                        if not BusyReader.conflicts(busy, utc_start, utc_end):
                            slots.append(TimeSlot(start_at=utc_start, end_at=utc_end))
                    slot_start = slot_start + step
            day_cursor += timedelta(days=1)

        return slots

    def acquire_lock(
        self,
        user_id: str,
        *,
        host_user_id: str,
        starts_at: datetime,
        ends_at: datetime,
        event_type_id: str | None = None,
        holder_token: str | None = None,
        now: datetime | None = None,
    ):
        cursor = _ensure_aware(now or datetime.now(timezone.utc))
        self.store.prune_expired_locks(now=cursor)
        token = holder_token or secrets.token_urlsafe(16)
        return self.store.create_slot_lock(
            user_id=user_id,
            host_user_id=host_user_id,
            starts_at=_ensure_aware(starts_at),
            ends_at=_ensure_aware(ends_at),
            holder_token=token,
            expires_at=cursor + timedelta(seconds=self.lock_ttl_seconds),
            event_type_id=event_type_id,
        )
