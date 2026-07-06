"""Channel routing rules (Prompt 24)."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from keprix.backend.notifications.preferences import get_preferences_service
from keprix.backend.notifications.schemas import DEFAULT_CHANNELS_BY_SEVERITY, GROUP_CHANNELS


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def in_quiet_hours(prefs: dict[str, Any], now: datetime | None = None) -> bool:
    if not prefs.get("quiet_hours_enabled"):
        return False
    tz_name = str(prefs.get("quiet_hours_timezone") or "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    current = (now or datetime.now(timezone.utc)).astimezone(tz).time()
    start = _parse_hhmm(str(prefs.get("quiet_hours_start") or "22:00"))
    end = _parse_hhmm(str(prefs.get("quiet_hours_end") or "07:00"))
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def route_channels(
    *,
    workspace_id: str,
    user_id: str | None,
    severity: str,
    sensitive: bool,
    notification_type: str,
) -> dict[str, Any]:
    prefs = get_preferences_service().get(workspace_id, user_id or "default")
    channels_enabled = prefs.get("channels_enabled") or {}
    base_channels = list(DEFAULT_CHANNELS_BY_SEVERITY.get(severity, ["in_app"]))

    if notification_type in {"approval_needed", "pack_gate_pending"}:
        if "email" not in base_channels:
            base_channels.append("email")

    selected: list[str] = []
    for channel in base_channels:
        if not channels_enabled.get(channel, channel == "in_app"):
            continue
        if sensitive and channel in GROUP_CHANNELS:
            continue
        selected.append(channel)

    if not selected:
        selected = ["in_app"]

    quiet = in_quiet_hours(prefs)
    delay_for_digest = quiet and severity != "critical" and prefs.get("digest_enabled", True)

    return {
        "channels": selected,
        "delay_for_digest": delay_for_digest,
        "preferences": prefs,
    }
