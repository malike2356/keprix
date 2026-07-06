"""Google People API contact sync."""

from __future__ import annotations

from typing import Any

import httpx

from keprix.contacts.store import get_contact_store
from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.oauth.tokens import load_oauth_tokens, refresh_google_tokens


def _map_person(person: dict[str, Any]) -> dict[str, Any]:
    names = person.get("names") or [{}]
    name = names[0]
    emails = [
        {"address": e.get("value", ""), "label": (e.get("type") or ""), "primary": e.get("metadata", {}).get("primary", False)}
        for e in person.get("emailAddresses") or []
        if e.get("value")
    ]
    phones = [
        {"number": p.get("value", ""), "label": (p.get("type") or ""), "primary": p.get("metadata", {}).get("primary", False)}
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
        user_id = source.get("user_id", "local")
        if not vault_id:
            raise RuntimeError("Google sync source has no vault token")
        tokens = await load_oauth_tokens(vault_id, user_id)
        if int(tokens.get("expires_at", 0)) - 60 < __import__("time").time():
            tokens = await refresh_google_tokens(vault_id, user_id)
        return str(tokens["access_token"])

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        token = await self._token(source)
        added = updated = skipped = 0
        sync_token = None
        page_token = None
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                params: dict[str, Any] = {
                    "personFields": "names,emailAddresses,phoneNumbers,organizations",
                    "pageSize": 200,
                }
                if page_token:
                    params["pageToken"] = page_token
                elif source.get("sync_token"):
                    params["syncToken"] = source["sync_token"]
                    params.pop("pageSize", None)
                response = await client.get(
                    "https://people.googleapis.com/v1/people/me/connections",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = response.json()
                for person in payload.get("connections") or []:
                    data = _map_person(person)
                    if not data["display_name"]:
                        skipped += 1
                        continue
                    primary = data["emails"][0]["address"] if data["emails"] else None
                    _, action = await store.upsert_import(data, source="google", match_email=primary)
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
        return SyncResult(added=added, updated=updated, skipped=skipped, sync_token=sync_token)

    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        if source.get("sync_token"):
            return await self.full_sync(source)
        return await self.full_sync(source)
