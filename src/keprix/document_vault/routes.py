"""HTTP API for Document Vault (/api/document-vault/*) Prompt 646."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response

from keprix.auth.dependencies import get_current_user
from keprix.document_vault.flags import load_flags
from keprix.document_vault.migrate import migrate_from_workspace_repo, migrate_workspace_documents
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import get_document_vault_service
from keprix.document_vault.store import get_document_vault_store

router = APIRouter(prefix="/api/document-vault", tags=["document-vault"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(
    workspace_id: str | None,
    x_workspace_id: str | None,
    user: dict[str, Any],
) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


def _raise(exc: VaultError) -> None:
    status = 409 if exc.code in {"stale_revision", "cycle_rejected", "idempotent_replay"} else 400
    if exc.code in {"not_found"}:
        status = 404
    if exc.code in {"workspace_mismatch", "host_fs_forbidden"}:
        status = 403
    if exc.code == "not_configured":
        status = 503
    if exc.code == "soft_wall_required":
        status = 402
    raise HTTPException(status_code=status, detail=exc.as_dict())


def _svc():
    return get_document_vault_service()


def _store():
    return get_document_vault_store()


@router.get("/flags")
def flags_route(_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return load_flags().as_env_map()


@router.get("/items")
def list_items(
    parent_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
    include_trashed: bool = Query(default=False),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    if q:
        return _store().search(ws, q, limit=limit, offset=offset)
    return _store().list_items(
        ws,
        parent_id=parent_id,
        include_trashed=include_trashed,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{item_id}")
def get_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    item = _store().get_item(ws, item_id, include_trashed=True)
    if not item:
        raise HTTPException(status_code=404, detail={"error_code": "not_found"})
    return item


@router.get("/items/{item_id}/content")
def read_content(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        text = _svc().read_text(ws, item_id)
    except VaultError as exc:
        _raise(exc)
        raise
    return {"item_id": item_id, "content": text}


@router.post("/items")
def create_item(
    body: dict[str, Any] = Body(...),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    actor = _uid(user)
    kind = str(body.get("kind") or "markdown")
    try:
        if kind == "folder":
            return _svc().create_folder(
                ws, str(body.get("name") or "Folder"), parent_id=body.get("parent_id"), actor_id=actor
            )
        content = str(body.get("content") or "")
        return _svc().create_text_item(
            ws,
            str(body.get("name") or "Untitled"),
            content,
            kind=kind,
            parent_id=body.get("parent_id"),
            actor_id=actor,
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.patch("/items/{item_id}")
def update_item(
    item_id: str,
    body: dict[str, Any] = Body(...),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    actor = _uid(user)
    try:
        if "content" in body:
            data = str(body.get("content") or "").encode("utf-8")
            return _svc().write_content(
                ws,
                item_id,
                data,
                expected_revision=body.get("expected_revision"),
                actor_id=actor,
                change_summary=str(body.get("change_summary") or "update"),
            )
        if body.get("append"):
            return _svc().append_text(
                ws,
                item_id,
                str(body.get("append")),
                expected_revision=body.get("expected_revision"),
                actor_id=actor,
            )
        return _store().update_item(
            ws,
            item_id,
            expected_revision=body.get("expected_revision"),
            name=body.get("name"),
            is_favorite=body.get("is_favorite"),
            index_policy=body.get("index_policy"),
            classification=body.get("classification"),
            metadata=body.get("metadata"),
            actor_id=actor,
            bump_revision=False,
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/items/{item_id}/move")
def move_item(
    item_id: str,
    body: dict[str, Any] = Body(...),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _store().move(ws, item_id, body.get("parent_id"), actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/items/{item_id}/copy")
def copy_item(
    item_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _store().copy(
            ws,
            item_id,
            new_parent_id=body.get("parent_id"),
            new_name=body.get("name"),
            actor_id=_uid(user),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/items/{item_id}/trash")
def trash_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        return _store().trash(ws, item_id, actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/items/{item_id}/restore")
def restore_item(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        return _store().restore(ws, item_id, actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise


@router.delete("/items/{item_id}")
def permanent_delete(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        return _store().permanent_delete(ws, item_id, actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise


@router.get("/items/{item_id}/revisions")
def list_revisions(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        rows = _store().list_revisions(ws, item_id)
    except VaultError as exc:
        _raise(exc)
        raise
    return {"item_id": item_id, "revisions": rows, "count": len(rows)}


@router.post("/items/{item_id}/revisions/{revision}/restore")
def restore_revision(
    item_id: str,
    revision: int,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        return _svc().restore_revision(ws, item_id, revision, actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise


@router.get("/jobs")
def list_jobs(
    status: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = _store().list_jobs(ws, status=status)
    return {"jobs": rows, "count": len(rows)}


@router.get("/audit")
def list_audit(
    limit: int = Query(default=100),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    rows = _store().list_audit(ws, limit=limit)
    return {"events": rows, "count": len(rows)}


@router.post("/migrate")
def migrate_route(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    dry_run = bool(body.get("dry_run", True))
    source = str(body.get("source") or "workspace_repo")
    if source == "documents" and isinstance(body.get("documents"), list):
        return migrate_workspace_documents(ws, body["documents"], dry_run=dry_run)
    return migrate_from_workspace_repo(ws, dry_run=dry_run)


@router.get("/formats")
def formats_matrix(_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    from keprix.document_vault.formats.registry import capability_matrix_for_clients

    return capability_matrix_for_clients()


@router.post("/import")
async def import_upload(
    file: UploadFile = File(...),
    parent_id: str | None = Query(default=None),
    keep_original: bool = Query(default=True),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    data = await file.read()
    try:
        return _svc().import_bytes(
            ws,
            data,
            filename=file.filename or "upload.bin",
            declared_mime=file.content_type or "",
            parent_id=parent_id,
            actor_id=_uid(user),
            keep_original=keep_original,
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/items/{item_id}/export")
def export_item_route(
    item_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    target = str(body.get("format") or body.get("target_format") or "markdown")
    try:
        result = _svc().export_item(ws, item_id, target_format=target, actor_id=_uid(user))
    except VaultError as exc:
        _raise(exc)
        raise
    export = result["export"]
    headers = {
        "X-Keprix-Source-Revision": str(result.get("source_revision") or ""),
        "X-Keprix-Fidelity": str(export.get("fidelity") or ""),
        "X-Keprix-Converter-Version": str(export.get("converter_version") or ""),
    }
    return Response(
        content=export["data"],
        media_type=export.get("mime") or "application/octet-stream",
        headers=headers,
    )


@router.post("/items/{item_id}/pdf")
def generate_pdf_route(
    item_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _svc().generate_pdf_artifact(
            ws,
            item_id,
            actor_id=_uid(user),
            parent_id=body.get("parent_id"),
        )
    except VaultError as exc:
        _raise(exc)
        raise
