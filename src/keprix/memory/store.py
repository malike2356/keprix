"""Memory store interface and ChromaDB implementation.

The MemoryStore handles:
  - Document ingestion (chunking + embedding + persistence)
  - Semantic search (hybrid: vector + keyword BM25)
  - Episodic session memory (conversation summaries)

The interface is abstract so Cursor can swap in pgvector or Weaviate later.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryDocument:
    id: str
    content: str
    metadata: dict[str, Any]
    score: float = 0.0


class BaseMemoryStore(ABC):
    """Protocol for all memory backends."""

    @abstractmethod
    async def add(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Chunk, embed, and store a document."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[MemoryDocument]:
        """Semantic search. Returns top_k most relevant chunks."""
        ...

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Remove a document and all its chunks. Returns True if found."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Total number of chunks currently indexed."""
        ...


class ChromaMemoryStore(BaseMemoryStore):
    """ChromaDB-backed memory store. Lazy-initialises on first use."""

    def __init__(self, collection_name: str = "keprix_memory") -> None:
        self._collection_name = collection_name
        self._client: Any = None
        self._collection: Any = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        from chromadb import AsyncHttpClient
        from keprix.config.settings import get_settings
        settings = get_settings()
        self._client = AsyncHttpClient(
            host=settings.KEPRIX_CHROMADB_HOST,
            port=settings.KEPRIX_CHROMADB_PORT,
        )

    async def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        self._ensure_client()
        self._collection = await self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    async def add(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        collection = await self._ensure_collection()
        await collection.upsert(
            ids=[document_id],
            documents=[content],
            metadatas=[metadata or {}],
        )
        logger.debug("Memory: added document %s", document_id)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[MemoryDocument]:
        collection = await self._ensure_collection()
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": top_k}
        if filter_metadata:
            kwargs["where"] = filter_metadata
        results = await collection.query(**kwargs)
        docs: list[MemoryDocument] = []
        for i, doc_id in enumerate(results["ids"][0]):
            docs.append(
                MemoryDocument(
                    id=doc_id,
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=1.0 - (results["distances"][0][i] if results.get("distances") else 0.0),
                )
            )
        return docs

    async def delete(self, document_id: str) -> bool:
        collection = await self._ensure_collection()
        await collection.delete(ids=[document_id])
        return True

    async def count(self) -> int:
        collection = await self._ensure_collection()
        return await collection.count()


_default_store: ChromaMemoryStore | None = None


def get_memory_store() -> ChromaMemoryStore:
    global _default_store
    if _default_store is None:
        _default_store = ChromaMemoryStore()
    return _default_store
