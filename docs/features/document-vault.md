# Document Vault

Tenant Document Vault is the canonical folder and document manager for Keprix (programme 645-653). It is **not** the markdown knowledge vault (`docs/features/vault.md`), **not** the credential vault, and **not** the admin host filesystem browser (`/api/fs`).

## Status

- `document_vault_ready`: **true** (Prompt 653 programme close)
- Runtime default: `KEPRIX_DOCUMENT_VAULT_ENABLED=0` until operators opt in
- No Carina runtime dependency; Community Edition works offline with local SQLite + disk blobs
- Google Drive and Telegram live delivery need credentials; absence is not a product failure

## Enable

```bash
# .env
KEPRIX_DOCUMENT_VAULT_ENABLED=1
# Optional migration writers after inventory:
# KEPRIX_DOCUMENT_VAULT_MIGRATE=1
# After checksum soak, stop dual-write:
# KEPRIX_DOCUMENT_VAULT_CUTOVER=1
# Optional Google / channel:
# KEPRIX_DOCUMENT_VAULT_GOOGLE_SYNC=1
# Emergency retract of ready claim only:
# KEPRIX_DOCUMENT_VAULT_READY=0
```

Host FS bridge is forced off. Never set a bridge flag expecting tenant vault access to `/api/fs`.

## Surfaces

| Surface | Entry |
| --- | --- |
| HTTP | `/api/document-vault/*` |
| Web | `/documents`, `/files` (vault mode; `?mode=host` is admin FS) |
| Desktop | Right sidebar Document Vault tab |
| TUI | Palette + `/vault` slash |
| Agent | `document_vault_*` tools; Soft Wall for delete/share/bulk/conflict/classified export |
| Channel | Telegram `/vault` when channel ops enabled |
| CLI | `python -m keprix.document_vault.inventory` / `conformance` |

## Local vs server sync

| Mode | Behavior |
| --- | --- |
| Community Edition / local | Local storage adapter; SQLite metadata; Google uses poll when sync enabled |
| Server (Postgres) | Alembic vault tables; optional S3/object storage; Google webhook when HTTPS + grant present |
| Interruption | Reconciler is idempotent; resume from mapping cursors; conflicts preserve-both |

## Optional dependencies

| Dependency | Required for CE? | Notes |
| --- | --- | --- |
| PostgreSQL | No | Auto when `KEPRIX_DATABASE_URL` works |
| Object storage | No | Local disk default |
| Google OAuth | No | `BLOCKED_OPTIONAL_CREDENTIALS` without grant |
| Telegram bot | No | Channel ops MANUAL without tokens |
| Carina | Never | Import scan forbids Carina in `document_vault` |

## Soft Wall

Permanent delete, public share, bulk mutate, conflict overwrite, and classified export require Soft Wall (or privileged UI). See `docs/architecture/document-vault-agent-tools.md`.

## Operator runbook

See [Document Vault runbook](../operations/document-vault-runbook.md).

## Architecture

- Contract: `docs/architecture/document-vault-contract.md`
- Matrix: `docs/architecture/document-vault-capability-matrix.md`
- Evidence: `docs/architecture/evidence/document-vault-conformance-653.json`
- Shared behavioral contract: `/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-DOCUMENT-VAULT.md`
