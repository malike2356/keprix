# CRM integrations (HubSpot, Salesforce, Pipedrive, GHL)

Writing style: plain ASCII only.

## Purpose

Import and export between Keprix CRM and external CRMs without lock-in.
CSV always works. Official APIs require credentials; missing keys return honest
`not_configured` status (no fake live sync).

## Operator paths

- GUI: `/crm/integrations`
- Preview: `POST /api/crm/integrations/preview`
- Soft Wall apply: `POST /api/crm/integrations/import`
- Export: `GET /api/crm/integrations/export?provider=...&stage=...&list_id=...`
- Adapter status: `GET /api/crm/integrations`

## Credentials

Prefer workspace Connections GUI: **`/crm/settings#connections`** (encrypted at rest).
Process env remains a fallback for ops deploys. See `docs/features/crm-connections.md`.

| Provider | Slot / env keys (first match wins) |
| --- | --- |
| HubSpot | `hubspot_access_token` / `KEPRIX_HUBSPOT_ACCESS_TOKEN`, `HUBSPOT_ACCESS_TOKEN` |
| Salesforce | `salesforce_access_token` / `KEPRIX_SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_ACCESS_TOKEN` |
| Pipedrive | `pipedrive_api_token` / `KEPRIX_PIPEDRIVE_API_TOKEN`, `PIPEDRIVE_API_TOKEN` |
| Go High Level | `ghl_api_key` / `KEPRIX_GHL_API_KEY`, `GHL_API_KEY` |
| CSV | none |

## Field mappings (inbound CSV / compatible export)

Canonical Keprix columns: `email`, `first_name`, `last_name`, `company`, `phone`, `notes`, `external_id`.

| Provider | External column | Keprix field |
| --- | --- | --- |
| HubSpot | email | email |
| HubSpot | firstname | first_name |
| HubSpot | lastname | last_name |
| HubSpot | company | company |
| GHL | Email | email |
| GHL | First Name | first_name |
| GHL | Last Name | last_name |
| GHL | Company Name | company |
| Salesforce | Email | email |
| Salesforce | FirstName | first_name |
| Salesforce | LastName | last_name |
| Salesforce | Company | company |
| Pipedrive | email | email |
| Pipedrive | name | first_name |
| Pipedrive | org_name | company |

## External id map

Table `crm_external_id_map` stores `(workspace_id, provider, external_id, crm_object_type)` ->
`crm_object_id`. Re-import with the same external id updates the same lead.

## Soft Wall

Import apply uses Soft Wall kind `crm_integration_import`. Conflicts (mapped id
disagrees with email match) are skipped, not force-merged.

## Honesty

Live API push is not claimed when only CSV fallback exists. Adapters with keys
present may still export CSV-compatible payloads until live push is wired.
