# keprix - Prompt 08: Security, Auth, Vault, and Backup

## Context

Sources:
- `odysseus/core/auth.py` - session auth
- `odysseus/routes/auth_routes.py` - login/logout/register
- `odysseus/routes/vault_routes.py` - encrypted credential vault
- `odysseus/routes/backup_routes.py` - backup/restore
- `odysseus/docs/security-ci.md`, `THREAT_MODEL.md`
- `hermes-agent/agent/file_safety.py`, `agent/redact.py`
- `hermes-agent/agent/secret_sources/bitwarden.py`
- `core.carinaai.uk/src/security/` - Carina security (minus Scout/kill switch)
Output: `keprix/backend/auth/`, `keprix/backend/security/`

## CRITICAL EXCLUSION

Do NOT port anything referencing:
- Labyrinth Scout (`scout-client`, `kill-switch-listener`, `labyrinth`)
- Blockchain trust or verification
- Scout proxy routes
- `LABYRINTH_*` env vars

These are Enterprise-only. If encountered, skip silently.

## Authentication

### Session Auth (port from Odysseus)

```
core/auth.py            -> backend/auth/session.py
routes/auth_routes.py   -> backend/auth/routes.py
```

keprix supports single-admin and multi-user modes:

**Single-admin mode** (default):
- One admin account set via `keprix_ADMIN_PASSWORD` env var
- No registration; login page with password prompt
- Session stored in encrypted cookie (HTTPOnly, SameSite=Strict)
- TOTP 2FA optional (see below)

**Multi-user mode** (`keprix_MULTI_USER=true`):
- Registration enabled
- Users stored in `users` table
- Roles: `admin`, `user`
- Admin approves new registrations when `keprix_REQUIRE_APPROVAL=true`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,    -- bcrypt
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin','user')),
    totp_secret TEXT,               -- encrypted TOTP secret if 2FA enabled
    is_approved BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,       -- SHA-256 of bearer token
    device_label TEXT,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON sessions (token_hash);
CREATE INDEX ON sessions (user_id, expires_at);
```

### Auth API Endpoints

```
POST   /api/auth/login               - login (username+password, returns bearer token)
POST   /api/auth/logout              - invalidate current session
POST   /api/auth/register            - create account (multi-user mode only)
GET    /api/auth/me                  - current user info
POST   /api/auth/totp/setup          - generate TOTP secret + QR code
POST   /api/auth/totp/verify         - verify TOTP code (during setup)
POST   /api/auth/totp/disable        - disable TOTP

POST   /api/admin/users              - admin: create user
GET    /api/admin/users              - admin: list users
PUT    /api/admin/users/{id}         - admin: update (approve, deactivate)
DELETE /api/admin/users/{id}         - admin: delete user
```

## TOTP (2FA)

Port from Odysseus (see `tests/test_totp_failclosed.py`):
- Use `pyotp` library
- TOTP secret encrypted with AES-256 before storing in DB
- Fail-closed: if TOTP is enabled and code is wrong, deny login even if password correct
- Test: `backend/security/tests/test_totp_failclosed.py` (port from Odysseus)

## Encrypted Vault

Port from Odysseus `routes/vault_routes.py`:
```
routes/vault_routes.py -> backend/security/vault_routes.py
```

The vault stores user secrets (API keys, email passwords, CalDAV passwords) encrypted
at rest using AES-256-GCM. The encryption key derives from the user's master password
via PBKDF2 (600,000 iterations). The key is never stored; derived on each session.

```sql
CREATE TABLE vault_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    label TEXT NOT NULL,
    category TEXT DEFAULT 'password',  -- password, api_key, note, ssh_key
    username TEXT,
    value_encrypted BYTEA NOT NULL,    -- AES-256-GCM encrypted
    url TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON vault_items (user_id, category);
```

```
POST   /api/vault/items              - create vault item
GET    /api/vault/items              - list (no plaintext values)
GET    /api/vault/items/{id}         - get with decrypted value (requires session)
PUT    /api/vault/items/{id}         - update
DELETE /api/vault/items/{id}         - delete
POST   /api/vault/unlock             - provide master password to unlock vault for session
POST   /api/vault/lock               - lock vault (clear decryption key from memory)
```

Security: vault decryption key is kept only in process memory (not Redis, not DB).
On lock or session end, key is zeroed. Port test: `test_vault_password_not_in_argv.py`.

## Bitwarden Integration

Port `hermes-agent/agent/secret_sources/bitwarden.py` to
`backend/security/bitwarden_source.py`.

This is a read-only bridge: when `BITWARDEN_CLIENT_ID` and `BITWARDEN_CLIENT_SECRET`
are set, keprix can read secrets from Bitwarden Secrets Manager and inject them
as tool parameters. The agent cannot write to Bitwarden.

## Secret Redaction

Port `hermes-agent/agent/redact.py` to `backend/security/redact.py`.

This middleware scans all API responses and agent outputs for patterns that look
like secrets (API key patterns, private keys, passwords) and redacts them before
returning to the client. Apply to all `/api/` responses.

## File Safety

Port `hermes-agent/agent/file_safety.py` to `backend/security/file_safety.py`.
Already referenced in Prompt 03 - ensure it is available here too.

## Prompt Injection Guard

From Aiva (commercial) `core.carinaai.uk/src/security/` (minus Scout):
- `backend/security/prompt_guard.py` - detect prompt injection attempts in user input
- Heuristics: look for instruction override patterns, role injection, delimiter tricks
- Log suspicious inputs to `audit_log` table
- Do not block (CE is self-hosted); only log and warn

## Audit Log

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    severity TEXT DEFAULT 'info' CHECK (severity IN ('info','warn','error','critical')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON audit_log (user_id, created_at DESC);
CREATE INDEX ON audit_log (event_type, created_at DESC);
```

Logged events: login, logout, failed login (with count), vault unlock/lock,
webhook triggered, admin action, suspicious prompt detected, wipe action.

## Backup and Restore

Port from Odysseus `routes/backup_routes.py` and `docs/backup-restore.md`:
```
routes/backup_routes.py -> backend/workspace/backup_routes.py
```

```
POST   /api/admin/backup/create       - create backup archive (.zip)
GET    /api/admin/backup/list         - list available backups
GET    /api/admin/backup/{id}/download - download backup file
POST   /api/admin/backup/restore      - restore from uploaded backup
DELETE /api/admin/backup/{id}         - delete backup file
```

Backup includes: all PostgreSQL tables (pg_dump), Redis state snapshot,
uploaded files, config file. Encrypted with user-supplied backup password
(AES-256, optional). Restore validates backup integrity before applying.

From `odysseus/docs/backup-restore.md` - implement the documented restore
procedure as an automated endpoint. No manual DB operations required.

## Rate Limiting

`backend/security/rate_limiter.py`:
- Apply to: `/api/auth/login` (5 attempts per 10 minutes per IP)
- Apply to: `/api/auth/register` (3 per hour per IP)
- Apply to: inbound webhooks (10 per minute per token)
- Use Redis for counter storage
- Return 429 with `Retry-After` header on limit exceeded

## Security Headers

`backend/security/headers_middleware.py` - add to all responses:
```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
```

Do not add HSTS here; let the reverse proxy (nginx) handle it.

## Acceptance Criteria

- `POST /api/auth/login` with correct password returns bearer token
- `POST /api/auth/login` with wrong password 6 times returns 429
- TOTP: enabling 2FA requires correct code on next login
- Vault: `GET /api/vault/items/{id}` without unlock returns 403
- Vault: decrypted value never appears in `audit_log.event_data`
- Backup: `POST /api/admin/backup/create` produces a downloadable .zip
- Restore: uploading a valid backup archive restores data
- All API responses include `X-Content-Type-Options: nosniff`
- `redact.py` replaces `sk-ant-api03-...` patterns with `[REDACTED]` in outputs
