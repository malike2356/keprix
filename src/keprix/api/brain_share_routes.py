"""Brain graph share link API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.brain.graph_query import BrainGraphQuery
from keprix.brain.share_links import SCOPE_KINDS, ShareScope, share_link_store

router = APIRouter(prefix="/api/brain/share", tags=["brain-share"])
public_router = APIRouter(prefix="/api/brain/share", tags=["brain-share-public"])


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    requested = workspace_id or str(user.get("workspace_id") or "default")
    allowed = user.get("workspace_id")
    if allowed and requested != allowed and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


class CreateShareBody(BaseModel):
    expires_in_days: int | None = Field(default=7, ge=1, le=365)
    scope: ShareScope = "all"
    password: str | None = None


def _public_base_url(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin
    host = request.headers.get("host", "localhost")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}"


def _resolve_share(share_id: str, password: str | None = None) -> Any:
    link = share_link_store.get(share_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Share link not found")
    if share_link_store.is_expired(link):
        raise HTTPException(status_code=410, detail="This share link has expired")
    if not share_link_store.verify_password(link, password):
        raise HTTPException(status_code=401, detail="Password required")
    return link


async def _shared_graph(link, *, include_content: bool = False) -> dict[str, Any]:
    kinds = SCOPE_KINDS.get(link.scope)
    graph = await BrainGraphQuery().load(link.workspace_id, kinds=list(kinds) if kinds else None, limit_nodes=10_000)
    share_link_store.record_access(link.share_id)
    return {
        "title": "Shared brain",
        "scope": link.scope,
        "nodes": [node.to_dict(include_content=include_content) for node in graph.nodes],
        "edges": [edge.to_dict() for edge in graph.edges],
        "total_nodes": graph.total_nodes,
        "total_edges": graph.total_edges,
        "truncated": graph.truncated,
        "password_protected": bool(link.password_hash),
    }


@router.get("")
async def list_share_links(
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    links = share_link_store.list_for_workspace(resolved)
    return {"links": [link.to_dict() for link in links]}


@router.post("")
async def create_share_link(
    body: CreateShareBody,
    request: Request,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    link = share_link_store.create(
        workspace_id=resolved,
        created_by=str(user.get("id") or "unknown"),
        scope=body.scope,
        expires_in_days=body.expires_in_days,
        password=body.password,
    )
    base_url = _public_base_url(request)
    return link.to_dict(include_url=True, base_url=base_url)


@router.delete("/{share_id}")
async def revoke_share_link(
    share_id: str,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, bool]:
    resolved = _workspace_id(workspace_id, user)
    revoked = share_link_store.revoke(share_id, resolved)
    if not revoked:
        raise HTTPException(status_code=404, detail="Share link not found")
    return {"revoked": True}


@router.get("/{share_id}/stats")
async def share_stats(
    share_id: str,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    link = share_link_store.get(share_id)
    if link is None or link.workspace_id != resolved:
        raise HTTPException(status_code=404, detail="Share link not found")
    return link.to_dict()


@public_router.get("/{share_id}/data")
async def shared_graph_data(
    share_id: str,
    password: str | None = Query(default=None),
) -> dict[str, Any]:
    link = _resolve_share(share_id, password)
    return await _shared_graph(link)


@public_router.get("/{share_id}/node/{kind}/{node_id}")
async def shared_graph_node(
    share_id: str,
    kind: str,
    node_id: str,
    password: str | None = Query(default=None),
) -> dict[str, Any]:
    link = _resolve_share(share_id, password)
    kinds = SCOPE_KINDS.get(link.scope)
    if kinds is not None and kind not in kinds:
        raise HTTPException(status_code=404, detail="Node not available in this share scope")
    query = BrainGraphQuery()
    node = await query.resolver.resolve(link.workspace_id, kind, node_id)
    if node is None:
        node = query.resolver.tombstone(kind, node_id)
    share_link_store.record_access(link.share_id)
    return node.to_dict(include_content=True)
