# Keprix Fleetz sidecar

Advisory fleet intelligence sidecar for Fleetz (Ghana fleet tracking and fuel).
Fleetz remains source of truth for telemetry, primary alerts, and all vehicle or
device commands. Keprix explains, correlates, drafts, and runs approved operator
playbooks only.

## Architecture

See `docs/ARCHITECTURE.md` and `docs/PILOT-SIGNOFF.md`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness / degraded / kill switch |
| GET | `/fleetz/capabilities` | Nodes, live/stub/disabled honesty |
| POST | `/fleetz/tools/{name}` | Direct tool dispatch |
| GET/POST | `/v1/products/fleetz/*` | Shared product sidecar contract |

Vehicle command capabilities are advertised as `disabled`. There is no Traccar
command path, MQTT command publish, or tracker TCP/UDP credential on this sidecar.

## Run locally

```bash
cd /opt/lampp/htdocs/verlox/keprix/domain-packs/fleetz
bash scripts/deploy-local.sh
# or
FLEETZ_USE_FIXTURES=1 python3 -m uvicorn http_app:app --host 127.0.0.1 --port 3354
```

Optional auth: set matching `FLEETZ_SHARED_TOKEN` / `FLEETZ_SIDECAR_TOKEN`.

Point a future Fleetz product API with `FLEETZ_PRODUCT_API_URL` and
`FLEETZ_USE_FIXTURES=0`. Until then fixtures under `fixtures/fleet_data.json` drive reads.

## Provision

```bash
cd /opt/lampp/htdocs/verlox/keprix
keprix product provision fleetz --namespace pilot
keprix product status fleetz --namespace pilot
```

Pack-local equivalent:

```bash
cd domain-packs/fleetz
python3 -c 'from provision.provisioner import provision; print(provision(fleet_namespace="pilot"))'
```

## Tests

```bash
cd /opt/lampp/htdocs/verlox/keprix
pytest domain-packs/fleetz/tests/test_fleetz_sidecar.py -q
```

## Safety defaults

- Advisory only; no immobilise / fuel cut / tracker config / firmware
- Geofence and route apply remain preview/simulation
- Stale or low-quality series refuse definitive conclusions
- Cross-fleet ids return no data
- Duplicate notification/task/case idempotency keys do not double-send
- Precise routes and driver PII are minimised by role and purpose
