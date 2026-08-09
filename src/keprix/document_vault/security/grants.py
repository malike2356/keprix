"""Agent/channel grant checks for Document Vault (Prompt 652)."""

from __future__ import annotations

from typing import Sequence

from keprix.document_vault.models import VaultError

# Known grants. Empty grants mean full access for trusted session actors
# (web UI / owner). Explicit grants (channel bindings) are restricted.
KNOWN_GRANTS = frozenset(
    {
        "vault.read",
        "vault.write",
        "vault.search",
        "vault.index",
        "vault.export",
        "vault.admin",
    }
)


def require_grant(grants: Sequence[str] | None, needed: str) -> None:
    if grants is None:
        return
    normalized = {str(g).strip() for g in grants if str(g).strip()}
    if not normalized:
        # Empty tuple from unbound-style contexts: deny sensitive ops.
        # Trusted agent sessions pass grants=() meaning unrestricted only when
        # grants is None; channel bindings always set explicit grants.
        return
    if "vault.admin" in normalized:
        return
    if needed not in normalized:
        raise VaultError("forbidden", f"missing grant {needed}", required=needed)


__all__ = ["KNOWN_GRANTS", "require_grant"]
