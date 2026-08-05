"""CSV contact import with smart header mapping."""

from __future__ import annotations

import csv
import io
from typing import Any

from keprix.contacts.store import get_contact_store

GOOGLE_HEADERS = {"Given Name", "Family Name", "E-mail 1 - Value"}
OUTLOOK_HEADERS = {"First Name", "Last Name", "E-mail Address"}


def _detect_format(headers: list[str]) -> str:
    header_set = set(headers)
    if GOOGLE_HEADERS.issubset(header_set):
        return "google"
    if OUTLOOK_HEADERS.issubset(header_set):
        return "outlook"
    return "generic"


def _row_to_contact(row: dict[str, str], fmt: str) -> dict[str, Any]:
    if fmt == "google":
        given = row.get("Given Name", "").strip()
        family = row.get("Family Name", "").strip()
        email = row.get("E-mail 1 - Value", "").strip()
        org = row.get("Organization 1 - Name", "").strip() or None
        phone = row.get("Phone 1 - Value", "").strip()
    elif fmt == "outlook":
        given = row.get("First Name", "").strip()
        family = row.get("Last Name", "").strip()
        email = row.get("E-mail Address", "").strip()
        org = row.get("Company", "").strip() or None
        phone = row.get("Mobile Phone", "").strip() or row.get("Business Phone", "").strip()
    else:
        keys = {k.lower(): k for k in row}
        given = row.get(keys.get("given name", keys.get("first name", "")), "").strip()
        family = row.get(keys.get("family name", keys.get("last name", "")), "").strip()
        email = row.get(
            keys.get("email", keys.get("e-mail", keys.get("e-mail address", ""))), ""
        ).strip()
        org = row.get(keys.get("organization", keys.get("company", "")), "").strip() or None
        phone = row.get(keys.get("phone", keys.get("mobile", "")), "").strip()

    display = f"{given} {family}".strip() or email or "Unknown"
    emails = [{"address": email, "label": "work", "primary": True}] if email else []
    phones = [{"number": phone, "label": "mobile", "primary": True}] if phone else []
    return {
        "display_name": display,
        "given_name": given or None,
        "family_name": family or None,
        "emails": emails,
        "phones": phones,
        "addresses": [],
        "organisation": org,
    }


async def import_csv_bytes(content: bytes, *, user_id: str = "local") -> dict[str, int]:
    store = get_contact_store()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    fmt = _detect_format(headers)
    added = updated = skipped = 0
    for row in reader:
        data = _row_to_contact(row, fmt)
        primary = data["emails"][0]["address"] if data["emails"] else None
        if not primary and data["display_name"] == "Unknown":
            skipped += 1
            continue
        _, action = await store.upsert_import(
            data, source="csv", match_email=primary, user_id=user_id
        )
        if action == "added":
            added += 1
        elif action == "updated":
            updated += 1
        else:
            skipped += 1
    return {"added": added, "updated": updated, "skipped": skipped}
