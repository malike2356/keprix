# Tool credential isolation

Keprix tools that call external APIs can declare credential routes with `@credential`. The tool sends ordinary HTTP requests through the credential-injection proxy; the proxy injects the real header from the external vault. The tool code only sees dummy environment variables and never receives the real secret.

```python
from keprix.tools.credential_contract import CredentialRoute, credential

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
def create_payment(...):
    ...
```

The registry validates declared routes against `~/.keprix/proxy.toml`, the proxy process, and the configured vault provider. Failed route configuration blocks strict startup validation. Missing secrets are warnings so operators can add or rotate credentials without editing tool code.

## Audit trail

Credential use is written to `~/.keprix/credential-audit.jsonl` and exposed to admins at:

- API: `GET /api/admin/credentials`
- UI: `/admin/dashboard/credentials`

Audit entries include timestamp, tool, session id, host, path, method, credential reference, response status, and duration. Secret values are never written.

## Rotation

A `401` response is shown in the audit trail with a link back to this section. Rotate the secret in the external vault, then run:

```bash
keprix proxy verify
keprix proxy doctor
```

Use [Credential rotation](credential-rotation.md) for hot key reload, manual invalidation, and scheduled reminders.
