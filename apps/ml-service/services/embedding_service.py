from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from providers.base import EmbeddingProvider
from utils.caching import get_cached, set_cached
from utils.chunking import chunk_document


@dataclass
class SearchResult:
    content: str
    score: float
    source_uri: str
    chunk_index: int
    metadata: dict[str, Any]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider, db_pool: Any):
        self.provider = provider
        self.pool = db_pool

    async def create_pack(self, pack_id: str, display_name: str, description: str = "") -> None:
        dims = self.provider.dimensions("voyage-3")
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO knowledge_packs (pack_id, display_name, description, embedding_dims)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (pack_id) DO UPDATE SET
                  display_name=EXCLUDED.display_name,
                  description=EXCLUDED.description,
                  updated_at=now()
                """,
                pack_id,
                display_name,
                description,
                dims,
            )

    async def delete_pack(self, pack_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM knowledge_packs WHERE pack_id=$1", pack_id)

    async def list_packs(self) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT pack_id, display_name, description, embedding_model, embedding_dims,
                       chunk_count, indexed_at, created_at, updated_at
                FROM knowledge_packs
                ORDER BY pack_id
                """
            )
        return [dict(row) for row in rows]

    async def embed_texts(self, texts: list[str], model: str = "voyage-3") -> list[list[float]]:
        cache_payload = {"texts": texts, "model": model}
        cached = await get_cached("embed", cache_payload)
        if cached is not None:
            return cached
        embeddings = await self.provider.embed(texts, model)
        await set_cached("embed", cache_payload, embeddings)
        return embeddings

    async def ingest_document(
        self,
        pack_id: str,
        source_uri: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        max_tokens_per_chunk: int = 512,
        overlap_tokens: int = 64,
    ) -> int:
        chunks = chunk_document(content, max_tokens_per_chunk, overlap_tokens, metadata or {})
        if not chunks:
            return 0

        embeddings: list[list[float]] = []
        for start in range(0, len(chunks), 96):
            batch = chunks[start:start + 96]
            embeddings.extend(await self.embed_texts([chunk.text for chunk in batch]))

        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM knowledge_chunks WHERE pack_id=$1 AND source_uri=$2", pack_id, source_uri)
            await conn.executemany(
                """
                INSERT INTO knowledge_chunks
                  (pack_id, source_uri, chunk_index, content, token_count, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::vector, $7::jsonb)
                """,
                [
                    (
                        pack_id,
                        source_uri,
                        chunk.index,
                        chunk.text,
                        chunk.token_count,
                        vector_literal(embedding),
                        json.dumps(chunk.metadata),
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ],
            )
            await conn.execute(
                """
                UPDATE knowledge_packs
                SET chunk_count=(SELECT COUNT(*) FROM knowledge_chunks WHERE pack_id=$1),
                    indexed_at=now(),
                    updated_at=now()
                WHERE pack_id=$1
                """,
                pack_id,
            )
        return len(chunks)

    async def search(
        self,
        pack_id: str,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.65,
    ) -> list[SearchResult]:
        cache_payload = {
            "pack_id": pack_id,
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold,
        }
        cached = await get_cached("search", cache_payload)
        if cached is not None:
            return [SearchResult(**row) for row in cached]

        query_embedding = (await self.embed_texts([query]))[0]
        vector = vector_literal(query_embedding)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT content, source_uri, chunk_index, metadata,
                       1 - (embedding <=> $1::vector) AS score
                FROM knowledge_chunks
                WHERE pack_id=$2
                  AND 1 - (embedding <=> $1::vector) >= $3
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                vector,
                pack_id,
                score_threshold,
                top_k,
            )

        results = [
            SearchResult(
                content=row["content"],
                score=float(row["score"]),
                source_uri=row["source_uri"],
                chunk_index=int(row["chunk_index"]),
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]
        await set_cached("search", cache_payload, [asdict(result) for result in results], ttl=3600)
        return results
