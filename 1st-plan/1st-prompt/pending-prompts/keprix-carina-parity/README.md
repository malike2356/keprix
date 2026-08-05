# Keprix: close Carina/Aiva parity gaps (inbound)

**Updated:** 2026-08-04  
**Status:** PENDING (programme)  
**Keprix IDs:** 403-415  
**Source gap doc:** `/opt/lampp/htdocs/verlox/archive/keprix-carina-parity-gap-2026-07-30.md`  
**Archive ref:** `../prompts-archive/ref-403-keprix-carina-parity-build-order.md`  
**Sister programme (Carina inbound):** `carina/01-devends/prompts-library/01-pending_prompts/carina-keprix-parity/`

## Problem

The 2026-07-30 parity analysis shows Carina still leads on multi-tenancy, governance/compliance, Scout Warden depth, production domain packs, and some product tooling. Keprix has since closed parts of the AI-security gap (372-375) and shipped viCal + capability mesh, but SaaS-blocking stubs remain.

## Already shipped (do not redo)

| Item | Evidence |
|---|---|
| Fail-closed prompt guard / ACL / RAG poison / Rule of Two health | prompts-archive 372-375 |
| viCal booking + calendar bridge | 376-388 |
| Capability mesh + Telegram pilot tools | 389-402 |
| Companies House tools in core | toolsets + Research UI |

## Build order

| ID | File | Severity | Status |
|---|---|---|---|
| 403 / 00 | `00-overview-and-stale-gap-refresh.md` | - | PENDING |
| 404 / 01 | `01-multi-tenancy-foundation.md` | CRITICAL | PENDING |
| 405 / 02 | `02-tenant-isolation-enforcement.md` | CRITICAL | PENDING |
| 406 / 03 | `03-governance-gdpr-rbac.md` | HIGH | PENDING |
| 407 / 04 | `04-ai-security-hardening-beyond-372.md` | HIGH | PENDING |
| 408 / 05 | `05-scout-warden-integration.md` | HIGH | PENDING |
| 409 / 06 | `06-domain-pack-library.md` | MEDIUM | PENDING |
| 410 / 07 | `07-product-tools-layer.md` | MEDIUM | PENDING |
| 411 / 08 | `08-rag-admin-and-training.md` | MEDIUM | PENDING |
| 412 / 09 | `09-self-knowledge-depth.md` | MEDIUM | PENDING |
| 413 / 10 | `10-billing-promo-trial-byok.md` | LOW | PENDING |
| 414 / 11 | `11-conditional-workflows.md` | LOW | PENDING |
| 415 / 12 | `12-cicd-security-workflows.md` | LOW | PENDING |

## Non-goals

- Nesting `carina/verlox/`.
- Copying property/CRM/accounting journals blindly into Keprix.
- New Stripe prices without owner ask.
- Re-implementing 372-375 from scratch.

## Carina reference paths (canonical only)

| Area | Path |
|---|---|
| Tenant isolation | `/opt/lampp/htdocs/verlox/carina/02-backends/core.carinaai.uk/src/security/tenant-isolation.ts` |
| Tenant docs | `/opt/lampp/htdocs/verlox/carina/02-backends/core.carinaai.uk/docs/TENANT-ISOLATION.md` |
| Ops tenants | `/opt/lampp/htdocs/verlox/carina/02-backends/admin/ops.carinaai.uk/lib/tenants.ts` |
| Tenant provisioning | `/opt/lampp/htdocs/verlox/carina/02-backends/admin/ops.carinaai.uk/lib/tenant-provisioning.ts` |
| BYOK | `/opt/lampp/htdocs/verlox/carina/02-backends/admin/ops.carinaai.uk/lib/tenant-byok.ts` |
| Scout / Warden product | Labyrinth Scout via Carina extensions / ops (never nest `carina/verlox/`) |

## Progress

- [x] 00 overview / stale gap refresh (archive status map 2026-08-04)
- [x] 01 multi-tenancy foundation
- [x] 02 tenant isolation
- [x] 03 governance
- [x] 04 AI security beyond 372
- [x] 05 Scout Warden
- [x] 06 domain packs
- [x] 07 product tools
- [x] 08 RAG admin
- [x] 09 self-knowledge
- [x] 10 billing promo/BYOK
- [x] 11 conditional workflows
- [x] 12 CI workflows


## Deepen pass (2026-08-04)

First YOLO landed thin adapters in places. Follow-up removed theatre:

- RAG admin -> real `rag_pipeline`
- Governance DSAR -> privacy fulfill/erase
- Booking confirmed -> real lead create/link
- Promo -> checkout `promo_code` + trial override
- BYOK -> AES-GCM
- Canary -> `build_system_prompt_parts`
- Scout alerts -> `scout` signal_log
- Packs -> registered tools + thicker guides

## Writing / security

Plain ASCII only. Secrets stay in `/opt/lampp/htdocs/verlox/.access/`.

## Stub-closure pass (2026-08-04)

Closed residual theatre: middleware session user, PG memberships, calendar tenant stamps,
canary egress scrub, privacy-backed DSAR UI, Scout/tenants/leads pages, promo checkout field,
public `/v1/tools` dispatch, durable `/v1/tasks`, real `/api/files/open`, JSON quota persistence.
