"""Microsoft Graph contact sync."""

from __future__ import annotations

from typing import Any

import httpx

from keprix.contacts.store import get_contact_store
from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.oauth.tokens import load_oauth_tokens


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
        user_id = source.get("user_id", "local")
        if not vault_id:
            raise RuntimeError("Microsoft sync source has no vault token")
        tokens = await load_oauth_tokens(vault_id, user_id)
        return str(tokens["access_token"])

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        token = await self._token(source)
        added = updated = skipped = 0
        delta_link = None
        url = "https://graph.microsoft.com/v1.0/me/contacts?$select=displayName,givenName,surname,emailAddresses,businessPhones,mobilePhone,jobTitle,companyName"
        if source.get("sync_token"):
            url = source["sync_token"]
        async with httpx.AsyncClient(timeout=60) as client:
            while url:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                response.raise_for_status()
                payload = response.json()
                for row in payload.get("value") or []:
                    data = _map_contact(row)
                    if not data["display_name"]:
                        skipped += 1
                        continue
                    primary = data["emails"][0]["address"] if data["emails"] else None
                    _, action = await store.upsert_import(data, source="microsoft", match_email=primary)
                    if action == "added":
                        added += 1
                    elif action == "updated":
                        updated += 1
                    else:
                        skipped += 1
                url = payload.get("@odata.nextLink")
                delta_link = payload.get("@odata.deltaLink") or delta_link
        return SyncResult(added=added, updated=updated, skipped=skipped, sync_token=delta_link)

    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        if source.get("sync_token"):
            url = source["sync_token"]
        else:
            url = "https://graph.microsoft.com/v1.0/me/contacts/delta?$select=displayName,givenName,surname,emailAddresses,businessPhones,mobilePhone,jobTitle,companyName"
            source = {**source, "sync_token": url}
        return await self.full_sync(source)
