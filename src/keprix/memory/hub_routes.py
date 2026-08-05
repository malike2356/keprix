"""World-class memory hub API (recall, KG, belief, dreaming, continuity)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.memory.belief import BeliefRevisionService
from keprix.memory.continuity import constitution_status, continuity_report
from keprix.memory.dreaming import DreamingService
from keprix.memory.episodic.store import create_episodic_store
from keprix.memory.orchestrator import MemoryOrchestrator
from keprix.memory.schema import MEMORY_TYPES, ensure_world_class_schema
from keprix.memory.temporal_kg import TemporalKnowledgeGraph

router = APIRouter(prefix="/api/memory", tags=["memory-hub"])
_store = create_episodic_store()
_orchestrator = MemoryOrchestrator(store=_store)
_kg = TemporalKnowledgeGraph()
_belief = BeliefRevisionService(store=_store)
_dream = DreamingService(store=_store, kg=_kg)


def _uid(user: dict | None = None, request: Request | None = None, x_user_id: str | None = None) -> str:
    if user:
        return str(user.get("id") or user.get("username") or "default")
    if x_user_id:
        return x_user_id
    if request is not None:
        header_user = request.headers.get("X-User-Id")
        if header_user:
            return header_user
    return "default"


class SaveBody(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None
    memory_type: str = "semantic"
    pin: bool = False
    modality: str = "text"
    model_side: str = "user"
    source: str = "manual"
    confidence: float = 0.85
    scope: str = "user"
    workspace_id: str | None = None


class UpdateBody(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    memory_type: str | None = None
    pin: bool | None = None
    belief_state: str | None = None
    confidence: float | None = None
    model_side: str | None = None


class RecallBody(BaseModel):
    query: str = ""
    limit: int = 12
    token_budget: int = 900
    include_curated: bool = True
    include_rag: bool = True
    include_graph: bool = True
    include_self: bool = False


class EntityBody(BaseModel):
    name: str
    entity_type: str = "thing"
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.7


class RelationBody(BaseModel):
    subject_name: str
    predicate: str
    object_name: str
    subject_type: str = "thing"
    object_type: str = "thing"
    confidence: float = 0.7
    evidence_memory_ids: list[str] = Field(default_factory=list)


class ResolveConflictBody(BaseModel):
    winner_id: str
    loser_id: str
    note: str = ""


class MultimodalIngestBody(BaseModel):
    content: str
    title: str | None = None
    modality: str = "document"
    source: str = "multimodal"
    tags: list[str] = Field(default_factory=list)
    memory_type: str = "semantic"


class ImportBody(BaseModel):
    memories: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/hub/bootstrap")
async def bootstrap_memory(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await ensure_world_class_schema()


@router.get("/hub/overview")
async def memory_overview(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    memories = await _store.list_all(uid)
    continuity = await continuity_report(uid, store=_store)
    graph = await _kg.search(uid, "", limit=20)
    conflicts = await _belief.detect_conflicts(uid, limit=20)
    return {
        "memories": [m.to_dict() for m in memories],
        "types": MEMORY_TYPES,
        "continuity": continuity,
        "constitution": constitution_status(),
        "graph": graph,
        "conflicts": conflicts,
        "count": len(memories),
    }


@router.post("/hub/save")
async def hub_save(body: SaveBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "content is required")
    memory_type = body.memory_type if body.memory_type in MEMORY_TYPES else "semantic"
    memory_id = await _store.save(
        _uid(user),
        content,
        metadata={
            "tags": body.tags,
            "session_id": body.session_id,
            "memory_type": memory_type,
            "pin": body.pin,
            "modality": body.modality,
            "model_side": body.model_side,
            "source": body.source,
            "confidence": body.confidence,
            "scope": body.scope,
            "workspace_id": body.workspace_id,
            "belief_state": "active",
        },
    )
    try:
        from keprix.brain.memory_graph_sync import emit_memory_saved_edge

        ws = body.workspace_id or str(user.get("workspace_id") or "default")
        emit_memory_saved_edge(
            workspace_id=ws,
            memory_id=memory_id,
            session_id=body.session_id,
            metadata={"memory_type": memory_type, "source": body.source},
        )
    except Exception:
        pass
    return {"ok": True, "memory_id": memory_id}


@router.patch("/hub/{memory_id}")
async def hub_update(memory_id: str, body: UpdateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if body.memory_type is not None:
        extra["memory_type"] = body.memory_type
    if body.pin is not None:
        extra["pin"] = body.pin
    if body.belief_state is not None:
        extra["belief_state"] = body.belief_state
    if body.confidence is not None:
        extra["confidence"] = body.confidence
    if body.model_side is not None:
        extra["model_side"] = body.model_side
    content = body.content.strip() if isinstance(body.content, str) else None
    if content is not None and not content:
        raise HTTPException(400, "content cannot be empty")
    ok = await _store.update(_uid(user), memory_id, content=content, tags=body.tags, extra=extra or None)
    if not ok:
        raise HTTPException(404, "Memory not found")
    return {"ok": True}


@router.post("/hub/recall")
async def hub_recall(body: RecallBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await _orchestrator.recall(
        _uid(user),
        body.query,
        limit=body.limit,
        token_budget=body.token_budget,
        include_curated=body.include_curated,
        include_rag=body.include_rag,
        include_graph=body.include_graph,
        include_self=body.include_self,
        reinforce=True,
    )


@router.get("/hub/continuity")
async def hub_continuity(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await continuity_report(_uid(user), store=_store)


@router.get("/hub/constitution")
async def hub_constitution(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return constitution_status()


@router.get("/hub/conflicts")
async def hub_conflicts(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"conflicts": await _belief.detect_conflicts(_uid(user))}


@router.post("/hub/conflicts/resolve")
async def hub_resolve_conflict(body: ResolveConflictBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await _belief.resolve(_uid(user), winner_id=body.winner_id, loser_id=body.loser_id, note=body.note)


@router.post("/hub/dream")
async def hub_dream(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await _dream.run(_uid(user))


@router.get("/hub/graph")
async def hub_graph(q: str = Query(""), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await _kg.search(_uid(user), q, limit=50)


@router.post("/hub/graph/entity")
async def hub_entity(body: EntityBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    entity = await _kg.upsert_entity(
        _uid(user),
        name=body.name,
        entity_type=body.entity_type,
        properties=body.properties,
        confidence=body.confidence,
    )
    return {"entity": entity}


@router.post("/hub/graph/relation")
async def hub_relation(body: RelationBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    relation = await _kg.relate(
        _uid(user),
        subject_name=body.subject_name,
        predicate=body.predicate,
        object_name=body.object_name,
        subject_type=body.subject_type,
        object_type=body.object_type,
        confidence=body.confidence,
        evidence_memory_ids=body.evidence_memory_ids,
    )
    return {"relation": relation}


@router.post("/hub/multimodal-ingest")
async def hub_multimodal_ingest(body: MultimodalIngestBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "content required")
    title = (body.title or "").strip()
    text = f"# {title}\n\n{content}" if title else content
    memory_id = await _store.save(
        _uid(user),
        text,
        metadata={
            "tags": list({*body.tags, body.modality, "multimodal"}),
            "memory_type": body.memory_type if body.memory_type in MEMORY_TYPES else "semantic",
            "modality": body.modality,
            "source": body.source,
            "belief_state": "active",
            "confidence": 0.75,
            "model_side": "user",
        },
    )
    return {"ok": True, "memory_id": memory_id}


@router.get("/hub/export")
async def hub_export(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    return {
        "memories": await _store.export_all(uid),
        "graph": await _kg.search(uid, "", limit=200),
        "continuity": await continuity_report(uid, store=_store),
    }


@router.post("/hub/import")
async def hub_import(body: ImportBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    imported = 0
    for item in body.memories:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        meta = dict(item.get("metadata") or {})
        meta["tags"] = list(item.get("tags") or meta.get("tags") or [])
        meta["source"] = meta.get("source") or "import"
        await _store.save(uid, content, metadata=meta)
        imported += 1
    return {"ok": True, "imported": imported}


@router.post("/hub/dedup")
async def hub_dedup(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    # Use dream service clustering for near-duplicate collapse.
    detail = await _dream.run(_uid(user))
    return {"ok": True, "detail": detail}
