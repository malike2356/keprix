"""Microsoft Graph Calendar adapter (Prompt 633).

Configurable via inject; returns not_configured when Graph credentials absent.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from keprix.vical.calendar.delivery_state import map_microsoft_response
from keprix.vical.calendar.types import (
    CalendarAdapterResult,
    CalendarAttendeeSnapshot,
    CalendarEventInput,
    CalendarSendUpdates,
)

MsFetch = Callable[[str, dict[str, Any]], dict[str, Any]]
TokenGetter = Callable[[str, str], str | None]


def microsoft_calendar_configured() -> bool:
    return bool(
        (os.environ.get("MICROSOFT_OAUTH_CLIENT_ID") or "").strip()
        and (os.environ.get("MICROSOFT_OAUTH_CLIENT_SECRET") or "").strip()
    )


class MicrosoftCalendarAdapter:
    provider = "microsoft"

    def __init__(
        self,
        *,
        fetch_impl: MsFetch | None = None,
        get_access_token: TokenGetter | None = None,
        create_cache: dict[str, CalendarAdapterResult] | None = None,
    ) -> None:
        self._fetch = fetch_impl
        self._get_token = get_access_token
        self._cache = create_cache if create_cache is not None else {}

    def create_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        if input.idempotency_key in self._cache:
            cached = self._cache[input.idempotency_key]
            return CalendarAdapterResult(
                ok=cached.ok,
                status="duplicate" if cached.ok else cached.status,
                provider="microsoft",
                provider_event_id=cached.provider_event_id,
                attendees=list(cached.attendees),
                host_event_created=cached.host_event_created,
                invitation_send_requested=cached.invitation_send_requested,
                invitation_delivery_state=cached.invitation_delivery_state,
                error_code=cached.error_code,
            )
        token = self._token(input.workspace_id, input.user_id)
        if not token or not self._fetch:
            result = CalendarAdapterResult(
                ok=False,
                status="not_configured",
                provider="microsoft",
                error_code="not_configured",
                error_message="Microsoft Graph calendar not configured",
            )
            self._cache[input.idempotency_key] = result
            return result
        body = {
            "subject": input.summary[:255],
            "body": {"contentType": "Text", "content": input.description or ""},
            "start": {"dateTime": input.starts_at.replace("Z", ""), "timeZone": input.timezone or "UTC"},
            "end": {"dateTime": input.ends_at.replace("Z", ""), "timeZone": input.timezone or "UTC"},
            "location": {"displayName": input.location or input.join_url or ""},
        }
        if input.guest_email:
            body["attendees"] = [
                {
                    "emailAddress": {"address": input.guest_email, "name": input.guest_name or ""},
                    "type": "required",
                }
            ]
        resp = self._fetch(
            "https://graph.microsoft.com/v1.0/me/events",
            {"method": "POST", "headers": {"Authorization": f"Bearer {token}"}, "body": body},
        )
        result = self._map(resp, invitation_requested=bool(input.guest_email))
        self._cache[input.idempotency_key] = result
        return result

    def update_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        if not input.provider_event_id or not self._fetch:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        token = self._token(input.workspace_id, input.user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        resp = self._fetch(
            f"https://graph.microsoft.com/v1.0/me/events/{input.provider_event_id}",
            {
                "method": "PATCH",
                "headers": {"Authorization": f"Bearer {token}"},
                "body": {"subject": input.summary[:255]},
            },
        )
        return self._map(resp, invitation_requested=bool(input.guest_email))

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
        if not self._fetch:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        token = self._token(workspace_id, user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        resp = self._fetch(
            f"https://graph.microsoft.com/v1.0/me/events/{provider_event_id}",
            {"method": "DELETE", "headers": {"Authorization": f"Bearer {token}"}},
        )
        status = int(resp.get("status") or 0)
        if status in {200, 204, 404}:
            return CalendarAdapterResult(
                ok=True, status="succeeded", provider="microsoft", provider_event_id=provider_event_id,
                host_event_created=True,
            )
        return CalendarAdapterResult(ok=False, status="failed", provider="microsoft", error_code="api_error")

    def get_event(
        self, *, workspace_id: str, user_id: str, provider_event_id: str
    ) -> CalendarAdapterResult:
        if not self._fetch:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        token = self._token(workspace_id, user_id)
        if not token:
            return CalendarAdapterResult(
                ok=False, status="not_configured", provider="microsoft", error_code="not_configured"
            )
        resp = self._fetch(
            f"https://graph.microsoft.com/v1.0/me/events/{provider_event_id}",
            {"method": "GET", "headers": {"Authorization": f"Bearer {token}"}},
        )
        return self._map(resp, invitation_requested=False)

    def _token(self, workspace_id: str, user_id: str) -> str | None:
        if self._get_token:
            return self._get_token(workspace_id, user_id)
        return (os.environ.get("KEPRIX_MICROSOFT_CALENDAR_ACCESS_TOKEN") or "").strip() or None

    def _map(self, resp: dict[str, Any], *, invitation_requested: bool) -> CalendarAdapterResult:
        status = int(resp.get("status") or 0)
        payload = resp.get("json") or {}
        if status == 429:
            return CalendarAdapterResult(
                ok=False, status="retryable", provider="microsoft", error_code="rate_limited", retry_after_ms=2000
            )
        if status < 200 or status >= 300:
            return CalendarAdapterResult(
                ok=False,
                status="failed" if status else "not_configured",
                provider="microsoft",
                error_code="api_error" if status else "not_configured",
                error_message=str(payload.get("error", {}).get("message") or "")[:300],
            )
        attendees: list[CalendarAttendeeSnapshot] = []
        for a in payload.get("attendees") or []:
            st = ((a.get("status") or {}).get("response")) or a.get("responseStatus")
            resp_s, del_s = map_microsoft_response(st)
            email = ((a.get("emailAddress") or {}).get("address")) or a.get("email") or ""
            attendees.append(
                CalendarAttendeeSnapshot(email=str(email), response_status=resp_s, delivery_state=del_s)
            )
        return CalendarAdapterResult(
            ok=True,
            status="succeeded",
            provider="microsoft",
            provider_event_id=str(payload.get("id") or "") or None,
            etag=payload.get("@odata.etag"),
            html_link=payload.get("webLink"),
            attendees=attendees,
            host_event_created=True,
            invitation_send_requested=invitation_requested,
            invitation_delivery_state=("sent" if invitation_requested else "unknown"),
        )
