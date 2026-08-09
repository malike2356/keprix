"""Concierge Zoom connection surface (Prompt 632)."""

from __future__ import annotations

from typing import Any

from keprix.vical.zoom_oauth import (
    exchange_zoom_code,
    revoke_zoom_tokens,
    test_zoom_connection,
    zoom_authorize_url,
    zoom_connection_status,
)


def connection_snapshot(workspace_id: str, user_id: str) -> dict[str, Any]:
    status = zoom_connection_status(workspace_id, user_id)
    return {
        **status,
        "fallback": {
            "staticRoomUrl": True,
            "label": "unmanaged_static_url",
            "icsFallback": True,
            "claimsManagedZoom": False,
        },
        "actions": ["connect", "reconnect", "revoke", "test"],
    }


def begin_connect(
    *,
    workspace_id: str,
    user_id: str,
    redirect_uri: str,
    state: str | None = None,
) -> dict[str, Any]:
    st = state or f"{workspace_id}:{user_id}"
    url = zoom_authorize_url(redirect_uri=redirect_uri, state=st)
    if not url:
        return {"ok": False, "error_code": "not_configured", **connection_snapshot(workspace_id, user_id)}
    return {"ok": True, "authorizeUrl": url, "state": st, **connection_snapshot(workspace_id, user_id)}


def complete_connect(
    *,
    workspace_id: str,
    user_id: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    tokens = exchange_zoom_code(
        code, redirect_uri=redirect_uri, workspace_id=workspace_id, user_id=user_id
    )
    snap = connection_snapshot(workspace_id, user_id)
    return {
        "ok": True,
        "accountEmail": tokens.account_email,
        **snap,
        # never return tokens
    }


def revoke_connection(workspace_id: str, user_id: str) -> dict[str, Any]:
    revoked = revoke_zoom_tokens(workspace_id, user_id)
    return {"ok": True, "revoked": revoked, **connection_snapshot(workspace_id, user_id)}


def test_connection(workspace_id: str, user_id: str) -> dict[str, Any]:
    return test_zoom_connection(workspace_id, user_id)


__all__ = [
    "begin_connect",
    "complete_connect",
    "connection_snapshot",
    "revoke_connection",
    "test_connection",
]
