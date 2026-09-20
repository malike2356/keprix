"""Calendar workspace routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from keprix.auth.dependencies import get_current_user, get_optional_current_user
from keprix.workspace.calendar_sync import (
    PROVIDER_PRESETS,
    looks_like_gmail_app_password,
    google_app_password_error,
    push_event_to_source,
    sync_caldav,
    sync_one_source,
)
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import CaldavSourceCreate, CaldavSourceUpdate, CalendarEventCreate, CalendarEventUpdate
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/workspace/calendar", tags=["workspace-calendar"])


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


async def _maybe_push_event(user: dict, event: dict[str, Any]) -> dict[str, Any]:
    source = workspace_repo.default_push_source(user)
    if not source:
        return event
    try:
        ok = await push_event_to_source(user, source, event, workspace_repo)
        if ok:
            return workspace_repo.update_event(
                user,
                event["id"],
                caldav_source_id=source["id"],
                external_etag=True,
            )
    except Exception:
        pass
    return event


@router.post("/events", status_code=201)
async def create_event(body: CalendarEventCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    event = workspace_repo.create_event(user, **body.model_dump())
    return await _maybe_push_event(user, event)


@router.get("/events")
async def list_events(
    user: dict = Depends(get_current_user),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
) -> dict[str, Any]:
    rows = workspace_repo.list_events(user, start=start, end=end)
    return {"items": rows}


@router.get("/events/{event_id}")
async def get_event(event_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.get_event(user, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    body: CalendarEventUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        event = workspace_repo.update_event(user, event_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None
    if event.get("external_readonly"):
        return event
    return await _maybe_push_event(user, event)


@router.delete("/events/{event_id}", status_code=200)
async def delete_event(event_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_event(user, event_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None


@router.get("/providers")
async def list_providers(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": PROVIDER_PRESETS}


@router.get("/auto-sync")
async def auto_sync_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.workspace.calendar_sync_scheduler import scheduler_status

    return scheduler_status()


@router.post("/sync")
async def trigger_sync(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    sources = workspace_repo.list_caldav_sources(user)
    return await sync_caldav(_user_id(user), sources)


@router.post("/sources/{source_id}/sync")
async def sync_source(source_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        source = workspace_repo.get_caldav_source(user, source_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None
    try:
        outcome = await sync_one_source(user, source, workspace_repo)
        workspace_repo.mark_source_synced(user, source_id, ok=True, message=outcome.get("message"))
        return outcome
    except Exception as exc:
        message = str(exc)
        workspace_repo.mark_source_synced(user, source_id, ok=False, message=message)
        raise HTTPException(status_code=400, detail=message) from None


@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": workspace_repo.list_caldav_sources(user)}


@router.post("/sources", status_code=201)
async def add_source(body: CaldavSourceCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    data = body.model_dump()
    provider = str(data.get("provider") or "caldav").lower()
    url = str(data.get("url") or "").strip()
    if provider == "google" and url.lower().endswith(".ics"):
        provider = "ics"
        data["provider"] = "ics"
    if provider == "ics" and not url:
        raise HTTPException(status_code=400, detail="ICS feed URL is required")
    if provider != "ics" and not url and not (
        provider == "google" and str(data.get("username") or "").strip()
    ):
        raise HTTPException(status_code=400, detail="CalDAV URL is required (or Google email as username)")
    if provider == "google" and looks_like_gmail_app_password(data.get("password") or ""):
        raise HTTPException(status_code=400, detail=google_app_password_error())
    if provider != "ics" and not data.get("password") and not data.get("vault_item_id"):
        raise HTTPException(status_code=400, detail="Password or access token is required for CalDAV sync")
    if provider == "ics":
        data["sync_direction"] = "pull"
        data["push_local_events"] = False
    elif data.get("push_local_events") is None and str(data.get("sync_direction") or "bidirectional") in {
        "bidirectional",
        "push",
    }:
        data["push_local_events"] = True
    source = workspace_repo.add_caldav_source(user, **data)
    try:
        full = workspace_repo.get_caldav_source(user, source["id"])
        outcome = await sync_one_source(user, full, workspace_repo)
        return workspace_repo.mark_source_synced(user, source["id"], ok=True, message=outcome.get("message"))
    except Exception as exc:
        return workspace_repo.mark_source_synced(user, source["id"], ok=False, message=str(exc))


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    body: CaldavSourceUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    data = body.model_dump(exclude_none=True)
    if looks_like_gmail_app_password(str(data.get("password") or "")):
        raise HTTPException(status_code=400, detail=google_app_password_error())
    url = str(data.get("url") or "").strip()
    if url.lower().endswith(".ics"):
        data["provider"] = "ics"
        data["sync_direction"] = "pull"
        data["push_local_events"] = False
    try:
        return workspace_repo.update_caldav_source(user, source_id, **data)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None


class GoogleOAuthAppBody(BaseModel):
    client_id: str = Field(min_length=8)
    client_secret: str = Field(min_length=8)


@router.get("/google/config")
async def google_oauth_config(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.workspace.calendar_google_oauth import calendar_google_oauth_app, public_calendar_google_oauth

    return public_calendar_google_oauth(await calendar_google_oauth_app(_user_id(user)))


@router.put("/google/config")
async def google_oauth_config_save(
    body: GoogleOAuthAppBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    from keprix.workspace.calendar_google_oauth import save_calendar_google_oauth_app

    try:
        return await save_calendar_google_oauth_app(_user_id(user), body.client_id, body.client_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/google/auth")
async def google_calendar_auth(user: dict = Depends(get_current_user)) -> dict[str, str]:
    from urllib.parse import urlencode

    from keprix.workspace.calendar_google_oauth import (
        GOOGLE_CALENDAR_SCOPE,
        calendar_google_oauth_app,
        google_calendar_redirect_uri,
        save_oauth_state,
    )

    uid = _user_id(user)
    app = await calendar_google_oauth_app(uid)
    if not app.get("configured"):
        raise HTTPException(
            status_code=501,
            detail="Google OAuth is not configured. Save a Google Cloud client ID and secret first.",
        )
    redirect = str(app.get("redirect_uri") or google_calendar_redirect_uri())
    state = save_oauth_state(user_id=uid)
    params = {
        "client_id": app["client_id"],
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": GOOGLE_CALENDAR_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {"auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
async def google_calendar_callback(
    code: str = "",
    state: str = "",
    _user: dict | None = Depends(get_optional_current_user),
):
    from keprix.oauth.tokens import exchange_google_code, store_oauth_tokens
    from keprix.workspace.calendar_google_oauth import (
        calendar_frontend_return_url,
        calendar_google_oauth_app,
        google_calendar_redirect_uri,
        take_oauth_state,
    )

    pending = take_oauth_state(state)
    if not code or not pending:
        return RedirectResponse(calendar_frontend_return_url(error="missing_code"), status_code=302)
    uid = str(pending.get("user_id") or "").strip()
    if not uid:
        return RedirectResponse(calendar_frontend_return_url(error="missing_user"), status_code=302)
    try:
        app = await calendar_google_oauth_app(uid)
        if not app.get("configured"):
            return RedirectResponse(calendar_frontend_return_url(error="oauth_app_not_configured"), status_code=302)
        tokens = await exchange_google_code(
            code,
            redirect_uri=str(app.get("redirect_uri") or google_calendar_redirect_uri()),
            client_id=app.get("client_id"),
            client_secret=app.get("client_secret"),
        )
        vault_id = await store_oauth_tokens(uid, provider="google", label="Google Calendar", tokens=tokens)
        user = {"id": uid}
        email = str(tokens.get("email") or "").strip()
        existing = next(
            (row for row in workspace_repo.list_caldav_sources(user) if str(row.get("provider") or "") == "google"),
            None,
        )
        if existing:
            source = workspace_repo.update_caldav_source(
                user,
                existing["id"],
                vault_item_id=vault_id,
                username=email or existing.get("username"),
            )
        else:
            source = workspace_repo.add_caldav_source(
                user,
                name="Google Calendar",
                provider="google",
                username=email,
                vault_item_id=vault_id,
                sync_direction="bidirectional",
                push_local_events=True,
                auto_sync=True,
            )
        full = workspace_repo.get_caldav_source(user, source["id"])
        try:
            outcome = await sync_one_source(user, full, workspace_repo)
            workspace_repo.mark_source_synced(user, source["id"], ok=True, message=outcome.get("message"))
        except Exception as exc:
            workspace_repo.mark_source_synced(user, source["id"], ok=False, message=str(exc))
            return RedirectResponse(calendar_frontend_return_url(error=str(exc)[:200]), status_code=302)
        return RedirectResponse(calendar_frontend_return_url(), status_code=302)
    except Exception as exc:
        return RedirectResponse(calendar_frontend_return_url(error=str(exc)[:200]), status_code=302)


@router.delete("/sources/{source_id}", status_code=200)
async def delete_source(
    source_id: str,
    user: dict = Depends(get_current_user),
    remove_events: bool = Query(False),
) -> dict[str, Any]:
    try:
        workspace_repo.delete_caldav_source(user, source_id, remove_events=remove_events)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found") from None
    return {"ok": True, "id": source_id}
