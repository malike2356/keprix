"""Google Calendar REST adapter (Prompt 633).

Creates host events with guest attendees and sendUpdates=all when configured.
Injectable fetch for hermetic tests.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from keprix.vical.calendar.delivery_state import map_google_response
from keprix.vical.calendar.types import (
    CalendarAdapterResult,
    CalendarAttendeeSnapshot,
    CalendarEventInput,
    CalendarSendUpdates,
)

GoogleFetch = Callable[[str, dict[str, Any]], dict[str, Any]]
TokenGetter = Callable[[str, str], str | None]


def google_calendar_configured() -> bool:
    return bool(
        (
            (os.environ.get("GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or "")
        ).strip()
        and (
            (os.environ.get("GOOGLE_CLIENT_SECRET") or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or "")
        ).strip()
    )


def _default_fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
    method = str(init.get("method") or "GET").upper()
    headers = dict(init.get("headers") or {})
    data = init.get("body")
    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else (
            data.encode("utf-8") if isinstance(data, str) else data
        )
        headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return {
                "status": getattr(resp, "status", 200),
                "json": json.loads(raw) if raw.strip() else {},
                "headers": dict(resp.headers.items()),
            }
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {"message": raw}
        return {"status": int(exc.code), "json": payload, "headers": dict(exc.headers.items()) if exc.headers else {}}
    except URLError as exc:
        return {"status": 0, "json": {"message": str(exc.reason)}, "headers": {}}


class GoogleCalendarAdapter:
    provider = "google"

    def __init__(
        self,
        *,
        fetch_impl: GoogleFetch | None = None,
        get_access_token: TokenGetter | None = None,
        create_cache: dict[str, CalendarAdapterResult] | None = None,
    ) -> None:
        self._fetch = fetch_impl or _default_fetch
        self._get_token = get_access_token
        self._cache = create_cache if create_cache is not None else {}

    def create_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        if input.idempotency_key in self._cache:
            cached = self._cache[input.idempotency_key]
            return CalendarAdapterResult(
                ok=cached.ok,
                status="duplicate" if cached.ok else cached.status,
                provider="google",
                provider_event_id=cached.provider_event_id,
                etag=cached.etag,
                html_link=cached.html_link,
                attendees=list(cached.attendees),
                host_event_created=cached.host_event_created,
                invitation_send_requested=cached.invitation_send_requested,
                invitation_delivery_state=cached.invitation_delivery_state,
                join_url=cached.join_url,
                error_code=cached.error_code,
            )

        token = self._token(input.workspace_id, input.user_id)
        if not token:
            result = CalendarAdapterResult(
                ok=False,
                status="not_configured",
                provider="google",
                error_code="not_configured",
                error_message="Google Calendar OAuth token missing",
            )
            self._cache[input.idempotency_key] = result
            return result

        body: dict[str, Any] = {
            "summary": input.summary[:1024],
            "description": input.description or "",
            "start": {"dateTime": input.starts_at, "timeZone": input.timezone or "UTC"},
            "end": {"dateTime": input.ends_at, "timeZone": input.timezone or "UTC"},
            "location": input.location or input.join_url or "",
        }
        if input.guest_email:
            body["attendees"] = [{"email": input.guest_email, "displayName": input.guest_name or ""}]
        send = input.send_updates or "all"
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?sendUpdates={send}"
        resp = self._fetch(
            url,
            {
                "method": "POST",
                "headers": {"Authorization": f"Bearer {token}"},
                "body": body,
            },
        )
        result = self._map_response(resp, invitation_requested=bool(input.guest_email) and send != "none")
        self._cache[input.idempotency_key] = result
        return result

    def update_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        if not input.provider_event_id:
            return CalendarAdapterResult(
                ok=False, status="failed", provider="google", error_code="missing_event_id"
            )
        token = self._token(input.workspace_id, input.user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="google", error_code="not_configured"
            )
        body = {
            "summary": input.summary[:1024],
            "description": input.description or "",
            "start": {"dateTime": input.starts_at, "timeZone": input.timezone or "UTC"},
            "end": {"dateTime": input.ends_at, "timeZone": input.timezone or "UTC"},
            "location": input.location or input.join_url or "",
        }
        if input.guest_email:
            body["attendees"] = [{"email": input.guest_email}]
        send = input.send_updates or "all"
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/"
            f"{input.provider_event_id}?sendUpdates={send}"
        )
        resp = self._fetch(
            url,
            {"method": "PATCH", "headers": {"Authorization": f"Bearer {token}"}, "body": body},
        )
        return self._map_response(resp, invitation_requested=bool(input.guest_email) and send != "none")

    def delete_event(
        self,
        *,
        workspace_id: str,
        user_id: str,
        booking_id: str,
        provider_event_id: str,
        idempotency_key: str,
        send_updates: CalendarSendUpdates = "all",
    ) -> CalendarAdapterResult:
        token = self._token(workspace_id, user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="google", error_code="not_configured"
            )
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/"
            f"{provider_event_id}?sendUpdates={send_updates}"
        )
        resp = self._fetch(url, {"method": "DELETE", "headers": {"Authorization": f"Bearer {token}"}})
        status = int(resp.get("status") or 0)
        if status in {200, 204, 404}:
            return CalendarAdapterResult(
                ok=True,
                status="succeeded",
                provider="google",
                provider_event_id=provider_event_id,
                host_event_created=True,
            )
        if status == 429:
            return CalendarAdapterResult(
                ok=False,
                status="retryable",
                provider="google",
                error_code="rate_limited",
                retry_after_ms=2000,
            )
        return CalendarAdapterResult(
            ok=False, status="failed", provider="google", error_code="api_error"
        )

    def get_event(
        self, *, workspace_id: str, user_id: str, provider_event_id: str
    ) -> CalendarAdapterResult:
        token = self._token(workspace_id, user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="google", error_code="not_configured"
            )
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{provider_event_id}"
        resp = self._fetch(url, {"method": "GET", "headers": {"Authorization": f"Bearer {token}"}})
        return self._map_response(resp, invitation_requested=False)

    def _token(self, workspace_id: str, user_id: str) -> str | None:
        if self._get_token:
            return self._get_token(workspace_id, user_id)
        # Env-injected test/dev token only (never invent OAuth exchange here)
        return (os.environ.get("KEPRIX_GOOGLE_CALENDAR_ACCESS_TOKEN") or "").strip() or None

    def _map_response(
        self, resp: dict[str, Any], *, invitation_requested: bool
    ) -> CalendarAdapterResult:
        status = int(resp.get("status") or 0)
        payload = resp.get("json") or {}
        if status == 401:
            return CalendarAdapterResult(
                ok=False, status="action_required", provider="google", error_code="expired_token"
            )
        if status == 429:
            return CalendarAdapterResult(
                ok=False,
                status="retryable",
                provider="google",
                error_code="rate_limited",
                retry_after_ms=2000,
            )
        if status == 409:
            return CalendarAdapterResult(
                ok=False, status="action_required", provider="google", error_code="conflict"
            )
        if status < 200 or status >= 300:
            return CalendarAdapterResult(
                ok=False,
                status="failed",
                provider="google",
                error_code="api_error",
                error_message=str(payload.get("error", {}).get("message") or payload)[:300],
            )
        attendees: list[CalendarAttendeeSnapshot] = []
        for a in payload.get("attendees") or []:
            resp_s, del_s = map_google_response(a.get("responseStatus"))
            attendees.append(
                CalendarAttendeeSnapshot(
                    email=str(a.get("email") or ""),
                    response_status=resp_s,
                    delivery_state=del_s if invitation_requested else resp_s and del_s or "unknown",
                )
            )
        invite_state = "sent" if invitation_requested else "unknown"
        if attendees:
            invite_state = attendees[0].delivery_state
        return CalendarAdapterResult(
            ok=True,
            status="succeeded",
            provider="google",
            provider_event_id=str(payload.get("id") or "") or None,
            etag=payload.get("etag"),
            html_link=payload.get("htmlLink"),
            organizer_email=(payload.get("organizer") or {}).get("email"),
            attendees=attendees,
            host_event_created=True,
            invitation_send_requested=invitation_requested,
            invitation_delivery_state=invite_state,  # type: ignore[arg-type]
            raw={"kind": payload.get("kind")},
        )
