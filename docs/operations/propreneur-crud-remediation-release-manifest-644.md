# Propreneur Keprix CRUD remediation — immutable release manifest (prompt 644)

**Date:** 2026-08-09  
**Programme:** keprix-propreneur-crud-remediation (636-644)  
**Writing style:** plain ASCII only.

Fill SHAs after focused commits land on `origin/main`. Do not paste secrets.

## Identity

| Field | Value |
| --- | --- |
| Product pair | Keprix product pack `propreneur` + Propreneur Aiva v1 |
| Keprix pack id | propreneur-sidecar |
| Contract | `propreneur-agent-capabilities` **1.3.0** |
| Feature flag | `product.propreneur.sidecar` |
| Memory namespace | `product:propreneur` |

## Git pins (immutable)

| Root | Branch | SHA | Notes |
| --- | --- | --- | --- |
| `keprix/` | main | `528188ac94c62de4dbc804e7a85fc163a012aa22` | Product pack + Soft Wall + readiness UI/docs |
| `propreneur/` | main | `8d37f4a144538396b5cbc30d54b9a64ed8efc180` | Aiva v1 CRUD + Pest matrix + brain knowledge |
| `carina/` (generated twins) | main | `72223c181f89987f5d741d2621beca8ea4e7ec1e` | `propreneur-aiva-tools.v1.json` + result envelope only |

## Evidence hashes (no tenant PII)

| Artefact | Path | sha256 |
| --- | --- | --- |
| E2E evidence | `keprix/docs/architecture/propreneur-e2e-evidence.v1.json` | `51216d434d6a361ca559f0b912c3df52a3006051cf996cb056617812ecaf1377` |
| RAG reindex counts | `keprix/docs/architecture/propreneur-rag-reindex-evidence.v1.json` | `7e90f84b59bb19e4f06c4c450c2df551201914955dc003777d9e49804919ea3e` |
| Capabilities contract | `keprix/domain-packs/propreneur/contracts/propreneur-agent-capabilities.v1.json` | `27da7b14a1d8cb37738c67a3c3fb6236cb9d9329664f5df4c2855ac6aca26e13` |

## Local validation (this session)

| Gate | Result |
| --- | --- |
| Public GitHub hygiene (`keprix`, `propreneur`) | OK |
| Contract regen `--check` | OK (v1.3.0; 69 ops / 48 executable HTTP) |
| Keprix focused product_sidecar + self_knowledge | 42 passed |
| Domain-pack `test_contract_load` | 3 passed |
| Pest Aiva matrix + security + API | 14 passed |
| Two-process harness `propreneur-e2e-harness.sh` | GREEN; capabilities=48 |
| Self-knowledge curated paths present | 61 / 61 |

## Migrations

Additive only. List applied on Contabo during deploy (fill from `php artisan migrate --pretend` / remote migrate output):

- Propreneur: Aiva/Keprix ledger and related migrations already shipped in prior RCs; this release is primarily Aiva v1 controller/surface + config catalogue.
- Keprix: no SQL migrations; Soft Wall / receipts under `KEPRIX_DATA_DIR/product_sidecar/`.

## Configuration names (values in vault / `.env` only)

- `PROPRENEUR_PRODUCT_API_URL`
- `KEPRIX_DISABLE_SHARED_COMPAT_TOKEN` (prefer `1` when grants are live)
- `product.propreneur.sidecar` / pack enable
- Aiva grant bundles: `read_only`, `operational_crud`
- Contabo Keprix loopback: `http://127.0.0.1:13333`

## Rollback points

| Layer | Action |
| --- | --- |
| Pack / Soft Wall | Disable pack; `force_carina` / outbound kill; preserve receipts |
| Keprix app | Redeploy previous Keprix SHA via Contabo compose |
| Propreneur app | `bash scripts/rollback-release.sh` / redeploy previous SHA |
| Migrations | Do not destructive-rollback until compatibility proven |
| Contabo never-break | Repair `carinaai.uk` with `reload-marketing-nginx.sh` if 403 |

## Canary sequence ( Contabo )

1. Shadow / emergency-safe: confirm readiness API; do not equate connectivity with CRUD.
2. Read-only canary on restricted tenant grant.
3. Owner-approved synthetic CRUD (create/read/update/archive) on non-customer records only.
4. Prove Soft Wall approval path, cross-tenant denial, event ack, fallback disable.
5. Soak; roll back on auth, integrity, duplicate mutation, or reconcile failure.

## Pre-deploy public health (baseline)

| URL | Code |
| --- | --- |
| https://carinaai.uk/ | 200 |
| https://propreneur.uk/health | 200 |
| https://app.keprixai.com/ | 200 |
| https://app.keprixai.com/api/health | 200 |
| Contabo Keprix loopback `/api/health` | 200 |

## Final status fields (fill after live)

| Dimension | Status |
| --- | --- |
| Engine readiness | PENDING_LIVE |
| CRUD readiness | PENDING_LIVE (local evidence GREEN) |
| Domain coverage | LIVE + APPROVAL_REQUIRED per matrix; forbidden explicit |
| Owner-controlled limitations | Hard delete, vault binary, payment post, outbound send |
| RAG freshness | Local docs/tests green; live reindex owner/ops |
| Deployment parity | PENDING after push+deploy |
| Remaining external owner configuration | Restricted live mutation canary tenant + soak window |

## Sign-off

Extracted by agent session 2026-08-09; owner review required for live mutation canary and soak close.
