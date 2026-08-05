# Credential rotation

The credential proxy fetches secrets per request by default. Rotating a key in the external vault takes effect without restarting Keprix or the active agent process.

## Cache modes

```toml
[[routes]]
host = "api.anthropic.com"
secret_ref = "anthropic-api-key"
cache = "none"

[[routes]]
host = "api.sendgrid.com"
secret_ref = "sendgrid-api-key"
cache = { ttl = "60s" }
```

Cached credentials live only in the proxy process. They are not persisted to disk, and cache entries are zeroized when evicted.

## Manual invalidation

```bash
keprix proxy rotate anthropic-api-key
keprix proxy rotate anthropic-api-key --verify
```

The command writes a local invalidation signal consumed by the running proxy. The next request fetches the current vault value. With `--verify`, a bad replacement keeps the previous in-memory credential during the grace path and records a failed rotation event.

## Dashboard

Rotation status is available at `/admin/dashboard/credentials/rotation` and `GET /api/admin/credentials/rotation`.
