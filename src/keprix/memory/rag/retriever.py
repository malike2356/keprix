"""RAG retrieval with vector and hybrid search."""

from __future__ import annotations

import re
from typing import Any

from keprix.memory.embeddings import EmbeddingService, cosine_similarity
from keprix.memory.rag.indexer import RagIndexer, resolve_rag_database_url


class RagRetriever:
    def __init__(
        self,
        database_url: str | None = None,
        embeddings: EmbeddingService | None = None,
        indexer: RagIndexer | None = None,
    ) -> None:
        if database_url is None and indexer is not None:
            self.database_url = indexer.database_url
        else:
            self.database_url = resolve_rag_database_url(database_url)
        self.embeddings = embeddings or EmbeddingService(deterministic=True)
        self.indexer = indexer or RagIndexer(
            database_url=self.database_url,
            embeddings=self.embeddings,
        )

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        include_quarantined: bool = False,
    ) -> list[dict[str, Any]]:
        if self.database_url:
            return await self._search_postgres(user_id, query, limit, source_types, include_quarantined=include_quarantined)
        return await self._search_memory(user_id, query, limit, source_types, include_quarantined=include_quarantined)

    async def hybrid_search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        include_quarantined: bool = False,
    ) -> list[dict[str, Any]]:
        vector_results = await self.search(
            user_id,
            query,
            limit=limit * 3,
            source_types=source_types,
            include_quarantined=include_quarantined,
        )
        if self.database_url:
            keyword_scores = await self._keyword_scores_postgres(
                user_id,
                query,
                source_types=source_types,
                include_quarantined=include_quarantined,
            )
        else:
            keyword_scores = self._keyword_scores(
                user_id,
                query,
                source_types=source_types,
                include_quarantined=include_quarantined,
            )
        combined: dict[str, dict[str, Any]] = {}

        for item in vector_results:
            key = f"{item['source']}:{item['content'][:80]}"
            combined[key] = {
                "content": item["content"],
                "source": item["source"],
                "score": item["score"] * 0.35,
            }

        for item in keyword_scores:
            key = f"{item['source']}:{item['content'][:80]}"
            if key in combined:
                combined[key]["score"] += item["score"] * 0.65
            else:
                combined[key] = {
                    "content": item["content"],
                    "source": item["source"],
                    "score": item["score"] * 0.65,
                }

        ranked = sorted(combined.values(), key=lambda row: row["score"], reverse=True)
        return ranked[:limit]

    async def _search_postgres(
        self,
        user_id: str,
        query: str,
        limit: int,
        source_types: list[str] | None,
        include_quarantined: bool,
    ) -> list[dict[str, Any]]:
        import asyncpg

        await self.indexer.ensure_schema()
        query_vec = await self.embeddings.embed(query)
        vector_literal = f"[{','.join(str(v) for v in query_vec)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            if source_types:
                rows = await conn.fetch(
                    """
                    SELECT content, source_type, source_id, COALESCE(trust, 'trusted') AS trust,
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
                    SELECT content, source_type, source_id, COALESCE(trust, 'trusted') AS trust,
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
                "trust": row["trust"] if "trust" in row.keys() else "trusted",
                "score": float(row["score"]),
            }
            for row in rows
            if include_quarantined or str(row["trust"] if "trust" in row.keys() else "trusted").lower() != "quarantined"
        ]

    async def _search_memory(
        self,
        user_id: str,
        query: str,
        limit: int,
        source_types: list[str] | None,
        include_quarantined: bool,
    ) -> list[dict[str, Any]]:
        query_vec = await self.embeddings.embed(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in self.indexer.memory_chunks:
            if chunk["user_id"] != user_id:
                continue
            if source_types and chunk["source_type"] not in source_types:
                continue
            if not include_quarantined and str(chunk.get("trust") or "trusted").lower() == "quarantined":
                continue
            score = cosine_similarity(query_vec, chunk["embedding"])
            scored.append(
                (
                    score,
                    {
                        "content": chunk["content"],
                        "source": f"{chunk['source_type']}:{chunk['source_id']}",
                        "trust": chunk.get("trust", "trusted"),
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
        include_quarantined: bool,
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
            if not include_quarantined and str(chunk.get("trust") or "trusted").lower() == "quarantined":
                continue
            source = f"{chunk['source_type']}:{chunk['source_id']}"
            searchable = f"{source}\n{chunk['content']}".lower()
            hits = sum(1 for term in terms if term in searchable)
            if hits == 0:
                continue
            score = hits / len(terms)
            results.append(
                {
                    "content": chunk["content"],
                    "source": source,
                        "trust": chunk.get("trust", "trusted"),
                        "score": score,
                    }
                )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results

    async def _keyword_scores_postgres(
        self,
        user_id: str,
        query: str,
        source_types: list[str] | None,
        include_quarantined: bool,
        *,
        scan_limit: int = 500,
    ) -> list[dict[str, Any]]:
        import asyncpg

        terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
        if not terms:
            return []
        patterns = [f"%{term}%" for term in terms]
        conn = await asyncpg.connect(self.database_url)
        try:
            if source_types:
                rows = await conn.fetch(
                    """
                    SELECT content, source_type, source_id, COALESCE(trust, 'trusted') AS trust
                    FROM rag_chunks
                    WHERE user_id = $1
                      AND source_type = ANY($2::text[])
                      AND (content ILIKE ANY($3::text[]) OR source_id ILIKE ANY($3::text[]))
                    LIMIT $4
                    """,
                    user_id,
                    source_types,
                    patterns,
                    scan_limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT content, source_type, source_id, COALESCE(trust, 'trusted') AS trust
                    FROM rag_chunks
                    WHERE user_id = $1
                      AND (content ILIKE ANY($2::text[]) OR source_id ILIKE ANY($2::text[]))
                    LIMIT $3
                    """,
                    user_id,
                    patterns,
                    scan_limit,
                )
        finally:
            await conn.close()

        results: list[dict[str, Any]] = []
        for row in rows:
            source = f"{row['source_type']}:{row['source_id']}"
            if not include_quarantined and str(row["trust"] if "trust" in row.keys() else "trusted").lower() == "quarantined":
                continue
            searchable = f"{source}\n{row['content']}".lower()
            hits = sum(1 for term in terms if term in searchable)
            if hits == 0:
                continue
            results.append(
                {
                    "content": row["content"],
                    "source": source,
                    "trust": row["trust"] if "trust" in row.keys() else "trusted",
                    "score": hits / len(terms),
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results
