"""Vault adapter that exposes labels only; never decrypts into prompts."""

from __future__ import annotations

from keprix.security.vault_service import get_vault_service
from keprix.typed_agents.dependencies import VaultAccess


class KeprixVaultAccess(VaultAccess):
    """Production vault wrapper backed by the Keprix vault service."""

    @classmethod
    async def from_user(cls, user_id: str) -> KeprixVaultAccess:
        vault = get_vault_service()
        items = await vault.list_items(user_id)
        labels = {item.id: item.label for item in items}
        return cls(user_id, labels=labels)
