# Prompt 411 / 08: RAG admin UI and training automation

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 403 / 00  
Blocks: 412  
Severity: MEDIUM  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina has richer RAG admin/training surfaces. Keprix RAG works but operator UX lags (`data-ops-surfaces-upgrade` may overlap; coordinate, do not duplicate).

## Goal

Improve `/data` RAG tab: pipeline status, ingest actions, evaluation snapshot; optional training job stub with honest status.

## Must-haves

1. Align with existing data-ops prompt; fill only missing Must items for RAG admin.
2. API + UI for list pipelines / last run / trigger ingest (auth).
3. Docs update.

## Acceptance

- [x] Operator can see RAG health without shell.
- [x] No secret leakage in UI.
