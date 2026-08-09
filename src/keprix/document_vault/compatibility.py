"""Compatibility adapter registry (Prompt 645 design; 646+ wiring).

Adapters document how legacy callers map into the canonical vault without
creating a fourth store after cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keprix.document_vault.flags import load_flags


@dataclass(frozen=True)
class AdapterSpec:
    caller: str
    source: str
    target: str
    status: str  # planned | partial | active | retired
    notes: str


ADAPTERS: tuple[AdapterSpec, ...] = (
    AdapterSpec(
        caller="/api/workspace/documents",
        source="workspace.documents_pg|repository",
        target="document_vault.items",
        status="planned",
        notes="Preserve IDs via mapping; enable when KEPRIX_DOCUMENT_VAULT_ENABLED",
    ),
    AdapterSpec(
        caller="/api/vault/files",
        source="keprix.vault.local_folder",
        target="document_vault.items(markdown)",
        status="planned",
        notes="Path segments become folder ancestry",
    ),
    AdapterSpec(
        caller="/api/documents",
        source="documents.index_manager",
        target="document_vault.index_state",
        status="planned",
        notes="Version-aware index jobs in 652",
    ),
    AdapterSpec(
        caller="/api/files/upload",
        source="conversation file_ids",
        target="document_vault.import",
        status="planned",
        notes="Quarantine + Soft Wall before durable import",
    ),
    AdapterSpec(
        caller="/api/fs",
        source="host filesystem",
        target="NONE",
        status="retired",
        notes="Explicitly not adapted; host_fs_forbidden",
    ),
)


def list_adapters() -> list[dict[str, Any]]:
    return [
        {
            "caller": a.caller,
            "source": a.source,
            "target": a.target,
            "status": a.status,
            "notes": a.notes,
        }
        for a in ADAPTERS
    ]


def adapter_routing_allowed(caller: str) -> dict[str, Any]:
    """Return whether a caller may route into the vault under current flags."""
    flags = load_flags()
    if caller.startswith("/api/fs"):
        return {
            "ok": False,
            "error_code": "host_fs_forbidden",
            "flags": flags.as_env_map(),
        }
    if not flags.enabled:
        return {
            "ok": False,
            "error_code": "not_configured",
            "legacy": True,
            "flags": flags.as_env_map(),
        }
    return {"ok": True, "flags": flags.as_env_map()}
