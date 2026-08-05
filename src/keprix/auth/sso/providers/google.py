"""Google OAuth provider for workspace SSO."""

from __future__ import annotations

import urllib.parse

import httpx

from keprix.auth.sso.models import SsoProfile, SsoProviderError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"


def authorization_url(*, client_id: str, state: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> SsoProfile:
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data=payload)
            if token_response.status_code >= 400:
                raise SsoProviderError("Google token exchange failed")
            token_data = token_response.json()
            access_token = str(token_data.get("access_token") or "")
            if not access_token:
                raise SsoProviderError("Google token response missing access_token")
            user_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_response.status_code >= 400:
                raise SsoProviderError("Google userinfo request failed")
            profile = user_response.json()
    except httpx.HTTPError as exc:
        raise SsoProviderError("Google OAuth request failed") from exc

    subject = str(profile.get("sub") or "")
    if not subject:
        raise SsoProviderError("Google profile missing subject")
    return SsoProfile(
        provider="google",
        subject=subject,
        email=str(profile.get("email") or "").strip().lower() or None,
        name=str(profile.get("name") or "").strip() or None,
        avatar_url=str(profile.get("picture") or "").strip() or None,
    )
