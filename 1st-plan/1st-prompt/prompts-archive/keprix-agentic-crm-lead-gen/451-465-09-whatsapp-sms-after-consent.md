# Prompt 459 / N09: WhatsApp Business and SMS (after consent)

**Status: COMPLETED 2026-08-08**
**Series:** 429-465
**Depends on:** 448 (consent/suppression Must), 444
**Blocks:** none
**Writing style:** plain ASCII only.

## What was built

- WhatsApp Cloud / Twilio SMS stubs with consent + Soft Wall first send
- Template registry Soft Wall; feature flag default off
- Workspace Connections GUI for WA token, phone number id, Twilio SID/token/from, and channel flag
- Messaging status surfaces `configure_path` to `/crm/settings#connections`
- Tests: `tests/crm/test_connections.py` (flag + provider ready after keys)
- Operator step remaining: enter provider credentials and enable flag, then Soft Wall enable on `/crm/messaging`

## Goal

WhatsApp Business and SMS outbound **only** via official providers, with explicit channel consent, template approval, and jurisdiction policies.

## Must-haves

1. Channel adapters: WhatsApp Cloud API / BSP stub, SMS via Twilio-like provider stub (keys in vault).
2. ConsentRecord channel scope: `email`, `sms`, `whatsapp` separately; enroll checks channel consent.
3. Template registry with provider template ids; Soft Wall before first use.
4. Soft Wall always on for first WhatsApp/SMS to a contact.
5. Stop keywords and suppression per channel.
6. Feature flags default **off** until 448 complete and owner enables.
7. Docs: prerequisites checklist (consent infra must exist).
8. Tests: send blocked without channel consent; flag off refuses.

## Acceptance

- [x] No SMS/WhatsApp send if only email consent present
- [x] Flag off returns honest error
- [x] Template unapproved cannot send
- [x] Connections GUI configures tokens without env-only gate

## Done When

Messaging channels cannot bypass PECR-style consent.

## Explicit non-goal

Unofficial WhatsApp web scrape / personal account automation.
