"""Document draft autosave routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.draft_store import draft_store
from keprix.workspace.repository import workspace_repo

router = APIRouter(prefix="/api/workspace/documents", tags=["workspace-drafts"])


class DraftBody(BaseModel):
    content: str


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


@router.put("/{doc_id}/draft")
async def save_draft(
    doc_id: str,
    body: DraftBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    draft_store.save(_user_id(user), doc_id, body.content)
    return {"ok": True}


@router.get("/{doc_id}/draft")
async def get_draft(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    content = draft_store.get(_user_id(user), doc_id)
    return {"content": content}


@router.delete("/{doc_id}/draft", status_code=204)
async def delete_draft(doc_id: str, user: dict = Depends(get_current_user)) -> Response:
    try:
        workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    draft_store.delete(_user_id(user), doc_id)
    return Response(status_code=204)
