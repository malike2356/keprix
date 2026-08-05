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
        user_id = str(source.get("user_id") or "local")
        if not vault_id:
            return ""
        vault = get_vault_service()
        # Passwords are stored via store_oauth_tokens as {"password": "..."}.
        bundle = await vault.get_oauth_bundle(str(vault_id), user_id)
        if isinstance(bundle, dict) and bundle.get("password"):
            return str(bundle["password"])
        item = await vault.get_item(str(vault_id), user_id, decrypt=True)
        if item and item._value:
            return str(item._value)
        return ""

    async def full_sync(self, source: dict[str, Any]) -> SyncResult:
        store = get_contact_store()
        user_id = str(source.get("user_id") or "local")
        url = (source.get("carddav_url") or "").rstrip("/")
        username = source.get("carddav_username") or ""
        password = await self._password(source)
        if not url or not username:
            return SyncResult(error="CardDAV URL and username required")
        if not password:
            return SyncResult(error="CardDAV password missing or could not be decrypted")
        added = updated = skipped = 0
        auth = (username, password)
        report_body = """<?xml version="1.0" encoding="utf-8" ?>
<C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:prop><D:getetag/><C:address-data/></D:prop>
</C:addressbook-query>"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.request(
                    "REPORT",
                    url,
                    content=report_body,
                    auth=auth,
                    headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
                )
                if response.status_code in (401, 403):
                    return SyncResult(error="CardDAV authentication failed")
                response.raise_for_status()
                text = response.text
        except httpx.HTTPError as exc:
            return SyncResult(error=f"CardDAV request failed: {exc}")

        for chunk in text.split("BEGIN:VCARD"):
            if "END:VCARD" not in chunk:
                continue
            vcf = ("BEGIN:VCARD" + chunk.split("END:VCARD")[0] + "END:VCARD").encode()
            try:
                for card in vobject.readComponents(vcf.decode()):
                    if card.name.lower() != "vcard":
                        continue
                    data = _contact_from_vcard(card)
                    uid = getattr(getattr(card, "uid", None), "value", None)
                    data["source_id"] = str(uid) if uid else (
                        data.get("display_name", "")
                        + (data["emails"][0]["address"] if data["emails"] else "")
                    )
                    primary = data["emails"][0]["address"] if data["emails"] else None
                    _, action = await store.upsert_import(
                        data, source="carddav", match_email=primary, user_id=user_id
                    )
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
