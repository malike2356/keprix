# keprix - Prompt: Tool Credential Isolation and Audit Trail

## Purpose

When a keprix agent calls a tool that makes an external API request (Stripe billing, SendGrid email, Google Calendar, database connections, web search APIs), that tool currently reads credentials from environment variables or the keprix vault. If the tool logs the request, crashes, or is compromised by prompt injection, real API keys leak.

This prompt ensures every tool call routes through the credential injection proxy (Prompt 239) and no tool ever holds a real secret. It also adds an audit trail so operators can see which tool used which credential, when, and for what.

## Prerequisites

- Prompt 239 (Credential Injection Proxy) -- the proxy must be running

## What already exists (do not rebuild)

- `tools/` -- 60+ tool implementations
- `agent/tool_executor.py` -- tool dispatch
- `agent/tool_guardrails.py` -- tool safety checks
- `agent/credential_pool.py` -- credential pool
- `security/audit.py` -- audit logging

## What to build

### 1. Tool credential contract

Every tool that makes external API calls must declare its credential requirements:

```python
# tools/stripe_tool.py
from keprix.tools.credential_contract import credential, CredentialRoute

@credential(
    routes=[
        CredentialRoute(
            host="api.stripe.com",
            header="Authorization",
            scheme="Bearer",
            secret_ref="stripe-secret-key",
        )
    ]
)
class StripeTool:
    async def create_payment(self, amount: int, currency: str) -> dict:
        # Tool code makes normal HTTP calls. Proxy injects credentials.
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stripe.com/v1/payment_intents",
                data={"amount": amount, "currency": currency},
            )
        return response.json()
```

The `@credential` decorator:

- Registers the route in the proxy config (if not already present).
- Validates at startup that the proxy is running and the route resolves.
- Wraps the tool execution with an audit span.
- Does NOT pass credentials to the tool. The tool code never sees them.

### 2. Tool credential registry

```python
# keprix/tools/credential_contract.py

@dataclass
class CredentialRoute:
    host: str
    header: str
    scheme: str | None = None
    secret_ref: str

class ToolCredentialRegistry:
    """Central registry of all tool credential requirements."""

    def register(self, tool_name: str, routes: list[CredentialRoute]) -> None: ...

    def validate_all(self) -> list[ValidationError]: ...
    # Returns errors for:
    # - Route not in proxy config
    # - Secret not found in vault
    # - Proxy not running

    def audit_log(self, tool_name: str, route: CredentialRoute, status: str) -> None: ...
```

### 3. Audit trail

Every proxied request is logged with:

```json
{
  "timestamp": "2026-07-06T12:34:56Z",
  "tool": "stripe.create_payment",
  "session_id": "sess_abc123",
  "route": {
    "host": "api.stripe.com",
    "path": "/v1/payment_intents",
    "method": "POST"
  },
  "credential_ref": "stripe-secret-key",
  "status": "injected",
  "duration_ms": 234,
  "response_status": 200
}
```

The audit log is stored in the keprix database (not in the proxy -- the proxy never stores data). The `@credential` decorator writes the audit entry after the tool call completes.

The operator can view the audit trail at `/admin/credentials` in the keprix dashboard:

| Timestamp | Tool | Route | Credential | Status | Duration |
|---|---|---|---|---|---|
| 12:34:56 | stripe.create_payment | api.stripe.com | stripe-secret-key | 200 OK | 234ms |
| 12:35:02 | sendgrid.send_email | api.sendgrid.com | sendgrid-api-key | 202 Accepted | 189ms |
| 12:35:10 | google_calendar.create | www.googleapis.com | google-api-key | 401 Unauthorized | 312ms |

### 4. Tool startup validation

When keprix starts, the `ToolCredentialRegistry.validate_all()` runs:

```
Credential check (4 tools, 7 routes):
  stripe.create_payment     -> api.stripe.com       OK (proxy running, secret found)
  sendgrid.send_email       -> api.sendgrid.com     OK
  google_calendar.create    -> www.googleapis.com   WARN: secret 'google-api-key' not found in vault
  web_search.search         -> api.tavily.com       FAIL: route not configured in proxy.toml

Add missing routes? Run: keprix proxy doctor --fix
```

The agent does NOT start if any tool has a FAIL status. Tools with WARN status start but log the warning.

### 5. Tool documentation contract

Every tool's docstring must include its credential requirements. The `@credential` decorator auto-generates the credential section:

```python
class StripeTool:
    """
    Create and manage Stripe payments.

    Credential requirements:
      - stripe-secret-key: stored in external vault, injected by proxy
      - Route: api.stripe.com, Authorization: Bearer <key>

    The proxy injects credentials. This tool never holds real API keys.
    """
```

## Files to create

```
src/keprix/tools/
  credential_contract.py     - @credential decorator, CredentialRoute, ToolCredentialRegistry
  credential_validator.py    - startup validation, proxy health check
  credential_audit.py        - audit trail writer

src/keprix/api/
  credential_audit_routes.py - GET /api/admin/credentials (audit trail)

frontend/src/app/(admin)/dashboard/
  credentials/
    page.tsx                 - credential audit trail table

docs/
  security/tool-credential-isolation.md

tests/
  tools/
    test_credential_contract.py
    test_credential_validator.py
    test_credential_audit.py
```

## Acceptance criteria

- Every tool that makes external API calls declares its credential routes via `@credential`.
- Tool code never accesses real API keys. All credentials are injected by the proxy.
- `keprix start` validates all tool credential routes and refuses to start if any FAIL.
- Every proxied tool call produces an audit log entry visible at `/admin/credentials`.
- A tool with a 401 response shows the error in the audit trail with a link to the credential rotation docs.
- The `@credential` decorator has zero runtime overhead after startup validation (it is a pass-through wrapper).
