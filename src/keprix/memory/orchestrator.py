"""Unified memory recall orchestrator across stores."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store
from keprix.memory.rag.retriever import RagRetriever
from keprix.memory.temporal_kg import TemporalKnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class RecallHit:
    id: str
    content: str
    source: str
    score: float
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _keprix_home() -> Path:
    raw = os.environ.get("KEPRIX_HOME") or os.environ.get("KEPRIX_DATA_DIR")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".keprix"


def _read_curated(name: str) -> str:
    home = _keprix_home()
    for path in (home / "memories" / name, home / name):
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return ""


def _budget_chars(token_budget: int) -> int:
    # Rough chars ~= tokens * 4
    return max(400, token_budget * 4)


class MemoryOrchestrator:
    def __init__(
        self,
        store: EpisodicStore | None = None,
        rag: RagRetriever | None = None,
        kg: TemporalKnowledgeGraph | None = None,
    ) -> None:
        self.store = store or create_episodic_store()
        self.rag = rag or RagRetriever()
        self.kg = kg or TemporalKnowledgeGraph()

    async def recall(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 12,
        token_budget: int = 900,
        include_curated: bool = True,
        include_rag: bool = True,
        include_graph: bool = True,
        include_self: bool = False,
        reinforce: bool = True,
    ) -> dict[str, Any]:
        query = (query or "").strip()
        hits: list[RecallHit] = []

        # Episodic / semantic vectors
        if query:
            try:
                episodic = await self.store.search(user_id, query, limit=limit)
            except Exception as exc:  # noqa: BLE001
                logger.debug("episodic recall failed: %s", exc)
                episodic = []
        else:
            episodic = (await self.store.list_all(user_id))[:limit]

        for memory in episodic:
            meta = dict(memory.metadata or {})
            if meta.get("belief_state") in {"superseded", "archived", "rejected"}:
                continue
            if meta.get("model_side") == "self" and not include_self:
                continue
            score = float(memory.score if memory.score is not None else 0.5)
            if meta.get("pin"):
                score += 0.15
            score += min(0.12, 0.02 * int(meta.get("access_count") or 0))
            score *= float(meta.get("confidence") or 0.7)
            hits.append(
                RecallHit(
                    id=memory.id,
                    content=memory.content,
                    source=str(meta.get("source") or "episodic"),
                    score=score,
                    provenance={
                        "kind": "episodic",
                        "memory_type": meta.get("memory_type") or "episodic",
                        "belief_state": meta.get("belief_state") or "active",
                        "tags": memory.tags,
                        "modality": meta.get("modality") or "text",
                        "session_id": memory.session_id,
                    },
                )
            )
            if reinforce:
                try:
                    await self.store.reinforce(user_id, memory.id)
                except Exception:
                    pass

        if include_curated:
            for label, filename, side in (
                ("USER.md", "USER.md", "user"),
                ("MEMORY.md", "MEMORY.md", "user"),
            ):
                text = _read_curated(filename)
                if not text.strip():
                    continue
                score = _text_overlap_score(query, text) if query else 0.35
                if score > 0.05 or not query:
                    hits.append(
                        RecallHit(
                            id=f"curated:{filename}",
                            content=text.strip()[:2000],
                            source="curated",
                            score=0.55 + score,
                            provenance={"kind": "curated", "file": label, "model_side": side},
                        )
                    )

        if include_rag and query:
            try:
                rag_hits = await self.rag.hybrid_search(user_id=user_id, query=query, limit=min(6, limit))
            except Exception as exc:  # noqa: BLE001
                logger.debug("rag recall failed: %s", exc)
                rag_hits = []
            for item in rag_hits or []:
                if isinstance(item, dict):
                    content = str(item.get("content") or "")
                    score = float(item.get("score") or item.get("combined_score") or 0.4)
                    hits.append(
                        RecallHit(
                            id=str(item.get("id") or item.get("source_id") or content[:24]),
                            content=content,
                            source="rag",
                            score=score,
                            provenance={
                                "kind": "rag",
                                "source_type": item.get("source_type") or item.get("source"),
                                "source_id": item.get("source_id"),
                            },
                        )
                    )

        if include_graph:
            try:
                graph = await self.kg.search(user_id, query, limit=8)
            except Exception as exc:  # noqa: BLE001
                logger.debug("kg recall failed: %s", exc)
                graph = {"entities": [], "relations": []}
            for entity in graph.get("entities") or []:
                hits.append(
                    RecallHit(
                        id=f"entity:{entity['id']}",
                        content=f"Entity {entity['name']} ({entity.get('entity_type')})",
                        source="temporal_kg",
                        score=0.4 + float(entity.get("confidence") or 0.5) * 0.3,
                        provenance={"kind": "entity", **entity},
                    )
                )
            for rel in graph.get("relations") or []:
                hits.append(
                    RecallHit(
                        id=f"rel:{rel['id']}",
                        content=f"{rel.get('subject_name')} -[{rel['predicate']}]-> {rel.get('object_name')}",
                        source="temporal_kg",
                        score=0.42 + float(rel.get("confidence") or 0.5) * 0.3,
                        provenance={"kind": "relation", **rel},
                    )
                )

        # Optional Graphiti soft note when configured but not queried deep.
        if os.getenv("GRAPHITI_MCP_URL", "").strip():
            hits.append(
                RecallHit(
                    id="graphiti:available",
                    content="Graphiti MCP is configured; use graphiti_query for temporal graph look-ups.",
                    source="graphiti",
                    score=0.2,
                    provenance={"kind": "graphiti", "status": "configured"},
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        selected: list[RecallHit] = []
        used = 0
        budget = _budget_chars(token_budget)
        for hit in hits:
            piece = hit.content.strip()
            if not piece:
                continue
            cost = len(piece) + 32
            if selected and used + cost > budget:
                break
            selected.append(hit)
            used += cost
            if len(selected) >= limit:
                break

        block = format_memory_context(selected)
        return {
            "query": query,
            "hits": [h.to_dict() for h in selected],
            "context": block,
            "token_budget": token_budget,
            "approx_chars": used,
            "count": len(selected),
        }


def format_memory_context(hits: list[RecallHit]) -> str:
    if not hits:
        return ""
    lines = ["Recalled memory (use silently unless the user asks):"]
    for hit in hits:
        prov = hit.provenance.get("kind") or hit.source
        lines.append(f"- [{prov} | score={hit.score:.2f}] {hit.content}")
    return "\n".join(lines)


def _text_overlap_score(query: str, text: str) -> float:
    q = set(re.findall(r"[a-zA-Z]{3,}", query.lower()))
    t = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
    if not q or not t:
        return 0.0
    return len(q & t) / max(1, len(q))
