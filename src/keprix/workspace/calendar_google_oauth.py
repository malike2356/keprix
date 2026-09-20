"""Google Calendar OAuth (refreshable tokens). Gmail app passwords cannot access Calendar."""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from keprix.auth.config import data_dir

GOOGLE_CALENDAR_SCOPE = " ".join(
    (
        "https://www.googleapis.com/auth/calendar.events",
        "openid",
        "email",
    )
)
_STATE_TTL_SECONDS = 15 * 60


def google_calendar_redirect_uri() -> str:
    dedicated = os.environ.get("GOOGLE_CALENDAR_OAUTH_REDIRECT_URI", "").strip()
    if dedicated:
        return dedicated
    api = (os.environ.get("KEPRIX_API_URL") or os.environ.get("API_PUBLIC_URL") or "").strip()
    if api:
        return f"{api.rstrip('/')}/api/workspace/calendar/google/callback"
    port = os.environ.get("BACKEND_PORT") or "9119"
    host = os.environ.get("KEPRIX_DASHBOARD_HOST") or "127.0.0.1"
    return f"http://{host}:{port}/api/workspace/calendar/google/callback"


def calendar_frontend_return_url(*, error: str | None = None) -> str:
    base = (
        os.environ.get("KEPRIX_FRONTEND_URL")
        or os.environ.get("FRONTEND_URL")
        or f"http://127.0.0.1:{os.environ.get('KEPRIX_DASHBOARD_FRONTEND_PORT', '9120')}"
    ).rstrip("/")
    params: dict[str, str] = {"google": "error" if error else "connected"}
    if error:
        params["error"] = error[:200]
    return f"{base}/calendar?{urlencode(params)}"


def _state_path() -> Path:
    return Path(data_dir()) / "calendar_google_oauth_state.json"


def save_oauth_state(*, user_id: str, source_id: str | None = None) -> str:
    state = secrets.token_urlsafe(24)
    payload = {
        "state": state,
        "user_id": user_id,
        "source_id": source_id,
        "created_at": time.time(),
    }
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return state


def take_oauth_state(state: str) -> dict[str, Any] | None:
    path = _state_path()
    if not path.is_file() or not state.strip():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if str(payload.get("state") or "") != state.strip():
        return None
    created = float(payload.get("created_at") or 0)
    if created and (time.time() - created) > _STATE_TTL_SECONDS:
        return None
    try:
        path.unlink()
    except OSError:
        pass
    return payload


async def calendar_google_oauth_app(user_id: str) -> dict[str, Any]:
    from keprix.contacts.google_oauth_config import get_google_oauth_app

    full = await get_google_oauth_app(user_id)
    full["redirect_uri"] = google_calendar_redirect_uri()
    return full


def public_calendar_google_oauth(full: dict[str, Any]) -> dict[str, Any]:
    from keprix.contacts.google_oauth_config import public_google_oauth_status

    public = public_google_oauth_status(full)
    public["calendar_api_hint"] = (
        "Enable Google Calendar API on the same Cloud project, then add the redirect URI."
    )
    return public


async def save_calendar_google_oauth_app(user_id: str, client_id: str, client_secret: str) -> dict[str, Any]:
    from keprix.contacts.google_oauth_config import save_google_oauth_app

    await save_google_oauth_app(user_id, client_id, client_secret)
    return public_calendar_google_oauth(await calendar_google_oauth_app(user_id))
