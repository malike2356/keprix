# Prompt 483 / 16: Mobile companion pairing GUI (Must)

**Status: COMPLETED 2026-08-08**
**Series:** 467-505 Keprix operator GUI gap closeout
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## What was built

- `/admin/companion` QR/code pairing + revoke Soft Wall
- Docs mobile.md prefers GUI; nav admin-companion


**Depends on:** 467, existing `/api/companion`
**Blocks:** 505

## Goal

Admins pair mobile companions via QR/code in GUI. Docs currently require
`POST /api/companion/pair` only.

## Must-haves

1. Route `/admin/companion` (or `/settings/companion`).
2. UI: create pair session, show QR + short code, expiry, revoke device list.
3. Wire to companion pairing routes; tokens never shown in full after create.
4. Device list: name, last seen, revoke Soft Wall/confirm.
5. Nav + docs update (`docs/integrations/mobile.md`) to prefer GUI.
6. Tests for pair create/revoke UI path.
7. Security: admin-only; audit events.

## Acceptance

- [x] Admin pairs device without curl
- [x] Revoke works from GUI
- [x] Docs no longer say API-only as the primary path

## Done When

Mobile pairing is a first-class admin surface.
