"""Workflow 7: CRM Import / Clean.

INPUT: messy CSV text
  → dedupe → normalize columns → map to CRM fields → validate
OUTPUT: clean rows ready for GoHighLevel / HubSpot / Salesforce-style import
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

CRM_FIELDS = ("email", "first_name", "last_name", "company", "phone", "notes")

_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "email": ("email", "e-mail", "mail", "email_address", "emailaddress"),
    "first_name": ("first_name", "firstname", "first", "given_name", "givenname"),
    "last_name": ("last_name", "lastname", "last", "surname", "family_name"),
    "company": ("company", "organization", "organisation", "org", "account"),
    "phone": ("phone", "mobile", "cell", "telephone", "phone_number"),
    "notes": ("notes", "note", "comments", "comment", "description"),
}


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _map_headers(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    used: set[str] = set()
    normalized = {_norm_header(h): h for h in headers}
    for field, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized and field not in used:
                mapping[normalized[alias]] = field
                used.add(field)
                break
    return mapping


def _split_name(full: str) -> tuple[str, str]:
    parts = [p for p in (full or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def clean_crm_import(*, csv_text: str, target: str = "generic") -> dict[str, Any]:
    raw = (csv_text or "").strip()
    if not raw:
        return {
            "status": "error",
            "workflow": "crm-import",
            "error": "csv_text is required",
            "output": "Provide CSV text to clean.",
        }

    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return {
            "status": "error",
            "workflow": "crm-import",
            "error": "CSV has no header row",
            "output": "CSV must include a header row.",
        }

    headers = list(reader.fieldnames)
    mapping = _map_headers(headers)
    # Fallback: if a generic "name" column exists, split it.
    name_col = next((h for h in headers if _norm_header(h) in {"name", "full_name", "fullname"}), None)

    cleaned: list[dict[str, str]] = []
    seen_emails: set[str] = set()
    duplicates = 0
    invalid = 0

    for row in reader:
        mapped: dict[str, str] = {field: "" for field in CRM_FIELDS}
        for source, field in mapping.items():
            mapped[field] = str(row.get(source) or "").strip()
        if name_col and not mapped["first_name"] and not mapped["last_name"]:
            first, last = _split_name(str(row.get(name_col) or ""))
            mapped["first_name"] = first
            mapped["last_name"] = last

        email = mapped["email"].lower()
        mapped["email"] = email
        if email:
            if email in seen_emails:
                duplicates += 1
                continue
            if "@" not in email or "." not in email.split("@")[-1]:
                invalid += 1
                continue
            seen_emails.add(email)
        elif not any(mapped[f] for f in ("first_name", "last_name", "company", "phone")):
            invalid += 1
            continue
        cleaned.append(mapped)

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(CRM_FIELDS))
    writer.writeheader()
    writer.writerows(cleaned)
    clean_csv = out.getvalue()

    markdown = [
        f"# CRM import clean ({target})",
        "",
        f"- Input rows processed from headers: {', '.join(headers)}",
        f"- Column map: {mapping or '{}'}",
        f"- Clean rows: {len(cleaned)}",
        f"- Duplicates removed: {duplicates}",
        f"- Invalid rows skipped: {invalid}",
        "",
        "## Preview",
        "",
        "```csv",
        clean_csv.strip(),
        "```",
    ]

    return {
        "status": "ok",
        "workflow": "crm-import",
        "target": target,
        "column_map": mapping,
        "row_count": len(cleaned),
        "duplicates_removed": duplicates,
        "invalid_skipped": invalid,
        "rows": cleaned,
        "clean_csv": clean_csv,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "crm_import",
            "target": target,
            "row_count": len(cleaned),
            "duplicates_removed": duplicates,
        },
    }
