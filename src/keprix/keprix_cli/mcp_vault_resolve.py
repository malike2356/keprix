"""Resolve Vault secrets for MCP catalog install (admin API)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException


async def resolve_vault_env(
    vault_env: Dict[str, str],
    user: Optional[dict],
) -> Dict[str, str]:
    """Map env var names to decrypted vault item values."""
    if not vault_env:
        return {}
    if not user:
        raise HTTPException(
            status_code=403,
            detail="Sign in to use Vault-backed MCP credentials",
        )
    user_id = str(user.get("id") or user.get("username") or "")
    if not user_id:
        raise HTTPException(status_code=403, detail="Sign in to use Vault-backed MCP credentials")

    from keprix.security.vault_session import vault_sessions
    from keprix.security.vault_store import vault_store

    encryption_key = vault_sessions.get_key(user_id)
    if encryption_key is None:
        raise HTTPException(status_code=403, detail="Vault is locked")

    resolved: Dict[str, str] = {}
    for env_name, item_id in vault_env.items():
        env_key = str(env_name).strip()
        secret_id = str(item_id).strip()
        if not env_key or not secret_id:
            continue
        try:
            item = await vault_store.get_item(
                user_id, secret_id, encryption_key=encryption_key
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Vault item '{secret_id}' not found for {env_key}",
            ) from exc
        value = str(item.get("value") or "").strip()
        if not value:
            raise HTTPException(
                status_code=400,
                detail=f"Vault item '{secret_id}' has no value for {env_key}",
            )
        resolved[env_key] = value
    return resolved


async def list_vault_secret_keys(user: Optional[dict]) -> list[dict[str, str]]:
    """Return vault item id/label pairs for MCP credential pickers."""
    if not user:
        return []
    user_id = str(user.get("id") or user.get("username") or "")
    if not user_id:
        return []

    from keprix.security.vault_store import vault_store

    items = await vault_store.list_items(user_id)
    return [{"id": str(item["id"]), "label": str(item.get("label") or item["id"])} for item in items]
