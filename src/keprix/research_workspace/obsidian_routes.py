"""Obsidian vault HTTP routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.errors import (
    PermissionDeniedError,
    ProjectNotFoundError,
    UnsafeWriteError,
    VaultPathError,
)
from keprix.research_workspace.obsidian.sync import index_vault, write_draft_note
from keprix.research_workspace.obsidian.templates import NOTE_TYPES, note_filename, render_research_note
from keprix.research_workspace.obsidian.vault import VaultRegistry
from keprix.research_workspace.permissions import assert_can_export
from keprix.research_workspace.store import get_research_workspace_store

router = APIRouter(prefix="/api/research/obsidian", tags=["research-obsidian"])


class VaultBody(BaseModel):
    name: str = Field(..., min_length=1)
    local_path: str = Field(..., min_length=1)
    allowed_folders: list[str] = Field(default_factory=lambda: ["."])
    excluded_folders: list[str] = Field(default_factory=lambda: [".obsidian", ".trash"])
    attachment_folder: str = "attachments"
    template_folder: str = "templates"
    sync_mode: str = "write-draft"
    allow_external_path: bool = False


class DraftNoteBody(BaseModel):
    vault_id: str = Field(..., min_length=1)
    note_type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    body: str = ""
    source_id: str | None = None
    backlinks: list[str] = Field(default_factory=list)


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


def _registry() -> VaultRegistry:
    store = get_research_workspace_store()
    return VaultRegistry(store.plane.root)


@router.get("/vaults")
async def list_vaults(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    vaults = _registry().list_vaults()
    return {"items": [vault.to_dict() for vault in vaults]}


@router.post("/vaults")
async def register_vault(body: VaultBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        vault = _registry().register(
            name=body.name,
            local_path=body.local_path,
            allowed_folders=body.allowed_folders,
            excluded_folders=body.excluded_folders,
            attachment_folder=body.attachment_folder,
            template_folder=body.template_folder,
            sync_mode=body.sync_mode,
            allow_external_path=body.allow_external_path,
        )
    except VaultPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"vault": vault.to_dict()}


@router.post("/vaults/{vault_id}/index")
async def index_registered_vault(vault_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    vault = _registry().get_vault(vault_id)
    if vault is None:
        raise HTTPException(status_code=404, detail="Vault not found")
    try:
        return index_vault(vault)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/notes")
async def create_draft_note(
    project_id: str,
    body: DraftNoteBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if body.note_type not in NOTE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported note_type. Use one of: {', '.join(NOTE_TYPES)}")
    store = get_research_workspace_store()
    project = store.get_project(project_id)
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
    vault = _registry().get_vault(body.vault_id)
    if vault is None:
        raise HTTPException(status_code=404, detail="Vault not found")
    trace_id = project.get("trace_id") or project_id
    content = render_research_note(
        body.note_type,
        title=body.title,
        body=body.body,
        project_id=project_id,
        trace_id=trace_id,
        source_id=body.source_id,
        backlinks=body.backlinks,
    )
    backup_dir = store.plane.root / "obsidian_backups" / project_id
    rel = note_filename(body.note_type, trace_id[:8])
    try:
        result = write_draft_note(vault, rel_path=rel, content=content, backup_dir=backup_dir)
    except UnsafeWriteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"note": result, "note_type": body.note_type}


@router.get("/projects/{project_id}/backlinks")
async def project_backlinks(project_id: str, vault_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    store = get_research_workspace_store()
    if store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    vault = _registry().get_vault(vault_id)
    if vault is None:
        raise HTTPException(status_code=404, detail="Vault not found")
    indexed = index_vault(vault)
    project_notes = [
        note
        for note in indexed["notes"]
        if note.get("meta", {}).get("keprix_project_id") == project_id
    ]
    return {"items": project_notes, "backlink_index": indexed["backlink_index"]}
