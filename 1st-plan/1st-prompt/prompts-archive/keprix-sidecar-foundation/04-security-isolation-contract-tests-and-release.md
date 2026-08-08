# Prompt KSF-04: Security, isolation, conformance, and release gate

**Status: COMPLETED 2026-08-08**
**Depends on:** KSF-00 through KSF-03

## Build

1. Cross-product/deployment/tenant/actor matrix for capabilities, invoke, jobs,
   streams, approvals, metrics, connectors, memory, files, cache and audit.
2. Adversarial suite: forged/replayed token/event, SSRF/DNS rebinding, prompt
   injection, schema confusion, oversized/decompression payload, path traversal,
   malicious pack, stale approval, confused deputy and connector redirect.
3. Pack signing/checksum, dependency/SBOM/image scan, sandbox and egress tests.
4. Load and chaos for event bursts, slow products/models, reconnects, queue/disk
   pressure, worker crash, cancellation, key rotation, upgrade and rollback.
5. Conformance command runs shared and product-supplied fixtures, outputs a signed
   evidence report without secrets, and blocks READY on any Must failure.
6. Release runbook defines versioning, compatibility window, vulnerability response,
   rollback, incident kill switches and product notification.
7. No product pack is enabled in production merely because foundation passes;
   its own queue, owner and pilot sign-off remain required.

## Acceptance

- [ ] Cross-product access fails across every persistence and streaming surface
- [ ] Malicious pack/connector cannot escape declared grants
- [ ] Chaos/recovery retains idempotency and audit correlation
- [ ] Reusable conformance report is required by all five product sign-offs

## What was built

- Shared product sidecar foundation under `src/keprix/product_sidecar/`
- Fixture packs + registry install/validate/upgrade/rollback/kill
- Northbound `/v1/products/{product_key}` including events/stream and durable jobs
- Southbound ProductConnector with SSRF/default-deny and FakeProductConnector
- CLI: `keprix product provision|plan|status|upgrade|rollback|disable|remove|conformance`
- Conformance gate + release runbook `docs/architecture/product-sidecar-foundation-release.md`
- Tests: `tests/product_sidecar/test_sidecar_foundation.py` (plus existing Carina/Aiva suite)
