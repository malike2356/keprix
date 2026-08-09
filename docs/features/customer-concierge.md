# Customer Concierge (setup and publish)

Prompt **628** adds a Keprix-native Customer Concierge setup wizard and publish control. Visitors never receive a workspace-member session.

## Surfaces

| Surface | Path |
| --- | --- |
| Operator area | `/concierge` (Setup, Conversations, Bookings, Knowledge, Channels, Integrations, Analytics) |
| Public embed | `/embed/concierge/{workspaceId}/{personaId}` |
| API | `/api/customer-concierge/*` |
| Public API | `/api/customer-concierge/public/{workspaceId}/{personaId}/*` |

## Wizard

1. Step 1: persona name, greeting, business identity, knowledge source IDs, escalation email
2. Step 2: channels (web / Telegram / WhatsApp / email), business hours, optional calendar and conferencing providers, meeting types

Publish is blocked while readiness blockers remain. Calendar and conferencing are optional in Community Edition; ICS-only booking fallback is allowed when no online provider is selected. Selecting a provider without connecting it blocks publish when that provider is required.

## Persona prompt

When published, `build_concierge_persona_overlay` injects business name, description, published knowledge boundary, business hours, and escalation contact. Registered as product prompt layer `customer_concierge`.

## Related

- Shared contract: `/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-CUSTOMER-CONCIERGE-BOOKING.md`
- Package: `src/keprix/customer_concierge/`
- Later prompts harden audience principal (630), knowledge (631), Zoom saga (632), and inbox tabs (634)
