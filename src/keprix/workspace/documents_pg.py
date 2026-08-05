"""Postgres persistence for workspace documents."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from keprix.database import get_engine, get_session_factory


def _use_db() -> bool:
    if "pytest" in sys.modules:
        return False
    return get_session_factory() is not None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_doc(row: Any) -> dict[str, Any]:
    mapping = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    tags = mapping.get("tags") or []
    if isinstance(tags, str):
        tags = [t for t in tags.strip("{}").split(",") if t]
    return {
        "id": str(mapping["id"]),
        "user_id": mapping["user_id"],
        "title": mapping.get("title") or "Untitled",
        "content": mapping.get("content") or "",
        "format": mapping.get("format") or "markdown",
        "tags": list(tags),
        "is_shared": bool(mapping.get("is_shared")),
        "share_token": mapping.get("share_token"),
        "is_favorite": bool(mapping.get("is_favorite")),
        "folder": mapping.get("folder") or "",
        "created_at": mapping.get("created_at"),
        "updated_at": mapping.get("updated_at"),
    }


async def ensure_workspace_document_tables() -> list[str]:
    engine = get_engine()
    if engine is None:
        return []
    ddl = """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT 'Untitled',
        content TEXT NOT NULL DEFAULT '',
        format TEXT NOT NULL DEFAULT 'markdown',
        tags TEXT[] DEFAULT '{}',
        is_shared BOOLEAN DEFAULT false,
        share_token TEXT UNIQUE,
        is_favorite BOOLEAN DEFAULT false,
        folder TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_documents_user_updated ON documents (user_id, updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin(tags);
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT false;
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS folder TEXT DEFAULT '';
    CREATE TABLE IF NOT EXISTS document_versions (
        id UUID PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_document_versions_doc
      ON document_versions (document_id, created_at DESC);
    """
    async with engine.begin() as conn:
        for stmt in ddl.split(";"):
            piece = stmt.strip()
            if piece:
                await conn.execute(text(piece))
    return ["documents", "document_versions"]


async def pg_create_document(user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    doc_id = str(data.get("id") or uuid.uuid4())
    now = _utcnow()
    async with factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO documents
                  (id, user_id, title, content, format, tags, is_shared, share_token,
                   is_favorite, folder, created_at, updated_at)
                VALUES
                  (:id, :user_id, :title, :content, :format, :tags, false, NULL,
                   :is_favorite, :folder, :created_at, :updated_at)
                """
            ),
            {
                "id": doc_id,
                "user_id": user_id,
                "title": data.get("title") or "Untitled",
                "content": data.get("content") or "",
                "format": data.get("format") or "markdown",
                "tags": list(data.get("tags") or []),
                "is_favorite": bool(data.get("is_favorite")),
                "folder": data.get("folder") or "",
                "created_at": now,
                "updated_at": now,
            },
        )
        await session.commit()
    return await pg_get_document(user_id, doc_id)


async def pg_list_documents(
    user_id: str,
    *,
    tag: str | None = None,
    fmt: str | None = None,
    q: str | None = None,
    folder: str | None = None,
    favorites_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    clauses = ["user_id = :user_id"]
    params: dict[str, Any] = {"user_id": user_id, "limit": limit, "offset": offset}
    if tag:
        clauses.append(":tag = ANY(tags)")
        params["tag"] = tag
    if fmt:
        clauses.append("format = :fmt")
        params["fmt"] = fmt
    if folder is not None:
        clauses.append("folder = :folder")
        params["folder"] = folder
    if favorites_only:
        clauses.append("is_favorite = true")
    if q:
        clauses.append("(title ILIKE :q OR content ILIKE :q)")
        params["q"] = f"%{q}%"
    where = " AND ".join(clauses)
    async with factory() as session:
        result = await session.execute(
            text(
                f"""
                SELECT id, user_id, title, content, format, tags, is_shared, share_token,
                       is_favorite, folder, created_at, updated_at
                FROM documents
                WHERE {where}
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [_row_to_doc(row) for row in result]


async def pg_get_document(user_id: str, doc_id: str) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, user_id, title, content, format, tags, is_shared, share_token,
                       is_favorite, folder, created_at, updated_at
                FROM documents WHERE id = :id AND user_id = :user_id
                """
            ),
            {"id": doc_id, "user_id": user_id},
        )
        row = result.first()
        return _row_to_doc(row) if row else None


async def pg_update_document(user_id: str, doc_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not _use_db():
        return None
    existing = await pg_get_document(user_id, doc_id)
    if existing is None:
        return None
    # Snapshot version before content/title change
    if "content" in updates or "title" in updates:
        await pg_add_version(user_id, existing)
    factory = get_session_factory()
    assert factory is not None
    fields = []
    params: dict[str, Any] = {"id": doc_id, "user_id": user_id, "updated_at": _utcnow()}
    for key in ("title", "content", "format", "tags", "is_favorite", "folder", "is_shared", "share_token"):
        if key in updates and updates[key] is not None:
            fields.append(f"{key} = :{key}")
            params[key] = updates[key]
    if not fields:
        return existing
    fields.append("updated_at = :updated_at")
    async with factory() as session:
        await session.execute(
            text(f"UPDATE documents SET {', '.join(fields)} WHERE id = :id AND user_id = :user_id"),
            params,
        )
        await session.commit()
    return await pg_get_document(user_id, doc_id)


async def pg_delete_document(user_id: str, doc_id: str) -> bool | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        result = await session.execute(
            text("DELETE FROM documents WHERE id = :id AND user_id = :user_id"),
            {"id": doc_id, "user_id": user_id},
        )
        await session.commit()
        return (result.rowcount or 0) > 0


async def pg_add_version(user_id: str, doc: dict[str, Any]) -> None:
    if not _use_db():
        return
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO document_versions (id, document_id, user_id, title, content, created_at)
                VALUES (:id, :document_id, :user_id, :title, :content, :created_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "document_id": doc["id"],
                "user_id": user_id,
                "title": doc.get("title") or "Untitled",
                "content": doc.get("content") or "",
                "created_at": _utcnow(),
            },
        )
        # Keep last 25 versions
        await session.execute(
            text(
                """
                DELETE FROM document_versions
                WHERE document_id = :document_id
                  AND id NOT IN (
                    SELECT id FROM document_versions
                    WHERE document_id = :document_id
                    ORDER BY created_at DESC
                    LIMIT 25
                  )
                """
            ),
            {"document_id": doc["id"]},
        )
        await session.commit()


async def pg_list_versions(user_id: str, doc_id: str, *, limit: int = 25) -> list[dict[str, Any]] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, document_id, title, content, created_at
                FROM document_versions
                WHERE document_id = :document_id AND user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"document_id": doc_id, "user_id": user_id, "limit": limit},
        )
        rows = []
        for row in result:
            m = dict(row._mapping)
            rows.append(
                {
                    "id": str(m["id"]),
                    "document_id": str(m["document_id"]),
                    "title": m["title"],
                    "content": m["content"],
                    "created_at": m["created_at"],
                }
            )
        return rows


async def pg_get_by_share_token(token: str) -> dict[str, Any] | None:
    if not _use_db():
        return None
    factory = get_session_factory()
    assert factory is not None
    async with factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, user_id, title, content, format, tags, is_shared, share_token,
                       is_favorite, folder, created_at, updated_at
                FROM documents
                WHERE share_token = :token AND is_shared = true
                """
            ),
            {"token": token},
        )
        row = result.first()
        return _row_to_doc(row) if row else None
