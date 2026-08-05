"""Document workspace routes with Postgres-backed durable store."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.workspace.core.exceptions import NotFoundError
from keprix.workspace.document_helpers import (
    ai_suggest,
    apply_ai_edit,
    document_to_dict,
    export_document,
)
from keprix.workspace.documents_pg import (
    _use_db,
    pg_create_document,
    pg_delete_document,
    pg_get_by_share_token,
    pg_get_document,
    pg_list_documents,
    pg_list_versions,
    pg_update_document,
)
from keprix.workspace.repository import workspace_repo
from keprix.workspace.schemas import DocumentAIEdit, DocumentCreate, DocumentUpdate

router = APIRouter(prefix="/api/workspace/documents", tags=["workspace-documents"])


def _uid(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "local")


class DocumentPatchExtras(BaseModel):
    is_favorite: bool | None = None
    folder: str | None = None


async def _create(user: dict, data: dict[str, Any]) -> dict[str, Any]:
    uid = _uid(user)
    if _use_db():
        doc = await pg_create_document(uid, data)
        if doc is None:
            raise HTTPException(500, "Failed to persist document")
        return doc
    return workspace_repo.create_document(user, **data)


async def _list(
    user: dict,
    *,
    tag: str | None,
    fmt: str | None,
    q: str | None,
    folder: str | None,
    favorites_only: bool,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    uid = _uid(user)
    if _use_db():
        rows = await pg_list_documents(
            uid,
            tag=tag,
            fmt=fmt,
            q=q,
            folder=folder,
            favorites_only=favorites_only,
            limit=limit,
            offset=offset,
        )
        return rows or []
    rows = workspace_repo.list_documents(user, tag=tag, fmt=fmt, limit=500, offset=0)
    if q:
        needle = q.lower()
        rows = [
            d
            for d in rows
            if needle in (d.get("title") or "").lower() or needle in (d.get("content") or "").lower()
        ]
    if folder is not None:
        rows = [d for d in rows if (d.get("folder") or "") == folder]
    if favorites_only:
        rows = [d for d in rows if d.get("is_favorite")]
    return rows[offset : offset + limit]


async def _get(user: dict, doc_id: str) -> dict[str, Any]:
    uid = _uid(user)
    if _use_db():
        doc = await pg_get_document(uid, doc_id)
        if doc is None:
            raise HTTPException(404, "Document not found")
        return doc
    try:
        return workspace_repo.get_document(user, doc_id)
    except NotFoundError as exc:
        raise HTTPException(404, "Document not found") from exc


async def _update(user: dict, doc_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    uid = _uid(user)
    if _use_db():
        doc = await pg_update_document(uid, doc_id, updates)
        if doc is None:
            raise HTTPException(404, "Document not found")
        return doc
    try:
        return workspace_repo.update_document(user, doc_id, **updates)
    except NotFoundError as exc:
        raise HTTPException(404, "Document not found") from exc


async def _delete(user: dict, doc_id: str) -> None:
    uid = _uid(user)
    if _use_db():
        ok = await pg_delete_document(uid, doc_id)
        if not ok:
            raise HTTPException(404, "Document not found")
        return
    try:
        workspace_repo.delete_document(user, doc_id)
    except NotFoundError as exc:
        raise HTTPException(404, "Document not found") from exc


@router.post("", status_code=201)
async def create_document(body: DocumentCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    doc = await _create(user, body.model_dump())
    return document_to_dict(doc)


@router.get("")
async def list_documents(
    user: dict = Depends(get_current_user),
    tag: str | None = None,
    format: str | None = Query(None, alias="format"),
    q: str | None = None,
    folder: str | None = None,
    favorites: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    rows = await _list(
        user,
        tag=tag,
        fmt=format,
        q=q,
        folder=folder,
        favorites_only=favorites,
        limit=limit,
        offset=offset,
    )
    return {"items": [document_to_dict(doc) for doc in rows], "limit": limit, "offset": offset}


@router.get("/shared/{token}")
async def get_shared_document(token: str) -> dict[str, Any]:
    doc = await pg_get_by_share_token(token)
    if doc is None:
        # Memory fallback scan
        for item in workspace_repo.documents.values():
            if item.get("share_token") == token and item.get("is_shared"):
                return document_to_dict(item)
        raise HTTPException(404, "Shared document not found")
    return document_to_dict(doc)


@router.get("/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return document_to_dict(await _get(user, doc_id))


@router.put("/{doc_id}")
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    updates = body.model_dump(exclude_none=True)
    return document_to_dict(await _update(user, doc_id, updates))


@router.patch("/{doc_id}/meta")
async def patch_document_meta(
    doc_id: str,
    body: DocumentPatchExtras,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return document_to_dict(await _update(user, doc_id, body.model_dump(exclude_none=True)))


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)) -> Response:
    await _delete(user, doc_id)
    return Response(status_code=204)


@router.post("/{doc_id}/ai-edit")
async def ai_edit_document(
    doc_id: str,
    body: DocumentAIEdit,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    doc = await _get(user, doc_id)
    modified = await apply_ai_edit(doc.get("content", ""), body.instruction)
    return {"content": modified, "instruction": body.instruction}


@router.post("/{doc_id}/ai-suggest")
async def ai_suggest_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    doc = await _get(user, doc_id)
    return {"suggestions": await ai_suggest(doc.get("content", ""))}


@router.get("/{doc_id}/export")
async def export_doc(
    doc_id: str,
    format: str = Query("md", alias="format"),
    user: dict = Depends(get_current_user),
) -> Response:
    doc = await _get(user, doc_id)
    media_type, payload = export_document(doc, format)
    filename = f"{(doc.get('title') or 'document').replace(' ', '_')}.{format if format != 'md' else 'md'}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if isinstance(payload, bytes):
        return Response(content=payload, media_type=media_type, headers=headers)
    return Response(content=payload, media_type=media_type, headers=headers)


@router.post("/{doc_id}/share")
async def share_document(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    token = secrets.token_urlsafe(24)
    doc = await _update(user, doc_id, {"is_shared": True, "share_token": token})
    return {"share_token": doc.get("share_token"), "is_shared": True, "path": f"/share/documents/{token}"}


@router.get("/{doc_id}/versions")
async def list_versions(doc_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    await _get(user, doc_id)
    if _use_db():
        rows = await pg_list_versions(_uid(user), doc_id) or []
        return {"items": rows}
    return {"items": []}


@router.post("/{doc_id}/versions/{version_id}/restore")
async def restore_version(
    doc_id: str, version_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    await _get(user, doc_id)
    if not _use_db():
        raise HTTPException(501, "Version history requires Postgres")
    versions = await pg_list_versions(_uid(user), doc_id) or []
    match = next((v for v in versions if v["id"] == version_id), None)
    if match is None:
        raise HTTPException(404, "Version not found")
    doc = await _update(user, doc_id, {"title": match["title"], "content": match["content"]})
    return document_to_dict(doc)


@router.post("/import")
async def import_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    raw = await file.read()
    name = file.filename or "upload.txt"
    lower = name.lower()
    title = name.rsplit(".", 1)[0] if "." in name else name
    content = ""
    try:
        if lower.endswith((".md", ".txt", ".markdown", ".csv")):
            content = raw.decode("utf-8", errors="replace")
        elif lower.endswith(".html") or lower.endswith(".htm"):
            content = raw.decode("utf-8", errors="replace")
        elif lower.endswith(".docx"):
            try:
                import io

                import docx  # type: ignore

                document = docx.Document(io.BytesIO(raw))
                content = "\n".join(p.text for p in document.paragraphs)
            except Exception as exc:
                raise HTTPException(400, f"Could not parse DOCX: {exc}") from exc
        elif lower.endswith(".pdf"):
            try:
                import io

                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(raw))
                content = "\n".join((page.extract_text() or "") for page in reader.pages)
            except Exception as exc:
                raise HTTPException(400, f"Could not parse PDF: {exc}") from exc
        else:
            content = raw.decode("utf-8", errors="replace")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Import failed: {exc}") from exc
    doc = await _create(
        user,
        {
            "title": title,
            "content": content.strip(),
            "format": "markdown",
            "tags": ["imported"],
        },
    )
    return document_to_dict(doc)


class ImportPathBody(BaseModel):
    path: str = Field(..., min_length=1)
    folder: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["disk", "imported"])


@router.post("/import-path")
async def import_document_from_path(
    body: ImportPathBody, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    from keprix.documents.disk_paths import read_path_as_text, resolve_allowed_path

    try:
        path = resolve_allowed_path(body.path)
        if not path.is_file():
            raise ValueError("Path must be a file")
        title, content = read_path_as_text(path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    doc = await _create(
        user,
        {
            "title": title,
            "content": content.strip(),
            "format": "markdown",
            "tags": body.tags or ["disk", "imported"],
            "folder": body.folder or "disk",
        },
    )
    return document_to_dict(doc)
