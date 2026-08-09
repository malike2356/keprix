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

## Contract and capability health (Prompt 629)

- Vendored contract: `contracts/customer-concierge-v1/` (version 1.0.0)
- Gap audit: `docs/architecture/customer-concierge-v1-baseline-audit.md`
- Capability matrix: `docs/architecture/customer-concierge-capability-matrix.md`
- Health API: `GET /api/customer-concierge/capability-health` (honest `not_configured`; `ready=false` until managed booking exists)

## Booking saga and Zoom (Prompt 632)

- Canonical service: `keprix.vical.saga.book_with_saga` (idempotent booking + conference provision)
- Zoom user OAuth via encrypted local token store (`vical/zoom_oauth.py`); no VERLOX-hosted credential service
- Host start URL redacted from public DTOs/logs; join URL persisted
- Webhook: `POST /api/vical/webhooks/zoom` (signature + dedupe)
- Operator: `/api/customer-concierge/integrations/zoom/*` + Integrations tab; doctor: `keprix.vical.doctor.run_vical_doctor`
- CE: labelled static URL + ICS fallback when Zoom is not configured
- Tests: `tests/customer_concierge/test_booking_saga_zoom_632.py`

## Calendar invitations and reconciliation (Prompt 633)

- Package: `src/keprix/vical/calendar/` (Google, Microsoft, ICS adapters + projection store)
- Host calendar creation and guest invitation delivery evidenced separately
- Durable notification outbox (`vical_notification_outbox`); not an in-memory list as sole record
- Google push: `POST /api/vical/webhooks/google-calendar` (channel token + dedupe + attendee reconcile)
- Invitation view: `GET /api/vical/bookings/{id}/invitation`
- CE: ICS-only host event + outbox invite when Google/Microsoft absent
- Tests: `tests/customer_concierge/test_calendar_invitations_633.py`

## Published knowledge, customer cases, handoff (Prompt 631)

- Tenant knowledge store with `draft` / `published` / `archived` + revisions (`published_knowledge.py`)
- Visitors only receive grounded answers from **published** sources attached to the persona
- Low confidence and sensitive intents auto-escalate via handoff + customer support case
- Customer cases live under `/api/customer-concierge/cases` with scope `tenant_customer_support` (never `/api/support` product tickets)
- Internal notes are owner-only; public widget responses set `internalNotesVisible: false`
- Operator UI: Knowledge and Conversations tabs on `/concierge`
- Tests: `tests/customer_concierge/test_knowledge_support_631.py`

## Audience principal (Prompt 630)

External visitors use a durable `audience_session` principal (not a workspace member or API operator).

- Package: `src/keprix/customer_concierge/audience/`
- Public web session: `POST /api/customer-concierge/public/{workspaceId}/{personaId}/session`
- Gateway channel session: `POST .../channel/session` (Telegram and peers)
- Deny-by-default tool policy (`tool_policy.py`); shell, Vault, Brain, admin, billing blocked in code
- Signed embed tokens + nonce replay prevention; optional origin allowlist
- Operator privacy: `GET/DELETE /api/customer-concierge/audience/identities...`
- Tests: `tests/customer_concierge/test_audience_principal_630.py`

## Related

- Shared architecture: `/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-CUSTOMER-CONCIERGE-BOOKING.md`
- Package: `src/keprix/customer_concierge/`
- Later prompts: knowledge (631), Zoom saga (632), inbox tabs (634)
