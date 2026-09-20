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
        "help": "Connect with Google (OAuth). Gmail app passwords cannot access Calendar. For pull-only without OAuth, paste the secret iCal URL from Google Calendar settings.",
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
    rid = component.get("recurrence-id")
    if rid is not None:
        rid_dt = _parse_dt(rid)
        if rid_dt is not None:
            uid = f"{uid}#{rid_dt.strftime('%Y%m%dT%H%M%SZ')}"
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


def looks_like_gmail_app_password(value: str | None) -> bool:
    """Google app passwords are 16 lowercase letters, often grouped in fours."""
    compact = "".join(ch for ch in str(value or "") if not ch.isspace())
    return len(compact) == 16 and compact.isalpha() and compact.islower()


def looks_like_google_oauth_token(value: str | None) -> bool:
    token = str(value or "").strip()
    if not token or looks_like_gmail_app_password(token):
        return False
    return token.startswith("ya29.") or len(token) >= 32


def google_app_password_error() -> str:
    return (
        "Gmail app passwords cannot access Google Calendar. "
        "Use Connect with Google (OAuth with calendar.events), or paste the "
        "secret iCal URL from Google Calendar → Settings → Integrate calendar."
    )


async def resolve_google_access_token(source: dict[str, Any], repo: Any) -> str:
    """Return a Calendar API Bearer token. Never uses a Gmail app password."""
    vault_id = str(source.get("vault_item_id") or "").strip()
    user_id = str(source.get("user_id") or "").strip()
    if vault_id and user_id:
        try:
            from keprix.oauth.tokens import load_oauth_tokens, refresh_google_tokens

            tokens = await load_oauth_tokens(vault_id, user_id)
            access = str(tokens.get("access_token") or "").strip()
            expires_at = int(tokens.get("expires_at") or 0)
            if expires_at and expires_at < int(_utcnow().timestamp()) + 60:
                tokens = await refresh_google_tokens(vault_id, user_id)
                access = str(tokens.get("access_token") or "").strip()
            if looks_like_google_oauth_token(access):
                return access
        except Exception as exc:
            logger.info("Google Calendar vault token failed: %s", exc)
    stored = repo.get_source_password(source["id"]) if hasattr(repo, "get_source_password") else None
    if looks_like_google_oauth_token(stored):
        return str(stored).strip()
    try:
        from keprix.integrations.google_workspace.oauth_store import GoogleWorkspaceOAuthStore

        token = GoogleWorkspaceOAuthStore().load()
        access = str(token.access_token or "").strip()
        if token.connected and looks_like_google_oauth_token(access):
            return access
    except Exception:
        pass
    env_token = os.environ.get("KEPRIX_GOOGLE_CALENDAR_ACCESS_TOKEN", "").strip()
    if looks_like_google_oauth_token(env_token):
        return env_token
    raise ValueError(google_app_password_error())


def _rfc3339(value: datetime) -> str:
    return _as_aware(value).isoformat().replace("+00:00", "Z")


def expand_events_for_range(
    events: list[dict[str, Any]],
    start: datetime | None,
    end: datetime | None,
) -> list[dict[str, Any]]:
    """Keep events that overlap [start, end], expanding RRULE masters into instances.

    With no window, return stored rows unchanged so push/sync does not explode recurrences.
    """
    if start is None and end is None:
        return sorted(list(events), key=lambda row: row.get("start_at") or datetime.min.replace(tzinfo=timezone.utc))
    window_start = _as_aware(start) if isinstance(start, datetime) else _parse_dt(start)
    window_end = _as_aware(end) if isinstance(end, datetime) else _parse_dt(end)
    out: list[dict[str, Any]] = []
    for event in events:
        event_start = _as_aware(_parse_dt(event.get("start_at")))
        event_end = _as_aware(_parse_dt(event.get("end_at")))
        if event_start is None or event_end is None:
            continue
        recurrence = str(event.get("recurrence") or "").strip()
        if not recurrence:
            if window_start and event_end < window_start:
                continue
            if window_end and event_start > window_end:
                continue
            out.append(event)
            continue
        out.extend(_expand_recurrence(event, event_start, event_end, window_start, window_end))
    out.sort(key=lambda row: row["start_at"])
    return out


def _expand_recurrence(
    event: dict[str, Any],
    event_start: datetime,
    event_end: datetime,
    window_start: datetime | None,
    window_end: datetime | None,
) -> list[dict[str, Any]]:
    from dateutil.rrule import rrulestr

    duration = event_end - event_start
    text = str(event.get("recurrence") or "").strip()
    if text.upper().startswith("RRULE:"):
        text = text.split(":", 1)[1]
    try:
        rule = rrulestr(text, dtstart=event_start)
    except Exception:
        if window_start and event_end < window_start:
            return []
        if window_end and event_start > window_end:
            return []
        return [event]
    range_start = window_start or event_start
    range_end = window_end or (event_start + timedelta(days=400))
    try:
        occurrences = rule.between(range_start - duration, range_end, inc=True)
    except Exception:
        return [event]
    rows: list[dict[str, Any]] = []
    for occ in occurrences:
        occ_start = _as_aware(occ)
        if occ_start is None:
            continue
        occ_end = occ_start + duration
        if window_start and occ_end < window_start:
            continue
        if window_end and occ_start > window_end:
            continue
        copy = dict(event)
        copy["start_at"] = occ_start
        copy["end_at"] = occ_end
        copy["id"] = f"{event.get('id')}:{occ_start.strftime('%Y%m%dT%H%M%SZ')}"
        rows.append(copy)
    return rows


def _google_item_to_fields(item: dict[str, Any]) -> dict[str, Any] | None:
    if str(item.get("status") or "").lower() == "cancelled":
        return None
    uid = str(item.get("id") or "").strip()
    if not uid:
        return None
    start_blob = item.get("start") or {}
    end_blob = item.get("end") or {}
    all_day = "date" in start_blob and "dateTime" not in start_blob
    start = _parse_dt(start_blob.get("dateTime") or start_blob.get("date"))
    end = _parse_dt(end_blob.get("dateTime") or end_blob.get("date"))
    if start is None:
        return None
    if end is None:
        end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
    return {
        "uid": uid,
        "title": str(item.get("summary") or "Untitled").strip() or "Untitled",
        "description": str(item.get("description") or ""),
        "location": str(item.get("location") or ""),
        "start_at": start,
        "end_at": end,
        "all_day": all_day,
        "recurrence": None,
    }


def _is_direct_calendar_collection(url: str) -> bool:
    lowered = url.rstrip("/").lower()
    return lowered.endswith("/events") or "/caldav/v2/" in lowered


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
        pulled = await _pull_external(user, source, repo)
    if direction in {"push", "bidirectional"}:
        if str(source.get("provider") or "").lower() == "google":
            try:
                pushed = await _push_google_api(user, source, repo)
            except Exception as exc:
                if pulled == 0:
                    raise
                logger.info("Google Calendar push failed after a successful pull: %s", exc)
        else:
            pushed = await _push_caldav(user, source, repo)
    kind = "Google" if str(source.get("provider") or "").lower() == "google" else "CalDAV"
    return {
        "source_id": source["id"],
        "name": source.get("name"),
        "ok": True,
        "pulled": pulled,
        "pushed": pushed,
        "message": f"{kind} pull={pulled} push={pushed}",
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
    kwargs: dict[str, Any] = {"url": url, "username": username, "password": password}
    if str(source.get("provider") or "").lower() == "google":
        kwargs["headers"] = {"Authorization": f"Bearer {password}"}
    try:
        return caldav.DAVClient(**kwargs)
    except TypeError:
        kwargs.pop("headers", None)
        return caldav.DAVClient(**kwargs)


def _calendar_from_url(client: Any, url: str):
    if not url:
        return None
    try:
        if hasattr(client, "calendar"):
            return client.calendar(url=url)
    except Exception:
        logger.debug("direct CalDAV calendar url failed", exc_info=True)
    try:
        import caldav

        return caldav.Calendar(client=client, url=url)
    except Exception:
        return None


def _pick_calendar(client: Any, source: dict[str, Any]):
    url = str(source.get("url") or "").strip()
    preferred = str(source.get("calendar_href") or "").strip() or url
    if preferred and (
        _is_direct_calendar_collection(preferred) or str(source.get("provider") or "").lower() == "google"
    ):
        calendar = _calendar_from_url(client, preferred)
        if calendar is not None:
            return calendar
    try:
        principal = client.principal()
        calendars = principal.calendars()
    except Exception as exc:
        calendar = _calendar_from_url(client, url)
        if calendar is not None:
            return calendar
        raise ValueError(f"Could not list CalDAV calendars: {exc}") from exc
    if not calendars:
        calendar = _calendar_from_url(client, url)
        if calendar is not None:
            return calendar
        raise ValueError("No calendars found on this CalDAV account")
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


async def _try_google_calendar_api(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    password = await resolve_google_access_token(source, repo)
    calendar_id = str(source.get("calendar_name") or source.get("username") or "primary").strip() or "primary"
    start = _utcnow() - timedelta(days=int(source.get("pull_past_days") or 90))
    end = _utcnow() + timedelta(days=int(source.get("pull_future_days") or 365))
    headers = {"Authorization": f"Bearer {password}", "Accept": "application/json"}
    params = {
        "timeMin": _rfc3339(start),
        "timeMax": _rfc3339(end),
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "2500",
    }
    encoded_id = quote(calendar_id, safe="@.")
    url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    retried_primary = False
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        while True:
            query = dict(params)
            if page_token:
                query["pageToken"] = page_token
            response = await client.get(url, headers=headers, params=query)
            if response.status_code in {401, 403}:
                raise ValueError(google_app_password_error())
            if response.status_code == 404 and not retried_primary:
                url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                retried_primary = True
                page_token = None
                continue
            response.raise_for_status()
            payload = response.json()
            items.extend(payload.get("items") or [])
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    count = 0
    direction = str(source.get("sync_direction") or "bidirectional").lower()
    for item in items:
        fields = _google_item_to_fields(item)
        if not fields:
            continue
        fields["external_readonly"] = direction == "pull"
        repo.upsert_event_by_uid(user, caldav_source_id=source["id"], **fields)
        count += 1
    return count


async def _pull_external(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    if str(source.get("provider") or "").lower() == "google":
        stored = repo.get_source_password(source["id"]) if hasattr(repo, "get_source_password") else None
        if looks_like_gmail_app_password(stored) and not source.get("vault_item_id"):
            return await _try_google_calendar_api(user, source, repo)
        try:
            return await _try_google_calendar_api(user, source, repo)
        except Exception as exc:
            if looks_like_gmail_app_password(stored):
                raise ValueError(google_app_password_error()) from exc
            logger.info("Google Calendar API pull failed, trying CalDAV: %s", exc)
            try:
                return await _pull_caldav(user, source, repo)
            except Exception as caldav_exc:
                raise ValueError(f"{exc} CalDAV also failed: {caldav_exc}") from caldav_exc
    return await _pull_caldav(user, source, repo)


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


def _google_event_body(event: dict[str, Any]) -> dict[str, Any]:
    start = _as_aware(event["start_at"] if isinstance(event.get("start_at"), datetime) else _parse_dt(event.get("start_at")))
    end = _as_aware(event["end_at"] if isinstance(event.get("end_at"), datetime) else _parse_dt(event.get("end_at")))
    body: dict[str, Any] = {
        "summary": event.get("title") or "Untitled",
        "description": event.get("description") or "",
        "location": event.get("location") or "",
    }
    if event.get("all_day") and start and end:
        body["start"] = {"date": start.date().isoformat()}
        body["end"] = {"date": end.date().isoformat()}
    else:
        if start:
            body["start"] = {"dateTime": _rfc3339(start)}
        if end:
            body["end"] = {"dateTime": _rfc3339(end)}
    return body


async def _push_google_api(user: dict[str, Any], source: dict[str, Any], repo: Any) -> int:
    token = await resolve_google_access_token(source, repo)
    calendar_id = str(source.get("calendar_name") or source.get("username") or "primary").strip() or "primary"
    encoded_id = quote(calendar_id, safe="@.")
    local_events = [
        event
        for event in repo.list_events(user)
        if event.get("caldav_source_id") in {None, source["id"]} and not event.get("external_readonly")
    ]
    pushable = [
        event
        for event in local_events
        if event.get("caldav_source_id") == source["id"]
        or (source.get("push_local_events") and not event.get("caldav_source_id"))
    ]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    count = 0
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        for event in pushable:
            body = _google_event_body(event)
            uid = str(event.get("uid") or "").strip()
            if uid and not str(uid).startswith("keprix-"):
                url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events/{quote(uid, safe='')}"
                response = await client.patch(url, headers=headers, json=body)
                if response.status_code == 404:
                    url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
                    response = await client.post(url, headers=headers, json=body)
            else:
                url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
                response = await client.post(url, headers=headers, json=body)
            if response.status_code in {401, 403}:
                raise ValueError(google_app_password_error())
            if response.status_code >= 400:
                logger.info("Google Calendar push HTTP %s: %s", response.status_code, response.text[:200])
                continue
            payload = response.json() if response.content else {}
            new_uid = str(payload.get("id") or uid or f"keprix-{event['id']}@local")
            repo.update_event(
                user,
                event["id"],
                caldav_source_id=source["id"],
                uid=new_uid,
                external_etag=True,
            )
            count += 1
    return count


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
    if str(source.get("provider") or "").lower() == "google":
        try:
            token = await resolve_google_access_token(source, repo)
            calendar_id = str(source.get("calendar_name") or source.get("username") or "primary").strip() or "primary"
            encoded_id = quote(calendar_id, safe="@.")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.post(
                    f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events",
                    headers=headers,
                    json=_google_event_body(event),
                )
            return response.status_code < 400
        except Exception:
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
