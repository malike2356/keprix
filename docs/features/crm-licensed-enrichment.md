# Licensed enrichment providers (Nice 456)

Bring-your-own licensed enrichment through the same Soft Wall apply path as sheet preprocess.

## Contract

`enrich_contacts(batch) -> patches + evidence + license_tag`

- Empty cells only (overwrite blocked)
- Each filled field stores provenance `source=provider:name`
- Soft Wall required before apply (`apply_enrichment`)
- Budget/rate counters per process (`DEFAULT_BUDGET`)

## Built-in slots

| Provider | Env | Behaviour |
| --- | --- | --- |
| `fake_licensed` | `KEPRIX_FAKE_ENRICH_KEY` or `KEPRIX_FAKE_ENRICH_ALWAYS=1` | Test provider |
| `clearbit_slot` | `KEPRIX_CLEARBIT_API_KEY` | Honest not_configured without key; no scrape |

## Legal note

Operators must hold licence rights for any commercial provider they enable. Keprix does not bundle Clearbit scraping or unlicensed data pulls.

## API

- `GET /api/crm/enrich/providers`
- `POST /api/crm/enrich/providers/propose`
- `POST /api/crm/enrich/providers/{run_id}/apply`
- `POST /api/crm/enrich/providers/{run_id}/reject`
