# PostgreSQL Tenant RLS Inventory

This is the review artifact for migration `040_postgres_tenant_rls`. The
migration queries `information_schema.columns` after all prior migrations and
applies a policy to every public table with one of the canonical scope columns.
The catalog query is the authoritative exhaustive check; the groups below make
the current product inventory reviewable in source control.

| Scope rule | Current table families | Predicate |
| --- | --- | --- |
| Direct `tenant_id` | `control_plane_memberships` | `tenant_id = current_setting('app.current_tenant_id', true)` |
| Workspace mapped to tenant | `crm_*`, `outreach_*`, `aiva_*`, `concierge_*`, `document_vault_*`, `vical_*`, `audience_*`, `worker_knowledge_*`, `keprix_scout_*`, `keprix_kill_switches`, `mutation_events`, `system_prompt_versions`, `localization_*`, `llm_usage_*`, `generation_log`, `developer_api_keys`, `billing_*` where `workspace_id` exists | A matching `control_plane_workspaces.workspace_id` has the current tenant |
| User mapped to tenant | `memories`, `memory_entities`, `memory_relations`, `memory_conflicts`, `memory_dream_runs`, `emails`, `contacts`, `channel_shield_*`, `vault_items`, `billing_*` where only `user_id` exists, and other catalog tables with `user_id` | A matching `control_plane_memberships.user_id` has the current tenant |
| Platform-global and excluded | `control_plane_tenants`, `users`, `schema_migrations`, `alembic_version` | Deliberately global; tenant registry and migration metadata are not customer rows |

The migration does not equate `user_id` with `tenant_id`. User-scoped tables
use the membership mapping. Workspace-scoped tables use the workspace-to-tenant
mapping. Tables containing both columns use the direct `tenant_id` rule first,
because it is the explicit row owner.

Every discovered tenant-bearing table is `ENABLE`d and `FORCE`d for RLS. The
policy uses `NULLIF(current_setting('app.current_tenant_id', true), '')`, so a
missing setting produces no matching rows and rejects writes. Prompt 014 must
set this value with `SET LOCAL` inside every application transaction.

Before production use, run the catalog audit below as the non-owner app role
and compare the result with this file:

```sql
SELECT table_name, string_agg(column_name, ',' ORDER BY column_name) AS scope_columns
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name IN ('tenant_id', 'workspace_id', 'user_id')
GROUP BY table_name
ORDER BY table_name;
```

The migration is intentionally not wired to live traffic by itself. It is a
schema change only. Prompt 014 owns transaction context injection, and prompt
015 owns data cutover and production enablement.
