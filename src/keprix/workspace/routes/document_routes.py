"""Document workspace routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.document_helpers import (
    ai_suggest,
    apply_ai_edit,
    document_to_dict,
    export_document,
)
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import DocumentAIEdit, DocumentCreate, DocumentUpdate

router = APIRouter(prefix="/api/workspace/documents", tags=["workspace-documents"])


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


@router.post("", status_code=201)
async def create_document(body: DocumentCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    doc = workspace_repo.create_document(user, **body.model_dump())
    return document_to_dict(doc)


@router.get("")
async def list_documents(
    user: dict = Depends(get_current_user),
    tag: str | None = None,
    format: str | None = Query(None, alias="format"),
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    rows = workspace_repo.list_documents(user, tag=tag, fmt=format, limit=limit, offset=offset)
    return {"items": [document_to_dict(doc) for doc in rows], "limit": limit, "offset": offset}


@router.get("/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        doc = workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return document_to_dict(doc)


@router.put("/{doc_id}")
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        doc = workspace_repo.update_document(user, doc_id, **body.model_dump(exclude_none=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return document_to_dict(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)) -> Response:
    try:
        workspace_repo.delete_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return Response(status_code=204)


@router.post("/{doc_id}/ai-edit")
async def ai_edit_document(
    doc_id: str,
    body: DocumentAIEdit,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        doc = workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    modified = apply_ai_edit(doc.get("content", ""), body.instruction)
    return {"content": modified, "instruction": body.instruction}


@router.post("/{doc_id}/ai-suggest")
async def ai_suggest_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        doc = workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return {"suggestions": ai_suggest(doc.get("content", ""))}


@router.get("/{doc_id}/export")
async def export_doc(
    doc_id: str,
    format: str = Query("md", alias="format"),
    user: dict = Depends(get_current_user),
) -> Response:
    try:
        doc = workspace_repo.get_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    media_type, payload = export_document(doc, format)
    if isinstance(payload, bytes):
        return Response(content=payload, media_type=media_type)
    return Response(content=payload, media_type=media_type)


@router.post("/{doc_id}/share")
async def share_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        doc = workspace_repo.share_document(user, doc_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return {"share_token": doc["share_token"], "is_shared": True}
