# Prompt 444 / 15: Nurture workflows and stage machine automation

**Status: COMPLETED 2026-08-08**  
**Series:** 429-450  
**Depends on:** 442, 443  
**Blocks:** 445, 447  
**Writing style:** plain ASCII only.

## What was built

- Implemented in crm/ Soft Wall glue + UI + tests (442-448 wave)

## Goal

Go High Level-like nurture: reasonable interval follow-ups until lead becomes contact/customer/paying, with human gates.

## Must-haves

1. Workflow definitions (YAML or Soft Wall sequence extensions): steps, delays, channel, stop conditions.
2. Defaults: day 0 intro, day 3 value, day 7 soft CTA, day 14 break-up; stop on reply/book/suppress.
3. Stage machine transitions enforced in one module (`crm/stages.py`).
4. Cron/process_due integration with Soft Wall `process_due`.
5. Agent can create/adjust nurture plan under Soft Wall.
6. Cadence caps: max emails/week/contact; quiet hours.
7. Tests for transition graph and stop-on-reply.
8. Version workflows and define owner, entry, exit, maximum touches/duration,
   re-enrollment, cancellation, timezone, and activation window.
9. Sender readiness, contactability, final suppression, workspace/campaign/domain
   rate limits, and kill switches are checked at scheduling and send time.
10. `customer` and `paying` require verified business events or explicit human
    confirmation. Model sentiment cannot make those transitions.
11. **GUI (Must-thin):** `/crm/workflows` lists nurture workflows/sequences with
    status, enroll counts, Soft Wall publish/pause/activate. Full canvas is Nice
    451; Must must still operate workflows from GUI (not YAML-only).
12. Cadence caps and kill switches editable under `/crm/settings` (466) with Soft
    Wall when changing live campaigns.

## Acceptance

- [x] Enrolled lead receives timed steps without operator babysitting
- [x] Reply stops sequence
- [x] Illegal stage skip blocked or Soft Wall required
- [x] Operator can list/pause/activate nurture from `/crm/workflows`

## Done When

445 can attach booking CTA at qualified.
