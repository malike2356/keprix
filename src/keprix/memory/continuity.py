"""Continuity scoring and memory constitution status."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store
from keprix.memory.temporal_kg import TemporalKnowledgeGraph


def _keprix_home() -> Path:
    raw = os.environ.get("KEPRIX_HOME") or os.environ.get("KEPRIX_DATA_DIR")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".keprix"


async def continuity_report(user_id: str, store: EpisodicStore | None = None) -> dict[str, Any]:
    store = store or create_episodic_store()
    memories = await store.list_all(user_id)
    now = datetime.now(timezone.utc)
    types: dict[str, int] = {}
    stale = 0
    disputed = 0
    pinned = 0
    for memory in memories:
        meta = memory.metadata or {}
        mtype = str(meta.get("memory_type") or "episodic")
        types[mtype] = types.get(mtype, 0) + 1
        if meta.get("belief_state") == "disputed":
            disputed += 1
        if meta.get("pin"):
            pinned += 1
        created = memory.created_at
        if created is not None:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (now - created).total_seconds() / 86400
            if age_days > 45 and int(meta.get("access_count") or 0) == 0:
                stale += 1

    home = _keprix_home()
    curated_memory = (home / "memories" / "MEMORY.md").is_file() or (home / "MEMORY.md").is_file()
    curated_user = (home / "memories" / "USER.md").is_file() or (home / "USER.md").is_file()

    kg = TemporalKnowledgeGraph()
    graph = await kg.search(user_id, "", limit=5)
    entity_count = len(graph.get("entities") or [])

    completeness = 0.0
    completeness += 0.25 if types.get("profile") or curated_user else 0.0
    completeness += 0.2 if types.get("preference") else 0.0
    completeness += 0.15 if types.get("decision") or types.get("semantic") else 0.0
    completeness += 0.15 if curated_memory else 0.0
    completeness += 0.15 if entity_count else 0.0
    completeness += 0.1 if pinned else 0.0
    completeness = round(min(1.0, completeness), 3)

    contradiction_rate = round(disputed / max(1, len(memories)), 3)
    staleness = round(stale / max(1, len(memories)), 3)
    score = round(max(0.0, completeness - 0.4 * contradiction_rate - 0.3 * staleness), 3)

    return {
        "score": score,
        "completeness": completeness,
        "staleness": staleness,
        "contradiction_rate": contradiction_rate,
        "counts": {
            "memories": len(memories),
            "by_type": types,
            "pinned": pinned,
            "disputed": disputed,
            "stale": stale,
            "entities": entity_count,
            "curated_memory": curated_memory,
            "curated_user": curated_user,
        },
    }


def constitution_status() -> dict[str, Any]:
    """Expose Memory Constitution (no invented 'I remembered' without a write)."""
    gate_enabled = os.getenv("KEPRIX_MEMORY_EDIT_GATE", "true").lower() in {"1", "true", "yes", "on"}
    rem_enabled = os.getenv("KEPRIX_REM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    memory_enabled = os.getenv("KEPRIX_MEMORY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    return {
        "title": "Memory Constitution",
        "rules": [
            "Agents must not claim memory writes without a successful memory tool or store write.",
            "Human edits and deletes win over automatic REM promotion.",
            "Superseded beliefs stay out of default recall.",
            "User-model and self-model memories stay labeled and separated.",
            "Cross-user recall is forbidden.",
        ],
        "gates": {
            "memory_edit_gate": gate_enabled,
            "rem_enabled": rem_enabled,
            "memory_enabled": memory_enabled,
            "graphiti_url_configured": bool(os.getenv("GRAPHITI_MCP_URL", "").strip()),
        },
    }
