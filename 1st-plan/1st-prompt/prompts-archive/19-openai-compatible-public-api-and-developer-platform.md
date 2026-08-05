# keprix - Prompt 19: OpenAI-Compatible Public API And Developer Platform

## Purpose

Add a public developer platform to keprix with OpenAI-compatible endpoints, API keys, usage reporting, webhooks, SDKs, and app integration workflows.

keprix should be usable as a drop-in local or self-hosted AI workspace for builders who already know OpenAI-compatible APIs, while also exposing Carina-native capabilities such as tools, memory, playbooks, jobs, research, and app actions.

## Scope

Implement:

- OpenAI-compatible chat completions.
- OpenAI-compatible responses where practical.
- Models endpoint.
- Embeddings endpoint where configured.
- API key management.
- Usage metering.
- Developer dashboard.
- Webhook management.
- Request logs with redaction.
- Rate limits.
- SDK examples.
- OpenAPI documentation.

## Output Paths

```text
keprix/backend/public_api/
  __init__.py
  auth.py
  keys.py
  openai_compat.py
  responses.py
  models.py
  embeddings.py
  usage.py
  webhooks.py
  logs.py
  rate_limits.py
  schemas.py

keprix/ui/web/developer/
keprix/sdk/python/
keprix/sdk/typescript/
keprix/docs/developer/
keprix/tests/public_api/
```

## API Surface

Expose:

```text
POST /v1/chat/completions
POST /v1/responses
GET  /v1/models
POST /v1/embeddings
GET  /api/developer/keys
POST /api/developer/keys
DELETE /api/developer/keys/{id}
GET  /api/developer/usage
GET  /api/developer/logs
GET  /api/developer/webhooks
POST /api/developer/webhooks
POST /api/developer/webhooks/test
```

## Security Rules

- API keys are hashed at rest.
- API keys are scoped by workspace and role.
- API keys can be limited by model, endpoint, tool, and monthly usage.
- Logs redact prompts where workspace policy requires it.
- Tool calls require explicit permission.
- Webhooks are signed.
- Rate limits are enforced per key and workspace.

## Developer UX

The developer dashboard must show:

- API keys.
- Usage.
- Rate limits.
- Available models.
- Enabled tools.
- Webhooks.
- Recent errors.
- SDK snippets.
- OpenAPI schema link.

## Tests

Add tests for:

- OpenAI-compatible chat request returns valid response shape.
- Invalid API key is rejected.
- Deleted API key stops working.
- Usage is recorded.
- Rate limit blocks excessive calls.
- Webhook signature is valid.
- Logs redact secrets.

## Acceptance Criteria

- keprix supports OpenAI-compatible client integrations.
- Developers can create, revoke, and scope API keys.
- Usage and errors are visible.
- Webhooks are signed and auditable.
- Carina-native capabilities remain permission-gated.
