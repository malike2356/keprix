"""Normalized citation records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CitationRecord:
    item_key: str
    citation_key: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: str | None = None
    publication: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source: str = "bibtex"
    obsidian_note_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CitationRecord:
        return cls(
            item_key=str(data.get("item_key") or data.get("citation_key") or ""),
            citation_key=str(data.get("citation_key") or data.get("item_key") or ""),
            title=str(data.get("title") or "Untitled"),
            authors=list(data.get("authors") or []),
            year=data.get("year"),
            publication=data.get("publication"),
            doi=data.get("doi"),
            url=data.get("url"),
            abstract=data.get("abstract"),
            tags=list(data.get("tags") or []),
            collections=list(data.get("collections") or []),
            attachments=list(data.get("attachments") or []),
            notes=list(data.get("notes") or []),
            source=str(data.get("source") or "bibtex"),
            obsidian_note_path=data.get("obsidian_note_path"),
        )
