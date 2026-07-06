"""Citation persistence for research projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.store import ResearchWorkspaceStore


class CitationLibrary:
    def __init__(self, store: ResearchWorkspaceStore) -> None:
        self.store = store
        self.cache_dir = store.plane.root / "citations"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_records(self, project_id: str, records: list[CitationRecord]) -> list[dict[str, Any]]:
        saved: list[dict[str, Any]] = []
        for record in records:
            citation = self.store.add_citation(
                project_id,
                label=record.citation_key,
                source_id=None,
                metadata=record.to_dict(),
            )
            self.store.save_object(
                object_id=f"cite-{record.citation_key}",
                object_type="citation",
                project_id=project_id,
                owner="zotero",
                source_ref=record.doi or record.url,
                provenance={"citation_key": record.citation_key, "source": record.source},
                payload=record.to_dict(),
                trace_id=record.citation_key,
            )
            saved.append(citation)
        cache_path = self.cache_dir / f"{project_id}.json"
        existing = self.list_cached(project_id)
        merged = {item.citation_key: item for item in existing}
        for record in records:
            merged[record.citation_key] = record
        cache_path.write_text(
            json.dumps([item.to_dict() for item in merged.values()], indent=2),
            encoding="utf-8",
        )
        return saved

    def list_cached(self, project_id: str) -> list[CitationRecord]:
        cache_path = self.cache_dir / f"{project_id}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            return [CitationRecord.from_dict(item) for item in payload]
        citations = self.store.list_citations(project_id)
        records: list[CitationRecord] = []
        for row in citations:
            metadata = row.get("metadata") or {}
            if metadata:
                records.append(CitationRecord.from_dict(metadata))
        return records

    def get_by_keys(self, project_id: str, citation_keys: list[str]) -> list[CitationRecord]:
        records = self.list_cached(project_id)
        wanted = set(citation_keys)
        return [record for record in records if record.citation_key in wanted]
