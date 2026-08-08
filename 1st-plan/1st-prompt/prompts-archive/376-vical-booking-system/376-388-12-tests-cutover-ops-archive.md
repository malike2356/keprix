# Prompt 388 / 12: Tests, cutover, ops runbook, archive

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 377-383 minimum; ideally 384-386; 387 optional  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Programme ships only when cutover is honest, ECHO flag default is deliberate, and prompts can archive with evidence.

## Goal

Harden tests, write ops runbook, execute cutover checklist, update nav/docs, archive completed prompt files.

## Must-haves

1. Test matrix (pytest):
   - domain/store
   - slots/locks/busy
   - lifecycle + calendar bridge
   - API auth + conflict
   - ECHO unify flag on/off
   - reminders idempotency
   - intake disqualify (if 10 landed)
2. Manual smoke script or docs section:
   - create Consultation type
   - public book
   - appear on `/calendar`
   - ECHO book same host conflicts correctly
   - cancel via hub + guest token
3. Ops runbook in `docs/features/vical.md`:
   - env flags (`KEPRIX_VICAL_ENABLED`, reminder, SMS, sync)
   - Docker recreate notes
   - `.access` pointers (no secret values)
4. Cutover:
   1. Deploy schema/store
   2. Seed defaults
   3. Enable flag on staging
   4. Smoke ECHO + public
   5. Default flag on
   6. Remove legacy invent path (or ticket follow-up if soak needed)
5. Queue hygiene:
   - Mark each completed prompt Status COMPLETED with date
   - Move to `../prompts-archive/`
   - Update `keprix-vical-booking/README.md` progress
   - Update `pending-prompts/README.md`
   - Write/update `../prompts-archive/ref-376-keprix-vical-booking-build-order.md` as COMPLETED programme map
6. Writing-style scan on touched first-party files.

## Nice-to-haves

1. `keprix doctor` check: vical enabled + seed present.
2. Frontend smoke playwright optional.

## Acceptance

- [ ] Documented pytest command set green in CI or local evidence pasted into archive note (no secrets).
- [ ] Flag default decision recorded.
- [ ] Programme README progress fully checked or remaining items explicitly deferred with owner note.
- [ ] Pending queue no longer lists unfinished 376-388 as "ready" without status truth.
