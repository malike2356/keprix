# Propreneur Keprix product sidecar

**Status:** pack registered; engine connectivity built; domain CRUD live for reads and Soft Wall for writes (prompts 636-643)
**Contract version:** see pack `contract_version` / capabilities contract `1.3.0`
**Writing style:** plain ASCII only.
**Canonical Propreneur root:** `/opt/lampp/htdocs/verlox/propreneur` (not `propreneur/propreneur-v2`).

## Architecture

Keprix hosts the Propreneur product pack under the shared multi-product sidecar
foundation (`src/keprix/product_sidecar/`). Propreneur remains the authorization
and data authority. Keprix advertises capability nodes, enforces Soft Wall and
idempotency, and calls allowlisted Propreneur `/api/aiva/v1` routes with
`TrustedExecutionContext`.

```
Propreneur (Laravel)  --events/ack-->  Keprix product connector
        ^                                         |
        |                                         v
   Soft Wall / Aiva grants              /v1/products/propreneur/*
```

Safe full CRUD means domain API access under Soft Wall and grants. It does **not**
mean unrestricted database access, hard delete, binary vault I/O, payment posting,
or a generic HTTP proxy.

Pack sources:

- Nodes: `src/keprix/product_sidecar/packs/propreneur.py` + `packs/propreneur_ops.py`
- Registry: `build_propreneur_pack()` in `registry.py`
- Honesty: `src/keprix/product_sidecar/honesty.py`
- Readiness: `src/keprix/product_sidecar/readiness.py` → `GET .../readiness`
- Operator UI: `/settings/sidecars/propreneur`
- Contract: `domain-packs/propreneur/contracts/propreneur-agent-capabilities.v1.json`
- Matrix: `propreneur/docs/aiva/CRUD-COVERAGE-MATRIX.md`
- Gap report (history): `docs/architecture/propreneur-crud-remediation-gap-report.md`

Memory namespace is always `product:propreneur`. Cross-product node composition
fails closed.

## Capability honesty (current)

| Status | Meaning |
| --- | --- |
| live | Executable read/list/get via pack invoke |
| approval_required | Mutate/archive/cancel after Soft Wall |
| proposal_only | Draft / review queue only |
| not_configured | No typed route yet (e.g. nested tasks, note_create, sync_health) |
| intentionally_forbidden | Hard delete, document binary, payment post, outbound send, generic proxy |

Do not claim CRUD complete while `not_configured` or `degraded` counts are non-zero.
`GET /v1/products/propreneur/health` includes readiness; connectivity alone is insufficient.

## Contabo loopback

On Contabo, Keprix publishes its API on the host loopback only:

- Host URL: `http://127.0.0.1:13333` (compose maps `127.0.0.1:13333:3333`)
- Propreneur on the same host should set `PROPRENEUR_PRODUCT_API_URL` / bridge URL to
  that loopback address, not a public hostname.
- Do not expose port 13333 on the public interface merely for convenience.

## Auth and scopes

1. Prefer short-lived signed exchange tokens and TrustedExecutionContext headers
   (`X-Keprix-Trusted-*`, Authorization bearer, tenant Host).
2. A transitional shared secret may bootstrap early deploys only; rotate and prefer grants.
3. Every mutate must carry tenant/workspace ID, actor ID, correlation ID, and an
   idempotency key.
4. Soft Wall owns elevated writes. Propreneur re-authorizes; Keprix is never sole authority.
5. Model arguments cannot override trusted identity headers (server-side only).

## Southbound connector

Env: `PROPRENEUR_PRODUCT_API_URL`

Host allowlist: `127.0.0.1`, `localhost`, `propreneur.local`, `*.propreneur.test`

Primary routes: `/api/aiva/v1/*` (CRUD). Compat `/api/carina/tools` remains for legacy bridges.

## Operator commands

```bash
cd /opt/lampp/htdocs/verlox/keprix
python -c "from keprix.product_sidecar.readiness import build_product_readiness; print(build_product_readiness('propreneur'))"
python -m pytest tests/product_sidecar/test_propreneur_pack.py -q
```

Feature flag: `product.propreneur.sidecar`

## Related runbooks

- Troubleshooting: `docs/troubleshooting/propreneur-sidecar.md`
- Approvals: `docs/architecture/propreneur-approvals-idempotency-events.md`
- Trusted identity: `docs/architecture/propreneur-connector-trusted-identity.md`
- E2E: `docs/architecture/propreneur-e2e-testing.md`
- Key rotation: `docs/propreneur-sidecar/key-rotation.md`
- Observability: `docs/propreneur-sidecar/observability-runbook.md`
- Canary / cutover / rollback: `docs/propreneur-sidecar/canary-cutover-rollback.md`
- Release candidate template: `docs/operations/propreneur-sidecar-release-manifest.md`
