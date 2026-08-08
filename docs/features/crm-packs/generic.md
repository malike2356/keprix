# CRM pack: generic

Pack id: `generic`  
Manifest: `src/keprix/discovery/packs/generic.yaml`

Default domain pack for Companies House, CSV, and web directory discovery when
no vertical pack is selected.

## Adapters

| Adapter | Status | Notes |
| --- | --- | --- |
| `companies_house` | Enabled | Requires CH API config; degrades to `not_configured` when missing |
| `csv_import` | Enabled | Operator-uploaded CSV / sheet-backed import |
| `web_directory` | Enabled | Rate-limited directory / search templates |
| `fake` | Enabled (dev) | Deterministic fixtures for tests and demos |
| Social API adapters | Stub / phased | LinkedIn / Meta / TikTok API-first stubs; scrape off by default |

## Sheet types

`generic`, `leads`, plus shared preprocess types. Column roles: identity,
metric, enrichment target, ignore, PII.

## Soft Wall

Same CRM Soft Wall gates as the programme default: list materialise, enrich
apply, enroll, first outbound, merge, kill-switch resume.

## Contactability defaults

Organisation and person contacts allowed when policy and consent/suppression
permit. Discovery hits are not contact permission.
