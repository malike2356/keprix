"""Temporal knowledge graph for user entities and relations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from keprix.memory.schema import resolve_database_url

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TemporalKnowledgeGraph:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = resolve_database_url(database_url)
        self._memory: dict[str, dict[str, Any]] = {"entities": {}, "relations": {}}

    async def upsert_entity(
        self,
        user_id: str,
        *,
        name: str,
        entity_type: str = "thing",
        properties: dict[str, Any] | None = None,
        confidence: float = 0.7,
    ) -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Entity name required")
        if not self.database_url:
            key = f"{user_id}:{entity_type}:{name.lower()}"
            entity = {
                "id": self._memory["entities"].get(key, {}).get("id") or str(uuid4()),
                "user_id": user_id,
                "name": name,
                "entity_type": entity_type,
                "properties": properties or {},
                "confidence": confidence,
                "belief_state": "active",
                "valid_from": _now().isoformat(),
                "valid_to": None,
            }
            self._memory["entities"][key] = entity
            return entity
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO memory_entities (user_id, name, entity_type, properties, confidence, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, $5, NOW())
                ON CONFLICT (user_id, name, entity_type) DO UPDATE
                SET properties = memory_entities.properties || EXCLUDED.properties,
                    confidence = GREATEST(memory_entities.confidence, EXCLUDED.confidence),
                    belief_state = 'active',
                    valid_to = NULL,
                    updated_at = NOW()
                RETURNING *
                """,
                user_id,
                name,
                entity_type,
                json.dumps(properties or {}),
                confidence,
            )
            return _entity_row(row)
        finally:
            await conn.close()

    async def relate(
        self,
        user_id: str,
        *,
        subject_name: str,
        predicate: str,
        object_name: str,
        subject_type: str = "thing",
        object_type: str = "thing",
        confidence: float = 0.7,
        evidence_memory_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        subject = await self.upsert_entity(user_id, name=subject_name, entity_type=subject_type, confidence=confidence)
        obj = await self.upsert_entity(user_id, name=object_name, entity_type=object_type, confidence=confidence)
        if not self.database_url:
            rel_id = str(uuid4())
            rel = {
                "id": rel_id,
                "user_id": user_id,
                "subject_id": subject["id"],
                "predicate": predicate,
                "object_id": obj["id"],
                "confidence": confidence,
                "belief_state": "active",
                "valid_from": _now().isoformat(),
                "valid_to": None,
                "evidence_memory_ids": evidence_memory_ids or [],
                "subject_name": subject["name"],
                "object_name": obj["name"],
            }
            self._memory["relations"][rel_id] = rel
            return rel
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO memory_relations (
                    user_id, subject_id, predicate, object_id, confidence, evidence_memory_ids
                )
                VALUES ($1, $2::uuid, $3, $4::uuid, $5, $6::uuid[])
                ON CONFLICT (user_id, subject_id, predicate, object_id) DO UPDATE
                SET confidence = GREATEST(memory_relations.confidence, EXCLUDED.confidence),
                    belief_state = 'active',
                    valid_to = NULL,
                    evidence_memory_ids = (
                        SELECT ARRAY(SELECT DISTINCT x FROM unnest(
                            COALESCE(memory_relations.evidence_memory_ids, '{}') || EXCLUDED.evidence_memory_ids
                        ) AS t(x))
                    )
                RETURNING *
                """,
                user_id,
                subject["id"],
                predicate,
                obj["id"],
                confidence,
                evidence_memory_ids or [],
            )
            payload = dict(row)
            payload["subject_name"] = subject["name"]
            payload["object_name"] = obj["name"]
            return _relation_row(payload)
        finally:
            await conn.close()

    async def close_relation(self, user_id: str, relation_id: str) -> bool:
        if not self.database_url:
            rel = self._memory["relations"].get(relation_id)
            if not rel or rel["user_id"] != user_id:
                return False
            rel["belief_state"] = "superseded"
            rel["valid_to"] = _now().isoformat()
            return True
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            result = await conn.execute(
                """
                UPDATE memory_relations
                SET belief_state = 'superseded', valid_to = NOW()
                WHERE user_id = $1 AND id = $2::uuid
                """,
                user_id,
                relation_id,
            )
            return result.endswith("1")
        finally:
            await conn.close()

    async def search(self, user_id: str, query: str, *, limit: int = 20) -> dict[str, Any]:
        needle = query.strip().lower()
        if not self.database_url:
            entities = [
                e
                for e in self._memory["entities"].values()
                if e["user_id"] == user_id and (not needle or needle in e["name"].lower())
            ][:limit]
            relations = [
                r
                for r in self._memory["relations"].values()
                if r["user_id"] == user_id
                and r.get("belief_state") == "active"
                and (not needle or needle in r["predicate"].lower() or needle in (r.get("subject_name") or "").lower())
            ][:limit]
            return {"entities": entities, "relations": relations}
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            if needle:
                entities = await conn.fetch(
                    """
                    SELECT * FROM memory_entities
                    WHERE user_id = $1
                      AND belief_state = 'active'
                      AND (valid_to IS NULL OR valid_to > NOW())
                      AND (LOWER(name) LIKE $2 OR LOWER(entity_type) LIKE $2)
                    ORDER BY confidence DESC
                    LIMIT $3
                    """,
                    user_id,
                    f"%{needle}%",
                    limit,
                )
            else:
                entities = await conn.fetch(
                    """
                    SELECT * FROM memory_entities
                    WHERE user_id = $1
                      AND belief_state = 'active'
                      AND (valid_to IS NULL OR valid_to > NOW())
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                )
            relations = await conn.fetch(
                """
                SELECT r.*, s.name AS subject_name, o.name AS object_name
                FROM memory_relations r
                JOIN memory_entities s ON s.id = r.subject_id
                JOIN memory_entities o ON o.id = r.object_id
                WHERE r.user_id = $1
                  AND r.belief_state = 'active'
                  AND (r.valid_to IS NULL OR r.valid_to > NOW())
                  AND (
                    $2 = '' OR LOWER(r.predicate) LIKE $3
                    OR LOWER(s.name) LIKE $3 OR LOWER(o.name) LIKE $3
                  )
                ORDER BY r.confidence DESC
                LIMIT $4
                """,
                user_id,
                needle,
                f"%{needle}%",
                limit,
            )
            return {
                "entities": [_entity_row(r) for r in entities],
                "relations": [_relation_row(dict(r)) for r in relations],
            }
        finally:
            await conn.close()


def _entity_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    props = data.get("properties")
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except json.JSONDecodeError:
            props = {}
    return {
        "id": str(data["id"]),
        "user_id": data["user_id"],
        "name": data["name"],
        "entity_type": data.get("entity_type") or "thing",
        "properties": props or {},
        "confidence": float(data.get("confidence") or 0.7),
        "belief_state": data.get("belief_state") or "active",
        "valid_from": _iso(data.get("valid_from")),
        "valid_to": _iso(data.get("valid_to")),
    }


def _relation_row(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(data["id"]),
        "user_id": data["user_id"],
        "subject_id": str(data["subject_id"]),
        "object_id": str(data["object_id"]),
        "predicate": data["predicate"],
        "confidence": float(data.get("confidence") or 0.7),
        "belief_state": data.get("belief_state") or "active",
        "valid_from": _iso(data.get("valid_from")),
        "valid_to": _iso(data.get("valid_to")),
        "evidence_memory_ids": [str(x) for x in (data.get("evidence_memory_ids") or [])],
        "subject_name": data.get("subject_name"),
        "object_name": data.get("object_name"),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
