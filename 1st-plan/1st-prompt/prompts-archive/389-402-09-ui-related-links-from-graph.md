# Prompt 398 / 09: UI related links from capability graph

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 390 / 01, 394 / 05, 396 / 07  
Blocks: 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

The mesh must be visible in the workspace UI, not only in the agent.

## Goal

Add a reusable "Related" / hop pattern driven by graph edges + object IDs on pilot pages.

## Must-haves

1. Shared frontend helper or component that, given feature id + object ids, renders links (calendar event, contact, booking, public book URL).
2. Wire into `/vical` booking detail and `/calendar` event detail (light touch; match existing UI kit).
3. Deep link query params where useful (`?event=`, `?booking=`).
4. Empty state when IDs missing (honest, not fake).

## Acceptance

- [ ] From a booking with `workspace_event_id`, hub links to calendar.
- [ ] From booking with `contact_id`, hub links to contact.
- [ ] No noticeboard walls of unrelated modules.
