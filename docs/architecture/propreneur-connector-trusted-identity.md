# Propreneur product connector CRUD and trusted identity (prompt 638)

## Connector

`ProductApiConnector` allows GET, POST, PATCH, PUT, and DELETE **only when** the method+path pair is present in the generated pack connector manifest. SSRF, redirect blocking, host allowlists, response-size limits, SQL/admin path denial, and default-deny remain in force.

Path templates substitute declared `{params}` with URL-encoding. Missing or unexpected path parameters raise `ConnectorDenied`.

Undeclared generic deletion still fails via `delete_subject()`; product archive uses declared DELETE routes through `archive()` / `call_manifest()`.

## Trusted execution context

`TrustedExecutionContext` (`keprix/product_sidecar/trusted_context.py`) carries product, workspace/tenant, actor id/type, conversation, worker, correlation, scopes, channel binding, approval evidence, and idempotency key.

Keprix injects this server-side into Propreneur tool callbacks (JSON body + `X-Keprix-Trusted-*` headers). Model tool arguments cannot set or override identity fields. A callback registered for tenant A cannot be redirected to tenant B by tool arguments.

Propreneur `CarinaToolHttpController` prefers trusted headers and rejects workspace header/body mismatches.

Identity claims are **not** present in model-visible OpenAI tool schemas.

## Credentials

Prefer short-lived audience-bound sidecar exchange tokens (`TokenService.mint` / `authenticate_request`).

Compatibility shared bearer (`CARINA_KEPRIX_SHARED_TOKEN`) remains available during migration. Disable after the exchange path is proven:

```bash
export KEPRIX_DISABLE_SHARED_COMPAT_TOKEN=1
# aliases also honored:
# KEPRIX_PRODUCT_SIDECAR_DISABLE_SHARED_TOKEN=1
# CARINA_KEPRIX_DISABLE_SHARED_TOKEN=1
```

When disabled, `/carina/agent/run` and product-sidecar auth reject the shared bearer and require an exchange credential.

## Tests

- `keprix/tests/product_sidecar/test_propreneur_connector_trusted_identity.py`
- `keprix/tests/api/test_carina_agent_routes.py` (tenant hijack denied)
