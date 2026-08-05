"""Busy windows for slot generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import VcalEventType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BusyWindow:
    start: datetime
    end: datetime
    source: str = "unknown"


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


class BusyReader:
    """Union busy from viCal bookings, locks, and workspace calendar events."""

    def __init__(
        self,
        *,
        store: VicalStore | None = None,
        list_workspace_events: Callable[..., list[dict[str, Any]]] | None = None,
    ) -> None:
        self.store = store or vical_store
        self._list_workspace_events = list_workspace_events

    def _workspace_events(self, user_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
        if self._list_workspace_events is not None:
            try:
                return list(self._list_workspace_events(user_id, start, end) or [])
            except Exception as exc:  # noqa: BLE001 - fail soft for busy
                logger.warning("viCal busy: workspace events failed: %s", exc)
                return []
        try:
            from keprix.workspace.repository import workspace_repo

            return workspace_repo.list_events({"id": user_id, "username": user_id}, start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            logger.warning("viCal busy: workspace_repo unavailable: %s", exc)
            return []

    def collect(
        self,
        *,
        user_id: str,
        host_user_id: str,
        start: datetime,
        end: datetime,
        event_type: VcalEventType | None = None,
        now: datetime | None = None,
    ) -> list[BusyWindow]:
        start = _ensure_aware(start)
        end = _ensure_aware(end)
        windows: list[BusyWindow] = []

        buf_before = timedelta(minutes=int(event_type.buffer_before_minutes)) if event_type else timedelta(0)
        buf_after = timedelta(minutes=int(event_type.buffer_after_minutes)) if event_type else timedelta(0)

        for booking in self.store.list_active_bookings_for_host(
            user_id,
            host_user_id,
            start=start - buf_after,
            end=end + buf_before,
        ):
            windows.append(
                BusyWindow(
                    start=_ensure_aware(booking.starts_at) - buf_before,
                    end=_ensure_aware(booking.ends_at) + buf_after,
                    source="vical_booking",
                )
            )

        for lock in self.store.list_active_locks(
            user_id,
            host_user_id,
            start=start,
            end=end,
            now=now,
        ):
            windows.append(
                BusyWindow(
                    start=_ensure_aware(lock.starts_at),
                    end=_ensure_aware(lock.ends_at),
                    source="vical_lock",
                )
            )

        for event in self._workspace_events(host_user_id, start, end):
            ev_start = event.get("start_at")
            ev_end = event.get("end_at")
            if isinstance(ev_start, str):
                try:
                    ev_start = datetime.fromisoformat(ev_start.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if isinstance(ev_end, str):
                try:
                    ev_end = datetime.fromisoformat(ev_end.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if not isinstance(ev_start, datetime) or not isinstance(ev_end, datetime):
                continue
            windows.append(
                BusyWindow(
                    start=_ensure_aware(ev_start),
                    end=_ensure_aware(ev_end),
                    source="workspace_calendar",
                )
            )

        windows.sort(key=lambda w: w.start)
        return windows

    @staticmethod
    def conflicts(windows: list[BusyWindow], start: datetime, end: datetime) -> bool:
        start = _ensure_aware(start)
        end = _ensure_aware(end)
        return any(_overlap(start, end, w.start, w.end) for w in windows)
