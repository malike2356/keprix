"""Known Document Vault-related surfaces for inventory (Prompt 645)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Surface:
    key: str
    category: str
    path: str
    tenant_scoped: bool
    migrate_eligible: bool
    notes: str


# Relative to keprix repo root unless noted.
SURFACES: tuple[Surface, ...] = (
    Surface(
        "workspace_documents_pg",
        "store",
        "src/keprix/workspace/documents_pg.py",
        True,
        True,
        "PG documents + document_versions",
    ),
    Surface(
        "workspace_repository_fallback",
        "store",
        "src/keprix/workspace/repository.py",
        True,
        True,
        "In-memory fallback when PG unavailable",
    ),
    Surface(
        "workspace_document_routes",
        "http",
        "src/keprix/workspace/routes/document_routes.py",
        True,
        False,
        "Compatibility adapter target",
    ),
    Surface(
        "frontend_documents",
        "ui",
        "frontend/src/app/(workspace)/documents/page.tsx",
        True,
        False,
        "Becomes primary vault UI in 648",
    ),
    Surface(
        "frontend_files",
        "ui",
        "frontend/src/app/(workspace)/files/page.tsx",
        True,
        False,
        "May redirect to /documents",
    ),
    Surface(
        "admin_host_fs",
        "http",
        "src/keprix/api/fs_routes.py",
        False,
        False,
        "OUT_OF_SCOPE for tenant vault",
    ),
    Surface(
        "chat_files_upload",
        "http",
        "src/keprix/api/conversation_routes.py",
        True,
        True,
        "file_ids upload/open; quarantine before vault import",
    ),
    Surface(
        "knowledge_vault_routes",
        "http",
        "src/keprix/api/knowledge_vault_routes.py",
        True,
        True,
        "Markdown vault files API",
    ),
    Surface(
        "knowledge_vault_local",
        "store",
        "src/keprix/vault/local_folder.py",
        True,
        True,
        "Local folder provider",
    ),
    Surface(
        "credential_vault",
        "store",
        "src/keprix/security/vault_store.py",
        True,
        False,
        "Secrets only; never migrate as documents",
    ),
    Surface(
        "document_agent_indexes",
        "store",
        "src/keprix/documents/index_manager.py",
        True,
        True,
        "Index state migrates to vault-aware jobs",
    ),
    Surface(
        "disk_folder_store",
        "store",
        "src/keprix/documents/disk_folder_store.py",
        True,
        True,
        "Registered roots; not wholesale host browse",
    ),
    Surface(
        "export_tools",
        "tools",
        "src/keprix/export/export_tool.py",
        True,
        False,
        "Export adapter; artifacts may link revisions",
    ),
    Surface(
        "google_drive_tools",
        "tools",
        "src/keprix/tools/google_workspace_tools.py",
        True,
        True,
        "Search today; sync in 649",
    ),
    Surface(
        "syncthing_bridge",
        "integration",
        "src/keprix/sync/syncthing",
        True,
        True,
        "Folder sync bridge",
    ),
    Surface(
        "obsidian_research",
        "integration",
        "src/keprix/research_workspace/obsidian",
        True,
        True,
        "Research Obsidian vaults",
    ),
    Surface(
        "desktop_file_tree",
        "ui",
        "src/keprix/apps/desktop/src/app/right-sidebar/files/tree.tsx",
        False,
        False,
        "Host/project FS; OUT_OF_SCOPE",
    ),
    Surface(
        "tui_file_actions",
        "ui",
        "src/keprix/tui/command_center/palette.py",
        True,
        False,
        "open_file; vault explorer in 648",
    ),
    Surface(
        "agent_vault_tools",
        "tools",
        "src/keprix/tools/vault_tools.py",
        True,
        False,
        "Knowledge vault tools; vault CRUD in 650",
    ),
    Surface(
        "agent_file_tools",
        "tools",
        "src/keprix/tools/file_tools.py",
        True,
        False,
        "Host-oriented file tools; policy in 650",
    ),
    Surface(
        "channel_gateway_docs",
        "gateway",
        "src/keprix/gateway/platforms/base.py",
        True,
        True,
        "Document cache; channel import in 651",
    ),
)
