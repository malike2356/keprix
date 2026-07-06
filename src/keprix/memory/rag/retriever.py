"""RAG retrieval with vector and hybrid search."""

from __future__ import annotations

import os
import re
from typing import Any

from keprix.memory.embeddings import EmbeddingService, cosine_similarity
from keprix.memory.rag.indexer import RagIndexer


class RagRetriever:
    def __init__(
        self,
        database_url: str | None = None,
        embeddings: EmbeddingService | None = None,
        indexer: RagIndexer | None = None,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.embeddings = embeddings or EmbeddingService(deterministic=True)
        self.indexer = indexer or RagIndexer(database_url=self.database_url, embeddings=self.embeddings)

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if self.database_url:
            return await self._search_postgres(user_id, query, limit, source_types)
        return await self._search_memory(user_id, query, limit, source_types)

    async def hybrid_search(self, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        vector_results = await self.search(user_id, query, limit=limit * 3)
        keyword_scores = self._keyword_scores(user_id, query, source_types=None)
        combined: dict[str, dict[str, Any]] = {}

        for item in vector_results:
            key = f"{item['source']}:{item['content'][:80]}"
            combined[key] = {
                "content": item["content"],
                "source": item["source"],
                "score": item["score"] * 0.7,
            }

        for item in keyword_scores:
            key = f"{item['source']}:{item['content'][:80]}"
            if key in combined:
                combined[key]["score"] += item["score"] * 0.3
            else:
                combined[key] = {
                    "content": item["content"],
                    "source": item["source"],
                    "score": item["score"] * 0.3,
                }

        ranked = sorted(combined.values(), key=lambda row: row["score"], reverse=True)
        return ranked[:limit]

    async def _search_postgres(
        self,
        user_id: str,
        query: str,
        limit: int,
        source_types: list[str] | None,
    ) -> list[dict[str, Any]]:
        import asyncpg

        query_vec = await self.embeddings.embed(query)
        vector_literal = f"[{','.join(str(v) for v in query_vec)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            if source_types:
                rows = await conn.fetch(
                    """
                    SELECT content, source_type, source_id,
                           1 - (embedding <=> $3::vector) AS score
                    FROM rag_chunks
                    WHERE user_id = $1 AND source_type = ANY($4::text[])
                    ORDER BY embedding <=> $3::vector
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                    vector_literal,
                    source_types,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT content, source_type, source_id,
                           1 - (embedding <=> $3::vector) AS score
                    FROM rag_chunks
                    WHERE user_id = $1
                    ORDER BY embedding <=> $3::vector
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                    vector_literal,
                )
        finally:
            await conn.close()

        return [
            {
                "content": row["content"],
                "source": f"{row['source_type']}:{row['source_id']}",
                "score": float(row["score"]),
            }
            for row in rows
        ]

    async def _search_memory(
        self,
        user_id: str,
        query: str,
        limit: int,
        source_types: list[str] | None,
    ) -> list[dict[str, Any]]:
        query_vec = await self.embeddings.embed(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self.indexer.memory_chunks:
            if chunk["user_id"] != user_id:
                continue
            if source_types and chunk["source_type"] not in source_types:
                continue
            score = cosine_similarity(query_vec, chunk["embedding"])
            scored.append(
                (
                    score,
                    {
                        "content": chunk["content"],
                        "source": f"{chunk['source_type']}:{chunk['source_id']}",
                        "score": score,
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def _keyword_scores(
        self,
        user_id: str,
        query: str,
        source_types: list[str] | None,
    ) -> list[dict[str, Any]]:
        terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
        if not terms:
            return []

        results: list[dict[str, Any]] = []
        for chunk in self.indexer.memory_chunks:
            if chunk["user_id"] != user_id:
                continue
            if source_types and chunk["source_type"] not in source_types:
                continue
            content_lower = chunk["content"].lower()
            hits = sum(1 for term in terms if term in content_lower)
            if hits == 0:
                continue
            score = hits / len(terms)
            results.append(
                {
                    "content": chunk["content"],
                    "source": f"{chunk['source_type']}:{chunk['source_id']}",
                    "score": score,
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results
