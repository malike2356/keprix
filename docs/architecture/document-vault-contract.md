# Keprix Document Vault service contract (Prompt 645)

**Status:** DOMAIN IMPLEMENTED (Prompt 646); UI/sync/agent/channel remain later prompts  
**Contract version:** `1.0.0`  
**Schema:** `schemas/document-vault/contract.schema.json`  
**Shared behavioral source:** `shared/workspace-governance/AIVA-KEPRIX-DOCUMENT-VAULT.md`

## Product identity

| Field | Value |
| --- | --- |
| Product | `keprix` |
| `carina_runtime_required` | **false** |
| Aiva relationship | Same behavioral contract; Aiva runs on Carina; Keprix is native |
| Community Edition | Full local vault without Google or Carina |

Keprix must never import Carina packages, call Carina HTTP as a required dependency, or fail to start when Carina is absent.

## Canonical owners (target)

| Concern | Owner (target after 646+) |
| --- | --- |
| Item metadata + hierarchy | Keprix Document Vault DB (`document_vault_*`) |
| Binary / blob content | Storage adapter (local CE dir or object storage) |
| Revisions | Vault revision table; immutable history |
| Jobs | Durable job runner (convert, index, sync, watch renew) |
| Provider mappings | Vault provider_mapping rows (Google revision tokens) |
| Index state | Vault-aware index jobs; versioned retrieval entries |
| Audit | Immutable vault audit log |

Current (pre-646) owners are listed in `document-vault-ownership-and-migration.md`. Compatibility adapters keep existing callers working until cutover.

## Item model (required)

Stable ID, workspace ID, parent ID, kind, name, normalized MIME, extension, content authority (`workspace` | `google`), storage locator, byte size, checksum, current revision, creator/updater, timestamps, favorite, trash, index policy, classification, optional provider mapping.

Required kinds: folder, rich_document, spreadsheet, presentation, markdown, html, plain_text, pdf, binary_upload.

## Boundaries

1. Tenant Document Vault is **not** the admin host filesystem (`/api/fs`).
2. Credential vault remains secrets-only.
3. Markdown knowledge vault and workspace documents migrate via the 645 manifest; they are not a fourth parallel store after cutover.
4. Agents use vault tools only (Prompt 650); no raw SQL or host paths for tenant content.
5. Public share / permanent delete / conflict overwrite require Soft Wall or privileged UI.

## Feature flags

| Flag | Default | Role |
| --- | --- | --- |
| `KEPRIX_DOCUMENT_VAULT_ENABLED` | `0` | Canonical service on |
| `KEPRIX_DOCUMENT_VAULT_MIGRATE` | `0` | Allow migration writers (646+) |
| `KEPRIX_DOCUMENT_VAULT_CUTOVER` | `0` | Retire adapters after evidence |
| `KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE` | `0` (forced) | Never bridge host FS into vault |

## Readiness

`document_vault_ready` stays **false** until Prompt 653. Prompt 645 only locks inventory, contract, flags, read-only audit, and conformance.

## Error codes

`not_configured`, `workspace_mismatch`, `soft_wall_required`, `conflict`, `stale_revision`, `cycle_rejected`, `path_traversal`, `quota_exceeded`, `host_fs_forbidden`, `idempotent_replay`, `unsupported_kind`.

## Rollback criteria (programme)

Roll back cutover if any of: content checksum mismatch after migrate, orphan mappings > threshold, workspace isolation failure, host FS bridge detected, Carina import regression in vault package, or Community Edition offline start fails.
