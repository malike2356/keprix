# Security architecture

Keprix is designed for self-hosted deployment. The security model assumes you control the host, the network perimeter, and the Docker environment. This document describes each security boundary and how to harden it.

## Threat model

| Threat | Mitigation |
| --- | --- |
| Unauthorised API access | JWT session tokens, API key auth, role-based checks |
| Credential theft | Vault encryption at rest, no plain-text secrets in DB |
| LLM prompt injection | Tool output sanitisation, iteration limits, approval gates |
| Mutation code execution | Isolated Docker sandbox, hard timeout, network block |
| Audit evasion | Immutable append-only audit log, optional Scout export |
| Data exfiltration | Egress control on skills/packs, network hosts allowlist |
| Supply chain (packs) | Pack signatures, pack gate approval workflow |
| Inbound malware / phishing | Channel Shield: intercept, immutable store, analyse, quarantine + safe summary |

## Channel Shield

Shared inbound protection across email, Slack, Teams, Telegram, WhatsApp, Discord, SMS, and web. See `docs/features/channel-shield.md`.

Agent OS is a protected consumer: assistants and employee agents receive only `agentSafeContent` plus verdict/provenance. Raw evidence stays behind `rawEvidenceRef` ACLs. Ingress, memory, and outbound guards live in `src/keprix/channel_shield/agent_ingress.py`.

- Fail-closed default for `malicious` and analysis `error`
- Raw payloads encrypted at rest (`ENCRYPTION_KEY`)
- Optional Scout signals/commands; gateway runs without Scout
- Release of malicious messages and destroy require admin

## Authentication

All API routes except `/api/health` and the auth endpoints require a valid credential.

### Session tokens (web UI)

Login at `/auth/login` returns a signed JWT stored in an `httpOnly` cookie. Token lifetime:

```bash
KEPRIX_SESSION_TTL=86400     # seconds (default 24 hours)
KEPRIX_SESSION_SECRET=...    # REQUIRED: change from default before production
```

### API keys (programmatic access)

Create API keys in **Developer > API Keys**. Pass as:

```
Authorization: Bearer <key>
```

Keys are scoped to a user and can be revoked at any time. Key hashes are stored in PostgreSQL; the plain-text key is shown only once at creation.

### Two-factor authentication (TOTP)

Enable per-user TOTP:

```bash
KEPRIX_REQUIRE_2FA=true       # force all users
```

Or enforce only for admin accounts: **Admin > Settings > Security > Require 2FA for admins**.

## Authorisation

Keprix has two roles:

| Role | Access |
| --- | --- |
| `user` | Own workspace data, chat, tools, memory, research |
| `admin` | All user access plus: mutations, team admin, MCP config, user management, cron, backup |

Role is set at user creation and editable by admins in **Admin > Users**.

Fine-grained feature flags (disable research, disable coding workspace, etc.) are available in **Admin > Settings > Feature flags**.

## Transport security

In development, the stack is HTTP only. For production:

1. Put a reverse proxy (Nginx, Caddy, Traefik) in front of port 3000 (frontend) and optionally 3333 (backend).
2. Terminate TLS at the proxy. Redirect HTTP to HTTPS.
3. Set `KEPRIX_TRUSTED_PROXIES` to the reverse-proxy peer CIDRs (for example `127.0.0.1,::1`). Forwarded headers are ignored unless the peer matches.
4. Use `KEPRIX_INSTANCE_URL=https://your-domain.com` and `KEPRIX_ALLOWED_ORIGINS=https://your-domain.com`.

See [Hardening](hardening.md) and [VPS deploy](../operations/vps-deploy.md) for Caddy/nginx templates under `deploy/`.

## Vault (secret storage)

Sensitive values (channel tokens, API keys, credentials added at runtime) are stored in the Vault, not plain-text in the database.

Vault encryption uses AES-256-GCM with a key derived from:

```bash
KEPRIX_VAULT_KEY=your-64-char-hex-key   # REQUIRED: generate with openssl rand -hex 32
```

If `KEPRIX_VAULT_KEY` is not set, the Vault is disabled and secrets are stored encrypted with a derived default key (NOT suitable for production).

See [Vault](vault.md) for usage.

## Mutation sandbox

Every mutation-synthesised tool runs in an isolated execution context before installation:

- Spawned inside the `backend` container with a restricted subprocess environment.
- Hard timeout: `KEPRIX_SANDBOX_TIMEOUT` seconds (default 30).
- No access to the host filesystem beyond the generated tools directory.
- Network egress blocked by default. Tools that declare `network_hosts` in their manifest still run inside the container; egress is enforced by the container network rules.

Approved tools run inside the main backend process but are Python functions, not subprocess calls.

## Audit log

Every security-relevant event is written to the structured audit log:

- Login, logout, failed login attempts
- Mutation proposals, approvals, rejections
- API key creation and revocation
- User and role changes
- Pack installs and uninstalls
- Vault read/write operations (metadata only, not values)

Audit log table: `audit_log` in PostgreSQL. Append-only by default (no update/delete in application code).

Forward to Scout for centralised governance:

```bash
KEPRIX_GOVERNANCE_AUDIT_EXPORT=true
```

See [Governance](governance.md) and [Scout integration](../integrations/scout.md).

## Pack and skill security

Packs declare:

- `network_hosts`: external domains the tools may call
- `required_env`: environment variables the tools expect
- `risk_level`: `low`, `medium`, `high`

High-risk packs require admin approval even when the pack gate is in open mode. Pack signatures are verified at install time.

Configure the pack gate in **Settings > Pack gate** or:

```bash
KEPRIX_PACK_GATE_ENABLED=true
KEPRIX_PACK_GATE_REQUIRE_ADMIN_APPROVAL=true
```

## Network egress

The agent's built-in web tools call `KEPRIX_RESEARCH_SEARXNG_URL` for web search (internal container). External network calls happen through declared tool `network_hosts` or MCP server connections.

To restrict all outbound traffic, configure your Docker network with an egress firewall and add explicit allow rules for:

- Your LLM provider API endpoints
- SearXNG (if external)
- Any MCP server hosts

## Web voice transcription

Workspace chat dictation uses `POST /api/audio/transcribe` on the main API (:3333).

- **Authentication:** Bearer session token required; unauthenticated calls return 401.
- **Rate limit:** 30 transcribes per hour per user (community default via `RateLimitMiddleware` on `/api/audio/transcribe`).
- **Temp files:** Uploaded audio is written to a temp path, transcribed, then deleted in the shared handler (`audio_transcribe.py`).
- **STT toggle:** When `stt.enabled` is false in `config.yaml`, the endpoint returns 403 and the mic UI is hidden.

Operator guide: [Web voice input](../features/web-voice-input.md).

## Production checklist

See [Hardening](hardening.md) for the complete pre-production security checklist covering TLS, headers, rate limiting, log rotation, and backup verification.

## Related

- [Vault](vault.md)
- [Governance](governance.md)
- [Review gateway](review-gateway.md)
- [Audit log](audit-log.md)
- [Hardening](hardening.md)
