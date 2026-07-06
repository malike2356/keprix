"""Typed structured extraction schemas."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


class InvoiceSchema(BaseModel):
    vendor: str = ""
    invoice_number: str = ""
    total_amount: str = ""
    due_date: str = ""


class ContractSchema(BaseModel):
    parties: list[str] = Field(default_factory=list)
    effective_date: str = ""
    term: str = ""


class ResearchPaperSchema(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""


class MeetingNotesSchema(BaseModel):
    attendees: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


class CustomerTicketSchema(BaseModel):
    ticket_id: str = ""
    customer: str = ""
    priority: str = "normal"
    summary: str = ""


class GenericEntitySchema(BaseModel):
    entity_type: str = "generic"
    name: str = ""
    attributes: dict[str, str] = Field(default_factory=dict)


SCHEMAS: dict[str, type[BaseModel]] = {
    "invoice": InvoiceSchema,
    "contract": ContractSchema,
    "research_paper": ResearchPaperSchema,
    "meeting_notes": MeetingNotesSchema,
    "customer_ticket": CustomerTicketSchema,
    "generic": GenericEntitySchema,
}


def extract_structured(text: str, schema_name: str) -> dict[str, Any]:
    model = SCHEMAS.get(schema_name)
    if model is None:
        raise ValueError(f"Unknown schema: {schema_name}")
    payload = _heuristic_extract(text, schema_name)
    try:
        validated = model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Structured extraction failed validation: {exc}") from exc
    return validated.model_dump()


def _heuristic_extract(text: str, schema_name: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if schema_name == "invoice":
        return {
            "vendor": _find_label(text, "vendor"),
            "invoice_number": _find_label(text, "invoice"),
            "total_amount": _find_money(text),
            "due_date": _find_label(text, "due"),
        }
    if schema_name == "contract":
        return {
            "parties": [line for line in lines[:3] if "party" in line.lower() or "between" in line.lower()],
            "effective_date": _find_label(text, "effective"),
            "term": _find_label(text, "term"),
        }
    if schema_name == "research_paper":
        return {
            "title": lines[0] if lines else "",
            "authors": [line for line in lines[1:4] if "author" in line.lower() or "," in line],
            "abstract": "\n".join(lines[:8]),
        }
    if schema_name == "meeting_notes":
        return {
            "attendees": [line.split(":", 1)[-1].strip() for line in lines if "attendee" in line.lower()],
            "decisions": [line for line in lines if line.lower().startswith("decision")],
            "action_items": [line for line in lines if "action" in line.lower()],
        }
    if schema_name == "customer_ticket":
        return {
            "ticket_id": _find_label(text, "ticket"),
            "customer": _find_label(text, "customer"),
            "priority": _find_label(text, "priority") or "normal",
            "summary": lines[0] if lines else "",
        }
    return {
        "entity_type": "generic",
        "name": lines[0] if lines else "",
        "attributes": {"preview": text[:240]},
    }


def _find_label(text: str, label: str) -> str:
    pattern = re.compile(rf"(?i){label}\s*[:#-]\s*(.+)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _find_money(text: str) -> str:
    match = re.search(r"[$£]\s?\d+(?:\.\d{2})?", text)
    return match.group(0) if match else ""
