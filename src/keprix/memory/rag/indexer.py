"""RAG document chunking and indexing."""

from __future__ import annotations

import csv
import io
import os
import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

from keprix.memory.embeddings import EmbeddingService


def resolve_rag_database_url(explicit: str | None = None) -> str:
    if explicit is None:
        raw = (os.getenv("DATABASE_URL") or os.getenv("KEPRIX_DATABASE_URL") or "").strip()
    else:
        raw = explicit.strip()
    if raw.startswith("postgresql+asyncpg://"):
        return "postgresql://" + raw.removeprefix("postgresql+asyncpg://")
    if raw.startswith("postgres+asyncpg://"):
        return "postgresql://" + raw.removeprefix("postgres+asyncpg://")
    return raw


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunk_words = max(1, chunk_tokens)
    overlap_words = max(0, min(overlap_tokens, chunk_words // 2))
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_words)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(0, end - overlap_words)
    return chunks


def parse_plaintext(content: str) -> str:
    return content.strip()


def parse_markdown(content: str) -> str:
    text = re.sub(r"```.*?```", " ", content, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    return " ".join(text.split())


def parse_html(content: str) -> str:
    parser = _TextExtractor()
    parser.feed(content)
    return parser.text()


def parse_email(raw: bytes | str) -> str:
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="ignore")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    parts = []
    if message.get("subject"):
        parts.append(str(message["subject"]))
    body = message.get_body(preferencelist=("plain", "html"))
    if body is not None:
        payload = body.get_content()
        if body.get_content_type() == "text/html":
            parts.append(parse_html(str(payload)))
        else:
            parts.append(str(payload))
    return "\n".join(part.strip() for part in parts if part and str(part).strip())


def parse_csv(content: str) -> str:
    reader = csv.reader(io.StringIO(content))
    rows = [" | ".join(cell.strip() for cell in row if cell.strip()) for row in reader]
    return "\n".join(row for row in rows if row)


def parse_pdf(content: bytes) -> str:
    # Lightweight PDF text extraction without extra deps: scan literal strings.
    text = content.decode("latin-1", errors="ignore")
    literals = re.findall(r"\(([^()\\]{3,})\)", text)
    return " ".join(literals)


class RagIndexer:
    def __init__(
        self,
        database_url: str | None = None,
        embeddings: EmbeddingService | None = None,
    ) -> None:
        self.database_url = resolve_rag_database_url(database_url)
        self.embeddings = embeddings or EmbeddingService(deterministic=True)
        self._memory_chunks: list[dict[str, Any]] = []
        self._schema_ready = False

    async def ensure_schema(self) -> None:
        if not self.database_url or self._schema_ready:
            return
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                CREATE EXTENSION IF NOT EXISTS vector;

                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    metadata JSONB DEFAULT '{}',
                    tags TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    trust TEXT NOT NULL DEFAULT 'trusted',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_memories_user_created
                    ON memories (user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_source
                    ON rag_chunks (user_id, source_type, source_id);
                """
            )
            try:
                await conn.execute("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS trust TEXT NOT NULL DEFAULT 'trusted'")
            except Exception:
                pass
            for stmt in (
                """
                CREATE INDEX IF NOT EXISTS idx_memories_embedding
                    ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
                    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_content_tsv
                    ON rag_chunks USING gin(to_tsvector('english', content))
                """,
            ):
                try:
                    await conn.execute(stmt)
                except Exception:
                    pass
        finally:
            await conn.close()
        self._schema_ready = True

    async def ingest(
        self,
        *,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str | bytes,
        trust: str = "trusted",
    ) -> int:
        text = self._normalize_content(source_type, content)
        chunks = chunk_text(text, chunk_tokens=512, overlap_tokens=64)
        if not chunks:
            return 0

        if self.database_url:
            await self.ensure_schema()
            return await self._persist_postgres(user_id, source_type, source_id, chunks, trust=trust)
        return await self._persist_memory(user_id, source_type, source_id, chunks, trust=trust)

    async def delete_source(self, user_id: str, source_id: str) -> int:
        if self.database_url:
            import asyncpg

            await self.ensure_schema()
            conn = await asyncpg.connect(self.database_url)
            try:
                result = await conn.execute(
                    "DELETE FROM rag_chunks WHERE user_id = $1 AND source_id = $2",
                    user_id,
                    source_id,
                )
            finally:
                await conn.close()
            return int(result.split()[-1]) if result else 0

        before = len(self._memory_chunks)
        self._memory_chunks = [
            chunk
            for chunk in self._memory_chunks
            if not (chunk["user_id"] == user_id and chunk["source_id"] == source_id)
        ]
        return before - len(self._memory_chunks)

    async def list_sources(self, user_id: str) -> list[dict[str, Any]]:
        if self.database_url:
            import asyncpg

            await self.ensure_schema()
            conn = await asyncpg.connect(self.database_url)
            try:
                rows = await conn.fetch(
                    """
                    SELECT source_type, source_id, COUNT(*) AS chunk_count,
                           MAX(created_at) AS updated_at
                    FROM rag_chunks
                    WHERE user_id = $1
                    GROUP BY source_type, source_id
                    ORDER BY updated_at DESC
                    """,
                    user_id,
                )
            finally:
                await conn.close()
            return [
                {
                    "source_type": row["source_type"],
                    "source_id": row["source_id"],
                    "chunk_count": row["chunk_count"],
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                }
                for row in rows
            ]

        grouped: dict[tuple[str, str], int] = {}
        for chunk in self._memory_chunks:
            if chunk["user_id"] != user_id:
                continue
            key = (chunk["source_type"], chunk["source_id"])
            grouped[key] = grouped.get(key, 0) + 1
        return [
            {"source_type": key[0], "source_id": key[1], "chunk_count": count}
            for key, count in grouped.items()
        ]

    def _normalize_content(self, source_type: str, content: str | bytes) -> str:
        source_type = source_type.lower()
        if source_type in {"text", "plaintext", "plain"}:
            return parse_plaintext(str(content))
        if source_type == "markdown":
            return parse_markdown(str(content))
        if source_type == "html":
            return parse_html(str(content))
        if source_type == "email":
            return parse_email(content)
        if source_type == "csv":
            return parse_csv(str(content))
        if source_type == "pdf" and isinstance(content, bytes | bytearray):
            return parse_pdf(bytes(content))
        return parse_plaintext(str(content))

    async def _persist_memory(
        self,
        user_id: str,
        source_type: str,
        source_id: str,
        chunks: list[str],
        *,
        trust: str = "trusted",
    ) -> int:
        await self.delete_source(user_id, source_id)
        for index, chunk in enumerate(chunks):
            embedding = await self.embeddings.embed(chunk)
            self._memory_chunks.append(
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": embedding,
                    "trust": trust,
                }
            )
        return len(chunks)

    async def _persist_postgres(
        self,
        user_id: str,
        source_type: str,
        source_id: str,
        chunks: list[str],
        *,
        trust: str = "trusted",
    ) -> int:
        import asyncpg

        await self.delete_source(user_id, source_id)
        conn = await asyncpg.connect(self.database_url)
        try:
            for index, chunk in enumerate(chunks):
                embedding = await self.embeddings.embed(chunk)
                vector_literal = f"[{','.join(str(v) for v in embedding)}]"
                await conn.execute(
                    """
                    INSERT INTO rag_chunks (
                        user_id, source_type, source_id, chunk_index, content, embedding, trust
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::vector, $7)
                    """,
                    user_id,
                    source_type,
                    source_id,
                    index,
                    chunk,
                    vector_literal,
                    trust,
                )
        finally:
            await conn.close()
        return len(chunks)

    @property
    def memory_chunks(self) -> list[dict[str, Any]]:
        return list(self._memory_chunks)
