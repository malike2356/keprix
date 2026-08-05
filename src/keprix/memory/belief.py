"""Belief revision for episodic memories."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store
from keprix.memory.schema import resolve_database_url

logger = logging.getLogger(__name__)

_CONTRAST = re.compile(
    r"\b(now|actually|instead|no longer|changed|prefer|preference|is|am|live|work)\b",
    re.I,
)


class BeliefRevisionService:
    def __init__(self, store: EpisodicStore | None = None, database_url: str | None = None) -> None:
        self.store = store or create_episodic_store(database_url)
        self.database_url = resolve_database_url(database_url)

    async def detect_conflicts(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        memories = await self.store.list_all(user_id)
        conflicts: list[dict[str, Any]] = []
        keyed: dict[str, list[Any]] = {}
        for memory in memories:
            if (memory.metadata or {}).get("belief_state") == "superseded":
                continue
            key = _topic_key(memory.content)
            keyed.setdefault(key, []).append(memory)
        for key, group in keyed.items():
            if len(group) < 2 or key == "general":
                continue
            left, right = group[0], group[1]
            if _looks_conflicting(left.content, right.content):
                conflicts.append(
                    {
                        "id": f"soft:{left.id}:{right.id}",
                        "left_memory_id": left.id,
                        "right_memory_id": right.id,
                        "left_content": left.content,
                        "right_content": right.content,
                        "status": "open",
                        "topic": key,
                    }
                )
            if len(conflicts) >= limit:
                break
        if self.database_url:
            await self._persist_open(user_id, conflicts)
            return await self._list_open(user_id, limit=limit)
        return conflicts

    async def resolve(
        self,
        user_id: str,
        *,
        winner_id: str,
        loser_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        # Supersede loser; reinforce winner.
        await self.store.update(
            user_id,
            loser_id,
            content=None,
            tags=None,
            extra={
                "belief_state": "superseded",
                "superseded_by": winner_id,
            },
        )
        winner = None
        for memory in await self.store.list_all(user_id):
            if memory.id == winner_id:
                winner = memory
                break
        if winner:
            meta = dict(winner.metadata or {})
            meta["belief_state"] = "active"
            meta["confidence"] = min(1.0, float(meta.get("confidence") or 0.7) + 0.1)
            await self.store.update(user_id, winner_id, content=winner.content, tags=winner.tags, extra=meta)
        if self.database_url:
            import asyncpg

            conn = await asyncpg.connect(self.database_url)
            try:
                await conn.execute(
                    """
                    UPDATE memory_conflicts
                    SET status = 'resolved', resolved_at = NOW(), resolution = $4, note = $5
                    WHERE user_id = $1
                      AND ((left_memory_id = $2::uuid AND right_memory_id = $3::uuid)
                        OR (left_memory_id = $3::uuid AND right_memory_id = $2::uuid))
                    """,
                    user_id,
                    winner_id,
                    loser_id,
                    f"keep:{winner_id}",
                    note,
                )
            finally:
                await conn.close()
        return {"ok": True, "winner_id": winner_id, "loser_id": loser_id}

    async def _persist_open(self, user_id: str, conflicts: list[dict[str, Any]]) -> None:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            for item in conflicts:
                await conn.execute(
                    """
                    INSERT INTO memory_conflicts (user_id, left_memory_id, right_memory_id, status, note)
                    SELECT $1, $2::uuid, $3::uuid, 'open', $4
                    WHERE NOT EXISTS (
                        SELECT 1 FROM memory_conflicts
                        WHERE user_id = $1 AND status = 'open'
                          AND (
                            (left_memory_id = $2::uuid AND right_memory_id = $3::uuid)
                            OR (left_memory_id = $3::uuid AND right_memory_id = $2::uuid)
                          )
                    )
                    """,
                    user_id,
                    item["left_memory_id"],
                    item["right_memory_id"],
                    item.get("topic") or "",
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("persist conflicts skipped: %s", exc)
        finally:
            await conn.close()

    async def _list_open(self, user_id: str, *, limit: int) -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                """
                SELECT c.*, l.content AS left_content, r.content AS right_content
                FROM memory_conflicts c
                LEFT JOIN memories l ON l.id = c.left_memory_id
                LEFT JOIN memories r ON r.id = c.right_memory_id
                WHERE c.user_id = $1 AND c.status = 'open'
                ORDER BY c.created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
            return [
                {
                    "id": str(row["id"]),
                    "left_memory_id": str(row["left_memory_id"]),
                    "right_memory_id": str(row["right_memory_id"]),
                    "left_content": row["left_content"] or "",
                    "right_content": row["right_content"] or "",
                    "status": row["status"],
                    "note": row["note"] or "",
                }
                for row in rows
            ]
        finally:
            await conn.close()


def _topic_key(content: str) -> str:
    lower = content.lower()
    for topic in ("timezone", "name", "prefer", "live", "work", "deadline", "email", "phone"):
        if topic in lower:
            return topic
    tokens = re.findall(r"[a-zA-Z]{4,}", lower)
    return tokens[0] if tokens else "general"


def _looks_conflicting(left: str, right: str) -> bool:
    if left.strip().lower() == right.strip().lower():
        return False
    return bool(_CONTRAST.search(left) or _CONTRAST.search(right))
