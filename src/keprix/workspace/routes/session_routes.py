"""Conversation session routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import SessionRename

router = APIRouter(prefix="/api/workspace/sessions", tags=["workspace-sessions"])


@router.get("")
async def list_sessions(
    user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows = workspace_repo.list_sessions(user, limit=limit, offset=offset)
    return {"items": rows, "limit": limit, "offset": offset}


@router.get("/{session_id}")
async def get_session(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.get_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.put("/{session_id}")
async def rename_session(
    session_id: str,
    body: SessionRename,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return workspace_repo.rename_session(user, session_id, body.title)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.delete("/{session_id}", status_code=200)
async def delete_session(session_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query("json", alias="format"),
    user: dict = Depends(get_current_user),
) -> Response:
    try:
        session = workspace_repo.get_session(user, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    title = session.get("title", "session")
    messages = session.get("messages") or []
    if format == "md":
        lines = [f"# {title}", ""]
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            lines.append(f"## {role}")
            lines.append(content)
            lines.append("")
        payload = "\n".join(lines)
        return Response(content=payload, media_type="text/markdown; charset=utf-8")
    if format == "txt":
        lines = [title, ""]
        for message in messages:
            lines.append(f"{message.get('role', 'user')}: {message.get('content', '')}")
        return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")
    return Response(content=json.dumps(session, default=str), media_type="application/json")
