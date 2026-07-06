"""Swappable kernel memory backends."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class MemoryRecord:
    id: str
    key: str
    content: str
    metadata: dict[str, Any]


class KernelMemoryBackend(ABC):
    name: str

    @abstractmethod
    async def remember(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        ...

    @abstractmethod
    async def recall(self, query: str, *, limit: int = 5) -> list[MemoryRecord]:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class InMemoryKernelMemory(KernelMemoryBackend):
    name = "in_memory"

    def __init__(self) -> None:
        self._rows: list[MemoryRecord] = []

    async def remember(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        record = MemoryRecord(id=str(uuid4()), key=key, content=content, metadata=metadata or {})
        self._rows.append(record)
        return record.id

    async def recall(self, query: str, *, limit: int = 5) -> list[MemoryRecord]:
        lowered = query.lower()
        matches = [row for row in self._rows if lowered in row.content.lower() or lowered in row.key.lower()]
        return matches[:limit]

    async def clear(self) -> None:
        self._rows.clear()


class SqliteKernelMemory(KernelMemoryBackend):
    name = "sqlite"

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kernel_memory (id TEXT PRIMARY KEY, key TEXT, content TEXT, metadata TEXT)"
            )

    async def remember(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        record_id = str(uuid4())
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO kernel_memory (id, key, content, metadata) VALUES (?, ?, ?, ?)",
                (record_id, key, content, json.dumps(metadata or {})),
            )
        return record_id

    async def recall(self, query: str, *, limit: int = 5) -> list[MemoryRecord]:
        pattern = f"%{query}%"
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, key, content, metadata FROM kernel_memory WHERE key LIKE ? OR content LIKE ? LIMIT ?",
                (pattern, pattern, limit),
            ).fetchall()
        return [
            MemoryRecord(id=row[0], key=row[1], content=row[2], metadata=json.loads(row[3] or "{}"))
            for row in rows
        ]

    async def clear(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM kernel_memory")


class FileIndexKernelMemory(KernelMemoryBackend):
    name = "file_index"

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._index_path = self._root / "index.json"
        self._rows: list[dict[str, Any]] = []
        if self._index_path.exists():
            self._rows = json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._index_path.write_text(json.dumps(self._rows, indent=2), encoding="utf-8")

    async def remember(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        record_id = str(uuid4())
        self._rows.append({"id": record_id, "key": key, "content": content, "metadata": metadata or {}})
        self._save()
        return record_id

    async def recall(self, query: str, *, limit: int = 5) -> list[MemoryRecord]:
        lowered = query.lower()
        matches = [
            MemoryRecord(
                id=row["id"],
                key=row["key"],
                content=row["content"],
                metadata=row.get("metadata") or {},
            )
            for row in self._rows
            if lowered in row["content"].lower() or lowered in row["key"].lower()
        ]
        return matches[:limit]

    async def clear(self) -> None:
        self._rows.clear()
        self._save()


class PgVectorKernelMemory(KernelMemoryBackend):
    name = "pgvector"

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn
        self._fallback = InMemoryKernelMemory()

    async def remember(self, key: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        if not self._dsn:
            return await self._fallback.remember(key, content, metadata)
        raise NotImplementedError("pgvector backend requires configured Postgres DSN")

    async def recall(self, query: str, *, limit: int = 5) -> list[MemoryRecord]:
        if not self._dsn:
            return await self._fallback.recall(query, limit=limit)
        raise NotImplementedError("pgvector backend requires configured Postgres DSN")

    async def clear(self) -> None:
        if not self._dsn:
            await self._fallback.clear()
            return
        raise NotImplementedError("pgvector backend requires configured Postgres DSN")


_memory_backend: KernelMemoryBackend | None = None


def get_memory_backend() -> KernelMemoryBackend:
    global _memory_backend
    if _memory_backend is None:
        _memory_backend = InMemoryKernelMemory()
    return _memory_backend


def set_memory_backend(backend: KernelMemoryBackend) -> None:
    global _memory_backend
    _memory_backend = backend
