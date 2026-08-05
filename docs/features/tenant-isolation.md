# Tenant isolation (CE compatible)

Default CE tenant is `local`. Isolation is on (`KEPRIX_TENANT_ISOLATION=1`).

Legacy rows without `tenant_id` soft-pass so upgrades do not break unless
`KEPRIX_TENANT_ISOLATION_STRICT=1`. New writes stamp the active `ProductContext.tenant_id`.

Cross-tenant get on viCal bookings, calendar events, and contacts fails closed.

IsolationMiddleware resolves Bearer/cookie session users before route Depends so
membership-aware tenant resolution works.

See `docs/features/multi-tenancy.md`.
