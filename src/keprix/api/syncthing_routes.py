"""Authenticated API for Syncthing Obsidian vault bridge."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.sync.syncthing.client import SyncthingError
from keprix.sync.syncthing.service import ensure_vault_folder, get_status, pause_folder, update_settings

router = APIRouter(prefix="/api/syncthing", tags=["syncthing"])


class SettingsBody(BaseModel):
    enabled: bool | None = None
    base_url: str | None = Field(default=None, alias="baseUrl")
    folder_id: str | None = Field(default=None, alias="folderId")
    folder_label: str | None = Field(default=None, alias="folderLabel")
    vault_path: str | None = Field(default=None, alias="vaultPath")
    syncthing_path: str | None = Field(default=None, alias="syncthingPath")
    writer_role: str | None = Field(default=None, alias="writerRole")
    device_ids: list[str] | None = Field(default=None, alias="deviceIds")
    rescan_interval_s: int | None = Field(default=None, alias="rescanIntervalS")
    api_key: str | None = Field(default=None, alias="apiKey")

    model_config = {"populate_by_name": True}


class PauseBody(BaseModel):
    paused: bool = True


@router.get("/status")
async def syncthing_status(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return get_status()


@router.put("/settings")
async def syncthing_settings(body: SettingsBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return update_settings(body.model_dump(by_alias=False, exclude_unset=True))


@router.post("/ensure-folder")
async def syncthing_ensure_folder(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        return ensure_vault_folder()
    except SyncthingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pause")
async def syncthing_pause(body: PauseBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        return pause_folder(body.paused)
    except SyncthingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
