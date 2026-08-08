# CRM Connections (workspace credentials + flags)

Operators configure CRM-dependent API keys, tokens, and feature flags under **`/crm/settings#connections`**.

## Behaviour

- Secrets encrypt at rest (`ENCRYPTION_KEY` via `keprix.email.crypto`).
- Status and list APIs return **masked last4 only**; plaintext never leaves the API.
- Adapters resolve **workspace credentials first**, then process env fallbacks (ops deploys).
- Feature flags (WhatsApp/SMS, LinkedIn/Meta/TikTok APIs, property portals, fake enrich) are workspace-scoped; Soft Wall still gates first sends and risky actions.

## Groups

| Group | Used by |
| --- | --- |
| CRM integrations | HubSpot, Salesforce, Pipedrive, GHL (`/crm/integrations`) |
| Licensed enrichment | Clearbit slot + fake enrich (`/crm/enrich`) |
| Messaging | WhatsApp Cloud + Twilio SMS (`/crm/messaging`) |
| Social | LinkedIn / Meta / TikTok API adapters (`/crm/discover`, messaging health) |
| Property portals | Rightmove/Zoopla feed tokens + portal flag (`/crm/messaging` portals) |

## API

- `GET /api/crm/connections`
- `PUT /api/crm/connections/credentials` `{ slot_id, value }`
- `DELETE /api/crm/connections/credentials/{slot_id}`
- `PUT /api/crm/connections/flags` `{ flag_id, enabled }`

Pass `workspace_id` (or `X-Workspace-Id`) on every call.
