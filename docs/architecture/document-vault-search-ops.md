# Document Vault search, RAG, security, and operations (Prompt 652)

Content indexing is opt-in via `index_policy` (`index` / `skip` / `inherit`). Root `inherit` resolves to **skip** so private files are never auto-indexed.

## Packages

| Area | Path |
| --- | --- |
| Policy + indexer + retrieval | `src/keprix/document_vault/search/` |
| Grants + SSRF | `src/keprix/document_vault/security/` |
| Jobs, diagnostics, repair, backup | `src/keprix/document_vault/ops/` |

## Retrieval

- Metadata search remains `GET /api/document-vault/items?q=` / `document_vault_search`
- Content search: `GET /api/document-vault/search?mode=content&q=` returning revision citations `{item_id, revision, name, snippet, source_id}`
- Trash, skip policy, and stale revisions are excluded
- Agent grants: `vault.search` required when grants are explicit

## Jobs

Durable `document_vault_jobs` lifecycle: `queued` → `running` → `completed` / requeue / `dead_letter`. Operators:

- `POST /api/document-vault/ops/jobs/drain`
- `POST /api/document-vault/ops/jobs/{id}/retry`
- `GET /api/document-vault/ops/diagnostics`
- `POST /api/document-vault/ops/repair/orphans`
- `POST /api/document-vault/items/{id}/reindex`
- `POST /api/document-vault/ops/backup`

## Security

- Existing MIME sniff / macros / HTML sanitize / Soft Wall retained
- SSRF guard for URL fetch (`assert_safe_fetch_url`)
- Prompt-injection control lines stripped from indexed text
- Threat tests in `tests/document_vault/test_search_rag_ops.py`

## Backup

Workspace pack includes items, revisions, audit, index entries, and sqlite copy; restore drill verifies counts.

## Flags

Requires `KEPRIX_DOCUMENT_VAULT_ENABLED=1`. Indexing still opt-in per item/folder policy.
