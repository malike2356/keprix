# Propreneur Keprix product sidecar

**Status:** pack registered in Keprix product_sidecar foundation
**Contract version:** 1.0.0
**Writing style:** plain ASCII only.

## Architecture

Keprix hosts the Propreneur product pack under the shared multi-product sidecar
foundation (`src/keprix/product_sidecar/`). Propreneur remains the authorization
and data authority. Keprix advertises capability nodes, mints short-lived scoped
tokens, and calls allowlisted Propreneur HTTP routes.

```
Propreneur (Laravel)  --southbound HTTP-->  Keprix product connector
        ^                                         |
        |                                         v
   soft-wall / tools                    /v1/products/propreneur/*
```

Pack sources:

- Nodes: `src/keprix/product_sidecar/packs/propreneur.py`
- Registry install: `build_propreneur_pack()` in `registry.py`
- Metadata: `packages/packs/propreneur-sidecar/pack.json`
- OpenAPI fragment: `docs/propreneur-sidecar/openapi.json`
- Schema: `schemas/propreneur-sidecar/contract.schema.json`

Memory namespace is always `product:propreneur`. Cross-product node composition
fails closed.

## Contabo loopback

On Contabo, Keprix publishes its API on the host loopback only:

- Host URL: `http://127.0.0.1:13333` (compose maps `127.0.0.1:13333:3333`)
- Propreneur on the same host should set `PROPRENEUR` bridge / Keprix base URL to
  that loopback address, not a public hostname.
- Do not expose port 13333 on the public interface merely for convenience.

Local Docker-to-host may use `host.docker.internal` or the compose service name
when both products share a compose network. Prefer documented product env vars
over hard-coded IPs in application code.

## Auth and scopes

1. Prefer short-lived signed exchange tokens (`POST /api/keprix/v1/token/exchange`
   on Propreneur, then Keprix session mint under `/v1/products/propreneur/sessions`).
2. A transitional shared secret may bootstrap early deploys. Store it outside
   source control, compare safely, rotate with overlap (see `key-rotation.md`).
3. Every invoke must carry tenant/workspace ID, actor ID, correlation ID, and an
   idempotency key for mutations.
4. Ordinary grants should use scoped permissions such as `properties.read`,
   `properties.write`, `contacts.read`, `contacts.write`. Avoid unrestricted `*`
   for tenant users.
5. Mutate, destructive, and propose nodes set `soft_wall=True`. Propreneur must
   re-authorize every tool execution; Keprix is never the sole authority.

## Capability risk map

| Risk | Nodes |
| --- | --- |
| read | property_search/get, contact_search/get, tenancy_search/get, deal_search/get, ask_portfolio |
| mutate | property_create/update, contact_create/update, tenancy_create/update, task_create, note_create |
| destructive | property_archive |
| propose | deal_propose |
| outbound | none in this pack (messaging later) |

## Southbound connector

Env: `PROPRENEUR_PRODUCT_API_URL`

Host allowlist: `127.0.0.1`, `localhost`, `propreneur.local`, `*.propreneur.test`

Routes:

- `GET /api/keprix/v1/health`
- `GET /api/keprix/v1/capabilities`
- `POST /api/keprix/v1/token/exchange`
- `GET /api/keprix/v1/context`
- `GET /api/carina/tools` (compat catalog)
- `POST /api/carina/tools/{toolName}` (compat execute; approval_required; idempotent)
- `POST /api/keprix/v1/events/ack`

Compat northbound path documented for legacy bridges: `/carina/agent/run`.

## Operator commands

```bash
cd /opt/lampp/htdocs/verlox/keprix
python -c "from keprix.product_sidecar.provision import plan_provision; print(plan_provision('propreneur'))"
python -c "from keprix.product_sidecar.registry import get_product_pack_registry; print(get_product_pack_registry().health('propreneur'))"
python -m pytest tests/product_sidecar/test_propreneur_pack.py -q
```

Feature flag: `product.propreneur.sidecar`

## Related runbooks

- Key rotation: `docs/propreneur-sidecar/key-rotation.md`
- Observability: `docs/propreneur-sidecar/observability-runbook.md`
- Canary / cutover / rollback: `docs/propreneur-sidecar/canary-cutover-rollback.md`
- Release candidate template: `docs/operations/propreneur-sidecar-release-manifest.md`
