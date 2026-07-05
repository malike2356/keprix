"""Note workspace routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from keprix.auth.dependencies import get_current_user
from keprix.memory.rag.indexer import RagIndexer
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import NoteCreate, NoteSearch, NoteUpdate

router = APIRouter(prefix="/api/workspace/notes", tags=["workspace-notes"])
_rag = RagIndexer()


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


async def _ingest_note(user: dict, note: dict[str, Any]) -> None:
    text = f"{note.get('title', '')}\n\n{note.get('content', '')}".strip()
    if not text:
        return
    await _rag.ingest(
        user_id=_user_id(user),
        source_type="note",
        source_id=str(note["id"]),
        content=text,
    )


@router.post("", status_code=201)
async def create_note(body: NoteCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    note = workspace_repo.create_note(user, **body.model_dump())
    await _ingest_note(user, note)
    return note


@router.get("")
async def list_notes(
    user: dict = Depends(get_current_user),
    tag: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    rows = workspace_repo.list_notes(user, tag=tag, search=search)
    return {"items": rows}


@router.get("/{note_id}")
async def get_note(note_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return workspace_repo.get_note(user, note_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found") from None


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    body: NoteUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        note = workspace_repo.update_note(user, note_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found") from None
    await _ingest_note(user, note)
    return note


@router.delete("/{note_id}", status_code=200)
async def delete_note(note_id: str, user: dict = Depends(get_current_user)) -> None:
    try:
        workspace_repo.delete_note(user, note_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Note not found") from None
    await _rag.delete_source(_user_id(user), note_id)


@router.post("/search")
async def search_notes(body: NoteSearch, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = workspace_repo.search_notes(user, body.query, limit=body.limit)
    return {"items": rows, "query": body.query}
