# Prompt KSF-02: Southbound connectors, workload identity, and grants

**Status: COMPLETED 2026-08-08**
**Depends on:** KSF-00
**Blocks:** product connector prompts

## Build

1. Typed `ProductConnector` interface for health, capabilities, token exchange,
   context, projected reads, preview, action, event acknowledgement and deletion.
2. Manifest allowlist binds operation key to method/path template, schema, grant,
   sensitivity, rate, timeout, retry/idempotency and approval. Default deny.
3. Workload identity supports signed short-lived tokens, issuer/audience/key
   rotation/revocation, clock skew, nonce/replay and optional mTLS.
4. Request context cannot be overridden by response or model output. Product,
   deployment and tenant host allowlist is provisioned, not user-supplied.
5. Connector enforces TLS, DNS/SSRF protections, response size/schema, circuit
   breaker, safe retry, redaction and stable error mapping.
6. Cache only non-sensitive capability/entitlement facts for bounded TTL. Writes
   fail closed when current authority cannot be checked.
7. Build fake connector and contract harness reused by all product packs.

## Acceptance

- [ ] Arbitrary product URL/path cannot be requested by a node
- [ ] Token replay, wrong audience and revoked key fail
- [ ] Retry semantics cannot duplicate product action
- [ ] Product connector fixture passes reusable conformance suite

## What was built

- Shared product sidecar foundation under `src/keprix/product_sidecar/`
- Fixture packs + registry install/validate/upgrade/rollback/kill
- Northbound `/v1/products/{product_key}` including events/stream and durable jobs
- Southbound ProductConnector with SSRF/default-deny and FakeProductConnector
- CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove|conformance`
- Conformance gate + release runbook `docs/architecture/product-sidecar-foundation-release.md`
- Tests: `tests/product_sidecar/test_sidecar_foundation.py` (plus existing Carina/Aiva suite)
