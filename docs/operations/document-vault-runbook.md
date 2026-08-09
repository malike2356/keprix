# Document Vault operator runbook

Programme close: Prompt 653. Enable runtime only when ready to serve tenants.

## Preconditions

1. `document_vault_ready` is true (default after 653; retract with `KEPRIX_DOCUMENT_VAULT_READY=0`).
2. Migrations applied through Alembic `032_document_vault_search_ops` (and earlier 029-031).
3. Backups cover vault metadata DB + blob root.
4. Do not bridge admin `/api/fs` into the tenant vault.

## Enable path

```bash
# 1) Inventory (read-only)
python -m keprix.document_vault.inventory --workspace-id <ws> --dry-run

# 2) Enable canonical API
# KEPRIX_DOCUMENT_VAULT_ENABLED=1

# 3) Migrate with writers (optional)
# KEPRIX_DOCUMENT_VAULT_MIGRATE=1
# POST /api/document-vault/migrate (workspace-scoped)
# Re-run inventory; compare counts and checksums

# 4) Cutover (stops dual-write)
# KEPRIX_DOCUMENT_VAULT_CUTOVER=1

# 5) Optional Google
# KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC=1
# Bind OAuth grant; prefer webhook on public HTTPS; CE uses poll
```

## Conformance and CE smoke

```bash
PYTHONPATH=src python -m keprix.document_vault.conformance
# Evidence: docs/architecture/evidence/document-vault-conformance-653.json
pytest tests/document_vault/ -q
```

Honesty: Google live OAuth and Telegram delivery stay MANUAL / credential-gated. Do not mark them live without a controlled test account.

## Rollback

| Goal | Action |
| --- | --- |
| Stop serving vault writes | `KEPRIX_DOCUMENT_VAULT_ENABLED=0` |
| Resume dual-write / legacy | `KEPRIX_DOCUMENT_VAULT_CUTOVER=0` |
| Retract ready claim | `KEPRIX_DOCUMENT_VAULT_READY=0` |
| Data | Leave migrated rows; restore from backup if writers corrupted content |

## Diagnostics

- Jobs / dead letters: vault ops APIs (Prompt 652)
- Repair / backup drill: `document_vault.ops`
- Soft Wall queues: CRM Soft Wall surfaces used by agent vault policy
- Cross-tenant: never query items without workspace scope

## Contabo note

Deploying Keprix app containers does not auto-enable Document Vault. Keep `ENABLED=0` until inventory and soak pass on that host. After any Contabo deploy, confirm `https://carinaai.uk/` returns HTTP 200 and Keprix health endpoints respond.
