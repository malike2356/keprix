"""Authenticated API routes for the workspace brain graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import get_current_user
from keprix.brain.graph_query import BrainGraphQuery
from keprix.brain.graph_types import NODE_KINDS
from keprix.data_architecture.graph_edges import delete_graph_edges

router = APIRouter(prefix="/api/brain/graph", tags=["brain-graph"])


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    requested = workspace_id or str(user.get("workspace_id") or "default")
    allowed = user.get("workspace_id")
    if allowed and requested != allowed and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


def _parse_kinds(kinds: str | None) -> list[str] | None:
    if not kinds:
        return None
    parsed = [item.strip() for item in kinds.split(",") if item.strip()]
    invalid = [item for item in parsed if item not in NODE_KINDS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"unknown node kinds: {', '.join(invalid)}")
    return parsed


@router.get("")
async def graph(
    workspace_id: str | None = None,
    kinds: str | None = None,
    session_id: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    include_archived: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    data = await BrainGraphQuery().load(
        _workspace_id(workspace_id, user),
        kinds=_parse_kinds(kinds),
        session_id=session_id,
        since=since,
        limit_nodes=limit,
        include_archived=include_archived,
        owner_user_id=str(user.get("id") or user.get("username") or ""),
    )
    return data.to_dict()


@router.get("/node/{kind}/{node_id}")
async def graph_node(
    kind: str,
    node_id: str,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if kind not in NODE_KINDS:
        raise HTTPException(status_code=404, detail="unknown node kind")
    query = BrainGraphQuery()
    owner = str(user.get("id") or user.get("username") or "")
    query.resolver.owner_user_ids = list(dict.fromkeys([owner, _workspace_id(workspace_id, user), "default"]))
    node = await query.resolver.resolve(_workspace_id(workspace_id, user), kind, node_id)
    if node is None:
        node = query.resolver.tombstone(kind, node_id)
    return node.to_dict(include_content=True)


@router.get("/neighbours/{kind}/{node_id}")
async def graph_neighbours(
    kind: str,
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if kind not in NODE_KINDS:
        raise HTTPException(status_code=404, detail="unknown node kind")
    data = await BrainGraphQuery().neighbours(
        _workspace_id(workspace_id, user),
        kind,
        node_id,
        depth=depth,
        owner_user_id=str(user.get("id") or user.get("username") or ""),
    )
    return data.to_dict()


@router.get("/search")
async def graph_search(
    q: str = Query(..., min_length=1),
    kinds: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    matches = await BrainGraphQuery().search(
        _workspace_id(workspace_id, user),
        q,
        kinds=_parse_kinds(kinds),
        limit=limit,
        owner_user_id=str(user.get("id") or user.get("username") or ""),
    )
    return {"matches": matches}


@router.get("/stats")
async def graph_stats(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, dict[str, int]]:
    return await BrainGraphQuery().stats(
        _workspace_id(workspace_id, user),
        owner_user_id=str(user.get("id") or user.get("username") or ""),
    )


@router.delete("/edges")
async def graph_edges_delete(
    workspace_id: str | None = None,
    source_kind: str | None = None,
    source_id: str | None = None,
    target_kind: str | None = None,
    target_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    removed = delete_graph_edges(
        workspace_id=_workspace_id(workspace_id, user),
        source_kind=source_kind,
        source_id=source_id,
        target_kind=target_kind,
        target_id=target_id,
    )
    return {"deleted": removed}
