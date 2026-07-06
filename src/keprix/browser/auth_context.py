"""Authenticated browser context from vault credentials."""

from __future__ import annotations

from typing import Any

from keprix.security.vault_service import get_vault_service


async def load_auth_context(
    *,
    user_id: str,
    vault_credential_id: str | None,
) -> dict[str, Any]:
    """Resolve login hints from vault without exposing secrets in API payloads."""
    if not vault_credential_id:
        return {"authenticated": False, "username": None, "login_url": None}
    vault = get_vault_service()
    item = await vault.get_item(vault_credential_id, user_id, decrypt=True)
    if item is None:
        return {"authenticated": False, "username": None, "login_url": None}
    public = item.to_public()
    return {
        "authenticated": True,
        "username": public.get("username"),
        "login_url": public.get("url"),
        "vault_credential_id": vault_credential_id,
        "label": public.get("label"),
    }


async def apply_auth_to_profile_state(
    *,
    user_id: str,
    vault_credential_id: str | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Attach encrypted session placeholders; credentials never stored in profile JSON."""
    if not vault_credential_id:
        return state
    vault = get_vault_service()
    item = await vault.get_item(vault_credential_id, user_id, decrypt=True)
    if item is None:
        return state
    sessions = list(state.get("sessions") or [])
    sessions.append(
        {
            "vault_credential_id": vault_credential_id,
            "username": item.username,
            "login_url": item.url,
            "status": "pending_login",
        }
    )
    state["sessions"] = sessions
    return state
