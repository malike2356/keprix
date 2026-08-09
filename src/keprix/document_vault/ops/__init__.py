"""Document Vault operations package (Prompt 652)."""

from __future__ import annotations

from keprix.document_vault.ops.backup import (
    export_workspace_pack,
    restore_workspace_pack_drill,
    temp_backup_restore_roundtrip,
)
from keprix.document_vault.ops.diagnostics import build_diagnostics
from keprix.document_vault.ops.jobs import drain_jobs, process_job, retry_job
from keprix.document_vault.ops.repair import reindex_item, repair_orphan_index_entries

__all__ = [
    "build_diagnostics",
    "drain_jobs",
    "export_workspace_pack",
    "process_job",
    "reindex_item",
    "repair_orphan_index_entries",
    "restore_workspace_pack_drill",
    "retry_job",
    "temp_backup_restore_roundtrip",
]
