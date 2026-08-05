# Prompt 381 / 05: Public book page and embed

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 380 / 04  
Blocks: 388  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur guest UX is `/book/{slug}` (+ embed). Keprix today has no guest funnel; appointments are operator/agent only.

## Goal

Ship a professional public booking funnel and optional embed in the Next frontend, calling `/api/vical` public endpoints.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur public views | `resources/views/tenant/vical/` book/cancel/reschedule/thanks/embed |
| Help | `resources/docs/help/vcal-bookings/06-public-booking-links.md` |
| Keprix UI patterns | `/calendar` page density; Companies House operator polish as quality bar |
| PageHeader / EmptyState | existing frontend UI kit |

## Must-haves

1. Routes:
   - `/book/{slug}`: choose event type (if multiple), pick slot, guest details, thanks.
   - `/book/{slug}/cancel` and `/book/{slug}/reschedule` via guest token query/body.
   - Optional `/book/embed/{slug}` minimal chrome for iframe.
2. Mobile-first, accessible forms; no noticeboard walls of text.
3. Honor event type approval / payment pending copy honestly ("request received" vs "confirmed").
4. ICS download link on thanks when confirmed (may stub until 08 wires full ICS; if stub, note and finish in 08). Prefer shipping real ICS with 08 same PR if small.
5. Public branding: Keprix Community / host display name; no Propreneur property jargon.
6. Feature flag / auth: guest pages must not require workspace login.
7. Tests: route renders; API failure shows clean error.

## Nice-to-haves

1. Signed embed tokens (Propreneur `VcalEmbedTokenService`).
2. Locale timezone picker for guest.

## Ultimate

1. Mentor directory / programmes public pages (Propreneur-only; skip unless owner asks).

## Acceptance

- [ ] Unauthenticated guest can book a free auto-confirm type end-to-end against local API.
- [ ] Cancel by token works within window.
- [ ] Embed route loads without app chrome.
- [ ] Writing-style scan clean on new copy.
