# Keprix Document Vault capability matrix (Prompt 645)

**Status:** BASELINE LOCKED  
**Date:** 2026-08-09  
**Series:** `keprix-document-vault` (645-653)  
**Shared behavioral contract:** `/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-DOCUMENT-VAULT.md`

Classification: **REAL** | **PARTIAL** | **SIMULATED** | **MANUAL** | **MISSING** | **BLOCKED_OPTIONAL_CREDENTIALS** | **OUT_OF_SCOPE**

Honesty rule: UI presence alone never marks REAL for the canonical Document Vault. Conformance: `tests/document_vault/test_contract_conformance.py`. Admin host filesystem is **OUT_OF_SCOPE** for the tenant vault.

## Naming trap (do not merge)

| Surface | What it is |
| --- | --- |
| Credential vault (`/vault`, `security/vault_*`) | Encrypted secrets |
| Markdown knowledge vault (`/api/vault/files`, `keprix.vault.*`) | Local markdown notes root |
| Workspace documents (`/api/workspace/documents`) | Editable docs + versions |
| Document agent indexes (`/api/documents`) | RAG indexes + disk folders |
| Host FS browser (`/api/fs`, `/files` admin mode) | Admin-only machine paths |
| **Document Vault (this programme)** | Tenant virtual FS; Keprix-native; no Carina |

## Current surface inventory

| Capability / path | Class | Evidence |
| --- | --- | --- |
| Workspace documents PG + versions | REAL | `workspace/documents_pg.py`, `document_versions` |
| Workspace documents in-memory fallback | REAL | `workspace/repository.py` when PG off / pytest |
| Workspace document HTTP | REAL | `workspace/routes/document_routes.py` |
| Frontend `/documents` | REAL | Document Vault explorer primary; legacy docs tab retained |
| Frontend `/files` | REAL | Defaults to Document Vault; `?mode=host` admin host FS |
| Admin host FS `/api/fs` | OUT_OF_SCOPE | `api/fs_routes.py`; stay separate forever |
| Sandboxed `/api/files/upload|open` | REAL | Chat attachment path; migrate via adapters |
| Markdown knowledge vault | PARTIAL | `api/knowledge_vault_routes.py`, `vault/*` |
| Credential vault | OUT_OF_SCOPE | Secrets module; not document content |
| Document agent indexes | PARTIAL | `documents/index_manager.py`, query/extract |
| Disk folder registry | PARTIAL | `documents/disk_folder_store.py` |
| Chat attachments | PARTIAL | `conversation_routes` file_ids |
| Export tools | PARTIAL | `export/*`, workspace export helpers |
| Google Drive tools | PARTIAL | `gws_drive_search` only; full sync is 649 |
| Syncthing bridge | PARTIAL | `sync/syncthing`, `syncthing_vault` tool |
| Obsidian / research vault | PARTIAL | `research_workspace/obsidian*` |
| Desktop file tree | OUT_OF_SCOPE | Host/project FS via `/api/fs`; vault tab is separate tenant UI |
| Desktop Document Vault tab | REAL | Right sidebar mode toggle; tenant API only |
| TUI recent file actions | PARTIAL | Host/path open_file remains |
| TUI Document Vault | REAL | Palette + `/vault` slash; browse/CRUD/export; `/vault sync` status (649) |
| Agent file tools | REAL | Host `file_tools` stay host-only; legacy `vault_tools` redirect when DV on |
| Channel gateway document cache | REAL | Gateway cache + `document_vault/channel` import/export contract (651) |
| Canonical Document Vault service | REAL | `document_vault.store` + `service` + `/api/document-vault/*` (646); flags default off |
| Vault tree + revisions APIs | REAL | Parent tree, trash/restore, optimistic revisions, audit, jobs |
| Local CE + optional object storage | REAL | `LocalStorageAdapter`; S3 adapter when bucket configured |
| Migration (workspace docs / knowledge vault) | REAL | Idempotent writers gated by `KEPRIX_DOCUMENT_VAULT_MIGRATE` |
| Format engines / PDF pipeline | REAL | Registry + safety + engines; PDF artifact revision-linked; CE MD/HTML/TXT/CSV/PDF |
| Document Vault UI explorer | REAL | Web explorer + desktop vault tab + TUI `/vault` (648) |
| Google Drive OAuth sync/push | REAL | Encrypted grants + reconciler + webhook/poll (649); Shared Drives gated |
| Document Vault agent tools | REAL | `document_vault_*` toolset; trusted session context (650) |
| Vault Soft Wall agent policy | REAL | Rule of Two via CRM Soft Wall for delete/share/bulk/conflict/classified export (650) |
| Channel / Telegram vault ops | REAL | Binding + `/vault` slash + import quarantine/dedup + attach/URL export (651) |
| Search/RAG/security ops | PARTIAL | Existing indexes; 652 consolidates |
| E2E package + deploy close | MISSING | Prompt 653 |

## Build order

| Prompt | Focus |
| --- | --- |
| 645 | This matrix + contract + inventory audit + conformance (no data mutation); **COMPLETED** |
| 646 | Canonical tree storage, revisions, migration writers; **COMPLETED** |
| 647 | Format engines, import/export, PDF; **COMPLETED** |
| 648 | Web, desktop, TUI explorer; **COMPLETED** |
| 649 | Google Drive OAuth sync and push; **COMPLETED** |
| 650 | Agent tools, policy, approvals; **COMPLETED** |
| 651 | Channel and Telegram vault operations; **COMPLETED** |
| 652 | Search, RAG, security, operations |
| 653 | E2E, packaging, docs, deploy; flip `document_vault_ready` |

## Community Edition constraints

- Local SQLite/filesystem adapters must work offline without Google, Carina, or paid object storage.
- Missing Google credentials yield `not_configured` / BLOCKED_OPTIONAL_CREDENTIALS, never fake success.
- `KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE` is permanently false.

## Test commands

```bash
cd /opt/lampp/htdocs/verlox/keprix
./.venv/bin/python -m pytest tests/document_vault -q
./.venv/bin/python -m keprix.document_vault.inventory --workspace-id local --dry-run
```
