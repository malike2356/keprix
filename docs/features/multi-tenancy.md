# Multi-tenancy

Status: foundation (JSON + Postgres when configured).

## Model

- Tenant: `id`, `slug` (unique), `display_name`, `owner_user_id`, `status`
- Membership: `tenant_id`, `user_id`, `role` (owner/admin/member/viewer)
- Default CE tenant: `local`

## Resolution

`ProductContext.tenant_id` is set by IsolationMiddleware:

1. `X-Keprix-Tenant` (id or slug) when membership allows
2. Subdomain when `KEPRIX_TENANT_SUBDOMAIN=1`
3. User `default_tenant_id` / first membership
4. `KEPRIX_TENANT_ID` or `local`

## API

- `GET/POST /api/tenants` (admin)
- `GET /api/tenants/me`
- `PATCH /api/tenants/{id}`
- `POST /api/tenants/{id}/memberships`

## Isolation path

Day-one: shared DB/JSON with `tenant_id` stamps and `assert_tenant_owns`.

Later: stronger planes (per-workspace data dirs, optional DB schemas) without rewriting agents.

## CE compatibility

Single-tenant CE needs no config. Isolation soft-passes legacy rows missing `tenant_id`.
Disable with `KEPRIX_TENANT_ISOLATION=0` only for recovery.

## Carina references (canonical)

- `/opt/lampp/htdocs/verlox/carina/02-backends/core.carinaai.uk/src/security/tenant-isolation.ts`
- `/opt/lampp/htdocs/verlox/carina/02-backends/core.carinaai.uk/docs/TENANT-ISOLATION.md`
