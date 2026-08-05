# keprix - Prompt 02: Security Foundation and Platform Hardening

## Purpose

Security is not a feature that gets added later. This prompt builds the security layer that
every other component depends on. It must be completed before Prompts 03 onwards.

Scope:
- Input validation and sanitization at every API boundary.
- Output redaction to prevent credential and PII leakage in agent replies.
- HTTP security headers.
- CORS configuration.
- Rate limiting.
- Session management and token security.
- Structured audit log.
- Vault bootstrap (full vault is in Prompt 08; this prompt creates the interface it depends on).
- Secret scanning guard (prevents credentials from reaching logs or responses).
- Dependency audit hook.

## Input Validation

`backend/security/validation.py`

All input to the API is validated before any business logic runs. Do not trust request data.

```python
class InputValidator:
    MAX_STRING_LENGTH = 65536          # 64 KB, hard limit on any single string field
    MAX_ARRAY_LENGTH = 1000
    MAX_NESTED_DEPTH = 10

    def validate_string(self, value: str, field_name: str, max_length: int | None = None) -> str:
        """Strip null bytes, validate length, return clean string."""

    def validate_url(self, value: str, field_name: str, allowed_schemes: list[str] | None = None) -> str:
        """Validate URL structure. Default allowed schemes: https, http."""

    def validate_path(self, value: str, field_name: str, base_dir: str) -> str:
        """Resolve path, confirm it is under base_dir (prevents path traversal)."""

    def validate_command_arg(self, value: str, field_name: str) -> str:
        """
        Reject strings that contain shell metacharacters when used as subprocess args.
        Tools must pass args as lists, never as shell strings.
        """
```

All FastAPI request bodies are validated with Pydantic models. Every model that accepts
free-text fields applies `InputValidator` in a `@field_validator`.

## Output Redaction

`backend/security/redactor.py`

The redactor runs on every agent output string before it reaches the client.

Redaction rules (applied in order):
1. Common API key patterns (OpenAI, Anthropic, GitHub, AWS, etc.) - replace with `[REDACTED:api_key]`.
2. Private key blocks (BEGIN RSA PRIVATE KEY, BEGIN EC PRIVATE KEY, etc.) - replace with `[REDACTED:private_key]`.
3. JWT tokens (three-part dot-separated base64) - replace with `[REDACTED:jwt]`.
4. Connection strings with passwords (`postgres://user:pass@host`) - redact password segment.
5. Environment variable assignments that match secret patterns (`SECRET=`, `KEY=`, `TOKEN=`,
   `PASSWORD=`, `PASS=`) - replace the value with `[REDACTED:secret]`.
6. IP addresses in private ranges - only if `keprix_REDACT_PRIVATE_IPS=true` (default off).
7. Custom patterns registered via `redactor.add_pattern(name, regex)` from other modules.

The redactor is NOT a content filter. It only removes credential-shaped strings. It does not
suppress information based on topic.

```python
class Redactor:
    def redact(self, text: str) -> str: ...
    def add_pattern(self, name: str, pattern: str) -> None: ...
    def audit_redaction(self, original_hash: str, redacted: str, patterns_fired: list[str]) -> None: ...
```

The `audit_redaction` method logs what was redacted (without the original value) so the
operator can tell if legitimate output is being suppressed.

## HTTP Security Headers

`backend/security/headers.py`

Applied as FastAPI middleware to every response.

Required headers:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'; ...  (configured per environment)
Strict-Transport-Security: max-age=31536000; includeSubDomains  (when HTTPS is enabled)
```

CSP is configurable via `keprix_CSP_EXTRA` so operators can add their own directives.

Do not set `Access-Control-Allow-Origin: *` anywhere in the main API. CORS is handled
separately below.

## CORS

`backend/security/cors.py`

Default policy: allow only origins listed in `keprix_ALLOWED_ORIGINS`. If the
variable is empty, allow `localhost` and `127.0.0.1` only.

Do not expose credentials to wildcard origins. Use `allow_credentials=True` only for
origins that are explicitly whitelisted.

Expose the following headers in CORS responses:
`X-Request-ID`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## Rate Limiting

`backend/security/rate_limit.py`

Rate limiting by user ID for authenticated routes and by IP for unauthenticated routes.

Default limits (configurable via environment variables):
- General API: 300 requests per minute per user.
- Agent chat: 60 requests per minute per user.
- Key activation: 5 requests per hour per IP.
- Risky tools: 100 operations per hour per user (local approval).
- Auth routes (login, register): 10 requests per 15 minutes per IP.

Use Redis as the rate limit store. Use a sliding window algorithm (not fixed window).

Add `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers to every response.

Return 429 with a clear message when a limit is exceeded:
```json
{
  "code": "rate_limited",
  "message": "Too many requests. You have {remaining} requests left. Reset at {reset_time}.",
  "retry_after": 42
}
```

## Session Management

`backend/security/sessions.py`

- Sessions are stored in Redis with a configurable TTL (default 7 days).
- Session tokens are 256-bit random values (32 bytes from `secrets.token_bytes`).
- Tokens are stored as `sha256(token)` in Redis. The raw token is never stored server-side.
- Tokens are sent in `HttpOnly; Secure; SameSite=Strict` cookies.
- API key auth is also supported for machine-to-machine use.
- Session data: user ID, created at, last seen, IP hash, user-agent hash.
- On logout: delete the session record from Redis immediately.
- Implement session listing (`GET /api/auth/sessions`) so users can see and revoke active
  sessions.

2FA:
- TOTP (Google Authenticator compatible) via `pyotp`.
- Backup codes: 10 single-use codes stored as bcrypt hashes.
- 2FA enforcement configurable per user (optional by default; admin can require it globally).

## Audit Log

`backend/security/audit.py`

A structured audit log for all security-relevant events. Separate from application logs.
Written to PostgreSQL so it can be queried, not just tailed.

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id TEXT,
    session_id TEXT,
    ip_hash TEXT,
    resource_type TEXT,
    resource_id TEXT,
    action TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('success', 'failure', 'denied')),
    detail JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON audit_log (user_id, occurred_at DESC);
CREATE INDEX ON audit_log (event_type, occurred_at DESC);
CREATE INDEX ON audit_log (result, occurred_at DESC);
```

Event types to log:
- `auth.login`, `auth.logout`, `auth.login_failed`, `auth.2fa_enabled`, `auth.session_revoked`
- `key.activated`, `key.deactivated`, `key.validation_failed`
- `agent.tool_run` (tool name, not full args, to avoid logging secrets)
- `developer_identity.created`, `developer_identity.verified`
- `cyber.*` events (logged separately in `cyber_audit_log`, cross-referenced here)
- `vault.secret_accessed`, `vault.secret_written`, `vault.secret_deleted`
- `admin.*` actions

IP addresses are stored as `sha256(ip + salt)` where salt is `keprix_IP_HASH_SALT`.
Never store raw IP addresses in the audit log.

## Vault Bootstrap

`backend/security/vault_bootstrap.py`

The full credential vault is implemented in Prompt 08. This bootstrap module creates the
interface that the rest of the platform uses, so Prompts 03-07 can reference it without
waiting for Prompt 08.

```python
class VaultClient:
    """
    Bootstrap interface. Returns plaintext credentials from environment variables.
    Prompt 08 replaces this with the full AES-256 encrypted vault backend.
    All callers use this interface, so the swap is transparent.
    """
    def get(self, key: str) -> str | None:
        """Return a credential by key. Falls back to env var if vault not yet initialized."""

    def set(self, key: str, value: str) -> None:
        """Store a credential. No-op in bootstrap mode (not yet persistent)."""

    def delete(self, key: str) -> None:
        """Remove a credential. No-op in bootstrap mode."""
```

Import via `from backend.security.vault_bootstrap import vault`. Prompt 08 replaces the
implementation, not the import path.

## Secret Scanning Guard

`backend/security/secret_scan.py`

A lightweight scanner that runs on:
1. Any string being written to the audit log.
2. Any agent output before it is stored in the database.
3. Any file upload before it is saved.

It does not scan web traffic (that is the redactor's job). It scans data at rest.

If a credential pattern is found in stored data, it logs a `security.credential_in_storage`
event to the audit log and replaces the credential with `[REDACTED]` before writing.

The patterns used are the same as the redactor's patterns. They live in a shared
`backend/security/patterns.py` module imported by both.

## Dependency Audit Hook

`scripts/audit-deps.sh`

A shell script that runs:
```bash
uv pip audit          # Python dependency CVE scan
pnpm audit            # JS dependency CVE scan
```

This script is run as a pre-commit hook and in CI. It does not fail the build on audit
findings by default (operators may accept known issues), but it prints a summary.

Add a `keprix_AUDIT_FAIL_ON_HIGH=true` env var that causes the script to exit 1
if any HIGH or CRITICAL vulnerabilities are found.

## Environment Variables

```bash
keprix_ALLOWED_ORIGINS=http://localhost:3000
keprix_SESSION_TTL_DAYS=7
keprix_REQUIRE_2FA=false
keprix_IP_HASH_SALT=              # required, set during init
keprix_CSP_EXTRA=                 # optional, additional CSP directives
keprix_REDACT_PRIVATE_IPS=false
keprix_AUDIT_FAIL_ON_HIGH=false
```

## Output Paths

```
backend/security/
  __init__.py
  validation.py
  redactor.py
  headers.py
  cors.py
  rate_limit.py
  sessions.py
  audit.py
  vault_bootstrap.py
  secret_scan.py
  patterns.py          - shared regex patterns for redactor and secret scanner

scripts/
  audit-deps.sh
```

## Tests

```
tests/security/
  test_validation.py   - path traversal, null bytes, oversized inputs
  test_redactor.py     - API key patterns, private key blocks, JWT, connection strings
  test_headers.py      - all required headers present in responses
  test_cors.py         - allowed origins pass, others are rejected
  test_rate_limit.py   - sliding window, headers, 429 response format
  test_sessions.py     - token generation, Redis storage, logout, 2FA flows
  test_audit.py        - events are written, IP is hashed, not raw
  test_secret_scan.py  - credential patterns are caught and replaced in stored data
```

## Acceptance Criteria

- `GET /api/health` returns all required security headers.
- Posting a path traversal string to any endpoint returns 422.
- An agent response containing a real API key has the key replaced with `[REDACTED:api_key]`.
- A CORS preflight from an unwhitelisted origin returns 403.
- The 61st login attempt within 15 minutes from the same IP returns 429.
- The audit log records every login success and failure with hashed IP.
- `scripts/audit-deps.sh` runs without error on a clean install.
- No raw IP address appears in the `audit_log` table.
