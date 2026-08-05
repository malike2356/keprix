"""Microsoft Graph contact sync."""

from __future__ import annotations

import time
from typing import Any

import httpx

from keprix.contacts.store import get_contact_store
from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.oauth.tokens import load_oauth_tokens, refresh_microsoft_tokens


def _map_contact(row: dict[str, Any]) -> dict[str, Any]:
    emails = [
        {"address": e.get("address", ""), "label": e.get("name", ""), "primary": idx == 0}
        for idx, e in enumerate(row.get("emailAddresses") or [])
        if e.get("address")
    ]
    phones = []
    if row.get("mobilePhone"):
        phones.append({"number": row["mobilePhone"], "label": "mobile", "primary": True})
    for p in row.get("businessPhones") or []:
        phones.append({"number": p, "label": "work", "primary": not phones})
    return {
        "display_name": row.get("displayName") or "",
        "given_name": row.get("givenName"),
        "family_name": row.get("surname"),
        "emails": emails,
        "phones": phones,
        "addresses": [],
        "organisation": row.get("companyName"),
        "job_title": row.get("jobTitle"),
        "source_id": row.get("id"),
        "source_etag": row.get("@odata.etag"),
    }


class MicrosoftContactsConnector(ContactSyncConnector):
    async def _token(self, source: dict[str, Any]) -> str:
        vault_id = source.get("vault_token_id")
        user_id = str(source.get("user_id") or "local")
        if not vault_id:
            raise RuntimeError("Microsoft sync source has no vault token")
        tokens = await load_oauth_tokens(str(vault_id), user_id)
        if not tokens.get("access_token"):
            raise RuntimeError("Microsoft OAuth tokens missing")
        if int(tokens.get("expires_at", 0)) - 60 < time.time():
            tokens = await refresh_microsoft_tokens(str(vault_id), user_id)
        return str(tokens["access_token"])

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        user_id = str(source.get("user_id") or "local")
        try:
            token = await self._token(source)
        except Exception as exc:
            return SyncResult(error=str(exc))

        added = updated = skipped = 0
        delta_link = None
        url = (
            "https://graph.microsoft.com/v1.0/me/contacts"
            "?$select=displayName,givenName,surname,emailAddresses,businessPhones,mobilePhone,jobTitle,companyName"
        )
        if source.get("sync_token"):
            url = str(source["sync_token"])
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                while url:
                    response = await client.get(
                        url, headers={"Authorization": f"Bearer {token}"}
                    )
                    if response.status_code in (401, 403):
                        return SyncResult(error="Microsoft contacts authorization failed")
                    if response.status_code == 410 and source.get("sync_token"):
                        cleared = {**source, "sync_token": None}
                        return await self.full_sync(cleared)
                    response.raise_for_status()
                    payload = response.json()
                    for row in payload.get("value") or []:
                        if row.get("@removed"):
                            skipped += 1
                            continue
                        data = _map_contact(row)
                        if not data["display_name"] and not data["emails"]:
                            skipped += 1
                            continue
                        if not data["display_name"]:
                            data["display_name"] = data["emails"][0]["address"]
                        primary = data["emails"][0]["address"] if data["emails"] else None
                        _, action = await store.upsert_import(
                            data, source="microsoft", match_email=primary, user_id=user_id
                        )
                        if action == "added":
                            added += 1
                        elif action == "updated":
                            updated += 1
                        else:
                            skipped += 1
                    url = payload.get("@odata.nextLink")
                    delta_link = payload.get("@odata.deltaLink") or delta_link
        except httpx.HTTPError as exc:
            return SyncResult(error=f"Microsoft contacts request failed: {exc}")
        return SyncResult(added=added, updated=updated, skipped=skipped, sync_token=delta_link)

    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        if source.get("sync_token"):
            return await self.full_sync(source)
        url = (
            "https://graph.microsoft.com/v1.0/me/contacts/delta"
            "?$select=displayName,givenName,surname,emailAddresses,businessPhones,mobilePhone,jobTitle,companyName"
        )
        return await self.full_sync({**source, "sync_token": url})
