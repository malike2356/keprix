"""Hermetic Zoom / Google / SMTP fakes for Customer Concierge e2e (Prompt 635)."""

from __future__ import annotations

from typing import Any, Callable

from keprix.vical.calendar.google_adapter import GoogleCalendarAdapter
from keprix.vical.conferencing.zoom_adapter import ZoomConferencingAdapter
from keprix.vical.zoom_oauth import ZoomTokenBundle


FetchImpl = Callable[[str, dict[str, Any]], dict[str, Any]]


def zoom_success_fetch(meeting_id: int = 900001) -> FetchImpl:
    def _fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
        method = str(init.get("method") or "GET").upper()
        if "meetings" in url and method == "POST":
            return {
                "status": 201,
                "headers": {},
                "json": {
                    "id": meeting_id,
                    "join_url": f"https://zoom.us/j/{meeting_id}",
                    "start_url": f"https://zoom.us/s/{meeting_id}?zak=HOSTSECRET",
                    "password": "pincode",
                },
            }
        if "meetings" in url and method in {"PATCH", "DELETE"}:
            return {"status": 204, "headers": {}, "json": {}}
        return {"status": 200, "headers": {}, "json": {}}

    return _fetch


def zoom_revoked_fetch() -> FetchImpl:
    def _fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
        return {"status": 401, "headers": {}, "json": {"code": 124, "message": "Invalid access token"}}

    return _fetch


def google_success_fetch(event_id: str = "gcal-e2e-1") -> FetchImpl:
    def _fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
        method = str(init.get("method") or "GET").upper()
        if method == "POST" or method == "PATCH":
            return {
                "status": 200,
                "headers": {},
                "json": {
                    "id": event_id,
                    "etag": "etag-e2e",
                    "htmlLink": f"https://calendar.google.com/event?eid={event_id}",
                    "attendees": [{"email": "guest@example.com", "responseStatus": "needsAction"}],
                },
            }
        if method == "DELETE":
            return {"status": 204, "headers": {}, "json": {}}
        if method == "GET":
            return {
                "status": 200,
                "headers": {},
                "json": {
                    "id": event_id,
                    "attendees": [{"email": "guest@example.com", "responseStatus": "accepted"}],
                },
            }
        return {"status": 200, "headers": {}, "json": {}}

    return _fetch


def google_outage_fetch() -> FetchImpl:
    def _fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
        return {"status": 503, "headers": {}, "json": {"error": {"message": "service unavailable"}}}

    return _fetch


def build_hermetic_zoom(
    *,
    fetch_impl: FetchImpl | None = None,
    tokens: dict[str, ZoomTokenBundle] | None = None,
) -> ZoomConferencingAdapter:
    bag = tokens if tokens is not None else {
        "host1": ZoomTokenBundle(access_token="hermetic-zoom", refresh_token="r", expires_at=9e12)
    }
    return ZoomConferencingAdapter(
        fetch_impl=fetch_impl or zoom_success_fetch(),
        get_tokens=lambda ws, uid: bag.get(uid) or bag.get("host1"),
        save_tokens=lambda ws, uid, t: bag.__setitem__(uid, t),
        meeting_by_idempotency={},
    )


def build_hermetic_google(
    *,
    fetch_impl: FetchImpl | None = None,
) -> GoogleCalendarAdapter:
    return GoogleCalendarAdapter(
        fetch_impl=fetch_impl or google_success_fetch(),
        get_access_token=lambda ws, uid: "hermetic-google",
        create_cache={},
    )


def smtp_delivery_evidence(message_id: str = "smtp-e2e-1") -> dict[str, Any]:
    """Fake transport ACK; never claims delivery without evidence id."""
    return {
        "ok": True,
        "provider": "hermetic_smtp",
        "evidence": f"smtp:{message_id}",
        "status": "sent",
    }


__all__ = [
    "build_hermetic_google",
    "build_hermetic_zoom",
    "google_outage_fetch",
    "google_success_fetch",
    "smtp_delivery_evidence",
    "zoom_revoked_fetch",
    "zoom_success_fetch",
]
