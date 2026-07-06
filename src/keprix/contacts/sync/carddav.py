"""CardDAV contact sync."""

from __future__ import annotations

from typing import Any

import httpx
import vobject

from keprix.contacts.import_vcf import _contact_from_vcard
from keprix.contacts.store import get_contact_store
from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.security.vault_service import get_vault_service


class CardDAVContactsConnector(ContactSyncConnector):
    async def _password(self, source: dict[str, Any]) -> str:
        vault_id = source.get("vault_token_id")
        user_id = source.get("user_id", "local")
        if vault_id:
            item = await get_vault_service().get_item(vault_id, user_id, decrypt=True)
            if item and item._value:
                return item._value
        return ""

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        url = (source.get("carddav_url") or "").rstrip("/")
        username = source.get("carddav_username") or ""
        password = await self._password(source)
        if not url or not username:
            return SyncResult(error="CardDAV URL and username required")
        added = updated = skipped = 0
        auth = (username, password)
        report_body = """<?xml version="1.0" encoding="utf-8" ?>
<C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:prop><D:getetag/><C:address-data/></D:prop>
</C:addressbook-query>"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(
                "REPORT",
                url,
                content=report_body,
                auth=auth,
                headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
            )
            response.raise_for_status()
            text = response.text
        for chunk in text.split("BEGIN:VCARD"):
            if "END:VCARD" not in chunk:
                continue
            vcf = ("BEGIN:VCARD" + chunk.split("END:VCARD")[0] + "END:VCARD").encode()
            try:
                for card in vobject.readComponents(vcf.decode()):
                    if card.name.lower() != "vcard":
                        continue
                    data = _contact_from_vcard(card)
                    data["source_id"] = data.get("display_name", "") + (data["emails"][0]["address"] if data["emails"] else "")
                    primary = data["emails"][0]["address"] if data["emails"] else None
                    _, action = await store.upsert_import(data, source="carddav", match_email=primary)
                    if action == "added":
                        added += 1
                    elif action == "updated":
                        updated += 1
                    else:
                        skipped += 1
            except Exception:
                skipped += 1
        return SyncResult(added=added, updated=updated, skipped=skipped)

    async def delta_sync(self, source: dict[str, Any]) -> SyncResult:
        return await self.full_sync(source)
