"""Document index lifecycle management."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.memory.rag.indexer import RagIndexer


@dataclass
class DocumentIndex:
    index_id: str
    user_id: str
    name: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _store_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "documents"
    except Exception:
        root = Path.home() / ".keprix" / "documents"
    root.mkdir(parents=True, exist_ok=True)
    return root / "indexes.json"


class DocumentIndexManager:
    def __init__(self, indexer: RagIndexer | None = None, store_path: Path | None = None) -> None:
        self._indexer = indexer or RagIndexer()
        self._path = store_path or _store_path()
        self._indexes: dict[str, DocumentIndex] = {}
        if self._path.exists():
            for row in json.loads(self._path.read_text(encoding="utf-8")):
                index = DocumentIndex(**row)
                self._indexes[index.index_id] = index

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([index.to_dict() for index in self._indexes.values()], indent=2),
            encoding="utf-8",
        )

    def create_index(self, *, user_id: str, name: str) -> DocumentIndex:
        index = DocumentIndex(index_id=str(uuid.uuid4()), user_id=user_id, name=name)
        self._indexes[index.index_id] = index
        self._save()
        return index

    def get(self, index_id: str) -> DocumentIndex | None:
        return self._indexes.get(index_id)

    def list_indexes(self, user_id: str) -> list[DocumentIndex]:
        return [index for index in self._indexes.values() if index.user_id == user_id]

    @property
    def indexer(self) -> RagIndexer:
        return self._indexer

    async def add_document(
        self,
        index_id: str,
        *,
        source_id: str,
        source_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        index = self._require(index_id)
        chunks = await self._indexer.ingest(
            user_id=index.user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
        )
        record = {
            "source_id": source_id,
            "source_type": source_type,
            "chunk_count": chunks,
            "metadata": metadata or {},
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        index.documents = [doc for doc in index.documents if doc.get("source_id") != source_id]
        index.documents.append(record)
        index.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return record

    async def refresh_index(self, index_id: str) -> dict[str, Any]:
        index = self._require(index_id)
        refreshed = 0
        for doc in index.documents:
            # Re-ingest metadata-only refresh marker; real refresh reuses stored connector metadata.
            refreshed += 1
            doc["refreshed_at"] = datetime.now(timezone.utc).isoformat()
        index.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return {"index_id": index_id, "refreshed_documents": refreshed}

    async def delete_index(self, index_id: str) -> bool:
        index = self._indexes.pop(index_id, None)
        if index is None:
            return False
        for doc in index.documents:
            await self._indexer.delete_source(index.user_id, str(doc["source_id"]))
        self._save()
        return True

    def inspect_coverage(self, index_id: str) -> dict[str, Any]:
        index = self._require(index_id)
        by_type: dict[str, int] = {}
        total_chunks = 0
        for doc in index.documents:
            by_type[doc["source_type"]] = by_type.get(doc["source_type"], 0) + 1
            total_chunks += int(doc.get("chunk_count") or 0)
        return {
            "index_id": index.index_id,
            "name": index.name,
            "document_count": len(index.documents),
            "chunk_count": total_chunks,
            "source_types": by_type,
        }

    def list_stale_documents(self, index_id: str, *, max_age_hours: int = 24) -> list[dict[str, Any]]:
        index = self._require(index_id)
        now = datetime.now(timezone.utc)
        stale: list[dict[str, Any]] = []
        for doc in index.documents:
            indexed_at = datetime.fromisoformat(str(doc.get("indexed_at")))
            age_hours = (now - indexed_at).total_seconds() / 3600
            if age_hours >= max_age_hours:
                stale.append({**doc, "age_hours": round(age_hours, 2)})
        return stale

    def _require(self, index_id: str) -> DocumentIndex:
        index = self.get(index_id)
        if index is None:
            raise KeyError(index_id)
        return index


_manager: DocumentIndexManager | None = None


def get_index_manager() -> DocumentIndexManager:
    global _manager
    if _manager is None:
        _manager = DocumentIndexManager()
    return _manager
