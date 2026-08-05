# Tenant isolation

assert_tenant_owns fails closed when resource.tenant_id and context.tenant_id both exist and differ.
Legacy rows without tenant_id soft-pass so CE upgrades keep working.

Applied on viCal bookings/event types and contacts list/get.
Disable only for recovery with KEPRIX_TENANT_ISOLATION=0.
