# OpenAI-compatible API

Keprix exposes OpenAI-style endpoints for drop-in client compatibility.

## Endpoints

| Path | Purpose |
| --- | --- |
| `/v1/chat/completions` | Chat completions |
| `/v1/models` | Model list |
| `/v1/embeddings` | Embeddings |
| `/v1/responses` | Responses API |
| `/v1/keys/self-disable` | Disable the calling key (leak response) |

## Authentication

Use instance API keys from **Developer > API keys**.

New keys are restricted by default (chat + models). Grant extra endpoints in the key editor.

```bash
export KEPRIX_API_KEY=kp_...
curl -X POST "$KEPRIX_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KEPRIX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"keprix","messages":[{"role":"user","content":"hello"}]}'
```

## Live schema

`/openapi.json` on your running backend.
