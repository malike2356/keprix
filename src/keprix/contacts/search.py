"""Fuzzy contact search."""

from __future__ import annotations

from typing import Any

try:
    from metaphone import doublemetaphone
except ImportError:
    doublemetaphone = None  # type: ignore[assignment,misc]

from keprix.contacts.store import ContactRecord, get_contact_store


def _metaphone(value: str) -> tuple[str, str]:
    if not value or doublemetaphone is None:
        return ("", "")
    return doublemetaphone(value)


def _primary_email(contact: ContactRecord) -> str | None:
    for item in contact.emails:
        if item.get("primary"):
            return item.get("address")
    return contact.emails[0]["address"] if contact.emails else None


def _primary_phone(contact: ContactRecord) -> str | None:
    for item in contact.phones:
        if item.get("primary"):
            return item.get("number")
    return contact.phones[0]["number"] if contact.phones else None


def _score_contact(contact: ContactRecord, query: str) -> float:
    q = query.strip().lower()
    if not q:
        return 0.0
    score = 0.0
    name = contact.display_name.lower()
    given = (contact.given_name or "").lower()
    family = (contact.family_name or "").lower()
    org = (contact.organisation or "").lower()

    if name == q:
        score += 100
    if given == q or family == q:
        score += 90
    if name.startswith(q) or given.startswith(q) or family.startswith(q):
        score += 70
    if q in name:
        score += 50
    if doublemetaphone is not None:
        q_meta = _metaphone(q)
        for part in (given, family, name):
            if part and _metaphone(part)[0] == q_meta[0] and q_meta[0]:
                score += 45
                break
    if q in org:
        score += 30
    for email in contact.emails:
        if q in (email.get("address") or "").lower():
            score += 25
    for phone in contact.phones:
        if q in (phone.get("number") or "").replace(" ", ""):
            score += 20
    return score


async def contact_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    store = get_contact_store()
    contacts = await store.all_contacts()
    ranked = [(c, _score_contact(c, query)) for c in contacts]
    ranked = [(c, s) for c, s in ranked if s > 0]
    ranked.sort(key=lambda item: (-item[1], item[0].display_name))
    results = []
    for contact, score in ranked[:limit]:
        results.append(
            {
                "id": contact.id,
                "display_name": contact.display_name,
                "organisation": contact.organisation,
                "primary_email": _primary_email(contact),
                "primary_phone": _primary_phone(contact),
                "score": score,
            }
        )
    return results


async def contact_get(contact_id: str) -> ContactRecord | None:
    return await get_contact_store().get(contact_id)


async def contact_get_primary_email(contact_id: str) -> str | None:
    contact = await contact_get(contact_id)
    return _primary_email(contact) if contact else None


async def contact_get_primary_phone(contact_id: str) -> str | None:
    contact = await contact_get(contact_id)
    return _primary_phone(contact) if contact else None
