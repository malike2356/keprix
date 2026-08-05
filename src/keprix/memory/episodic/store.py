"""Episodic memory store."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from keprix.memory.embeddings import EmbeddingService, cosine_similarity
from keprix.memory.episodic.models import Memory


def _merge_meta(base: dict[str, Any], extra: dict[str, Any] | None) -> dict[str, Any]:
    meta = dict(base or {})
    if extra:
        meta.update(extra)
    return meta


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    try:
        return dict(value)
    except Exception:
        return {}


class EpisodicStore:
    async def save(self, user_id: str, content: str, metadata: dict | None = None) -> str:
        raise NotImplementedError

    async def update(
        self,
        user_id: str,
        memory_id: str,
        *,
        content: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        raise NotImplementedError

    async def reinforce(self, user_id: str, memory_id: str) -> None:
        raise NotImplementedError

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        raise NotImplementedError

    async def delete(self, user_id: str, memory_id: str) -> None:
        raise NotImplementedError

    async def list_all(self, user_id: str) -> list[Memory]:
        raise NotImplementedError

    async def clear(self, user_id: str) -> None:
        raise NotImplementedError

    async def export_all(self, user_id: str) -> list[dict[str, Any]]:
        return [m.to_dict() for m in await self.list_all(user_id)]


class InMemoryEpisodicStore(EpisodicStore):
    """Test-friendly in-memory episodic store with vector search."""

    def __init__(self, embeddings: EmbeddingService | None = None) -> None:
        self._records: list[dict[str, Any]] = []
        self.embeddings = embeddings or EmbeddingService(deterministic=True)

    async def save(self, user_id: str, content: str, metadata: dict | None = None) -> str:
        memory_id = str(uuid4())
        embedding = await self.embeddings.embed(content)
        meta = dict(metadata or {})
        meta.setdefault("memory_type", meta.get("memory_type") or "episodic")
        meta.setdefault("belief_state", "active")
        meta.setdefault("confidence", 0.7)
        meta.setdefault("access_count", 0)
        meta.setdefault("modality", meta.get("modality") or "text")
        meta.setdefault("model_side", meta.get("model_side") or "user")
        meta.setdefault("source", meta.get("source") or "manual")
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

    async def update(
        self,
        user_id: str,
        memory_id: str,
        *,
        content: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        for record in self._records:
            if record["user_id"] != user_id or record["id"] != memory_id:
                continue
            if content is not None:
                record["content"] = content
                record["embedding"] = await self.embeddings.embed(content)
            meta = _merge_meta(record.get("metadata") or {}, extra)
            if tags is not None:
                record["tags"] = list(tags)
                meta["tags"] = list(tags)
            record["metadata"] = meta
            return True
        return False

    async def reinforce(self, user_id: str, memory_id: str) -> None:
        for record in self._records:
            if record["user_id"] == user_id and record["id"] == memory_id:
                meta = dict(record.get("metadata") or {})
                meta["access_count"] = int(meta.get("access_count") or 0) + 1
                meta["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
                record["metadata"] = meta
                return

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        query_vec = await self.embeddings.embed(query)
        now = datetime.now(timezone.utc)
        scored: list[tuple[float, dict[str, Any]]] = []
        for record in self._records:
            if record["user_id"] != user_id:
                continue
            if record["expires_at"] < now:
                continue
            meta = record.get("metadata") or {}
            if meta.get("belief_state") in {"superseded", "archived", "rejected"}:
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
        meta.setdefault("memory_type", meta.get("memory_type") or "episodic")
        meta.setdefault("belief_state", "active")
        meta.setdefault("confidence", 0.7)
        meta.setdefault("access_count", 0)
        meta.setdefault("modality", meta.get("modality") or "text")
        meta.setdefault("model_side", meta.get("model_side") or "user")
        meta.setdefault("source", meta.get("source") or "manual")
        tags = list(meta.get("tags") or [])
        session_id = meta.get("session_id")
        ttl_days = int(os.getenv("MEMORY_TTL_DAYS", os.getenv("MEMORY_RETENTION_DAYS", "90")))
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        vector_literal = f"[{','.join(str(v) for v in embedding)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO memories (
                    id, user_id, session_id, content, embedding, metadata, tags, expires_at,
                    memory_type, confidence, belief_state, access_count, pin, scope,
                    workspace_id, modality, model_side, source
                )
                VALUES (
                    $1::uuid, $2, $3, $4, $5::vector, $6::jsonb, $7, $8,
                    $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
                """,
                memory_id,
                user_id,
                session_id,
                content,
                vector_literal,
                json.dumps(meta),
                tags,
                expires_at,
                meta.get("memory_type") or "episodic",
                float(meta.get("confidence") or 0.7),
                meta.get("belief_state") or "active",
                int(meta.get("access_count") or 0),
                bool(meta.get("pin") or False),
                meta.get("scope") or "user",
                meta.get("workspace_id"),
                meta.get("modality") or "text",
                meta.get("model_side") or "user",
                meta.get("source") or "manual",
            )
        except Exception:
            # Fallback for pre-migration schemas.
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

    async def update(
        self,
        user_id: str,
        memory_id: str,
        *,
        content: str | None = None,
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                SELECT content, metadata, tags
                FROM memories
                WHERE user_id = $1 AND id = $2::uuid
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                user_id,
                memory_id,
            )
            if row is None:
                return False
            next_content = content if content is not None else row["content"]
            next_tags = list(tags) if tags is not None else list(row["tags"] or [])
            meta = _merge_meta(_as_dict(row["metadata"]), extra)
            meta["tags"] = next_tags
            embedding = await self.embeddings.embed(next_content)
            vector_literal = f"[{','.join(str(v) for v in embedding)}]"
            try:
                await conn.execute(
                    """
                    UPDATE memories
                    SET content = $3,
                        embedding = $4::vector,
                        metadata = $5::jsonb,
                        tags = $6,
                        memory_type = COALESCE($7, memory_type),
                        confidence = COALESCE($8, confidence),
                        belief_state = COALESCE($9, belief_state),
                        pin = COALESCE($10, pin),
                        modality = COALESCE($11, modality),
                        model_side = COALESCE($12, model_side),
                        source = COALESCE($13, source),
                        superseded_by = COALESCE($14::uuid, superseded_by)
                    WHERE user_id = $1 AND id = $2::uuid
                    """,
                    user_id,
                    memory_id,
                    next_content,
                    vector_literal,
                    json.dumps(meta),
                    next_tags,
                    meta.get("memory_type"),
                    float(meta["confidence"]) if meta.get("confidence") is not None else None,
                    meta.get("belief_state"),
                    bool(meta["pin"]) if meta.get("pin") is not None else None,
                    meta.get("modality"),
                    meta.get("model_side"),
                    meta.get("source"),
                    meta.get("superseded_by"),
                )
            except Exception:
                await conn.execute(
                    """
                    UPDATE memories
                    SET content = $3,
                        embedding = $4::vector,
                        metadata = $5::jsonb,
                        tags = $6
                    WHERE user_id = $1 AND id = $2::uuid
                    """,
                    user_id,
                    memory_id,
                    next_content,
                    vector_literal,
                    json.dumps(meta),
                    next_tags,
                )
            return True
        finally:
            await conn.close()

    async def reinforce(self, user_id: str, memory_id: str) -> None:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            try:
                await conn.execute(
                    """
                    UPDATE memories
                    SET access_count = COALESCE(access_count, 0) + 1,
                        last_accessed_at = NOW(),
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{access_count}',
                            to_jsonb(COALESCE(access_count, 0) + 1),
                            true
                        )
                    WHERE user_id = $1 AND id = $2::uuid
                    """,
                    user_id,
                    memory_id,
                )
            except Exception:
                row = await conn.fetchrow(
                    "SELECT metadata FROM memories WHERE user_id = $1 AND id = $2::uuid",
                    user_id,
                    memory_id,
                )
                if row:
                    meta = _as_dict(row["metadata"])
                    meta["access_count"] = int(meta.get("access_count") or 0) + 1
                    meta["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
                    await conn.execute(
                        "UPDATE memories SET metadata = $3::jsonb WHERE user_id = $1 AND id = $2::uuid",
                        user_id,
                        memory_id,
                        json.dumps(meta),
                    )
        finally:
            await conn.close()

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        import asyncpg

        query_vec = await self.embeddings.embed(query)
        vector_literal = f"[{','.join(str(v) for v in query_vec)}]"
        conn = await asyncpg.connect(self.database_url)
        try:
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, user_id, session_id, content, metadata, tags, created_at,
                           1 - (embedding <=> $3::vector) AS score
                    FROM memories
                    WHERE user_id = $1
                      AND (expires_at IS NULL OR expires_at > NOW())
                      AND COALESCE(belief_state, 'active') NOT IN ('superseded', 'archived', 'rejected')
                    ORDER BY embedding <=> $3::vector
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                    vector_literal,
                )
            except Exception:
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
        out: list[Memory] = []
        for row in rows:
            meta = _as_dict(row["metadata"])
            if meta.get("belief_state") in {"superseded", "archived", "rejected"}:
                continue
            out.append(
                Memory(
                    id=str(row["id"]),
                    user_id=row["user_id"],
                    content=row["content"],
                    session_id=row["session_id"],
                    metadata=meta,
                    tags=list(row["tags"] or []),
                    created_at=row["created_at"],
                    score=float(row["score"]),
                )
            )
        return out

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
                metadata=_as_dict(row["metadata"]),
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
    from keprix.memory.schema import resolve_database_url

    url = resolve_database_url(database_url)
    if url:
        return PostgresEpisodicStore(url)
    return InMemoryEpisodicStore()
