# Prompt 454 / N04: CRM integrations (HubSpot, Salesforce, Pipedrive, GHL)

**Status: COMPLETED 2026-08-08**
**Series:** 429-465
**Depends on:** 430, 448
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- Adapters hubspot/salesforce/pipedrive/ghl/csv with honest not_configured without keys
- External id map + Soft Wall import apply
- GUI `/crm/integrations` preview, Soft Wall apply, export
- Docs `docs/features/crm-integrations.md`
- Tests: `test_454_csv_preview_and_not_configured`
- Live HubSpot/SF/GHL HTTP push remains owner-credential deferred (CSV lock-in exit path ships)

## Goal

Import/export with external CRM systems using external-id maps and conflict previews.

## Acceptance

- [x] CSV GHL export imports cleanly back as preview
- [x] API adapter stubs refuse without credentials
- [x] External ids stable across re-import

## Done When

Operators can leave or enter Keprix CRM without dead-end lock-in.
