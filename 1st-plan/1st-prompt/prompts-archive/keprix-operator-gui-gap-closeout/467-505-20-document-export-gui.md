# Prompt 487 / 20: Document export GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/data?tab=export` cover/signatory/classification Soft Wall
- Documents page link; `document-export-api.ts`


**Depends on:** 467, existing `/api/export`
**Blocks:** 505

## Goal

Operators export documents with classification/signatory/cover options from GUI.

## Must-haves

1. Entry points: Documents page export action + `/data?tab=export` optional hub.
2. Form: template, classification, signatory, format (HTML/PDF), destination.
3. Soft Wall if export includes restricted classification.
4. Download + activity audit.
5. Client for `/api/export`; tests; docs.
6. Never dump secrets into export payloads.

## Acceptance

- [x] Operator completes signed/cover export from GUI
- [x] Restricted classification Soft Wall gated

## Done When

Export is not curl-only.
