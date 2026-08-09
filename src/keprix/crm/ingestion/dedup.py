"""Lead deduplication helpers for ingestion."""

from __future__ import annotations

from typing import Any

from keprix.crm.store import (
    CrmStore,
    _emails_from_fields,
    _normalise_website,
    _phones_from_fields,
    _primary_email,
    _primary_phone,
)


def _phone_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    return digits or None


def find_existing(store: CrmStore, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    """Find an existing lead by email, then phone, then website+company+locality.

    Also reuses store._find_lead_key which includes external_source_id / company_number.
    """
    return store._find_lead_key(workspace_id, fields)


def match_key(fields: dict[str, Any]) -> tuple[str, str] | None:
    """Return (kind, value) describing the strongest match key present."""
    email = _primary_email(_emails_from_fields(fields))
    if email:
        return ("email", email)
    phone = _phone_digits(_primary_phone(_phones_from_fields(fields)))
    if phone:
        return ("phone", phone)
    website = _normalise_website(fields.get("website"))
    company = str(fields.get("company_name") or "").strip().lower()
    locality = str(fields.get("locality") or "").strip().lower()
    if website and company:
        return ("website_company_locality", f"{website}|{company}|{locality}")
    return None
