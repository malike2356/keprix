# Developer platform

Build on Keprix with API keys, webhooks, and OpenAI-compatible endpoints.

## Web UI (`/developer`)

- Developer identity fingerprint
- Create and revoke API keys (scopes, expiry)
- Webhook endpoints for agent events
- Links to OpenAPI explorer at `/api/docs`

## OpenAI-compatible API

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/chat/completions` | Chat completions |
| `POST /v1/responses` | Responses API shape |
| `POST /v1/embeddings` | Embeddings |

Authenticate with `Authorization: Bearer <api_key>`.

## REST API

Full surface documented in [API reference](../reference/api.md) and interactive explorer.

## SDKs

- Python: `sdk/python/`
- TypeScript: `sdk/typescript/`

See [SDK](../integrations/sdk.md).

## Developer identity

Run `keprix init` on the machine owner account to enable developer mode. See [Developer identity](../configuration/developer-identity.md).

## Related

- [OpenAI-compatible API](../integrations/openai-api.md)
- [Settings](settings.md)
