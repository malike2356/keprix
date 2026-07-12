"""Universal markdown knowledge vault API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.auth.dependencies import get_current_user
from keprix.vault.config import VaultConfig, get_configured_provider, get_vault_config, save_vault_config

router = APIRouter(prefix="/api/vault", tags=["knowledge-vault"])


class VaultConfigBody(BaseModel):
    provider: str = "local_folder"
    root_path: str
    watch: bool = True
    read_only: bool = False


class VaultWriteBody(BaseModel):
    content: str


def _provider():
    try:
        return get_configured_provider()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/config")
async def get_config(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"config": get_vault_config().to_dict()}


@router.put("/config")
async def put_config(body: VaultConfigBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    config = save_vault_config(VaultConfig(**body.model_dump()))
    provider = get_configured_provider()
    files = await provider.list_files("/")
    record_onboarding_event_for_user(user, "vault.configured")
    return {"config": config.to_dict(), "file_count": len(files)}


@router.get("/files")
async def list_files(path: str = Query(default="/"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        files = await _provider().list_files(path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"files": [item.to_dict() for item in files]}


@router.get("/files/{file_path:path}")
async def read_file(file_path: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        content = await _provider().read_file(file_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"path": file_path, "content": content}


@router.put("/files/{file_path:path}")
async def write_file(file_path: str, body: VaultWriteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    config = get_vault_config()
    if config.read_only:
        raise HTTPException(status_code=403, detail="Vault is read-only")
    try:
        from keprix.agent_os.guardrails import maybe_backup_vault_before_write

        maybe_backup_vault_before_write()
    except Exception:
        pass
    try:
        await _provider().write_file(file_path, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "vault.file_in_wiki")
    return {"ok": True, "path": file_path}


@router.delete("/files/{file_path:path}")
async def delete_file(file_path: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    config = get_vault_config()
    if config.read_only:
        raise HTTPException(status_code=403, detail="Vault is read-only")
    try:
        await _provider().delete_file(file_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/search")
async def search(query: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    files = await _provider().search(query)
    return {"results": [item.to_dict() for item in files]}


@router.get("/graph")
async def graph(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return await _provider().get_graph()


@router.get("/backlinks/{file_path:path}")
async def backlinks(file_path: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        links = await _provider().get_backlinks(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"backlinks": links}
