# Developer platform

Build on Keprix with API keys, webhooks, and OpenAI-compatible endpoints.

## Security model

- Public contract is primarily `/v1/*` (OpenAI-compatible). Workspace `/api/*` is reachable with API keys only when those scopes are explicitly granted.
- New keys are **restricted by default**: chat completions + models only; tools off; models allowlisted.
- Secrets are shown once, stored hashed (`kp_...`).
- Session cookies never authenticate `/v1`.
- Token security and client approval **fail closed** (503) if subsystems error.
- `KEPRIX_API_TOKEN` is a restricted break-glass token unless `KEPRIX_API_TOKEN_UNRESTRICTED=1`. Tools require `KEPRIX_API_TOKEN_ALLOW_TOOLS=1`.
- Key management when `AUTH_ENABLED=false` is limited to loopback (or `KEPRIX_API_ADMIN_TOKEN`).

## Web UI (`/developer`)

ElevenLabs-style API key editor:

- Name, expire after, restrict key, usage limits
- Granular endpoint permissions (No Access / Access / Read / Write)
- Restrict by IP
- Auto-disable if leaked (`POST /v1/keys/self-disable`)
- Enable/disable toggle, edit, revoke
- Client approvals and usage monitor

## OpenAI-compatible API

| Endpoint | Purpose | Default on new keys |
| --- | --- | --- |
| `POST /v1/chat/completions` | Chat | Yes |
| `GET /v1/models` | Model list | Yes |
| `POST /v1/responses` | Responses API | No |
| `POST /v1/embeddings` | Embeddings | No |
| `POST /v1/keys/self-disable` | Disable calling key if leak flag on | Always (authenticated) |

Authenticate with `Authorization: Bearer <api_key>` or `X-API-Key`.

## Workspace `/api/*` via API keys

Grant scopes such as Conversations, Tasks, Voice, Memory, Admin in the key editor. Restricted keys without those grants receive `403 endpoint_forbidden`.

## REST API

Full surface documented in [API reference](../reference/api.md) and interactive explorer.

## SDKs

- Python: `sdk/python/`
- TypeScript: `sdk/typescript/`

See [SDK](../integrations/sdk.md).

## Related

- [OpenAI-compatible API](../integrations/openai-api.md)
- [Client approval and token security](client-approval-token-security.md)
- [Settings](settings.md)
