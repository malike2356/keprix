"""Contact sync HTTP routes."""

from __future__ import annotations

import os
import uuid
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, get_optional_current_user
from keprix.contacts.google_oauth_config import (
    clear_google_oauth_app,
    get_google_oauth_app,
    google_contacts_redirect_uri,
    public_google_oauth_status,
    save_google_oauth_app,
)
from keprix.contacts.sync.scheduler import (
    get_sync_source,
    list_sync_sources,
    patch_sync_source,
    register_sync_source,
    run_sync,
    unregister_sync_source,
)
from keprix.oauth.tokens import (
    exchange_google_code,
    exchange_microsoft_code,
    store_oauth_tokens,
)

router = APIRouter(prefix="/api/contacts/sync", tags=["contacts-sync"])

GOOGLE_CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"
MS_CONTACTS_SCOPE = "Contacts.Read offline_access User.Read"


def _uid(user: dict | None) -> str:
    if not user:
        return "local"
    return str(user.get("id") or user.get("username") or "local")


def _microsoft_contacts_redirect() -> str:
    dedicated = os.environ.get("MICROSOFT_CONTACTS_OAUTH_REDIRECT_URI", "").strip()
    if dedicated:
        return dedicated
    base = os.environ.get("MICROSOFT_OAUTH_REDIRECT_URI", "").strip()
    if "/api/contacts/sync/microsoft/callback" in base:
        return base
    if base and "/oauth/microsoft/callback" in base:
        return base.replace("/oauth/microsoft/callback", "/api/contacts/sync/microsoft/callback")
    if base and "/api/email/" in base:
        return base.rsplit("/api/", 1)[0] + "/api/contacts/sync/microsoft/callback"
    api = os.environ.get("KEPRIX_API_URL") or os.environ.get("API_PUBLIC_URL") or "http://localhost:3334"
    return f"{api.rstrip('/')}/api/contacts/sync/microsoft/callback"


def _frontend_sync_url(*, connected: str, error: str | None = None) -> str:
    base = (
        os.environ.get("KEPRIX_FRONTEND_URL")
        or os.environ.get("FRONTEND_URL")
        or "http://localhost:3000"
    ).rstrip("/")
    params = {"connected": connected}
    if error:
        params["error"] = error[:200]
    return f"{base}/contacts/sync?{urlencode(params)}"


class CardDAVSourceCreate(BaseModel):
    display_name: str
    carddav_url: str
    carddav_username: str
    carddav_password: str
    sync_interval_minutes: int = Field(default=60, ge=5, le=10080)


class SyncSourcePatch(BaseModel):
    sync_enabled: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    display_name: str | None = None


class GoogleOAuthAppBody(BaseModel):
    client_id: str
    client_secret: str


@router.get("/sources")
async def sync_sources(user: dict = Depends(get_current_user)) -> list[dict[str, Any]]:
    return await list_sync_sources(user_id=_uid(user))


@router.get("/google/config")
async def google_oauth_config_status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    full = await get_google_oauth_app(_uid(user))
    return public_google_oauth_status(full)


@router.put("/google/config")
async def google_oauth_config_save(
    body: GoogleOAuthAppBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    try:
        return await save_google_oauth_app(_uid(user), body.client_id, body.client_secret)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/google/config")
async def google_oauth_config_clear(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await clear_google_oauth_app(_uid(user))


@router.post("/sources")
async def add_carddav_source(
    body: CardDAVSourceCreate, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    uid = _uid(user)
    if not body.carddav_url.strip() or not body.carddav_username.strip() or not body.carddav_password:
        raise HTTPException(400, "CardDAV URL, username, and password are required")
    vault_id = await store_oauth_tokens(
        uid,
        provider="carddav",
        label=f"CardDAV: {body.display_name}",
        tokens={"password": body.carddav_password},
    )
    source = {
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "provider": "carddav",
        "display_name": body.display_name.strip(),
        "vault_token_id": vault_id,
        "carddav_url": body.carddav_url.strip(),
        "carddav_username": body.carddav_username.strip(),
        "sync_enabled": True,
        "sync_interval_minutes": body.sync_interval_minutes,
        "contact_count": 0,
    }
    saved = await register_sync_source(source)
    sync_result = await run_sync(saved["id"])
    return {**saved, "initial_sync": sync_result}


@router.patch("/sources/{source_id}")
async def update_sync_source(
    source_id: str, body: SyncSourcePatch, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    updated = await patch_sync_source(
        source_id, body.model_dump(exclude_unset=True), user_id=_uid(user)
    )
    if updated is None:
        raise HTTPException(404, "Sync source not found")
    return updated


@router.delete("/sources/{source_id}", status_code=200)
async def delete_sync_source(
    source_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    if not await unregister_sync_source(source_id, user_id=_uid(user)):
        raise HTTPException(404, "Sync source not found")
    return {"ok": True, "id": source_id}


@router.get("/google/auth")
async def google_contacts_auth(user: dict = Depends(get_current_user)) -> dict[str, str]:
    uid = _uid(user)
    app = await get_google_oauth_app(uid)
    if not app["configured"]:
        raise HTTPException(
            501,
            "Google OAuth not configured. Save your Google Client ID and Secret first.",
        )
    redirect = app["redirect_uri"] or google_contacts_redirect_uri()
    params = {
        "client_id": app["client_id"],
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": GOOGLE_CONTACTS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": uid,
    }
    return {"auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
async def google_contacts_callback(
    code: str = "",
    state: str = "",
    user: dict | None = Depends(get_optional_current_user),
):
    if not code:
        return RedirectResponse(_frontend_sync_url(connected="google", error="missing_code"), status_code=302)
    uid = state.strip() or _uid(user)
    try:
        app = await get_google_oauth_app(uid)
        if not app["configured"]:
            return RedirectResponse(
                _frontend_sync_url(connected="google", error="oauth_app_not_configured"),
                status_code=302,
            )
        tokens = await exchange_google_code(
            code,
            redirect_uri=app["redirect_uri"],
            client_id=app["client_id"],
            client_secret=app["client_secret"],
        )
        vault_id = await store_oauth_tokens(
            uid, provider="google", label="Google Contacts", tokens=tokens
        )
        source = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "provider": "google",
            "display_name": "Google Contacts",
            "vault_token_id": vault_id,
            "sync_enabled": True,
            "sync_interval_minutes": 60,
            "contact_count": 0,
        }
        await register_sync_source(source)
        result = await run_sync(source["id"])
        if result.get("error"):
            return RedirectResponse(
                _frontend_sync_url(connected="google", error=str(result["error"])),
                status_code=302,
            )
        return RedirectResponse(_frontend_sync_url(connected="google"), status_code=302)
    except Exception as exc:
        return RedirectResponse(
            _frontend_sync_url(connected="google", error=str(exc)), status_code=302
        )


@router.get("/microsoft/auth")
async def microsoft_contacts_auth(user: dict = Depends(get_current_user)) -> dict[str, str]:
    client_id = os.environ.get("MICROSOFT_OAUTH_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(501, "Microsoft OAuth not configured")
    redirect = _microsoft_contacts_redirect()
    tenant = os.environ.get("MICROSOFT_OAUTH_TENANT_ID", "common")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": MS_CONTACTS_SCOPE,
        "state": _uid(user),
    }
    return {
        "auth_url": (
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"
        )
    }


@router.get("/microsoft/callback")
async def microsoft_contacts_callback(
    code: str = "",
    state: str = "",
    user: dict | None = Depends(get_optional_current_user),
):
    if not code:
        return RedirectResponse(
            _frontend_sync_url(connected="microsoft", error="missing_code"), status_code=302
        )
    uid = state.strip() or _uid(user)
    try:
        tokens = await exchange_microsoft_code(
            code, scope=MS_CONTACTS_SCOPE, redirect_uri=_microsoft_contacts_redirect()
        )
        vault_id = await store_oauth_tokens(
            uid, provider="microsoft", label="Microsoft Contacts", tokens=tokens
        )
        source = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "provider": "microsoft",
            "display_name": "Microsoft Outlook",
            "vault_token_id": vault_id,
            "sync_enabled": True,
            "sync_interval_minutes": 60,
            "contact_count": 0,
        }
        await register_sync_source(source)
        result = await run_sync(source["id"])
        if result.get("error"):
            return RedirectResponse(
                _frontend_sync_url(connected="microsoft", error=str(result["error"])),
                status_code=302,
            )
        return RedirectResponse(_frontend_sync_url(connected="microsoft"), status_code=302)
    except Exception as exc:
        return RedirectResponse(
            _frontend_sync_url(connected="microsoft", error=str(exc)), status_code=302
        )


@router.post("/{source_id}/now")
async def sync_now(source_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    source = await get_sync_source(source_id, user_id=_uid(user))
    if source is None:
        raise HTTPException(404, "Sync source not found")
    return await run_sync(source_id)


@router.get("/{source_id}/status")
async def sync_status(source_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    source = await get_sync_source(source_id, user_id=_uid(user))
    if source is None:
        raise HTTPException(404, "Sync source not found")
    return {
        "id": source["id"],
        "provider": source["provider"],
        "display_name": source["display_name"],
        "last_full_sync_at": source.get("last_full_sync_at"),
        "last_delta_sync_at": source.get("last_delta_sync_at"),
        "last_sync_error": source.get("last_sync_error"),
        "contact_count": source.get("contact_count", 0),
        "sync_enabled": source.get("sync_enabled", True),
        "sync_interval_minutes": source.get("sync_interval_minutes", 60),
    }
