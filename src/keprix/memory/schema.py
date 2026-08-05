"""World-class memory schema bootstrap (PG)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_TYPES = (
    "episodic",
    "profile",
    "preference",
    "decision",
    "entity",
    "open_loop",
    "semantic",
    "self",
)

BELIEF_STATES = ("active", "disputed", "superseded", "archived", "rejected")
MODEL_SIDES = ("user", "self")
MODALITIES = ("text", "image_ocr", "document", "audio", "vault", "graphiti")


def resolve_database_url(explicit: str | None = None) -> str:
    """Normalize SQLAlchemy-style URLs for asyncpg (quote passwords with + / @)."""
    import re
    from urllib.parse import quote_plus

    url = (
        explicit
        or os.getenv("DATABASE_URL")
        or os.getenv("KEPRIX_DATABASE_URL")
        or ""
    ).strip()
    if not url:
        return ""
    match = re.match(
        r"^(?:postgresql\+asyncpg|postgres\+asyncpg|postgresql|postgres)://([^:]+):(.*)@([^:/]+)(?::(\d+))?/(.+)$",
        url,
    )
    if match:
        user, password, host, port, db = match.groups()
        port = port or "5432"
        db = db.split("?", 1)[0]
        return (
            f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{db}"
        )
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres+asyncpg://"):
        return "postgres://" + url[len("postgres+asyncpg://") :]
    return url


async def ensure_world_class_schema(database_url: str | None = None) -> dict[str, Any]:
    url = resolve_database_url(database_url)
    if not url:
        return {"ok": False, "reason": "no-database-url"}
    import asyncpg

    conn = await asyncpg.connect(url)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(
            """
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
            )
            """
        )
        for stmt in (
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS memory_type TEXT DEFAULT 'episodic'",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS confidence REAL DEFAULT 0.7",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS belief_state TEXT DEFAULT 'active'",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS access_count INT DEFAULT 0",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMPTZ",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS superseded_by UUID",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS pin BOOLEAN DEFAULT FALSE",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'user'",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS workspace_id TEXT",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS modality TEXT DEFAULT 'text'",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS model_side TEXT DEFAULT 'user'",
            "ALTER TABLE memories ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual'",
            """
            CREATE TABLE IF NOT EXISTS memory_entities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                entity_type TEXT DEFAULT 'thing',
                properties JSONB DEFAULT '{}',
                confidence REAL DEFAULT 0.7,
                belief_state TEXT DEFAULT 'active',
                valid_from TIMESTAMPTZ DEFAULT NOW(),
                valid_to TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (user_id, name, entity_type)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_relations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                subject_id UUID NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
                predicate TEXT NOT NULL,
                object_id UUID NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
                confidence REAL DEFAULT 0.7,
                belief_state TEXT DEFAULT 'active',
                valid_from TIMESTAMPTZ DEFAULT NOW(),
                valid_to TIMESTAMPTZ,
                evidence_memory_ids UUID[] DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (user_id, subject_id, predicate, object_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                left_memory_id UUID NOT NULL,
                right_memory_id UUID NOT NULL,
                status TEXT DEFAULT 'open',
                note TEXT DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                resolved_at TIMESTAMPTZ,
                resolution TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_dream_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                promoted INT DEFAULT 0,
                archived INT DEFAULT 0,
                entities INT DEFAULT 0,
                relations INT DEFAULT 0,
                detail JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories (user_id, memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_memories_user_belief ON memories (user_id, belief_state)",
            "CREATE INDEX IF NOT EXISTS idx_memory_entities_user ON memory_entities (user_id, name)",
            "CREATE INDEX IF NOT EXISTS idx_memory_relations_user ON memory_relations (user_id, predicate)",
            "CREATE INDEX IF NOT EXISTS idx_memory_conflicts_user ON memory_conflicts (user_id, status)",
        ):
            try:
                await conn.execute(stmt)
            except Exception as exc:  # noqa: BLE001
                logger.debug("memory schema stmt skipped: %s (%s)", stmt[:60], exc)
        return {"ok": True}
    finally:
        await conn.close()
