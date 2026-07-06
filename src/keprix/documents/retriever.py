"""Document retriever with metadata filters."""

from __future__ import annotations

from typing import Any

from keprix.memory.rag.indexer import RagIndexer
from keprix.memory.rag.retriever import RagRetriever


class DocumentRetriever:
    def __init__(self, retriever: RagRetriever | None = None, *, indexer: RagIndexer | None = None) -> None:
        if retriever is not None:
            self._retriever = retriever
        else:
            self._retriever = RagRetriever(indexer=indexer or RagIndexer())

    async def retrieve(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
        source_types: list[str] | None = None,
        hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        if hybrid:
            rows = await self._retriever.hybrid_search(user_id, query, limit=limit * 2)
        else:
            rows = await self._retriever.search(user_id, query, limit=limit * 2, source_types=source_types)
        if source_types:
            rows = [row for row in rows if row.get("source", "").split(":", 1)[0] in source_types]
        return rows[:limit]
