"""BibTeX parsing and serialization."""

from __future__ import annotations

import re
from typing import Any

from keprix.research_workspace.citations.citation_keys import generate_citation_key
from keprix.research_workspace.citations.models import CitationRecord

_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL | re.IGNORECASE)
_FIELD_RE = re.compile(r"(\w+)\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^,\n]+)", re.DOTALL)


def _clean_value(raw: str) -> str:
    value = raw.strip().rstrip(",")
    if value.startswith("{") and value.endswith("}"):
        return value[1:-1].strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].strip()
    return value


def parse_authors(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(" and ") if part.strip()]
    return parts


def parse_bibtex(text: str, *, source: str = "bibtex") -> list[CitationRecord]:
    records: list[CitationRecord] = []
    for match in _ENTRY_RE.finditer(text):
        entry_key = match.group(2).strip()
        fields: dict[str, str] = {}
        for field_match in _FIELD_RE.finditer(match.group(3)):
            fields[field_match.group(1).lower()] = _clean_value(field_match.group(2))
        authors = parse_authors(fields.get("author"))
        year = fields.get("year")
        title = fields.get("title") or entry_key
        citation_key = generate_citation_key(
            authors=authors,
            year=year,
            title=title,
            preferred_key=entry_key,
        )
        records.append(
            CitationRecord(
                item_key=entry_key,
                citation_key=citation_key,
                title=title,
                authors=authors,
                year=year,
                publication=fields.get("journal") or fields.get("booktitle") or fields.get("publisher"),
                doi=fields.get("doi"),
                url=fields.get("url"),
                abstract=fields.get("abstract"),
                tags=[tag.strip() for tag in (fields.get("keywords") or "").split(",") if tag.strip()],
                source=source,
            )
        )
    return records


def record_to_bibtex(record: CitationRecord) -> str:
    authors = " and ".join(record.authors) if record.authors else "Unknown"
    lines = [
        f"@article{{{record.citation_key},",
        f"  author = {{{authors}}},",
        f"  title = {{{record.title}}},",
    ]
    if record.year:
        lines.append(f"  year = {{{record.year}}},")
    if record.publication:
        lines.append(f"  journal = {{{record.publication}}},")
    if record.doi:
        lines.append(f"  doi = {{{record.doi}}},")
    if record.url:
        lines.append(f"  url = {{{record.url}}},")
    if record.abstract:
        lines.append(f"  abstract = {{{record.abstract}}},")
    lines.append("}")
    return "\n".join(lines)
