"""Secret redaction for conferencing payloads (Prompt 632)."""

from __future__ import annotations

import re
from typing import Any

_HOST_URL_KEYS = frozenset(
    {
        "host_start_url",
        "hostStartUrl",
        "start_url",
        "startUrl",
        "host_url",
        "hostUrl",
    }
)
_SECRET_KEYS = frozenset(
    {
        "access_token",
        "accessToken",
        "refresh_token",
        "refreshToken",
        "client_secret",
        "clientSecret",
        "authorization",
        "password",
        "secret",
    }
)
_ZOOM_START_URL_RE = re.compile(r"https?://[^\s]*zoom\.us/s/[^\s]+", re.I)


def redact_conferencing_payload(value: Any) -> Any:
    """Recursively strip host start URLs and OAuth secrets from nested payloads."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if k in _HOST_URL_KEYS or k in _SECRET_KEYS:
                continue
            out[k] = redact_conferencing_payload(v)
        return out
    if isinstance(value, list):
        return [redact_conferencing_payload(v) for v in value]
    if isinstance(value, str):
        return _ZOOM_START_URL_RE.sub("[redacted-host-start-url]", value)
    return value


def to_public_booking_view(booking_dict: dict[str, Any]) -> dict[str, Any]:
    """Public-safe booking view: join URL ok, host start URL never."""
    raw = dict(booking_dict)
    meta = dict(raw.get("metadata") or {})
    meta.pop("host_start_url", None)
    meta.pop("hostStartUrl", None)
    meta.pop("zoom_start_url", None)
    raw["metadata"] = meta
    # Ensure meeting_url is join URL only (never start URL)
    for key in ("meeting_url", "meetingUrl"):
        url = raw.get(key)
        if isinstance(url, str) and "zoom.us" in url.lower() and "/s/" in url:
            raw[key] = None
            raw["meetingUrlRedacted"] = True
    public = redact_conferencing_payload(raw)
    return public


__all__ = ["redact_conferencing_payload", "to_public_booking_view"]
