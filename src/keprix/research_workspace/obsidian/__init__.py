"""Filesystem-first Obsidian vault adapter."""

from keprix.research_workspace.obsidian.graph_export import export_obsidian_vault
from keprix.research_workspace.obsidian.sync import index_vault, read_note, write_draft_note
from keprix.research_workspace.obsidian.templates import NOTE_TYPES, render_research_note
from keprix.research_workspace.obsidian.vault import SyncMode, VaultConfig, VaultRegistry

__all__ = [
    "NOTE_TYPES",
    "SyncMode",
    "VaultConfig",
    "VaultRegistry",
    "export_obsidian_vault",
    "index_vault",
    "read_note",
    "render_research_note",
    "write_draft_note",
]
