# Tenant isolation (CE compatible)

Default CE tenant is `local`. Isolation is on (`KEPRIX_TENANT_ISOLATION=1`).

Legacy rows without `tenant_id` soft-pass so upgrades do not break unless
`KEPRIX_TENANT_ISOLATION_STRICT=1`. New writes stamp the active `ProductContext.tenant_id`.

Cross-tenant get on viCal bookings, calendar events, and contacts fails closed.

IsolationMiddleware resolves Bearer/cookie session users before route Depends so
membership-aware tenant resolution works.

## Database-level enforcement (PostgreSQL)

On PostgreSQL, isolation is not only application-level: migration
`040_postgres_tenant_rls` discovers every tenant-bearing table (by
`tenant_id`, `workspace_id`, or `user_id` column) and applies a `FORCE ROW
LEVEL SECURITY` policy scoped to `current_setting('app.current_tenant_id')`.
Every ORM session (`TenantAsyncSession`, `src/keprix/db/tenant_session.py`)
sets that value from the request's `ProductContext` on first query in a
transaction, so a query that somehow bypassed the application-level checks
above still cannot read or write another tenant's rows at the database
layer. See `docs/security/postgres-tenant-rls-inventory.md` for the full
table inventory and predicate rules.

See `docs/features/multi-tenancy.md`.
