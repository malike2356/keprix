"""Zotero citation HTTP routes."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.citations.better_bibtex import parse_better_bibtex
from keprix.research_workspace.citations.bibtex import parse_bibtex
from keprix.research_workspace.citations.bibliography import export_bibliography
from keprix.research_workspace.citations.literature_notes import generate_literature_note
from keprix.research_workspace.citations.registry import CitationLibrary
from keprix.research_workspace.citations.zotero_api import ZoteroAPIError, ZoteroClient, ZoteroSettings, ZoteroSettingsStore
from keprix.research_workspace.citations.zotero_local import ZoteroLocalClient
from keprix.research_workspace.errors import PermissionDeniedError
from keprix.research_workspace.obsidian.sync import write_draft_note
from keprix.research_workspace.obsidian.vault import VaultRegistry
from keprix.research_workspace.permissions import assert_can_export
from keprix.research_workspace.store import get_research_workspace_store
from keprix.security.vault_service import get_vault_service

router = APIRouter(prefix="/api/research/zotero", tags=["research-zotero"])


class ZoteroConnectBody(BaseModel):
    mode: Literal["web", "local", "file"] = "web"
    api_key: str | None = None
    library_id: str | None = None
    library_type: str = "user"
    local_base_url: str = "http://127.0.0.1:23119"
    upload_attachments: bool = False
    obsidian_vault_id: str | None = None


class BibTeXImportBody(BaseModel):
    project_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    format: Literal["bibtex", "better-bibtex"] = "bibtex"


class LiteratureNotesBody(BaseModel):
    citation_keys: list[str] = Field(default_factory=list)
    vault_id: str | None = None
    sections: dict[str, str] = Field(default_factory=dict)


class BibliographyBody(BaseModel):
    format: Literal["bibtex", "csl-json", "markdown", "report"] = "markdown"
    citation_keys: list[str] = Field(default_factory=list)


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


def _settings_store() -> ZoteroSettingsStore:
    store = get_research_workspace_store()
    return ZoteroSettingsStore(store.plane.root)


async def _resolve_api_key(settings: ZoteroSettings) -> str | None:
    if not settings.api_key_vault_id:
        return None
    owner = str(settings.vault_user_id or "default")
    item = await get_vault_service().get_item(str(settings.api_key_vault_id), owner, decrypt=True)
    if item is None or not item._value:
        return None
    return item._value


@router.get("/settings")
async def get_zotero_settings(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    settings = _settings_store().load()
    payload = settings.to_dict()
    payload["connected"] = bool(
        settings.mode == "local"
        or (settings.mode == "web" and settings.api_key_vault_id and settings.library_id)
        or settings.mode == "file"
    )
    payload.pop("api_key_vault_id", None)
    return {"settings": payload}


@router.post("/settings")
async def connect_zotero(body: ZoteroConnectBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = _settings_store()
    current = store.load()
    vault_service = get_vault_service()
    user_id = _user_id(user)

    if body.mode == "web":
        if not body.api_key or not body.library_id:
            raise HTTPException(status_code=400, detail="api_key and library_id are required for web mode")
        if current.api_key_vault_id:
            await vault_service.delete_item(str(current.api_key_vault_id), user_id)
        item = await vault_service.create_item(
            user_id,
            label="Zotero API key",
            value=body.api_key,
            category="api_key",
            tags=["zotero"],
        )
        settings = ZoteroSettings(
            mode="web",
            library_id=body.library_id,
            library_type=body.library_type,
            api_key_vault_id=item.id,
            vault_user_id=user_id,
            upload_attachments=body.upload_attachments,
            obsidian_vault_id=body.obsidian_vault_id,
        )
    else:
        settings = ZoteroSettings(
            mode=body.mode,
            library_id=body.library_id or "0",
            library_type=body.library_type,
            local_base_url=body.local_base_url,
            upload_attachments=body.upload_attachments,
            obsidian_vault_id=body.obsidian_vault_id,
            vault_user_id=user_id,
        )
    saved = store.save(settings)
    payload = saved.to_dict()
    payload["connected"] = True
    payload.pop("api_key_vault_id", None)
    return {"settings": payload}


@router.post("/import")
async def import_bibtex(body: BibTeXImportBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    workspace_store = get_research_workspace_store()
    if workspace_store.get_project(body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.format == "better-bibtex":
        records = parse_better_bibtex(body.content)
    else:
        records = parse_bibtex(body.content)
    library = CitationLibrary(workspace_store)
    saved = library.save_records(body.project_id, records)
    return {"imported": len(records), "citations": saved, "items": [record.to_dict() for record in records]}


@router.post("/sync/{project_id}")
async def sync_zotero_library(project_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    workspace_store = get_research_workspace_store()
    project = workspace_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    settings = _settings_store().load()
    try:
        if settings.mode == "local":
            client: ZoteroClient = ZoteroLocalClient(base_url=settings.local_base_url)
            records = client.list_items(
                library_type=settings.library_type,
                library_id=settings.library_id or "0",
            )
        elif settings.mode == "web":
            api_key = await _resolve_api_key(settings)
            if not api_key or not settings.library_id:
                raise HTTPException(status_code=400, detail="Zotero web library is not configured")
            client = ZoteroClient(api_key=api_key)
            records = client.list_items(
                library_type=settings.library_type,
                library_id=settings.library_id,
            )
        else:
            raise HTTPException(status_code=400, detail="Sync is only available for web or local mode")
    except ZoteroAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if settings.upload_attachments:
        raise HTTPException(
            status_code=400,
            detail="Attachment upload to remote services is disabled unless explicitly approved",
        )
    library = CitationLibrary(workspace_store)
    saved = library.save_records(project_id, records)
    return {"synced": len(records), "citations": saved}


@router.get("/projects/{project_id}/citations")
async def list_project_citations(project_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    workspace_store = get_research_workspace_store()
    if workspace_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    records = CitationLibrary(workspace_store).list_cached(project_id)
    return {"items": [record.to_dict() for record in records]}


@router.post("/projects/{project_id}/literature-notes")
async def create_literature_notes(
    project_id: str,
    body: LiteratureNotesBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    workspace_store = get_research_workspace_store()
    project = workspace_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        assert_can_export(
            export_policy=project.get("export_policy") or "allow",
            user_id=_user_id(user),
            owner=project.get("owner") or "default",
        )
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    library = CitationLibrary(workspace_store)
    records = library.get_by_keys(project_id, body.citation_keys) if body.citation_keys else library.list_cached(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="No citations found")
    trace_id = project.get("trace_id") or project_id
    notes: list[dict[str, Any]] = []
    vault = None
    if body.vault_id:
        vault = VaultRegistry(workspace_store.plane.root).get_vault(body.vault_id)
        if vault is None:
            raise HTTPException(status_code=404, detail="Obsidian vault not found")
    for record in records:
        generated = generate_literature_note(
            record,
            project_id=project_id,
            trace_id=trace_id,
            sections=body.sections,
        )
        if vault is not None:
            from keprix.research_workspace.errors import UnsafeWriteError

            backup_dir = workspace_store.plane.root / "obsidian_backups" / project_id
            try:
                write_draft_note(
                    vault,
                    rel_path=generated["path"],
                    content=generated["content"],
                    backup_dir=backup_dir,
                )
            except (UnsafeWriteError, FileExistsError) as exc:
                generated["write_error"] = str(exc)
        notes.append(generated)
    return {"notes": notes}


@router.post("/projects/{project_id}/bibliography")
async def export_project_bibliography(
    project_id: str,
    body: BibliographyBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    workspace_store = get_research_workspace_store()
    if workspace_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    library = CitationLibrary(workspace_store)
    records = library.get_by_keys(project_id, body.citation_keys) if body.citation_keys else library.list_cached(project_id)
    if not records:
        raise HTTPException(status_code=404, detail="No citations found")
    content = export_bibliography(records, body.format)
    return {"format": body.format, "content": content, "count": len(records)}
