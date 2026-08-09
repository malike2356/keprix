# Standalone lead outreach durable storage (Prompt 622)

## Backends

| Mode | Backend | When |
| --- | --- | --- |
| Community / local | SQLite under `data_dir()/crm` and `data_dir()/outreach` | Default under pytest; CE when Postgres is unreachable |
| Hosted | PostgreSQL via `KEPRIX_DATABASE_URL` | `KEPRIX_CRM_BACKEND=postgres` or `auto` outside pytest when Postgres connects |

Selector: `keprix.crm.durable.resolve_crm_backend` (re-exported as `keprix.outreach.durable`).

## Env

| Variable | Meaning |
| --- | --- |
| `KEPRIX_CRM_BACKEND` | `auto` (default), `sqlite`, or `postgres` |
| `KEPRIX_CRM_DB_PATH` | Optional SQLite file override for CRM |
| `KEPRIX_DATABASE_URL` | Shared async Postgres URL (`postgresql+asyncpg://...`) |
| `KEPRIX_CRM_FORCE_PG` | `1` forces Postgres under pytest / auto |
| `KEPRIX_TEST_DATABASE_URL` | Optional test DB URL for durable tests |

CRM and outreach use the same selector. Runtime schema uses **TEXT** primary keys (not UUID). Alembic `028_crm_durable_storage` creates CRM tables and replaces unused UUID outreach tables from `024` with TEXT-id tables. Every outreach table includes `workspace_id`.

## Migration CLI

```bash
keprix crm-migrate --dry-run
keprix crm-migrate --apply
# or
python -m keprix.crm.migrate_sqlite_to_pg --dry-run
python -m keprix.crm.migrate_sqlite_to_pg --apply
```

Apply steps:

1. Zip backup of `data_dir()/crm` and `data_dir()/outreach`
2. Per-table row counts and sha256 of sorted ids per workspace
3. Upsert copy in FK-safe order inside transactions (idempotent by primary key)
4. Reconcile counts; fail if Postgres has fewer rows than SQLite

## Rollback

1. Set `KEPRIX_CRM_BACKEND=sqlite`
2. Restore the backup zip into `data_dir()`
3. Restart Keprix

## Contabo / hosted note

After deploying this revision, run Alembic upgrade through `028_crm_durable_storage` on the hosted database before enabling `KEPRIX_CRM_BACKEND=postgres` (or relying on `auto` outside pytest).
