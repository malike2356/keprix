"""Google People API contact sync."""

from __future__ import annotations

import time
from typing import Any

import httpx

from keprix.contacts.store import get_contact_store
from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.oauth.tokens import load_oauth_tokens, refresh_google_tokens


def _map_person(person: dict[str, Any]) -> dict[str, Any]:
    names = person.get("names") or [{}]
    name = names[0]
    emails = [
        {
            "address": e.get("value", ""),
            "label": (e.get("type") or ""),
            "primary": e.get("metadata", {}).get("primary", False),
        }
        for e in person.get("emailAddresses") or []
        if e.get("value")
    ]
    phones = [
        {
            "number": p.get("value", ""),
            "label": (p.get("type") or ""),
            "primary": p.get("metadata", {}).get("primary", False),
        }
        for p in person.get("phoneNumbers") or []
        if p.get("value")
    ]
    orgs = person.get("organizations") or [{}]
    org = orgs[0].get("name") if orgs else None
    return {
        "display_name": name.get("displayName") or "",
        "given_name": name.get("givenName"),
        "family_name": name.get("familyName"),
        "emails": emails,
        "phones": phones,
        "addresses": [],
        "organisation": org,
        "source_id": person.get("resourceName"),
        "source_etag": person.get("etag"),
    }


class GoogleContactsConnector(ContactSyncConnector):
    async def _token(self, source: dict[str, Any]) -> str:
        vault_id = source.get("vault_token_id")
        user_id = str(source.get("user_id") or "local")
        if not vault_id:
            raise RuntimeError("Google sync source has no vault token")
        tokens = await load_oauth_tokens(str(vault_id), user_id)
        if not tokens.get("access_token"):
            raise RuntimeError("Google OAuth tokens missing")
        if int(tokens.get("expires_at", 0)) - 60 < time.time():
            from keprix.contacts.google_oauth_config import get_google_oauth_app

            app = await get_google_oauth_app(user_id)
            tokens = await refresh_google_tokens(
                str(vault_id),
                user_id,
                client_id=app.get("client_id"),
                client_secret=app.get("client_secret"),
            )
        return str(tokens["access_token"])

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        user_id = str(source.get("user_id") or "local")
        try:
            token = await self._token(source)
        except Exception as exc:
            return SyncResult(error=str(exc))

        added = updated = skipped = 0
        sync_token = None
        page_token = None
        use_delta = bool(source.get("sync_token"))
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                while True:
                    params: dict[str, Any] = {
                        "personFields": "names,emailAddresses,phoneNumbers,organizations",
                        "pageSize": 200,
                    }
                    if use_delta and not page_token:
                        params["syncToken"] = source["sync_token"]
                    else:
                        params["requestSyncToken"] = "true"
                    if page_token:
                        params["pageToken"] = page_token
                    response = await client.get(
                        "https://people.googleapis.com/v1/people/me/connections",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if response.status_code == 410 and use_delta:
                        # Sync token expired: fall back to full sync once.
                        source = {**source, "sync_token": None}
                        return await self.full_sync(source)
                    if response.status_code in (401, 403):
                        return SyncResult(error="Google contacts authorization failed")
                    response.raise_for_status()
                    payload = response.json()
                    for person in payload.get("connections") or []:
                        data = _map_person(person)
                        if not data["display_name"] and not data["emails"]:
                            skipped += 1
                            continue
                        if not data["display_name"]:
                            data["display_name"] = data["emails"][0]["address"]
                        primary = data["emails"][0]["address"] if data["emails"] else None
                        _, action = await store.upsert_import(
                            data, source="google", match_email=primary, user_id=user_id
                        )
                        if action == "added":
                            added += 1
                        elif action == "updated":
                            updated += 1
                        else:
                            skipped += 1
                    sync_token = payload.get("nextSyncToken") or sync_token
                    page_token = payload.get("nextPageToken")
                    if not page_token:
                        break
        except httpx.HTTPError as exc:
            return SyncResult(error=f"Google contacts request failed: {exc}")
        return SyncResult(added=added, updated=updated, skipped=skipped, sync_token=sync_token)

    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        return await self.full_sync(source)
