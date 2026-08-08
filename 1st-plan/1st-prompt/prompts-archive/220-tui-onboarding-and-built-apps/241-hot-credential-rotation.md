# keprix - Prompt: Hot Credential Rotation and Zero-Downtime Secret Updates

## Purpose

Today, rotating an API key in keprix means:
1. Update the key in the vault or .env file
2. Restart keprix
3. Wait for health checks to pass
4. Hope nothing broke

For a self-hosted agent that may be mid-conversation with a customer, this is unacceptable. A production agent cannot be restarted every time a credential changes.

Cordon solved this: credentials are fetched per-request from the external vault. Change the key in 1Password, the next request picks it up. No restart.

This prompt implements hot credential rotation for keprix: credentials reload from the external vault on every proxied request (or on a configurable cache interval). Agents never need to restart when keys change.

## Prerequisites

- Prompt 239 (Credential Injection Proxy)
- Prompt 240 (Tool Credential Isolation)

## What to build

### 1. Per-request credential fetch (no cache -- default)

The proxy fetches the credential from the vault on every request. This is the default for security-sensitive credentials (LLM API keys, payment processor keys):

```toml
[[routes]]
host = "api.anthropic.com"
secret_ref = "anthropic-api-key"
cache = "none"              # fetch per-request (default)
```

Trade-off: adds ~50-100ms latency per request (vault CLI call). Acceptable for LLM API calls which are already 1-10 seconds. Not acceptable for high-frequency internal calls.

### 2. TTL-based credential cache

For higher-frequency credentials, a short-lived cache with a configurable TTL:

```toml
[[routes]]
host = "api.sendgrid.com"
secret_ref = "sendgrid-api-key"
cache = { ttl = "60s" }     # cache for 60 seconds, then re-fetch
```

The cache lives in the proxy process memory only. It is never persisted to disk. On proxy restart, the cache is empty. The `Secret` type zeroizes cache entries on eviction.

### 3. Cache invalidation signal

For immediate rotation without waiting for TTL expiry:

```bash
keprix proxy rotate anthropic-api-key
```

This sends a signal to the running proxy to invalidate the cache for that specific secret. The next request fetches the new value. Zero downtime.

### 4. Rotation audit

Every time a credential is rotated (new value detected from vault), the proxy emits a structured log event:

```json
{
  "event": "credential.rotated",
  "secret_ref": "anthropic-api-key",
  "previous_hash": "sha256:abc123...",
  "new_hash": "sha256:def456...",
  "timestamp": "2026-07-06T12:34:56Z",
  "trigger": "cache_expiry"
}
```

The keprix audit system captures these events and displays them in the credential audit trail with a "rotated" badge.

### 5. Rotation health check

After rotation, the proxy verifies the new credential works:

1. Fetch the new credential from the vault.
2. Make a lightweight probe request to the upstream API (e.g., `GET /v1/models` for Anthropic, `GET /v1/charges?limit=1` for Stripe).
3. If the probe succeeds: mark rotation as healthy, log success.
4. If the probe fails (401, 403): mark rotation as failed, keep using the cached old credential, alert the operator.

```bash
keprix proxy rotate anthropic-api-key --verify
```

The `--verify` flag enables probe-then-switch behaviour. Without it, rotation is immediate (trust the vault).

### 6. Rotation schedule (optional)

For credentials that should be rotated on a schedule (e.g., every 90 days per security policy):

```toml
[[routes]]
host = "api.stripe.com"
secret_ref = "stripe-secret-key"
rotation = { schedule = "90d", reminder = "7d" }
```

The proxy does not automatically rotate credentials (it cannot write to the external vault). It reminds the operator:

```
[WARN] Credential 'stripe-secret-key' has not been rotated in 90 days.
       Next rotation reminder: already overdue.
       Run: keprix proxy rotate --check stripe-secret-key
```

### 7. Rotation status dashboard

At `/admin/credentials/rotation` in the keprix dashboard:

| Credential | Last Rotated | Age | Next Reminder | Cache TTL | Status |
|---|---|---|---|---|---|
| anthropic-api-key | 2h ago | 2h | 88d | none | Healthy |
| stripe-secret-key | 95d ago | 95d | Overdue | 60s | Needs rotation |
| sendgrid-api-key | 30d ago | 30d | 60d | 60s | Healthy |

### 8. Grace period during rotation

When the proxy detects a rotation event:

1. It continues serving in-flight requests with the old credential.
2. New requests use the new credential.
3. If the new credential fails (401), the proxy falls back to the old credential for 60 seconds (configurable) while alerting the operator.
4. After the grace period, the old credential is evicted and all requests use the new one.

This prevents a bad rotation from causing an outage.

## Files to create

```
keprix-proxy/src/
  cache.rs                 - in-memory credential cache with TTL
  rotation.rs              - rotation detection, probe, grace period, fallback
  scheduler.rs             - rotation reminder scheduler
  signal.rs                - IPC signal handler (rotate, invalidate, flush)

src/keprix/proxy/
  rotation_cli.py          - keprix proxy rotate subcommand
  rotation_monitor.py      - rotation event consumer (logs, audit, alerts)

src/keprix/api/
  rotation_routes.py       - GET /api/admin/credentials/rotation

frontend/src/app/(admin)/dashboard/
  credentials/
    rotation/
      page.tsx             - rotation status dashboard

docs/
  security/credential-rotation.md

tests/
  proxy/
    test_cache.py
    test_rotation.py
    test_grace_period.py
    test_scheduler.py
```

## Acceptance criteria

- Changing a credential in the external vault takes effect on the next proxied request without restarting keprix.
- `keprix proxy rotate <secret_ref>` invalidates the cache immediately. The next request uses the new credential.
- `keprix proxy rotate <secret_ref> --verify` probes the upstream API before switching. If the probe fails, the old credential is retained.
- During a grace period after rotation, failed requests with the new credential fall back to the old credential.
- Credentials not rotated within their schedule generate operator reminders in the dashboard and logs.
- The proxy never persists cached credentials to disk. Cache entries zeroize on eviction.
- Zero-downtime rotation works during an active agent conversation. The agent does not drop messages or fail mid-turn.
