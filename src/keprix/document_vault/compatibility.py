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
        status="partial",
        notes="Migrate via /api/document-vault/migrate; dual-write only while ENABLED and not CUTOVER; CUTOVER=1 stops dual-write",
    ),
    AdapterSpec(
        caller="/api/vault/files",
        source="keprix.vault.local_folder",
        target="document_vault.items(markdown)",
        status="partial",
        notes="Knowledge vault files migrate into folder tree; path segments become parents",
    ),
    AdapterSpec(
        caller="/api/documents",
        source="documents.index_manager",
        target="document_vault.index_entries",
        status="partial",
        notes="Canonical content index + revision citations (652); legacy indexes remain until cutover",
    ),
    AdapterSpec(
        caller="/api/files/upload",
        source="conversation file_ids",
        target="document_vault.import",
        status="planned",
        notes="Quarantine + Soft Wall before durable import",
    ),
    AdapterSpec(
        caller="/api/document-vault",
        source="document_vault.store",
        target="document_vault.items",
        status="active",
        notes="Canonical HTTP surface (Prompt 646)",
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
    # Cutover: canonical vault is the only write path; dual-write stops.
    return {
        "ok": True,
        "flags": flags.as_env_map(),
        "cutover": bool(flags.cutover),
        "dual_write": bool(flags.migrate and not flags.cutover),
    }
