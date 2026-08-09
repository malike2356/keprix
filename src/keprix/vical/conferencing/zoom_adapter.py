"""Zoom Meetings adapter with user OAuth (Prompt 632).

Host start_url stays on a private field only. Waiting room / passcode are not weakened.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from keprix.vical.conferencing.types import (
    ConferenceAdapterResult,
    ConferenceCreateInput,
    ConferenceDeleteInput,
    ConferenceUpdateInput,
)
from keprix.vical.zoom_oauth import (
    ZoomTokenBundle,
    is_zoom_oauth_configured,
    load_zoom_tokens,
    refresh_zoom_access_token,
    save_zoom_tokens,
)

logger = logging.getLogger(__name__)

ZoomFetch = Callable[[str, dict[str, Any]], dict[str, Any]]


class ZoomConferencingError(RuntimeError):
    def __init__(
        self,
        message: str,
        code: str,
        *,
        retry_after_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retry_after_ms = retry_after_ms


def _default_fetch(url: str, init: dict[str, Any]) -> dict[str, Any]:
    method = str(init.get("method") or "GET").upper()
    headers = dict(init.get("headers") or {})
    data = init.get("body")
    body_bytes = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body_bytes = json.dumps(data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body_bytes = data.encode("utf-8")
        else:
            body_bytes = data
    req = Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
            payload = json.loads(raw) if raw.strip() else {}
            return {"status": status, "json": payload, "headers": dict(resp.headers.items())}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            payload = {"message": raw}
        return {
            "status": int(exc.code),
            "json": payload,
            "headers": dict(exc.headers.items()) if exc.headers else {},
        }
    except URLError as exc:
        raise ZoomConferencingError(str(exc.reason), "api_error") from exc


def _retry_after_ms(headers: dict[str, Any]) -> int | None:
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        seconds = float(raw)
        return int(min(seconds * 1000, 60_000))
    except Exception:
        return None


class ZoomConferencingAdapter:
    provider = "zoom"

    def __init__(
        self,
        *,
        fetch_impl: ZoomFetch | None = None,
        get_tokens: Callable[[str, str], ZoomTokenBundle | None] | None = None,
        save_tokens: Callable[[str, str, ZoomTokenBundle], None] | None = None,
        meeting_by_idempotency: dict[str, ConferenceAdapterResult] | None = None,
    ) -> None:
        self._fetch = fetch_impl or _default_fetch
        self._get_tokens = get_tokens or (lambda ws, uid: load_zoom_tokens(ws, uid))
        self._save_tokens = save_tokens or (
            lambda ws, uid, tokens: save_zoom_tokens(ws, uid, tokens)
        )
        self._meeting_by_key = meeting_by_idempotency if meeting_by_idempotency is not None else {}

    def create_meeting(self, input: ConferenceCreateInput) -> ConferenceAdapterResult:
        key = input.idempotency_key or ""
        if key and key in self._meeting_by_key:
            existing = self._meeting_by_key[key]
            return ConferenceAdapterResult(
                ok=existing.ok,
                provider="zoom",
                status="duplicate" if existing.ok else existing.status,
                meeting_id=existing.meeting_id,
                join_url=existing.join_url,
                host_start_url=existing.host_start_url,
                passcode=existing.passcode,
                duplicate=True,
                managed=True,
                error_code=existing.error_code,
                detail=existing.detail,
            )

        try:
            token = self._resolve_access_token(input.workspace_id, input.user_id)
        except ZoomConferencingError as exc:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code=exc.code,
                detail=str(exc),
                managed=True,
                retry_after_ms=exc.retry_after_ms,
            )

        body = {
            "topic": input.topic[:200],
            "type": 2,
            "start_time": input.starts_at,
            "duration": max(15, min(480, int(input.duration_minutes))),
            "timezone": input.timezone or "UTC",
            "settings": {
                # Preserve account defaults; do not disable waiting room / passcode.
                "waiting_room": True,
            },
        }
        if input.agenda:
            body["agenda"] = str(input.agenda)[:2000]

        resp = self._fetch(
            "https://api.zoom.us/v2/users/me/meetings",
            {
                "method": "POST",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                "body": body,
            },
        )
        status = int(resp.get("status") or 0)
        payload = resp.get("json") or {}
        headers = resp.get("headers") or {}

        if status == 401:
            result = ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code="expired_token",
                detail="Zoom access token rejected",
                managed=True,
            )
            if key:
                self._meeting_by_key[key] = result
            return result
        if status == 429:
            result = ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code="rate_limited",
                detail="Zoom rate limited",
                managed=True,
                retry_after_ms=_retry_after_ms(headers),
            )
            if key:
                self._meeting_by_key[key] = result
            return result
        if status < 200 or status >= 300:
            result = ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code="api_error",
                detail=str(payload.get("message") or payload)[:300],
                managed=True,
            )
            if key:
                self._meeting_by_key[key] = result
            return result

        result = ConferenceAdapterResult(
            ok=True,
            provider="zoom",
            status="created",
            meeting_id=str(payload.get("id") or ""),
            join_url=str(payload.get("join_url") or "") or None,
            host_start_url=str(payload.get("start_url") or "") or None,
            passcode=str(payload.get("password") or "") or None,
            managed=True,
        )
        if key:
            self._meeting_by_key[key] = result
        # Never log host_start_url
        logger.info(
            "zoom meeting created meeting_id=%s workspace=%s",
            result.meeting_id,
            input.workspace_id,
        )
        return result

    def update_meeting(self, input: ConferenceUpdateInput) -> ConferenceAdapterResult:
        try:
            token = self._resolve_access_token(input.workspace_id, input.user_id)
        except ZoomConferencingError as exc:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code=exc.code,
                detail=str(exc),
                managed=True,
            )
        patch: dict[str, Any] = {}
        if input.topic:
            patch["topic"] = input.topic[:200]
        if input.starts_at:
            patch["start_time"] = input.starts_at
        if input.duration_minutes is not None:
            patch["duration"] = max(15, min(480, int(input.duration_minutes)))
        if input.timezone:
            patch["timezone"] = input.timezone
        resp = self._fetch(
            f"https://api.zoom.us/v2/meetings/{input.meeting_id}",
            {
                "method": "PATCH",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                "body": patch,
            },
        )
        status = int(resp.get("status") or 0)
        if status == 429:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                meeting_id=input.meeting_id,
                error_code="rate_limited",
                managed=True,
                retry_after_ms=_retry_after_ms(resp.get("headers") or {}),
            )
        if status < 200 or status >= 300:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                meeting_id=input.meeting_id,
                error_code="api_error",
                detail=str((resp.get("json") or {}).get("message") or "")[:300],
                managed=True,
            )
        return ConferenceAdapterResult(
            ok=True,
            provider="zoom",
            status="updated",
            meeting_id=input.meeting_id,
            managed=True,
        )

    def delete_meeting(self, input: ConferenceDeleteInput) -> ConferenceAdapterResult:
        try:
            token = self._resolve_access_token(input.workspace_id, input.user_id)
        except ZoomConferencingError as exc:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                error_code=exc.code,
                detail=str(exc),
                managed=True,
            )
        resp = self._fetch(
            f"https://api.zoom.us/v2/meetings/{input.meeting_id}",
            {
                "method": "DELETE",
                "headers": {"Authorization": f"Bearer {token}"},
            },
        )
        status = int(resp.get("status") or 0)
        if status in {200, 204, 404}:
            return ConferenceAdapterResult(
                ok=True,
                provider="zoom",
                status="deleted",
                meeting_id=input.meeting_id,
                managed=True,
            )
        if status == 429:
            return ConferenceAdapterResult(
                ok=False,
                provider="zoom",
                status="error",
                meeting_id=input.meeting_id,
                error_code="rate_limited",
                managed=True,
                retry_after_ms=_retry_after_ms(resp.get("headers") or {}),
            )
        return ConferenceAdapterResult(
            ok=False,
            provider="zoom",
            status="error",
            meeting_id=input.meeting_id,
            error_code="api_error",
            managed=True,
        )

    def _resolve_access_token(self, workspace_id: str, user_id: str) -> str:
        tokens = self._get_tokens(workspace_id, user_id)
        if not tokens or not tokens.access_token:
            if not is_zoom_oauth_configured():
                raise ZoomConferencingError("Zoom OAuth not configured", "not_configured")
            raise ZoomConferencingError("Zoom not connected for user", "not_configured")
        # Refresh path when expired marker present
        if tokens.expired:
            refreshed = refresh_zoom_access_token(workspace_id, user_id, tokens=tokens)
            if not refreshed or not refreshed.access_token:
                raise ZoomConferencingError("Zoom token refresh failed", "expired_token")
            self._save_tokens(workspace_id, user_id, refreshed)
            return refreshed.access_token
        return tokens.access_token


__all__ = ["ZoomConferencingAdapter", "ZoomConferencingError"]
