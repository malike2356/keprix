"""Design live preview studio API routes."""

from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.design.preview_server import (
    build_design_skill_message,
    design_preview_enabled,
    render_session_html,
    resolve_preview_entry,
    resolve_session_file,
    session_mtime,
)
from keprix.design.preview_session_store import PreviewSessionStore

router = APIRouter(prefix="/api/design/preview", tags=["design"])


class OpenPreviewBody(BaseModel):
    path: str | None = None
    artifact_id: str | None = None
    entry: str | None = "index.html"


class SelectionBody(BaseModel):
    selector: str = Field(..., min_length=1)
    html_snippet: str = Field(..., min_length=1)
    meta: dict[str, Any] = Field(default_factory=dict)


def _guard_enabled() -> None:
    if not design_preview_enabled():
        raise HTTPException(status_code=403, detail="Design preview is disabled")


def _load_session(session_id: str):
    session = PreviewSessionStore().get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Preview session not found")
    return session


@router.post("/open")
async def open_preview(body: OpenPreviewBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    root, entry_path = resolve_preview_entry(body.path, body.artifact_id, body.entry)
    session = PreviewSessionStore().create(
        root_path=str(root),
        artifact_id=body.artifact_id,
        entry_file=str(entry_path.relative_to(root)),
    )
    return {
        "session": session.to_dict(),
        "preview_url": f"/api/design/preview/{session.session_id}/render",
    }


@router.get("")
async def list_previews(limit: int = 20, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return {"sessions": [session.to_dict() for session in PreviewSessionStore().list(limit=limit)]}


@router.get("/{session_id}")
async def get_preview(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return {"session": _load_session(session_id).to_dict()}


@router.get("/{session_id}/url")
async def preview_url(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    _ = user
    _guard_enabled()
    _load_session(session_id)
    return {"url": f"/api/design/preview/{session_id}/render"}


@router.get("/{session_id}/render")
async def render_preview(session_id: str) -> HTMLResponse:
    _guard_enabled()
    session = _load_session(session_id)
    return HTMLResponse(
        render_session_html(session),
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self' 'unsafe-inline' data: blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
        },
    )


@router.get("/{session_id}/asset/{asset_path:path}")
async def preview_asset(session_id: str, asset_path: str) -> Response:
    _guard_enabled()
    session = _load_session(session_id)
    path = resolve_session_file(session, asset_path)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return Response(path.read_bytes(), media_type=mime, headers={"Cache-Control": "no-store"})


@router.post("/{session_id}/selection")
async def update_selection(session_id: str, body: SelectionBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    store = PreviewSessionStore()
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Preview session not found")
    session.selected_selector = body.selector
    session.selected_html_snippet = body.html_snippet[:4000]
    session.selected_meta = body.meta
    store.save(session)
    return {"session": session.to_dict()}


@router.get("/{session_id}/skill-message")
async def design_skill_message(session_id: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    _ = user
    _guard_enabled()
    return {"message": build_design_skill_message(_load_session(session_id))}


@router.get("/{session_id}/events")
async def preview_events(session_id: str) -> StreamingResponse:
    _guard_enabled()
    session = _load_session(session_id)

    async def generate():
        last = session_mtime(session)
        yield f"data: {json.dumps({'type': 'ready', 'mtime': last})}\n\n"
        while True:
            await asyncio.sleep(0.5)
            current_session = PreviewSessionStore().get(session_id)
            if current_session is None:
                yield f"data: {json.dumps({'type': 'closed'})}\n\n"
                break
            current = session_mtime(current_session)
            if current and current != last:
                last = current
                yield f"data: {json.dumps({'type': 'reload', 'mtime': current})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
