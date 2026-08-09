"""Trusted channel identity binding for Document Vault (Prompt 651).

Unbound, revoked, public, and ambiguous identities have no vault access.
Workspace is never inferred from message content, filenames, or model args.
"""

from __future__ import annotations

from typing import Any

from keprix.document_vault.agent_context import VaultAgentContext
from keprix.document_vault.flags import load_flags
from keprix.document_vault.models import VaultError
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store

_PUBLIC = frozenset({"public", "external", "anonymous", "world"})
_ANON_USERS = frozenset({"", "anonymous", "stranger", "unknown", "public"})


def _store(store: DocumentVaultStore | None = None) -> DocumentVaultStore:
    return store or get_document_vault_store()


def resolve_channel_binding(
    platform: str,
    channel_user_id: str,
    *,
    claimed_workspace_id: str | None = None,
    store: DocumentVaultStore | None = None,
) -> VaultAgentContext:
    flags = load_flags()
    if not flags.enabled or not flags.channel_ops:
        raise VaultError("not_configured", "Document Vault channel ops disabled")

    platform_key = str(platform or "").strip().lower()
    user_key = str(channel_user_id or "").strip()
    if not platform_key or user_key.lower() in _ANON_USERS:
        raise VaultError("channel_unbound", "channel identity is unbound or anonymous")

    row = _store(store).get_channel_binding(platform_key, user_key)
    if not row:
        raise VaultError("channel_unbound", "no Document Vault binding for this channel identity")
    status = str(row.get("status") or "")
    if status == "revoked":
        raise VaultError("channel_revoked", "channel Document Vault binding revoked")
    if status != "active":
        raise VaultError("channel_unbound", f"channel binding status is {status}")

    audience = str(row.get("audience") or "private").lower()
    if audience in _PUBLIC:
        raise VaultError("forbidden", "public channel audience cannot access private Document Vault")

    workspace_id = str(row.get("workspace_id") or "").strip()
    if not workspace_id:
        raise VaultError("channel_unbound", "binding missing workspace")

    claimed = str(claimed_workspace_id or "").strip()
    if claimed and claimed != workspace_id:
        raise VaultError("workspace_mismatch", "claimed workspace does not match channel binding")

    grants = row.get("grants") or []
    if isinstance(grants, str):
        grants = [g.strip() for g in grants.split(",") if g.strip()]

    return VaultAgentContext(
        workspace_id=workspace_id,
        actor_id=str(row.get("actor_id") or user_key),
        audience=audience or "private",
        session_id=f"{platform_key}:{user_key}",
        channel=platform_key,
        grants=tuple(str(g) for g in grants),
    )


def bind_channel_identity(
    *,
    workspace_id: str,
    platform: str,
    channel_user_id: str,
    actor_id: str | None = None,
    audience: str = "private",
    grants: list[str] | None = None,
    store: DocumentVaultStore | None = None,
) -> dict[str, Any]:
    ws = str(workspace_id or "").strip()
    platform_key = str(platform or "").strip().lower()
    user_key = str(channel_user_id or "").strip()
    if not ws or not platform_key or user_key.lower() in _ANON_USERS:
        raise VaultError("invalid_args", "workspace, platform, and channel_user_id required")
    if str(audience or "").lower() in _PUBLIC:
        raise VaultError("forbidden", "cannot bind public audience to private Document Vault")
    return _store(store).upsert_channel_binding(
        workspace_id=ws,
        platform=platform_key,
        channel_user_id=user_key,
        actor_id=str(actor_id or user_key),
        audience=audience or "private",
        grants=grants or ["vault.read", "vault.write"],
        status="active",
    )


def revoke_channel_binding(
    platform: str,
    channel_user_id: str,
    *,
    store: DocumentVaultStore | None = None,
) -> dict[str, Any] | None:
    return _store(store).set_channel_binding_status(
        str(platform or "").strip().lower(),
        str(channel_user_id or "").strip(),
        status="revoked",
    )


def tool_kwargs_from_binding(ctx: VaultAgentContext) -> dict[str, Any]:
    """Trusted kwargs for document_vault_* tool dispatch."""
    return {
        "trusted_workspace_id": ctx.workspace_id,
        "workspace_id": ctx.workspace_id,
        "user_id": ctx.actor_id,
        "actor_id": ctx.actor_id,
        "session_id": ctx.session_id,
        "channel": ctx.channel,
        "audience": ctx.audience,
        "grants": list(ctx.grants),
    }


__all__ = [
    "bind_channel_identity",
    "resolve_channel_binding",
    "revoke_channel_binding",
    "tool_kwargs_from_binding",
]
