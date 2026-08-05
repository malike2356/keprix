"""Per-user Google OAuth app credentials for Contacts sync (BYOK)."""

from __future__ import annotations

import json
import os
from typing import Any

from keprix.security.vault_service import get_vault_service

_PROVIDER_TAG = "google_contacts_oauth_app"
_LABEL = "Google Contacts OAuth app"


def google_contacts_redirect_uri() -> str:
    dedicated = os.environ.get("GOOGLE_CONTACTS_OAUTH_REDIRECT_URI", "").strip()
    if dedicated:
        return dedicated
    base = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if "/api/contacts/sync/google/callback" in base:
        return base
    if base and "/oauth/google/callback" in base:
        return base.replace("/oauth/google/callback", "/api/contacts/sync/google/callback")
    if base and "/api/email/" in base:
        return base.rsplit("/api/", 1)[0] + "/api/contacts/sync/google/callback"
    api = (
        os.environ.get("KEPRIX_API_URL")
        or os.environ.get("API_PUBLIC_URL")
        or f"http://localhost:{os.environ.get('BACKEND_PORT', '3334')}"
    )
    return f"{api.rstrip('/')}/api/contacts/sync/google/callback"


def _env_client() -> tuple[str, str]:
    client_id = (
        os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        or os.environ.get("KEPRIX_GOOGLE_CLIENT_ID")
        or ""
    ).strip()
    client_secret = (
        os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        or os.environ.get("KEPRIX_GOOGLE_CLIENT_SECRET")
        or ""
    ).strip()
    return client_id, client_secret


async def _find_vault_item_id(user_id: str) -> str | None:
    vault = get_vault_service()
    items = await vault.list_items(user_id)
    for item in items:
        tags = set(item.tags or [])
        if _PROVIDER_TAG in tags or (
            item.category == "oauth_app" and "google_contacts" in tags
        ):
            return item.id
        if item.label == _LABEL:
            return item.id
    return None


async def get_google_oauth_app(user_id: str) -> dict[str, Any]:
    """Return public status plus usable secrets for auth/token exchange."""
    env_id, env_secret = _env_client()
    redirect_uri = google_contacts_redirect_uri()
    vault_id = await _find_vault_item_id(user_id)
    client_id = ""
    client_secret = ""
    source = "none"
    if vault_id:
        bundle = await get_vault_service().get_oauth_bundle(vault_id, user_id)
        client_id = str(bundle.get("client_id") or "").strip()
        client_secret = str(bundle.get("client_secret") or "").strip()
        if client_id and client_secret:
            source = "user"
    if not client_id or not client_secret:
        if env_id and env_secret:
            client_id, client_secret = env_id, env_secret
            source = "env"
            vault_id = None
    configured = bool(client_id and client_secret)
    return {
        "configured": configured,
        "source": source,
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_masked": _mask(client_id) if client_id else "",
        "redirect_uri": redirect_uri,
        "vault_item_id": vault_id,
        "people_api_hint": "Enable People API on the Google Cloud project for this OAuth client.",
    }


def public_google_oauth_status(full: dict[str, Any]) -> dict[str, Any]:
    return {
        "configured": full["configured"],
        "source": full["source"],
        "client_id_masked": full.get("client_id_masked") or "",
        "redirect_uri": full["redirect_uri"],
        "people_api_hint": full.get("people_api_hint"),
    }


async def save_google_oauth_app(user_id: str, client_id: str, client_secret: str) -> dict[str, Any]:
    client_id = client_id.strip()
    client_secret = client_secret.strip()
    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret are required")
    vault = get_vault_service()
    payload = {"client_id": client_id, "client_secret": client_secret}
    existing = await _find_vault_item_id(user_id)
    if existing:
        await vault.update_oauth_bundle(existing, user_id, payload)
    else:
        await vault.create_item(
            user_id,
            label=_LABEL,
            value=json.dumps(payload),
            category="oauth_app",
            tags=[_PROVIDER_TAG, "google_contacts"],
        )
    return public_google_oauth_status(await get_google_oauth_app(user_id))


async def clear_google_oauth_app(user_id: str) -> dict[str, Any]:
    vault_id = await _find_vault_item_id(user_id)
    if vault_id:
        await get_vault_service().delete_item(vault_id, user_id)
    return public_google_oauth_status(await get_google_oauth_app(user_id))


def _mask(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:10]}…{value[-6:]}"
