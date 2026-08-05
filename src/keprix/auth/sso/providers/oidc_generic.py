"""Generic OIDC provider for workspace SSO."""

from __future__ import annotations

import time
import urllib.parse
from typing import Any

import httpx

from keprix.auth.sso.models import SsoProfile, SsoProviderError

_DISCOVERY_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 300


async def _discovery(issuer: str) -> dict[str, Any]:
    issuer = issuer.rstrip("/")
    now = time.time()
    cached = _DISCOVERY_CACHE.get(issuer)
    if cached and cached[0] > now:
        return cached[1]
    url = f"{issuer}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                raise SsoProviderError("OIDC discovery failed")
            data = response.json()
    except httpx.HTTPError as exc:
        raise SsoProviderError("OIDC discovery request failed") from exc
    if not isinstance(data, dict):
        raise SsoProviderError("OIDC discovery returned invalid payload")
    _DISCOVERY_CACHE[issuer] = (now + _CACHE_TTL_SECONDS, data)
    return data


def authorization_url(
    *,
    client_id: str,
    state: str,
    redirect_uri: str,
    issuer: str,
    discovery: dict[str, Any],
) -> str:
    endpoint = str(discovery.get("authorization_endpoint") or "")
    if not endpoint:
        raise SsoProviderError("OIDC discovery missing authorization_endpoint")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return f"{endpoint}?{urllib.parse.urlencode(params)}"


async def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    issuer: str,
) -> SsoProfile:
    discovery = await _discovery(issuer)
    token_endpoint = str(discovery.get("token_endpoint") or "")
    userinfo_endpoint = str(discovery.get("userinfo_endpoint") or "")
    if not token_endpoint:
        raise SsoProviderError("OIDC discovery missing token_endpoint")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_response = await client.post(token_endpoint, data=payload)
            if token_response.status_code >= 400:
                raise SsoProviderError("OIDC token exchange failed")
            token_data = token_response.json()
            access_token = str(token_data.get("access_token") or "")
            if not access_token:
                raise SsoProviderError("OIDC token response missing access_token")
            profile: dict[str, Any] = {}
            if userinfo_endpoint:
                user_response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_response.status_code >= 400:
                    raise SsoProviderError("OIDC userinfo request failed")
                profile = user_response.json()
    except httpx.HTTPError as exc:
        raise SsoProviderError("OIDC OAuth request failed") from exc

    subject = str(profile.get("sub") or "")
    if not subject:
        raise SsoProviderError("OIDC profile missing subject")
    email = str(profile.get("email") or "").strip().lower() or None
    name = str(profile.get("name") or profile.get("preferred_username") or "").strip() or None
    avatar_url = str(profile.get("picture") or "").strip() or None
    return SsoProfile(
        provider="oidc",
        subject=subject,
        email=email,
        name=name,
        avatar_url=avatar_url,
    )
