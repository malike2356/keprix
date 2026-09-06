# Worker Tool Coverage Audit

Status: current implementation audit, 2026-09-01.

| Business surface | Worker tool | Scope | Notes |
| --- | --- | --- | --- |
| CRM contacts | `worker_contacts` | workspace | CRUD, fill-empty enrichment remains in Google Contacts tool |
| Document Vault notes | `worker_notes` | workspace | Markdown/plain-text notes through canonical vault |
| Calendar | Google Workspace calendar tools | connector/workspace | Existing connector |
| Documents | Document Vault and Google Workspace tools | workspace | Existing tools |
| Property due diligence | `property_due_diligence` | workspace | Explicit `not_configured` until canonical property backend |
| Property floor plans | `property_floor_plan_analyze` | workspace | Explicit `not_configured` until canonical property backend |
| Property saved searches | `property_saved_search_run` | workspace | Explicit `not_configured` until canonical property backend |
| Property calculators | `property_calculator_run` | workspace | Explicit `not_configured` until canonical property backend |

The property tools are placeholders only in the operational sense: they provide a
deterministic status response and never pretend to have performed an action. Prompts
034 and 035 must supply the backend before these tools can be upgraded to live calls.
