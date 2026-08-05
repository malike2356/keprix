"""vCard import."""

from __future__ import annotations

from typing import Any

import vobject

from keprix.contacts.store import get_contact_store


def _email_entries(card: vobject.base.Component) -> list[dict[str, Any]]:
    emails: list[dict[str, Any]] = []
    for idx, item in enumerate(getattr(card, "email_list", [])):
        emails.append(
            {
                "address": str(item.value),
                "label": str(getattr(item, "type_param", "") or ""),
                "primary": idx == 0,
            }
        )
    return emails


def _phone_entries(card: vobject.base.Component) -> list[dict[str, Any]]:
    phones: list[dict[str, Any]] = []
    for idx, item in enumerate(getattr(card, "tel_list", [])):
        phones.append(
            {
                "number": str(item.value),
                "label": str(getattr(item, "type_param", "") or ""),
                "primary": idx == 0,
            }
        )
    return phones


def _contact_from_vcard(card: vobject.base.Component) -> dict[str, Any]:
    given = ""
    family = ""
    if hasattr(card, "n"):
        parts = card.n.value
        family = str(getattr(parts, "family", "") or "")
        given = str(getattr(parts, "given", "") or "")
    display = str(card.fn.value) if hasattr(card, "fn") else f"{given} {family}".strip()
    org = str(card.org.value[0]) if hasattr(card, "org") and card.org.value else None
    return {
        "display_name": display or "Unknown",
        "given_name": given or None,
        "family_name": family or None,
        "emails": _email_entries(card),
        "phones": _phone_entries(card),
        "addresses": [],
        "organisation": org,
        "job_title": str(card.title.value) if hasattr(card, "title") else None,
        "notes": str(card.note.value) if hasattr(card, "note") else None,
    }


async def import_vcf_bytes(content: bytes, *, user_id: str = "local") -> dict[str, int]:
    store = get_contact_store()
    text = content.decode("utf-8", errors="replace")
    added = updated = skipped = 0
    for card in vobject.readComponents(text):
        if card.name.lower() != "vcard":
            continue
        data = _contact_from_vcard(card)
        primary = data["emails"][0]["address"] if data["emails"] else None
        if not primary and not data["display_name"]:
            skipped += 1
            continue
        _, action = await store.upsert_import(
            data, source="vcf", match_email=primary, user_id=user_id
        )
        if action == "added":
            added += 1
        elif action == "updated":
            updated += 1
        else:
            skipped += 1
    return {"added": added, "updated": updated, "skipped": skipped}
