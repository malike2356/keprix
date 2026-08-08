# Product sidecar foundation release runbook

**Status:** BINDING for keprix-sidecar-foundation
**Date:** 2026-08-08
**Writing style:** plain ASCII only.

## Scope

This runbook covers the shared multi-product sidecar foundation only
(`keprix/src/keprix/product_sidecar/`). Passing foundation conformance does
**not** enable any product pack in production. Each product queue
(petraclus, abbis, xeclone, fleetz, clinicom, carina/aiva) still needs its
own owner pilot sign-off.

## Versioning

- Contract version: `1.0.0` (`X-Keprix-Contract-Version`)
- Packs carry `version`, `checksum`, and optional `signature`
- Upgrades use expand / migrate / contract with last-known-good retained
- CLI: `keprix product upgrade <product> --version <ver>`
- Rollback: `keprix product rollback <product>`

## Compatibility window

- Additive OpenAPI evolution only within a major contract version
- Deprecation header: `X-Keprix-API-Deprecated` (shared-token compat)
- Capability discovery (`GET /capabilities`) is authoritative for live/stub

## Conformance gate

```bash
keprix product conformance
# or
python -c "from keprix.product_sidecar.conformance import run_foundation_conformance; print(run_foundation_conformance())"
```

Any Must failure blocks READY. The signed report must not contain secrets.

## Kill switches and incidents

| Switch | Effect |
| --- | --- |
| `keprix product disable <product>` | Stops new invoke; preserves jobs/events/memory for investigation |
| `POST .../admin/kill` `disable_node` | Node-level kill |
| `force_carina` / `outbound_kill` | Carina/Aiva ops kill board |
| Circuit breaker | Opens after repeated handler failures |

Notify the product owner before re-enabling after an incident.

## Vulnerability response

1. Disable the affected product or node.
2. Rotate signing keys (`TokenService.revoke_kid`) and bootstrap secrets in vault.
3. Patch, run conformance, upgrade with dry-run evidence.
4. Rollback to last-known-good if smoke fails.

## Local deploy smoke

```bash
cd /opt/lampp/htdocs/verlox/keprix
docker compose -f docker/docker-compose.yml up -d --build
curl -fsS http://127.0.0.1:3333/api/health
curl -fsS http://127.0.0.1:3333/v1/products/carina/health
keprix product conformance
```

## Contabo note

Clinicom on Contabo remains Carina-backed until the Clinicom product queue
owner flip. Do not treat foundation completion as Contabo cutover.
