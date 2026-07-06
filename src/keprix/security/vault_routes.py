"""Encrypted vault HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.security.audit import audit_log
from keprix.security.vault_session import vault_sessions
from keprix.security.vault_store import derive_vault_key, vault_store

router = APIRouter(prefix="/api/vault", tags=["vault"])


class VaultUnlockRequest(BaseModel):
    master_password: str


class VaultItemCreate(BaseModel):
    label: str
    category: str = "password"
    username: str | None = None
    value: str
    url: str | None = None
    tags: list[str] = Field(default_factory=list)


class VaultItemUpdate(BaseModel):
    label: str | None = None
    category: str | None = None
    username: str | None = None
    value: str | None = None
    url: str | None = None
    tags: list[str] | None = None


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username"))


def _require_unlocked(user: dict) -> bytes:
    user_id = _user_id(user)
    key = vault_sessions.get_key(user_id)
    if key is None:
        raise HTTPException(status_code=403, detail="Vault is locked")
    return key


@router.post("/unlock")
async def unlock_vault(body: VaultUnlockRequest, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    user_id = _user_id(user)
    key = derive_vault_key(body.master_password, user_id=user_id)
    vault_sessions.unlock(user_id, key)
    await audit_log("vault_unlock", user_id=user_id, event_data={"label": "vault"})
    return {"ok": True}


@router.post("/lock")
async def lock_vault(user: dict = Depends(get_current_user)) -> dict[str, bool]:
    user_id = _user_id(user)
    vault_sessions.lock(user_id)
    await audit_log("vault_lock", user_id=user_id)
    return {"ok": True}


@router.post("/items")
async def create_vault_item(body: VaultItemCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    key = _require_unlocked(user)
    item = await vault_store.create(
        user_id=_user_id(user),
        label=body.label,
        category=body.category,
        username=body.username,
        value=body.value,
        url=body.url,
        tags=body.tags,
        encryption_key=key,
    )
    await audit_log(
        "vault_item_create",
        user_id=_user_id(user),
        event_data={"item_id": item["id"], "label": body.label},
    )
    return {"item": item}


@router.get("/items")
async def list_vault_items(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    items = await vault_store.list_items(_user_id(user))
    return {"items": items}


@router.get("/items/{item_id}")
async def get_vault_item(item_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    key = _require_unlocked(user)
    try:
        item = await vault_store.get_item(_user_id(user), item_id, encryption_key=key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Vault item not found") from exc
    await audit_log("vault_item_read", user_id=_user_id(user), event_data={"item_id": item_id})
    return {"item": item}


@router.put("/items/{item_id}")
async def update_vault_item(
    item_id: str,
    body: VaultItemUpdate,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    key = _require_unlocked(user)
    try:
        item = await vault_store.update(
            _user_id(user),
            item_id,
            encryption_key=key,
            **body.model_dump(exclude_unset=True),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Vault item not found") from exc
    await audit_log("vault_item_update", user_id=_user_id(user), event_data={"item_id": item_id})
    return {"item": item}


@router.delete("/items/{item_id}")
async def delete_vault_item(item_id: str, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    _require_unlocked(user)
    try:
        await vault_store.delete(_user_id(user), item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Vault item not found") from exc
    await audit_log("vault_item_delete", user_id=_user_id(user), event_data={"item_id": item_id})
    return {"ok": True}
