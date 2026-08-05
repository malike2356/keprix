"""Offline dreaming / REM consolidation job."""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store
from keprix.memory.rem_consolidation import score_episode
from keprix.memory.schema import resolve_database_url
from keprix.memory.temporal_kg import TemporalKnowledgeGraph

logger = logging.getLogger(__name__)

_ENTITY = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
_PREFER = re.compile(r"\b(?:prefer|likes?|hates?|always|never)\b", re.I)


class DreamingService:
    def __init__(
        self,
        store: EpisodicStore | None = None,
        kg: TemporalKnowledgeGraph | None = None,
        database_url: str | None = None,
    ) -> None:
        self.store = store or create_episodic_store(database_url)
        self.kg = kg or TemporalKnowledgeGraph(database_url)
        self.database_url = resolve_database_url(database_url)

    async def run(self, user_id: str) -> dict[str, Any]:
        memories = await self.store.list_all(user_id)
        promoted = 0
        archived = 0
        entities = 0
        relations = 0
        clusters: dict[str, list[Any]] = defaultdict(list)

        for memory in memories:
            meta = dict(memory.metadata or {})
            if meta.get("belief_state") in {"superseded", "archived"}:
                continue
            score = score_episode(
                role=str(meta.get("source_role") or "user"),
                content=memory.content,
                priority=1 if meta.get("pin") else 0,
                access_count=int(meta.get("access_count") or 0),
                created_at=memory.created_at,
            )
            key = _cluster_key(memory.content)
            clusters[key].append((score, memory))

            # Promote strong preferences/facts to semantic type.
            if score >= float(os.getenv("KEPRIX_DREAM_PROMOTE_THRESHOLD", "0.7")):
                mtype = "preference" if _PREFER.search(memory.content) else "semantic"
                await self.store.update(
                    user_id,
                    memory.id,
                    content=memory.content,
                    tags=list({*(memory.tags or []), "dreamed", mtype}),
                    extra={
                        "memory_type": mtype,
                        "confidence": max(float(meta.get("confidence") or 0.7), score),
                        "belief_state": "active",
                        "source": meta.get("source") or "dream",
                    },
                )
                promoted += 1

            # Extract crude entities / relations.
            names = [m.group(1) for m in _ENTITY.finditer(memory.content)][:4]
            for name in names:
                await self.kg.upsert_entity(user_id, name=name, entity_type="mention", confidence=score)
                entities += 1
            if len(names) >= 2:
                await self.kg.relate(
                    user_id,
                    subject_name=names[0],
                    predicate="mentioned_with",
                    object_name=names[1],
                    confidence=score,
                    evidence_memory_ids=[memory.id],
                )
                relations += 1

            # Archive fluff (never manual/import/pinned).
            if (
                score < float(os.getenv("KEPRIX_DREAM_ARCHIVE_THRESHOLD", "0.25"))
                and not meta.get("pin")
                and str(meta.get("source") or "") not in {"manual", "import", "hub"}
            ):
                await self.store.update(
                    user_id,
                    memory.id,
                    extra={"belief_state": "archived", "memory_type": meta.get("memory_type") or "episodic"},
                )
                archived += 1

        # Collapse near-duplicates within clusters: keep highest score.
        for _key, group in clusters.items():
            if len(group) < 2:
                continue
            group.sort(key=lambda item: item[0], reverse=True)
            winner = group[0][1]
            for score, memory in group[1:]:
                if _near_duplicate(winner.content, memory.content):
                    await self.store.update(
                        user_id,
                        memory.id,
                        extra={
                            "belief_state": "superseded",
                            "superseded_by": winner.id,
                        },
                    )
                    archived += 1

        detail = {
            "promoted": promoted,
            "archived": archived,
            "entities": entities,
            "relations": relations,
            "clusters": len(clusters),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._record_run(user_id, detail)
        logger.info("Dream run user=%s detail=%s", user_id, detail)
        return detail

    async def _record_run(self, user_id: str, detail: dict[str, Any]) -> None:
        if not self.database_url:
            return
        import asyncpg

        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO memory_dream_runs (user_id, promoted, archived, entities, relations, detail)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                user_id,
                detail["promoted"],
                detail["archived"],
                detail["entities"],
                detail["relations"],
                json.dumps(detail),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("dream run record skipped: %s", exc)
        finally:
            await conn.close()


def _cluster_key(content: str) -> str:
    tokens = re.findall(r"[a-zA-Z]{4,}", content.lower())
    return " ".join(tokens[:4]) or "misc"


def _near_duplicate(left: str, right: str) -> bool:
    a = set(re.findall(r"[a-zA-Z]{4,}", left.lower()))
    b = set(re.findall(r"[a-zA-Z]{4,}", right.lower()))
    if not a or not b:
        return False
    overlap = len(a & b) / max(1, len(a | b))
    return overlap >= 0.72
