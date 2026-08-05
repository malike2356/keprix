"""GitHub OAuth provider for workspace SSO."""

from __future__ import annotations

import urllib.parse

import httpx

from keprix.auth.sso.models import SsoProfile, SsoProviderError

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
SCOPES = "read:user user:email"


def authorization_url(*, client_id: str, state: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    return f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}"


async def _primary_email(client: httpx.AsyncClient, headers: dict[str, str]) -> str | None:
    response = await client.get(GITHUB_EMAILS_URL, headers=headers)
    if response.status_code >= 400:
        return None
    emails = response.json()
    if not isinstance(emails, list):
        return None
    for row in emails:
        if isinstance(row, dict) and row.get("primary") and row.get("verified"):
            return str(row.get("email") or "").strip().lower() or None
    for row in emails:
        if isinstance(row, dict) and row.get("verified"):
            return str(row.get("email") or "").strip().lower() or None
    return None


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
    }
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_response = await client.post(GITHUB_TOKEN_URL, data=payload, headers=headers)
            if token_response.status_code >= 400:
                raise SsoProviderError("GitHub token exchange failed")
            token_data = token_response.json()
            access_token = str(token_data.get("access_token") or "")
            if not access_token:
                raise SsoProviderError("GitHub token response missing access_token")
            auth_headers = {
                **headers,
                "Authorization": f"Bearer {access_token}",
            }
            user_response = await client.get(GITHUB_USER_URL, headers=auth_headers)
            if user_response.status_code >= 400:
                raise SsoProviderError("GitHub user request failed")
            profile = user_response.json()
            email = str(profile.get("email") or "").strip().lower() or None
            if not email:
                email = await _primary_email(client, auth_headers)
    except httpx.HTTPError as exc:
        raise SsoProviderError("GitHub OAuth request failed") from exc

    subject = str(profile.get("id") or "")
    if not subject:
        raise SsoProviderError("GitHub profile missing subject")
    return SsoProfile(
        provider="github",
        subject=subject,
        email=email,
        name=str(profile.get("name") or profile.get("login") or "").strip() or None,
        avatar_url=str(profile.get("avatar_url") or "").strip() or None,
    )
