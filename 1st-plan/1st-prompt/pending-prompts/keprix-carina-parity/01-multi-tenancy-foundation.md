# Prompt 404 / 01: Multi-tenancy foundation

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 403 / 00  
Blocks: 405  
Severity: CRITICAL  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina ships SaaS subdomain + database-per-tenant isolation. Keprix still largely has user/workspace stubs (`X-Keprix-Tenant` hints exist) without a first-class tenant product model. Blocks honest SaaS deploy.

## Goal

Introduce a durable Keprix tenant model (create/list/switch), resolution (header + optional subdomain), and data-dir/DB scoping contract without requiring a full DB-per-tenant cutover on day one.

## Baseline (Carina)

Canonical Carina only under `carina/02-backends/` and `carina/03-frontends/`. Study tenant resolution, demo reset patterns, and isolation boundaries; map to Keprix workspace/auth rather than forking Laravel.

## Must-haves

1. Tenant entity + store (JSON or Postgres) with id, slug, display_name, owner_user_id, status.
2. API: create/list/get/update (admin/owner gated).
3. Request context: `ProductContext.tenant_id` reliably set from auth session and/or `X-Keprix-Tenant`.
4. Docs: `docs/features/multi-tenancy.md` with migration path toward stronger isolation (02).
5. Tests for resolution and CRUD isolation of tenant records.

## Nice-to-haves

1. Subdomain resolution behind env flag.
2. Demo tenant reset (Carina-inspired) for CE demos.

## Acceptance

- [x] Two tenants cannot share the same slug.
- [x] Authenticated requests attach tenant_id when membership exists.
- [x] Writing-style clean; no secrets.
