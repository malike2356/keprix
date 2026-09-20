"""FastAPI routes for session trajectories."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.trajectory.service import get_trajectory_service
from keprix.trajectory.store import AppendOnlyViolation

router = APIRouter(prefix="/api/trajectories", tags=["trajectories"])


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    requested = workspace_id or str(user.get("workspace_id") or "default")
    allowed = user.get("workspace_id")
    if allowed and requested != allowed and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


class CreateTrajectoryBody(BaseModel):
    title: str | None = None
    session_id: str | None = None
    workspace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AppendEventBody(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    tool_name: str | None = None
    soft_wall_outcome: str | None = None
    error_text: str | None = None


class ForkBody(BaseModel):
    through_seq: int = Field(ge=0)
    title: str | None = None


class ReplayBody(BaseModel):
    from_seq: int = Field(default=1, ge=1)
    through_seq: int | None = Field(default=None, ge=1)
    mode: str = Field(default="recorded", pattern="^(recorded|live)$")


@router.get("")
async def list_trajectories(
    workspace_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    rows = svc.store.list_trajectories(workspace_id=ws, limit=limit, offset=offset)
    return {"trajectories": rows, "workspace_id": ws}


@router.post("")
async def create_trajectory(
    body: CreateTrajectoryBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(body.workspace_id, user)
    svc = get_trajectory_service()
    return svc.create(
        workspace_id=ws,
        session_id=body.session_id,
        title=body.title,
        metadata=body.metadata,
    )


@router.get("/search")
async def search_trajectory_events(
    workspace_id: str | None = None,
    trajectory_id: str | None = None,
    event_type: str | None = None,
    tool_name: str | None = None,
    soft_wall_outcome: str | None = None,
    error_query: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    events = svc.search(
        workspace_id=ws,
        trajectory_id=trajectory_id,
        event_type=event_type,
        tool_name=tool_name,
        soft_wall_outcome=soft_wall_outcome,
        error_query=error_query,
        limit=limit,
        offset=offset,
    )
    return {"events": events, "count": len(events)}


@router.get("/{trajectory_id}")
async def get_trajectory(
    trajectory_id: str,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    data = svc.get(trajectory_id)
    if data is None:
        raise HTTPException(status_code=404, detail="trajectory not found")
    if data.get("workspace_id") != ws and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return data


@router.post("/{trajectory_id}/events")
async def append_event(
    trajectory_id: str,
    body: AppendEventBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    meta = svc.store.get_trajectory(trajectory_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="trajectory not found")
    if meta.get("workspace_id") != ws and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    try:
        event = svc.append(
            trajectory_id,
            body.event_type,
            body.payload,
            tool_name=body.tool_name,
            soft_wall_outcome=body.soft_wall_outcome,
            error_text=body.error_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AppendOnlyViolation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return event.to_dict()


@router.post("/{trajectory_id}/fork")
async def fork_trajectory(
    trajectory_id: str,
    body: ForkBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    meta = svc.store.get_trajectory(trajectory_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="trajectory not found")
    if meta.get("workspace_id") != ws and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    try:
        return svc.fork(
            trajectory_id,
            through_seq=body.through_seq,
            title=body.title,
            workspace_id=ws,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{trajectory_id}/replay")
async def replay_trajectory(
    trajectory_id: str,
    body: ReplayBody,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace_id(workspace_id, user)
    svc = get_trajectory_service()
    meta = svc.store.get_trajectory(trajectory_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="trajectory not found")
    if meta.get("workspace_id") != ws and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    try:
        return svc.replay(
            trajectory_id,
            from_seq=body.from_seq,
            through_seq=body.through_seq,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
