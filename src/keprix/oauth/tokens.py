"""Shared OAuth token exchange and vault storage."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from keprix.security.vault_service import get_vault_service


def google_auth_url(*, state: str = "") -> str:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    redirect = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def microsoft_auth_url(*, scope: str, state: str = "") -> str:
    client_id = os.environ.get("MICROSOFT_OAUTH_CLIENT_ID", "")
    redirect = os.environ.get("MICROSOFT_OAUTH_REDIRECT_URI", "")
    tenant = os.environ.get("MICROSOFT_OAUTH_TENANT_ID", "common")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": scope,
        "state": state,
    }
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urlencode(params)}"


async def exchange_google_code(code: str, *, redirect_uri: str | None = None) -> dict[str, Any]:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect = redirect_uri or os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
        data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
        return data


async def exchange_microsoft_code(
    code: str, *, scope: str, redirect_uri: str | None = None
) -> dict[str, Any]:
    client_id = os.environ.get("MICROSOFT_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("MICROSOFT_OAUTH_CLIENT_SECRET", "")
    redirect = redirect_uri or os.environ.get("MICROSOFT_OAUTH_REDIRECT_URI", "")
    tenant = os.environ.get("MICROSOFT_OAUTH_TENANT_ID", "common")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
                "scope": scope,
            },
        )
        response.raise_for_status()
        data = response.json()
        data["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
        return data


async def store_oauth_tokens(
    user_id: str,
    *,
    provider: str,
    label: str,
    tokens: dict[str, Any],
    existing_vault_id: str | None = None,
) -> str:
    vault = get_vault_service()
    if existing_vault_id:
        await vault.update_oauth_bundle(existing_vault_id, user_id, tokens)
        return existing_vault_id
    return await vault.store_oauth_bundle(user_id, provider=provider, label=label, tokens=tokens)


async def load_oauth_tokens(vault_item_id: str, user_id: str) -> dict[str, Any]:
    return await get_vault_service().get_oauth_bundle(vault_item_id, user_id)


async def refresh_google_tokens(vault_item_id: str, user_id: str) -> dict[str, Any]:
    tokens = await load_oauth_tokens(vault_item_id, user_id)
    refresh = tokens.get("refresh_token")
    if not refresh:
        return tokens
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
        tokens.update(data)
        tokens["expires_at"] = int(time.time()) + int(data.get("expires_in", 3600))
    await get_vault_service().update_oauth_bundle(vault_item_id, user_id, tokens)
    return tokens
