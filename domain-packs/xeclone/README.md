# Xeclone / iLaud Keprix sidecar

Local product sidecar pack for Xeclone (iLaud digital clone). Contract version
`1.0.0`, pack version `0.1.0`, persona pin `ilaud@0.1.0`, HTTP port **3361**.

## Boundary

- Xeclone owns identity assets, consent, product UX, channel accounts and approvals.
- Keprix owns persona runtime, scoped RAG, multimodal draft jobs and playbooks.
- Carina remains the Phase 1 live path for inbound webhooks and OAuth until a
  separately signed cutover.
- Autonomous mode is **OFF** unless separately signed.

## Quick start

```bash
bash scripts/provision-local.sh
bash scripts/start-xeclone-sidecar.sh
curl -s http://127.0.0.1:3361/v1/products/xeclone/health
```

Shared token via `XECLONE_SHARED_TOKEN` or `XECLONE_SIDECAR_TOKEN` (empty = open for local).

Fixture product API: `/fixture-product/api/keprix/v1/*` (tenant `owner-laud`).

## Tests

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/pytest domain-packs/xeclone/tests -q
```

## Hard rules

- Generation never calls distribution.
- Shadow dual-run never publishes.
- No secrets in provision receipts.
- No live ElevenLabs/HeyGen calls; handlers are deterministic stubs.
- Watermark/disclosure removal blocked in Phase 1-4.
