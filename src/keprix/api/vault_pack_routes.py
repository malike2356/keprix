"""Vault starter pack API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.vault.pack_registry import list_vault_packs
from keprix.vault.vault_init_service import init_vault
from keprix.vault.vault_validator import validate_vault

router = APIRouter(prefix="/api/vault", tags=["vault-packs"])


class VaultInitBody(BaseModel):
    pack: str = "obsidian-starter"
    path: str = Field(..., min_length=1)
    overwrite: bool = False


class VaultValidateBody(BaseModel):
    path: str = Field(..., min_length=1)


@router.get("/packs")
async def vault_packs(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"packs": [pack.to_dict() for pack in list_vault_packs()]}


@router.post("/init")
async def vault_init(body: VaultInitBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    try:
        return init_vault(pack=body.pack, path=body.path, overwrite=body.overwrite)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/validate")
async def vault_validate(body: VaultValidateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return validate_vault(body.path)
