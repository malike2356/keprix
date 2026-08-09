# Standalone lead outreach funnel orchestration (Prompt 627)

**Status:** IMPLEMENTED  
**Date:** 2026-08-09  
**Series:** `keprix-standalone-lead-outreach` (620-628)

## Goal

Unify leads, contacts, customers, campaigns, replies, bookings, tasks, approvals, agents, and channels into one durable CRM funnel that Keprix can orchestrate as a standalone product.

## Lifecycle aliases (not a third stage vocabulary)

Prompt labels map to existing `CrmStage` values (docs/UI aliases only):

| Prompt label | CrmStage |
| --- | --- |
| New Lead | `discovered` |
| Enriched | `enriched` |
| Ready for Outreach | `listed` / `approved` |
| Contacted | `contacted` |
| Replied | `engaged` |
| Qualified | `qualified` |
| Appointment Booked | `booked` |
| Proposal | `booked` (alias; no new enum) |
| Customer | `customer` / `paying` |
| Closed Lost | `lost` |
| Suppressed | `suppressed` |

Post-customer nurture uses sequence kind `nurture`, not a new stage.

Conversion helpers: Soft Wall `lead→contact` and `lead→customer/paying` with attribution preserved. Identity merge remains the existing Soft Wall path.

## Modules

| Module | Role |
| --- | --- |
| `crm/lifecycle.py` | Aliases + Soft Wall conversion |
| `crm/funnel_orchestrator.py` | Durable trigger→action runner + `crm_funnel_runs` |
| `crm/channel_journey.py` | Sheet → list → Soft Wall campaign journey |
| `crm/channel_adapters.py` | Thin Slack/WhatsApp adapters (PARTIAL without bytes) |
| `crm/next_best_action.py` | Suggestions; execute always Soft Wall gated |
| `crm/nurture.py` | Stop-on-reply + optional Soft Wall branch |
| `crm/funnel_analytics.py` | Time-in-stage, conversion rates, rollups |
| `sheet_preprocess/email_ingest.py` | IMAP sheet poll when enabled (default off) |
| `crm/telegram_funnel.py` | Telegram intents including journey |

## Triggers and actions

Triggers: `lead_created`, `enriched`, `list_joined`, `stage_changed`, `campaign_enrolled`, `provider_event`, `reply_received`, `booking_created`, `no_response_after_delay`, `task_overdue`, `converted`, `suppressed`.

Actions call existing services: assign agent, add tag, add to list, update stage, create task, request approval, enrol/pause sequence, draft reply, notify, schedule follow-up, enrich, create booking link.

Idempotency key: `(workspace_id, trigger, subject_id, action, idempotency_key)`. Soft Wall for high-risk actions. Suppression never bypassed.

## Channel journey

1. `ingest_channel_attachment` / sheet upload  
2. Soft Wall enrich propose (or skip)  
3. Add eligible leads to list  
4. Draft campaign → Soft Wall  
5. After approve: enroll eligible  
6. Monitor replies via existing `scan_replies` (626; do not use email_ingest for replies)  
7. Funnel digest outcomes  

Telegram: REAL initiation. Slack/WhatsApp: PARTIAL thin adapters to the same journey when attachment bytes exist.

## Surfaces

- API: `/api/crm/funnel/*` (orchestrate, nba, journey, analytics), `/api/crm/lifecycle/aliases`, convert  
- Tools: `crm_funnel_orchestrate`, `crm_next_best_action`, `crm_channel_journey`  
- CLI: `keprix crm-funnel tick|nba|journey`  
- Web: CRM home conversion/journey cards; pipeline NBA chip  

## Contabo notes

- Keep `KEPRIX_OUTREACH_DRY_RUN=1`  
- Keep `KEPRIX_SHEET_EMAIL_INGEST` default off (`0`)  
- `standalone_outreach_ready` is true after Prompt 628 (E2E + observability + ops)

## Tests

```bash
cd /opt/lampp/htdocs/verlox/keprix
./.venv/bin/python -m pytest \
  tests/crm/test_funnel_orchestrator.py \
  tests/crm/test_channel_journey.py \
  tests/crm/test_next_best_action.py \
  tests/sheet_preprocess/test_email_ingest.py \
  tests/crm/test_telegram_funnel.py \
  tests/crm/test_standalone_outreach_conformance.py \
  -q --tb=short
```
