# CRM pack: property

Pack id: `property`  
Manifest: `src/keprix/discovery/packs/property.yaml`  
Legal checklist: `docs/security/property-portal-legal-checklist.md`

UK property operator vertical: stock sheets, landlord pipelines, and lawful
discovery. Prefer CSV, Companies House, and web directory.

## Adapters

| Adapter | Status | Notes |
| --- | --- | --- |
| `property_csv` | Enabled | Property stock / comparables CSV |
| `companies_house` | Enabled | Company research into CRM lists |
| `web_directory` | Enabled | Directory / search templates |
| `rightmove_http` | Stub / flagged | Off unless `KEPRIX_PROPERTY_PORTAL_ADAPTERS` |
| `zoopla_http` | Stub / flagged | Off unless portal flag; ToS risk documented |

Portal HTTP adapters default **disabled**. Do not claim scrape coverage in UI.

## Sheet types

`property_data`, `tenant_list`, `landlord_pipeline` (see manifest columns and
metrics).

## Soft Wall and honesty

List enrich and enroll use standard Soft Wall. Marketing copy must not imply
autonomous portal scraping.
