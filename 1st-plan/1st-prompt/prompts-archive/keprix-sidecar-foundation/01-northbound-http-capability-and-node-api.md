# Prompt KSF-01: Northbound product-sidecar HTTP and node API

**Status: COMPLETED 2026-08-08**
**Depends on:** KSF-00
**Blocks:** product pack HTTP integration

## Build

1. Implement `/v1/products/{product_key}` endpoints from the shared contract:
   health, capabilities, manifest, sessions, invoke, jobs, cancellation, events,
   stream, approval decision and metrics.
2. OpenAPI has discriminated node schemas and stable error codes. Capability
   discovery is authoritative for live/stub/degraded, versions and requirements.
3. `/invoke` binds only a registered node and validates schema, product/deployment,
   tenant, actor, grant, purpose, entitlement evidence, approval, rate, budget and
   policy. It cannot accept Python paths, arbitrary URLs, shell or tool names.
4. Sessions are optional convenience, not authority. Every call remains fully
   authenticated and scoped; session context cannot widen token grants.
5. Async jobs return 202 and location; sync limits force long work into jobs.
   Cancellation and stream cursor are idempotent.
6. Request/body/file/output limits, redaction, correlation, trace and audit.
7. Version negotiation and deprecation headers support additive evolution.

## Acceptance

- [ ] Product fixture invokes advertised node and receives typed result
- [ ] Unknown/disabled/unauthorised nodes fail without handler execution
- [ ] Jobs survive process restart and stream resumes by cursor
- [ ] OpenAPI and runtime capability schemas agree

## What was built

- Shared product sidecar foundation under `src/keprix/product_sidecar/`
- Fixture packs + registry install/validate/upgrade/rollback/kill
- Northbound `/v1/products/{product_key}` including events/stream and durable jobs
- Southbound ProductConnector with SSRF/default-deny and FakeProductConnector
- CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove|conformance`
- Conformance gate + release runbook `docs/architecture/product-sidecar-foundation-release.md`
- Tests: `tests/product_sidecar/test_sidecar_foundation.py` (plus existing Carina/Aiva suite)
