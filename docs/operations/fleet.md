# Fleet operations (Enterprise)

Managed fleet register and health for Enterprise operators.

## GUI (preferred)

Open **Admin > Fleet** at `/admin/fleet`.

- Register instances (name, base URL, version)
- Refresh health via server-side probe (`POST /api/fleet/instances/{id}/probe`)
- Remove with Soft Wall confirm
- Review audit events when `audit_export` is enabled

Community Edition shows an honest locked state with an upgrades link. No fake instances are rendered.

## API

- `GET /api/fleet/instances` (Enterprise `fleet_deploy`)
- `POST /api/fleet/instances`
- `POST /api/fleet/instances/{id}/health`
- `POST /api/fleet/instances/{id}/probe`
- `DELETE /api/fleet/instances/{id}`
- `GET /api/fleet/audit` (Enterprise `audit_export`)

Persistence: `~/.keprix/fleet/instances.json` and `audit.jsonl`.
