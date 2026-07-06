"""Document stores for RAG pipelines."""

from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.memory.rag.indexer import RagIndexer


class DocumentStore(ABC):
  @abstractmethod
  async def ingest(
      self,
      *,
      user_id: str,
      source_type: str,
      source_id: str,
      content: str,
      chunks: list[str] | None = None,
      embeddings: list[list[float]] | None = None,
  ) -> int:
      raise NotImplementedError

  @abstractmethod
  async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
      raise NotImplementedError

  @abstractmethod
  async def delete_source(self, user_id: str, source_id: str) -> int:
      raise NotImplementedError


class InMemoryDocumentStore(DocumentStore):
    def __init__(self, indexer: RagIndexer | None = None) -> None:
        self.indexer = indexer or RagIndexer()

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
        chunks: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> int:
        _ = chunks, embeddings
        return await self.indexer.ingest(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
        )

    async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        return await self.indexer.list_sources(user_id)

    async def delete_source(self, user_id: str, source_id: str) -> int:
        return await self.indexer.delete_source(user_id, source_id)


class SqliteDocumentStore(DocumentStore):
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".keprix" / "rag_pipeline" / "chunks.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_pipeline_chunks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_json TEXT
                )
                """
            )
            conn.commit()

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
        chunks: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> int:
        from keprix.memory.rag.indexer import chunk_text

        rows = chunks or chunk_text(content)
        await self.delete_source(user_id, source_id)
        with sqlite3.connect(self.path) as conn:
            for index, chunk in enumerate(rows):
                embedding = embeddings[index] if embeddings and index < len(embeddings) else []
                conn.execute(
                    """
                    INSERT INTO rag_pipeline_chunks
                    (id, user_id, source_type, source_id, chunk_index, content, embedding_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        source_type,
                        source_id,
                        index,
                        chunk,
                        json.dumps(embedding),
                    ),
                )
            conn.commit()
        return len(rows)

    async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as conn:
            cursor = conn.execute(
                """
                SELECT source_type, source_id, COUNT(*) AS chunk_count
                FROM rag_pipeline_chunks
                WHERE user_id = ?
                GROUP BY source_type, source_id
                """,
                (user_id,),
            )
            return [
                {
                    "source_type": row[0],
                    "source_id": row[1],
                    "chunk_count": row[2],
                }
                for row in cursor.fetchall()
            ]

    async def delete_source(self, user_id: str, source_id: str) -> int:
        with sqlite3.connect(self.path) as conn:
            cursor = conn.execute(
                "DELETE FROM rag_pipeline_chunks WHERE user_id = ? AND source_id = ?",
                (user_id, source_id),
            )
            conn.commit()
            return int(cursor.rowcount)


class PostgresDocumentStore(DocumentStore):
    """Postgres/pgvector store via existing RagIndexer."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.indexer = RagIndexer(database_url=self.database_url)

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
        chunks: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> int:
        _ = chunks, embeddings
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgresDocumentStore")
        return await self.indexer.ingest(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
        )

    async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        return await self.indexer.list_sources(user_id)

    async def delete_source(self, user_id: str, source_id: str) -> int:
        return await self.indexer.delete_source(user_id, source_id)


class ExternalVectorStore(DocumentStore):
    """Optional adapter for external vector stores (disabled unless configured)."""

    def __init__(self, adapter_name: str = "none", endpoint: str = "") -> None:
        self.adapter_name = adapter_name
        self.endpoint = endpoint
        self._fallback = InMemoryDocumentStore()

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
        chunks: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> int:
        if self.adapter_name == "none" or not self.endpoint:
            return await self._fallback.ingest(
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                content=content,
                chunks=chunks,
                embeddings=embeddings,
            )
        raise NotImplementedError(f"External adapter '{self.adapter_name}' is not configured")

    async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        return await self._fallback.list_sources(user_id)

    async def delete_source(self, user_id: str, source_id: str) -> int:
        return await self._fallback.delete_source(user_id, source_id)


def create_document_store(kind: str = "memory", **kwargs: Any) -> DocumentStore:
    normalized = kind.lower()
    if normalized in {"memory", "in-memory", "test"}:
        return InMemoryDocumentStore(kwargs.get("indexer"))
    if normalized == "sqlite":
        return SqliteDocumentStore(kwargs.get("path"))
    if normalized in {"postgres", "pgvector"}:
        return PostgresDocumentStore(kwargs.get("database_url"))
    if normalized == "external":
        return ExternalVectorStore(
            adapter_name=str(kwargs.get("adapter_name") or "none"),
            endpoint=str(kwargs.get("endpoint") or ""),
        )
    raise ValueError(f"Unknown document store kind: {kind}")
