# Operator migration: Carina bridge -> product sidecar capabilities

**Writing style:** plain ASCII only.

## Before

`POST /carina/agent/run` with `Authorization: Bearer $CARINA_KEPRIX_SHARED_TOKEN`.

## After (preferred)

1. Exchange: `POST /v1/products/carina/token/exchange` (bootstrap shared token).
2. List: `GET /v1/products/carina/capabilities`.
3. Invoke: `POST /v1/products/carina/invoke` with short-lived token + `X-Correlation-ID`.
4. Soft Wall: follow `deep_link`; decide via `POST .../approvals/{id}/decision`.

Aiva uses `/v1/products/aiva` with the same nodes minus Carina-admin-only.

Legacy `/carina/agent/run` remains a compatibility shim mapped to `agent.run`.
