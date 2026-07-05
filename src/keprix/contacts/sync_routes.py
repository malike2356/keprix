"""Contact sync HTTP routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.contacts.sync.google import GoogleContactsConnector
from keprix.contacts.sync.scheduler import (
    get_sync_source,
    list_sync_sources,
    register_sync_source,
    run_sync,
)
from keprix.oauth.tokens import (
    exchange_google_code,
    exchange_microsoft_code,
    google_auth_url,
    microsoft_auth_url,
    store_oauth_tokens,
)

router = APIRouter(prefix="/api/contacts/sync", tags=["contacts-sync"])

GOOGLE_CONTACTS_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"
MS_CONTACTS_SCOPE = "Contacts.Read offline_access"


def _user_id(request: Request) -> str:
    return request.headers.get("x-user-id", "").strip() or "local"


class CardDAVSourceCreate(BaseModel):
    display_name: str
    carddav_url: str
    carddav_username: str
    carddav_password: str
    sync_interval_minutes: int = 60


@router.get("/sources")
async def sync_sources() -> list[dict[str, Any]]:
    return await list_sync_sources()


@router.post("/sources")
async def add_carddav_source(body: CardDAVSourceCreate, request: Request) -> dict[str, Any]:
    user = _user_id(request)
    vault_id = await store_oauth_tokens(
        user,
        provider="carddav",
        label=f"CardDAV: {body.display_name}",
        tokens={"password": body.carddav_password},
    )
    source = {
        "id": str(uuid.uuid4()),
        "user_id": user,
        "provider": "carddav",
        "display_name": body.display_name,
        "vault_token_id": vault_id,
        "carddav_url": body.carddav_url,
        "carddav_username": body.carddav_username,
        "sync_enabled": True,
        "sync_interval_minutes": body.sync_interval_minutes,
        "contact_count": 0,
    }
    await register_sync_source(source)
    return source


@router.delete("/sources/{source_id}", status_code=200)
async def delete_sync_source(source_id: str) -> None:
    sources = await list_sync_sources()
    if not any(s["id"] == source_id for s in sources):
        raise HTTPException(404, "Sync source not found")


@router.get("/google/auth")
async def google_contacts_auth() -> dict[str, str]:
    import os
    from urllib.parse import urlencode

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    redirect = os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3333/api/contacts/sync/google/callback"
    )
    if not client_id:
        raise HTTPException(501, "Google OAuth not configured")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect.replace("/oauth/google/callback", "/api/contacts/sync/google/callback"),
        "response_type": "code",
        "scope": GOOGLE_CONTACTS_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
async def google_contacts_callback(code: str, request: Request) -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Missing code")
    user = _user_id(request)
    tokens = await exchange_google_code(code)
    vault_id = await store_oauth_tokens(
        user, provider="google", label="Google Contacts", tokens=tokens
    )
    source = {
        "id": str(uuid.uuid4()),
        "user_id": user,
        "provider": "google",
        "display_name": "Google Contacts",
        "vault_token_id": vault_id,
        "sync_enabled": True,
        "sync_interval_minutes": 60,
        "contact_count": 0,
    }
    await register_sync_source(source)
    result = await run_sync(source["id"])
    return {"source_id": source["id"], "sync": result}


@router.get("/microsoft/auth")
async def microsoft_contacts_auth() -> dict[str, str]:
    return {"auth_url": microsoft_auth_url(scope=MS_CONTACTS_SCOPE)}


@router.get("/microsoft/callback")
async def microsoft_contacts_callback(code: str, request: Request) -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Missing code")
    user = _user_id(request)
    tokens = await exchange_microsoft_code(code, scope=MS_CONTACTS_SCOPE)
    vault_id = await store_oauth_tokens(
        user, provider="microsoft", label="Microsoft Contacts", tokens=tokens
    )
    source = {
        "id": str(uuid.uuid4()),
        "user_id": user,
        "provider": "microsoft",
        "display_name": "Microsoft Outlook",
        "vault_token_id": vault_id,
        "sync_enabled": True,
        "sync_interval_minutes": 60,
        "contact_count": 0,
    }
    await register_sync_source(source)
    result = await run_sync(source["id"])
    return {"source_id": source["id"], "sync": result}


@router.post("/{source_id}/now")
async def sync_now(source_id: str) -> dict[str, Any]:
    source = await get_sync_source(source_id)
    if source is None:
        raise HTTPException(404, "Sync source not found")
    return await run_sync(source_id)


@router.get("/{source_id}/status")
async def sync_status(source_id: str) -> dict[str, Any]:
    source = await get_sync_source(source_id)
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
    }
