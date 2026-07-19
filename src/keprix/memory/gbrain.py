"""Persistent memory store with context queries (gstack-compatible)."""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_DEFAULT_TYPES = frozenset(
    {"session_summary", "decision", "knowledge", "retro", "review", "incident"}
)


class GBrain:
    """Persistent memory store. Saves and retrieves context by project, persona, and type.

    Storage: SQLite database (default ~/.keprix/gbrain.db).
    """

    def __init__(self, db_path: str = "~/.keprix/gbrain.db"):
        self.db_path = db_path
        if db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            path = Path(os.path.expanduser(db_path))
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                persona TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_persona ON memories(persona)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)"
        )
        self._conn.commit()

    def save(self, project: str, persona: str, type: str, content: str) -> int:
        """Save a memory entry. Returns row id."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """
            INSERT INTO memories (project, persona, type, content, embedding, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
            """,
            (project, persona, type, content, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def query(self, project: str, persona: str, filters: dict | None = None) -> str:
        """Execute context queries. Returns formatted markdown for prompt injection."""
        filters = filters or {}
        mem_type = filters.get("type")
        sort = filters.get("sort", "updated_at_desc")
        limit = int(filters.get("limit", 5))
        include_old = bool(filters.get("include_old", False))
        context_query = filters.get("context_query") or filters.get("q")

        where = ["project = ?"]
        params: list[Any] = [project]

        if persona:
            where.append("persona = ?")
            params.append(persona)

        if mem_type:
            where.append("type = ?")
            params.append(mem_type)

        if not include_old:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            where.append("updated_at >= ?")
            params.append(cutoff)

        order = {
            "updated_at_desc": "updated_at DESC",
            "created_at_desc": "created_at DESC",
            "relevance": "updated_at DESC",
        }.get(sort, "updated_at DESC")

        sql = (
            f"SELECT type, content, persona, updated_at FROM memories "
            f"WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?"
        )
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()

        if context_query and rows:
            q_lower = str(context_query).lower()
            scored = []
            for row in rows:
                text = (row["content"] or "").lower()
                score = sum(1 for tok in re.findall(r"[a-z0-9]+", q_lower) if tok in text)
                scored.append((score, row))
            scored.sort(key=lambda x: (-x[0], x[1]["updated_at"]), reverse=False)
            scored.sort(key=lambda x: -x[0])
            rows = [r for _, r in scored]

        if not rows:
            return f"## gbrain ({project}/{persona or '*'})\n\n(no matching memories)"

        lines = [f"## gbrain ({project}/{persona or '*'})", ""]
        for row in rows:
            lines.append(f"- **{row['type']}** ({row['updated_at'][:10]}): {row['content']}")
        return "\n".join(lines)

    def search(self, project: str, query: str, limit: int = 5) -> list[dict]:
        """Full-text search across all entries for a project."""
        like = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT id, project, persona, type, content, created_at, updated_at
            FROM memories
            WHERE project = ? AND content LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (project, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent(self, project: str, persona: str, days: int = 7) -> str:
        """Get recent entries from last N days, formatted for context injection."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            """
            SELECT type, content, updated_at FROM memories
            WHERE project = ? AND persona = ? AND updated_at >= ?
            ORDER BY updated_at DESC
            LIMIT 20
            """,
            (project, persona, cutoff),
        ).fetchall()
        if not rows:
            return f"## Recent ({days}d)\n\n(no recent memories)"
        lines = [f"## Recent ({days}d) for {persona}", ""]
        for row in rows:
            lines.append(f"- **{row['type']}**: {row['content']}")
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()


# Backward-compatible alias used by older stubs
gbrain = GBrain
