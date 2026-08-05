# Prompt 410 / 07: Product tools layer (non-property)

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 405 / 02, 409 / 06, capability mesh 389-402  
Blocks: 415  
Severity: MEDIUM  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina/Aiva has outreach, campaigns, bookings, pipeline. Keprix now has viCal + mesh. Still thin on campaign/lead product surfaces that are channel-operable.

## Goal

Define a thin product tool layer for leads/campaigns that reuses Contacts + viCal + send_message, not a second CRM. Agent tools in core or opt-in toolset.

## Must-haves

1. Minimal lead/campaign store + API.
2. Tools: create_lead, list_leads, link_booking_to_lead (or equivalent).
3. Graph edges to contacts/vical.
4. Telegram-usable via tools (mesh DoD).

## Non-goals

Porting Aiva outreach sequences wholesale in this prompt (see Carina aiva-outreach prompts for that product line).

## Acceptance

- [x] Agent can create a lead and list it via tool in tests.
- [x] Mesh DoD soft gate still green.
