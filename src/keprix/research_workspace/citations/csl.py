"""CSL JSON helpers."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.citations.models import CitationRecord


def record_to_csl(record: CitationRecord) -> dict[str, Any]:
    authors = [{"family": name.split()[-1], "given": " ".join(name.split()[:-1])} for name in record.authors]
    if not authors and record.authors:
        authors = [{"literal": record.authors[0]}]
    item: dict[str, Any] = {
        "id": record.citation_key,
        "type": "article-journal",
        "title": record.title,
        "author": authors,
    }
    if record.year:
        item["issued"] = {"date-parts": [[int(record.year[:4])]]}
    if record.publication:
        item["container-title"] = record.publication
    if record.doi:
        item["DOI"] = record.doi
    if record.url:
        item["URL"] = record.url
    if record.abstract:
        item["abstract"] = record.abstract
    return item


def records_to_csl_json(records: list[CitationRecord]) -> list[dict[str, Any]]:
    return [record_to_csl(record) for record in records]
