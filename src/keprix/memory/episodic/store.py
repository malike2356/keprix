"""Episodic memory store."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from keprix.memory.embeddings import EmbeddingService, cosine_similarity
from keprix.memory.episodic.models import Memory


class EpisodicStore:
    async def save(self, user_id: str, content: str, metadata: dict | None = None) -> str:
        raise NotImplementedError

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        raise NotImplementedError

    async def delete(self, user_id: str, memory_id: str) -> None:
        raise NotImplementedError

    async def list_all(self, user_id: str) -> list[Memory]:
        raise NotImplementedError

    async def clear(self, user_id: str) -> None:
        raise NotImplementedError


class InMemoryEpisodicStore(EpisodicStore):
    """Test-friendly in-memory episodic store with vector search."""

    def __init__(self, embeddings: EmbeddingService | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self.embeddings = embeddings or EmbeddingService(deterministic=True)

    async def save(self, user_id: str, content: str, metadata: dict | None = None) -> str:
        memory_id = str(uuid4())
        embedding = await self.embeddings.embed(content)
        meta = dict(metadata or {})
        ttl_days = int(os.getenv("MEMORY_TTL_DAYS", os.getenv("MEMORY_RETENTION_DAYS", "90")))
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        self._records.append(
            {
                "id": memory_id,
                "user_id": user_id,
                "content": content,
                "embedding": embedding,
                "metadata": meta,
                "tags": list(meta.get("tags") or []),
                "session_id": meta.get("session_id"),
                "created_at": datetime.now(timezone.utc),
                "expires_at": expires_at,
            }
        )
        return memory_id

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        query_vec = await self.embeddings.embed(query)
        now = datetime.now(timezone.utc)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in self._records:
            if record["user_id"] != user_id:
                continue
            if record["expires_at"] < now:
                continue
            score = cosine_similarity(query_vec, record["embedding"])
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [self._to_memory(record, score=score) for score, record in scored[:limit]]

    async def delete(self, user_id: str, memory_id: str) -> None:
        self._records = [
            record
            for record in self._records
            if not (record["user_id"] == user_id and record["id"] == memory_id)
        ]

    async def list_all(self, user_id: str) -> list[Memory]:
        now = datetime.now(timezone.utc)
        rows = [
            record
            for record in self._records
            if record["user_id"] == user_id and record["expires_at"] >= now
        ]
        rows.sort(key=lambda item: item["created_at"], reverse=True)
        return [self._to_memory(record) for record in rows]

    async def clear(self, user_id: str) -> None:
        self._records = [record for record in self._records if record["user_id"] != user_id]

    @staticmethod
    def _to_memory(record: dict[str, Any], *, score: float | None = None) -> Memory:
        return Memory(
            id=record["id"],
            user_id=record["user_id"],
            content=record["content"],
            session_id=record.get("session_id"),
            metadata=dict(record.get("metadata") or {}),
            tags=list(record.get("tags") or []),
            created_at=record.get("created_at"),
            score=score,
        )


class PostgresEpisodicStore(EpisodicStore):
    def __init__(self, database_url: str, embeddings: EmbeddingService | None = None) -> None:
        self.database_url = database_url
        self.embeddings = embeddings or EmbeddingService()

    async def save(self, user_id: str, content: str, metadata: dict | None = None) -> str:
        import asyncpg

        memory_id = str(uuid4())
        embedding = await self.embeddings.embed(content)
        meta = dict(metadata or {})
        tags = list(meta.get("tags") or [])
        session_id = meta.get("session_id")
        ttl_days = int(os.getenv("MEMORY_TTL_DAYS", os.getenv("MEMORY_RETENTION_DAYS", "90")))
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        vector_literal = f"[{','.join(str(v) for v in embedding)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO memories (id, user_id, session_id, content, embedding, metadata, tags, expires_at)
                VALUES ($1::uuid, $2, $3, $4, $5::vector, $6::jsonb, $7, $8)
                """,
                memory_id,
                user_id,
                session_id,
                content,
                vector_literal,
                json.dumps(meta),
                tags,
                expires_at,
            )
        finally:
            await conn.close()
        return memory_id

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        import asyncpg

        query_vec = await self.embeddings.embed(query)
        vector_literal = f"[{','.join(str(v) for v in query_vec)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, content, metadata, tags, created_at,
                       1 - (embedding <=> $3::vector) AS score
                FROM memories
                WHERE user_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
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
            Memory(
                id=str(row["id"]),
                user_id=row["user_id"],
                content=row["content"],
                session_id=row["session_id"],
                metadata=dict(row["metadata"] or {}),
                tags=list(row["tags"] or []),
                created_at=row["created_at"],
                score=float(row["score"]),
            )
            for row in rows
        ]

    async def delete(self, user_id: str, memory_id: str) -> None:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                "DELETE FROM memories WHERE user_id = $1 AND id = $2::uuid",
                user_id,
                memory_id,
            )
        finally:
            await conn.close()

    async def list_all(self, user_id: str) -> list[Memory]:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, content, metadata, tags, created_at
                FROM memories
                WHERE user_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                """,
                user_id,
            )
        finally:
            await conn.close()
        return [
            Memory(
                id=str(row["id"]),
                user_id=row["user_id"],
                content=row["content"],
                session_id=row["session_id"],
                metadata=dict(row["metadata"] or {}),
                tags=list(row["tags"] or []),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def clear(self, user_id: str) -> None:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute("DELETE FROM memories WHERE user_id = $1", user_id)
        finally:
            await conn.close()


def create_episodic_store(database_url: str | None = None) -> EpisodicStore:
    url = database_url or os.getenv("DATABASE_URL", "")
    if url:
        return PostgresEpisodicStore(url)
    return InMemoryEpisodicStore()
