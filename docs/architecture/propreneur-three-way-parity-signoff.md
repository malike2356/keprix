# Propreneur three-way parity sign-off (CRUD remediation 644)

**Date:** 2026-08-09  
**Programme:** keprix-propreneur-crud-remediation (636-644)  
**Verdict:** CONDITIONAL_GREEN

Local + git + Contabo engine deploy are green. Live Contabo **agent mutation canary** remains owner-gated until `PROPRENEUR_PRODUCT_API_URL` is set on Keprix Contabo and a restricted synthetic tenant run completes.

## Pinned SHAs

| Root | SHA |
| --- | --- |
| Keprix | `de69828ec14518abeb16ee7eb0bcb3ddca3720a5` (includes connector readiness fix) |
| Propreneur | `8d37f4a144538396b5cbc30d54b9a64ed8efc180` |
| Carina twin sync | `72223c181f89987f5d741d2621beca8ea4e7ec1e` |

Immutable manifest: `keprix/docs/operations/propreneur-crud-remediation-release-manifest-644.md`

## Dimension status (READY only from passing evidence)

| Dimension | Status | Evidence |
| --- | --- | --- |
| Engine readiness | READY | Contabo `/v1/products/propreneur/health` ok; loopback + public API 200 |
| CRUD readiness (local) | READY | Harness GREEN; 48 executable capabilities; Pest 14; sidecar 42 |
| CRUD readiness (Contabo live mutate) | OWNER_PENDING | `PROPRENEUR_PRODUCT_API_URL` empty in Keprix Contabo env; connector_configured=false (honest) |
| Domain coverage | READY | Matrix + contract 1.3.0; live/approval_required/forbidden classified |
| Owner-controlled limitations | READY (documented) | Hard delete, vault binary, payment post, outbound send forbidden |
| RAG freshness | READY (local) | 61 curated paths; retrieval tests pass; Contabo reindex owner/ops |
| Deployment parity | READY | Focused commits pushed; Contabo rsync/compose; carinaai.uk 200 |
| Remaining external owner configuration | OPEN | Connector URL + allowlist + restricted synthetic mutation canary + soak |

## Local gates (this session)

- Hygiene: keprix + propreneur OK
- Contract regen `--check` OK
- Keprix focused suites: 42 passed (+ readiness fix 2 passed)
- Pest Aiva matrix/security/API: 14 passed
- Two-process harness: GREEN capabilities=48
- Evidence sha256: see release manifest

## Contabo smoke (post-deploy)

| Check | Result |
| --- | --- |
| https://carinaai.uk/ | 200 |
| https://propreneur.uk/health | 200 |
| https://app.keprixai.com/ + `/api/health` | 200 |
| Keprix loopback `/api/health` | 200 |
| Pack nodes | 58 (live 23, approval_required 25) |
| Readiness honesty | `partial_fail_closed`; executable 48; crud_complete false (3 not_configured) |
| Connector env | Not set (fail closed; do not claim live mutate) |

## Owner follow-up (before general-release READY)

1. Set Contabo Keprix `PROPRENEUR_PRODUCT_API_URL` to the host-local Propreneur base URL that matches connector allowlist (extend allowlist for `propreneur.uk` only if intentionally egressing HTTPS).
2. Restart keprix-backend; confirm readiness `callback_health.connector_configured=true`.
3. Run restricted synthetic tenant canary (non-customer records): create/read/update/archive + Soft Wall + cross-tenant deny + event ack + emergency disable.
4. Soak and keep rollback SHA ready.
5. Optional: Contabo `keprix memory index-self` / Propreneur masterbrain RAG sync.

## Rollback

- Keprix: redeploy prior SHA via Contabo compose; pack disable / kill switches.
- Propreneur: `scripts/rollback-release.sh` / prior SHA redeploy.
- Never-break: `bash docker/scripts/reload-marketing-nginx.sh` from Contabo `core.carinaai.uk` if carinaai.uk != 200.

## Correction vs prior PARTIAL (prompt 636)

Historical engine-only PARTIAL is superseded for **code and local proof**. Marketing and ops must still say Contabo live agent mutate is owner-gated until the connector env and synthetic canary close.
