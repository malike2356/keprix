"""Bridge episodic + temporal memory into the workspace brain graph.

The brain graph is edge-first: nodes without edges never appear. Chat activation
historically created edges; hub saves and Temporal KG lived outside that plane.
This module seeds overlay edges at read time and can persist links on write.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.brain.graph_types import GraphEdge
from keprix.data_architecture.graph_edges import add_graph_edge

MEMORY_HUB_SESSION_ID = "memory-hub"
MEMORY_HUB_RELATION = "episodic_store"
TEMPORAL_RELATION_PREFIX = "kg:"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def build_memory_overlay_edges(
    workspace_id: str,
    owner_user_ids: list[str],
    *,
    limit_memories: int = 200,
    limit_entities: int = 150,
) -> list[GraphEdge]:
    """Return synthetic edges so hub memories and Temporal KG show on /brain/graph."""
    edges: list[GraphEdge] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def _push(edge: GraphEdge) -> None:
        key = (edge.source_kind, edge.source_id, edge.target_kind, edge.target_id, edge.relation)
        if key in seen:
            return
        seen.add(key)
        edges.append(edge)

    owners = [uid for uid in dict.fromkeys(owner_user_ids) if uid]
    if not owners:
        owners = [workspace_id or "default"]

    try:
        from keprix.memory.episodic.store import create_episodic_store

        store = create_episodic_store()
        for user_id in owners:
            memories = await store.list_all(user_id)
            for memory in memories[:limit_memories]:
                _push(
                    GraphEdge(
                        edge_id=f"seed-mem-{memory.id}",
                        source_kind="memory",
                        source_id=memory.id,
                        target_kind="session",
                        target_id=MEMORY_HUB_SESSION_ID,
                        relation=MEMORY_HUB_RELATION,
                        weight=1.0,
                        created_at=_parse_dt(getattr(memory, "created_at", None)) or _utcnow(),
                        metadata={
                            "source": "episodic_overlay",
                            "owner_user_id": user_id,
                            "workspace_id": workspace_id,
                        },
                    )
                )
    except Exception:
        pass

    try:
        from keprix.memory.temporal_kg import TemporalKnowledgeGraph

        kg = TemporalKnowledgeGraph()
        for user_id in owners:
            graph = await kg.search(user_id, "", limit=limit_entities)
            entities = graph.get("entities") or []
            relations = graph.get("relations") or []
            # Anchor entities to the memory hub so they appear even without relations.
            for entity in entities[:limit_entities]:
                eid = str(entity.get("id") or "")
                if not eid:
                    continue
                _push(
                    GraphEdge(
                        edge_id=f"seed-ent-hub-{eid}",
                        source_kind="entity",
                        source_id=eid,
                        target_kind="session",
                        target_id=MEMORY_HUB_SESSION_ID,
                        relation="temporal_entity",
                        weight=float(entity.get("confidence") or 0.7),
                        created_at=_parse_dt(entity.get("valid_from")) or _utcnow(),
                        metadata={
                            "source": "temporal_overlay",
                            "owner_user_id": user_id,
                            "entity_type": entity.get("entity_type"),
                        },
                    )
                )
            for rel in relations[:limit_entities]:
                sid = str(rel.get("subject_id") or "")
                oid = str(rel.get("object_id") or "")
                predicate = str(rel.get("predicate") or "related_to")
                if not sid or not oid:
                    continue
                _push(
                    GraphEdge(
                        edge_id=f"seed-rel-{rel.get('id') or sid}-{oid}",
                        source_kind="entity",
                        source_id=sid,
                        target_kind="entity",
                        target_id=oid,
                        relation=f"{TEMPORAL_RELATION_PREFIX}{predicate}",
                        weight=float(rel.get("confidence") or 0.7),
                        created_at=_parse_dt(rel.get("valid_from")) or _utcnow(),
                        metadata={
                            "source": "temporal_overlay",
                            "owner_user_id": user_id,
                            "predicate": predicate,
                            "evidence_memory_ids": rel.get("evidence_memory_ids") or [],
                        },
                    )
                )
            # Link memories that already cite evidence on a relation.
            for rel in relations:
                for mid in rel.get("evidence_memory_ids") or []:
                    mid_s = str(mid)
                    if not mid_s:
                        continue
                    _push(
                        GraphEdge(
                            edge_id=f"seed-ev-{rel.get('id')}-{mid_s}",
                            source_kind="memory",
                            source_id=mid_s,
                            target_kind="entity",
                            target_id=str(rel.get("subject_id")),
                            relation="evidence_for",
                            weight=0.8,
                            created_at=_utcnow(),
                            metadata={"source": "temporal_overlay", "owner_user_id": user_id},
                        )
                    )
    except Exception:
        pass

    return edges


def emit_memory_saved_edge(
    *,
    workspace_id: str,
    memory_id: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a graph edge when a hub memory is saved."""
    try:
        add_graph_edge(
            workspace_id=workspace_id or "default",
            source_kind="memory",
            source_id=memory_id,
            target_kind="session",
            target_id=session_id or MEMORY_HUB_SESSION_ID,
            relation="memory_saved",
            metadata={"source": "hub_save", **(metadata or {})},
        )
    except Exception:
        pass


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
