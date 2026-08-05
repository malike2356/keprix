# Tenancy overview

Keprix tenants have id, unique slug, display_name, owner_user_id, and status.
Default CE tenant is `local`.

API:
- GET/POST /api/tenants (admin)
- GET /api/tenants/me
- PATCH /api/tenants/{id}
- POST /api/tenants/{id}/memberships

Resolution order for ProductContext.tenant_id:
1. X-Keprix-Tenant header (id or slug) when membership allows
2. Subdomain when KEPRIX_TENANT_SUBDOMAIN=1
3. User default_tenant_id / first membership
4. KEPRIX_TENANT_ID or local

Storage: JSON under data_dir/tenancy by default; Postgres control_plane_tenants when DB is configured (pytest forces JSON).
