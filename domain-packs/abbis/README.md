# Keprix ABBIS sidecar

Product sidecar for the ABBIS Ghana / West Africa borehole industry platform.

ABBIS remains the SaaS source of truth. This pack provides Keprix agent sessions, deterministic calculators, mesh registration, channels, degraded queues and isolation.

## Run locally

```bash
cd /opt/lampp/htdocs/verlox/keprix/domain-packs/abbis
bash scripts/start-abbis-sidecar.sh
# or:
python3 -m uvicorn http_app:app --host 127.0.0.1 --port 3360
```

Health:

```bash
curl -fsS http://127.0.0.1:3360/v1/products/abbis/health
```

Fixture product API (mounted under the same process):

```bash
curl -fsS http://127.0.0.1:3360/fixture-product/api/keprix/v1/health
```

Provision dry-run:

```bash
curl -fsS -X POST http://127.0.0.1:3360/v1/products/abbis/provision \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-alpha","stakeholder":"S07","dry_run":true}'
```

## Contract surface

Northbound: `/v1/products/abbis/{health,capabilities,manifest,sessions,invoke,jobs,events,approvals,metrics}`

Southbound fixture: `/fixture-product/api/keprix/v1/*`

## Tests

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/pytest domain-packs/abbis/tests -q
```

## Naming rules

- Operator: Ghanaian operating company
- Association: BDAG
- Never VERLOX as operator
- Never Kari / `KB` quote prefixes in live paths
