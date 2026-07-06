"""Better BibTeX export import."""

from __future__ import annotations

import re

from keprix.research_workspace.citations.bibtex import parse_bibtex
from keprix.research_workspace.citations.citation_keys import generate_citation_key
from keprix.research_workspace.citations.models import CitationRecord

_CITATION_KEY_RE = re.compile(r"citationKey\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^,\n]+)", re.IGNORECASE)


def _extract_bbt_key(block: str, entry_key: str) -> str | None:
    match = _CITATION_KEY_RE.search(block)
    if not match:
        return None
    raw = match.group(1).strip().rstrip(",")
    if raw.startswith("{") and raw.endswith("}"):
        return raw[1:-1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].strip()
    return raw


def parse_better_bibtex(text: str) -> list[CitationRecord]:
    records = parse_bibtex(text, source="better_bibtex")
    for match in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", text, re.DOTALL | re.IGNORECASE):
        entry_key = match.group(1).strip()
        bbt_key = _extract_bbt_key(match.group(0), entry_key)
        if not bbt_key:
            continue
        for record in records:
            if record.item_key == entry_key:
                record.citation_key = bbt_key
                record.source = "better_bibtex"
                break
    for record in records:
        if record.source != "better_bibtex":
            record.citation_key = generate_citation_key(
                authors=record.authors,
                year=record.year,
                title=record.title,
                preferred_key=record.citation_key,
            )
    return records
