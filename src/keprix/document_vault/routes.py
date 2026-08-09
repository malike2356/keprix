"""HTTP API for Document Vault (/api/document-vault/*) Prompt 646."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, Request, UploadFile
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


def _google():
    from keprix.document_vault.google.service import GoogleDriveVaultService

    return GoogleDriveVaultService()


@router.get("/google/status")
def google_status(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    return _google().status(ws)


@router.post("/google/connect")
def google_connect(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().begin_connect(
            ws,
            user_id=_uid(user),
            mode=str(body.get("mode") or "outbound_only"),
            redirect_uri=body.get("redirect_uri"),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/callback")
def google_callback(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Complete OAuth using exchanged tokens (bridge or test harness)."""
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().complete_connect(
            ws,
            user_id=_uid(user),
            access_token=str(body.get("access_token") or ""),
            refresh_token=str(body.get("refresh_token") or ""),
            account_email=body.get("account_email"),
            scopes=body.get("scopes"),
            mode=body.get("mode"),
            expires_at=body.get("expires_at"),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/configure")
def google_configure(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().configure_root(
            ws,
            root_folder_id=str(body.get("root_folder_id") or ""),
            root_folder_name=body.get("root_folder_name"),
            mode=body.get("mode"),
            enable_shared_drives=bool(body.get("enable_shared_drives")),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/sync")
def google_sync(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().sync_now(
            ws,
            source=str(body.get("source") or "manual"),
            actor_id=_uid(user),
            direction=str(body.get("direction") or "inbound"),
            item_id=body.get("item_id"),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.get("/google/conflicts")
def google_conflicts(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    return _google().list_conflicts(ws)


@router.post("/google/conflicts/{item_id}/resolve")
def google_resolve_conflict(
    item_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().resolve_conflict(
            ws,
            item_id,
            choice=str(body.get("choice") or "keep_both"),
            actor_id=_uid(user),
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/disconnect")
def google_disconnect(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    return _google().disconnect(ws)


@router.post("/google/watch/renew")
def google_watch_renew(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().renew_watch(ws)
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/refresh")
def google_refresh(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    try:
        return _google().refresh_grant(ws)
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/google/webhook")
async def google_webhook(request: Request) -> dict[str, Any]:
    """Google Drive changes notification wakeup (no OAuth bearer)."""
    headers = {str(k).lower(): str(v) for k, v in request.headers.items()}
    channel_id = headers.get("x-goog-channel-id") or ""
    resource_id = headers.get("x-goog-resource-id") or ""
    token = headers.get("x-goog-channel-token") or ""
    message_number = headers.get("x-goog-message-number")
    resource_state = headers.get("x-goog-resource-state")
    if not channel_id:
        raise HTTPException(status_code=400, detail={"error_code": "invalid_notification"})
    try:
        return _google().handle_webhook(
            channel_id=channel_id,
            resource_id=resource_id,
            channel_token=token,
            message_number=message_number,
            resource_state=resource_state,
        )
    except VaultError as exc:
        _raise(exc)
        raise


@router.get("/delivery/{token}")
def consume_delivery(token: str) -> Response:
    """Short-lived authenticated export download (Prompt 651). Token is single-use."""
    import hashlib

    if not load_flags().enabled:
        raise HTTPException(status_code=503, detail={"error_code": "not_configured"})
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = _store().consume_delivery_token(token_hash)
    if not row:
        raise HTTPException(status_code=404, detail={"error_code": "delivery_expired"})
    try:
        exported = _svc().export_item(
            row["workspace_id"],
            row["item_id"],
            target_format="markdown",
            actor_id=row.get("created_by") or "delivery",
        )
    except VaultError as exc:
        _raise(exc)
        raise
    export = exported.get("export") or {}
    data = export.get("data") or b""
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    return Response(
        content=raw,
        media_type=str(export.get("mime") or "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{row["item_id"]}"'},
    )


@router.post("/channel/bindings")
def upsert_channel_binding_route(
    body: dict[str, Any] = Body(default_factory=dict),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Bind a gateway channel identity to a workspace Document Vault."""
    from keprix.document_vault.channel.binding import bind_channel_identity

    try:
        row = bind_channel_identity(
            workspace_id=str(body.get("workspace_id") or _uid(user)),
            platform=str(body.get("platform") or ""),
            channel_user_id=str(body.get("channel_user_id") or ""),
            actor_id=str(body.get("actor_id") or _uid(user)),
            audience=str(body.get("audience") or "private"),
            grants=list(body.get("grants") or ["vault.read", "vault.write"]),
        )
        return {"ok": True, "binding": row}
    except VaultError as exc:
        _raise(exc)
        raise


@router.delete("/channel/bindings/{platform}/{channel_user_id}")
def revoke_channel_binding_route(
    platform: str,
    channel_user_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.channel.binding import revoke_channel_binding

    _ = user
    row = revoke_channel_binding(platform, channel_user_id)
    return {"ok": True, "binding": row}


@router.get("/search")
def content_or_metadata_search(
    q: str = Query(...),
    mode: str = Query(default="metadata"),
    limit: int = Query(default=20, ge=1, le=100),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    ws = _workspace(workspace_id, x_workspace_id, user)
    if not load_flags().enabled:
        raise HTTPException(status_code=503, detail={"error_code": "not_configured"})
    if mode in {"content", "rag"}:
        from keprix.document_vault.search.retriever import content_search

        return content_search(_store(), ws, q, limit=limit, grants=None)
    result = _store().search(ws, q, limit=limit)
    return {"ok": True, "mode": "metadata", "q": q, **result}


@router.post("/items/{item_id}/reindex")
def reindex_item_route(
    item_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.repair import reindex_item

    ws = _workspace(workspace_id, x_workspace_id, user)
    return reindex_item(ws, item_id, store=_store(), service=_svc())


@router.get("/ops/diagnostics")
def ops_diagnostics(
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.diagnostics import build_diagnostics

    ws = _workspace(workspace_id, x_workspace_id, user)
    return build_diagnostics(ws, store=_store())


@router.post("/ops/jobs/{job_id}/retry")
def ops_retry_job(
    job_id: str,
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.jobs import retry_job

    ws = _workspace(workspace_id, x_workspace_id, user)
    try:
        return {"ok": True, "job": retry_job(_store(), ws, job_id)}
    except VaultError as exc:
        _raise(exc)
        raise


@router.post("/ops/jobs/drain")
def ops_drain_jobs(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.jobs import drain_jobs

    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    results = drain_jobs(ws, limit=int(body.get("limit") or 20), store=_store(), service=_svc())
    return {"ok": True, "results": results, "count": len(results)}


@router.post("/ops/repair/orphans")
def ops_repair_orphans(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.repair import repair_orphan_index_entries

    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    dry_run = body.get("dry_run", True)
    return repair_orphan_index_entries(ws, dry_run=bool(dry_run), store=_store())


@router.post("/ops/backup")
def ops_backup(
    body: dict[str, Any] = Body(default_factory=dict),
    workspace_id: str | None = Query(default=None),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.document_vault.ops.backup import export_workspace_pack

    ws = _workspace(workspace_id or body.get("workspace_id"), x_workspace_id, user)
    dest = body.get("dest_dir")
    if not dest:
        raise HTTPException(status_code=400, detail={"error_code": "dest_dir_required"})
    return export_workspace_pack(_store(), ws, dest, storage_root=body.get("storage_root"))
