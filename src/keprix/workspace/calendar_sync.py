"""External calendar sync: CalDAV (bidirectional) and ICS feeds (pull).

Providers:
- caldav / nextcloud / icloud / google: CalDAV with username + password or OAuth token
- ics: read-only HTTP(S) iCalendar feed (works with Google secret ICS URLs)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

PROVIDER_PRESETS: list[dict[str, Any]] = [
    {
        "id": "google",
        "label": "Google Calendar",
        "provider": "google",
        "sync_modes": ["pull", "push", "bidirectional"],
        "url_hint": "https://apidata.googleusercontent.com/caldav/v2/YOUR_EMAIL/events",
        "help": "Use your Google account email as username and an OAuth access token (or app password where allowed) as the password. For pull-only, paste the calendar secret ICS URL as an ICS feed instead.",
    },
    {
        "id": "google-ics",
        "label": "Google Calendar (ICS feed, pull only)",
        "provider": "ics",
        "sync_modes": ["pull"],
        "url_hint": "https://calendar.google.com/calendar/ical/.../basic.ics",
        "help": "In Google Calendar settings, copy the secret address in iCal format.",
    },
    {
        "id": "nextcloud",
        "label": "Nextcloud / ownCloud",
        "provider": "nextcloud",
        "sync_modes": ["pull", "push", "bidirectional"],
        "url_hint": "https://cloud.example/remote.php/dav/",
        "help": "CalDAV principal or calendar URL. Username is your Nextcloud login; password can be an app password.",
    },
    {
        "id": "icloud",
        "label": "Apple iCloud",
        "provider": "icloud",
        "sync_modes": ["pull", "push", "bidirectional"],
        "url_hint": "https://caldav.icloud.com/",
        "help": "Use your Apple ID email and an app-specific password from appleid.apple.com.",
    },
    {
        "id": "fastmail",
        "label": "Fastmail",
        "provider": "caldav",
        "sync_modes": ["pull", "push", "bidirectional"],
        "url_hint": "https://caldav.fastmail.com/dav/",
        "help": "Use your Fastmail username and an app password.",
    },
    {
        "id": "caldav",
        "label": "Generic CalDAV",
        "provider": "caldav",
        "sync_modes": ["pull", "push", "bidirectional"],
        "url_hint": "https://caldav.example.com/",
        "help": "Any CalDAV server URL (Radicale, Baikal, Synology, etc.).",
    },
    {
        "id": "ics",
        "label": "ICS / iCal feed (pull only)",
        "provider": "ics",
        "sync_modes": ["pull"],
        "url_hint": "https://example.com/calendar.ics",
        "help": "Public or secret HTTPS iCalendar feed. Pull only.",
    },
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_aware(value)
    try:
        from icalendar.prop import vDDDTypes

        if isinstance(value, vDDDTypes):
            return _parse_dt(value.dt)
    except Exception:
        pass
    if hasattr(value, "dt"):
        return _parse_dt(getattr(value, "dt"))
    # date-only
    try:
        from datetime import date

        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    except Exception:
        pass
    if isinstance(value, str):
        try:
            return _as_aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def _vevent_to_fields(component: Any) -> dict[str, Any] | None:
    uid = str(component.get("uid") or "").strip()
    if not uid:
        return None
    summary = str(component.get("summary") or "Untitled").strip() or "Untitled"
    description = str(component.get("description") or "")
    location = str(component.get("location") or "")
    start = _parse_dt(component.get("dtstart"))
    end = _parse_dt(component.get("dtend"))
    if start is None:
        return None
    all_day = False
    try:
        from datetime import date

        raw_start = component.get("dtstart").dt if component.get("dtstart") else None
        if isinstance(raw_start, date) and not isinstance(raw_start, datetime):
            all_day = True
    except Exception:
        pass
    if end is None:
        end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    rrule = component.get("rrule")
    recurrence = None
    if rrule is not None:
        try:
            recurrence = rrule.to_ical().decode() if hasattr(rrule, "to_ical") else str(rrule)
        except Exception:
            recurrence = str(rrule)
    return {
        "uid": uid,
        "title": summary,
        "description": description,
        "location": location,
        "start_at": start,
        "end_at": end,
        "all_day": all_day,
        "recurrence": recurrence,
    }


def _event_to_ics(event: dict[str, Any]) -> bytes:
    from icalendar import Calendar, Event, vDatetime

    cal = Calendar()
    cal.add("prodid", "-//Keprix//Calendar Sync//EN")
    cal.add("version", "2.0")
    vevent = Event()
    vevent.add("uid", event.get("uid") or f"keprix-{event['id']}@local")
    vevent.add("summary", event.get("title") or "Untitled")
    if event.get("description"):
        vevent.add("description", event["description"])
    if event.get("location"):
        vevent.add("location", event["location"])
    start = _as_aware(event["start_at"] if isinstance(event["start_at"], datetime) else _parse_dt(event["start_at"]))
    end = _as_aware(event["end_at"] if isinstance(event["end_at"], datetime) else _parse_dt(event["end_at"]))
    if event.get("all_day") and start and end:
        vevent.add("dtstart", start.date())
        vevent.add("dtend", end.date())
    else:
        if start:
            vevent.add("dtstart", vDatetime(start))
        if end:
            vevent.add("dtend", vDatetime(end))
    vevent.add("dtstamp", vDatetime(_utcnow()))
    if event.get("recurrence"):
        vevent.add("rrule", event["recurrence"])
    cal.add_component(vevent)
    return cal.to_ical()


def default_google_caldav_url(email: str) -> str:
    return f"https://apidata.googleusercontent.com/caldav/v2/{quote(email.strip())}/events"


async def sync_caldav(user_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Backward-compatible entrypoint used by routes."""
    from keprix.workspace.repository import workspace_repo

    if os.getenv("KEPRIX_CALDAV_DETERMINISTIC", "").lower() in {"1", "true", "yes"}:
        return {"ok": True, "synced": len(sources), "pulled": 0, "pushed": 0, "message": "CalDAV sync completed (deterministic)"}

    user = {"id": user_id}
    results: list[dict[str, Any]] = []
    pulled = 0
    pushed = 0
    errors = 0
    for listed in sources:
        try:
            source = workspace_repo.get_caldav_source(user, listed["id"])
        except Exception:
            source = listed
        if source.get("enabled") is False:
            results.append({"source_id": source["id"], "name": source.get("name"), "skipped": True, "reason": "disabled"})
            continue
        try:
            outcome = await sync_one_source(user, source, workspace_repo)
            pulled += int(outcome.get("pulled") or 0)
            pushed += int(outcome.get("pushed") or 0)
            results.append(outcome)
            workspace_repo.mark_source_synced(user, source["id"], ok=True, message=outcome.get("message"))
        except Exception as exc:
            errors += 1
            logger.exception("calendar sync failed for source %s", source.get("id"))
            message = str(exc)
            workspace_repo.mark_source_synced(user, source["id"], ok=False, message=message)
            results.append({"source_id": source["id"], "name": source.get("name"), "ok": False, "error": message})

    return {
        "ok": errors == 0,
        "synced": len(sources) - errors,
        "pulled": pulled,
        "pushed": pushed,
        "errors": errors,
        "results": results,
        "message": f"Synced {len(sources) - errors}/{len(sources)} sources (pulled {pulled}, pushed {pushed})",
    }


async def sync_one_source(user: dict[str, Any], source: dict[str, Any], repo: Any) -> dict[str, Any]:
    provider = str(source.get("provider") or "caldav").lower()
    direction = str(source.get("sync_direction") or "bidirectional").lower()
    if provider == "ics" or direction == "pull" and str(source.get("url") or "").lower().endswith(".ics"):
        if direction == "push":
            raise ValueError("ICS feeds are pull-only")
        count = await _pull_ics(user, source, repo)
        return {
            "source_id": source["id"],
            "name": source.get("name"),
            "ok": True,
            "pulled": count,
            "pushed": 0,
            "message": f"Pulled {count} events from ICS feed",
        }

    pulled = 0
    pushed = 0
    if direction in {"pull", "bidirectional"}:
        pulled = await _pull_caldav(user, source, repo)
    if direction in {"push", "bidirectional"}:
        pushed = await _push_caldav(user, source, repo)
    return {
        "source_id": source["id"],
        "name": source.get("name"),
        "ok": True,
        "pulled": pulled,
        "pushed": pushed,
        "message": f"CalDAV pull={pulled} push={pushed}",
    }


async def _pull_ics(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    from icalendar import Calendar

    url = str(source.get("url") or "").strip()
    if not url:
        raise ValueError("ICS source URL is required")
    headers = {}
    password = repo.get_source_password(source["id"])
    username = source.get("username") or ""
    auth = None
    if username and password:
        auth = (username, password)
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers, auth=auth)
        response.raise_for_status()
        payload = response.content
    calendar = Calendar.from_ical(payload)
    count = 0
    for component in calendar.walk():
        if component.name != "VEVENT":
            continue
        fields = _vevent_to_fields(component)
        if not fields:
            continue
        fields["external_readonly"] = True
        repo.upsert_event_by_uid(user, caldav_source_id=source["id"], **fields)
        count += 1
    return count


def _caldav_client(source: dict[str, Any], password: str | None):
    import caldav

    url = str(source.get("url") or "").strip()
    if not url:
        raise ValueError("CalDAV URL is required")
    username = str(source.get("username") or "").strip()
    if not username:
        raise ValueError("CalDAV username is required")
    if not password:
        raise ValueError("CalDAV password or access token is required")
    # Google CalDAV often expects Bearer-style tokens; caldav uses basic auth with token as password.
    return caldav.DAVClient(url=url, username=username, password=password)


def _pick_calendar(client: Any, source: dict[str, Any]):
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise ValueError("No calendars found on this CalDAV account")
    preferred = str(source.get("calendar_href") or "").strip()
    if preferred:
        for calendar in calendars:
            href = str(getattr(calendar, "url", "") or "")
            if preferred in href or href.endswith(preferred):
                return calendar
    name_hint = str(source.get("calendar_name") or "").strip().lower()
    if name_hint:
        for calendar in calendars:
            try:
                display = str(calendar.get_display_name() or "").lower()
            except Exception:
                display = ""
            if name_hint in display:
                return calendar
    return calendars[0]


async def _pull_caldav(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    import asyncio

    password = repo.get_source_password(source["id"])

    def _run() -> int:
        client = _caldav_client(source, password)
        calendar = _pick_calendar(client, source)
        start = _utcnow() - timedelta(days=int(source.get("pull_past_days") or 90))
        end = _utcnow() + timedelta(days=int(source.get("pull_future_days") or 365))
        try:
            events = calendar.date_search(start=start, end=end, expand=True)
        except TypeError:
            events = calendar.date_search(start=start, end=end)
        except Exception:
            # Some servers do not support date_search well; fall back to all events.
            events = calendar.events()
        count = 0
        for item in events:
            try:
                ical = item.data
                if hasattr(ical, "encode"):
                    raw = ical.encode() if isinstance(ical, str) else ical
                else:
                    raw = bytes(ical)
                from icalendar import Calendar

                parsed = Calendar.from_ical(raw)
                for component in parsed.walk():
                    if component.name != "VEVENT":
                        continue
                    fields = _vevent_to_fields(component)
                    if not fields:
                        continue
                    direction = str(source.get("sync_direction") or "bidirectional").lower()
                    fields["external_readonly"] = direction == "pull"
                    repo.upsert_event_by_uid(user, caldav_source_id=source["id"], **fields)
                    count += 1
            except Exception:
                logger.debug("skip caldav event parse failure", exc_info=True)
        return count

    return await asyncio.to_thread(_run)


async def _push_caldav(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    import asyncio

    password = repo.get_source_password(source["id"])
    local_events = [
        event
        for event in repo.list_events(user)
        if event.get("caldav_source_id") in {None, source["id"]} and not event.get("external_readonly")
    ]
    # Only push events tagged for this source, or local-only events when source is default push target.
    pushable = [
        event
        for event in local_events
        if event.get("caldav_source_id") == source["id"]
        or (source.get("push_local_events") and not event.get("caldav_source_id"))
    ]

    def _run() -> int:
        client = _caldav_client(source, password)
        calendar = _pick_calendar(client, source)
        count = 0
        for event in pushable:
            ics = _event_to_ics(event)
            uid = event.get("uid") or f"keprix-{event['id']}@local"
            try:
                calendar.save_event(ics.decode("utf-8"))
                repo.update_event(
                    user,
                    event["id"],
                    caldav_source_id=source["id"],
                    uid=uid,
                    external_etag=True,
                )
                count += 1
            except TypeError:
                calendar.save_event(ics)
                count += 1
            except Exception:
                logger.debug("caldav push failed for %s", uid, exc_info=True)
        return count

    return await asyncio.to_thread(_run)


async def push_event_to_source(user: dict[str, Any], source: dict[str, Any], event: dict[str, Any], repo: Any) -> bool:
    """Push a single local event immediately after create/update."""
    if str(source.get("provider") or "").lower() == "ics":
        return False
    direction = str(source.get("sync_direction") or "bidirectional").lower()
    if direction not in {"push", "bidirectional"}:
        return False
    import asyncio

    password = repo.get_source_password(source["id"])

    def _run() -> bool:
        client = _caldav_client(source, password)
        calendar = _pick_calendar(client, source)
        ics = _event_to_ics(event)
        try:
            calendar.save_event(ics.decode("utf-8"))
        except TypeError:
            calendar.save_event(ics)
        return True

    return await asyncio.to_thread(_run)
