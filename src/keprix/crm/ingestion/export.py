"""Lead export to Excel (default) and CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from keprix.crm.ingestion.canonical import CANONICAL_KEYS, REFERENCE_HEADERS
from keprix.sheet_preprocess.safety import escape_csv_cell

EXPORT_COLUMNS: list[tuple[str, str]] = list(zip(REFERENCE_HEADERS, CANONICAL_KEYS)) + [
    ("Pipeline Stage", "pipeline_stage"),
    ("Source Type", "source_type"),
    ("Source Name", "source_name"),
    ("Source URL", "source_url"),
    ("Source Captured At", "source_captured_at"),
    ("Consent Status", "consent_status"),
    ("Priority", "priority"),
    ("Custom Fields", "custom_fields"),
]


def _primary_email(lead: dict[str, Any]) -> str:
    for item in lead.get("emails") or []:
        if isinstance(item, dict) and item.get("address"):
            return str(item["address"])
        if isinstance(item, str):
            return item
    return ""


def _primary_phone(lead: dict[str, Any]) -> str:
    for item in lead.get("phones") or []:
        if isinstance(item, dict) and (item.get("number") or item.get("phone")):
            return str(item.get("number") or item.get("phone"))
        if isinstance(item, str):
            return item
    return ""


def lead_to_export_row(lead: dict[str, Any], *, flatten_custom: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for header, key in EXPORT_COLUMNS:
        if key == "email":
            row[header] = _primary_email(lead)
        elif key == "phone":
            row[header] = _primary_phone(lead)
        elif key == "stage":
            row[header] = lead.get("stage") or lead.get("pipeline_stage") or ""
        elif key == "custom_fields":
            custom = lead.get("custom_fields") or {}
            if flatten_custom and isinstance(custom, dict):
                for ck, cv in custom.items():
                    row[f"custom.{ck}"] = cv
                row[header] = ""
            else:
                row[header] = json.dumps(custom, ensure_ascii=False) if custom else ""
        else:
            value = lead.get(key)
            row[header] = "" if value is None else value
    # Deduplicate Priority if already in reference headers.
    return row


def export_leads_csv(
    leads: list[dict[str, Any]],
    path: str | Path,
    *,
    flatten_custom: bool = False,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = [lead_to_export_row(lead, flatten_custom=flatten_custom) for lead in leads]
    # Collect headers preserving order, then any flattened custom keys.
    headers: list[str] = []
    seen: set[str] = set()
    for header, _ in EXPORT_COLUMNS:
        if header not in seen:
            headers.append(header)
            seen.add(header)
    for row in rows:
        for key in row:
            if key not in seen:
                headers.append(key)
                seen.add(key)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: escape_csv_cell(row.get(k, "")) for k in headers})
    return destination


def export_leads_xlsx(
    leads: list[dict[str, Any]],
    path: str | Path,
    *,
    flatten_custom: bool = False,
) -> Path:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ImportError(
            "Excel export requires openpyxl; install keprix[analytics]"
        ) from exc

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = [lead_to_export_row(lead, flatten_custom=flatten_custom) for lead in leads]
    headers: list[str] = []
    seen: set[str] = set()
    for header, _ in EXPORT_COLUMNS:
        if header not in seen:
            headers.append(header)
            seen.add(header)
    for row in rows:
        for key in row:
            if key not in seen:
                headers.append(key)
                seen.add(key)

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h, "") for h in headers])
    wb.save(destination)
    return destination


def export_leads(
    leads: list[dict[str, Any]],
    path: str | Path,
    *,
    format: str = "xlsx",
    flatten_custom: bool = False,
) -> Path:
    fmt = (format or "xlsx").lower().lstrip(".")
    if fmt == "csv":
        return export_leads_csv(leads, path, flatten_custom=flatten_custom)
    return export_leads_xlsx(leads, path, flatten_custom=flatten_custom)
