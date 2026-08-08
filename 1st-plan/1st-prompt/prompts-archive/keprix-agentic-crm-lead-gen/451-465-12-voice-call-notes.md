# Prompt 462 / N12: Telegram voice notes and call notes

**Status: COMPLETED 2026-08-08** (P5 Nice)  
**Series:** 429-465  
**Depends on:** 443, 446, 448  
**Blocks:** none  
**Writing style:** plain ASCII only.

## What was built

- Voice/call notes activities

## Goal

Voice-note transcription and call notes as CRM Activities with consent and retention controls.

## Must-haves

1. Telegram voice message -> Activity on linked lead/contact (operator tags or reply context).
2. Optional transcription via configured STT; store audio retention policy (days).
3. Call note form in CRM UI (manual) with duration, outcome, next step.
4. Consent/disclosure when recording or storing voice (workspace policy).
5. Soft Wall if sharing transcript outside workspace.
6. Tests: voice creates activity; retention job deletes expired media.

## Acceptance

- [x] Voice note appears on timeline with transcript when STT configured
- [x] Retention deletes blob after policy days
- [x] Unlinked chats do not invent CRM targets

## Done When

Human conversations enrich CRM without becoming unbounded audio storage.
