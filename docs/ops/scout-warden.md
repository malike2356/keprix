# Scout Warden integration

Disabled by default for Community Edition.

## Env

- `KEPRIX_SCOUT_WARDEN_ENABLED=1`
- `KEPRIX_SCOUT_WARDEN_URL=https://scout.example`
- `KEPRIX_SCOUT_WARDEN_TOKEN` from `.access` (never commit)

## API

- `GET /api/scout-warden/status`
- `POST /api/scout-warden/scans`
- `POST /api/scout-warden/alerts`

Unreachable Scout returns `{ok: false, degraded: true}` without crashing Keprix.
