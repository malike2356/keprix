# Document Vault ownership and migration manifest (Prompt 645)

**Status:** EXECUTABLE PLAN (audit read-only; writers gated by flags)  
**Date:** 2026-08-09

## Current ownership (as-is)

| Concern | Current store / module | Scope key |
| --- | --- | --- |
| Editable doc metadata + body | `documents` PG or `workspace_repo` | `user_id` / workspace |
| Document versions | `document_versions` PG | document id |
| Drafts | Redis / `draft_store` | user + doc |
| Markdown vault files | `keprix.vault.*` + `KEPRIX_VAULT_ROOT` | vault root / pack |
| Credential secrets | `security/vault_*` | **OUT_OF_SCOPE** |
| Document agent indexes | `documents/index_manager` | index id |
| Disk folders | `disk_folder_store` | registered roots |
| Chat uploads | `/api/files/*` | session / file id |
| Export artifacts | `export/*` | job / temp |
| Google Drive | OAuth + `gws_drive_search` | account grant |
| Syncthing / Obsidian | sync + research modules | folder / vault id |
| Gateway attachments | `~/.keprix/cache/documents` | channel cache |
| Host filesystem | `/api/fs` | admin only; **never migrate into tenant vault** |

## Target ownership (to-be)

See `document-vault-contract.md` owners table. One canonical vault service; adapters until cutover.

## Migration map (record types → canonical)

| Source type | Target kind / mapping | Notes |
| --- | --- | --- |
| Workspace document | `markdown` / `rich_document` / `plain_text` by format | Preserve id via mapping row if UUID clash |
| Document version row | Vault revision | Checksum content; order by created_at |
| Repository fallback doc | Same as workspace doc | Migrate when CE uses memory→disk path |
| Knowledge vault `.md` file | `markdown` item under mapped folder tree | Relative path → parents |
| Disk-folder indexed file | `binary_upload` or typed kind + index policy | Do not copy host root wholesale |
| Chat attachment (durable) | `binary_upload` only if user confirmed import | Ephemeral cache stays ephemeral |
| Google Drive mapping | provider_mapping + authority `google` | 649 implements sync |
| Syncthing folder pointer | External folder link / import job | Not automatic host browse |
| Credential vault entries | **skip** | Secrets |
| Host FS paths | **skip / reject** | `host_fs_forbidden` |

## Compatibility adapters (design; 646 implements)

| Caller | Adapter behavior until cutover |
| --- | --- |
| `/api/workspace/documents` | Read/write through vault when ENABLED else legacy |
| `/api/vault/files` | Knowledge vault bridge; map paths to items |
| `/api/documents` indexes | Index vault revisions when enabled |
| `/api/files/upload` | Optional quarantine → vault import Soft Wall |
| Agent `vault_*` / file tools | Prefer vault tools when ENABLED |
| `/api/fs` | Unchanged; never routed through vault |

## Idempotent migration rules

1. Inventory and audit modes **must not** INSERT/UPDATE/DELETE user content.
2. Writers require `KEPRIX_DOCUMENT_VAULT_MIGRATE=1`.
3. Each source row uses idempotency key `migrate:{source_store}:{source_id}`.
4. Verify counts and checksums before flipping `KEPRIX_DOCUMENT_VAULT_CUTOVER`.
5. Retain legacy tables until Prompt 653 evidence + rollback drills pass.

## Rollback plan

| Step | Action |
| --- | --- |
| R1 | Set `KEPRIX_DOCUMENT_VAULT_CUTOVER=0` |
| R2 | Set `KEPRIX_DOCUMENT_VAULT_ENABLED=0` (legacy callers only) |
| R3 | Leave migrated rows in place (no destructive reverse unless owner asks) |
| R4 | Re-run read-only inventory; compare checksum report to pre-cutover baseline |
| R5 | If writers ran incorrectly, restore from backup that includes metadata + blobs + mappings |

## Read-only audit report

```bash
keprix document-vault inventory --workspace-id <ws> --dry-run
# or
python -m keprix.document_vault.inventory --workspace-id <ws> --dry-run
```

Report sections: surfaces present, duplicates (id / checksum), orphans (version without parent, mapping without item), identifier conflicts, content checksum samples, flag snapshot, `mutated=false`.
